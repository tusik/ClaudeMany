from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app import database, crud, schemas, auth
from app.config import settings
from typing import List
import json

router = APIRouter()

@router.post("/login", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    if not auth.authenticate_admin(form_data.username, form_data.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": form_data.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/api-keys", response_model=schemas.APIKeyResponse)
async def create_api_key(
    api_key: schemas.APIKeyCreate,
    current_user: str = Depends(auth.get_current_admin_user),
    db: Session = Depends(database.get_db)
):
    db_key, key = crud.create_api_key(db, api_key)
    return schemas.APIKeyResponse(
        id=db_key.id,
        name=db_key.name,
        key=key,
        is_active=db_key.is_active,
        rate_limit=db_key.rate_limit,
        quota_limit=db_key.quota_limit,
        cost_limit=db_key.cost_limit,
        daily_quota=db_key.daily_quota,
        created_at=db_key.created_at,
        last_used=db_key.last_used
    )

@router.get("/api-keys", response_model=List[schemas.APIKeyInfo])
async def get_api_keys(
    current_user: str = Depends(auth.get_current_admin_user),
    db: Session = Depends(database.get_db)
):
    db_keys = crud.get_api_keys(db)
    return [
        schemas.APIKeyInfo(
            id=key.id,
            name=key.name,
            is_active=key.is_active,
            rate_limit=key.rate_limit,
            quota_limit=key.quota_limit,
            created_at=key.created_at,
            last_used=key.last_used
        ) for key in db_keys
    ]

@router.delete("/api-keys/{key_id}")
async def deactivate_api_key(
    key_id: str,
    current_user: str = Depends(auth.get_current_admin_user),
    db: Session = Depends(database.get_db)
):
    if not crud.deactivate_api_key(db, key_id):
        raise HTTPException(status_code=404, detail="API key not found")
    return {"message": "API key deactivated successfully"}

@router.put("/api-keys/{key_id}")
async def update_api_key(
    key_id: str,
    api_key_update: schemas.APIKeyUpdate,
    request: Request,
    db: Session = Depends(database.get_db)
):
    """更新API密钥配置"""
    # 支持Bearer token和Cookie两种认证方式
    try:
        current_user = await auth.get_current_admin_user_cookie(request)
    except:
        # 如果Cookie认证失败，尝试Bearer token认证
        current_user = await auth.get_current_admin_user(Depends(auth.security))
    
    if not crud.update_api_key(
        db, 
        key_id, 
        name=api_key_update.name,
        rate_limit=api_key_update.rate_limit,
        quota_limit=api_key_update.quota_limit,
        cost_limit=api_key_update.cost_limit,
        daily_quota=api_key_update.daily_quota
    ):
        raise HTTPException(status_code=404, detail="API key not found")
    
    # 返回更新后的API密钥信息
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    return schemas.APIKeyInfo(
        id=db_key.id,
        name=db_key.name,
        is_active=db_key.is_active,
        rate_limit=db_key.rate_limit,
        quota_limit=db_key.quota_limit,
        cost_limit=db_key.cost_limit,
        daily_quota=db_key.daily_quota,
        created_at=db_key.created_at,
        last_used=db_key.last_used
    )

@router.get("/api-keys/{key_id}/stats", response_model=schemas.UsageStats)
async def get_api_key_stats(
    key_id: str,
    current_user: str = Depends(auth.get_current_admin_user),
    db: Session = Depends(database.get_db)
):
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return crud.get_usage_stats(db, key_id)

@router.get("/api-keys/{key_id}/rate-limit-status")
async def get_rate_limit_status(
    key_id: str,
    current_user: str = Depends(auth.get_current_admin_user),
    db: Session = Depends(database.get_db)
):
    """获取API密钥的速率限制状态"""
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # 获取最近一小时的请求数量
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_requests = db.query(func.count(database.UsageRecord.id)).filter(
        and_(
            database.UsageRecord.api_key_id == key_id,
            database.UsageRecord.timestamp >= one_hour_ago
        )
    ).scalar()
    
    return {
        "rate_limit": db_key.rate_limit,
        "current_usage": recent_requests or 0,
        "remaining": max(0, db_key.rate_limit - (recent_requests or 0)),
        "reset_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "is_limited": db_key.rate_limit > 0
    }

@router.get("/api-keys/{key_id}/cost-limit-status")
async def get_cost_limit_status(
    key_id: str,
    current_user: str = Depends(auth.get_current_admin_user),
    db: Session = Depends(database.get_db)
):
    """获取API密钥的成本限制状态"""
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # 获取最近一小时的成本
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    recent_cost = db.query(func.sum(database.UsageRecord.cost)).filter(
        and_(
            database.UsageRecord.api_key_id == key_id,
            database.UsageRecord.timestamp >= one_hour_ago
        )
    ).scalar() or 0.0
    
    return {
        "cost_limit": db_key.cost_limit,
        "current_cost": round(recent_cost, 6),
        "remaining_cost": max(0, round(db_key.cost_limit - recent_cost, 6)),
        "reset_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "is_limited": db_key.cost_limit > 0
    }

@router.get("/api-keys/{key_id}/daily-quota-status")
async def get_daily_quota_status(
    key_id: str,
    current_user: str = Depends(auth.get_current_admin_user),
    db: Session = Depends(database.get_db)
):
    """获取API密钥的每日额度状态"""
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    # 获取今日的成本
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_cost = db.query(func.sum(database.UsageRecord.cost)).filter(
        and_(
            database.UsageRecord.api_key_id == key_id,
            database.UsageRecord.timestamp >= today_start
        )
    ).scalar() or 0.0
    
    return {
        "daily_quota": db_key.daily_quota,
        "current_usage": round(today_cost, 6),
        "remaining_quota": max(0, round(db_key.daily_quota - today_cost, 6)),
        "reset_time": (today_start + timedelta(days=1)).isoformat(),
        "is_limited": db_key.daily_quota > 0
    }

@router.get("/model-swap-config", response_model=schemas.ModelSwapConfig)
async def get_model_swap_config(
    current_user: str = Depends(auth.get_current_admin_user)
):
    """获取模型替换配置"""
    return schemas.ModelSwapConfig(
        enable_model_swapping=settings.enable_model_swapping,
        model_mapping=settings.model_mapping
    )

@router.put("/model-swap-config", response_model=schemas.ModelSwapConfig)
async def update_model_swap_config(
    config: schemas.ModelSwapConfig,
    current_user: str = Depends(auth.get_current_admin_user)
):
    """更新模型替换配置"""
    settings.enable_model_swapping = config.enable_model_swapping
    settings.model_mapping = config.model_mapping
    
    # 保存配置到环境变量或配置文件
    # 注意：这里只是内存中的修改，重启后会丢失
    # 如果需要持久化，需要写入配置文件
    
    return schemas.ModelSwapConfig(
        enable_model_swapping=settings.enable_model_swapping,
        model_mapping=settings.model_mapping
    )