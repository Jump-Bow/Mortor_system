# FEM 設備保養管理系統 (Facility Equipment Maintenance System)

![Python Version](https://img.shields.io/badge/python-3.10.13-blue.svg)
![Flask Version](https://img.shields.io/badge/flask-3.0.0-green.svg)
![License](https://img.shields.io/badge/license-MIT-orange.svg)
![PostgreSQL](https://img.shields.io/badge/database-postgresql-blue.svg)

**FEM 設備保養管理系統**是一個完整的設備巡檢、保養與維修管理解決方案，包含網頁管理後台與行動應用程式，支援離線作業。

## 📋 目錄

- [系統特色](#系統特色)
- [技術架構](#技術架構)
- [快速開始](#快速開始)
- [API 文件](#api-文件)
- [資料庫結構](#資料庫結構)
- [開發指南](#開發指南)
- [測試](#測試)
- [部署](#部署)
- [授權](#授權)

## 🌟 系統特色

### 核心功能

- **🔐 使用者認證**
  - 本地帳號密碼登入
  - Azure Entra ID (Azure AD) 整合
  - JWT Token 認證機制
  - 角色權限管理

- **📊 儀表板與統計**
  - 即時異常追蹤統計
  - 巡檢作業進度監控
  - 數據視覺化展示

- **🔍 巡檢管理**
  - 組織樹狀結構管理
  - 巡檢路線/表單配置
  - 管制點與檢查項目設定
  - 巡檢紀錄查詢與鑽取

- **📱 行動裝置支援**
  - 任務下載與離線執行
  - RFID 感應驗證
  - 數據採集與照片上傳
  - 自動同步機制

- **📈 報表與分析**
  - 異常追蹤管理
  - 設備狀態監控
  - 趨勢圖分析 (開發中)

## 🛠 技術架構

### 後端技術堆疊

```
├── Flask 3.0.0                 # Web 框架
├── SQLAlchemy 2.0.23           # ORM
├── Flask-Migrate 4.0.5         # 資料庫遷移
├── Flask-Login 0.6.3           # 使用者認證
├── Flask-Caching 2.1.0         # 快取
├── PyJWT 2.8.0                 # JWT Token
├── psycopg2-binary 2.9.9       # PostgreSQL 驅動
├── msal 1.26.0                 # Azure AD
├── Pillow 10.1.0               # 圖片處理
└── pytest 7.4.3                # 測試框架
```

### 資料庫

- **PostgreSQL 16**
- 測試環境: `postgres` (Docker Service)
- 正式環境: GCP Cloud SQL / 自建 PostgreSQL

### 部署環境

- **GCP (Google Cloud Platform)**
- Docker 容器化 (Docker Compose)
- SSL/TLS 加密傳輸

## 🚀 快速開始

### 前置需求

- Python 3.10.13 或更高版本
- PostgreSQL 16 (或使用 Docker)
- libpq-dev (Linux/macOS) 或 PostgreSQL Client Tools
- pip (Python 套件管理器)

### 安裝步驟

1. **克隆專案**

```bash
git clone <repository-url>
cd fem-admin
```

2. **建立虛擬環境**

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

3. **安裝依賴套件**

```bash
pip install -r requirements.txt
```

4. **配置環境變數**

複製 `.env.example` 為 `.env` 並填入配置：

```bash
cp .env.example .env
```

編輯 `.env` 檔案 (`DEV_DB_TYPE` 可選 `postgresql` 或 `sqlite`)：

```env
# Flask Configuration
FLASK_ENV=development
FLASK_APP=run.py
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Development Database (Local Docker PostgreSQL)
DEV_DB_TYPE=postgresql
DEV_DB_SERVER=localhost
DEV_DB_PORT=5433
DEV_DB_NAME=fem_dev
DEV_DB_USER=fem_admin
DEV_DB_PASSWORD=devpassword123

# Azure AD (Optional)
AZURE_CLIENT_ID=your-azure-client-id
AZURE_CLIENT_SECRET=your-azure-client-secret
AZURE_TENANT_ID=your-azure-tenant-id
```

5. **初始化資料庫**

```bash
# 初始化資料表與預設資料
python init_db.py
```

6. **啟動開發伺服器**

```bash
python run.py
```

伺服器將在 `http://localhost:4999` 啟動。

### 預設帳號

- **使用者名稱**: `admin`
- **密碼**: `1234qwer5T`

## 📚 API 文件

### 🔍 Swagger API 文件 (推薦)

本系統已整合 **Swagger UI**，提供完整的互動式 API 文件：

- **📖 Swagger UI**: `http://localhost:4999/api/docs`
- **📄 OpenAPI 規格**: `http://localhost:4999/api/swagger.json`
- **📚 使用指南**: [docs/SWAGGER_GUIDE.md](docs/SWAGGER_GUIDE.md)

**詳細文件**:
- [docs/system-spec.md](docs/system-spec.md) - 系統規格與資料庫 Schema

## 🗄 資料庫結構

### 核心資料表 (PostgreSQL)

1. **hr_account** (HrAccount) - 使用者帳號
2. **roles** (Role) - 角色 (保留功能)
3. **hr_organization** (HrOrganization) - 組織架構
4. **t_organization** (TOrganization) - 設施/廠區
5. **t_equipment** (TEquipment) - 設備清單
6. **equit_check_item** (EquitCheckItem) - 檢查項目
7. **t_job** (TJob) - 巡檢任務
8. **inspection_result** (InspectionResult) - 巡檢結果
9. **abnormal_cases** (AbnormalCases) - 異常追蹤
10. **user_action_log** (UserActionLog) - 使用者操作紀錄
11. **system_log** (SystemLog) - 系統日誌

詳細結構請參考 `docs/system-spec.md`。

## 💻 開發指南

### 專案結構

```
fem-admin/
├── app/                        # 應用程式主目錄
│   ├── __init__.py            # Application Factory
│   ├── models/                # 資料模型
│   │   ├── Mortor_user.py     # HrAccount, Role
│   │   ├── Mortor_organization.py # HrOrganization, TOrganization
│   │   ├── Mortor_inspection.py   # TJob, InspectionResult
│   │   ├── Mortor_abnormal.py     # AbnormalCases
│   │   └── ...
│   ├── api/                   # API Blueprints
│   │   ├── Mortor_auth.py
│   │   ├── Mortor_tasks.py
│   │   └── ...
│   ├── auth/                  # 認證模組
│   │   └── jwt_handler.py
│   └── ...
├── tests/                     # 測試程式
├── scripts/                   # 實用工具腳本 (如資料庫重置)
├── docker-compose.yml         # 生產環境配置 (Production: Gunicorn, Redis, Nginx)
├── docker-compose.dev.yml     # 開發環境配置 (Development: Flask run, Local PostgreSQL)
├── init_db.py                 # 資料庫初始化腳本
├── create_tables.sql          # PostgreSQL DDL 腳本
├── config.py                  # 配置管理
├── run.py                     # 應用程式入口
└── requirements.txt           # Python 依賴
```

## 🧪 測試

### 執行所有測試

```bash
pytest
```

## 🚢 部署

### Docker Compose 部署 (推薦)

1. **開發環境部署**

```bash
docker-compose -f docker-compose.dev.yml up --build -d
# 預設埠號: App (4999), Postgres (5433)
```

2. **生產環境部署**

```bash
docker-compose up --build -d
# 預設埠號: App (5000), Postgres (5432), Redis (6379)
```

### 資料庫遷移

如果是全新部署，容器啟動後請執行初始化：

```bash
docker exec -it fem-admin python init_db.py
```

## 📄 授權

本專案採用 MIT 授權。

