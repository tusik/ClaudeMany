from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from app import database, schemas
from passlib.context import CryptContext
from datetime import datetime, timedelta
import secrets
import hashlib

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_api_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()

def generate_api_key() -> str:
    # 生成不含特殊字符的随机字符串
    token = secrets.token_urlsafe(32).replace('-', '').replace('_', '')
    # 如果长度不够32位，继续生成直到够长
    while len(token) < 32:
        token += secrets.token_urlsafe(16).replace('-', '').replace('_', '')
    return f"ck-{token[:32]}"

# 后端配置管理
def create_backend_config(db: Session, name: str, base_url: str, api_key: str, is_default: bool = False) -> database.BackendConfig:
    """创建后端配置"""
    # 如果设置为默认，先取消其他默认配置
    if is_default:
        db.query(database.BackendConfig).update({"is_default": False})
        db.commit()
    
    config = database.BackendConfig(
        name=name,
        base_url=base_url.rstrip('/'),  # 移除尾部斜杠
        api_key=api_key,
        is_default=is_default
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config

def get_backend_configs(db: Session) -> list[database.BackendConfig]:
    """获取所有后端配置"""
    return db.query(database.BackendConfig).order_by(database.BackendConfig.created_at.desc()).all()

def get_active_backend_config(db: Session) -> database.BackendConfig:
    """获取当前激活的后端配置"""
    config = db.query(database.BackendConfig).filter(database.BackendConfig.is_active == True).first()
    if not config:
        # 如果没有激活配置，返回默认配置
        config = db.query(database.BackendConfig).filter(database.BackendConfig.is_default == True).first()
    return config

def get_default_backend_config(db: Session) -> database.BackendConfig:
    """获取默认后端配置"""
    return db.query(database.BackendConfig).filter(database.BackendConfig.is_default == True).first()

def activate_backend_config(db: Session, config_id: str) -> bool:
    """激活指定的后端配置"""
    # 先取消所有激活状态
    db.query(database.BackendConfig).update({"is_active": False})
    
    # 激活指定配置
    config = db.query(database.BackendConfig).filter(database.BackendConfig.id == config_id).first()
    if config:
        config.is_active = True
        db.commit()
        return True
    return False

def delete_backend_config(db: Session, config_id: str) -> bool:
    """删除后端配置"""
    config = db.query(database.BackendConfig).filter(database.BackendConfig.id == config_id).first()
    if config and not config.is_default:  # 不允许删除默认配置
        db.delete(config)
        db.commit()
        return True
    return False

def update_backend_config(db: Session, config_id: str, name: str = None, base_url: str = None, api_key: str = None, is_default: bool = None) -> bool:
    """更新后端配置"""
    config = db.query(database.BackendConfig).filter(database.BackendConfig.id == config_id).first()
    if not config:
        return False
    
    if name is not None:
        config.name = name
    if base_url is not None:
        config.base_url = base_url.rstrip('/')
    if api_key is not None:
        config.api_key = api_key
    if is_default is not None:
        if is_default:
            # 如果设置为默认，先取消其他默认配置
            db.query(database.BackendConfig).update({"is_default": False})
        config.is_default = is_default
    
    db.commit()
    return True

def create_api_key(db: Session, api_key: schemas.APIKeyCreate) -> tuple[database.APIKey, str]:
    key = generate_api_key()
    key_hash = hash_api_key(key)
    
    db_key = database.APIKey(
        name=api_key.name,
        key_hash=key_hash,
        key_value=key,  # 保存明文API key
        rate_limit=api_key.rate_limit or 1000,
        quota_limit=api_key.quota_limit or 100000,
        cost_limit=api_key.cost_limit or 10.0,
        daily_quota=api_key.daily_quota or 50.0
    )
    db.add(db_key)
    db.commit()
    db.refresh(db_key)
    return db_key, key

def get_api_key_by_hash(db: Session, key_hash: str) -> database.APIKey:
    return db.query(database.APIKey).filter(
        and_(database.APIKey.key_hash == key_hash, database.APIKey.is_active == True)
    ).first()

def get_api_keys(db: Session) -> list[database.APIKey]:
    return db.query(database.APIKey).all()

def deactivate_api_key(db: Session, key_id: str) -> bool:
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    if db_key:
        db_key.is_active = False
        db.commit()
        return True
    return False

def delete_api_key(db: Session, key_id: str) -> bool:
    """删除API密钥及其相关使用记录"""
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    if db_key:
        # 先删除相关的使用记录
        db.query(database.UsageRecord).filter(database.UsageRecord.api_key_id == key_id).delete()
        db.query(database.DailyUsage).filter(database.DailyUsage.api_key_id == key_id).delete()
        
        # 删除API密钥
        db.delete(db_key)
        db.commit()
        return True
    return False

def regenerate_api_key(db: Session, key_id: str) -> tuple[database.APIKey, str]:
    """重新生成API密钥"""
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    if not db_key:
        return None, None
    
    # 生成新的API密钥
    new_key = generate_api_key()
    new_key_hash = hash_api_key(new_key)
    
    # 更新数据库中的密钥信息
    db_key.key_hash = new_key_hash
    db_key.key_value = new_key
    db_key.created_at = datetime.utcnow()  # 更新创建时间
    db_key.last_used = None  # 重置最后使用时间
    
    db.commit()
    db.refresh(db_key)
    
    return db_key, new_key

def update_api_key(db: Session, key_id: str, name: str = None, rate_limit: int = None, quota_limit: int = None, cost_limit: float = None, daily_quota: float = None) -> bool:
    """更新API密钥的配置"""
    db_key = db.query(database.APIKey).filter(database.APIKey.id == key_id).first()
    if not db_key:
        return False
    
    if name is not None:
        db_key.name = name
    if rate_limit is not None:
        db_key.rate_limit = rate_limit
    if quota_limit is not None:
        db_key.quota_limit = quota_limit
    if cost_limit is not None:
        db_key.cost_limit = cost_limit
    if daily_quota is not None:
        db_key.daily_quota = daily_quota
    
    db.commit()
    return True

def update_last_used(db: Session, key_id: str):
    db.query(database.APIKey).filter(database.APIKey.id == key_id).update(
        {"last_used": datetime.utcnow()}
    )
    db.commit()

def check_rate_limit(db: Session, api_key_id: str, rate_limit: int) -> tuple[bool, dict]:
    """检查API密钥是否超过速率限制 (请求/小时)
    
    Returns:
        tuple[bool, dict]: (是否允许请求, 限制信息)
    """
    if rate_limit <= 0:
        return True, {"unlimited": True}  # 无限制
    
    # 计算一小时前的时间
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # 查询最近一小时的请求次数
    recent_requests = db.query(func.count(database.UsageRecord.id)).filter(
        and_(
            database.UsageRecord.api_key_id == api_key_id,
            database.UsageRecord.timestamp >= one_hour_ago
        )
    ).scalar() or 0
    
    allowed = recent_requests < rate_limit
    limit_info = {
        "rate_limit": rate_limit,
        "current_usage": recent_requests,
        "remaining": max(0, rate_limit - recent_requests),
        "reset_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "unlimited": False
    }
    
    return allowed, limit_info

def check_cost_limit(db: Session, api_key_id: str, cost_limit: float) -> tuple[bool, dict]:
    """检查API密钥是否超过每小时成本限制
    
    Returns:
        tuple[bool, dict]: (是否允许请求, 成本限制信息)
    """
    if cost_limit <= 0:
        return True, {"unlimited": True}  # 无限制
    
    # 计算一小时前的时间
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    
    # 查询最近一小时的成本总和
    recent_cost = db.query(func.sum(database.UsageRecord.cost)).filter(
        and_(
            database.UsageRecord.api_key_id == api_key_id,
            database.UsageRecord.timestamp >= one_hour_ago
        )
    ).scalar() or 0.0
    
    allowed = recent_cost < cost_limit
    limit_info = {
        "cost_limit": cost_limit,
        "current_cost": round(recent_cost, 6),
        "remaining_cost": max(0, round(cost_limit - recent_cost, 6)),
        "reset_time": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
        "unlimited": False
    }
    
    return allowed, limit_info

def check_daily_quota(db: Session, api_key_id: str, daily_quota: float) -> tuple[bool, dict]:
    """检查API密钥是否超过每日成本额度限制
    
    Returns:
        tuple[bool, dict]: (是否允许请求, 额度限制信息)
    """
    if daily_quota <= 0:
        return True, {"unlimited": True}  # 无限制
    
    # 计算今日00:00:00的时间
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 查询今日的成本总和
    today_cost = db.query(func.sum(database.UsageRecord.cost)).filter(
        and_(
            database.UsageRecord.api_key_id == api_key_id,
            database.UsageRecord.timestamp >= today_start
        )
    ).scalar() or 0.0
    
    allowed = today_cost < daily_quota
    limit_info = {
        "daily_quota": daily_quota,
        "current_usage": round(today_cost, 6),
        "remaining_quota": max(0, round(daily_quota - today_cost, 6)),
        "reset_time": (today_start + timedelta(days=1)).isoformat(),
        "unlimited": False
    }
    
    return allowed, limit_info

def record_usage_detailed(db: Session, api_key_id: str, endpoint: str, method: str,
                          model: str = "unknown", input_tokens: int = 0, output_tokens: int = 0,
                          cache_creation_tokens: int = 0, cache_read_tokens: int = 0,
                          tokens_used: int = 0, cost: float = 0.0,
                          request_size: int = 0, response_size: int = 0,
                          processing_time: float = 0.0, output_tps: float = 0.0,
                          status_code: int = 200, error_message: str = None):
    """记录详细的使用统计，包含模型和缓存信息"""
    usage = database.UsageRecord(
        api_key_id=api_key_id,
        endpoint=endpoint,
        method=method,
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cache_creation_tokens=cache_creation_tokens,
        cache_read_tokens=cache_read_tokens,
        tokens_used=tokens_used,
        cost=cost,
        request_size=request_size,
        response_size=response_size,
        processing_time=processing_time,
        output_tps=output_tps,
        status_code=status_code,
        error_message=error_message
    )
    db.add(usage)
    db.commit()

def record_usage(db: Session, api_key_id: str, endpoint: str, method: str, 
                tokens_used: int = 0, cost: float = 0.0, request_size: int = 0,
                response_size: int = 0, processing_time: float = 0.0,
                status_code: int = 200, error_message: str = None):
    """向后兼容的使用记录函数"""
    record_usage_detailed(
        db=db,
        api_key_id=api_key_id,
        endpoint=endpoint,
        method=method,
        model="unknown",
        input_tokens=0,
        output_tokens=0,
        cache_creation_tokens=0,
        cache_read_tokens=0,
        tokens_used=tokens_used,
        cost=cost,
        request_size=request_size,
        response_size=response_size,
        processing_time=processing_time,
        status_code=status_code,
        error_message=error_message
    )

def get_usage_stats(db: Session, api_key_id: str) -> schemas.UsageStats:
    today = datetime.utcnow().date()
    
    all_usage = db.query(
        func.count(database.UsageRecord.id).label("total_requests"),
        func.sum(database.UsageRecord.tokens_used).label("total_tokens"),
        func.sum(database.UsageRecord.cost).label("total_cost"),
        func.avg(database.UsageRecord.processing_time).label("avg_processing_time"),
        func.avg(database.UsageRecord.output_tps).label("avg_output_tps")
    ).filter(database.UsageRecord.api_key_id == api_key_id).first()
    
    today_usage = db.query(
        func.count(database.UsageRecord.id).label("requests_today"),
        func.sum(database.UsageRecord.tokens_used).label("tokens_today")
    ).filter(
        and_(
            database.UsageRecord.api_key_id == api_key_id,
            func.date(database.UsageRecord.timestamp) == today
        )
    ).first()
    
    return schemas.UsageStats(
        total_requests=all_usage.total_requests or 0,
        total_tokens=all_usage.total_tokens or 0,
        total_cost=all_usage.total_cost or 0.0,
        avg_processing_time=all_usage.avg_processing_time or 0.0,
        avg_output_tps=all_usage.avg_output_tps or 0.0,
        requests_today=today_usage.requests_today or 0,
        tokens_today=today_usage.tokens_today or 0
    )

def get_usage_records(db: Session, api_key_id: str, limit: int = 100) -> list[database.UsageRecord]:
    return db.query(database.UsageRecord).filter(
        database.UsageRecord.api_key_id == api_key_id
    ).order_by(database.UsageRecord.timestamp.desc()).limit(limit).all()

def aggregate_daily_usage(db: Session, date_str: str = None):
    """汇总指定日期的用量统计，如果不指定日期则汇总昨天的数据"""
    if not date_str:
        yesterday = (datetime.utcnow() - timedelta(days=1)).date()
        date_str = yesterday.strftime('%Y-%m-%d')
    
    print(f"Aggregating daily usage for {date_str}")
    
    # 查询指定日期的所有使用记录
    records = db.query(database.UsageRecord).filter(
        func.date(database.UsageRecord.timestamp) == date_str
    ).all()
    
    # 按API密钥和模型分组汇总
    usage_summary = {}
    for record in records:
        key = (record.api_key_id, record.model)
        if key not in usage_summary:
            usage_summary[key] = {
                'total_requests': 0,
                'total_input_tokens': 0,
                'total_output_tokens': 0,
                'total_cache_creation_tokens': 0,
                'total_cache_read_tokens': 0,
                'total_tokens': 0,
                'total_cost': 0.0,
                'processing_times': [],
                'output_tps_values': []
            }
        
        summary = usage_summary[key]
        summary['total_requests'] += 1
        summary['total_input_tokens'] += record.input_tokens
        summary['total_output_tokens'] += record.output_tokens
        summary['total_cache_creation_tokens'] += record.cache_creation_tokens
        summary['total_cache_read_tokens'] += record.cache_read_tokens
        summary['total_tokens'] += record.tokens_used
        summary['total_cost'] += record.cost
        if record.processing_time > 0:
            summary['processing_times'].append(record.processing_time)
        if record.output_tps > 0:
            summary['output_tps_values'].append(record.output_tps)
    
    # 保存汇总数据
    for (api_key_id, model), summary in usage_summary.items():
        avg_processing_time = sum(summary['processing_times']) / len(summary['processing_times']) if summary['processing_times'] else 0
        avg_output_tps = sum(summary['output_tps_values']) / len(summary['output_tps_values']) if summary['output_tps_values'] else 0
        
        # 检查是否已存在当天的汇总数据
        existing = db.query(database.DailyUsage).filter(
            and_(
                database.DailyUsage.api_key_id == api_key_id,
                database.DailyUsage.date == date_str,
                database.DailyUsage.model == model
            )
        ).first()
        
        if existing:
            # 更新现有记录
            existing.total_requests = summary['total_requests']
            existing.total_input_tokens = summary['total_input_tokens']
            existing.total_output_tokens = summary['total_output_tokens']
            existing.total_cache_creation_tokens = summary['total_cache_creation_tokens']
            existing.total_cache_read_tokens = summary['total_cache_read_tokens']
            existing.total_tokens = summary['total_tokens']
            existing.total_cost = summary['total_cost']
            existing.avg_processing_time = avg_processing_time
            existing.avg_output_tps = avg_output_tps
        else:
            # 创建新记录
            daily_usage = database.DailyUsage(
                api_key_id=api_key_id,
                date=date_str,
                model=model,
                total_requests=summary['total_requests'],
                total_input_tokens=summary['total_input_tokens'],
                total_output_tokens=summary['total_output_tokens'],
                total_cache_creation_tokens=summary['total_cache_creation_tokens'],
                total_cache_read_tokens=summary['total_cache_read_tokens'],
                total_tokens=summary['total_tokens'],
                total_cost=summary['total_cost'],
                avg_processing_time=avg_processing_time,
                avg_output_tps=avg_output_tps
            )
            db.add(daily_usage)
    
    db.commit()
    print(f"Aggregated {len(usage_summary)} daily usage records for {date_str}")

def get_daily_usage_chart_data(db: Session, api_key_id: str, days: int = 30) -> list[dict]:
    """获取指定API密钥的每日用量图表数据"""
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days-1)
    
    # 直接从usage_records表实时查询数据，按日期分组
    from sqlalchemy import func, and_
    daily_stats = db.query(
        func.date(database.UsageRecord.timestamp).label('date'),
        database.UsageRecord.model,
        func.count(database.UsageRecord.id).label('requests'),
        func.sum(database.UsageRecord.input_tokens).label('input_tokens'),
        func.sum(database.UsageRecord.output_tokens).label('output_tokens'),
        func.sum(database.UsageRecord.cache_creation_tokens).label('cache_creation_tokens'),
        func.sum(database.UsageRecord.cache_read_tokens).label('cache_read_tokens'),
        func.sum(database.UsageRecord.tokens_used).label('total_tokens'),
        func.sum(database.UsageRecord.cost).label('total_cost')
    ).filter(
        and_(
            database.UsageRecord.api_key_id == api_key_id,
            func.date(database.UsageRecord.timestamp) >= start_date.strftime('%Y-%m-%d'),
            func.date(database.UsageRecord.timestamp) <= end_date.strftime('%Y-%m-%d')
        )
    ).group_by(
        func.date(database.UsageRecord.timestamp),
        database.UsageRecord.model
    ).all()
    
    # 创建日期范围内的所有日期，并按日期汇总数据
    chart_data = []
    current_date = start_date
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        
        # 汇总当天所有模型的数据
        day_total = {
            'date': date_str,
            'total_requests': 0,
            'total_tokens': 0,
            'total_cost': 0.0,
            'models': {}
        }
        
        # 查找当天的记录
        for stat in daily_stats:
            if stat.date == date_str:
                requests = stat.requests or 0
                input_tokens = stat.input_tokens or 0
                output_tokens = stat.output_tokens or 0
                cache_creation_tokens = stat.cache_creation_tokens or 0
                cache_read_tokens = stat.cache_read_tokens or 0
                total_tokens = stat.total_tokens or 0
                total_cost = stat.total_cost or 0.0
                model = stat.model or 'unknown'
                
                day_total['total_requests'] += requests
                day_total['total_tokens'] += total_tokens
                day_total['total_cost'] += total_cost
                
                # 按模型分组的详细数据
                day_total['models'][model] = {
                    'requests': requests,
                    'tokens': total_tokens,
                    'cost': total_cost,
                    'input_tokens': input_tokens,
                    'output_tokens': output_tokens,
                    'cache_creation_tokens': cache_creation_tokens,
                    'cache_read_tokens': cache_read_tokens
                }
        
        chart_data.append(day_total)
        current_date += timedelta(days=1)
    
    return chart_data