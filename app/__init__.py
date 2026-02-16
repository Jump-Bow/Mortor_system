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
    
    # CORS Configuration - Allow all origins for API
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
            "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    
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
            AbnormalCases, SysLog, UserLog
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
            'SysLog': SysLog,
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
    """Register error handlers"""
    from app.models.Mortor_system_log import SysLog
    import traceback
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            'status': 'error',
            'error_code': 'BAD_REQUEST',
            'message': '請求參數錯誤'
        }), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        SysLog.create(level='WARN', module='Auth')
        return jsonify({
            'status': 'error',
            'error_code': 'UNAUTHORIZED',
            'message': '未授權，需要登入'
        }), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        SysLog.create(level='WARN', module='Auth')
        return jsonify({
            'status': 'error',
            'error_code': 'FORBIDDEN',
            'message': '禁止訪問，權限不足'
        }), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'status': 'error',
            'error_code': 'NOT_FOUND',
            'message': '資源不存在'
        }), 404
    
    @app.errorhandler(409)
    def conflict(error):
        return jsonify({
            'status': 'error',
            'error_code': 'CONFLICT',
            'message': '資源衝突'
        }), 409
    
    @app.errorhandler(422)
    def unprocessable_entity(error):
        return jsonify({
            'status': 'error',
            'error_code': 'UNPROCESSABLE_ENTITY',
            'message': '資料驗證失敗'
        }), 422
    
    @app.errorhandler(429)
    def too_many_requests(error):
        return jsonify({
            'status': 'error',
            'error_code': 'TOO_MANY_REQUESTS',
            'message': '請求過於頻繁'
        }), 429
    
    @app.errorhandler(500)
    def internal_server_error(error):
        app.logger.error(f'Internal Server Error: {error}')
        SysLog.create(level='ERROR', module='System')
        return jsonify({
            'status': 'error',
            'error_code': 'INTERNAL_SERVER_ERROR',
            'message': '伺服器內部錯誤'
        }), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        SysLog.create(level='ERROR', module='System')
        return jsonify({
            'status': 'error',
            'error_code': 'SERVICE_UNAVAILABLE',
            'message': '服務暫時無法使用'
        }), 503


def setup_logging(app: Flask) -> None:
    """Setup application logging"""
    if not app.debug and not app.testing:
        # Create logs directory
        os.makedirs('logs', exist_ok=True)
        
        # File handler
        file_handler = RotatingFileHandler(
            app.config['LOG_FILE'],
            maxBytes=10240000,  # 10MB
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            app.config['LOG_FORMAT']
        ))
        file_handler.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(getattr(logging, app.config['LOG_LEVEL']))
        app.logger.info('FEM Application startup')
