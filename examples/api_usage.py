"""
API Usage Examples
API 使用範例腳本
"""
import requests
import json
from datetime import datetime

# Base URL
BASE_URL = 'http://localhost:5000/api/v1'

# Store token globally
token = None


def print_response(response):
    """Print formatted response"""
    print(f"\nStatus Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def login(username='admin', password='1234qwer5T'):
    """Example: User login"""
    global token
    
    print("\n" + "="*60)
    print("1. User Login")
    print("="*60)
    
    url = f'{BASE_URL}/auth/login'
    payload = {
        'username': username,
        'password': password,
        'login_type': 'local'
    }
    
    response = requests.post(url, json=payload)
    print_response(response)
    
    if response.status_code == 200:
        data = response.json()
        token = data['data']['token']
        print(f"\n✓ Login successful! Token: {token[:50]}...")
    
    return token


def get_headers():
    """Get authorization headers"""
    return {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }


def get_current_user():
    """Example: Get current user info"""
    print("\n" + "="*60)
    print("2. Get Current User")
    print("="*60)
    
    url = f'{BASE_URL}/auth/me'
    response = requests.get(url, headers=get_headers())
    print_response(response)


def get_dashboard_statistics():
    """Example: Get dashboard statistics"""
    print("\n" + "="*60)
    print("3. Get Dashboard Statistics")
    print("="*60)
    
    url = f'{BASE_URL}/inspection/statistics'
    response = requests.get(url, headers=get_headers())
    print_response(response)


def get_organization_tree():
    """Example: Get organization tree"""
    print("\n" + "="*60)
    print("4. Get Organization Tree")
    print("="*60)
    
    url = f'{BASE_URL}/organizations/tree'
    response = requests.get(url, headers=get_headers())
    print_response(response)


def list_tasks():
    """Example: List inspection tasks"""
    print("\n" + "="*60)
    print("5. List Inspection Tasks")
    print("="*60)
    
    url = f'{BASE_URL}/tasks/list'
    params = {
        'page': 1,
        'page_size': 10
    }
    response = requests.get(url, params=params, headers=get_headers())
    print_response(response)


def download_tasks():
    """Example: Download tasks for mobile app"""
    print("\n" + "="*60)
    print("6. Download Tasks (for Mobile App)")
    print("="*60)
    
    url = f'{BASE_URL}/tasks/download'
    params = {
        'date': datetime.now().strftime('%Y-%m-%d')
    }
    response = requests.get(url, params=params, headers=get_headers())
    print_response(response)


def query_inspection_records():
    """Example: Query inspection records"""
    print("\n" + "="*60)
    print("7. Query Inspection Records")
    print("="*60)
    
    url = f'{BASE_URL}/inspection/records'
    params = {
        'start_date': '2025-10-01',
        'end_date': '2025-10-31',
        'page': 1,
        'page_size': 10
    }
    response = requests.get(url, params=params, headers=get_headers())
    print_response(response)


def run_all_examples():
    """Run all API examples"""
    print("\n" + "#"*60)
    print("# FEM API Usage Examples")
    print("#"*60)
    
    try:
        # Authentication
        login()
        
        if not token:
            print("\n✗ Login failed. Cannot continue with other examples.")
            return
        
        get_current_user()
        get_dashboard_statistics()
        get_organization_tree()
        list_tasks()
        download_tasks()
        query_inspection_records()
        
        print("\n" + "#"*60)
        print("# All examples completed!")
        print("#"*60)
        
    except requests.exceptions.ConnectionError:
        print("\n✗ Error: Cannot connect to server.")
        print("Please make sure the server is running: python run.py")
    except Exception as e:
        print(f"\n✗ Error: {str(e)}")


if __name__ == '__main__':
    run_all_examples()
