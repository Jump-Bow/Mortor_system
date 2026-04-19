# 資料庫關聯圖 (Database Relationship Diagram)

本文件描述 FEM 系統的資料庫實體關聯圖 (ER Diagram) 與詳細關聯說明。

> **唯一真實來源**：所有欄位名稱與型別均來自 [`DB_SCHEMA.txt`](file:///d:/chimei/DB_SCHEMA.txt)。

## ER Diagram (Mermaid)

```mermaid
---
config:
  layout: elk
---
erDiagram
    t_organization {
        VARCHAR(48) unitid PK "設施編號"
        VARCHAR(48) parentunitid FK "上層設施編號"
        VARCHAR(96) unitname "設施名稱"
        VARCHAR(48) unittype "設施類別"
    }

    t_equipment {
        VARCHAR(48) id PK "設備編號"
        VARCHAR(96) name "設備名稱"
        VARCHAR(48) assetid "設備ID"
        VARCHAR(48) unitid FK "設施編號"
    }

    t_job {
        VARCHAR(48) actid PK "工單ID"
        VARCHAR(48) equipmentid FK "設備編號"
        VARCHAR(8) mdate "開始日期"
        VARCHAR(2000) act_desc "工單內容"
        VARCHAR(30) act_key "工單編號"
        VARCHAR(30) act_mem_id FK "負責人ID"
        VARCHAR(30) act_mem "負責人名稱"
        VARCHAR(8) group "等級(ABCD)"
        VARCHAR(8) mterm "頻率(1M, 3M)"
    }

    equit_check_item {
        VARCHAR(48) item_id PK "項目ID"
        VARCHAR(48) equipmentid FK "設備編號"
        VARCHAR(24) sort_order "顯示順序"
        VARCHAR(48) item_name "項目名稱"
        VARCHAR(2000) item_desc "項目備註"
        VARCHAR(48) status_type "項目狀態"
        VARCHAR(48) max_v "標準上限"
        VARCHAR(48) min_v "標準下限"
        VARCHAR(24) group "等級(ABCD)"
        VARCHAR(24) mterm "頻率(1M, 3M)"
        VARCHAR(24) unit "單位(mm, C)"
    }

    inspection_result {
        VARCHAR(48) actid PK_FK "工單ID"
        VARCHAR(48) equipmentid PK_FK "設備編號(複合PK)"
        VARCHAR(48) item_id PK_FK "項目ID"
        VARCHAR(48) measured_value "量測值"
        VARCHAR(30) act_mem_id FK "負責人ID"
        DATETIME2 act_time "量測時間"
        VARCHAR(2000) result_photo "照片位置"
        BIT is_out_of_spec "是否異常(0,1,2,3)"
        BIT is_synced "是否已同步(0,1)"
    }

    AbnormalCases {
        VARCHAR(48) actid PK_FK "工單ID"
        VARCHAR(48) equipmentid PK_FK "設備編號(複合PK)"
        VARCHAR(48) item_id PK_FK "項目ID"
        VARCHAR(48) measured_value "量測值"
        BIT is_processed "是否處理"
        VARCHAR(2000) abn_msg "異常內容"
        VARCHAR(2000) abn_solution "處理方式"
        VARCHAR(48) processed_memid FK "處理人員"
        DATETIME2 processed_time "更新時間"
    }

    hr_organization {
        VARCHAR(48) id PK "組織編號"
        VARCHAR(48) parentid FK "上層組織編號"
        VARCHAR(96) name "組織名稱"
    }

    hr_account {
        VARCHAR(48) id PK "人員編號"
        VARCHAR(48) name "人員名稱"
        VARCHAR(48) organizationid FK "組織編號"
        VARCHAR(384) email "電子郵箱"
        VARCHAR(48) password "本地密碼"
    }

    sys_log {
        VARCHAR(48) log_id PK "Log ID"
        DATETIME2 timestamp "時間"
        VARCHAR(48) level "INFO/WARN/ERROR"
        VARCHAR(48) module "模組名稱"
    }

    user_log {
        VARCHAR(48) user_id FK "操作者ID"
        DATETIME2 timestamp "執行時間"
        TEXT changes "操作紀錄"
    }

    %% Relationships
    t_organization ||--o{ t_organization : "parentunitid"
    t_organization ||--o{ t_equipment : "unitid"

    t_equipment ||--o{ t_job : "equipmentid"
    t_equipment ||--o{ equit_check_item : "equipmentid"

    t_job ||--o{ inspection_result : "actid"
    t_equipment ||--o{ inspection_result : "equipmentid"
    equit_check_item ||--o{ inspection_result : "item_id"

    hr_account ||--o{ inspection_result : "act_mem_id"

    inspection_result ||--o{ AbnormalCases : "actid, item_id"
    equit_check_item ||--o{ AbnormalCases : "item_id"

    hr_organization ||--o{ hr_organization : "parentid"
    hr_organization ||--o{ hr_account : "organizationid"
    hr_account ||--o{ user_log : "user_id"
```

## 關聯說明 (Relationships Description)

### 1. 組織與人員 (Organization & Users)
*   **hr_organization (Self-Reference)**: 組織表透過 `parentid` 關聯自身，形成樹狀組織結構。
*   **hr_organization → hr_account**: 一個組織 (`id`) 可以包含多個使用者，透過 `organizationid` 關聯。
*   **roles (應用層輔助表)**: 角色表 (`roles`) 不在 DB_SCHEMA.txt 中定義，為應用層擴展功能。

### 2. 設施與設備 (Facilities & Equipment)
*   **t_organization (Self-Reference)**: 設施表透過 `parentunitid` 關聯自身，形成樹狀設施結構（廠區 → 樓層 → 區域）。
*   **t_organization → t_equipment**: 一個設施 (`unitid`) 可以包含多個設備。
*   **t_equipment → equit_check_item**: 一個設備 (`id`) 擁有多個檢查項目（`equipmentid` 關聯）。

### 3. 巡檢任務與結果 (Inspection Tasks & Results)
*   **t_equipment → t_job**: 針對一個設備可以建立多個巡檢工單（`equipmentid` 關聯）。
*   **hr_account → t_job**: 一個工單指派給一個負責人（`act_mem_id` 關聯）。
*   **t_job → inspection_result**: 一個工單包含多個檢查項目的結果（`actid` 關聯）。
*   **equit_check_item → inspection_result**: 每個結果對應一個檢查項目（`item_id` 關聯）。
*   **hr_account → inspection_result**: 每個檢查結果記錄了實際檢查人員（`act_mem_id` 關聯）。

### 4. 異常追蹤 (Abnormal Tracking)
*   **inspection_result → AbnormalCases**: 異常追蹤記錄關聯到特定的巡檢結果（複合鍵 `actid` + `equipmentid` + `item_id`）。
*   **hr_account → AbnormalCases**: 異常由特定的處理人員處理（`processed_memid` 關聯）。

### 5. 系統日誌 (Logs)
*   **hr_account → user_log**: 使用者的操作行為記錄（`user_id` 關聯）。
*   **sys_log**: 獨立的系統日誌，無直接外鍵關聯。

## 欄位名稱對照表

| 表名 | Model 檔案 | Class 名稱 |
|------|-----------|-----------|
| `t_organization` | `Mortor_organization.py` | `TOrganization` |
| `t_equipment` | `Mortor_equipment.py` | `TEquipment` |
| `t_job` | `Mortor_inspection.py` | `TJob` |
| `equit_check_item` | `Mortor_equipment.py` | `EquitCheckItem` |
| `inspection_result` | `Mortor_inspection.py` | `InspectionResult` |
| `AbnormalCases` | `Mortor_abnormal.py` | `AbnormalCases` |
| `hr_organization` | `Mortor_organization.py` | `HrOrganization` |
| `hr_account` | `Mortor_user.py` | `HrAccount` |
| `sys_log` | `Mortor_system_log.py` | `SystemLog` |
| `user_log` | `Mortor_system_log.py` | `UserLog` |
