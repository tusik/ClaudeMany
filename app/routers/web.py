from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app import database, crud, auth
from datetime import timedelta
from app.config import settings

router = APIRouter()
templates = Jinja2Templates(directory="templates")

def get_redirect_url(request: Request, path: str) -> str:
    """生成考虑代理头信息的重定向URL"""
    # 首先尝试从代理头获取信息
    forwarded_proto = request.headers.get("x-forwarded-proto")
    forwarded_host = request.headers.get("x-forwarded-host")
    host_header = request.headers.get("host")
    
    # 如果有完整的代理头信息
    if forwarded_proto and forwarded_host:
        return f"{forwarded_proto}://{forwarded_host}{path}"
    
    # 如果只有协议信息，使用Host头
    if forwarded_proto and host_header:
        return f"{forwarded_proto}://{host_header}{path}"
    
    # 如果Host头不是127.0.0.1，使用Host头构建URL
    if host_header and host_header != "127.0.0.1" and host_header != "127.0.0.1:8000":
        # 判断协议（简单判断，生产环境建议配置）
        scheme = "https" if "443" in host_header or forwarded_proto == "https" else "http"
        return f"{scheme}://{host_header}{path}"
    
    # 本地测试：如果是127.0.0.1访问，直接使用相对路径
    if host_header and ("127.0.0.1" in host_header or "localhost" in host_header):
        return path
    
    # 降级：使用相对路径重定向
    return path

@router.get("/", response_class=HTMLResponse)
@router.get("", response_class=HTMLResponse)  # 同时匹配 /web 和 /web/
async def admin_dashboard(request: Request, db: Session = Depends(database.get_db)):
    try:
        # 检查是否有有效的session cookie
        token = request.cookies.get("admin_token")
        if token:
            # 验证token
            from jose import jwt, JWTError
            try:
                payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
                username = payload.get("sub")
                if username == settings.admin_username:
                    api_keys = crud.get_api_keys(db)
                    
                    # 获取后端配置
                    backend_configs = crud.get_backend_configs(db)
                    active_config = crud.get_active_backend_config(db)
                    
                    # 为每个API密钥获取使用统计
                    api_keys_with_stats = []
                    for key in api_keys:
                        stats = crud.get_usage_stats(db, key.id)
                        api_keys_with_stats.append({
                            "key": key,
                            "stats": stats
                        })
                    
                    # 获取总体统计
                    from sqlalchemy import func
                    summary = db.query(
                        func.count(database.UsageRecord.id).label("total_requests"),
                        func.sum(database.UsageRecord.tokens_used).label("total_tokens"),
                        func.sum(database.UsageRecord.cost).label("total_cost"),
                        func.count(func.distinct(database.UsageRecord.api_key_id)).label("active_keys")
                    ).first()
                    
                    stats = {
                        "total_requests": summary.total_requests or 0,
                        "total_tokens": summary.total_tokens or 0,
                        "total_cost": summary.total_cost or 0.0,
                        "active_keys": summary.active_keys or 0,
                        "total_api_keys": len(api_keys)
                    }
                    
                    return templates.TemplateResponse("dashboard.html", {
                        "request": request,
                        "api_keys_with_stats": api_keys_with_stats,
                        "stats": stats,
                        "backend_configs": backend_configs,
                        "active_config": active_config
                    })
            except JWTError:
                pass
    except Exception:
        pass
    
    return templates.TemplateResponse("login.html", {"request": request})

@router.post("/login")
async def web_login(request: Request, username: str = Form(...), password: str = Form(...)):
    if not auth.authenticate_admin(username, password):
        return templates.TemplateResponse("login.html", {
            "request": request, 
            "error": "用户名或密码错误"
        })
    
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = auth.create_access_token(
        data={"sub": username}, expires_delta=access_token_expires
    )
    
    # 调试信息
    host_header = request.headers.get("host")
    forwarded_host = request.headers.get("x-forwarded-host")
    forwarded_proto = request.headers.get("x-forwarded-proto")
    print(f"Login redirect debug - Host: {host_header}, X-Forwarded-Host: {forwarded_host}, X-Forwarded-Proto: {forwarded_proto}")
    
    redirect_url = get_redirect_url(request, "/web/")  # 添加尾斜杠
    print(f"Redirect URL: {redirect_url}")
    
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie(
        key="admin_token", 
        value=access_token,
        max_age=settings.access_token_expire_minutes * 60,
        httponly=True,
        secure=False,  # 允许HTTP连接
        samesite="lax"  # 放宽同源限制
    )
    return response

@router.post("/logout")
async def web_logout(request: Request):
    response = RedirectResponse(url=get_redirect_url(request, "/web/"), status_code=303)
    response.delete_cookie("admin_token", secure=False, samesite="lax")
    return response

@router.post("/create-key")
async def web_create_key(
    request: Request,
    name: str = Form(...),
    rate_limit: int = Form(1000),
    quota_limit: int = Form(100000),
    cost_limit: float = Form(10.0),
    daily_quota: float = Form(50.0),
    db: Session = Depends(database.get_db)
):
    # 验证token
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("sub") != settings.admin_username:
            raise HTTPException(status_code=401, detail="权限不足")
    except:
        raise HTTPException(status_code=401, detail="Token无效")
    
    from app.schemas import APIKeyCreate
    api_key_data = APIKeyCreate(name=name, rate_limit=rate_limit, quota_limit=quota_limit, cost_limit=cost_limit, daily_quota=daily_quota)
    db_key, key = crud.create_api_key(db, api_key_data)
    
    return RedirectResponse(url=get_redirect_url(request, f"/web/?new_key={key}"), status_code=303)

@router.post("/deactivate-key/{key_id}")
async def web_deactivate_key(
    key_id: str,
    request: Request,
    db: Session = Depends(database.get_db)
):
    # 验证token
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("sub") != settings.admin_username:
            raise HTTPException(status_code=401, detail="权限不足")
    except:
        raise HTTPException(status_code=401, detail="Token无效")
    
    crud.deactivate_api_key(db, key_id)
    return RedirectResponse(url=get_redirect_url(request, "/web/"), status_code=303)

@router.post("/delete-key/{key_id}")
async def web_delete_key(
    key_id: str,
    request: Request,
    db: Session = Depends(database.get_db)
):
    # 验证token
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("sub") != settings.admin_username:
            raise HTTPException(status_code=401, detail="权限不足")
    except:
        raise HTTPException(status_code=401, detail="Token无效")
    
    crud.delete_api_key(db, key_id)
    return RedirectResponse(url=get_redirect_url(request, "/web/"), status_code=303)

@router.post("/regenerate-key/{key_id}")
async def web_regenerate_key(
    key_id: str,
    request: Request,
    db: Session = Depends(database.get_db)
):
    # 验证token
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("sub") != settings.admin_username:
            raise HTTPException(status_code=401, detail="权限不足")
    except:
        raise HTTPException(status_code=401, detail="Token无效")
    
    db_key, new_key = crud.regenerate_api_key(db, key_id)
    if db_key and new_key:
        return RedirectResponse(url=get_redirect_url(request, f"/web/?regenerated_key={new_key}&key_name={db_key.name}"), status_code=303)
    else:
        raise HTTPException(status_code=404, detail="API密钥不存在")

# 后端配置管理路由
@router.post("/create-backend")
async def web_create_backend(
    request: Request,
    name: str = Form(...),
    base_url: str = Form(...),
    api_key: str = Form(...),
    db: Session = Depends(database.get_db)
):
    # 验证token
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("sub") != settings.admin_username:
            raise HTTPException(status_code=401, detail="权限不足")
    except:
        raise HTTPException(status_code=401, detail="Token无效")
    
    # 处理复选框 - 如果未勾选，不会在form数据中
    form_data = await request.form()
    is_default = 'is_default' in form_data
    
    crud.create_backend_config(db, name, base_url, api_key, is_default)
    return RedirectResponse(url=get_redirect_url(request, "/web/"), status_code=303)

@router.post("/activate-backend/{config_id}")
async def web_activate_backend(
    config_id: str,
    request: Request,
    db: Session = Depends(database.get_db)
):
    # 验证token
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("sub") != settings.admin_username:
            raise HTTPException(status_code=401, detail="权限不足")
    except:
        raise HTTPException(status_code=401, detail="Token无效")
    
    crud.activate_backend_config(db, config_id)
    return RedirectResponse(url=get_redirect_url(request, "/web/"), status_code=303)

@router.post("/delete-backend/{config_id}")
async def web_delete_backend(
    config_id: str,
    request: Request,
    db: Session = Depends(database.get_db)
):
    # 验证token
    token = request.cookies.get("admin_token")
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    
    try:
        from jose import jwt
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        if payload.get("sub") != settings.admin_username:
            raise HTTPException(status_code=401, detail="权限不足")
    except:
        raise HTTPException(status_code=401, detail="Token无效")
    
    if crud.delete_backend_config(db, config_id):
        return RedirectResponse(url=get_redirect_url(request, "/web/"), status_code=303)
    else:
        raise HTTPException(status_code=400, detail="无法删除默认配置或配置不存在")