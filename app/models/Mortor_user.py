"""
User and Role Models
使用者與角色資料模型
"""
from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


class Role(db.Model):
    """角色模型 (預留功能，暫時停用前端管理介面)"""
    __tablename__ = 'roles'
    
    role_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    role_name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.String(255))
    
    def __repr__(self):
        return f'<Role {self.role_name}>'
    
    def to_dict(self):
        return {
            'role_id': self.role_id,
            'role_name': self.role_name,
            'description': self.description
        }


class HrAccount(UserMixin, db.Model):
    """使用者模型 (hr_account)"""
    __tablename__ = 'hr_account'
    
    id = db.Column(db.String(48), primary_key=True)
    name = db.Column(db.String(48), nullable=False)
    organizationid = db.Column(db.String(48), db.ForeignKey('hr_organization.id'))
    email = db.Column(db.String(384))
    password = db.Column(db.String(255))  # 加大長度以容納 hash
    
    # Relationships
    # - jobs: managed by TJob.assigned_user (backref='jobs')
    # - inspector/inspection_results: managed by EquitCheckItem side
    inspection_results = db.relationship('InspectionResult', backref='inspector', lazy='dynamic',
                                          foreign_keys='InspectionResult.act_mem_id')
    # - logs: managed by UserLog.user (backref='logs')
    
    def __repr__(self):
        return f'<HrAccount {self.id} - {self.name}>'
    
    def get_id(self):
        """Override UserMixin method for Flask-Login"""
        return str(self.id)
    
    def set_password(self, password: str) -> None:
        """設置密碼 (加密)"""
        self.password = generate_password_hash(password, method='pbkdf2:sha256')
    
    def check_password(self, password: str) -> bool:
        """驗證密碼"""
        if not self.password:
            return False
            
        # 兼容舊版系統/手動建檔的明文密碼
        # 如果資料庫中的密碼不是標準的 Werkzeug Hash 格式 (不包含 $ 符號或 pbkdf2)
        # 則退回使用直接明文比對
        if not self.password.startswith('pbkdf2:'):
            if self.password == password:
                # 若明文比對成功，代表這是一個舊的明文密碼。
                # 理論上應該在這裡自動把它升級成 Hash 並存回 DB，
                # 但為避免在單純讀取流程中觸發非預期的寫入，此處先維持相容性放行。
                return True
            return False
            
        return check_password_hash(self.password, password)
    
    def to_dict(self, include_sensitive: bool = False):
        """轉換為字典"""
        data = {
            'id': self.id,
            'name': self.name,
            'organizationid': self.organizationid,
            'org_name': self.organization.name if self.organization else None,
            'email': self.email,
        }
        
        if include_sensitive:
            data['password'] = self.password
        
        return data
    
    @staticmethod
    def create_default_admin():
        """創建預設管理員帳號"""
        admin = HrAccount.query.filter_by(id='admin').first()
        if not admin:
            admin = HrAccount(
                id='admin',
                name='系統管理員',
            )
            admin.set_password('1234qwer5T')
            db.session.add(admin)
            db.session.commit()
            return admin
        return None
