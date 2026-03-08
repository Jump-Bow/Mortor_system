"""
Global Error Handlers
全局異常處理器

統一攔截系統層級的錯誤，並回傳標準化的 JSON 格式，
避免 Flask 在發生 500 錯誤時回傳 HTML，導致 APP JSON 解析失敗 (Crash)。
"""
from flask import current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from app.utils.api_response import error_response


def register_error_handlers(app):
    """註冊全局異常處理器"""
    
    @app.errorhandler(400)
    def bad_request(e):
        return error_response(
            message='請求參數錯誤',
            error_code='BAD_REQUEST',
            status_code=400
        )

    @app.errorhandler(401)
    def unauthorized(e):
        return error_response(
            message='未授權的存取，請重新登入',
            error_code='UNAUTHORIZED',
            status_code=401
        )

    @app.errorhandler(403)
    def forbidden(e):
        return error_response(
            message='權限不足',
            error_code='FORBIDDEN',
            status_code=403
        )

    @app.errorhandler(404)
    def not_found(e):
        return error_response(
            message='請求的資源或路徑不存在',
            error_code='NOT_FOUND',
            status_code=404
        )
        
    @app.errorhandler(405)
    def method_not_allowed(e):
        return error_response(
            message='不允許的 HTTP 方法 (Method Not Allowed)',
            error_code='METHOD_NOT_ALLOWED',
            status_code=405
        )

    @app.errorhandler(429)
    def too_many_requests(e):
        return error_response(
            message='請求過於頻繁，請稍後再試',
            error_code='TOO_MANY_REQUESTS',
            status_code=429
        )

    @app.errorhandler(SQLAlchemyError)
    def handle_db_error(e):
        # 資料庫層級的錯誤（不要將詳細錯誤訊息吐給前端，保護內部 SQL 架構）
        app.logger.error(f"Database Error: {str(e)}")
        from app.models.Mortor_system_log import SystemLog
        SystemLog.create(level='ERROR', module='Database', message=f'DB Error occurred')
        
        return error_response(
            message='伺服器資料庫發生異常，請聯絡系統管理員',
            error_code='DATABASE_ERROR',
            status_code=500
        )

    @app.errorhandler(Exception)
    def handle_exception(e):
        # 處理所有未捕捉的程式碼當機 (HTTP 500)
        # 如果錯誤本身是 HTTP 異常，就直接轉發其代碼
        if isinstance(e, HTTPException):
            return error_response(
                message=e.description,
                error_code=e.name.upper().replace(' ', '_'),
                status_code=e.code
            )
            
        app.logger.exception(f"Unhandled Exception: {str(e)}")
        from app.models.Mortor_system_log import SystemLog
        SystemLog.create(level='ERROR', module='System', message=f'Unhandled Exception: {type(e).__name__}')
        
        return error_response(
            message='伺服器發生非預期錯誤 (Internal Server Error)',
            error_code='INTERNAL_SERVER_ERROR',
            status_code=500
        )
