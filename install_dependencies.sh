#!/bin/bash

# ===== سكريبت تثبيت التبعيات - Dependencies Installation Script =====
# هذا السكريبت يقوم بتثبيت جميع التبعيات المطلوبة للبوت

set -e  # إيقاف السكريبت عند حدوث خطأ

echo "🚀 بدء تثبيت تبعيات البوت المحسن..."

# ===== التحقق من نظام التشغيل =====
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    if command -v apt-get &> /dev/null; then
        OS_TYPE="debian"
        echo "✅ تم اكتشاف نظام Debian/Ubuntu"
    elif command -v yum &> /dev/null; then
        OS_TYPE="rhel"
        echo "✅ تم اكتشاف نظام CentOS/RHEL"
    elif command -v apk &> /dev/null; then
        OS_TYPE="alpine"
        echo "✅ تم اكتشاف نظام Alpine Linux"
    else
        echo "⚠️ نظام تشغيل غير معروف، قد تحتاج لتثبيت التبعيات يدوياً"
        OS_TYPE="unknown"
    fi
elif [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    OS_TYPE="macos"
    echo "✅ تم اكتشاف نظام macOS"
else
    echo "⚠️ نظام تشغيل غير مدعوم: $OSTYPE"
    OS_TYPE="unknown"
fi

# ===== تثبيت FFmpeg =====
echo ""
echo "🎬 تثبيت FFmpeg..."

install_ffmpeg() {
    case $OS_TYPE in
        "debian")
            echo "📦 تثبيت FFmpeg على Ubuntu/Debian..."
            sudo apt-get update
            sudo apt-get install -y ffmpeg
            ;;
        "rhel")
            echo "📦 تثبيت FFmpeg على CentOS/RHEL..."
            sudo yum install -y epel-release
            sudo yum install -y ffmpeg
            ;;
        "alpine")
            echo "📦 تثبيت FFmpeg على Alpine Linux..."
            apk add ffmpeg
            ;;
        "macos")
            echo "📦 تثبيت FFmpeg على macOS..."
            if command -v brew &> /dev/null; then
                brew install ffmpeg
            else
                echo "❌ Homebrew غير مثبت. قم بتثبيته أولاً:"
                echo "   /bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
                exit 1
            fi
            ;;
        *)
            echo "⚠️ تثبيت FFmpeg يدوياً:"
            echo "   Ubuntu/Debian: sudo apt install ffmpeg"
            echo "   CentOS/RHEL: sudo yum install ffmpeg"
            echo "   Alpine: apk add ffmpeg"
            echo "   macOS: brew install ffmpeg"
            echo "   Windows: https://ffmpeg.org/download.html"
            ;;
    esac
}

# محاولة تثبيت FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    install_ffmpeg
else
    echo "✅ FFmpeg مثبت بالفعل"
fi

# التحقق من تثبيت FFmpeg
if command -v ffmpeg &> /dev/null; then
    FFMPEG_VERSION=$(ffmpeg -version | head -1 | cut -d' ' -f3)
    echo "✅ FFmpeg مثبت بنجاح - الإصدار: $FFMPEG_VERSION"
    
    # التحقق من ffprobe
    if command -v ffprobe &> /dev/null; then
        echo "✅ ffprobe متوفر أيضاً"
    else
        echo "⚠️ ffprobe غير متوفر، قد تحتاج لتثبيت حزمة إضافية"
    fi
else
    echo "❌ فشل في تثبيت FFmpeg"
    echo "💡 البوت سيعمل باستخدام OpenCV كبديل، لكن الأداء سيكون أقل"
fi

# ===== تثبيت Python =====
echo ""
echo "🐍 التحقق من Python..."

if ! command -v python3 &> /dev/null; then
    echo "📦 تثبيت Python 3..."
    case $OS_TYPE in
        "debian")
            sudo apt-get install -y python3 python3-pip python3-venv
            ;;
        "rhel")
            sudo yum install -y python3 python3-pip
            ;;
        "alpine")
            apk add python3 py3-pip
            ;;
        "macos")
            if command -v brew &> /dev/null; then
                brew install python3
            else
                echo "❌ Homebrew غير مثبت"
                exit 1
            fi
            ;;
    esac
else
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    echo "✅ Python 3 مثبت - الإصدار: $PYTHON_VERSION"
fi

# ===== إنشاء بيئة افتراضية =====
echo ""
echo "🔧 إنشاء بيئة افتراضية..."

if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "✅ تم إنشاء البيئة الافتراضية"
else
    echo "✅ البيئة الافتراضية موجودة بالفعل"
fi

# ===== تفعيل البيئة الافتراضية =====
echo "🔄 تفعيل البيئة الافتراضية..."
source venv/bin/activate

# ===== ترقية pip =====
echo "📦 ترقية pip..."
python -m pip install --upgrade pip

# ===== تثبيت تبعيات Python =====
echo ""
echo "📦 تثبيت تبعيات Python..."

if [ -f "requirements.txt" ]; then
    echo "📋 تثبيت من requirements.txt..."
    pip install -r requirements.txt
    echo "✅ تم تثبيت جميع تبعيات Python"
else
    echo "⚠️ ملف requirements.txt غير موجود"
fi

# ===== تثبيت تبعيات التطوير (اختيارية) =====
if [ -f "requirements-dev.txt" ]; then
    echo ""
    echo "🔧 تثبيت تبعيات التطوير (اختيارية)..."
    read -p "هل تريد تثبيت تبعيات التطوير؟ (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        pip install -r requirements-dev.txt
        echo "✅ تم تثبيت تبعيات التطوير"
    fi
fi

# ===== التحقق النهائي =====
echo ""
echo "🔍 التحقق النهائي من التثبيت..."

# التحقق من Python packages
echo "📦 تبعيات Python:"
pip list --format=columns | grep -E "(opencv|pillow|numpy|telethon)"

# التحقق من FFmpeg
if command -v ffmpeg &> /dev/null; then
    echo "✅ FFmpeg: متوفر"
    ffmpeg -version | head -1
else
    echo "⚠️ FFmpeg: غير متوفر (البوت سيعمل مع OpenCV)"
fi

# ===== رسالة النجاح =====
echo ""
echo "🎉 تم تثبيت جميع التبعيات بنجاح!"
echo ""
echo "📋 ملخص التثبيت:"
echo "   ✅ Python 3 + pip"
echo "   ✅ البيئة الافتراضية"
echo "   ✅ تبعيات Python"
if command -v ffmpeg &> /dev/null; then
    echo "   ✅ FFmpeg (أداء مثالي)"
else
    echo "   ⚠️ FFmpeg (البوت سيعمل مع OpenCV)"
fi
echo ""
echo "🚀 لتشغيل البوت:"
echo "   source venv/bin/activate"
echo "   python main.py"
echo ""
echo "💡 نصائح:"
if ! command -v ffmpeg &> /dev/null; then
    echo "   - لتثبيت FFmpeg لاحقاً: sudo apt install ffmpeg (Ubuntu/Debian)"
    echo "   - أو: sudo yum install ffmpeg (CentOS/RHEL)"
fi
echo "   - لتحديث التبعيات: pip install -r requirements.txt --upgrade"
echo "   - لإزالة البيئة الافتراضية: rm -rf venv"

echo ""
echo "✨ البوت جاهز للتشغيل!"