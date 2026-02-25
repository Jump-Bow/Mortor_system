"""
Equipment and Check Item Models
設備與檢查項目資料模型
"""
from app import db


class TEquipment(db.Model):
    """設備模型 (t_equipment)"""
    __tablename__ = 't_equipment'
    
    id = db.Column(db.String(48), primary_key=True)
    name = db.Column(db.String(96), nullable=False)
    assetid = db.Column(db.String(48), nullable=False)
    unitid = db.Column(db.String(48), db.ForeignKey('t_organization.unitid'))
    
    # Relationships
    jobs = db.relationship('TJob', back_populates='equipment', lazy='dynamic')
    
    def __repr__(self):
        return f'<TEquipment {self.id} - {self.name}>'
    
    def to_dict(self, include_items: bool = False):
        data = {
            'id': self.id,
            'name': self.name,
            'assetid': self.assetid,
            'unitid': self.unitid,
            'unitname': self.facility.unitname if self.facility else None,
        }
        
        if include_items:
            # 暫時保留空列表，或者根據新的業務邏輯填入通用項目
            data['check_items'] = [] 
        
        return data


class EquitCheckItem(db.Model):
    """設備檢查項目模型 (equit_check_item) - 通用檢查項目"""
    __tablename__ = 'equit_check_item'
    
    item_id = db.Column(db.String(48), primary_key=True, comment='項目ID')
    # equipmentid 已移除
    sort_order = db.Column(db.String(24), comment='顯示順序')
    item_name = db.Column(db.String(48), comment='項目名稱')
    item_desc = db.Column(db.String(2000), comment='項目備註')
    status_type = db.Column(db.String(48), comment='項目狀態')
    max_v = db.Column(db.String(48), comment='標準上限')
    min_v = db.Column(db.String(48), comment='標準下限')
    grade = db.Column(db.String(24), comment='等級(ABCD)') # Renamed from group
    mterm = db.Column(db.String(24), comment='頻率(1M, 3M)')
    unit = db.Column(db.String(24), comment='單位(mm, C)')
    
    # Relationships
    inspection_results = db.relationship('InspectionResult', backref='check_item', lazy='dynamic')
    
    def __repr__(self):
        return f'<EquitCheckItem {self.item_id} - {self.item_name}>'
    
    def to_dict(self):
        return {
            'item_id': self.item_id,
            'sort_order': self.sort_order,
            'item_name': self.item_name,
            'item_desc': self.item_desc,
            'status_type': self.status_type,
            'max_v': self.max_v,
            'min_v': self.min_v,
            'grade': self.grade, # Renamed
            'mterm': self.mterm,
            'unit': self.unit
        }
