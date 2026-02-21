"""
Authentication API Tests
"""


def test_login_success(client, admin_user):
    """測試成功登入"""
    response = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': '1234qwer5T',
        'login_type': 'local'
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'token' in data['data']
    assert 'refresh_token' in data['data']
    assert data['data']['user']['id'] == 'admin'


def test_login_wrong_password(client, admin_user):
    """測試錯誤密碼"""
    response = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': 'wrongpassword',
        'login_type': 'local'
    })
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['status'] == 'error'
    assert '帳號或密碼錯誤' in data['message']


def test_login_user_not_exist(client):
    """測試使用者不存在"""
    response = client.post('/api/v1/auth/login', json={
        'username': 'nonexistent',
        'password': 'password',
        'login_type': 'local'
    })
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['status'] == 'error'


def test_login_missing_fields(client):
    """測試缺少必填欄位"""
    response = client.post('/api/v1/auth/login', json={
        'username': 'admin'
    })
    
    assert response.status_code == 400
    data = response.get_json()
    assert data['status'] == 'error'
    assert '缺少必填欄位' in data['message']


def test_verify_token(client, auth_headers):
    """測試驗證 Token"""
    response = client.get('/api/v1/auth/verify', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['valid'] is True
    assert 'user' in data['data']


def test_verify_token_without_auth(client):
    """測試無 Token 驗證"""
    response = client.get('/api/v1/auth/verify')
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['status'] == 'error'


def test_get_current_user(client, auth_headers):
    """測試取得當前使用者"""
    response = client.get('/api/v1/auth/me', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['data']['user']['id'] == 'admin'


def test_logout(client, auth_headers):
    """測試登出"""
    response = client.post('/api/v1/auth/logout', headers=auth_headers)
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert data['message'] == 'Successfully logged out'


def test_refresh_token(client, admin_user):
    """測試 Token 重新整理"""
    # First login to get refresh token
    login_response = client.post('/api/v1/auth/login', json={
        'username': 'admin',
        'password': '1234qwer5T',
        'login_type': 'local'
    })
    
    login_data = login_response.get_json()
    refresh_token = login_data['data']['refresh_token']
    
    # Refresh the token
    response = client.post('/api/v1/auth/refresh', json={
        'refresh_token': refresh_token
    })
    
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'success'
    assert 'token' in data['data']


def test_logout_error_handling(client, auth_headers, monkeypatch):
    """測試登出時發生錯誤的處理"""
    from app.models.Mortor_system_log import UserLog
    
    # Mock UserLog.log_action to raise an exception
    def mock_log_action(*args, **kwargs):
        raise Exception("Database error during logging")
        
    monkeypatch.setattr(UserLog, 'log_action', mock_log_action)
    
    response = client.post('/api/v1/auth/logout', headers=auth_headers)
    
    # Expect 500 error as we catch the exception and return 500
    assert response.status_code == 500
    data = response.get_json()
    assert data['status'] == 'error'
    assert '登出過程發生錯誤' in data['message']
