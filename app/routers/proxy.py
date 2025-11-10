import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response, StreamingResponse
from sqlalchemy.orm import Session
from app import database, crud
from app.claude_client import claude_client
from app.config import settings
import time
import json

router = APIRouter()

@router.api_route("/v1/{endpoint:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_claude_api(
    endpoint: str,
    request: Request,
    db: Session = Depends(database.get_db)
):
    # 验证API密钥
    auth_header = request.headers.get("authorization") or request.headers.get("x-api-key")
    if not auth_header:
        raise HTTPException(status_code=401, detail="API key required")
    
    api_key = auth_header.replace("Bearer ", "").replace("x-api-key ", "")
    key_hash = crud.hash_api_key(api_key)
    
    db_key = crud.get_api_key_by_hash(db, key_hash)
    if not db_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # 检查速率限制
    rate_allowed, rate_info = crud.check_rate_limit(db, db_key.id, db_key.rate_limit)
    if not rate_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Used {rate_info['current_usage']}/{rate_info['rate_limit']} requests in the last hour. Try again later.",
            headers={
                "X-RateLimit-Limit": str(rate_info['rate_limit']),
                "X-RateLimit-Remaining": str(rate_info['remaining']),
                "X-RateLimit-Reset": rate_info['reset_time'],
                "Retry-After": "3600"
            }
        )
    
    # 检查成本限制
    cost_allowed, cost_info = crud.check_cost_limit(db, db_key.id, db_key.cost_limit)
    if not cost_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Cost limit exceeded. Used ${cost_info['current_cost']:.6f}/${cost_info['cost_limit']:.2f} in the last hour. Try again later.",
            headers={
                "X-CostLimit-Limit": str(cost_info['cost_limit']),
                "X-CostLimit-Remaining": str(cost_info['remaining_cost']),
                "X-CostLimit-Reset": cost_info['reset_time'],
                "Retry-After": "3600"
            }
        )
    
    # 检查每日额度限制
    quota_allowed, quota_info = crud.check_daily_quota(db, db_key.id, db_key.daily_quota)
    if not quota_allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Daily quota exceeded. Used ${quota_info['current_usage']:.6f}/${quota_info['daily_quota']:.2f} today. Try again tomorrow.",
            headers={
                "X-DailyQuota-Limit": str(quota_info['daily_quota']),
                "X-DailyQuota-Remaining": str(quota_info['remaining_quota']),
                "X-DailyQuota-Reset": quota_info['reset_time'],
                "Retry-After": "86400"
            }
        )
    
    # 获取当前激活的后端配置
    backend_config = crud.get_active_backend_config(db)
    if not backend_config:
        raise HTTPException(status_code=503, detail="No backend configuration available")
    
    try:
        # 获取原始请求体
        request_body = await request.body()
        
        # 构建代理请求头 - 使用后端配置的API密钥
        proxy_headers = {}
        original_auth_header = None

        for k, v in request.headers.items():
            if k.lower() not in ["host", "authorization", "x-api-key"]:
                proxy_headers[k] = v
            elif k.lower() == "authorization":
                original_auth_header = "authorization"
            elif k.lower() == "x-api-key":
                original_auth_header = "x-api-key"

        # 使用原始请求的认证头格式
        if original_auth_header == "authorization":
            proxy_headers["Authorization"] = f"Bearer {backend_config.api_key}"
        else:
            # 默认使用 x-api-key
            proxy_headers["x-api-key"] = backend_config.api_key

        if "anthropic-version" not in proxy_headers:
            proxy_headers["anthropic-version"] = "2023-06-01"
        
        # 构建完整URL - 使用后端配置的base_url
        url = f"{backend_config.base_url}/v1/{endpoint.lstrip('/')}"
        
        # 调试请求信息
        print(f"Using backend: {backend_config.name} ({backend_config.base_url})")
        print(f"Request URL: {url}")
        print(f"Request method: {request.method}")
        print(f"Request headers: {proxy_headers}")
        print(f"Request body length: {len(request_body) if request_body else 0}")
        if request_body:
            print(f"Request body preview: {request_body[:500]}")
        
        # 发起请求
        start_time = time.time()
        
        # 使用流式请求来获得真实的token时间
        async with claude_client.client.stream(
            method=request.method,
            url=url,
            headers=proxy_headers,
            content=request_body,
            params=dict(request.query_params)
        ) as response:
            end_time = time.time()
            processing_time = end_time - start_time
            
            # 调试响应信息
            print(f"Response Status: {response.status_code}")
            print(f"Response Headers: {dict(response.headers)}")
            
            # 检查内容类型
            content_type = response.headers.get("content-type", "")
            
            # 收集响应内容和计时信息
            response_chunks = []
            first_token_time = None
            last_token_time = None
            response_text_preview = None
            response_content = b''
            
            if "text/event-stream" in content_type:
                print("Processing streaming response...")
                async for chunk in response.aiter_text():
                    if chunk:
                        response_chunks.append(chunk)
                        
                        # 检查是否是第一个实际内容token
                        if first_token_time is None and 'content_block_delta' in chunk:
                            first_token_time = time.time()
                            print(f"First content token received at: {first_token_time}")
                        
                        # 持续更新最后token时间
                        if 'content_block_delta' in chunk or 'message_delta' in chunk:
                            last_token_time = time.time()
            else:
                # 非流式响应
                print("Processing non-streaming response...")
                raw_chunks = []
                async for chunk in response.aiter_bytes():
                    raw_chunks.append(chunk)

                response_content = b''.join(raw_chunks)

                if response_content:
                    try:
                        response_text_preview = response_content.decode('utf-8')
                    except UnicodeDecodeError as e:
                        print(f"UTF-8 decode error: {e}, attempting with error handling...")
                        response_text_preview = response_content.decode('utf-8', errors='replace')

            # 组合完整响应内容
            if "text/event-stream" in content_type:
                response_text_preview = ''.join(response_chunks)
                response_content = response_text_preview.encode('utf-8')
            
            print(f"Response Content length: {len(response_content)}")
            if len(response_content) > 0:
                if response_text_preview is not None:
                    print(f"Response Content preview: {response_text_preview[:500]}")
                else:
                    print(f"Response Content preview (bytes): {response_content[:500]}")
            else:
                print("Response Content: EMPTY!")
            
            # 检查是否是空响应但状态码200的情况
            if response.status_code == 200 and len(response_content) == 0:
                print("WARNING: Got empty response with 200 status code!")
                return Response(
                    content='{"error": {"message": "Empty response from upstream API", "type": "proxy_error"}}',
                    status_code=502,
                    headers={"content-type": "application/json"}
                )
        
        # 后台统计（异步，不影响响应）
        async def record_stats():
            try:
                # Token使用量详细统计
                input_tokens = 0
                output_tokens = 0
                cache_creation_tokens = 0
                cache_read_tokens = 0
                model = "unknown"
                total_tokens = 0
                output_tps = 0.0
                precise_cost = 0.0

                # 生成时间统计
                generation_time = processing_time
                
                # 尝试解析响应中的token使用量
                try:
                    if response_content and len(response_content) > 0:
                        content_type = response.headers.get("content-type", "")
                        
                        if "text/event-stream" in content_type:
                            # 解析SSE格式响应
                            response_text = response_content.decode('utf-8', errors='replace')
                            print(f"Parsing SSE response for tokens...")
                            
                            # 解析每个SSE事件，提取token统计信息
                            for line in response_text.split('\n'):
                                if line.startswith('data: ') and not line.strip().endswith('[DONE]'):
                                    try:
                                        data_json = line[6:]  # 移除 'data: ' 前缀
                                        if data_json.strip():
                                            data = json.loads(data_json)
                                            event_type = data.get("type")
                                            
                                            # 检查message_start事件中的usage和model
                                            if event_type == "message_start":
                                                message = data.get("message", {})
                                                model = message.get("model", "unknown")
                                                usage = message.get("usage", {})
                                                if usage:
                                                    input_tokens = usage.get("input_tokens", 0)
                                                    output_tokens = usage.get("output_tokens", 0)
                                                    cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
                                                    cache_read_tokens = usage.get("cache_read_input_tokens", 0)
                                                    print(f"Found usage in message_start: model={model}, input={input_tokens}, output={output_tokens}, cache_creation={cache_creation_tokens}, cache_read={cache_read_tokens}")
                                            
                                            # 检查message_delta事件中的usage更新
                                            elif event_type == "message_delta":
                                                delta = data.get("delta", {})
                                                usage = delta.get("usage", {})
                                                if usage:
                                                    if "output_tokens" in usage:
                                                        output_tokens = usage["output_tokens"]
                                                        print(f"Updated output tokens from message_delta: {output_tokens}")
                                    except json.JSONDecodeError:
                                        continue
                            
                            # 使用真实的token生成时间
                            if first_token_time and last_token_time and output_tokens > 0:
                                generation_time = last_token_time - first_token_time
                                print(f"Real token generation time: {generation_time:.3f}s (from first to last token)")
                            else:
                                # 如果没有token生成时间，使用总处理时间
                                generation_time = processing_time
                                print(f"Using total processing time (no token timing): {generation_time:.3f}s")
                                                        
                        elif "json" in content_type:
                            try:
                                response_text = response_content.decode('utf-8')
                            except UnicodeDecodeError as decode_error:
                                print(f"Token stats decode error: {decode_error}")
                            else:
                                if response_text.strip():
                                    response_data = json.loads(response_text)
                                    if isinstance(response_data, dict):
                                        model = response_data.get("model", "unknown")
                                        usage = response_data.get("usage", {})
                                        if usage:
                                            input_tokens = usage.get("input_tokens", 0)
                                            output_tokens = usage.get("output_tokens", 0)
                                            cache_creation_tokens = usage.get("cache_creation_input_tokens", 0)
                                            cache_read_tokens = usage.get("cache_read_input_tokens", 0)
                                else:
                                    print("Token stats: JSON response is empty after decoding.")
                        else:
                            print(f"Skipping token stats parsing for content-type: {content_type}")

                        # 如果无法从响应中提取模型，使用claude_client提取
                        if model == "unknown":
                            model = claude_client._extract_model_from_response(response_content)
                            print(f"Extracted model from response: {model}")

                        # 计算总token数和精确成本
                        total_tokens = input_tokens + output_tokens + cache_creation_tokens + cache_read_tokens

                        # 计算输出TPS (基于生成时间)
                        if output_tokens > 0 and generation_time > 0:
                            output_tps = output_tokens / generation_time
                        
                        # 使用精确的模型定价计算成本
                        from app.pricing import calculate_token_cost
                        precise_cost = calculate_token_cost(
                            model=model,
                            input_tokens=input_tokens,
                            output_tokens=output_tokens,
                            cache_creation_tokens=cache_creation_tokens,
                            cache_read_tokens=cache_read_tokens
                        )
                        
                        if total_tokens > 0:
                            print(f"Model: {model}")
                            print(f"Token breakdown: input={input_tokens}, output={output_tokens}, cache_creation={cache_creation_tokens}, cache_read={cache_read_tokens}, total={total_tokens}")
                            print(f"Total processing time: {processing_time:.3f}s")
                            print(f"Response generation time: {generation_time:.3f}s")
                            if output_tokens > 0:
                                print(f"Output TPS: {output_tps:.2f} tokens/sec")
                            print(f"Precise cost: ${precise_cost:.8f}")

                except Exception as parse_error:
                    print(f"Token parsing error: {parse_error}")
                    # 如果解析失败，使用默认值和总处理时间
                    input_tokens = 0
                    output_tokens = 0
                    cache_creation_tokens = 0
                    cache_read_tokens = 0
                    model = "unknown"
                    total_tokens = 0
                    output_tps = 0.0
                    precise_cost = 0.0
                    generation_time = processing_time
                
                # 记录详细的使用统计（使用精确的generation_time计算的TPS）
                crud.record_usage_detailed(
                    db=db,
                    api_key_id=db_key.id,
                    endpoint=endpoint,
                    method=request.method,
                    model=model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cache_creation_tokens=cache_creation_tokens,
                    cache_read_tokens=cache_read_tokens,
                    tokens_used=total_tokens,
                    cost=precise_cost,
                    request_size=len(request_body) if request_body else 0,
                    response_size=len(response_content) if response_content else 0,
                    processing_time=processing_time,  # 保留总处理时间用于其他统计
                    output_tps=output_tps,  # 使用精确计算的TPS
                    status_code=response.status_code
                )
                crud.update_last_used(db, db_key.id)
            except Exception as e:
                print(f"Stats error: {e}")
        
        import asyncio
        asyncio.create_task(record_stats())
        
        # 构建响应头，排除可能有问题的头
        response_headers = {}
        for k, v in response.headers.items():
            if k.lower() not in ["content-length", "transfer-encoding"]:
                response_headers[k] = v
        
        # 直接返回响应
        return Response(
            content=response_content,
            status_code=response.status_code,
            headers=response_headers
        )
        
    except Exception as e:
        print(f"Proxy error: {e}")
        raise HTTPException(status_code=500, detail="Proxy error")
