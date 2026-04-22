"""
Organizations API Blueprint
組織管理 API

【架構原則】全系統以 t_organization (設施單位) 為組織主體，
HrOrganization (人事組織) 僅在人員帳號關聯時使用，
透過 /hr/* 子路由存取。
"""
from flask import Blueprint, request, jsonify
from app.models.Mortor_organization import TOrganization, HrOrganization
from app.auth.jwt_handler import token_required
from app.utils.decorators import log_request

organizations_bp = Blueprint('organizations', __name__)


# ==============================================================================
# 設施組織樹（t_organization）— 主要組織架構，供設備搜尋與巡檢查詢使用
# ==============================================================================

def _t_org_to_frontend(org, include_children: bool = False) -> dict:
    """
    將 TOrganization 物件轉換為前端期待的統一格式。
    前端 jsTree 等元件期待 id / name / parentid 欄位。
    """
    data = {
        'id': org.unitid,
        'name': org.unitname,
        'parentid': org.parentunitid,
        'unittype': org.unittype,
    }
    if include_children:
        data['children'] = [
            _t_org_to_frontend(child, include_children=True)
            for child in org.children
        ]
    return data


@organizations_bp.route('/tree', methods=['GET'])
@token_required
@log_request
def get_organization_tree(**kwargs):
    """
    取得設施組織樹狀結構（t_organization）
    用於巡檢查詢、AIMS工單查詢、異常追蹤等所有需要組織篩選的頁面。

    Response:
        - organizations: 完整設施組織樹狀結構
    """
    root_orgs = TOrganization.query.filter(
        (TOrganization.parentunitid == None) |  # noqa: E711
        (TOrganization.parentunitid == '')
    ).all()
    tree = [_t_org_to_frontend(org, include_children=True) for org in root_orgs]

    return jsonify({
        'status': 'success',
        'data': {
            'organizations': tree
        }
    }), 200


@organizations_bp.route('', methods=['GET'])
@organizations_bp.route('/', methods=['GET'])
@organizations_bp.route('/list', methods=['GET'])
@token_required
@log_request
def list_organizations(**kwargs):
    """
    取得設施組織列表（扁平結構，t_organization）

    Query Parameters:
        - parent_id: 上層設施單位 ID (可選)

    Response:
        - organizations: 設施組織列表
    """
    parent_id = request.args.get('parent_id')

    query = TOrganization.query
    if parent_id:
        query = query.filter_by(parentunitid=parent_id)

    organizations = query.all()
    orgs_data = [_t_org_to_frontend(org) for org in organizations]

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
    取得設施組織詳細資訊（t_organization）

    Response:
        - organization: 設施組織詳細資訊
    """
    org = TOrganization.query.get(org_id)

    if not org:
        return jsonify({
            'status': 'error',
            'message': '組織不存在'
        }), 404

    include_children = request.args.get('include_children', 'false').lower() == 'true'
    include_equipment = request.args.get('include_equipment', 'false').lower() == 'true'

    data = _t_org_to_frontend(org, include_children=include_children)
    if include_equipment:
        data['equipment_count'] = org.equipment.count()

    return jsonify({
        'status': 'success',
        'data': {
            'organization': data
        }
    }), 200


# ==============================================================================
# 人事組織（hr_organization）— 僅供人員帳號關聯使用，路由前綴 /hr
# ==============================================================================

@organizations_bp.route('/hr/tree', methods=['GET'])
@token_required
@log_request
def get_hr_organization_tree(**kwargs):
    """
    取得人事組織樹狀結構（hr_organization）
    僅供使用者管理頁面顯示人員所屬部門使用。

    Response:
        - organizations: 完整人事組織樹狀結構
    """
    root_orgs = HrOrganization.query.filter(
        (HrOrganization.parentid == None) |  # noqa: E711
        (HrOrganization.parentid == '')
    ).all()
    tree = [org.to_dict(include_children=True) for org in root_orgs]

    return jsonify({
        'status': 'success',
        'data': {
            'organizations': tree
        }
    }), 200


@organizations_bp.route('/hr/list', methods=['GET'])
@token_required
@log_request
def list_hr_organizations(**kwargs):
    """
    取得人事組織列表（扁平結構，hr_organization）

    Query Parameters:
        - parent_id: 上層部門 ID (可選)
    """
    parent_id = request.args.get('parent_id')

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


@organizations_bp.route('/hr/<org_id>', methods=['GET'])
@token_required
@log_request
def get_hr_organization_detail(org_id, **kwargs):
    """
    取得人事組織詳細資訊（hr_organization）

    Query Parameters:
        - include_users: 是否包含使用者資訊 (true/false)
    """
    org = HrOrganization.query.get(org_id)

    if not org:
        return jsonify({
            'status': 'error',
            'message': '人事組織不存在'
        }), 404

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
