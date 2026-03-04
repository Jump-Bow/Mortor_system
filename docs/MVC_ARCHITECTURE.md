# FEM 設備保養管理系統 - MVC 架構說明

## 目錄
- [MVC 架構概述](#mvc-架構概述)
- [專案 MVC 對應結構](#專案-mvc-對應結構)
- [目錄結構對照](#目錄結構對照)
- [各層詳細說明](#各層詳細說明)
- [資料流程圖](#資料流程圖)
- [程式碼範例](#程式碼範例)
- [開發指南](#開發指南)

---

## MVC 架構概述

MVC（Model-View-Controller）是一種軟體設計模式，將應用程式分為三個核心元件：

| 元件 | 說明 | 職責 |
|------|------|------|
| **Model（模型）** | 資料層 | 負責資料的定義、存取、商業邏輯 |
| **View（視圖）** | 呈現層 | 負責使用者介面的呈現 |
| **Controller（控制器）** | 控制層 | 處理使用者請求、協調 Model 與 View |

### MVC 架構優點
- **關注點分離**：各元件職責明確，易於維護
- **程式碼重用**：Model 可被多個 Controller 共用
- **平行開發**：前後端可同時開發
- **易於測試**：各元件可獨立進行單元測試

---

## 專案 MVC 對應結構

本專案採用 **Flask + AdminLTE** 技術棧，結合了傳統 MVC 與 RESTful API 架構：

```
┌─────────────────────────────────────────────────────────────────┐
│                         使用者請求                                │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Controller（控制器層）                         │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │   Web Routes         │    │   API Blueprints             │  │
│  │   app/web_routes.py  │    │   app/api/*.py               │  │
│  │   (網頁路由)          │    │   (RESTful API)              │  │
│  └──────────────────────┘    └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Model（模型層）                              │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │   SQLAlchemy ORM Models                                   │  │
│  │   app/models/*.py                                         │  │
│  │   - user.py (使用者、角色)                                 │  │
│  │   - organization.py (組織、設施)                           │  │
│  │   - equipment.py (設備、檢查項目)                          │  │
│  │   - inspection.py (巡檢任務、結果)                         │  │
│  │   - abnormal.py (異常追蹤)                                 │  │
│  │   - system_log.py (系統日誌)                               │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                      View（視圖層）                               │
│  ┌──────────────────────┐    ┌──────────────────────────────┐  │
│  │   Jinja2 Templates   │    │   JSON Response              │  │
│  │   app/templates/     │    │   (API 回應)                  │  │
│  │   (HTML 頁面)         │    │                              │  │
│  └──────────────────────┘    └──────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │   Static Files: app/static/                               │  │
│  │   - css/custom.css                                        │  │
│  │   - js/custom.js                                          │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 目錄結構對照

```
fem-admin/
├── app/                           # 應用程式主目錄
│   ├── __init__.py                # Application Factory (應用程式工廠)
│   ├── web_routes.py              # 🎮 Controller: 網頁路由控制器
│   │
│   ├── api/                       # 🎮 Controller: API 控制器層
│   │   ├── __init__.py            #    API Blueprint 匯出
│   │   ├── auth.py                #    認證 API
│   │   ├── tasks.py               #    任務管理 API
│   │   ├── results.py             #    巡檢結果 API
│   │   ├── inspection.py          #    巡檢相關 API
│   │   ├── organizations.py       #    組織設施 API
│   │   ├── facilities.py          #    設施管理 API
│   │   ├── users.py               #    使用者管理 API
│   │   └── system_logs.py         #    系統日誌 API
│   │
│   ├── models/                    # 📊 Model: 資料模型層
│   │   ├── __init__.py            #    模型匯出
│   │   ├── user.py                #    User, Role 模型
│   │   ├── organization.py        #    Organization, Facility 模型
│   │   ├── equipment.py           #    Equipment, EquipmentCheckItem 模型
│   │   ├── inspection.py          #    InspectionTask, InspectionResult 模型
│   │   ├── abnormal.py            #    AbnormalTracking 模型
│   │   └── system_log.py          #    SystemLog, UserLog 模型
│   │
│   ├── templates/                 # 🖼️ View: HTML 模板層
│   │   ├── layout/
│   │   │   └── base.html          #    基礎版面 (AdminLTE)
│   │   ├── auth/
│   │   │   └── login.html         #    登入頁面
│   │   ├── dashboard/
│   │   │   └── index.html         #    儀表板
│   │   ├── task/
│   │   │   ├── list.html          #    任務列表
│   │   │   ├── create.html        #    建立任務
│   │   │   ├── detail.html        #    任務詳情
│   │   │   └── edit.html          #    編輯任務
│   │   ├── inspection/
│   │   │   ├── records.html       #    巡檢紀錄
│   │   │   └── abnormal_tracking.html  # 異常追蹤
│   │   ├── facility/
│   │   │   ├── list.html          #    設施列表
│   │   │   ├── detail.html        #    設施詳情
│   │   │   └── tree.html          #    設施樹狀圖
│   │   ├── organization/
│   │   │   └── tree.html          #    組織樹狀圖
│   │   ├── system/
│   │   │   ├── users.html         #    使用者管理
│   │   │   └── logs.html          #    系統日誌
│   │   └── errors/
│   │       ├── 404.html           #    404 錯誤頁
│   │       └── 500.html           #    500 錯誤頁
│   │
│   ├── static/                    # 🖼️ View: 靜態資源
│   │   ├── css/
│   │   │   └── custom.css         #    自定義樣式
│   │   ├── js/
│   │   │   └── custom.js          #    自定義 JavaScript
│   │   └── images/                #    圖片資源
│   │
│   ├── auth/                      # 🔐 輔助模組：認證
│   │   ├── jwt_handler.py         #    JWT Token 處理
│   │   └── azure_ad_handler.py    #    Azure AD (MSAL) 認證處理
│   │
│   ├── utils/                     # 🔧 輔助模組：工具
│   │   ├── decorators.py          #    裝飾器 (驗證、日誌、限流)
│   │   ├── validators.py          #    資料驗證器
│   │   ├── file_helpers.py        #    檔案處理工具
│   │   └── mock_data_service.py   #    模擬資料服務
│   │
│   └── swagger/                   # 📖 API 文件
│       └── swagger.json           #    Swagger/OpenAPI 規格
│
├── config.py                      # ⚙️ 配置檔案
├── run.py                         # 🚀 應用程式進入點
├── requirements.txt               # 📦 相依套件
└── migrations/                    # 🗄️ 資料庫遷移
```

---

## 各層詳細說明

### 1. Model（模型層）- `app/models/`

模型層負責定義資料結構和商業邏輯，使用 **SQLAlchemy ORM**。

#### 主要模型類別

| 檔案 | 模型 | 說明 |
|------|------|------|
| `user.py` | `User`, `Role` | 使用者與角色管理 |
| `organization.py` | `Organization`, `Facility` | 組織與設施結構 |
| `equipment.py` | `Equipment`, `EquipmentCheckItem` | 設備與檢查項目 |
| `inspection.py` | `InspectionTask`, `InspectionResult` | 巡檢任務與結果 |
| `abnormal.py` | `AbnormalTracking` | 異常追蹤記錄 |
| `system_log.py` | `SystemLog`, `UserLog` | 系統與使用者日誌 |

#### Model 範例程式碼

```python
# app/models/user.py
class User(UserMixin, db.Model):
    """使用者模型"""
    __tablename__ = 'users'
    
    user_id = db.Column(db.String(50), primary_key=True)
    full_name = db.Column(db.String(50), nullable=False)
    org_id = db.Column(db.String(50), db.ForeignKey('organizations.org_id'))
    email = db.Column(db.String(255))
    password_hash = db.Column(db.String(255))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.role_id'))
    is_active = db.Column(db.Boolean, default=True)
    
    # 關聯
    inspection_tasks = db.relationship('InspectionTask', backref='assigned_user')
    
    # 商業邏輯方法
    def set_password(self, password: str) -> None:
        """設置密碼 (加密)"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password: str) -> bool:
        """驗證密碼"""
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        """轉換為字典（用於 API 回應）"""
        return {
            'user_id': self.user_id,
            'full_name': self.full_name,
            'role': self.role.role_name if self.role else None
        }
```

---

### 2. View（視圖層）- `app/templates/` & `app/static/`

視圖層負責呈現使用者介面，本專案使用：
- **Jinja2 模板引擎**：動態 HTML 生成
- **AdminLTE**：後台管理介面框架
- **靜態資源**：CSS、JavaScript、圖片

#### 模板繼承結構

```
base.html (基礎版面)
├── auth/login.html
├── dashboard/index.html
├── task/list.html
├── task/create.html
├── task/detail.html
├── inspection/records.html
└── ...
```

#### View 範例程式碼

```html
<!-- app/templates/layout/base.html -->
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <title>{% block title %}FEM 設備保養管理系統{% endblock %}</title>
    <!-- AdminLTE CSS -->
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/admin-lte@3.2/dist/css/adminlte.min.css">
    <!-- 自定義 CSS -->
    <link rel="stylesheet" href="{{ url_for('static', filename='css/custom.css') }}">
</head>
<body class="hold-transition sidebar-mini">
    <div class="wrapper">
        <!-- 導航欄、側邊欄 -->
        {% block content %}{% endblock %}
    </div>
    <!-- JavaScript -->
    <script src="{{ url_for('static', filename='js/custom.js') }}"></script>
</body>
</html>

<!-- app/templates/task/list.html -->
{% extends "layout/base.html" %}

{% block title %}任務列表 - FEM{% endblock %}

{% block content %}
<div class="card">
    <div class="card-header">
        <h3 class="card-title">任務列表</h3>
    </div>
    <div class="card-body">
        <table id="taskTable" class="table table-bordered table-striped">
            <!-- 表格內容由 JavaScript 動態載入 -->
        </table>
    </div>
</div>
{% endblock %}
```

---

### 3. Controller（控制器層）- `app/web_routes.py` & `app/api/`

控制器層處理使用者請求，協調 Model 與 View，本專案分為兩種控制器：

| 類型 | 路徑 | 說明 |
|------|------|------|
| **Web Controller** | `app/web_routes.py` | 處理網頁請求，回傳 HTML |
| **API Controller** | `app/api/*.py` | 處理 API 請求，回傳 JSON |

#### Web Controller 範例

```python
# app/web_routes.py
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user

web_bp = Blueprint('web', __name__)

@web_bp.route('/dashboard')
@login_required
def dashboard():
    """儀表板 - 回傳 HTML 頁面"""
    return render_template('dashboard/index.html')

@web_bp.route('/task/list')
@login_required
def task_list():
    """任務列表頁面"""
    return render_template('task/list.html')

@web_bp.route('/login', methods=['GET', 'POST'])
def login():
    """登入處理"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.get(username)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('web.dashboard'))
        
        flash('登入失敗', 'error')
    
    return render_template('auth/login.html')
```

#### API Controller 範例

```python
# app/api/tasks.py
from flask import Blueprint, request, jsonify
from app.models.inspection import InspectionTask
from app.auth.jwt_handler import token_required

tasks_bp = Blueprint('tasks', __name__)

@tasks_bp.route('/download', methods=['GET'])
@token_required
def download_tasks(**kwargs):
    """
    下載任務 API - 回傳 JSON
    
    GET /api/tasks/download?user_id=xxx&date=2025-01-01
    """
    current_user = kwargs.get('current_user')
    user_id = request.args.get('user_id', current_user.user_id)
    
    tasks = InspectionTask.query.filter_by(assigned_to=user_id).all()
    
    return jsonify({
        'status': 'success',
        'data': {
            'tasks': [task.to_dict() for task in tasks]
        }
    })
```

---

## 資料流程圖

### 網頁請求流程

```
[瀏覽器] 
    │ GET /task/list
    ▼
[Flask Router] ──▶ web_routes.py
    │                  │
    │                  ▼ @login_required 驗證
    │                  │
    │                  ▼ task_list()
    │                  │
    │                  ▼ render_template('task/list.html')
    │
    ▼
[Jinja2 Engine] ──▶ base.html + task/list.html
    │
    ▼
[HTML Response] ──▶ 瀏覽器顯示
```

### API 請求流程

```
[前端 JavaScript / 行動 App]
    │ GET /api/tasks/download
    │ Header: Authorization: Bearer <token>
    ▼
[Flask Router] ──▶ api/tasks.py
    │                  │
    │                  ▼ @token_required 驗證 JWT
    │                  │
    │                  ▼ download_tasks()
    │                  │
    │                  ▼ InspectionTask.query.filter_by()
    │                  │
    │                  ▼ task.to_dict()
    │
    ▼
[JSON Response]
{
    "status": "success",
    "data": {
        "tasks": [...]
    }
}
```

### 完整資料流

```
┌──────────────┐     HTTP Request      ┌──────────────────┐
│   Browser    │ ────────────────────▶ │   Controller     │
│   / App      │                       │  (web_routes.py  │
└──────────────┘                       │   or api/*.py)   │
       ▲                               └────────┬─────────┘
       │                                        │
       │ HTML/JSON                              │ Query/Update
       │                                        ▼
┌──────┴───────┐                       ┌──────────────────┐
│    View      │                       │     Model        │
│ (templates/) │                       │   (models/*.py)  │
└──────────────┘                       └────────┬─────────┘
                                                │
                                                │ SQL
                                                ▼
                                       ┌──────────────────┐
                                       │    (PostgreSQL)  │
                                       └──────────────────┘
```

---

## 程式碼範例

### 完整功能實作範例：任務管理

#### 1. Model - 定義資料結構

```python
# app/models/inspection.py
class InspectionTask(db.Model):
    __tablename__ = 'inspection_tasks'
    
    task_id = db.Column(db.String(50), primary_key=True)
    equipment_id = db.Column(db.String(50), db.ForeignKey('equipment.equipment_id'))
    inspection_date = db.Column(db.Date, nullable=False)
    assigned_to = db.Column(db.String(50), db.ForeignKey('users.user_id'))
    status = db.Column(db.String(20), default='Pending')
    
    def to_dict(self):
        return {
            'task_id': self.task_id,
            'equipment_id': self.equipment_id,
            'inspection_date': self.inspection_date.isoformat(),
            'status': self.status
        }
```

#### 2. Controller - 處理請求

```python
# app/api/tasks.py
@tasks_bp.route('/list', methods=['GET'])
@token_required
def list_tasks(**kwargs):
    """取得任務列表"""
    status = request.args.get('status')
    
    query = InspectionTask.query
    if status:
        query = query.filter_by(status=status)
    
    tasks = query.all()
    
    return jsonify({
        'status': 'success',
        'data': [task.to_dict() for task in tasks]
    })
```

#### 3. View - 顯示介面

```html
<!-- app/templates/task/list.html -->
{% extends "layout/base.html" %}

{% block content %}
<div class="card">
    <div class="card-body">
        <table id="taskTable" class="table">
            <thead>
                <tr>
                    <th>任務編號</th>
                    <th>設備</th>
                    <th>日期</th>
                    <th>狀態</th>
                </tr>
            </thead>
            <tbody id="taskList">
                <!-- JavaScript 動態載入 -->
            </tbody>
        </table>
    </div>
</div>
{% endblock %}

{% block extra_js %}
<script>
// 載入任務資料
async function loadTasks() {
    const response = await fetch('/api/tasks/list', {
        headers: {
            'Authorization': `Bearer ${getApiToken()}`
        }
    });
    const result = await response.json();
    
    if (result.status === 'success') {
        renderTable(result.data);
    }
}

document.addEventListener('DOMContentLoaded', loadTasks);
</script>
{% endblock %}
```

---

## 開發指南

### 新增功能的步驟

1. **定義 Model**（如需要新資料表）
   - 在 `app/models/` 建立或修改模型
   - 執行資料庫遷移

2. **建立 Controller**
   - API 功能：在 `app/api/` 新增或修改
   - 網頁路由：在 `app/web_routes.py` 新增

3. **建立 View**
   - 新增 HTML 模板於 `app/templates/`
   - 繼承 `layout/base.html`

4. **註冊 Blueprint**（如為新模組）
   - 在 `app/__init__.py` 的 `register_blueprints()` 註冊

### 命名規範

| 類型 | 規範 | 範例 |
|------|------|------|
| Model | 大駝峰式 | `InspectionTask`, `User` |
| Blueprint | 小寫底線 | `tasks_bp`, `auth_bp` |
| 路由函式 | 小寫底線 | `download_tasks()`, `task_list()` |
| Template | 小寫底線 | `task_list.html`, `abnormal_tracking.html` |
| URL | 小寫連字號 | `/api/tasks/download`, `/inspection/abnormal-tracking` |

### 重要檔案清單

| 檔案 | 用途 |
|------|------|
| `app/__init__.py` | 應用程式工廠、Blueprint 註冊 |
| `config.py` | 環境配置 (開發/測試/生產) |
| `run.py` | 應用程式進入點 |
| `app/auth/jwt_handler.py` | JWT Token 驗證 |
| `app/utils/decorators.py` | 常用裝飾器 |

---

## 相關文件

- [API 文件指南](API_DOCUMENTATION_GUIDE.md)
- [資料庫關聯圖](DB_RELATION.md)
- [系統需求規格](system-requirement.md)
- [系統規格說明](system-spec.md)
- [開發環境設定](DEVELOPMENT.md)
- [Web UI 指南](WEB_UI_GUIDE.md)

---

*文件更新日期：2025-12-07*
