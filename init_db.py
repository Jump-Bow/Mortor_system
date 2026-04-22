"""
Database Initialization Script (Self-contained Sample Data)
初始化資料庫並建立完整的固定測試資料
"""
import os
import random
from datetime import datetime, timedelta, date
from app import create_app, db
from app.models import (
    HrAccount, Role, HrOrganization, TOrganization, 
    TEquipment, EquitCheckItem, TJob, InspectionResult,
    AbnormalCases, SystemLog, UserLog
)

# ==============================================================================
# 1. 輔助函數：日期生成
# ==============================================================================

def get_dynamic_date(month_offset=0, day=None):
    """
    生成最近三個月內的日期。
    month_offset: 0 (本月), 1 (上個月), 2 (前二個月)
    """
    today = date.today()
    
    # 計算目標年月份
    target_month = today.month - month_offset
    target_year = today.year
    while target_month <= 0:
        target_month += 12
        target_year -= 1
    
    if day is None:
        day = random.randint(1, 28)
    
    return date(target_year, target_month, day).strftime('%Y%m%d')

# ==============================================================================
# 2. 初始化流程
# ==============================================================================

def init_database():
    """初始化資料庫並建立固定測試資料 (冪等性設計，可重複執行)"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    uploads_dir = os.path.join(base_dir, 'uploads', 'photos')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        print(f"Created directory: {uploads_dir}")

    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)

    with app.app_context():
        print("--- 建立資料表 (若不存在) ---")
        # db.drop_all()  # 已移除危險指令
        db.create_all()

        # 取得控制參數：是否跳過範例資料 (正式環境建議設為 true)
        skip_sample = os.getenv('SKIP_SAMPLE_DATA', 'false').lower() == 'true'
        print(f"模式設定: {'[僅建立基礎結構]' if skip_sample else '[完整初始化 (包含範例資料)]'}")

        # 1. 建立角色 (系統基礎必要資料)
        print("檢查角色...")
        roles_data = [
            {'name': '管理者', 'desc': '系統管理員'},
            {'name': '巡檢人員', 'desc': '現場執行人員'},
            {'name': '查詢人員', 'desc': '報表查詢人員'}
        ]
        for r_data in roles_data:
            if not Role.query.filter_by(role_name=r_data['name']).first():
                db.session.add(Role(role_name=r_data['name'], description=r_data['desc']))

        # 2. 預設管理員 (系統基礎必要資料)
        print("檢查預設管理員...")
        HrAccount.create_default_admin()
        db.session.commit()

        if skip_sample:
            print(">>> 已啟動 SKIP_SAMPLE_DATA，跳過後續範例資料建立。")
        else:
            # 3. 建立組織 (HrOrganization) - 範例資料
            print("檢查組織架構 (範例)...")
            orgs_data = [
                {'id': 'CORP', 'name': '奇美實業', 'pid': None},
                {'id': '11102', 'name': '行政處', 'pid': 'CORP'},
                {'id': '11102-M', 'name': '馬達巡檢課', 'pid': '11102'},
                {'id': '11103', 'name': '生產處', 'pid': 'CORP'},
                {'id': '11103-C', 'name': '冷卻系統課', 'pid': '11103'},
            ]
            for o in orgs_data:
                if not HrOrganization.query.get(o['id']):
                    db.session.add(HrOrganization(id=o['id'], name=o['name'], parentid=o['pid']))

            # 4. 建立場域 (TOrganization) - 範例資料
            print("檢查廠區場域 (範例)...")
            facilities_data = [
                {'id': 'PLANT_A', 'name': 'A廠區', 'type': 'Plant', 'pid': None},
                {'id': 'PLANT_B', 'name': 'B廠區', 'type': 'Plant', 'pid': None},
                {'id': 'A_RM_01', 'name': 'A1廠馬達機房', 'type': 'Area', 'pid': 'PLANT_A'},
                {'id': 'B_RM_01', 'name': 'B1廠冷卻機房', 'type': 'Area', 'pid': 'PLANT_B'},
            ]
            for f in facilities_data:
                if not TOrganization.query.get(f['id']):
                    db.session.add(TOrganization(unitid=f['id'], unitname=f['name'], unittype=f['type'], parentunitid=f['pid']))

            # 5. 建立人員 (HrAccount) - 範例資料
            print("檢查測試帳號 (範例)...")
            users_data = [
                {'id': 'I0001', 'name': '張文雄', 'email': 'i0001@chimei.com', 'org': '11102-M'},
                {'id': 'I0002', 'name': '李建國', 'email': 'i0002@chimei.com', 'org': '11102-M'},
                {'id': 'I0003', 'name': '王美玲', 'email': 'i0003@chimei.com', 'org': '11103-C'},
            ]
            for u in users_data:
                if not HrAccount.query.get(u['id']):
                    user = HrAccount(id=u['id'], name=u['name'], email=u['email'], organizationid=u['org'])
                    user.set_password('1234')
                    db.session.add(user)

            # 6. 建立設備 (TEquipment) - 範例資料
            print("檢查馬達設備 (範例)...")
            equip_data_list = [
                {'id': 'MAE05D31', 'name': 'MAE05D31 真空泵浦馬達', 'asset': 'AST-M01', 'unit': 'A_RM_01'},
                {'id': 'MAE05D32', 'name': 'MAE05D32 冷卻泵浦馬達', 'asset': 'AST-M02', 'unit': 'A_RM_01'},
                {'id': 'MAE05D33', 'name': 'MAE05D33 抽風機馬達', 'asset': 'AST-M03', 'unit': 'A_RM_01'},
                {'id': 'COOL01', 'name': 'COOL01 主冷卻塔馬達', 'asset': 'AST-C01', 'unit': 'B_RM_01'},
                {'id': 'COOL02', 'name': 'COOL02 副冷卻塔馬達', 'asset': 'AST-C02', 'unit': 'B_RM_01'},
            ]
            for e in equip_data_list:
                if not TEquipment.query.get(e['id']):
                    db.session.add(TEquipment(id=e['id'], name=e['name'], assetid=e['asset'], unitid=e['unit']))
            
            db.session.commit()

            # 7. 建立通用檢查項目 (EquitCheckItem) - 範例資料/預設規格
            print("檢查通用檢查項目 (預設規格)...")
            # item_id 格式："{grade}_{mterm}_{sort_order}" 確保跨等級唯一，冪等性正確
            # 格式範例：A_1M_001, B_3M_011, D_4M_005
            specs_data = [
                ('001', '前軸承溫度', None, '70', '℃', 'A', '1M'), ('002', '馬達本體溫度', None, '80', '℃', 'A', '1M'),
                ('003', '後軸承溫度', None, '70', '℃', 'A', '1M'), ('004', 'MIH振動量測', None, '4', 'mm/s', 'A', '1M'),
                ('005', 'MIV振動量測', None, '4', 'mm/s', 'A', '1M'), ('006', 'MIA振動量測', None, '4', 'mm/s', 'A', '1M'),
                ('007', 'MOH振動量測', None, '4', 'mm/s', 'A', '1M'), ('008', 'MOV振動量測', None, '4', 'mm/s', 'A', '1M'),
                ('009', '馬達異響', '聲音項目', None, None, 'A', '1M'), ('010', '油位是否於正常範圍', '油位檢查(液壓油位)', None, None, 'A', '1M'),
                ('011', '注油', '注油(牛油)', None, None, 'A', '1M'),
                ('001', '前軸承溫度', None, '70', '℃', 'B', '1M'), ('002', '馬達本體溫度', None, '80', '℃', 'B', '1M'),
                ('003', '後軸承溫度', None, '70', '℃', 'B', '1M'), ('004', 'MIH振動量測', None, '4', 'mm/s', 'B', '1M'),
                ('005', 'MIV振動量測', None, '4', 'mm/s', 'B', '1M'), ('006', 'MIA振動量測', None, '4', 'mm/s', 'B', '1M'),
                ('007', 'MOH振動量測', None, '4', 'mm/s', 'B', '1M'), ('008', 'MOV振動量測', None, '4', 'mm/s', 'B', '1M'),
                ('009', '馬達異響', '聲音項目', None, None, 'B', '1M'), ('010', '油位是否於正常範圍', '油位檢查(液壓油位)', None, None, 'B', '1M'),
                ('011', '注油', '注油(牛油)', None, None, 'B', '3M'),
                ('001', '前軸承溫度', None, '70', '℃', 'C', '1M'), ('002', '馬達本體溫度', None, '80', '℃', 'C', '1M'),
                ('003', '後軸承溫度', None, '70', '℃', 'C', '1M'), ('004', 'MIH振動量測', None, '4', 'mm/s', 'C', '1M'),
                ('005', 'MIV振動量測', None, '4', 'mm/s', 'C', '1M'), ('006', 'MIA振動量測', None, '4', 'mm/s', 'C', '1M'),
                ('007', 'MOH振動量測', None, '4', 'mm/s', 'C', '1M'), ('008', 'MOV振動量測', None, '4', 'mm/s', 'C', '1M'),
                ('009', '馬達異響', '聲音項目', None, None, 'C', '1M'), ('010', '油位是否於正常範圍', '油位檢查(液壓油位)', None, None, 'C', '1M'),
                ('011', '注油', '注油(牛油)', None, None, 'C', '3M'),
                ('001', '前軸承溫度', None, '70', '℃', 'D', '4M'), ('002', '馬達本體溫度', None, '80', '℃', 'D', '4M'),
                ('003', '後軸承溫度', None, '70', '℃', 'D', '4M'), ('004', 'MIH振動量測', None, '4', 'mm/s', 'D', '4M'),
                ('005', 'MIV振動量測', None, '4', 'mm/s', 'D', '4M'), ('006', 'MIA振動量測', None, '4', 'mm/s', 'D', '4M'),
                ('007', 'MOH振動量測', None, '4', 'mm/s', 'D', '4M'), ('008', 'MOV振動量測', None, '4', 'mm/s', 'D', '4M'),
                ('009', '馬達異響', '聲音項目', None, None, 'D', '4M'), ('010', '油位是否於正常範圍', '油位檢查(液壓油位)', None, None, 'D', '4M'),
                ('011', '注油', '注油(牛油)', None, None, 'D', '4M')
            ]

            for row in specs_data:
                sort_order, item_name, item_desc, max_v, unit, grade, mterm = row
                # KEY FIX: item_id 用複合 key 確保各等級/週期的相同項目唯一
                item_id = f"{grade}_{mterm}_{sort_order}"
                if not EquitCheckItem.query.get(item_id):
                    status_type = 'status' if item_desc in ['聲音項目', '油位檢查(液壓油位)', '注油(牛油)'] else 'normal'
                    db.session.add(EquitCheckItem(
                        item_id=item_id, item_name=item_name, item_desc=item_desc,
                        sort_order=sort_order, max_v=max_v, unit=unit, grade=grade, mterm=mterm,
                        status_type=status_type
                    ))
            db.session.commit()

            # 8. 建立巡檢工單 (範例資料)
            if TJob.query.count() == 0:
                print("建立初始巡檢工單 (範例)...")
                inspectors = ['I0001', 'I0002', 'I0003']
                available_specs = [('A', '1M'), ('B', '1M'), ('B', '3M'), ('C', '1M'), ('C', '3M'), ('D', '4M')]
                task_count = 0
                equip_list = TEquipment.query.all()

                for m_off in [2, 1, 0]:
                    for eq in equip_list:
                        for d in [5, 20]:
                            task_date = get_dynamic_date(month_offset=m_off, day=d)
                            actid = f"JOB-{task_date}-{eq.id}"
                            if not TJob.query.filter_by(actid=actid, equipmentid=eq.id).first():
                                spec_grade, spec_mterm = random.choice(available_specs)
                                inspector_id = inspectors[task_count % len(inspectors)]
                                db.session.add(TJob(
                                    actid=actid, equipmentid=eq.id, mdate=task_date,
                                    act_desc=f"{eq.name} 例行巡檢 ({spec_mterm}) {spec_grade}級",
                                    act_key=f"K{task_date}{task_count:03d}",
                                    act_mem_id=inspector_id,
                                    act_mem=next((u['name'] for u in users_data if u['id'] == inspector_id), 'Admin'),
                                    grade=spec_grade, mterm=spec_mterm
                                ))
                                task_count += 1
                db.session.commit()

            # 9. 建立結果 (範例資料)
            if InspectionResult.query.count() == 0:
                print("填寫初始巡檢量測結果 (範例)...")
                today_str = date.today().strftime('%Y%m%d')
                past_jobs = TJob.query.filter(TJob.mdate < today_str).all()

                for job in past_jobs:
                    # item_id 格式已與步驟 7 對齊："{grade}_{mterm}_{sort_order}"
                    matched_items = EquitCheckItem.query.filter_by(grade=job.grade, mterm=job.mterm).all()
                    for item in matched_items:
                        measured = "正常"
                        # is_out_of_spec 語義：0=正常(在規格內), 2=異常(超標)
                        # 前端用 is_out_of_spec > 0 判斷是否異常，0=正常不顯示紅色
                        status = 0
                        if item.status_type == 'normal':
                            max_val = float(item.max_v) if item.max_v else 100.0
                            val = round(random.uniform(0.1, max_val * 0.9), 2) if random.random() > 0.1 else round(max_val * 1.2, 1)
                            status = 0 if val <= max_val else 2   # 0=正常, 2=異常
                            measured = str(val)
                        else:
                            if random.random() > 0.95:
                                measured = "異常"
                                status = 2

                        db.session.add(InspectionResult(
                            actid=job.actid, item_id=item.item_id, equipmentid=job.equipmentid,
                            measured_value=measured, is_out_of_spec=status,
                            act_mem_id=job.act_mem_id,
                            act_time=datetime.strptime(job.mdate, '%Y%m%d') + timedelta(hours=random.randint(9, 16))
                        ))

                # 先 commit InspectionResult，以滿足 AbnormalCases 的複合 FK 約束
                db.session.commit()
                print(f" - InspectionResult: {InspectionResult.query.count()} 筆")

                # 第二步：對異常結果建立 AbnormalCases 追蹤紀錄
                print("建立異常追蹤案件...")
                for job in past_jobs:
                    matched_items = EquitCheckItem.query.filter_by(grade=job.grade, mterm=job.mterm).all()
                    for item in matched_items:
                        result = InspectionResult.query.filter_by(
                            actid=job.actid, item_id=item.item_id
                        ).first()
                        if result and result.is_out_of_spec and result.is_out_of_spec > 0:
                            abn_msg = (
                                f"{item.item_name} 量測值 {result.measured_value} 超出上限 {item.max_v}"
                                if item.max_v else f"{item.item_name} 狀態異常"
                            )
                            db.session.add(AbnormalCases(
                                actid=job.actid,
                                item_id=item.item_id,
                                equipmentid=job.equipmentid,
                                measured_value=result.measured_value,
                                is_processed=False,
                                abn_msg=abn_msg
                            ))
                db.session.commit()

        print("\n" + "="*50)
        print("✅ 資料庫檢查與初始化成功！")
        if not skip_sample:
            print(f" - 組織: {HrOrganization.query.count()}")
            print(f" - 人員: {HrAccount.query.count()}")
            print(f" - 設備: {TEquipment.query.count()}")
            print(f" - 通用檢查項目: {EquitCheckItem.query.count()}")
            print(f" - 工單: {TJob.query.count()}")
            print(f" - 結果: {InspectionResult.query.count()}")
        else:
            print(" - 僅建立結構、角色與預設管理員。")
        print("="*50)


if __name__ == "__main__":
    init_database()
