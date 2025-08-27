import httpx
from fastapi import HTTPException
from typing import Dict, Any, AsyncGenerator
import time
import json
from app.config import settings

class ClaudeProxyClient:
    def __init__(self):
        self.base_url = settings.anthropic_base_url
        self.api_key = settings.anthropic_api_key
        self.client = httpx.AsyncClient(timeout=300.0)
    
    async def proxy_request_stream(self, method: str, endpoint: str, headers: Dict[str, str] = None, 
                                  body: bytes = None, params: Dict[str, str] = None) -> AsyncGenerator[bytes, None]:
        # 构建代理请求头
        proxy_headers = dict(headers) if headers else {}
        
        # 移除客户端认证头，添加服务器认证头
        proxy_headers.pop("authorization", None) 
        proxy_headers["x-api-key"] = self.api_key
        
        # 如果没有anthropic-version，添加默认版本
        if "anthropic-version" not in proxy_headers:
            proxy_headers["anthropic-version"] = "2023-06-01"
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            async with self.client.stream(
                method=method,
                url=url,
                headers=proxy_headers,
                content=body,
                params=params
            ) as response:
                # 直接流式传输响应内容，不做任何处理
                async for chunk in response.aiter_bytes():
                    if chunk:
                        yield chunk
                        
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Request to Claude API timed out")
        except httpx.RequestError as e:
            raise HTTPException(status_code=502, detail=f"Error connecting to Claude API: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

    async def proxy_request_completely_raw(self, method: str, endpoint: str, headers: Dict[str, str] = None, 
                                          body: bytes = None, params: Dict[str, str] = None) -> tuple[bytes, int, float, Dict[str, str]]:
        start_time = time.time()
        
        # 构建代理请求头 - 只替换认证相关的头
        proxy_headers = dict(headers) if headers else {}
        
        # 移除客户端认证头，添加服务器认证头
        proxy_headers.pop("authorization", None) 
        proxy_headers["x-api-key"] = self.api_key
        
        # 如果没有anthropic-version，添加默认版本
        if "anthropic-version" not in proxy_headers:
            proxy_headers["anthropic-version"] = "2023-06-01"
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            # 完全透明转发，不解析任何内容
            response = await self.client.request(
                method=method,
                url=url,
                headers=proxy_headers,
                content=body,
                params=params
            )
            
            processing_time = time.time() - start_time
            
            # 返回原始字节内容和响应头
            response_headers = dict(response.headers)
            
            return response.content, response.status_code, processing_time, response_headers
            
        except httpx.TimeoutException:
            processing_time = time.time() - start_time
            raise HTTPException(status_code=504, detail="Request to Claude API timed out")
        except httpx.RequestError as e:
            processing_time = time.time() - start_time
            raise HTTPException(status_code=502, detail=f"Error connecting to Claude API: {str(e)}")
        except Exception as e:
            processing_time = time.time() - start_time
            raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

    async def proxy_request_raw(self, method: str, endpoint: str, headers: Dict[str, str] = None, 
                               body: bytes = None, params: Dict[str, str] = None) -> tuple[Any, int, float]:
        start_time = time.time()
        
        # 构建代理请求头 - 只替换认证相关的头
        proxy_headers = dict(headers) if headers else {}
        
        # 替换认证头
        proxy_headers["x-api-key"] = self.api_key
        
        # 移除客户端的认证头，但是先保存x-api-key的值
        original_auth = proxy_headers.pop("authorization", None) 
        original_x_api_key = proxy_headers.pop("x-api-key", None)
        proxy_headers["x-api-key"] = self.api_key
        
        # 如果没有anthropic-version，添加默认版本
        if "anthropic-version" not in proxy_headers:
            proxy_headers["anthropic-version"] = "2023-06-01"
        
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        try:
            # 使用httpx直接转发，保持完全透明
            response = await self.client.request(
                method=method,
                url=url,
                headers=proxy_headers,
                content=body,
                params=params
            )
            
            processing_time = time.time() - start_time
            
            # 完全不处理响应内容，直接返回
            try:
                # 尝试解析JSON，但不强制
                response_data = response.json()
            except:
                # 如果不是JSON，返回文本
                response_data = response.text
            
            return response_data, response.status_code, processing_time
            
        except httpx.TimeoutException:
            processing_time = time.time() - start_time
            raise HTTPException(status_code=504, detail="Request to Claude API timed out")
        except httpx.RequestError as e:
            processing_time = time.time() - start_time
            raise HTTPException(status_code=502, detail=f"Error connecting to Claude API: {str(e)}")
        except Exception as e:
            processing_time = time.time() - start_time
            raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

    # 保持原方法以防其他地方调用
    async def proxy_request(self, method: str, endpoint: str, headers: Dict[str, str] = None, 
                           body: bytes = None, params: Dict[str, str] = None) -> tuple[Any, int, float]:
        return await self.proxy_request_raw(method, endpoint, headers, body, params)

claude_client = ClaudeProxyClient()