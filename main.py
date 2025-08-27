from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import database
from app.routers import proxy, admin, usage, web
from app.config import settings

app = FastAPI(
    title="Claude Code Proxy Server",
    description="代理Anthropic LLM协议，提供API密钥管理和用量统计",
    version="1.0.0"
)

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