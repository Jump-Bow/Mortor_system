"""
AIMS 資料同步腳本
從 AIMS 系統 API 同步組織、設備及巡檢工單資料

同步資料表：
- t_organization -> Facility (設施)
- t_equipment -> Equipment (設備)
- t_job -> InspectionTask (巡檢工單)

使用方式：
    python scripts/sync_aims_data.py [--dry-run] [--verbose] [--sync-type TYPE]
    
    選項：
        --dry-run       模擬執行，不實際寫入資料庫
        --verbose       顯示詳細日誌
        --sync-type     指定同步類型：all, organization, equipment, job (預設: all)

環境變數配置：
    AIMS_API_URL    AIMS API 基礎 URL
    AIMS_API_KEY    AIMS API 金鑰
"""

import os
import sys
import argparse
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 將專案根目錄加入 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import Facility, Equipment, InspectionTask
from config import Config


# ============================================================================
# 常數與設定
# ============================================================================

class SyncType(Enum):
    """同步類型列舉"""
    ALL = "all"
    ORGANIZATION = "organization"
    EQUIPMENT = "equipment"
    JOB = "job"


@dataclass
class SyncResult:
    """同步結果資料類別"""
    sync_type: str
    total_count: int
    created_count: int
    updated_count: int
    error_count: int
    errors: List[str]
    
    def __str__(self) -> str:
        return (
            f"{self.sync_type}: "
            f"總計 {self.total_count} 筆, "
            f"新增 {self.created_count} 筆, "
            f"更新 {self.updated_count} 筆, "
            f"錯誤 {self.error_count} 筆"
        )


# ============================================================================
# AIMS API 客戶端
# ============================================================================

class AIMSClient:
    """
    AIMS 系統 API 客戶端
    
    負責與 AIMS 系統進行 API 通訊，取得組織、設備及工單資料。
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        初始化 AIMS API 客戶端
        
        Args:
            base_url: AIMS API 基礎 URL
            api_key: API 驗證金鑰
            timeout: 請求逾時時間（秒）
            max_retries: 最大重試次數
        """
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
        self.logger = logging.getLogger(__name__)
        
        # 設定 requests session 與重試機制
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 設定預設 headers
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        發送 HTTP 請求
        
        Args:
            method: HTTP 方法 (GET, POST, etc.)
            endpoint: API 端點路徑
            params: 查詢參數
            data: 請求主體資料
            
        Returns:
            API 回應的 JSON 資料
            
        Raises:
            requests.RequestException: 請求失敗時
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        self.logger.debug(f"發送 {method} 請求至 {url}")
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            self.logger.error(f"HTTP 錯誤: {e}")
            raise
        except requests.exceptions.ConnectionError as e:
            self.logger.error(f"連線錯誤: {e}")
            raise
        except requests.exceptions.Timeout as e:
            self.logger.error(f"請求逾時: {e}")
            raise
        except requests.exceptions.RequestException as e:
            self.logger.error(f"請求異常: {e}")
            raise
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """
        取得所有組織/設施資料 (t_organization)
        
        API 假設端點: GET /api/organizations
        
        Returns:
            組織資料列表，每筆包含:
            - unitid: 設施編號
            - parentunitid: 上層設施編號
            - unitname: 設施名稱
            - unittype: 設施類別
        """
        self.logger.info("正在取得組織資料...")
        response = self._request("GET", "/api/organizations")
        
        # 假設 API 回傳格式: {"data": [...], "total": n}
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        elif isinstance(response, list):
            return response
        else:
            self.logger.warning(f"未預期的回應格式: {type(response)}")
            return []
    
    def get_equipment(self) -> List[Dict[str, Any]]:
        """
        取得所有設備資料 (t_equipment)
        
        API 假設端點: GET /api/equipment
        
        Returns:
            設備資料列表，每筆包含:
            - id: 設備編號
            - name: 設備名稱
            - assetid: 設備資產 ID
            - unitid: 設施編號
        """
        self.logger.info("正在取得設備資料...")
        response = self._request("GET", "/api/equipment")
        
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        elif isinstance(response, list):
            return response
        else:
            self.logger.warning(f"未預期的回應格式: {type(response)}")
            return []
    
    def get_jobs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        取得巡檢工單資料 (t_job)
        
        API 假設端點: GET /api/jobs
        
        Args:
            start_date: 開始日期 (格式: YYYYMMDD)
            end_date: 結束日期 (格式: YYYYMMDD)
        
        Returns:
            工單資料列表，每筆包含:
            - actid: 工單 ID
            - equipmentid: 設備編號
            - mdate: 開始日期 (YYYYMMDD)
            - act_desc: 工單內容
            - act_key: 工單編號
            - act_mem_id: 負責人 ID
            - act_mem_name: 負責人名稱
        """
        self.logger.info("正在取得工單資料...")
        
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        
        response = self._request("GET", "/api/jobs", params=params)
        
        if isinstance(response, dict) and "data" in response:
            return response["data"]
        elif isinstance(response, list):
            return response
        else:
            self.logger.warning(f"未預期的回應格式: {type(response)}")
            return []


# ============================================================================
# Mock AIMS 客戶端（供測試使用）
# ============================================================================

class MockAIMSClient(AIMSClient):
    """
    模擬 AIMS API 客戶端（供測試與開發使用）
    
    當未設定 AIMS_API_URL 或 USE_MOCK_AIMS=true 時使用此客戶端。
    """
    
    def __init__(self, *args, **kwargs):
        """初始化（不需要實際的 API 連線）"""
        self.logger = logging.getLogger(__name__)
        self.logger.info("使用 Mock AIMS 客戶端")
    
    def get_organizations(self) -> List[Dict[str, Any]]:
        """回傳模擬的組織資料"""
        self.logger.info("回傳模擬組織資料...")
        return [
            {
                "unitid": "ORG001",
                "parentunitid": None,
                "unitname": "奇美醫學中心",
                "unittype": "醫學中心"
            },
            {
                "unitid": "ORG001-01",
                "parentunitid": "ORG001",
                "unitname": "第一醫療大樓",
                "unittype": "大樓"
            },
            {
                "unitid": "ORG001-01-01",
                "parentunitid": "ORG001-01",
                "unitname": "1樓門診區",
                "unittype": "樓層"
            },
            {
                "unitid": "ORG001-01-02",
                "parentunitid": "ORG001-01",
                "unitname": "2樓病房區",
                "unittype": "樓層"
            },
            {
                "unitid": "ORG001-02",
                "parentunitid": "ORG001",
                "unitname": "第二醫療大樓",
                "unittype": "大樓"
            }
        ]
    
    def get_equipment(self) -> List[Dict[str, Any]]:
        """回傳模擬的設備資料"""
        self.logger.info("回傳模擬設備資料...")
        return [
            {
                "id": "EQ001",
                "name": "空調主機 A",
                "assetid": "AIMS-AC-001",
                "unitid": "ORG001-01-01"
            },
            {
                "id": "EQ002",
                "name": "空調主機 B",
                "assetid": "AIMS-AC-002",
                "unitid": "ORG001-01-01"
            },
            {
                "id": "EQ003",
                "name": "電梯 1 號",
                "assetid": "AIMS-EL-001",
                "unitid": "ORG001-01"
            },
            {
                "id": "EQ004",
                "name": "發電機組",
                "assetid": "AIMS-GEN-001",
                "unitid": "ORG001-02"
            }
        ]
    
    def get_jobs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """回傳模擬的工單資料"""
        self.logger.info("回傳模擬工單資料...")
        today = datetime.now().strftime("%Y%m%d")
        return [
            {
                "actid": "JOB001",
                "equipmentid": "EQ001",
                "mdate": today,
                "act_desc": "空調主機定期保養",
                "act_key": "WO-2024-001",
                "act_mem_id": "USER001",
                "act_mem_name": "張三"
            },
            {
                "actid": "JOB002",
                "equipmentid": "EQ003",
                "mdate": today,
                "act_desc": "電梯年度檢驗",
                "act_key": "WO-2024-002",
                "act_mem_id": "USER002",
                "act_mem_name": "李四"
            },
            {
                "actid": "JOB003",
                "equipmentid": "EQ004",
                "mdate": today,
                "act_desc": "發電機負載測試",
                "act_key": "WO-2024-003",
                "act_mem_id": "USER001",
                "act_mem_name": "張三"
            }
        ]


# ============================================================================
# 資料同步服務
# ============================================================================

class AIMSSyncService:
    """
    AIMS 資料同步服務
    
    負責將 AIMS 系統的資料同步至本地資料庫。
    """
    
    def __init__(self, client: AIMSClient, dry_run: bool = False):
        """
        初始化同步服務
        
        Args:
            client: AIMS API 客戶端實例
            dry_run: 是否為模擬執行（不實際寫入資料庫）
        """
        self.client = client
        self.dry_run = dry_run
        self.logger = logging.getLogger(__name__)
    
    def sync_organizations(self) -> SyncResult:
        """
        同步組織/設施資料
        
        將 AIMS t_organization 資料同步至 Facility 表
        
        欄位對應：
        - unitid -> facility_id
        - parentunitid -> parent_facility_id
        - unitname -> facility_name
        - unittype -> facility_type
        
        Returns:
            同步結果
        """
        self.logger.info("開始同步組織資料...")
        result = SyncResult(
            sync_type="organization",
            total_count=0,
            created_count=0,
            updated_count=0,
            error_count=0,
            errors=[]
        )
        
        try:
            organizations = self.client.get_organizations()
            result.total_count = len(organizations)
            self.logger.info(f"取得 {len(organizations)} 筆組織資料")
            
            # 先處理沒有父層的組織，再處理有父層的（確保外鍵關聯正確）
            # 依據 parentunitid 排序，None 優先
            organizations_sorted = sorted(
                organizations,
                key=lambda x: (x.get("parentunitid") is not None, x.get("parentunitid") or "")
            )
            
            for org_data in organizations_sorted:
                try:
                    facility_id = org_data.get("unitid")
                    if not facility_id:
                        result.error_count += 1
                        result.errors.append("缺少 unitid 欄位")
                        continue
                    
                    # 查詢現有資料
                    existing = Facility.query.get(facility_id)
                    
                    if existing:
                        # 更新現有資料
                        existing.parent_facility_id = org_data.get("parentunitid")
                        existing.facility_name = org_data.get("unitname", "")
                        existing.facility_type = org_data.get("unittype", "")
                        result.updated_count += 1
                        self.logger.debug(f"更新設施: {facility_id}")
                    else:
                        # 建立新資料
                        new_facility = Facility(
                            facility_id=facility_id,
                            parent_facility_id=org_data.get("parentunitid"),
                            facility_name=org_data.get("unitname", ""),
                            facility_type=org_data.get("unittype", "")
                        )
                        db.session.add(new_facility)
                        result.created_count += 1
                        self.logger.debug(f"建立設施: {facility_id}")
                    
                    if not self.dry_run:
                        db.session.flush()  # 確保每筆資料即時寫入以處理外鍵
                        
                except Exception as e:
                    result.error_count += 1
                    error_msg = f"處理設施 {org_data.get('unitid', 'unknown')} 時發生錯誤: {str(e)}"
                    result.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            if not self.dry_run:
                db.session.commit()
                self.logger.info("組織資料同步完成並已提交")
            else:
                db.session.rollback()
                self.logger.info("組織資料同步完成（模擬執行，未提交）")
                
        except Exception as e:
            db.session.rollback()
            error_msg = f"同步組織資料時發生錯誤: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def sync_equipment(self) -> SyncResult:
        """
        同步設備資料
        
        將 AIMS t_equipment 資料同步至 Equipment 表
        
        欄位對應：
        - id -> equipment_id
        - name -> equipment_name
        - assetid -> asset_id
        - unitid -> facility_id
        
        Returns:
            同步結果
        """
        self.logger.info("開始同步設備資料...")
        result = SyncResult(
            sync_type="equipment",
            total_count=0,
            created_count=0,
            updated_count=0,
            error_count=0,
            errors=[]
        )
        
        try:
            equipment_list = self.client.get_equipment()
            result.total_count = len(equipment_list)
            self.logger.info(f"取得 {len(equipment_list)} 筆設備資料")
            
            for eq_data in equipment_list:
                try:
                    equipment_id = eq_data.get("id")
                    if not equipment_id:
                        result.error_count += 1
                        result.errors.append("缺少 id 欄位")
                        continue
                    
                    # 檢查 facility_id 是否存在
                    facility_id = eq_data.get("unitid")
                    if facility_id:
                        facility_exists = Facility.query.get(facility_id)
                        if not facility_exists:
                            self.logger.warning(
                                f"設備 {equipment_id} 的設施 {facility_id} 不存在，"
                                "將設為 NULL"
                            )
                            facility_id = None
                    
                    # 查詢現有資料
                    existing = Equipment.query.get(equipment_id)
                    
                    if existing:
                        # 更新現有資料
                        existing.equipment_name = eq_data.get("name", "")
                        existing.asset_id = eq_data.get("assetid", "")
                        existing.facility_id = facility_id
                        result.updated_count += 1
                        self.logger.debug(f"更新設備: {equipment_id}")
                    else:
                        # 建立新資料
                        new_equipment = Equipment(
                            equipment_id=equipment_id,
                            equipment_name=eq_data.get("name", ""),
                            asset_id=eq_data.get("assetid", ""),
                            facility_id=facility_id
                        )
                        db.session.add(new_equipment)
                        result.created_count += 1
                        self.logger.debug(f"建立設備: {equipment_id}")
                    
                except Exception as e:
                    result.error_count += 1
                    error_msg = f"處理設備 {eq_data.get('id', 'unknown')} 時發生錯誤: {str(e)}"
                    result.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            if not self.dry_run:
                db.session.commit()
                self.logger.info("設備資料同步完成並已提交")
            else:
                db.session.rollback()
                self.logger.info("設備資料同步完成（模擬執行，未提交）")
                
        except Exception as e:
            db.session.rollback()
            error_msg = f"同步設備資料時發生錯誤: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def sync_jobs(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> SyncResult:
        """
        同步巡檢工單資料
        
        將 AIMS t_job 資料同步至 InspectionTask 表
        
        欄位對應：
        - actid -> task_id
        - equipmentid -> equipment_id
        - mdate -> inspection_date (YYYYMMDD -> Date)
        - act_desc -> description
        - act_key -> task_number
        - act_mem_id -> assigned_to
        - act_mem_name -> assigned_user_name
        
        Args:
            start_date: 開始日期篩選
            end_date: 結束日期篩選
        
        Returns:
            同步結果
        """
        self.logger.info("開始同步工單資料...")
        result = SyncResult(
            sync_type="job",
            total_count=0,
            created_count=0,
            updated_count=0,
            error_count=0,
            errors=[]
        )
        
        try:
            jobs = self.client.get_jobs(start_date, end_date)
            result.total_count = len(jobs)
            self.logger.info(f"取得 {len(jobs)} 筆工單資料")
            
            for job_data in jobs:
                try:
                    task_id = job_data.get("actid")
                    if not task_id:
                        result.error_count += 1
                        result.errors.append("缺少 actid 欄位")
                        continue
                    
                    # 檢查 equipment_id 是否存在
                    equipment_id = job_data.get("equipmentid")
                    if equipment_id:
                        equipment_exists = Equipment.query.get(equipment_id)
                        if not equipment_exists:
                            self.logger.warning(
                                f"工單 {task_id} 的設備 {equipment_id} 不存在，"
                                "將設為 NULL"
                            )
                            equipment_id = None
                    
                    # 轉換日期格式 YYYYMMDD -> Date
                    mdate_str = job_data.get("mdate", "")
                    inspection_date = None
                    if mdate_str and len(mdate_str) == 8:
                        try:
                            inspection_date = datetime.strptime(mdate_str, "%Y%m%d").date()
                        except ValueError:
                            self.logger.warning(f"無效的日期格式: {mdate_str}")
                    
                    # 查詢現有資料
                    existing = InspectionTask.query.get(task_id)
                    
                    if existing:
                        # 更新現有資料
                        existing.equipment_id = equipment_id
                        existing.inspection_date = inspection_date
                        existing.description = job_data.get("act_desc")
                        existing.task_number = job_data.get("act_key")
                        existing.assigned_to = job_data.get("act_mem_id")
                        existing.assigned_user_name = job_data.get("act_mem_name")
                        result.updated_count += 1
                        self.logger.debug(f"更新工單: {task_id}")
                    else:
                        # 建立新資料
                        new_task = InspectionTask(
                            task_id=task_id,
                            equipment_id=equipment_id,
                            inspection_date=inspection_date,
                            description=job_data.get("act_desc"),
                            task_number=job_data.get("act_key"),
                            assigned_to=job_data.get("act_mem_id"),
                            assigned_user_name=job_data.get("act_mem_name"),
                            status="Pending"  # 預設狀態
                        )
                        db.session.add(new_task)
                        result.created_count += 1
                        self.logger.debug(f"建立工單: {task_id}")
                    
                except Exception as e:
                    result.error_count += 1
                    error_msg = f"處理工單 {job_data.get('actid', 'unknown')} 時發生錯誤: {str(e)}"
                    result.errors.append(error_msg)
                    self.logger.error(error_msg)
            
            if not self.dry_run:
                db.session.commit()
                self.logger.info("工單資料同步完成並已提交")
            else:
                db.session.rollback()
                self.logger.info("工單資料同步完成（模擬執行，未提交）")
                
        except Exception as e:
            db.session.rollback()
            error_msg = f"同步工單資料時發生錯誤: {str(e)}"
            result.errors.append(error_msg)
            self.logger.error(error_msg)
        
        return result
    
    def sync_all(self) -> Dict[str, SyncResult]:
        """
        同步所有資料
        
        依序同步組織、設備、工單資料。
        順序很重要，因為有外鍵依賴關係。
        
        Returns:
            各類型同步結果的字典
        """
        self.logger.info("=" * 60)
        self.logger.info("開始執行完整資料同步")
        self.logger.info("=" * 60)
        
        results = {}
        
        # 1. 先同步組織（設施）
        results["organization"] = self.sync_organizations()
        self.logger.info(str(results["organization"]))
        
        # 2. 再同步設備（依賴設施）
        results["equipment"] = self.sync_equipment()
        self.logger.info(str(results["equipment"]))
        
        # 3. 最後同步工單（依賴設備）
        results["job"] = self.sync_jobs()
        self.logger.info(str(results["job"]))
        
        self.logger.info("=" * 60)
        self.logger.info("完整資料同步完成")
        self.logger.info("=" * 60)
        
        return results


# ============================================================================
# 工具函式
# ============================================================================

def setup_logging(verbose: bool = False) -> None:
    """
    設定日誌
    
    Args:
        verbose: 是否啟用詳細日誌
    """
    level = logging.DEBUG if verbose else logging.INFO
    
    # 建立日誌格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 設定根日誌記錄器
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # 清除現有 handlers
    root_logger.handlers = []
    
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 檔案 handler
    log_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        'logs'
    )
    os.makedirs(log_dir, exist_ok=True)
    
    file_handler = logging.FileHandler(
        os.path.join(log_dir, 'aims_sync.log'),
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)


def create_aims_client() -> AIMSClient:
    """
    建立 AIMS API 客戶端
    
    根據環境變數決定使用實際客戶端或模擬客戶端
    
    Returns:
        AIMS API 客戶端實例
    """
    use_mock = os.getenv('USE_MOCK_AIMS', 'true').lower() == 'true'
    aims_url = os.getenv('AIMS_API_URL', '')
    aims_key = os.getenv('AIMS_API_KEY', '')
    
    if use_mock or not aims_url:
        logging.info("使用 Mock AIMS 客戶端")
        return MockAIMSClient(base_url="", api_key="")
    else:
        logging.info(f"連接 AIMS API: {aims_url}")
        return AIMSClient(
            base_url=aims_url,
            api_key=aims_key,
            timeout=Config.AIMS_TIMEOUT if hasattr(Config, 'AIMS_TIMEOUT') else 30
        )


def print_summary(results: Dict[str, SyncResult]) -> None:
    """
    列印同步摘要
    
    Args:
        results: 同步結果字典
    """
    print("\n" + "=" * 60)
    print("AIMS 資料同步摘要")
    print("=" * 60)
    
    total_created = 0
    total_updated = 0
    total_errors = 0
    
    for sync_type, result in results.items():
        print(f"\n【{sync_type.upper()}】")
        print(f"  總計: {result.total_count} 筆")
        print(f"  新增: {result.created_count} 筆")
        print(f"  更新: {result.updated_count} 筆")
        print(f"  錯誤: {result.error_count} 筆")
        
        if result.errors:
            print("  錯誤詳情:")
            for error in result.errors[:5]:  # 只顯示前 5 個錯誤
                print(f"    - {error}")
            if len(result.errors) > 5:
                print(f"    ... 還有 {len(result.errors) - 5} 個錯誤")
        
        total_created += result.created_count
        total_updated += result.updated_count
        total_errors += result.error_count
    
    print("\n" + "-" * 60)
    print(f"總計: 新增 {total_created} 筆, 更新 {total_updated} 筆, 錯誤 {total_errors} 筆")
    print("=" * 60)


# ============================================================================
# 主程式
# ============================================================================

def main():
    """主程式入口點"""
    parser = argparse.ArgumentParser(
        description="從 AIMS 系統同步資料至 FEM 系統"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="模擬執行，不實際寫入資料庫"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="顯示詳細日誌"
    )
    parser.add_argument(
        "--sync-type",
        type=str,
        choices=["all", "organization", "equipment", "job"],
        default="all",
        help="指定同步類型（預設: all）"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="工單同步開始日期（格式: YYYYMMDD）"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="工單同步結束日期（格式: YYYYMMDD）"
    )
    
    args = parser.parse_args()
    
    # 設定日誌
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)
    
    if args.dry_run:
        logger.info("*** 模擬執行模式 - 不會實際寫入資料庫 ***")
    
    # 建立 Flask 應用程式上下文
    app = create_app()
    
    with app.app_context():
        # 建立 AIMS 客戶端
        client = create_aims_client()
        
        # 建立同步服務
        sync_service = AIMSSyncService(client, dry_run=args.dry_run)
        
        # 執行同步
        results = {}
        
        if args.sync_type == "all":
            results = sync_service.sync_all()
        elif args.sync_type == "organization":
            results["organization"] = sync_service.sync_organizations()
        elif args.sync_type == "equipment":
            results["equipment"] = sync_service.sync_equipment()
        elif args.sync_type == "job":
            results["job"] = sync_service.sync_jobs(
                start_date=args.start_date,
                end_date=args.end_date
            )
        
        # 列印摘要
        print_summary(results)
        
        # 如果有錯誤，回傳非零退出碼
        total_errors = sum(r.error_count for r in results.values())
        if total_errors > 0:
            logger.warning(f"同步過程中發生 {total_errors} 個錯誤")
            sys.exit(1)
        
        logger.info("同步程序執行完成")
        sys.exit(0)


if __name__ == "__main__":
    main()
