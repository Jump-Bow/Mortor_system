"""
Users API Blueprint
使用者管理 API
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.Mortor_user import HrAccount, Role
from app.models.Mortor_system_log import UserLog
from app.auth.jwt_handler import token_required
from app.utils.decorators import log_request, web_or_api_required, admin_required
from app.utils.validators import Validator

users_bp = Blueprint('users', __name__)


@users_bp.route('/list', methods=['GET'])
@web_or_api_required
@admin_required
@log_request
def list_users(**kwargs):
    """
    取得使用者列表
    
    Query Parameters:
        - search: 搜尋關鍵字 (可選)
        - page: 頁碼 (可選，預設 1)
        - per_page: 每頁筆數 (可選，預設 20)
    
    Response:
        - users: 使用者列表
        - pagination: 分頁資訊
    """
    # Get filters
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query
    query = HrAccount.query
    
    if search:
        search_filter = f'%{search}%'
        query = query.filter(
            db.or_(
                HrAccount.id.like(search_filter),
                HrAccount.name.like(search_filter)
            )
        )
    
    # Paginate
    pagination = query.order_by(HrAccount.id).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    users_data = [user.to_dict() for user in pagination.items]
    
    return jsonify({
        'status': 'success',
        'data': {
            'users': users_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        }
    }), 200


@users_bp.route('/<user_id>', methods=['GET'])
@web_or_api_required
@admin_required
@log_request
def get_user_detail(user_id, **kwargs):
    """
    取得使用者詳細資訊
    
    Response:
        - user: 使用者詳細資訊
    """
    user = HrAccount.query.get(user_id)
    
    if not user:
        return jsonify({
            'status': 'error',
            'message': '使用者不存在'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': {
            'user': user.to_dict()
        }
    }), 200


@users_bp.route('/create', methods=['POST'])
@web_or_api_required
@admin_required
@log_request
def create_user(**kwargs):
    """
    建立新使用者
    
    Request Body:
        - id: 使用者 ID / 員工編號 (必填)
        - password: 密碼 (必填)
        - name: 姓名 (必填)
        - organizationid: 組織 ID (可選)
        - email: Email (可選)
    
    Response:
        - user: 新建立的使用者資訊
    """
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['id', 'password', 'name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({
                'status': 'error',
                'message': f'缺少必填欄位: {field}'
            }), 400
    
    # Check if user_id already exists
    if HrAccount.query.get(data['id']):
        return jsonify({
            'status': 'error',
            'message': '使用者 ID 已存在'
        }), 400
    
    # Validate password
    if not Validator.validate_password(data['password']):
        return jsonify({
            'status': 'error',
            'message': '密碼長度至少 6 個字元'
        }), 400
    
    try:
        # Create user
        user = HrAccount(
            id=data['id'],
            name=data['name'],
            organizationid=data.get('organizationid'),
            email=data.get('email'),
        )
        user.set_password(data['password'])
        
        db.session.add(user)
        db.session.commit()
        
        # Log action
        current_user_id = kwargs.get('current_user', {})
        if hasattr(current_user_id, 'id'):
            current_user_id = current_user_id.id
        elif isinstance(current_user_id, dict):
            current_user_id = current_user_id.get('user_id', current_user_id.get('id', 'system'))
            
        UserLog.log_action(
            user_id=current_user_id,
            action_type='USER_CREATE',
            description=f'建立新使用者: {user.id} ({user.name})',
            ip_address=request.remote_addr,
            status='SUCCESS'
        )
        
        return jsonify({
            'status': 'success',
            'message': '使用者建立成功',
            'data': {
                'user': user.to_dict()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'建立使用者失敗: {str(e)}'
        }), 500


@users_bp.route('/<user_id>/update', methods=['PUT'])
@web_or_api_required
@admin_required
@log_request
def update_user(user_id, **kwargs):
    """
    更新使用者資訊
    
    Request Body:
        - name: 姓名 (可選)
        - organizationid: 組織 ID (可選)
        - email: Email (可選)
    
    Response:
        - user: 更新後的使用者資訊
    """
    user = HrAccount.query.get(user_id)
    
    if not user:
        return jsonify({
            'status': 'error',
            'message': '使用者不存在'
        }), 404
    
    data = request.get_json()
    
    try:
        # Update fields
        if 'name' in data:
            user.name = data['name']
        
        if 'organizationid' in data:
            user.organizationid = data['organizationid']
            
        if 'email' in data:
            user.email = data['email']
        
        db.session.commit()
        
        # Log action
        current_user_id = kwargs.get('current_user', {})
        if hasattr(current_user_id, 'id'):
            current_user_id = current_user_id.id
        elif isinstance(current_user_id, dict):
            current_user_id = current_user_id.get('user_id', current_user_id.get('id', 'system'))
            
        UserLog.log_action(
            user_id=current_user_id,
            action_type='USER_UPDATE',
            description=f'更新使用者: {user.id} ({user.name})',
            ip_address=request.remote_addr,
            status='SUCCESS'
        )
        
        return jsonify({
            'status': 'success',
            'message': '使用者更新成功',
            'data': {
                'user': user.to_dict()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'更新使用者失敗: {str(e)}'
        }), 500


@users_bp.route('/<user_id>/password', methods=['PUT'])
@web_or_api_required
@admin_required
@log_request
def reset_password(user_id, **kwargs):
    """
    重設使用者密碼
    
    Request Body:
        - new_password: 新密碼 (必填)
    
    Response:
        - message: 操作結果訊息
    """
    user = HrAccount.query.get(user_id)
    
    if not user:
        return jsonify({
            'status': 'error',
            'message': '使用者不存在'
        }), 404
    
    data = request.get_json()
    
    if not data.get('new_password'):
        return jsonify({
            'status': 'error',
            'message': '缺少新密碼'
        }), 400
    
    # Validate password
    if not Validator.validate_password(data['new_password']):
        return jsonify({
            'status': 'error',
            'message': '密碼長度至少 6 個字元'
        }), 400
    
    try:
        user.set_password(data['new_password'])
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '密碼重設成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'重設密碼失敗: {str(e)}'
        }), 500


@users_bp.route('/<user_id>/delete', methods=['DELETE'])
@web_or_api_required
@admin_required
@log_request
def delete_user(user_id, **kwargs):
    """
    刪除使用者
    
    Response:
        - message: 操作結果訊息
    """
    user = HrAccount.query.get(user_id)
    
    if not user:
        return jsonify({
            'status': 'error',
            'message': '使用者不存在'
        }), 404
    
    # Prevent deleting own account
    current_user = kwargs.get('current_user')
    current_id = current_user.id if hasattr(current_user, 'id') else current_user.get('user_id', current_user.get('id'))
    
    if user.id == current_id:
        return jsonify({
            'status': 'error',
            'message': '無法刪除自己的帳號'
        }), 400
    
    try:
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '使用者已刪除'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'刪除使用者失敗: {str(e)}'
        }), 500


@users_bp.route('/roles', methods=['GET'])
@web_or_api_required
@log_request
def list_roles(**kwargs):
    """
    取得角色列表（預留功能）
    
    Response:
        - roles: 角色列表
    """
    roles = Role.query.all()
    roles_data = [role.to_dict() for role in roles]
    
    return jsonify({
        'status': 'success',
        'data': {
            'roles': roles_data
        }
    }), 200
