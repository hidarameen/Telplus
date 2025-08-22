#!/usr/bin/env python3
"""
إصلاح صلاحيات قاعدة البيانات ومنع مشاكل readonly
"""

import os
import sqlite3
import logging
import stat
from pathlib import Path

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fix_database_permissions():
    """إصلاح صلاحيات قاعدة البيانات"""
    
    db_files = [
        'telegram_bot.db',
        'userbot.db',
        'bot.db',
        'database.db'
    ]
    
    fixed_files = []
    
    for db_file in db_files:
        if os.path.exists(db_file):
            try:
                # الحصول على الصلاحيات الحالية
                current_mode = os.stat(db_file).st_mode
                current_permissions = stat.filemode(current_mode)
                
                logger.info(f"📁 فحص ملف: {db_file}")
                logger.info(f"   الصلاحيات الحالية: {current_permissions}")
                
                # إصلاح الصلاحيات
                os.chmod(db_file, 0o666)
                
                # التحقق من الصلاحيات الجديدة
                new_mode = os.stat(db_file).st_mode
                new_permissions = stat.filemode(new_mode)
                
                logger.info(f"   الصلاحيات الجديدة: {new_permissions}")
                
                # اختبار الاتصال بقاعدة البيانات
                try:
                    conn = sqlite3.connect(db_file, timeout=30)
                    cursor = conn.cursor()
                    
                    # اختبار الكتابة
                    cursor.execute("CREATE TABLE IF NOT EXISTS test_permissions (id INTEGER PRIMARY KEY)")
                    cursor.execute("INSERT INTO test_permissions (id) VALUES (1)")
                    cursor.execute("DELETE FROM test_permissions WHERE id = 1")
                    cursor.execute("DROP TABLE test_permissions")
                    
                    conn.commit()
                    conn.close()
                    
                    logger.info(f"   ✅ تم إصلاح {db_file} بنجاح")
                    fixed_files.append(db_file)
                    
                except sqlite3.OperationalError as e:
                    if "readonly database" in str(e).lower():
                        logger.error(f"   ❌ لا يزال هناك مشكلة readonly في {db_file}")
                    else:
                        logger.error(f"   ❌ خطأ في قاعدة البيانات {db_file}: {e}")
                except Exception as e:
                    logger.error(f"   ❌ خطأ عام في {db_file}: {e}")
                    
            except Exception as e:
                logger.error(f"❌ خطأ في إصلاح {db_file}: {e}")
    
    return fixed_files

def create_database_backup():
    """إنشاء نسخة احتياطية من قاعدة البيانات"""
    
    db_file = 'telegram_bot.db'
    if os.path.exists(db_file):
        try:
            import shutil
            from datetime import datetime
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = f"{db_file}.backup_{timestamp}"
            
            shutil.copy2(db_file, backup_file)
            os.chmod(backup_file, 0o666)
            
            logger.info(f"💾 تم إنشاء نسخة احتياطية: {backup_file}")
            return backup_file
            
        except Exception as e:
            logger.error(f"❌ فشل في إنشاء النسخة الاحتياطية: {e}")
            return None
    
    return None

def test_database_connection():
    """اختبار الاتصال بقاعدة البيانات"""
    
    db_file = 'telegram_bot.db'
    if not os.path.exists(db_file):
        logger.warning(f"⚠️ ملف قاعدة البيانات {db_file} غير موجود")
        return False
    
    try:
        conn = sqlite3.connect(db_file, timeout=30)
        cursor = conn.cursor()
        
        # اختبار القراءة
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"📊 عدد الجداول في قاعدة البيانات: {len(tables)}")
        
        # اختبار الكتابة
        cursor.execute("CREATE TABLE IF NOT EXISTS connection_test (id INTEGER PRIMARY KEY, test_value TEXT)")
        cursor.execute("INSERT INTO connection_test (test_value) VALUES ('test')")
        cursor.execute("SELECT test_value FROM connection_test WHERE id = 1")
        result = cursor.fetchone()
        cursor.execute("DELETE FROM connection_test WHERE id = 1")
        cursor.execute("DROP TABLE connection_test")
        
        conn.commit()
        conn.close()
        
        if result and result[0] == 'test':
            logger.info("✅ اختبار الاتصال بقاعدة البيانات ناجح")
            return True
        else:
            logger.error("❌ فشل في اختبار الكتابة في قاعدة البيانات")
            return False
            
    except sqlite3.OperationalError as e:
        if "readonly database" in str(e).lower():
            logger.error(f"❌ قاعدة البيانات للقراءة فقط: {e}")
        else:
            logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ خطأ عام في اختبار قاعدة البيانات: {e}")
        return False

def fix_database_pragmas():
    """إصلاح إعدادات PRAGMA لقاعدة البيانات"""
    
    db_file = 'telegram_bot.db'
    if not os.path.exists(db_file):
        logger.warning(f"⚠️ ملف قاعدة البيانات {db_file} غير موجود")
        return False
    
    try:
        conn = sqlite3.connect(db_file, timeout=30)
        cursor = conn.cursor()
        
        # تطبيق إعدادات PRAGMA آمنة
        pragma_settings = [
            ('journal_mode', 'DELETE'),
            ('locking_mode', 'NORMAL'),
            ('synchronous', 'NORMAL'),
            ('busy_timeout', '30000'),
            ('foreign_keys', 'ON'),
            ('temp_store', 'memory'),
            ('cache_size', '2000'),
            ('mmap_size', '268435456'),  # 256MB
            ('page_size', '4096'),
            ('auto_vacuum', 'NONE')
        ]
        
        logger.info("🔧 تطبيق إعدادات PRAGMA...")
        
        for pragma_name, pragma_value in pragma_settings:
            try:
                cursor.execute(f'PRAGMA {pragma_name}={pragma_value}')
                logger.info(f"   ✅ {pragma_name} = {pragma_value}")
            except Exception as e:
                logger.warning(f"   ⚠️ فشل في تطبيق {pragma_name}: {e}")
        
        # اختبار الكتابة
        cursor.execute('BEGIN IMMEDIATE')
        cursor.execute('ROLLBACK')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ تم تطبيق إعدادات PRAGMA بنجاح")
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل في تطبيق إعدادات PRAGMA: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    
    logger.info("🚀 بدء إصلاح قاعدة البيانات...")
    
    # إنشاء نسخة احتياطية
    backup_file = create_database_backup()
    
    # إصلاح الصلاحيات
    logger.info("🔧 إصلاح صلاحيات قاعدة البيانات...")
    fixed_files = fix_database_permissions()
    
    if fixed_files:
        logger.info(f"✅ تم إصلاح {len(fixed_files)} ملف(ات)")
    else:
        logger.warning("⚠️ لم يتم العثور على ملفات قاعدة بيانات للإصلاح")
    
    # اختبار الاتصال
    logger.info("🧪 اختبار الاتصال بقاعدة البيانات...")
    connection_ok = test_database_connection()
    
    # إصلاح إعدادات PRAGMA
    if connection_ok:
        logger.info("🔧 تطبيق إعدادات PRAGMA...")
        pragma_ok = fix_database_pragmas()
        
        if pragma_ok:
            logger.info("✅ تم إصلاح قاعدة البيانات بنجاح")
        else:
            logger.error("❌ فشل في تطبيق إعدادات PRAGMA")
    else:
        logger.error("❌ فشل في اختبار الاتصال بقاعدة البيانات")
    
    # عرض ملخص
    logger.info("📋 ملخص الإصلاح:")
    logger.info(f"   📁 الملفات المُصلحة: {len(fixed_files)}")
    logger.info(f"   🔗 الاتصال: {'✅ ناجح' if connection_ok else '❌ فشل'}")
    if backup_file:
        logger.info(f"   💾 النسخة الاحتياطية: {backup_file}")
    
    logger.info("🏁 انتهى إصلاح قاعدة البيانات")

if __name__ == "__main__":
    main()