"""
JWT Handler for Authentication
JWT Token 管理與驗證
"""
import jwt
from datetime import datetime
from flask import current_app, request
from functools import wraps
from typing import Dict, Optional, Tuple
from app.models.Mortor_system_log import SysLog


class JWTHandler:
    """JWT Token 處理器"""
    
    @staticmethod
    def generate_token(user_id: int, username: str, role: str) -> Tuple[str, str]:
        """
        生成 Access Token 和 Refresh Token
        
        Args:
            user_id: 使用者 ID
            username: 使用者名稱
            role: 使用者角色
            
        Returns:
            Tuple of (access_token, refresh_token)
        """
        # Access Token
        access_payload = {
            'user_id': user_id,
            'username': username,
            'role': role,
            'exp': datetime.utcnow() + current_app.config['JWT_ACCESS_TOKEN_EXPIRES'],
            'iat': datetime.utcnow(),
            'type': 'access'
        }
        access_token = jwt.encode(
            access_payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm=current_app.config['JWT_ALGORITHM']
        )
        
        # Refresh Token
        refresh_payload = {
            'user_id': user_id,
            'username': username,
            'exp': datetime.utcnow() + current_app.config['JWT_REFRESH_TOKEN_EXPIRES'],
            'iat': datetime.utcnow(),
            'type': 'refresh'
        }
        refresh_token = jwt.encode(
            refresh_payload,
            current_app.config['JWT_SECRET_KEY'],
            algorithm=current_app.config['JWT_ALGORITHM']
        )
        
        return access_token, refresh_token
    
    @staticmethod
    def decode_token(token: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        解碼並驗證 Token
        
        Args:
            token: JWT Token
            
        Returns:
            (payload, error_code)
            - payload: dict or None
            - error_code: None / 'EXPIRED' / 'INVALID'
        """
        try:
            payload = jwt.decode(
                token,
                current_app.config['JWT_SECRET_KEY'],
                algorithms=[current_app.config['JWT_ALGORITHM']],
                leeway=current_app.config.get('JWT_LEEWAY', 0)
            )
            return payload, None
        except jwt.ExpiredSignatureError:
            current_app.logger.warning('Token has expired')
            return None, 'EXPIRED'
        except jwt.InvalidTokenError:
            current_app.logger.warning('Invalid token')
            return None, 'INVALID'

    @staticmethod
    def is_token_expiring(payload: Dict, threshold_seconds: int = 300) -> bool:
        """判斷 Token 是否即將過期 (預設 5 分鐘內)"""
        try:
            exp = payload.get('exp')
            if not exp:
                return False
            # PyJWT returns int timestamp
            remaining = exp - int(datetime.utcnow().timestamp())
            return remaining <= threshold_seconds
        except Exception:
            return False
    
    @staticmethod
    def get_token_from_header() -> Optional[str]:
        """
        從 HTTP Header 中提取 Token
        
        Returns:
            Token string or None
        """
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith('Bearer '):
            return auth_header.split(' ')[1]
        return None
    
    @staticmethod
    def refresh_access_token(refresh_token: str) -> Optional[str]:
        """
        使用 Refresh Token 生成新的 Access Token
        
        Args:
            refresh_token: Refresh Token
            
        Returns:
            New access token or None
        """
        payload, error = JWTHandler.decode_token(refresh_token)
        
        if not payload or error or payload.get('type') != 'refresh':
            return None
        
        # Generate new access token
        from app.models.Mortor_user import HrAccount
        user = HrAccount.query.get(payload['user_id'])
        if not user:
            return None
        
        new_access_token, _ = JWTHandler.generate_token(
            user.id,
            user.name,
            'User'  # 角色功能預留
        )
        
        return new_access_token


def token_required(f):
    """
    裝飾器: 驗證 JWT Token
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        token = JWTHandler.get_token_from_header()
        
        if not token:
            SysLog.create(level='WARN', module='Auth')
            return {
                'status': 'error',
                'error_code': 'UNAUTHORIZED',
                'message': '未提供認證 Token'
            }, 401
        
        payload, error = JWTHandler.decode_token(token)
        
        if not payload:
            msg = 'Token 無效或已過期' if error == 'EXPIRED' else '無效的 Token'
            SysLog.create(level='WARN', module='Auth')
            return {
                'status': 'error',
                'error_code': 'UNAUTHORIZED',
                'message': msg
            }, 401
        
        # Check if access token
        if payload.get('type') != 'access':
            SysLog.create(level='WARN', module='Auth')
            return {
                'status': 'error',
                'error_code': 'UNAUTHORIZED',
                'message': '無效的 Token 類型'
            }, 401
        
        # Verify user still exists and is active
        from app.models.Mortor_user import HrAccount
        user = HrAccount.query.get(payload['user_id'])
        if not user:
            SysLog.create(level='WARN', module='Auth')
            return {
                'status': 'error',
                'error_code': 'UNAUTHORIZED',
                'message': '使用者不存在'
            }, 401
        
        # Add current user to kwargs
        kwargs['current_user'] = user
        kwargs['token_payload'] = payload
        kwargs['token_will_expire_soon'] = JWTHandler.is_token_expiring(payload)
        
        return f(*args, **kwargs)
    
    return decorated


def role_required(*allowed_roles):
    """
    裝飾器: 驗證使用者角色
    """
    def decorator(f):
        @wraps(f)
        @token_required
        def decorated(*args, **kwargs):
            current_user = kwargs.get('current_user')
            
            if not current_user:
                SystemLog.create(level='WARN', module='Auth')
                return {
                    'status': 'error',
                    'error_code': 'FORBIDDEN',
                    'message': '權限不足'
                }, 403
            
            # TODO: 角色功能預留 - 暫時允許所有已認證使用者通過
            # user_role = current_user.role.role_name if current_user.role else None
            # if user_role not in allowed_roles:
            #     return {'status': 'error', 'message': '權限不足'}, 403
            
            return f(*args, **kwargs)
        
        return decorated
    return decorator
