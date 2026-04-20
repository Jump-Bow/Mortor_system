"""
Global Rate Limiter Middleware
全局 API 速率限制中間件 - 使用 Redis 計數器

對所有 /api/* 路徑生效，基於 IP 做滑動窗口限制。
Redis 不可用時自動降級為不限制。
"""
import redis
import time
from flask import request, jsonify, current_app
from datetime import datetime


class RateLimiter:
    """全局速率限制器"""
    
    _redis_client = None
    _prefix = 'rate_limit:'
    
    @classmethod
    def _get_redis(cls):
        """取得 Redis 連線（懶載入，失敗時不快取避免永遠無法重試）"""
        # 若功能已停用，直接返回，不嘗試連線也不印警告
        if not current_app.config.get('RATELIMIT_ENABLED', True):
            return None

        if cls._redis_client is not None:
            try:
                cls._redis_client.ping()
                return cls._redis_client
            except Exception:
                cls._redis_client = None
        
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        try:
            client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            client.ping()
            cls._redis_client = client
            return cls._redis_client
        except Exception:
            current_app.logger.warning('Redis 無法連線，速率限制功能降級為停用')
            return None
    
    @classmethod
    def init_app(cls, app):
        """註冊為 Flask 中間件（before_request）"""
        
        @app.before_request
        def check_rate_limit():
            # 僅對 API 路徑生效
            if not request.path.startswith('/api/'):
                return None
            
            # 檢查是否啟用
            if not app.config.get('RATELIMIT_ENABLED', True):
                return None
            
            # 解析限制設定（格式："100 per hour"）
            rate_config = app.config.get('RATELIMIT_DEFAULT', '100 per hour')
            max_requests, window_seconds = cls._parse_rate_config(rate_config)
            
            # 取得客戶端識別（IP 或 Token user_id）
            client_id = request.remote_addr or 'unknown'
            
            # 檢查是否超過限制
            is_limited, remaining, reset_time = cls._check_limit(
                client_id, max_requests, window_seconds
            )
            
            if is_limited:
                response = jsonify({
                    'status': 'error',
                    'error_code': 'TOO_MANY_REQUESTS',
                    'message': f'請求過於頻繁，請稍後再試',
                    'timestamp': datetime.utcnow().isoformat(),
                })
                response.status_code = 429
                response.headers['Retry-After'] = str(reset_time)
                response.headers['X-RateLimit-Limit'] = str(max_requests)
                response.headers['X-RateLimit-Remaining'] = '0'
                return response
        
        @app.after_request
        def add_rate_limit_headers(response):
            """在回應 Header 中加入速率限制資訊"""
            if not request.path.startswith('/api/'):
                return response
            
            if not app.config.get('RATELIMIT_ENABLED', True):
                return response
            
            rate_config = app.config.get('RATELIMIT_DEFAULT', '100 per hour')
            max_requests, _ = cls._parse_rate_config(rate_config)
            
            # 加入標準 Rate Limit Headers
            response.headers.setdefault('X-RateLimit-Limit', str(max_requests))
            
            return response

    @classmethod
    def check_login_limit(cls, ip: str, username: str):
        """
        登入端點雙維度速率限制（防 Brute-force 攻擊）

        維度 1 — IP：每 IP 每 15 分鐘最多 10 次登入請求
                      防止同一網段的快速暴力嘗試
        維度 2 — 帳號：每帳號每 15 分鐘最多 5 次
                      防止攻擊者用多個 IP 輪換繞過 IP 限制

        Returns:
            (is_limited: bool, dimension: str, reset_seconds: int)
            dimension 為 'ip' 或 'account'，供錯誤訊息使用
        """
        LOGIN_IP_LIMIT = 10       # 每 IP 每窗口最大登入次數
        LOGIN_ACCOUNT_LIMIT = 5   # 每帳號每窗口最大登入次數
        LOGIN_WINDOW = 900        # 窗口大小：15 分鐘

        # 維度 1：IP 檢查
        is_limited, _, reset_time = cls._check_limit(
            f'login_ip:{ip}', LOGIN_IP_LIMIT, LOGIN_WINDOW
        )
        if is_limited:
            return True, 'ip', reset_time

        # 維度 2：帳號檢查
        is_limited, _, reset_time = cls._check_limit(
            f'login_account:{username}', LOGIN_ACCOUNT_LIMIT, LOGIN_WINDOW
        )
        if is_limited:
            return True, 'account', reset_time

        return False, None, 0

    
    @classmethod
    def _check_limit(cls, client_id, max_requests, window_seconds):
        """
        使用 Redis 滑動窗口檢查速率限制
        
        Returns:
            (is_limited, remaining, reset_seconds)
        """
        r = cls._get_redis()
        if r is None:
            return False, max_requests, 0  # Redis 不可用，降級為不限制
        
        try:
            key = f'{cls._prefix}{client_id}'
            now = time.time()
            pipe = r.pipeline()
            
            # 移除窗口外的舊記錄
            pipe.zremrangebyscore(key, 0, now - window_seconds)
            # 加入當前請求
            pipe.zadd(key, {str(now): now})
            # 計算窗口內請求數
            pipe.zcard(key)
            # 設定 key 過期時間
            pipe.expire(key, window_seconds)
            
            results = pipe.execute()
            request_count = results[2]
            
            remaining = max(0, max_requests - request_count)
            is_limited = request_count > max_requests
            reset_time = window_seconds
            
            return is_limited, remaining, reset_time
        except Exception as e:
            current_app.logger.error(f'速率限制檢查失敗: {e}')
            return False, max_requests, 0
    
    @staticmethod
    def _parse_rate_config(config_str):
        """
        解析速率限制設定字串
        
        格式: "100 per hour", "10 per minute", "1000 per day"
        
        Returns:
            (max_requests, window_seconds)
        """
        parts = config_str.lower().split()
        max_requests = int(parts[0])
        
        time_unit = parts[-1]
        time_map = {
            'second': 1,
            'minute': 60,
            'hour': 3600,
            'day': 86400,
        }
        window_seconds = time_map.get(time_unit, 3600)
        
        return max_requests, window_seconds
