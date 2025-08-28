from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app import database, crud, schemas
from typing import List, Optional

router = APIRouter()

@router.get("/stats/{api_key_id}", response_model=schemas.UsageStats)
async def get_usage_stats(
    api_key_id: str,
    db: Session = Depends(database.get_db)
):
    db_key = db.query(database.APIKey).filter(database.APIKey.id == api_key_id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    return crud.get_usage_stats(db, api_key_id)

@router.get("/records/{api_key_id}", response_model=List[schemas.UsageRecord])
async def get_usage_records(
    api_key_id: str,
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(database.get_db)
):
    db_key = db.query(database.APIKey).filter(database.APIKey.id == api_key_id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    records = crud.get_usage_records(db, api_key_id, limit)
    
    return [
        schemas.UsageRecord(
            id=record.id,
            endpoint=record.endpoint,
            method=record.method,
            tokens_used=record.tokens_used,
            cost=record.cost,
            processing_time=record.processing_time,
            output_tps=record.output_tps,
            timestamp=record.timestamp,
            status_code=record.status_code,
            error_message=record.error_message
        ) for record in records
    ]

@router.get("/chart/{api_key_id}")
async def get_usage_chart_data(
    api_key_id: str,
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(database.get_db)
):
    """获取API密钥的每日用量图表数据"""
    db_key = db.query(database.APIKey).filter(database.APIKey.id == api_key_id).first()
    if not db_key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    chart_data = crud.get_daily_usage_chart_data(db, api_key_id, days)
    
    return {
        "api_key_id": api_key_id,
        "days": days,
        "data": chart_data
    }

@router.post("/aggregate")
async def aggregate_daily_usage(
    date: Optional[str] = None,
    db: Session = Depends(database.get_db)
):
    """手动触发每日用量汇总（管理员功能）"""
    try:
        crud.aggregate_daily_usage(db, date)
        return {"message": f"Daily usage aggregated successfully for date: {date or 'yesterday'}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Aggregation failed: {str(e)}")

@router.get("/summary")
async def get_overall_usage_summary(db: Session = Depends(database.get_db)):
    from sqlalchemy import func
    
    summary = db.query(
        func.count(database.UsageRecord.id).label("total_requests"),
        func.sum(database.UsageRecord.tokens_used).label("total_tokens"),
        func.sum(database.UsageRecord.cost).label("total_cost"),
        func.count(func.distinct(database.UsageRecord.api_key_id)).label("active_keys")
    ).first()
    
    return {
        "total_requests": summary.total_requests or 0,
        "total_tokens": summary.total_tokens or 0,
        "total_cost": summary.total_cost or 0.0,
        "active_keys": summary.active_keys or 0
    }

@router.get("/chart")
async def get_overall_usage_chart_data(
    days: int = Query(30, ge=1, le=365),
    db: Session = Depends(database.get_db)
):
    """获取所有API密钥的每日用量汇总图表数据"""
    from datetime import datetime, timedelta
    from sqlalchemy import func, and_
    
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=days-1)
    
    # 按日期汇总所有API密钥的用量
    daily_stats = db.query(
        func.date(database.UsageRecord.timestamp).label('date'),
        func.count(database.UsageRecord.id).label('total_requests'),
        func.sum(database.UsageRecord.tokens_used).label('total_tokens'),
        func.sum(database.UsageRecord.cost).label('total_cost')
    ).filter(
        and_(
            func.date(database.UsageRecord.timestamp) >= start_date.strftime('%Y-%m-%d'),
            func.date(database.UsageRecord.timestamp) <= end_date.strftime('%Y-%m-%d')
        )
    ).group_by(
        func.date(database.UsageRecord.timestamp)
    ).all()
    
    # 创建完整的日期范围数据
    chart_data = []
    current_date = start_date
    
    # 将查询结果转换为字典以便快速查找
    stats_dict = {str(stat.date): stat for stat in daily_stats}
    
    while current_date <= end_date:
        date_str = current_date.strftime('%Y-%m-%d')
        stat = stats_dict.get(date_str)
        
        if stat:
            chart_data.append({
                "date": date_str,
                "total_requests": stat.total_requests or 0,
                "total_tokens": stat.total_tokens or 0,
                "total_cost": round(stat.total_cost or 0.0, 6)
            })
        else:
            # 没有数据的日期填充0
            chart_data.append({
                "date": date_str,
                "total_requests": 0,
                "total_tokens": 0,
                "total_cost": 0.0
            })
        
        current_date += timedelta(days=1)
    
    return {
        "days": days,
        "data": chart_data
    }