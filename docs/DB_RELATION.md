# 資料庫關聯圖 (Database Relationship Diagram)

本文件描述 FEM 系統的資料庫實體關聯圖 (ER Diagram) 與詳細關聯說明。

## ER Diagram (Mermaid)

## ER Diagram (Mermaid)

```mermaid
erDiagram
    t_organization {
        VARCHAR(48) unitid PK
        VARCHAR(48) parentunitid FK
        VARCHAR(96) unitname
        VARCHAR(48) unittype
    }

    t_equipment {
        VARCHAR(48) id PK
        VARCHAR(96) name
        VARCHAR(48) assetid
        VARCHAR(48) unitid FK
    }

    hr_organization {
        VARCHAR(48) id PK
        VARCHAR(48) parentid FK
        VARCHAR(96) name
    }

    hr_account {
        VARCHAR(48) id PK
        VARCHAR(48) name
        VARCHAR(128) email
        VARCHAR(255) password_hash
        INTEGER role_id FK
        TIMESTAMP created_at
    }

    roles {
        SERIAL role_id PK
        VARCHAR(64) role_name
        VARCHAR(200) description
    }

    t_job {
        VARCHAR(48) actid PK
        VARCHAR(48) actkey
        VARCHAR(48) equipmentid FK
        DATE mdate
        VARCHAR(256) description
        VARCHAR(48) actmemid FK
        VARCHAR(20) status
        TIMESTAMP created_at
    }

    equit_check_item {
        VARCHAR(48) itemid PK
        VARCHAR(48) equipmentid FK
        VARCHAR(96) itemname
        VARCHAR(256) itemdescription
        VARCHAR(48) statustype
        VARCHAR(48) ulspec
        VARCHAR(48) llspec
        INTEGER sortorder
    }

    inspection_result {
        VARCHAR(48) actid PK, FK
        VARCHAR(48) itemid PK, FK
        VARCHAR(48) equipmentid FK
        VARCHAR(48) measuredvalue
        VARCHAR(48) inspectorid FK
        TIMESTAMP acttime
        VARCHAR(256) photopath
        SMALLINT isoutofspec
        BOOLEAN isprocessed
        TIMESTAMP created_at
    }

    abnormal_cases {
        SERIAL id PK
        VARCHAR(48) actid FK
        VARCHAR(48) itemid FK
        VARCHAR(48) equipmentid
        VARCHAR(48) measuredvalue
        VARCHAR(256) abnmsg
        TEXT abnsolution
        BOOLEAN isprocessed
        VARCHAR(48) responsibleperson FK
        TIMESTAMP processedat
    }

    system_log {
        VARCHAR(48) logid PK
        TIMESTAMP createdat
        VARCHAR(20) level
        VARCHAR(50) module
        TEXT message
        TEXT exception
    }

    user_action_log {
        SERIAL id PK
        VARCHAR(48) userid FK
        TIMESTAMP timestamp
        VARCHAR(64) actiontype
        VARCHAR(256) description
        JSONB changes
        VARCHAR(48) ipaddress
        VARCHAR(20) status
    }

    %% Relationships
    t_organization ||--o{ t_organization : "parent/child"
    t_organization ||--o{ t_equipment : "contains"
    hr_organization ||--o{ hr_organization : "parent/child"
    hr_account }|--|| hr_organization : "belongs to"
    roles ||--o{ hr_account : "assigned to"
    t_equipment ||--o{ t_job : "inspected in"
    t_equipment ||--o{ equit_check_item : "has items"
    hr_account ||--o{ t_job : "assigned to"
    t_job ||--o{ inspection_result : "has results"
    equit_check_item ||--o{ inspection_result : "has results"
    hr_account ||--o{ inspection_result : "inspected by"
    inspection_result ||--o{ abnormal_cases : "triggers"
    hr_account ||--o{ abnormal_cases : "responsible for"
    hr_account ||--o{ user_action_log : "performs"
```

## 關聯說明 (Relationships Description)

### 1. 組織與人員 (Organization & Users)
*   **hr_organization (Self-Reference)**: 組織表透過 `parentid` 關聯自身，形成樹狀組織結構。
*   **hr_organization -> hr_account**: 一個組織 (`id`) 可以包含多個使用者 (`hr_account`)。關聯並非強制外鍵，而是業務邏輯關聯。
*   **roles -> hr_account**: 一個角色 (`role_id`) 可以分配給多個使用者 (`id`)。詳細權限邏輯保留於應用層。

### 2. 設施與設備 (Facilities & Equipment)
*   **t_organization (Self-Reference)**: 設施表透過 `parentunitid` 關聯自身，形成樹狀設施結構 (例如：廠區 -> 樓層 -> 區域)。
*   **t_organization -> t_equipment**: 一個設施 (`unitid`) 可以包含多個設備 (`id`)。
*   **t_equipment -> equit_check_item**: 一個設備 (`id`) 擁有多個檢查項目 (`itemid`)。

### 3. 巡檢任務與結果 (Inspection Tasks & Results)
*   **t_equipment -> t_job**: 針對一個設備 (`id`) 可以建立多個巡檢任務 (`actid`)。
*   **hr_account -> t_job**: 一個任務 (`actid`) 指派給一個負責人 (`actmemid`)。
*   **t_job -> inspection_result**: 一個任務 (`actid`) 包含多個檢查項目的結果。
*   **equit_check_item -> inspection_result**: 每個結果對應一個檢查項目 (`itemid`)。
*   **hr_account -> inspection_result**: 每個檢查結果記錄了實際檢查人員 (`inspectorid`)。

### 4. 異常追蹤 (Abnormal Tracking)
*   **inspection_result -> abnormal_cases**: 異常追蹤記錄關聯到特定的巡檢結果 (`actid`, `itemid`)。
*   **hr_account -> abnormal_cases**: 異常追蹤由特定的負責人 (`responsibleperson`) 處理。

### 5. 系統日誌 (Logs)
*   **hr_account -> user_action_log**: 使用者 (`userid`) 的操作行為被記錄在使用者日誌中。
*   **system_log**: 獨立的系統日誌，無直接的外鍵關聯，用於記錄系統層級事件。
