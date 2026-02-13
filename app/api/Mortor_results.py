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
        - uploaded_count: 成功上傳數量
        - failed_count: 失敗數量
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
    results = data['results']
    
    # Verify task exists
    task = TJob.query.get(actid)
    if not task:
        return jsonify({
            'status': 'error',
            'message': '任務不存在'
        }), 404
    
    uploaded_count = 0
    failed_count = 0
    errors = []
    
    for idx, result_data in enumerate(results):
        try:
            # Validate required fields for each result
            required_fields = ['item_id', 'measured_value', 'act_time', 'act_mem_id']
            # Map old keys if needed
            if 'itemid' in result_data: result_data['item_id'] = result_data.pop('itemid')
            if 'measuredvalue' in result_data: result_data['measured_value'] = result_data.pop('measuredvalue')
            if 'acttime' in result_data: result_data['act_time'] = result_data.pop('acttime')
            if 'actmemid' in result_data: result_data['act_mem_id'] = result_data.pop('actmemid')
            if 'isoutofspec' in result_data: result_data['is_out_of_spec'] = result_data.pop('isoutofspec')
            if 'resultphoto' in result_data: result_data['result_photo'] = result_data.pop('resultphoto')
            
            error = Validator.validate_required_fields(result_data, required_fields)
            if error:
                errors.append({'index': idx, 'reason': error})
                failed_count += 1
                continue
            
            # Validate act_time format
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
                errors.append({'index': idx, 'reason': '檢查時間格式錯誤'})
                failed_count += 1
                continue
            
            # Handle photo
            result_photo = result_data.get('result_photo')
            if 'photo_data' in result_data:
                success, saved_path = save_base64_image(
                    result_data['photo_data'],
                    subfolder='photos'
                )
                if success:
                    result_photo = saved_path
            
            # Check if result already exists (update or create)
            result = InspectionResult.query.filter_by(
                actid=actid,
                item_id=result_data['item_id']
            ).first()
            
            if result:
                # Update
                result.measured_value = result_data['measured_value']
                result.is_out_of_spec = result_data.get('is_out_of_spec', 0)
                result.act_time = acttime
                result.act_mem_id = result_data['act_mem_id']
                result.equipmentid = task.equipmentid
                if result_photo:
                    result.result_photo = result_photo
            else:
                # Create
                result = InspectionResult(
                    actid=actid,
                    item_id=result_data['item_id'],
                    equipmentid=task.equipmentid,
                    measured_value=result_data['measured_value'],
                    act_mem_id=result_data['act_mem_id'],
                    act_time=acttime,
                    is_out_of_spec=result_data.get('is_out_of_spec', 0),
                    result_photo=result_photo
                )
                db.session.add(result)
            
            # Create abnormal tracking if is_out_of_spec >= 2 (異常 or 停機)
            if result.is_out_of_spec and result.is_out_of_spec >= 2:
                tracking = AbnormalCases.query.filter_by(
                    actid=actid,
                    item_id=result_data['item_id']
                ).first()
                
                if not tracking:
                    tracking = AbnormalCases(
                        actid=actid,
                        equipmentid=task.equipmentid,
                        item_id=result_data['item_id'],
                        measured_value=result_data['measured_value'],
                        is_processed=False,
                        abn_msg='',
                        abn_solution='',
                    )
                    db.session.add(tracking)
            
            uploaded_count += 1
            
        except Exception as e:
            current_app.logger.error(f'Error uploading result {idx}: {str(e)}')
            errors.append({'index': idx, 'reason': str(e)})
            failed_count += 1
            db.session.rollback()
            continue
    
    # Commit all changes
    try:
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f'Error committing results: {str(e)}')
        return jsonify({
            'status': 'error',
            'message': f'資料儲存失敗: {str(e)}'
        }), 500
    
    current_app.logger.info(
        f'User {current_user.id} uploaded {uploaded_count} results for task {actid}'
    )
    
    # Determine response status
    if failed_count == 0:
        return jsonify({
            'status': 'success',
            'message': '資料上傳完成',
            'data': {
                'uploaded_count': uploaded_count,
                'failed_count': failed_count
            }
        }), 200
    elif uploaded_count > 0:
        return jsonify({
            'status': 'partial_success',
            'message': '部分資料上傳失敗',
            'data': {
                'uploaded_count': uploaded_count,
                'failed_count': failed_count,
                'errors': errors
            }
        }), 207
    else:
        return jsonify({
            'status': 'error',
            'message': '所有資料上傳失敗',
            'data': {
                'uploaded_count': uploaded_count,
                'failed_count': failed_count,
                'errors': errors
            }
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
        - actid: 任務 ID
        - itemid: 檢查項目 ID
        - file: 圖片檔案
    
    Response:
        - resultphoto: 照片路徑
    """
    current_user = kwargs.get('current_user')
    
    # Validate form data
    if 'actid' not in request.form or 'itemid' not in request.form:
        return jsonify({
            'status': 'error',
            'message': '缺少 actid 或 itemid'
        }), 400
    
    if 'file' not in request.files:
        return jsonify({
            'status': 'error',
            'message': '缺少圖片檔案'
        }), 400
    
    actid = request.form['actid']
    itemid = request.form['itemid']
    file = request.files['file']
    
    # Verify result exists
    result = InspectionResult.query.filter_by(
        actid=actid,
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
        f'User {current_user.id} uploaded photo for task {actid} item {itemid}'
    )
    
    return jsonify({
        'status': 'success',
        'data': {
            'resultphoto': photo_path
        }
    }), 200
