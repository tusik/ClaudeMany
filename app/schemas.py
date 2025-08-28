from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

class APIKeyCreate(BaseModel):
    name: str
    rate_limit: Optional[int] = None
    quota_limit: Optional[int] = None
    cost_limit: Optional[float] = None
    daily_quota: Optional[float] = None

class APIKeyUpdate(BaseModel):
    name: Optional[str] = None
    rate_limit: Optional[int] = None
    quota_limit: Optional[int] = None
    cost_limit: Optional[float] = None
    daily_quota: Optional[float] = None

class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: str
    is_active: bool
    rate_limit: int
    quota_limit: int
    cost_limit: float
    daily_quota: float
    created_at: datetime
    last_used: Optional[datetime]

class APIKeyInfo(BaseModel):
    id: str
    name: str
    is_active: bool
    rate_limit: int
    quota_limit: int
    cost_limit: float
    daily_quota: float
    created_at: datetime
    last_used: Optional[datetime]

class UsageStats(BaseModel):
    total_requests: int
    total_tokens: int
    total_cost: float
    avg_processing_time: float
    avg_output_tps: Optional[float] = 0.0
    requests_today: int
    tokens_today: int

class UsageRecord(BaseModel):
    id: str
    endpoint: str
    method: str
    tokens_used: int
    cost: float
    processing_time: float
    output_tps: Optional[float] = 0.0
    timestamp: datetime
    status_code: int
    error_message: Optional[str]

class AdminLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str