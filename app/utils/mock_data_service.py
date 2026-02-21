"""
Mock Data Service - 用於本地開發測試
提供模擬資料,無需連接資料庫
"""
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path


class MockDataService:
    """Mock 資料服務類別"""
    
    def __init__(self, mock_data_path: str = './data/mock_data.json'):
        """
        初始化 Mock 資料服務
        
        Args:
            mock_data_path: Mock 資料檔案路徑
        """
        self.mock_data_path = mock_data_path
        self._data: Dict[str, Any] = {}
        self._load_data()
    
    def _load_data(self) -> None:
        """載入 Mock 資料"""
        try:
            if os.path.exists(self.mock_data_path):
                with open(self.mock_data_path, 'r', encoding='utf-8') as f:
                    self._data = json.load(f)
            else:
                print(f"Mock 資料檔案不存在: {self.mock_data_path}")
                self._data = {}
        except Exception as e:
            print(f"載入 Mock 資料時發生錯誤: {str(e)}")
            self._data = {}
    
    def _save_data(self) -> None:
        """儲存 Mock 資料"""
        try:
            # 確保資料夾存在
            Path(self.mock_data_path).parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.mock_data_path, 'w', encoding='utf-8') as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"儲存 Mock 資料時發生錯誤: {str(e)}")
    
    # ==================== 使用者相關 ====================
    
    def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        根據使用者名稱取得使用者資料
        
        Args:
            username: 使用者名稱
            
        Returns:
            使用者資料字典或 None
        """
        users = self._data.get('users', [])
        for user in users:
            if user.get('username') == username:
                return user
        return None
    
    def get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """
        根據使用者 ID 取得使用者資料
        
        Args:
            user_id: 使用者 ID
            
        Returns:
            使用者資料字典或 None
        """
        users = self._data.get('users', [])
        for user in users:
            if user.get('user_id') == user_id:
                return user
        return None
    
    def get_all_users(self) -> List[Dict]:
        """取得所有使用者"""
        return self._data.get('users', [])
    
    # ==================== 組織相關 ====================
    
    def get_organization_tree(self) -> List[Dict]:
        """
        取得組織樹狀結構
        
        Returns:
            組織樹狀結構列表
        """
        organizations = self._data.get('organizations', [])
        
        # 建立組織字典以便快速查找
        org_dict = {org['org_id']: {**org, 'children': []} for org in organizations}
        
        # 建立樹狀結構
        tree = []
        for org in org_dict.values():
            if org['parent_id'] is None:
                tree.append(org)
            else:
                parent = org_dict.get(org['parent_id'])
                if parent:
                    parent['children'].append(org)
        
        return tree
    
    def get_organization_by_id(self, org_id: int) -> Optional[Dict]:
        """根據組織 ID 取得組織資料"""
        organizations = self._data.get('organizations', [])
        for org in organizations:
            if org.get('org_id') == org_id:
                return org
        return None
    
    # ==================== 巡檢路線相關 ====================
    
    def get_routes_by_org_id(self, org_id: int) -> List[Dict]:
        """根據組織 ID 取得巡檢路線"""
        routes = self._data.get('inspection_routes', [])
        return [route for route in routes if route.get('org_id') == org_id]
    
    def get_route_by_id(self, route_id: int) -> Optional[Dict]:
        """根據路線 ID 取得路線資料"""
        routes = self._data.get('inspection_routes', [])
        for route in routes:
            if route.get('route_id') == route_id:
                return route
        return None
    
    # ==================== 管制點相關 ====================
    
    def get_control_points_by_route_id(self, route_id: int) -> List[Dict]:
        """根據路線 ID 取得管制點列表"""
        points = self._data.get('control_points', [])
        return [point for point in points if point.get('route_id') == route_id]
    
    def get_control_point_by_id(self, point_id: int) -> Optional[Dict]:
        """根據管制點 ID 取得管制點資料"""
        points = self._data.get('control_points', [])
        for point in points:
            if point.get('point_id') == point_id:
                return point
        return None
    
    # ==================== 檢查項目相關 ====================
    
    def get_check_items_by_point_id(self, point_id: int) -> List[Dict]:
        """根據管制點 ID 取得檢查項目列表"""
        items = self._data.get('check_items', [])
        return [item for item in items if item.get('point_id') == point_id]
    
    def get_check_item_by_id(self, item_id: int) -> Optional[Dict]:
        """根據檢查項目 ID 取得項目資料"""
        items = self._data.get('check_items', [])
        for item in items:
            if item.get('item_id') == item_id:
                return item
        return None
    
    # ==================== 巡檢任務相關 ====================
    
    def get_tasks_by_user_id(self, user_id: int) -> List[Dict]:
        """根據使用者 ID 取得任務列表"""
        tasks = self._data.get('inspection_tasks', [])
        return [task for task in tasks if task.get('assigned_to') == user_id]
    
    def get_task_by_id(self, task_id: int) -> Optional[Dict]:
        """根據任務 ID 取得任務資料"""
        tasks = self._data.get('inspection_tasks', [])
        for task in tasks:
            if task.get('task_id') == task_id:
                return task
        return None
    
    def get_task_with_details(self, task_id: int) -> Optional[Dict]:
        """
        取得任務詳細資料(包含路線、管制點、檢查項目)
        
        Args:
            task_id: 任務 ID
            
        Returns:
            包含完整資料的任務字典
        """
        task = self.get_task_by_id(task_id)
        if not task:
            return None
        
        # 取得路線資訊
        route = self.get_route_by_id(task.get('route_id'))
        if route:
            task['route_name'] = route.get('route_name')
            task['route_type'] = route.get('route_type')
        
        # 取得管制點與檢查項目
        control_points = self.get_control_points_by_route_id(task.get('route_id'))
        for point in control_points:
            point['check_items'] = self.get_check_items_by_point_id(point.get('point_id'))
        
        task['control_points'] = control_points
        
        return task
    
    def update_task_status(self, task_id: int, status: str, completion_rate: float = None) -> bool:
        """
        更新任務狀態
        
        Args:
            task_id: 任務 ID
            status: 新狀態
            completion_rate: 完成率(可選)
            
        Returns:
            更新是否成功
        """
        tasks = self._data.get('inspection_tasks', [])
        for task in tasks:
            if task.get('task_id') == task_id:
                task['status'] = status
                if completion_rate is not None:
                    task['completion_rate'] = completion_rate
                if status == '執行中' and not task.get('start_time'):
                    task['start_time'] = datetime.now().isoformat()
                if status == '已完成':
                    task['end_time'] = datetime.now().isoformat()
                    task['completion_rate'] = 100.0
                
                self._save_data()
                return True
        return False
    
    # ==================== 巡檢結果相關 ====================
    
    def add_inspection_result(self, result_data: Dict) -> int:
        """
        新增巡檢結果
        
        Args:
            result_data: 結果資料
            
        Returns:
            新增的結果 ID
        """
        results = self._data.get('inspection_results', [])
        
        # 產生新的 result_id
        if results:
            new_id = max(r.get('result_id', 0) for r in results) + 1
        else:
            new_id = 1
        
        result_data['result_id'] = new_id
        results.append(result_data)
        
        self._save_data()
        return new_id
    
    def get_results_by_task_id(self, task_id: int) -> List[Dict]:
        """根據任務 ID 取得巡檢結果列表"""
        results = self._data.get('inspection_results', [])
        return [result for result in results if result.get('task_id') == task_id]
    
    # ==================== 統計資料相關 ====================
    
    def get_dashboard_statistics(self) -> Dict:
        """取得儀表板統計資料"""
        return self._data.get('statistics', {
            'abnormal_tracking': {
                'today_abnormal': 0,
                'today_attention': 0,
                'accumulated_abnormal_open': 0,
                'accumulated_attention_open': 0
            },
            'inspection_tasks': {
                'not_assigned': 0,
                'not_completed': 0,
                'in_progress': 0,
                'completed': 0
            }
        })
    
    def get_inspection_records(self, filters: Dict = None, page: int = 1, page_size: int = 20) -> Dict:
        """
        取得巡檢紀錄
        
        Args:
            filters: 篩選條件
            page: 頁碼
            page_size: 每頁筆數
            
        Returns:
            包含總數與紀錄的字典
        """
        tasks = self._data.get('inspection_tasks', [])
        
        # 套用篩選條件
        if filters:
            if 'org_id' in filters:
                # 需要透過 route 來篩選組織
                org_routes = self.get_routes_by_org_id(filters['org_id'])
                route_ids = [r['route_id'] for r in org_routes]
                tasks = [t for t in tasks if t.get('route_id') in route_ids]
            
            if 'start_date' in filters:
                tasks = [t for t in tasks if t.get('inspection_date') >= filters['start_date']]
            
            if 'end_date' in filters:
                tasks = [t for t in tasks if t.get('inspection_date') <= filters['end_date']]
            
            if 'status' in filters:
                tasks = [t for t in tasks if t.get('status') == filters['status']]
        
        # 分頁
        total = len(tasks)
        start = (page - 1) * page_size
        end = start + page_size
        
        # 補充額外資訊
        records = []
        for task in tasks[start:end]:
            route = self.get_route_by_id(task.get('route_id'))
            user = self.get_user_by_id(task.get('assigned_to'))
            org = self.get_organization_by_id(route.get('org_id')) if route else None
            
            # 檢查是否有異常
            results = self.get_results_by_task_id(task.get('task_id'))
            has_abnormal = any(r.get('is_abnormal') for r in results)
            
            records.append({
                **task,
                'org_name': org.get('org_name') if org else '',
                'route_name': route.get('route_name') if route else '',
                'inspector_name': user.get('full_name') if user else '',
                'has_abnormal': has_abnormal
            })
        
        return {
            'total': total,
            'page': page,
            'page_size': page_size,
            'records': records
        }


# 全域實例
_mock_service = None


def get_mock_service(mock_data_path: str = None) -> MockDataService:
    """
    取得 Mock 資料服務實例(單例模式)
    
    Args:
        mock_data_path: Mock 資料檔案路徑
        
    Returns:
        MockDataService 實例
    """
    global _mock_service
    
    if _mock_service is None:
        if mock_data_path is None:
            mock_data_path = os.getenv('MOCK_DATA_PATH', './data/mock_data.json')
        _mock_service = MockDataService(mock_data_path)
    
    return _mock_service
