"""
API Response Helpers
統一 API 回應格式工具

所有 API 端點應使用此模組的函式回傳標準化格式。
格式：
{
    "status": "success" | "error",
    "data": { ... } | null,
    "message": "...",
    "error_code": "..." (僅錯誤時),
    "timestamp": "2024-01-01T00:00:00.000000"
}
"""
from flask import jsonify
from datetime import datetime


def success_response(data=None, message=None, status_code=200, **extra):
    """
    成功回應

    Args:
        data: 回應資料 (dict, list, or None)
        message: 成功訊息
        status_code: HTTP 狀態碼 (預設 200)
        **extra: 額外欄位（如 pagination）

    Returns:
        Flask Response, status_code
    
    Example:
        return success_response(data={'user': user.to_dict()}, message='登入成功')
        return success_response(data=users, total=100, page=1, per_page=20)
    """
    response = {
        'status': 'success',
        'data': data,
        'timestamp': datetime.utcnow().isoformat(),
    }
    if message:
        response['message'] = message
    
    # 加入額外欄位（分頁、統計等）
    response.update(extra)
    
    return jsonify(response), status_code


def error_response(message, error_code=None, status_code=400, errors=None):
    """
    錯誤回應

    Args:
        message: 錯誤訊息
        error_code: 錯誤代碼 (如 'UNAUTHORIZED', 'NOT_FOUND')
        status_code: HTTP 狀態碼 (預設 400)
        errors: 詳細錯誤列表（驗證錯誤時使用）

    Returns:
        Flask Response, status_code
    
    Example:
        return error_response('帳號或密碼錯誤', error_code='AUTH_FAILED', status_code=401)
        return error_response('欄位驗證失敗', errors=[{'field': 'email', 'message': '格式不正確'}])
    """
    response = {
        'status': 'error',
        'message': message,
        'timestamp': datetime.utcnow().isoformat(),
    }
    if error_code:
        response['error_code'] = error_code
    if errors:
        response['errors'] = errors
    
    return jsonify(response), status_code


def paginated_response(items, total, page, per_page, message=None):
    """
    分頁回應

    Args:
        items: 項目列表 (list of dict)
        total: 總筆數
        page: 當前頁碼
        per_page: 每頁筆數
        message: 成功訊息

    Returns:
        Flask Response, 200
    """
    return success_response(
        data=items,
        message=message,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=(total + per_page - 1) // per_page if per_page > 0 else 0,
    )
