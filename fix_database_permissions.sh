#!/bin/bash

echo "🚀 بدء إصلاح قاعدة البيانات..."

# التحقق من وجود Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 غير مثبت"
    exit 1
fi

# تشغيل سكريبت إصلاح قاعدة البيانات
echo "🔧 تشغيل سكريبت إصلاح قاعدة البيانات..."
python3 fix_database_permissions.py

# التحقق من الصلاحيات بعد الإصلاح
echo ""
echo "📋 فحص الصلاحيات بعد الإصلاح:"
if [ -f "telegram_bot.db" ]; then
    echo "📁 telegram_bot.db:"
    ls -la telegram_bot.db
else
    echo "⚠️ ملف telegram_bot.db غير موجود"
fi

echo ""
echo "✅ انتهى إصلاح قاعدة البيانات"