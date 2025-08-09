#!/usr/bin/env python3
"""
اختبار بدائل مختلفة لتنسيق spoiler في تليجرام
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from userbot_service.userbot import UserbotService

def test_spoiler_alternatives():
    """اختبار بدائل مختلفة لـ spoiler"""
    
    print("🧪 اختبار بدائل تنسيق spoiler")
    print("="*50)
    
    test_text = "نص مخفي للاختبار"
    
    # بدائل مختلفة لـ spoiler
    spoiler_formats = [
        ('span class="tg-spoiler"', f'<span class="tg-spoiler">{test_text}</span>'),
        ('tg-spoiler tag', f'<tg-spoiler>{test_text}</tg-spoiler>'),
        ('spoiler tag', f'<spoiler>{test_text}</spoiler>'),
        ('markdown spoiler', f'||{test_text}||'),
    ]
    
    for name, formatted_text in spoiler_formats:
        print(f"\n📝 {name}:")
        print(f"   النتيجة: '{formatted_text}'")
        print(f"   الطول: {len(formatted_text)} حرف")

if __name__ == "__main__":
    test_spoiler_alternatives()