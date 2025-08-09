
#!/usr/bin/env python3
"""
اختبار تنسيق HTML لتليجرام
"""

def test_telegram_html_formats():
    """اختبار جميع تنسيقات HTML المدعومة في تليجرام"""
    
    test_text = "نص الاختبار"
    
    formats = {
        'عادي': test_text,
        'عريض': f'<b>{test_text}</b>',
        'مائل': f'<i>{test_text}</i>',
        'تحته خط': f'<u>{test_text}</u>',
        'مشطوب': f'<s>{test_text}</s>',
        'كود': f'<code>{test_text}</code>',
        'كود متعدد': f'<pre>{test_text}</pre>',
        'اقتباس': f'<blockquote>{test_text}</blockquote>',
        'مخفي': f'<tg-spoiler>{test_text}</tg-spoiler>',
        'رابط': f'<a href="https://t.me/mychannel">{test_text}</a>'
    }
    
    print("🧪 اختبار تنسيقات HTML لتليجرام")
    print("="*50)
    
    for format_name, formatted_text in formats.items():
        print(f"\n📝 {format_name}:")
        print(f"   HTML: {formatted_text}")
        
        # فحص صحة التنسيق
        if format_name == 'رابط':
            if '<a href=' in formatted_text and '</a>' in formatted_text:
                print("   ✅ تنسيق HTML صحيح للرابط")
            else:
                print("   ❌ تنسيق HTML خاطئ للرابط")
                
        elif format_name == 'مخفي':
            if '<tg-spoiler>' in formatted_text and '</tg-spoiler>' in formatted_text:
                print("   ✅ تنسيق HTML صحيح للنص المخفي")
            else:
                print("   ❌ تنسيق HTML خاطئ للنص المخفي")

if __name__ == "__main__":
    test_telegram_html_formats()
