
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from app import create_app
    from app.models import (
        SystemLog, UserLog
    )
    
    print("Successfully imported all models.")
    
    app = create_app()
    with app.app_context():
        print("Successfully created app context.")
        
        # Verify SystemLog fields
        print(f"SystemLog table: {SystemLog.__tablename__}")
        sys_log_cols = [c.name for c in SystemLog.__table__.columns]
        print(f"SystemLog columns: {sys_log_cols}")
        assert 'log_id' in sys_log_cols
        assert 'timestamp' in sys_log_cols
        assert 'level' in sys_log_cols
        assert 'module' in sys_log_cols
        
        # Verify UserLog fields
        print(f"UserLog table: {UserLog.__tablename__}")
        user_log_cols = [c.name for c in UserLog.__table__.columns]
        print(f"UserLog columns: {user_log_cols}")
        assert 'user_id' in user_log_cols
        assert 'timestamp' in user_log_cols
        assert 'changes' in user_log_cols
        
        print("Verification successful: All log fields are present.")
        
except Exception as e:
    print(f"Verification failed: {e}")
    import traceback
    traceback.print_exc()
