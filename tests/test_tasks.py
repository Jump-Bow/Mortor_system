"""
Tasks API Tests
"""
from datetime import date
from app.models.Mortor_inspection import TJob


def test_download_tasks(client, auth_headers, session, equipment, equipment_check_item, normal_user):
    """測試下載任務"""
    task = TJob(
        actid='TASK_DOWNLOAD_001',
        actkey='TASK001',
        equipmentid=equipment.id,
        actmemid=normal_user.id,
        mdate=date.today(),
    )
    session.add(task)
    session.commit()
    
    response = client.get(
        f'/api/v1/tasks/download?user_id={normal_user.id}',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'tasks' in data['data']
    assert isinstance(data['data']['tasks'], list)
    if data['data']['tasks']:
        first = data['data']['tasks'][0]
        assert 'equipment_check_items' in first
        assert isinstance(first['equipment_check_items'], list)


def test_list_tasks(client, auth_headers, session, equipment, equipment_check_item, admin_user):
    """測試任務列表"""
    task1 = TJob(
        actid='TASK_LIST_001',
        actkey='TASK001',
        equipmentid=equipment.id,
        actmemid=admin_user.id,
        mdate=date.today(),
    )
    task2 = TJob(
        actid='TASK_LIST_002',
        actkey='TASK002',
        equipmentid=equipment.id,
        actmemid=admin_user.id,
        mdate=date.today(),
    )
    session.add_all([task1, task2])
    session.commit()
    
    response = client.get('/api/v1/tasks/list', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'tasks' in data['data']
    assert 'pagination' in data['data']


def test_get_task_detail(client, auth_headers, session, equipment, admin_user):
    """測試取得任務詳情"""
    task = TJob(
        actid='TASK_DETAIL_001',
        actkey='TASK001',
        equipmentid=equipment.id,
        actmemid=admin_user.id,
        mdate=date.today(),
    )
    session.add(task)
    session.commit()
    
    response = client.get(
        f'/api/v1/tasks/{task.actid}',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['task']['actkey'] == 'TASK001'


def test_list_tasks_with_filters(client, auth_headers, session, equipment, admin_user):
    """測試帶篩選條件的任務列表"""
    for i in range(5):
        task = TJob(
            actid=f'TASK_FILTER_{i}',
            actkey=f'TASK00{i}',
            equipmentid=equipment.id,
            actmemid=admin_user.id,
            mdate=date.today(),
        )
        session.add(task)
    session.commit()
    
    response = client.get(
        '/api/v1/tasks/list',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
