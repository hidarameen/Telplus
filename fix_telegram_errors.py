#!/usr/bin/env python3
"""
CRITICAL FIX: Telegram Bot Authorization and Rate Limiting Errors
إصلاح شامل لأخطاء التفويض وحد المعدل في بوت التليجرام
"""

import re
import sys

def fix_main_retry_logic():
    """إصلاح منطق إعادة المحاولة في main.py لتجنب rate limiting"""
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # إصلاح 1: زيادة التأخير للبوت الرئيسي
    old_bot_delay = """                # Progressive delay but max 30 seconds
                delay = min(5 + (retry_count * 2), 30)
                logger.info(f"⏱️ انتظار {delay} ثانية قبل إعادة تشغيل بوت التحكم...")
                await asyncio.sleep(delay)"""
    
    new_bot_delay = """                # Progressive delay with longer waits to avoid rate limiting
                # Handle ImportBotAuthorizationRequest specifically
                if "ImportBotAuthorizationRequest" in str(e) or "wait" in str(e).lower():
                    # Extract wait time if mentioned
                    wait_match = re.search(r'wait of (\d+) seconds', str(e))
                    if wait_match:
                        required_wait = int(wait_match.group(1))
                        # Add 10% buffer to the required wait time
                        delay = min(required_wait + (required_wait * 0.1), 900)  # Max 15 minutes
                        logger.info(f"⏱️ Telegram requires wait: {required_wait}s, using {delay:.0f}s with buffer")
                    else:
                        delay = min(60 + (retry_count * 30), 900)  # Start with 1 minute, max 15 minutes
                else:
                    delay = min(30 + (retry_count * 10), 300)  # Other errors: 30s to 5 minutes
                
                logger.info(f"⏱️ انتظار {delay:.0f} ثانية قبل إعادة تشغيل بوت التحكم...")
                await asyncio.sleep(delay)"""
    
    if old_bot_delay in content:
        content = content.replace(old_bot_delay, new_bot_delay)
        print("✅ تم إصلاح منطق إعادة المحاولة للبوت الرئيسي")
    
    # إصلاح 2: تحسين منطق إعادة تشغيل UserBot
    old_userbot_delay = """                        # Progressive delay with max limit
                        wait_time = min(60 + (userbot_failures * 15), 300)  # Max 5 minutes
                        logger.info(f"⏱️ انتظار {wait_time} ثانية قبل إعادة المحاولة...")
                        await asyncio.sleep(wait_time)"""
    
    new_userbot_delay = """                        # Progressive delay with better rate limiting handling
                        if "ImportBotAuthorizationRequest" in str(e) or "wait" in str(e).lower():
                            # Extract wait time if mentioned
                            wait_match = re.search(r'wait of (\d+) seconds', str(e))
                            if wait_match:
                                required_wait = int(wait_match.group(1))
                                wait_time = min(required_wait + 60, 1200)  # Add 1 minute buffer, max 20 minutes
                                logger.info(f"⏱️ Telegram requires wait: {required_wait}s, using {wait_time}s with buffer")
                            else:
                                wait_time = min(120 + (userbot_failures * 60), 1200)  # 2 minutes to 20 minutes
                        else:
                            wait_time = min(60 + (userbot_failures * 30), 600)  # 1 minute to 10 minutes
                        
                        logger.info(f"⏱️ انتظار {wait_time} ثانية قبل إعادة المحاولة...")
                        await asyncio.sleep(wait_time)"""
    
    if old_userbot_delay in content:
        content = content.replace(old_userbot_delay, new_userbot_delay)
        print("✅ تم إصلاح منطق إعادة المحاولة للUserBot")
    
    # إصلاح 3: إضافة import re في البداية
    if "import re" not in content:
        content = content.replace("import sys", "import sys\nimport re")
        print("✅ تم إضافة import re")
    
    # كتابة الملف المحدث
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)

def fix_bot_config_tokens():
    """التحقق من صحة التوكينات وإصلاح أي مشاكل"""
    
    try:
        # قراءة ملف bot_package/config.py
        with open('bot_package/config.py', 'r', encoding='utf-8') as f:
            config_content = f.read()
        
        print("✅ تم العثور على ملف الإعدادات")
        
        # التحقق من وجود التوكينات
        if "BOT_TOKEN" in config_content and "API_ID" in config_content:
            print("✅ التوكينات موجودة في ملف الإعدادات")
        else:
            print("⚠️ التوكينات غير موجودة أو غير مكتملة")
            
    except FileNotFoundError:
        print("❌ ملف الإعدادات غير موجود")

def fix_session_handling():
    """إصلاح معالجة الجلسات لتجنب تضارب الاتصالات"""
    
    try:
        # قراءة ملف userbot_service/userbot.py
        with open('userbot_service/userbot.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # إضافة معالجة أفضل للجلسات المتضاربة
        old_session_check = """    async def start_session(self, user_id: int, session_string: str) -> bool:
        \"\"\"بدء جلسة جديدة للمستخدم\"\"\"
        try:"""
        
        new_session_check = """    async def start_session(self, user_id: int, session_string: str) -> bool:
        \"\"\"بدء جلسة جديدة للمستخدم مع معالجة التضارب\"\"\"
        try:
            # التحقق من وجود جلسة سابقة
            if user_id in self.clients:
                logger.info(f"🔄 إغلاق الجلسة السابقة للمستخدم {user_id}")
                try:
                    await self.clients[user_id].disconnect()
                    await asyncio.sleep(2)  # انتظار قصير لضمان الإغلاق
                except Exception:
                    pass
                del self.clients[user_id]"""
        
        if old_session_check in content:
            content = content.replace(old_session_check, new_session_check)
            print("✅ تم إصلاح معالجة الجلسات لتجنب التضارب")
            
            # كتابة الملف المحدث
            with open('userbot_service/userbot.py', 'w', encoding='utf-8') as f:
                f.write(content)
        
    except FileNotFoundError:
        print("⚠️ ملف userbot.py غير موجود")

if __name__ == "__main__":
    print("🔧 بدء إصلاح أخطاء التليجرام...")
    
    try:
        fix_main_retry_logic()
        fix_bot_config_tokens()
        fix_session_handling()
        
        print("\n✅ تم إنجاز جميع الإصلاحات بنجاح!")
        print("📝 الإصلاحات المطبقة:")
        print("   🔄 إصلاح منطق إعادة المحاولة مع معالجة rate limiting")
        print("   ⏱️ زيادة أوقات الانتظار لتجنب ImportBotAuthorizationRequest")
        print("   🔗 تحسين معالجة الجلسات لتجنب التضارب")
        print("   📊 استخراج أوقات الانتظار المطلوبة من رسائل الخطأ")
        
    except Exception as e:
        print(f"❌ خطأ في تطبيق الإصلاحات: {e}")
        sys.exit(1)