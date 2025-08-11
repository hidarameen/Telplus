#!/usr/bin/env python3
"""
Main entry point for Telegram Bot System
Only runs the Telegram bot - no web interface
"""

import threading
import time
import signal
import sys
import os
import asyncio
import logging
from bot_package.bot_simple import run_simple_bot
from userbot_service.userbot import userbot_instance, start_userbot_service, stop_userbot_service
from bot_package.config import BOT_TOKEN, API_ID, API_HASH

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global bot instance for userbot to access
bot_instance = None

class TelegramBotSystem:
    def __init__(self):
        self.bot_thread = None
        self.userbot_thread = None
        self.running = True

    async def start_telegram_bot(self):
        """Start Telegram bot"""
        global bot_instance
        logger.info("🤖 بدء تشغيل بوت تليجرام...")
        try:
            bot_instance = await run_simple_bot()
            # Keep the bot running
            await bot_instance.bot.run_until_disconnected()
        except Exception as e:
            logger.error(f"خطأ في بوت تليجرام: {e}")

    def start_userbot_service_thread(self):
        """Start userbot service in async context"""
        logger.info("👤 بدء تشغيل خدمة UserBot...")
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            async def userbot_main():
                # Start userbot service
                await start_userbot_service()
                
                # Start background task processing
                async def background_admin_processor():
                    while self.running:
                        try:
                            await asyncio.sleep(10)  # Check every 10 seconds
                            if userbot_instance:
                                await userbot_instance.process_pending_admin_tasks()
                        except Exception as e:
                            logger.error(f"خطأ في معالج المشرفين الخلفي: {e}")
                            await asyncio.sleep(30)  # Wait longer if error
                
                # Start background processor
                asyncio.create_task(background_admin_processor())
                logger.info("🔄 تم تشغيل معالج المشرفين الخلفي")
                
                # Keep running forever
                logger.info("🚀 UserBot يعمل ويراقب الرسائل...")
                while self.running:
                    await asyncio.sleep(1)
            
            # Run the userbot service
            loop.run_until_complete(userbot_main())
            
        except KeyboardInterrupt:
            pass
        except Exception as e:
            logger.error(f"خطأ في خدمة UserBot: {e}")
        finally:
            if 'loop' in locals():
                try:
                    logger.info("📴 إغلاق خدمة UserBot...")
                    loop.run_until_complete(stop_userbot_service())
                    loop.close()
                except:
                    pass

    def start_all_services(self):
        """Start all services"""
        logger.info("🚀 بدء تشغيل نظام بوت تليجرام...")

        # Start Telegram bot in separate thread  
        def run_bot():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.start_telegram_bot())
            
        self.bot_thread = threading.Thread(target=run_bot, daemon=True)
        self.bot_thread.start()

        # Start userbot service monitoring
        self.userbot_thread = threading.Thread(target=self.start_userbot_service_thread, daemon=True)
        self.userbot_thread.start()

        logger.info("✅ تم تشغيل جميع الخدمات بنجاح")
        self.print_startup_info()

    def print_startup_info(self):
        """Print startup information"""
        bot_username = BOT_TOKEN.split(':')[0] if BOT_TOKEN and ':' in BOT_TOKEN else 'غير محدد'

        print("\n" + "="*60)
        print("🤖 نظام بوت التوجيه التلقائي - تليجرام")
        print("="*60)
        print(f"🤖 بوت تليجرام: @{bot_username}")
        print("📱 ابحث عن البوت في تليجرام وابدأ بـ /start")
        print("="*60)
        print("📋 الخدمات النشطة:")
        print("  ✅ بوت التحكم (Telegram Bot API)")
        print("  ⏳ UserBot (في انتظار تسجيل الدخول)")
        print("="*60)
        print("💡 لبدء الاستخدام:")
        print("  1. ابحث عن البوت في تليجرام")
        print("  2. أرسل /start")
        print("  3. سجل دخولك برقم هاتفك")
        print("  4. أنشئ مهام التوجيه التلقائي")
        print("="*60)
        print("⌨️  اضغط Ctrl+C لإيقاف النظام")
        print("="*60)

    def stop(self):
        """Stop all services"""
        logger.info("⏹️ إيقاف جميع الخدمات...")
        self.running = False

        # Stop userbot if running
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(userbot_instance.stop())
            loop.close()
        except Exception as e:
            logger.error(f"خطأ في إيقاف UserBot: {e}")

        logger.info("✅ تم إيقاف النظام بنجاح")
        sys.exit(0)

def signal_handler(signum, frame):
    """Handle system signals"""
    logger.info("🛑 تم استلام إشارة الإيقاف...")
    bot_system.stop()

def check_environment():
    """Check if required environment variables are set"""
    required_vars = ['BOT_TOKEN', 'API_ID', 'API_HASH']
    missing_vars = []

    for var in required_vars:
        value = os.getenv(var)
        if not value or (var != 'API_ID' and value == f'your_{var.lower()}_here'):
            missing_vars.append(var)

    if missing_vars:
        print("\n" + "="*60)
        print("❌ متغيرات البيئة المطلوبة مفقودة:")
        print("="*60)
        for var in missing_vars:
            if var == 'BOT_TOKEN':
                print(f"• {var}: احصل عليه من @BotFather في تليجرام")
            elif var == 'API_ID':
                print(f"• {var}: احصل عليه من my.telegram.org")
            elif var == 'API_HASH':
                print(f"• {var}: احصل عليه من my.telegram.org")
        print("="*60)
        print("🔧 كيفية إعداد المتغيرات:")
        print("1. انتقل إلى قسم Secrets في Replit")
        print("2. أضف المتغيرات المطلوبة مع قيمها")
        print("3. أعد تشغيل البرنامج")
        print("="*60)
        return False

    return True

def main():
    """Main function"""
    global bot_system

    logger.info("🚀 بدء تشغيل نظام بوت تليجرام...")

    # Check environment variables
    if not check_environment():
        sys.exit(1)

    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Create bot system instance
    bot_system = TelegramBotSystem()

    try:
        # Start all services
        bot_system.start_all_services()

        # Keep main thread alive
        while bot_system.running:
            time.sleep(1)

    except KeyboardInterrupt:
        logger.info("🛑 تم الإيقاف بواسطة المستخدم")
        bot_system.stop()
    except Exception as e:
        logger.error(f"❌ خطأ في النظام: {e}")
        bot_system.stop()

if __name__ == '__main__':
    main()