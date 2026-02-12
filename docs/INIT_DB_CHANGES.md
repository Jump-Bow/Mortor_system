# init_db.py 更新說明

## 更新日期
2026-02-11

## 主要變更

### 1. PostgreSQL 遷移與模型對齊
- ✅ **HrOrganization 欄位修正**：將 `organizationid` / `organizationname` 更正為 `id` / `name`，以符合 `HrOrganization` 模型定義。
- ✅ **模型名稱更新**：全面使用新版 ORM 模型名稱 (`HrAccount`, `TJob`, `TOrganization`, `TEquipment` 等)。
- ✅ **移除 MSSQL 依賴**：確保初始化腳本兼容 PostgreSQL。

## 更新日期
2025-11-25

## 主要變更

### 1. 移除不必要的 Mock Data 處理邏輯

**移除的內容：**
- ❌ `inspection_routes` 相關處理（已被 Facilities 取代）
- ❌ `control_points` 相關處理（已被 Equipment 取代）
- ❌ 複雜的 ID 映射邏輯（從舊結構到新結構的轉換）
- ❌ 從 JSON 檔案讀取 mock_data.json 的邏輯

**原因：**
根據 `docs/DB_RELATION.md`，系統應使用以下結構：
- `Facilities` - 設施（取代舊的 inspection_routes）
- `Equipment` - 設備（取代舊的 control_points）
- `Equipment_Check_Items` - 檢查項目

### 2. 新增完整的測試資料結構

**組織架構（Organizations）：**
```
CORP (奇美實業)
├── 11102 (行政處)
│   └── 11102-MOTOR (行政處-馬達巡檢)
└── 11103 (生產處)
    └── 11103-COOLING (生產處-冷卻系統)
```

**設施階層（Facilities）：**
```
PLANT_A (A廠區)
└── BUILDING_A1 (A1廠房)
    └── FLOOR_A1_1F (A1廠房-1樓)
        └── AREA_MOTOR_ROOM (馬達機房)

PLANT_B (B廠區)
└── BUILDING_B1 (B1廠房)
    └── FLOOR_B1_2F (B1廠房-2樓)
        └── AREA_COOLING_ROOM (冷卻系統機房)
```

**設備（Equipment）：**
- MAE05D31 - V2真空泵浦馬達（5個檢查項目）
- MAE05D32 - 冷卻泵浦馬達（3個檢查項目）
- MAE05D33 - 抽風機馬達（2個檢查項目）
- COOL01 - 主冷卻塔（3個檢查項目）
- COOL02 - 副冷卻塔（2個檢查項目）

**使用者（Users）：**
- admin - 系統管理員
- I0001 - 張文雄（巡檢人員）
- I0002 - 李建國（巡檢人員）
- I0003 - 王美玲（巡檢人員）

### 3. 確保 10-12 月都有測試資料

**巡檢任務生成規則：**
- 📅 **時間範圍**：2025年10月、11月、12月
- 🔄 **頻率**：每3天為每個設備生成一次任務
- 👥 **指派**：輪流指派給 I0001, I0002, I0003
- 📊 **狀態邏輯**：
  - 過去日期 → `Completed`（已完成）
  - 今天 → `InProgress`（進行中）
  - 未來日期 → `Pending`（待執行）

**預估任務數量：**
- 10月：約 50 個任務（5設備 × 10次）
- 11月：約 50 個任務（5設備 × 10次）
- 12月：約 50 個任務（5設備 × 10次）
- **總計：約 150 個任務**

### 4. 巡檢結果（Inspection Results）

**已完成任務（Completed）：**
- ✅ 所有檢查項目都有結果
- 📊 80% 正常值，20% 異常值（模擬真實情況）
- ⏰ 檢查時間：任務日期的 8:00-17:00 之間隨機

**進行中任務（InProgress）：**
- ⚡ 約 50% 的檢查項目已完成
- ⏰ 檢查時間：最近 1-3 小時內

**待執行任務（Pending）：**
- ⏳ 無巡檢結果

### 5. 數據真實性

**數值型檢查項目：**
- 正常值：在上下限範圍的 30%-70% 之間
- 異常值：超出上限 1-5 單位，或低於下限 1-3 單位

**選項型檢查項目：**
- 選項：正常、充足、良好、需補充
- 異常判定：「需補充」視為異常

## 使用方式

### 初始化資料庫

```bash
# 刪除舊資料庫（如果存在）
rm -f instance/fem.db

# 執行初始化腳本
python init_db.py
```

### 預期輸出

```
Creating database tables...
✓ Database tables created successfully

Creating roles...
  ✓ Created role: 管理者
  ✓ Created role: 巡檢人員
  ✓ Created role: 查詢人員

Creating default admin user...
  ✓ Admin user created (user_id: admin, password: 1234qwer5T)

Creating sample users...
  ✓ Created user: I0001 - 張文雄
  ✓ Created user: I0002 - 李建國
  ✓ Created user: I0003 - 王美玲

Creating organizations...
  ✓ Created organization: 奇美實業
  ✓ Created organization: 行政處
  ...

Creating facilities...
  ✓ Created facility: A廠區
  ✓ Created facility: A1廠房
  ...

Creating equipment...
  ✓ Created equipment: MAE05D31 V2真空泵浦馬達
  ...

Creating check items...
  ✓ Created check item: MAE05D31 - 前軸承溫度
  ...

Creating inspection tasks for Oct-Dec 2025...
  ✓ Created task: TASK20251001001 - MAE05D31 V2真空泵浦馬達 (2025-10-01) - Completed
  ...

Creating inspection results for completed tasks...
  ✓ Created XXX inspection results

Creating partial results for in-progress tasks...
  ✓ Created XX partial inspection results

============================================================
Database initialization completed successfully!
============================================================

Database Statistics:
  Organizations: 5
  Facilities: 8
  Equipment: 5
  Check Items: 15
  Users: 4
  Inspection Tasks: ~150
    - Completed: ~XXX
    - In Progress: ~X
    - Pending: ~XX
  Inspection Results: ~XXX

Tasks by Month:
  2025-10: XX tasks
  2025-11: XX tasks
  2025-12: XX tasks

============================================================
Default credentials:
  User ID: admin
  Password: 1234qwer5T

Sample users:
  User ID: I0001 / I0002 / I0003
  Password: password123
============================================================
```

## 符合 DB_RELATION.md 的結構

✅ **Organizations** - 組織階層結構
✅ **Facilities** - 設施階層結構（Plant → Building → Floor → Area）
✅ **Equipment** - 設備關聯到 Facilities
✅ **Equipment_Check_Items** - 檢查項目關聯到 Equipment
✅ **Users** - 使用者關聯到 Organizations 和 Roles
✅ **Inspection_Tasks** - 巡檢任務關聯到 Equipment 和 Users
✅ **Inspection_Results** - 巡檢結果（複合主鍵：task_id + item_id）

## 移除的舊結構

❌ **inspection_routes** - 已被 Facilities 取代
❌ **control_points** - 已被 Equipment 取代
❌ **aims_orders** - 不在 DB_RELATION.md 中定義

## 注意事項

1. **mock_data.json 不再使用**：所有測試資料現在直接在 `init_db.py` 中生成
2. **資料一致性**：所有外鍵關聯都正確設定
3. **測試資料完整性**：10-12月都有充足的測試資料
4. **真實性**：模擬真實的巡檢場景，包含正常和異常數據
