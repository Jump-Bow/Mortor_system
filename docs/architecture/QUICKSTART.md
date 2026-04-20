# 設備保養管理系統 - 快速啟動指南

## 🚀 5 分鐘快速啟動

### 步驟 1: 安裝 Python 依賴 (1 分鐘)

```bash
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 安裝依賴
pip install -r requirements.txt
```

### 步驟 2: 配置環境變數 (1 分鐘)

```bash
# 複製環境變數範例檔案
cp .env.example .env

# 編輯 .env 檔案（可先使用預設值測試）
# 注意：實際部署時需要修改資料庫連線資訊
```

**最小配置（用於快速測試）：**
```env
FLASK_ENV=development
FLASK_APP=run.py
SECRET_KEY=dev-secret-key-for-testing
JWT_SECRET_KEY=jwt-secret-key-for-testing
```

### 步驟 3: 初始化資料庫 (1 分鐘)

```bash
# 執行初始化腳本（會建立 SQLite 測試資料庫）
python init_db.py
```

**輸出示例：**
```
Creating database tables...
✓ Database tables created successfully

Creating roles...
  ✓ Created role: 管理者
  ✓ Created role: 巡檢人員
  ✓ Created role: 查詢人員

Creating default admin user...
  ✓ Admin user created (username: admin, password: 1234qwer5T)

...

============================================================
Database initialization completed successfully!
============================================================
```

### 步驟 4: 啟動應用 (30 秒)

```bash
# 啟動 Flask 開發伺服器
python run.py
```

**輸出示例：**
```
 * Serving Flask app 'run.py'
 * Debug mode: on
 * Running on http://127.0.0.1:5000
```

### 步驟 5: 測試 API (1 分鐘)

**方法 1: 使用提供的測試腳本**

```bash
# 開啟新的終端視窗
python examples/api_usage.py
```

**方法 2: 使用 curl 手動測試**

```bash
# 測試登入
curl -X POST http://localhost:5000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"1234qwer5T","login_type":"local"}'
```

**方法 3: 使用 Postman 或其他 API 工具**

1. 匯入 Postman Collection（可從 README 取得範例）
2. 設定 BASE_URL: `http://localhost:5000/api/v1`
3. 開始測試
 
## 📋 預設帳號

### 管理員帳號
- **使用者名稱**: `admin`
- **密碼**: `1234qwer5T`
- **角色**: 管理者

### 測試帳號
- **使用者名稱**: `inspector1` / `inspector2`
- **密碼**: `password123`
- **角色**: 巡檢人員

## 🧪 執行測試

```bash
# 執行所有測試
pytest

# 執行特定測試
pytest tests/test_auth.py

# 產生測試覆蓋率報告
pytest --cov=app --cov-report=html
```

## 🐳 使用 Docker 快速啟動

```bash
# 建立 Docker 映像
docker build -t fem-admin:latest .

# 執行容器（使用 SQLite）
docker run -d \
  -p 5000:5000 \
  -e FLASK_ENV=development \
  --name fem-admin \
  fem-admin:latest

# 或使用 Docker Compose
docker-compose up -d
```

## 🔧 常見問題

### Q1: 找不到 PostgreSQL Driver？

**問題**: `psycopg2.OperationalError`

**解決方案**:
```bash
# Windows/Mac/Linux:
# 專案使用 psycopg2-binary，通常不需要額外安裝系統驅動程式。
# 若有需要，請安裝 PostgreSQL Client Tools (libpq)

```

### Q2: 資料庫連線失敗？

**問題**: 無法連線到 PostgreSQL 資料庫

**解決方案**:
1. 檢查 `.env` 檔案中的資料庫連線資訊
2. 確認資料庫伺服器允許外部連線
3. 檢查防火牆設定（預設埠 5432）
4. 測試時可先使用 SQLite（不需要額外配置）

### Q3: 模組匯入錯誤？

**問題**: `ModuleNotFoundError: No module named 'app'`

**解決方案**:
```bash
# 確保在專案根目錄執行
cd /path/to/fem-admin

# 確認虛擬環境已啟動
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows

# 重新安裝依賴
pip install -r requirements.txt
```

### Q4: Token 過期錯誤？

**問題**: API 返回 401 Unauthorized

**解決方案**:
1. 重新登入取得新的 token
2. 使用 refresh token 重新整理 access token
3. 檢查系統時間是否正確

## 📚 進階配置

### 使用 PostgreSQL 資料庫

編輯 `.env` 檔案：

```env
FLASK_ENV=development

# 資料庫配置
# 資料庫配置
DEV_DB_SERVER=localhost
DEV_DB_PORT=5432
DEV_DB_NAME=fem_dev
DEV_DB_USER=fem_admin
DEV_DB_PASSWORD=your-password

```

### 啟用 Azure AD 登入

編輯 `.env` 檔案：

```env
# Azure AD 配置
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id
```

### 配置 AIMS 整合

編輯 `.env` 檔案：

```env
# AIMS API 配置
AIMS_API_URL=https://your-aims-api.com/api
AIMS_API_KEY=your-aims-api-key
```

## 🎯 下一步

1. ✅ 完成快速啟動
2. 📖 閱讀 [README.md](README.md) 了解詳細功能
3. 🔍 查看 [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md) 了解實作細節
4. 📝 參考 [system-spec.md](system-spec.md) 查看 API 規格
5. 🧪 執行測試確認系統正常
6. 🚀 開始開發或部署

## 💡 提示

- 開發時建議使用 SQLite 資料庫進行快速測試
- 使用 `pytest -v` 查看詳細測試輸出
- 查看 `logs/fem.log` 檢查系統日誌
- 使用 Postman 或類似工具測試 API
- 參考 `examples/api_usage.py` 了解 API 使用方式

## 📞 需要協助？

- 📖 查看 [README.md](README.md)
- 📋 查看 [IMPLEMENTATION_SUMMARY.md](IMPLEMENTATION_SUMMARY.md)
- 🐛 回報問題或建議

---

**祝您使用愉快！** 🎉
