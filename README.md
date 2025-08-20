# 🤖 البوت المحسن لـ Telegram - Enhanced Telegram Bot

## 📋 نظرة عامة
بوت Telegram محسن مع وظائف متقدمة للعلامة المائية، معالجة الوسائط، وتوجيه الرسائل. يدعم معالجة الوسائط مرة واحدة وإعادة استخدامها لكل الأهداف لتحسين الأداء.

## ✨ الميزات الرئيسية

### 🎯 **معالجة الوسائط المحسنة**
- **معالجة مرة واحدة**: معالجة الوسائط مرة واحدة وإعادة استخدامها لكل الأهداف
- **ذاكرة مؤقتة ذكية**: حفظ الوسائط المعالجة مسبقاً لتحسين الأداء
- **تنظيف تلقائي**: تنظيف الملفات المؤقتة والذاكرة المؤقتة

### 🏷️ **العلامة المائية المتقدمة**
- **نص وصورة**: دعم العلامات المائية النصية والصورية
- **مواضع متعددة**: 9 مواضع مختلفة للعلامة المائية
- **إعدادات مخصصة**: حجم، شفافية، لون، إزاحة

### 🎬 **معالجة الفيديو المحسنة**
- **ضغط ذكي**: ضغط الفيديو مع الحفاظ على الجودة
- **صيغة MP4**: تحويل تلقائي إلى صيغة MP4
- **تحسين الأداء**: استخدام FFmpeg لمعالجة محسنة

### 📤 **توجيه الرسائل**
- **أهداف متعددة**: إرسال لعدة أهداف في نفس الوقت
- **فلاتر متقدمة**: فلترة حسب النوع، المشرف، الكلمات
- **تنسيق الرسائل**: ترويسة، تذييل، أزرار إنلاين

## 🚀 التثبيت السريع

### **1. تثبيت المتطلبات الأساسية**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS
brew install ffmpeg
```

### **2. تثبيت مكتبات Python**
```bash
# تثبيت تلقائي
./install_dependencies.sh

# أو تثبيت يدوي
pip install -r requirements.txt
```

### **3. تشغيل البوت**
```bash
python main.py
```

## 🐳 التثبيت باستخدام Docker

### **تشغيل سريع**
```bash
docker-compose up -d
```

### **بناء الصورة**
```bash
docker build -t enhanced-telegram-bot .
```

## 📁 هيكل المشروع

```
enhanced-telegram-bot/
├── main.py                 # نقطة البداية الرئيسية
├── userbot_service/        # خدمة Userbot
│   └── userbot.py         # البوت الرئيسي
├── watermark_processor.py  # معالج العلامة المائية
├── database/               # قاعدة البيانات
├── bot_package/           # حزمة البوت
├── requirements.txt        # متطلبات Python
├── install_dependencies.sh # سكريبت التثبيت
├── Dockerfile             # صورة Docker
├── docker-compose.yml     # تكوين Docker
└── README.md              # هذا الملف
```

## ⚙️ الإعدادات

### **متغيرات البيئة**
```bash
# Telegram API
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token

# قاعدة البيانات
DATABASE_URL=sqlite:///telegram_bot.db

# إعدادات إضافية
DEBUG=false
LOG_LEVEL=INFO
```

### **إعدادات العلامة المائية**
```python
watermark_settings = {
    'enabled': True,
    'watermark_type': 'text',  # 'text' أو 'image'
    'watermark_text': 'نص العلامة المائية',
    'position': 'bottom_right',
    'opacity': 80,
    'size_percentage': 50,
    'offset_x': 0,
    'offset_y': 0
}
```

## 🔧 الاستخدام

### **1. إنشاء مهمة جديدة**
```python
# إنشاء مهمة توجيه
task = {
    'source_chat_id': '@source_channel',
    'target_chat_id': '@target_channel',
    'watermark_enabled': True,
    'forward_mode': 'copy'
}
```

### **2. إعداد العلامة المائية**
```python
# إعدادات العلامة المائية
watermark = {
    'type': 'text',
    'text': '© 2024',
    'position': 'bottom_right',
    'opacity': 70
}
```

### **3. مراقبة الأداء**
```python
# إحصائيات الذاكرة المؤقتة
stats = watermark_processor.get_cache_stats()
print(f"حجم الذاكرة المؤقتة: {stats['cache_size']}")

# مسح الذاكرة المؤقتة
watermark_processor.clear_cache()
```

## 📊 الأداء

### **التحسينات المتوقعة**
- **سرعة المعالجة**: 70-80% تحسن
- **استهلاك الذاكرة**: 60-70% تقليل
- **حجم الفيديو**: 30-50% تقليل مع الحفاظ على الجودة

### **الذاكرة المؤقتة**
- **حجم أقصى**: 50 عنصر
- **تنظيف تلقائي**: عند الوصول للحد الأقصى
- **حفظ ذكي**: حسب نوع الوسائط والمهمة

## 🛠️ استكشاف الأخطاء

### **مشاكل شائعة**

#### **1. FFmpeg غير مثبت**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# التحقق من التثبيت
ffmpeg -version
```

#### **2. مشاكل الذاكرة**
```python
# مسح الذاكرة المؤقتة
watermark_processor.clear_cache()

# مراقبة الاستخدام
stats = watermark_processor.get_cache_stats()
```

#### **3. مشاكل قاعدة البيانات**
```bash
# إعادة إنشاء قاعدة البيانات
rm telegram_bot.db
python main.py
```

### **سجلات الأخطاء**
```bash
# مراقبة السجلات
tail -f logs/bot.log

# تصفية الأخطاء
grep "ERROR" logs/bot.log
```

## 🔒 الأمان

### **أفضل الممارسات**
- **تأمين API Keys**: لا تشارك مفاتيح API
- **فلترة المشرفين**: استخدام فلترة المشرفين
- **فلترة المحتوى**: فلترة الرسائل حسب النوع
- **مراقبة الاستخدام**: تتبع استخدام البوت

### **إعدادات الأمان**
```python
# فلترة المشرفين
admin_filter = {
    'enabled': True,
    'allowed_admins': ['@admin1', '@admin2']
}

# فلترة المحتوى
content_filter = {
    'blocked_words': ['كلمة1', 'كلمة2'],
    'allowed_media': ['photo', 'video', 'text']
}
```

## 📈 التطوير

### **إضافة ميزات جديدة**
1. إنشاء وحدة جديدة في `modules/`
2. تحديث `requirements.txt`
3. إضافة اختبارات في `tests/`
4. تحديث التوثيق

### **اختبار البوت**
```bash
# تشغيل الاختبارات
pytest tests/

# اختبارات محددة
pytest tests/test_watermark.py
```

## 🤝 المساهمة

### **كيفية المساهمة**
1. Fork المشروع
2. إنشاء فرع جديد (`git checkout -b feature/amazing-feature`)
3. Commit التغييرات (`git commit -m 'Add amazing feature'`)
4. Push للفرع (`git push origin feature/amazing-feature`)
5. إنشاء Pull Request

### **معايير الكود**
- استخدام Python 3.8+
- اتباع PEP 8
- إضافة تعليقات باللغة العربية
- كتابة اختبارات شاملة

## 📞 الدعم

### **المساعدة**
- **المسائل**: إنشاء Issue في GitHub
- **الأسئلة**: استخدام Discussions
- **التحديثات**: متابعة Releases

### **المجتمع**
- Telegram Group: [رابط المجموعة]
- Discord Server: [رابط السيرفر]
- Email: [البريد الإلكتروني]

## 📄 الترخيص

هذا المشروع مرخص تحت رخصة MIT. راجع ملف `LICENSE` للتفاصيل.

## 🙏 الشكر

- Telegram API
- OpenCV
- FFmpeg
- Python Community
- جميع المساهمين

---

**⭐ إذا أعجبك المشروع، لا تنس إعطاءه نجمة!**

**🚀 البوت جاهز للتشغيل مع جميع التحسينات!**