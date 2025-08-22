import os
import stat
import time
import glob

def fix_all_permissions():
    """Fix permissions for all session and database files"""
    files_fixed = 0
    
    # Fix all session files
    for pattern in ['*.session', '*.session-*', 'telegram_bot.db*']:
        for file_path in glob.glob(pattern):
            if os.path.exists(file_path):
                try:
                    # Set 666 permissions (read/write for all)
                    os.chmod(file_path, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
                    files_fixed += 1
                    print(f"✅ Fixed permissions: {file_path}")
                except Exception as e:
                    print(f"❌ Failed to fix {file_path}: {e}")
    
    return files_fixed

if __name__ == "__main__":
    print("🔧 Starting permissions fix...")
    fixed = fix_all_permissions()
    print(f"✅ Fixed {fixed} files")
