-- Migration Script: Rename 'group' column to 'grade'
-- Date: 2026-03-08

-- 1. Rename column in equit_check_item table
ALTER TABLE public.equit_check_item RENAME COLUMN "group" TO grade;

-- 2. Rename column in t_job table
ALTER TABLE public.t_job RENAME COLUMN "group" TO grade;

-- 3. Update comments (Optional)
COMMENT ON COLUMN public.equit_check_item.grade IS '等級(ABCD)';
COMMENT ON COLUMN public.t_job.grade IS '等級(ABCD)';

-- 4. Re-create index if necessary (PostgreSQL automatically renames index dependencies)
-- However, if the index name itself contained 'group', we might want to rename it too
-- But based on our current schema, it was ix_equit_check_item_grade_mterm, which is already correct.
