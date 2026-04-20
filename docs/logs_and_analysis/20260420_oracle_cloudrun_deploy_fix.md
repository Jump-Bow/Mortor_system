---
type: log_analysis
audience: backend_devops
date: 2026-04-20
---

# 20260420 Oracle Thick Mode 與 Cloud Run 部署問題追蹤與修正紀錄

## 摘要與背景
於 2026 年 4 月 20 日下午 15:00 至 17:00 之間，在部署 `motor-oracle-sync` Cloud Run Job 至 GCP 時，遭遇以下主要報錯：
`DPI-1047: Cannot locate a 64-bit Oracle Client library`

在排查初期，由於 Cloud Run 與內部網路環境的複雜性，一度將問題錯誤歸咎於 GCP 的 VPC 連線或是 IAM 權限設定（非 GCP 基礎設施問題）。經嚴格遵循第一性原理，拆解 Docker 內部實際執行態後，確認**根本原因是 Docker 環境內的連結器 (OS Linker) 找不到 Oracle Instant Client 所需的動態依賴檔（如 `libnnz19.so`）**。

本文件記錄下午產出的所有相關修正與檔案異動。

---

## 修改項目清單

### 1. Dockerfile 與動態連結庫設定修正
*   **相關檔案**：`Dockerfile`, `.gitignore`
*   **修正內容**：
    *   **新增環境變數**：在 `Dockerfile` 補上 `ENV LD_LIBRARY_PATH=/opt/oracle/instantclient`。
    *   **原因說明**：即使在 Python 程式碼中使用了 `oracledb.init_oracle_client(lib_dir=...)`，這僅對 python-oracledb 模組有效。當 Oracle 底層的 `.so` 檔案彼此進行 `dlopen` 時，仍會仰賴 OS 的動態連結機制；缺少全域的 `LD_LIBRARY_PATH` 會導致作業系統層級找不到依賴庫。
    *   依據 Oracle Instant Client zip 是否隨 codebase 追蹤而調整了 `.gitignore` 的排除規則。

### 2. Python 同步腳本路徑邏輯修正
*   **相關檔案**：`scripts/sync_oracle_data.py`
*   **修正內容**：
    *   **修正路徑 Bug**：修復了 `LD_LIBRARY_PATH` 尾部挾帶冒號（`:`）導致作業系統無法正確解析路徑的問題。

### 3. Cloud Build / Cloud Run 部署設定相容性修正
*   **相關檔案**：`devops/cloudbuild-main.yaml`
*   **修正內容**：
    *   **VPC-SC Egress 設定**：更新建立 Cloud Run Job 的指令，修正 `vpc-egress` 的導向設定，以避免 GCP VPC-SC (VPC Service Controls) 規則誤擋 Docker Image Manifest 的拉取與驗證流程。這解決了後續啟動時伴隨發生的容器載入失敗狀況。

---

## 結論與後續防範
本次錯誤根源為**容器建置層級 (Container Build Layer)** 和**作業系統動態連結庫層級 (OS Linker Layer)**，與外部 GCP 網路、資料庫網路防火牆無關。

1. **第一性原則應用**：未來如再遇 `DPI-1047` 等錯誤，應直接檢測 Docker image 內的實際檔案結構及環境變數（例如先透過 `docker run -it --entrypoint bash ...` 利用 `ldconfig` 或 `echo $LD_LIBRARY_PATH` 檢驗），而非貿然更改外部雲端網路配置。
2. **通訊邊界界定**：查修應用程式依賴時，已確認將 GCP 基礎設施設為「不可改變的已知正確環境」，避免排查方向失焦。
