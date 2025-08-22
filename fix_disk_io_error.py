#!/usr/bin/env python3
"""
إصلاح مشكلة disk I/O error
"""

import os
import sqlite3
import logging
import shutil
import time
from pathlib import Path

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_disk_space():
    """فحص مساحة القرص"""
    logger.info("🔍 فحص مساحة القرص...")
    
    try:
        import shutil
        total, used, free = shutil.disk_usage('.')
        
        total_gb = total // (1024**3)
        used_gb = used // (1024**3)
        free_gb = free // (1024**3)
        
        logger.info(f"💾 إجمالي المساحة: {total_gb} GB")
        logger.info(f"📊 المساحة المستخدمة: {used_gb} GB")
        logger.info(f"🆓 المساحة المتاحة: {free_gb} GB")
        
        if free_gb < 1:
            logger.error("❌ مساحة القرص منخفضة جداً (أقل من 1 GB)")
            return False
        elif free_gb < 5:
            logger.warning("⚠️ مساحة القرص منخفضة (أقل من 5 GB)")
            return True
        else:
            logger.info("✅ مساحة القرص كافية")
            return True
            
    except Exception as e:
        logger.error(f"❌ خطأ في فحص مساحة القرص: {e}")
        return False

def check_file_system():
    """فحص نظام الملفات"""
    logger.info("🔍 فحص نظام الملفات...")
    
    try:
        # فحص إذا كان الملف قابل للكتابة
        test_file = "test_write.tmp"
        
        # محاولة الكتابة
        with open(test_file, 'w') as f:
            f.write("test")
        
        # محاولة القراءة
        with open(test_file, 'r') as f:
            content = f.read()
        
        # حذف الملف المؤقت
        os.remove(test_file)
        
        if content == "test":
            logger.info("✅ نظام الملفات يعمل بشكل طبيعي")
            return True
        else:
            logger.error("❌ مشكلة في نظام الملفات")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في فحص نظام الملفات: {e}")
        return False

def check_database_integrity():
    """فحص سلامة قاعدة البيانات"""
    logger.info("🔍 فحص سلامة قاعدة البيانات...")
    
    db_file = 'telegram_bot.db'
    if not os.path.exists(db_file):
        logger.error("❌ ملف قاعدة البيانات غير موجود")
        return False
    
    try:
        conn = sqlite3.connect(db_file, timeout=30)
        cursor = conn.cursor()
        
        # فحص سلامة قاعدة البيانات
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        if result and result[0] == 'ok':
            logger.info("✅ سلامة قاعدة البيانات جيدة")
            conn.close()
            return True
        else:
            logger.error(f"❌ مشكلة في سلامة قاعدة البيانات: {result}")
            conn.close()
            return False
            
    except sqlite3.OperationalError as e:
        if "disk I/O error" in str(e).lower():
            logger.error(f"❌ خطأ في القرص: {e}")
            return False
        else:
            logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ عام في فحص قاعدة البيانات: {e}")
        return False

def fix_database_file():
    """إصلاح ملف قاعدة البيانات"""
    logger.info("🔧 محاولة إصلاح ملف قاعدة البيانات...")
    
    db_file = 'telegram_bot.db'
    if not os.path.exists(db_file):
        logger.error("❌ ملف قاعدة البيانات غير موجود")
        return False
    
    try:
        # إنشاء نسخة احتياطية
        timestamp = int(time.time())
        backup_file = f"{db_file}.backup_{timestamp}"
        
        logger.info(f"💾 إنشاء نسخة احتياطية: {backup_file}")
        shutil.copy2(db_file, backup_file)
        
        # محاولة إصلاح قاعدة البيانات
        logger.info("🔧 محاولة إصلاح قاعدة البيانات...")
        
        conn = sqlite3.connect(db_file, timeout=60)
        cursor = conn.cursor()
        
        # تطبيق إعدادات PRAGMA آمنة
        cursor.execute('PRAGMA journal_mode=DELETE')
        cursor.execute('PRAGMA synchronous=NORMAL')
        cursor.execute('PRAGMA locking_mode=NORMAL')
        cursor.execute('PRAGMA temp_store=memory')
        cursor.execute('PRAGMA cache_size=1000')
        cursor.execute('PRAGMA page_size=4096')
        cursor.execute('PRAGMA auto_vacuum=NONE')
        
        # فحص وإصلاح قاعدة البيانات
        cursor.execute('PRAGMA integrity_check')
        integrity_result = cursor.fetchone()
        
        if integrity_result and integrity_result[0] == 'ok':
            logger.info("✅ قاعدة البيانات سليمة")
        else:
            logger.warning("⚠️ مشكلة في سلامة قاعدة البيانات، محاولة الإصلاح...")
            cursor.execute('PRAGMA quick_check')
            quick_result = cursor.fetchone()
            
            if quick_result and quick_result[0] == 'ok':
                logger.info("✅ فحص سريع ناجح")
            else:
                logger.error("❌ فشل في إصلاح قاعدة البيانات")
                conn.close()
                return False
        
        # اختبار الكتابة
        cursor.execute("CREATE TABLE IF NOT EXISTS test_repair (id INTEGER PRIMARY KEY)")
        cursor.execute("INSERT INTO test_repair (id) VALUES (1)")
        cursor.execute("SELECT id FROM test_repair WHERE id = 1")
        result = cursor.fetchone()
        cursor.execute("DELETE FROM test_repair WHERE id = 1")
        cursor.execute("DROP TABLE test_repair")
        
        conn.commit()
        conn.close()
        
        if result and result[0] == 1:
            logger.info("✅ إصلاح قاعدة البيانات ناجح")
            return True
        else:
            logger.error("❌ فشل في اختبار الكتابة")
            return False
            
    except sqlite3.OperationalError as e:
        if "disk I/O error" in str(e).lower():
            logger.error(f"❌ خطأ في القرص أثناء الإصلاح: {e}")
            return False
        else:
            logger.error(f"❌ خطأ في قاعدة البيانات أثناء الإصلاح: {e}")
            return False
    except Exception as e:
        logger.error(f"❌ خطأ عام أثناء الإصلاح: {e}")
        return False

def optimize_database():
    """تحسين قاعدة البيانات"""
    logger.info("⚡ تحسين قاعدة البيانات...")
    
    db_file = 'telegram_bot.db'
    if not os.path.exists(db_file):
        logger.error("❌ ملف قاعدة البيانات غير موجود")
        return False
    
    try:
        conn = sqlite3.connect(db_file, timeout=60)
        cursor = conn.cursor()
        
        # تحسين قاعدة البيانات
        cursor.execute('PRAGMA optimize')
        cursor.execute('PRAGMA wal_checkpoint(TRUNCATE)')
        
        # تنظيف الذاكرة المؤقتة
        cursor.execute('PRAGMA shrink_memory')
        
        conn.commit()
        conn.close()
        
        logger.info("✅ تم تحسين قاعدة البيانات")
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحسين قاعدة البيانات: {e}")
        return False

def check_system_resources():
    """فحص موارد النظام"""
    logger.info("🔍 فحص موارد النظام...")
    
    try:
        import psutil
        
        # فحص الذاكرة
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available = memory.available // (1024**3)  # GB
        
        logger.info(f"🧠 استخدام الذاكرة: {memory_percent}%")
        logger.info(f"🆓 الذاكرة المتاحة: {memory_available} GB")
        
        if memory_percent > 90:
            logger.error("❌ استخدام الذاكرة مرتفع جداً")
            return False
        elif memory_percent > 80:
            logger.warning("⚠️ استخدام الذاكرة مرتفع")
            return True
        else:
            logger.info("✅ استخدام الذاكرة طبيعي")
            return True
            
    except ImportError:
        logger.warning("⚠️ مكتبة psutil غير متوفرة، تخطي فحص الذاكرة")
        return True
    except Exception as e:
        logger.error(f"❌ خطأ في فحص موارد النظام: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء فحص وإصلاح مشاكل القرص...")
    
    # فحص موارد النظام
    if not check_system_resources():
        logger.error("❌ مشاكل في موارد النظام")
        return False
    
    # فحص مساحة القرص
    if not check_disk_space():
        logger.error("❌ مشاكل في مساحة القرص")
        return False
    
    # فحص نظام الملفات
    if not check_file_system():
        logger.error("❌ مشاكل في نظام الملفات")
        return False
    
    # فحص سلامة قاعدة البيانات
    if not check_database_integrity():
        logger.warning("⚠️ مشاكل في سلامة قاعدة البيانات")
        
        # محاولة الإصلاح
        if not fix_database_file():
            logger.error("❌ فشل في إصلاح قاعدة البيانات")
            return False
    
    # تحسين قاعدة البيانات
    if not optimize_database():
        logger.warning("⚠️ فشل في تحسين قاعدة البيانات")
    
    logger.info("✅ تم إكمال فحص وإصلاح مشاكل القرص")
    return True

if __name__ == "__main__":
    main()