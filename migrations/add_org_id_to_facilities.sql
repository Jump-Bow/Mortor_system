"""
數據庫遷移指令 - 為 Facilities 資料表新增 org_id 欄位

執行步驟：
1. 備份現有資料庫
2. 執行此 SQL 指令新增 org_id 欄位
3. 更新現有資料（根據業務邏輯設定 org_id）
4. 驗證資料完整性

注意事項：
- org_id 欄位允許 NULL，因此不會影響現有資料
- 建議根據設施與組織的業務關係更新現有記錄
- 新增外鍵約束，確保資料完整性
"""

# ============================================
# 1. 新增 org_id 欄位到 Facilities 資料表
# ============================================
ALTER TABLE Facilities
ADD org_id NVARCHAR(50) NULL;

# ============================================
# 2. 新增外鍵約束
# ============================================
ALTER TABLE Facilities
ADD CONSTRAINT FK_Facilities_Organizations
FOREIGN KEY (org_id) REFERENCES Organizations(org_id);

# ============================================
# 3. (可選) 為 org_id 欄位建立索引以提升查詢效能
# ============================================
CREATE INDEX IX_Facilities_OrgId ON Facilities(org_id);

# ============================================
# 4. 更新現有資料 (範例)
# ============================================
# 根據業務邏輯更新現有設施的 org_id
# 以下為範例，請根據實際情況調整

-- 範例 1: 將所有設施關聯到預設組織
-- UPDATE Facilities
-- SET org_id = 'DEFAULT_ORG_ID'
-- WHERE org_id IS NULL;

-- 範例 2: 根據設施名稱或類型進行關聯
-- UPDATE Facilities
-- SET org_id = 'DEPT_A'
-- WHERE facility_name LIKE '%部門A%';

# ============================================
# 5. 驗證資料完整性
# ============================================
-- 檢查未關聯組織的設施數量
SELECT COUNT(*) AS unlinked_facilities
FROM Facilities
WHERE org_id IS NULL;

-- 檢查設施與組織的關聯統計
SELECT 
    o.org_id,
    o.org_name,
    COUNT(f.facility_id) AS facility_count
FROM Organizations o
LEFT JOIN Facilities f ON o.org_id = f.org_id
GROUP BY o.org_id, o.org_name
ORDER BY facility_count DESC;

-- 驗證外鍵約束
SELECT 
    f.facility_id,
    f.facility_name,
    f.org_id,
    o.org_name
FROM Facilities f
LEFT JOIN Organizations o ON f.org_id = o.org_id
WHERE f.org_id IS NOT NULL;

# ============================================
# 回滾指令 (如需移除變更)
# ============================================
-- 1. 移除外鍵約束
-- ALTER TABLE Facilities
-- DROP CONSTRAINT FK_Facilities_Organizations;

-- 2. 移除索引
-- DROP INDEX IX_Facilities_OrgId ON Facilities;

-- 3. 移除欄位
-- ALTER TABLE Facilities
-- DROP COLUMN org_id;
