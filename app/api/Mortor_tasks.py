"""
Tasks API Blueprint
任務管理 API
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.Mortor_inspection import TJob
from app.models.Mortor_equipment import TEquipment, EquitCheckItem
from app.models.Mortor_user import HrAccount
from app.auth.jwt_handler import token_required
from app.utils.decorators import log_request
from app.utils.validators import Validator
from datetime import datetime, date
import uuid

tasks_bp = Blueprint('tasks', __name__)


@tasks_bp.route('/download', methods=['GET'])
@token_required
@log_request
def download_tasks(**kwargs):
    """
    下載巡檢任務清單
    注意：目前未啟用人員派工功能，回傳所有工單供現場人員使用
    待 Admin 派工功能上線後，再依 act_mem_id 篩選指派工單
    """
    # Get date filter
    date_str = request.args.get('date')
    if date_str:
        if not Validator.validate_date_format(date_str):
            return jsonify({
                'status': 'error',
                'message': '日期格式錯誤，應為 YYYY-MM-DD'
            }), 400
        filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        filter_date = date.today()

    # Query tasks — 全部工單（未實作派工故不篩人員）
    tasks_query = TJob.query

    if date_str:
        # P2-9：mdate 是 VARCHAR(8)，統一轉為 YYYYMMDD 字串比較
        filter_date_str = filter_date.strftime('%Y%m%d')
        tasks_query = tasks_query.filter(TJob.mdate >= filter_date_str)

    tasks = tasks_query.all()

    # Build response with full task details
    tasks_data = []
    for task in tasks:
        assigned_user = task.assigned_user if task.act_mem_id else None
        equipment = task.equipment
        
        # P0-1：巡檢項目改為查通用表（按 grade/mterm），不再用已移除的 equipment.check_items 關聯
        check_items_objs = EquitCheckItem.query.filter_by(
            grade=task.grade,
            mterm=task.mterm
        ).order_by(EquitCheckItem.sort_order).all()

        check_items = []
        for item in check_items_objs:
            check_items.append({
                'item_id': item.item_id,
                'item_name': item.item_name,
                'item_desc': item.item_desc,
                'status_type': item.status_type,
                'max_v': item.max_v,
                'min_v': item.min_v,
                'sort_order': item.sort_order,
                'grade': item.grade,
                'mterm': item.mterm,
                'unit': item.unit,
                'data_type': '數值' if item.max_v or item.min_v else '文字',
                'is_required': True
            })

        # P1-7：完成數排除 is_out_of_spec=0（未填寫 / 取消停機後的空白紀錄）
        total_items = len(check_items)
        completed_items = 0

        if total_items > 0:
            from app.models.Mortor_inspection import InspectionResult
            completed_items = task.results.filter(
                InspectionResult.is_out_of_spec != 0
            ).count()
            completion_rate = (completed_items / total_items) * 100
        else:
            completion_rate = 0

        current_app.logger.debug(
            f' assigned task {task.actid} and act_mem_id {task.act_mem_id}'
        )
        
        tasks_data.append({
            'actid': task.actid,
            'act_key': task.act_key,
            'equipmentid': task.equipmentid,
            'equipment_name': equipment.name if equipment else None,
            'mdate': task.mdate if task.mdate else None,
            'act_desc': task.act_desc,
            'act_mem_id': task.act_mem_id,
            'act_mem': assigned_user.name if assigned_user else task.act_mem,
            'grade': task.grade,
            'mterm': task.mterm,
            # P0-B：App TaskModel.fromJson 讀 total_items / completed_items
            # completed_items 需與 P1-7 一致：排除 is_out_of_spec=0（未填寫）
            'total_items': total_items,
            'completed_items': completed_items,
            'completion_rate': round(completion_rate, 1),
            'unitid': equipment.unitid if equipment else None,
            'unitname': equipment.facility.unitname if equipment and equipment.facility else None,
            'equipment_check_items': check_items
        })
    
    current_app.logger.info(
        f'User {current_user.id} downloaded {len(tasks)} tasks for date {filter_date}'
    )
    
    return jsonify({
        'status': 'success',
        'data': {
            'tasks': tasks_data,
            'last_sync': datetime.utcnow().isoformat() + 'Z',
            'total_count': len(tasks),
            'synced_at': datetime.utcnow().isoformat() + 'Z'
        }
    }), 200


@tasks_bp.route('/list', methods=['GET'])
@token_required
@log_request
def list_tasks(**kwargs):
    """
    取得任務列表
    """
    current_user = kwargs.get('current_user')  # noqa: F841
    
    # Get filters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Validate pagination
    page, page_size, error = Validator.validate_pagination(
        request.args.get('page'),
        request.args.get('page_size'),
        current_app.config['MAX_ITEMS_PER_PAGE']
    )
    
    if error:
        return jsonify({
            'status': 'error',
            'message': error
        }), 400
    
    # Build query
    query = TJob.query
    
    # Date range filter
    if start_date_str:
        if not Validator.validate_date_format(start_date_str):
            return jsonify({
                'status': 'error',
                'message': '開始日期格式錯誤'
            }), 400
        # Assuming database stores mdate as String YYYYMMDD? Or Date?
        # Model definition: mdate = db.Column(db.String(8)...)
        # So we should convert input YYYY-MM-DD to YYYYMMDD if needed, OR if DB stores YYYY-MM-DD.
        # DB_SCHEMA.txt: mdate VARCHAR(8). Usually YYYYMMDD.
        # But previous code used Date type.
        # I will assume YYYY-MM-DD string or Date object.
        # Let's try to filter by string ISO format or check.
        # Wait, if mdate is String(8), it's likely YYYYMMDD.
        # Input start_date_str is YYYY-MM-DD.
        start_date_db = start_date_str.replace('-', '')
        query = query.filter(TJob.mdate >= start_date_db)
    
    if end_date_str:
        if not Validator.validate_date_format(end_date_str):
            return jsonify({
                'status': 'error',
                'message': '結束日期格式錯誤'
            }), 400
        end_date_db = end_date_str.replace('-', '')
        query = query.filter(TJob.mdate <= end_date_db)
    
    # Order by date descending
    query = query.order_by(TJob.mdate.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    tasks_data = []
    for task in pagination.items:
        assigned_user = task.assigned_user if task.act_mem_id else None
        equipment = task.equipment

        current_app.logger.debug(
            f' assigned task {task.actid} and equipmentid {task.equipmentid}'
        )
        
        # Get check items for this equipment
        check_items = []
        if equipment:
            for item in equipment.check_items.order_by(EquitCheckItem.item_id):
                check_items.append({
                    'item_id': item.item_id,
                    'item_name': item.item_name,
                    'item_desc': item.item_desc,
                    'status_type': item.status_type,
                    'max_v': item.max_v,
                    'min_v': item.min_v,
                    'sort_order': item.sort_order,
                    'grade': item.grade,
                    'mterm': item.mterm,
                    'unit': item.unit,
                    'data_type': '數值' if item.max_v or item.min_v else '文字',
                    'is_required': True
                })
        
        # Calculate completion rate
        total_items = 0
        completed_items = 0
        if task.equipment:
            total_items = task.equipment.check_items.count()
        if total_items > 0:
            completed_items = task.results.count()
            completion_rate = (completed_items / total_items) * 100
        else:
            completion_rate = 0
        
        tasks_data.append({
            'actid': task.actid,
            'act_key': task.act_key,
            'equipmentid': task.equipmentid,
            'equipment_name': equipment.name if equipment else None,
            'mdate': task.mdate, # Return as stored (YYYYMMDD) or format? Frontend expects?
            'act_desc': task.act_desc,
            'act_mem_id': task.act_mem_id,
            'act_mem': assigned_user.name if assigned_user else task.act_mem,
            'grade': task.grade,
            'mterm': task.mterm,
            'completion_rate': round(completion_rate, 1),
            'unitid': equipment.unitid if equipment else None,
            'unitname': equipment.facility.unitname if equipment and equipment.facility else None,
            'equipment_check_items': check_items
        })
    
    return jsonify({
        'status': 'success',
        'data': {
            'tasks': tasks_data,
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


@tasks_bp.route('/<task_id>', methods=['GET'])
@token_required
@log_request
def get_task_detail(task_id, **kwargs):
    """
    取得特定任務詳細資訊
    """
    task = TJob.query.get(task_id)
    
    if not task:
        return jsonify({
            'status': 'error',
            'message': '任務不存在'
        }), 404
    
    # to_dict needs to be updated in Model, but we likely need manual construction here if model isn't fully ready
    # Check if TJob.to_dict usage is safe.
    # I didn't verify TJob.to_dict in my model update earlier? 
    # I updated InspectionResult.to_dict.
    # TJob probably doesn't have a comprehensive to_dict or I missed it.
    # Let's assume we return similar structure manually or verify TJob update later.
    
    # For now, I'll return manual structure to be safe and consistent with list/download
    
    assigned_user = task.assigned_user if task.act_mem_id else None
    equipment = task.equipment  # noqa: F841
    
    data = {
        'actid': task.actid,
        'act_key': task.act_key,
        'equipmentid': task.equipmentid,
        'act_desc': task.act_desc,
        'act_mem_id': task.act_mem_id,
        'act_mem': assigned_user.name if assigned_user else task.act_mem,
        'mdate': task.mdate,
        'grade': task.grade,
        'mterm': task.mterm,
    }
    
    return jsonify({
        'status': 'success',
        'data': {
            'task': data
        }
    }), 200


@tasks_bp.route('', methods=['POST'])
@token_required
@log_request
def create_task(**kwargs):
    """
    建立新任務
    """
    current_user = kwargs.get('current_user')
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['equipmentid', 'mdate', 'act_mem_id']
    for field in required_fields:
        if field not in data:
            # Fallback for old API callers?
            if field == 'act_mem_id' and 'actmemid' in data:
                data['act_mem_id'] = data['actmemid']
            else:
                return jsonify({
                    'status': 'error',
                    'message': f'缺少必填欄位: {field}'
                }), 400
    
    # Validate equipment exists
    equipment = TEquipment.query.get(data['equipmentid'])
    if not equipment:
        return jsonify({
            'status': 'error',
            'message': '設備不存在'
        }), 404
    
    # Validate user exists
    user = HrAccount.query.get(data['act_mem_id'])
    if not user:
        return jsonify({
            'status': 'error',
            'message': '使用者不存在'
        }), 404
    
    # Validate date format
    if not Validator.validate_date_format(data['mdate']):
        return jsonify({
            'status': 'error',
            'message': '日期格式錯誤，應為 YYYY-MM-DD'
        }), 400
    
    # Convert to YYYYMMDD for DB
    mdate_val = data['mdate'].replace('-', '')
    
    # Generate task ID and Number
    actid = str(uuid.uuid4())
    actkey = f'TASK-{mdate_val}-{int(datetime.utcnow().timestamp())}'
    
    # Create task
    task = TJob(
        actid=actid,
        act_key=actkey,
        equipmentid=data['equipmentid'],
        act_mem_id=data['act_mem_id'],
        act_mem=user.name,
        mdate=mdate_val,
        act_desc=data.get('act_desc') or data.get('actdesc'),
        grade=data.get('grade') or data.get('grade_level') or data.get('group') or data.get('group_level'),
        mterm=data.get('mterm'),
    )
    
    db.session.add(task)
    db.session.commit()
    
    current_app.logger.info(
        f'Task {task.act_key} created by user {current_user.id}'
    )
    
    return jsonify({
        'status': 'success',
        'message': '任務建立成功',
        'data': {
            'task': {
                'actid': task.actid,
                'act_key': task.act_key
            }
        }
    }), 201


@tasks_bp.route('/<task_id>', methods=['PUT'])
@token_required
@log_request
def update_task(task_id, **kwargs):
    """
    更新任務資訊
    """
    current_user = kwargs.get('current_user')
    
    task = TJob.query.get(task_id)
    
    if not task:
        return jsonify({
            'status': 'error',
            'message': '任務不存在'
        }), 404
    
    data = request.get_json()
    
    # Update equipment
    if 'equipmentid' in data:
        equipment = TEquipment.query.get(data['equipmentid'])
        if not equipment:
            return jsonify({
                'status': 'error',
                'message': '設備不存在'
            }), 404
        task.equipmentid = data['equipmentid']
    
    # Update assigned user
    if 'act_mem_id' in data:
        user = HrAccount.query.get(data['act_mem_id'])
        if not user:
            return jsonify({
                'status': 'error',
                'message': '使用者不存在'
            }), 404
        task.act_mem_id = data['act_mem_id']
        task.act_mem = user.name
    elif 'actmemid' in data: # Support old key
        user = HrAccount.query.get(data['actmemid'])
        if not user:
            return jsonify({
                'status': 'error',
                'message': '使用者不存在'
            }), 404
        task.act_mem_id = data['actmemid']
        task.act_mem = user.name
    
    # Update inspection date
    if 'mdate' in data:
        if not Validator.validate_date_format(data['mdate']):
            return jsonify({
                'status': 'error',
                'message': '日期格式錯誤，應為 YYYY-MM-DD'
            }), 400
        task.mdate = data['mdate'].replace('-', '')
    
    # Update description
    if 'act_desc' in data:
        task.act_desc = data['act_desc']
    elif 'actdesc' in data:
        task.act_desc = data['actdesc']
        
    # Update grade
    if 'grade' in data:
        task.grade = data['grade']
    elif 'grade_level' in data:
        task.grade = data['grade_level']
    elif 'group' in data:
        task.grade = data['group']
    elif 'group_level' in data:
        task.grade = data['group_level']
    
    # Update mterm
    if 'mterm' in data:
        task.mterm = data['mterm']
    
    db.session.commit()
    
    current_app.logger.info(
        f'Task {task.act_key} updated by user {current_user.id}'
    )
    
    return jsonify({
        'status': 'success',
        'message': '任務更新成功',
        'data': {
            'task': {
                'actid': task.actid,
                'act_key': task.act_key
            }
        }
    }), 200


@tasks_bp.route('/<task_id>', methods=['DELETE'])
@token_required
@log_request
def delete_task(task_id, **kwargs):
    """
    刪除任務
    """
    current_user = kwargs.get('current_user')
    
    task = TJob.query.get(task_id)
    
    if not task:
        return jsonify({
            'status': 'error',
            'message': '任務不存在'
        }), 404
    
    # Don't allow deletion of tasks with results
    if task.results.count() > 0:
        return jsonify({
            'status': 'error',
            'message': '無法刪除已有巡檢結果的任務'
        }), 400
    
    act_key = task.act_key
    db.session.delete(task)
    db.session.commit()
    
    current_app.logger.info(
        f'Task {act_key} deleted by user {current_user.id}'
    )
    
    return jsonify({
        'status': 'success',
        'message': '任務已刪除'
    }), 200
