"""
Test Configuration
"""
import os
import sys

from sqlalchemy.orm import scoped_session, sessionmaker

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import create_app, db
from app.models.Mortor_user import HrAccount, Role
from app.models.Mortor_organization import HrOrganization, TOrganization
from app.models.Mortor_equipment import TEquipment, EquitCheckItem


@pytest.fixture(scope='session')
def app():
    """Create application for testing"""
    app = create_app('testing')
    return app


@pytest.fixture(scope='session')
def _db(app):
    """Create database for testing"""
    with app.app_context():
        db.create_all()
        yield db
        db.drop_all()


@pytest.fixture(scope='function')
def session(_db):
    """Create a new database session for a test"""
    connection = _db.engine.connect()
    transaction = connection.begin()

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)
    _db.session = session
    
    yield session
    
    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture(scope='function')
def client(app, session):
    """Create a test client"""
    return app.test_client()


@pytest.fixture
def admin_role(session):
    """Create admin role"""
    role = Role(role_name='管理者', description='系統管理員')
    session.add(role)
    session.commit()
    return role


@pytest.fixture
def user_role(session):
    """Create user role"""
    role = Role(role_name='使用者', description='一般使用者')
    session.add(role)
    session.commit()
    return role


@pytest.fixture
def admin_user(session, admin_role):
    """Create admin user"""
    user = HrAccount(
        id='admin',
        name='系統管理員',
    )
    user.set_password('1234qwer5T')
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def normal_user(session, user_role):
    """Create normal user"""
    user = HrAccount(
        id='user1',
        name='測試使用者',
    )
    user.set_password('password123')
    session.add(user)
    session.commit()
    return user


@pytest.fixture
def organization(session):
    """Create test organization"""
    org = HrOrganization(
        organizationid='ORG001',
        organizationname='測試組織'
    )
    session.add(org)
    session.commit()
    return org


@pytest.fixture
def facility(session):
    """Create test facility"""
    facility = TOrganization(
        unitid='FAC001',
        unitname='測試設施',
        unittype='廠區',
    )
    session.add(facility)
    session.commit()
    return facility


@pytest.fixture
def equipment(session, facility):
    """Create test equipment"""
    equipment = TEquipment(
        id='EQ001',
        name='測試設備',
        unitid=facility.unitid,
    )
    session.add(equipment)
    session.commit()
    return equipment


@pytest.fixture
def equipment_check_item(session, equipment):
    """Create test equipment check item"""
    item = EquitCheckItem(
        itemid='ITEM001',
        equipmentid=equipment.id,
        itemname='溫度',
        sortorder=1,
        ulspec='80',
        llspec='30',
    )
    session.add(item)
    session.commit()
    return item


@pytest.fixture
def inspection_task(session, equipment, normal_user):
    """Create a basic inspection task"""
    task = TJob(
        actid='TASK001',
        actkey='TASK001',
        equipmentid=equipment.id,
        mdate=date.today(),
        actmemid=normal_user.id,
    )
    session.add(task)
    session.commit()
    return task


@pytest.fixture
def auth_headers(client, admin_user):
    """Get authentication headers"""
    response = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': '1234qwer5T',
        'login_type': 'local'
    })
    
    data = response.get_json()
    token = data['data']['token']
    
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
