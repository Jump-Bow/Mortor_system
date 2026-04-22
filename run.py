"""
FEM 設備保養管理系統 - Application Entry Point
Run the Flask application
"""
from app import create_app
import os

# Create application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))

# GCP Internal Load Balancer ProxyFix
# 信任 LB 傳入的 X-Forwarded-Proto / X-Forwarded-For，
# 確保 Flask 產生的重導向 URL 使用 https:// 而非 http://
from werkzeug.middleware.proxy_fix import ProxyFix
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

if __name__ == '__main__':
    # Get host and port from environment or use defaults
    host = os.getenv('FLASK_HOST', '0.0.0.0')
    port = int(os.getenv('FLASK_PORT', 4999))
    debug = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    app.run(host=host, port=port, debug=debug)
