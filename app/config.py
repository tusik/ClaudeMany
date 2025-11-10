from pydantic_settings import BaseSettings
from typing import Optional, Dict, List

class Settings(BaseSettings):
    anthropic_api_key: str
    anthropic_base_url: str = "https://api.anthropic.com"
    
    database_url: str = "sqlite:///./claude_proxy.db"
    db_pool_size: int = 20
    db_max_overflow: int = 40
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800
    secret_key: str
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days
    
    admin_username: str = "admin"
    admin_password: str
    
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    
    default_rate_limit: int = 1000
    default_quota_limit: int = 100000
    
    # 模型替换功能配置
    enable_model_swapping: bool = False  # 模型替换功能开关
    model_mapping: Dict[str, str] = {}  # 模型映射表，格式: {"原始模型": "目标模型"}
    
    class Config:
        env_file = ".env"

settings = Settings()
