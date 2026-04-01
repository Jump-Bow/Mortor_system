"""
FEM 設備保養管理系統 - 配置文件
Configuration Management for Development, Testing and Production Environments
"""
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""
    
    # Application
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    APP_NAME = 'FEM 設備保養管理系統'
    
    # Mock Data Configuration
    USE_MOCK_DATA = os.getenv('USE_MOCK_DATA', 'false').lower() == 'true'
    MOCK_DATA_PATH = os.getenv('MOCK_DATA_PATH', './data/mock_data.json')
    
    # Database
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_POOL_SIZE = 10
    SQLALCHEMY_POOL_RECYCLE = 3600
    SQLALCHEMY_MAX_OVERFLOW = 20
    
    # JWT Configuration
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-in-production')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_ALGORITHM = 'HS256'
    # Allow small clock skew when decoding (seconds)
    JWT_LEEWAY = int(os.getenv('JWT_LEEWAY', '30'))
    
    # Azure Entra ID (Azure AD)
    USE_AZURE_AD = os.getenv('USE_AZURE_AD', 'false').lower() == 'true'
    AZURE_CLIENT_ID = os.getenv('AZURE_CLIENT_ID', '')
    AZURE_CLIENT_SECRET = os.getenv('AZURE_CLIENT_SECRET', '')
    AZURE_TENANT_ID = os.getenv('AZURE_TENANT_ID', '')
    AZURE_AUTHORITY = f"https://login.microsoftonline.com/{os.getenv('AZURE_TENANT_ID', '')}"
    AZURE_REDIRECT_URI = os.getenv('AZURE_REDIRECT_URI', 'http://localhost:5000/api/v1/auth/azure/callback')
    AZURE_SCOPE = ["User.Read"]
    
    # AIMS Integration
    USE_MOCK_AIMS = os.getenv('USE_MOCK_AIMS', 'true').lower() == 'true'
    AIMS_API_URL = os.getenv('AIMS_API_URL', '')
    AIMS_API_KEY = os.getenv('AIMS_API_KEY', '')
    
    # File Upload
    UPLOAD_PROVIDER = os.getenv('UPLOAD_PROVIDER', 'local')  # 'local' or 'gcs'
    UPLOAD_FOLDER = os.getenv('UPLOAD_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads'))
    MAX_CONTENT_LENGTH = int(os.getenv('MAX_UPLOAD_SIZE', 16 * 1024 * 1024))  # 16MB default
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', '')
    
    # Pagination
    ITEMS_PER_PAGE = 20
    MAX_ITEMS_PER_PAGE = 1000
    
    # Cache & Redis
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    USE_REDIS = os.getenv('USE_REDIS', 'false').lower() == 'true'
    CACHE_TYPE = 'redis' if os.getenv('USE_REDIS', 'false').lower() == 'true' else 'SimpleCache'
    CACHE_REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Token Blacklist（使用 Redis 存儲已撤銷的 Token JTI）
    TOKEN_BLACKLIST_ENABLED = os.getenv('TOKEN_BLACKLIST_ENABLED', 'true').lower() == 'true'
    
    # Security
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(hours=8)
    
    # CORS - 允許的來源域名（各環境可覆蓋）
    # 注意：不可使用 "*" 搭配 supports_credentials=True（違反 CORS 規範）
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5000',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5000',
    ]
    
    # API Rate Limiting
    RATELIMIT_ENABLED = os.getenv('RATELIMIT_ENABLED', 'true').lower() == 'true'
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'logs/fem.log'
    
    # AIMS Integration
    AIMS_API_URL = os.getenv('AIMS_API_URL', '')
    AIMS_API_KEY = os.getenv('AIMS_API_KEY', '')
    AIMS_TIMEOUT = 30


class DevelopmentConfig(Config):
    """Development environment configuration"""
    
    DEBUG = True
    TESTING = False
    
    # JWT Configuration - Extended for development
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)  # 延長至 8 小時方便開發
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)  # 延長至 30 天
    
    # Database - Development (SQLite for local, PostgreSQL for remote dev)
    DB_TYPE = os.getenv('DEV_DB_TYPE', 'sqlite')
    
    if DB_TYPE == 'sqlite':
        # SQLite for local development
        DB_PATH = os.getenv('DEV_DB_PATH', './data/fem_dev.db')

        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Define the path for the database file inside the 'data' subfolder
        db_path = os.path.join(script_dir, 'data', 'fem_dev.db')

        SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    else:
        # PostgreSQL for remote development
        DB_SERVER = os.getenv('DEV_DB_SERVER', 'localhost')
        DB_PORT = os.getenv('DEV_DB_PORT', '5432')
        DB_NAME = os.getenv('DEV_DB_NAME', 'fem_dev')
        DB_USER = os.getenv('DEV_DB_USER', 'fem_admin')
        DB_PASSWORD = os.getenv('DEV_DB_PASSWORD', '')
        
        SQLALCHEMY_DATABASE_URI = (
            f"postgresql+psycopg2://{DB_USER}:{DB_PASSWORD}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"
        )
    
    SQLALCHEMY_ECHO = True
    SESSION_COOKIE_SECURE = False
    LOG_LEVEL = 'DEBUG'
    
    # CORS - 開發環境允許所有本地域名
    CORS_ORIGINS = [
        'http://localhost:3000',
        'http://localhost:5000',
        'http://127.0.0.1:3000',
        'http://127.0.0.1:5000',
    ]


class TestingConfig(Config):
    """Testing environment configuration"""
    
    DEBUG = True
    TESTING = True
    
    # Database - Testing (In-memory SQLite)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # JWT for testing
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=5)
    
    SESSION_COOKIE_SECURE = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production environment configuration"""
    
    DEBUG = False
    TESTING = False
    
    # Database - Production (PostgreSQL)
    DB_SERVER = os.getenv('PROD_DB_SERVER', 'localhost')
    DB_PORT = os.getenv('PROD_DB_PORT', '5432')
    DB_NAME = os.getenv('PROD_DB_NAME', 'fem_prod')
    DB_USER = os.getenv('PROD_DB_USER', 'fem_admin')
    DB_PASSWORD = os.getenv('PROD_DB_PASSWORD', '')
    
    import urllib.parse
    # URL encode password to handle special characters (@, :, /, etc.)
    encoded_password = urllib.parse.quote_plus(DB_PASSWORD) if DB_PASSWORD else ''
    
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg2://{DB_USER}:{encoded_password}@{DB_SERVER}:{DB_PORT}/{DB_NAME}"
    )
    
    # Enhanced Security for Production
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'  # OAuth SSO redirect 需要 Lax；Strict 會導致 Edge SSO 後 session cookie 遺失
    
    # Cache - Redis for Production
    CACHE_TYPE = 'RedisCache'
    CACHE_REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
    CACHE_REDIS_PORT = os.getenv('REDIS_PORT', 6379)
    CACHE_REDIS_DB = 0
    CACHE_REDIS_PASSWORD = os.getenv('REDIS_PASSWORD', '')
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    UPLOAD_PROVIDER = 'gcs'  # 在 Cloud Run 預設切換為 GCS
    
    # CORS - 生產環境僅允許正式域名
    CORS_ORIGINS = [
        os.getenv('CORS_ORIGIN_1', 'https://fem.chimei.com'),
        os.getenv('CORS_ORIGIN_2', ''),
    ]


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}


def get_config(env: str = None) -> Config:
    """Get configuration based on environment"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')
    return config.get(env, config['default'])
