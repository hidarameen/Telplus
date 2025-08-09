#!/usr/bin/env python3
"""
إصلاح جميع أنماط التنسيق لتستخدم HTML بدلاً من markdown
"""

def fix_formatting():
    with open('userbot_service/userbot.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # الاستبدالات المطلوبة
    replacements = [
        ('return f"**{cleaned_text.strip()}**"', 'return f"<b>{cleaned_text.strip()}</b>"'),
        ('return f"*{cleaned_text.strip()}*"', 'return f"<i>{cleaned_text.strip()}</i>"'),
        ('return f"__{cleaned_text.strip()}__"', 'return f"<u>{cleaned_text.strip()}</u>"'),
        ('return f"~~{cleaned_text.strip()}~~"', 'return f"<s>{cleaned_text.strip()}</s>"'),
        ('return f"`{cleaned_text.strip()}`"', 'return f"<code>{cleaned_text.strip()}</code>"'),
        ('return f"```\\n{cleaned_text.strip()}\\n```"', 'return f"<pre>{cleaned_text.strip()}</pre>"'),
    ]
    
    # تطبيق الاستبدالات
    modified = False
    for old, new in replacements:
        if old in content:
            content = content.replace(old, new)
            modified = True
            print(f"✅ تم تغيير: {old[:30]}...")
    
    if modified:
        with open('userbot_service/userbot.py', 'w', encoding='utf-8') as f:
            f.write(content)
        print("\n✅ تم إصلاح جميع أنماط التنسيق بنجاح!")
    else:
        print("ℹ️ لا توجد تغييرات مطلوبة")

if __name__ == "__main__":
    fix_formatting()