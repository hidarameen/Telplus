#!/usr/bin/env python3
"""
اختبار طرق مختلفة لتنسيق النص المخفي في التليثون
Test different methods for spoiler formatting in Telethon
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_spoiler_methods():
    """اختبار طرق مختلفة لتنسيق spoiler في Telethon"""
    
    print("🧪 اختبار طرق تنسيق spoiler في Telethon")
    print("="*60)
    
    test_text = "نص مخفي للاختبار"
    
    methods = [
        ("HTML tg-spoiler", f'<tg-spoiler>{test_text}</tg-spoiler>'),
        ("HTML span class", f'<span class="tg-spoiler">{test_text}</span>'),
        ("Markdown style", f'||{test_text}||'),
        ("Plain spoiler tag", f'<spoiler>{test_text}</spoiler>'),
    ]
    
    print(f"\nنص الاختبار: '{test_text}'")
    print("-" * 50)
    
    for i, (method_name, formatted_text) in enumerate(methods, 1):
        print(f"\n{i}. الطريقة: {method_name}")
        print(f"   النتيجة: '{formatted_text}'")
        
        # تحليل التنسيق
        if '<tg-spoiler>' in formatted_text:
            print(f"   📝 يستخدم: tg-spoiler tag")
        elif 'class="tg-spoiler"' in formatted_text:
            print(f"   📝 يستخدم: span with tg-spoiler class")  
        elif '||' in formatted_text:
            print(f"   📝 يستخدم: Markdown spoiler syntax")
        elif '<spoiler>' in formatted_text:
            print(f"   📝 يستخدم: Plain spoiler tag")
    
    print("\n" + "="*60)
    print("📚 معلومات إضافية:")
    print("- Telethon قد يحتاج MessageEntitySpoiler بدلاً من HTML")
    print("- بعض إصدارات Telethon تدعم HTML spoiler tags")
    print("- قد نحتاج إلى استخدام formatting_entities")
    print("="*60)

def test_message_entity_spoiler():
    """اختبار استخدام MessageEntitySpoiler مباشرة"""
    
    print("\n🔍 اختبار MessageEntitySpoiler:")
    print("-" * 40)
    
    try:
        # محاولة استيراد MessageEntitySpoiler
        from telethon.tl.types import MessageEntitySpoiler
        print("✅ تم استيراد MessageEntitySpoiler بنجاح")
        
        # مثال على كيفية الاستخدام
        text = "هذا نص عادي مع نص مخفي هنا"
        spoiler_start = text.find("نص مخفي")
        spoiler_length = len("نص مخفي")
        
        print(f"النص: '{text}'")
        print(f"موقع البداية: {spoiler_start}")
        print(f"الطول: {spoiler_length}")
        
        # إنشاء entity
        entity = MessageEntitySpoiler(offset=spoiler_start, length=spoiler_length)
        print(f"✅ تم إنشاء MessageEntitySpoiler: offset={entity.offset}, length={entity.length}")
        
        return True
        
    except ImportError as e:
        print(f"❌ فشل في استيراد MessageEntitySpoiler: {e}")
        return False
    except Exception as e:
        print(f"❌ خطأ في اختبار MessageEntitySpoiler: {e}")
        return False

if __name__ == "__main__":
    test_spoiler_methods()
    success = test_message_entity_spoiler()
    
    if success:
        print("\n💡 التوصية: استخدام MessageEntitySpoiler مع formatting_entities")
    else:
        print("\n💡 التوصية: الاستمرار مع HTML formatting")