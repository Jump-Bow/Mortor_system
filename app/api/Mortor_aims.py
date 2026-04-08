"""
AIMS API Blueprint
AIMS工單執行進度查詢 API
"""
from flask import Blueprint, request, jsonify, current_app
from app.models.Mortor_inspection import TJob, InspectionResult
from app.models.Mortor_equipment import TEquipment
from app.models.Mortor_abnormal import AbnormalCases
from app.api.Mortor_inspection import get_descendant_unit_ids
from app.auth.jwt_handler import token_required
from app.utils.decorators import log_request
from datetime import datetime
import io
import csv

aims_bp = Blueprint('aims', __name__)


@aims_bp.route('/progress', methods=['GET'])
@token_required
@log_request
def aims_progress_list(**kwargs):
    """
    AIMS工單執行進度查詢 - 工單列表
    支援篩選: org_id, start_date, end_date, motor_type(group), mterm, act_key
    """
    try:
        # 取得篩選參數
        org_id = request.args.get('org_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        motor_type = request.args.get('motor_type')  # group (A/B/C/D)
        mterm = request.args.get('mterm')  # 保養週期 (1M/3M)
        act_key = request.args.get('act_key')  # 工單號碼
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)

        # 建立查詢
        query = TJob.query.join(TEquipment, TJob.equipmentid == TEquipment.id, isouter=True)

        # 篩選條件
        if org_id:
            unit_ids = get_descendant_unit_ids(org_id)
            query = query.filter(TEquipment.unitid.in_(unit_ids))
        if start_date:
            query = query.filter(TJob.mdate >= start_date.replace('-', ''))
        if end_date:
            query = query.filter(TJob.mdate <= end_date.replace('-', ''))
        if motor_type:
            query = query.filter(TJob.grade == motor_type)
        if mterm:
            query = query.filter(TJob.mterm == mterm)
        if act_key:
            query = query.filter(TJob.act_key.ilike(f'%{act_key}%'))

        # 排序
        query = query.order_by(TJob.mdate.desc())

        # 分頁
        total = query.count()
        jobs = query.offset((page - 1) * page_size).limit(page_size).all()

        # 統計
        all_jobs = TJob.query
        if org_id:
            unit_ids = get_descendant_unit_ids(org_id)
            all_jobs = all_jobs.join(TEquipment, TJob.equipmentid == TEquipment.id).filter(TEquipment.unitid.in_(unit_ids))
        if start_date:
            all_jobs = all_jobs.filter(TJob.mdate >= start_date.replace('-', ''))
        if end_date:
            all_jobs = all_jobs.filter(TJob.mdate <= end_date.replace('-', ''))

        records = []
        for job in jobs:
            job_dict = job.to_dict()
            # 計算是否有異常
            has_abnormal = AbnormalCases.query.filter_by(actid=job.actid).count() > 0
            job_dict['has_abnormal'] = has_abnormal
            records.append(job_dict)

        return jsonify({
            'status': 'success',
            'data': {
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
        current_app.logger.error(f'AIMS progress list error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'查詢失敗: {str(e)}'
        }), 500


@aims_bp.route('/progress/<actid>', methods=['GET'])
@token_required
@log_request
def aims_progress_detail(actid, **kwargs):
    """
    AIMS工單詳細 - 設備列表
    取得指定工單下的所有設備及其完成率
    """
    try:
        job = TJob.query.get_or_404(actid)

        # 取得該工單的所有設備 (通常一個工單對一個設備，但結構支援多個)
        equipment_list = []
        if job.equipment:
            equip = job.equipment
            # KEY FIX: EquitCheckItem 已改為全域 grade/mterm 通用架構，無 equipmentid FK
            # total_items 應依工單的 grade+mterm 查詢通用項目數量
            from app.models.Mortor_equipment import EquitCheckItem
            total_items = EquitCheckItem.query.filter_by(
                grade=job.grade, mterm=job.mterm
            ).count()
            completed_items = InspectionResult.query.filter_by(
                actid=actid, equipmentid=equip.id
            ).count()
            completion_rate = round((completed_items / total_items * 100), 1) if total_items > 0 else 0

            equipment_list.append({
                'id': equip.id,
                'name': equip.name,
                'assetid': equip.assetid,
                'total_items': total_items,
                'completed_items': completed_items,
                'completion_rate': completion_rate
            })

        return jsonify({
            'status': 'success',
            'data': {
                'job': job.to_dict(),
                'equipment_list': equipment_list
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'AIMS progress detail error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'查詢失敗: {str(e)}'
        }), 500


@aims_bp.route('/progress/<actid>/equipment/<equipmentid>', methods=['GET'])
@token_required
@log_request
def aims_equipment_measurements(actid, equipmentid, **kwargs):
    """
    AIMS設備量測資訊
    取得指定工單下指定設備的所有量測結果
    """
    try:
        results = InspectionResult.query.filter_by(
            actid=actid, equipmentid=equipmentid
        ).all()

        measurements = []
        for result in results:
            result_dict = result.to_dict()
            # 加入檢查項目的上下限警戒值
            if result.check_item:
                result_dict['max_v'] = result.check_item.max_v
                result_dict['min_v'] = result.check_item.min_v
                result_dict['unit'] = result.check_item.unit
                result_dict['status_type'] = result.check_item.status_type
            # 加入異常追蹤資料（abn_msg / abn_solution / processed_memname）
            abnormal = AbnormalCases.query.filter_by(
                actid=actid, item_id=result.item_id
            ).first()
            if abnormal:
                result_dict['abn_msg'] = abnormal.abn_msg
                result_dict['abn_solution'] = abnormal.abn_solution
                result_dict['is_processed'] = abnormal.is_processed
                result_dict['processed_memname'] = (
                    abnormal.responsible_user.name
                    if abnormal.responsible_user else abnormal.processed_memid
                )
            else:
                result_dict['abn_msg'] = None
                result_dict['abn_solution'] = None
                result_dict['processed_memname'] = None
            measurements.append(result_dict)

        return jsonify({
            'status': 'success',
            'data': {
                'measurements': measurements
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'AIMS equipment measurements error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'查詢失敗: {str(e)}'
        }), 500


@aims_bp.route('/progress/export', methods=['GET'])
@token_required
@log_request
def aims_progress_export(**kwargs):
    """
    AIMS工單報表匯出 (CSV)
    """
    try:
        from flask import Response

        # 取得篩選參數 (同 list)
        org_id = request.args.get('org_id')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        motor_type = request.args.get('motor_type')
        mterm = request.args.get('mterm')

        query = TJob.query.join(TEquipment, TJob.equipmentid == TEquipment.id, isouter=True)

        if org_id:
            unit_ids = get_descendant_unit_ids(org_id)
            query = query.filter(TEquipment.unitid.in_(unit_ids))
        if start_date:
            query = query.filter(TJob.mdate >= start_date.replace('-', ''))
        if end_date:
            query = query.filter(TJob.mdate <= end_date.replace('-', ''))
        if motor_type:
            query = query.filter(TJob.grade == motor_type)
        if mterm:
            query = query.filter(TJob.mterm == mterm)

        jobs = query.order_by(TJob.mdate.desc()).all()

        # 產生 CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(['工單號碼', '工單日期', '組織', '設備名稱', '馬達類別', '保養週期', '負責人', '狀態', '完成率', '工單內容'])

        for job in jobs:
            job_dict = job.to_dict()
            writer.writerow([
                job_dict.get('act_key', ''),
                job_dict.get('mdate', ''),
                job_dict.get('org_name', ''),
                job_dict.get('equipment_name', ''),
                job_dict.get('grade', ''),
                job_dict.get('mterm', ''),
                job_dict.get('act_mem', ''),
                job_dict.get('status', ''),
                f"{job_dict.get('completion_rate', 0)}%",
                job_dict.get('act_desc', '')
            ])

        csv_data = output.getvalue()
        output.close()

        return Response(
            csv_data,
            mimetype='text/csv',
            headers={
                'Content-Disposition': f'attachment; filename=aims_progress_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv',
                'Content-Type': 'text/csv; charset=utf-8-sig'
            }
        )

    except Exception as e:
        current_app.logger.error(f'AIMS export error: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'匯出失敗: {str(e)}'
        }), 500
