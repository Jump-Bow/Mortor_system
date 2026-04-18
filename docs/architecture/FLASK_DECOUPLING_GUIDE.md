# Flask 前後端分離實施指南 (FLASK_DECOUPLING_GUIDE)
## 解決 Flask Monolithic「神仙全包」架構問題

---

## 一、問題的本質

目前 `chimei-fem-admin` 在**同一個 Flask 應用程式**中同時負責兩件性質截然不同的工作：

```
┌─────────────────────────────────────────────────────────────┐
│                 chimei-fem-admin Flask App                  │
│                                                             │
│  ① API 層（高併發、要求穩定）                                  │
│    ├── /api/v1/tasks/download     ← APP 每次同步都打這裡       │
│    ├── /api/v1/results/upload     ← APP 巡檢完上傳打這裡       │
│    └── /api/v1/facilities/tree    ← 組織樹查詢                │
│                                                             │
│  ② 網頁渲染層（IO 密集、頻繁迭代）                              │
│    ├── /inspection/progress       ← Jinja2 渲染 HTML         │
│    ├── /inspection/abnormal       ← 同上                     │
│    └── /inspection/aims-progress  ← 同上                     │
└─────────────────────────────────────────────────────────────┘
```

### 兩大核心衝突

**① 搶奪資源（Python GIL 問題）**：
Python 引擎有「全域直譯器鎖（GIL）」，同一時間只有一個執行緒真正運算。
當主管瀏覽器發出複雜的統計頁面請求時，Flask 忙著組裝 HTML，
外面工廠的 APP 上傳量測結果的 API 請求只能排隊等候（高延遲、甚至 Timeout）。

**② 修網頁殃及 API（部署耦合）**：
只要修改一個網頁的 CSS 或 JS，就必須重新建置整包 Docker 映像並重新部署 Cloud Run 服務。
這代表負責全廠通訊心跳的 API 伺服器必須短暫下線重啟
（即使 Cloud Run 支援 Traffic Splitting，新版本健康檢查期間仍有風險窗口）。

---

## 二、在 GCP Cloud Run 上的影響程度

| 問題 | 在 GCP Cloud Run 上的緩解程度 |
|---|---|
| 修網頁要重啟 API | ✅ **大幅緩解**：Traffic Splitting 確保舊版本在新版本就緒前繼續服務 |
| 主管看網頁拖慢 APP API | ⚠️ **部分緩解**：多個 Container Instance 各有獨立 GIL，橫向擴展可分攤 |
| 前後端發版需協調 | ❌ **無法緩解**：只要是同一個 Image，就必須一起改、一起部署 |
| 部署包過大（含 HTML/CSS/JS）| ❌ **無法緩解**：每次 deploy 仍需搬運靜態檔案 |

**結論**：目前架構在 GCP 上可以正常運作；但仍有隱性成本（部署耦合、資源競爭）。
這是一個「可以接受」但「不應長期維持」的技術債。

---

## 三、分離架構目標

```
┌──────────────────────┐      ┌──────────────────────────┐
│   靜態前端 (Browser)  │      │   Flask 純 API 後端       │
│                      │      │                          │
│  Cloud Storage /     │      │  Cloud Run               │
│  Nginx               │      │  /api/v1/...             │
│                      │      │                          │
│  HTML + CSS + JS     │─────▶│  只處理 JSON 資料          │
│  (自己 Ajax 要資料)   │      │  不再 render 任何 HTML     │
└──────────────────────┘      └──────────────────────────┘
```

---

## 四、分三階段漸進式改造（不影響現有功能）

### Phase 1：API-First 整理（無感知、低風險）

**目標**：確保所有業務邏輯都在 `/api/v1/` 路由中，網頁路由只做「資料轉交」。

**做法**：

1. 確認所有 `@blueprint.route('/xxx')` 的網頁路由，其內部邏輯是否已抽出為 API
2. 若網頁路由直接查詢 DB，將查詢邏輯搬入對應的 API 端點
3. 原網頁路由改為：
```python
# 舊：網頁路由直接查 DB 組裝 HTML
@inspection_bp.route('/progress')
def inspection_progress():
    tasks = TJob.query.all()           # ← 直接查 DB
    stats = compute_stats(tasks)       # ← 業務邏輯
    return render_template('...', stats=stats)

# 新：網頁路由只返回空白殼子，資料由 JS Ajax 向 API 取得
@inspection_bp.route('/progress')
def inspection_progress():
    return render_template('Mortor_progress_shell.html')
    # Mortor_progress_shell.html 只有空殼 + JS，透過 /api/v1/... 取資料
```

### Phase 2：前端靜態化（需 JS 開發能力）

**目標**：將所有 `templates/` 中的 `.html` 轉換為純靜態 HTML + JS（無 Jinja2 模板語法）。

**做法**：

1. 建立 `frontend/` 目錄（或獨立 Git Repo）
2. 將 `Mortor_progress.html`、`Mortor_abnormal_tracking.html` 等改寫，
   刪除所有 `{{ variable }}` Jinja2 語法，改為 JavaScript 動態渲染：
```javascript
// 舊 Jinja2 渲染（需 Python 執行）
// {{ stats.total_tasks }}

// 新 JavaScript 渲染（瀏覽器直接執行）
fetch('/api/v1/inspection/statistics')
  .then(r => r.json())
  .then(data => {
    document.getElementById('total-tasks').textContent = data.total_tasks;
  });
```

### Phase 3：部署分離（DevOps 層面）

**目標**：靜態前端與 Flask API 完全獨立部署，互不影響。

**GCP 架構方案：**

```
使用者瀏覽器
     │
     ▼
Cloud Load Balancer
     │
     ├──── /api/v1/*  ──────▶  Cloud Run（Flask 純 API）
     │                          │
     │                          └── PostgreSQL (Cloud SQL)
     │
     └──── /* (其餘)  ──────▶  Cloud Storage（靜態網站 Hosting）
                               HTML + CSS + JS
```

**設定方法（Cloud Storage Static Site）：**
```bash
# 建立靜態網站 Bucket
gsutil mb -p YOUR_PROJECT gs://fem-admin-ui

# 開啟靜態網站 Hosting
gsutil web set -m index.html -e 404.html gs://fem-admin-ui

# 同步靜態檔案（只上傳 HTML/JS/CSS，無需重啟 Flask）
gsutil -m rsync -r frontend/dist gs://fem-admin-ui
```

**好處**：
- 改網頁 CSS：只需執行 `gsutil rsync`，不觸碰 Flask API，**秒級生效**
- 改 API 邏輯：只重新部署 Cloud Run，前端不受影響
- 兩個服務可以**各自獨立擴縮**（前端靜態無需 CPU，API 可以精準控制 Instance 數量）

---

## 五、過渡期的折衷方案（不需完整分離）

若短期內無法進行完整分離，以下是降低風險的折衷措施：

### 方案 A：使用 Gunicorn 多 Worker 降低 GIL 影響
```dockerfile
# Dockerfile 啟動命令改為多核 gunicorn
CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8080", "run:app"]
```
每個 Worker 是獨立的 Python Process，各有自己的 GIL，
讓 4 個請求可真正並行處理。

### 方案 B：靜態檔案交由 Nginx 服務
```nginx
server {
    # 靜態資源直接由 Nginx 返回（不過 Python）
    location /static/ {
        alias /app/static/;
        expires 30d;
    }
    # API 才轉給 Flask
    location /api/ {
        proxy_pass http://flask:8080;
    }
}
```

---

## 六、建議執行順序

| 優先順序 | 項目 | 工作量 | 效果 |
|---|---|---|---|
| 🔴 現在就做 | Gunicorn 多 Worker | 1 行配置 | 立即緩解 GIL 競爭 |
| 🟡 短期（1個月） | Phase 1 API-First | 中 | 邏輯乾淨，為分離做準備 |
| 🟢 中期（3個月） | Phase 2+3 完整分離 | 大 | 完全根治，部署獨立 |
