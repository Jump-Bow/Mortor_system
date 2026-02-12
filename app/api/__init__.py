"""
API Blueprints Package
"""
from app.api.Mortor_auth import auth_bp
from app.api.Mortor_tasks import tasks_bp
from app.api.Mortor_results import results_bp
from app.api.Mortor_inspection import inspection_bp
from app.api.Mortor_organizations import organizations_bp
from app.api.Mortor_roles import roles_bp

__all__ = [
    'auth_bp',
    'tasks_bp',
    'results_bp',
    'inspection_bp',
    'organizations_bp',
    'roles_bp',
]
