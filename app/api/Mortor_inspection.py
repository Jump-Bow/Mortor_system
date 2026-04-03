"""
Inspection API Blueprint
巡檢查詢與報表 API
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.Mortor_inspection import TJob, InspectionResult
from app.models.Mortor_equipment import TEquipment, EquitCheckItem
from app.models.Mortor_abnormal import AbnormalCases
from app.models.Mortor_organization import TOrganization
from app.models.Mortor_user import HrAccount
from app.auth.jwt_handler import token_required
from app.utils.decorators import log_request, web_or_api_required
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
    current_user = kwargs.get('current_user')  # noqa: F841
    
    # Get filters
    org_id = request.args.get('org_id')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    has_abnormal_str = request.args.get('has_abnormal')
    grade = request.args.get('group')  # 修正：前端傳送的參數名為 group
    mterm = request.args.get('mterm')  # 保養週期 (1M/3M/6M/1Y)
    equipment_id = request.args.get('equipment_id')  # 設備篩選
    act_key = request.args.get('act_key')  # 工單號碼
    status_filter = request.args.get('status')  # 工單狀態
    
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
    
    # Grade filter (馬達類別)
    if grade:
        query = query.filter(TJob.grade == grade)
    
    # Mterm filter (保養週期)
    if mterm:
        query = query.filter(TJob.mterm == mterm)
    
    # Equipment filter
    if equipment_id:
        query = query.filter(TJob.equipmentid == equipment_id)
    
    # Act key filter (工單號碼模糊搜尋)
    if act_key:
        query = query.filter(TJob.act_key.ilike(f'%{act_key}%'))
    
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
        # 原本 equipment.check_items 關聯已移除，需改為查詢通用檢查項目
        # 並根據 task.grade 和 task.mterm 進行過濾
        # from app.models.Mortor_equipment import EquitCheckItem
        
        # 1. 找出該任務應該做的項目 (依規格)
        spec_items = EquitCheckItem.query.filter_by(
            grade=task.grade,
            mterm=task.mterm
        ).order_by(EquitCheckItem.sort_order).all()
        
        for item in spec_items:
            result = InspectionResult.query.filter_by(
                actid=task_id,
                item_id=item.item_id
            ).first()
            
            item_dict = item.to_dict()
            
            if result:
                # P1-8：取真實姓名，不再回傳 ID
                inspector = HrAccount.query.get(result.act_mem_id) if result.act_mem_id else None
                item_dict['result'] = {
                    'measured_value': result.measured_value,
                    'is_out_of_spec': result.is_out_of_spec,
                    'act_time': result.act_time.isoformat() if result.act_time else None,
                    'inspector_name': inspector.name if inspector else result.act_mem_id,
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
    case_status = request.args.get('case_status')  # 前端傳遞: 未結案/已結案
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    org_id = request.args.get('org_id')  # 組織篩選
    equipment_id = request.args.get('equipment_id')  # 設備篩選
    grade = request.args.get('group')  # 修正：前端傳送的參數名為 group
    mterm = request.args.get('mterm')  # 保養週期 (1M/3M/6M/1Y)
    abnormal_type = request.args.get('abnormal_type')  # 異常類型
    
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
    ).join(TJob, AbnormalCases.actid == TJob.actid
    ).join(TEquipment, TJob.equipmentid == TEquipment.id, isouter=True)
    
    # Status filter (支援 is_processed 和 case_status 兩種傳參方式)
    if case_status:
        if case_status == '未結案':
            query = query.filter(AbnormalCases.is_processed == False)
        elif case_status == '已結案':
            query = query.filter(AbnormalCases.is_processed == True)
    elif is_processed_str:
        is_processed = is_processed_str.lower() == 'true'
        query = query.filter(AbnormalCases.is_processed == is_processed)
    
    # Organization filter
    if org_id:
        query = query.join(HrAccount, TJob.act_mem_id == HrAccount.id).filter(HrAccount.organizationid == org_id)
    
    # Equipment filter
    if equipment_id:
        query = query.filter(AbnormalCases.equipmentid == equipment_id)
    
    # Grade filter (馬達類別)
    if grade:
        query = query.filter(TJob.grade == grade)
    
    # Mterm filter (保養週期)
    if mterm:
        query = query.filter(TJob.mterm == mterm)
    
    # Abnormal type filter
    if abnormal_type:
        if abnormal_type == '異常':
            query = query.filter(InspectionResult.is_out_of_spec == 2)
        elif abnormal_type == '注意':
            query = query.filter(InspectionResult.is_out_of_spec == 3)
    
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
            
            # P1-6：修正語意— is_out_of_spec=3 是停機，不是「注意」
            if result.is_out_of_spec == 2:
                tracking_dict['abnormal_type'] = '異常'
            elif result.is_out_of_spec == 3:
                tracking_dict['abnormal_type'] = '停機'
            else:
                tracking_dict['abnormal_type'] = '異常'  # 預設
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
        grade = request.args.get('group')  # 修正：前端傳送的參數名為 group
        mterm = request.args.get('mterm')  # 保養週期 (1M/3M/6M/1Y)
        status_filter = request.args.get('status')  # 工單狀態
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        query = TJob.query.join(
            TEquipment, TJob.equipmentid == TEquipment.id, isouter=True
        )

        if org_id:
            query = query.join(HrAccount, TJob.act_mem_id == HrAccount.id).filter(HrAccount.organizationid == org_id)
        if start_date:
            query = query.filter(TJob.mdate >= start_date.replace('-', ''))
        if end_date:
            query = query.filter(TJob.mdate <= end_date.replace('-', ''))
        if grade:
            query = query.filter(TJob.grade == grade)
        if mterm:
            query = query.filter(TJob.mterm == mterm)

        all_jobs = query.all()

        # 統計各狀態 & 套用 status_filter
        stats = {
            'not_assigned': 0,
            'not_completed': 0,
            'in_progress': 0,
            'completed': 0,
            'other': 0
        }
        filtered_jobs = []
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
            
            # 狀態篩選（status 為計算欄位，需於此處過濾）
            if status_filter and status != status_filter:
                continue
            filtered_jobs.append(job)

        # 分頁查詢
        total = len(filtered_jobs)
        paginated_jobs = filtered_jobs[(page - 1) * page_size: page * page_size]

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

        # 取得所有通用檢查項目 (不再綁定特定設備)
        check_items = EquitCheckItem.query.all()

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
                'unit': item.unit,
                'max_v': float(item.max_v) if item.max_v else None,
                'min_v': float(item.min_v) if item.min_v else None,
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

        org_id = request.args.get('org_id')
        grade = request.args.get('grade') # Renamed from group
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 查詢設備
        equip_query = TEquipment.query
        if org_id:
            equip_query = equip_query.filter(TEquipment.unitid == org_id)

        # 透過 jobs 篩選 grade
        if grade:
            equip_ids_with_group = db.session.query(TJob.equipmentid).filter(
                TJob.grade == grade
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
                    org_name = org.unitname

            # 設備的 grade
            equip_grade = None
            job = TJob.query.filter_by(equipmentid=equip.id).first()
            if job:
                equip_grade = job.grade

            equipment_list.append({
                'id': equip.id,
                'name': equip.name,
                'org_name': org_name,
                'grade': equip_grade, # Renamed
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


@inspection_bp.route('/calendar', methods=['GET'])
@web_or_api_required
@log_request
def get_inspection_calendar(**kwargs):
    """
    巡檢行事曆資料
    參數: year (預設今年), month (預設今月)
    回傳: 每日工單統計 (total / completed / abnormal)
    """
    try:
        year = request.args.get('year', type=int, default=date.today().year)
        month = request.args.get('month', type=int, default=date.today().month)

        if not (1 <= month <= 12):
            return jsonify({'status': 'error', 'message': '月份格式錯誤（1-12）'}), 400

        # 計算該月起訖日期字串（mdate 格式 YYYYMMDD）
        month_start = f"{year}{month:02d}01"
        # 計算月末日期
        import calendar as cal
        last_day = cal.monthrange(year, month)[1]
        month_end = f"{year}{month:02d}{last_day:02d}"

        # 查詢該月所有工單
        jobs = TJob.query.filter(
            TJob.mdate >= month_start,
            TJob.mdate <= month_end
        ).all()

        # 每日統計 dict: {date_str: {total, completed, abnormal}}
        daily_stats = {}
        for job in jobs:
            # mdate 格式 YYYYMMDD → 轉為 YYYY-MM-DD
            if job.mdate and len(job.mdate) == 8:
                d_str = f"{job.mdate[:4]}-{job.mdate[4:6]}-{job.mdate[6:8]}"
            else:
                continue

            if d_str not in daily_stats:
                daily_stats[d_str] = {'total': 0, 'completed': 0, 'abnormal': 0}

            daily_stats[d_str]['total'] += 1

            # 判斷是否完成：使用 TJob.to_dict 的 status 計算
            from app.models.Mortor_equipment import EquitCheckItem
            total_items = EquitCheckItem.query.filter_by(
                grade=job.grade, mterm=job.mterm
            ).count()
            # P1-5：完成數不計入 is_out_of_spec=0（未填寫的空白紀錄）
            completed_items = job.results.filter(
                InspectionResult.is_out_of_spec != 0
            ).count()
            if total_items > 0 and completed_items >= total_items:
                daily_stats[d_str]['completed'] += 1

            # 判斷是否有異常
            has_abnormal = job.results.filter(
                InspectionResult.is_out_of_spec >= 2
            ).count() > 0
            if has_abnormal:
                daily_stats[d_str]['abnormal'] += 1

        # 轉為事件列表（FullCalendar 格式）
        events = []
        for d_str, stats in sorted(daily_stats.items()):
            events.append({
                'date': d_str,
                'total': stats['total'],
                'completed': stats['completed'],
                'abnormal': stats['abnormal']
            })

        return jsonify({
            'status': 'success',
            'data': {
                'year': year,
                'month': month,
                'events': events
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'Calendar query error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'查詢失敗: {str(e)}'
        }), 500


@inspection_bp.route('/comparison', methods=['GET'])
@web_or_api_required
@log_request
def get_inspection_comparison(**kwargs):
    """
    同性質設備趨勢比較
    依據馬達類別(group=grade)、組織、日期範圍，回傳每台設備的統計摘要
    """
    try:
        org_id = request.args.get('org_id')
        group = request.args.get('group')        # 對應 TJob.grade (A/B/C/D)
        start_date = request.args.get('start_date', '').replace('-', '')
        end_date = request.args.get('end_date', '').replace('-', '')

        # 查詢有巡檢記錄的工單
        query = TJob.query.join(TEquipment, TJob.equipmentid == TEquipment.id, isouter=True)

        if org_id:
            query = query.filter(TEquipment.unitid == org_id)
        if group:
            query = query.filter(TJob.grade == group)
        if start_date:
            query = query.filter(TJob.mdate >= start_date)
        if end_date:
            query = query.filter(TJob.mdate <= end_date)

        jobs = query.all()

        # 依設備彙整統計
        equip_stats = {}
        for job in jobs:
            eid = job.equipmentid
            if eid not in equip_stats:
                equip = TEquipment.query.get(eid)
                org_name = None
                if equip and equip.unitid:
                    org = TOrganization.query.get(equip.unitid)
                    org_name = org.unitname if org else None
                equip_stats[eid] = {
                    'id': eid,
                    'name': equip.name if equip else eid,
                    'org_name': org_name,
                    'grade': job.grade,
                    'last_inspection_date': None,
                    'total_measurements': 0,
                    'abnormal_count': 0,
                    'numeric_values': []
                }

            stat = equip_stats[eid]
            # 最近巡檢日期
            if stat['last_inspection_date'] is None or job.mdate > stat['last_inspection_date']:
                stat['last_inspection_date'] = job.mdate

            # 統計該工單的量測結果
            results = InspectionResult.query.filter_by(actid=job.actid).all()
            for r in results:
                stat['total_measurements'] += 1
                if r.is_out_of_spec and r.is_out_of_spec > 0:
                    stat['abnormal_count'] += 1
                # 嘗試將 measured_value 轉為數值
                try:
                    val = float(r.measured_value)
                    stat['numeric_values'].append(val)
                except (TypeError, ValueError):
                    pass

        # 計算平均值並格式化
        equipment_list = []
        for stat in equip_stats.values():
            avg = (sum(stat['numeric_values']) / len(stat['numeric_values'])
                   if stat['numeric_values'] else None)
            equipment_list.append({
                'id': stat['id'],
                'name': stat['name'],
                'org_name': stat['org_name'],
                'grade': stat['grade'],
                'last_inspection_date': stat['last_inspection_date'],
                'total_measurements': stat['total_measurements'],
                'abnormal_count': stat['abnormal_count'],
                'avg_value': round(avg, 2) if avg is not None else None
            })

        # 依異常次數排序（多的在前）
        equipment_list.sort(key=lambda x: x['abnormal_count'], reverse=True)

        return jsonify({
            'status': 'success',
            'data': {
                'equipment_list': equipment_list,
                'total': len(equipment_list)
            }
        }), 200

    except Exception as e:
        import traceback as tb
        full_trace = tb.format_exc()
        current_app.logger.error(f'Comparison FULL traceback:\n{full_trace}')
        return jsonify({
            'status': 'error',
            'message': f'查詢失敗: {str(e)}'
        }), 500


# ============================================================
# Comparison — 新版 API
# ============================================================

@inspection_bp.route('/comparison/items', methods=['GET'])
@token_required
@log_request
def get_comparison_item_tree(**kwargs):
    """
    取得去重後的檢查項目樹（依 unit 分類）
    回傳：類別 → 項目清單（唯一 item_name）
    """
    try:
        from app.models.Mortor_equipment import EquitCheckItem

        all_items = EquitCheckItem.query.filter(
            EquitCheckItem.unit != None
        ).order_by(EquitCheckItem.item_name).all()

        # 去重：只保留唯一 item_name，並記錄代表性 max_v
        seen = {}
        for item in all_items:
            key = item.item_name
            if key not in seen:
                seen[key] = {
                    'item_name': item.item_name,
                    'unit': item.unit,
                    'max_v': float(item.max_v) if item.max_v else None,
                    'min_v': float(item.min_v) if item.min_v else None,
                }

        # 依 unit 分類
        UNIT_CATEGORY = {
            'mm/s': '馬達-振動',
            '℃':    '馬達-溫度',
        }
        categories = {}
        for info in seen.values():
            cat = UNIT_CATEGORY.get(info['unit'], '其他')
            if cat not in categories:
                categories[cat] = {'name': cat, 'unit': info['unit'], 'items': []}
            categories[cat]['items'].append(info)

        return jsonify({
            'status': 'success',
            'data': {'categories': list(categories.values())}
        }), 200

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'查詢失敗: {str(e)}'}), 500


@inspection_bp.route('/comparison/equip-trend', methods=['GET'])
@token_required
@log_request
def get_comparison_equip_trend(**kwargs):
    """
    取得多設備在「同一檢查項目名稱」的時序趨勢
    Query params:
        item_name  (必填) — 項目名稱，例如 MIH振動量測
        equip_ids  (必填) — 設備 ID 清單，可多個
        start_date — YYYY-MM-DD
        end_date   — YYYY-MM-DD
    """
    try:
        from app.models.Mortor_equipment import EquitCheckItem, TEquipment
        from app.models.Mortor_organization import TOrganization
        from datetime import datetime

        item_name  = request.args.get('item_name', '').strip()
        equip_ids  = request.args.getlist('equip_ids')
        start_date = request.args.get('start_date')
        end_date   = request.args.get('end_date')

        if not item_name or not equip_ids:
            return jsonify({'status': 'error', 'message': '缺少 item_name 或 equip_ids'}), 400

        # --- 找全部叫 item_name 的 EquitCheckItem（代表性資料用第一筆）---
        rep_item = EquitCheckItem.query.filter_by(item_name=item_name).first()
        max_v = float(rep_item.max_v) if rep_item and rep_item.max_v else None
        unit  = rep_item.unit if rep_item else None

        # --- 對每台設備，取得對應 item_id 並查 InspectionResult ---
        equip_series = []
        date_set = set()

        for eid in equip_ids:
            equip = TEquipment.query.get(eid)
            if not equip:
                continue

            # 找到此設備的工單對應的 item（根據 grade/mterm）
            from app.models.Mortor_inspection import TJob
            job = TJob.query.filter_by(equipmentid=eid).first()
            grade = job.grade if job else None
            mterm = job.mterm if job else None

            # 找到符合的 EquitCheckItem
            item_q = EquitCheckItem.query.filter_by(item_name=item_name)
            if grade:
                item_q = item_q.filter_by(grade=grade)
            if mterm:
                item_q = item_q.filter_by(mterm=mterm)
            check_item = item_q.first()

            if not check_item:
                # 退而求其次：只用 item_name 找
                check_item = EquitCheckItem.query.filter_by(item_name=item_name).first()

            if not check_item:
                continue

            # 查 InspectionResult
            rq = InspectionResult.query.filter_by(
                equipmentid=eid,
                item_id=check_item.item_id
            ).order_by(InspectionResult.act_time.asc())

            if start_date:
                rq = rq.filter(InspectionResult.act_time >=
                               datetime.strptime(start_date, '%Y-%m-%d'))
            if end_date:
                rq = rq.filter(InspectionResult.act_time <=
                               datetime.strptime(end_date + ' 23:59:59', '%Y-%m-%d %H:%M:%S'))

            results = rq.all()
            date_vals = {}
            for r in results:
                if r.act_time:
                    d = r.act_time.strftime('%Y-%m-%d')
                    date_set.add(d)
                    try:
                        date_vals[d] = float(r.measured_value)
                    except (ValueError, TypeError):
                        date_vals[d] = None

            equip_series.append({
                'equipment_id':   eid,
                'equipment_name': equip.name,
                'date_vals':      date_vals,
            })

        # 統一時間軸
        dates = sorted(date_set)

        # 補齊每台設備的時間序列（無資料補 null）
        for s in equip_series:
            s['values'] = [s['date_vals'].get(d) for d in dates]
            del s['date_vals']

        return jsonify({
            'status': 'success',
            'data': {
                'item_name': item_name,
                'unit':      unit,
                'max_v':     max_v,
                'dates':     dates,
                'series':    equip_series,
            }
        }), 200

    except Exception as e:
        import traceback as tb
        current_app.logger.error(f'equip-trend error:\n{tb.format_exc()}')
        return jsonify({'status': 'error', 'message': f'查詢失敗: {str(e)}'}), 500
