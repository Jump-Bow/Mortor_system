"""
Authentication API Blueprint
認證與授權 API（支援 Local 與 Azure AD 登入）
"""
from flask import Blueprint, request, jsonify, current_app, redirect, url_for, flash, session
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
    系統將使用 authorization code 換取 token 並嘗試登入使用者，
    不論失敗或成功，都會重新導向回網頁畫面並顯示適當的訊息。
    
    注意：因為從微軟跨網域重導向回來時 SameSite=Strict 會導致
    Session 遺失，所以錯誤訊息改用 URL Query Parameter 傳遞。
    """
    # 檢查是否有錯誤回傳 (例如使用者取消登入)
    error = request.args.get('error')
    if error:
        error_desc = request.args.get('error_description', error)
        current_app.logger.warning(f'Azure AD callback error: {error_desc}')
        return redirect(url_for('web.login', azure_error=f'Azure AD 認證失敗: {error_desc}'))

    # 取得 authorization code
    code = request.args.get('code')
    if not code:
        return redirect(url_for('web.login', azure_error='Azure AD 認證失敗：未提供授權碼'))

    # 用 code 換取 token
    result, token_error = AzureADHandler.acquire_token_by_code(code)
    if token_error:
        return redirect(url_for('web.login', azure_error=token_error))

    # 從 token 提取使用者帳號
    username = AzureADHandler.get_username_from_token(result)
    if not username:
        return redirect(url_for('web.login', azure_error='Azure AD 認證失敗：無法取得使用者帳號'))

    # 以帳號查詢資料庫
    user = HrAccount.query.filter_by(id=username).first()
    if not user:
        current_app.logger.warning(f'Azure AD user not found in database: {username}')
        return redirect(url_for('web.login', azure_error='此帳號未授權使用本系統'))

    # 產生本系統 JWT Token
    access_token, refresh_token = JWTHandler.generate_token(
        user.id,
        user.name if hasattr(user, 'name') else user.id,
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

    from flask_login import login_user as flask_login_user
    from flask import session as flask_session
    
    # 執行網頁使用者登入
    flask_login_user(user)
    flask_session['api_token'] = access_token
    flask_session['refresh_token'] = refresh_token

    flash('Azure AD 登入成功！', 'success')
    return redirect(url_for('web.dashboard'))


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

        # ── 雙維度登入速率限制（IP + 帳號），防止 Brute-force 攻擊 ──────────────
        # 注意：必須在 DB 查詢之前執行，避免攻擊者消耗資料庫連線資源
        if current_app.config.get('RATELIMIT_ENABLED', True):
            from app.middleware.rate_limiter import RateLimiter
            is_limited, dimension, reset_time = RateLimiter.check_login_limit(
                ip=request.remote_addr or 'unknown',
                username=username
            )
            if is_limited:
                dim_msg = '此帳號' if dimension == 'account' else '此 IP'
                response = jsonify({
                    'status': 'error',
                    'error_code': 'TOO_MANY_REQUESTS',
                    'message': f'{dim_msg}登入嘗試次數過多，請 15 分鐘後再試',
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(reset_time)
                return response
        # ─────────────────────────────────────────────────────────────────────────

        # Find user
        user = HrAccount.query.filter_by(id=username).first()

        if not user or not user.check_password(password):
            current_app.logger.warning(f'Failed login attempt for user: {username}')

            return jsonify({
                'status': 'error',
                'message': '帳號或密碼錯誤'
            }), 401

    elif login_type == 'azure_ad':
        # ── Azure AD ROPC（Resource Owner Password Credentials）流程 ─────────────
        # 公司要求：APP 直接丟帳號/密碼給 Server，由 Server 去與 Azure AD 認證。
        # 流程：APP → POST /login {username, password, login_type: azure_ad}
        #       Server → POST https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token
        #       Azure AD → 成功 → Server 產生自己的 JWT → 回傳給 APP
        import requests as _requests

        error = Validator.validate_required_fields(data, ['username', 'password'])
        if error:
            return jsonify({'status': 'error', 'message': error}), 400

        ad_username = data['username']
        ad_password = data['password']

        tenant_id = current_app.config.get('AZURE_TENANT_ID', '')
        client_id = current_app.config.get('AZURE_CLIENT_ID', '')
        client_secret = current_app.config.get('AZURE_CLIENT_SECRET', '')

        if not tenant_id or not client_id:
            return jsonify({'status': 'error', 'message': 'Azure AD 認證未設定，請聯絡系統管理員'}), 503

        # Azure AD UPN 格式：員工編號@公司域名（可由環境變數設定）
        upn_domain = current_app.config.get('AZURE_UPN_DOMAIN', '')
        upn = ad_username if '@' in ad_username else (
            f"{ad_username}@{upn_domain}" if upn_domain else ad_username
        )

        token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
        try:
            ad_resp = _requests.post(token_url, data={
                'grant_type':    'password',
                'client_id':     client_id,
                'client_secret': client_secret,
                'username':      upn,
                'password':      ad_password,
                'scope':         'openid profile email',
            }, timeout=10)
        except Exception as e:
            current_app.logger.error(f'Azure AD ROPC request failed: {e}')
            return jsonify({'status': 'error', 'message': 'AD 伺服器連線失敗'}), 503

        if ad_resp.status_code != 200:
            ad_error = ad_resp.json().get('error_description', 'AD 認證失敗')
            current_app.logger.warning(f'Azure AD ROPC failed for {upn}: {ad_error}')
            return jsonify({'status': 'error', 'message': '帳號或密碼錯誤（AD）'}), 401

        # 以員工編號（不含 domain）查詢本地資料庫
        employee_id = ad_username.split('@')[0]
        user = HrAccount.query.filter_by(id=employee_id).first()
        if not user:
            current_app.logger.warning(f'Azure AD user not found in hr_account: {employee_id}')
            return jsonify({'status': 'error', 'message': '此帳號未授權使用本系統，請聯絡管理員'}), 403

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
    
    將當前 Token 的 JTI 加入 Redis 黑名單，
    使該 Token 在過期前無法再用於認證。
    """
    try:
        current_user = kwargs.get('current_user')
        token_payload = kwargs.get('token_payload', {})
        current_user_id = current_user.id if current_user else 'Unknown'
        
        # 將 Token JTI 加入黑名單
        jti = token_payload.get('jti')
        if jti:
            from app.services.token_blacklist import TokenBlacklistService
            from datetime import datetime, timedelta
            
            # 計算 Token 剩餘有效時間作為 Redis TTL
            exp = token_payload.get('exp')
            if exp:
                remaining = exp - int(datetime.utcnow().timestamp())
                expires_delta = timedelta(seconds=max(remaining, 0))
            else:
                expires_delta = None
            
            TokenBlacklistService.add_to_blacklist(jti, expires_delta)
        
        UserLog.log_action(
            user_id=current_user_id,
            action_type='LOGOUT',
            description=f'使用者 {current_user_id} 登出系統 (JTI: {jti[:8] if jti else "N/A"}...)',
            ip_address=request.remote_addr
        )
        
        from app.utils.api_response import success_response
        return success_response(message='登出成功')
    except Exception as e:
        current_app.logger.error(f"Logout error: {str(e)}")
        from app.utils.api_response import error_response
        return error_response(message='登出過程發生錯誤', error_code='LOGOUT_ERROR', status_code=500)


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
