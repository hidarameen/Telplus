# 🔧 استكشاف أخطاء FFmpeg - FFmpeg Troubleshooting Guide

## 🚨 المشكلة الحالية
البوت يواجه مشكلة مع `ffprobe` و `ffmpeg` مما يؤدي إلى:
- فشل في الحصول على معلومات الفيديو
- فشل في تحسين ضغط الفيديو
- استخدام الملفات المؤقتة بدون معالجة

## ✅ الحلول المتاحة

### 1. **تثبيت FFmpeg (الحل الأمثل)**

#### Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg
```

#### CentOS/RHEL:
```bash
sudo yum install epel-release
sudo yum install ffmpeg
```

#### Alpine Linux:
```bash
apk add ffmpeg
```

#### macOS:
```bash
brew install ffmpeg
```

### 2. **التحقق من التثبيت**
```bash
ffmpeg -version
ffprobe -version
```

### 3. **الحل البديل (OpenCV)**
البوت الآن يدعم استخدام OpenCV كبديل لـ FFmpeg:
- ✅ الحصول على معلومات الفيديو
- ✅ معالجة الفيديو مع تقليل الدقة
- ✅ تقليل معدل الإطارات
- ✅ تحويل إلى MP4

## 🔍 تشخيص المشكلة

### رسائل الخطأ الشائعة:
```
ERROR - خطأ في الحصول على معلومات الفيديو: [Errno 2] No such file or directory: 'ffprobe'
WARNING - فشل في الحصول على معلومات الفيديو، استخدام إعدادات افتراضية
WARNING - فشل في تحسين الفيديو، استخدام الملف المؤقت
```

### أسباب المشكلة:
1. **FFmpeg غير مثبت** على النظام
2. **FFmpeg غير موجود** في PATH
3. **صلاحيات غير كافية** لتشغيل FFmpeg
4. **إصدار قديم** من FFmpeg

## 🛠️ الحلول التفصيلية

### الحل 1: تثبيت FFmpeg
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y ffmpeg

# التحقق من التثبيت
which ffmpeg
which ffprobe
```

### الحل 2: إضافة FFmpeg إلى PATH
```bash
# البحث عن FFmpeg
find /usr -name "ffmpeg" 2>/dev/null
find /usr -name "ffprobe" 2>/dev/null

# إضافة إلى PATH إذا كان في مجلد مختلف
export PATH="/usr/local/bin:$PATH"
```

### الحل 3: استخدام Docker
```bash
# تشغيل البوت في Docker مع FFmpeg
docker run --rm -it -v $(pwd):/app -w /app python:3.11-slim bash

# داخل الحاوية
apt update && apt install -y ffmpeg
pip install -r requirements.txt
python main.py
```

### الحل 4: استخدام OpenCV (مدمج)
البوت سيتعامل تلقائياً مع عدم وجود FFmpeg باستخدام OpenCV.

## 📊 مقارنة الأداء

| الميزة | FFmpeg | OpenCV |
|--------|--------|--------|
| **سرعة المعالجة** | ⚡ سريع جداً | 🐌 بطيء نسبياً |
| **جودة الضغط** | 🎯 ممتازة | 🎯 جيدة |
| **استهلاك الذاكرة** | 💾 منخفض | 💾 متوسط |
| **دعم الصيغ** | 📹 شامل | 📹 محدود |
| **سهولة التثبيت** | ⚠️ يتطلب تثبيت | ✅ مدمج |

## 🔧 إعدادات متقدمة

### 1. **تخصيص إعدادات FFmpeg**
```python
# في watermark_processor.py
ffmpeg_settings = {
    'video_codec': 'libx264',
    'preset': 'medium',
    'crf': '23',
    'audio_codec': 'aac',
    'audio_bitrate': '128k'
}
```

### 2. **تخصيص إعدادات OpenCV**
```python
# في watermark_processor.py
opencv_settings = {
    'scale_factor': 0.8,
    'fps_factor': 0.9,
    'quality': 'high'
}
```

## 📝 سجل التغييرات

### الإصدار 2.1.0:
- ✅ إضافة دعم OpenCV كبديل لـ FFmpeg
- ✅ تحسين معالجة الفيديو بدون FFmpeg
- ✅ تقليل الدقة ومعدل الإطارات تلقائياً
- ✅ رسائل خطأ أكثر وضوحاً

### الإصدار 2.0.0:
- ✅ معالجة الوسائط مرة واحدة
- ✅ نظام التخزين المؤقت
- ✅ تنظيف الملفات المؤقتة

## 🚀 التوصيات

### للمطورين:
1. **تثبيت FFmpeg** للحصول على أفضل أداء
2. **اختبار OpenCV** كبديل احتياطي
3. **مراقبة السجلات** للتأكد من عمل المعالجة

### للمستخدمين:
1. **تثبيت FFmpeg** إذا أمكن
2. **البقاء على الإصدار الحالي** إذا لم يكن ممكناً
3. **الإبلاغ عن المشاكل** مع السجلات

## 📞 الدعم

### إذا استمرت المشكلة:
1. **تحقق من السجلات** للحصول على تفاصيل أكثر
2. **اختبر FFmpeg** يدوياً
3. **أعد تشغيل البوت** بعد التثبيت
4. **تواصل مع الدعم** مع نسخة من السجلات

### معلومات مفيدة:
- إصدار Python: `python --version`
- إصدار OpenCV: `python -c "import cv2; print(cv2.__version__)"`
- إصدار FFmpeg: `ffmpeg -version`
- نظام التشغيل: `uname -a`

---

**ملاحظة**: البوت يعمل الآن بشكل صحيح حتى بدون FFmpeg، لكن الأداء سيكون أفضل مع تثبيته.