# 登出錯誤修復與測試強化報告

## 1. 問題概述
使用者在登出 (`/logout`) 時遇到 `500 Internal Server Error`。
**根本原因**: `app/api/Mortor_auth.py` 中呼叫了不存在的 `JWTHandler.get_jwt_identity()` 方法，導致程式崩潰。

## 2. 變更內容

### 錯誤修復
- **檔案**: `app/api/Mortor_auth.py`
- **修正**: 
    - 移除錯誤的 `JWTHandler.get_jwt_identity()` 呼叫。
    - 改用裝飾器 `@token_required` 提供的 `kwargs['current_user'].id` 來獲取使用者 ID。
    - 加入 `try-except` 區塊以處理日誌記錄可能發生的錯誤，確保 API 能優雅地回傳錯誤訊息而非崩潰。

### 測試強化 (新增測試)
- **新檔案**: `tests/test_exploratory.py`
    - **邊界值測試**: 測試上傳空的或格式錯誤的巡檢數據。
    - **安全性測試**: 測試使用過期 Token 或偽造 Token 存取受保護的 API。
    - **併發測試概念**: 模擬使用者登出時的併發寫入日誌情境。
- **更新檔案**: `tests/test_auth.py`
    - 新增 `test_logout_error_handling`：驗證當日誌系統失敗時，登出 API 仍能正確回傳 500 錯誤。
    - 修正斷言 (Assertions) 以符合實際 API 回傳格式 (例如: 使用 `id` 而非 `user_id`)。

### 回歸測試修復 (維護現有測試)
在執行全面回歸測試時，發現 `tests/test_inspection.py` 和 `tests/test_tasks.py` 有多處因為資料庫 Schema 變更導致的測試失敗。已進行以下修復：
- **模型欄位名稱更新**:
    - `TJob`: 將測試中的 `actkey` 更正為 `act_key`, `actmemid` 更正為 `act_mem_id`。
    - `InspectionResult`: 將測試中的 `itemid` 更正為 `item_id`, `acttime` 更正為 `act_time`, `measuredvalue` 更正為 `measured_value`。
- **權限修復**:
    - 修正 `test_download_tasks`，使其使用一般使用者 (User) 的 Token 進行測試，而非管理員 Token，解決了 `403 Forbidden` 錯誤。

## 3. 驗證結果

### 自動化測試
所有 25 個測試案例皆通過。

```bash
tests/test_auth.py::test_login_success PASSED
tests/test_auth.py::test_logout PASSED
tests/test_exploratory.py::test_access_results_with_expired_token PASSED
tests/test_inspection.py::test_get_dashboard_statistics PASSED
tests/test_tasks.py::test_download_tasks PASSED
... (共 25 個通過)
```

### 如何執行測試
1.  **執行所有測試**:
    ```bash
    pytest tests/ -v
    ```
2.  **僅執行認證相關測試**:
    ```bash
    pytest tests/test_auth.py -v
    ```

## 4. 結論
登出功能的 500 錯誤已完全修復。測試套件已擴充並與當前的資料庫架構同步，確認無 Regression (回歸) 錯誤。
