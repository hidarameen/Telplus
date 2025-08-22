
#!/bin/bash

# سكريبت تنصيب بوت التوجيه التلقائي
echo "🚀 بدء تنصيب بوت التوجيه التلقائي..."

# التحقق من وجود Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 غير مُنصب. يرجى تنصيب Python 3.8 أو أحدث"
    exit 1
fi

# التحقق من وجود pip
if ! command -v pip3 &> /dev/null; then
    echo "❌ pip3 غير مُنصب. يرجى تنصيب pip3"
    exit 1
fi

# إنشاء مجلد البيانات
echo "📁 إنشاء مجلدات البيانات..."
mkdir -p data
mkdir -p watermark_images
mkdir -p attached_assets

# نسخ ملف المتغيرات البيئية
if [ ! -f .env ]; then
    echo "📝 إنشاء ملف المتغيرات البيئية..."
    cp .env.example .env
    echo "⚠️  يرجى تحديث ملف .env بالقيم الصحيحة"
fi

# تنصيب المكتبات المطلوبة
echo "📦 تنصيب المكتبات المطلوبة..."
pip3 install -r requirements.txt

# إنشاء قاعدة البيانات
echo "🗄️ إنشاء قاعدة البيانات..."
python3 -c "
from database.database import Database
db = Database()
print('✅ تم إنشاء قاعدة البيانات بنجاح')
"

echo ""
echo "✅ تم تنصيب البوت بنجاح!"
echo ""
echo "📋 الخطوات التالية:"
echo "1. حدث ملف .env بمعلومات البوت الخاص بك"
echo "2. احصل على BOT_TOKEN من @BotFather"
echo "3. احصل على API_ID و API_HASH من my.telegram.org"
echo "4. شغل البوت باستخدام: python3 main.py"
echo ""
echo "🔧 للحصول على المساعدة:"
echo "- اقرأ ملف README.md"
echo "- تحقق من ملف replit.md للتفاصيل"
echo ""
