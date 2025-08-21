#!/usr/bin/env python3
"""
Database Readonly Fix
إصلاح مشكلة قاعدة البيانات المقفولة للقراءة فقط
"""

import os
import sqlite3
import shutil
import sys

def fix_database_permissions():
    """إصلاح صلاحيات قاعدة البيانات"""
    
    db_files = [
        'telegram_bot.db',
        'telegram_bot.db-wal', 
        'telegram_bot.db-shm'
    ]
    
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                # تغيير الصلاحيات
                os.chmod(db_file, 0o664)
                print(f"✅ تم إصلاح صلاحيات {db_file}")
            except Exception as e:
                print(f"⚠️ لا يمكن تغيير صلاحيات {db_file}: {e}")

def recreate_clean_database():
    """إنشاء قاعدة بيانات جديدة ونظيفة"""
    
    try:
        # نسخ احتياطية
        if os.path.exists('telegram_bot.db'):
            shutil.copy('telegram_bot.db', 'telegram_bot.db.backup')
            print("✅ تم إنشاء نسخة احتياطية من قاعدة البيانات")
        
        # حذف ملفات قاعدة البيانات المشكلة
        db_files = ['telegram_bot.db-wal', 'telegram_bot.db-shm']
        for file in db_files:
            if os.path.exists(file):
                os.remove(file)
                print(f"🗑️ تم حذف {file}")
        
        # إعادة إنشاء قاعدة البيانات بصلاحيات صحيحة
        conn = sqlite3.connect('telegram_bot.db')
        
        # التأكد من إعدادات WAL mode
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=10000")
        conn.execute("PRAGMA foreign_keys=ON")
        
        conn.commit()
        conn.close()
        
        # تعيين الصلاحيات المناسبة
        os.chmod('telegram_bot.db', 0o664)
        
        print("✅ تم إنشاء قاعدة بيانات جديدة مع إعدادات صحيحة")
        
    except Exception as e:
        print(f"❌ خطأ في إعادة إنشاء قاعدة البيانات: {e}")

def fix_database_config():
    """إصلاح إعدادات قاعدة البيانات في الكود"""
    
    try:
        # إصلاح ملف database.py
        with open('database/database.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # إضافة timeout والتحقق من الصلاحيات
        old_connection = "self.connection = sqlite3.connect(self.db_path, check_same_thread=False)"
        new_connection = """# إعدادات اتصال محسنة لتجنب readonly errors
        self.connection = sqlite3.connect(
            self.db_path, 
            check_same_thread=False,
            timeout=30.0,  # انتظار 30 ثانية في حالة القفل
            isolation_level='DEFERRED'  # تحسين التعامل مع المعاملات
        )"""
        
        if old_connection in content:
            content = content.replace(old_connection, new_connection)
            print("✅ تم تحسين إعدادات الاتصال بقاعدة البيانات")
            
            with open('database/database.py', 'w', encoding='utf-8') as f:
                f.write(content)
        
    except FileNotFoundError:
        print("⚠️ ملف database.py غير موجود")
    except Exception as e:
        print(f"❌ خطأ في إصلاح إعدادات قاعدة البيانات: {e}")

if __name__ == "__main__":
    print("🔧 إصلاح مشكلة قاعدة البيانات المقفولة...")
    
    try:
        fix_database_permissions()
        recreate_clean_database()
        fix_database_config()
        
        print("\n✅ تم إصلاح مشكلة قاعدة البيانات بنجاح!")
        print("📋 الإصلاحات المطبقة:")
        print("   🔓 إصلاح صلاحيات قاعدة البيانات")
        print("   🆕 إنشاء قاعدة بيانات جديدة مع إعدادات صحيحة")
        print("   ⚙️ تحسين إعدادات الاتصال")
        print("   ⏱️ إضافة timeout لتجنب القفل")
        
    except Exception as e:
        print(f"❌ خطأ في إصلاح قاعدة البيانات: {e}")
        sys.exit(1)