# 🔒 دليل الأمان - Security Guide

## 🚨 **الإبلاغ عن ثغرات الأمان**

إذا اكتشفت ثغرة أمنية، **لا تفتح issue عادي** على GitHub. بدلاً من ذلك:

### **📧 الإبلاغ الخاص**
- أرسل بريد إلكتروني إلى: `security@your-domain.com`
- أو استخدم: [GitHub Security Advisories](https://github.com/your-repo/security/advisories)

### **⏰ الاستجابة**
- سنرد خلال **24-48 ساعة**
- سنقوم بتقييم الثغرة
- سنطور إصلاحاً
- سننشر تحديث أمني

---

## 🛡️ **ممارسات الأمان**

### **1️⃣ حماية المفاتيح**
```bash
# ❌ خطأ - لا تفعل هذا
API_ID=12345
API_HASH=abcdef123456789

# ✅ صحيح - استخدم متغيرات البيئة
API_ID=${API_ID}
API_HASH=${API_HASH}
```

### **2️⃣ ملف .env**
```bash
# أضف .env إلى .gitignore
echo ".env" >> .gitignore

# استخدم .env.example للمثال
cp .env.example .env
```

### **3️⃣ تحديث المكتبات**
```bash
# تحديث دوري
pip install --upgrade -r requirements.txt

# فحص الثغرات
pip-audit
safety check
```

---

## 🔐 **إعدادات الأمان**

### **متغيرات البيئة المطلوبة**
```bash
# Telegram API
API_ID=your_api_id
API_HASH=your_api_hash
BOT_TOKEN=your_bot_token

# التشفير
SECRET_KEY=your_secret_key_here

# قاعدة البيانات
DATABASE_URL=sqlite:///telegram_bot.db

# الأمان
DEBUG=false
LOG_LEVEL=INFO
ALLOWED_HOSTS=localhost,127.0.0.1
```

### **إعدادات قاعدة البيانات**
```python
# تشفير البيانات الحساسة
from cryptography.fernet import Fernet

class SecureDatabase:
    def __init__(self):
        self.cipher = Fernet(os.getenv('ENCRYPTION_KEY'))
    
    def encrypt_data(self, data: str) -> bytes:
        return self.cipher.encrypt(data.encode())
    
    def decrypt_data(self, encrypted_data: bytes) -> str:
        return self.cipher.decrypt(encrypted_data).decode()
```

---

## 🚫 **ممارسات محظورة**

### **❌ لا تفعل**
- لا تشارك مفاتيح API
- لا تضع كلمات مرور في الكود
- لا تستخدم DEBUG=true في الإنتاج
- لا تفتح منافذ غير ضرورية
- لا تستخدم HTTP بدون تشفير

### **✅ افعل**
- استخدم HTTPS دائماً
- شفر البيانات الحساسة
- حدث المكتبات بانتظام
- استخدم كلمات مرور قوية
- راجع السجلات بانتظام

---

## 🔍 **فحص الأمان**

### **أدوات الفحص**
```bash
# فحص الثغرات
bandit -r .
safety check
pip-audit

# فحص التبعيات
safety check --full-report

# فحص الكود
pylint --disable=C0114,C0116 your_file.py
```

### **فحص التكوين**
```bash
# فحص متغيرات البيئة
python -c "import os; print('API_ID:', 'SET' if os.getenv('API_ID') else 'NOT SET')"

# فحص الملفات
ls -la .env*
chmod 600 .env
```

---

## 🚨 **استجابة الحوادث**

### **خطة الاستجابة**
1. **تحديد** - اكتشاف الحادث
2. **احتواء** - منع انتشار الضرر
3. **استئصال** - إزالة السبب
4. **استرداد** - إعادة الخدمة
5. **تعلم** - تحسين الأمان

### **خطوات فورية**
```bash
# إيقاف البوت
make stop

# فحص السجلات
tail -f logs/bot.log | grep -i "error\|warning\|security"

# فحص العمليات
ps aux | grep python

# فحص الشبكة
netstat -tulpn | grep python
```

---

## 🔒 **تشفير البيانات**

### **تشفير الملفات**
```python
import cryptography
from cryptography.fernet import Fernet

def encrypt_file(file_path: str, key: bytes) -> bytes:
    """تشفير ملف"""
    cipher = Fernet(key)
    with open(file_path, 'rb') as f:
        data = f.read()
    return cipher.encrypt(data)

def decrypt_file(encrypted_data: bytes, key: bytes) -> bytes:
    """فك تشفير ملف"""
    cipher = Fernet(key)
    return cipher.decrypt(encrypted_data)
```

### **تشفير قاعدة البيانات**
```python
# تشفير البيانات الحساسة
class SecureUser:
    def __init__(self, username: str, password: str):
        self.username = username
        self.encrypted_password = self.encrypt_password(password)
    
    def encrypt_password(self, password: str) -> bytes:
        return self.cipher.encrypt(password.encode())
    
    def verify_password(self, password: str) -> bool:
        return self.cipher.decrypt(self.encrypted_password).decode() == password
```

---

## 🛡️ **حماية الشبكة**

### **جدار الحماية**
```bash
# فتح المنافذ المطلوبة فقط
sudo ufw allow 8000/tcp
sudo ufw allow 22/tcp
sudo ufw enable

# فحص المنافذ المفتوحة
sudo netstat -tulpn
```

### **VPN & Proxy**
```bash
# استخدام VPN
sudo apt install openvpn

# إعدادات البروكسي
export HTTP_PROXY=http://proxy:port
export HTTPS_PROXY=http://proxy:port
```

---

## 📊 **مراقبة الأمان**

### **سجلات الأمان**
```python
import logging
from datetime import datetime

# إعداد سجلات الأمان
security_logger = logging.getLogger('security')
security_logger.setLevel(logging.INFO)

def log_security_event(event_type: str, details: str):
    """تسجيل حدث أمني"""
    timestamp = datetime.now().isoformat()
    security_logger.info(f"[{timestamp}] {event_type}: {details}")
```

### **تنبيهات الأمان**
```python
def send_security_alert(message: str):
    """إرسال تنبيه أمني"""
    # إرسال إلى المشرف
    # إرسال بريد إلكتروني
    # إرسال إشعار
    pass
```

---

## 🔐 **إدارة المفاتيح**

### **توليد المفاتيح**
```python
import secrets
import string

def generate_secure_key(length: int = 32) -> str:
    """توليد مفتاح آمن"""
    alphabet = string.ascii_letters + string.digits + string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_encryption_key() -> bytes:
    """توليد مفتاح تشفير"""
    return Fernet.generate_key()
```

### **تخزين المفاتيح**
```bash
# استخدام keyring
pip install keyring

# أو استخدام متغيرات البيئة
export ENCRYPTION_KEY=$(python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

---

## 🚨 **سيناريوهات الطوارئ**

### **اختراق الحساب**
1. **فوري**: تغيير كلمة المرور
2. **فوري**: إيقاف البوت
3. **خلال ساعة**: مراجعة السجلات
4. **خلال 24 ساعة**: تقرير الحادث

### **تسرب البيانات**
1. **فوري**: تحديد نطاق التسرب
2. **فوري**: إيقاف الخدمة
3. **خلال ساعة**: إشعار المستخدمين
4. **خلال 24 ساعة**: تقرير للسلطات

---

## 📋 **قائمة فحص الأمان**

### **قبل النشر**
- [ ] فحص الثغرات
- [ ] تشفير البيانات الحساسة
- [ ] إعداد جدار الحماية
- [ ] تحديث المكتبات
- [ ] فحص التكوين

### **بعد النشر**
- [ ] مراقبة السجلات
- [ ] فحص الأداء
- [ ] مراجعة الأمان
- [ ] تحديث دوري
- [ ] نسخ احتياطية

---

## 📞 **اتصال الطوارئ**

### **معلومات الاتصال**
- **الأمان**: security@your-domain.com
- **المشرف**: admin@your-domain.com
- **الدعم**: support@your-domain.com

### **أرقام الطوارئ**
- **الشرطة السيبرانية**: [رقم الطوارئ]
- **مزود الخدمة**: [معلومات الاتصال]

---

## 📚 **موارد إضافية**

### **أدوات الأمان**
- [OWASP](https://owasp.org/)
- [SANS Security](https://www.sans.org/)
- [CVE Database](https://cve.mitre.org/)

### **أفضل الممارسات**
- [Python Security](https://python-security.readthedocs.io/)
- [Telegram Security](https://core.telegram.org/security)

---

**🔒 الأمان مسؤولية الجميع. ساعدنا في الحفاظ على البوت آمناً!**