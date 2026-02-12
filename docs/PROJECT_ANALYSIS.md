# 專案概念解構分析 (Project Concept Deconstruction)

本文件基於 **第一性原理 (First Principles)**、**MECE (Mutually Exclusive, Collectively Exhaustive)**、**SWOT 分析** 與 **5W1H** 框架，對 `chimei-fem-admin` 專案進行深度解構與分析。

---

## 1. 執行摘要 (Executive Summary)

**FEM (Facility Equipment Maintenance System)** 是一個專為奇美實業設計的設備巡檢與保養管理系統。其核心價值在於將傳統紙本巡檢流程數位化，透過行動裝置與雲端後台的整合，實現數據即時同步、異常追蹤自動化與決策數據化。

目前的開發狀態為 **V1.4.0 (PostgreSQL Migration Completed)**，正處於由開發環境轉向生產部署的過渡期。

---

## 2. 5W1H 情境分析 (Context Analysis)

| 構面 | 內容 | 補充說明 |
| :--- | :--- | :--- |
| **Why (為什麼)** | 解決巡檢紙本作業效率低、異常追蹤不易、數據無法即時分析的痛點。 | 數位轉型、無紙化、預防性保養基礎。 |
| **What (做什麼)** | 建立一套包含 Web 管理後台與 Mobile APP 的數位巡檢系統。 | 核心功能：巡檢派工、行動執行、異常管理、報表分析。 |
| **Who (誰參與)** | **管理者 (Admin)**: 派工、審核、系統設定。<br>**巡檢員 (Inspector)**: 執行巡檢、回報異常。<br>**查詢者 (Viewer)**: 監控進度、查看報表。 | 涉及行政處與生產處等單位。 |
| **Where (在哪裡)** | **場域**: 廠區 (Plant)、廠房 (Building)、特定樓層 (Floor) 與機房。<br>**系統**: 部署於 GCP / 地端伺服器 (Docker)。 | 支援離線作業 (APP)。 |
| **When (何時做)** | **週期性**: 每日、每週、每月定期巡檢。<br>**即時性**: 異常發生時立即回報與追蹤。 | 數據同步發生在網路連線時。 |
| **How (如何做)** | **技術**: Flask (Backend) + PostgreSQL (DB) + Flutter (APP)。<br>**流程**: 排程派工 -> APP下載 -> 現場NFC/RFID到位 -> 抄表/拍照 -> 上傳同步 -> 異常追蹤。 | 採用 JWT 認證與 RESTful API。 |

---

## 3. 第一性原理與 MECE 解構 (First Principles & MECE)

### 3.1 第一性原理 (First Principles)
回歸系統最根本的物理與邏輯需求：
> **「準確記錄設備在特定時間點的狀態，並確保異常被處理。」**

基於此原理，系統設計的所有功能都應服務於此目標：
1.  **準確記錄**: 需要由本人 (Auth)、在現場 (RFID/GPS)、針對正確設備 (Equipment ID) 進行操作。 -> *推導出 Mobile APP + NFC 驗證需求*
2.  **特定時間點**: 需記錄 Timestamp 與時區。 -> *推導出資料庫 Timezone 處理需求*
3.  **狀態**: 需定義標準規格 (Spec) 與量測值 (Value)。 -> *推導出 Check Items 與 Validation 邏輯*
4.  **異常被處理**: 需有異常觸發 (Alert) 與追蹤 (Tracking) 機制。 -> *推導出 System Log 與 Abnormal Cases 模組*

### 3.2 MECE 架構拆解 (Architectural Breakdown)
將系統拆解為互不重疊且完全窮盡的模組：

*   **前端交互層 (Presentation Layer)**
    *   **Web Portal**: 管理者介面 (Dashboard, Task Management, User Management)。
    *   **Mobile APP**: 執行介面 (Task List, Inspection, Sync)。
*   **應用邏輯層 (Application Layer)**
    *   **身份識別 (Identity)**: Auth (JWT), User/Role Management.
    *   **核心業務 (Core Business)**:
        *   派工引擎 (Task Generation)
        *   巡檢執行 (Inspection Logic)
        *   異常處理 (Abnormal Handling)
    *   **數據服務 (Data Services)**: API Endpoints, Synchronization, Reporting.
*   **資料持久層 (Persistence Layer)**
    *   **關聯式資料庫 (RDBMS)**: PostgreSQL (Users, Orgs, Tasks, Results).
    *   **快取 (Cache)**: Redis (Session, Frequent Queries).
    *   **檔案儲存 (File Storage)**: Local/Cloud Storage (Photos).
*   **基礎設施層 (Infrastructure Layer)**
    *   **容器化 (Containerization)**: Docker, Docker Compose.
    *   **網路 (Networking)**: Nginx (Proxy), SSL/TLS.

---

## 4. SWOT 分析 (Strategic Analysis)

| | 正向 (Positive) | 負向 (Negative) |
| :--- | :--- | :--- |
| **內部 (Internal)** | **Strengths (優勢)**<br>1. **現代化架構**: 採用 Flask Blueprint 與 Docker，易於維護與擴展。<br>2. **開源技術**: 使用 PostgreSQL 取代昂貴的 MSSQL，降低成本。<br>3. **完整 API 文件**: 整合 Swagger，前後端協作順暢。<br>4. **資安考量**: 實作 JWT、Rate Limit 與密碼雜湊。 | **Weaknesses (劣勢)**<br>1. **功能缺口**: Azure AD 整合尚在開發中 (501 Not Implemented)。<br>2. **測試覆蓋**: 單元測試偏向 Happy Path，邊界條件測試較少。<br>3. **配置管理**: 部分設定 (如密碼) 在開發檔案中暴露 (雖已用 .env改善，需持續監控)。 |
| **外部 (External)** | **Opportunities (機會)**<br>1. **AI 預測性維護**: 累積的數據可用於訓練 ML 模型，預測設備故障。<br>2. **IoT 整合**: 未來可直接介接設備 PLC/Sensor，減少人工抄表。<br>3. **行動化升級**: 結合 AR 眼鏡進行巡檢指導。 | **Threats (威脅)**<br>1. **資安攻擊**: API 暴露於網路，需防範 DDoS 與 SQL Injection。<br>2. **資料隱私**: 巡檢照片可能包含敏感資訊，需加強存取控制。<br>3. **依賴風險**: 第三方套件 (Dependencies) 的漏洞更新維護。 |

---

## 5. 角色視角分析 (Role-Based Perspectives)

### 👨‍💻 AI 工程師視角
*   **數據品質**: `inspection_result` 表結構良好，包含數值 (`measuredvalue`) 與規格上下限 (`ulspec`, `llspec`)，有利於標記異常數據。
*   **建議**:
    1.  增加 `equipment_type` 欄位以利於跨設備型號訓練。
    2.  將照片數據 (`photopath`) 與異常標記連結，可用於訓練電腦視覺 (CV) 模型自動識別異常。

### 🛡️ 資安工程師視角
*   **現狀**: 已實作 JWT 且有基本的 Rate Limiting。資料庫連線字串已參數化。
*   **風險**: `config.py` 中存在預設的 `SECRET_KEY`。
*   **建議**:
    1.  生產環境強制輪換 JWT Secret。
    2.  強化 Log 審計 (UserActionLog)，確保所有敏感操作 (刪除、權限變更) 皆不可否認。
    3.  導入靜態程式碼分析 (SAST) 工具掃描潛在漏洞。

### 🏗️ 系統架構師視角
*   **現狀**: Flask Blueprint 切分合理 (Auth, API, Models)。Docker 化部署解決了環境一致性問題。
*   **建議**:
    1.  考慮引入 Celery 處理異步任務 (如報表生成、大量數據匯入)，避免阻塞 API。
    2.  隨著數據量增長，需規劃主從資料庫 (Read/Write Splitting) 或資料庫分區 (Partitioning)。

### 👤 一般使用者視角
*   **體驗**: 介面需直觀，操作步驟需最少化。
*   **痛點**: 網路不穩時的資料同步體驗 (Sync)。
*   **建議**: 強化 APP 的離線提示與同步進度條，減少使用者的焦慮感。

---

## 6. 結論與行動計畫

本專案架構穩健，已從傳統的 MSSQL 成功轉型為開源 PostgreSQL 架構。下一步的關鍵在於：
1.  **補強**: 完成 Azure AD 整合與完整單元測試。
2.  **優化**: 移除開發用的 Hardcoded 密碼，全面轉向 Secret Manager。
3.  **擴展**: 開始規劃數據分析模組，發揮數位化的真正價值。
