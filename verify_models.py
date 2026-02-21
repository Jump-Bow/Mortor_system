
import sys

# Add project root to path
sys.path.append('/Users/edward_hsieh/Cht/Projects/Chimei/fem-admin')

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
        assert 'message' in sys_log_cols
        assert 'exception' in sys_log_cols
        assert 'server_ip' in sys_log_cols
        
        # Verify UserLog fields
        print(f"UserLog table: {UserLog.__tablename__}")
        user_log_cols = [c.name for c in UserLog.__table__.columns]
        print(f"UserLog columns: {user_log_cols}")
        assert 'action_type' in user_log_cols
        assert 'ip_address' in user_log_cols
        assert 'user_agent' in user_log_cols
        assert 'status' in user_log_cols
        assert 'error_message' in user_log_cols
        
        print("Verification successful: All new log fields are present.")
        
except Exception as e:
    print(f"Verification failed: {e}")
    import traceback
    traceback.print_exc()
