# 資料庫規格文件更新記錄 (Documentation Updates v1.2.0)

**日期**: 2025-11-24  
**版本**: v1.2.0  
**主題**: Organizations-Facilities 雙向關聯實作文件同步

---

## 📋 更新摘要

為了與新的 Organizations-Facilities 雙向關聯功能保持一致，已同步更新以下文件：

1. **DB_RELATION.md** - 資料庫關聯圖
2. **system-spec.md** - 系統規格文件

---

## 🔄 具體變更內容

### 1. DB_RELATION.md 更新

#### 1.1 ER Diagram 更新

**Facilities 表結構**:
```mermaid
Facilities {
    NVARCHAR(50) facility_id PK
    NVARCHAR(50) parent_facility_id FK
    NVARCHAR(50) org_id FK         ← 新增
    NVARCHAR(100) facility_name
    NVARCHAR(50) facility_type
}
```

**新增關聯關係**:
```mermaid
Organizations ||--o{ Facilities : "owns"  ← 新增
```

#### 1.2 關聯說明更新

在「設施與設備」(Facilities & Equipment) 區段，新增：
- **Organizations -> Facilities**: 一個組織 (`org_id`) 可以包含多個設施 (`facility_id`)。此為新增的 Organizations-Facilities 關聯。

---

### 2. system-spec.md 更新

#### 2.1 版本歷史更新

新增 v1.2.0 版本記錄：
```
v1.2.0 | 2025-11-24 | - 新增 Facilities 表 org_id 欄位，建立 Organizations-Facilities 關聯
                       - 新增 Facilities API (tree, list, detail, equipment)
                       - 新增 Organizations API 增強 (include_facilities, include_users 參數)
                       - 更新 Mermaid ER Diagram 顯示 Organizations-Facilities 關聯
```

#### 2.2 資料庫結構更新

**Facilities 表**:
- ✅ 新增欄位: `org_id` (NVARCHAR(50))
- ✅ 新增約束: FOREIGN KEY REFERENCES Organizations(org_id)

```sql
| `org_id` | NVARCHAR(50) | 所屬組織編號 | FOREIGN KEY REFERENCES Organizations(org_id) |
```

#### 2.3 API 功能清單更新

新增「組織與設施」功能類別：
- `/api/organizations/{org_id}` - 取得組織詳情 (支援 include_facilities, include_users)
- `/api/organizations/{org_id}/facilities` - 取得組織的設施列表
- `/api/facilities/tree` - 取得設施樹狀結構
- `/api/facilities/list` - 取得設施列表 (支援篩選和分頁)
- `/api/facilities/{facility_id}` - 取得設施詳情
- `/api/facilities/{facility_id}/equipment` - 取得設施的設備列表

移除舊的 `/api/routes/list` (已整合到 Facilities API)

#### 2.4 API 規格詳細說明 - 新增「2.5 組織與設施管理」

包含以下 6 個新的 API 端點的完整規格：

1. **GET /api/organizations/{org_id}** (增強)
   - 新增參數: `include_facilities`, `include_users`
   - 返回組織詳情及相關設施與使用者

2. **GET /api/organizations/{org_id}/facilities**
   - 取得組織的所有設施列表
   - 支援 `include_equipment` 參數

3. **GET /api/facilities/tree**
   - 取得設施樹狀結構
   - 支援 `org_id` 篩選

4. **GET /api/facilities/list**
   - 取得設施列表 (扁平結構)
   - 支援篩選與分頁

5. **GET /api/facilities/{facility_id}**
   - 取得設施詳情
   - 支援 `include_equipment`, `include_children` 參數

6. **GET /api/facilities/{facility_id}/equipment**
   - 取得設施的設備列表

每個 API 都包含：
- ✅ 完整的 Request 說明
- ✅ Response 範例 (JSON 格式)
- ✅ 查詢參數說明
- ✅ HTTP Header 說明

---

## 📊 文件對應關係

```
system-spec.md (v1.2.0)
├── 資料庫結構
│   └── Facilities 表 (新增 org_id 欄位)
├── API 功能清單
│   └── 新增「組織與設施」類別
└── API 規格詳細說明
    └── 2.5 組織與設施管理 (新增完整 6 個端點規格)

DB_RELATION.md
├── ER Diagram
│   └── Facilities 表 (新增 org_id FK)
│   └── Organizations-Facilities 關聯 (新增)
└── 關聯說明
    └── 設施與設備區段 (新增 Organizations->Facilities 描述)
```

---

## 🔗 相關檔案更新清單

| 檔案名稱 | 更新內容 |
|---------|---------|
| `docs/DB_RELATION.md` | ✅ ER Diagram 新增 org_id 欄位 |
| `docs/DB_RELATION.md` | ✅ 新增 Organizations-Facilities 關聯 |
| `docs/DB_RELATION.md` | ✅ 關聯說明文件更新 |
| `docs/system-spec.md` | ✅ 版本歷史新增 v1.2.0 |
| `docs/system-spec.md` | ✅ Facilities 表新增 org_id 欄位 |
| `docs/system-spec.md` | ✅ API 功能清單新增「組織與設施」類別 |
| `docs/system-spec.md` | ✅ API 規格新增「2.5 組織與設施管理」 |
| `docs/ORGANIZATIONS_FACILITIES_API.md` | ✅ 獨立 API 規格文件 (已建立) |
| `docs/ORGANIZATIONS_FACILITIES_SUMMARY.md` | ✅ 實作摘要文件 (已建立) |
| `docs/MOCK_DATA_UPDATE.md` | ✅ Mock Data 更新說明 (已建立) |

---

## ✅ 驗證清單

- ✅ DB_RELATION.md 的 ER Diagram 正確反映 Organizations-Facilities 關聯
- ✅ system-spec.md 的 Facilities 表結構與程式碼一致
- ✅ API 規格文件完整包含所有新增端點
- ✅ API 請求/回應範例格式正確
- ✅ 版本歷史記錄完整
- ✅ 文件內部交叉參考正確

---

## 🚀 後續建議

1. **同步更新其他相關文件**:
   - [ ] API_DOCUMENTATION_GUIDE.md (如有)
   - [ ] WEB_UI_GUIDE.md (更新 UI 與 API 的對應)
   - [ ] DEVELOPMENT.md (更新開發指南)

2. **驗證部署**:
   - [ ] 確認 API 文件與實際程式碼一致
   - [ ] 更新 Swagger/OpenAPI 文件
   - [ ] 測試所有新 API 端點

3. **團隊溝通**:
   - [ ] 發佈更新通知給前端團隊
   - [ ] 發佈更新通知給行動 APP 團隊
   - [ ] 更新技術文件共享

---

## 📚 相關文件清單

- [DB_RELATION.md](./DB_RELATION.md) - 資料庫關聯圖
- [system-spec.md](./system-spec.md) - 系統規格文件
- [ORGANIZATIONS_FACILITIES_API.md](./ORGANIZATIONS_FACILITIES_API.md) - 詳細 API 規格
- [ORGANIZATIONS_FACILITIES_SUMMARY.md](./ORGANIZATIONS_FACILITIES_SUMMARY.md) - 實作摘要
- [MOCK_DATA_UPDATE.md](./MOCK_DATA_UPDATE.md) - Mock Data 更新說明

---

**最後更新**: 2025-11-24  
**版本**: v1.0  
**狀態**: ✅ 完成

