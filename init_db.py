"""
Database Initialization Script (Self-contained Sample Data)
初始化資料庫並建立完整的固定測試資料
"""
import os
import random
from datetime import datetime, timedelta, date
from app import create_app, db
from app.models.Mortor_user import HrAccount, Role
from app.models.Mortor_organization import HrOrganization, TOrganization
from app.models.Mortor_equipment import TEquipment, EquitCheckItem
from app.models.Mortor_inspection import TJob, InspectionResult

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
    """初始化資料庫並建立固定測試資料"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    uploads_dir = os.path.join(base_dir, 'uploads', 'photos')
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)
        print(f"Created directory: {uploads_dir}")

    env = os.getenv('FLASK_ENV', 'development')
    app = create_app(env)

    with app.app_context():
        print("--- 清空資料庫 ---")
        db.drop_all()
        db.create_all()

        # 1. 建立角色
        print("建立角色...")
        roles = [
            Role(role_name='管理者', description='系統管理員'),
            Role(role_name='巡檢人員', description='現場執行人員'),
            Role(role_name='查詢人員', description='報表查詢人員')
        ]
        db.session.add_all(roles)

        # 2. 建立組織 (HrOrganization)
        print("建立組織架構...")
        orgs = [
            HrOrganization(id='CORP', name='奇美實業', parentid=None),
            HrOrganization(id='11102', name='行政處', parentid='CORP'),
            HrOrganization(id='11102-M', name='馬達巡檢課', parentid='11102'),
            HrOrganization(id='11103', name='生產處', parentid='CORP'),
            HrOrganization(id='11103-C', name='冷卻系統課', parentid='11103'),
        ]
        db.session.add_all(orgs)

        # 3. 建立場域 (TOrganization)
        print("建立廠區場域...")
        facilities = [
            TOrganization(unitid='PLANT_A', unitname='A廠區', unittype='Plant'),
            TOrganization(unitid='PLANT_B', unitname='B廠區', unittype='Plant'),
            TOrganization(unitid='A_RM_01', unitname='A1廠馬達機房', unittype='Area', parentunitid='PLANT_A'),
            TOrganization(unitid='B_RM_01', unitname='B1廠冷卻機房', unittype='Area', parentunitid='PLANT_B'),
        ]
        db.session.add_all(facilities)

        # 4. 建立人員 (HrAccount)
        print("建立測試帳號...")
        users_data = [
            {'id': 'I0001', 'name': '張文雄', 'email': 'i0001@chimei.com', 'org': '11102-M'},
            {'id': 'I0002', 'name': '李建國', 'email': 'i0002@chimei.com', 'org': '11102-M'},
            {'id': 'I0003', 'name': '王美玲', 'email': 'i0003@chimei.com', 'org': '11103-C'},
        ]
        for u in users_data:
            user = HrAccount(id=u['id'], name=u['name'], email=u['email'], organizationid=u['org'])
            user.set_password('1234')
            db.session.add(user)
        
        # 預設管理員
        HrAccount.create_default_admin()

        # 5. 建立設備 (TEquipment)
        print("建立馬達設備...")
        equip_list = [
            TEquipment(id='MAE05D31', name='MAE05D31 真空泵浦馬達', assetid='AST-M01', unitid='A_RM_01'),
            TEquipment(id='MAE05D32', name='MAE05D32 冷卻泵浦馬達', assetid='AST-M02', unitid='A_RM_01'),
            TEquipment(id='MAE05D33', name='MAE05D33 抽風機馬達', assetid='AST-M03', unitid='A_RM_01'),
            TEquipment(id='COOL01', name='COOL01 主冷卻塔馬達', assetid='AST-C01', unitid='B_RM_01'),
            TEquipment(id='COOL02', name='COOL02 副冷卻塔馬達', assetid='AST-C02', unitid='B_RM_01'),
        ]
        db.session.add_all(equip_list)
        db.session.commit()

        # 6. 建立通用檢查項目 (EquitCheckItem) - 完整規格
        print("建立通用檢查項目 (完整規格)...")
        # 資料來源: extract_and_transform.py get_specs_df
        # 格式: (sort_order, item_name, item_desc, max_v, unit, grade, mterm)
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
        
        items = []
        for idx, row in enumerate(specs_data, 1):
            sort_order, item_name, item_desc, max_v, unit, grade, mterm = row
            
            # Determine status_type
            if item_desc in ['聲音項目', '油位檢查(液壓油位)', '注油(牛油)']:
                status_type = 'status'
            else:
                status_type = 'normal'
                
            items.append(EquitCheckItem(
                item_id=str(idx), # check_item_id as item_id
                item_name=item_name,
                item_desc=item_desc,
                sort_order=sort_order,
                max_v=max_v,
                min_v=None, # Source data has no min_v defined
                unit=unit,
                grade=grade, # Renamed
                mterm=mterm,
                status_type=status_type
            ))
            
        db.session.add_all(items)
        db.session.commit()

        # 7. 建立巡檢工單 (TJob) - 隨機分配 Grade 與 Mterm
        print("建立最近三個月的巡檢工單...")
        inspectors = ['I0001', 'I0002', 'I0003']
        task_count = 0
        
        # 定義可用的 Grade 與 Mterm 組合 (參考 specs_data)
        available_specs = [
            ('A', '1M'), ('B', '1M'), ('B', '3M'), ('C', '1M'), ('C', '3M'), ('D', '4M')
        ]
        
        for m_off in [2, 1, 0]: # 最近三個月
            for eq in equip_list:
                for d in [5, 20]:
                    task_date = get_dynamic_date(month_offset=m_off, day=d)
                    actid = f"JOB-{task_date}-{eq.id}"
                    
                    if not TJob.query.get(actid):
                        # 隨機選擇工單的 Grade 和 Mterm
                        spec_grade, spec_mterm = random.choice(available_specs)
                        
                        inspector_id = inspectors[task_count % len(inspectors)]
                        job = TJob(
                            actid=actid,
                            equipmentid=eq.id,
                            mdate=task_date,
                            act_desc=f"{eq.name} 例行巡檢 ({spec_mterm}) {spec_grade}級", # 模擬 ACT_DESC 格式
                            act_key=f"K{task_date}{task_count:03d}",
                            act_mem_id=inspector_id,
                            act_mem=next(u['name'] for u in users_data if u['id'] == inspector_id),
                            grade=spec_grade, # Renamed
                            mterm=spec_mterm
                        )
                        db.session.add(job)
                        task_count += 1
        
        db.session.commit()

        # 8. 建立模擬量測結果 (InspectionResult) - 依據 Grade/Mterm 匹配
        print("填寫模擬巡檢量測結果 (依據規格匹配)...")
        today_str = date.today().strftime('%Y%m%d')
        past_jobs = TJob.query.filter(TJob.mdate < today_str).all()
        
        result_count = 0
        for job in past_jobs:
            # 只找出符合該工單 Grade 和 Mterm 的檢查項目
            matched_items = EquitCheckItem.query.filter_by(
                grade=job.grade, # Renamed
                mterm=job.mterm
            ).all()
            
            for item in matched_items:
                status = 1
                measured = "正常"
                
                if item.status_type == 'normal':
                    try:
                        # 處理數值型項目的模擬值
                        max_val = float(item.max_v) if item.max_v else 100.0
                        min_val = float(item.min_v) if item.min_v else 0.0
                        
                        if random.random() > 0.1: # 90% 機率正常
                            safe_min = min_val
                            safe_max = max_val
                            
                            # 針對振動 (通常 max=4)
                            if safe_max < 10:
                                val = round(random.uniform(0.1, safe_max * 0.9), 2)
                            else:
                                val = round(random.uniform(safe_min, safe_max), 1)
                            status = 1
                        else: # 10% 機率異常
                            if item.max_v:
                                val = round(float(item.max_v) * 1.2, 1)
                            else:
                                val = 999
                            status = 2
                        
                        measured = str(val)
                    except Exception:
                        measured = "0"
                        status = 1
                else:
                    # 狀態型項目
                    if random.random() > 0.95: # 5% 機率異常
                        measured = "異常"
                        status = 2
                    else:
                        measured = "正常"
                        status = 1
                
                res = InspectionResult(
                    actid=job.actid,
                    item_id=item.item_id,
                    equipmentid=job.equipmentid,
                    measured_value=measured,
                    is_out_of_spec=status,
                    act_mem_id=job.act_mem_id,
                    act_time=datetime.strptime(job.mdate, '%Y%m%d') + timedelta(hours=random.randint(9, 16))
                )
                db.session.add(res)
                result_count += 1
        
        db.session.commit()

        print("\n" + "="*50)
        print("✅ 測試資料庫初始化成功！")
        print(f" - 組織: {HrOrganization.query.count()}")
        print(f" - 人員: {HrAccount.query.count()}")
        print(f" - 設備: {TEquipment.query.count()}")
        print(f" - 通用檢查項目: {EquitCheckItem.query.count()} (完整規格表)")
        print(f" - 工單: {TJob.query.count()} (隨機分配 Grade/Mterm)")
        print(f" - 結果: {InspectionResult.query.count()} 筆 (僅生成匹配項目)")
        print("="*50)

if __name__ == "__main__":
    init_database()
