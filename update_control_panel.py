#!/usr/bin/env python3
"""
سكريبت لتحديث لوحة التحكم لاستخدام force_new_message
"""

import re

def update_bot_file():
    """تحديث ملف bot_simple.py لاستخدام force_new_message"""
    
    # قراءة الملف
    with open('bot_package/bot_simple.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # قائمة الدوال الرئيسية التي يجب تحديثها
    main_functions = [
        'show_tasks_menu',
        'show_channels_menu', 
        'show_advanced_features',
        'show_task_settings',
        'show_task_details',
        'show_character_limit_settings',
        'show_rate_limit_settings',
        'show_forwarding_delay_settings',
        'show_sending_interval_settings',
        'show_text_formatting_settings',
        'show_duplicate_filter_settings',
        'show_language_filter_settings',
        'show_admin_filter_settings',
        'show_inline_button_filter_settings',
        'show_forwarded_message_filter_settings',
        'show_text_cleaning_settings',
        'show_translation_settings',
        'show_working_hours_settings',
        'show_watermark_settings',
        'show_audio_metadata_settings',
        'show_media_filters',
        'show_word_filters',
        'show_text_replacements',
        'show_header_settings',
        'show_footer_settings',
        'show_inline_buttons',
        'show_forwarding_settings'
    ]
    
    # تحديث الدوال الرئيسية
    for func_name in main_functions:
        # البحث عن الدالة
        pattern = rf'async def {func_name}\(self, event[^)]*\):.*?await self\.edit_or_send_message\(event, ([^,]+), buttons=buttons\)'
        
        # استبدال بـ force_new_message
        replacement = rf'async def {func_name}(self, event\1):\2\n        await self.force_new_message(event, \3, buttons=buttons)'
        
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    # تحديث الدوال الأخرى التي تستخدم edit_or_send_message
    # استبدال edit_or_send_message بـ force_new_message في الدوال الرئيسية
    content = re.sub(
        r'await self\.edit_or_send_message\(event, ([^,]+), buttons=buttons\)',
        r'await self.force_new_message(event, \1, buttons=buttons)',
        content
    )
    
    # حفظ الملف المحدث
    with open('bot_package/bot_simple.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ تم تحديث ملف bot_simple.py بنجاح!")

def update_specific_functions():
    """تحديث دوال محددة"""
    
    with open('bot_package/bot_simple.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # تحديث دوال محددة
    replacements = [
        # show_tasks_menu
        (
            r'async def show_tasks_menu\(self, event\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_tasks_menu(self, event):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_channels_menu
        (
            r'async def show_channels_menu\(self, event\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_channels_menu(self, event):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_advanced_features
        (
            r'async def show_advanced_features\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_advanced_features(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
    ]
    
    for pattern, replacement in replacements:
        content = re.sub(pattern, replacement, content, flags=re.DOTALL)
    
    with open('bot_package/bot_simple.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("✅ تم تحديث الدوال المحددة!")

if __name__ == "__main__":
    print("🔧 تحديث لوحة التحكم لاستخدام force_new_message")
    print("=" * 60)
    
    update_specific_functions()
    
    print("\n🎉 تم الانتهاء من التحديث!")