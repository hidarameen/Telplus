#!/usr/bin/env python3
"""
Fix broken f-strings in userbot.py
"""

def fix_f_strings():
    """Fix broken f-strings in userbot.py"""
    try:
        # Read the file
        with open('userbot_service/userbot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix the broken f-strings
        content = content.replace('return f" {cleaned_text.strip()} {', 'return f"<s>{cleaned_text.strip()}</s>"')
        
        # Write the fixed content back
        with open('userbot_service/userbot.py', 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ تم إصلاح f-strings بنجاح")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في إصلاح f-strings: {e}")
        return False

if __name__ == "__main__":
    fix_f_strings()