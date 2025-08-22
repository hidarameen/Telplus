#!/bin/bash

# سكريبت فحص وإصلاح معرفات القنوات في قاعدة البيانات
# Fix Database Chat IDs Script

echo "🔧 فحص وإصلاح معرفات القنوات في قاعدة البيانات..."
echo "=================================================="

# التحقق من وجود Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python3 غير مثبت"
    exit 1
fi

# التحقق من وجود الملفات المطلوبة
if [ ! -f "database/database.py" ]; then
    echo "❌ ملف database.py غير موجود"
    exit 1
fi

if [ ! -f "userbot_service/userbot.py" ]; then
    echo "❌ ملف userbot.py غير موجود"
    exit 1
fi

echo "✅ تم التحقق من الملفات المطلوبة"

# فحص قاعدة البيانات
echo ""
echo "🔍 فحص قاعدة البيانات للبحث عن معرفات قنوات غير صحيحة..."
python3 fix_chat_ids_in_database.py

if [ $? -eq 0 ]; then
    echo "✅ تم فحص قاعدة البيانات بنجاح"
else
    echo "⚠️ هناك مشكلة في فحص قاعدة البيانات"
fi

echo ""
echo "📋 ملخص المشكلة والحل:"
echo "1. ❌ المشكلة: معرف القناة 2638960177 هو رقم هاتف وليس معرف قناة"
echo "2. ✅ الحل: استخدم معرف قناة صحيح يبدأ بـ -100"
echo "3. 🔧 الإصلاح: فحص قاعدة البيانات وتحديث المعرفات غير الصحيحة"

echo ""
echo "💡 أمثلة على معرفات القنوات الصحيحة:"
echo "   - -1001234567890 (معرف قناة)"
echo "   - @channel_name (اسم القناة)"
echo "   - -123456789 (معرف مجموعة)"

echo ""
echo "📖 للمزيد من المعلومات:"
echo "- راجع ملف CHAT_ID_FIX.md"
echo "- راجع ملف FINAL_SOLUTION.md"
echo "- استخدم python3 fix_chat_ids_in_database.py لفحص قاعدة البيانات"
echo "- استخدم python3 test_chat_id_validation.py لاختبار المعرفات"

echo ""
echo "🎉 انتهى فحص قاعدة البيانات!"
echo "=================================================="