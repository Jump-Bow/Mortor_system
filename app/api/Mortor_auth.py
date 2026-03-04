"""
Authentication API Blueprint
認證與授權 API（支援 Local 與 Azure AD 登入）
"""
from flask import Blueprint, request, jsonify, current_app
from app.models.Mortor_user import HrAccount
from app.models.Mortor_system_log import UserLog
from app.auth.jwt_handler import JWTHandler, token_required
from app.auth.azure_ad_handler import AzureADHandler
from app.utils.decorators import validate_json, rate_limit, log_request
from app.utils.validators import Validator

auth_bp = Blueprint('auth', __name__)


# ==============================================================================
# Azure AD OAuth 2.0 端點
# ==============================================================================

@auth_bp.route('/azure/login', methods=['GET'])
@log_request
def azure_login():
    """
    取得 Azure AD 授權 URL

    前端應將使用者導向回傳的 auth_url，以進行 Microsoft 登入。

    Response:
        - auth_url: Azure AD 登入頁面的完整 URL
    """
    if not AzureADHandler.is_enabled():
        return jsonify({
            'status': 'error',
            'message': 'Azure AD 認證未啟用'
        }), 503

    auth_url, error = AzureADHandler.get_auth_url()

    if error:
        return jsonify({
            'status': 'error',
            'message': error
        }), 500

    return jsonify({
        'status': 'success',
        'data': {
            'auth_url': auth_url
        }
    }), 200


@auth_bp.route('/azure/callback', methods=['GET'])
@log_request
def azure_callback():
    """
    Azure AD OAuth 回調端點

    Microsoft 登入成功後會自動將使用者導向此端點，
    並帶入 authorization code。系統用此 code 換取 token，
    再以 preferred_username 比對 hr_account.id 發放本系統 JWT。

    Query Parameters:
        - code: Azure AD 回傳的授權碼 (由 Microsoft 自動帶入)
        - error: 錯誤代碼 (若使用者取消或認證失敗)
        - error_description: 錯誤描述

    Response:
        - token: JWT Access Token
        - refresh_token: JWT Refresh Token
        - user: 使用者資訊
    """
    # 檢查是否有錯誤回傳 (例如使用者取消登入)
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', error)
        current_app.logger.warning(f'Azure AD callback error: {error_desc}')
        return jsonify({
            'status': 'error',
            'message': f'Azure AD 認證失敗: {error_desc}'
        }), 400

    # 取得 authorization code
    code = request.args.get('code')
    if not code:
        return jsonify({
            'status': 'error',
            'message': 'Azure AD 認證失敗：未提供授權碼'
        }), 400

    # 用 code 換取 token
    result, token_error = AzureADHandler.acquire_token_by_code(code)
    if token_error:
        return jsonify({
            'status': 'error',
            'message': token_error
        }), 401

    # 從 token 提取使用者帳號
    username = AzureADHandler.get_username_from_token(result)
    if not username:
        return jsonify({
            'status': 'error',
            'message': 'Azure AD 認證失敗：無法取得使用者帳號'
        }), 401

    # 以帳號查詢資料庫
    user = HrAccount.query.filter_by(id=username).first()
    if not user:
        current_app.logger.warning(f'Azure AD user not found in database: {username}')
        return jsonify({
            'status': 'error',
            'message': '此帳號未授權使用本系統'
        }), 401

    # 產生本系統 JWT Token
    access_token, refresh_token = JWTHandler.generate_token(
        user.id,
        user.id,
        'User'
    )

    # 記錄成功登入
    UserLog.log_action(
        user_id=user.id,
        action_type='LOGIN',
        description=f'使用者 {user.id} 透過 Azure AD 登入系統',
        ip_address=request.remote_addr
    )

    current_app.logger.info(f'User {user.id} logged in via Azure AD')

    return jsonify({
        'status': 'success',
        'data': {
            'token': access_token,
            'refresh_token': refresh_token,
            'expires_in': int(current_app.config['JWT_ACCESS_TOKEN_EXPIRES'].total_seconds()),
            'user': user.to_dict()
        }
    }), 200


# ==============================================================================
# Local 登入端點
# ==============================================================================

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

            return jsonify({
                'status': 'error',
                'message': '帳號或密碼錯誤'
            }), 401

    elif login_type == 'azure_ad':
        # Azure AD: 導引前端至 Azure AD 授權頁面
        if not AzureADHandler.is_enabled():
            return jsonify({
                'status': 'error',
                'message': 'Azure AD 認證未啟用'
            }), 503

        auth_url, error = AzureADHandler.get_auth_url()
        if error:
            return jsonify({
                'status': 'error',
                'message': error
            }), 500

        return jsonify({
            'status': 'success',
            'message': '請導向 Azure AD 登入頁面',
            'data': {
                'auth_url': auth_url
            }
        }), 200
    
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
    UserLog.log_action( # Changed from UserLog.log_action
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
    try:
        current_user = kwargs.get('current_user')
        current_user_id = current_user.id if current_user else 'Unknown'
        
        UserLog.log_action(
            user_id=current_user_id,
            action_type='LOGOUT',
            description='User logged out',
            ip_address=request.remote_addr
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Successfully logged out'
        }), 200
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '登出過程發生錯誤'
        }), 500   
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
