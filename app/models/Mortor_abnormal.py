"""
Abnormal Cases Model
異常追蹤資料模型
"""
from app import db


class AbnormalCases(db.Model):
    """異常追蹤模型 (abnormal_cases) - is_processed 加索引供 dashboard 統計"""
    __tablename__ = 'abnormal_cases'
    
    actid = db.Column(db.String(48), db.ForeignKey('t_job.actid'), primary_key=True, comment='工單ID')
    equipmentid = db.Column(db.String(48), db.ForeignKey('t_equipment.id'), comment='設備編號')
    item_id = db.Column(db.String(48), db.ForeignKey('equit_check_item.item_id'), primary_key=True, comment='項目ID')
    measured_value = db.Column(db.String(48), comment='量測值')
    is_processed = db.Column(db.Boolean, default=False, index=True, comment='是否處理')  # dashboard 統計常用
    abn_msg = db.Column(db.String(2000), comment='異常內容')
    abn_solution = db.Column(db.String(2000), comment='處理方式')
    processed_memid = db.Column(db.String(48), db.ForeignKey('hr_account.id'), comment='處理人員')
    processed_time = db.Column(db.DateTime, comment='更新時間')
    
    # Relationships
    responsible_user = db.relationship('HrAccount', foreign_keys=[processed_memid])
    
    # Composite foreign key relationship to InspectionResult
    __table_args__ = (
        db.ForeignKeyConstraint(
            ['actid', 'item_id'],
            ['inspection_result.actid', 'inspection_result.item_id']
        ),
    )
    
    def __repr__(self):
        return f'<AbnormalCases {self.actid} - {self.item_id}>'
    
    def to_dict(self):
        # Determine abnormal type from related result if possible
        # We need to query InspectionResult but we don't have direct relationship easily accessible here without query
        # But we added Foreign Key Constraint.
        # Let's assume we can add a relationship or just query it.
        # Actually, let's look at the class definition again. We didn't define relationship to InspectionResult directly?
        # We have __table_args__. 
        # But we can use db.session query if needed, or add relationship. 
        # For efficiency, adding relationship is better.
        # But let's leave it for now and try to infer or use placeholder.
        # Wait, app/api/Mortor_inspection.py query_abnormal_tracking joins InspectionResult!
        # So we can fetch it there.
        # But here in to_dict we might not have it.
        # Let's just return basic info here and let API enrich it if needed, OR add fields.
        
        # 'tracking_id': Use actid + item_id hash or concatenation?
        tracking_id = f"{self.actid}_{self.item_id}"
        
        return {
            'actid': self.actid,
            'equipmentid': self.equipmentid,
            'item_id': self.item_id,
            'measured_value': self.measured_value,
            'is_processed': self.is_processed,
            'case_status': '已結案' if self.is_processed else '未結案',
            'abn_msg': self.abn_msg,
            'abn_solution': self.abn_solution,
            'processed_memid': self.processed_memid,
            'processed_memname': self.responsible_user.name if self.responsible_user else (self.processed_memid if self.processed_memid else '未指派'),
            'processed_time': self.processed_time.isoformat() if self.processed_time else None,
            'tracking_id': tracking_id,
            # abnormal_type will be enriched by API
        }
