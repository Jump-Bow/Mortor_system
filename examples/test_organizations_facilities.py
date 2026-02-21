"""
測試 Organizations-Facilities API
測試新增的組織與設施關聯 API 端點

執行方式:
    python examples/test_organizations_facilities.py

注意事項:
    - 需要先啟動 Flask 應用程式
    - 需要有效的 JWT token
    - 確保資料庫已執行遷移指令
"""
import requests
import json

# 配置
BASE_URL = "http://localhost:5000/api/v1"
TOKEN = "YOUR_JWT_TOKEN_HERE"  # 請替換為實際的 JWT token

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}


def print_response(title: str, response: requests.Response):
    """格式化輸出 API 回應"""
    print(f"\n{'=' * 60}")
    print(f"{title}")
    print(f"{'=' * 60}")
    print(f"Status Code: {response.status_code}")
    print("Response:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))


def test_organizations_tree():
    """測試 1: 取得組織樹狀結構"""
    print("\n📋 測試 1: 取得組織樹狀結構")
    response = requests.get(f"{BASE_URL}/organizations/tree", headers=headers)
    print_response("Organizations Tree", response)
    return response.json()


def test_organization_detail(org_id: str, include_facilities: bool = False, include_users: bool = False):
    """測試 2: 取得組織詳情"""
    print(f"\n📋 測試 2: 取得組織詳情 (org_id={org_id})")
    params = {}
    if include_facilities:
        params['include_facilities'] = 'true'
    if include_users:
        params['include_users'] = 'true'
    
    response = requests.get(
        f"{BASE_URL}/organizations/{org_id}",
        headers=headers,
        params=params
    )
    print_response(f"Organization Detail ({org_id})", response)
    return response.json()


def test_organization_facilities(org_id: str, include_equipment: bool = False):
    """測試 3: 取得組織的所有設施"""
    print(f"\n📋 測試 3: 取得組織的所有設施 (org_id={org_id})")
    params = {}
    if include_equipment:
        params['include_equipment'] = 'true'
    
    response = requests.get(
        f"{BASE_URL}/organizations/{org_id}/facilities",
        headers=headers,
        params=params
    )
    print_response(f"Organization Facilities ({org_id})", response)
    return response.json()


def test_facilities_tree(org_id: str = None):
    """測試 4: 取得設施樹狀結構"""
    print("\n📋 測試 4: 取得設施樹狀結構")
    params = {}
    if org_id:
        params['org_id'] = org_id
    
    response = requests.get(
        f"{BASE_URL}/facilities/tree",
        headers=headers,
        params=params
    )
    print_response("Facilities Tree", response)
    return response.json()


def test_facilities_list(org_id: str = None, page: int = 1, page_size: int = 20):
    """測試 5: 取得設施列表"""
    print("\n📋 測試 5: 取得設施列表 (分頁)")
    params = {
        'page': page,
        'page_size': page_size
    }
    if org_id:
        params['org_id'] = org_id
    
    response = requests.get(
        f"{BASE_URL}/facilities/list",
        headers=headers,
        params=params
    )
    print_response("Facilities List", response)
    return response.json()


def test_facility_detail(facility_id: str, include_equipment: bool = False, include_children: bool = False):
    """測試 6: 取得設施詳情"""
    print(f"\n📋 測試 6: 取得設施詳情 (facility_id={facility_id})")
    params = {}
    if include_equipment:
        params['include_equipment'] = 'true'
    if include_children:
        params['include_children'] = 'true'
    
    response = requests.get(
        f"{BASE_URL}/facilities/{facility_id}",
        headers=headers,
        params=params
    )
    print_response(f"Facility Detail ({facility_id})", response)
    return response.json()


def test_facility_equipment(facility_id: str):
    """測試 7: 取得設施的所有設備"""
    print(f"\n📋 測試 7: 取得設施的所有設備 (facility_id={facility_id})")
    response = requests.get(
        f"{BASE_URL}/facilities/{facility_id}/equipment",
        headers=headers
    )
    print_response(f"Facility Equipment ({facility_id})", response)
    return response.json()


def test_relationship_integrity():
    """測試 8: 驗證關聯完整性"""
    print("\n📋 測試 8: 驗證 Organizations-Facilities 關聯完整性")
    
    # 1. 取得組織列表
    orgs_response = test_organizations_tree()
    if orgs_response.get('status') != 'success':
        print("❌ 無法取得組織列表")
        return
    
    organizations = orgs_response['data']['organizations']
    if not organizations:
        print("⚠️  沒有組織資料")
        return
    
    # 取得第一個組織
    first_org = organizations[0]
    org_id = first_org['org_id']
    
    # 2. 取得該組織的設施
    facilities_response = test_organization_facilities(org_id, include_equipment=True)
    if facilities_response.get('status') != 'success':
        print(f"❌ 無法取得組織 {org_id} 的設施")
        return
    
    facilities = facilities_response['data']['facilities']
    if not facilities:
        print(f"⚠️  組織 {org_id} 沒有關聯的設施")
        return
    
    # 3. 驗證設施的 org_id 是否正確
    first_facility = facilities[0]
    facility_id = first_facility['facility_id']
    
    # 4. 取得設施詳情，驗證是否包含正確的 org_id
    facility_detail = test_facility_detail(facility_id, include_equipment=True)
    if facility_detail.get('status') != 'success':
        print(f"❌ 無法取得設施 {facility_id} 的詳情")
        return
    
    facility_org_id = facility_detail['data']['facility']['org_id']
    
    # 5. 驗證關聯
    if facility_org_id == org_id:
        print("\n✅ 關聯驗證成功!")
        print(f"   組織: {first_org['org_name']} ({org_id})")
        print(f"   設施: {first_facility['facility_name']} ({facility_id})")
        print(f"   設施的 org_id: {facility_org_id}")
    else:
        print("\n❌ 關聯驗證失敗!")
        print(f"   預期 org_id: {org_id}")
        print(f"   實際 org_id: {facility_org_id}")


def run_all_tests():
    """執行所有測試"""
    print("=" * 60)
    print("Organizations-Facilities API 測試套件")
    print("=" * 60)
    
    try:
        # 基本測試
        orgs = test_organizations_tree()
        
        # 如果有組織資料，執行詳細測試
        if orgs.get('status') == 'success' and orgs['data']['organizations']:
            org_id = orgs['data']['organizations'][0]['org_id']
            
            # 測試組織相關 API
            test_organization_detail(org_id, include_facilities=True, include_users=True)
            test_organization_facilities(org_id, include_equipment=True)
            
            # 測試設施相關 API
            test_facilities_tree(org_id=org_id)
            test_facilities_list(org_id=org_id, page=1, page_size=10)
            
            # 如果有設施資料，測試設施詳情
            facilities = test_organization_facilities(org_id)
            if facilities.get('status') == 'success' and facilities['data']['facilities']:
                facility_id = facilities['data']['facilities'][0]['facility_id']
                test_facility_detail(facility_id, include_equipment=True, include_children=True)
                test_facility_equipment(facility_id)
            
            # 測試關聯完整性
            test_relationship_integrity()
        
        print("\n" + "=" * 60)
        print("✅ 所有測試執行完成!")
        print("=" * 60)
        
    except requests.exceptions.ConnectionError:
        print("\n❌ 錯誤: 無法連線到伺服器")
        print("請確保 Flask 應用程式正在執行 (python run.py)")
    except Exception as e:
        print(f"\n❌ 測試執行錯誤: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # 檢查 token
    if TOKEN == "YOUR_JWT_TOKEN_HERE":
        print("⚠️  警告: 請先設定有效的 JWT token")
        print("方法 1: 在程式碼中修改 TOKEN 變數")
        print("方法 2: 先登入系統取得 token")
        print("\n繼續執行可能會收到 401 Unauthorized 錯誤\n")
        
        response = input("是否繼續? (y/n): ")
        if response.lower() != 'y':
            print("測試已取消")
            exit()
    
    run_all_tests()
