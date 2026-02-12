#!/usr/bin/env python
"""
測試 /api/inspection/records API
驗證是否包含 org_name 和 assigned_user_name 欄位
"""
import requests
import json
import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from app import create_app
from app.auth.jwt_handler import JWTHandler

# Create app context
app = create_app('development')

with app.app_context():
    # Generate token for a normal user
    # generate_token returns (access_token, refresh_token)
    # User I0001, role 巡檢人員
    access_token, _ = JWTHandler.generate_token('I0001', 'I0001', '巡檢人員')
    
    # Make request
    headers = {'Authorization': f'Bearer {access_token}'}
    # Assuming the server is running on localhost:4999 from the user's context
    try:
        response = requests.get(
            'http://localhost:4999/api/v1/inspection/records',
            headers=headers,
            params={'page': 1, 'page_size': 3}
        )
        
        print("Status Code:", response.status_code)
        print("Headers:", response.headers)
        print("Response Text:", response.text)
        
        if response.status_code == 200:
            data = response.json()
            
            # Verify fields
            if data.get('status') == 'success' and data.get('data', {}).get('records'):
                print("\n" + "="*60)
                print("驗證欄位:")
                print("="*60)
                
                records = data['data']['records']
                if not records:
                    print("No records found.")
                
                for i, record in enumerate(records[:3], 1):
                    print(f"\n記錄 {i}:")
                    print(f"  ✓ task_number: {record.get('task_number')}")
                    print(f"  ✓ equipment_name: {record.get('equipment_name')}")
                    print(f"  ✓ assigned_user_name: {record.get('assigned_user_name')}")
                    print(f"  ✓ org_name: {record.get('org_name')}")
                    
                    # Check if fields exist (even if None)
                    if 'assigned_user_name' in record:
                        print("  ✓ Field 'assigned_user_name' exists")
                    else:
                        print("  ❌ Field 'assigned_user_name' MISSING")
                        
                    if 'org_name' in record:
                        print("  ✓ Field 'org_name' exists")
                    else:
                        print("  ❌ Field 'org_name' MISSING")
            else:
                print("API returned error or no data")
                print(data)
        else:
            print("Request failed")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("Could not connect to server. Is it running?")
