"""
Inspection Related Models
巡檢相關資料模型
"""
from app import db
from datetime import datetime


class TJob(db.Model):
    """巡檢工單模型 (t_job)"""
    __tablename__ = 't_job'
    
    actid = db.Column(db.String(48), primary_key=True, comment='工單ID')
    equipmentid = db.Column(db.String(48), db.ForeignKey('t_equipment.id'), comment='設備編號')
    mdate = db.Column(db.String(8), nullable=False, comment='開始日期')
    act_desc = db.Column(db.String(2000), comment='工單內容')
    act_key = db.Column(db.String(30), comment='工單編號')
    act_mem_id = db.Column(db.String(30), db.ForeignKey('hr_account.id'), comment='負責人ID')
    act_mem = db.Column(db.String(30), comment='負責人名稱')
    group = db.Column(db.String(8), comment='等級(ABCD)')
    mterm = db.Column(db.String(8), comment='頻率(1M, 3M)')
    
    # Relationships
    equipment = db.relationship('TEquipment', back_populates='jobs')
    results = db.relationship('InspectionResult', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    abnormal_cases = db.relationship('AbnormalCases', backref='job', lazy='dynamic', cascade='all, delete-orphan')
    assigned_user = db.relationship('HrAccount', foreign_keys=[act_mem_id], backref=db.backref('jobs', lazy='dynamic'))
    
    def __repr__(self):
        return f'<TJob {self.actid}>'
    
    def to_dict(self, include_results: bool = False):
        # Calculate status
        total_items = 0
        if self.equipment:
            total_items = self.equipment.check_items.count()
            
        completed_items = self.results.count()
        
        status = '未派工'
        if completed_items > 0:
            if completed_items >= total_items and total_items > 0:
                status = '已完成'
            else:
                status = '執行中'
        
        completion_rate = 0
        if total_items > 0:
            completion_rate = (completed_items / total_items) * 100

        data = {
            'actid': self.actid,
            'equipmentid': self.equipmentid,
            'equipment_name': self.equipment.name if self.equipment else None,
            'mdate': self.mdate, # already a string or date? Model says String(8).
            'act_desc': self.act_desc,
            'act_key': self.act_key,
            'act_mem_id': self.act_mem_id,
            'act_mem': self.act_mem,
            'act_mem_name': self.act_mem, # Alias for App compatibility
            'org_name': self.assigned_user.organization.name if self.assigned_user and self.assigned_user.organization else None,
            'group': self.group,
            'mterm': self.mterm,
            'status': status,
            'completion_rate': round(completion_rate, 1),
            'total_items': total_items,     # For App Progress Bar
            'completed_items': completed_items # For App Progress Bar
        }
        
        if include_results:
            data['results'] = [result.to_dict() for result in self.results]
        
        return data


class InspectionResult(db.Model):
    """巡檢結果模型 (inspection_result)"""
    __tablename__ = 'inspection_result'

    actid = db.Column(db.String(48), db.ForeignKey('t_job.actid'), primary_key=True, comment='工單ID')
    item_id = db.Column(db.String(48), db.ForeignKey('equit_check_item.item_id'), primary_key=True, comment='項目ID')
    equipmentid = db.Column(db.String(48), db.ForeignKey('t_equipment.id'), comment='設備編號')
    measured_value = db.Column(db.String(48), comment='量測值')
    act_mem_id = db.Column(db.String(30), db.ForeignKey('hr_account.id'), comment='負責人ID')
    act_time = db.Column(db.DateTime, comment='量測時間')
    result_photo = db.Column(db.String(2000), comment='照片位置')
    is_out_of_spec = db.Column(db.SmallInteger, comment='是否異常(0,1,2,3)')
    
    # Relationships are managed by the other side:
    # - check_item: defined via EquitCheckItem.inspection_results (backref='check_item')
    # - inspector: defined via HrAccount.inspection_results (backref='inspector')
    
    def __repr__(self):
        return f'<InspectionResult {self.actid} - {self.item_id}>'

    def to_dict(self):
        # Fetch associated abnormal case if any
        # Avoid circular import by importing here
        from app.models.Mortor_abnormal import AbnormalCases
        
        abnormal_case = AbnormalCases.query.filter_by(
            actid=self.actid, 
            item_id=self.item_id
        ).first()
        
        abnormal_reason = None
        is_processed = 0 # Default to 0 (False)
        solution = None
        processed_memid = None
        processed_time = None
        
        if abnormal_case:
            abnormal_reason = abnormal_case.abn_msg
            is_processed = 1 if abnormal_case.is_processed else 0
            solution = abnormal_case.abn_solution
            processed_memid = abnormal_case.processed_memid
            processed_time = abnormal_case.processed_time.isoformat() if abnormal_case.processed_time else None

        return {
            'actid': self.actid,
            'item_id': self.item_id,
            'equipmentid': self.equipmentid,
            'item_name': self.check_item.item_name if self.check_item else None,
            'measured_value': self.measured_value,
            'act_mem_id': self.act_mem_id,
            'act_time': self.act_time.strftime('%Y-%m-%d %H:%M:%S') if self.act_time else None,
            'result_photo': self.result_photo,
            'is_out_of_spec': self.is_out_of_spec,
            
            # Flattened Abnormal Fields for App
            'abnormal_reason': abnormal_reason,
            'is_processed': is_processed,
            'solution': solution,
            'processed_memid': processed_memid,
            'processed_time': processed_time
        }
