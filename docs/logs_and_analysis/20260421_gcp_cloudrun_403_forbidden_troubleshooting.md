---
type: investigation_and_analysis
audience: backend_engineers
date: 2026-04-21
---

# 記錄與分析：GCP Cloud Run Deploy 後出現 Error: Forbidden 403 錯誤

## 問題描述

專案在透過 Cloud Build 部署並啟動於 Cloud Run 後，直接訪問 Cloud Run 原生提供的 `.run.app` URL，畫面顯示如下黑白純文字錯誤：

> **Error: Forbidden**
> Your client does not have permission to get URL / from this server.

此錯誤源自 Google Front End (GFE) 基礎設施層，代表請求在「到達 Flask 應用程式之前」就已被 GCP 的安全機制攔截。

## 第一性原理分析與根本原因

由於專案架構中包含建立 Shared VPC 與部署時指定使用特定的 subnet 進行通訊，可以判斷出我們身處一個具備相對高安全級別的企業雲端環境中。此現象通常並非程式碼錯誤，而是由於以下三個基礎架構限制所導致：

### 1. VPC Service Controls 邊界攔截 (最可能的主因)
當專案 (`prj-ai-intellipatrol-ip`) 受到 **VPC Service Controls (外圍防護)** 保護時，Google 會在基礎架構層直接封鎖所有來自「公開網際網路」的存取嘗試。
即便已經在部署時加上了 `--allow-unauthenticated`，來自外部直接存取 `.run.app` 網址的行為都會被 VPC SC 完全無情地阻絕。只有經許可的 Access Level (例如公司內部網段、專屬 VPN)，或白名單中的代理端才能通行。

### 2. 組織政策阻擋 `allUsers` (Domain Restricted Sharing)
儘管在 `cloudbuild-main.yaml` 中的 `gcloud run deploy` 使用了 `--allow-unauthenticated` 參數來允許未驗證的訪問，但如果企業 GCP 組織開啟了 **網域限制共用 (Domain Restricted Sharing)** 限制，這個加上 `allUsers` (也就是無限制公開) 的操作將會被 GCP 靜默忽略或拒絕。結果是該 Cloud Run 服務始終需要提供有效的 IAM 身分才能訪問。

### 3. Ingress 設定改為 Internal
部署雖然預設為 `All Traffic` 可以進入，但在某些安全規範或設定中，這項 Cloud Run 服務的 **Ingress** (進入點) 被設定成了 **Internal** (或是 Internal and Cloud Load Balancing)。
在 Internal 的情況下，不論 IAM 的存取規則多寬鬆，外部的瀏覽器都無法直接造訪預設的 `.run.app` 網址。

---

## 明日進公司確認事項與解決步驟清單

請依據此清單與公司的架構師或 DevOps 人員確認以下三個方向：

### 確認一、網路存取與 VPN 限制
這是一個僅限內部使用的後台系統，還是會暴露到外網？
* **行動**：如果這屬於內部系統，您可能需要先連線至**公司專屬 VPN**。只有當您的連線 IP 位於企業內網且被加入 VPC SC 的 Access Level 白名單中，才能順利通過 VPC SC 的邊界驗證並看到畫面。

### 確認二、是否應使用正式網域 (Load Balancer) 取代 `.run.app`
* **行動**：請確認架構中，此 Cloud Run 服務前方是否架設了 **HTTP(S) Load Balancer** 或 **API Gateway**。
在企業系統中，通常會完全封鎖外部直接對 Cloud Run 原生 `.run.app` 網址的呼叫。您應該從公司核發的「掛載憑證與企業 WAF 防護的正式網域 (如 `admin.chimei...`)」來存取系統，因為只有負載平衡器的子網路具備存取該 Cloud Run 服務的內部權限。

### 確認三、從 GCP Console 中檢查實際生效的安全設定
請登入 GCP Console 並導航至 **Cloud Run -> `motor-server` -> 分頁: Security (安全性) 與 Networking (網路)** 進行檢核：
* **檢核 IAM 權限**：在權限列表中，確認是否「真的有」加入一個名為 `allUsers` 的主體，且其被賦予了 `Cloud Run Invoker (Cloud Run 呼叫者)` 的角色。若找不到，這代表您部署指令中的 `--allow-unauthenticated` 已經被「組織策略防護」默默阻擋。
* **檢核 Ingress (進入點路徑)**：檢查該服務的連入流量設定是否為 `All (允許所有流量)`。若呈現為 `Internal` 或 `Internal and Cloud Load Balancing`，這正是造成從外網連線發生 403 Forbidden 的主要原因。
