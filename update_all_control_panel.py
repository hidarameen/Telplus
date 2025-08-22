#!/usr/bin/env python3
"""
سكريبت لتحديث جميع دوال لوحة التحكم لاستخدام force_new_message
"""

import re

def update_all_control_panel_functions():
    """تحديث جميع دوال لوحة التحكم"""
    
    # قراءة الملف
    with open('bot_package/bot_simple.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # قائمة الدوال الرئيسية التي يجب تحديثها
    main_functions = [
        # دوال القوائم الرئيسية
        'show_tasks_menu',
        'show_channels_menu',
        'show_advanced_features',
        'show_task_settings',
        'show_task_details',
        'show_task_manage',
        
        # دوال الإعدادات
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
        'show_forwarding_settings',
        
        # دوال إدارة المصادر والأهداف
        'show_sources_management',
        'show_targets_management',
        'show_source_selection',
        'show_target_selection',
        
        # دوال إدارة القنوات
        'show_channels_menu',
        'list_channels',
        'show_channel_selection',
        
        # دوال أخرى
        'show_login_menu',
        'show_main_menu',
        'show_task_list',
        'show_create_task_menu'
    ]
    
    # تحديث الدوال الرئيسية
    updated_count = 0
    
    for func_name in main_functions:
        # البحث عن الدالة
        pattern = rf'async def {func_name}\(self, event[^)]*\):.*?await self\.edit_or_send_message\(event, ([^,]+), buttons=buttons\)'
        
        # استبدال بـ force_new_message
        replacement = rf'async def {func_name}(self, event\1):\2\n        await self.force_new_message(event, \3, buttons=buttons)'
        
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        if new_content != content:
            content = new_content
            updated_count += 1
            print(f"✅ تم تحديث دالة: {func_name}")
    
    # تحديث الدوال الأخرى التي تستخدم edit_or_send_message مع buttons
    pattern = r'await self\.edit_or_send_message\(event, ([^,]+), buttons=buttons\)'
    replacement = r'await self.force_new_message(event, \1, buttons=buttons)'
    
    new_content = re.sub(pattern, replacement, content)
    if new_content != content:
        content = new_content
        updated_count += 1
        print(f"✅ تم تحديث {len(re.findall(pattern, content))} استدعاء إضافي")
    
    # حفظ الملف المحدث
    with open('bot_package/bot_simple.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"\n🎉 تم تحديث {updated_count} دالة بنجاح!")

def update_specific_functions():
    """تحديث دوال محددة يدوياً"""
    
    with open('bot_package/bot_simple.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # تحديث دوال محددة
    replacements = [
        # show_character_limit_settings
        (
            r'async def show_character_limit_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_character_limit_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_rate_limit_settings
        (
            r'async def show_rate_limit_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_rate_limit_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_forwarding_delay_settings
        (
            r'async def show_forwarding_delay_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_forwarding_delay_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_sending_interval_settings
        (
            r'async def show_sending_interval_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_sending_interval_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_text_formatting_settings
        (
            r'async def show_text_formatting_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_text_formatting_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_duplicate_filter_settings
        (
            r'async def show_duplicate_filter_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_duplicate_filter_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_language_filter_settings
        (
            r'async def show_language_filter_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_language_filter_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_admin_filter_settings
        (
            r'async def show_admin_filter_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_admin_filter_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_inline_button_filter_settings
        (
            r'async def show_inline_button_filter_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_inline_button_filter_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_forwarded_message_filter_settings
        (
            r'async def show_forwarded_message_filter_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_forwarded_message_filter_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_text_cleaning_settings
        (
            r'async def show_text_cleaning_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_text_cleaning_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_translation_settings
        (
            r'async def show_translation_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_translation_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_working_hours_settings
        (
            r'async def show_working_hours_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_working_hours_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_watermark_settings
        (
            r'async def show_watermark_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_watermark_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_audio_metadata_settings
        (
            r'async def show_audio_metadata_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_audio_metadata_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_media_filters
        (
            r'async def show_media_filters\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_media_filters(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_word_filters
        (
            r'async def show_word_filters\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_word_filters(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_text_replacements
        (
            r'async def show_text_replacements\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_text_replacements(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_header_settings
        (
            r'async def show_header_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_header_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_footer_settings
        (
            r'async def show_footer_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_footer_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_inline_buttons
        (
            r'async def show_inline_buttons\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_inline_buttons(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
        # show_forwarding_settings
        (
            r'async def show_forwarding_settings\(self, event, task_id\):.*?await self\.edit_or_send_message\(event, message_text, buttons=buttons\)',
            r'async def show_forwarding_settings(self, event, task_id):\1\n        await self.force_new_message(event, message_text, buttons=buttons)',
        ),
    ]
    
    updated_count = 0
    for pattern, replacement in replacements:
        new_content = re.sub(pattern, replacement, content, flags=re.DOTALL)
        if new_content != content:
            content = new_content
            updated_count += 1
    
    with open('bot_package/bot_simple.py', 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ تم تحديث {updated_count} دالة محددة!")

if __name__ == "__main__":
    print("🔧 تحديث جميع دوال لوحة التحكم")
    print("=" * 60)
    
    update_specific_functions()
    
    print("\n🎉 تم الانتهاء من التحديث!")