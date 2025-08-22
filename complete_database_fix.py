import os
import stat
import sqlite3
import glob

def fix_telethon_session_databases():
    """Fix all Telethon session database modes and permissions"""
    print("🔧 Starting comprehensive database fix...")
    
    # Fix all database files
    for pattern in ['*.db', '*.session']:
        for db_file in glob.glob(pattern):
            if os.path.exists(db_file):
                try:
                    print(f"🔨 Fixing {db_file}...")
                    
                    # Set proper permissions first
                    os.chmod(db_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
                    
                    # Connect and fix database settings
                    conn = sqlite3.connect(db_file, timeout=30)
                    conn.execute('PRAGMA journal_mode=DELETE')
                    conn.execute('PRAGMA synchronous=NORMAL')
                    conn.execute('PRAGMA temp_store=MEMORY')
                    conn.execute('PRAGMA locking_mode=NORMAL')
                    conn.commit()
                    conn.close()
                    
                    print(f"✅ Fixed {db_file}")
                except Exception as e:
                    print(f"❌ Error fixing {db_file}: {e}")
    
    # Clean up any journal/wal files
    for pattern in ['*.db-*', '*.session-*']:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"🗑️ Removed {file_path}")
            except:
                pass
    
    print("✅ Database fix complete!")

if __name__ == "__main__":
    fix_telethon_session_databases()
