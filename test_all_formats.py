#!/usr/bin/env python3
"""
اختبار شامل لجميع أنماط التنسيق
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService

def test_all_formats():
    """اختبار جميع أنماط التنسيق"""
    
    print("🧪 اختبار شامل لجميع أنماط التنسيق")
    print("="*60)
    
    userbot = UserbotService()
    test_text = "اختبار التنسيق"
    
    # جميع أنماط التنسيق
    formats = {
        'regular': 'عادي',
        'bold': 'عريض', 
        'italic': 'مائل',
        'underline': 'تحت خط',
        'strikethrough': 'مشطوب',
        'code': 'كود',
        'monospace': 'كود متعدد الأسطر',
        'quote': 'اقتباس',
        'spoiler': 'مخفي'
    }
    
    for format_type, description in formats.items():
        try:
            result = userbot.apply_text_formatting_test(format_type, test_text)
            
            print(f"\n📝 {description} ({format_type}):")
            print(f"   الأصل: '{test_text}'")
            print(f"   النتيجة: '{result}'")
            
            # فحص التنسيق
            if format_type == 'regular':
                status = "✅" if result == test_text else "❌"
            elif format_type == 'bold':
                status = "✅" if '<b>' in result and '</b>' in result else "❌"
            elif format_type == 'italic':
                status = "✅" if '<i>' in result and '</i>' in result else "❌"
            elif format_type == 'underline':
                status = "✅" if '<u>' in result and '</u>' in result else "❌"
            elif format_type == 'strikethrough':
                status = "✅" if '<s>' in result and '</s>' in result else "❌"
            elif format_type == 'code':
                status = "✅" if '<code>' in result and '</code>' in result else "❌"
            elif format_type == 'monospace':
                status = "✅" if '<pre>' in result and '</pre>' in result else "❌"
            elif format_type == 'quote':
                status = "✅" if '<blockquote>' in result and '</blockquote>' in result else "❌"
            elif format_type == 'spoiler':
                status = "✅" if '<span class="tg-spoiler">' in result and '</span>' in result else "❌"
            else:
                status = "❓"
                
            print(f"   الحالة: {status}")
            
        except Exception as e:
            print(f"   ❌ خطأ: {e}")
    
    print("\n" + "="*60)
    print("🎯 ملخص النتائج:")
    print("✅ = HTML صحيح")
    print("❌ = تنسيق خاطئ")
    print("❓ = غير محدد")

if __name__ == "__main__":
    test_all_formats()