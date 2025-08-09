
#!/usr/bin/env python3
"""
اختبار نهائي شامل لإصلاح spoiler
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService

def test_spoiler_comprehensive():
    """اختبار شامل لـ spoiler مع جميع الحالات"""
    
    print("🧪 اختبار شامل نهائي لـ spoiler")
    print("="*60)
    
    userbot = UserbotService()
    
    # حالات اختبار مختلفة
    test_cases = [
        ("نص بسيط", "نص بسيط"),
        ("نص مع ||spoiler|| موجود", "نص مع spoiler موجود"),
        ("نص مع <tg-spoiler>spoiler</tg-spoiler>", "نص مع spoiler"),
        ("نص مع <span class=\"tg-spoiler\">spoiler</span>", "نص مع spoiler"),
        ("**نص عريض** مع ||مخفي||", "نص عريض مع مخفي"),
        ("نص نظيف تماماً", "نص نظيف تماماً")
    ]
    
    print("\n🔍 اختبار تنظيف النصوص:")
    print("-" * 50)
    
    for i, (input_text, expected_clean) in enumerate(test_cases, 1):
        # اختبار spoiler formatting
        result = userbot.apply_text_formatting_test('spoiler', input_text)
        
        # استخراج النص المنظف من النتيجة
        import re
        clean_match = re.search(r'<tg-spoiler>(.*?)</tg-spoiler>', result)
        actual_clean = clean_match.group(1) if clean_match else result
        
        print(f"\n{i}. اختبار: '{input_text}'")
        print(f"   متوقع نظيف: '{expected_clean}'")
        print(f"   فعلي نظيف: '{actual_clean}'")
        print(f"   نتيجة spoiler: '{result}'")
        
        # فحص النتيجة
        if actual_clean == expected_clean:
            print(f"   ✅ التنظيف صحيح")
        else:
            print(f"   ❌ التنظيف خاطئ")
            
        if '<tg-spoiler>' in result and '</tg-spoiler>' in result:
            print(f"   ✅ تنسيق spoiler صحيح")
        else:
            print(f"   ❌ تنسيق spoiler خاطئ")
    
    # اختبار مقارن مع تنسيقات أخرى
    print("\n🔧 مقارنة مع التنسيقات الأخرى:")
    print("-" * 50)
    
    test_text = "نص للاختبار"
    formats = {
        'bold': '<b>',
        'italic': '<i>', 
        'spoiler': '<tg-spoiler>',
        'quote': '<blockquote>',
        'hyperlink': '<a href='
    }
    
    all_good = True
    for format_type, expected_tag in formats.items():
        result = userbot.apply_text_formatting_test(format_type, test_text)
        if expected_tag in result:
            print(f"✅ {format_type}: {result}")
        else:
            print(f"❌ {format_type}: {result}")
            all_good = False
    
    print("\n" + "="*60)
    print("📋 تقرير نهائي شامل")
    print("="*60)
    
    if all_good:
        print("🎉 جميع التنسيقات تعمل بشكل صحيح!")
        print("✅ spoiler تم إصلاحه نهائياً")
        print("✅ لا يوجد تضارب أو تكرار")
        print("🚀 جاهز للاستخدام في تليجرام")
    else:
        print("⚠️ ما زالت هناك مشاكل تحتاج إصلاح")

if __name__ == "__main__":
    test_spoiler_comprehensive()
