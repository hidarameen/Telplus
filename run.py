#!/usr/bin/env python3
import threading
import time
import signal
import sys
import os
from app import app
from bot import run_bot
from userbot import run_userbot
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TelegramBotSystem:
    def __init__(self):
        self.threads = []
        self.running = True
    
    def start_web_server(self):
        """Start Flask web server"""
        logger.info("🌐 بدء تشغيل خادم الويب...")
        app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
    
    def start_telegram_bot(self):
        """Start Telegram bot"""
        logger.info("🤖 بدء تشغيل بوت تليجرام...")
        try:
            run_bot()
        except Exception as e:
            logger.error(f"خطأ في بوت تليجرام: {e}")
    
    def start_userbot(self):
        """Start userbot service"""
        logger.info("👤 بدء تشغيل خدمة UserBot...")
        # Wait a bit for web server to start
        time.sleep(3)
        try:
            run_userbot()
        except Exception as e:
            logger.error(f"خطأ في UserBot: {e}")
    
    def start_all_services(self):
        """Start all services in separate threads"""
        logger.info("🚀 بدء تشغيل نظام بوت تليجرام...")
        
        # Start web server
        web_thread = threading.Thread(target=self.start_web_server, daemon=True)
        web_thread.start()
        self.threads.append(web_thread)
        
        # Start Telegram bot
        bot_thread = threading.Thread(target=self.start_telegram_bot, daemon=True)
        bot_thread.start()
        self.threads.append(bot_thread)
        
        # Start userbot (will start when session is available)
        userbot_thread = threading.Thread(target=self.start_userbot, daemon=True)
        userbot_thread.start()
        self.threads.append(userbot_thread)
        
        logger.info("✅ تم تشغيل جميع الخدمات بنجاح")
        self.print_startup_info()
    
    def print_startup_info(self):
        """Print startup information"""
        print("\n" + "="*60)
        print("🤖 نظام بوت التوجيه التلقائي - تليجرام")
        print("="*60)
        print(f"🌐 لوحة التحكم الويب: http://localhost:5000")
        print(f"🤖 بوت تليجرام: @{os.getenv('BOT_TOKEN', 'your_bot_token').split(':')[0] if os.getenv('BOT_TOKEN') else 'غير محدد'}")
        print(f"👤 UserBot: سيتم التشغيل بعد تسجيل الدخول")
        print("="*60)
        print("📋 الخدمات النشطة:")
        print("  ✅ خادم الويب (Flask)")
        print("  ✅ بوت التحكم (Telegram Bot API)")
        print("  ⏳ UserBot (في انتظار الجلسة)")
        print("="*60)
        print("⌨️  اضغط Ctrl+C لإيقاف النظام")
        print("="*60)
    
    def stop(self):
        """Stop all services"""
        logger.info("⏹️ إيقاف جميع الخدمات...")
        self.running = False
        
        # Give threads time to cleanup
        time.sleep(2)
        
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
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error("❌ متغيرات البيئة المفقودة:")
        for var in missing_vars:
            logger.error(f"  - {var}")
        logger.error("يرجى تعيين هذه المتغيرات قبل تشغيل النظام")
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
