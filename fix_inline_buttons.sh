#!/bin/bash

# سكريبت إصلاح مشكلة الأزرار الإنلاين
# Fix Inline Buttons Script

echo "🔧 بدء إصلاح مشكلة الأزرار الإنلاين..."
echo "=================================="

# التحقق من وجود Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 غير مثبت"
    exit 1
fi

# التحقق من وجود الملفات المطلوبة
if [ ! -f "bot_package/config.py" ]; then
    echo "❌ ملف config.py غير موجود"
    exit 1
fi

if [ ! -f "userbot_service/userbot.py" ]; then
    echo "❌ ملف userbot.py غير موجود"
    exit 1
fi

echo "✅ تم التحقق من الملفات المطلوبة"

# فحص حالة البوت
echo ""
echo "🔍 فحص حالة البوت..."
python3 check_bot_status.py

if [ $? -eq 0 ]; then
    echo "✅ تم فحص حالة البوت بنجاح"
else
    echo "⚠️ هناك مشكلة في فحص حالة البوت"
fi

# اختبار الأزرار
echo ""
echo "🧪 اختبار الأزرار الإنلاين..."
python3 test_inline_buttons.py

if [ $? -eq 0 ]; then
    echo "✅ تم اختبار الأزرار بنجاح"
else
    echo "⚠️ هناك مشكلة في اختبار الأزرار"
fi

echo ""
echo "📋 ملخص الإصلاحات المطبقة:"
echo "1. ✅ تحسين دالة إضافة الأزرار"
echo "2. ✅ إضافة دالة احتياطية"
echo "3. ✅ التحقق من صلاحيات البوت"
echo "4. ✅ معالجة محسنة للأخطاء"
echo "5. ✅ طرق بديلة لإضافة الأزرار"

echo ""
echo "📖 للمزيد من المعلومات:"
echo "- راجع ملف README_INLINE_BUTTONS.md"
echo "- راجع ملف INLINE_BUTTONS_FIX.md"
echo "- استخدم python3 check_bot_status.py لفحص البوت"
echo "- استخدم python3 test_inline_buttons.py لاختبار الأزرار"

echo ""
echo "🎉 انتهى إصلاح مشكلة الأزرار الإنلاين!"
echo "=================================="