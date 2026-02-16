"""
Inspection API Blueprint
巡檢查詢與報表 API
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.Mortor_inspection import TJob, InspectionResult
from app.models.Mortor_equipment import TEquipment, EquitCheckItem
from app.models.Mortor_organization import HrOrganization, TOrganization
from app.models.Mortor_abnormal import AbnormalCases
from app.models.Mortor_user import HrAccount
from app.auth.jwt_handler import token_required
from app.utils.decorators import log_request
from app.utils.validators import Validator
from datetime import datetime, date
from sqlalchemy import func

inspection_bp = Blueprint('inspection', __name__)


@inspection_bp.route('/statistics', methods=['GET'])
@token_required
@log_request
def get_dashboard_statistics(**kwargs):
    """
    取得儀表板統計資料
    """
    # Get date filter
    date_str = request.args.get('date')
    if date_str:
        if not Validator.validate_date_format(date_str):
            return jsonify({
                'status': 'error',
                'message': '日期格式錯誤'
            }), 400
        query_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    else:
        query_date = date.today()
    
    # Abnormal tracking statistics
    # is_out_of_spec: 0=已建立, 1=正常, 2=異常, 3=停機
    today_abnormal = db.session.query(func.count(InspectionResult.actid)).filter(
        InspectionResult.is_out_of_spec >= 2,
        func.date(InspectionResult.act_time) == query_date
    ).scalar() or 0
    
    today_attention = 0  # 預留
    
    accumulated_abnormal_open = AbnormalCases.query.filter_by(
        is_processed=False
    ).count()
    
    accumulated_attention_open = 0
    
    # Inspection task statistics - 基於工單日期統計
    # mdate is String in Model now? If DB stores 'YYYYMMDD', we need to match.
    # Assuming mdate store YYYYMMDD
    query_date_str = query_date.strftime('%Y%m%d')
    total_tasks_today = TJob.query.filter(TJob.mdate == query_date_str).count()
    
    completed_results_today = db.session.query(
        func.count(func.distinct(InspectionResult.actid))
    ).join(TJob, InspectionResult.actid == TJob.actid).filter(
        TJob.mdate == query_date_str,
        InspectionResult.is_out_of_spec >= 1  # 已執行（正常/異常/停機）
    ).scalar() or 0
    
    return jsonify({
        'status': 'success',
        'data': {
            'abnormal_tracking': {
                'today_abnormal': today_abnormal,
                'today_attention': today_attention,
                'accumulated_abnormal_open': accumulated_abnormal_open,
                'accumulated_attention_open': accumulated_attention_open
            },
            'inspection_tasks': {
                'total_tasks_today': total_tasks_today,
                'completed_today': completed_results_today,
            }
        }
    }), 200


@inspection_bp.route('/records', methods=['GET'])
@token_required
@log_request
def query_inspection_records(**kwargs):
    """
    查詢巡檢紀錄
    """
    current_user = kwargs.get('current_user')
    
    # Get filters
    org_id = request.args.get('org_id')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    has_abnormal_str = request.args.get('has_abnormal')
    
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
    
    # Organization filter (via Assigned User)
    if org_id:
        # act_mem_id
        query = query.join(HrAccount, TJob.act_mem_id == HrAccount.id).filter(HrAccount.organizationid == org_id)
    
    # Date range filter
    if start_date_str:
        if not Validator.validate_date_format(start_date_str):
            return jsonify({
                'status': 'error',
                'message': '開始日期格式錯誤'
            }), 400
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
    
    # Abnormal filter (is_out_of_spec >= 2)
    if has_abnormal_str:
        has_abnormal = has_abnormal_str.lower() == 'true'
        if has_abnormal:
            query = query.join(InspectionResult).filter(
                InspectionResult.is_out_of_spec >= 2
            ).distinct()
    
    # Order by date descending
    query = query.order_by(TJob.mdate.desc())
    
    # Paginate
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    # Build response
    records_data = []
    for task in pagination.items:
        has_abnormal = task.results.filter(
            InspectionResult.is_out_of_spec >= 2
        ).count() > 0
        
        record = task.to_dict() # Should return snake_case now
        record['has_abnormal'] = has_abnormal
        
        records_data.append(record)
    
    return jsonify({
        'status': 'success',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'records': records_data
        }
    }), 200


@inspection_bp.route('/records/<task_id>/details', methods=['GET'])
@token_required
@log_request
def get_inspection_record_details(task_id, **kwargs):
    """
    取得巡檢紀錄詳細資訊 (可鑽取至檢查項目)
    """
    task = TJob.query.get(task_id)
    
    if not task:
        return jsonify({
            'status': 'error',
            'message': '任務不存在'
        }), 404
    
    equipment = task.equipment
    equipment_list = []
    
    if equipment:
        items_data = []
        for item in equipment.check_items.order_by(EquitCheckItem.item_id):
            result = InspectionResult.query.filter_by(
                actid=task_id,
                item_id=item.item_id
            ).first()
            
            item_dict = item.to_dict()
            
            if result:
                item_dict['result'] = {
                    'measured_value': result.measured_value,
                    'is_out_of_spec': result.is_out_of_spec,
                    'act_time': result.act_time.isoformat() if result.act_time else None,
                    'inspector_name': result.act_mem_id, # Simplified, or fetch user name
                    'result_photo': result.result_photo
                }
            else:
                item_dict['result'] = None
            
            items_data.append(item_dict)
        
        equipment_data = equipment.to_dict()
        equipment_data['check_items'] = items_data
        equipment_list.append(equipment_data)
    
    return jsonify({
        'status': 'success',
        'data': {
            'task': task.to_dict(),
            'equipment_list': equipment_list
        }
    }), 200


@inspection_bp.route('/abnormal/tracking', methods=['GET'])
@token_required
@log_request
def query_abnormal_tracking(**kwargs):
    """
    異常追蹤查詢
    """
    # Get filters
    is_processed_str = request.args.get('is_processed')
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
    query = AbnormalCases.query.join(InspectionResult, 
        (AbnormalCases.actid == InspectionResult.actid) & 
        (AbnormalCases.item_id == InspectionResult.item_id)
    )
    
    # Status filter
    if is_processed_str:
        is_processed = is_processed_str.lower() == 'true'
        query = query.filter(AbnormalCases.is_processed == is_processed)
    
    # Date range filter
    if start_date_str:
        if not Validator.validate_date_format(start_date_str):
            return jsonify({
                'status': 'error',
                'message': '開始日期格式錯誤'
            }), 400
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        query = query.filter(func.date(InspectionResult.act_time) >= start_date)
    
    if end_date_str:
        if not Validator.validate_date_format(end_date_str):
            return jsonify({
                'status': 'error',
                'message': '結束日期格式錯誤'
            }), 400
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        query = query.filter(func.date(InspectionResult.act_time) <= end_date)
    
    # Paginate
    pagination = query.paginate(page=page, per_page=page_size, error_out=False)
    
    # Build response
    tracking_data = []
    for tracking in pagination.items:
        tracking_dict = tracking.to_dict()
        
        result = InspectionResult.query.filter_by(
            actid=tracking.actid,
            item_id=tracking.item_id
        ).first()
            
        if result:
            tracking_dict['result_info'] = {
                'act_key': result.job.act_key if result.job else None,
                'equipment_name': result.job.equipment.name if result.job and result.job.equipment else None,
                'item_name': result.check_item.item_name if result.check_item else None,
                'measured_value': result.measured_value,
                'act_time': result.act_time.isoformat() if result.act_time else None,
                'inspector_name': result.act_mem_id
            }
            
            # Derive abnormal_type
            if result.is_out_of_spec == 2:
                tracking_dict['abnormal_type'] = '異常'
            elif result.is_out_of_spec == 3:
                tracking_dict['abnormal_type'] = '注意' # Map 3 (Machine Down/Other) to Attention for now
            else:
                tracking_dict['abnormal_type'] = '異常' # Default to Abnormal if processed but no specific match
        else:
             tracking_dict['abnormal_type'] = '異常'
        
        tracking_data.append(tracking_dict)
    
    return jsonify({
        'status': 'success',
        'data': {
            'total': pagination.total,
            'page': page,
            'page_size': page_size,
            'tracking_records': tracking_data
        }
    }), 200


@inspection_bp.route('/progress', methods=['GET'])
@token_required
@log_request
def query_inspection_progress(**kwargs):
    """
    巡檢進度查詢 - 含統計卡片資料
    """
    try:
        org_id = request.args.get('org_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        query = TJob.query.join(
            TEquipment, TJob.equipmentid == TEquipment.id, isouter=True
        )

        if org_id:
            query = query.filter(TEquipment.unitid == org_id)
        if start_date:
            query = query.filter(TJob.mdate >= start_date.replace('-', ''))
        if end_date:
            query = query.filter(TJob.mdate <= end_date.replace('-', ''))

        all_jobs = query.all()

        # 統計各狀態
        stats = {
            'not_assigned': 0,
            'not_completed': 0,
            'in_progress': 0,
            'completed': 0,
            'other': 0
        }
        for job in all_jobs:
            job_data = job.to_dict()
            status = job_data.get('status', '')
            if status == '未派工':
                stats['not_assigned'] += 1
            elif status == '未完成':
                stats['not_completed'] += 1
            elif status == '執行中':
                stats['in_progress'] += 1
            elif status == '已完成':
                stats['completed'] += 1
            else:
                stats['other'] += 1

        # 分頁查詢
        total = len(all_jobs)
        paginated_jobs = all_jobs[(page - 1) * page_size: page * page_size]

        records = []
        for job in paginated_jobs:
            job_dict = job.to_dict()
            has_abnormal = AbnormalCases.query.filter_by(actid=job.actid).count() > 0
            job_dict['has_abnormal'] = has_abnormal
            records.append(job_dict)

        return jsonify({
            'status': 'success',
            'data': {
                'statistics': stats,
                'records': records,
                'pagination': {
                    'total': total,
                    'page': page,
                    'page_size': page_size,
                    'total_pages': (total + page_size - 1) // page_size
                }
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'Inspection progress error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'查詢失敗: {str(e)}'
        }), 500


@inspection_bp.route('/trend/<equipmentid>', methods=['GET'])
@token_required
@log_request
def query_equipment_trend(equipmentid, **kwargs):
    """
    抄表趨勢圖 - 設備歷史量測資料
    """
    try:
        from app.models.Mortor_equipment import EquitCheckItem

        # 取得設備的所有檢查項目
        check_items = EquitCheckItem.query.filter_by(equipmentid=equipmentid).all()

        # 取得歷史量測結果
        results = InspectionResult.query.filter_by(
            equipmentid=equipmentid
        ).order_by(InspectionResult.act_time.asc()).all()

        # 整理時間軸
        dates = []
        date_set = set()
        for r in results:
            if r.act_time:
                date_str = r.act_time.strftime('%Y-%m-%d')
                if date_str not in date_set:
                    dates.append(date_str)
                    date_set.add(date_str)

        # 整理每個檢查項目的歷史數據
        items_data = []
        for item in check_items:
            item_results = [r for r in results if r.item_id == item.item_id]
            values = []
            for d in dates:
                # 找到該日期的量測值
                val = None
                for r in item_results:
                    if r.act_time and r.act_time.strftime('%Y-%m-%d') == d:
                        try:
                            val = float(r.measured_value) if r.measured_value else None
                        except (ValueError, TypeError):
                            val = None
                        break
                values.append(val)

            items_data.append({
                'item_name': item.item_name,
                'values': values
            })

        # 上下限
        limits = {}
        if check_items:
            limits = {
                'max_v': check_items[0].max_v,
                'min_v': check_items[0].min_v
            }

        # 明細記錄
        records = []
        for r in results:
            r_dict = r.to_dict()
            if r.check_item:
                r_dict['max_v'] = r.check_item.max_v
                r_dict['min_v'] = r.check_item.min_v
                r_dict['unit'] = r.check_item.unit
            records.append(r_dict)

        return jsonify({
            'status': 'success',
            'data': {
                'dates': dates,
                'items': items_data,
                'limits': limits,
                'records': records
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'Equipment trend error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'查詢失敗: {str(e)}'
        }), 500


@inspection_bp.route('/comparison', methods=['GET'])
@token_required
@log_request
def query_equipment_comparison(**kwargs):
    """
    同性質設備趨勢比較
    """
    try:
        from app.models.Mortor_equipment import EquitCheckItem

        org_id = request.args.get('org_id')
        group = request.args.get('group')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 查詢設備
        equip_query = TEquipment.query
        if org_id:
            equip_query = equip_query.filter(TEquipment.unitid == org_id)

        # 透過 jobs 篩選 group
        if group:
            equip_ids_with_group = db.session.query(TJob.equipmentid).filter(
                TJob.group == group
            ).distinct().all()
            equip_ids = [e[0] for e in equip_ids_with_group]
            equip_query = equip_query.filter(TEquipment.id.in_(equip_ids))

        equipments = equip_query.all()

        equipment_list = []
        for equip in equipments:
            # 量測結果查詢
            result_query = InspectionResult.query.filter_by(equipmentid=equip.id)
            if start_date:
                result_query = result_query.filter(
                    InspectionResult.act_time >= datetime.strptime(start_date, '%Y-%m-%d')
                )
            if end_date:
                result_query = result_query.filter(
                    InspectionResult.act_time <= datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S')
                )

            results = result_query.all()

            # 計算平均值
            numeric_values = []
            for r in results:
                try:
                    if r.measured_value:
                        numeric_values.append(float(r.measured_value))
                except (ValueError, TypeError):
                    pass

            avg_value = sum(numeric_values) / len(numeric_values) if numeric_values else None

            # 異常次數
            abnormal_count = sum(1 for r in results if r.is_out_of_spec and r.is_out_of_spec > 0)

            # 最近量測日期
            last_date = None
            if results:
                last_result = max(results, key=lambda r: r.act_time or datetime.min)
                if last_result.act_time:
                    last_date = last_result.act_time.strftime('%Y-%m-%d')

            # 組織名稱
            org_name = None
            if equip.unitid:
                org = TOrganization.query.get(equip.unitid)
                if org:
                    org_name = org.name

            # 設備的 group
            equip_group = None
            job = TJob.query.filter_by(equipmentid=equip.id).first()
            if job:
                equip_group = job.group

            equipment_list.append({
                'id': equip.id,
                'name': equip.name,
                'org_name': org_name,
                'group': equip_group,
                'last_inspection_date': last_date,
                'avg_value': avg_value,
                'abnormal_count': abnormal_count
            })

        return jsonify({
            'status': 'success',
            'data': {
                'equipment_list': equipment_list
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'Equipment comparison error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'查詢失敗: {str(e)}'
        }), 500
