"""
System Logs API Blueprint
系統日誌 API
"""
from flask import Blueprint, request, jsonify
from app.models.Mortor_system_log import UserActionLog
from app.models.Mortor_user import HrAccount
from app.utils.decorators import log_request, admin_required, web_or_api_required
from datetime import datetime, timedelta

system_logs_bp = Blueprint('system_logs', __name__)


@system_logs_bp.route('/list', methods=['GET'])
@web_or_api_required
@admin_required
@log_request
def list_logs(**kwargs):
    """
    取得使用者操作日誌列表
    
    Query Parameters:
        - userid: 使用者 ID (可選)
        - start_date: 開始日期 (可選，格式: YYYY-MM-DD)
        - end_date: 結束日期 (可選，格式: YYYY-MM-DD)
        - page: 頁碼 (可選，預設 1)
        - per_page: 每頁筆數 (可選，預設 50)
    
    Response:
        - logs: 日誌列表
        - pagination: 分頁資訊
    """
    # Get filters
    userid = request.args.get('userid')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    
    # Build query
    query = UserActionLog.query
    
    if userid:
        query = query.filter_by(userid=userid)
    
    if start_date:
        try:
            start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            query = query.filter(UserActionLog.timestamp >= start_datetime)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '開始日期格式不正確 (應為 YYYY-MM-DD)'
            }), 400
    
    if end_date:
        try:
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d') + timedelta(days=1)
            query = query.filter(UserActionLog.timestamp < end_datetime)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': '結束日期格式不正確 (應為 YYYY-MM-DD)'
            }), 400
    
    # Paginate
    pagination = query.order_by(UserActionLog.timestamp.desc()).paginate(
        page=page,
        per_page=per_page,
        error_out=False
    )
    
    logs_data = [log.to_dict() for log in pagination.items]
    
    return jsonify({
        'status': 'success',
        'data': {
            'logs': logs_data,
            'pagination': {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_prev': pagination.has_prev,
                'has_next': pagination.has_next
            }
        }
    }), 200


@system_logs_bp.route('/stats', methods=['GET'])
@web_or_api_required
@admin_required
@log_request
def get_stats(**kwargs):
    """
    取得操作日誌統計資訊
    
    Query Parameters:
        - days: 統計天數 (可選，預設 7)
    
    Response:
        - stats: 統計資訊
    """
    days = request.args.get('days', 7, type=int)
    
    # Calculate date range
    end_date = datetime.utcnow()
    start_date = end_date - timedelta(days=days)
    
    # Get logs in date range
    logs = UserActionLog.query.filter(
        UserActionLog.timestamp >= start_date,
        UserActionLog.timestamp <= end_date
    ).all()
    
    # Calculate statistics
    total_logs = len(logs)
    
    # Count by user
    user_counts = {}
    for log in logs:
        if log.user:
            user_name = log.user.name
            user_counts[user_name] = user_counts.get(user_name, 0) + 1
    
    # Top 10 most active users
    top_users = sorted(
        user_counts.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]
    
    # Daily activity
    daily_activity = {}
    for log in logs:
        date_key = log.timestamp.strftime('%Y-%m-%d')
        daily_activity[date_key] = daily_activity.get(date_key, 0) + 1
    
    return jsonify({
        'status': 'success',
        'data': {
            'stats': {
                'total_logs': total_logs,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                },
                'top_users': [
                    {'user_name': name, 'count': count}
                    for name, count in top_users
                ],
                'daily_activity': [
                    {'date': date, 'count': count}
                    for date, count in sorted(daily_activity.items())
                ]
            }
        }
    }), 200


@system_logs_bp.route('/<int:log_id>', methods=['GET'])
@web_or_api_required
@admin_required
@log_request
def get_log_detail(log_id, **kwargs):
    """
    取得日誌詳細資訊
    
    Response:
        - log: 日誌詳細資訊
    """
    log = UserActionLog.query.get(log_id)
    
    if not log:
        return jsonify({
            'status': 'error',
            'message': '日誌不存在'
        }), 404
    
    return jsonify({
        'status': 'success',
        'data': {
            'log': log.to_dict()
        }
    }), 200
