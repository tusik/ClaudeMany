from fastapi import Request
from fastapi.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class ProxyHeadersMiddleware(BaseHTTPMiddleware):
    """
    处理反向代理头信息的中间件
    支持nginx等反向代理服务器转发的头信息
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 获取原始头信息
        forwarded_proto = request.headers.get("x-forwarded-proto")
        forwarded_host = request.headers.get("x-forwarded-host") 
        forwarded_port = request.headers.get("x-forwarded-port")
        forwarded_for = request.headers.get("x-forwarded-for")
        
        # 如果有代理头信息，更新request.url
        if forwarded_proto or forwarded_host:
            # 构建新的URL
            scheme = forwarded_proto or request.url.scheme
            host = forwarded_host or request.url.hostname
            port = None
            
            # 处理端口
            if forwarded_port:
                port = int(forwarded_port)
            elif scheme == "https" and request.url.port != 443:
                port = request.url.port
            elif scheme == "http" and request.url.port != 80:
                port = request.url.port
                
            # 重构URL
            if port and port not in (80, 443):
                netloc = f"{host}:{port}"
            else:
                netloc = host
                
            # 更新request的URL属性
            new_url = request.url.replace(
                scheme=scheme,
                hostname=host,
                port=port
            )
            
            # 这里我们不能直接修改request.url，但可以在请求中添加标识
            # 让应用知道真实的访问地址
            request.state.original_url = str(new_url)
            request.state.forwarded_proto = scheme
            request.state.forwarded_host = host
            
            logger.debug(f"Proxy headers detected - Original: {request.url}, Forwarded: {new_url}")
        
        # 设置真实IP
        if forwarded_for:
            # X-Forwarded-For 可能包含多个IP，取第一个
            real_ip = forwarded_for.split(",")[0].strip()
            request.state.real_ip = real_ip
        
        response = await call_next(request)
        return response