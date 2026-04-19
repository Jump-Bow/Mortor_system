---
type: analysis
audience: developers
date: 2026-04-18
---

# 命名一致性交叉比對報告

## 核心資料來源層級（權威順序）

```
PostgreSQL DB Schema (create_tables.sql)
    ↓
Python ORM Model (app/models/*.py)
    ↓
Python API Blueprint (app/api/*.py)
    ↓
Dart Remote DataSource (lib/data/datasources/remote/*.dart)
    ↓
Dart Model (lib/data/models/*.dart)
```

---

## 🔴 問題 1：`equit_check_item.grade` — DB 實際欄位仍是 `"group"`

### 追蹤路徑

| 層級 | 欄位名稱 | 狀態 |
|------|----------|------|
| **DB Schema** (`create_tables.sql`) | `"group"` (PostgreSQL 保留字，用引號) | ❌ 真實欄位名仍是 `group` |
| **ORM** (`Mortor_equipment.py` L54) | `grade = db.Column(db.String(24), ...)` | ⚠️ ORM 已改名，但未做 `__column_name__` 對應 |
| **API** (`Mortor_tasks.py` L68~71) | `EquitCheckItem.query.filter_by(grade=...)` | ⚠️ 依賴 ORM 的 grade |
| **API** (`Mortor_tasks.py` L218) | `equipment.check_items` | ❌ 已移除的關聯，會 AttributeError |

### 根本原因
DB 實際欄位是 `"group"`（PostgreSQL 保留字），Python ORM 改為 `grade` 但沒有設定 `column_name='group'` 對應。這表示：
- 若 migration 已在 DB 執行了 ALTER COLUMN，則 DB 已改成 `grade` → ORM OK
- 若 migration 未執行，DB 還是 `"group"` → ORM 的 `grade` 屬性對應不到，查詢會報錯

**需要確認：** 實際 DB 目前欄位名稱為何？

---

## 🔴 問題 2：`list_tasks` 仍使用已移除的 `equipment.check_items` 關聯

### 追蹤路徑

| 位置 | 程式碼 | 狀態 |
|------|--------|------|
| `Mortor_equipment.py` TEquipment 模型 | **沒有** `check_items` relationship 定義 | ❌ 關聯已移除 |
| `Mortor_tasks.py` L218 `list_tasks()` | `equipment.check_items.order_by(...)` | ❌ AttributeError 必發 |
| `Mortor_tasks.py` L238 `list_tasks()` | `task.equipment.check_items.count()` | ❌ AttributeError 必發 |
| `Mortor_tasks.py` L67 `download_tasks()` | **已修正**：用 `EquitCheckItem.query.filter_by(grade=..., mterm=...)` | ✅ 正確 |

### 修正方向
`list_tasks()` 的第 216~242 行需與 `download_tasks()` 的第 68~101 行對齊。

---

## 🔴 問題 3：`AbnormalCases` FK Constraint 只有 2 欄，但 `inspection_result` PK 是 3 欄

### 追蹤路徑

| 層級 | 主鍵定義 | 問題 |
|------|----------|------|
| **DB** `inspection_result` | `actid + item_id + equipmentid` (三欄複合 PK) | 真實 DB 結構 |
| **ORM** `InspectionResult` | `actid PK + item_id PK + equipmentid PK` | ✅ ORM 正確 |
| **ORM** `AbnormalCases.__table_args__` | FK to `(actid, item_id)` **只有 2 欄** | ❌ 少了 `equipmentid`，FK 無法正確建立 |

### 根本原因
`Mortor_abnormal.py` 第 27-30 行：
```python
db.ForeignKeyConstraint(
    ['actid', 'item_id'],              # ← 少了 equipmentid
    ['inspection_result.actid', 'inspection_result.item_id']
)
```
對應的 `inspection_result` PK 實際是 `(actid, equipmentid, item_id)`，FK constraint 2欄無法關聯 3欄 PK，會造成 DB 層的 constraint 無效或建立失敗。

---

## 🟡 問題 4：`result_remote_data_source.dart` 不處理 HTTP 207

| 層級 | 狀態 |
|------|------|
| **後端** `Mortor_results.py` | 明確設計 `207 partial_success` 語意 |
| **Dart** `result_remote_data_source.dart` L44 | 只判斷 `statusCode == 200`，207 會走 `else { throw ServerException }` |

### 影響
- 後端部分成功（有些 item 上傳失敗），回傳 `207`
- Dart 接到 207 → 拋出例外 → Repository 標記整批上傳失敗 → 下次重試時重複上傳（浪費頻寬，可能觸發 LWW 衝突）

---

## 需修正的檔案清單

| 優先 | 檔案 | 修正方式 |
|------|------|----------|
| 🔴 P1 | `app/api/Mortor_tasks.py` L216~242 | 將 `list_tasks` 的 check_items 查詢改為 `EquitCheckItem.query.filter_by(grade=task.grade, mterm=task.mterm)`，完成率計算加入 `is_out_of_spec != 0` 過濾 |
| 🔴 P1 | `app/models/Mortor_abnormal.py` L27-30 | FK Constraint 補上 `equipmentid` 第三欄 |
| 🟡 P2 | `lib/data/datasources/remote/result_remote_data_source.dart` L44 | 加入 `statusCode == 207` 的成功處理分支 |
| ℹ️ 確認 | `equit_check_item` DB 欄位 | 確認 DB 是否已執行 migration 將 `"group"` 改為 `grade` |
