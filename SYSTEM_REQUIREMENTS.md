# 🔧 متطلبات النظام - System Requirements

## 📋 **نظرة عامة**
هذا المستند يوضح الفرق بين متطلبات Python ومتطلبات النظام، وكيفية تثبيتها.

## 🐍 **متطلبات Python (Python Requirements)**

### التثبيت:
```bash
pip install -r requirements.txt
```

### الملفات المطلوبة:
- `requirements.txt` - يحتوي على مكتبات Python
- `requirements-dev.txt` - مكتبات التطوير (اختيارية)

## 🖥️ **متطلبات النظام (System Requirements)**

### 1. **FFmpeg - أداة معالجة الوسائط**

#### ما هو FFmpeg؟
- **أداة نظام** (system tool) لمعالجة الوسائط
- **غير مدمجة** مع Python
- **يجب تثبيتها منفصلة** على النظام

#### لماذا نحتاجها؟
- ضغط الفيديو المتقدم
- تحويل صيغ الوسائط
- استخراج معلومات الفيديو
- معالجة الصوت

#### كيفية التثبيت:

##### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg
```

##### CentOS/RHEL:
```bash
sudo yum install epel-release
sudo yum install ffmpeg
```

##### Alpine Linux:
```bash
apk add ffmpeg
```

##### macOS:
```bash
brew install ffmpeg
```

##### Windows:
1. تحميل من: https://ffmpeg.org/download.html
2. إضافة إلى PATH

#### التحقق من التثبيت:
```bash
ffmpeg -version
ffprobe -version
```

### 2. **Python 3.8+**

#### Ubuntu/Debian:
```bash
sudo apt install python3 python3-pip
```

#### CentOS/RHEL:
```bash
sudo yum install python3 python3-pip
```

#### Alpine:
```bash
apk add python3 py3-pip
```

### 3. **مكتبات النظام الأخرى**

#### Ubuntu/Debian:
```bash
sudo apt install build-essential python3-dev
```

#### CentOS/RHEL:
```bash
sudo yum groupinstall "Development Tools"
sudo yum install python3-devel
```

## 🔍 **الفرق بين Python Packages و System Tools**

| النوع | Python Packages | System Tools |
|-------|----------------|--------------|
| **التثبيت** | `pip install` | `apt install` / `yum install` |
| **الموقع** | مجلد Python | مجلد النظام |
| **الاستخدام** | `import package` | `subprocess.run(['tool'])` |
| **المثال** | `import cv2` | `ffmpeg -i input.mp4 output.mp4` |

## 📦 **تفاصيل المكتبات**

### ffmpeg-python
```python
# مكتبة Python للتفاعل مع FFmpeg
import ffmpeg

# لكن FFmpeg نفسه يجب أن يكون مثبت على النظام
```

### opencv-python
```python
# مكتبة Python مدمجة - لا تحتاج أدوات نظام إضافية
import cv2
```

## 🚀 **سيناريوهات التشغيل**

### 1. **مع FFmpeg (الأفضل)**
```bash
# تثبيت FFmpeg
sudo apt install ffmpeg

# تثبيت Python packages
pip install -r requirements.txt

# البوت سيعمل بأقصى كفاءة
```

### 2. **بدون FFmpeg (البديل)**
```bash
# تثبيت Python packages فقط
pip install -r requirements.txt

# البوت سيعمل باستخدام OpenCV كبديل
# الأداء سيكون أقل لكنه يعمل
```

### 3. **في Docker**
```dockerfile
# Dockerfile يتضمن FFmpeg تلقائياً
FROM python:3.11-slim
RUN apt-get update && apt-get install -y ffmpeg
```

## 🔧 **استكشاف الأخطاء**

### مشكلة: "No such file or directory: 'ffmpeg'"
**الحل**: تثبيت FFmpeg على النظام

### مشكلة: "ffmpeg-python import error"
**الحل**: `pip install ffmpeg-python`

### مشكلة: "OpenCV not found"
**الحل**: `pip install opencv-python`

## 📚 **أمثلة عملية**

### استخدام FFmpeg مباشرة:
```bash
# ضغط فيديو
ffmpeg -i input.mp4 -c:v libx264 -crf 23 output.mp4

# استخراج معلومات
ffprobe -v quiet -print_format json -show_format input.mp4
```

### استخدام Python مع FFmpeg:
```python
import subprocess

# تشغيل FFmpeg
result = subprocess.run(['ffmpeg', '-i', 'input.mp4', 'output.mp4'])
```

### استخدام OpenCV (بدون FFmpeg):
```python
import cv2

# معالجة الفيديو
cap = cv2.VideoCapture('input.mp4')
```

## 🎯 **التوصيات**

### للمطورين:
1. **تثبيت FFmpeg** للحصول على أفضل أداء
2. **اختبار البدائل** للتأكد من التوافق
3. **توثيق المتطلبات** بوضوح

### للمستخدمين:
1. **قراءة المتطلبات** قبل التثبيت
2. **تثبيت FFmpeg** إذا أمكن
3. **البقاء على البديل** إذا لم يكن ممكناً

## 📞 **الدعم**

### إذا واجهت مشاكل:
1. **تحقق من تثبيت FFmpeg**: `ffmpeg -version`
2. **تحقق من Python packages**: `pip list`
3. **راجع السجلات** للحصول على تفاصيل الخطأ
4. **تواصل مع الدعم** مع معلومات النظام

---

**ملاحظة مهمة**: `ffmpeg-python` هي مكتبة Python، لكن FFmpeg نفسه أداة نظام يجب تثبيتها منفصلة!