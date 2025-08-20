# 📥 دليل التثبيت الشامل - Complete Installation Guide

## 🎯 **نظرة عامة على التثبيت**

هذا الدليل يوضح كيفية تثبيت البوت المحسن لـ Telegram على مختلف أنظمة التشغيل. يغطي جميع الطرق الممكنة للتثبيت والتشغيل.

---

## 🚀 **التثبيت السريع (5 دقائق)**

### **1️⃣ تثبيت FFmpeg**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# macOS
brew install ffmpeg

# Windows
# قم بتحميل FFmpeg من https://ffmpeg.org/download.html
```

### **2️⃣ تثبيت Python**
```bash
# Ubuntu/Debian
sudo apt install python3 python3-pip python3-venv

# CentOS/RHEL
sudo yum install python3 python3-pip

# macOS
brew install python3

# Windows
# قم بتحميل Python من https://python.org/downloads/
```

### **3️⃣ نسخ المشروع**
```bash
git clone https://github.com/your-repo/enhanced-telegram-bot.git
cd enhanced-telegram-bot
```

### **4️⃣ التثبيت التلقائي**
```bash
# إعطاء صلاحيات التنفيذ
chmod +x *.sh

# التثبيت التلقائي
./install_dependencies.sh
```

### **5️⃣ إعداد البيئة**
```bash
# نسخ ملف الإعدادات
cp .env.example .env

# تعديل الإعدادات
nano .env
```

### **6️⃣ تشغيل البوت**
```bash
# تشغيل تلقائي
./start.sh

# أو تشغيل يدوي
python3 main.py
```

---

## 🐳 **التثبيت باستخدام Docker**

### **متطلبات Docker**
```bash
# تثبيت Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# تثبيت Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### **تشغيل البوت**
```bash
# بناء وتشغيل
docker-compose up -d

# أو باستخدام Make
make docker-run

# عرض السجلات
docker-compose logs -f

# إيقاف البوت
docker-compose down
```

---

## 🛠️ **التثبيت باستخدام Make**

### **التثبيت الكامل**
```bash
# تثبيت FFmpeg والمتطلبات
make full-install

# أو خطوة بخطوة
make install-ffmpeg
make install
make setup-env
```

### **أوامر مفيدة**
```bash
# تشغيل البوت
make start

# إيقاف البوت
make stop

# إعادة تشغيل
make restart

# فحص الصحة
make health-check

# تنظيف
make clean

# نسخ احتياطي
make backup
```

---

## 🔧 **التثبيت اليدوي**

### **1. إنشاء بيئة افتراضية**
```bash
# إنشاء البيئة
python3 -m venv venv

# تفعيل البيئة
source venv/bin/activate  # Linux/macOS
# أو
venv\Scripts\activate     # Windows
```

### **2. تثبيت المكتبات**
```bash
# تحديث pip
pip install --upgrade pip setuptools wheel

# تثبيت المتطلبات الأساسية
pip install -r requirements.txt

# تثبيت متطلبات التطوير (اختياري)
pip install -r requirements-dev.txt
```

### **3. إعداد قاعدة البيانات**
```bash
# إنشاء مجلدات مطلوبة
mkdir -p data logs watermark_images

# تعيين الصلاحيات
chmod 755 data logs watermark_images
```

---

## 📱 **التثبيت على أنظمة مختلفة**

### **Ubuntu 20.04+**
```bash
# تحديث النظام
sudo apt update && sudo apt upgrade

# تثبيت المتطلبات الأساسية
sudo apt install -y \
    python3 \
    python3-pip \
    python3-venv \
    python3-dev \
    build-essential \
    libssl-dev \
    libffi-dev \
    ffmpeg \
    git \
    curl \
    wget

# نسخ المشروع
git clone https://github.com/your-repo/enhanced-telegram-bot.git
cd enhanced-telegram-bot

# التثبيت التلقائي
./install_dependencies.sh
```

### **CentOS 8+ / RHEL 8+**
```bash
# تحديث النظام
sudo dnf update

# تثبيت المتطلبات الأساسية
sudo dnf install -y \
    python3 \
    python3-pip \
    python3-devel \
    gcc \
    gcc-c++ \
    make \
    openssl-devel \
    ffmpeg \
    git \
    curl \
    wget

# نسخ المشروع
git clone https://github.com/your-repo/enhanced-telegram-bot.git
cd enhanced-telegram-bot

# التثبيت التلقائي
./install_dependencies.sh
```

### **macOS 11+**
```bash
# تثبيت Homebrew (إذا لم يكن مثبتاً)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# تثبيت المتطلبات الأساسية
brew install \
    python3 \
    ffmpeg \
    git \
    curl \
    wget

# نسخ المشروع
git clone https://github.com/your-repo/enhanced-telegram-bot.git
cd enhanced-telegram-bot

# التثبيت التلقائي
./install_dependencies.sh
```

### **Windows 10+**
```bash
# تثبيت Chocolatey (إذا لم يكن مثبتاً)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# تثبيت المتطلبات الأساسية
choco install \
    python3 \
    ffmpeg \
    git \
    curl

# نسخ المشروع
git clone https://github.com/your-repo/enhanced-telegram-bot.git
cd enhanced-telegram-bot

# التثبيت التلقائي
./install_dependencies.sh
```

---

## 🔐 **إعداد الأمان**

### **1. إنشاء مفاتيح Telegram**
```bash
# 1. اذهب إلى https://my.telegram.org
# 2. سجل دخولك برقم هاتفك
# 3. اذهب إلى "API development tools"
# 4. أنشئ تطبيق جديد
# 5. انسخ api_id و api_hash
```

### **2. إنشاء بوت**
```bash
# 1. ابحث عن @BotFather في Telegram
# 2. أرسل /newbot
# 3. اتبع التعليمات
# 4. انسخ BOT_TOKEN
```

### **3. إعداد ملف .env**
```bash
# نسخ ملف المثال
cp .env.example .env

# تعديل الإعدادات
nano .env

# إضافة المفاتيح
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_here
```

---

## 🧪 **اختبار التثبيت**

### **1. فحص الصحة**
```bash
# فحص شامل
./health_check.py

# أو باستخدام Make
make health-check
```

### **2. اختبار المكتبات**
```python
# اختبار المكتبات المطلوبة
python3 -c "
import telethon, cv2, PIL, numpy, flask
print('✅ جميع المكتبات تعمل')
"
```

### **3. اختبار FFmpeg**
```bash
# اختبار FFmpeg
ffmpeg -version

# اختبار ffprobe
ffprobe -version

# اختبار معالجة فيديو
ffmpeg -i test.mp4 -f null - 2>/dev/null && echo "✅ FFmpeg يعمل"
```

---

## 🚨 **استكشاف الأخطاء**

### **مشكلة: "FFmpeg not found"**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg

# التحقق من التثبيت
which ffmpeg
ffmpeg -version
```

### **مشكلة: "Module not found"**
```bash
# إعادة تثبيت المكتبات
pip install --force-reinstall -r requirements.txt

# أو استخدام pip3
pip3 install -r requirements.txt
```

### **مشكلة: "Permission denied"**
```bash
# إعطاء صلاحيات التنفيذ
chmod +x *.sh
chmod +x *.py

# فحص الصلاحيات
ls -la
```

### **مشكلة: "Database locked"**
```bash
# إيقاف البوت
make stop

# انتظار قليل
sleep 5

# إعادة تشغيل
make start
```

---

## 📊 **مراقبة التثبيت**

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
```

---

## 🔄 **التحديث**

### **تحديث البوت**
```bash
# باستخدام Make
make update

# أو يدوياً
git pull origin main
pip install -r requirements.txt --upgrade
```

### **تحديث المكتبات**
```bash
# تحديث جميع المكتبات
pip list --outdated
pip install --upgrade -r requirements.txt

# فحص الثغرات
pip-audit
safety check
```

---

## 📋 **قائمة فحص التثبيت**

### **قبل التثبيت**
- [ ] تثبيت Python 3.8+
- [ ] تثبيت FFmpeg
- [ ] تثبيت Git
- [ ] إنشاء حساب Telegram
- [ ] الحصول على مفاتيح API

### **أثناء التثبيت**
- [ ] نسخ المشروع
- [ ] تثبيت المكتبات
- [ ] إعداد البيئة
- [ ] تكوين المفاتيح
- [ ] إنشاء المجلدات

### **بعد التثبيت**
- [ ] فحص الصحة
- [ ] اختبار المكتبات
- [ ] اختبار FFmpeg
- [ ] تشغيل البوت
- [ ] اختبار الوظائف

---

## 📞 **المساعدة**

### **إذا واجهت مشاكل**
1. **اقرأ هذا الدليل** بعناية
2. **تحقق من المتطلبات** الأساسية
3. **راجع السجلات** للأخطاء
4. **استخدم فحص الصحة** `./health_check.py`
5. **اطلب المساعدة** في GitHub Issues

### **قنوات الدعم**
- **GitHub Issues**: [your-repo/issues](https://github.com/your-repo/issues)
- **Telegram Group**: [@EnhancedBotGroup](https://t.me/EnhancedBotGroup)
- **البريد الإلكتروني**: support@your-domain.com

---

## 🎉 **مبروك!**

إذا وصلت إلى هنا، فهذا يعني أنك قمت بتثبيت البوت المحسن بنجاح! 🎉

### **الخطوات التالية**
1. **اقرأ README.md** للحصول على معلومات مفصلة
2. **جرب الميزات** المختلفة
3. **شارك تجربتك** مع المجتمع
4. **ساعد الآخرين** في التثبيت

---

**🚀 البوت المحسن جاهز للاستخدام! استمتع بالتجربة!**