---
type: migration
audience: DBA / DevOps
date: 2026-04-22
---

# t_job 複合主鍵 Migration

## 背景

Oracle AIMS 設計：同一工單號（`actid`）可對應多台設備，每台設備一行。  
原 PostgreSQL `t_job` 以 `actid` 為單一 PK，導致每次同步只保留一筆（其餘 1093 筆被視為「重複」丟棄）。

**修正**：將 `t_job` PK 改為複合主鍵 `(actid, equipmentid)`，與 Oracle AIMS 真實設計一致。

## 影響範圍

| 資料表 | 變動內容 |
|---|---|
| `t_job` | PK 從 `actid` → `(actid, equipmentid)` |
| `inspection_result` | FK 從 `actid → t_job.actid` → `(actid, equipmentid) → t_job(actid, equipmentid)` |

## ⚠️ 執行前確認

> [!CAUTION]
> 此 Migration 會修改 PK 定義。請先確認：
> 1. 在測試環境執行並驗證，再套用正式環境
> 2. 在 Cloud SQL 執行前備份資料庫
> 3. 確認 motor-server **已停止或無流量**（避免執行中的 FK 衝突）

## Migration SQL（一次全部執行）

```sql
-- ======================================================================
-- Step 1：移除 t_job 舊的單一 PK，並使用 CASCADE 連帶刪除所有依賴的外鍵
-- (這會自動刪除 inspection_result 和 abnormal_cases 身上舊的 FK)
-- ======================================================================
ALTER TABLE t_job
    DROP CONSTRAINT IF EXISTS t_job_pkey CASCADE;

-- ======================================================================
-- Step 2：確保 equipmentid NOT NULL（PK 欄位不允許 NULL）
-- ======================================================================
UPDATE t_job SET equipmentid = '' WHERE equipmentid IS NULL;
ALTER TABLE t_job ALTER COLUMN equipmentid SET NOT NULL;

-- ======================================================================
-- Step 3：建立複合主鍵 (actid, equipmentid)
-- ======================================================================
ALTER TABLE t_job
    ADD PRIMARY KEY (actid, equipmentid);

-- ======================================================================
-- Step 4：重建 inspection_result 複合 FK
-- ======================================================================
ALTER TABLE inspection_result
    ADD CONSTRAINT inspection_result_tjob_fkey
    FOREIGN KEY (actid, equipmentid)
    REFERENCES t_job (actid, equipmentid)
    ON DELETE CASCADE;

-- ======================================================================
-- Step 5：重建 abnormal_cases 複合 FK
-- ======================================================================
ALTER TABLE abnormal_cases
    ADD CONSTRAINT abnormal_cases_tjob_fkey
    FOREIGN KEY (actid, equipmentid)
    REFERENCES t_job (actid, equipmentid)
    ON DELETE CASCADE;

-- ======================================================================
-- Step 6：驗證
-- ======================================================================
-- 確認 t_job PK
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 't_job'::regclass;

-- 確認 inspection_result FK
SELECT conname, contype, pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'inspection_result'::regclass AND contype = 'f';
```

## 執行方式（GCP Cloud SQL）

### 方法 A：Cloud SQL Studio（推薦）
1. GCP Console → Cloud SQL → `motor-db` → Cloud SQL Studio
2. 依序貼入並執行上方 SQL（每個 Step 分開確認）

### 方法 B：psql via Cloud Shell
```bash
gcloud sql connect motor-db --user=web_runtime --database=postgres
# 進入 psql 後貼入 SQL
```

## 執行後驗證

Migration 完成後，觸發 `motor-oracle-sync` Cloud Run Job，確認：
- ✅ 不再出現 `CardinalityViolation` 警告（1093 筆重複）
- ✅ `t_job: Upsert` 數量接近原始工單總數（約 1,184 筆）
- ✅ App 下載工單、上傳巡檢結果正常
