import requests
import json
import sys

BASE_URL = 'http://localhost:4999/api'

def login():
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
        if response:
            print(response.text)
        sys.exit(1)

def verify_download(token):
    print("\n--- Verifying /api/tasks/download ---")
    url = f"{BASE_URL}/tasks/download"
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))
        
        tasks = data['data']['tasks']
        if not tasks:
            print("No tasks found.")
            return

        task = tasks[0]
        required_fields = [
            'task_id', 'task_number', 'equipment_id', 'equipment_name', 
            'inspection_date', 'status', 'description', 'assigned_to', 
            'assigned_user_name', 'completion_rate', 'facility_id', 
            'facility_name', 'equipment_check_items'
        ]
        
        missing = [f for f in required_fields if f not in task]
        if missing:
            print(f"FAILED: Missing fields in task: {missing}")
        else:
            print("SUCCESS: All required fields present in task.")
            
        if not isinstance(task['equipment_check_items'], list):
             print("FAILED: equipment_check_items should be a list")
        elif len(task['equipment_check_items']) > 0 and 'item_id' not in task['equipment_check_items'][0]:
             print("FAILED: equipment_check_items items should be check item objects")
        else:
             print("SUCCESS: equipment_check_items structure looks correct.")

    except Exception as e:
        print(f"Download failed: {e}")
        if response:
            print(response.text)

def verify_list(token):
    print("\n--- Verifying /api/tasks/list ---")
    url = f"{BASE_URL}/tasks/list"
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(json.dumps(data, indent=2, ensure_ascii=False))

        tasks = data['data']['tasks']
        if not tasks:
            print("No tasks found.")
            return

        task = tasks[0]
        required_fields = [
            'task_id', 'task_number', 'equipment_id', 'equipment_name', 
            'inspection_date', 'status', 'description', 'assigned_to', 
            'assigned_user_name', 'completion_rate', 'facility_id', 
            'facility_name', 'equipment_check_items'
        ]
        
        missing = [f for f in required_fields if f not in task]
        if missing:
            print(f"FAILED: Missing fields in task: {missing}")
        else:
            print("SUCCESS: All required fields present in task.")

        if not isinstance(task['equipment_check_items'], list):
             print("FAILED: equipment_check_items should be a list")
        elif len(task['equipment_check_items']) > 0 and 'item_id' not in task['equipment_check_items'][0]:
             print("FAILED: equipment_check_items items should be check item objects")
        else:
             print("SUCCESS: equipment_check_items structure looks correct.")

    except Exception as e:
        print(f"List failed: {e}")
        if response:
            print(response.text)

if __name__ == "__main__":
    token = login()
    verify_download(token)
    verify_list(token)
