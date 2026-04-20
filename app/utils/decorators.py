"""
Utility Decorators
工具裝飾器
"""
from functools import wraps
from flask import request, jsonify, current_app
from flask_login import current_user as flask_current_user
import time


def validate_json(f):
    """驗證請求必須為 JSON 格式"""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'error_code': 'BAD_REQUEST',
                'message': '請求必須為 JSON 格式'
            }), 400
        return f(*args, **kwargs)
    return decorated


def rate_limit(max_requests: int, time_window: int):
    """
    API 速率限制裝飾器（基於 Redis 滑動窗口，跨 Worker 有效）

    使用 app/middleware/rate_limiter.py 的 RateLimiter，
    透過 Redis 計數確保多 Gunicorn Worker 共享同一計數狀態。
    Redis 不可用時自動降級為放行（不限制），不影響服務可用性。

    Args:
        max_requests: 時間窗口內最大請求數
        time_window:  時間窗口（秒）
    """
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if not current_app.config.get('RATELIMIT_ENABLED', True):
                return f(*args, **kwargs)

            from app.middleware.rate_limiter import RateLimiter
            client_ip = request.remote_addr or 'unknown'

            is_limited, remaining, reset_time = RateLimiter._check_limit(
                client_ip, max_requests, time_window
            )

            if is_limited:
                return jsonify({
                    'status': 'error',
                    'error_code': 'TOO_MANY_REQUESTS',
                    'message': f'請求過於頻繁，請在 {time_window} 秒後重試'
                }), 429

            return f(*args, **kwargs)

        return decorated
    return decorator



def log_request(f):
    """記錄 API 請求"""
    @wraps(f)
    def decorated(*args, **kwargs):
        current_app.logger.info(
            f"API Request: {request.method} {request.path} "
            f"from {request.remote_addr}"
        )
        
        start_time = time.time()
        result = f(*args, **kwargs)
        elapsed_time = time.time() - start_time
        
        current_app.logger.info(
            f"API Response: {request.method} {request.path} "
            f"completed in {elapsed_time:.3f}s"
        )
        
        return result
    
    return decorated


def web_or_api_required(f):
    """
    混合認證裝飾器 - 支援 Flask-Login (Web) 或 JWT (API)
    優先使用 Flask-Login session，如果不存在則嘗試 JWT token
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = None
        auth_method = None
        
        # 方法 1: 檢查 Flask-Login session (Web UI)
        if flask_current_user.is_authenticated:
            user = flask_current_user
            auth_method = 'session'
            current_app.logger.debug(f'Authenticated via Flask-Login: {user.id}')
        else:
            # 方法 2: 檢查 JWT Token (API)
            from app.auth.jwt_handler import JWTHandler
            token = JWTHandler.get_token_from_header()
            
            if token:
                payload = JWTHandler.decode_token(token)
                if payload and payload.get('type') == 'access':
                    from app.models.Mortor_user import HrAccount
                    user = HrAccount.query.get(payload['user_id'])
                    if user:
                        auth_method = 'jwt'
                        current_app.logger.debug(f'Authenticated via JWT: {user.id}')
        
        # 如果兩種方式都失敗
        if not user:
            return jsonify({
                'status': 'error',
                'error_code': 'UNAUTHORIZED',
                'message': '登入已過期或未授權'
            }), 401
        
        # 將使用者資訊加入 kwargs
        kwargs['current_user'] = {
            'user_id': user.id,
            'id': user.id,
            'username': user.id,
            'name': user.name,
            'auth_method': auth_method
        }
        kwargs['user_object'] = user
        
        return f(*args, **kwargs)
    
    return decorated


def admin_required(f):
    """
    驗證使用者必須為管理者
    
    Note: 角色功能為預留狀態。目前暫時允許所有已認證使用者通過，
    後續啟用角色管理時可恢復角色檢查邏輯。
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        # Check if current_user exists in kwargs (from web_or_api_required)
        current_user_data = kwargs.get('current_user')
        
        if not current_user_data:
            return jsonify({
                'status': 'error',
                'error_code': 'UNAUTHORIZED',
                'message': '需要登入才能執行此操作'
            }), 401
        
        # TODO: 角色功能預留 - 後續啟用角色管理時恢復角色檢查
        # 目前暫時允許所有已認證使用者通過
        # if current_user_data.get('role') != '管理者':
        #     return jsonify({
        #         'status': 'error',
        #         'error_code': 'FORBIDDEN',
        #         'message': '此功能僅限管理者使用'
        #     }), 403
        
        return f(*args, **kwargs)
    
    return decorated
