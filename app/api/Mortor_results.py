"""
Results API Blueprint
資料同步與結果上傳 API
"""
from flask import Blueprint, request, jsonify, current_app
from app import db
from app.models.Mortor_inspection import InspectionResult, TJob
from app.models.Mortor_abnormal import AbnormalCases
from app.auth.jwt_handler import token_required
from app.utils.decorators import validate_json, log_request
from app.utils.validators import Validator
from app.utils.file_helpers import save_base64_image, save_uploaded_file
from datetime import datetime
from app.utils.inspection_status import InspectionStatus
# P1: 引入 PostgreSQL 方言的原子 UPSERT，取代 Check-Then-Insert 模式
from sqlalchemy.dialects.postgresql import insert as pg_insert

results_bp = Blueprint('results', __name__)


@results_bp.route('/upload', methods=['POST'])
@token_required
@validate_json
@log_request
def upload_results(**kwargs):
    """
    上傳巡檢結果
    
    Request Body:
        - actid: 任務 ID
        - results: 結果列表
            - itemid: 檢查項目 ID
            - measuredvalue: 檢查結果值
            - isoutofspec: 狀態 (0=已建立, 1=正常, 2=異常, 3=停機)
            - acttime: 檢查時間
            - actmemid: 檢查人員 ID
            - resultphoto: 照片路徑 (可選)
            - photo_data: Base64 照片 (可選)
    
    Response:
        - uploaded_count: 成功上傳數量（新建立 或 LWW 判定為有效覆蓋）
        - conflict_count: 衝突跳過數量（LWW 判定：App 送來的資料比 DB 舊，合理跳過）
        - failed_count: 失敗數量（系統/驗證錯誤，App 應下次重試）
    """
    current_user = kwargs.get('current_user')
    data = request.get_json()
    
    # Validate required fields
    error = Validator.validate_required_fields(data, ['actid', 'results'])
    if error:
        return jsonify({
            'status': 'error',
            'message': error
        }), 400
    
    actid = data['actid']
    equipmentid = data.get('equipmentid')  # App 須同時提供 equipmentid（與複合主鍵對齊）
    results = data['results']
    
    # Verify task exists — 使用複合主鍵精確查詢
    if equipmentid:
        task = TJob.query.filter_by(actid=actid, equipmentid=equipmentid).first()
    else:
        # 向下相容：若 App 未提供 equipmentid，取第一筆（舊版 App）
        task = TJob.query.filter_by(actid=actid).first()
    if not task:
        return jsonify({
            'status': 'error',
            'message': '任務不存在'
        }), 404
    
    uploaded_count = 0
    conflict_count = 0  # P2: LWW 跳過（資料太舊），App 應標記 is_synced=1，不需重試
    failed_count = 0
    errors = []
    conflicts = []  # P2: 記錄被跳過的 item_id 與原因，回傳給 App 以利 debug
    
    for idx, result_data in enumerate(results):
        try:
            # 驗證每筆必要欄位
            required_fields = ['item_id', 'measured_value', 'act_time', 'act_mem_id']
            
            error = Validator.validate_required_fields(result_data, required_fields)
            if error:
                errors.append({'index': idx, 'item_id': result_data.get('item_id'), 'reason': error})
                failed_count += 1
                continue
            
            # 解析 act_time
            acttime_str = result_data['act_time']
            acttime = None
            
            formats = [
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S.%f',
                '%Y-%m-%dT%H:%M:%S.%fZ',
                '%Y-%m-%dT%H:%M:%S'
            ]
            
            for fmt in formats:
                try:
                    acttime = datetime.strptime(acttime_str, fmt)
                    break
                except ValueError:
                    continue
            
            if not acttime:
                errors.append({'index': idx, 'item_id': result_data.get('item_id'), 'reason': '檢查時間格式錯誤'})
                failed_count += 1
                continue
            
            # 處理照片
            result_photo = result_data.get('result_photo')
            if 'photo_data' in result_data:
                success, saved_path = save_base64_image(
                    result_data['photo_data'],
                    subfolder='photos'
                )
                if success:
                    result_photo = saved_path
            
            item_id = result_data['item_id']
            is_out_of_spec = result_data.get('is_out_of_spec', 0)

            # ─────────────────────────────────────────────────────────
            # P1: PostgreSQL 原子 UPSERT（取代 Check-Then-Insert）
            # 用 ON CONFLICT DO UPDATE 搭配 LWW 條件（新時間 > 舊時間才覆蓋）
            # 即使兩個 Flask worker 同時進入此段，DB 層也能保證原子性，
            # 不會發生 Race Condition 或主鍵衝突的 IntegrityError。
            # ─────────────────────────────────────────────────────────
            stmt = pg_insert(InspectionResult).values(
                actid=actid,
                equipmentid=task.equipmentid,
                item_id=item_id,
                measured_value=result_data['measured_value'],
                act_mem_id=result_data['act_mem_id'],
                act_time=acttime,
                is_out_of_spec=is_out_of_spec,
                result_photo=result_photo
            )

            # 僅當新資料的 act_time 嚴格大於 DB 中現有的 act_time 才執行覆蓋（LWW）
            # 若條件不成立（資料太舊或相同），PostgreSQL 不執行任何 UPDATE，
            # 並透過 returning() 讓我們知道哪些欄位沒有被更新（xmax=0 表示未更新）
            upsert_stmt = stmt.on_conflict_do_update(
                index_elements=['actid', 'equipmentid', 'item_id'],
                set_=dict(
                    measured_value=stmt.excluded.measured_value,
                    act_mem_id=stmt.excluded.act_mem_id,
                    act_time=stmt.excluded.act_time,
                    is_out_of_spec=stmt.excluded.is_out_of_spec,
                    result_photo=stmt.excluded.result_photo,
                ),
                # P1 LWW 核心：只有新資料時間更新才覆蓋
                where=(stmt.excluded.act_time > InspectionResult.act_time)
            ).returning(InspectionResult.act_time, InspectionResult.actid)

            result_row = db.session.execute(upsert_stmt)
            returned = result_row.fetchone()

            # ─────────────────────────────────────────────────────────
            # P2: 語意判斷 — UPSERT 是否真的執行了寫入（新建或覆蓋）？
            # returned 有值 → 資料被寫入（新建 or 覆蓋）→ uploaded_count
            # returned 無值 → DB 端 LWW 條件不成立（舊資料），靜默跳過 → conflict_count
            # ─────────────────────────────────────────────────────────
            if returned is not None:
                uploaded_count += 1
            else:
                # DB 認為現有資料比傳入的更新，合理跳過
                conflict_count += 1
                conflicts.append({
                    'item_id': item_id,
                    'reason': 'DB 已有更新資料（LWW 跳過）'
                })

            # 異常追蹤：is_out_of_spec >= ABNORMAL，確保 AbnormalCases 存在
            if is_out_of_spec and is_out_of_spec >= InspectionStatus.ABNORMAL:
                tracking = AbnormalCases.query.filter_by(
                    actid=actid,
                    equipmentid=task.equipmentid,
                    item_id=item_id
                ).first()
                
                if not tracking:
                    tracking = AbnormalCases(
                        actid=actid,
                        equipmentid=task.equipmentid,
                        item_id=item_id,
                        measured_value=result_data['measured_value'],
                        is_processed=False,
                        abn_msg=result_data.get('abn_msg', '') or '',
                        abn_solution='',
                    )
                    db.session.add(tracking)
            
            db.session.commit()
            
        except Exception as e:
            db.session.rollback()
            current_app.logger.error(f'Error uploading result idx={idx} item_id={result_data.get("item_id")}: {str(e)}')
            errors.append({'index': idx, 'item_id': result_data.get('item_id'), 'reason': str(e)})
            failed_count += 1
            continue
    
    current_app.logger.info(
        f'User {current_user.id} uploaded results for task {actid}: '
        f'uploaded={uploaded_count}, conflict={conflict_count}, failed={failed_count}'
    )
    
    # ─────────────────────────────────────────────────────────────────
    # P2: 回應語意設計
    # - failed_count=0           → 200 success（含 conflict_count 資訊）
    # - failed_count>0 但有成功  → 207 partial_success
    # - 全部失敗                 → 400 error
    # conflict_count 不算失敗，App 端收到後應將對應筆標記 is_synced=1
    # ─────────────────────────────────────────────────────────────────
    response_data = {
        'uploaded_count': uploaded_count,
        'conflict_count': conflict_count,
        'failed_count': failed_count,
    }
    if conflicts:
        response_data['conflicts'] = conflicts
    if errors:
        response_data['errors'] = errors

    if failed_count == 0:
        return jsonify({
            'status': 'success',
            'message': f'資料上傳完成（上傳 {uploaded_count} 筆，跳過舊資料 {conflict_count} 筆）',
            'data': response_data
        }), 200
    elif uploaded_count > 0 or conflict_count > 0:
        return jsonify({
            'status': 'partial_success',
            'message': f'部分資料上傳失敗（失敗 {failed_count} 筆）',
            'data': response_data
        }), 207
    else:
        return jsonify({
            'status': 'error',
            'message': '所有資料上傳失敗',
            'data': response_data
        }), 400


@results_bp.route('/sync', methods=['POST'])
@token_required
@validate_json
@log_request
def sync_results(**kwargs):
    """
    批次同步巡檢結果
    """
    return upload_results(**kwargs)


@results_bp.route('/photos/upload', methods=['POST'])
@token_required
@log_request
def upload_photo(**kwargs):
    """
    上傳異常照片 (multipart/form-data)
    
    Form Data:
        - actid:       任務 ID
        - itemid:      檢查項目 ID
        - equipmentid: 設備 ID（與 InspectionResult 三欄複合主鍵對齊）
        - file:        圖片檔案
    
    Response:
        - resultphoto: 照片路徑
    """
    current_user = kwargs.get('current_user')
    
    # Validate form data — equipmentid 是複合主鍵的第三欄，必須一併傳入
    if 'actid' not in request.form or 'itemid' not in request.form or 'equipmentid' not in request.form:
        return jsonify({
            'status': 'error',
            'message': '缺少 actid、itemid 或 equipmentid'
        }), 400
    
    if 'file' not in request.files:
        return jsonify({
            'status': 'error',
            'message': '缺少圖片檔案'
        }), 400
    
    actid = request.form['actid']
    itemid = request.form['itemid']
    equipmentid = request.form['equipmentid']
    file = request.files['file']
    
    # Verify result exists — 使用完整三欄複合主鍵查詢，與 InspectionResult PK 定義嚴格對齊
    # 若僅用 (actid, item_id) 兩欄，在同一工單跨設備情境下可能命中錯誤紀錄。
    result = InspectionResult.query.filter_by(
        actid=actid,
        equipmentid=equipmentid,
        item_id=itemid
    ).first()
    
    if not result:
        return jsonify({
            'status': 'error',
            'message': '結果不存在'
        }), 404
    
    # Save file
    success, photo_path = save_uploaded_file(file, subfolder='photos')
    
    if not success:
        return jsonify({
            'status': 'error',
            'message': photo_path  # Error message
        }), 400
    
    # Update result photo path
    result.result_photo = photo_path
    db.session.commit()
    
    current_app.logger.info(
        f'User {current_user.id} uploaded photo for task {actid} equipment {equipmentid} item {itemid}'
    )
    
    return jsonify({
        'status': 'success',
        'data': {
            'resultphoto': photo_path
        }
    }), 200
