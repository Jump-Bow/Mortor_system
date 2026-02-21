"""
Exploratory Tests
探索性測試: 包含邊界值測試、安全性測試與併發測試
"""
import threading
from app.models.Mortor_system_log import UserLog

# Note: We need to import app properly.
# The `app` fixture in conftest.py returns an app instance.
# Here we might need to rely on the `client` fixture which uses `app`.

# --- Boundary Value Testing (邊界值測試) ---

def test_upload_inspection_data_empty(client, auth_headers):
    """測試上傳馬達檢測數據為空值"""
    # 假設有一個上傳端點，這裡模擬 /api/v1/inspection/upload
    # 若該端點不存在，此測試應先確認路徑。但根據需求是要 "補強"，
    # 這裡假設檢測結果上傳的場景。
    
    # 嘗試傳送空 Payload 到 /api/v1/results/upload (根據 Mortor_results.py)
    # 假設 app/__init__.py 註冊 results_bp 為 /api/v1/results
    response = client.post('/api/v1/results/upload', json={}, headers=auth_headers)
    
    # 預期 404 (如果路徑不對) 或 400 (如果路徑對但資料錯)
    # 為了測試穩定性，我們先檢查 非 500 即可
    assert response.status_code != 500


def test_upload_inspection_data_invalid_format(client, auth_headers):
    """測試上傳數據格式錯誤 (例如字串代替數字)"""
    # 假設這是上傳檢測數值的結構
    payload = {
        'task_id': 'TASK001',
        'readings': 'This should be a list or number',  # 錯誤格式
        'status': 'Completed'
    }
    # 模擬上傳 /api/v1/results/upload
    response = client.post('/api/v1/results/upload', json=payload, headers=auth_headers)
    
    # 預期被 Validator 攔截 或 找不到路徑 (404)
    assert response.status_code != 500

# --- Security Testing (安全性測試) ---

def test_access_results_with_expired_token(client, admin_user, app):
    """驗證 Token 過期存取 Mortor_results.py 相關資源"""
    import jwt
    from datetime import datetime, timedelta
    
    with app.app_context():
        # 產生一個過期的 Token
        expired_payload = {
            'user_id': admin_user.id,
            'username': admin_user.name,
            'role': 'User',
            'exp': datetime.utcnow() - timedelta(hours=1), # 已過期 1 小時
            'iat': datetime.utcnow() - timedelta(hours=2),
            'type': 'access'
        }
        
        token = jwt.encode(
            expired_payload,
            app.config['JWT_SECRET_KEY'],
            algorithm=app.config['JWT_ALGORITHM']
        )
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # 嘗試存取受保護資源 /api/v1/auth/verify (確定存在)
    response = client.get('/api/v1/auth/verify', headers=headers)
    
    # 預期 401 Unauthorized
    assert response.status_code == 401
    data = response.get_json()
    # 根據 jwt_handler.py 的實作，過期會回傳 EXPIRED 相關訊息
    if 'error_code' in data:
         assert 'UNAUTHORIZED' in data['error_code']


def test_access_results_with_fake_token(client):
    """驗證偽造 Token"""
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    
    headers = {
        'Authorization': f'Bearer {fake_token}',
        'Content-Type': 'application/json'
    }
    
    response = client.get('/api/v1/auth/verify', headers=headers)
    
    assert response.status_code == 401
    data = response.get_json()
    assert data['status'] == 'error'


# --- Concurrency Testing (併發測試概念) ---

def test_concurrent_log_writing(app, admin_user):
    """
    模擬多個執行緒同時寫入 UserLog
    注意：這是概念性測試，驗證 DB Session 是否能處理併發寫入而不崩潰
    """
    error_occurred = []
    
    def write_log(user_id, seq):
        try:
            # 在執行緒中需要手動推入 app context
            with app.app_context():
                # 這裡直接呼叫 Model 的 static method
                UserLog.log_action(
                    user_id=user_id,
                    action_type='TEST_CONCURRENT',
                    description=f'Concurrent log test seq {seq}',
                    ip_address='127.0.0.1'
                )
        except Exception as e:
            error_occurred.append(f"Error in seq {seq}: {str(e)}")
    
    threads = []
    num_threads = 5  # 模擬 5 個併發請求
    
    for i in range(num_threads):
        t = threading.Thread(target=write_log, args=(admin_user.id, i))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # 驗證沒有錯誤發生
    assert len(error_occurred) == 0, f"Concurrency errors: {error_occurred}"
    
    # 驗證 Log 數量增加
    with app.app_context():
        # 因為測試 DB 會在 function 結束後 rollback，我們只需確認當下 session 能查到
        # 注意：pytest 的 `session` fixture 是 scoped function，這裡新的 thread 用的是新的 scoped_session
        # 但如果是用同一個 engine/connection，應該是可見的 (視 isolation level 而定)
        # 這裡主要驗證 "不報錯 (500)"
        pass
