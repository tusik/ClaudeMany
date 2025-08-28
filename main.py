from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database
from app.routers import proxy, admin, usage, web
from app.config import settings
from app.middleware import ProxyHeadersMiddleware

app = FastAPI(
    title="ClaudeMany",
    description="A high-performance proxy server for Anthropic Claude API",
    version="2.0.0"
)

# 信任所有主机（生产环境应该配置具体域名）
app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

# 添加代理头处理中间件
app.add_middleware(ProxyHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    database.create_tables()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"}
    )

@app.get("/")
async def root():
    return {
        "message": "Claude Code Proxy Server",
        "version": "1.0.0",
        "endpoints": {
            "proxy": "/v1/*",
            "admin": "/admin/*",
            "usage": "/usage/*"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

app.include_router(proxy.router, tags=["proxy"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(usage.router, prefix="/usage", tags=["usage"])
app.include_router(web.router, prefix="/web", tags=["web"])

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.server_host,
        port=settings.server_port,
        reload=True
    )