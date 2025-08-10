#!/usr/bin/env python3
"""
اختبار شامل لفلتر اللغة المحدث - الإصدار النهائي
تاريخ: 10 أغسطس 2025

هذا الاختبار يتحقق من:
1. تطبيق فلتر اللغة في UserBot
2. كشف اللغة بدقة
3. منطق السماح والحظر
4. معالجة إدخال اللغات المخصصة
5. اختبار سيناريوهات متنوعة
"""

import asyncio
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database.database import Database
from userbot_service.userbot import UserbotService
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class MockMessage:
    """Mock message object for testing"""
    def __init__(self, text: str, media=None, forward=None, reply_markup=None):
        self.message = text
        self.media = media
        self.forward = forward
        self.reply_markup = reply_markup

async def test_language_filter():
    """Test complete language filter functionality"""
    
    print("🚀 بدء اختبار فلتر اللغة الشامل")
    print("=" * 50)
    
    # Initialize database and userbot
    db = Database()
    userbot = UserbotService()
    
    task_id = 7  # Use existing task
    
    # Test 1: Setup language filter with English in block mode
    print("\n📋 اختبار 1: إعداد فلتر اللغة الإنجليزية في وضع الحظر")
    
    # Clear existing languages first
    existing_languages = db.get_language_filters(task_id)['languages']
    for lang in existing_languages:
        db.remove_language_filter(task_id, lang['language_code'])
    
    # Add English to block mode
    success = db.add_language_filter(task_id, 'en', 'English', True)
    print(f"   ✅ إضافة اللغة الإنجليزية: {success}")
    
    success = db.set_language_filter_mode(task_id, 'block')
    print(f"   ✅ تحديد وضع الحظر: {success}")
    
    # Enable language filter
    success = db.toggle_language_filter(task_id, True)
    print(f"   ✅ تفعيل فلتر اللغة: {success}")
    
    # Test 2: Language detection accuracy
    print("\n🔍 اختبار 2: دقة كشف اللغة")
    
    test_texts = [
        ("Hello, this is an English message", "en"),
        ("مرحبا، هذه رسالة باللغة العربية", "ar"),
        ("Bonjour, ceci est un message en français", "fr"),
        ("Привет, это сообщение на русском языке", "ru"),
        ("Mixed message نص مختلط with English and Arabic", "en"),  # Should detect primary (English)
        ("123 456 !@# $%^", "unknown"),  # No letters
        ("", "unknown"),  # Empty
    ]
    
    for text, expected in test_texts:
        detected = userbot._detect_message_language(text)
        status = "✅" if detected == expected else "❌"
        print(f"   {status} '{text[:30]}...' -> متوقع: {expected}, مكتشف: {detected}")
    
    # Test 3: Language filter logic - Block mode
    print("\n🚫 اختبار 3: منطق فلتر اللغة - وضع الحظر")
    
    test_messages = [
        ("Hello world", True),   # English - should be blocked
        ("مرحبا بالعالم", False), # Arabic - should pass
        ("Bonjour", False),      # French - should pass
        ("", False),             # Empty - should pass
    ]
    
    for text, should_block in test_messages:
        message = MockMessage(text)
        blocked = await userbot._check_language_filter(task_id, message)
        status = "✅" if blocked == should_block else "❌"
        action = "محظور" if blocked else "مسموح"
        expected_action = "محظور" if should_block else "مسموح"
        print(f"   {status} '{text}' -> متوقع: {expected_action}, النتيجة: {action}")
    
    # Test 4: Allow mode
    print("\n✅ اختبار 4: منطق فلتر اللغة - وضع السماح")
    
    # Switch to allow mode
    success = db.set_language_filter_mode(task_id, 'allow')
    print(f"   ✅ تبديل إلى وضع السماح: {success}")
    
    for text, should_block in [
        ("Hello world", False),  # English - should pass (allowed)
        ("مرحبا بالعالم", True),  # Arabic - should be blocked (not allowed)
        ("Bonjour", True),       # French - should be blocked (not allowed)
    ]:
        message = MockMessage(text)
        blocked = await userbot._check_language_filter(task_id, message)
        status = "✅" if blocked == should_block else "❌"
        action = "محظور" if blocked else "مسموح"
        expected_action = "محظور" if should_block else "مسموح"
        print(f"   {status} '{text}' -> متوقع: {expected_action}, النتيجة: {action}")
    
    # Test 5: Multiple languages
    print("\n🌍 اختبار 5: لغات متعددة")
    
    # Add Arabic to allowed list
    success = db.add_language_filter(task_id, 'ar', 'العربية', True)
    print(f"   ✅ إضافة اللغة العربية: {success}")
    
    for text, should_block in [
        ("Hello world", False),  # English - allowed
        ("مرحبا بالعالم", False), # Arabic - allowed  
        ("Bonjour", True),       # French - blocked
        ("Привет", True),        # Russian - blocked
    ]:
        message = MockMessage(text)
        blocked = await userbot._check_language_filter(task_id, message)
        status = "✅" if blocked == should_block else "❌"
        action = "محظور" if blocked else "مسموح"
        expected_action = "محظور" if should_block else "مسموح"
        print(f"   {status} '{text}' -> متوقع: {expected_action}, النتيجة: {action}")
    
    # Test 6: Advanced filter integration
    print("\n🔧 اختبار 6: تكامل الفلاتر المتقدمة")
    
    # Switch back to block mode for comprehensive test
    db.set_language_filter_mode(task_id, 'block')
    
    # Test with full advanced filter check
    message = MockMessage("Hello, this should be blocked by language filter")
    should_block, should_remove_buttons, should_remove_forward = await userbot._check_message_advanced_filters(task_id, message)
    
    print(f"   ✅ فحص الفلاتر المتقدمة:")
    print(f"      - حظر الرسالة: {should_block}")
    print(f"      - حذف الأزرار: {should_remove_buttons}")  
    print(f"      - حذف علامة التوجيه: {should_remove_forward}")
    
    # Test 7: Filter disabled
    print("\n⏹️ اختبار 7: فلتر اللغة معطل")
    
    # Disable language filter
    success = db.toggle_language_filter(task_id, False)
    print(f"   ✅ تعطيل فلتر اللغة: {success}")
    
    message = MockMessage("Hello, this should pass when filter is disabled")
    blocked = await userbot._check_language_filter(task_id, message)
    print(f"   ✅ فلتر معطل - النتيجة: {'محظور' if blocked else 'مسموح'} (يجب أن يكون مسموح)")
    
    # Test 8: Custom language handling
    print("\n🔧 اختبار 8: معالجة اللغات المخصصة")
    
    # Re-enable for custom language test
    db.toggle_language_filter(task_id, True)
    
    # Test custom language code
    success = db.add_language_filter(task_id, 'ja', 'Japanese', True)
    print(f"   ✅ إضافة لغة مخصصة (يابانية): {success}")
    
    # Test Japanese-like text (will likely be detected as unknown)
    message = MockMessage("これは日本語のメッセージです")
    blocked = await userbot._check_language_filter(task_id, message)
    print(f"   ✅ نص ياباني -> النتيجة: {'محظور' if blocked else 'مسموح'}")
    
    print("\n🎉 انتهى اختبار فلتر اللغة الشامل")
    print("=" * 50)
    
    # Cleanup - restore to original state
    print("\n🧹 تنظيف الإعدادات...")
    db.set_language_filter_mode(task_id, 'allow')
    existing_languages = db.get_language_filters(task_id)['languages']
    for lang in existing_languages:
        db.remove_language_filter(task_id, lang['language_code'])
    print("✅ تم تنظيف إعدادات الاختبار")

if __name__ == "__main__":
    asyncio.run(test_language_filter())