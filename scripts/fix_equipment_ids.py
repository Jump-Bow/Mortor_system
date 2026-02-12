"""
Fix Equipment IDs in Inspection Tasks
修復巡檢任務中遺失的 equipmentid
"""
import os
import json
from app import create_app, db
from app.models.Mortor_inspection import TJob

def fix_equipment_ids():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # Go up one level to project root
    project_root = os.path.dirname(base_dir)
    mock_data_path = os.path.join(project_root, 'data', 'mock_data.json')
    
    if not os.path.exists(mock_data_path):
        print(f"Mock data file not found: {mock_data_path}")
        return

    app = create_app('development')
    
    with app.app_context():
        print("Loading mock data...")
        with open(mock_data_path, 'r', encoding='utf-8') as f:
            mock_data = json.load(f)
            
        print("Checking inspection tasks...")
        updated_count = 0
        
        for task_data in mock_data.get('inspection_tasks', []):
            actkey = task_data.get('task_number') or task_data.get('actkey')
            equipmentid = task_data.get('equipment_id') or task_data.get('equipmentid')
            
            if not actkey or not equipmentid:
                continue
                
            task = TJob.query.filter_by(actkey=actkey).first()
            if task:
                if not task.equipmentid:
                    print(f"Fixing task {actkey}: setting equipmentid to {equipmentid}")
                    task.equipmentid = equipmentid
                    updated_count += 1
                elif task.equipmentid != equipmentid:
                    print(f"Updating task {actkey}: changing equipmentid from {task.equipmentid} to {equipmentid}")
                    task.equipmentid = equipmentid
                    updated_count += 1
        
        if updated_count > 0:
            db.session.commit()
            print(f"Successfully updated {updated_count} tasks.")
        else:
            print("No tasks needed updating.")

if __name__ == '__main__':
    fix_equipment_ids()
