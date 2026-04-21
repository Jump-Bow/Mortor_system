---
type: technical-brief
audience: IT Infrastructure / DevOps / Security Teams
date: 2026-04-21
---

# 設備保養管理系統 — IT 技術說明文件

> 本文件供 IT 人員了解系統的完整架構、使用工具、程式碼功能與安全防護機制。
> 如需業務功能說明，請參閱 `docs/features/`；如需 API 規格，請參閱 `docs/api_and_data/`。

---

## 目錄

1. [系統定位與範疇](#1-系統定位與範疇)
2. [整體架構](#2-整體架構)
3. [技術堆疊清單](#3-技術堆疊清單)
4. [後端服務模組說明](#4-後端服務模組說明)
5. [資料庫設計](#5-資料庫設計)
6. [Oracle AIMS 資料同步（ETL）](#6-oracle-aims-資料同步etl)
7. [容器化與部署](#7-容器化與部署)
8. [安全防護機制](#8-安全防護機制)
9. [日誌與可觀測性](#9-日誌與可觀測性)
10. [環境變數與機密管理](#10-環境變數與機密管理)
11. [維運注意事項](#11-維運注意事項)

---

## 1. 系統定位與範疇

**設備保養管理系統（FEM Admin）** 是奇美集團設備巡檢數位化平台的核心後端服務，負責：

| 角色 | 說明 |
|------|------|
| **管理後台 API** | 提供 Web 管理介面（儀表板、報表、異常追蹤）所需的 RESTful API |
| **行動 App 後端** | 供 Android 行動應用（`chimei-fem-app`）下載任務、上傳量測結果、同步資料 |
| **資料整合中介** | 從上游 Legacy Oracle AIMS 系統抽取設備/工單主檔，轉換後存入 PostgreSQL |

系統**不**負責：量測硬體驅動（由 App 端透過 USB 直連）、Azure AD 帳號管理（由 Microsoft 365 管理）。

---

## 2. 整體架構

```
┌─────────────────────────────────────────────────────────────┐
│                     使用者端                                 │
│  ┌──────────────────┐     ┌─────────────────────────────┐   │
│  │  Web 管理後台     │     │  Android 行動 App            │   │
│  │  (Browser)       │     │  (chimei-fem-app, Flutter)  │   │
│  └────────┬─────────┘     └──────────────┬──────────────┘   │
│           │ HTTPS (REST)                  │ HTTPS (REST)     │
└───────────┼───────────────────────────────┼──────────────────┘
            │                               │
┌───────────▼───────────────────────────────▼──────────────────┐
│                    GCP Cloud Run                              │
│  ┌──────────────────────────────────────────────────────┐    │
│  │          FEM Admin Backend  (Python Flask 3.0)       │    │
│  │  ┌──────────┐  ┌──────────┐  ┌───────────────────┐  │    │
│  │  │ Auth API │  │ Task API │  │ Inspection API ... │  │    │
│  │  └──────────┘  └──────────┘  └───────────────────┘  │    │
│  │         Gunicorn WSGI (4 workers x 2 threads)        │    │
│  └───────────────────────┬──────────────────────────────┘    │
│                          │                                    │
│  ┌────────────────────────▼──────────────────────────────┐   │
│  │  Cloud SQL (PostgreSQL 16) 生産資料庫                  │   │
│  │  資料表：t_job / t_equipment / inspection_result /     │   │
│  │          hr_account / hr_organization / abnormal_cases │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                               │
│  ┌──────────────┐  ┌──────────────────────────────────────┐  │
│  │  Cloud Run   │  │  GCS Bucket                          │  │
│  │  Job (排程)  │  │  (巡檢照片儲存)                       │  │
│  │  ETL 同步腳本 │  └──────────────────────────────────────┘  │
│  └──────┬───────┘                                             │
└─────────┼───────────────────────────────────────────────────┘
          │ Oracle Thick Mode (oracledb + Instant Client 19.x)
          │ TCP 1521 (VPN / 私有網路)
┌─────────▼───────────────────┐
│  Oracle 11.2g (AIMS 系統)   │
│  chimei.t_job                │
│  chimei.t_equipment          │
│  chimei.hr_account / ...     │
└─────────────────────────────┘
```

### 關鍵設計原則

- **唯讀 Oracle**：ETL 腳本對 Oracle AIMS 資料庫**僅執行 SELECT**，絕對不寫入任何資料。
- **PostgreSQL 為唯一寫入目標**：所有業務資料（巡檢結果、異常紀錄）只存於 PostgreSQL。
- **行動端離線優先**：行動 App 下載工單後，可在離線狀態執行巡檢，之後再批次上傳。

---

## 3. 技術堆疊清單

### 3.1 後端框架

| 套件 | 版本 | 用途 |
|------|------|------|
| Python | 3.10.13 | 執行環境 |
| **Flask** | 3.0.0 | Web 框架（WSGI） |
| **Gunicorn** | 最新穩定版 | WSGI 伺服器（Production） |
| Flask-SQLAlchemy | 3.1.1 | ORM（Object Relational Mapper） |
| Flask-Migrate | 4.0.5 | 資料庫 Schema 版控（Alembic） |
| Flask-Login | 0.6.3 | Session 管理 |
| Flask-CORS | 4.0.0 | 跨域資源共享控制 |
| Flask-WTF | 1.2.1 | CSRF 防護 |
| Flask-Caching | 2.1.0 | 應用層快取 |

### 3.2 資料庫與快取

| 工具 | 版本 | 用途 |
|------|------|------|
| **PostgreSQL** | 16 | 主要業務資料庫 |
| psycopg2-binary | 2.9.9 | PostgreSQL Python 驅動 |
| SQLAlchemy | 2.0.23 | 資料庫抽象層 |
| **Redis** | 5.0.1 (client) | Rate Limiting 計數器 / Token 黑名單 / 快取 |

### 3.3 認證與安全

| 套件 | 版本 | 用途 |
|------|------|------|
| PyJWT | 2.8.0 | JWT Token 簽發與驗證 |
| bcrypt | 4.1.2 | 密碼雜湊（Bcrypt） |
| **msal** | 1.26.0 | Microsoft Azure AD OAuth 2.0 |
| azure-identity | 1.15.0 | Azure 身份驗證輔助 |
| cryptography | 41.0.7 | 密碼學函式庫 |
| Flask-Talisman | 1.1.0 | HTTP Security Headers（CSP / HSTS） |

### 3.4 Oracle 整合（AIMS ETL）

| 套件 / 工具 | 版本 | 用途 |
|------------|------|------|
| **oracledb** | 2.1.2 | Python Oracle 驅動（Thick Mode） |
| Oracle Instant Client | **19.24.0**（linux x64） | Oracle 本地函式庫（.so） |
| **pandas** | 2.1.4 | 資料框架處理與轉換 |
| libaio1 | 系統套件 | Linux AIO 支援（Instant Client 依賴） |

### 3.5 API 文件

| 工具 | 版本 | 用途 |
|------|------|------|
| flask-swagger-ui | 4.11.1 | Swagger UI 互動式 API 文件（`/api/docs`） |
| marshmallow | 3.20.1 | 請求 / 回應資料驗證與序列化 |

### 3.6 雲端基礎設施（GCP）

| 服務 | 用途 |
|------|------|
| **Cloud Run** | 無伺服器容器執行（主服務） |
| **Cloud Run Job** | 排程 ETL 任務（Oracle → PostgreSQL） |
| **Cloud SQL** | 受管理 PostgreSQL 實例 |
| **Cloud Storage (GCS)** | 巡檢照片永久儲存 |
| **Secret Manager** | 機密資訊儲存（DB 密碼、Oracle 連線等） |
| **Cloud Build** | CI/CD 自動化建置與部署 |
| **Artifact Registry** | Docker Image 儲存庫 |
| **Cloud Logging** | 結構化 JSON 日誌收集 |

---

## 4. 後端服務模組說明

### 4.1 應用程式進入點與工廠模式（`app/__init__.py`）

Flask 採用 **Application Factory 模式**，透過 `create_app(env)` 函式依不同環境（`development` / `testing` / `production`）動態組合應用實例。

```
create_app()
  ├── 載入 config.py 對應環境設定
  ├── 初始化 SQLAlchemy / Redis Cache / CSRF
  ├── 設定 CORS（白名單域名）
  ├── 掛載 Rate Limiter 中間件（before_request）
  ├── 設定結構化日誌（Cloud Run JSON 格式）
  ├── 註冊所有 API Blueprint
  └── 啟動配置驗證（防止 SECRET_KEY 使用預設值）
```

### 4.2 API Blueprint 路由總覽

所有 API 以 `/api/v1/` 為前綴，同時保留 `/api/` 別名路由（向後相容）：

| Blueprint 檔案 | URL 前綴 | 主要功能 |
|----------------|---------|---------|
| `Mortor_auth.py` | `/api/v1/auth` | 登入、登出、Azure AD SSO、Token 刷新 |
| `Mortor_tasks.py` | `/api/v1/tasks` | 工單下載、建立、更新、刪除 |
| `Mortor_results.py` | `/api/v1/results` | 巡檢量測結果上傳 |
| `Mortor_inspection.py` | `/api/v1/inspection` | 儀表板統計、巡檢紀錄查詢、異常追蹤、趨勢圖 |
| `Mortor_aims.py` | `/api/v1/aims` | AIMS 資料查詢介面 |
| `Mortor_organizations.py` | `/api/v1/organizations` | 組織架構查詢 |
| `Mortor_facilities.py` | `/api/v1/facilities` | 設施與設備查詢 |
| `Mortor_users.py` | `/api/users` | 使用者管理 |
| `Mortor_system_logs.py` | `/api/system-logs` | 系統日誌查詢 |

**行動端核心流程（App ↔ 後端）：**

```
[1] 登入        POST /api/v1/auth/login
                  → 取得 access_token（1h）+ refresh_token（7d）

[2] 下載任務    GET /api/v1/tasks/download?user_id=xxx&date=YYYY-MM-DD
                  → 取得工單清單 + 各工單檢查項目定義（App 本地儲存，可離線執行）

[3] 上傳結果    POST /api/v1/results/batch
                  → 批次寫入 inspection_result
                  → 異常時自動建立 abnormal_cases

[4] 上傳照片    POST /api/v1/results/{actid}/{item_id}/photo
                  → 儲存至 GCS，URL 寫入 result_photo 欄位
```

### 4.3 任務下載功能詳解（`Mortor_tasks.py`）

`GET /api/v1/tasks/download` 的核心邏輯：

1. 驗證 JWT Token，確認呼叫者即為請求的 `user_id`（**防越權**）。
2. 依 `act_mem_id = user_id` 查詢 `t_job`，篩選指定日期後的工單。
3. 依各工單的 `grade`（保養等級：A/B/C/D）與 `mterm`（週期：1M/3M/6M/1Y）查詢通用檢查項目表（`equit_check_item`）。
4. 計算各工單的已完成項目數（**排除 `is_out_of_spec=0` 的佔位紀錄**，僅計算有效量測）。
5. 回傳完整工單資訊供 App 本地儲存並離線執行。

### 4.4 巡檢 API 功能詳解（`Mortor_inspection.py`）

| 端點 | 功能說明 |
|------|---------|
| `GET /inspection/statistics` | 儀表板統計（今日異常數、任務完成率） |
| `GET /inspection/records` | 多維度篩選巡檢紀錄（組織、日期、等級、週期、狀態） |
| `GET /inspection/progress` | 巡檢進度查詢（含未派工 / 執行中 / 已完成統計卡片） |
| `GET /inspection/trend/{equipmentid}` | 設備歷史量測趨勢圖資料 |
| `GET /inspection/abnormal/tracking` | 異常追蹤列表（已結案 / 未結案篩選） |
| `PUT /inspection/abnormal/{actid}/{item_id}` | 更新異常處理方式，自動記錄操作者與時間 |

> **組織樹狀遞迴查詢**：選取上層組織時，API 會遞迴取得所有子孫組織 ID，確保選廠區時自動包含所有下屬設施。

---

## 5. 資料庫設計

### 5.1 資料表清單（PostgreSQL）

| 資料表 | 對應 Model | 說明 |
|--------|-----------|------|
| `hr_organization` | HrOrganization | 人事組織架構（從 Oracle hr_organization 同步） |
| `hr_account` | HrAccount | 使用者帳號（ID 對應 Azure AD preferred_username） |
| `roles` | Role | 角色定義（功能預留） |
| `t_organization` | TOrganization | 設施 / 廠區（從 Oracle t_organization 同步） |
| `t_equipment` | TEquipment | 設備清單（從 Oracle t_equipment 同步） |
| `equit_check_item` | EquitCheckItem | 通用檢查項目定義（依 grade + mterm 分類） |
| `t_job` | TJob | 巡檢工單（從 Oracle t_job 同步，最近 90 天） |
| `inspection_result` | InspectionResult | 巡檢量測結果（App 巡檢員寫入，後端不預建） |
| `abnormal_cases` | AbnormalCases | 異常案例追蹤（量測異常時自動建立） |
| `sys_log` | SystemLog | 系統日誌（INFO / WARN / ERROR） |
| `user_log` | UserLog | 使用者操作日誌（記錄 IP、操作類型） |

### 5.2 核心外鍵關係

```
hr_account.id ────────────► t_job.act_mem_id      （工單負責人）
t_equipment.id ───────────► t_job.equipmentid      （工單對應設備）
t_organization.unitid ────► t_equipment.unitid     （設備所在設施）

t_job.actid ──────────────► inspection_result.actid   （量測紀錄）
equit_check_item.item_id ─► inspection_result.item_id  （量測項目）
t_equipment.id ───────────► inspection_result.equipmentid

t_job.actid ──────────────► abnormal_cases.actid    （異常連結工單）
```

### 5.3 inspection_result 複合主鍵

```sql
PRIMARY KEY (actid, item_id, equipmentid)
```

三欄聯合主鍵確保：同一台設備的同一工單同一項目，只能存在**唯一一筆**量測值（App 批次上傳時 `ON CONFLICT` 可安全 Upsert）。

### 5.4 is_out_of_spec 狀態碼

| 值 | 語意（InspectionStatus） | 說明 |
|----|--------------------------|------|
| `0` | CREATED（已建立） | 空白佔位，**不計入完成數** |
| `1` | NORMAL（正常） | 量測值在規格範圍內 |
| `2` | ABNORMAL（異常） | 量測值超出規格，自動建立 `abnormal_cases` |
| `3` | SHUTDOWN（停機） | 設備停機，自動建立 `abnormal_cases` |

---

## 6. Oracle AIMS 資料同步（ETL）

### 6.1 腳本位置與觸發方式

```
scripts/sync_oracle_data.py
```

由 **GCP Cloud Run Job**（`motor-oracle-sync`）定期排程執行，建議每日一次在離峰時段。

### 6.2 ETL 三階段流程

```
┌─────────────────────────────────────────────────────────────────┐
│ [E] Extract — 從 Oracle AIMS 讀取（僅 SELECT，不寫入）          │
│                                                                 │
│   chimei.t_job         WHERE mdate >= 最近 90 天               │
│     欄位: actid, equipmentid, act_desc, mdate,                  │
│           act_key, act_mem_id, act_mem                          │
│   chimei.t_equipment   全量（id, name, assetid, unitid）        │
│   chimei.t_organization 全量（unitid, parentunitid, ...）       │
│   chimei.hr_organization 全量（id, parentid, name）             │
│   chimei.hr_account    全量（id, name, organizationid, email）  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [T] Transform — 解析工單描述                                    │
│                                                                 │
│   正規表達式：\((?P<mterm>\d+[MY])\).*?(?P<grade>[A-Z])級       │
│   範例："(3M) A 級保養" → mterm="3M", grade="A"                │
│   無法解析的工單：記錄 WARNING 但不中止流程                      │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│ [L] Load — 依外鍵順序寫入 PostgreSQL（SCD Type 1 Upsert）       │
│                                                                 │
│   ① t_organization  （廠區主檔）                               │
│   ② t_equipment     （設備主檔）                               │
│   ③ hr_organization（人事組織）                                │
│   ④ hr_account      （人員帳號）                               │
│   ⑤ t_job           （工單：Insert-Only + 補齊 act_key/act_mem）│
│   ✗ inspection_result — 永不同步（App 巡檢員獨占寫入權）       │
│   ✗ abnormal_cases  — 純 FEM 業務資料，Oracle 不存在此概念     │
└─────────────────────────────────────────────────────────────────┘
```

### 6.3 Oracle Thick Mode 技術需求

Oracle 11.2g 舊版要求使用 **Thick Mode**（需要本地 C 函式庫），而非 Thin Mode：

| 需求項目 | 說明 |
|---------|------|
| `libaio1` | Linux 非同步 I/O 系統套件（Container 必須安裝） |
| Oracle Instant Client 19.24 | 解壓縮至 `/opt/oracle/instantclient/` |
| 環境變數 `LD_LIBRARY_PATH` | 指向 `/opt/oracle/instantclient` |
| `oracledb.init_oracle_client()` | 每進程啟動時呼叫一次（重複呼叫自動跳過） |

連線字串格式：
```
oracle+oracledb://username:password@host:1521/?service_name=SERVICE
```

### 6.4 SCD Type 1 Upsert 策略

所有主檔採用 PostgreSQL 原生的 `INSERT ... ON CONFLICT ... DO UPDATE SET` 語法（原子性操作，無 Race Condition）：

```sql
-- 以 t_equipment 為例
INSERT INTO t_equipment (id, name, assetid, unitid)
VALUES (...)
ON CONFLICT (id) DO UPDATE SET
  name    = EXCLUDED.name,
  assetid = EXCLUDED.assetid,
  unitid  = EXCLUDED.unitid
```

**工單（t_job）特殊規則**：已存在的工單只補齊 `act_key` / `act_mem`，**絕不更新** `equipmentid` / `mdate`（行動 App 的量測結果依賴此外鍵關聯，改動會造成孤兒紀錄）。

### 6.5 冪等性設計

每次執行均可重試，不會重複建立資料，也不會覆蓋 App 端已寫入的業務資料。

---

## 7. 容器化與部署

### 7.1 Multi-stage Dockerfile 設計

```
Stage 1: Builder（含編譯工具）
  └── 安裝 gcc / g++ / libpq-dev / unzip
  └── 解壓 Oracle Instant Client 19.24 zip（33 MB）至 /opt/oracle/
  └── pip install requirements.prod.txt

Stage 2: Final（最小化執行環境）
  └── 僅安裝執行期依賴（libpq5、curl、libaio1）
  └── COPY --from=builder：Python site-packages + gunicorn + Oracle .so 庫
  └── ENV LD_LIBRARY_PATH=/opt/oracle/instantclient
  └── CMD: gunicorn --workers 4 --threads 2 --timeout 60 ...
```

Multi-stage 的優點：最終 Image **不含** `gcc`、`g++`、`unzip` 等工具，縮小攻擊面與 Image 大小。

### 7.2 Gunicorn 啟動參數

| 參數 | 值 | 說明 |
|------|-----|------|
| `--workers` | 4 | 工作行程數（建議 = 2 × CPU 核心數） |
| `--threads` | 2 | 每 worker 執行緒數（提升 I/O 並行能力） |
| `--timeout` | 60 秒 | 請求超過 60 秒強制中斷 |
| `--access-logfile -` | stdout | 存取日誌輸出至 Cloud Logging |
| `--error-logfile -` | stdout | 錯誤日誌輸出至 Cloud Logging |

### 7.3 環境設定分級

| 環境 | 資料庫 | Debug | Rate Limit | Session Cookie Secure |
|------|--------|-------|-----------|----------------------|
| development | SQLite 或 PostgreSQL | 開啟 | 停用 | 關閉 |
| testing | In-memory SQLite | 開啟 | 停用 | 關閉 |
| production | Cloud SQL PostgreSQL | 關閉 | 啟用 | 開啟 |

---

## 8. 安全防護機制

### 8.1 使用者認證（雙軌機制）

#### 軌道一：本地帳號密碼登入

```
POST /api/v1/auth/login
  1. 呼叫 Rate Limiter（雙維度防暴力破解）
  2. 查詢 hr_account，bcrypt 比對密碼雜湊
  3. 驗證成功 → 簽發 access_token（1h）+ refresh_token（7d）
```

#### 軌道二：Azure Entra ID SSO（OAuth 2.0 Authorization Code Flow）

```
GET  /api/v1/auth/azure/login
       → 導向至 Microsoft 登入頁（MSAL 產生授權 URL）

GET  /api/v1/auth/azure/callback?code=...
  1. MSAL acquire_token_by_authorization_code()
  2. 從 id_token_claims.preferred_username 取得帳號
     （例：user@chimei.com → 取前段 user）
  3. 以此 ID 查詢本地 hr_account 確認帳號存在
  4. 驗證成功 → 簽發 JWT Token（與本地登入相同格式）
```

> **核心觀念**：Azure AD 僅負責**驗證身份（Authentication）**；授權（此人是否為有效使用者）由本地 `hr_account` 資料庫決定。

### 8.2 JWT Token 機制

每個 Token 包含以下 Payload：

```json
{
  "jti": "唯一 UUID（黑名單機制使用）",
  "user_id": "使用者 ID",
  "username": "使用者名稱",
  "role": "角色",
  "exp": "到期時間戳（Unix Timestamp）",
  "iat": "簽發時間戳",
  "type": "access 或 refresh"
}
```

| 防護項目 | 實作方式 |
|---------|---------|
| **Token 黑名單** | 登出時將 `jti` 存入 Redis，後續請求驗證時比對是否已撤銷 |
| **Token 類型驗證** | `access` Token 不能用於 `refresh` 端點，反之亦然 |
| **即將過期偵測** | 5 分鐘內到期時回應標記 `token_will_expire_soon`，前端可自動刷新 |
| **時鐘偏差容忍** | `JWT_LEEWAY=30` 秒，防止伺服器時鐘微小差異導致 Token 誤判過期 |
| **使用者存在驗證** | 每次請求均查詢 DB 確認 `user_id` 對應帳號仍存在 |

### 8.3 速率限制（Rate Limiting）

基於 **Redis 滑動視窗（Sliding Window）**。Redis 不可用時自動降級（不限制，不崩潰）。

#### 全局 API 限制

```
對象：所有 /api/* 路徑
規則：每 IP 每小時 100 次（可透過 RATELIMIT_DEFAULT 環境變數調整）
執行：Flask before_request 鉤子，超限回傳 HTTP 429
```

#### 登入端點強化防護（雙維度）

```
維度 1 — IP：每 IP 每 15 分鐘最多 10 次登入嘗試
維度 2 — 帳號：每帳號每 15 分鐘最多 5 次登入嘗試

目的：防止攻擊者用多個 IP 輪換，繞過單一 IP 限制（帳號鎖定維度）
```

HTTP 回應 Header（供前端展示）：
```
X-RateLimit-Limit:     100
X-RateLimit-Remaining: 87
Retry-After:           3600
```

### 8.4 CORS 跨域設定

```python
# 生産環境 CORS 白名單（不可使用 "*" + credentials，違反規範）
CORS_ORIGINS = [
    'https://fem.chimei.com',   # 正式域名
]
```

後端僅允許明確白名單域名攜帶憑證發送請求。

### 8.5 CSRF 防護

| 情境 | 防護方式 |
|------|---------|
| Web 管理後台頁面（Session） | `Flask-WTF` CSRF Token 驗證 |
| API 路由（Bearer JWT） | CSRF Exempt（JWT + CORS 白名單提供等效防護） |

### 8.6 Session Cookie 安全設定

| 設定 | 值 | 說明 |
|------|-----|------|
| `SESSION_COOKIE_SECURE` | `True` | 僅 HTTPS 傳送 |
| `SESSION_COOKIE_HTTPONLY` | `True` | 禁止 JavaScript 讀取 |
| `SESSION_COOKIE_SAMESITE` | `Lax` | 防 CSRF（Strict 會導致 Azure SSO redirect 後 Cookie 遺失） |
| `PERMANENT_SESSION_LIFETIME` | 8 小時 | Session 自動失效 |

### 8.7 資料庫操作安全防護（ETL 防災機制）

程式碼層面明確禁止以下操作，防止不可逆的資料災難：

| 禁止操作 | 原因 |
|---------|------|
| ❌ `TRUNCATE t_equipment CASCADE` | 連鎖刪除：t_job → inspection_result → abnormal_cases（不可逆） |
| ❌ 預建 `inspection_result` 空行 | `is_out_of_spec=0` 的空行會讓 App 上傳的正常值被 `ON CONFLICT DO NOTHING` 吞掉 |
| ❌ 對未定義資料表執行 Upsert | 腳本嚴格比對 `TABLE_UPSERT_CONFIG`，不在清單的資料表一律拒絕寫入 |
| ❌ 更新工單的 `equipmentid` / `mdate` | App 量測結果依賴此外鍵，變動後量測紀錄將成孤兒資料 |

### 8.8 密碼安全

```python
# 儲存：bcrypt 雜湊（自動 salt，成本因子由函式庫決定）
bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

# 連線字串：特殊字元 URL 編碼（防止 @ : / 破壞連線字串）
urllib.parse.quote_plus(DB_PASSWORD)

# 日誌輸出：密碼遮罩
re.sub(r':([^:@]{1,})@', ':****@', db_uri)
# 輸出：postgresql://fem_admin:****@host:5432/fem_prod
```

---

## 9. 日誌與可觀測性

### 9.1 雙模式日誌輸出

| 環境 | 格式 | 輸出目標 |
|------|------|---------|
| Production（Cloud Run） | **JSON 結構化**（含 `severity` / `time` 欄位） | stdout → Cloud Logging 自動解析 |
| 本地開發 | 純文字（`timestamp - module - level - message`） | `logs/fem.log`（RotatingFileHandler，10MB × 10 份備份） |

### 9.2 系統日誌資料表（`sys_log`）

| 欄位 | 說明 |
|------|------|
| `log_id` | UUID 主鍵 |
| `timestamp` | UTC 時間 |
| `level` | INFO / WARN / ERROR |
| `module` | 來源模組（如 Auth、ETL） |
| `message` | 日誌訊息 |
| `exception` | 例外堆疊（Text，可選） |

**主動寫入時機**：

| Level | 觸發時機 |
|-------|---------|
| `WARN` | Token 驗證失敗、未授權存取嘗試 |
| `ERROR` | DB 寫入失敗、Oracle 連線失敗、照片上傳失敗 |
| `INFO` | 重大業務操作（完成同步、結案異常） |

### 9.3 使用者操作日誌（`user_log`）

記錄格式：
```
[操作類型] 描述 | IP: x.x.x.x | (狀態：FAILED) | 錯誤: 訊息
```

可透過 `GET /api/system-logs` 端點查詢（需 JWT 認證）。

---

## 10. 環境變數與機密管理

### 10.1 必要環境變數清單

| 變數名稱 | 說明 | 機密層級 |
|---------|------|:--------:|
| `SECRET_KEY` | Flask Session 加密金鑰 | 🔴 高 |
| `JWT_SECRET_KEY` | JWT 簽章金鑰 | 🔴 高 |
| `PROD_DB_SERVER` | PostgreSQL 主機位址 | 🟡 中 |
| `PROD_DB_NAME` | 資料庫名稱 | 🟡 中 |
| `PROD_DB_USER` | 資料庫帳號 | 🟡 中 |
| `PROD_DB_PASSWORD` | 資料庫密碼 | 🔴 高 |
| `ORA_DB_USER` | Oracle AIMS 帳號 | 🔴 高 |
| `ORA_DB_PASS` | Oracle AIMS 密碼 | 🔴 高 |
| `ORA_DB_SERVER` | Oracle 主機位址 | 🟡 中 |
| `ORA_DB_PORT` | Oracle 連接埠（預設 1521） | 🟢 低 |
| `ORA_DB_SERVICE` | Oracle Service Name | 🟡 中 |
| `ORA_DB_SCHEMA` | Oracle Schema 前綴（預設 chimei） | 🟢 低 |
| `AZURE_CLIENT_ID` | Azure AD 應用程式 ID | 🔴 高 |
| `AZURE_CLIENT_SECRET` | Azure AD 應用程式密鑰 | 🔴 高 |
| `AZURE_TENANT_ID` | Azure AD 租用戶 ID | 🟡 中 |
| `GCS_BUCKET_NAME` | GCS Bucket 名稱 | 🟢 低 |
| `REDIS_URL` | Redis 連線字串 | 🟡 中 |

> ⚠️ **GCP 生産環境**：所有 🔴 高機密變數必須存入 **GCP Secret Manager**，避免明文出現在 Dockerfile 或 CI/CD 設定檔中。

### 10.2 啟動配置自動驗證

應用啟動時自動掃描以下 Key，若使用預設不安全值則輸出 WARNING：

```
SECRET_KEY          → 不得為 'dev-secret-key' 等預設值
JWT_SECRET_KEY      → 不得為 'jwt-secret-key' 等預設值
SQLALCHEMY_DATABASE_URI → 不得為空
```

---

## 11. 維運注意事項

### 11.1 資料庫 Schema 變更流程

一律透過 Flask-Migrate（Alembic）管理版控，**禁止手動 ALTER TABLE**：

```bash
# 產生遷移腳本
flask db migrate -m "新增 xxx 欄位"

# 套用至 DB（先在 staging 驗證，再執行 production）
flask db upgrade

# 查看目前版本與歷史
flask db current
flask db history
```

### 11.2 Oracle ETL 排程作業注意事項

| 項目 | 說明 |
|------|------|
| 網路需求 | Cloud Run Job 需透過 VPC Connector 或 Private IP 路由至 Oracle 主機（TCP 1521） |
| 資料範圍 | 每次拉取最近 **90 天**的工單，設備 / 組織主檔為全量同步 |
| 失敗處理 | 失敗後日誌明確輸出原因（連線失敗 / Schema 不符 / 欄位缺失），下次排程自動重試 |
| 冪等性 | 重複執行安全；Upsert 設計保證不建立重複資料 |

### 11.3 照片儲存說明

| 項目 | 說明 |
|------|------|
| 開發環境 | 本地 `uploads/photos/` 目錄（`UPLOAD_PROVIDER=local`） |
| 生産環境 | GCS Bucket（`UPLOAD_PROVIDER=gcs`，Cloud Run 自動切換） |
| 大小限制 | **16 MB**（`MAX_CONTENT_LENGTH`） |
| 允許格式 | `png`、`jpg`、`jpeg`、`gif` |

### 11.4 Redis 可用性與自動降級

| 依賴 Redis 的功能 | Redis 中斷時的行為 |
|------------------|------------------|
| Rate Limiting | 自動**停用**（不限制請求），記錄 WARNING |
| Token 黑名單 | 黑名單暫時失效，直到 Redis 恢復 |
| 應用層快取 | 降級為 SimpleCache（記憶體快取） |

> 建議生産環境使用高可用 Redis（GCP Memorystore 或 Redis Cluster）。

### 11.5 防火牆 / 連接埠需求

| 方向 | 來源 | 目標 | Port | 協定 |
|------|------|------|------|------|
| 入站 | 瀏覽器 / App | Cloud Run | 443 | HTTPS |
| 出站 | Cloud Run | Cloud SQL（PostgreSQL） | 5432 | TCP |
| 出站 | Cloud Run Job | Oracle AIMS | 1521 | TCP |
| 出站 | Cloud Run | Redis（Memorystore） | 6379 | TCP |
| 出站 | Cloud Run | GCS | 443 | HTTPS |
| 出站 | Cloud Run | Microsoft login endpoint | 443 | HTTPS |

---

*文件版本：v1.0*
*撰寫日期：2026-04-21*
*依據：`chimei-fem-admin` 原始碼（main branch）*
