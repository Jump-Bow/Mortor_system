# FEM 開發環境設定指南

## Windows 開發環境設定

### 1. 安裝 Python

1. 下載並安裝 Python 3.9 或以上版本：https://www.python.org/downloads/
2. 安裝時請勾選「Add Python to PATH」

### 2. 建立虛擬環境 (PowerShell)

```powershell
# 進入專案目錄
cd fem-admin

# 建立虛擬環境
python -m venv .venv

# 啟動虛擬環境
.\.venv\Scripts\Activate.ps1

# 如果遇到執行政策錯誤，請以管理員身份執行 PowerShell 並執行：
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### 3. 安裝相依套件

```powershell
# 確保虛擬環境已啟動
pip install -r requirements.txt
```

### 4. 設定環境變數

複製 `.env.example` 為 `.env`：

```powershell
copy .env.example .env
```

然後編輯 `.env` 檔案設定您的環境變數。

---

## PostgreSQL 設定與 Docker 開發

### 使用 Docker 啟動 PostgreSQL (推薦)

最簡單的方式是使用專案提供的 `docker-compose.dev.yml`：

```powershell
# 啟動 PostgreSQL 和開發環境容器
docker-compose -f docker-compose.dev.yml up -d

# 查看容器狀態
docker ps
```

這將會在 localhost:4999 啟動 Web App，並在 localhost:5433 啟動 PostgreSQL。

### 連接 PostgreSQL

如果您想要在本地執行 Flask (非 Docker) 但連接到 Docker 的 PostgreSQL，請在 `.env` 設定：

```properties
# 使用 PostgreSQL
DEV_DB_TYPE=postgresql
DEV_DB_SERVER=localhost
DEV_DB_PORT=5433
DEV_DB_NAME=fem_dev
DEV_DB_USER=fem_admin
DEV_DB_PASSWORD=devpassword123
```

### 安裝 PostgreSQL Client (Optional)

如果您需要在 Windows 上直接管理 PostgreSQL，建議安裝 pgAdmin 或 DBeaver。

### 初始化資料庫

```bash
# Windows
.\.venv\Scripts\python.exe init_db.py

# macOS/Linux
.venv/bin/python init_db.py
```

---

## 本地開發模式 (使用 SQLite)

本地開發也可以不使用 Docker，直接使用 SQLite 進行開發測試。

### 1. 環境設定

確保 `.env` 檔案中有以下設定:

```properties
# Development Database (SQLite for local testing)
DEV_DB_TYPE=sqlite
DEV_DB_PATH=./data/fem_dev.db
```

### 2. 資料庫初始化

首次使用時,需要執行資料庫初始化腳本:

```bash
# Windows
.\.venv\Scripts\python.exe init_db.py
```

這會建立 SQLite 資料庫檔案 `data/fem_dev.db` 並寫入測試資料。

### 3. 使用 SQLAlchemy ORM 操作資料

在程式碼中使用資料庫:

```python
from app import db
from app.models.Mortor_user import HrAccount
from app.models.Mortor_organization import HrOrganization
from app.models.Mortor_inspection import TJob, InspectionResult
from app.models.Mortor_equipment import TEquipment

# 使用者查詢
user = HrAccount.query.filter_by(id='admin').first()

# 取得組織列表
orgs = HrOrganization.query.all()

# 取得任務列表
tasks = TJob.query.filter_by(actmemid='I0001').all()
```

### 4. 切換到 PostgreSQL

當需要連接實際的 PostgreSQL Server (GCP Cloud SQL 或地端伺服器) 時,修改 `.env`:

```properties
# 使用 PostgreSQL
DEV_DB_TYPE=postgresql
DEV_DB_SERVER=35.x.x.x
DEV_DB_PORT=5432
DEV_DB_NAME=fem_prod
DEV_DB_USER=fem_admin
DEV_DB_PASSWORD=your-password
```

### 6. AIMS 系統整合

本地開發預設使用 Mock AIMS 資料:

```properties
USE_MOCK_AIMS=true
```

如需連接真實 AIMS API:

```properties
USE_MOCK_AIMS=false
AIMS_API_URL=https://aims.example.com/api
AIMS_API_KEY=your-api-key
```

### 7. Azure AD 整合

本地開發預設不使用 Azure AD:

```properties
USE_AZURE_AD=false
```

如需測試 Azure AD 登入:

```properties
USE_AZURE_AD=true
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
```

### 8. 啟動應用程式

```bash
# 安裝相依套件
pip install -r requirements.txt

# 初始化資料庫 (首次執行)
python init_db.py

# 啟動 Flask 應用程式
python run.py
```

應用程式預設使用 SQLite 資料庫 (`data/fem_dev.db`)。

### 9. API 測試

所有 API 端點都可正常運作:

```bash
# 登入
curl -X POST http://localhost:4999/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "1234qwer5T", "login_type": "local"}'

# 取得任務列表
curl -X GET http://localhost:4999/api/tasks/list \
  -H "Authorization: Bearer {your_token}"

# 取得儀表板統計
curl -X GET http://localhost:4999/api/inspection/statistics \
  -H "Authorization: Bearer {your_token}"
```

### 10. 注意事項

- SQLite 資料庫檔案位於 `data/fem_dev.db`
- 重新啟動應用程式時,資料不會遺失
- 如需重置資料庫,可使用 `python scripts/reset_db.py`
- `data/mock_data.json` 僅用於單元測試,API 不使用此檔案

### 11. 開發流程建議

1. **本地開發**: 使用 SQLite 資料庫 (執行 `init_db.py` 初始化)
2. **整合測試**: 連接測試區 PostgreSQL
3. **正式部署**: 連接正式區 PostgreSQL + Redis + GCP

---

## 常見問題

**Q: 預設密碼是什麼?**
A: 管理員 `admin` 密碼是 `1234qwer5T`，巡檢人員密碼是 `password123`

**Q: 如何新增更多測試資料?**
A: 修改 `init_db.py` 後重新執行，或直接使用 Flask shell 操作資料庫

**Q: 如何重置資料庫?**
A: 請執行 `python scripts/reset_db.py`，它會自動刪除舊資料庫並重新初始化。
