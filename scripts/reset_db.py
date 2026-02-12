"""
資料庫重置腳本
刪除舊資料庫並重新建立
"""
import os
import sys

# 將專案根目錄加入 sys.path 以便導入模組
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

def reset_database():
    """重置資料庫"""
    # 資料庫檔案路徑 (在專案根目錄的 data 資料夾)
    db_files = [
        os.path.join(project_root, 'data', 'fem_dev.db'),
        os.path.join(project_root, 'data', 'my_database.db')
    ]
    
    # 刪除舊的資料庫檔案
    print("🗑️  正在刪除舊資料庫檔案...")
    for db_file in db_files:
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"   ✓ 已刪除: {db_file}")
        else:
            print(f"   - 不存在: {db_file}")
    
    # 執行資料庫初始化
    print("\n🔨 正在重新建立資料庫...")
    # 切換工作目錄到專案根目錄，確保 init_db 能正確執行
    os.chdir(project_root)
    from init_db import init_database
    init_database()
    
    print("\n✅ 資料庫重置完成!")
    print("\n預設管理員帳號:")
    print("   帳號: admin")
    print("   密碼: 1234qwer5T")


if __name__ == '__main__':
    confirm = input("⚠️  確定要重置資料庫嗎？所有資料將被刪除！(yes/no): ")
    if confirm.lower() in ['yes', 'y']:
        reset_database()
    else:
        print("❌ 已取消操作")
