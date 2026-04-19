---
type: change_log
audience: developers, maintainers
date: 2026-04-19
---

# UI 優化與品牌名稱清理 — 變更日誌

## 摘要

本次提交（`a9c0c36`，分支 `20260419_UI優化與品牌名稱清理`）包含三項獨立改動：
1. AIMS 工單執行進度頁欄位名稱調整
2. 儀表板折線圖曲線改為直線
3. 全站 FEM 品牌字樣移除

---

## 1. AIMS 工單執行進度查詢頁面欄位名稱調整

**受影響檔案：** `app/templates/inspection/Mortor_aims_progress.html`

| 位置 | 原名稱 | 新名稱 | 說明 |
|------|--------|--------|------|
| 主表格表頭（L108） | `異常` | `狀態` | 顯示正常/異常 badge 的欄位 |
| 主表格表頭（L116） | `狀態` | `執行狀態` | 工單執行狀態（未派工/執行中/已完成） |
| 量測資訊 Modal 表頭（L164） | `異常` | `狀態` | Modal 內檢查項目狀態欄 |

### 設計理由
「異常」語意上容易與「異常原因」欄混淆，且精確語意為「有無異常」（正常/異常），故統一改為「狀態」。原「狀態」欄為工單執行流程狀態，改為「執行狀態」以明確區隔兩者。

---

## 2. 儀表板首頁異常趨勢圖：曲線 → 直線折線圖

**受影響檔案：** `app/templates/dashboard/Mortor_index.html`

```diff
- tension: 0.4   // 貝茲曲線（平滑）
+ tension: 0     // 直線折線圖（polygon）
```

**影響範圍：** 「異常」與「停機」兩條折線均套用，無功能影響。

---

## 3. 全站 FEM 品牌名稱清理

**背景：** `FEM` 為舊專案代號（Front-End Monitoring），已不適用於現行系統命名。

### 替換規則

| 原字串 | 替換後 |
|--------|--------|
| `FEM 設備保養管理系統` | `設備保養管理系統` |
| `FEM 管理系統` | `管理系統` |
| `FEM 設備保養系統` | `設備保養系統` |
| `window.FEM` (JS 命名空間) | `window.App` |

### 受影響檔案清單（共 20 個）

#### Layout / 基礎模板
- `app/templates/layout/Mortor_base.html` — `<title>` 預設值、Sidebar 品牌名、頁尾版權

#### 認證頁
- `app/templates/auth/Mortor_login.html` — 獨立 `<title>` + 登入頁顯示名稱

#### 錯誤頁（獨立 HTML，不繼承 base）
- `app/templates/errors/Mortor_404.html`
- `app/templates/errors/Mortor_500.html`

#### 各功能頁面（`{% block title %}` 繼承自 base）
- `app/templates/dashboard/Mortor_index.html`
- `app/templates/inspection/Mortor_abnormal_tracking.html`
- `app/templates/inspection/Mortor_aims_progress.html`
- `app/templates/inspection/Mortor_calendar.html`
- `app/templates/inspection/Mortor_comparison.html`
- `app/templates/inspection/Mortor_progress.html`
- `app/templates/inspection/Mortor_public_report.html`（含獨立頁尾版權）
- `app/templates/inspection/Mortor_records.html`
- `app/templates/inspection/Mortor_trend.html`
- `app/templates/organization/Mortor_tree.html`
- `app/templates/system/Mortor_logs.html`
- `app/templates/system/Mortor_roles.html`
- `app/templates/system/Mortor_users.html`
- `app/templates/task/Mortor_create.html`
- `app/templates/task/Mortor_detail.html`
- `app/templates/task/Mortor_edit.html`
- `app/templates/task/Mortor_list.html`

#### 靜態資源
- `app/static/js/custom.js` — 頂部說明註解 + `window.FEM` → `window.App`
- `app/static/css/custom.css` — 頂部說明註解

> **注意：** `window.FEM` → `window.App` 不影響任何功能。
> 經搜尋確認，整個 templates 及 static 目錄無任何頁面透過 `FEM.xxx()` 方式呼叫此命名空間，所有頁面均直接使用全域函式（如 `showLoading()`），故此命名空間為冗餘輸出，可安全重命名。

---

## 4. docs 目錄結構重組

本次提交同步執行文件歸檔重組，依 MECE 原則將 `docs/` 根目錄散落的文件移至對應子目錄：

| 原路徑 | 新路徑 |
|--------|--------|
| `docs/API_DOCUMENTATION_GUIDE.md` | `docs/api_and_data/API_DOCUMENTATION_GUIDE.md` |
| `docs/system-spec.md` | `docs/api_and_data/SYSTEM_SPEC.md` |
| `docs/DB_RELATION.md` | `docs/architecture/DB_RELATION.md` |
| `docs/DEVELOPMENT.md` | `docs/architecture/DEVELOPMENT.md` |
| `docs/FLASK_DECOUPLING_GUIDE.md` | `docs/architecture/FLASK_DECOUPLING_GUIDE.md` |
| `docs/MVC_ARCHITECTURE.md` | `docs/architecture/MVC_ARCHITECTURE.md` |
| `docs/QUICKSTART.md` | `docs/architecture/QUICKSTART.md` |
| `docs/WEB_UI_GUIDE.md` | `docs/architecture/WEB_UI_GUIDE.md` |
| `docs/SYSTEM_MANAGEMENT_GUIDE.md` | `docs/features/SYSTEM_MANAGEMENT_GUIDE.md` |
| `docs/system-requirement.md` | `docs/features/SYSTEM_REQUIREMENT.md` |
| `docs/DOCUMENTATION_UPDATES_v1.2.0.md` | `docs/logs_and_analysis/20251124_documentation_updates_v1.2.0.md` |
| `docs/INIT_DB_CHANGES.md` | `docs/logs_and_analysis/20260211_init_db_changes.md` |
| `docs/ARCHITECTURE_REFACTORING_v1.3.md` | `docs/logs_and_analysis/20260409_architecture_refactoring_v1.3.md` |

新增 `docs/README.md` 作為文件庫導覽總綱。

---

## Git 發布資訊

| 項目 | 內容 |
|------|------|
| 分支 | `20260419_UI優化與品牌名稱清理` |
| Commit Hash | `a9c0c36` |
| Push 目標 1 | `origin` → [Jump-Bow/Mortor_system](https://github.com/Jump-Bow/Mortor_system) |
| Push 目標 2 | `upstream` → [CHIMEI-CORP/ai-motor-server](https://github.com/CHIMEI-CORP/ai-motor-server) |
| Push 時間 | 2026-04-19 02:11 (UTC+8) |
