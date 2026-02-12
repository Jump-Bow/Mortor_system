"""
Database Initialization Script
初始化資料庫並建立預設資料
"""
import os
import random
from datetime import datetime, timedelta, date
from app import create_app, db
from app.models.Mortor_user import HrAccount, Role
from app.models.Mortor_organization import HrOrganization, TOrganization
from app.models.Mortor_equipment import TEquipment, EquitCheckItem
from app.models.Mortor_inspection import TJob, InspectionResult
from app.models.Mortor_abnormal import AbnormalCases
from app.models.Mortor_system_log import SysLog, UserLog


def init_database():
    """初始化資料庫"""
    # 確保必要的目錄存在
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    logs_dir = os.path.join(base_dir, 'logs')
    uploads_dir = os.path.join(base_dir, 'uploads', 'photos')
    
    for directory in [data_dir, logs_dir, uploads_dir]:
        if not os.path.exists(directory):
            os.makedirs(directory)
            print(f"✓ Created directory: {directory}")
    
    app = create_app('development')
    
    with app.app_context():
        print("Dropping all tables...")
        db.drop_all()
        print("✓ All tables dropped")
        
        print("Creating database tables...")
        db.create_all()
        print("✓ Database tables created successfully")
        
        # Create roles (預留功能)
        print("\nCreating roles (reserved)...")
        roles_data = [
            {'role_name': '管理者', 'description': '系統管理員，擁有完整權限'},
            {'role_name': '巡檢人員', 'description': '執行巡檢任務的現場人員'},
            {'role_name': '查詢人員', 'description': '僅能查詢資料的人員'}
        ]
        
        for role_data in roles_data:
            if not Role.query.filter_by(role_name=role_data['role_name']).first():
                role = Role(**role_data)
                db.session.add(role)
                print(f"  ✓ Created role: {role_data['role_name']}")
        
        db.session.commit()
        
        # Create default admin user
        print("\nCreating default admin user...")
        HrAccount.create_default_admin()
        print("  ✓ Admin user created (id: admin, password: 1234qwer5T)")
        
        # Create sample users
        print("\nCreating sample users...")
        sample_users = [
            {
                'id': 'I0001',
                'name': '張文雄',
                'password': 'password123',
                'email': 'i0001@chimei.com',
            },
            {
                'id': 'I0002',
                'name': '李建國',
                'password': 'password123',
                'email': 'i0002@chimei.com',
            },
            {
                'id': 'I0003',
                'name': '王美玲',
                'password': 'password123',
                'email': 'i0003@chimei.com',
            }
        ]
        
        for user_data in sample_users:
            if not HrAccount.query.get(user_data['id']):
                password = user_data.pop('password')
                user = HrAccount(**user_data)
                user.set_password(password)
                db.session.add(user)
                print(f"  ✓ Created user: {user_data['id']} - {user_data['name']}")
        
        db.session.commit()
        
        # Create organizations (hr_organization)
        print("\nCreating organizations...")
        orgs_data = [
            {'id': 'CORP', 'name': '奇美實業', 'parentid': None},
            {'id': '11102', 'name': '行政處', 'parentid': 'CORP'},
            {'id': '11102-MOTOR', 'name': '行政處-馬達巡檢', 'parentid': '11102'},
            {'id': '11103', 'name': '生產處', 'parentid': 'CORP'},
            {'id': '11103-COOLING', 'name': '生產處-冷卻系統', 'parentid': '11103'},
        ]
        
        for org_data in orgs_data:
            if not HrOrganization.query.get(org_data['id']):
                # Filter out unexpected keys if any, though here we constructed them manually
                safe_data = {k: v for k, v in org_data.items() if k in ['id', 'name', 'parentid']}
                org = HrOrganization(**safe_data)
                db.session.add(org)
                print(f"  ✓ Created organization: {org_data['name']}")
        
        db.session.commit()
        
        # Create facilities (t_organization)
        print("\nCreating facilities...")
        facilities_data = [
            {'unitid': 'PLANT_A', 'unitname': 'A廠區', 'unittype': 'Plant', 'parentunitid': None},
            {'unitid': 'PLANT_B', 'unitname': 'B廠區', 'unittype': 'Plant', 'parentunitid': None},
            {'unitid': 'BUILDING_A1', 'unitname': 'A1廠房', 'unittype': 'Building', 'parentunitid': 'PLANT_A'},
            {'unitid': 'BUILDING_B1', 'unitname': 'B1廠房', 'unittype': 'Building', 'parentunitid': 'PLANT_B'},
            {'unitid': 'FLOOR_A1_1F', 'unitname': 'A1廠房-1樓', 'unittype': 'Floor', 'parentunitid': 'BUILDING_A1'},
            {'unitid': 'FLOOR_B1_2F', 'unitname': 'B1廠房-2樓', 'unittype': 'Floor', 'parentunitid': 'BUILDING_B1'},
            {'unitid': 'AREA_MOTOR_ROOM', 'unitname': '馬達機房', 'unittype': 'Area', 'parentunitid': 'FLOOR_A1_1F'},
            {'unitid': 'AREA_COOLING_ROOM', 'unitname': '冷卻系統機房', 'unittype': 'Area', 'parentunitid': 'FLOOR_B1_2F'},
        ]
        
        for facility_data in facilities_data:
            if not TOrganization.query.get(facility_data['unitid']):
                facility = TOrganization(**facility_data)
                db.session.add(facility)
                print(f"  ✓ Created facility: {facility_data['unitname']}")
        
        db.session.commit()
        
        # Create equipment (t_equipment)
        print("\nCreating equipment...")
        equipment_data_list = [
            {'id': 'MAE05D31', 'name': 'MAE05D31 V2真空泵浦馬達', 'unitid': 'AREA_MOTOR_ROOM', 'assetid': 'AST-001'},
            {'id': 'MAE05D32', 'name': 'MAE05D32 冷卻泵浦馬達', 'unitid': 'AREA_MOTOR_ROOM', 'assetid': 'AST-002'},
            {'id': 'MAE05D33', 'name': 'MAE05D33 抽風機馬達', 'unitid': 'AREA_MOTOR_ROOM', 'assetid': 'AST-003'},
            {'id': 'COOL01', 'name': 'COOL01 主冷卻塔', 'unitid': 'AREA_COOLING_ROOM', 'assetid': 'AST-004'},
            {'id': 'COOL02', 'name': 'COOL02 副冷卻塔', 'unitid': 'AREA_COOLING_ROOM', 'assetid': 'AST-005'},
        ]
        
        for equip_data in equipment_data_list:
            if not TEquipment.query.get(equip_data['id']):
                equipment = TEquipment(**equip_data)
                db.session.add(equipment)
                print(f"  ✓ Created equipment: {equip_data['name']}")
        
        try:
            db.session.commit()
        except Exception as e:
            print(f"Error creating equipment: {e}")
            db.session.rollback()
            raise e
        
        # Create check items (equit_check_item)
        print("\nCreating check items...")
        check_items_data = [
            # MAE05D31
            {'item_id': 'MAE05D31-C01', 'equipmentid': 'MAE05D31', 'item_name': '前軸承溫度', 'sort_order': 1, 'max_v': '70.0', 'min_v': '30.0', 'group': 'A', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'MAE05D31-C02', 'equipmentid': 'MAE05D31', 'item_name': '馬達本體溫度', 'sort_order': 2, 'max_v': '80.0', 'min_v': '35.0', 'group': 'A', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'MAE05D31-C03', 'equipmentid': 'MAE05D31', 'item_name': '後軸承溫度', 'sort_order': 3, 'max_v': '70.0', 'min_v': '30.0', 'group': 'A', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'MAE05D31-C04', 'equipmentid': 'MAE05D31', 'item_name': '運轉電流', 'sort_order': 4, 'max_v': '4.0', 'min_v': '2.5', 'group': 'A', 'mterm': '1M', 'unit': 'A', 'status_type': 'normal'},
            {'item_id': 'MAE05D31-C05', 'equipmentid': 'MAE05D31', 'item_name': '軸承潤滑油', 'sort_order': 5, 'max_v': None, 'min_v': None, 'group': 'A', 'mterm': '1M', 'unit': None, 'status_type': 'normal'},
            # MAE05D32
            {'item_id': 'MAE05D32-C01', 'equipmentid': 'MAE05D32', 'item_name': '前軸承溫度', 'sort_order': 1, 'max_v': '70.0', 'min_v': '30.0', 'group': 'A', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'MAE05D32-C02', 'equipmentid': 'MAE05D32', 'item_name': '馬達本體溫度', 'sort_order': 2, 'max_v': '80.0', 'min_v': '35.0', 'group': 'A', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'MAE05D32-C03', 'equipmentid': 'MAE05D32', 'item_name': '振動值', 'sort_order': 3, 'max_v': '5.0', 'min_v': '0.0', 'group': 'A', 'mterm': '1M', 'unit': 'mm/s', 'status_type': 'normal'},
            # MAE05D33
            {'item_id': 'MAE05D33-C01', 'equipmentid': 'MAE05D33', 'item_name': '馬達溫度', 'sort_order': 1, 'max_v': '75.0', 'min_v': '30.0', 'group': 'A', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'MAE05D33-C02', 'equipmentid': 'MAE05D33', 'item_name': '風扇轉速', 'sort_order': 2, 'max_v': '1500', 'min_v': '1200', 'group': 'A', 'mterm': '1M', 'unit': 'RPM', 'status_type': 'normal'},
            # COOL01
            {'item_id': 'COOL01-C01', 'equipmentid': 'COOL01', 'item_name': '進水溫度', 'sort_order': 1, 'max_v': '35.0', 'min_v': '15.0', 'group': 'B', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'COOL01-C02', 'equipmentid': 'COOL01', 'item_name': '出水溫度', 'sort_order': 2, 'max_v': '30.0', 'min_v': '10.0', 'group': 'B', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'COOL01-C03', 'equipmentid': 'COOL01', 'item_name': '水壓', 'sort_order': 3, 'max_v': '5.0', 'min_v': '2.0', 'group': 'B', 'mterm': '1M', 'unit': 'kg/cm2', 'status_type': 'normal'},
            # COOL02
            {'item_id': 'COOL02-C01', 'equipmentid': 'COOL02', 'item_name': '進水溫度', 'sort_order': 1, 'max_v': '35.0', 'min_v': '15.0', 'group': 'B', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
            {'item_id': 'COOL02-C02', 'equipmentid': 'COOL02', 'item_name': '出水溫度', 'sort_order': 2, 'max_v': '30.0', 'min_v': '10.0', 'group': 'B', 'mterm': '1M', 'unit': 'C', 'status_type': 'normal'},
        ]
        
        for item_data in check_items_data:
            if not EquitCheckItem.query.get(item_data['item_id']):
                item = EquitCheckItem(**item_data)
                db.session.add(item)
                print(f"  ✓ Created check item: {item_data['equipmentid']} - {item_data['item_name']}")
        
        db.session.commit()
        
        # Create inspection tasks (t_job) for Oct, Nov, Dec 2025
        print("\nCreating inspection tasks for Oct-Dec 2025...")
        
        all_equipment = TEquipment.query.all()
        inspectors = ['I0001', 'I0002', 'I0003']
        
        task_counter = 1
        for month in [10, 11, 12]:
            days = 31 if month in [10, 12] else 30
            
            for day in range(1, days + 1, 3):
                for equipment in all_equipment:
                    task_date = date(2025, month, day)
                    date_str = task_date.strftime('%Y%m%d')
                    actkey = f"TASK{date_str}{task_counter:03d}"
                    actid = actkey
                    
                    assigned_to = inspectors[task_counter % len(inspectors)]
                    assigned_name = next((u['name'] for u in sample_users if u['id'] == assigned_to), 'Unknown')
                    
                    if not TJob.query.get(actid):
                        task = TJob(
                            actid=actid,
                            act_key=actkey,
                            equipmentid=equipment.id,
                            act_mem_id=assigned_to,
                            act_mem=assigned_name,
                            mdate=date_str,
                            group='A',
                            mterm='1M'
                        )
                        db.session.add(task)
                        print(f"  ✓ Created task: {actkey} - {equipment.name} ({date_str})")
                    
                    task_counter += 1
        
        db.session.commit()
        
        # Create inspection results for past tasks
        print("\nCreating inspection results...")
        
        today = datetime.now().date()
        today_str = today.strftime('%Y%m%d')
        past_tasks = TJob.query.filter(TJob.mdate < today_str).all()
        result_counter = 0
        
        for task in past_tasks:
            check_items = EquitCheckItem.query.filter_by(equipmentid=task.equipmentid).all()
            
            for item in check_items:
                if not InspectionResult.query.filter_by(actid=task.actid, item_id=item.item_id).first():
                    measured_value = '正常'
                    is_out_of_spec = 1
                    
                    if item.max_v and item.min_v:
                        try:
                            lower = float(item.min_v)
                            upper = float(item.max_v)
                            
                            if upper > 0 and lower >= 0:
                                if random.random() < 0.8:  # 80% normal
                                    measured_value = str(round(lower + (upper - lower) * random.uniform(0.3, 0.7), 1))
                                    is_out_of_spec = 1  # 正常
                                else:  # 20% abnormal
                                    if random.random() < 0.5:
                                        measured_value = str(round(upper + random.uniform(1, 5), 1))
                                    else:
                                        measured_value = str(round(max(0, lower - random.uniform(1, 3)), 1))
                                    is_out_of_spec = 2  # 異常
                            else:
                                measured_value = '正常'
                                is_out_of_spec = 1
                        except ValueError:
                            measured_value = '正常'
                            is_out_of_spec = 1
                    
                    # Convert task.mdate string back to date object for adding time
                    task_date_obj = datetime.strptime(task.mdate, '%Y%m%d').date()
                    
                    act_time = datetime.combine(
                        task_date_obj,
                        datetime.min.time()
                    ) + timedelta(hours=random.randint(8, 17), minutes=random.randint(0, 59))
                    
                    result = InspectionResult(
                        actid=task.actid,
                        item_id=item.item_id,
                        equipmentid=task.equipmentid,
                        measured_value=measured_value,
                        is_out_of_spec=is_out_of_spec,
                        act_time=act_time,
                        act_mem_id=task.act_mem_id
                    )
                    db.session.add(result)
                    result_counter += 1
        
        db.session.commit()
        print(f"  ✓ Created {result_counter} inspection results")
        
        print("\n" + "="*60)
        print("Database initialization completed successfully!")
        print("="*60)
        
        # Print statistics
        print("\nDatabase Statistics:")
        print(f"  HR Organizations: {HrOrganization.query.count()}")
        print(f"  Facilities (TOrganization): {TOrganization.query.count()}")
        print(f"  Equipment: {TEquipment.query.count()}")
        print(f"  Check Items: {EquitCheckItem.query.count()}")
        print(f"  Users: {HrAccount.query.count()}")
        print(f"  Inspection Tasks: {TJob.query.count()}")
        print(f"  Inspection Results: {InspectionResult.query.count()}")
        
        print("\n" + "="*60)
        print("Default credentials:")
        print("  User ID: admin")
        print("  Password: 1234qwer5T")
        print("\nSample users:")
        print("  User ID: I0001 / I0002 / I0003")
        print("  Password: password123")
        print("="*60)


if __name__ == '__main__':
    init_database()
