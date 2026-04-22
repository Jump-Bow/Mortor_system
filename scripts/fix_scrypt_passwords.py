import os
import sys
import sqlalchemy as sa
from werkzeug.security import generate_password_hash

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app

def fix_passwords():
    print("🚀 開始修復 scrypt 密碼雜湊為 pbkdf2:sha256...")
    env = os.getenv("FLASK_ENV", "production")
    app = create_app(env)
    
    with app.app_context():
        from app import db
        
        # 找出所有使用 scrypt 雜湊的帳號
        users = db.session.execute(
            sa.text("SELECT id FROM hr_account WHERE password LIKE 'scrypt:%'")
        ).fetchall()
        
        if not users:
            print("✅ 找不到需要修復的帳號，所有密碼格式皆正常。")
            return
            
        print(f"⚠️ 發現 {len(users)} 筆使用 scrypt 雜湊的帳號，正在進行重置...")
        
        for row in users:
            uid = row[0]
            new_hash = generate_password_hash(str(uid), method='pbkdf2:sha256')
            db.session.execute(
                sa.text("UPDATE hr_account SET password = :pwd WHERE id = :uid"),
                {"pwd": new_hash, "uid": uid}
            )
            
        db.session.commit()
        print(f"✅ 成功修復 {len(users)} 筆帳號的密碼！您現在可以使用員工編號進行登入了。")

if __name__ == "__main__":
    fix_passwords()
