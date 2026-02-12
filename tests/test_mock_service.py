#!/usr/bin/env python
"""
Mock Data Service 測試腳本
驗證 mock data 功能是否正常運作
"""
import sys
import os

# 加入專案根目錄到 Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.mock_data_service import get_mock_service


def test_mock_service():
    """測試 Mock Data Service 各項功能"""
    
    print("=" * 60)
    print("Mock Data Service 功能測試")
    print("=" * 60)
    
    # 取得 mock service 實例
    mock_service = get_mock_service()
    
    # 測試 1: 使用者驗證
    print("\n【測試 1】使用者登入驗證")
    print("-" * 60)
    user = mock_service.get_user_by_username('admin')
    if user:
        print(f"✓ 找到使用者: {user['full_name']} ({user['username']})")
        print(f"  員工編號: {user['employee_id']}")
        print(f"  角色: {user['role_name']}")
    else:
        print("✗ 找不到使用者")
    
    # 測試 2: 組織樹狀結構
    print("\n【測試 2】組織樹狀結構")
    print("-" * 60)
    org_tree = mock_service.get_organization_tree()
    print(f"✓ 取得組織架構,共 {len(org_tree)} 個頂層組織:")
    for org in org_tree:
        print(f"  - {org['org_name']} ({org['org_code']})")
        for child in org.get('children', []):
            print(f"    └── {child['org_name']} ({child['org_code']})")
    
    # 測試 3: 任務列表
    print("\n【測試 3】巡檢任務列表")
    print("-" * 60)
    tasks = mock_service.get_tasks_by_user_id(2)
    print(f"✓ 使用者 ID 2 的任務,共 {len(tasks)} 筆:")
    for task in tasks:
        print(f"  - {task['task_number']}: {task['status']} (完成率: {task['completion_rate']}%)")
    
    # 測試 4: 任務詳細資料
    print("\n【測試 4】任務詳細資料")
    print("-" * 60)
    if tasks:
        task_detail = mock_service.get_task_with_details(tasks[0]['task_id'])
        if task_detail:
            print(f"✓ 任務: {task_detail['task_number']}")
            print(f"  路線: {task_detail.get('route_name')}")
            print(f"  類型: {task_detail.get('route_type')}")
            print(f"  管制點數量: {len(task_detail.get('control_points', []))}")
            
            for point in task_detail.get('control_points', [])[:2]:  # 只顯示前 2 個
                print(f"\n  管制點: {point['point_name']}")
                print(f"  檢查項目數量: {len(point.get('check_items', []))}")
                for item in point.get('check_items', [])[:3]:  # 只顯示前 3 個
                    limits = ""
                    if item.get('lower_limit') is not None:
                        limits = f" ({item['lower_limit']}-{item['upper_limit']} {item['unit']})"
                    print(f"    - {item['item_description']}{limits}")
    
    # 測試 5: 儀表板統計
    print("\n【測試 5】儀表板統計資料")
    print("-" * 60)
    stats = mock_service.get_dashboard_statistics()
    print("✓ 異常追蹤統計:")
    abn = stats.get('abnormal_tracking', {})
    print(f"  - 今日異常項目: {abn.get('today_abnormal')}")
    print(f"  - 今日注意項目: {abn.get('today_attention')}")
    print(f"  - 累積異常未結案: {abn.get('accumulated_abnormal_open')}")
    print(f"  - 累積注意未結案: {abn.get('accumulated_attention_open')}")
    
    print("\n✓ 巡檢作業統計:")
    tasks_stat = stats.get('inspection_tasks', {})
    print(f"  - 未派工: {tasks_stat.get('not_assigned')}")
    print(f"  - 未完成: {tasks_stat.get('not_completed')}")
    print(f"  - 執行中: {tasks_stat.get('in_progress')}")
    print(f"  - 已完成: {tasks_stat.get('completed')}")
    
    # 測試 6: 巡檢紀錄查詢
    print("\n【測試 6】巡檢紀錄查詢")
    print("-" * 60)
    records = mock_service.get_inspection_records(
        filters={'start_date': '2025-10-01', 'end_date': '2025-10-31'},
        page=1,
        page_size=10
    )
    print(f"✓ 查詢結果: 共 {records['total']} 筆,顯示第 {records['page']} 頁")
    for record in records['records']:
        print(f"  - {record['task_number']}: {record['org_name']} / {record['route_name']}")
        print(f"    狀態: {record['status']}, 檢查人員: {record['inspector_name']}, 異常: {'是' if record['has_abnormal'] else '否'}")
    
    # 測試 7: 新增巡檢結果
    print("\n【測試 7】新增巡檢結果")
    print("-" * 60)
    result_data = {
        'task_id': 101,
        'point_id': 1001,
        'item_id': 10001,
        'result_value': '68.2',
        'result_status': '正常',
        'is_abnormal': False,
        'rfid_scanned': True,
        'check_time': '2025-10-14T14:30:00',
        'inspector_id': 2
    }
    result_id = mock_service.add_inspection_result(result_data)
    print(f"✓ 成功新增巡檢結果,ID: {result_id}")
    
    # 驗證結果是否已新增
    results = mock_service.get_results_by_task_id(101)
    print(f"  任務 101 目前有 {len(results)} 筆結果")
    
    print("\n" + "=" * 60)
    print("測試完成!")
    print("=" * 60)


if __name__ == '__main__':
    test_mock_service()
