"""
Inspection API Tests
"""
from datetime import date, datetime
from app.models.Mortor_inspection import TJob, InspectionResult
from app.models.Mortor_abnormal import AbnormalCases


def test_get_dashboard_statistics(client, auth_headers, session):
    """測試儀表板統計"""
    response = client.get('/api/v1/inspection/statistics', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'abnormal_tracking' in data['data']
    assert 'inspection_tasks' in data['data']
    
    abnormal = data['data']['abnormal_tracking']
    assert 'today_abnormal' in abnormal
    assert 'today_attention' in abnormal
    assert 'accumulated_abnormal_open' in abnormal
    assert 'accumulated_attention_open' in abnormal
    
    tasks = data['data']['inspection_tasks']
    assert 'total_tasks_today' in tasks
    assert 'completed_today' in tasks


def test_query_inspection_records(client, auth_headers, session, equipment, admin_user):
    """測試查詢巡檢紀錄"""
    task = TJob(
        actid='TASK_REC_001',
        act_key='TASK001',
        equipmentid=equipment.id,
        act_mem_id=admin_user.id,
        mdate=date.today().strftime('%Y%m%d'),
    )
    session.add(task)
    session.commit()
    
    response = client.get('/api/v1/inspection/records', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'records' in data['data']
    assert 'total' in data['data']


def test_get_inspection_record_details(
    client,
    auth_headers,
    session,
    equipment,
    equipment_check_item,
    admin_user,
):
    """測試取得巡檢紀錄詳細資訊"""
    task = TJob(
        actid='TASK_REC_DETAIL_001',
        act_key='TASK001',
        equipmentid=equipment.id,
        act_mem_id=admin_user.id,
        mdate=date.today().strftime('%Y%m%d'),
    )
    session.add(task)
    session.commit()
    
    result = InspectionResult(
        actid=task.actid,
        item_id=equipment_check_item.item_id,
        equipmentid=equipment.id,
        measured_value='65.5',
        is_out_of_spec=1,  # 正常
        act_time=datetime.utcnow(),
        act_mem_id=admin_user.id
    )
    session.add(result)
    session.commit()
    
    response = client.get(
        f'/api/v1/inspection/records/{task.actid}/details',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'task' in data['data']
    assert 'equipment_list' in data['data']
    
    equipment_list = data['data']['equipment_list']
    assert isinstance(equipment_list, list)
    if equipment_list:
        assert 'check_items' in equipment_list[0]


def test_query_abnormal_tracking(
    client,
    auth_headers,
    session,
    equipment,
    equipment_check_item,
    admin_user,
):
    """測試異常追蹤查詢"""
    task = TJob(
        actid='TASK_ABN_001',
        act_key='TASK001',
        equipmentid=equipment.id,
        act_mem_id=admin_user.id,
        mdate=date.today().strftime('%Y%m%d'),
    )
    session.add(task)
    session.commit()
    
    result = InspectionResult(
        actid=task.actid,
        item_id=equipment_check_item.item_id,
        equipmentid=equipment.id,
        measured_value='95.0',
        is_out_of_spec=2,  # 異常
        act_time=datetime.utcnow(),
        act_mem_id=admin_user.id
    )
    session.add(result)
    session.commit()
    
    tracking = AbnormalCases(
        actid=result.actid,
        item_id=result.item_id,
        equipmentid=equipment.id,
        measured_value=result.measured_value,
        is_processed=False,
        abn_solution='尚未處理',
    )
    session.add(tracking)
    session.commit()
    
    response = client.get('/api/v1/inspection/abnormal/tracking', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'tracking_records' in data['data']


def test_query_records_with_date_filter(client, auth_headers, session):
    """測試帶日期篩選的巡檢紀錄查詢"""
    today_str = date.today().isoformat()
    
    response = client.get(
        f'/api/v1/inspection/records?start_date={today_str}&end_date={today_str}',
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
