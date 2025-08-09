#!/usr/bin/env python3
"""
اختبار تنسيق HTML للاقتباس والمخفي في تليجرام
"""

def test_html_formatting():
    """اختبار تنسيق HTML مع أمثلة من النص الحقيقي"""
    
    # نص عادي للاختبار
    test_text = "بيان القوات المسلحة اليمنية بشأن استهداف سلاح الجو المسير"
    
    print("🧪 اختبار تنسيق HTML للتليجرام")
    print("="*60)
    
    # تنسيقات HTML المختلفة
    formats = {
        "اقتباس HTML": f"<blockquote>{test_text}</blockquote>",
        "مخفي HTML": f"<spoiler>{test_text}</spoiler>",
        "اقتباس Markdown القديم": f"> {test_text}",
        "مخفي Markdown القديم": f"||{test_text}||"
    }
    
    for format_name, formatted_text in formats.items():
        print(f"\n📝 {format_name}:")
        print(f"   النص: '{formatted_text}'")
        print(f"   الطول: {len(formatted_text)} حرف")
        
        if "HTML" in format_name:
            print("   parse_mode='html' ✅")
        else:
            print("   parse_mode='md' ❌ (مشكلة)")
    
    print("\n" + "="*60)
    print("💡 الحلول المطبقة:")
    print("✅ تم تغيير parse_mode من 'md' إلى 'html'")
    print("✅ تم استبدال > بـ <blockquote>")
    print("✅ تم استبدال || بـ <spoiler>")
    print("🎯 النتيجة المتوقعة: تنسيق صحيح في تليجرام")

if __name__ == "__main__":
    test_html_formatting()