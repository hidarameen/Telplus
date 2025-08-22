#!/usr/bin/env python3
"""
اختبار مشاكل التزامن في قاعدة البيانات
"""

import threading
import time
import sqlite3
import logging
from database import get_database

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_single_connection():
    """اختبار اتصال واحد"""
    logger.info("🧪 اختبار اتصال واحد...")
    try:
        db = get_database()
        conn = db.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        logger.info("✅ اتصال واحد ناجح")
        return True
    except Exception as e:
        logger.error(f"❌ فشل في اتصال واحد: {e}")
        return False

def test_multiple_connections():
    """اختبار اتصالات متعددة"""
    logger.info("🧪 اختبار اتصالات متعددة...")
    try:
        db = get_database()
        connections = []
        
        for i in range(5):
            conn = db.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT ?", (i,))
            result = cursor.fetchone()
            connections.append(conn)
            logger.info(f"✅ اتصال {i+1} ناجح")
        
        # إغلاق جميع الاتصالات
        for conn in connections:
            conn.close()
        
        logger.info("✅ جميع الاتصالات المتعددة ناجحة")
        return True
    except Exception as e:
        logger.error(f"❌ فشل في اتصالات متعددة: {e}")
        return False

def test_concurrent_writes():
    """اختبار الكتابة المتزامنة"""
    logger.info("🧪 اختبار الكتابة المتزامنة...")
    
    def write_task(thread_id):
        try:
            db = get_database()
            conn = db.get_connection()
            cursor = conn.cursor()
            
            # إنشاء جدول مؤقت للاختبار
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_concurrency (
                    id INTEGER PRIMARY KEY,
                    thread_id INTEGER,
                    timestamp REAL
                )
            """)
            
            # إدراج بيانات
            cursor.execute(
                "INSERT INTO test_concurrency (thread_id, timestamp) VALUES (?, ?)",
                (thread_id, time.time())
            )
            
            conn.commit()
            conn.close()
            logger.info(f"✅ Thread {thread_id} كتب بنجاح")
            return True
        except Exception as e:
            logger.error(f"❌ Thread {thread_id} فشل: {e}")
            return False
    
    # تشغيل 5 threads للكتابة المتزامنة
    threads = []
    results = []
    
    for i in range(5):
        thread = threading.Thread(target=lambda x=i: results.append(write_task(x)))
        threads.append(thread)
        thread.start()
    
    # انتظار انتهاء جميع threads
    for thread in threads:
        thread.join()
    
    success_count = sum(results)
    logger.info(f"✅ {success_count}/5 threads نجحت في الكتابة المتزامنة")
    return success_count == 5

def test_database_permissions():
    """اختبار صلاحيات قاعدة البيانات"""
    logger.info("🧪 اختبار صلاحيات قاعدة البيانات...")
    
    import os
    import stat
    
    db_file = 'telegram_bot.db'
    if os.path.exists(db_file):
        # الحصول على الصلاحيات
        mode = os.stat(db_file).st_mode
        permissions = stat.filemode(mode)
        logger.info(f"📁 صلاحيات الملف: {permissions}")
        
        # اختبار الكتابة
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
            
            logger.info("✅ اختبار الكتابة ناجح")
            return True
        except sqlite3.OperationalError as e:
            if "readonly database" in str(e).lower():
                logger.error(f"❌ قاعدة البيانات للقراءة فقط: {e}")
                return False
            else:
                logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
                return False
        except Exception as e:
            logger.error(f"❌ خطأ عام: {e}")
            return False
    else:
        logger.error("❌ ملف قاعدة البيانات غير موجود")
        return False

def test_database_factory():
    """اختبار مصنع قاعدة البيانات"""
    logger.info("🧪 اختبار مصنع قاعدة البيانات...")
    
    try:
        from database import DatabaseFactory
        
        # اختبار إنشاء قاعدة البيانات
        db = DatabaseFactory.create_database()
        logger.info(f"✅ تم إنشاء قاعدة البيانات: {type(db).__name__}")
        
        # اختبار معلومات قاعدة البيانات
        db_info = DatabaseFactory.get_database_info()
        logger.info(f"📊 معلومات قاعدة البيانات: {db_info}")
        
        # اختبار الاتصال
        test_result = DatabaseFactory.test_connection()
        logger.info(f"🔗 نتيجة اختبار الاتصال: {test_result}")
        
        return test_result.get('success', False)
    except Exception as e:
        logger.error(f"❌ فشل في اختبار مصنع قاعدة البيانات: {e}")
        return False

def main():
    """الدالة الرئيسية"""
    logger.info("🚀 بدء اختبارات قاعدة البيانات...")
    
    tests = [
        ("اتصال واحد", test_single_connection),
        ("اتصالات متعددة", test_multiple_connections),
        ("كتابة متزامنة", test_concurrent_writes),
        ("صلاحيات قاعدة البيانات", test_database_permissions),
        ("مصنع قاعدة البيانات", test_database_factory),
    ]
    
    results = {}
    
    for test_name, test_func in tests:
        logger.info(f"\n{'='*50}")
        logger.info(f"🧪 اختبار: {test_name}")
        logger.info(f"{'='*50}")
        
        try:
            result = test_func()
            results[test_name] = result
            status = "✅ نجح" if result else "❌ فشل"
            logger.info(f"{status}: {test_name}")
        except Exception as e:
            logger.error(f"❌ خطأ في اختبار {test_name}: {e}")
            results[test_name] = False
    
    # ملخص النتائج
    logger.info(f"\n{'='*50}")
    logger.info("📋 ملخص النتائج:")
    logger.info(f"{'='*50}")
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ نجح" if result else "❌ فشل"
        logger.info(f"{status}: {test_name}")
    
    logger.info(f"\n🎯 النتيجة الإجمالية: {passed}/{total} اختبارات نجحت")
    
    if passed == total:
        logger.info("🎉 جميع الاختبارات نجحت!")
    else:
        logger.error("⚠️ بعض الاختبارات فشلت")
    
    return passed == total

if __name__ == "__main__":
    main()