"""
Swagger UI Configuration
提供 API 文件的 Swagger UI 介面
"""
from flask import Blueprint, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
import os

# Swagger UI configuration
SWAGGER_URL = '/api/docs'  # Swagger UI 訪問路徑
API_URL = '/api/swagger.json'  # Swagger JSON 規格檔案路徑

# 建立 Swagger UI Blueprint
swagger_ui_blueprint = get_swaggerui_blueprint(
    SWAGGER_URL,
    API_URL,
    config={
        'app_name': "FEM 巡檢管理系統 API",
        'docExpansion': 'list',  # 預設展開層級: 'none', 'list', 'full'
        'defaultModelsExpandDepth': 3,
        'defaultModelExpandDepth': 3,
        'displayRequestDuration': True,
        'filter': True,  # 啟用搜尋過濾功能
        'showExtensions': True,
        'showCommonExtensions': True,
        'tryItOutEnabled': True,  # 預設啟用 "Try it out" 功能
        'persistAuthorization': True,  # 保持授權資訊
        'layout': 'BaseLayout',
        'deepLinking': True,  # 啟用深層連結
        'displayOperationId': False,
        'validatorUrl': None  # 停用線上驗證器
    }
)

# 建立 Blueprint 來提供 swagger.json 檔案
swagger_static_blueprint = Blueprint('swagger_static', __name__)


@swagger_static_blueprint.route('/api/swagger.json')
def swagger_json():
    """提供 Swagger JSON 規格檔案"""
    swagger_dir = os.path.dirname(__file__)
    return send_from_directory(swagger_dir, 'swagger.json')
