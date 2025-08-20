# 🔧 دليل استكشاف الأخطاء الشامل - Complete Troubleshooting Guide

## 🚨 **نظرة عامة على استكشاف الأخطاء**

هذا الدليل يغطي جميع المشاكل الشائعة التي قد تواجهها مع البوت المحسن لـ Telegram وكيفية حلها. يبدأ من المشاكل البسيطة وينتهي بالمشاكل المعقدة.

---

## ⚡ **المشاكل العاجلة (حلول سريعة)**

### **البوت لا يعمل**
```bash
# 1. فحص سريع
./health_check.py

# 2. إعادة تشغيل
make restart

# 3. فحص السجلات
tail -f logs/bot.log
```

### **مشاكل العلامة المائية**
```bash
# 1. فحص FFmpeg
ffmpeg -version

# 2. مسح الذاكرة المؤقتة
python3 -c "from watermark_processor import WatermarkProcessor; WatermarkProcessor().clear_cache()"

# 3. إعادة تشغيل
make restart
```

### **مشاكل قاعدة البيانات**
```bash
# 1. إيقاف البوت
make stop

# 2. انتظار قليل
sleep 5

# 3. إعادة تشغيل
make start
```

---

## 🔍 **تشخيص المشاكل**

### **1️⃣ فحص شامل للنظام**
```bash
# فحص الصحة الكامل
./health_check.py

# فحص الموارد
make resources

# فحص العمليات
make status
```

### **2️⃣ فحص السجلات**
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

### **3️⃣ فحص الشبكة**
```bash
# فحص الاتصال
ping 8.8.8.8

# فحص DNS
nslookup google.com

# فحص المنافذ
netstat -tulpn | grep python
```

---

## ❓ **المشاكل الشائعة وحلولها**

### **1. خطأ: "FFmpeg not found"**

#### **الوصف**
```
خطأ في الحصول على معلومات الفيديو: [Errno 2] No such file or directory: 'ffprobe'
```

#### **الحل**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS
brew install ffmpeg

# التحقق من التثبيت
ffmpeg -version
ffprobe -version
```

#### **التحقق**
```bash
# فحص وجود FFmpeg
which ffmpeg
which ffprobe

# اختبار المعالجة
ffmpeg -i test.mp4 -f null - 2>/dev/null && echo "✅ FFmpeg يعمل"
```

---

### **2. خطأ: "Module not found"**

#### **الوصف**
```
ModuleNotFoundError: No module named 'telethon'
```

#### **الحل**
```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# أو التثبيت التلقائي
./install_dependencies.sh

# إعادة تشغيل البوت
make restart
```

#### **التحقق**
```python
# اختبار المكتبات
python3 -c "
import telethon, cv2, PIL, numpy, flask
print('✅ جميع المكتبات تعمل')
"
```

---

### **3. خطأ: "Permission denied"**

#### **الوصف**
```
PermissionError: [Errno 13] Permission denied: 'start.sh'
```

#### **الحل**
```bash
# إعطاء صلاحيات التنفيذ
chmod +x *.sh
chmod +x *.py

# فحص الصلاحيات
ls -la

# تشغيل كـ مستخدم عادي (ليس root)
./start.sh
```

#### **التحقق**
```bash
# فحص الصلاحيات
ls -la *.sh *.py

# فحص المستخدم الحالي
whoami
```

---

### **4. خطأ: "Database locked"**

#### **الوصف**
```
sqlite3.OperationalError: database is locked
```

#### **الحل**
```bash
# 1. إيقاف البوت
make stop

# 2. انتظار قليل
sleep 5

# 3. فحص العمليات
ps aux | grep python

# 4. إعادة تشغيل
make start
```

#### **التحقق**
```bash
# فحص قاعدة البيانات
ls -la *.db

# فحص العمليات
ps aux | grep python

# فحص المنافذ
lsof -i :8000
```

---

### **5. خطأ: "Memory error"**

#### **الوصف**
```
MemoryError: Unable to allocate array
```

#### **الحل**
```python
# مسح الذاكرة المؤقتة
from watermark_processor import WatermarkProcessor
processor = WatermarkProcessor()
processor.clear_cache()

# أو من Python console
python3 -c "from watermark_processor import WatermarkProcessor; WatermarkProcessor().clear_cache()"
```

#### **التحقق**
```bash
# فحص الذاكرة
free -h

# فحص العمليات
ps aux | grep python | grep -v grep
```

---

### **6. خطأ: "Network timeout"**

#### **الوصف**
```
telethon.errors.NetworkError: Connection timeout
```

#### **الحل**
```bash
# 1. فحص الاتصال
ping 8.8.8.8

# 2. فحص DNS
nslookup google.com

# 3. إعادة تشغيل الشبكة
sudo systemctl restart NetworkManager

# 4. إعادة تشغيل البوت
make restart
```

#### **التحقق**
```bash
# فحص الاتصال
curl -I https://api.telegram.org

# فحص المنافذ
netstat -tulpn | grep python
```

---

## 🎬 **مشاكل معالجة الوسائط**

### **1. مشاكل العلامة المائية**

#### **العلامة المائية لا تظهر**
```python
# فحص الإعدادات
watermark_settings = {
    'enabled': True,  # تأكد من التفعيل
    'watermark_type': 'text',
    'watermark_text': 'نص العلامة المائية',
    'position': 'bottom_right',
    'opacity': 80,
    'size_percentage': 50
}

# فحص الخط
from PIL import ImageFont
try:
    font = ImageFont.truetype("arial.ttf", 24)
    print("✅ الخط يعمل")
except:
    print("❌ مشكلة في الخط")
```

#### **العلامة المائية مشوهة**
```python
# فحص حجم الصورة
from PIL import Image
img = Image.open("test.jpg")
print(f"حجم الصورة: {img.size}")

# ضبط حجم العلامة المائية
watermark_settings['size_percentage'] = 30  # 30% من حجم الصورة
```

### **2. مشاكل معالجة الفيديو**

#### **الفيديو لا يتم معالجته**
```bash
# فحص FFmpeg
ffmpeg -version

# اختبار معالجة فيديو
ffmpeg -i test.mp4 -c:v libx264 -crf 23 output.mp4

# فحص السجلات
grep -i "video\|ffmpeg" logs/bot.log
```

#### **الفيديو يزداد في الحجم**
```python
# فحص إعدادات الضغط
video_settings = {
    'codec': 'libx264',
    'preset': 'medium',
    'crf': 23,  # جودة ثابتة
    'maxrate': '1000k',  # معدل بت أقصى
    'bufsize': '2000k'
}

# تطبيق الضغط
success = watermark_processor.optimize_video_compression(
    input_path, output_path, target_size_mb=50
)
```

---

## 🔐 **مشاكل الأمان**

### **1. مشاكل المفاتيح**

#### **مفاتيح API غير صحيحة**
```bash
# فحص متغيرات البيئة
echo $API_ID
echo $API_HASH
echo $BOT_TOKEN

# أو فحص ملف .env
cat .env | grep -E "API_ID|API_HASH|BOT_TOKEN"
```

#### **مفاتيح API منتهية الصلاحية**
```bash
# 1. إنشاء مفاتيح جديدة
# اذهب إلى https://my.telegram.org

# 2. تحديث ملف .env
nano .env

# 3. إعادة تشغيل البوت
make restart
```

### **2. مشاكل الصلاحيات**

#### **صلاحيات ملف .env**
```bash
# تعيين صلاحيات صحيحة
chmod 600 .env

# فحص الصلاحيات
ls -la .env

# يجب أن تكون: -rw------- (600)
```

---

## 💾 **مشاكل الذاكرة والموارد**

### **1. استهلاك الذاكرة العالي**

#### **فحص استخدام الذاكرة**
```bash
# فحص الذاكرة
free -h

# فحص العمليات
ps aux --sort=-%mem | head -10

# فحص الذاكرة المؤقتة
python3 -c "
from watermark_processor import WatermarkProcessor
stats = WatermarkProcessor().get_cache_stats()
print(f'حجم الذاكرة المؤقتة: {stats}')
"
```

#### **تنظيف الذاكرة**
```python
# مسح الذاكرة المؤقتة
watermark_processor.clear_cache()

# تنظيف garbage collector
import gc
gc.collect()

# إعادة تشغيل البوت
make restart
```

### **2. مشاكل القرص**

#### **فحص مساحة القرص**
```bash
# فحص المساحة
df -h

# فحص الملفات الكبيرة
find . -type f -size +100M

# تنظيف الملفات المؤقتة
make clean
```

---

## 🌐 **مشاكل الشبكة**

### **1. مشاكل الاتصال**

#### **فحص الاتصال**
```bash
# فحص الإنترنت
ping 8.8.8.8

# فحص DNS
nslookup api.telegram.org

# فحص HTTPS
curl -I https://api.telegram.org
```

#### **حل مشاكل DNS**
```bash
# تغيير DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
echo "nameserver 8.8.4.4" | sudo tee -a /etc/resolv.conf

# إعادة تشغيل الشبكة
sudo systemctl restart NetworkManager
```

### **2. مشاكل البروكسي**

#### **إعداد البروكسي**
```bash
# تعيين متغيرات البروكسي
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port

# أو في ملف .env
echo "HTTP_PROXY=http://proxy:port" >> .env
echo "HTTPS_PROXY=http://proxy:port" >> .env
```

---

## 🐳 **مشاكل Docker**

### **1. مشاكل بناء الصورة**

#### **خطأ في بناء Docker**
```bash
# تنظيف الصور
docker system prune -a

# إعادة بناء
docker build --no-cache -t enhanced-telegram-bot .

# فحص الصور
docker images
```

#### **مشاكل في docker-compose**
```bash
# إيقاف وإعادة تشغيل
docker-compose down
docker-compose up -d

# فحص السجلات
docker-compose logs -f
```

### **2. مشاكل الصلاحيات**

#### **مشاكل صلاحيات Docker**
```bash
# إضافة المستخدم لمجموعة docker
sudo usermod -aG docker $USER

# إعادة تسجيل الدخول
newgrp docker

# اختبار Docker
docker run hello-world
```

---

## 🔄 **إعادة تعيين كاملة**

### **1. إعادة تعيين البوت**
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

### **2. إعادة تعيين قاعدة البيانات**
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

### **3. إعادة تعيين النظام**
```bash
# 1. إيقاف البوت
make stop

# 2. إعادة تشغيل النظام
sudo reboot

# 3. انتظار إعادة التشغيل
# 4. تشغيل البوت
make start
```

---

## 📞 **طلب المساعدة**

### **1️⃣ قبل طلب المساعدة**
- [ ] اقرأ هذا الدليل بعناية
- [ ] جرب الحلول المقترحة
- [ ] اجمع معلومات النظام
- [ ] التقط لقطة شاشة للخطأ

### **2️⃣ معلومات مطلوبة**
```bash
# معلومات النظام
uname -a
python3 --version
ffmpeg -version

# معلومات البوت
cat VERSION
./health_check.py

# السجلات
tail -50 logs/bot.log
```

### **3️⃣ قنوات المساعدة**
- **GitHub Issues**: [your-repo/issues](https://github.com/your-repo/issues)
- **Telegram Group**: [@EnhancedBotGroup](https://t.me/EnhancedBotGroup)
- **البريد الإلكتروني**: support@your-domain.com

---

## 📋 **قائمة فحص استكشاف الأخطاء**

### **مشاكل أساسية**
- [ ] البوت لا يعمل
- [ ] مشاكل العلامة المائية
- [ ] مشاكل قاعدة البيانات
- [ ] مشاكل الذاكرة

### **مشاكل تقنية**
- [ ] FFmpeg غير مثبت
- [ ] مكتبات Python مفقودة
- [ ] مشاكل الصلاحيات
- [ ] مشاكل الشبكة

### **مشاكل متقدمة**
- [ ] مشاكل Docker
- [ ] مشاكل الأداء
- [ ] مشاكل الأمان
- [ ] مشاكل التكامل

---

## 🎉 **الخلاصة**

مع هذا الدليل الشامل، يمكنك حل معظم المشاكل التي تواجهها مع البوت المحسن:

- 🔍 **تشخيص دقيق** للمشاكل
- 🛠️ **حلول عملية** ومجربة
- 📚 **مراجع شاملة** لكل مشكلة
- 🚀 **حلول سريعة** للمشاكل العاجلة

**🎯 البوت المحسن مصمم ليعمل بسلاسة مع دعم فني شامل!**

---

**🔧 إذا لم تجد حلاً هنا، لا تتردد في طلب المساعدة!**