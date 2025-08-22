#!/bin/bash

# سكريبت حل مشكلة معرف القناة - رقم الهاتف
# Fix Chat ID Issue Script

echo "🔧 بدء حل مشكلة معرف القناة..."
echo "=================================="

# التحقق من وجود Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 غير مثبت"
    exit 1
fi

# التحقق من وجود الملفات المطلوبة
if [ ! -f "userbot_service/userbot.py" ]; then
    echo "❌ ملف userbot.py غير موجود"
    exit 1
fi

echo "✅ تم التحقق من الملفات المطلوبة"

# اختبار التحقق من المعرفات
echo ""
echo "🧪 اختبار التحقق من معرفات القنوات..."
python3 test_chat_id_validation.py

if [ $? -eq 0 ]; then
    echo "✅ تم اختبار التحقق من المعرفات بنجاح"
else
    echo "⚠️ هناك مشكلة في اختبار المعرفات"
fi

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
echo "🔘 اختبار الأزرار الإنلاين..."
python3 test_inline_buttons.py

if [ $? -eq 0 ]; then
    echo "✅ تم اختبار الأزرار بنجاح"
else
    echo "⚠️ هناك مشكلة في اختبار الأزرار"
fi

echo ""
echo "📋 ملخص الإصلاحات المطبقة:"
echo "1. ✅ تحسين التحقق من معرف القناة"
echo "2. ✅ كشف أرقام الهواتف تلقائياً"
echo "3. ✅ رسائل خطأ واضحة مع إرشادات"
echo "4. ✅ دعم معرفات القنوات الصحيحة"
echo "5. ✅ معالجة محسنة للأخطاء"

echo ""
echo "💡 المشكلة الأساسية:"
echo "   النظام كان يحاول استخدام رقم الهاتف 2638960177 كمعرف قناة"
echo "   البوت لا يستطيع الوصول للقنوات باستخدام أرقام الهواتف"

echo ""
echo "🔧 الحل:"
echo "   استخدم معرف القناة الصحيح مثل:"
echo "   - -1001234567890 (معرف قناة)"
echo "   - @channel_name (اسم القناة)"
echo "   - -123456789 (معرف مجموعة)"

echo ""
echo "📖 للمزيد من المعلومات:"
echo "- راجع ملف CHAT_ID_FIX.md"
echo "- راجع ملف README_INLINE_BUTTONS.md"
echo "- استخدم python3 test_chat_id_validation.py لاختبار المعرفات"
echo "- استخدم python3 check_bot_status.py لفحص البوت"

echo ""
echo "🎉 انتهى حل مشكلة معرف القناة!"
echo "=================================="