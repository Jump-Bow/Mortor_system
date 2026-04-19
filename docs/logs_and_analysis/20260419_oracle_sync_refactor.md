---
type: change_log
audience: developer, devops
date: 2026-04-19
---

# 20260419 Oracle 同步機制還原與安全重構

## 摘要

本次工作分為兩個階段。第一階段還原被誤刪的 Oracle 直連同步腳本；第二階段對腳本進行深度審查，發現並修正了三個嚴重的生產安全問題，將其升版至 Production-Ready v2。

---

## 一、背景：腳本被誤刪的原因

在 2026-04-10 的 `20260410_084817_fix_cloudbuild_clean_diag_steps` 分支中，`scripts/sync_oracle_data.py` 連同 `oracledb` / `pandas` 套件、`libaio1` 系統套件，被一併從專案中移除，但 `devops/cloudbuild-main.yaml` 的步驟五卻仍然指向這支不存在的腳本，導致 `motor-oracle-sync` Cloud Run Job 部署後若觸發執行，會立即因 `FileNotFoundError` 崩潰。

---

## 二、本次修改清單（共 3 個 Commit）

### Commit 1 — `b4980df`
**分支**：`20260419_還原Oracle直連同步機制`  
**時間**：2026-04-19 16:51

**修改內容**：
```
Dockerfile       ← 補回 libaio1 系統套件
requirements.txt ← 補回 oracledb==2.1.2, pandas==2.1.4
scripts/sync_oracle_data.py ← 從 Git 歷史 commit b0c15c5 還原
```

**說明**：Oracle Thick Mode 需要 `libaio1` 底層 I/O 函式庫，以及 `oracledb`（Python 驅動）和 `pandas`（資料轉換）。三者缺一不可，缺少任何一個都會導致容器啟動後立即崩潰。

---

### Commit 2 — `d3fc763`
**分支**：`20260419_還原Oracle直連同步機制`  
**時間**：2026-04-19 17:32

**說明**：深度審查腳本後，發現還原回來的 v1 版本存在三個嚴重問題，本次進行 Production-Ready 重構。

---

## 三、三項安全問題詳細說明

### 問題 P0-1：Extract 遺漏關鍵欄位（高風險）

**檔案**：`scripts/sync_oracle_data.py` — `main()` 函式

**問題描述**：

舊版從 Oracle 撈取工單時，SQL 語句遺漏了兩個關鍵欄位：

```sql
-- v1（有問題的版本）
SELECT actid, equipmentid, act_desc, mdate, act_mem_id
FROM t_job WHERE mdate >= '{three_months_ago}'
```

遺漏的欄位與後果：

| 遺漏欄位 | PostgreSQL `t_job` 定義 | 後果 |
|---------|------------------------|------|
| `act_key` | 工單編號，AIMS工單執行進度查詢頁面的主要聚合鍵 | 所有同步回的工單 `act_key = NULL`，前端頁面無法正常聚合顯示，功能損壞 |
| `act_mem` | 負責人姓名（非FK，App離線顯示用） | 工單負責人名稱欄位全部空白 |

**修正後**：

```sql
-- v2（修正後）
SELECT actid, equipmentid, act_desc, mdate, act_key, act_mem_id, act_mem
FROM t_job WHERE mdate >= '{three_months_ago}'
```

---

### 問題 P0-2：TRUNCATE CASCADE 連鎖刪除（災難等級）

**檔案**：`scripts/sync_oracle_data.py` — `upsert_dataframe()` 函式

**問題描述**：

舊版對主檔資料表（設備、組織、人員）採用 `TRUNCATE ... RESTART IDENTITY CASCADE` 的全量覆寫策略：

```python
# v1（危險寫法）
FULL_OVERWRITE_TABLES = {"t_organization", "t_equipment", "hr_organization", "hr_account"}
conn.execute(sa.text(f'TRUNCATE TABLE "{table_name}" RESTART IDENTITY CASCADE'))
```

PostgreSQL 的 `CASCADE` 關鍵字會自動沿外鍵約束進行連鎖刪除。當 `t_equipment` 被清空時，刪除路徑如下：

```
TRUNCATE t_equipment CASCADE
 ├─→ t_job（所有巡檢工單被刪除）
 │    ├─→ inspection_result（所有量測紀錄被刪除）
 │    └─→ abnormal_cases（所有異常追蹤案件被刪除）
```

加上腳本只撈取最近 90 天的工單，這代表同步腳本每執行一次，**90 天以前的所有歷史巡檢紀錄都會永久消失且無法還原**。

此行為違反 ISO 55000 資產管理標準的可追溯性要求，也是 SAP PM、IBM Maximo 等業界 EAM 系統中的明確 Anti-Pattern。

**修正後（SCD Type 1 Upsert）**：

```python
# v2（安全寫法）— 使用 PostgreSQL 原生 INSERT ... ON CONFLICT
TABLE_UPSERT_CONFIG = {
    "t_equipment": {
        "key": ["id"],
        "update": ["name", "assetid", "unitid"],  # 只更新這些欄位
    },
    ...
}

stmt = pg_insert(table).values(records)
stmt = stmt.on_conflict_do_update(
    index_elements=key_cols,
    set_=update_dict,
)
```

**效果**：
- 設備改名 → PostgreSQL 自動更新 `name` 欄位
- 設備不動 → 不產生無意義的 Write（減少 WAL log 膨脹）
- 歷史工單、量測結果、異常追蹤 → **完整保留，零影響**

---

### 問題 P1：inspection_result 初始化邏輯衝突（中風險）

**檔案**：`scripts/sync_oracle_data.py` — `transform_jobs()` 函式

**問題描述**：

舊版在同步時，會自動替每個新工單的每個檢查項目預建一筆空白的 `inspection_result` 紀錄：

```python
# v1（有問題）
result_df["is_out_of_spec"] = 0  # 預建空白佔位，is_out_of_spec = 0
# 然後以 ON CONFLICT DO NOTHING 寫入
```

這產生兩個問題：

**問題 A — 語意模糊**：無法區分「App 送來的正常量測值（`is_out_of_spec=0`）」和「同步腳本建立的未量測佔位空格（`is_out_of_spec=0`）」。

**問題 B — 靜默資料吞噬（致命 Bug）**：當 App 巡檢員後來上傳一筆正常的量測結果（`is_out_of_spec=0`），因為佔位空格已存在且 Key 相同，`ON CONFLICT DO NOTHING` 機制會靜默地跳過，導致 App 實際量測的正常值永遠無法寫入資料庫。

這個 Bug 不會有任何錯誤訊息，屬於「靜默資料損失」的最危險類型。

**修正後**：

完整移除 `transform_jobs()` 中建立 `inspection_result` 的所有邏輯。量測結果的建立權完全交還給 App 巡檢員，ETL 腳本不再介入。

```python
# v2：transform_jobs() 只負責解析 grade / mterm，不產生任何 inspection_result
def transform_jobs(jobs_df: pd.DataFrame) -> pd.DataFrame:
    # 解析 act_desc 取得 mterm / grade
    ...
    return jobs_df[keep_cols].copy()
    # 無 result_df，無 inspection_result 相關操作
```

---

## 四、各資料表最終同步策略（v2 正式版）

| 資料表 | 同步策略 | 說明 |
|--------|---------|------|
| `t_organization` | SCD Type 1 Upsert | 有則更新 unitname/unittype，無則新增 |
| `t_equipment` | SCD Type 1 Upsert | 有則更新 name/assetid/unitid，無則新增 |
| `hr_organization` | SCD Type 1 Upsert | 有則更新 parentid/name，無則新增 |
| `hr_account` | SCD Type 1 Upsert | 有則更新 name/organizationid/email，無則新增 |
| `t_job` | Insert + 有限 Update | 有則僅補齊 act_key/act_mem，無則新增 |
| `inspection_result` | **不同步** | 量測結果僅由 App 巡檢員產生 |
| `abnormal_cases` | **不同步** | 純 FEM 業務資料，Oracle AIMS 不存在此概念 |

---

## 五、理論依據

- **ISO 55000**：資產管理系統要求完整的可追溯性（Traceability）與歷史紀錄保留（Historical Record Retention）。`TRUNCATE CASCADE` 直接違反此要求。
- **SCD Type 1 (Slowly Changing Dimension)**：資料倉儲設計中針對「主檔更新」的標準模式，只覆蓋當前值，不刪除任何歷史關聯資料。
- **PostgreSQL `INSERT ... ON CONFLICT`**：原子性操作，避免「先 SELECT 再 INSERT/UPDATE」可能產生的 Race Condition，效能優於 MERGE 指令（適用於標準 Upsert 場景）。

---

## 六、Git 推送狀態

| 遠端 | 分支 | 狀態 |
|------|------|------|
| CHIMEI-CORP (`upstream`) | `20260419_還原Oracle直連同步機制` | ✅ 已推送，待 PR Merge |
| Jump-Bow (`origin`) | `20260419_還原Oracle直連同步機制` | ✅ 已推送，待 PR Merge |

---

## 七、後續行動

1. 在 GitHub 建立 PR，將分支合併進 `main`
2. 等待 Cloud Build 完成自動部署
3. 至 GCP Cloud Run → Jobs → `motor-oracle-sync` → 手動觸發執行
4. 確認 Log 輸出無錯誤，各資料表筆數符合預期

> **注意**：在 PR Merge 並完成部署之前，請勿提前觸發 `motor-oracle-sync`，否則容器仍會執行舊版本映像檔。
