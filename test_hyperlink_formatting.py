#!/usr/bin/env python3
"""
اختبار تنسيق الروابط الجديد
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService

def test_hyperlink_formatting():
    """اختبار تنسيق الروابط الجديد"""
    print("🔗 اختبار تنسيق الروابط الجديد...")
    
    userbot = UserbotService()
    
    # نصوص الاختبار
    test_texts = [
        "مرحباً بك في قناتنا",
        "انضم إلينا الآن",
        "آخر الأخبار العاجلة",
        "تحديث مهم جداً",
        "عرض خاص محدود",
        "نص **عريض** مع تنسيق",
        "*نص مائل* للاختبار",
        "نص متعدد\nالأسطر\nللاختبار"
    ]
    
    # روابط للاختبار
    test_urls = [
        "https://t.me/mychannel",
        "https://google.com",
        "https://github.com/myproject",
        "https://example.com/page?param=value"
    ]
    
    print("\n" + "="*60)
    print("🔗 اختبار تحويل النص الأصلي إلى رابط")
    print("="*60)
    
    for text in test_texts:
        print(f"\n📄 النص الأصلي: '{text}'")
        print("-" * 50)
        
        for url in test_urls:
            # محاكاة إعدادات التنسيق
            formatted_text = userbot.apply_text_formatting_test('hyperlink', text)
            # استبدال الرابط الافتراضي بالرابط المحدد
            formatted_with_custom_url = formatted_text.replace('https://example.com', url)
            print(f"  {url:30} → {formatted_with_custom_url}")
    
    print("\n✅ انتهى اختبار تنسيق الروابط!")

def main():
    """دالة رئيسية"""
    try:
        test_hyperlink_formatting()
    except Exception as e:
        print(f"❌ خطأ في الاختبار: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()