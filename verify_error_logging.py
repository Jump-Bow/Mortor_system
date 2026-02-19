import requests
import sys
import time
from app import create_app
from app.models.Mortor_system_log import SystemLog

BASE_URL = 'http://localhost:4999/api'

def login_admin():
    url = f"{BASE_URL}/auth/login"
    payload = {
        "username": "admin",
        "password": "1234qwer5T",
        "login_type": "local"
    }
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        return response.json()['data']['token']
    except Exception as e:
        print(f"Login failed: {e}")
        sys.exit(1)

def trigger_401():
    print("\n--- Triggering 401 Unauthorized ---")
    url = f"{BASE_URL}/tasks/list"
    # No auth header
    response = requests.get(url)
    print(f"Response Status: {response.status_code}")
    if response.status_code == 401:
        print("SUCCESS: Got 401")
    else:
        print(f"FAILED: Expected 401, got {response.status_code}")

def trigger_403(token):
    print("\n--- Triggering 403 Forbidden ---")
    # We need a non-admin user to trigger 403 on admin-only endpoints.
    # But currently we only have admin login in this script.
    # Let's try to access an endpoint that doesn't exist or try to delete a task without permission if we were a normal user.
    # Alternatively, we can try to access a resource that belongs to another user if we were a normal user.
    # Since we are admin, we have access to everything.
    # Let's try to create a user with a fake token or just skip this for now if we can't easily switch users.
    # Actually, we can try to access a route that explicitly forbids even admin? Unlikely.
    # Let's try to login as a normal user if possible.
    # Assuming 'user' exists with password 'password' or similar.
    # If not, we can skip 403 verification or try to mock it.
    
    # Let's try to access a route that requires a specific role that admin might not have? No, admin has all.
    # Let's try to simulate 403 by sending a token that is valid but for a user that is blocked?
    pass

def check_logs():
    print("\n--- Checking System Logs ---")
    app = create_app('development')
    with app.app_context():
        # Get latest logs
        logs = SystemLog.query.order_by(SystemLog.created_at.desc()).limit(5).all()
        for log in logs:
            print(f"[{log.log_level}] {log.module_name}: {log.message}")
            
        # Check for specific logs we expect
        found_401 = any("Unauthorized access" in log.message for log in logs)
        found_500 = any("Internal Server Error" in log.message for log in logs)
        
        if found_401:
            print("SUCCESS: Found 401 log entry.")
        else:
            print("FAILED: Did not find 401 log entry.")

        if found_500:
            print("SUCCESS: Found 500 log entry.")
        else:
            print("FAILED: Did not find 500 log entry.")
            
        # Test direct creation
        print("\n--- Testing Direct Log Creation ---")
        log = SystemLog.create(level='INFO', module='Test', message='Direct test log')
        if log:
            print(f"Direct log created: {log.log_id}")
            # Check if we can read it back
            read_log = SystemLog.query.get(log.log_id)
            if read_log:
                print("SUCCESS: Read back direct log.")
            else:
                print("FAILED: Could not read back direct log.")
        else:
            print("FAILED: Could not create direct log.")

def trigger_500(token):
    print("\n--- Triggering 500 Internal Server Error ---")
    url = f"{BASE_URL}/tasks/list"
    headers = {'Authorization': f'Bearer {token}'}
    # We need to modify the server to raise 500 first
    response = requests.get(url, headers=headers)
    print(f"Response Status: {response.status_code}")
    if response.status_code == 500:
        print("SUCCESS: Got 500")
    else:
        print(f"FAILED: Expected 500, got {response.status_code}")

if __name__ == "__main__":
    token = login_admin()
    trigger_401()
    trigger_500(token)
    
    # Wait a bit for logs to be written
    time.sleep(1)
    
    check_logs()
