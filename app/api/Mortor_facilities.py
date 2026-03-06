"""
Facilities API Blueprint
設施管理 API
"""
from flask import Blueprint, request, jsonify, current_app
from app.models.Mortor_organization import TOrganization
from app.models.Mortor_equipment import TEquipment
from app.auth.jwt_handler import token_required
from app.utils.decorators import log_request
from app.utils.validators import Validator

facilities_bp = Blueprint('facilities', __name__)


@facilities_bp.route('/tree', methods=['GET'])
@token_required
@log_request
def get_facility_tree(**kwargs):
    """
    取得設施樹狀結構
    
    Response:
        - facilities: 完整設施樹狀結構
    """
    # Build query for root facilities (no parent)
    query = TOrganization.query.filter_by(parentunitid=None)
    
    root_facilities = query.all()
    tree = [facility.to_dict(include_children=True) for facility in root_facilities]
    
    return jsonify({
        'status': 'success',
        'data': {
            'facilities': tree,
            'total_count': len(tree)
        }
    }), 200


@facilities_bp.route('', methods=['GET'])
@facilities_bp.route('/', methods=['GET'])
@facilities_bp.route('/list', methods=['GET'])
@token_required
@log_request
def list_facilities(**kwargs):
    """
    取得設施列表 (扁平結構)
    
    Query Parameters:
        - parent_id: 上層設施 ID (可選)
        - unittype: 設施類型 (可選)
        - page: 頁碼
        - page_size: 每頁筆數
    
    Response:
        - facilities: 設施列表
        - pagination: 分頁資訊
    """
    # Get filters
    parent_id = request.args.get('parent_id')
    unittype = request.args.get('unittype')
    
    # Validate pagination
    page, page_size, error = Validator.validate_pagination(
        request.args.get('page'),
        request.args.get('page_size'),
        current_app.config.get('MAX_ITEMS_PER_PAGE', 100)
    )
    
    if error:
        return jsonify({
            'status': 'error',
            'message': error
        }), 400
    
    # Build query
    query = TOrganization.query
    
    if parent_id:
        query = query.filter_by(parentunitid=parent_id)
    
    if unittype:
        query = query.filter_by(unittype=unittype)
    
    # Execute pagination
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    facilities_data = [facility.to_dict(include_equipment=True) for facility in pagination.items]
    
    return jsonify({
        'status': 'success',
        'data': {
            'draw': request.args.get('draw', type=int),
            'facilities': facilities_data,
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }
    }), 200


@facilities_bp.route('/<facility_id>', methods=['GET'])
@token_required
@log_request
def get_facility_detail(facility_id, **kwargs):
    """
    取得設施詳細資訊
    
    Query Parameters:
        - include_equipment: 是否包含設備資訊 (true/false)
        - include_children: 是否包含子設施 (true/false)
    
    Response:
        - facility: 設施詳細資訊
    """
    facility = TOrganization.query.get(facility_id)
    
    if not facility:
        return jsonify({
            'status': 'error',
            'message': '設施不存在'
        }), 404
    
    # Get query parameters
    include_equipment = request.args.get('include_equipment', 'false').lower() == 'true'
    include_children = request.args.get('include_children', 'false').lower() == 'true'
    
    return jsonify({
        'status': 'success',
        'data': {
            'facility': facility.to_dict(
                include_children=include_children,
                include_equipment=include_equipment
            )
        }
    }), 200


@facilities_bp.route('/<facility_id>/equipment', methods=['GET'])
@token_required
@log_request
def get_facility_equipment(facility_id, **kwargs):
    """
    取得設施的所有設備
    
    Response:
        - equipment: 設備列表
    """
    facility = TOrganization.query.get(facility_id)
    
    if not facility:
        return jsonify({
            'status': 'error',
            'message': '設施不存在'
        }), 404
    
    equipment_data = [eq.to_dict() for eq in facility.equipment]
    
    return jsonify({
        'status': 'success',
        'data': {
            'unitid': facility_id,
            'unitname': facility.unitname,
            'equipment': equipment_data,
            'total_count': len(equipment_data)
        }
    }), 200


@facilities_bp.route('/equipment/all', methods=['GET'])
@token_required
@log_request
def list_all_equipment(**kwargs):
    """
    取得所有設備列表 (用於下拉選單)
    
    Response:
        - equipment: 設備列表
    """
    equipment_list = TEquipment.query.all()
    
    data = []
    for eq in equipment_list:
        data.append({
            'id': eq.id,
            'name': eq.name,
            'unitname': eq.facility.unitname if eq.facility else None
        })
        
    return jsonify({
        'status': 'success',
        'data': {
            'equipment': data,
            'total_count': len(data)
        }
    }), 200
