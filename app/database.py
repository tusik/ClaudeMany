from sqlalchemy import create_engine, Column, String, Integer, DateTime, Float, Boolean, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func
from app.config import settings
import uuid
from datetime import datetime

engine = create_engine(settings.database_url, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class BackendConfig(Base):
    __tablename__ = "backend_configs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)  # 配置名称
    base_url = Column(String, nullable=False)  # API base URL
    api_key = Column(String, nullable=False)  # API密钥
    is_active = Column(Boolean, default=False)  # 是否为当前激活的配置
    is_default = Column(Boolean, default=False)  # 是否为默认配置
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    key_hash = Column(String, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=1000)
    quota_limit = Column(Integer, default=100000)
    created_at = Column(DateTime, default=func.now())
    last_used = Column(DateTime)

class UsageRecord(Base):
    __tablename__ = "usage_records"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(String, nullable=False)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    
    # 模型信息
    model = Column(String, default="unknown")
    
    # Token使用量详细统计
    input_tokens = Column(Integer, default=0)
    output_tokens = Column(Integer, default=0)
    cache_creation_tokens = Column(Integer, default=0)
    cache_read_tokens = Column(Integer, default=0)
    tokens_used = Column(Integer, default=0)  # 总token数 (向后兼容)
    
    # 成本计算
    cost = Column(Float, default=0.0)
    
    # 请求响应信息
    request_size = Column(Integer, default=0)
    response_size = Column(Integer, default=0)
    processing_time = Column(Float, default=0.0)
    
    # TPS (Tokens Per Second) 统计
    output_tps = Column(Float, default=0.0)  # 输出token生成速度
    
    timestamp = Column(DateTime, default=func.now())
    status_code = Column(Integer)
    error_message = Column(Text)

class DailyUsage(Base):
    __tablename__ = "daily_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(String, nullable=False)
    date = Column(String, nullable=False)  # YYYY-MM-DD格式
    model = Column(String, nullable=False)
    
    # 每日汇总统计
    total_requests = Column(Integer, default=0)
    total_input_tokens = Column(Integer, default=0)
    total_output_tokens = Column(Integer, default=0)
    total_cache_creation_tokens = Column(Integer, default=0)
    total_cache_read_tokens = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)
    
    # 性能统计
    avg_processing_time = Column(Float, default=0.0)
    avg_output_tps = Column(Float, default=0.0)  # 平均输出TPS

def create_tables():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()