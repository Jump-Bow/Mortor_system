"""
FEM 設備保養管理系統 - Application Factory
Flask Application Initialization with Blueprint Registration
"""
from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_caching import Cache
# from flask_talisman import Talisman
from flask_cors import CORS
from flask_wtf.csrf import CSRFProtect
from config import get_config
import logging
from logging.handlers import RotatingFileHandler
import os

# Initialize extensions
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
cache = Cache()
csrf = CSRFProtect()


def create_app(config_name: str = None) -> Flask:
    """
    Application Factory Pattern
    
    Args:
        config_name: Configuration environment name (development/testing/production)
        
    Returns:
        Flask application instance
    """
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.getenv('FLASK_ENV', 'development')
    app.config.from_object(get_config(config_name))
    
    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    cache.init_app(app)
    csrf.init_app(app)
    
    # CORS Configuration - 使用 config 中的白名單（禁止萬用字元 + credentials）
    CORS(app, resources={
        r"/api/*": {
            "origins": app.config.get('CORS_ORIGINS', []),
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    
    # 全局 API 速率限制（使用 Redis 滑動窗口）
    from app.middleware.rate_limiter import RateLimiter
    RateLimiter.init_app(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Create upload folders
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'photos'), exist_ok=True)
    
    # Login manager configuration
    login_manager.login_view = 'web.login'
    login_manager.login_message = '請先登入系統'
    login_manager.login_message_category = 'warning'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.Mortor_user import HrAccount
        return HrAccount.query.get(user_id)
    
    # Shell context for flask shell
    @app.shell_context_processor
    def make_shell_context():
        from app.models import (
            TOrganization, HrOrganization, HrAccount, Role,
            TEquipment, EquitCheckItem, TJob, InspectionResult,
            AbnormalCases, SystemLog, UserLog
        )
        return {
            'db': db,
            'HrAccount': HrAccount,
            'Role': Role,
            'TOrganization': TOrganization,
            'HrOrganization': HrOrganization,
            'TEquipment': TEquipment,
            'EquitCheckItem': EquitCheckItem,
            'TJob': TJob,
            'InspectionResult': InspectionResult,
            'AbnormalCases': AbnormalCases,
            'SystemLog': SystemLog,
            'UserLog': UserLog,
        }
    
    app.logger.info(f'FEM Application started in {config_name} mode')
    
    # Log Database Connection (Masked)
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI', 'Not Set')
    if db_uri and 'sqlite' not in db_uri:
        import re
        # Mask password in postgresql://user:password@host...
        masked_uri = re.sub(r':([^:@]{1,})@', ':****@', db_uri)
        app.logger.info(f'Connecting to Database: {masked_uri}')
    else:
        app.logger.info(f'Connecting to Database: {db_uri}')
    
    # 5d: 啟動配置驗證
    _validate_config(app)
    
    return app


def register_blueprints(app: Flask) -> None:
    """Register application blueprints"""
    from app.api.Mortor_auth import auth_bp
    from app.api.Mortor_tasks import tasks_bp
    from app.api.Mortor_results import results_bp
    from app.api.Mortor_inspection import inspection_bp
    from app.api.Mortor_organizations import organizations_bp
    from app.api.Mortor_facilities import facilities_bp
    from app.api.Mortor_aims import aims_bp
    from app.api.Mortor_users import users_bp
    from app.api.Mortor_roles import roles_bp
    from app.api.Mortor_system_logs import system_logs_bp
    from app.Mortor_web_routes import web_bp
    from app.swagger import swagger_ui_blueprint, swagger_static_blueprint
    
    # Web UI blueprints (register at root only)
    app.register_blueprint(web_bp, url_prefix='/')
    
    # API v1 blueprints (explicit version)
    app.register_blueprint(auth_bp, url_prefix='/api/v1/auth')
    app.register_blueprint(tasks_bp, url_prefix='/api/v1/tasks')
    app.register_blueprint(results_bp, url_prefix='/api/v1/results')
    app.register_blueprint(inspection_bp, url_prefix='/api/v1/inspection')
    app.register_blueprint(aims_bp, url_prefix='/api/v1/aims')
    app.register_blueprint(organizations_bp, url_prefix='/api/v1/organizations')
    app.register_blueprint(facilities_bp, url_prefix='/api/v1/facilities')
    
    # API latest version (points to v1 currently)
    app.register_blueprint(auth_bp, url_prefix='/api/auth', name='auth_latest')
    app.register_blueprint(tasks_bp, url_prefix='/api/tasks', name='tasks_latest')
    app.register_blueprint(results_bp, url_prefix='/api/results', name='results_latest')
    app.register_blueprint(inspection_bp, url_prefix='/api/inspection', name='inspection_latest')
    app.register_blueprint(aims_bp, url_prefix='/api/aims', name='aims_latest')
    app.register_blueprint(organizations_bp, url_prefix='/api/organizations', name='organizations_latest')
    app.register_blueprint(facilities_bp, url_prefix='/api/facilities', name='facilities_latest')
    
    # API blueprints for system management
    app.register_blueprint(users_bp, url_prefix='/api/users')
    app.register_blueprint(roles_bp, url_prefix='/api/roles')  # 預留功能
    app.register_blueprint(system_logs_bp, url_prefix='/api/system-logs')
    
    # Swagger UI blueprints
    app.register_blueprint(swagger_ui_blueprint)
    app.register_blueprint(swagger_static_blueprint)
    
    # Exempt API routes from CSRF protection
    csrf.exempt(auth_bp)
    csrf.exempt(tasks_bp)
    csrf.exempt(results_bp)
    csrf.exempt(inspection_bp)
    csrf.exempt(aims_bp)
    csrf.exempt(organizations_bp)
    csrf.exempt(facilities_bp)
    csrf.exempt(users_bp)
    csrf.exempt(roles_bp)
    csrf.exempt(system_logs_bp)
    csrf.exempt(swagger_static_blueprint)
    
    app.logger.info('Blueprints registered successfully')


def register_error_handlers(app: Flask) -> None:
    """將錯誤處理委派給獨立模組（utils/error_handlers.py）"""
    from app.utils.error_handlers import register_error_handlers as _register
    _register(app)




def setup_logging(app: Flask) -> None:
    """設置應用程式日誌
    
    - Cloud Run (Production/K_SERVICE)：使用 JSON 結構化格式，由 Google Cloud Logging 自動解析
    - 本地開發：使用人類可讀的純文字格式，寫入 RotatingFileHandler
    """
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    
    if app.debug or app.testing:
        app.logger.setLevel(logging.DEBUG)
        return

    if app.config.get('FLASK_ENV') == 'production' or os.getenv('K_SERVICE'):
        # Cloud Run：JSON 結構化日誌，Google Cloud Logging 可正確解析 severity/module
        try:
            from pythonjsonlogger import jsonlogger
            json_formatter = jsonlogger.JsonFormatter(
                fmt='%(asctime)s %(name)s %(levelname)s %(message)s',
                rename_fields={'levelname': 'severity', 'asctime': 'time'}
            )
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(json_formatter)
            stream_handler.setLevel(log_level)
            app.logger.addHandler(stream_handler)
        except ImportError:
            # 降級：python-json-logger 未安裝時，使用純文字 stdout
            stream_handler = logging.StreamHandler()
            stream_handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            stream_handler.setLevel(log_level)
            app.logger.addHandler(stream_handler)
        
        app.logger.setLevel(log_level)
        app.logger.info('FEM Application logging to stdout (Cloud Run JSON mode)')
    else:
        # 本地開發：純文字格式，寫入 RotatingFileHandler
        os.makedirs('logs', exist_ok=True)
        formatter = logging.Formatter(
            app.config.get('LOG_FORMAT', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        file_handler = RotatingFileHandler(
            app.config.get('LOG_FILE', 'logs/fem.log'),
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        app.logger.addHandler(file_handler)
        app.logger.setLevel(log_level)
        app.logger.info('FEM Application logging to file')


def _validate_config(app: Flask) -> None:
    """5d: 啟動配置驗證 — 缺少關鍵設定時提早發出警告"""
    required_keys = [
        ('SECRET_KEY', '請設定 SECRET_KEY 環境變數'),
        ('JWT_SECRET_KEY', '請設定 JWT_SECRET_KEY 環境變數'),
        ('SQLALCHEMY_DATABASE_URI', '請設定資料庫連線字串'),
    ]
    for key, hint in required_keys:
        val = app.config.get(key)
        if not val or val in ('dev-secret-key', 'dev-jwt-secret-key', 'change-me-in-production'):
            app.logger.warning(f'[配置警告] {key} 未設定或使用預設值。{hint}')  

