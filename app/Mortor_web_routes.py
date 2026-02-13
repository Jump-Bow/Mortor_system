"""
Web UI Blueprint
網頁介面路由
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models.Mortor_user import HrAccount
from app.models.Mortor_system_log import UserLog
from app.models.Mortor_organization import TOrganization

web_bp = Blueprint('web', __name__)


@web_bp.route('/')
def index():
    """首頁 - 重定向到儀表板或登入頁"""
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))
    return redirect(url_for('web.login'))


@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登入頁面"""
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember', False)
        
        if not username or not password:
            flash('請輸入使用者名稱和密碼', 'error')
            return render_template('auth/Mortor_login.html')
        
        # username maps to HrAccount.id
        user = HrAccount.query.get(username)
        
        if not user or not user.check_password(password):
            flash('使用者名稱或密碼錯誤', 'error')
            return render_template('auth/Mortor_login.html')
        
        # Login user
        login_user(user, remember=remember)
        
        # Log the action
        UserLog.log_action(
            user_id=user.id,
            action_type='WEB_LOGIN',
            description=f'使用者 {user.id} 透過網頁登入系統',
            ip_address=request.remote_addr,
            status='SUCCESS'
        )
        
        # Store token in session for API calls
        from app.auth.jwt_handler import JWTHandler
        access_token, refresh_token = JWTHandler.generate_token(
            user.id,
            user.name,
            'User'  # 角色功能預留
        )
        session['api_token'] = access_token
        session['refresh_token'] = refresh_token
        
        flash('登入成功！', 'success')
        
        # Redirect to next page or dashboard
        next_page = request.args.get('next')
        return redirect(next_page or url_for('web.dashboard'))
    
    return render_template('auth/Mortor_login.html')


@web_bp.route('/logout')
@login_required
def logout():
    """登出"""
    # Log the action
    UserActionLog.log_action(
        user_id=current_user.id,
        action_type='WEB_LOGOUT',
        description=f'使用者 {current_user.id} 登出系統',
        ip_address=request.remote_addr,
        status='SUCCESS'
    )
    
    # Clear session
    session.pop('api_token', None)
    session.pop('refresh_token', None)
    
    logout_user()
    flash('您已成功登出', 'success')
    return redirect(url_for('web.login'))


@web_bp.route('/dashboard')
@login_required
def dashboard():
    """儀表板"""
    return render_template('dashboard/Mortor_index.html')


@web_bp.route('/inspection/records')
@login_required
def inspection_records():
    """巡檢紀錄查詢"""
    return render_template('inspection/Mortor_records.html')


@web_bp.route('/inspection/abnormal-tracking')
@login_required
def abnormal_tracking():
    """異常追蹤管理"""
    return render_template('inspection/Mortor_abnormal_tracking.html')


@web_bp.route('/task/list')
@login_required
def task_list():
    """任務列表"""
    return render_template('task/Mortor_list.html')


@web_bp.route('/task/create')
@login_required
def task_create():
    """新增任務"""
    return render_template('task/Mortor_create.html')


@web_bp.route('/task/<task_id>')
@login_required
def task_detail(task_id):
    """任務詳情"""
    return render_template('task/Mortor_detail.html', task_id=task_id)


@web_bp.route('/task/<task_id>/edit')
@login_required
def task_edit(task_id):
    """編輯任務"""
    return render_template('task/Mortor_edit.html', task_id=task_id)


@web_bp.route('/organization/tree')
@login_required
def organization_tree():
    """組織架構"""
    return render_template('organization/Mortor_tree.html')


@web_bp.route('/facility/list')
@login_required
def facility_list():
    """設施列表"""
    return render_template('facility/Mortor_list.html')


@web_bp.route('/facility/tree')
@login_required
def facility_tree():
    """設施架構"""
    return render_template('facility/Mortor_tree.html')


@web_bp.route('/facility/<facility_id>')
@login_required
def facility_detail(facility_id):
    """設施詳情"""
    facility = TOrganization.query.get_or_404(facility_id)
    return render_template('facility/Mortor_detail.html', facility=facility)


@web_bp.route('/system/users')
@login_required
def user_management():
    """使用者管理"""
    return render_template('system/Mortor_users.html')


@web_bp.route('/system/roles')
@login_required
def role_management():
    """角色管理（預留功能）"""
    return render_template('system/Mortor_roles.html')


@web_bp.route('/system/logs')
@login_required
def system_logs():
    """系統日誌"""
    return render_template('system/Mortor_logs.html')


# Error handlers
@web_bp.errorhandler(404)
def not_found_error(error):
    """404 錯誤處理"""
    return render_template('errors/Mortor_404.html'), 404


@web_bp.errorhandler(500)
def internal_error(error):
    """500 錯誤處理"""
    db.session.rollback()
    return render_template('errors/Mortor_500.html'), 500
