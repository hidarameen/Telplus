#!/usr/bin/env python3
"""
اختبار وظائف تنسيق النصوص
هذا البرنامج يختبر جميع وظائف التنسيق المختلفة
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService
from database.database import Database

def test_text_formatting():
    """اختبار جميع وظائف التنسيق"""
    print("🧪 بدء اختبار وظائف تنسيق النصوص...")
    
    # إنشاء قاعدة بيانات وهمية للاختبار
    db = Database()
    userbot = UserbotService()
    
    # نص للاختبار
    test_texts = [
        "نص عادي بدون تنسيق",
        "**نص عريض** في المنتصف",
        "*نص مائل* في البداية",
        "__نص تحته خط__",
        "`كود برمجي`",
        "```\nكود متعدد الأسطر\nسطر ثاني\n```",
        "> اقتباس في البداية",
        "نص مع ||نص مخفي|| في المنتصف",
        "[رابط](https://example.com)",
        "نص **عريض** و *مائل* و __تحته خط__ معاً"
    ]
    
    # اختبار كل نوع تنسيق
    format_types = [
        ('regular', 'عادي'),
        ('bold', 'عريض'),
        ('italic', 'مائل'),
        ('underline', 'تحته خط'),
        ('code', 'كود'),
        ('monospace', 'خط ثابت'),
        ('quote', 'اقتباس'),
        ('spoiler', 'مخفي'),
        ('strikethrough', 'مخطوط')
    ]
    
    print("\n" + "="*60)
    print("📝 اختبار تنظيف وتطبيق التنسيقات")
    print("="*60)
    
    for text in test_texts:
        print(f"\n📄 النص الأصلي: {text}")
        print("-" * 50)
        
        for format_type, format_name in format_types:
            # محاكاة إعدادات التنسيق
            formatted_text = userbot.apply_text_formatting_test(format_type, text)
            print(f"  {format_name:12} → {formatted_text}")
    
    # اختبار خاص للروابط
    print("\n" + "="*60)
    print("🔗 اختبار تنسيق الروابط")
    print("="*60)
    
    hyperlink_tests = [
        ("نص الرابط", "https://t.me/mychannel"),
        ("اضغط هنا", "https://google.com"),
        ("رابط طويل", "https://example.com/very/long/path?param=value"),
    ]
    
    for link_text, link_url in hyperlink_tests:
        formatted = f"[{link_text}]({link_url})"
        print(f"  {link_text:15} → {formatted}")
    
    print("\n✅ انتهى الاختبار!")

def main():
    """دالة رئيسية"""
    try:
        test_text_formatting()
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()