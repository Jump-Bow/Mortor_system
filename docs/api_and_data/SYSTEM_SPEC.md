### 設備保養管理系統 - 後台與 API 系統架構文件

---

## 文件版本資訊

| 欄位 | 內容 |
|-----|------|
| **版本號** | v1.4.0 |
| **最後修改日期** | 2025-12-07 |
| **狀態** | 發佈 |
| **修改摘要** | 更新 API 功能清單格式、補充缺漏的 API 端點、完善後台功能清單 |

### 修改履歷

| 版本 | 日期 | 修改內容 |
|------|------|---------|
| v1.0.0 | 2025-10-14 | 初版發布 |
| v1.1.0 | 2025-11-11 | - 修正 Equipment 表重複定義 equipment_id<br>- 修正 API 使用不存在的 point_id，改為 equipment_id<br>- 修正任務下載 API response，將 control_points 改為 equipment_list<br>- 補充任務下載 API 缺失欄位 (route_id, org_id, assigned_to 等) |
| v1.2.0 | 2025-11-24 | - 新增 Facilities 表 org_id 欄位，建立 Organizations-Facilities 關聯<br>- 新增 Facilities API (tree, list, detail, equipment)<br>- 新增 Organizations API 增強 (include_facilities, include_users 參數)<br>- 更新 Mermaid ER Diagram 顯示 Organizations-Facilities 關聯 |
| v1.3.0 | 2025-11-25 | - 修改任務下載及任務列表 API 回應，將 equipment_list 改為 equipment_check_items |
| v1.4.0 | 2025-12-07 | - 更新 API 功能清單格式並補充缺漏端點<br>- 新增使用者管理 API (list, detail, create, update, delete, password, roles)<br>- 新增任務 CRUD API (POST, PUT, DELETE)<br>- 新增系統日誌 API (list, stats, action-types, detail)<br>- 新增設備列表 API<br>- 完善後台功能清單 (任務管理、設施管理、系統日誌管理) |

---

### **第一部分:後台系統 (Backend)**

#### **1. 系統技術堆疊**

| 元件 | 技術 | 說明 |
| :--- | :--- | :--- |
| **後端框架** | Flask (Python 3.10.13) | 採用 Blueprint 模組化架構 |
| **伺服器資料庫** | PostgreSQL 16 | 分為測試區與正式區環境 |
| **部署環境** | GCP / Docker | 雲端與容器化部署 |
| **安全協定** | SSL/TLS | 所有網路傳輸加密 |
| **身份驗證** | Azure Entra ID / JWT | 支援 Local 帳密登入與 Azure AD (OAuth 2.0 Authorization Code Flow) 認證 |
| **資料庫驗證** | Password / IAM | 遵循最小權限原則 |
| **資料庫驅動** | psycopg2-binary | PostgreSQL Python Adapter |

#### **2. 後台功能清單 (Function List)**

後台系統主要為網頁管理介面,提供管理者進行全面的數據監控、查詢與系統管理。

| **模組** | **功能項目** | **詳細描述** | **參考資料** |
| :--- | :--- | :--- | :--- |
| **使用者管理** | 使用者登入/登出 | - 提供帳號密碼登入介面(預設帳密為 admin / 1234qwer5T)。<br>- 系統名稱為「設備保養管理系統」。<br>- 支援 Azure Entra ID (Azure AD) 帳號進行 OAuth 2.0 認證登入。<br>- AD 帳號與系統 hr_account.id 對應，AD 僅負責身份驗證。 | system-requirement.md 3.1 |
| **使用者管理** | 權限管理 | - 根據不同使用者角色(如管理者、一般使用者)給予相對應的操作權限。 | system-requirement.md 3.1 |
| **使用者管理** | 使用者 CRUD | - 提供使用者列表查詢、新增、編輯、停用功能。<br>- 支援密碼重設功能。<br>- 支援搜尋與篩選功能。 | system-requirement.md 3.1 |
| **主頁儀表板 (Dashboard)** | 異常追蹤統計 | - 顯示即時的異常追蹤數據,包含:今日異常項目總數、今日注意項目總數、累積異常未結案、累積注意未結案。 | system-requirement.md 3.2 |
| **主頁儀表板 (Dashboard)** | 巡檢作業統計 | - 顯示即時的巡檢作業狀態,包含:未派工、未完成、執行中、已完成的任務數量。 | system-requirement.md 3.2 |
| **巡檢管理** | 組織與任務管理 | - 以樹狀結構管理公司組織與其對應的巡檢任務/表單。<br>- 每個組織單位底下可對應多張巡檢表單。 | system-requirement.md 3.4 |
| **巡檢管理** | 巡檢紀錄查詢 | - 提供依據開始日期與結束日期進行篩選查詢功能。<br>- 透過點選左側的組織樹狀結構進行資料搜尋。<br>- 查詢結果以列表呈現,包含詳細資料、異常、組織、檢查日期、檢查人員等欄位。<br>- 可點擊查看單筆紀錄的詳細資訊,如設備、作業時間、到點時間、人員等欄位資訊。<br>- 可鑽取至最底層,查看該次巡檢所有檢查項目的量測結果、上下限值、單位與檢查時間。 | system-requirement.md 3.3 |
| **巡檢管理** | 異常追蹤管理 | - 提供異常紀錄列表查詢與管理。<br>- 支援依日期、處理狀態進行篩選。<br>- 可查看異常詳細資訊與處理狀態。 | system-requirement.md 3.2 |
| **任務管理** | 任務列表查詢 | - 提供任務列表查詢與篩選功能。<br>- 支援依狀態、日期範圍進行篩選。<br>- 顯示任務完成率。 | system-requirement.md 4.1 |
| **任務管理** | 任務 CRUD | - 提供新增、編輯、刪除任務功能。<br>- 支援指派設備與負責人員。<br>- 僅管理者可建立與刪除任務。 | system-requirement.md 4.1, 4.2 |
| **設施管理** | 設施樹狀結構 | - 以樹狀結構顯示設施層級關係。<br>- 支援依組織篩選設施。 | system-requirement.md 3.4 |
| **設施管理** | 設施列表與詳情 | - 提供設施列表查詢與分頁功能。<br>- 支援查看設施詳情與關聯設備。 | system-requirement.md 3.4 |
| **系統管理** | 系統日誌查詢 | - 提供系統操作日誌查詢功能。<br>- 支援依使用者、操作類型、日期進行篩選。<br>- 提供日誌統計與活動分析。 | - |
| **報表與分析** | 趨勢圖分析 | - 提供抄表趨勢圖(設備)功能。<br>- 提供同性質設備趨勢比較功能。 | system-requirement.md 3.3 |

#### **3. 資料庫結構 (Database Schema)**

以下為根據新版規格整合的核心資料庫 Schema 設計 (以 PostgreSQL 為基礎)。

**資料庫環境配置:**
- 測試區: `PostgreSQL (Docker Service - fem-postgres-dev)`
- 正式區: `PostgreSQL (GCP Cloud SQL / Docker Production)`

**`t_organization` (設施/廠區)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `unitid` | VARCHAR(48) | 設施編號 | PRIMARY KEY |
| `parentunitid` | VARCHAR(48) | 上層設施編號 | FOREIGN KEY REFERENCES t_organization(unitid) |
| `unitname` | VARCHAR(96) | 設施名稱 | NOT NULL |
| `unittype` | VARCHAR(48) | 設施類別 | NOT NULL |

**`t_equipment` (設備)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(48) | 設備編號 | PRIMARY KEY |
| `name` | VARCHAR(96) | 設備名稱 | NOT NULL |
| `assetid` | VARCHAR(48) | 設備資產 ID | |
| `unitid` | VARCHAR(48) | 所屬設施編號 | FOREIGN KEY REFERENCES t_organization(unitid) |

**`hr_organization` (組織)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(48) | 組織編號 | PRIMARY KEY |
| `parentid` | VARCHAR(48) | 上層組織編號 | FOREIGN KEY REFERENCES hr_organization(id) |
| `name` | VARCHAR(96) | 組織名稱 | NOT NULL |

**`hr_account` (使用者帳號)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `id` | VARCHAR(48) | 使用者編號 (員編/AD帳號) | PRIMARY KEY |
| `name` | VARCHAR(48) | 使用者姓名 | NOT NULL |
| `email` | VARCHAR(128) | 電子郵箱 | |
| `password_hash` | VARCHAR(255) | 加密後的密碼 | |
| `role_id` | INTEGER | 權限角色 (保留功能) | FOREIGN KEY REFERENCES roles(role_id) |
| `created_at` | TIMESTAMP | 建立時間 | DEFAULT CURRENT_TIMESTAMP |

**`roles` (角色 - 保留功能)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `role_id` | SERIAL | 角色 ID | PRIMARY KEY |
| `role_name` | VARCHAR(64) | 角色名稱 | UNIQUE, NOT NULL |
| `description` | VARCHAR(200) | 角色描述 | |

**`t_job` (巡檢任務)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `actid` | VARCHAR(48) | 工單 ID (PK) | PRIMARY KEY |
| `actkey` | VARCHAR(48) | 工單編號 (顯示用) | |
| `equipmentid` | VARCHAR(48) | 設備編號 | FOREIGN KEY REFERENCES t_equipment(id) |
| `mdate` | DATE | 檢查日期 | |
| `description` | VARCHAR(256) | 工單內容 | |
| `actmemid` | VARCHAR(48) | 負責人 ID | FOREIGN KEY REFERENCES hr_account(id) |
| `status` | VARCHAR(20) | 狀態 | DEFAULT 'Pending' |
| `created_at` | TIMESTAMP | 建立時間 | DEFAULT CURRENT_TIMESTAMP |

**`equit_check_item` (設備檢查項目)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `itemid` | VARCHAR(48) | 項目 ID | PRIMARY KEY |
| `equipmentid` | VARCHAR(48) | 設備編號 | FOREIGN KEY REFERENCES t_equipment(id) |
| `itemname` | VARCHAR(96) | 項目名稱 | NOT NULL |
| `itemdescription` | VARCHAR(256) | 項目說明 | |
| `statustype` | VARCHAR(48) | 狀態類型 | |
| `ulspec` | VARCHAR(48) | 規格上限 | |
| `llspec` | VARCHAR(48) | 規格下限 | |
| `sortorder` | INTEGER | 排序 | |

**`inspection_result` (巡檢結果)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `actid` | VARCHAR(48) | 工單 ID | FOREIGN KEY REFERENCES t_job(actid) |
| `itemid` | VARCHAR(48) | 項目 ID | FOREIGN KEY REFERENCES equit_check_item(itemid) |
| `equipmentid` | VARCHAR(48) | 設備 ID | FOREIGN KEY REFERENCES t_equipment(id) |
| `measuredvalue` | VARCHAR(48) | 量測值 | |
| `actmemid` | VARCHAR(48) | 檢查人員 ID | FOREIGN KEY REFERENCES hr_account(id) |
| `acttime` | TIMESTAMP | 量測時間 | |
| `photopath` | VARCHAR(256) | 照片路徑 | |
| `isoutofspec` | SMALLINT | 狀態代碼 | 0=未檢, 1=正常, 2=異常, 3=停機 |
| `isprocessed` | BOOLEAN | 是否已處理 | |
| `created_at` | TIMESTAMP | 建立時間 | DEFAULT CURRENT_TIMESTAMP |
| **Constraint** | PK | 複合主鍵 (actid, itemid) | |

**`abnormal_cases` (異常追蹤)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL | 追蹤 ID | PRIMARY KEY |
| `actid` | VARCHAR(48) | 工單 ID | FOREIGN KEY (actid, itemid) REFERENCES inspection_result |
| `itemid` | VARCHAR(48) | 項目 ID | |
| `equipmentid` | VARCHAR(48) | 設備 ID | |
| `measuredvalue` | VARCHAR(48) | 異常數值 | |
| `abnmsg` | VARCHAR(256) | 異常描述 | |
| `abnsolution` | TEXT | 處理方式 | |
| `isprocessed` | BOOLEAN | 是否結案 | DEFAULT FALSE |
| `responsibleperson` | VARCHAR(48) | 處理人員 | FOREIGN KEY REFERENCES hr_account(id) |
| `processedat` | TIMESTAMP | 處理時間 | |

**`system_log` (系統日誌)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `logid` | VARCHAR(48) | Log ID | PRIMARY KEY |
| `createdat` | TIMESTAMP | 時間 | NOT NULL |
| `level` | VARCHAR(20) | 等級 (INFO/WARN/ERROR) | NOT NULL |
| `module` | VARCHAR(50) | 模組名稱 | |
| `message` | TEXT | 詳細訊息 | |
| `exception` | TEXT | 異常堆疊資訊 | |

**`user_action_log` (使用者操作日誌)**
| 欄位名稱 | 資料型態 | 描述 | 約束 |
| :--- | :--- | :--- | :--- |
| `id` | SERIAL | Log ID | PRIMARY KEY |
| `userid` | VARCHAR(48) | 操作者 ID | FOREIGN KEY REFERENCES hr_account(id) |
| `timestamp` | TIMESTAMP | 執行時間 | DEFAULT CURRENT_TIMESTAMP |
| `actiontype` | VARCHAR(64) | 動作類別 | NOT NULL |
| `description` | VARCHAR(256) | 操作描述 | |
| `changes` | JSONB | 變更內容 | (PostgreSQL JSONB) |
| `ipaddress` | VARCHAR(48) | 使用者 IP | |
| `status` | VARCHAR(20) | 執行狀態 | |

---

### **第二部分:API 系統**

#### **1. API 功能清單 (API Function List)**

API 作為後台與行動 APP 之間的溝通橋樑。

| **功能類別** | **API 端點** | **HTTP Method** | **描述** | **使用對象** | **參考** |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **認證與授權** | `/api/auth/login` | POST | 使用者登入並獲取 JWT token (Local/Azure AD) | APP, Web | system-requirement.md 3.1, 4.1 |
| **認證與授權** | `/api/auth/azure/login` | GET | 產生 Azure AD 授權 URL，導向 Microsoft 登入頁 | Web | - |
| **認證與授權** | `/api/auth/azure/callback` | GET | Azure AD OAuth 回調，用授權碼換取 Token 並發放 JWT | Web | - |
| **認證與授權** | `/api/auth/logout` | POST | 使用者登出 | APP, Web | system-requirement.md 3.1 |
| **認證與授權** | `/api/auth/refresh` | POST | 重新整理 token | APP, Web | - |
| **任務管理** | `/api/tasks/download` | GET | 下載指派給該使用者的巡檢任務與表單內容至 APP 本地 | APP | system-requirement.md 4.1, 4.2 |
| **任務管理** | `/api/tasks/list` | GET | 取得任務列表 (支援狀態、日期篩選與分頁) | APP, Web | system-requirement.md 4.1 |
| **任務管理** | `/api/tasks` | POST | 建立新任務 | Web | system-requirement.md 4.1 |
| **任務管理** | `/api/tasks/{task_id}` | GET | 取得特定任務詳細資訊 | APP, Web | system-requirement.md 3.3 |
| **任務管理** | `/api/tasks/{task_id}` | PUT | 更新任務資訊 | Web | system-requirement.md 4.1 |
| **任務管理** | `/api/tasks/{task_id}` | DELETE | 刪除任務 | Web | system-requirement.md 4.1 |
| **任務管理** | `/api/tasks/{task_id}/status` | PUT | 更新任務狀態 | APP | system-requirement.md 4.2 |
| **資料同步** | `/api/results/upload` | POST | 將 APP 本地儲存的巡檢結果 (包含量測數據、照片、異常原因) 回傳至後台伺服器 | APP | system-requirement.md 4.2 |
| **資料同步** | `/api/results/sync` | POST | 批次同步巡檢結果 | APP | system-requirement.md 2 |
| **資料同步** | `/api/results/photos/upload` | POST | 上傳異常照片 (multipart/form-data) | APP | system-requirement.md 4.2 |
| **組織與設施** | `/api/organizations/tree` | GET | 取得組織樹狀結構 | Web | system-requirement.md 3.3, 3.4 |
| **組織與設施** | `/api/organizations/list` | GET | 取得組織列表 (扁平結構) | Web | system-requirement.md 3.3 |
| **組織與設施** | `/api/organizations/{org_id}` | GET | 取得組織詳情 (支援 include_facilities, include_users) | Web | system-requirement.md 3.3 |
| **組織與設施** | `/api/organizations/{org_id}/facilities` | GET | 取得組織的設施列表 | Web | system-requirement.md 3.4 |
| **組織與設施** | `/api/facilities/tree` | GET | 取得設施樹狀結構 | Web | system-requirement.md 3.4 |
| **組織與設施** | `/api/facilities/list` | GET | 取得設施列表 (支援篩選和分頁) | Web | system-requirement.md 3.4 |
| **組織與設施** | `/api/facilities/{facility_id}` | GET | 取得設施詳情 | Web | system-requirement.md 3.4 |
| **組織與設施** | `/api/facilities/{facility_id}/equipment` | GET | 取得設施的設備列表 | Web | system-requirement.md 3.4 |
| **組織與設施** | `/api/facilities/equipment/all` | GET | 取得所有設備列表 (用於下拉選單) | Web | system-requirement.md 3.4 |
| **使用者管理** | `/api/users/list` | GET | 取得使用者列表 (支援搜尋、篩選與分頁) | Web | system-requirement.md 3.1 |
| **使用者管理** | `/api/users/{user_id}` | GET | 取得使用者詳細資訊 | Web | system-requirement.md 3.1 |
| **使用者管理** | `/api/users/create` | POST | 建立新使用者 | Web | system-requirement.md 3.1 |
| **使用者管理** | `/api/users/{user_id}/update` | PUT | 更新使用者資訊 | Web | system-requirement.md 3.1 |
| **使用者管理** | `/api/users/{user_id}/password` | PUT | 重設使用者密碼 | Web | system-requirement.md 3.1 |
| **使用者管理** | `/api/users/{user_id}/delete` | DELETE | 刪除使用者 (軟刪除 - 停用帳號) | Web | system-requirement.md 3.1 |
| **使用者管理** | `/api/users/roles` | GET | 取得角色列表 | Web | system-requirement.md 3.1 |
| **查詢與報表** | `/api/inspection/records` | GET | 查詢巡檢紀錄 | Web | system-requirement.md 3.3 |
| **查詢與報表** | `/api/inspection/records/{task_id}/details` | GET | 取得巡檢紀錄詳細資訊 (可鑽取至檢查項目) | Web | system-requirement.md 3.3 |
| **查詢與報表** | `/api/inspection/statistics` | GET | 取得儀表板統計資料 | Web | system-requirement.md 3.2 |
| **查詢與報表** | `/api/inspection/abnormal/tracking` | GET | 異常追蹤查詢 | Web | system-requirement.md 3.2 |
| **系統日誌** | `/api/system-logs/list` | GET | 取得系統日誌列表 | Web | - |
| **系統日誌** | `/api/system-logs/stats` | GET | 取得系統日誌統計資訊 | Web | - |
| **系統日誌** | `/api/system-logs/action-types` | GET | 取得所有操作類型 | Web | - |
| **系統日誌** | `/api/system-logs/{log_id}` | GET | 取得日誌詳細資訊 | Web | - |

#### **2. API 規格 (API Specification)**

以下為主要的 API 端點 (Endpoint) 詳細設計。

##### **2.1 認證與授權**

本系統支援兩種認證方式：**Local 帳密登入** 與 **Azure AD (Microsoft Entra ID) OAuth 2.0 授權碼登入**。

###### Azure AD 認證流程圖

```
[前端 App / 瀏覽器]
    │
    │ 1. GET /api/v1/auth/azure/login
    ▼
[Flask API]
    │
    │ 2. 回傳 Azure AD 授權 URL (auth_url)
    ▼
[前端 App / 瀏覽器]
    │
    │ 3. 導向 Microsoft 登入頁面
    ▼
[Azure AD (Microsoft)]
    │
    │ 4. 使用者輸入 AD 帳密，認證成功
    │
    │ 5. 回調 GET /api/v1/auth/azure/callback?code=AUTHORIZATION_CODE
    ▼
[Flask API]
    │
    │ 6. 使用 MSAL 將 code 換取 id_token
    │ 7. 從 id_token 取得 preferred_username
    │ 8. 以 username 查詢 hr_account.id
    │ 9. 若存在 → 發放本系統 JWT Token
    │    若不存在 → 401 此帳號未授權使用本系統
    ▼
[前端接收 JWT Token，後續 API 呼叫帶入 Authorization Header]
```

> **核心認知**：Azure AD 僅負責驗證身份。AD 帳號 = `hr_account.id`，認證成功後直接查詢資料庫中對應的使用者，不需要額外的資料庫欄位。

---

**2.1.1 Local 使用者登入**

* **Endpoint**: `/api/auth/login`
* **Method**: `POST`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "username": "admin",
    "password": "1234qwer5T",
    "login_type": "local"
  }
  ```

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "refresh_token_string",
      "expires_in": 3600,
      "user": {
        "id": "admin",
        "name": "系統管理員",
        "organizationid": "ORG-ADMIN",
        "email": "admin@chimei.com"
      }
    }
  }
  ```

* **Response Body (Error - 401 Unauthorized)**:
  ```json
  {
    "status": "error",
    "message": "帳號或密碼錯誤"
  }
  ```

---

**2.1.2 Azure AD 授權 URL 取得**

* **Endpoint**: `/api/auth/azure/login`
* **Method**: `GET`
* **描述**: 產生 Azure AD OAuth 2.0 授權 URL，前端需將使用者導向此 URL 以進行 Microsoft 登入。

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "auth_url": "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/authorize?client_id=...&redirect_uri=...&scope=User.Read&response_type=code"
    }
  }
  ```

* **Response Body (Error - 503 Service Unavailable)**:
  ```json
  {
    "status": "error",
    "message": "Azure AD 認證未啟用"
  }
  ```

---

**2.1.3 Azure AD OAuth 回調**

* **Endpoint**: `/api/auth/azure/callback`
* **Method**: `GET`
* **描述**: Microsoft 登入成功後自動導向此端點，系統接收 authorization code 並換取 token。
* **Query Parameters**:
  - `code`: Azure AD 回傳的授權碼 (由 Microsoft 自動帶入)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "refresh_token": "refresh_token_string",
      "expires_in": 3600,
      "user": {
        "id": "I0001",
        "name": "張文雄",
        "organizationid": "ORG-ADMIN",
        "email": "user001@chimei.com"
      }
    }
  }
  ```

* **Response Body (Error - 401 Unauthorized)**:
  ```json
  {
    "status": "error",
    "message": "此帳號未授權使用本系統"
  }
  ```

* **Response Body (Error - 400 Bad Request)**:
  ```json
  {
    "status": "error",
    "message": "Azure AD 認證失敗：未提供授權碼"
  }
  ```

---

**2.1.4 Azure AD 環境設定**

| 環境變數 | 說明 | 範例 |
| :--- | :--- | :--- |
| `USE_AZURE_AD` | 是否啟用 Azure AD 認證 | `true` |
| `AZURE_CLIENT_ID` | Azure 應用程式註冊 Client ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_CLIENT_SECRET` | Azure 應用程式 Client Secret | `your-secret` |
| `AZURE_TENANT_ID` | Azure AD 租戶 ID | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` |
| `AZURE_REDIRECT_URI` | OAuth 回調 URL | `https://your-domain/api/v1/auth/azure/callback` |

**Azure Portal Redirect URI 設定：**

| 環境 | Redirect URI |
| :--- | :--- |
| Production | `https://<YOUR_DOMAIN>/api/v1/auth/azure/callback` |
| 本地開發 | `http://localhost:5000/api/v1/auth/azure/callback` |

##### **2.2 任務管理**

**任務下載**

* **Endpoint**: `/api/tasks/download`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `date`: 指定日期 (可選,格式: YYYY-MM-DD)
  - `current_user`: 當前使用者任務

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "tasks": [
        {
          "assigned_to": "I0001",
          "assigned_user_name": "張文雄",
          "completion_rate": 0.0,
          "description": "MAE05D31 V2真空泵浦馬達 定期巡檢",
          "equipment_check_items": [
            {
              "data_type": "數值",
              "is_required": true,
              "item_description": "馬達本體溫度檢查",
              "item_id": "MAE05D31-C02",
              "item_name": "馬達本體溫度",
              "lower_limit": "35.0",
              "status_type": "數值",
              "upper_limit": "80.0"
            } 
          ],
          "equipment_id": "MAE05D31",
          "equipment_name": "MAE05D31 V2真空泵浦馬達",
          "inspection_date": "2025-12-31",
          "facility_id": "AREA_MOTOR_ROOM",
          "facility_name": "馬達機房",
          "status": "Pending",
          "task_id": "TASK20251231156",
          "task_number": "TASK20251231156"
        }
      ],
      "last_sync": "2025-11-25T16:50:00Z",
      "total_count": 1,
      "synced_at": "2025-11-25T16:50:00Z"
    }
  }
  ```

##### **2.3 資料同步**

**巡檢結果上傳**

* **Endpoint**: `/api/results/upload`
* **Method**: `POST`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Content-Type**: `application/json`
* **Request Body**:
  ```json
  {
    "task_id": "TASK-20251014-001",
    "results": [
      {
        "equipment_id": "MAE05D31",
        "item_id": "ITEM-C01",
        "result_value": "65.5",
        "result_status": "正常",
        "is_abnormal": false,
        "rfid_scanned": true,
        "check_time": "2025-10-14T10:32:38Z",
        "inspector_id": "USER005"
      },
      {
        "equipment_id": "MAE05D31",
        "item_id": "ITEM-C05",
        "result_value": "4.05",
        "result_status": "異常",
        "is_abnormal": true,
        "abnormal_reason": "軸承潤滑油異常(請更換)",
        "rfid_scanned": true,
        "check_time": "2025-10-14T10:35:18Z",
        "inspector_id": "USER005",
        "photo_data": "base64_encoded_image_string"
      },
      {
        "equipment_id": "MAE05D32",
        "item_id": "ITEM-C10",
        "result_value": "停機",
        "result_status": "停機",
        "is_abnormal": false,
        "rfid_scanned": false,
        "rfid_skip_reason": "設備維修中無法感應",
        "check_time": "2025-10-14T10:40:25Z",
        "inspector_id": "USER005"
      }
    ]
  }
  ```

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "message": "資料上傳完成",
    "data": {
      "uploaded_count": 3,
      "failed_count": 0,
      "result_ids": [50001, 50002, 50003]
    }
  }
  ```

* **Response Body (Partial Success - 207 Multi-Status)**:
  ```json
  {
    "status": "partial_success",
    "message": "部分資料上傳失敗",
    "data": {
      "uploaded_count": 2,
      "failed_count": 1,
      "errors": [
        {
          "index": 1,
          "reason": "檢查項目 ID 不存在"
        }
      ]
    }
  }
  ```

**照片上傳**

* **Endpoint**: `/api/photos/upload`
* **Method**: `POST`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Content-Type**: `multipart/form-data`
* **Request Body**:
  - `result_id`: 結果 ID
  - `photo_type`: 照片類型 (異常/佐證)
  - `file`: 圖片檔案

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "photo_id": 8001,
      "photo_path": "/uploads/photos/2025/10/14/photo_8001.jpg"
    }
  }
  ```

**任務列表查詢**

* **Endpoint**: `/api/tasks/list`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `status`: 狀態篩選 (Pending/InProgress/Completed)
  - `start_date`: 開始日期 (YYYY-MM-DD)
  - `end_date`: 結束日期 (YYYY-MM-DD)
  - `page`: 頁碼
  - `page_size`: 每頁筆數
  - `current_user`: 當前使用者任務

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "tasks": [
        {
          "assigned_to": "I0001",
          "assigned_user_name": "張文雄",
          "completion_rate": 0.0,
          "description": "MAE05D31 V2真空泵浦馬達 定期巡檢",
          "equipment_check_items": [
            {
              "data_type": "數值",
              "is_required": true,
              "item_description": "馬達本體溫度檢查",
              "item_id": "MAE05D31-C02",
              "item_name": "馬達本體溫度",
              "lower_limit": "35.0",
              "status_type": "數值",
              "upper_limit": "80.0"
            } 
          ],
          "equipment_id": "MAE05D31",
          "equipment_name": "MAE05D31 V2真空泵浦馬達",
          "inspection_date": "2025-12-31",
          "facility_id": "AREA_MOTOR_ROOM",
          "facility_name": "馬達機房",
          "status": "Pending",
          "task_id": "TASK20251231156",
          "task_number": "TASK20251231156"
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 20,
        "total": 1,
        "pages": 1,
        "has_next": false,
        "has_prev": false
      }
    }
  }
  ```

**建立新任務**

* **Endpoint**: `/api/tasks`
* **Method**: `POST`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Content-Type**: `application/json`
* **Request Body**:
  - `equipment_id`: 設備 ID (必填)
  - `inspection_date`: 檢查日期 (YYYY-MM-DD, 必填)
  - `assigned_to`: 指派人員 ID (必填)
  - `description`: 任務描述 (可選)

* **Response Body (Success - 201 Created)**:
  ```json
  {
    "status": "success",
    "message": "任務建立成功",
    "data": {
      "task": {
        "task_id": "TASK-NEW-001",
        "task_number": "TASK20251125001",
        "status": "Pending",
        "created_at": "2025-11-25T10:00:00Z"
      }
    }
  }
  ```

**更新任務資訊**

* **Endpoint**: `/api/tasks/{task_id}`
* **Method**: `PUT`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Content-Type**: `application/json`
* **Request Body**:
  - `equipment_id`: 設備 ID (可選)
  - `inspection_date`: 檢查日期 (可選)
  - `assigned_to`: 指派人員 ID (可選)
  - `status`: 狀態 (可選)
  - `description`: 描述 (可選)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "message": "任務更新成功",
    "data": {
      "task": {
        "task_id": "TASK-20251014-001",
        "status": "InProgress"
      }
    }
  }
  ```

**更新任務狀態**

* **Endpoint**: `/api/tasks/{task_id}/status`
* **Method**: `PUT`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Content-Type**: `application/json`
* **Request Body**:
  - `status`: 新狀態 (Pending/InProgress/Completed)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "message": "任務狀態已更新",
    "data": {
      "task": {
        "task_id": "TASK-20251014-001",
        "status": "Completed"
      }
    }
  }
  ```

**刪除任務**

* **Endpoint**: `/api/tasks/{task_id}`
* **Method**: `DELETE`
* **Header**: `Authorization: Bearer {jwt_token}`

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "message": "任務已刪除"
  }
  ```

**取得特定任務詳細資訊**

* **Endpoint**: `/api/tasks/{task_id}`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "task": {
        "task_id": "TASK-20251014-001",
        "task_number": "TASK20251014001",
        "equipment_id": "MAE05D31",
        "equipment_name": "MAE05D31 V2真空泵浦馬達",
        "inspection_date": "2025-10-14",
        "status": "InProgress",
        "results": []
      }
    }
  }
  ```

##### **2.5 組織與設施管理**

**取得組織詳情 (增強)**

* **Endpoint**: `/api/organizations/{org_id}`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `include_facilities`: 是否包含設施列表 (可選, 預設 false)
  - `include_users`: 是否包含使用者列表 (可選, 預設 false)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "organization": {
        "org_id": "ORG-ADMIN",
        "parent_org_id": null,
        "org_name": "行政處",
        "facilities": [
          {
            "facility_id": "PLANT_A",
            "facility_name": "A廠區",
            "facility_type": "Plant",
            "equipment_count": 25
          }
        ],
        "users": [
          {
            "user_id": "USER001",
            "full_name": "張文雄",
            "email": "user001@chimei.com"
          }
        ]
      }
    }
  }
  ```

**取得組織的設施列表**

* **Endpoint**: `/api/organizations/{org_id}/facilities`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `include_equipment`: 是否包含設備統計 (可選, 預設 false)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "org_id": "ORG-ADMIN",
      "org_name": "行政處",
      "facilities": [
        {
          "facility_id": "PLANT_A",
          "facility_name": "A廠區",
          "facility_type": "Plant",
          "parent_facility_id": null,
          "equipment_count": 15
        }
      ],
      "total_count": 1
    }
  }
  ```

**取得設施樹狀結構**

* **Endpoint**: `/api/facilities/tree`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `org_id`: 組織 ID (可選，篩選特定組織的設施)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "facilities": [
        {
          "facility_id": "PLANT_A",
          "facility_name": "A廠區",
          "facility_type": "Plant",
          "parent_facility_id": null,
          "org_id": "ORG-ADMIN",
          "org_name": "行政處",
          "children": [
            {
              "facility_id": "FLOOR_A1_1F",
              "facility_name": "A1廠房-1樓",
              "facility_type": "Floor",
              "parent_facility_id": "PLANT_A",
              "org_id": "ORG-ADMIN",
              "children": []
            }
          ]
        }
      ],
      "total_count": 1
    }
  }
  ```

**取得設施列表**

* **Endpoint**: `/api/facilities/list`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `org_id`: 組織 ID (可選)
  - `parent_id`: 上層設施 ID (可選)
  - `facility_type`: 設施類型 (可選)
  - `page`: 頁碼 (預設 1)
  - `page_size`: 每頁筆數 (預設 20，最大 100)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "facilities": [
        {
          "facility_id": "PLANT_A",
          "facility_name": "A廠區",
          "facility_type": "Plant",
          "parent_facility_id": null,
          "org_id": "ORG-ADMIN",
          "org_name": "行政處",
          "equipment_count": 15
        }
      ],
      "pagination": {
        "page": 1,
        "page_size": 20,
        "total": 1,
        "pages": 1,
        "has_next": false,
        "has_prev": false
      }
    }
  }
  ```

**取得設施詳情**

* **Endpoint**: `/api/facilities/{facility_id}`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `include_equipment`: 是否包含設備資訊 (可選, 預設 false)
  - `include_children`: 是否包含子設施 (可選, 預設 false)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "facility": {
        "facility_id": "PLANT_A",
        "facility_name": "A廠區",
        "facility_type": "Plant",
        "parent_facility_id": null,
        "org_id": "ORG-ADMIN",
        "org_name": "行政處",
        "equipment_count": 15,
        "children": [
          {
            "facility_id": "FLOOR_A1_1F",
            "facility_name": "A1廠房-1樓",
            "facility_type": "Floor",
            "parent_facility_id": "PLANT_A"
          }
        ]
      }
    }
  }
  ```

**取得設施的設備列表**

* **Endpoint**: `/api/facilities/{facility_id}/equipment`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "facility_id": "PLANT_A",
      "facility_name": "A廠區",
      "equipment": [
        {
          "equipment_id": "MAE05D31",
          "equipment_name": "真空泵浦馬達",
          "equipment_type": "馬達",
          "asset_id": "ASSET-001"
        }
      ],
      "total_count": 1
    }
  }
  ```

##### **2.5 查詢與報表**

**儀表板統計資料**

* **Endpoint**: `/api/inspection/statistics`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `date`: 查詢日期 (可選,預設為今日)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "abnormal_tracking": {
        "today_abnormal": 5,
        "today_attention": 12,
        "accumulated_abnormal_open": 23,
        "accumulated_attention_open": 45
      },
      "inspection_tasks": {
        "not_assigned": 3,
        "not_completed": 8,
        "in_progress": 5,
        "completed": 42
      }
    }
  }
  ```

**巡檢紀錄查詢**

* **Endpoint**: `/api/inspection/records`
* **Method**: `GET`
* **Header**: `Authorization: Bearer {jwt_token}`
* **Query Parameters**:
  - `org_id`: 組織 ID (可選)
  - `start_date`: 開始日期 (格式: YYYY-MM-DD)
  - `end_date`: 結束日期 (格式: YYYY-MM-DD)
  - `status`: 狀態篩選 (可選)
  - `page`: 頁碼 (預設: 1)
  - `page_size`: 每頁筆數 (預設: 20)

* **Response Body (Success - 200 OK)**:
  ```json
  {
    "status": "success",
    "data": {
      "total": 156,
      "page": 1,
      "page_size": 20,
      "records": [
        {
          "task_id": "TASK-20251014-001",
          "task_number": "TASK20251014001",
          "org_name": "行政處",
          "inspection_date": "2025-10-14",
          "inspector_name": "張文雄",
          "status": "已完成",
          "has_abnormal": true,
          "completion_rate": 100.0,
          "start_time": "2025-10-14T08:30:00Z",
          "end_time": "2025-10-14T11:45:00Z"
        }
      ]
    }
  }
  ```

#### **3. API 安全規範**

* **認證機制**: 使用 JWT (JSON Web Token) 進行使用者身份驗證
* **Token 有效期**: 1 小時
* **Token 重新整理**: 提供 refresh token 機制,有效期 7 天
* **HTTPS**: 所有 API 呼叫必須透過 HTTPS 加密傳輸
* **Rate Limiting**: 實施 API 呼叫頻率限制,防止濫用
* **Input Validation**: 所有輸入參數進行嚴格驗證
* **Error Handling**: 統一的錯誤回應格式,不洩露敏感資訊

#### **4. API 錯誤代碼**

| HTTP 狀態碼 | 錯誤代碼 | 描述 |
| :--- | :--- | :--- |
| 400 | BAD_REQUEST | 請求參數錯誤 |
| 401 | UNAUTHORIZED | 未授權,需要登入 |
| 403 | FORBIDDEN | 禁止訪問,權限不足 |
| 404 | NOT_FOUND | 資源不存在 |
| 409 | CONFLICT | 資源衝突 |
| 422 | UNPROCESSABLE_ENTITY | 資料驗證失敗 |
| 429 | TOO_MANY_REQUESTS | 請求過於頻繁 |
| 500 | INTERNAL_SERVER_ERROR | 伺服器內部錯誤 |
| 503 | SERVICE_UNAVAILABLE | 服務暫時無法使用 |

---

### **第三部分:部署與維運規範**

#### **1. 基礎設施需求**

* **資料庫環境**:
  - 測試區: `SQLDEVXXX,1433`
  - 正式區: `APPSQLXXX,1433`
  - 驗證方式: SQL Login 與 AD Login
  - 權限管理: 遵循最小權限原則

* **網路設定**:
  - 需設定系統網域名稱 (DNS)
  - 開啟 Web 服務通訊埠 (443 for HTTPS)
  - 開啟 PostgreSQL 通訊埠 (5432)
  - 配置防火牆規則

* **SSL/TLS 憑證**:
  - 所有網路傳輸使用 SSL/TLS 加密
  - 定期更新憑證

#### **2. 部署流程**

* 建立標準化部署程序
* 實施資料庫遷移策略 (使用 Flask-Migrate)
* 配置環境變數管理
* 建立自動化部署 Pipeline

#### **3. 備份與災難復原**

* 資料庫每日自動備份
* 保留至少 30 天的備份記錄
* 定期進行災難復原演練
* 建立 RPO (Recovery Point Objective) 與 RTO (Recovery Time Objective) 指標

#### **4. 監控與日誌**

* 實施應用程式日誌記錄 (Logging)
* 監控系統效能指標
* 設定告警機制
* 記錄所有 API 呼叫
* 追蹤異常與錯誤

#### **5. 效能優化**

* 使用 Flask-Caching 進行快取
* 資料庫查詢優化
* 實施 CDN 加速靜態資源
* 定期進行效能分析與調整

---

### **第四部分:Mobile APP 整合規範**

#### **1. 離線模式運作**

* **本地資料庫**: SQLite
* **資料同步策略**:
  - APP 啟動時下載最新任務
  - 支援離線模式執行巡檢
  - 網路恢復後自動同步結果
  - 衝突解決機制

#### **2. 資料收集方式**

* **量測採集**: 按壓採集按鈕進行數據收集
* **RFID 感應**: 支援 RFID 標籤感應驗證
* **照片上傳**: 支援異常照片拍攝與上傳
* **設備狀態**: 支援標記備機、檢修、停機等狀態

#### **3. APP 功能**

* 使用者登入 (系統名稱: Smart 設備保養)
* 任務列表顯示 (含完成度環圈圖)
* 管制點選擇
* 檢查項目執行
* 異常處理與拍照
* 資料同步
