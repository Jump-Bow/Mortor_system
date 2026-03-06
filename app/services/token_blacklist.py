"""
Token Blacklist Service
Token 黑名單服務 - 使用 Redis 管理已撤銷的 JWT Token

當使用者登出時，將 Token 的 JTI 加入黑名單。
每次驗證 Token 時，檢查 JTI 是否在黑名單中。
黑名單條目會在 Token 過期時間後自動清除（Redis TTL）。
"""
import redis
from flask import current_app
from datetime import datetime, timedelta


class TokenBlacklistService:
    """Token 黑名單管理服務"""
    
    _redis_client = None
    _prefix = 'token_blacklist:'
    
    @classmethod
    def _get_redis(cls):
        """取得 Redis 連線（懶載入，失敗時不快取避免永遠無法重試）"""
        if cls._redis_client is not None:
            try:
                cls._redis_client.ping()  # 確認連線仍有效
                return cls._redis_client
            except Exception:
                cls._redis_client = None  # 重置，允許下次重試
        
        redis_url = current_app.config.get('REDIS_URL', 'redis://localhost:6379/0')
        try:
            client = redis.from_url(redis_url, decode_responses=True, socket_connect_timeout=2)
            client.ping()
            cls._redis_client = client
            return cls._redis_client
        except Exception:
            current_app.logger.warning('Redis 無法連線，Token 黑名單功能降級為停用')
            return None  # 不快取 None，下次請求仍可重試
    
    @classmethod
    def is_enabled(cls):
        """檢查黑名單功能是否啟用"""
        return current_app.config.get('TOKEN_BLACKLIST_ENABLED', True)
    
    @classmethod
    def add_to_blacklist(cls, jti: str, expires_delta: timedelta = None):
        """將 Token JTI 加入黑名單
        
        Args:
            jti: JWT Token 的唯一識別碼
            expires_delta: Token 剩餘有效時間（用於設定 Redis TTL）
        
        Returns:
            bool: 是否成功加入
        """
        if not cls.is_enabled():
            return False
            
        r = cls._get_redis()
        if r is None:
            return False
        
        try:
            # 預設 TTL 為 Access Token 過期時間（避免黑名單無限增長）
            if expires_delta is None:
                expires_delta = current_app.config.get(
                    'JWT_ACCESS_TOKEN_EXPIRES', 
                    timedelta(hours=1)
                )
            
            # setex: 設定值並帶 TTL（秒）
            ttl_seconds = int(expires_delta.total_seconds())
            if ttl_seconds <= 0:
                ttl_seconds = 3600  # 最少保留 1 小時
                
            r.setex(
                f'{cls._prefix}{jti}',
                ttl_seconds,
                datetime.utcnow().isoformat()
            )
            current_app.logger.info(f'Token {jti[:8]}... 已加入黑名單 (TTL: {ttl_seconds}s)')
            return True
        except Exception as e:
            current_app.logger.error(f'Token 黑名單寫入失敗: {e}')
            return False
    
    @classmethod
    def is_blacklisted(cls, jti: str) -> bool:
        """檢查 Token JTI 是否在黑名單中
        
        Args:
            jti: JWT Token 的唯一識別碼
            
        Returns:
            bool: 是否已被撤銷
        """
        if not cls.is_enabled():
            return False
        
        r = cls._get_redis()
        if r is None:
            return False  # Redis 不可用時，降級為不檢查
        
        try:
            return r.exists(f'{cls._prefix}{jti}') > 0
        except Exception as e:
            current_app.logger.error(f'Token 黑名單查詢失敗: {e}')
            return False  # 查詢失敗時降級為不阻擋
    
    @classmethod
    def revoke_all_user_tokens(cls, user_id: str):
        """撤銷使用者的所有 Token（強制登出）
        
        注意：此方法需要額外的 user→jti 映射機制。
        目前版本僅在登出時撤銷當前 Token。
        完整實現需要在 generate_token 時記錄 user_id→jti 映射。
        """
        # TODO: 實現使用者層級的全量撤銷
        current_app.logger.info(f'User {user_id} 全量 Token 撤銷（待實現）')
        pass
