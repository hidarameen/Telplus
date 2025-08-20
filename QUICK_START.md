# 🚀 البدء السريع - Quick Start Guide

## ⚡ **تشغيل البوت في 5 دقائق!**

### **1️⃣ التثبيت السريع (Ubuntu/Debian)**
```bash
# تثبيت FFmpeg
sudo apt update && sudo apt install ffmpeg

# تثبيت Python
sudo apt install python3 python3-pip

# نسخ المشروع
git clone <repository-url>
cd enhanced-telegram-bot

# التثبيت التلقائي
./install_dependencies.sh
```

### **2️⃣ إعداد البيئة**
```bash
# نسخ ملف الإعدادات
cp .env.example .env

# تعديل الإعدادات
nano .env
```

**أضف هذه القيم:**
```bash
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here
```

### **3️⃣ تشغيل البوت**
```bash
# تشغيل تلقائي
./start.sh

# أو تشغيل يدوي
python3 main.py
```

---

## 🎯 **البدء السريع باستخدام Make**

### **التثبيت الكامل**
```bash
make full-install
```

### **تشغيل البوت**
```bash
make start
```

### **فحص الصحة**
```bash
make health-check
```

---

## 🐳 **البدء السريع بـ Docker**

### **تشغيل فوري**
```bash
# بناء وتشغيل
docker-compose up -d

# أو باستخدام Make
make docker-run
```

### **إيقاف البوت**
```bash
docker-compose down

# أو باستخدام Make
make docker-stop
```

---

## 📱 **الحصول على مفاتيح Telegram**

### **1. API ID & API Hash**
1. اذهب إلى [my.telegram.org](https://my.telegram.org)
2. سجل دخولك برقم هاتفك
3. اذهب إلى "API development tools"
4. أنشئ تطبيق جديد
5. انسخ `api_id` و `api_hash`

### **2. Bot Token**
1. ابحث عن [@BotFather](https://t.me/BotFather) في Telegram
2. أرسل `/newbot`
3. اتبع التعليمات
4. انسخ `BOT_TOKEN`

---

## 🔧 **استكشاف الأخطاء السريع**

### **مشكلة: FFmpeg غير مثبت**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS
brew install ffmpeg
```

### **مشكلة: مكتبات Python مفقودة**
```bash
pip3 install -r requirements.txt
```

### **مشكلة: ملف .env مفقود**
```bash
cp .env.example .env
# ثم عدل الإعدادات
```

### **مشكلة: صلاحيات الملفات**
```bash
chmod +x *.sh
chmod +x *.py
```

---

## 📊 **فحص الأداء**

### **فحص الذاكرة المؤقتة**
```python
# في Python console
from watermark_processor import WatermarkProcessor
processor = WatermarkProcessor()
stats = processor.get_cache_stats()
print(f"حجم الذاكرة المؤقتة: {stats['cache_size']}")
```

### **مسح الذاكرة المؤقتة**
```python
processor.clear_cache()
```

---

## 🎬 **اختبار العلامة المائية**

### **1. إنشاء مهمة**
```python
task = {
    'source_chat_id': '@your_source',
    'target_chat_id': '@your_target',
    'watermark_enabled': True,
    'watermark_text': '© 2024'
}
```

### **2. إرسال صورة/فيديو**
- أرسل صورة أو فيديو إلى المصدر
- البوت سيطبق العلامة المائية تلقائياً
- سيتم إرسالها إلى الهدف

---

## 📈 **مراقبة الأداء**

### **عرض السجلات**
```bash
# السجلات المباشرة
make logs

# أو
tail -f logs/bot.log
```

### **فحص الموارد**
```bash
make resources
```

### **حالة البوت**
```bash
make status
```

---

## 🚨 **أوامر الطوارئ**

### **إيقاف فوري**
```bash
make stop
# أو
pkill -f "python.*main.py"
```

### **إعادة تشغيل**
```bash
make restart
```

### **تنظيف كامل**
```bash
make clean
```

---

## 📞 **المساعدة السريعة**

### **عرض جميع الأوامر**
```bash
make help
```

### **فحص شامل**
```bash
make health-check
```

### **نسخ احتياطي**
```bash
make backup
```

---

## 🎉 **مبروك! البوت يعمل الآن**

### **✅ ما تم إنجازه:**
- ✅ تثبيت FFmpeg
- ✅ تثبيت مكتبات Python
- ✅ إعداد متغيرات البيئة
- ✅ تشغيل البوت
- ✅ تطبيق العلامة المائية
- ✅ معالجة الوسائط مرة واحدة

### **🚀 الميزات المتاحة:**
- 🎯 معالجة الوسائط مرة واحدة
- 🏷️ علامة مائية متقدمة
- 🎬 تحسين الفيديو
- 📤 توجيه الرسائل
- 💾 ذاكرة مؤقتة ذكية
- 🧹 تنظيف تلقائي

---

## 📚 **الخطوات التالية**

1. **اقرأ README.md** للحصول على معلومات مفصلة
2. **راجع CHANGELOG.md** لمعرفة التحديثات
3. **جرب الميزات المتقدمة** مثل الفلاتر والفلترة
4. **أضف ميزات جديدة** حسب احتياجاتك

---

**🎯 البوت جاهز للاستخدام! أرسل صورة أو فيديو إلى المصدر وسترى العلامة المائية تعمل!**