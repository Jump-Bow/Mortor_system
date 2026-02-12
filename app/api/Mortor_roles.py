"""
Roles API Blueprint
角色管理 API（預留功能）

Note: 角色管理為預留功能，API 保留但後端暫不與 HrAccount 連結。
後續啟用角色管理時可恢復關聯。
"""
from flask import Blueprint, request, jsonify
from app import db
from app.models.Mortor_user import Role
from app.utils.decorators import log_request, admin_required, web_or_api_required

roles_bp = Blueprint('roles', __name__)


@roles_bp.route('/list', methods=['GET'])
@web_or_api_required
@admin_required
@log_request
def list_roles(**kwargs):
    """
    取得角色列表
    
    Query Parameters:
        - search: 搜尋關鍵字 (可選)
        - page: 頁碼 (可選，預設 1)
        - per_page: 每頁筆數 (可選，預設 20)
    
    Response:
        - roles: 角色列表
        - pagination: 分頁資訊
    """
    search = request.args.get('search', '').strip()
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    # Build query
    query = Role.query
    
    if search:
        query = query.filter(
            db.or_(
                Role.role_name.like(f'%{search}%'),
                Role.description.like(f'%{search}%')
            )
        )
    
    # Order by role_id
    query = query.order_by(Role.role_id)
    
    # Paginate
    pagination = query.paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    roles_data = [role.to_dict() for role in pagination.items]
    
    return jsonify({
        'status': 'success',
        'data': {
            'roles': roles_data,
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


@roles_bp.route('/all', methods=['GET'])
@web_or_api_required
@log_request
def get_all_roles(**kwargs):
    """
    取得所有角色 (不分頁，用於下拉選單)
    
    Response:
        - roles: 所有角色列表
    """
    roles = Role.query.order_by(Role.role_id).all()
    
    return jsonify({
        'status': 'success',
        'data': {
            'roles': [role.to_dict() for role in roles]
        }
    }), 200


@roles_bp.route('/<int:role_id>', methods=['GET'])
@web_or_api_required
@admin_required
@log_request
def get_role(role_id, **kwargs):
    """
    取得單一角色資訊
    
    Response:
        - role: 角色資訊
    """
    role = Role.query.get(role_id)
    
    if not role:
        return jsonify({
            'status': 'error',
            'message': '角色不存在'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': {
            'role': role.to_dict()
        }
    }), 200


@roles_bp.route('/create', methods=['POST'])
@web_or_api_required
@admin_required
@log_request
def create_role(**kwargs):
    """
    建立新角色
    
    Request Body:
        - role_name: 角色名稱 (必填，唯一)
        - description: 角色說明 (可選)
    
    Response:
        - role: 建立的角色資訊
    """
    data = request.get_json()
    
    # Validate required fields
    if not data or 'role_name' not in data:
        return jsonify({
            'status': 'error',
            'message': '缺少必要欄位: role_name'
        }), 400
    
    role_name = data['role_name'].strip()
    description = data.get('description', '').strip()
    
    if not role_name or len(role_name) > 50:
        return jsonify({
            'status': 'error',
            'message': '角色名稱長度必須在 1-50 字元之間'
        }), 400
    
    # Check if role_name already exists
    existing_role = Role.query.filter_by(role_name=role_name).first()
    if existing_role:
        return jsonify({
            'status': 'error',
            'message': f'角色名稱 "{role_name}" 已存在'
        }), 400
    
    try:
        role = Role(
            role_name=role_name,
            description=description if description else None
        )
        
        db.session.add(role)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '角色建立成功',
            'data': {
                'role': role.to_dict()
            }
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'建立角色時發生錯誤: {str(e)}'
        }), 500


@roles_bp.route('/<int:role_id>', methods=['PUT'])
@web_or_api_required
@admin_required
@log_request
def update_role(role_id, **kwargs):
    """
    更新角色資訊
    
    Request Body:
        - role_name: 角色名稱 (可選)
        - description: 角色說明 (可選)
    
    Response:
        - role: 更新後的角色資訊
    """
    data = request.get_json()
    
    if not data:
        return jsonify({
            'status': 'error',
            'message': '未提供更新資料'
        }), 400
    
    role = Role.query.get(role_id)
    
    if not role:
        return jsonify({
            'status': 'error',
            'message': '角色不存在'
        }), 404
    
    try:
        if 'role_name' in data:
            role_name = data['role_name'].strip()
            
            if not role_name or len(role_name) > 50:
                return jsonify({
                    'status': 'error',
                    'message': '角色名稱長度必須在 1-50 字元之間'
                }), 400
            
            existing_role = Role.query.filter(
                Role.role_name == role_name,
                Role.role_id != role_id
            ).first()
            
            if existing_role:
                return jsonify({
                    'status': 'error',
                    'message': f'角色名稱 "{role_name}" 已存在'
                }), 400
            
            role.role_name = role_name
        
        if 'description' in data:
            description = data['description'].strip()
            role.description = description if description else None
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '角色更新成功',
            'data': {
                'role': role.to_dict()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'更新角色時發生錯誤: {str(e)}'
        }), 500


@roles_bp.route('/<int:role_id>', methods=['DELETE'])
@web_or_api_required
@admin_required
@log_request
def delete_role(role_id, **kwargs):
    """
    刪除角色
    
    Response:
        - message: 刪除結果訊息
    """
    role = Role.query.get(role_id)
    
    if not role:
        return jsonify({
            'status': 'error',
            'message': '角色不存在'
        }), 404
    
    try:
        db.session.delete(role)
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '角色刪除成功'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'刪除角色時發生錯誤: {str(e)}'
        }), 500
