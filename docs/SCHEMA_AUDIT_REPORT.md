# 系統架構與頁面整合審計報告 (Schema & Web Consistency Audit Report)

本報告針對 `chimei-fem-admin` 專案的 **資料庫架構 (Schema)** 與 **網頁前端 (Web View)** 之間的對應關係進行深度審計。

## 1. 執行摘要 (Executive Summary)

經過詳細的程式碼審查，發現 **網頁前端模板 (Templates)** 與 **後端 API 回傳格式** 存在嚴重的 **命名慣例不一致 (Naming Convention Mismatch)**。這主要源於專案從舊有的 MSSQL 架構遷移至 PostgreSQL 時，後端模型已採用 snake_case (或全小寫) 風格，但前端頁面仍保留了舊有或不一致的欄位引用。

**風險等級**: 🔴 **高 (Critical)** - 主要功能頁面 (使用者管理、任務列表) 將無法正常顯示資料。

---

## 2. 審計發現詳情 (Detailed Findings) - MECE 分析

### 2.1 使用者管理模組 (User Management)

*   **前端**: `app/templates/system/Mortor_users.html`
*   **後端**: `app/api/Mortor_users.py` / `app/models/Mortor_user.py`

| 欄位概念 | 前端需求欄位 (JS/HTML) | 後端 API 回傳欄位 (Response) | 狀態 | 差異分析 |
| :--- | :--- | :--- | :--- | :--- |
| 使用者 ID | `user_id` / `user.user_id` | `id` | ❌ 錯誤 | 前端預期 `user_id`，但後端回傳 `id`。 |
| 使用者名稱 | `username` | `id` (作為 username) | ❌ 錯誤 | 使用者名稱概念混淆，後端無 `username` 欄位。 |
| 全名 | `full_name` | `name` | ❌ 錯誤 | 前端預期 `full_name`，但後端回傳 `name`。 |
| 員工編號 | `employee_id` | **無此欄位** | ❌ 缺漏 | 資料庫與模型中均無此欄位。 |
| AD 帳號 | `ad_account` | **無此欄位** | ❌ 缺漏 | 資料庫與模型中均無此欄位。 |
| 角色 | `role` | `role_id` (無名稱) | ❌ 錯誤 | `to_dict` 未回傳角色名稱。 |
| 啟用狀態 | `is_active` | **無此欄位** | ❌ 缺漏 | 模型中無 `is_active` 欄位。 |
| 建立時間 | `created_at` | **無此欄位** | ❌ 缺漏 | 模型中無 `created_at` 欄位。 |

### 2.2 任務管理模組 (Task Management)

*   **前端**: `app/templates/task/Mortor_list.html`
*   **後端**: `app/api/Mortor_tasks.py` / `app/models/Mortor_inspection.py`

| 欄位概念 | 前端需求欄位 (JS/HTML) | 後端 API 回傳欄位 (Response) | 狀態 | 差異分析 |
| :--- | :--- | :--- | :--- | :--- |
| 任務編號 | `task_number` | `actid` / `actkey` | ❌ 錯誤 | API 回傳 `actkey` (如 TASK-2025...) 較符合需求，但名稱不符。 |
| 設備名稱 | `equipment_name` | `equipment_name` | ✅ 正確 | 一致。 |
| 指派人員 | `assigned_user_name` | `actmemname` | ❌ 錯誤 | 前端預期 `assigned_user_name`，後端回傳 `actmemname`。 |
| 檢查日期 | `inspection_date` | `mdate` | ❌ 錯誤 | 前端預期 `inspection_date`，後端回傳 `mdate`。 |
| 完成率 | `completion_rate` | `completion_rate` | ✅ 正確 | 一致。 |
| 操作 ID | `task_id` | `actid` | ❌ 錯誤 | 前端操作依賴 `task_id`，但 API 回傳 `actid`。 |

---

## 3. 角色視角分析 (Role-Based Perspectives)

### 👨‍💻 AI 工程師 (AI Engineer)
*   **問題**: 數據欄位定義不一致 (Label Inconsistency) 會導致未來的數據清洗 (Data Cleaning) 成本極高。
*   **觀點**: `actmemname` vs `assigned_user_name` 的混用會造成特徵工程的困擾。建議統一使用語意清晰的英文命名 (如 `inspector_name`)。

### 🛡️ 資安工程師 (Security Engineer)
*   **問題**: 前端請求了不存在的 `ad_account` 欄位，這顯示系統設計時可能考慮過 AD 整合但未完全實作，容易產生 "幻覺欄位" (Ghost Fields)，誤導安全審計。
*   **風險**: 錯誤的資料對應可能導致前端顯示 `undefined`，甚至洩露堆疊追蹤資訊 (Stack Trace) 如果後端因此報錯。

### 🏗️ 系統架構師 (System Architect)
*   **根本原因 (First Principles)**: 違反了 "Single Source of Truth"。Datamodel (`Mortor_*.py`) 定義了一套語言，API (`api/*.py`) 轉換了一套，前端 (`html/js`) 又講另一套語言。
*   **建議**: 必須建立統一的 "Data Contract" (資料契約)。

---

## 4. 改善建議 (Recommendations) - 5W1H

| 構面 | 行動 |
| :--- | :--- |
| **What** | 重構 API 的回應格式 (`to_dict` 方法及其封裝) 以匹配前端需求，或修正前端以匹配 API。 |
| **Why** | 從根本解決資料顯示錯誤與無法操作的問題。 |
| **Who** | 後端工程師負責修正 API Response Transformer。 |
| **How** | 建議 **修改後端 API** 以適配前端 (Adapter Pattern)，因為修改前端涉及大量的 JS 邏輯變更，風險較高。 |

### 建議修正方案 (API Response Mapping)

**Users API (`api/Mortor_users.py`) 應調整為:**
```python
{
    'user_id': user.id,
    'username': user.id,  # 暫時 map 到 id
    'full_name': user.name,
    'employee_id': user.id, # 暫時 map 到 id
    'role': 'User', # 暫時 Hardcode 或關聯查詢
    'is_active': True, # 預設 True
    'created_at': datetime.now() # 暫時 Mock
}
```

**Tasks API (`api/Mortor_tasks.py`) 應調整為:**
```python
{
    'task_id': task.actid,
    'task_number': task.actkey,
    'equipment_name': task.equipment_name,
    'assigned_user_name': task.actmemname,
    'inspection_date': task.mdate,
    ...
}
```
