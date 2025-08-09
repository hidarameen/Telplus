
#!/usr/bin/env python3
"""
اختبار شامل لإصلاح النص المخفي (spoiler) في Telethon
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService

def test_spoiler_fix():
    """اختبار إصلاح spoiler مع Telethon"""
    
    print("🧪 اختبار إصلاح النص المخفي (Spoiler)")
    print("="*60)
    
    userbot = UserbotService()
    test_text = "نص مخفي للاختبار"
    
    # اختبار spoiler
    print("\n🔍 اختبار النص المخفي")
    print("-" * 40)
    
    spoiler_result = userbot.apply_text_formatting_test('spoiler', test_text)
    print(f"النص الأصلي: '{test_text}'")
    print(f"النتيجة: '{spoiler_result}'")
    
    # فحص التنسيق الصحيح لـ Telethon
    expected_format = f'<tg-spoiler>{test_text}</tg-spoiler>'
    
    if spoiler_result == expected_format:
        print("✅ تنسيق spoiler صحيح - يستخدم <tg-spoiler> كما هو مطلوب في Telethon")
        print("✅ HTML السليم:", spoiler_result)
    elif '<span class="tg-spoiler">' in spoiler_result:
        print("❌ تنسيق spoiler خاطئ - يستخدم <span> بدلاً من <tg-spoiler>")
        print("❌ HTML الخاطئ:", spoiler_result)
        print("✅ HTML المطلوب:", expected_format)
    else:
        print("❓ تنسيق spoiler غير متوقع:", spoiler_result)
    
    # اختبار الروابط للتأكد من سلامتها
    print("\n🔗 اختبار الروابط (للتأكد من سلامتها)")
    print("-" * 40)
    
    hyperlink_result = userbot.apply_text_formatting_test('hyperlink', test_text)
    print(f"نتيجة الرابط: '{hyperlink_result}'")
    
    if '<a href=' in hyperlink_result and '</a>' in hyperlink_result:
        print("✅ الروابط تعمل بشكل صحيح")
    else:
        print("❌ مشكلة في الروابط")
    
    print("\n" + "="*60)
    print("📋 تقرير نهائي")
    print("="*60)
    
    # التحقق من جميع التنسيقات
    formats_to_test = {
        'spoiler': '<tg-spoiler>',
        'hyperlink': '<a href=',
        'bold': '<b>',
        'italic': '<i>',
        'quote': '<blockquote>'
    }
    
    all_good = True
    for format_type, expected_tag in formats_to_test.items():
        result = userbot.apply_text_formatting_test(format_type, test_text)
        if expected_tag in result:
            print(f"✅ {format_type}: صحيح")
        else:
            print(f"❌ {format_type}: خاطئ - {result}")
            all_good = False
    
    if all_good:
        print("\n🎉 جميع التنسيقات تعمل بشكل صحيح!")
        print("🚀 النص المخفي جاهز للاستخدام في تليجرام")
    else:
        print("\n⚠️ ما زالت هناك مشاكل في بعض التنسيقات")

if __name__ == "__main__":
    test_spoiler_fix()
