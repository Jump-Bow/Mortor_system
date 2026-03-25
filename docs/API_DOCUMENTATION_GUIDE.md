# API 文件使用指南

## Swagger UI API 文件

系統已整合 Swagger UI，提供完整的 API 互動式文件。

### 訪問 API 文件

啟動應用程式後，可透過以下網址訪問 Swagger UI：

```
http://localhost:5000/api/docs
```

或在生產環境中：

```
https://your-domain.com/api/docs
```

### 功能特色

1. **互動式測試**
   - 所有 API 端點都可以直接在瀏覽器中測試
   - 支援 "Try it out" 功能，即時查看回應結果

2. **完整的 API 規格**
   - Request/Response 範例
   - 參數說明與類型定義
   - 錯誤碼與錯誤訊息說明

3. **JWT 認證整合**
   - 支援在 Swagger UI 中輸入 JWT Token
   - 自動在請求標頭中加入 Authorization

### 使用步驟

#### 1. 取得 JWT Token

首先使用登入 API 取得 Token：

**POST** `/api/v1/auth/login` 或 `/api/auth/login`

```json
{
  "login_type": "local",
  "username": "admin",
  "password": "your_password"
}
```

成功後會回傳：

```json
{
  "status": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "user": {
      "user_id": "admin",
      "full_name": "系統管理員",
      "role": {
        "role_id": 1,
        "role_name": "管理者"
      }
    }
  }
}
```

#### 2. 在 Swagger UI 中授權

1. 點擊頁面右上角的 **"Authorize"** 按鈕
2. 在彈出的對話框中輸入：`Bearer your_token_here`
   - 注意：必須包含 `Bearer ` 前綴
   - 例如：`Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...`
3. 點擊 **"Authorize"** 確認
4. 之後所有 API 請求都會自動帶入此 Token

#### 3. 測試 API

1. 選擇要測試的 API 端點
2. 點擊 **"Try it out"** 按鈕
3. 填寫必要的參數
4. 點擊 **"Execute"** 執行
5. 查看 Response 區域的回應結果

### API 端點分類

所有 API 依功能分為以下類別：

> **API 版本說明**：系統支援兩種存取路徑
> - `/api/v1/*` - 明確指定 v1 版本
> - `/api/*` - 指向最新版本（目前為 v1）

- **認證** (`/api/v1/auth/*` 或 `/api/auth/*`)
  - `POST /login` - 使用者登入 (Local 帳密)
  - `GET /azure/login` - 取得 Azure AD 授權 URL
  - `GET /azure/callback` - Azure AD OAuth 回調
  - `POST /logout` - 使用者登出
  - `POST /refresh` - Token 刷新
  - `GET /verify` - 驗證 Token
  - `GET /me` - 取得當前使用者資訊

- **使用者管理** (`/api/users/*`)
  - `GET /list` - 取得使用者列表
  - `GET /<user_id>` - 取得使用者詳情
  - `POST /` - 建立使用者
  - `PUT /<user_id>` - 更新使用者
  - `DELETE /<user_id>` - 刪除使用者
  - 需管理員權限

- **組織管理** (`/api/v1/organizations/*` 或 `/api/organizations/*`)
  - `GET /tree` - 組織樹狀結構
  - `GET /list` - 組織列表（扁平結構）
  - `GET /<org_id>` - 組織詳情
  - `GET /<org_id>/facilities` - 組織下的設施

- **設施管理** (`/api/v1/facilities/*` 或 `/api/facilities/*`)
  - `GET /tree` - 設施樹狀結構
  - `GET /list` - 設施列表（扁平結構）
  - `GET /<facility_id>` - 設施詳情
  - `GET /<facility_id>/equipment` - 設施下的設備
  - `GET /equipment/all` - 所有設備列表

- **任務管理** (`/api/v1/tasks/*` 或 `/api/tasks/*`)
  - `GET /download` - 下載巡檢任務
  - `GET /list` - 任務列表查詢
  - `GET /<task_id>` - 任務詳情
  - `POST /` - 建立任務
  - `PUT /<task_id>` - 更新任務

- **結果上傳** (`/api/v1/results/*` 或 `/api/results/*`)
  - `POST /upload` - 巡檢結果上傳
  - `POST /photo` - 照片上傳

- **巡檢查詢** (`/api/v1/inspection/*` 或 `/api/inspection/*`)
  - `GET /statistics` - 統計資料查詢
  - `GET /records` - 巡檢記錄查詢
    - 參數:
      - `page`: 頁碼 (預設 1)
      - `page_size`: 每頁筆數 (預設 20)
      - `start_date`: 開始日期 (YYYY-MM-DD)
      - `end_date`: 結束日期 (YYYY-MM-DD)
      - `org_id`: 組織代號
      - `equipment_id`: 設備代號
      - `act_key`: 任務編號 (模糊搜尋)
      - `status`: 任務狀態 (未派工/執行中/已完成)
      - `group`: 馬達類別
      - `mterm`: 保養週期
      - `has_abnormal`: 是否有異常 (true/false)
  - `GET /records/<task_id>/details` - 任務詳細記錄
  - `GET /progress` - 巡檢進度查詢
    - 參數:
      - `page`: 頁碼
      - `page_size`: 每頁筆數
      - `start_date`: 開始日期
      - `end_date`: 結束日期
      - `group`: 馬達類別
      - `mterm`: 保養週期
      - `status`: 狀態篩選
  - `GET /abnormal/tracking` - 異常追蹤
    - 參數:
      - `page`: 頁碼
      - `page_size`: 每頁筆數
      - `start_date`: 開始日期
      - `end_date`: 結束日期
      - `org_id`: 組織代號
      - `equipment_id`: 設備代號
      - `group`: 馬達類別
      - `mterm`: 保養週期
      - `case_status`: 案件狀態 (未結案/已結案)
      - `abnormal_type`: 異常類型 (異常/注意)
  - `GET /trend/<equipment_id>` - 把表趨勢圖 - 設備歷史量測資料
    - 參數:
      - `start_date`: 開始日期 (YYYY-MM-DD)
      - `end_date`: 結束日期 (YYYY-MM-DD)
    - 回傳: `dates`、`items`（含 `unit`/`max_v`）、`records`
  - `GET /comparison` - 同性質設備比較查詢（舊版）
  - `GET /comparison/items` - 取得去重後檢查項目樹
    - 回傳: 依 `unit` 分類的 `categories`（馬達-振動/馬達-溫度）
  - `GET /comparison/equip-trend` - 多設備在同一項目的時序趨勢
    - 參數:
      - `item_name`: 項目名稱（必填），例： MIH振動量測
      - `equip_ids`: 設備 ID 清單（可多筆）
      - `start_date`: 開始日期
      - `end_date`: 結束日期
    - 回傳: `item_name`、`unit`、`max_v`、`dates`、`series`（每台設備的時序資料）

- **系統日誌** (`/api/system-logs/*`)
  - `GET /list` - 操作日誌查詢
  - `GET /stats` - 日誌統計
  - `GET /action-types` - 操作類型列表
  - 需管理員權限

### 常見 API 使用範例

#### 範例 1：Azure AD 登入流程

**步驟 1：取得 Azure AD 授權 URL**
```http
GET /api/v1/auth/azure/login
```

回應範例：
```json
{
  "status": "success",
  "data": {
    "auth_url": "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?client_id=...&redirect_uri=...&scope=User.Read&response_type=code"
  }
}
```

**步驟 2：前端導向 `auth_url`，使用者在 Microsoft 頁面完成登入**

**步驟 3：Microsoft 自動回調 callback 端點，系統回傳 JWT Token**
```http
GET /api/v1/auth/azure/callback?code=AUTHORIZATION_CODE
```

回應範例：
```json
{
  "status": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token": "...",
    "expires_in": 3600,
    "user": {
      "id": "I0001",
      "name": "張文雄",
      "email": "user001@chimei.com"
    }
  }
}
```

> **注意**：Azure AD 帳號必須與系統 `hr_account.id` 對應，否則回傳 401。

#### 範例 2：下載巡檢任務

```http
GET /api/v1/tasks/download?date=2024-10-28
Authorization: Bearer your_token_here
```

回應範例：
```json
{
  "status": "success",
  "data": {
    "tasks": [
      {
        "task_id": 1,
        "task_number": "TSK-20241028-001",
        "equipment_id": "EQ001",
        "equipment_name": "空調主機 A",
        "inspection_date": "2024-10-28",
        "status": "Pending",
        "assigned_to": "user001",
        "completion_rate": 0,
        "equipment_check_items": [...]
      }
    ],
    "total_count": 5,
    "synced_at": "2024-10-28T08:00:00Z"
  }
}
```

#### 範例 3：上傳巡檢結果

```http
POST /api/v1/results/upload
Authorization: Bearer your_token_here
Content-Type: application/json

{
  "task_id": 1,
  "results": [
    {
      "item_id": "CI001",
      "result_value": "正常",
      "is_abnormal": false,
      "check_time": "2024-10-28T10:30:00",
      "inspector_id": "user001"
    }
  ]
}
```

回應範例：
```json
{
  "status": "success",
  "message": "結果上傳成功",
  "data": {
    "uploaded_count": 1,
    "failed_count": 0
  }
}
```

#### 範例 4：查詢組織樹

```http
GET /api/v1/organizations/tree
Authorization: Bearer your_token_here
```

#### 範例 5：查詢設施樹

```http
GET /api/v1/facilities/tree?org_id=ORG001
Authorization: Bearer your_token_here
```

#### 範例 6：查詢巡檢統計

```http
GET /api/v1/inspection/statistics?start_date=2024-10-01&end_date=2024-10-31
Authorization: Bearer your_token_here
```

#### 範例 6：查詢系統日誌（需管理員權限）

```http
GET /api/system-logs/list?page=1&per_page=20&action_type=LOGIN
Authorization: Bearer admin_token_here
```

### Response 格式

所有 API 回應均遵循統一格式：

**成功回應**：
```json
{
  "status": "success",
  "message": "操作成功",
  "data": { ... }
}
```

**錯誤回應**：
```json
{
  "status": "error",
  "message": "錯誤訊息說明"
}
```

### HTTP 狀態碼

- `200 OK` - 請求成功
- `201 Created` - 建立成功
- `400 Bad Request` - 請求參數錯誤
- `401 Unauthorized` - 未授權或 Token 無效
- `403 Forbidden` - 權限不足
- `404 Not Found` - 資源不存在
- `500 Internal Server Error` - 伺服器錯誤

### 注意事項

1. **Token 過期處理**
   - Access Token 預設 24 小時後過期
   - 使用 Refresh Token 可換取新的 Access Token
   - API: `POST /api/v1/auth/refresh`

2. **檔案上傳**
   - 照片上傳支援兩種方式：
     - Base64 編碼（適用於批次上傳）
     - multipart/form-data（適用於單張上傳）
   - 最大檔案大小：16MB

3. **分頁參數**
   - `page`: 頁碼（從 1 開始）
   - `per_page` 或 `page_size`: 每頁筆數
   - 預設每頁 20 筆

4. **日期格式**
   - 統一使用 ISO 8601 格式
   - 日期：`YYYY-MM-DD`（例：2024-10-28）
   - 日期時間：`YYYY-MM-DDTHH:mm:ss`（例：2024-10-28T10:30:00）

### Swagger 規格檔案

如需直接存取 Swagger JSON 規格檔案：

```
http://localhost:5000/api/swagger.json
```

此檔案可匯入其他 API 工具（如 Postman）使用。

### 疑難排解

**問題 1：無法載入 Swagger UI**
- 確認應用程式已正確啟動
- 檢查 `/app/swagger/swagger.json` 檔案是否存在
- 查看瀏覽器開發者工具的 Console 是否有錯誤訊息

**問題 2：API 測試返回 401 錯誤**
- 確認已點擊 "Authorize" 按鈕並輸入有效的 Token
- 檢查 Token 格式是否正確（需包含 `Bearer ` 前綴）
- 確認 Token 尚未過期

**問題 3：CORS 錯誤**
- 確認請求來源在允許的 CORS 清單中
- 檢查 `config.py` 中的 CORS 設定

### 更多資訊

- Flask-Swagger-UI 官方文件: https://github.com/sveint/flask-swagger-ui
- OpenAPI 3.0 規格: https://swagger.io/specification/
- Swagger Editor（線上編輯器）: https://editor.swagger.io/
