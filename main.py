#!/usr/bin/env python3
"""
Main entry point for Telegram Bot System
Only runs the Telegram bot - no web interface
"""

import threading
import time
import signal
import sys
import re
import os
import asyncio
import logging
from dotenv import load_dotenv
from bot_package.bot_simple import run_simple_bot
from userbot_service.userbot import userbot_instance, start_userbot_service, stop_userbot_service
from bot_package.config import BOT_TOKEN, API_ID, API_HASH

# Load environment variables from .env file
load_dotenv()

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
        """Start Telegram bot with maximum resilience"""
        global bot_instance
        logger.info("🤖 بدء تشغيل بوت التحكم المعزول...")
        
        max_retries = float('inf')  # Infinite retries
        retry_count = 0
        
        while self.running:
            try:
                retry_count += 1
                if retry_count > 1:
                    logger.info(f"🔄 إعادة تشغيل بوت التحكم (المحاولة {retry_count})")
                
                bot_instance = await run_simple_bot()
                if bot_instance and hasattr(bot_instance, 'bot'):
                    logger.info("✅ بوت التحكم جاهز ومعزول عن UserBot")
                    
                    # Keep the bot running
                    await bot_instance.bot.run_until_disconnected()
                else:
                    logger.error("❌ فشل في إنشاء instance البوت")
                    raise Exception("Bot instance creation failed")
                
                # If we reach here, bot disconnected normally
                if self.running:
                    logger.warning("⚠️ بوت التحكم انقطع - إعادة تشغيل...")
                    await asyncio.sleep(5)
                    
            except Exception as e:
                logger.error(f"❌ خطأ في بوت التحكم: {e}")
                logger.info("🔄 بوت التحكم سيعيد المحاولة - معزول عن مشاكل UserBot")
                
                # Progressive delay with longer waits to avoid rate limiting
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
                await asyncio.sleep(delay)
                
                # Reset counter after 10 failures
                if retry_count >= 10:
                    retry_count = 0

    def start_userbot_service_thread(self):
        """Start userbot service in async context with complete isolation from control bot"""
        logger.info("👤 بدء تشغيل خدمة UserBot...")
        
        # Set thread as daemon to ensure main bot continues if this fails
        import threading
        current_thread = threading.current_thread()
        try:
            current_thread.daemon = True
        except RuntimeError:
            pass
        
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Clean up any old session files on startup
            self.cleanup_old_sessions()
            
            async def userbot_main():
                userbot_failures = 0
                max_failures = 10  # Increased to allow more retries
                
                logger.info("🔄 بدء UserBot مع عزل كامل عن بوت التحكم")
                
                # إضافة فحص أولي للجلسات
                await self.check_and_cleanup_invalid_sessions()
                
                while self.running:  # Keep trying indefinitely
                    try:
                        logger.info(f"🔄 محاولة تشغيل UserBot (المحاولة {userbot_failures + 1})")
                        
                        # Start userbot service with error handling
                        userbot_started = await start_userbot_service()
                        
                        if not userbot_started:
                            logger.warning("⚠️ فشل في تشغيل UserBot - لا توجد جلسات صالحة")
                            logger.info("💡 بوت التحكم يعمل بشكل طبيعي ويسمح بإعادة تسجيل الدخول")
                            userbot_failures += 1
                            
                            # Progressive delay: start with 30 seconds, max 5 minutes
                            wait_time = min(30 + (userbot_failures * 30), 300)
                            logger.info(f"⏱️ انتظار {wait_time} ثانية قبل إعادة المحاولة...")
                            await asyncio.sleep(wait_time)
                            continue
                        
                        # Reset failure counter on successful start
                        userbot_failures = 0
                        logger.info("✅ UserBot يعمل - بوت التحكم مستقل تماماً")
                        
                        # Start background task processing only if userbot started successfully
                        async def background_admin_processor():
                            while self.running:
                                try:
                                    await asyncio.sleep(10)  # Check every 10 seconds
                                    if userbot_instance:
                                        await userbot_instance.process_pending_admin_tasks()
                                except Exception as e:
                                    logger.debug(f"خطأ في معالج المشرفين الخلفي: {e}")
                                    await asyncio.sleep(30)  # Wait longer if error
                        
                        # Start background processor
                        background_task = asyncio.create_task(background_admin_processor())
                        logger.info("🔄 تم تشغيل معالج المشرفين الخلفي")
                        
                        # Keep userbot running and monitor its health
                        logger.info("🚀 UserBot يعمل ويراقب الرسائل...")
                        
                        # Monitor userbot health
                        while self.running:
                            try:
                                # Check if userbot is still healthy
                                if userbot_instance and userbot_instance.clients:
                                    # Simple health check - if this fails, userbot needs restart
                                    await asyncio.sleep(30)  # Check every 30 seconds
                                else:
                                    logger.warning("⚠️ UserBot توقف - سيتم إعادة المحاولة")
                                    logger.info("💡 بوت التحكم يعمل بشكل طبيعي")
                                    break
                            except Exception as e:
                                logger.error(f"خطأ في مراقبة صحة UserBot: {e}")
                                logger.info("💡 بوت التحكم غير متأثر بهذا الخطأ")
                                break
                        
                        # Cancel background task if we exit the loop
                        if not background_task.done():
                            background_task.cancel()
                            
                    except Exception as e:
                        logger.error(f"🚫 خطأ في UserBot: {e}")
                        logger.info("💡 بوت التحكم يعمل بشكل طبيعي")
                        userbot_failures += 1
                        
                        # Progressive delay with better rate limiting handling
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
                        await asyncio.sleep(wait_time)
                        
                        # Reset failure counter after 10 failures to prevent infinite growth
                        if userbot_failures >= 10:
                            logger.info("🔄 إعادة تعيين عداد الفشل لتجنب التأخير المفرط")
                            userbot_failures = 0
                
                logger.info("📴 تم إيقاف UserBot بشكل طبيعي")
            
            # Run the userbot service
            if 'loop' in locals() and loop:
                loop.run_until_complete(userbot_main())
            else:
                logger.error("❌ Loop not initialized properly")
            
        except KeyboardInterrupt:
            logger.info("🛑 تم إيقاف UserBot بواسطة المستخدم")
        except Exception as e:
            logger.error(f"خطأ عام في خدمة UserBot: {e}")
            logger.info("💡 بوت التحكم يعمل بشكل طبيعي ولن يتأثر")
        finally:
            # Clean shutdown
            try:
                logger.info("📴 إغلاق خدمة UserBot...")
                if 'loop' in locals() and loop:
                    try:
                        loop.run_until_complete(stop_userbot_service())
                    except:
                        pass
                    try:
                        loop.close()
                    except:
                        pass
            except Exception as e:
                logger.error(f"خطأ في إغلاق UserBot: {e}")
            
            logger.info("✅ UserBot Service Thread منتهي - بوت التحكم يعمل بشكل طبيعي")

    async def check_and_cleanup_invalid_sessions(self):
        """فحص وتنظيف الجلسات المعطلة"""
        try:
            from database.database import Database
            db = Database()
            
            logger.info("🔍 فحص صحة الجلسات المحفوظة...")
            
            # جلب جميع الجلسات المصادق عليها
            authenticated_users = db.get_all_authenticated_users()
            
            invalid_sessions = 0
            for user_data in authenticated_users:
                user_id = user_data['user_id']
                
                # فحص إذا كانت الجلسة تحتوي على خطأ IP conflict
                health_status = db.get_session_health_status(user_id)
                if health_status and health_status.get('last_error_message'):
                    error_msg = health_status['last_error_message']
                    if "different IP addresses simultaneously" in error_msg:
                        logger.warning(f"🚫 جلسة معطلة بسبب تضارب IP: المستخدم {user_id}")
                        
                        # تحديث الجلسة كمعطلة
                        db.update_session_health(user_id, False, "IP conflict - re-login required")
                        invalid_sessions += 1
            
            if invalid_sessions > 0:
                logger.warning(f"⚠️ تم العثور على {invalid_sessions} جلسة معطلة")
                logger.info("💡 المستخدمون يحتاجون إعادة تسجيل الدخول عبر البوت")
            else:
                logger.info("✅ جميع الجلسات صحية")
                
        except Exception as e:
            logger.error(f"خطأ في فحص الجلسات: {e}")

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

        print("\n" + "="*70)
        print("🤖 نظام بوت التوجيه التلقائي - معزول ومستقل")
        print("="*70)
        print(f"🤖 بوت التحكم: @{bot_username}")
        print("📱 ابحث عن البوت في تليجرام وابدأ بـ /start")
        print("="*70)
        print("🛡️ الحماية المضمونة:")
        print("  ✅ بوت التحكم معزول تماماً عن UserBot")
        print("  ✅ لا يتوقف أبداً حتى لو فشلت جميع الجلسات")
        print("  ✅ يسمح بإعادة تسجيل الدخول في أي وقت")
        print("  ✅ إدارة المهام متاحة دائماً")
        print("="*70)
        print("📋 الخدمات:")
        print("  🟢 بوت التحكم (نشط دائماً)")
        print("  🔄 UserBot (حسب الجلسات المتاحة)")
        print("="*70)
        print("🔧 الميزات المتقدمة:")
        print("  • عزل كامل بين بوت التحكم وجلسات UserBot")
        print("  • إعادة تشغيل تلقائي للجلسات المعطلة")
        print("  • مراقبة صحة الجلسات كل 30 ثانية")
        print("  • تنظيف تلقائي للجلسات غير الصالحة")
        print("  • نظام تأخير تدريجي لإعادة المحاولة")
        print("="*70)
        print("💡 لبدء الاستخدام:")
        print("  1. ابحث عن البوت في تليجرام")
        print("  2. أرسل /start")
        print("  3. سجل دخولك برقم هاتفك")
        print("  4. أنشئ مهام التوجيه التلقائي")
        print("="*70)
        print("🔐 ضمان الاستمرارية:")
        print("  البوت يعمل دائماً حتى لو فشلت جميع جلسات UserBot")
        print("="*70)
        print("⌨️  اضغط Ctrl+C لإيقاف النظام")
        print("="*70)

    def cleanup_old_sessions(self):
        """Clean up old session files that might cause conflicts"""
        try:
            import glob
            import os
            from database.database import Database
            
            # Clean up database first
            logger.info("🧹 تنظيف قاعدة البيانات من الجلسات المعطلة...")
            db = Database()
            deleted_db_sessions = db.cleanup_broken_sessions()
            
            # Find all .session files
            session_files = glob.glob("*.session")
            
            if session_files:
                logger.info(f"🧹 تم العثور على {len(session_files)} ملف جلسة قديم")
                for session_file in session_files:
                    try:
                        os.remove(session_file)
                        logger.info(f"🗑️ تم حذف ملف الجلسة القديم: {session_file}")
                    except Exception as e:
                        logger.warning(f"⚠️ لا يمكن حذف {session_file}: {e}")
                        
                logger.info("✅ تم تنظيف ملفات الجلسات القديمة")
            else:
                logger.info("✅ لا توجد ملفات جلسات قديمة للحذف")
                
        except Exception as e:
            logger.error(f"خطأ في تنظيف الجلسات القديمة: {e}")

    def stop(self):
        """Stop all services"""
        logger.info("⏹️ إيقاف جميع الخدمات...")
        self.running = False

        # Stop userbot if running
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(userbot_instance.stop_all())
            loop.close()
        except Exception as e:
            logger.error(f"خطأ في إيقاف UserBot: {e}")

        logger.info("✅ تم إيقاف النظام بنجاح")
        sys.exit(0)

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

    # Signal handlers removed to avoid conflicts in threading

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