#!/usr/bin/env python3
import os
import stat
import sqlite3
import glob
import time

def fix_all_databases():
    """Fix all database files before starting the bot"""
    print("🔧 Starting automatic database fix...")
    
    # Discover data and sessions directories
    data_dir = os.getenv('DATA_DIR', '/app/data')
    sessions_dir = os.getenv('SESSIONS_DIR', os.path.join(data_dir, 'sessions'))

    # Build list of candidate files
    scan_dirs = ['.', data_dir, sessions_dir]
    patterns = ['*.db', '*.session', 'telegram_bot.db*']
    files_to_fix = set()
    for base in scan_dirs:
        try:
            for pattern in patterns:
                for path in glob.glob(os.path.join(base, pattern)):
                    if os.path.exists(path) and not path.endswith('.backup'):
                        files_to_fix.add(os.path.abspath(path))
        except Exception:
            pass

    # Fix all database and session files
    for db_file in sorted(files_to_fix):
        try:
            print(f"🔨 Fixing {db_file}...")
            
            # Ensure parent directory exists and set permissions to 666
            try:
                os.makedirs(os.path.dirname(db_file), exist_ok=True)
            except Exception:
                pass
            os.chmod(db_file, 0o666)
            
            # Fix SQLite database settings
            if db_file.endswith('.db') or db_file.endswith('.session'):
                conn = sqlite3.connect(db_file, timeout=30)
                try:
                    conn.execute('PRAGMA journal_mode=DELETE')
                    conn.execute('PRAGMA synchronous=NORMAL') 
                    conn.execute('PRAGMA temp_store=MEMORY')
                    conn.execute('PRAGMA locking_mode=NORMAL')
                    conn.commit()
                    print(f"✅ Fixed database settings for {db_file}")
                except Exception as e:
                    print(f"⚠️ Warning fixing {db_file}: {e}")
                finally:
                    conn.close()
            
        except Exception as e:
            print(f"❌ Error with {db_file}: {e}")
    
    # Clean up journal/wal files
    cleanup_patterns = ['*.db-wal', '*.db-shm', '*.session-journal', '*.session-wal']
    for base in scan_dirs:
        for pattern in cleanup_patterns:
            for file_path in glob.glob(os.path.join(base, pattern)):
                try:
                    os.remove(file_path)
                    print(f"🗑️ Removed {file_path}")
                except:
                    pass
    
    print("✅ Database fix complete!")

if __name__ == "__main__":
    fix_all_databases()
