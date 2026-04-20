# 系統管理功能完善指南

## 已完成功能

### 1. 使用者管理 (User Management)

#### 1.1 API 端點 (`app/api/users.py`)

- **GET** `/api/users/list` - 取得使用者列表
  - 支援過濾：角色、啟用狀態、搜尋關鍵字
  - 支援分頁
  
- **GET** `/api/users/<user_id>` - 取得使用者詳細資訊
  
- **POST** `/api/users/create` - 建立新使用者
  - 必填欄位：username, password, full_name, role_id
  - 驗證：使用者名稱格式、密碼強度、角色存在性
  
- **PUT** `/api/users/<user_id>/update` - 更新使用者資訊
  - 可更新：full_name, employee_id, ad_account, role_id, is_active
  
- **PUT** `/api/users/<user_id>/password` - 重設使用者密碼
  - 僅管理者可執行
  
- **DELETE** `/api/users/<user_id>/delete` - 停用使用者 (軟刪除)
  - 防止刪除自己的帳號
  
- **GET** `/api/users/roles` - 取得角色列表

#### 1.2 Web 路由

- **GET** `/system/users` - 使用者管理頁面
  - 僅管理者可訪問

#### 1.3 前端功能 (`app/templates/system/users.html`)

- 使用者列表展示 (DataTables)
- 角色、狀態過濾
- 搜尋功能 (使用者名稱、姓名、員工編號)
- 新增使用者對話框
- 編輯使用者對話框
- 重設密碼對話框
- 停用使用者功能

### 2. 系統日誌 (System Logs)

#### 2.1 API 端點 (`app/api/system_logs.py`)

- **GET** `/api/system-logs/list` - 取得系統日誌列表
  - 支援過濾：使用者、操作類型、日期範圍
  - 支援分頁
  
- **GET** `/api/system-logs/stats` - 取得統計資訊
  - 總操作數
  - 依操作類型統計
  - 活躍使用者排行 (Top 10)
  - 每日活動趨勢
  
- **GET** `/api/system-logs/action-types` - 取得所有操作類型
  
- **GET** `/api/system-logs/<log_id>` - 取得日誌詳細資訊

#### 2.2 Web 路由

- **GET** `/system/logs` - 系統日誌頁面
  - 僅管理者可訪問

#### 2.3 前端功能 (`app/templates/system/logs.html`)

- 統計卡片顯示
  - 總操作數
  - 活躍使用者數
  - 操作類型數
  - 統計天數
- 每日活動趨勢圖表 (Chart.js)
- 活躍使用者排行榜
- 日誌列表展示 (DataTables)
- 操作類型、日期範圍過濾
- 搜尋功能

### 3. 組織架構 (Organization Tree)

#### 3.1 已更新功能

- 使用 session 中的 API token 進行認證
- 改善日期時間顯示格式 (使用 moment.js)
- 修正路由跳轉路徑

### 4. 權限控制

#### 4.1 新增裝飾器 (`app/utils/decorators.py`)

- `@admin_required` - 驗證管理者權限
  - 檢查使用者角色是否為「管理者」
  - 返回 403 Forbidden 如果權限不足

#### 4.2 Web 路由權限檢查

- 使用者管理頁面：僅管理者可訪問
- 系統日誌頁面：僅管理者可訪問

### 5. UI 更新

#### 5.1 側邊欄導航 (`app/templates/layout/base.html`)

- 系統管理選單
  - 使用者管理連結
  - 系統日誌連結
  - 僅對管理者顯示
  - 支援 active 狀態顯示

## 功能特色

### 使用者管理

✅ 完整的 CRUD 操作
✅ 角色管理整合
✅ 密碼加密儲存
✅ 密碼重設功能
✅ 軟刪除 (停用帳號)
✅ 搜尋與過濾
✅ 分頁支援
✅ 表單驗證
✅ 操作日誌記錄

### 系統日誌

✅ 完整的日誌查詢
✅ 多維度過濾
✅ 統計圖表展示
✅ 活躍度分析
✅ 操作類型分類
✅ 日期範圍查詢
✅ 分頁支援
✅ 視覺化圖表

### 組織架構

✅ 樹狀結構展示
✅ 組織詳情查看
✅ 關聯路線顯示
✅ 完整路徑顯示

## 使用方式

### 1. 啟動應用

```bash
# 確保已安裝所有相依套件
pip install -r requirements.txt

# 初始化資料庫 (如果尚未初始化)
python init_db.py

# 啟動應用
python run.py
```

### 2. 登入系統

使用管理者帳號登入：
- 預設使用者名稱：`admin`
- 預設密碼：`admin123` (應該在 init_db.py 中設定)

### 3. 訪問管理功能

登入後，在側邊欄可看到「系統管理」選單 (僅管理者)：
- 使用者管理：`/system/users`
- 系統日誌：`/system/logs`

### 4. 使用者管理操作

#### 新增使用者
1. 點擊「新增使用者」按鈕
2. 填寫必填欄位：
   - 使用者名稱 (3-50 字元，僅英文、數字、底線)
   - 密碼 (至少 6 個字元)
   - 姓名
   - 角色
3. 選填欄位：員工編號、AD 帳號
4. 點擊「儲存」

#### 編輯使用者
1. 點擊使用者列表中的編輯按鈕
2. 修改資訊
3. 可切換啟用/停用狀態
4. 點擊「儲存」

#### 重設密碼
1. 點擊使用者列表中的鑰匙圖示
2. 輸入新密碼 (至少 6 個字元)
3. 點擊「重設密碼」

#### 停用使用者
1. 點擊使用者列表中的刪除按鈕
2. 確認操作
3. 使用者將被停用 (可稍後重新啟用)

### 5. 系統日誌查詢

#### 查看統計
- 頁面頂部顯示統計卡片
- 每日活動趨勢圖表
- 活躍使用者排行榜

#### 篩選日誌
1. 選擇操作類型 (可選)
2. 設定日期範圍 (可選)
3. 輸入搜尋關鍵字 (可選)
4. 點擊「搜尋」

#### 日誌類型
系統會記錄以下操作：
- `WEB_LOGIN` - 網頁登入
- `WEB_LOGOUT` - 登出
- `API_LOGIN` - API 登入
- `USER_CREATE` - 建立使用者
- `USER_UPDATE` - 更新使用者
- `USER_DELETE` - 停用使用者
- `USER_PASSWORD_RESET` - 重設密碼
- `TASK_CREATE` - 建立任務
- `TASK_UPDATE` - 更新任務
- `INSPECTION_SUBMIT` - 提交巡檢結果

## 技術棧

### 後端
- Flask - Web 框架
- SQLAlchemy - ORM
- Flask-Login - 使用者認證
- JWT - API 認證

### 前端
- AdminLTE 3 - 管理介面框架
- jQuery - JavaScript 函式庫
- DataTables - 表格元件
- Chart.js - 圖表元件
- Moment.js - 日期時間處理
- Toastr - 通知訊息
- Bootstrap 4 - UI 框架

## 安全性考量

1. **密碼加密**：使用 werkzeug 的 password hash
2. **JWT 認證**：API 端點使用 JWT token 認證
3. **CSRF 保護**：Web 表單使用 CSRF token
4. **權限檢查**：管理功能僅限管理者訪問
5. **操作日誌**：記錄所有重要操作
6. **軟刪除**：使用者停用而非直接刪除

## 未來增強建議

### 使用者管理
- [ ] 批次匯入使用者
- [ ] 匯出使用者列表
- [ ] 使用者權限細粒度控制
- [ ] 密碼複雜度設定
- [ ] 密碼過期機制
- [ ] 登入失敗鎖定

### 系統日誌
- [ ] 日誌匯出 (CSV/Excel)
- [ ] 更多統計維度
- [ ] 異常行為偵測
- [ ] 自動清理舊日誌
- [ ] 日誌備份機制

### 組織架構
- [ ] 組織新增/編輯/刪除
- [ ] 組織拖放排序
- [ ] 組織成員管理
- [ ] 組織權限設定

## 測試建議

### 功能測試
1. 測試使用者 CRUD 操作
2. 測試權限控制
3. 測試密碼重設
4. 測試日誌記錄
5. 測試搜尋與過濾
6. 測試分頁功能

### 安全測試
1. 測試未授權訪問
2. 測試 SQL 注入防護
3. 測試 XSS 防護
4. 測試 CSRF 防護
5. 測試密碼強度驗證

### 效能測試
1. 測試大量使用者載入
2. 測試大量日誌查詢
3. 測試並發操作

## 疑難排解

### 問題 1: API 返回 401 未授權
**原因**：Session 中沒有 API token
**解決**：重新登入系統

### 問題 2: 無法看到系統管理選單
**原因**：當前使用者不是管理者角色
**解決**：使用管理者帳號登入

### 問題 3: DataTables 顯示異常
**原因**：語言檔載入失敗
**解決**：檢查 `static/datatable_zh-Hant.json` 是否存在

### 問題 4: 圖表無法顯示
**原因**：Chart.js 載入失敗或資料格式錯誤
**解決**：檢查瀏覽器 console 錯誤訊息

## 相關檔案清單

### 後端 API
- `app/api/users.py` - 使用者管理 API
- `app/api/system_logs.py` - 系統日誌 API
- `app/api/organizations.py` - 組織管理 API (既有)

### 前端模板
- `app/templates/system/users.html` - 使用者管理頁面
- `app/templates/system/logs.html` - 系統日誌頁面
- `app/templates/organization/tree.html` - 組織架構頁面 (已更新)
- `app/templates/layout/base.html` - 基礎模板 (已更新)

### 工具與裝飾器
- `app/utils/decorators.py` - 裝飾器 (新增 admin_required)
- `app/utils/validators.py` - 驗證器 (既有)

### 資料模型
- `app/models/user.py` - 使用者與角色模型
- `app/models/system_log.py` - 系統日誌模型
- `app/models/organization.py` - 組織模型

### 路由與設定
- `app/web_routes.py` - Web 路由 (已更新)
- `app/__init__.py` - 應用初始化 (已更新)

## 版本資訊

- **版本**: 1.0.0
- **更新日期**: 2025-01-15
- **作者**: Development Team
