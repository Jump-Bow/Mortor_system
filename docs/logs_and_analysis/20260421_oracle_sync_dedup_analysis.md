---
type: investigation
audience: backend-dev, dba
date: 2026-04-21
---

# Oracle Sync 去重策略分析：CardinalityViolation 根因與雙層防護設計

## 問題背景

`motor-oracle-sync` Cloud Run Job 連續出現以下錯誤：

| 時間 | 錯誤 |
|------|------|
| 2026-04-21 02:11 | `ORA-00942: table or view does not exist` |
| 2026-04-21 03:30 | `ORA-00904: "ACT_MEM": invalid identifier` |
| 2026-04-21 06:03 | `CardinalityViolation: ON CONFLICT DO UPDATE command cannot affect row a second time` |
| 2026-04-21 06:03 | `ForeignKeyViolation: hr_account violates foreign key constraint hr_account_organizationid_fkey` |

---

## 第一性原理根因分析

### Oracle AIMS `t_organization` 的設計模式

Oracle Legacy EAM 系統對 `t_organization` **並非以 `unitid` 為唯一主鍵設計**，  
而是對同一個 `unitid` 存放兩種角色的紀錄：

```
角色 A（Master Record）  ：parentunitid = unitid   → 標記此 unit 為獨立存在的實體
角色 B（Hierarchy Record）：parentunitid = 真正父節點 → 描述此 unit 在組織樹的真實位置
```

實際資料範例：

| unitid | parentunitid | unitname |
|--------|-------------|----------|
| 11102  | **11102**   | 行政部   | ← 自我指向（Master Record）|
| 11102  | **11108**   | 行政部   | ← 真實層級（Hierarchy Record）|
| 11106  | **11126**   | 財會處會計部 |
| 11106  | **11106**   | 財會處會計部 | ← 自我指向（Master Record）|

> **這不是資料錯誤，而是 1990 年代 Oracle EAM 系統的設計慣例**（類似 SAP 功能位置的 master record 模式）。

### 錯誤連鎖反應

```
Oracle t_organization 有重複 unitid（設計如此）
    ↓
舊版：Python drop_duplicates(keep='last') 依 DataFrame 順序隨機保留一筆
    ↓
可能保留「自我指向版本」→ 組織樹結構錯誤（所有節點變根節點）
    ↓
PostgreSQL ON CONFLICT — 同批次 INSERT 對同一 unitid UPDATE 兩次
    ↓
CardinalityViolation ❌
    ↓
hr_organization 同樣問題，部分 id 未成功寫入 PostgreSQL
    ↓
hr_account.organizationid FK 找不到對應 id
    ↓
ForeignKeyViolation ❌
```

---

## 修復策略：雙層防護架構（Defense in Depth）

### 第一層：Oracle SQL 層（根本修復）

在 `sync_oracle_data.py` 的 Extract 階段，對 `t_organization` 與 `hr_organization`  
改用 `ROW_NUMBER() OVER (PARTITION BY ...)` 視窗函式，在 Oracle 端做去重：

```sql
SELECT unitid, parentunitid, unitname, unittype
FROM (
    SELECT unitid, parentunitid, unitname, unittype,
           ROW_NUMBER() OVER (
               PARTITION BY unitid
               ORDER BY
                   CASE WHEN parentunitid <> unitid THEN 0 ELSE 1 END,  -- ① 優先非自我指向
                   CASE WHEN parentunitid = '*'     THEN 1 ELSE 0 END,  -- ② 避免根節點標記
                   unittype                                              -- ③ 決定性排序
           ) AS rn
    FROM chimei.t_organization
) WHERE rn = 1
```

**優先序說明：**

| 優先序 | 條件 | 意義 |
|--------|------|------|
| ① 最高 | `parentunitid <> unitid` → 排序 0 | 保留真實層級紀錄，維持正確組織樹 |
| ② 次之 | `parentunitid <> '*'` → 排序 0 | 避免保留根節點標記 |
| ③ 最低 | `unittype` 字典序 | 確保相同條件下輸出具決定性 |

### 第二層：Python upsert_dataframe() 層（安全冗餘）

```python
# ── CardinalityViolation 防護 ──────────────────────────────────────────────
# PostgreSQL ON CONFLICT DO UPDATE 不允許同批次對同一行 UPDATE 兩次。
# 若 Oracle 來源有重複主鍵（資料品質問題），必須在此去重，保留最後一筆。
before_count = len(df)
df = df.drop_duplicates(subset=key_cols, keep="last")
dup_count = before_count - len(df)
if dup_count > 0:
    logger.warning(f"  ⚠️  {table_name}: 發現並移除 {dup_count} 筆重複主鍵紀錄（CardinalityViolation 防護）")
```

### 兩層防護的角色分工

| 資料表 | 第一層（Oracle SQL） | 第二層（Python） | 說明 |
|--------|---------------------|-----------------|------|
| `t_organization` | ✅ ROW_NUMBER() 去重 | `dup_count` 必為 0，安全冗餘 | 根本修復在 SQL 層 |
| `hr_organization` | ✅ ROW_NUMBER() 去重 | `dup_count` 必為 0，安全冗餘 | 同上 |
| `t_equipment` | ❌ 無特殊去重 | ✅ 有效防護 | `id` 若有異常重複，此層救命 |
| `hr_account` | ❌ 無特殊去重 | ✅ 有效防護 | 同上 |
| `t_job` | ❌ 無特殊去重 | ✅ 有效防護 | `actid` 若有異常重複，此層救命 |

> **結論：`drop_duplicates` 的角色已從「主要修復」轉為「第二道防線」。**  
> 對已在 SQL 層去重的表，執行後 `dup_count = 0`，零副作用；  
> 對其他表，仍有實質防護價值。  
> 任何未來新增資料表只要走 `upsert_dataframe()`，自動受到保護。

---

## 其他一併修復的問題

| 錯誤 | 根因 | 修復 |
|------|------|------|
| `ORA-00942` | Oracle schema 前綴缺失 | 新增 `ORA_PREFIX = "chimei."` 環境變數，所有查詢加前綴 |
| `ORA-00904` | `act_mem`/`act_mem_id` 為 FEM 自訂欄位，Oracle 原生不存在 | 從 SELECT、keep_cols、Upsert config 三處移除 |
| `ForeignKeyViolation` | `hr_account.organizationid` 參照到 PG 中不存在的 `hr_organization.id` | 寫入前以 `valid_org_ids` 集合過濾孤兒紀錄 |

---

## 修復 Commit 紀錄

| Commit | 說明 |
|--------|------|
| `4773009` | `fix(oracle): ORA-00942 — 加入 chimei. Schema 前綴` |
| `28cbf9b` | `fix(oracle): ORA-00904 — 移除 act_mem/act_mem_id` |
| `8c578c7` | `fix(sync): CardinalityViolation 主鍵去重 + ForeignKeyViolation hr_account 孤兒過濾` |
| `a07857b` | `fix(sync): 根本修復 — 改用 Oracle ROW_NUMBER() 在 SQL 層對 t_organization/hr_organization 去重` |
