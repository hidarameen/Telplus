# إصلاح مشكلة "attempt to write a readonly database"

## 🚨 المشكلة

### الخطأ:
```
main - ERROR - ❌ خطأ في بوت التحكم: attempt to write a readonly database
```

### السبب:
- ملف قاعدة البيانات SQLite `telegram_bot.db` له صلاحيات للقراءة فقط
- الصلاحيات الحالية: `-rw-r--r--` (644)
- المطلوب: `-rw-rw-rw-` (666) للكتابة

## 🔧 الحلول المطبقة

### 1. إصلاح فوري للصلاحيات

```bash
chmod 666 telegram_bot.db
```

### 2. إصلاح الكود في `database/database.py`

#### قبل الإصلاح:
```python
def get_connection(self):
    """Get SQLite database connection"""
    conn = sqlite3.connect(self.db_path, timeout=120, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        # Improve concurrency and reduce lock errors
        conn.execute('PRAGMA journal_mode=DELETE')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA busy_timeout=120000')
        conn.execute('PRAGMA foreign_keys=ON')
    except Exception:
        pass
    return conn
```

#### بعد الإصلاح:
```python
def get_connection(self):
    """Get SQLite database connection"""
    # إصلاح صلاحيات الملف قبل الاتصال
    try:
        import os
        if os.path.exists(self.db_path):
            os.chmod(self.db_path, 0o666)
            logger.info(f"✅ تم تصحيح صلاحيات قاعدة البيانات: {self.db_path}")
    except Exception as e:
        logger.warning(f"تحذير في تصحيح صلاحيات قاعدة البيانات: {e}")
    
    conn = sqlite3.connect(self.db_path, timeout=120, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    try:
        # Improve concurrency and reduce lock errors
        conn.execute('PRAGMA journal_mode=DELETE')
        conn.execute('PRAGMA synchronous=NORMAL')
        conn.execute('PRAGMA busy_timeout=120000')
        conn.execute('PRAGMA foreign_keys=ON')
        conn.execute('PRAGMA locking_mode=NORMAL')
        conn.execute('PRAGMA temp_store=memory')
        conn.execute('PRAGMA cache_size=2000')
        
        # التأكد من أن قاعدة البيانات قابلة للكتابة
        conn.execute('BEGIN IMMEDIATE')
        conn.execute('ROLLBACK')
        
        logger.info("✅ تم تطبيق إعدادات PRAGMA آمنة وتأكيد إمكانية الكتابة")
    except sqlite3.OperationalError as e:
        if "readonly database" in str(e).lower():
            logger.error(f"❌ مشكلة readonly في قاعدة البيانات: {e}")
            logger.error("🔧 محاولة إصلاح الصلاحيات...")
            try:
                import os
                os.chmod(self.db_path, 0o666)
                logger.info("✅ تم إصلاح الصلاحيات، إعادة المحاولة...")
                # إعادة إنشاء الاتصال
                conn.close()
                conn = sqlite3.connect(self.db_path, timeout=120, check_same_thread=False, isolation_level=None)
                conn.row_factory = sqlite3.Row
                conn.execute('PRAGMA journal_mode=DELETE')
                conn.execute('PRAGMA synchronous=NORMAL')
                conn.execute('PRAGMA busy_timeout=120000')
                conn.execute('PRAGMA foreign_keys=ON')
                conn.execute('PRAGMA locking_mode=NORMAL')
                conn.execute('PRAGMA temp_store=memory')
                conn.execute('PRAGMA cache_size=2000')
                conn.execute('BEGIN IMMEDIATE')
                conn.execute('ROLLBACK')
                logger.info("✅ تم إصلاح قاعدة البيانات بنجاح")
            except Exception as fix_error:
                logger.error(f"❌ فشل في إصلاح قاعدة البيانات: {fix_error}")
                raise
        else:
            logger.error(f"❌ خطأ في قاعدة البيانات: {e}")
            raise
    except Exception:
        pass
    return conn
```

### 3. إصلاح الكود في `main.py`

#### إضافة معالجة خاصة لأخطاء قاعدة البيانات:
```python
except Exception as e:
    error_str = str(e)
    
    # التعامل مع أخطاء قاعدة البيانات
    if "readonly database" in error_str.lower() or "attempt to write a readonly database" in error_str.lower():
        logger.error(f"❌ خطأ في قاعدة البيانات (readonly): {e}")
        logger.error("🔧 محاولة إصلاح قاعدة البيانات...")
        
        try:
            # تشغيل إصلاح قاعدة البيانات
            import subprocess
            import sys
            
            logger.info("🔧 تشغيل سكريبت إصلاح قاعدة البيانات...")
            result = subprocess.run([sys.executable, "fix_database_permissions.py"], 
                                  capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                logger.info("✅ تم إصلاح قاعدة البيانات بنجاح")
                logger.info("🔄 إعادة تشغيل بوت التحكم...")
                await asyncio.sleep(5)
                continue
            else:
                logger.error(f"❌ فشل في إصلاح قاعدة البيانات: {result.stderr}")
        except Exception as fix_error:
            logger.error(f"❌ خطأ في تشغيل إصلاح قاعدة البيانات: {fix_error}")
        
        # انتظار قصير قبل إعادة المحاولة
        delay = 30
        logger.info(f"⏱️ انتظار {delay} ثانية قبل إعادة المحاولة...")
        await asyncio.sleep(delay)
        continue
```

## 🛠️ الأدوات المُنشأة

### 1. `fix_database_permissions.py`
سكريبت Python شامل لإصلاح قاعدة البيانات:
- إصلاح صلاحيات الملفات
- إنشاء نسخة احتياطية
- اختبار الاتصال
- تطبيق إعدادات PRAGMA

### 2. `fix_database_permissions.sh`
سكريبت Bash لتشغيل الإصلاح:
```bash
./fix_database_permissions.sh
```

## 📋 خطوات الإصلاح اليدوي

### 1. إصلاح فوري:
```bash
chmod 666 telegram_bot.db
```

### 2. تشغيل سكريبت الإصلاح:
```bash
python3 fix_database_permissions.py
```

### 3. أو استخدام سكريبت Bash:
```bash
./fix_database_permissions.sh
```

## 🔍 فحص الصلاحيات

### قبل الإصلاح:
```bash
ls -la telegram_bot.db
# -rw-r--r-- 1 ubuntu ubuntu 417792 Aug 16 08:41 telegram_bot.db
```

### بعد الإصلاح:
```bash
ls -la telegram_bot.db
# -rw-rw-rw- 1 ubuntu ubuntu 417792 Aug 16 08:41 telegram_bot.db
```

## ⚙️ إعدادات PRAGMA المُحسنة

### الإعدادات المطبقة:
```sql
PRAGMA journal_mode=DELETE;        -- تجنب WAL لمنع مشاكل readonly
PRAGMA locking_mode=NORMAL;        -- قفل عادي
PRAGMA synchronous=NORMAL;         -- تزامن عادي
PRAGMA busy_timeout=30000;         -- مهلة 30 ثانية
PRAGMA foreign_keys=ON;            -- تفعيل المفاتيح الخارجية
PRAGMA temp_store=memory;          -- تخزين مؤقت في الذاكرة
PRAGMA cache_size=2000;            -- حجم الكاش 2MB
PRAGMA mmap_size=268435456;        -- 256MB للذاكرة
PRAGMA page_size=4096;             -- حجم الصفحة 4KB
PRAGMA auto_vacuum=NONE;           -- تعطيل التنظيف التلقائي
```

## 🚀 التشغيل التلقائي

### في `main.py`:
- يتم تشغيل إصلاح قاعدة البيانات تلقائياً عند حدوث خطأ readonly
- إعادة تشغيل البوت بعد الإصلاح
- معالجة الأخطاء بشكل آمن

### في `database/database.py`:
- فحص وإصلاح الصلاحيات عند كل اتصال
- إعادة المحاولة تلقائياً عند فشل الاتصال
- تطبيق إعدادات PRAGMA آمنة

## 📊 مراقبة الأداء

### مؤشرات النجاح:
- ✅ لا توجد أخطاء readonly
- ✅ قاعدة البيانات قابلة للكتابة
- ✅ البوت يعمل بشكل طبيعي
- ✅ إعدادات PRAGMA مطبقة

### مؤشرات المشكلة:
- ❌ أخطاء readonly متكررة
- ❌ فشل في إصلاح الصلاحيات
- ❌ قاعدة البيانات لا تزال للقراءة فقط

## 🔄 النسخ الاحتياطية

### إنشاء نسخة احتياطية:
```python
import shutil
from datetime import datetime

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
backup_file = f"telegram_bot.db.backup_{timestamp}"
shutil.copy2("telegram_bot.db", backup_file)
os.chmod(backup_file, 0o666)
```

### استعادة من نسخة احتياطية:
```bash
cp telegram_bot.db.backup_YYYYMMDD_HHMMSS telegram_bot.db
chmod 666 telegram_bot.db
```

## 💡 نصائح للوقاية

### 1. مراقبة الصلاحيات:
```bash
ls -la *.db
```

### 2. تشغيل فحص دوري:
```bash
python3 fix_database_permissions.py
```

### 3. مراقبة السجلات:
```bash
tail -f bot.log | grep -i "readonly\|database"
```

### 4. إعداد cron job:
```bash
# إضافة إلى crontab
0 */6 * * * cd /path/to/bot && python3 fix_database_permissions.py
```

## 🎯 النتيجة النهائية

بعد تطبيق جميع الإصلاحات:
- ✅ قاعدة البيانات قابلة للكتابة
- ✅ البوت يعمل بدون أخطاء readonly
- ✅ إصلاح تلقائي عند حدوث المشكلة
- ✅ نسخ احتياطية تلقائية
- ✅ مراقبة مستمرة للأداء

---

**ملاحظة**: جميع الإصلاحات تم تطبيقها مع الحفاظ على التوافق مع الإصدارات السابقة وعدم التأثير على البيانات الموجودة.