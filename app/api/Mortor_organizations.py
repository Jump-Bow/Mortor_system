"""
Organizations API Blueprint
組織管理 API
"""
from flask import Blueprint, request, jsonify, current_app
from app.models.Mortor_organization import HrOrganization
from app.auth.jwt_handler import token_required
from app.utils.decorators import log_request
from app.utils.validators import Validator

organizations_bp = Blueprint('organizations', __name__)


@organizations_bp.route('/tree', methods=['GET'])
@token_required
@log_request
def get_organization_tree(**kwargs):
    """
    取得組織樹狀結構
    
    Response:
        - organizations: 完整組織樹狀結構
    """
    root_orgs = HrOrganization.query.filter_by(parentid=None).all()
    tree = [org.to_dict(include_children=True) for org in root_orgs]
    
    return jsonify({
        'status': 'success',
        'data': {
            'organizations': tree
        }
    }), 200


@organizations_bp.route('/list', methods=['GET'])
@token_required
@log_request
def list_organizations(**kwargs):
    """
    取得組織列表 (扁平結構)
    
    Query Parameters:
        - parent_id: 上層組織 ID (可選)
    
    Response:
        - organizations: 組織列表
    """
    # Get filters
    parent_id = request.args.get('parent_id')
    
    # Build query
    query = HrOrganization.query
    
    if parent_id:
        query = query.filter_by(parentid=parent_id)
    
    organizations = query.all()
    
    orgs_data = [org.to_dict() for org in organizations]
    
    return jsonify({
        'status': 'success',
        'data': {
            'organizations': orgs_data
        }
    }), 200


@organizations_bp.route('/<org_id>', methods=['GET'])
@token_required
@log_request
def get_organization_detail(org_id, **kwargs):
    """
    取得組織詳細資訊
    
    Query Parameters:
        - include_users: 是否包含使用者資訊 (true/false)
    
    Response:
        - organization: 組織詳細資訊
        - users: 使用者列表 (可選)
    """
    org = HrOrganization.query.get(org_id)
    
    if not org:
        return jsonify({
            'status': 'error',
            'message': '組織不存在'
        }), 404
    
    # Get query parameters
    include_users = request.args.get('include_users', 'false').lower() == 'true'
    
    response_data = {
        'organization': org.to_dict()
    }
    
    if include_users:
        response_data['users'] = [user.to_dict() for user in org.users]
    
    return jsonify({
        'status': 'success',
        'data': response_data
    }), 200
