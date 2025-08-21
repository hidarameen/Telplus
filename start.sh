#!/bin/bash

# سكريبت تشغيل البوت المحسن
# Enhanced Bot Startup Script

echo "🚀 بدء تشغيل البوت المحسن..."
echo "=========================================="

# التحقق من وجود Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 غير مثبت"
    echo "يرجى تثبيت Python 3.8+"
    exit 1
fi

# التحقق من وجود FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo "⚠️ FFmpeg غير مثبت"
    echo "سيتم استخدام الوضع الأساسي بدون تحسين الفيديو"
    echo "لتثبيت FFmpeg: sudo apt install ffmpeg"
else
    echo "✅ FFmpeg مثبت"
    ffmpeg -version | head -n 1
fi

# التحقق من وجود ffprobe
if ! command -v ffprobe &> /dev/null; then
    echo "⚠️ ffprobe غير مثبت"
    echo "سيتم استخدام الوضع الأساسي"
else
    echo "✅ ffprobe مثبت"
fi

echo "=========================================="
echo "🔍 فحص المتطلبات..."

# التحقق من وجود الملفات المطلوبة
if [ ! -f "main.py" ]; then
    echo "❌ ملف main.py غير موجود"
    exit 1
fi

if [ ! -f "requirements.txt" ]; then
    echo "❌ ملف requirements.txt غير موجود"
    exit 1
fi

# التحقق من وجود مجلد السجلات
if [ ! -d "logs" ]; then
    echo "📁 إنشاء مجلد السجلات..."
    mkdir -p logs
fi

# التحقق من وجود مجلد البيانات
if [ ! -d "data" ]; then
    echo "📁 إنشاء مجلد البيانات..."
    mkdir -p data
fi

# التحقق من وجود مجلد الصور
if [ ! -d "watermark_images" ]; then
    echo "📁 إنشاء مجلد صور العلامة المائية..."
    mkdir -p watermark_images
fi

echo "=========================================="
echo "🐍 فحص مكتبات Python..."

# التحقق من المكتبات المطلوبة
python3 -c "
import sys
required_modules = ['telethon', 'opencv-python', 'PIL', 'numpy']
missing_modules = []

for module in required_modules:
    try:
        __import__(module.replace('-', '_'))
    except ImportError:
        missing_modules.append(module)

if missing_modules:
    print(f'❌ المكتبات المفقودة: {missing_modules}')
    print('يرجى تشغيل: pip install -r requirements.txt')
    sys.exit(1)
else:
    print('✅ جميع المكتبات المطلوبة مثبتة')
"

if [ $? -ne 0 ]; then
    echo "❌ فشل في فحص المكتبات"
    exit 1
fi

echo "=========================================="
echo "🔧 فحص الإعدادات..."

# التحقق من وجود ملف .env
if [ ! -f ".env" ]; then
    if [ -f ".env.example" ]; then
        echo "⚠️ ملف .env غير موجود"
        echo "يرجى نسخ .env.example إلى .env وتعديل الإعدادات"
        cp .env.example .env
        echo "✅ تم إنشاء ملف .env من .env.example"
        echo "يرجى تعديل الإعدادات قبل التشغيل"
        exit 1
    else
        echo "❌ ملف .env و .env.example غير موجودان"
        exit 1
    fi
fi

echo "✅ ملف .env موجود"

echo "=========================================="
echo "🚀 بدء تشغيل البوت..."

# تشغيل البوت
python3 main.py

# في حالة توقف البوت
echo ""
echo "=========================================="
echo "🔄 البوت توقف"
echo "لإعادة التشغيل: ./start.sh"
echo "للمساعدة: ./start.sh --help"