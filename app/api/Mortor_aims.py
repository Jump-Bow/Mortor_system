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
    【第一性原理】以 act_key（工單號碼）為聚合鍵，一列 = 一個工單號碼。
    同一工單號碼下可有多台設備（多個 T_JOB actid），設備明細由詳細彈窗展示。
    支援篩選: org_id, start_date, end_date, motor_type(grade), mterm, act_key
    """
    try:
        from collections import defaultdict
        from app.models.Mortor_equipment import EquitCheckItem

        org_id     = request.args.get('org_id')
        start_date = request.args.get('start_date')
        end_date   = request.args.get('end_date')
        motor_type = request.args.get('motor_type')
        mterm_f    = request.args.get('mterm')
        act_key_f  = request.args.get('act_key')
        page       = request.args.get('page', 1, type=int)
        page_size  = request.args.get('page_size', 20, type=int)

        # 基礎查詢（取所有符合篩選的 TJob）
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
        if mterm_f:
            query = query.filter(TJob.mterm == mterm_f)
        if act_key_f:
            query = query.filter(TJob.act_key.ilike(f'%{act_key_f}%'))

        # 取出全部符合的 TJob（先按日期降序，保留最新排序）
        jobs = query.order_by(TJob.mdate.desc()).all()

        # ── 以 act_key 為主鍵聚合（保留首次出現的排序）──
        act_key_order  = []
        act_key_groups = defaultdict(list)
        for job in jobs:
            key = job.act_key or job.actid  # act_key 為 None 時 fallback 用 actid
            if key not in act_key_groups:
                act_key_order.append(key)
            act_key_groups[key].append(job)

        # 快取 (grade, mterm) → 檢查項目數量，避免重複 DB 查詢
        check_item_cache = {}

        records = []
        for key in act_key_order:
            job_list   = act_key_groups[key]
            first_job  = job_list[0]

            # 聚合 org_name：跨組織時顯示「多組織」
            org_names = []
            for j in job_list:
                org = (j.equipment.facility.unitname
                       if j.equipment and j.equipment.facility else None)
                if org and org not in org_names:
                    org_names.append(org)
            if len(org_names) == 0:
                org_display = '-'
            elif len(org_names) == 1:
                org_display = org_names[0]
            else:
                org_display = '多組織'

            # 聚合完成率：所有設備的已完成 / 總項目數
            total_items_all    = 0
            completed_items_all = 0
            for j in job_list:
                gm = (j.grade, j.mterm)
                if gm not in check_item_cache:
                    check_item_cache[gm] = EquitCheckItem.query.filter_by(
                        grade=j.grade, mterm=j.mterm
                    ).count()
                t = check_item_cache[gm]
                c = (InspectionResult.query
                     .filter_by(actid=j.actid, equipmentid=j.equipmentid)
                     .filter(InspectionResult.is_out_of_spec != 0)
                     .count())
                total_items_all     += t
                completed_items_all += c

            overall_rate = (
                round(completed_items_all / total_items_all * 100, 1)
                if total_items_all > 0 else 0
            )

            # 聚合狀態
            if total_items_all == 0:
                agg_status = '未派工'
            elif completed_items_all >= total_items_all:
                agg_status = '已完成'
            elif completed_items_all > 0:
                agg_status = '執行中'
            else:
                agg_status = '未派工'

            # 是否有異常（批次查詢減少 DB 往返）
            actids = [j.actid for j in job_list]
            has_abnormal = (
                AbnormalCases.query
                .filter(AbnormalCases.actid.in_(actids))
                .count() > 0
            )

            records.append({
                'act_key':         key,
                'mdate':           first_job.mdate,
                'act_desc':        first_job.act_desc or '',
                'org_name':        org_display,
                'grade':           first_job.grade or '-',
                'mterm':           first_job.mterm or '-',
                'act_mem':         first_job.act_mem or '-',
                'status':          agg_status,
                'completion_rate': overall_rate,
                'has_abnormal':    has_abnormal,
                'equipment_count': len(job_list),
            })

        # 分頁（聚合後再分頁）
        total      = len(records)
        paginated  = records[(page - 1) * page_size: page * page_size]

        return jsonify({
            'status': 'success',
            'data': {
                'records': paginated,
                'pagination': {
                    'total':       total,
                    'page':        page,
                    'page_size':   page_size,
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


@aims_bp.route('/progress/key/<act_key>', methods=['GET'])
@token_required
@log_request
def aims_progress_detail_by_key(act_key, **kwargs):
    """
    AIMS工單詳細（依工單號碼 act_key）
    列出該工單號碼下所有設備的 actid、完成率，供前端設備彈窗使用。
    每台設備返回各自的 actid，供量測明細 API 使用。
    """
    try:
        from app.models.Mortor_equipment import EquitCheckItem

        jobs = TJob.query.filter_by(act_key=act_key).order_by(TJob.mdate.desc()).all()
        if not jobs:
            return jsonify({'status': 'error', 'message': '找不到工單'}), 404

        first_job = jobs[0]
        check_item_cache = {}
        equipment_list = []

        for job in jobs:
            if not job.equipment:
                continue
            equip = job.equipment
            gm = (job.grade, job.mterm)
            if gm not in check_item_cache:
                check_item_cache[gm] = EquitCheckItem.query.filter_by(
                    grade=job.grade, mterm=job.mterm
                ).count()
            total_items = check_item_cache[gm]
            completed_items = (
                InspectionResult.query
                .filter_by(actid=job.actid, equipmentid=equip.id)
                .filter(InspectionResult.is_out_of_spec != 0)
                .count()
            )
            completion_rate = (
                round(completed_items / total_items * 100, 1)
                if total_items > 0 else 0
            )
            equipment_list.append({
                'actid':           job.actid,      # 量測明細 API 所需
                'id':              equip.id,
                'name':            equip.name,
                'assetid':         equip.assetid,
                'total_items':     total_items,
                'completed_items': completed_items,
                'completion_rate': completion_rate,
            })

        return jsonify({
            'status': 'success',
            'data': {
                'act_key':      act_key,
                'act_desc':     first_job.act_desc or '',
                'equipment_list': equipment_list,
            }
        }), 200

    except Exception as e:
        current_app.logger.error(f'AIMS progress detail by key error: {str(e)}')
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
        job = TJob.query.filter_by(actid=actid).first()
        if not job:
            return jsonify({'status': 'error', 'message': '工單不存在'}), 404

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
