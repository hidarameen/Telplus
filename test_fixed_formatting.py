
#!/usr/bin/env python3
"""
اختبار شامل للتنسيق المُصحح
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService

def test_fixed_formatting():
    """اختبار التنسيق المُصحح لـ spoiler والروابط"""
    
    print("🧪 اختبار التنسيق المُصحح")
    print("="*60)
    
    userbot = UserbotService()
    test_text = "نص للاختبار"
    
    # اختبار النص المخفي (spoiler)
    print("\n🔍 اختبار النص المخفي (Spoiler)")
    print("-" * 40)
    spoiler_result = userbot.apply_text_formatting_test('spoiler', test_text)
    print(f"النص الأصلي: '{test_text}'")
    print(f"النتيجة: '{spoiler_result}'")
    
    # فحص صحة spoiler
    if '<tg-spoiler>' in spoiler_result and '</tg-spoiler>' in spoiler_result:
        print("✅ تنسيق spoiler صحيح - يستخدم <tg-spoiler>")
    elif '<span class="tg-spoiler">' in spoiler_result:
        print("❌ تنسيق spoiler خاطئ - ما زال يستخدم <span>")
    else:
        print("❓ تنسيق spoiler غير متوقع")
    
    # اختبار الرابط (hyperlink)
    print("\n🔗 اختبار الرابط (Hyperlink)")
    print("-" * 40)
    hyperlink_result = userbot.apply_text_formatting_test('hyperlink', test_text)
    print(f"النص الأصلي: '{test_text}'")
    print(f"النتيجة: '{hyperlink_result}'")
    
    # فحص صحة hyperlink
    if '<a href=' in hyperlink_result and '</a>' in hyperlink_result:
        print("✅ تنسيق hyperlink صحيح - يستخدم HTML <a>")
    elif '[' in hyperlink_result and '](' in hyperlink_result:
        print("❌ تنسيق hyperlink خاطئ - ما زال يستخدم Markdown")
    else:
        print("❓ تنسيق hyperlink غير متوقع")
    
    # اختبار تنسيقات أخرى للتأكد أنها لم تتأثر
    print("\n🔧 اختبار التنسيقات الأخرى")
    print("-" * 40)
    
    other_formats = {
        'bold': ('<b>', '</b>'),
        'italic': ('<i>', '</i>'),
        'quote': ('<blockquote>', '</blockquote>'),
        'code': ('<code>', '</code>')
    }
    
    for format_type, (start_tag, end_tag) in other_formats.items():
        result = userbot.apply_text_formatting_test(format_type, test_text)
        if start_tag in result and end_tag in result:
            print(f"✅ {format_type}: صحيح")
        else:
            print(f"❌ {format_type}: خاطئ - '{result}'")
    
    print("\n" + "="*60)
    print("📋 ملخص نتائج الاختبار")
    print("="*60)
    
    # ملخص نهائي
    spoiler_ok = '<tg-spoiler>' in spoiler_result
    hyperlink_ok = '<a href=' in hyperlink_result
    
    if spoiler_ok and hyperlink_ok:
        print("🎉 جميع الإصلاحات تعمل بشكل صحيح!")
        print("✅ النص المخفي يستخدم <tg-spoiler>")
        print("✅ الروابط تستخدم HTML <a href>")
        print("🚀 جاهز للاختبار في تليجرام")
    else:
        print("⚠️ ما زالت هناك مشاكل:")
        if not spoiler_ok:
            print("❌ النص المخفي لا يعمل")
        if not hyperlink_ok:
            print("❌ الروابط لا تعمل")

if __name__ == "__main__":
    test_fixed_formatting()
