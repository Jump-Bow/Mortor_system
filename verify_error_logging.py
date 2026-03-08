import requests
import sys
import time
import os
from app import create_app
from app.models.Mortor_system_log import SystemLog

BASE_URL = 'http://localhost:4999/api/v1'

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
        # If server not running, we might still want to check app context part
        return None

def check_logs():
    print("\n--- Checking System Logs ---")
    app = create_app('development')
    with app.app_context():
        # Get latest logs
        logs = SystemLog.query.order_by(SystemLog.timestamp.desc()).limit(5).all()
        for log in logs:
            print(f"[{log.level}] {log.module}: {log.log_id}")
            
        # Test direct creation
        print("\n--- Testing Direct Log Creation ---")
        log = SystemLog.create(level='INFO', module='Test')
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

if __name__ == "__main__":
    # This script assumes the server is running for the first part, 
    # but can still check the database direct part if not.
    token = login_admin()
    if token:
        print("Logged in successfully.")
    else:
        print("Server might not be running, skipping API triggers.")
    
    check_logs()
