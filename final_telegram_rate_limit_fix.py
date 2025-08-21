#!/usr/bin/env python3
"""
CRITICAL FIX: Telegram Rate Limiting - Respect Required Wait Times
إصلاح نهائي لاحترام أوقات الانتظار المطلوبة من تليجرام
"""

import re
import sys

def apply_final_rate_limit_fix():
    """تطبيق الإصلاح النهائي لاحترام أوقات الانتظار"""
    
    with open('main.py', 'r', encoding='utf-8') as f:
        content = f.read()
    
    # إصلاح نهائي: احترام أوقات الانتظار الكاملة من Telegram
    old_bot_logic = """                # Progressive delay with longer waits to avoid rate limiting
                # Handle ImportBotAuthorizationRequest specifically
                error_str = str(e)
                if "ImportBotAuthorizationRequest" in error_str or "wait" in error_str.lower():
                    # Extract wait time if mentioned
                    wait_match = re.search(r'wait of (\d+) seconds', error_str)
                    if wait_match:
                        required_wait = int(wait_match.group(1))
                        # Add 10% buffer to the required wait time
                        delay = min(required_wait + int(required_wait * 0.1), 900)  # Max 15 minutes
                        logger.info(f"⏱️ Telegram requires wait: {required_wait}s, using {delay}s with buffer")
                    else:
                        delay = min(60 + (retry_count * 30), 900)  # Start with 1 minute, max 15 minutes
                else:
                    delay = min(30 + (retry_count * 10), 300)  # Other errors: 30s to 5 minutes
                
                logger.info(f"⏱️ انتظار {delay} ثانية قبل إعادة تشغيل بوت التحكم...")
                await asyncio.sleep(delay)"""
    
    new_bot_logic = """                # CRITICAL: Respect Telegram's exact wait time requirements
                error_str = str(e)
                if "ImportBotAuthorizationRequest" in error_str or "wait" in error_str.lower():
                    # Extract exact wait time from Telegram
                    wait_match = re.search(r'wait of (\d+) seconds', error_str)
                    if wait_match:
                        required_wait = int(wait_match.group(1))
                        # Use EXACT wait time + small buffer to avoid repeated errors
                        delay = required_wait + 30  # Just 30 seconds buffer
                        logger.info(f"🚨 Telegram requires EXACT wait: {required_wait}s, using {delay}s")
                        logger.info(f"⏰ سيتم إعادة المحاولة خلال {delay//60} دقيقة و {delay%60} ثانية")
                    else:
                        # If can't extract exact time, use progressive delay
                        delay = min(300 + (retry_count * 60), 1800)  # 5 minutes to 30 minutes
                        logger.info(f"⏱️ لا يمكن استخراج الوقت المحدد، استخدام {delay//60} دقيقة")
                else:
                    # For other errors, use shorter delays
                    delay = min(60 + (retry_count * 30), 600)  # 1 minute to 10 minutes
                    logger.info(f"⚠️ خطأ عام، انتظار {delay} ثانية")
                
                logger.info(f"💤 بدء الانتظار لمدة {delay} ثانية...")
                await asyncio.sleep(delay)
                logger.info("✅ انتهى الانتظار، إعادة المحاولة الآن...")"""
    
    if old_bot_logic in content:
        content = content.replace(old_bot_logic, new_bot_logic)
        print("✅ تم تطبيق الإصلاح النهائي لبوت التحكم")
    
    # إصلاح مماثل للUserBot
    old_userbot_logic = """                        # Progressive delay with better rate limiting handling
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
    
    new_userbot_logic = """                        # CRITICAL: Respect Telegram's exact wait time for UserBot
                        error_str = str(e)
                        if "ImportBotAuthorizationRequest" in error_str or "wait" in error_str.lower():
                            # Extract exact wait time from Telegram
                            wait_match = re.search(r'wait of (\d+) seconds', error_str)
                            if wait_match:
                                required_wait = int(wait_match.group(1))
                                # Use EXACT wait time + minimal buffer
                                wait_time = required_wait + 60  # Just 1 minute buffer
                                logger.info(f"🚨 UserBot: Telegram requires EXACT wait: {required_wait}s, using {wait_time}s")
                                logger.info(f"⏰ UserBot سيتم إعادة تشغيله خلال {wait_time//60} دقيقة")
                            else:
                                # If can't extract exact time, use longer delay
                                wait_time = min(600 + (userbot_failures * 120), 3600)  # 10 minutes to 1 hour
                                logger.info(f"⏱️ UserBot: لا يمكن استخراج الوقت، استخدام {wait_time//60} دقيقة")
                        else:
                            # For other errors
                            wait_time = min(120 + (userbot_failures * 60), 1200)  # 2 minutes to 20 minutes
                            logger.info(f"⚠️ UserBot: خطأ عام، انتظار {wait_time//60} دقيقة")
                        
                        logger.info(f"💤 UserBot: بدء الانتظار لمدة {wait_time} ثانية...")
                        await asyncio.sleep(wait_time)
                        logger.info("✅ UserBot: انتهى الانتظار، إعادة المحاولة...")"""
    
    if old_userbot_logic in content:
        content = content.replace(old_userbot_logic, new_userbot_logic)
        print("✅ تم تطبيق الإصلاح النهائي للUserBot")
    
    # كتابة الملف المحدث
    with open('main.py', 'w', encoding='utf-8') as f:
        f.write(content)

def add_error_monitoring():
    """إضافة مراقبة محسنة للأخطاء"""
    
    # إنشاء ملف مراقبة الأخطاء
    monitor_content = '''#!/usr/bin/env python3
"""
Telegram Error Monitor - Real-time monitoring of rate limiting
مراقب أخطاء تليجرام - مراقبة فورية لحدود المعدل
"""

import time
import logging
from datetime import datetime, timedelta

class TelegramErrorMonitor:
    def __init__(self):
        self.last_rate_limit = None
        self.rate_limit_count = 0
        
    def log_rate_limit(self, required_wait: int):
        """تسجيل حدود المعدل"""
        now = datetime.now()
        self.last_rate_limit = now
        self.rate_limit_count += 1
        
        expected_clear_time = now + timedelta(seconds=required_wait)
        
        print(f"🚨 Rate Limit #{self.rate_limit_count}")
        print(f"⏰ Required Wait: {required_wait} seconds ({required_wait//60}m {required_wait%60}s)")
        print(f"🕐 Clear Time: {expected_clear_time.strftime('%H:%M:%S')}")
        print(f"📊 Total Rate Limits Today: {self.rate_limit_count}")

# Global monitor instance
error_monitor = TelegramErrorMonitor()
'''
    
    with open('telegram_error_monitor.py', 'w', encoding='utf-8') as f:
        f.write(monitor_content)
    
    print("✅ تم إنشاء مراقب الأخطاء")

if __name__ == "__main__":
    print("🔧 تطبيق الإصلاح النهائي لحدود معدل تليجرام...")
    
    try:
        apply_final_rate_limit_fix()
        add_error_monitoring()
        
        print("\n🎯 تم تطبيق الإصلاح النهائي بنجاح!")
        print("📋 التحسينات:")
        print("   ⏰ احترام أوقات الانتظار المحددة من تليجرام")
        print("   🎯 إضافة buffer صغير (30-60 ثانية) فقط")
        print("   📊 تحسين رسائل السجل لمتابعة الانتظار")
        print("   🔍 مراقبة محسنة للأخطاء")
        print("\n💡 النظام سيحترم الآن أوقات الانتظار المطلوبة من تليجرام")
        
    except Exception as e:
        print(f"❌ خطأ في تطبيق الإصلاح: {e}")
        sys.exit(1)