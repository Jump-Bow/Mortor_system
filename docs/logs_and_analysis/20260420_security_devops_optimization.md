---
type: optimization_log
audience: backend_engineers
date: 2026-04-20
---

# 系統安全與 DevOps 優化紀錄

## 背景

本次優化基於系統架構完整性審查的後續行動，以第一性原理識別三項核心痛點並逐一修正。

---

## 優化一：Dockerfile 改寫為 Multi-stage Build

### 問題根因
- 原本使用 Single-stage Build，`gcc`, `g++` 等編譯工具殘留於 Production Image
- `requirements.txt` 將 `pytest`, `flake8`, `black` 等測試與 Lint 工具一併打包進最終 Image

### 修正方案
新增 `requirements.prod.txt`，排除所有開發/測試工具套件，並將 `Dockerfile` 改寫為兩階段架構：

| Stage | 名稱 | 內容 |
|-------|------|------|
| Stage 1 | `builder` | 安裝 `gcc`, `g++`, `libpq-dev`；解壓 Oracle Instant Client；`pip install requirements.prod.txt` |
| Stage 2 | `final` | 複製 `site-packages` + `instantclient`；僅安裝 `libpq5`, `libaio1`, `curl` 三個執行期系統庫 |

### 效益
- **資安**：Production Image 不再含編譯工具，降低 RCE 漏洞利用風險
- **體積**：預期 Image 縮小約 200~400MB（省去 gcc 工具鏈）
- **Cache**：應用程式碼變更不會觸發 `pip install` 重新執行（Layer 順序優化）

---

## 優化二：CI/CD Pipeline 加入測試守門關卡

### 問題根因
`cloudbuild-main.yaml` 原本五個步驟（Build → Push → Deploy Service → DB Init → Oracle Sync）完全沒有執行 pytest，雖然 `tests/` 目錄有完整的 7 個測試檔案，但測試碼形同虛設。

### 修正方案
在 `cloudbuild-main.yaml` 最前面插入 **Step 0（Run Unit Tests）**：
- 使用 `python:3.10-slim` image
- 安裝 `requirements.txt` 後執行 `pytest tests/ -v --tb=short`
- `--ignore=tests/test_exploratory.py`（排除需要外部服務的 threading 探索測試）
- `Build image` 步驟加入 `waitFor: ['Run Unit Tests']`，確保測試失敗時不進行 Build/Deploy

### 效益
- 任何導致 `test_auth`, `test_tasks`, `test_inspection` 等測試失敗的程式碼，都不會被部署至 Cloud Run

---

## 優化三：登入 API 強化雙維度速率限制

### 問題根因（發現了兩層問題）

**問題 A（嚴重）**：`app/utils/decorators.py` 的 `rate_limit()` 裝飾器使用**閉包記憶體字典**計數，在 Gunicorn `--workers 4` 多進程環境下，4 個 worker 各自維護獨立的 `request_history`，限流效果為設定值的 1/N（N = worker 數量）。實際上 `rate_limit(max_requests=5)` 在 4 workers 下等同於允許 20 次／窗口，**限流完全失效**。

**問題 B（安全漏洞）**：原本僅有 IP 維度的限制，攻擊者可使用多個 IP 輪換發送，繞過 IP 維度限制，對同一帳號進行無限次暴力破解。

### 修正方案

| 修改檔案 | 修改內容 |
|---------|---------|
| `app/utils/decorators.py` | `rate_limit()` 改呼叫 `RateLimiter._check_limit()`，使用 Redis 計數，跨 Worker 共享狀態 |
| `app/middleware/rate_limiter.py` | 新增 `check_login_limit(ip, username)` 方法，同時對 IP + 帳號兩個維度獨立計數 |
| `app/api/Mortor_auth.py` | 在 `login()` 取得 username 後、執行 DB 查詢前，呼叫 `RateLimiter.check_login_limit()`；超限時返回含 `Retry-After` header 的 `429` |

### 限制參數定義

| 維度 | 觸發 Key | 限制 | 窗口 |
|------|---------|------|------|
| IP | `login_ip:{ip}` | 10 次 | 15 分鐘 |
| 帳號 | `login_account:{username}` | 5 次 | 15 分鐘 |

### 降級策略（不改變）
若 Redis 連線失敗，`RateLimiter._check_limit()` 回傳 `(False, max, 0)`，自動放行，不影響服務可用性。

---

## 改動檔案清單

| 檔案 | 狀態 | 說明 |
|------|------|------|
| `Dockerfile` | MODIFIED | Multi-stage Build（Builder + Final） |
| `requirements.prod.txt` | NEW | Production 專用依賴（排除測試/開發工具） |
| `devops/cloudbuild-main.yaml` | MODIFIED | 插入 Step 0 pytest 守門關卡 |
| `app/utils/decorators.py` | MODIFIED | `rate_limit()` 改為 Redis 計數，修復多 Worker 失效 |
| `app/middleware/rate_limiter.py` | MODIFIED | 新增 `check_login_limit()` IP+帳號雙維度方法 |
| `app/api/Mortor_auth.py` | MODIFIED | `login()` 整合帳號維度限流，DB 查詢前攔截 |
