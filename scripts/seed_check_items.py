"""
seed_check_items.py
====================
職責：確保 equit_check_item 巡檢項目主檔存在於資料庫中。

本表為本系統（馬達巡檢系統）自行維護的業務主檔，
並非來自 Oracle AIMS，故需在正式環境初次部署（或重建 DB）後手動執行。

設計原則：
- 冪等性（Idempotent）：可安全重複執行，不會產生重複資料
- item_id 格式："{grade}_{mterm}_{sort_order}"
- 各等級（A~D）對應不同保養週期（mterm）

執行方式：
  python scripts/seed_check_items.py

環境變數（可選）：
  FLASK_ENV=production  (預設 development)
"""
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app, db
from app.models import EquitCheckItem


# ==============================================================================
# 業務主檔：巡檢項目標準規格
# 格式：(sort_order, item_name, item_desc, max_v, unit, grade, mterm)
#
# 規則說明：
#   - status_type='normal'  → 有數值上限，需量測填寫數字
#   - status_type='status'  → 狀態型項目（正常/異常），填寫描述
#
# 等級對應週期：
#   A 級 → 1M（每月）
#   B 級 → 1M（每月）+ 3M（每季，注油）
#   C 級 → 1M（每月）+ 3M（每季，注油）
#   D 級 → 4M（每四個月）
# ==============================================================================
SPECS_DATA = [
    # ── A 級 (1M) ───────────────────────────────────────────────────
    ('001', '前軸承溫度',           None,               '70',  '℃',    'A', '1M'),
    ('002', '馬達本體溫度',         None,               '80',  '℃',    'A', '1M'),
    ('003', '後軸承溫度',           None,               '70',  '℃',    'A', '1M'),
    ('004', 'MIH振動量測',          None,               '4',   'mm/s', 'A', '1M'),
    ('005', 'MIV振動量測',          None,               '4',   'mm/s', 'A', '1M'),
    ('006', 'MIA振動量測',          None,               '4',   'mm/s', 'A', '1M'),
    ('007', 'MOH振動量測',          None,               '4',   'mm/s', 'A', '1M'),
    ('008', 'MOV振動量測',          None,               '4',   'mm/s', 'A', '1M'),
    ('009', '馬達異響',             '聲音項目',          None,  None,   'A', '1M'),
    ('010', '油位是否於正常範圍',   '油位檢查(液壓油位)', None, None,   'A', '1M'),
    ('011', '注油',                 '注油(牛油)',        None,  None,   'A', '1M'),

    # ── B 級 (1M) ───────────────────────────────────────────────────
    ('001', '前軸承溫度',           None,               '70',  '℃',    'B', '1M'),
    ('002', '馬達本體溫度',         None,               '80',  '℃',    'B', '1M'),
    ('003', '後軸承溫度',           None,               '70',  '℃',    'B', '1M'),
    ('004', 'MIH振動量測',          None,               '4',   'mm/s', 'B', '1M'),
    ('005', 'MIV振動量測',          None,               '4',   'mm/s', 'B', '1M'),
    ('006', 'MIA振動量測',          None,               '4',   'mm/s', 'B', '1M'),
    ('007', 'MOH振動量測',          None,               '4',   'mm/s', 'B', '1M'),
    ('008', 'MOV振動量測',          None,               '4',   'mm/s', 'B', '1M'),
    ('009', '馬達異響',             '聲音項目',          None,  None,   'B', '1M'),
    ('010', '油位是否於正常範圍',   '油位檢查(液壓油位)', None, None,   'B', '1M'),
    # ── B 級 (3M) ───────────────────────────────────────────────────
    ('011', '注油',                 '注油(牛油)',        None,  None,   'B', '3M'),

    # ── C 級 (1M) ───────────────────────────────────────────────────
    ('001', '前軸承溫度',           None,               '70',  '℃',    'C', '1M'),
    ('002', '馬達本體溫度',         None,               '80',  '℃',    'C', '1M'),
    ('003', '後軸承溫度',           None,               '70',  '℃',    'C', '1M'),
    ('004', 'MIH振動量測',          None,               '4',   'mm/s', 'C', '1M'),
    ('005', 'MIV振動量測',          None,               '4',   'mm/s', 'C', '1M'),
    ('006', 'MIA振動量測',          None,               '4',   'mm/s', 'C', '1M'),
    ('007', 'MOH振動量測',          None,               '4',   'mm/s', 'C', '1M'),
    ('008', 'MOV振動量測',          None,               '4',   'mm/s', 'C', '1M'),
    ('009', '馬達異響',             '聲音項目',          None,  None,   'C', '1M'),
    ('010', '油位是否於正常範圍',   '油位檢查(液壓油位)', None, None,   'C', '1M'),
    # ── C 級 (3M) ───────────────────────────────────────────────────
    ('011', '注油',                 '注油(牛油)',        None,  None,   'C', '3M'),

    # ── D 級 (4M) ───────────────────────────────────────────────────
    ('001', '前軸承溫度',           None,               '70',  '℃',    'D', '4M'),
    ('002', '馬達本體溫度',         None,               '80',  '℃',    'D', '4M'),
    ('003', '後軸承溫度',           None,               '70',  '℃',    'D', '4M'),
    ('004', 'MIH振動量測',          None,               '4',   'mm/s', 'D', '4M'),
    ('005', 'MIV振動量測',          None,               '4',   'mm/s', 'D', '4M'),
    ('006', 'MIA振動量測',          None,               '4',   'mm/s', 'D', '4M'),
    ('007', 'MOH振動量測',          None,               '4',   'mm/s', 'D', '4M'),
    ('008', 'MOV振動量測',          None,               '4',   'mm/s', 'D', '4M'),
    ('009', '馬達異響',             '聲音項目',          None,  None,   'D', '4M'),
    ('010', '油位是否於正常範圍',   '油位檢查(液壓油位)', None, None,   'D', '4M'),
    ('011', '注油',                 '注油(牛油)',        None,  None,   'D', '4M'),
]

STATUS_ITEMS = {'聲音項目', '油位檢查(液壓油位)', '注油(牛油)'}


def seed(dry_run: bool = False) -> None:
    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)

    with app.app_context():
        created = 0
        skipped = 0

        for row in SPECS_DATA:
            sort_order, item_name, item_desc, max_v, unit, grade, mterm = row
            item_id = f"{grade}_{mterm}_{sort_order}"

            if EquitCheckItem.query.get(item_id):
                skipped += 1
                continue

            status_type = 'status' if item_desc in STATUS_ITEMS else 'normal'
            db.session.add(EquitCheckItem(
                item_id=item_id,
                item_name=item_name,
                item_desc=item_desc,
                sort_order=sort_order,
                max_v=max_v,
                unit=unit,
                grade=grade,
                mterm=mterm,
                status_type=status_type,
            ))
            created += 1

        if dry_run:
            db.session.rollback()
            print(f"[Dry Run] 待新增: {created} 筆，已存在跳過: {skipped} 筆")
        else:
            db.session.commit()
            print(f"✅ 完成！新增: {created} 筆，已存在跳過: {skipped} 筆")


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='寫入 equit_check_item 巡檢項目主檔')
    parser.add_argument('--dry-run', action='store_true', help='模擬執行，不實際寫入資料庫')
    args = parser.parse_args()

    seed(dry_run=args.dry_run)
