"""
Organization and Facility Models
組織與設施資料模型
"""
from app import db


class TOrganization(db.Model):
    """設施模型 (t_organization)"""
    __tablename__ = 't_organization'
    
    unitid = db.Column(db.String(48), primary_key=True)
    parentunitid = db.Column(db.String(48), db.ForeignKey('t_organization.unitid', deferrable=True, initially='DEFERRED'), nullable=True)
    unitname = db.Column(db.String(96), nullable=False)
    unittype = db.Column(db.String(48), nullable=False)
    
    # Self-referential relationship (樹狀結構)
    children = db.relationship(
        'TOrganization',
        backref=db.backref('parent', remote_side=[unitid]),
        lazy='dynamic'
    )
    
    # Relationships
    equipment = db.relationship('TEquipment', backref='facility', lazy='dynamic')
    
    def __repr__(self):
        return f'<TOrganization {self.unitname}>'
    
    def to_dict(self, include_children: bool = False, include_equipment: bool = False):
        data = {
            'unitid': self.unitid,
            'parentunitid': self.parentunitid,
            'unitname': self.unitname,
            'unittype': self.unittype,
        }
        
        if include_children:
            data['children'] = [child.to_dict(include_children=True) for child in self.children]
        
        if include_equipment:
            data['equipment_count'] = self.equipment.count()
            
        return data


class HrOrganization(db.Model):
    """組織模型 (hr_organization)"""
    __tablename__ = 'hr_organization'
    
    id = db.Column(db.String(48), primary_key=True)
    parentid = db.Column(db.String(48), db.ForeignKey('hr_organization.id', deferrable=True, initially='DEFERRED'), nullable=True)
    name = db.Column(db.String(96), nullable=False)
    
    # Self-referential relationship (樹狀結構)
    children = db.relationship(
        'HrOrganization',
        backref=db.backref('parent', remote_side=[id]),
        lazy='dynamic'
    )
    
    # Relationships
    users = db.relationship('HrAccount', backref='organization', lazy='dynamic')
    
    def __repr__(self):
        return f'<HrOrganization {self.name}>'
    
    def to_dict(self, include_children: bool = False):
        data = {
            'id': self.id,
            'parentid': self.parentid,
            'name': self.name
        }
        
        if include_children:
            data['children'] = [child.to_dict(include_children=True) for child in self.children]
            
        return data
