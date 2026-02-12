"""
Authentication API Blueprint
認證與授權 API
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.Mortor_user import HrAccount
from app.models.Mortor_system_log import SystemLog, UserActionLog
from app.auth.jwt_handler import JWTHandler, token_required
from app.utils.decorators import validate_json, rate_limit, log_request
from app.utils.validators import Validator

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
@validate_json
@rate_limit(max_requests=5, time_window=60)
@log_request
def login():
    """
    使用者登入
    
    Request Body:
        - username: 使用者名稱
        - password: 密碼
        - login_type: 登入類型 (local/azure_ad)
        - ad_token: Azure AD Token (當 login_type=azure_ad 時)
    
    Response:
        - token: JWT Access Token
        - refresh_token: JWT Refresh Token
        - user: 使用者資訊
    """
    data = request.get_json()
    
    # Validate required fields
    login_type = data.get('login_type', 'local')
    
    if login_type == 'local':
        # Local authentication
        error = Validator.validate_required_fields(data, ['username', 'password'])
        if error:
            return jsonify({
                'status': 'error',
                'message': error
            }), 400
        
        username = data['username']
        password = data['password']
        
        # Find user
        user = HrAccount.query.filter_by(id=username).first()
        
        if not user or not user.check_password(password):
            current_app.logger.warning(f'Failed login attempt for user: {username}')
            
            # Log failed attempt
            # Note: We need a valid user_id for logging, but if login fails we might only have username
            # If user exists but password wrong, we use user.id. If user doesn't exist, we can't log to UserLog easily with FK.
            # For now, let's skip logging to UserLog for non-existent users or handle carefully.
            
            return jsonify({
                'status': 'error',
                'message': '帳號或密碼錯誤'
            }), 401
            
    elif login_type == 'azure_ad':
        # ... Azure AD logic ...
        return jsonify({
            'status': 'error',
            'message': 'Azure AD 登入功能開發中'
        }), 501
    
    else:
        return jsonify({
            'status': 'error',
            'message': '不支援的登入類型'
        }), 400
    
    # Generate JWT tokens
    access_token, refresh_token = JWTHandler.generate_token(
        user.id,
        user.id,
        'User'
    )
    
    # Log successful login
    UserActionLog.log_action( # Changed from UserLog.log_action
        user_id=user.id,
        action_type='LOGIN',
        description=f'使用者 {user.id} 登入系統',
        ip_address=request.remote_addr
    )
    
    current_app.logger.info(f'User {user.id} logged in successfully')
    
    return jsonify({
        'status': 'success',
        'data': {
            'token': access_token,
            'refresh_token': refresh_token,
            'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()),
            'user': user.to_dict()
        }
    }), 200


@auth_bp.route('/logout', methods=['POST'])
@token_required
@log_request
def logout(**kwargs):
    """
    使用者登出
    
    Note: JWT 是無狀態的，實際登出需要前端刪除 token
    """
    current_user_id = JWTHandler.get_jwt_identity() # Changed from get_jwt_identity() to JWTHandler.get_jwt_identity()
    
    UserActionLog.log_action( # Changed from UserLog.log_action to UserActionLog.log_action
        user_id=current_user_id,
        action_type='LOGOUT',
        description='User logged out',
        ip_address=request.remote_addr
    )
    
    return jsonify({'message': 'Successfully logged out'}), 200   
    # The following lines were part of the original response and are now replaced by the new return statement.
    # return jsonify({
    #     'status': 'success',
    #     'message': '登出成功'
    # }), 200


@auth_bp.route('/refresh', methods=['POST'])
@validate_json
@log_request
def refresh_token():
    """
    重新整理 Access Token
    
    Request Body:
        - refresh_token: Refresh Token
    
    Response:
        - token: 新的 Access Token
    """
    data = request.get_json()
    
    error = Validator.validate_required_fields(data, ['refresh_token'])
    if error:
        return jsonify({
            'status': 'error',
            'message': error
        }), 400
    
    refresh_token = data['refresh_token']
    
    # Generate new access token
    new_access_token = JWTHandler.refresh_access_token(refresh_token)
    
    if not new_access_token:
        return jsonify({
            'status': 'error',
            'message': 'Refresh Token 無效或已過期'
        }), 401
    
    return jsonify({
        'status': 'success',
        'data': {
            'token': new_access_token,
            'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds())
        }
    }), 200


@auth_bp.route('/verify', methods=['GET'])
@token_required
@log_request
def verify_token(**kwargs):
    """
    驗證 Token 是否有效
    
    Response:
        - valid: Token 是否有效
        - user: 使用者資訊
    """
    current_user = kwargs.get('current_user')
    
    return jsonify({
        'status': 'success',
        'data': {
            'valid': True,
            'user': current_user.to_dict()
        }
    }), 200


@auth_bp.route('/me', methods=['GET'])
@token_required
@log_request
def get_current_user(**kwargs):
    """
    取得當前使用者資訊
    
    Response:
        - user: 使用者詳細資訊
    """
    current_user = kwargs.get('current_user')
    
    return jsonify({
        'status': 'success',
        'data': {
            'user': current_user.to_dict()
        }
    }), 200
