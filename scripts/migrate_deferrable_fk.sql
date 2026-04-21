-- ===========================================================================
-- 遷移說明：修復自身參照 FK 為 DEFERRABLE INITIALLY DEFERRED
-- 適用版本：PostgreSQL 12+
-- 執行時機：部署新版本前，由 DBA 或具 SUPERUSER/OWNER 權限帳號執行
-- ===========================================================================
-- 問題根因：
--   t_organization.parentunitid → t_organization.unitid（自身參照）
--   hr_organization.parentid   → hr_organization.id（自身參照）
--
--   普通 FK（非 DEFERRABLE）會在每列 INSERT 時立即檢查。
--   批次 INSERT 整棵樹時，子節點先於父節點插入 → FK 違規。
--
--   解法：改為 DEFERRABLE INITIALLY DEFERRED
--   → PostgreSQL 將 FK 檢查延遲到 COMMIT 時，屆時整棵樹已完整，不違規。
-- ===========================================================================

BEGIN;

-- 1. 修復 t_organization 自身參照 FK
ALTER TABLE t_organization
    DROP CONSTRAINT IF EXISTS t_organization_parentunitid_fkey;

ALTER TABLE t_organization
    ADD CONSTRAINT t_organization_parentunitid_fkey
        FOREIGN KEY (parentunitid)
        REFERENCES t_organization(unitid)
        DEFERRABLE INITIALLY DEFERRED;

-- 2. 修復 hr_organization 自身參照 FK
ALTER TABLE hr_organization
    DROP CONSTRAINT IF EXISTS hr_organization_parentid_fkey;

ALTER TABLE hr_organization
    ADD CONSTRAINT hr_organization_parentid_fkey
        FOREIGN KEY (parentid)
        REFERENCES hr_organization(id)
        DEFERRABLE INITIALLY DEFERRED;

COMMIT;

-- 驗證（執行後確認 isDeferrable = YES）：
-- SELECT conname, condeferrable, condeferred
-- FROM pg_constraint
-- WHERE conname IN (
--     't_organization_parentunitid_fkey',
--     'hr_organization_parentid_fkey'
-- );
