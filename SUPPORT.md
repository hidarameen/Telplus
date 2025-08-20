# 🆘 دليل الدعم - Support Guide

## 📞 **كيفية الحصول على المساعدة**

### **🚨 المشاكل العاجلة**
إذا كان البوت لا يعمل أو لديك مشكلة عاجلة:

1. **أولاً**: تحقق من [استكشاف الأخطاء السريع](#-استكشاف-الأخطاء-السريع)
2. **ثانياً**: ابحث في [المشاكل الشائعة](#-المشاكل-الشائعة)
3. **ثالثاً**: اطرح سؤال في [GitHub Discussions](https://github.com/your-repo/discussions)
4. **رابعاً**: أرسل بريد إلكتروني للدعم

---

## 🔧 **استكشاف الأخطاء السريع**

### **البوت لا يعمل**
```bash
# 1. فحص الصحة
./health_check.py

# 2. فحص السجلات
tail -f logs/bot.log

# 3. فحص العمليات
ps aux | grep python

# 4. إعادة تشغيل
make restart
```

### **مشاكل العلامة المائية**
```bash
# 1. فحص FFmpeg
ffmpeg -version

# 2. فحص المكتبات
python -c "import cv2, PIL, numpy; print('OK')"

# 3. تنظيف الذاكرة المؤقتة
python -c "from watermark_processor import WatermarkProcessor; WatermarkProcessor().clear_cache()"
```

### **مشاكل قاعدة البيانات**
```bash
# 1. فحص الملف
ls -la *.db

# 2. إعادة إنشاء
rm telegram_bot.db
python main.py

# 3. فحص الصلاحيات
chmod 644 *.db
```

---

## ❓ **المشاكل الشائعة**

### **1. خطأ: "FFmpeg not found"**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS
brew install ffmpeg

# التحقق
ffmpeg -version
```

### **2. خطأ: "Module not found"**
```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# أو التثبيت التلقائي
./install_dependencies.sh
```

### **3. خطأ: "Permission denied"**
```bash
# إعطاء صلاحيات التنفيذ
chmod +x *.sh
chmod +x *.py

# فحص الصلاحيات
ls -la
```

### **4. خطأ: "Database locked"**
```bash
# إيقاف البوت
make stop

# انتظار قليل
sleep 5

# إعادة تشغيل
make start
```

---

## 📱 **قنوات الدعم**

### **GitHub**
- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Wiki**: [GitHub Wiki](https://github.com/your-repo/wiki)

### **Telegram**
- **المجموعة الرئيسية**: [@EnhancedBotGroup](https://t.me/EnhancedBotGroup)
- **قناة الأخبار**: [@EnhancedBotNews](https://t.me/EnhancedBotNews)
- **الدعم المباشر**: [@EnhancedBotSupport](https://t.me/EnhancedBotSupport)

### **البريد الإلكتروني**
- **الدعم العام**: support@your-domain.com
- **المشاكل التقنية**: tech@your-domain.com
- **المشاكل الأمنية**: security@your-domain.com

---

## 🧪 **اختبار البوت**

### **اختبار أساسي**
```bash
# 1. فحص الصحة
make health-check

# 2. اختبار المكتبات
python -c "
import telethon, cv2, PIL, numpy
print('✅ جميع المكتبات تعمل')
"

# 3. اختبار FFmpeg
ffmpeg -i test.mp4 -f null - 2>/dev/null && echo "✅ FFmpeg يعمل"
```

### **اختبار العلامة المائية**
```python
# اختبار معالج العلامة المائية
from watermark_processor import WatermarkProcessor

processor = WatermarkProcessor()

# اختبار إنشاء علامة مائية نصية
watermark_settings = {
    'enabled': True,
    'watermark_type': 'text',
    'watermark_text': 'اختبار',
    'position': 'bottom_right'
}

# اختبار معالجة صورة
# (أضف صورة اختبار)
```

---

## 📊 **تشخيص المشاكل**

### **فحص الموارد**
```bash
# الذاكرة
free -h

# المساحة
df -h

# المعالج
top -bn1

# الشبكة
netstat -tulpn
```

### **فحص السجلات**
```bash
# السجلات المباشرة
tail -f logs/bot.log

# البحث عن أخطاء
grep -i "error\|exception\|traceback" logs/bot.log

# البحث عن تحذيرات
grep -i "warning" logs/bot.log

# آخر 100 سطر
tail -100 logs/bot.log
```

### **فحص العمليات**
```bash
# عمليات Python
ps aux | grep python

# عمليات FFmpeg
ps aux | grep ffmpeg

# استخدام المنافذ
lsof -i :8000
```

---

## 🔄 **إعادة تعيين البوت**

### **إعادة تعيين كاملة**
```bash
# 1. إيقاف البوت
make stop

# 2. نسخ احتياطية
make backup

# 3. تنظيف
make clean

# 4. إعادة تثبيت
make install

# 5. إعادة تشغيل
make start
```

### **إعادة تعيين قاعدة البيانات**
```bash
# 1. إيقاف البوت
make stop

# 2. نسخ احتياطية
cp telegram_bot.db telegram_bot.db.backup

# 3. حذف قاعدة البيانات
rm telegram_bot.db

# 4. إعادة تشغيل
make start
```

---

## 📋 **قوالب التقارير**

### **تقرير مشكلة**
```markdown
## وصف المشكلة
[وصف واضح للمشكلة]

## خطوات إعادة الإنتاج
1. [خطوة 1]
2. [خطوة 2]
3. [خطوة 3]

## السلوك المتوقع
[ما كان يجب أن يحدث]

## السلوك الفعلي
[ما حدث بالفعل]

## معلومات النظام
- OS: [مثل Ubuntu 20.04]
- Python: [مثل 3.9.0]
- FFmpeg: [مثل 4.4]
- إصدار البوت: [مثل 2.0.0]

## السجلات
```
[أضف السجلات هنا]
```

## معلومات إضافية
[أي معلومات أخرى مفيدة]
```

### **طلب ميزة**
```markdown
## الميزة المطلوبة
[وصف الميزة]

## المشكلة التي تحلها
[اشرح لماذا هذه الميزة مفيدة]

## الحل المقترح
[وصف كيفية تنفيذ الميزة]

## البدائل المدروسة
[أي حلول أخرى فكرت فيها]

## معلومات إضافية
[أي معلومات أخرى مفيدة]
```

---

## 🚨 **حالات الطوارئ**

### **البوت لا يستجيب**
```bash
# 1. إيقاف فوري
pkill -f "python.*main.py"

# 2. فحص العمليات
ps aux | grep python

# 3. إعادة تشغيل
make start
```

### **مشاكل الذاكرة**
```bash
# 1. فحص الذاكرة
free -h

# 2. مسح الذاكرة المؤقتة
python -c "from watermark_processor import WatermarkProcessor; WatermarkProcessor().clear_cache()"

# 3. إعادة تشغيل
make restart
```

### **مشاكل الشبكة**
```bash
# 1. فحص الاتصال
ping 8.8.8.8

# 2. فحص DNS
nslookup google.com

# 3. فحص المنافذ
netstat -tulpn
```

---

## 📚 **الموارد المفيدة**

### **الوثائق الرسمية**
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [Telethon Documentation](https://docs.telethon.dev/)
- [FFmpeg Documentation](https://ffmpeg.org/documentation.html)
- [OpenCV Documentation](https://docs.opencv.org/)

### **أدوات مفيدة**
- [FFmpeg Online](https://ffmpeg-online.com/)
- [Python Debugger](https://docs.python.org/3/library/pdb.html)
- [Log Analyzer](https://loganalyzer.com/)

### **مجتمعات الدعم**
- [Stack Overflow](https://stackoverflow.com/)
- [Reddit Python](https://www.reddit.com/r/Python/)
- [Telegram Developers](https://t.me/TelegramDevelopers)

---

## 🎯 **نصائح للحصول على مساعدة أفضل**

### **قبل طلب المساعدة**
1. **اقرأ الوثائق** أولاً
2. **ابحث في المشاكل السابقة**
3. **اختبر المشكلة** بنفسك
4. **اجمع المعلومات** المطلوبة

### **عند طلب المساعدة**
1. **اكتب وصفاً واضحاً** للمشكلة
2. **أضف رسائل الخطأ** كاملة
3. **أضف معلومات النظام**
4. **أضف خطوات إعادة الإنتاج**

### **بعد الحصول على المساعدة**
1. **اختبر الحل** المقدم
2. **أبلغ عن النتيجة**
3. **ساعد الآخرين** إذا استطعت
4. **اكتب تعليقاً** شكراً

---

## 📞 **معلومات الاتصال**

### **فريق الدعم**
- **المدير**: [اسم المدير] - manager@your-domain.com
- **المطور الرئيسي**: [اسم المطور] - dev@your-domain.com
- **مدير الأمان**: [اسم مدير الأمان] - security@your-domain.com

### **أوقات العمل**
- **الأحد - الخميس**: 9:00 ص - 6:00 م (GMT+3)
- **الجمعة - السبت**: 10:00 ص - 4:00 م (GMT+3)
- **الطوارئ**: 24/7

### **الاستجابة المتوقعة**
- **المشاكل العاجلة**: خلال 2-4 ساعات
- **المشاكل العادية**: خلال 24 ساعة
- **طلبات الميزات**: خلال أسبوع
- **المشاكل المعقدة**: حسب التعقيد

---

## 🎉 **شكراً لك!**

شكراً لاستخدام البوت المحسن! نحن هنا لمساعدتك في أي وقت تحتاج فيه إلى دعم.

**💡 تذكر**: أفضل طريقة لتجنب المشاكل هي قراءة الوثائق والاختبار المنتظم!

---

**🆘 إذا لم تجد إجابة هنا، لا تتردد في التواصل معنا!**