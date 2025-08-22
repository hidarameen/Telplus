#!/usr/bin/env python3
import os
import stat
import sqlite3
import glob
import time

def fix_all_databases():
    """Fix all database files before starting the bot"""
    print("🔧 Starting automatic database fix...")
    
    # Fix all database and session files
    patterns = ['*.db', '*.session', 'telegram_bot.db*']
    for pattern in patterns:
        for db_file in glob.glob(pattern):
            if os.path.exists(db_file) and not db_file.endswith('.backup'):
                try:
                    print(f"🔨 Fixing {db_file}...")
                    
                    # Set permissions to 666
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
    for pattern in cleanup_patterns:
        for file_path in glob.glob(pattern):
            try:
                os.remove(file_path)
                print(f"🗑️ Removed {file_path}")
            except:
                pass
    
    print("✅ Database fix complete!")

if __name__ == "__main__":
    fix_all_databases()
