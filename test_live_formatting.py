#!/usr/bin/env python3
"""
اختبار مباشر لتنسيق النصوص لتحديد السبب الجذري للمشكلة
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService

def test_live_formatting():
    """اختبار التنسيق المباشر باستخدام الكود الفعلي"""
    
    print("🧪 اختبار تنسيق النصوص المباشر")
    print("="*50)
    
    # إنشاء instance من UserbotService
    userbot = UserbotService()
    
    # نص للاختبار
    test_text = "بيان القوات المسلحة اليمنية"
    
    # اختبار تنسيقات مختلفة
    formats_to_test = [
        'quote',
        'spoiler', 
        'bold',
        'regular'
    ]
    
    for format_type in formats_to_test:
        try:
            result = userbot.apply_text_formatting_test(format_type, test_text)
            print(f"\n📝 {format_type.upper()}:")
            print(f"   الأصل: '{test_text}'")
            print(f"   النتيجة: '{result}'")
            
            # فحص النتيجة
            if format_type == 'quote':
                if '<blockquote>' in result:
                    print("   ✅ HTML blockquote صحيح")
                elif '>' in result:
                    print("   ❌ ما زال يستخدم markdown")
                else:
                    print("   ❓ تنسيق غير متوقع")
                    
            elif format_type == 'spoiler':
                if '<spoiler>' in result:
                    print("   ✅ HTML spoiler صحيح")
                elif '||' in result:
                    print("   ❌ ما زال يستخدم markdown")
                else:
                    print("   ❓ تنسيق غير متوقع")
                    
        except Exception as e:
            print(f"   ❌ خطأ: {e}")
    
    print("\n" + "="*50)
    print("💡 التشخيص:")
    print("- إذا كان HTML، فالمشكلة في parse_mode")
    print("- إذا كان markdown، فالمشكلة في الكود")

if __name__ == "__main__":
    test_live_formatting()