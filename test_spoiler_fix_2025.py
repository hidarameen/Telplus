#!/usr/bin/env python3
"""
اختبار إصلاح تنسيق النص المخفي (Spoiler) لعام 2025
Test the spoiler text formatting fix for 2025
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService

def test_spoiler_fix_2025():
    """اختبار تطبيق تنسيق النص المخفي المُحدث"""
    
    print("🧪 اختبار إصلاح النص المخفي (Spoiler) 2025")
    print("="*60)
    
    userbot = UserbotService()
    
    test_cases = [
        ("نص مخفي للاختبار", "نص مخفي للاختبار"),
        ("نص مع ||spoiler|| موجود", "نص مع spoiler موجود"),
        ("نص مع <tg-spoiler>spoiler</tg-spoiler>", "نص مع spoiler"),
        ("نص مع <span class=\"tg-spoiler\">spoiler</span>", "نص مع spoiler"),
        ("**نص عريض** مع ||مخفي||", "نص عريض مع مخفي"),
        ("نص نظيف تماماً", "نص نظيف تماماً"),
        ("نص مع تنسيق مختلط *مائل* و ||مخفي||", "نص مع تنسيق مختلط مائل و مخفي")
    ]
    
    print("\n🔍 اختبار تنسيق النص المخفي الجديد:")
    print("-" * 60)
    
    for i, (input_text, expected_clean) in enumerate(test_cases, 1):
        # اختبار spoiler formatting
        result = userbot.apply_text_formatting_test('spoiler', input_text)
        
        # استخراج النص المنظف من النتيجة
        import re
        
        # Check for new format first
        clean_match = re.search(r'<span class="tg-spoiler">(.*?)</span>', result)
        if not clean_match:
            # Fallback to old format
            clean_match = re.search(r'<tg-spoiler>(.*?)</tg-spoiler>', result)
            
        actual_clean = clean_match.group(1) if clean_match else result.strip()
        
        print(f"\n{i}. اختبار: '{input_text}'")
        print(f"   متوقع نظيف: '{expected_clean}'")
        print(f"   فعلي نظيف: '{actual_clean}'")
        print(f"   نتيجة spoiler: '{result}'")
        
        # فحص النتيجة
        if actual_clean == expected_clean:
            print(f"   ✅ التنظيف صحيح")
        else:
            print(f"   ❌ التنظيف خاطئ")
            
        # فحص التنسيق الصحيح للتليثون
        if '<tg-spoiler>' in result and '</tg-spoiler>' in result:
            print(f"   ✅ التنسيق صحيح للتليثون - يستخدم <tg-spoiler>")
        elif '<span class="tg-spoiler">' in result:
            print(f"   ⚠️ يستخدم تنسيق البوت API - <span class=\"tg-spoiler\"> (قد لا يعمل مع التليثون)")
        else:
            print(f"   ❌ تنسيق غير متوقع")
    
    print("\n" + "="*60)
    print("✅ انتهى اختبار إصلاح النص المخفي 2025")

if __name__ == "__main__":
    test_spoiler_fix_2025()