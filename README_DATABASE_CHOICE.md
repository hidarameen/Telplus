# دليل استخدام قاعدة البيانات المرنة

## 📋 نظرة عامة

تم تطوير نظام مرن يدعم كلا النوعين من قواعد البيانات (SQLite و PostgreSQL) مع إمكانية التبديل بينهما بسهولة عبر متغير البيئة.

## 🎯 المميزات

### ✅ **المرونة الكاملة:**
- دعم SQLite و PostgreSQL
- تبديل سهل بين النوعين
- لا حاجة لنقل البيانات
- كل نوع يعمل بشكل مستقل

### ✅ **سهولة الاستخدام:**
- تحديد النوع عبر متغير البيئة
- تشغيل فوري بدون إعدادات معقدة
- عودة تلقائية إلى SQLite عند فشل PostgreSQL

### ✅ **التوافق الكامل:**
- نفس الواجهة البرمجية لكلا النوعين
- جميع الدوال متوافقة
- لا حاجة لتعديل الكود

## 🚀 كيفية الاستخدام

### 1. **إعداد ملف .env**

#### لاستخدام SQLite (افتراضي):
```env
# نوع قاعدة البيانات
DATABASE_TYPE=sqlite

# إعدادات البوت
BOT_TOKEN=your_bot_token_here
API_ID=your_api_id_here
API_HASH=your_api_hash_here
```

#### لاستخدام PostgreSQL:
```env
# نوع قاعدة البيانات
DATABASE_TYPE=postgresql

# رابط قاعدة البيانات
DATABASE_URL=postgresql://telegram_bot_user:your_secure_password@localhost:5432/telegram_bot_db

# إعدادات البوت
BOT_TOKEN=your_bot_token_here
API_ID=your_api_id_here
API_HASH=your_api_hash_here
```

### 2. **تشغيل البوت**

#### الطريقة العادية:
```bash
python run.py
```

#### الطريقة الجديدة مع خيارات:
```bash
# تشغيل مع SQLite
python run_with_database_choice.py --database sqlite

# تشغيل مع PostgreSQL
python run_with_database_choice.py --database postgresql

# اختبار الاتصال فقط
python run_with_database_choice.py --test

# عرض معلومات قاعدة البيانات
python run_with_database_choice.py --info
```

### 3. **استخدام في الكود**

#### الطريقة القديمة:
```python
from database.database import Database
db = Database()
```

#### الطريقة الجديدة:
```python
from database import get_database
db = get_database()
```

#### أو استخدام المصنع مباشرة:
```python
from database import DatabaseFactory
db = DatabaseFactory.create_database()
```

## 📁 الملفات الجديدة

### 1. **`database/database_factory.py`**
- **الوصف:** مصنع قاعدة البيانات الرئيسي
- **المميزات:**
  - اختيار النوع حسب متغير البيئة
  - عودة تلقائية إلى SQLite عند الفشل
  - معلومات قاعدة البيانات
  - اختبار الاتصال

### 2. **`database/__init__.py`**
- **الوصف:** واجهة موحدة لقاعدة البيانات
- **المميزات:**
  - دالة `get_database()` للاستخدام السريع
  - تصدير `DatabaseFactory` للاستخدام المتقدم

### 3. **`run_with_database_choice.py`**
- **الوصف:** سكريبت تشغيل محسن
- **المميزات:**
  - خيارات سطر الأوامر
  - اختبار الاتصال
  - عرض المعلومات
  - تحميل الإعدادات

### 4. **`.env.example`**
- **الوصف:** ملف مثال للإعدادات
- **المميزات:**
  - إعدادات SQLite و PostgreSQL
  - تعليقات توضيحية
  - متغيرات مطلوبة

## 🔧 التعديلات المطلوبة

### 1. **تحديث استيراد قاعدة البيانات:**

#### في `bot_package/bot_simple.py`:
```python
# تغيير من:
from database.database import Database

# إلى:
from database import get_database
```

#### في `userbot_service/userbot.py`:
```python
# تغيير من:
from database.database import Database

# إلى:
from database import get_database
```

### 2. **تحديث إنشاء قاعدة البيانات:**

#### في `SimpleTelegramBot.__init__()`:
```python
# تغيير من:
self.db = Database()

# إلى:
self.db = get_database()
```

#### في `UserbotService.__init__()`:
```python
# تغيير من:
self.db = Database()

# إلى:
self.db = get_database()
```

## 🧪 الاختبار

### 1. **اختبار المصنع:**
```bash
python test_database_factory.py
```

### 2. **اختبار الاتصال:**
```bash
python run_with_database_choice.py --test
```

### 3. **اختبار التشغيل:**
```bash
# اختبار SQLite
DATABASE_TYPE=sqlite python run_with_database_choice.py

# اختبار PostgreSQL
DATABASE_TYPE=postgresql python run_with_database_choice.py
```

## 📊 مقارنة الأداء

### SQLite:
- ✅ **سهولة الاستخدام:** ملف واحد
- ✅ **سرعة التشغيل:** فوري
- ✅ **لا حاجة لإعداد:** جاهز للاستخدام
- ⚠️ **محدودية التزامن:** للمستخدمين القليلين

### PostgreSQL:
- ✅ **أداء عالي:** للاستخدامات الكبيرة
- ✅ **تزامن متقدم:** للمستخدمين المتعددين
- ✅ **أمان عالي:** إدارة صلاحيات متقدمة
- ⚠️ **حاجة لإعداد:** تثبيت وتكوين

## 🔄 التبديل بين النوعين

### من SQLite إلى PostgreSQL:
1. تثبيت PostgreSQL
2. إنشاء قاعدة البيانات
3. تحديث ملف `.env`:
   ```env
   DATABASE_TYPE=postgresql
   DATABASE_URL=postgresql://user:pass@localhost:5432/db
   ```
4. تشغيل البوت

### من PostgreSQL إلى SQLite:
1. تحديث ملف `.env`:
   ```env
   DATABASE_TYPE=sqlite
   ```
2. تشغيل البوت

## ⚠️ ملاحظات مهمة

### 1. **البيانات المنفصلة:**
- كل نوع قاعدة بيانات له بياناته الخاصة
- لا يتم نقل البيانات تلقائياً
- يمكن استخدام كلا النوعين في نفس الوقت

### 2. **الأداء:**
- SQLite مناسب للمستخدمين القليلين
- PostgreSQL مناسب للمستخدمين المتعددين
- اختر النوع حسب احتياجاتك

### 3. **النسخ الاحتياطية:**
- احتفظ بنسخ احتياطية من كلا النوعين
- SQLite: نسخ ملف `telegram_bot.db`
- PostgreSQL: استخدام أدوات النسخ الاحتياطي

## 🚀 أمثلة الاستخدام

### مثال 1: تشغيل سريع مع SQLite
```bash
# إنشاء ملف .env
echo "DATABASE_TYPE=sqlite" > .env
echo "BOT_TOKEN=your_token" >> .env
echo "API_ID=your_api_id" >> .env
echo "API_HASH=your_api_hash" >> .env

# تشغيل البوت
python run.py
```

### مثال 2: تشغيل مع PostgreSQL
```bash
# إنشاء ملف .env
echo "DATABASE_TYPE=postgresql" > .env
echo "DATABASE_URL=postgresql://user:pass@localhost:5432/db" >> .env
echo "BOT_TOKEN=your_token" >> .env
echo "API_ID=your_api_id" >> .env
echo "API_HASH=your_api_hash" >> .env

# تشغيل البوت
python run_with_database_choice.py --database postgresql
```

### مثال 3: اختبار الاتصال
```bash
# اختبار SQLite
python run_with_database_choice.py --database sqlite --test

# اختبار PostgreSQL
python run_with_database_choice.py --database postgresql --test
```

## 🎉 النتيجة النهائية

بعد تطبيق هذا النظام ستحصل على:

- ✅ **مرونة كاملة** في اختيار قاعدة البيانات
- ✅ **سهولة الاستخدام** بدون تعقيدات
- ✅ **توافق كامل** مع الكود الموجود
- ✅ **أداء محسن** حسب الاحتياجات
- ✅ **قابلية التوسع** للمستقبل

**🚀 البوت جاهز للعمل مع كلا النوعين من قواعد البيانات!** 🗄️