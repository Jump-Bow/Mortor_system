"""
System and User Log Models
系統與使用者日誌資料模型
"""
from app import db
from datetime import datetime
import uuid


class SystemLog(db.Model):
    """系統日誌模型 (sys_log)"""
    __tablename__ = 'sys_log'
    
    log_id = db.Column(db.String(48), primary_key=True, comment='Log ID')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True, comment='時間')
    level = db.Column(db.String(48), nullable=False, comment='INFO/WARN/ERROR')  
    module = db.Column(db.String(48), comment='模組名稱')
    
    def __repr__(self):
        return f'<SystemLog {self.log_id} - {self.level}>'
    
    def to_dict(self):
        return {
            'log_id': self.log_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'level': self.level,
            'module': self.module,
        }
        
    @staticmethod
    def create(level: str, module: str, message: str = None, exception: str = None):
        """建立系統日誌"""
        try:
            log = SystemLog(
                log_id=str(uuid.uuid4()),
                level=level,
                module=module,
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            print(f"Error creating system log: {e}")
            return None


class UserLog(db.Model):
    """使用者操作日誌模型 (user_log)"""
    __tablename__ = 'user_log'
    
    # Note: user_action_log used `id` (int PK), DB_SCHEMA says nothing about PK but usually implicit.
    # However, DB_SCHEMA.txt for user_log shows:
    # user_id FK, timestamp, changes.
    # It does NOT show a PK. But SQLAlchemy needs a PK.
    # I will keep a surrogate PK `id` but rename proper fields.
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.String(48), db.ForeignKey('hr_account.id'), comment='操作者ID')
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True, comment='執行時間')
    changes = db.Column(db.Text, comment='操作紀錄')
    
    # Relationship
    user = db.relationship('HrAccount', backref='logs')
    
    def __repr__(self):
        return f'<UserLog {self.id} - {self.user_id}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'changes': self.changes,
        }
        
    @staticmethod
    def log_action(user_id: str, action_type: str, description: str, ip_address: str = None, status: str = 'SUCCESS', error_message: str = None):
        """記錄使用者操作"""
        try:
            changes_parts = []
            if action_type:
                changes_parts.append(f"[{action_type}]")
            if description:
                changes_parts.append(description)
            if status and status != 'SUCCESS':
                changes_parts.append(f"(狀態: {status})")
            if error_message:
                changes_parts.append(f"錯誤: {error_message}")
            if ip_address:
                changes_parts.append(f"IP: {ip_address}")
                
            changes_text = ' | '.join(changes_parts)
            
            log = UserLog(
                user_id=user_id,
                changes=changes_text,
            )
            db.session.add(log)
            db.session.commit()
            return log
        except Exception as e:
            db.session.rollback()
            print(f"Error logging user action: {e}")
            return None
