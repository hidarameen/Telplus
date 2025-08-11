"""
Simple Telegram Bot using Telethon
Handles bot API and user API functionality
"""
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.sessions import StringSession
from database.database import Database
from userbot_service.userbot import userbot_instance
from bot_package.config import BOT_TOKEN, API_ID, API_HASH
import json
import time
import os
from datetime import datetime

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    def __init__(self):
        self.db = Database()
        self.bot = None
        self.conversation_states = {}
        self.user_states = {}  # For handling user input states

    def set_user_state(self, user_id, state, data=None):
        """Set user conversation state"""
        self.user_states[user_id] = {'state': state, 'data': data or {}}
    
    def get_user_state(self, user_id):
        """Get user conversation state"""
        return self.user_states.get(user_id, {}).get('state', None)
    
    def clear_user_state(self, user_id):
        """Clear user conversation state"""
        self.user_states.pop(user_id, None)

    async def start(self):
        """Start the bot"""
        if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
            logger.error("❌ BOT_TOKEN غير محدد في متغيرات البيئة")
            return False

        # Create bot client with unique session name
        self.bot = TelegramClient('simple_bot_session', int(API_ID), API_HASH)
        await self.bot.start(bot_token=BOT_TOKEN)

        # Add event handlers
        self.bot.add_event_handler(self.handle_start, events.NewMessage(pattern='/start'))
        self.bot.add_event_handler(self.handle_callback, events.CallbackQuery())
        self.bot.add_event_handler(self.handle_message, events.NewMessage())

        # Start notification monitoring task
        asyncio.create_task(self.monitor_notifications())

        logger.info("✅ Bot started successfully!")
        return True

    async def handle_start(self, event):
        """Handle /start command"""
        logger.info(f"📥 تم استلام أمر /start من المستخدم: {event.sender_id}")
        
        # Only respond to /start in private chats
        if not event.is_private:
            logger.info(f"🚫 تجاهل أمر /start في محادثة غير خاصة: {event.chat_id}")
            return

        user_id = event.sender_id
        logger.info(f"🔍 فحص حالة المصادقة للمستخدم: {user_id}")

        # Check if user is authenticated
        is_authenticated = self.db.is_user_authenticated(user_id)
        logger.info(f"🔐 حالة المصادقة للمستخدم {user_id}: {'مُصادق عليه' if is_authenticated else 'غير مُصادق عليه'}")
        
        if is_authenticated:
            # Show main menu
            buttons = [
                [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
                [Button.inline("⚙️ الإعدادات", b"settings")],
                [Button.inline("ℹ️ حول البوت", b"about")]
            ]

            logger.info(f"📤 إرسال قائمة رئيسية للمستخدم المُصادق عليه: {user_id}")
            await event.respond(
                f"🎉 أهلاً بك في بوت التوجيه التلقائي!\n\n"
                f"👋 مرحباً {event.sender.first_name}\n"
                f"🔑 أنت مسجل دخولك بالفعل\n\n"
                f"اختر ما تريد فعله:",
                buttons=buttons
            )
            logger.info(f"✅ تم إرسال الرد بنجاح للمستخدم: {user_id}")
        else:
            # Show authentication menu
            buttons = [
                [Button.inline("📱 تسجيل الدخول برقم الهاتف", b"auth_phone")]
            ]

            logger.info(f"📤 إرسال قائمة تسجيل الدخول للمستخدم غير المُصادق عليه: {user_id}")
            await event.respond(
                f"🤖 مرحباً بك في بوت التوجيه التلقائي!\n\n"
                f"📋 هذا البوت يساعدك في:\n"
                f"• توجيه الرسائل تلقائياً\n"
                f"• إدارة مهام التوجيه\n"
                f"• مراقبة المحادثات\n\n"
                f"🔐 يجب تسجيل الدخول أولاً:",
                buttons=buttons
            )
            logger.info(f"✅ تم إرسال رد التسجيل بنجاح للمستخدم: {user_id}")


    async def handle_callback(self, event):
        """Handle button callbacks"""
        try:
            data = event.data.decode('utf-8')
            user_id = event.sender_id

            if data == "auth_phone":
                await self.start_auth(event)
            elif data == "manage_tasks":
                await self.show_tasks_menu(event)
            elif data == "create_task":
                await self.start_create_task(event)
            elif data == "list_tasks":
                await self.list_tasks(event)
            elif data.startswith("task_toggle_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.toggle_task(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للتبديل: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("task_delete_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.delete_task(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للحذف: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("task_manage_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_task_details(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للإدارة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("task_settings_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_task_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للإعدادات: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_forward_mode_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_forward_mode(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل وضع التوجيه: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("manage_sources_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.manage_task_sources(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإدارة المصادر: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("manage_targets_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.manage_task_targets(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإدارة الأهداف: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("add_source_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.start_add_source(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإضافة مصدر: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("add_target_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.start_add_target(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإضافة هدف: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("remove_source_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        source_id = int(parts[2])
                        task_id = int(parts[3])
                        await self.remove_source(event, source_id, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المصدر/المهمة لحذف المصدر: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("remove_target_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        target_id = int(parts[2])
                        task_id = int(parts[3])
                        await self.remove_target(event, target_id, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف الهدف/المهمة لحذف الهدف: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data == "settings":
                await self.show_settings(event)
            elif data == "check_userbot":
                await self.check_userbot_status(event)
            elif data == "about":
                await self.show_about(event)
            elif data == "main_menu":
                await self.show_main_menu(event)
            elif data == "back_main":
                await self.show_main_menu(event)
            elif data == "cancel_auth":
                await self.cancel_auth(event)
            elif data == "login": # Added handler for login button
                await self.handle_relogin(event)
            elif data == "timezone_settings":
                await self.show_timezone_settings(event)
            elif data == "language_settings":
                await self.show_language_settings(event)
            elif data.startswith("set_timezone_"):
                timezone = data.replace("set_timezone_", "")
                await self.set_user_timezone(event, timezone)
            elif data.startswith("set_language_"):
                language = data.replace("set_language_", "")
                await self.set_user_language(event, language)
            elif data.startswith("advanced_filters_"): # Handler for advanced filters
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_advanced_filters(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للفلاتر المتقدمة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("advanced_features_"): # Handler for advanced features
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_advanced_features(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للميزات المتقدمة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("character_limit_"): # Handler for character limit settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_character_limit_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات حد الأحرف: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("rate_limit_"): # Handler for rate limit settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_rate_limit_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات حد الرسائل: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("forwarding_delay_"): # Handler for forwarding delay settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_forwarding_delay_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات تأخير التوجيه: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("sending_interval_"): # Handler for sending interval settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_sending_interval_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات فاصل الإرسال: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_char_limit_"): # Toggle character limit
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_character_limit(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل حد الأحرف: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_char_mode_"): # Toggle character limit mode
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_character_limit_mode(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل وضع حد الأحرف: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_rate_limit_"): # Toggle rate limit
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_rate_limit(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل حد الرسائل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_forwarding_delay_"): # Toggle forwarding delay
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_forwarding_delay(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل تأخير التوجيه: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_settings_"): # Handler for watermark settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات العلامة المائية: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_"): # Toggle watermark
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.toggle_watermark(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_appearance_"): # Watermark appearance settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_appearance(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات مظهر العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_type_"): # Watermark type settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_type(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات نوع العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_media_"): # Watermark media types
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_media_types(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لأنواع الوسائط للعلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_size_up_"): # Increase watermark size
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_size(event, task_id, increase=True)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لزيادة حجم العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_size_down_"): # Decrease watermark size
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_size(event, task_id, increase=False)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتقليل حجم العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_opacity_up_"): # Increase watermark opacity
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_opacity(event, task_id, increase=True)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لزيادة شفافية العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_opacity_down_"): # Decrease watermark opacity
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_opacity(event, task_id, increase=False)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتقليل شفافية العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_font_up_"): # Increase watermark font size
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_font_size(event, task_id, increase=True)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لزيادة حجم خط العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_font_down_"): # Decrease watermark font size
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_font_size(event, task_id, increase=False)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتقليل حجم خط العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_default_up_"): # Increase default watermark size
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_default_size(event, task_id, increase=True)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لزيادة الحجم الافتراضي: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_default_down_"): # Decrease default watermark size
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_default_size(event, task_id, increase=False)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتقليل الحجم الافتراضي: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_apply_default_"): # Apply default size
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.apply_default_watermark_size(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتطبيق الحجم الافتراضي: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_offset_left_"): # Move watermark left
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_offset(event, task_id, axis='x', increase=False)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للإزاحة يساراً: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_offset_right_"): # Move watermark right
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_offset(event, task_id, axis='x', increase=True)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للإزاحة يميناً: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_offset_up_"): # Move watermark up
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_offset(event, task_id, axis='y', increase=False)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للإزاحة أعلى: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_offset_down_"): # Move watermark down
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.adjust_watermark_offset(event, task_id, axis='y', increase=True)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للإزاحة أسفل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_reset_offset_"): # Reset watermark offset
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.reset_watermark_offset(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعادة تعيين الإزاحة: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_position_selector_"): # Show watermark position selector
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.show_watermark_position_selector(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لعرض أختيار موضع العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_watermark_position_"): # Set watermark position
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        position = parts[3]
                        task_id = int(parts[4])
                        await self.set_watermark_position(event, task_id, position)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعيين موضع العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_watermark_type_"): # Set watermark type
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        watermark_type = parts[3]  # text or image
                        task_id = int(parts[4])
                        await self.set_watermark_type(event, task_id, watermark_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل نوع العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")

            elif data.startswith("toggle_sending_interval_"): # Toggle sending interval
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_sending_interval(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل فاصل الإرسال: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_char_range_"): # Handler for editing character range
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_edit_character_range(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل نطاق الأحرف: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_rate_count_"): # Handler for editing rate count
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_edit_rate_count(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل عدد الرسائل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_rate_period_"): # Handler for editing rate period
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_edit_rate_period(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل فترة الرسائل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_forwarding_delay_"): # Handler for editing forwarding delay
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_edit_forwarding_delay(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل تأخير التوجيه: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_sending_interval_"): # Handler for editing sending interval
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_edit_sending_interval(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل فاصل الإرسال: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("day_filters_"): # Handler for day filters
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_day_filters(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلاتر الأيام: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("working_hours_filter_"): # Handler for working hours
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.show_working_hours_filter(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلتر ساعات العمل: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("language_filters_"): # Handler for language filters
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_language_filters(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلاتر اللغات: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("admin_filters_"): # Handler for admin filters
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_admin_filters(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلاتر المشرفين: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("admin_list_"): # Handler for admin list
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_admin_list(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لقائمة المشرفين: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_settings_"): # Handler for watermark settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_") and not data.startswith("toggle_watermark_photos_") and not data.startswith("toggle_watermark_videos_") and not data.startswith("toggle_watermark_documents_"): # Handler for toggle watermark
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.toggle_watermark(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_config_"): # Handler for watermark config
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_config(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتكوين العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_media_"): # Handler for watermark media settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_media_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات وسائط العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_text_"): # Handler for watermark text setting
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.start_set_watermark_text(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل نص العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_image_"): # Handler for watermark image setting
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.start_set_watermark_image(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل صورة العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_position_"): # Handler for watermark position setting
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_position_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل موقع العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_appearance_"): # Handler for watermark appearance setting
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_appearance_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل مظهر العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_photos_"): # Handler for toggle watermark photos
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_watermark_media_type(event, task_id, 'photos')
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للصور: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_videos_"): # Handler for toggle watermark videos
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_watermark_media_type(event, task_id, 'videos')
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للفيديوهات: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_documents_"): # Handler for toggle watermark documents
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_watermark_media_type(event, task_id, 'documents')
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للمستندات: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_watermark_position_"): # Handler for set watermark position
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[3])
                        position = parts[4]
                        await self.set_watermark_position(event, task_id, position)
                    except (ValueError, IndexError) as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد موقع العلامة المائية: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_watermark_"): # Handler for editing watermark appearance
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        setting_type = parts[2]  # size, opacity, font_size, color
                        task_id = int(parts[3])
                        await self.start_edit_watermark_setting(event, task_id, setting_type)
                    except (ValueError, IndexError) as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحرير العلامة المائية: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("source_admins_"): # Handler for source admins
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        source_chat_id = parts[3]
                        await self.show_source_admins(event, task_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة/المصدر لمشرفي المصدر: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("refresh_source_admins_"): # Handler for refreshing source admins
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        source_chat_id = parts[4]
                        await self.refresh_source_admin_list(event, task_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة/المصدر لتحديث المشرفين: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
                    except IndexError as e:
                        logger.error(f"❌ خطأ في تحليل البيانات لتحديث المشرفين: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_admin_"): # Handler for toggle admin
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        admin_user_id = int(parts[3])
                        source_chat_id = parts[4] if len(parts) >= 5 else None
                        await self.toggle_admin(event, task_id, admin_user_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة/المشرف للتبديل: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("duplicate_filter_"): # Handler for duplicate filter
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_duplicate_filter(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلتر التكرار: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("duplicate_settings_"): # Handler for duplicate settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_duplicate_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات التكرار: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("inline_button_filter_"): # Handler for inline button filter
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.show_inline_button_filter(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلتر الأزرار الشفافة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("forwarded_msg_filter_"): # Handler for forwarded message filter
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.show_forwarded_message_filter(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلتر الرسائل المعاد توجيهها: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_settings_"): # Handler for watermark settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات العلامة المائية: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_"): # Handler for toggle watermark
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.toggle_watermark(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_config_"): # Handler for watermark configuration
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_config(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات العلامة المائية: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_media_"): # Handler for watermark media settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_watermark_media_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات وسائط العلامة المائية: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_photos_"): # Handler for toggle watermark photos
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_watermark_media_type(event, task_id, 'photos')
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_videos_"): # Handler for toggle watermark videos
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_watermark_media_type(event, task_id, 'videos')
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_documents_"): # Handler for toggle watermark documents
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_watermark_media_type(event, task_id, 'documents')
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_inline_block_"): # Handler for toggle inline button block
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_inline_button_filter(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل حظر الأزرار: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("clear_text_clean_keywords_"):
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[4])
                        await self.clear_text_cleaning_keywords(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لمسح كلمات التنظيف: {e}, data='{data}'")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("text_formatting_"): # Handler for text formatting
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_text_formatting(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتنسيق النصوص: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_text_formatting_"): # Handler for toggling text formatting
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_text_formatting(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل تنسيق النص: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_text_format_"): # Handler for setting text format type
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        format_type = parts[3]
                        task_id = int(parts[4])
                        await self.set_text_format_type(event, task_id, format_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد نوع التنسيق: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_hyperlink_"): # Handler for editing hyperlink settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.start_edit_hyperlink_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل إعدادات الرابط: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_forwarded_block_"): # Handler for toggle forwarded message block
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_forwarded_message_block(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل حظر الرسائل المعاد توجيهها: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_advanced_filter_"): # Handler for toggling advanced filters
                parts = data.split("_")
                logger.info(f"🔍 Processing toggle_advanced_filter: data='{data}', parts={parts}")
                if len(parts) >= 4:
                    try:
                        # Extract task_id (always the last part)
                        task_id = int(parts[-1])
                        
                        # Extract filter_type (everything between 'toggle_advanced_filter_' and task_id)
                        filter_type = "_".join(parts[3:-1])
                        
                        logger.info(f"✅ Parsed task_id={task_id}, filter_type='{filter_type}'")
                        await self.toggle_advanced_filter(event, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الفلتر المتقدم: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_day_"): # Handler for day filter toggles
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        day_number = int(parts[3])
                        await self.toggle_day_filter(event, task_id, day_number)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل فلتر اليوم: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("select_all_days_"): # Handler for select all days
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.select_all_days(event, task_id, True)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد كل الأيام: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("deselect_all_days_"): # Handler for deselect all days
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.select_all_days(event, task_id, False)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإلغاء تحديد كل الأيام: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("media_filters_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_media_filters(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلاتر الوسائط: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_media_check_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_media_check(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل فحص الوسائط: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_text_check_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_text_check(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل فحص النص: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_threshold_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.set_duplicate_threshold(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد نسبة التشابه: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_time_window_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.set_duplicate_time_window(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد النافذة الزمنية: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_media_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        media_type = parts[3]
                        await self.toggle_media_filter(event, task_id, media_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل فلتر الوسائط: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("allow_all_media_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    task_id = int(parts[3])
                    await self.set_all_media_filters(event, task_id, True)
            elif data.startswith("block_all_media_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    task_id = int(parts[3])
                    await self.set_all_media_filters(event, task_id, False)
            elif data.startswith("reset_media_filters_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    task_id = int(parts[3])
                    await self.reset_media_filters(event, task_id)
            elif data.startswith("word_filters_"): # Handler for word filters
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_word_filters(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلاتر الكلمات: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_word_filter_"): # Handler for toggling word filter
                parts = data.split("_")
                logger.info(f"🔍 Toggle word filter callback: data='{data}', parts={parts}")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[3])  # Fixed: task_id is at index 3
                        filter_type = parts[4]   # Fixed: filter_type is at index 4
                        await self.toggle_word_filter(event, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("manage_words_"): # Handler for managing words in a filter
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        filter_type = parts[3] # 'whitelist' or 'blacklist'
                        await self.manage_words(event, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإدارة الكلمات: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("add_word_"): # Handler for adding a word to a filter
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[2])
                        filter_type = parts[3]
                        await self.start_add_word(event, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإضافة كلمة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("remove_word_"): # Handler for removing a word from a filter
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        word_id = int(parts[2])
                        task_id = int(parts[3])
                        filter_type = parts[4]
                        await self.remove_word(event, word_id, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف الكلمة/المهمة لحذف الكلمة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("view_filter_"): # Handler for viewing filter words
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        filter_type = parts[3]
                        await self.view_filter_words(event, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لعرض الفلتر: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("manage_whitelist_"): # Handler for whitelist management
                await self.handle_manage_whitelist(event)
            elif data.startswith("manage_blacklist_"): # Handler for blacklist management
                await self.handle_manage_blacklist(event)
            elif data.startswith("add_multiple_words_"): # Handler for adding multiple words
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        logger.info(f"🔍 Processing add_multiple_words: data='{data}', parts={parts}")
                        # add_multiple_words_6_whitelist -> ['add', 'multiple', 'words', '6', 'whitelist']
                        task_id = int(parts[3])  # parts[3] = '6'
                        filter_type = parts[4]   # parts[4] = 'whitelist'
                        logger.info(f"✅ Parsed task_id={task_id}, filter_type={filter_type}")
                        await self.start_add_multiple_words(event, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإضافة كلمات متعددة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("clear_filter_"): # Handler for clearing filter with confirmation
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        filter_type = parts[3]
                        await self.clear_filter_with_confirmation(event, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لمسح الفلتر: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("confirm_clear_"): # Handler for confirming filter clear
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        filter_type = parts[3]
                        await self.confirm_clear_filter(event, task_id, filter_type)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتأكيد المسح: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("text_replacements_"): # Handler for text replacements
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_text_replacements(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لاستبدال النصوص: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("text_cleaning_"): # Handler for text cleaning
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_text_cleaning(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتنظيف النصوص: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("translation_settings_"): # Handler for translation settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_translation_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات الترجمة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_text_clean_"): # Handler for toggling text cleaning settings
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        setting_type = parts[3]
                        task_id = int(parts[4]) if len(parts) >= 5 else int(parts[3])
                        if setting_type in ['remove', 'links', 'emojis', 'hashtags', 'phone', 'empty', 'keywords', 'caption']:
                            await self.toggle_text_cleaning_setting(event, task_id, setting_type)
                        else:
                            logger.error(f"نوع إعداد تنظيف النص غير صالح: {setting_type}")
                            await event.answer("❌ نوع إعداد غير صالح")
                    except (ValueError, IndexError) as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل تنظيف النص: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_translation_"): # Handler for toggling translation
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.toggle_translation(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الترجمة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_translation_"): # Handler for setting translation languages
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        setting = parts[2] # source or target
                        task_id = int(parts[3])
                        await self.set_translation_language(event, task_id, setting)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل لغة الترجمة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_lang_"): # Handler for setting specific language
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        setting = parts[2] # source or target
                        task_id = int(parts[3])
                        language_code = parts[4]
                        await self.set_specific_language(event, task_id, setting, language_code)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل لغة محددة: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("manage_text_clean_keywords_"): # Handler for managing text cleaning keywords
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[4])
                        await self.manage_text_cleaning_keywords(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإدارة كلمات التنظيف: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("add_text_clean_keywords_"): # Handler for adding text cleaning keywords
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[4])
                        await self.start_adding_text_cleaning_keywords(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإضافة كلمات تنظيف: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_replacement_"): # Handler for toggling text replacements
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.toggle_text_replacement(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الاستبدال: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("add_replacement_"): # Handler for adding replacements
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.start_add_replacement(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإضافة الاستبدال: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("view_replacements_"): # Handler for viewing replacements
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.view_replacements(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لعرض الاستبدالات: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("clear_replacements_"): # Handler for clearing replacements
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.clear_replacements_confirm(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لحذف الاستبدالات: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("confirm_clear_replacements_"): # Handler for confirming clear replacements
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.clear_replacements_execute(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتأكيد حذف الاستبدالات: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("header_settings_"): # Handler for header settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_header_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات الرأس: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("footer_settings_"): # Handler for footer settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_footer_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات الذيل: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("inline_buttons_"): # Handler for inline buttons
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_inline_buttons_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات الأزرار: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_header_"): # Handler for toggling header
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.toggle_header(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الرأس: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_footer_"): # Handler for toggling footer
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.toggle_footer(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الذيل: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_header_"): # Handler for editing header
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.start_edit_header(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل الرأس: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_footer_"): # Handler for editing footer
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.start_edit_footer(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل الذيل: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_inline_buttons_"): # Handler for toggling inline buttons
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_inline_buttons(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الأزرار: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("add_inline_button_"): # Handler for adding inline button
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_add_inline_button(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإضافة زر: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("view_inline_buttons_"): # Handler for viewing inline buttons
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.view_inline_buttons(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لعرض الأزرار: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("clear_inline_buttons_"): # Handler for clearing inline buttons
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.clear_inline_buttons_confirm(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لحذف الأزرار: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("confirm_clear_inline_buttons_"): # Handler for confirming clear inline buttons
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        # Get the last part which should be the task_id
                        task_id = int(parts[-1])
                        await self.clear_inline_buttons_execute(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتأكيد حذف الأزرار: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("forwarding_settings_"): # Handler for forwarding settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_forwarding_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات التوجيه: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("approve_"):
                # Handle message approval
                try:
                    pending_id = int(data.split("_")[1])
                    await self.handle_message_approval(event, pending_id, True)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف الرسالة المعلقة للموافقة: {e}")
                    await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("reject_"):
                # Handle message rejection
                try:
                    pending_id = int(data.split("_")[1])
                    await self.handle_message_approval(event, pending_id, False)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف الرسالة المعلقة للرفض: {e}")
                    await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("details_"):
                # Handle showing message details
                try:
                    pending_id = int(data.split("_")[1])
                    await self.show_pending_message_details(event, pending_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف الرسالة المعلقة للتفاصيل: {e}")
                    await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("publishing_mode_"):
                # Handle publishing mode settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_publishing_mode_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات وضع النشر: {e}")
                        await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("toggle_publishing_mode_"):
                # Handle publishing mode toggle
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_publishing_mode(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل وضع النشر: {e}")
                        await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("toggle_split_album_"): # Handler for toggling split album
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_split_album(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل تقسيم الألبوم: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_link_preview_"): # Handler for toggling link preview
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_link_preview(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل معاينة الرابط: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_pin_message_"): # Handler for toggling pin message
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_pin_message(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل تثبيت الرسالة: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_silent_notifications_"): # Handler for toggling silent notifications
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_silent_notifications(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الإشعارات الصامتة: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_auto_delete_"): # Handler for toggling auto delete
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_auto_delete(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الحذف التلقائي: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_sync_edit_"): # Handler for toggling sync edit
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_sync_edit(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل مزامنة التعديل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_sync_delete_"): # Handler for toggling sync delete
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_sync_delete(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل مزامنة الحذف: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_auto_delete_time_"): # Handler for setting auto delete time
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[4])
                        await self.start_set_auto_delete_time(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد وقت الحذف التلقائي: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_delete_time_"): # Handler for direct time setting
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        seconds = int(parts[4])
                        await self.set_delete_time_direct(event, task_id, seconds)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة أو الوقت: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_inline_block_"): # Handler for toggling inline button block
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_inline_button_block(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل حظر الأزرار: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_forwarded_block_"): # Handler for toggling forwarded message block
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_forwarded_message_block(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل حظر الرسائل المعاد توجيهها: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_working_hours_"): # Handler for setting working hours
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_set_working_hours(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد ساعات العمل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_working_hours_") and not data.startswith("toggle_working_hours_mode_"): # Handler for toggling working hours filter
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_working_hours(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل ساعات العمل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_working_hours_mode_"): # Handler for toggling working hours mode
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        # Extract task_id - it should be the last part
                        task_id = int(parts[-1])
                        await self.toggle_working_hours_mode(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل وضع ساعات العمل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("schedule_working_hours_"): # Handler for schedule working hours
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.schedule_working_hours(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لجدولة ساعات العمل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_hour_"): # Handler for toggling specific hour
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        hour = int(parts[3])
                        await self.toggle_hour(event, task_id, hour)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة أو الساعة: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("select_all_hours_"): # Handler for selecting all hours
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.select_all_hours(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد جميع الساعات: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("clear_all_hours_"): # Handler for clearing all hours
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.clear_all_hours(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإلغاء جميع الساعات: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("add_language_") or data.startswith("add_custom_language_"): # Handler for adding language
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        if data.startswith("add_custom_language_"):
                            task_id = int(parts[3])
                        else:
                            task_id = int(parts[2])
                        await self.start_add_language(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإضافة لغة: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("quick_add_lang_"): # Handler for quick language addition
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[3])
                        language_code = parts[4]
                        language_name = "_".join(parts[5:]) if len(parts) > 5 else parts[4]
                        await self.quick_add_language(event, task_id, language_code, language_name)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في إضافة اللغة السريعة: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_lang_selection_"): # Handler for toggling language selection
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[3])
                        language_code = parts[4]
                        await self.toggle_language_selection(event, task_id, language_code)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تبديل اللغة: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_language_mode_"): # Handler for toggling language mode
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_language_mode(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تبديل وضع اللغة: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("clear_all_languages_"): # Handler for clearing all languages
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.clear_all_languages(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في مسح اللغات: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("duplicate_settings_"): # Handler for duplicate settings
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_duplicate_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات التكرار: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("refresh_admins_"): # Handler for refreshing admins
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.refresh_admin_list(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديث المشرفين: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("admin_list_"): # Handler for showing admin list (source channels)
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_admin_list(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لقائمة المشرفين: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("source_admins_"): # Handler for showing specific source admins
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        source_chat_id = parts[3]
                        await self.show_source_admins(event, task_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لمشرفي المصدر: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_admin_"): # Handler for toggling individual admin
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        admin_user_id = int(parts[3])
                        await self.toggle_admin(event, task_id, admin_user_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة/المشرف: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("refresh_source_admins_"): # Handler for refreshing specific source admins
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[3])
                        source_chat_id = parts[4]
                        await self.refresh_source_admin_list(event, task_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة/المصدر: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")

        except Exception as e:
            import traceback
            logger.error(f"خطأ في معالج الأزرار: {e}, data='{data}', user_id={user_id}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            try:
                await event.answer("❌ حدث خطأ، حاول مرة أخرى")
            except:
                pass  # Sometimes event.answer fails if callback is already processed

    async def toggle_advanced_filter(self, event, task_id, filter_type):
        """Toggle advanced filter setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get current settings
            settings = self.db.get_advanced_filters_settings(task_id)
            current_value = settings.get(filter_type, False)
            new_value = not current_value
            
            # Update the setting
            success = self.db.update_advanced_filter_setting(task_id, filter_type, new_value)
            
            if success:
                status = "تم التفعيل" if new_value else "تم التعطيل"
                await event.answer(f"✅ {status}")
                
                # Force refresh UserBot tasks
                try:
                    from userbot_service.userbot import userbot_instance
                    if user_id in userbot_instance.clients:
                        await userbot_instance.refresh_user_tasks(user_id)
                        logger.info(f"🔄 تم تحديث مهام UserBot بعد تغيير الفلتر المتقدم")
                except Exception as e:
                    logger.error(f"خطأ في تحديث مهام UserBot: {e}")
                
                # Return to advanced filters menu
                await self.show_advanced_filters(event, task_id)
            else:
                await event.answer("❌ فشل في تحديث الإعداد")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل الفلتر المتقدم: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def show_day_filters(self, event, task_id):
        """Show day filters settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        settings = self.db.get_advanced_filters_settings(task_id)
        is_enabled = settings.get('day_filter_enabled', False)
        day_filters = self.db.get_day_filters(task_id)
        
        status_text = "🟢 مفعل" if is_enabled else "🔴 معطل"
        
        # Create day selection buttons
        days = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
        day_buttons = []
        
        for i, day in enumerate(days, 1):
            is_selected = any(df['day_number'] == i for df in day_filters)
            icon = "✅" if is_selected else "❌"
            day_buttons.append(Button.inline(f"{icon} {day}", f"toggle_day_{task_id}_{i}"))
        
        # Arrange buttons in rows of 2
        arranged_buttons = []
        for i in range(0, len(day_buttons), 2):
            if i + 1 < len(day_buttons):
                arranged_buttons.append([day_buttons[i], day_buttons[i + 1]])
            else:
                arranged_buttons.append([day_buttons[i]])
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_advanced_filter_day_filter_enabled_{task_id}")],
        ] + arranged_buttons + [
            [Button.inline("✅ تحديد الكل", f"select_all_days_{task_id}"),
             Button.inline("❌ إلغاء الكل", f"deselect_all_days_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"📅 فلتر الأيام - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📋 الأيام المحددة: {len(day_filters)}/7\n\n"
            f"اختر الأيام المسموح بالتوجيه فيها:",
            buttons=buttons
        )

    async def toggle_day_filter(self, event, task_id, day_number):
        """Toggle specific day filter"""
        user_id = event.sender_id
        
        try:
            # Get current day filters
            day_filters = self.db.get_day_filters(task_id)
            is_selected = any(df['day_number'] == day_number for df in day_filters)
            
            if is_selected:
                # Remove the day by setting to False
                success = self.db.set_day_filter(task_id, day_number, False)
                action = "تم إلغاء تحديد"
            else:
                # Add the day by setting to True
                success = self.db.set_day_filter(task_id, day_number, True)
                action = "تم تحديد"
            
            if success:
                days = ["", "الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
                await event.answer(f"✅ {action} {days[day_number]}")
                
                # Force refresh UserBot tasks
                try:
                    from userbot_service.userbot import userbot_instance
                    if user_id in userbot_instance.clients:
                        await userbot_instance.refresh_user_tasks(user_id)
                except Exception as e:
                    logger.error(f"خطأ في تحديث مهام UserBot: {e}")
                
                # Refresh the menu - catch content modification error
                try:
                    await self.show_day_filters(event, task_id)
                except Exception as e:
                    if "Content of the message was not modified" in str(e):
                        logger.debug("المحتوى لم يتغير، تجاهل الخطأ")
                    else:
                        raise e
            else:
                await event.answer("❌ فشل في التحديث")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل فلتر اليوم: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def select_all_days(self, event, task_id, select_all=True):
        """Select or deselect all days"""
        user_id = event.sender_id
        
        try:
            if select_all:
                # Add all days using set_day_filter
                for day_num in range(1, 8):
                    self.db.set_day_filter(task_id, day_num, True)
                await event.answer("✅ تم تحديد جميع الأيام")
            else:
                # Remove all days using set_day_filter with False
                for day_num in range(1, 8):
                    self.db.set_day_filter(task_id, day_num, False)
                await event.answer("✅ تم إلغاء تحديد جميع الأيام")
            
            # Force refresh UserBot tasks
            try:
                from userbot_service.userbot import userbot_instance
                if user_id in userbot_instance.clients:
                    await userbot_instance.refresh_user_tasks(user_id)
            except Exception as e:
                logger.error(f"خطأ في تحديث مهام UserBot: {e}")
            
            # Refresh the menu - catch content modification error
            try:
                await self.show_day_filters(event, task_id)
            except Exception as e:
                if "Content of the message was not modified" in str(e):
                    logger.debug("المحتوى لم يتغير، تجاهل الخطأ")
                else:
                    raise e
            
        except Exception as e:
            logger.error(f"خطأ في تحديد/إلغاء جميع الأيام: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def show_advanced_filters(self, event, task_id):
        """Show advanced filters menu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get all advanced filter settings
        settings = self.db.get_advanced_filters_settings(task_id)
        
        # Status indicators
        day_status = "🟢" if settings.get('day_filter_enabled', False) else "🔴"
        hours_status = "🟢" if settings.get('working_hours_enabled', False) else "🔴"
        lang_status = "🟢" if settings.get('language_filter_enabled', False) else "🔴"
        admin_status = "🟢" if settings.get('admin_filter_enabled', False) else "🔴"
        duplicate_status = "🟢" if settings.get('duplicate_filter_enabled', False) else "🔴"
        inline_status = "🟢" if settings.get('inline_button_filter_enabled', False) else "🔴"
        forwarded_status = "🟢" if settings.get('forwarded_message_filter_enabled', False) else "🔴"
        
        buttons = [
            [Button.inline(f"{day_status} فلتر الأيام", f"day_filters_{task_id}"),
             Button.inline(f"{hours_status} ساعات العمل", f"working_hours_filter_{task_id}")],
            [Button.inline(f"{lang_status} فلتر اللغات", f"language_filters_{task_id}"),
             Button.inline(f"{admin_status} فلتر المشرفين", f"admin_filters_{task_id}")],
            [Button.inline(f"{duplicate_status} فلتر التكرار", f"duplicate_filter_{task_id}"),
             Button.inline(f"{inline_status} الأزرار الإنلاين", f"inline_button_filter_{task_id}")],
            [Button.inline(f"{forwarded_status} الرسائل المُوجهة", f"forwarded_msg_filter_{task_id}")],
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]
        
        await event.edit(
            f"🔍 الفلاتر المتقدمة - المهمة #{task_id}\n\n"
            f"📊 حالة الفلاتر:\n"
            f"• {day_status} فلتر الأيام\n"
            f"• {hours_status} ساعات العمل\n"
            f"• {lang_status} فلتر اللغات\n"
            f"• {admin_status} فلتر المشرفين\n"
            f"• {duplicate_status} فلتر التكرار\n"
            f"• {inline_status} الأزرار الإنلاين\n"
            f"• {forwarded_status} الرسائل المُوجهة\n\n"
            f"اختر الفلتر الذي تريد إدارته:",
            buttons=buttons
        )

    async def show_advanced_features(self, event, task_id):
        """Show advanced features menu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get settings for status display
        char_settings = self.db.get_character_limit_settings(task_id)
        rate_settings = self.db.get_rate_limit_settings(task_id)
        delay_settings = self.db.get_forwarding_delay_settings(task_id)
        interval_settings = self.db.get_sending_interval_settings(task_id)
        
        char_status = "🟢" if char_settings.get('enabled', False) else "🔴"
        rate_status = "🟢" if rate_settings.get('enabled', False) else "🔴"
        delay_status = "🟢" if delay_settings.get('enabled', False) else "🔴"
        interval_status = "🟢" if interval_settings.get('enabled', False) else "🔴"
        
        buttons = [
            [Button.inline(f"{char_status} حدود الأحرف", f"character_limit_{task_id}"),
             Button.inline(f"{rate_status} حد المعدل", f"rate_limit_{task_id}")],
            [Button.inline(f"{delay_status} تأخير التوجيه", f"forwarding_delay_{task_id}"),
             Button.inline(f"{interval_status} فاصل الإرسال", f"sending_interval_{task_id}")],
            [Button.inline("📊 وضع النشر", f"publishing_mode_{task_id}")],
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]
        
        await event.edit(
            f"⚡ الميزات المتقدمة - المهمة #{task_id}\n\n"
            f"📊 حالة الميزات:\n"
            f"• {char_status} حدود الأحرف\n"
            f"• {rate_status} حد المعدل\n"
            f"• {delay_status} تأخير التوجيه\n"
            f"• {interval_status} فاصل الإرسال\n\n"
            f"اختر الميزة التي تريد إدارتها:",
            buttons=buttons
        )

    async def handle_message(self, event):
        """Handle text messages"""
        # Skip if it's a command
        if event.text.startswith('/'):
            return

        user_id = event.sender_id

        # Check user state from both systems (user_states and database)
        user_state_data = self.user_states.get(user_id, {})
        current_user_state = user_state_data.get('state')
        current_user_data = user_state_data.get('data', {})
        
        # If we have a user state (new system), handle it first
        if current_user_state:
            if current_user_state.startswith('watermark_text_input_'):
                try:
                    task_id = current_user_data.get('task_id')
                    if task_id:
                        await self.handle_watermark_text_input(event, task_id)
                        return
                except Exception as e:
                    logger.error(f"خطأ في معالجة إدخال نص العلامة المائية: {e}")
                    await event.respond("❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                    self.clear_user_state(user_id)
                    return
                    
            elif current_user_state.startswith('watermark_image_input_'):
                try:
                    task_id = current_user_data.get('task_id')
                    if task_id:
                        await self.handle_watermark_image_input(event, task_id)
                        return
                except Exception as e:
                    logger.error(f"خطأ في معالجة إدخال صورة العلامة المائية: {e}")
                    await event.respond("❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                    self.clear_user_state(user_id)
                    return

        # Check if user is in authentication or task creation process (old system)
        state_data = self.db.get_conversation_state(user_id)

        if state_data:
            state, data_str = state_data
            try:
                if isinstance(data_str, dict):
                    data = data_str
                else:
                    data = json.loads(data_str) if data_str else {}
            except:
                data = {}

            state_data = (state, data)

            # Handle authentication states
            if state in ['waiting_phone', 'waiting_code', 'waiting_password']:
                await self.handle_auth_message(event, state_data)
                return

            # Handle task creation states
            elif state in ['waiting_task_name', 'waiting_source_chat', 'waiting_target_chat']:
                await self.handle_task_message(event, state_data)
                return
            elif state in ['adding_source', 'adding_target']:
                try:
                    await self.handle_add_source_target(event, state_data)
                except Exception as e:
                    logger.error(f"خطأ في معالجة إضافة مصدر/هدف للمستخدم {user_id}: {e}")
                    await event.respond(
                        "❌ حدث خطأ أثناء إضافة المصدر/الهدف\n\n"
                        "حاول مرة أخرى أو اضغط /start للعودة للقائمة الرئيسية"
                    )
                    self.db.clear_conversation_state(user_id)
                return
            elif state == 'adding_multiple_words': # Handle adding multiple words state
                await self.handle_adding_multiple_words(event, state_data)
                return
            elif state == 'adding_text_cleaning_keywords': # Handle adding text cleaning keywords
                await self.handle_adding_text_cleaning_keywords(event, state_data)
                return
            elif state.startswith('watermark_text_input_'): # Handle watermark text input
                try:
                    task_id = data.get('task_id')
                    if task_id:
                        await self.handle_watermark_text_input(event, task_id)
                    else:
                        # Extract task_id from state if not in data
                        task_id = int(state.split('_')[-1])
                        await self.handle_watermark_text_input(event, task_id)
                except Exception as e:
                    logger.error(f"خطأ في معالجة إدخال نص العلامة المائية: {e}")
                    await event.respond("❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                    self.clear_user_state(user_id)
                return
            elif state.startswith('watermark_image_input_'): # Handle watermark image input
                try:
                    task_id = data.get('task_id')
                    if task_id:
                        await self.handle_watermark_image_input(event, task_id)
                    else:
                        # Extract task_id from state if not in data
                        task_id = int(state.split('_')[-1])
                        await self.handle_watermark_image_input(event, task_id)
                except Exception as e:
                    logger.error(f"خطأ في معالجة إدخال صورة العلامة المائية: {e}")
                    await event.respond("❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                    self.clear_user_state(user_id)
                return
            elif state == 'waiting_watermark_size': # Handle setting watermark size
                task_id = int(data)
                await self.handle_watermark_setting_input(event, task_id, 'size', event.text)
                return
            elif state == 'waiting_watermark_opacity': # Handle setting watermark opacity
                task_id = int(data)
                await self.handle_watermark_setting_input(event, task_id, 'opacity', event.text)
                return
            elif state == 'waiting_watermark_font_size': # Handle setting watermark font size
                task_id = int(data)
                await self.handle_watermark_setting_input(event, task_id, 'font_size', event.text)
                return
            elif state == 'waiting_watermark_color': # Handle setting watermark color
                task_id = int(data)
                await self.handle_watermark_setting_input(event, task_id, 'color', event.text)
                return
            elif state == 'waiting_text_replacements': # Handle adding text replacements
                task_id = int(data)
                await self.handle_add_replacements(event, task_id, event.text)
                return
            elif state == 'waiting_header_text': # Handle editing header text
                task_id = int(data)
                await self.handle_set_header_text(event, task_id, event.text)
                return
            elif state == 'waiting_footer_text': # Handle editing footer text
                task_id = int(data)
                await self.handle_set_footer_text(event, task_id, event.text)
                return
            elif state == 'waiting_button_data': # Handle adding inline button
                task_id = int(data)
                await self.handle_add_inline_button(event, task_id, event.text)
                return
            elif state == 'editing_char_range': # Handle character range editing
                task_id = int(data)
                await self.handle_edit_character_range(event, task_id, event.text)
                return
            elif state == 'editing_rate_count': # Handle rate count editing
                task_id = int(data)
                await self.handle_edit_rate_count(event, task_id, event.text)
                return
            elif state == 'editing_rate_period': # Handle rate period editing
                task_id = int(data)
                await self.handle_edit_rate_period(event, task_id, event.text)
                return
            elif state == 'editing_forwarding_delay': # Handle forwarding delay editing
                task_id = int(data)
                await self.handle_edit_forwarding_delay(event, task_id, event.text)
                return
            elif state == 'editing_sending_interval': # Handle sending interval editing
                task_id = int(data)
                await self.handle_edit_sending_interval(event, task_id, event.text)
                return
            elif state == 'waiting_auto_delete_time': # Handle setting auto delete time
                task_id = int(data)
                await self.handle_set_auto_delete_time(event, task_id, event.text)
                return
            elif state == 'set_working_hours': # Handle setting working hours
                task_id = data.get('task_id')
                await self.handle_set_working_hours(event, task_id, event.text)
                return
            elif state == 'add_language': # Handle adding language filter
                task_id = data.get('task_id')
                await self.handle_add_language_filter(event, task_id, event.text)
                return
            elif state == 'waiting_hyperlink_settings': # Handle editing hyperlink settings
                task_id = data.get('task_id')
                await self.handle_hyperlink_settings(event, task_id, event.text)
                return

        # Handle user_states for duplicate filter settings
        if hasattr(self, 'user_states') and user_id in self.user_states:
            state_info = self.user_states[user_id]
            state = state_info.get('state')
            task_id = state_info.get('task_id')
            
            if state == 'awaiting_threshold':
                await self.handle_threshold_input(event, task_id, event.text)
                return
            elif state == 'awaiting_time_window':
                await self.handle_time_window_input(event, task_id, event.text)
                return

        # Check if this chat is a target chat for any active forwarding task
        chat_id = event.chat_id

        # Get all active tasks from database
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT target_chat_id FROM tasks
                    WHERE is_active = 1 AND target_chat_id = ?
                ''', (str(chat_id),))
                target_tasks = cursor.fetchall()

            # If this chat is a target chat, then filter based on word filters
            if target_tasks:
                # Get the user_id associated with this task (assuming one user per target for simplicity here)
                # A more robust solution would involve mapping target_chat_id back to user_id if needed
                # For now, we'll assume a general check if any task targets this chat
                # In a real scenario, you might want to check which user's task is active for this target

                # Fetching words filters for all tasks targeting this chat could be complex.
                # For simplicity, we'll check if ANY active task targets this chat.
                # A more advanced implementation would fetch specific user's task filters.
                
                # For now, let's just log and return if it's a target chat, as the core logic
                # for filtering based on words happens within the UserBot itself when forwarding.
                # The Bot's role here is to receive messages and potentially trigger actions,
                # but the message filtering logic is primarily in UserBot.
                logger.info(f"🤖 الرسالة مستلمة في المحادثة الهدف {chat_id}, سيتم معالجتها بواسطة UserBot.")
                return

            # Also ignore forwarded messages in any case
            if hasattr(event.message, 'forward') and event.message.forward:
                logger.info(f"🚫 تجاهل الرسالة المُوجهة في {chat_id}")
                return

        except Exception as e:
            logger.error(f"خطأ في فحص المحادثات الهدف: {e}")

        # Default response only if not a target chat and not forwarded and in private chat
        if event.is_private:
            await event.respond("👋 أهلاً! استخدم /start لعرض القائمة الرئيسية")
        else:
            logger.info(f"🚫 تجاهل الرد التلقائي في محادثة غير خاصة: {event.chat_id}")

    async def show_task_settings(self, event, task_id):
        """Show task settings menu"""
        user_id = event.sender_id
        task = self.db.get_task_with_sources_targets(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        forward_mode = task.get('forward_mode', 'forward')
        forward_mode_text = "📨 نسخ" if forward_mode == 'copy' else "📩 توجيه"

        # Count sources and targets
        sources_count = len(task.get('sources', []))
        targets_count = len(task.get('targets', []))

        # Get message settings for status display
        message_settings = self.db.get_message_settings(task_id)
        header_status = "🟢" if message_settings['header_enabled'] else "🔴"
        footer_status = "🟢" if message_settings['footer_enabled'] else "🔴"
        buttons_status = "🟢" if message_settings['inline_buttons_enabled'] else "🔴"
        
        # Get text formatting settings for status display
        formatting_settings = self.db.get_text_formatting_settings(task_id)
        formatting_status = "🟢" if formatting_settings['text_formatting_enabled'] else "🔴"
        
        # Get translation settings for status display
        translation_settings = self.db.get_translation_settings(task_id)
        translation_status = "🟢" if translation_settings['enabled'] else "🔴"
        
        # Get watermark settings for status display
        watermark_settings = self.db.get_watermark_settings(task_id)
        watermark_status = "🟢" if watermark_settings['enabled'] else "🔴"

        buttons = [
            # الصف الأول - وضع التوجيه
            [Button.inline(f"🔄 وضع التوجيه ({forward_mode_text})", f"toggle_forward_mode_{task_id}")],
            
            # الصف الثاني - إدارة المصادر والأهداف
            [Button.inline(f"📥 المصادر ({sources_count})", f"manage_sources_{task_id}"),
             Button.inline(f"📤 الأهداف ({targets_count})", f"manage_targets_{task_id}")],
            
            # الصف الثالث - إعدادات التوجيه والفلاتر
            [Button.inline("⚙️ إعدادات التوجيه", f"forwarding_settings_{task_id}"),
             Button.inline("🎬 فلاتر الوسائط", f"media_filters_{task_id}")],
            
            # الصف الرابع - فلاتر النصوص
            [Button.inline("📝 فلاتر الكلمات", f"word_filters_{task_id}"),
             Button.inline("🔄 استبدال النصوص", f"text_replacements_{task_id}")],
            
            # الصف الخامس - تنظيف وترجمة
            [Button.inline("🧹 تنظيف النصوص", f"text_cleaning_{task_id}"),
             Button.inline(f"🌍 ترجمة النصوص {translation_status}", f"translation_settings_{task_id}")],
            
            # الصف السادس - تنسيق وأزرار
            [Button.inline(f"🎨 تنسيق النصوص {formatting_status}", f"text_formatting_{task_id}"),
             Button.inline(f"🔘 أزرار إنلاين {buttons_status}", f"inline_buttons_{task_id}")],
            
            # الصف السابع - رأس وذيل الرسالة
            [Button.inline(f"📄 رأس الرسالة {header_status}", f"header_settings_{task_id}"),
             Button.inline(f"📝 ذيل الرسالة {footer_status}", f"footer_settings_{task_id}")],
            
            # الصف الثامن - العلامة المائية
            [Button.inline(f"🏷️ العلامة المائية {watermark_status}", f"watermark_settings_{task_id}")],
            
            # الصف التاسع - الفلاتر والميزات المتقدمة
            [Button.inline("🔍 الفلاتر المتقدمة", f"advanced_filters_{task_id}"),
             Button.inline("⚡ الميزات المتقدمة", f"advanced_features_{task_id}")],
            
            # الصف الأخير - العودة
            [Button.inline("🔙 رجوع لتفاصيل المهمة", f"task_manage_{task_id}")]
        ]

        await event.edit(
            f"⚙️ إعدادات المهمة: {task_name}\n\n"
            f"📋 الإعدادات الحالية:\n"
            f"• وضع التوجيه: {forward_mode_text}\n"
            f"• عدد المصادر: {sources_count}\n"
            f"• عدد الأهداف: {targets_count}\n"
            f"• فلاتر الوسائط: متاحة\n\n"
            f"اختر الإعداد الذي تريد تعديله:",
            buttons=buttons
        )

    async def toggle_forward_mode(self, event, task_id):
        """Toggle forward mode between copy and forward"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        current_mode = task.get('forward_mode', 'forward')
        new_mode = 'copy' if current_mode == 'forward' else 'forward'

        success = self.db.update_task_forward_mode(task_id, user_id, new_mode)

        if success:
            mode_text = "نسخ" if new_mode == 'copy' else "توجيه"
            await event.answer(f"✅ تم تغيير وضع التوجيه إلى {mode_text}")

            # Force refresh UserBot tasks
            try:
                from userbot_service.userbot import userbot_instance
                if user_id in userbot_instance.clients:
                    await userbot_instance.refresh_user_tasks(user_id)
                    logger.info(f"🔄 تم تحديث مهام UserBot بعد تغيير وضع التوجيه للمهمة {task_id}")
            except Exception as e:
                logger.error(f"خطأ في تحديث مهام UserBot: {e}")

            await self.show_task_settings(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير وضع التوجيه")

    async def manage_task_sources(self, event, task_id):
        """Manage task sources"""
        user_id = event.sender_id

        # First migrate task to new structure if needed
        self.db.migrate_task_to_new_structure(task_id)

        task = self.db.get_task_with_sources_targets(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        sources = task.get('sources', [])

        message = f"📥 إدارة مصادر المهمة: {task.get('task_name', 'مهمة بدون اسم')}\n\n"

        if not sources:
            message += "❌ لا توجد مصادر حالياً\n\n"
        else:
            message += f"📋 المصادر الحالية ({len(sources)}):\n\n"
            for i, source in enumerate(sources[:10], 1):  # Show max 10
                chat_id = source.get('chat_id')
                chat_name = source.get('chat_name') or chat_id

                # Create channel link if it's a channel ID (starts with -100)
                if str(chat_id).startswith('-100'):
                    # Convert -100XXXXXXXXX to https://t.me/c/XXXXXXXXX/1
                    clean_id = str(chat_id)[4:]  # Remove -100 prefix
                    channel_link = f"https://t.me/c/{clean_id}/1"
                    message += f"{i}. [{chat_name}]({channel_link})\n\n"
                else:
                    # For usernames or other formats
                    if str(chat_id).startswith('@'):
                        channel_link = f"https://t.me/{chat_id[1:]}"
                        message += f"{i}. [{chat_name}]({channel_link})\n\n"
                    else:
                        message += f"{i}. {chat_name}\n\n"

        buttons = [
            [Button.inline("➕ إضافة مصدر", f"add_source_{task_id}")]
        ]

        # Add remove buttons for each source (max 8 buttons per row due to Telegram limits)
        for source in sources[:8]:  # Limit to avoid too many buttons
            name = source.get('chat_name') or source.get('chat_id')
            if len(name) > 12:
                name = name[:12] + "..."
            buttons.append([
                Button.inline(f"🗑️ حذف {name}", f"remove_source_{source['id']}_{task_id}")
            ])

        buttons.append([Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")])

        await event.edit(message, buttons=buttons, parse_mode='Markdown')

    async def manage_task_targets(self, event, task_id):
        """Manage task targets"""
        user_id = event.sender_id

        # First migrate task to new structure if needed
        self.db.migrate_task_to_new_structure(task_id)

        task = self.db.get_task_with_sources_targets(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        targets = task.get('targets', [])

        message = f"📤 إدارة أهداف المهمة: {task.get('task_name', 'مهمة بدون اسم')}\n\n"

        if not targets:
            message += "❌ لا توجد أهداف حالياً\n\n"
        else:
            message += f"📋 الأهداف الحالية ({len(targets)}):\n\n"
            for i, target in enumerate(targets[:10], 1):  # Show max 10
                chat_id = target.get('chat_id')
                chat_name = target.get('chat_name') or target.get('chat_id')

                # Create channel link if it's a channel ID (starts with -100)
                if str(chat_id).startswith('-100'):
                    # Convert -100XXXXXXXXX to https://t.me/c/XXXXXXXXX/1
                    clean_id = str(chat_id)[4:]  # Remove -100 prefix
                    channel_link = f"https://t.me/c/{clean_id}/1"
                    message += f"{i}. [{chat_name}]({channel_link})\n\n"
                else:
                    # For usernames or other formats
                    if str(chat_id).startswith('@'):
                        channel_link = f"https://t.me/{chat_id[1:]}"
                        message += f"{i}. [{chat_name}]({channel_link})\n\n"
                    else:
                        message += f"{i}. {chat_name}\n\n"

        buttons = [
            [Button.inline("➕ إضافة هدف", f"add_target_{task_id}")]
        ]

        # Add remove buttons for each target (max 8 buttons per row due to Telegram limits)
        for target in targets[:8]:  # Limit to avoid too many buttons
            name = target.get('chat_name') or target.get('chat_id')
            if len(name) > 12:
                name = name[:12] + "..."
            buttons.append([
                Button.inline(f"🗑️ حذف {name}", f"remove_target_{target['id']}_{task_id}")
            ])

        buttons.append([Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")])

        await event.edit(message, buttons=buttons)

    async def start_add_source(self, event, task_id):
        """Start adding source to task"""
        user_id = event.sender_id

        # Set conversation state with proper error handling
        import json
        try:
            data = {'task_id': int(task_id), 'action': 'add_source'}
            data_str = json.dumps(data)
            self.db.set_conversation_state(user_id, 'adding_source', data_str)

            logger.info(f"✅ تم حفظ حالة إضافة مصدر للمستخدم {user_id}: {data_str}")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ حالة إضافة مصدر: {e}")
            await event.answer("❌ حدث خطأ، حاول مرة أخرى")
            return

        buttons = [
            [Button.inline("❌ إلغاء", f"manage_sources_{task_id}")]
        ]

        await event.edit(
            "➕ إضافة مصدر جديد\n\n"
            "أرسل معرف أو رابط المجموعة/القناة المراد إضافتها كمصدر:\n\n"
            "أمثلة:\n"
            "• @channelname\n"
            "• https://t.me/channelname\n"
            "• -1001234567890\n\n"
            "⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات قراءة الرسائل",
            buttons=buttons
        )

    async def start_add_target(self, event, task_id):
        """Start adding target to task"""
        user_id = event.sender_id

        # Set conversation state with proper error handling
        import json
        try:
            data = {'task_id': int(task_id), 'action': 'add_target'}
            data_str = json.dumps(data)
            self.db.set_conversation_state(user_id, 'adding_target', data_str)

            logger.info(f"✅ تم حفظ حالة إضافة هدف للمستخدم {user_id}: {data_str}")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ حالة إضافة هدف: {e}")
            await event.answer("❌ حدث خطأ، حاول مرة أخرى")
            return

        buttons = [
            [Button.inline("❌ إلغاء", f"manage_targets_{task_id}")]
        ]

        await event.edit(
            "➕ إضافة هدف جديد\n\n"
            "أرسل معرف أو رابط المجموعة/القناة المراد إضافتها كهدف:\n\n"
            "أمثلة:\n"
            "• @channelname\n"
            "• https://t.me/channelname\n"
            "• -1001234567890\n\n"
            "⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات إرسال الرسائل",
            buttons=buttons
        )

    async def remove_source(self, event, source_id, task_id):
        """Remove source from task"""
        user_id = event.sender_id

        # First migrate task to new structure if needed
        self.db.migrate_task_to_new_structure(task_id)

        success = self.db.remove_task_source(source_id, task_id)

        if success:
            # Force refresh UserBot tasks
            try:
                from userbot_service.userbot import userbot_instance
                if user_id in userbot_instance.clients:
                    await userbot_instance.refresh_user_tasks(user_id)
                    logger.info(f"🔄 تم تحديث مهام UserBot بعد حذف مصدر من المهمة {task_id}")
            except Exception as e:
                logger.error(f"خطأ في تحديث مهام UserBot: {e}")

            await event.answer("✅ تم حذف المصدر بنجاح")
            await self.manage_task_sources(event, task_id)
        else:
            await event.answer("❌ فشل في حذف المصدر")

    async def remove_target(self, event, target_id, task_id):
        """Remove target from task"""
        user_id = event.sender_id

        # First migrate task to new structure if needed
        self.db.migrate_task_to_new_structure(task_id)

        success = self.db.remove_task_target(target_id, task_id)

        if success:
            # Force refresh UserBot tasks
            try:
                from userbot_service.userbot import userbot_instance
                if user_id in userbot_instance.clients:
                    await userbot_instance.refresh_user_tasks(user_id)
                    logger.info(f"🔄 تم تحديث مهام UserBot بعد حذف هدف من المهمة {task_id}")
            except Exception as e:
                logger.error(f"خطأ في تحديث مهام UserBot: {e}")

            await event.answer("✅ تم حذف الهدف بنجاح")
            await self.manage_task_targets(event, task_id)
        else:
            await event.answer("❌ فشل في حذف الهدف")


    async def show_working_hours_filter(self, event, task_id):
        """Show working hours filter settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        is_enabled = advanced_settings.get('working_hours_enabled', False)
        settings = self.db.get_working_hours(task_id)
        if settings:
            mode = settings.get('mode', 'work_hours')
            start_hour = settings.get('start_hour', 9)
            end_hour = settings.get('end_hour', 17)
        else:
            mode = 'work_hours'
            start_hour = 9
            end_hour = 17
        
        status_text = "🟢 مفعل" if is_enabled else "🔴 معطل"
        mode_text = "حظر خارج الساعات" if mode == 'block' else "السماح في الساعات فقط"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_working_hours_{task_id}")],
            [Button.inline(f"⏰ تحديد ساعات العمل ({start_hour}:00 - {end_hour}:00)", f"set_working_hours_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع ({mode_text})", f"toggle_working_hours_mode_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"⏰ فلتر ساعات العمل - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"🕒 ساعات العمل: {start_hour}:00 - {end_hour}:00\n"
            f"⚙️ الوضع: {mode_text}\n\n"
            f"💡 هذا الفلتر يتحكم في توقيت توجيه الرسائل حسب ساعات العمل",
            buttons=buttons
        )

    async def show_language_filters(self, event, task_id):
        """Show language filter settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        settings = self.db.get_advanced_filters_settings(task_id)
        is_enabled = settings.get('language_filter_enabled', False)
        filter_settings = self.db.get_language_filters(task_id)
        mode = filter_settings.get('mode', 'allow')
        languages = filter_settings.get('languages', [])
        
        status_text = "🟢 مفعل" if is_enabled else "🔴 معطل"
        mode_text = "حظر اللغات المحددة" if mode == 'block' else "السماح للغات المحددة فقط"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_advanced_filter_language_filter_enabled_{task_id}")],
            [Button.inline(f"🌍 إدارة اللغات ({len(languages)})", f"manage_languages_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع ({mode_text})", f"toggle_language_mode_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"🌍 فلتر اللغات - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"🗣️ عدد اللغات: {len(languages)}\n"
            f"⚙️ الوضع: {mode_text}\n\n"
            f"💡 هذا الفلتر يتحكم في الرسائل حسب لغة النص",
            buttons=buttons
        )

    async def show_admin_filters(self, event, task_id):
        """Show admin filter settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        settings = self.db.get_advanced_filters_settings(task_id)
        is_enabled = settings.get('admin_filter_enabled', False)
        admins = self.db.get_admin_filters(task_id)
        
        status_text = "🟢 مفعل" if is_enabled else "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_advanced_filter_admin_filter_enabled_{task_id}")],
            [Button.inline(f"👥 قائمة المشرفين ({len(admins)})", f"admin_list_{task_id}")],
            [Button.inline("🔄 تحديث قائمة المشرفين", f"refresh_admins_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"👥 فلتر المشرفين - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"👤 عدد المشرفين: {len(admins)}\n\n"
            f"💡 هذا الفلتر يتحكم في الرسائل حسب صلاحيات المرسل",
            buttons=buttons
        )

    async def show_duplicate_filter(self, event, task_id):
        """Show duplicate filter settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        settings = self.db.get_duplicate_settings(task_id)
        is_enabled = settings.get('enabled', False)
        threshold = settings.get('similarity_threshold', 80)
        time_window = settings.get('time_window_hours', 24)
        check_text = settings.get('check_text', True)
        check_media = settings.get('check_media', True)
        
        status_text = "🟢 مفعل" if is_enabled else "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_advanced_filter_duplicate_filter_enabled_{task_id}")],
            [Button.inline("⚙️ إعدادات التكرار", f"duplicate_settings_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"🔄 فلتر التكرار - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📏 نسبة التشابه: {threshold}%\n"
            f"⏱️ النافذة الزمنية: {time_window} ساعة\n"
            f"📝 فحص النص: {'✅' if check_text else '❌'}\n"
            f"🎬 فحص الوسائط: {'✅' if check_media else '❌'}\n\n"
            f"💡 هذا الفلتر يمنع توجيه الرسائل المتكررة",
            buttons=buttons
        )

    async def show_inline_button_filter(self, event, task_id):
        """Show inline button filter settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        settings = self.db.get_advanced_filters_settings(task_id)
        is_enabled = settings.get('inline_button_filter_enabled', False)
        button_setting = self.db.get_inline_button_filter_setting(task_id)
        
        status_text = "🟢 مفعل" if is_enabled else "🔴 معطل"
        mode_text = "حظر الرسائل" if button_setting else "حذف الأزرار"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_advanced_filter_inline_button_filter_enabled_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع ({mode_text})", f"toggle_inline_block_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"🔘 فلتر الأزرار الإنلاين - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⚙️ الوضع: {mode_text}\n\n"
            f"💡 هذا الفلتر يتحكم في الرسائل التي تحتوي على أزرار إنلاين",
            buttons=buttons
        )

    async def show_forwarded_message_filter(self, event, task_id):
        """Show forwarded message filter settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        settings = self.db.get_advanced_filters_settings(task_id)
        is_enabled = settings.get('forwarded_message_filter_enabled', False)
        block_setting = self.db.get_forwarded_message_filter_setting(task_id)
        
        status_text = "🟢 مفعل" if is_enabled else "🔴 معطل"
        mode_text = "حظر الرسائل المُوجهة" if block_setting else "إزالة علامة التوجيه"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_advanced_filter_forwarded_message_filter_enabled_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع ({mode_text})", f"toggle_forwarded_block_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"↗️ فلتر الرسائل المُوجهة - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⚙️ الوضع: {mode_text}\n\n"
            f"💡 هذا الفلتر يتحكم في الرسائل المُوجهة من مصادر أخرى",
            buttons=buttons
        )

    async def show_main_menu(self, event):
        """Show main menu"""
        buttons = [
            [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
            [Button.inline("⚙️ الإعدادات", b"settings")],
            [Button.inline("ℹ️ حول البوت", b"about")]
        ]

        try:
            await event.edit(
                "🏠 القائمة الرئيسية\n\nاختر ما تريد فعله:",
                buttons=buttons
            )
        except Exception as e:
            # If edit fails, send new message
            await event.respond(
                "🏠 القائمة الرئيسية\n\nاختر ما تريد فعله:",
                buttons=buttons
            )

    async def show_tasks_menu(self, event):
        """Show tasks management menu"""
        user_id = event.sender_id
        tasks = self.db.get_user_tasks(user_id)

        buttons = [
            [Button.inline("➕ إنشاء مهمة جديدة", b"create_task")],
            [Button.inline("📋 عرض المهام", b"list_tasks")],
            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        ]

        tasks_count = len(tasks)
        active_count = len([t for t in tasks if t['is_active']])

        await event.edit(
            f"📝 إدارة مهام التوجيه\n\n"
            f"📊 الإحصائيات:\n"
            f"• إجمالي المهام: {tasks_count}\n"
            f"• المهام النشطة: {active_count}\n"
            f"• المهام المتوقفة: {tasks_count - active_count}\n\n"
            f"اختر إجراء:",
            buttons=buttons
        )

    async def start_create_task(self, event):
        """Start creating new task"""
        user_id = event.sender_id

        # Check if user is authenticated
        if not self.db.is_user_authenticated(user_id):
            await event.edit("❌ يجب تسجيل الدخول أولاً لإنشاء المهام")
            return

        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_task_name', json.dumps({}))

        buttons = [
            [Button.inline("❌ إلغاء", b"manage_tasks")]
        ]

        await event.edit(
            "➕ إنشاء مهمة توجيه جديدة\n\n"
            "🏷️ **الخطوة 1: تحديد اسم المهمة**\n\n"
            "أدخل اسماً لهذه المهمة (أو اضغط تخطي لاستخدام اسم افتراضي):\n\n"
            "• اسم المهمة: (مثال: مهمة متابعة الأخبار)",
            buttons=buttons
        )


    async def list_tasks(self, event):
        """List user tasks"""
        user_id = event.sender_id

        # Check if user is authenticated
        if not self.db.is_user_authenticated(user_id):
            await event.edit("❌ يجب تسجيل الدخول أولاً لعرض المهام")
            return

        tasks = self.db.get_user_tasks(user_id)

        if not tasks:
            buttons = [
                [Button.inline("➕ إنشاء مهمة جديدة", b"create_task")],
                [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
            ]

            await event.edit(
                "📋 قائمة المهام\n\n"
                "❌ لا توجد مهام حالياً\n\n"
                "أنشئ مهمتك الأولى للبدء!",
                buttons=buttons
            )
            return

        # Build tasks list with full sources and targets info
        message = "📋 قائمة المهام:\n\n"
        buttons = []

        for i, task in enumerate(tasks[:10], 1):  # Show max 10 tasks
            status = "🟢 نشطة" if task['is_active'] else "🔴 متوقفة"
            task_name = task.get('task_name', 'مهمة بدون اسم')

            # Get all sources and targets for this task
            task_with_details = self.db.get_task_with_sources_targets(task['id'], user_id)

            if task_with_details:
                sources = task_with_details.get('sources', [])
                targets = task_with_details.get('targets', [])

                # Build sources text
                if not sources:
                    sources_text = "لا توجد مصادر"
                elif len(sources) == 1:
                    source_name = sources[0].get('chat_name') or sources[0].get('chat_id')
                    sources_text = str(source_name)
                else:
                    sources_text = f"{len(sources)} مصادر"

                # Build targets text
                if not targets:
                    targets_text = "لا توجد أهداف"
                elif len(targets) == 1:
                    target_name = targets[0].get('chat_name') or targets[0].get('chat_id')
                    targets_text = str(target_name)
                else:
                    targets_text = f"{len(targets)} أهداف"
            else:
                # Fallback to old data
                sources_text = task['source_chat_name'] or task['source_chat_id'] or "غير محدد"
                targets_text = task['target_chat_name'] or task['target_chat_id'] or "غير محدد"

            message += f"{i}. {status} - {task_name}\n"
            message += f"   📥 من: {sources_text}\n"
            message += f"   📤 إلى: {targets_text}\n\n"

            # Add task button
            buttons.append([
                Button.inline(f"⚙️ {task_name[:15]}{'...' if len(task_name) > 15 else ''}", f"task_manage_{task['id']}")
            ])

        buttons.append([Button.inline("➕ إنشاء مهمة جديدة", b"create_task")])
        buttons.append([Button.inline("🏠 القائمة الرئيسية", b"back_main")])

        await event.edit(message, buttons=buttons)

    async def show_task_details(self, event, task_id):
        """Show task details"""
        user_id = event.sender_id

        # First migrate task to new structure if needed
        self.db.migrate_task_to_new_structure(task_id)

        # Get task with all sources and targets
        task = self.db.get_task_with_sources_targets(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        status = "🟢 نشطة" if task['is_active'] else "🔴 متوقفة"
        toggle_text = "⏸️ إيقاف" if task['is_active'] else "▶️ تشغيل"
        task_name = task.get('task_name', 'مهمة بدون اسم')

        forward_mode_text = "📨 نسخ" if task.get('forward_mode', 'forward') == 'copy' else "📩 توجيه"

        # Get sources and targets
        sources = task.get('sources', [])
        targets = task.get('targets', [])

        buttons = [
            [Button.inline(toggle_text, f"task_toggle_{task_id}")],
            [Button.inline("⚙️ إعدادات المهمة", f"task_settings_{task_id}")],
            [Button.inline("🗑️ حذف المهمة", f"task_delete_{task_id}")],
            [Button.inline("📋 عرض المهام", b"list_tasks")]
        ]

        # Build sources text
        sources_text = f"📥 المصادر ({len(sources)}):\n"
        if not sources:
            sources_text += "• لا توجد مصادر\n"
        else:
            for i, source in enumerate(sources[:5], 1):  # Show max 5
                chat_id = source.get('chat_id')
                chat_name = source.get('chat_name') or chat_id

                # Create channel link if it's a channel ID (starts with -100)
                if str(chat_id).startswith('-100'):
                    # Convert -100XXXXXXXXX to https://t.me/c/XXXXXXXXX/1
                    clean_id = str(chat_id)[4:]  # Remove -100 prefix
                    channel_link = f"https://t.me/c/{clean_id}/1"
                    sources_text += f"• [{chat_name}]({channel_link})\n"
                else:
                    # For usernames or other formats
                    if str(chat_id).startswith('@'):
                        channel_link = f"https://t.me/{chat_id[1:]}"
                        sources_text += f"• [{chat_name}]({channel_link})\n"
                    else:
                        sources_text += f"• {chat_name}\n"
            if len(sources) > 5:
                sources_text += f"  ... و {len(sources) - 5} مصدر آخر\n"

        # Build targets text
        targets_text = f"\n📤 الأهداف ({len(targets)}):\n"
        if not targets:
            targets_text += "• لا توجد أهداف\n"
        else:
            for i, target in enumerate(targets[:5], 1):  # Show max 5
                chat_id = target.get('chat_id')
                chat_name = target.get('chat_name') or target.get('chat_id')

                # Create channel link if it's a channel ID (starts with -100)
                if str(chat_id).startswith('-100'):
                    # Convert -100XXXXXXXXX to https://t.me/c/XXXXXXXXX/1
                    clean_id = str(chat_id)[4:]  # Remove -100 prefix
                    channel_link = f"https://t.me/c/{clean_id}/1"
                    targets_text += f"• [{chat_name}]({channel_link})\n"
                else:
                    # For usernames or other formats
                    if str(chat_id).startswith('@'):
                        channel_link = f"https://t.me/{chat_id[1:]}"
                        targets_text += f"• [{chat_name}]({channel_link})\n"
                    else:
                        targets_text += f"• {chat_name}\n"
            if len(targets) > 5:
                targets_text += f"  ... و {len(targets) - 5} هدف آخر\n"

        await event.edit(
            f"⚙️ تفاصيل المهمة #{task['id']}\n\n"
            f"🏷️ اسم المهمة: {task_name}\n"
            f"📊 الحالة: {status}\n"
            f"📋 وضع التوجيه: {forward_mode_text}\n\n"
            f"{sources_text}"
            f"{targets_text}\n"
            f"📅 تاريخ الإنشاء: {task['created_at'][:16]}",
            buttons=buttons
        )

    async def toggle_task(self, event, task_id):
        """Toggle task status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_status = not task['is_active']
        self.db.update_task_status(task_id, user_id, new_status)

        # Update userbot tasks - ensure UserBot is running first
        try:
            from userbot_service.userbot import userbot_instance

            # Check if UserBot is running, if not try to start it
            if user_id not in userbot_instance.clients:
                logger.info(f"🔄 UserBot غير متصل للمستخدم {user_id}, محاولة تشغيله...")
                session_data = self.db.get_user_session(user_id)
                if session_data and session_data[2]:  # session_string exists
                    success = await userbot_instance.start_with_session(user_id, session_data[2])
                    if success:
                        logger.info(f"✅ تم تشغيل UserBot بنجاح للمستخدم {user_id}")
                    else:
                        logger.error(f"❌ فشل في تشغيل UserBot للمستخدم {user_id}")
                else:
                    logger.error(f"❌ لا توجد جلسة محفوظة للمستخدم {user_id}")

            # Refresh tasks
            await userbot_instance.refresh_user_tasks(user_id)
            logger.info(f"تم تحديث مهام UserBot للمستخدم {user_id} بعد إنشاء المهمة")

            # Verify task was loaded
            user_tasks = userbot_instance.user_tasks.get(user_id, [])
            active_tasks = [t for t in user_tasks if t.get('is_active', True)]
            logger.info(f"📋 المهام النشطة للمستخدم {user_id}: {len(active_tasks)}")

        except Exception as e:
            logger.error(f"خطأ في تحديث مهام UserBot للمستخدم {user_id}: {e}")

        status_text = "تم تشغيل" if new_status else "تم إيقاف"
        await event.answer(f"✅ {status_text} المهمة بنجاح")

        # Refresh task details
        await self.show_task_details(event, task_id)

    async def delete_task(self, event, task_id):
        """Delete task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        self.db.delete_task(task_id, user_id)

        # Update userbot tasks - ensure UserBot is running first
        try:
            from userbot_service.userbot import userbot_instance

            # Check if UserBot is running, if not try to start it
            if user_id not in userbot_instance.clients:
                logger.info(f"🔄 UserBot غير متصل للمستخدم {user_id}, محاولة تشغيله...")
                session_data = self.db.get_user_session(user_id)
                if session_data and session_data[2]:  # session_string exists
                    success = await userbot_instance.start_with_session(user_id, session_data[2])
                    if success:
                        logger.info(f"✅ تم تشغيل UserBot بنجاح للمستخدم {user_id}")
                    else:
                        logger.error(f"❌ فشل في تشغيل UserBot للمستخدم {user_id}")
                else:
                    logger.error(f"❌ لا توجد جلسة محفوظة للمستخدم {user_id}")

            # Refresh tasks
            await userbot_instance.refresh_user_tasks(user_id)
            logger.info(f"تم تحديث مهام UserBot للمستخدم {user_id} بعد إنشاء المهمة")

            # Verify task was loaded
            user_tasks = userbot_instance.user_tasks.get(user_id, [])
            active_tasks = [t for t in user_tasks if t.get('is_active', True)]
            logger.info(f"📋 المهام النشطة للمستخدم {user_id}: {len(active_tasks)}")

        except Exception as e:
            logger.error(f"خطأ في تحديث مهام UserBot للمستخدم {user_id}: {e}")

        await event.answer("✅ تم حذف المهمة بنجاح")
        await self.list_tasks(event)

    async def handle_conversation_message(self, event):
        """Handle conversation messages for task creation"""
        user_id = event.sender_id

        state_data = self.db.get_conversation_state(user_id)
        if not state_data:
            return

        state, data_str = state_data
        try:
            if isinstance(data_str, dict):
                data = data_str
            else:
                data = json.loads(data_str) if data_str else {}
        except:
            data = {}
        message_text = event.raw_text.strip()

        try:
            if state == 'waiting_source_chat':
                await self.handle_source_chat(event, message_text)
            elif state == 'waiting_target_chat':
                await self.handle_target_chat(event, message_text)
            elif state == 'waiting_phone':
                await self.handle_phone_input(event, message_text)
            elif state == 'waiting_code':
                await self.handle_code_input(event, message_text, data)
            elif state == 'waiting_password':
                await self.handle_password_input(event, message_text, data)
        except Exception as e:
            logger.error(f"خطأ في معالجة رسالة المحادثة: {e}")
            await event.respond("❌ حدث خطأ، حاول مرة أخرى")
            self.db.clear_conversation_state(user_id)

    async def handle_add_source_target(self, event, state_data):
        """Handle adding source or target to task"""
        user_id = event.sender_id
        state, data_str = state_data

        try:
            import json
            if isinstance(data_str, dict):
                data = data_str
            else:
                data = json.loads(data_str) if data_str else {}
        except Exception as e:
            logger.error(f"خطأ في تحليل البيانات: {e}")
            data = {}

        task_id = data.get('task_id')
        action = data.get('action')
        chat_input = event.raw_text.strip()

        # Debug logging
        logger.info(f"🔍 تفاصيل البيانات المستلمة:")
        logger.info(f"   State: {state}")
        logger.info(f"   Data string: {data_str}")
        logger.info(f"   Parsed data: {data}")
        logger.info(f"   Task ID: {task_id}")
        logger.info(f"   Action: {action}")
        logger.info(f"   Chat input: {chat_input}")

        if not task_id or not action:
            await event.respond(
                "❌ خطأ في البيانات، حاول مرة أخرى\n\n"
                f"🔍 تفاصيل المشكلة:\n"
                f"• معرف المهمة: {task_id}\n"
                f"• الإجراء: {action}\n"
                f"• الحالة: {state}"
            )
            self.db.clear_conversation_state(user_id)
            return

        # Debug: log received data
        logger.info(f"🔍 إضافة مصدر/هدف: task_id={task_id}, action={action}, input='{chat_input}'")

        # Parse chat input
        chat_ids, chat_names = self.parse_chat_input(chat_input)

        if not chat_ids:
            await event.respond(
                "❌ تنسيق معرف المجموعة/القناة غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890\n\n"
                "لعدة معرفات، افصل بينها بفاصلة: @channel1, @channel2"
            )
            return

        # Add each chat
        added_count = 0
        for i, chat_id in enumerate(chat_ids):
            chat_name = chat_names[i] if chat_names and i < len(chat_names) else None

            try:
                if action == 'add_source':
                    # Migrate task to new structure if needed
                    self.db.migrate_task_to_new_structure(task_id)
                    source_id = self.db.add_task_source(task_id, chat_id, chat_name)
                    if source_id:
                        added_count += 1
                elif action == 'add_target':
                    # Migrate task to new structure if needed
                    self.db.migrate_task_to_new_structure(task_id)
                    target_id = self.db.add_task_target(task_id, chat_id, chat_name)
                    if target_id:
                        added_count += 1
            except Exception as e:
                logger.error(f"خطأ في إضافة {action}: {e}")

        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        # Show success message and return to appropriate menu
        if added_count > 0:
            item_name = "مصدر" if action == 'add_source' else "هدف"
            plural = "مصادر" if action == 'add_source' and added_count > 1 else "أهداف" if action == 'add_target' and added_count > 1 else item_name

            # Force refresh UserBot tasks
            try:
                from userbot_service.userbot import userbot_instance
                if user_id in userbot_instance.clients:
                    await userbot_instance.refresh_user_tasks(user_id)
                    logger.info(f"🔄 تم تحديث مهام UserBot بعد إضافة {plural} للمهمة {task_id}")
            except Exception as e:
                logger.error(f"خطأ في تحديث مهام UserBot: {e}")

            await event.respond(f"✅ تم إضافة {added_count} {plural} بنجاح!")

            # Return to appropriate management menu
            if action == 'add_source':
                await self.manage_task_sources(event, task_id)
            else:
                await self.manage_task_targets(event, task_id)
        else:
            await event.respond("❌ فشل في إضافة المدخلات")

    async def handle_task_name(self, event, task_name):
        """Handle task name input"""
        user_id = event.sender_id

        # Use default name if user wants to skip
        if task_name.lower() in ['تخطي', 'skip']:
            task_name = 'مهمة توجيه'

        # Get existing task data (task name) from previous step
        state_data = self.db.get_conversation_state(user_id)
        task_name_stored = 'مهمة توجيه'  # default value

        if state_data and state_data[1]:
            try:
                existing_data = json.loads(state_data[1])
                task_name_stored = existing_data.get('task_name', 'مهمة توجيه')
            except:
                pass

        # Store source chat data along with task name
        task_data = {
            'task_name': task_name,
            'source_chat_ids': [],
            'source_chat_names': []
        }
        self.db.set_conversation_state(user_id, 'waiting_source_chat', json.dumps(task_data))

        buttons = [
            [Button.inline("❌ إلغاء", b"manage_tasks")]
        ]

        await event.respond(
            f"✅ اسم المهمة: {task_name}\n\n"
            f"📥 **الخطوة 2: تحديد المصادر**\n\n"
            f"أرسل معرفات أو روابط المجموعات/القنوات المصدر:\n\n"
            f"🔹 **للمصدر الواحد:**\n"
            f"• @channelname\n"
            f"• https://t.me/channelname\n"
            f"• -1001234567890\n\n"
            f"🔹 **لعدة مصادر (مفصولة بفاصلة):**\n"
            f"• @channel1, @channel2, @channel3\n"
            f"• -1001234567890, -1001234567891\n\n"
            f"⚠️ تأكد من أن البوت مضاف لجميع المجموعات/القنوات وله صلاحيات قراءة الرسائل",
            buttons=buttons
        )

    async def handle_source_chat(self, event, chat_input):
        """Handle source chat input using database conversation state"""
        user_id = event.sender_id

        # Parse chat input
        source_chat_ids, source_chat_names = self.parse_chat_input(chat_input)

        if not source_chat_ids:
            await event.respond(
                "❌ تنسيق معرفات المجموعات/القنوات غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890\n\n"
                "لعدة مصادر، افصل بينها بفاصلة: @channel1, @channel2"
            )
            return

        # Get existing task data (task name) from previous step
        state_data = self.db.get_conversation_state(user_id)
        task_name = 'مهمة توجيه'  # default value

        if state_data and state_data[1]:
            try:
                existing_data = json.loads(state_data[1])
                task_name = existing_data.get('task_name', 'مهمة توجيه')
            except:
                pass

        # Store source chat data along with task name
        task_data = {
            'task_name': task_name,
            'source_chat_ids': source_chat_ids,
            'source_chat_names': source_chat_names
        }
        self.db.set_conversation_state(user_id, 'waiting_target_chat', json.dumps(task_data))

        buttons = [
            [Button.inline("❌ إلغاء", b"manage_tasks")]
        ]

        await event.respond(
            f"✅ تم تحديد المصادر: {', '.join([str(name) for name in source_chat_names if name])}\n\n"
            f"📤 **الخطوة 3: تحديد الوجهة**\n\n"
            f"أرسل معرف أو رابط المجموعة/القناة المراد توجيه الرسائل إليها:\n\n"
            f"أمثلة:\n"
            f"• @targetchannel\n"
            f"• https://t.me/targetchannel\n"
            f"• -1001234567890\n\n"
            f"⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات إرسال الرسائل",
            buttons=buttons
        )

    async def handle_target_chat(self, event, chat_input):
        """Handle target chat input using database conversation state"""
        user_id = event.sender_id

        # Parse target chat
        target_chat_ids, target_chat_names = self.parse_chat_input(chat_input)

        if not target_chat_ids:
            await event.respond(
                "❌ تنسيق معرفات المجموعات/القنوات غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890\n\n"
                "لعدة أهداف، افصل بينها بفاصلة: @channel1, @channel2"
            )
            return

        # Get source chat data from database
        state_data = self.db.get_conversation_state(user_id)
        if not state_data:
            await event.respond("❌ حدث خطأ، يرجى البدء من جديد")
            return

        state, data_str = state_data
        if data_str:
            try:
                if isinstance(data_str, dict):
                    source_data = data_str
                else:
                    source_data = json.loads(data_str) if data_str else {}

                source_chat_ids = source_data.get('source_chat_ids', [])
                source_chat_names = source_data.get('source_chat_names', [])
                task_name = source_data.get('task_name', 'مهمة توجيه')

                # Ensure source_chat_names has the same length as source_chat_ids and no None values
                if len(source_chat_names) < len(source_chat_ids):
                    source_chat_names.extend([None] * (len(source_chat_ids) - len(source_chat_names)))

                # Replace None values with chat IDs and ensure all are strings
                for i, name in enumerate(source_chat_names):
                    if name is None or name == '':
                        source_chat_names[i] = str(source_chat_ids[i])
                    else:
                        source_chat_names[i] = str(name)

                # Ensure all source_chat_ids are strings
                source_chat_ids = [str(chat_id) for chat_id in source_chat_ids]
            except:
                await event.respond("❌ حدث خطأ في البيانات، يرجى البدء من جديد")
                return
        else:
            await event.respond("❌ لم يتم تحديد المصدر، يرجى البدء من جديد")
            return

        # Create task in database with multiple sources and targets
        task_id = self.db.create_task_with_multiple_sources_targets(
            user_id,
            task_name,
            source_chat_ids,
            source_chat_names,
            target_chat_ids,
            target_chat_names
        )

        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        # Update userbot tasks - ensure UserBot is running first
        try:
            from userbot_service.userbot import userbot_instance

            # Check if UserBot is running, if not try to start it
            if user_id not in userbot_instance.clients:
                logger.info(f"🔄 UserBot غير متصل للمستخدم {user_id}, محاولة تشغيله...")
                session_data = self.db.get_user_session(user_id)
                if session_data and session_data[2]:  # session_string exists
                    success = await userbot_instance.start_with_session(user_id, session_data[2])
                    if success:
                        logger.info(f"✅ تم تشغيل UserBot بنجاح للمستخدم {user_id}")
                    else:
                        logger.error(f"❌ فشل في تشغيل UserBot للمستخدم {user_id}")
                else:
                    logger.error(f"❌ لا توجد جلسة محفوظة للمستخدم {user_id}")

            # Refresh tasks
            await userbot_instance.refresh_user_tasks(user_id)
            logger.info(f"تم تحديث مهام UserBot للمستخدم {user_id} بعد إنشاء المهمة")

            # Verify task was loaded
            user_tasks = userbot_instance.user_tasks.get(user_id, [])
            active_tasks = [t for t in user_tasks if t.get('is_active', True)]
            logger.info(f"📋 المهام النشطة للمستخدم {user_id}: {len(active_tasks)}")

        except Exception as e:
            logger.error(f"خطأ في تحديث مهام UserBot للمستخدم {user_id}: {e}")

        # Get the name of the last target added
        target_chat_name = target_chat_names[-1] if target_chat_names else target_chat_ids[-1]

        buttons = [
            [Button.inline("📋 عرض المهام", b"list_tasks")],
            [Button.inline("➕ إنشاء مهمة أخرى", b"create_task")],
            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        ]

        await event.respond(
            f"🎉 تم إنشاء المهمة بنجاح!\n\n"
            f"🆔 رقم المهمة: #{task_id}\n"
            f"🏷️ اسم المهمة: {task_name}\n"
            f"📥 المصادر: {', '.join([str(name) for name in (source_chat_names or source_chat_ids)])}\n"
            f"📤 الوجهة: {target_chat_name}\n"
            f"🟢 الحالة: نشطة\n\n"
            f"✅ سيتم توجيه جميع الرسائل الجديدة تلقائياً",
            buttons=buttons
        )

    def parse_chat_input(self, chat_input: str) -> tuple:
        """Parse chat input and return chat_ids and names"""
        chat_input = chat_input.strip()
        chat_ids = []
        chat_names = []

        # Split by comma if multiple inputs
        if ',' in chat_input:
            inputs = [inp.strip() for inp in chat_input.split(',') if inp.strip()]
        else:
            inputs = [chat_input] if chat_input else []

        for chat_input_item in inputs:
            chat_input_item = chat_input_item.strip()
            if not chat_input_item:
                continue

            if chat_input_item.startswith('@'):
                # Username format
                username = chat_input_item[1:] if len(chat_input_item) > 1 else None
                if username:
                    chat_ids.append(chat_input_item)
                    chat_names.append(username)
            elif chat_input_item.startswith('https://t.me/'):
                # URL format
                username = chat_input_item.split('/')[-1]
                if username:
                    chat_ids.append(f"@{username}")
                    chat_names.append(username)
            elif chat_input_item.startswith('-') and len(chat_input_item) > 1 and chat_input_item[1:].isdigit():
                # Chat ID format (negative)
                chat_ids.append(chat_input_item)
                chat_names.append(None)
            else:
                # Try to parse as numeric ID
                try:
                    chat_id = int(chat_input_item)
                    chat_ids.append(str(chat_id))
                    chat_names.append(None)
                except ValueError:
                    # Invalid format, skip this item
                    continue

        # Return None if no valid inputs were found
        if not chat_ids:
            return None, None

        return chat_ids, chat_names

    async def show_watermark_settings(self, event, task_id):
        """Show watermark settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Get watermark settings
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        enabled = watermark_settings.get('enabled', False)
        status = "🟢 مفعل" if enabled else "🔴 معطل"
        toggle_text = "❌ إلغاء تفعيل" if enabled else "✅ تفعيل"
        
        # Get watermark type
        watermark_type = watermark_settings.get('watermark_type', 'text')
        type_display = "📝 نص" if watermark_type == 'text' else "🖼️ صورة"
        
        # Get position
        position = watermark_settings.get('position', 'bottom_right')
        position_map = {
            'top_left': 'أعلى يسار',
            'top': 'أعلى وسط',
            'top_right': 'أعلى يمين', 
            'bottom_left': 'أسفل يسار',
            'bottom': 'أسفل وسط',
            'bottom_right': 'أسفل يمين',
            'center': 'الوسط'
        }
        position_display = position_map.get(position, position)

        buttons = [
            [Button.inline(toggle_text, f"toggle_watermark_{task_id}")],
            [Button.inline("🎨 إعدادات المظهر", f"watermark_appearance_{task_id}")],
            [Button.inline("🎭 نوع العلامة", f"watermark_type_{task_id}")],
            [Button.inline("📱 اختيار الوسائط", f"watermark_media_{task_id}")],
            [Button.inline("🔙 عودة للمهمة", f"task_settings_{task_id}")]
        ]

        # Build media settings display
        media_settings = []
        if watermark_settings.get('apply_to_photos', True):
            media_settings.append("📷 الصور")
        if watermark_settings.get('apply_to_videos', True):
            media_settings.append("🎥 الفيديوهات")
        if watermark_settings.get('apply_to_documents', False):
            media_settings.append("📄 المستندات")
        
        media_display = " • ".join(media_settings) if media_settings else "لا يوجد"

        await event.edit(
            f"🏷️ إعدادات العلامة المائية - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"🎭 **النوع**: {type_display}\n"
            f"📍 **الموقع**: {position_display}\n"
            f"🎯 **الوسائط المطبقة**: {media_display}\n\n"
            f"🔧 **الإعدادات الحالية:**\n"
            f"• الحجم: {watermark_settings.get('size_percentage', 20)}%\n"
            f"• الشفافية: {watermark_settings.get('opacity', 70)}%\n"
            f"• حجم الخط: {watermark_settings.get('font_size', 32)}px\n\n"
            f"🏷️ **الوظيفة**: إضافة علامة مائية نصية أو صورة على الوسائط المرسلة لحماية الحقوق\n\n"
            f"📝 **نص العلامة**: {watermark_settings.get('watermark_text', 'غير محدد')[:30]}{'...' if len(watermark_settings.get('watermark_text', '')) > 30 else ''}\n"
            f"🖼️ **صورة العلامة**: {'محددة' if watermark_settings.get('watermark_image_path') else 'غير محددة'}",
            buttons=buttons
        )

    async def toggle_watermark(self, event, task_id):
        """Toggle watermark on/off"""
        user_id = event.sender_id
        
        # Get current settings
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_enabled = watermark_settings.get('enabled', False)
        
        # Toggle state
        new_enabled = not current_enabled
        self.db.update_watermark_settings(task_id, enabled=new_enabled)
        
        status = "🟢 مفعل" if new_enabled else "🔴 معطل"
        await event.answer(f"✅ تم تعديل حالة العلامة المائية: {status}")
        
        # Refresh the watermark settings display
        await self.show_watermark_settings(event, task_id)

    async def show_watermark_appearance(self, event, task_id):
        """Show watermark appearance settings with resize controls"""
        user_id = event.sender_id
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        size = watermark_settings.get('size_percentage', 20)
        opacity = watermark_settings.get('opacity', 70)
        font_size = watermark_settings.get('font_size', 32)
        
        default_size = watermark_settings.get('default_size', 50)
        offset_x = watermark_settings.get('offset_x', 0)
        offset_y = watermark_settings.get('offset_y', 0)
        
        buttons = [
            [
                Button.inline("🔺", f"watermark_size_up_{task_id}"),
                Button.inline(f"الحجم: {size}%", f"watermark_appearance_info_{task_id}"),
                Button.inline("🔻", f"watermark_size_down_{task_id}")
            ],
            [
                Button.inline("🔺", f"watermark_opacity_up_{task_id}"),
                Button.inline(f"الشفافية: {opacity}%", f"watermark_appearance_info_{task_id}"),
                Button.inline("🔻", f"watermark_opacity_down_{task_id}")
            ],
            [
                Button.inline("🔺", f"watermark_font_up_{task_id}"),
                Button.inline(f"الخط: {font_size}px", f"watermark_appearance_info_{task_id}"),
                Button.inline("🔻", f"watermark_font_down_{task_id}")
            ],
            [
                Button.inline("🔺", f"watermark_default_up_{task_id}"),
                Button.inline(f"افتراضي: {default_size}%", f"watermark_default_info_{task_id}"),
                Button.inline("🔻", f"watermark_default_down_{task_id}")
            ],
            [
                Button.inline("⬅️", f"watermark_offset_left_{task_id}"),
                Button.inline(f"إزاحة أفقية: {offset_x}", f"watermark_offset_info_{task_id}"),
                Button.inline("➡️", f"watermark_offset_right_{task_id}")
            ],
            [
                Button.inline("⬆️", f"watermark_offset_up_{task_id}"),
                Button.inline(f"إزاحة عمودية: {offset_y}", f"watermark_offset_info_{task_id}"),
                Button.inline("⬇️", f"watermark_offset_down_{task_id}")
            ],
            [Button.inline("🎯 تطبيق الحجم الافتراضي", f"watermark_apply_default_{task_id}")],
            [Button.inline("🔄 إعادة تعيين الإزاحة", f"watermark_reset_offset_{task_id}")],
            [Button.inline("📍 تغيير الموقع", f"watermark_position_selector_{task_id}")],
            [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]
        ]
        
        await event.edit(
            f"🎨 إعدادات مظهر العلامة المائية - المهمة #{task_id}\n\n"
            f"📏 **الحجم الحالي**: {size}% (المدى: 5-100%)\n"
            f"🌫️ **الشفافية**: {opacity}% (المدى: 10-100%)\n"
            f"📝 **حجم الخط**: {font_size}px (المدى: 12-72px)\n"
            f"🎯 **الحجم الافتراضي**: {default_size}% (المدى: 5-100%)\n"
            f"➡️ **الإزاحة الأفقية**: {offset_x} (المدى: -200 إلى +200)\n"
            f"⬇️ **الإزاحة العمودية**: {offset_y} (المدى: -200 إلى +200)\n\n"
            f"ℹ️ **الحجم الذكي**: عند 100% تغطي العلامة المائية العرض الكامل\n"
            f"🎛️ **الإزاحة اليدوية**: تحريك العلامة المائية بدقة من موقعها الأساسي\n"
            f"🔧 **التحكم**: استخدم الأزرار أعلاه لتعديل الإعدادات\n"
            f"🔺 زيادة القيمة / ⬅️➡️⬆️⬇️ التحريك\n"
            f"🔻 تقليل القيمة",
            buttons=buttons
        )

    async def adjust_watermark_size(self, event, task_id, increase=True):
        """Adjust watermark size"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_size = watermark_settings.get('size_percentage', 20)
        
        if increase:
            new_size = min(100, current_size + 5)  # Max 100% for full coverage
        else:
            new_size = max(5, current_size - 5)    # Min 5%
        
        self.db.update_watermark_settings(task_id, size_percentage=new_size)
        await event.answer(f"✅ تم تعديل الحجم إلى {new_size}%")
        
        # Refresh display
        await self.show_watermark_appearance(event, task_id)

    async def adjust_watermark_default_size(self, event, task_id, increase=True):
        """Adjust watermark default size"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_default = watermark_settings.get('default_size', 50)
        
        if increase:
            new_default = min(100, current_default + 5)  # Max 100%
        else:
            new_default = max(5, current_default - 5)    # Min 5%
        
        self.db.update_watermark_settings(task_id, default_size=new_default)
        await event.answer(f"✅ تم تعديل الحجم الافتراضي إلى {new_default}%")
        
        # Refresh display
        await self.show_watermark_appearance(event, task_id)

    async def apply_default_watermark_size(self, event, task_id):
        """Apply default watermark size to current size"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        default_size = watermark_settings.get('default_size', 50)
        
        self.db.update_watermark_settings(task_id, size_percentage=default_size)
        await event.answer(f"✅ تم تطبيق الحجم الافتراضي {default_size}%")
        
        # Refresh display
        await self.show_watermark_appearance(event, task_id)

    async def adjust_watermark_offset(self, event, task_id, axis='x', increase=True):
        """Adjust watermark offset position"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        if axis == 'x':
            current_offset = watermark_settings.get('offset_x', 0)
            if increase:
                new_offset = min(200, current_offset + 10)  # Max +200px
            else:
                new_offset = max(-200, current_offset - 10)  # Min -200px
            
            self.db.update_watermark_settings(task_id, offset_x=new_offset)
            direction = "يمين" if increase else "يسار"
            await event.answer(f"✅ تم تحريك العلامة المائية {direction} إلى {new_offset}px")
            
        else:  # axis == 'y'
            current_offset = watermark_settings.get('offset_y', 0)
            if increase:
                new_offset = min(200, current_offset + 10)  # Max +200px
            else:
                new_offset = max(-200, current_offset - 10)  # Min -200px
            
            self.db.update_watermark_settings(task_id, offset_y=new_offset)
            direction = "أسفل" if increase else "أعلى"
            await event.answer(f"✅ تم تحريك العلامة المائية {direction} إلى {new_offset}px")
        
        # Refresh display
        await self.show_watermark_appearance(event, task_id)

    async def reset_watermark_offset(self, event, task_id):
        """Reset watermark offset to center position"""
        self.db.update_watermark_settings(task_id, offset_x=0, offset_y=0)
        await event.answer("✅ تم إعادة تعيين الإزاحة إلى المركز")
        
        # Refresh display
        await self.show_watermark_appearance(event, task_id)

    async def adjust_watermark_opacity(self, event, task_id, increase=True):
        """Adjust watermark opacity"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_opacity = watermark_settings.get('opacity', 70)
        
        if increase:
            new_opacity = min(100, current_opacity + 10)  # Max 100%
        else:
            new_opacity = max(10, current_opacity - 10)   # Min 10%
        
        self.db.update_watermark_settings(task_id, opacity=new_opacity)
        await event.answer(f"✅ تم تعديل الشفافية إلى {new_opacity}%")
        
        # Refresh display
        await self.show_watermark_appearance(event, task_id)

    async def adjust_watermark_font_size(self, event, task_id, increase=True):
        """Adjust watermark font size"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_font = watermark_settings.get('font_size', 32)
        
        if increase:
            new_font = min(72, current_font + 4)  # Max 72px
        else:
            new_font = max(12, current_font - 4)   # Min 12px
        
        self.db.update_watermark_settings(task_id, font_size=new_font)
        await event.answer(f"✅ تم تعديل حجم الخط إلى {new_font}px")
        
        # Refresh display
        await self.show_watermark_appearance(event, task_id)

    async def show_watermark_position_selector(self, event, task_id):
        """Show watermark position selection with individual buttons"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_position = watermark_settings.get('position', 'bottom_right')
        
        position_map = {
            'top_left': 'أعلى يسار',
            'top': 'أعلى وسط',
            'top_right': 'أعلى يمين', 
            'bottom_left': 'أسفل يسار',
            'bottom': 'أسفل وسط',
            'bottom_right': 'أسفل يمين',
            'center': 'الوسط'
        }
        
        buttons = []
        for position, display_name in position_map.items():
            checkmark = " ✅" if position == current_position else ""
            buttons.append([Button.inline(f"{display_name}{checkmark}", f"set_watermark_position_{position}_{task_id}")])
        
        buttons.append([Button.inline("🔙 عودة لإعدادات المظهر", f"watermark_appearance_{task_id}")])
        
        await event.edit(
            f"📍 اختيار موقع العلامة المائية - المهمة #{task_id}\n\n"
            f"الموقع الحالي: {position_map.get(current_position, current_position)}\n\n"
            f"اختر الموقع المطلوب:",
            buttons=buttons
        )

    async def set_watermark_position(self, event, task_id, position):
        """Set watermark position"""
        position_map = {
            'top_left': 'أعلى يسار',
            'top': 'أعلى وسط',
            'top_right': 'أعلى يمين', 
            'bottom_left': 'أسفل يسار',
            'bottom': 'أسفل وسط',
            'bottom_right': 'أسفل يمين',
            'center': 'الوسط'
        }
        
        self.db.update_watermark_settings(task_id, position=position)
        await event.answer(f"✅ تم تغيير الموقع إلى: {position_map.get(position, position)}")
        
        # Refresh position selector display
        await self.show_watermark_position_selector(event, task_id)
    
    async def show_watermark_position_settings(self, event, task_id):
        """Show watermark position settings (alias for position selector)"""
        await self.show_watermark_position_selector(event, task_id)

    async def show_watermark_type(self, event, task_id):
        """Show watermark type selection"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_type = watermark_settings.get('watermark_type', 'text')
        
        buttons = [
            [Button.inline("📝 نص" + (" ✅" if current_type == 'text' else ""), f"set_watermark_type_text_{task_id}")],
            [Button.inline("🖼️ صورة" + (" ✅" if current_type == 'image' else ""), f"set_watermark_type_image_{task_id}")],
            [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]
        ]
        
        await event.edit(
            f"🎭 نوع العلامة المائية - المهمة #{task_id}\n\n"
            f"اختر نوع العلامة المائية:\n\n"
            f"📝 **نص**: إضافة نص مخصص\n"
            f"🖼️ **صورة**: استخدام صورة PNG شفافة\n\n"
            f"النوع الحالي: {'📝 نص' if current_type == 'text' else '🖼️ صورة'}",
            buttons=buttons
        )

    async def show_watermark_media_types(self, event, task_id):
        """Show watermark media type selection"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        photos = watermark_settings.get('apply_to_photos', True)
        videos = watermark_settings.get('apply_to_videos', True)
        documents = watermark_settings.get('apply_to_documents', False)
        
        buttons = [
            [Button.inline(f"📷 الصور {'✅' if photos else '❌'}", f"toggle_watermark_photos_{task_id}")],
            [Button.inline(f"🎥 الفيديوهات {'✅' if videos else '❌'}", f"toggle_watermark_videos_{task_id}")],
            [Button.inline(f"📄 المستندات {'✅' if documents else '❌'}", f"toggle_watermark_documents_{task_id}")],
            [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]
        ]
        
        await event.edit(
            f"📱 أنواع الوسائط للعلامة المائية - المهمة #{task_id}\n\n"
            f"اختر أنواع الوسائط التي تريد تطبيق العلامة المائية عليها:\n\n"
            f"📷 **الصور**: JPG, PNG, WebP\n"
            f"🎥 **الفيديوهات**: MP4, AVI, MOV\n"
            f"📄 **المستندات**: ملفات الصور المرسلة كمستندات\n\n"
            f"✅ = مفعل  |  ❌ = معطل",
            buttons=buttons
        )

    async def set_watermark_type(self, event, task_id, watermark_type):
        """Set watermark type (text or image)"""
        self.db.update_watermark_settings(task_id, watermark_type=watermark_type)
        
        type_display = "📝 نص" if watermark_type == 'text' else "🖼️ صورة"
        await event.answer(f"✅ تم تعديل نوع العلامة المائية إلى: {type_display}")
        
        # Start input process based on type
        if watermark_type == 'text':
            await self.start_watermark_text_input(event, task_id)
        else:
            await self.start_watermark_image_input(event, task_id)

    async def start_watermark_text_input(self, event, task_id):
        """Start watermark text input process"""
        self.set_user_state(event.sender_id, f'watermark_text_input_{task_id}', {'task_id': task_id})
        await event.edit(
            f"📝 إدخال نص العلامة المائية - المهمة #{task_id}\n\n"
            f"أرسل النص الذي تريد استخدامه كعلامة مائية:\n\n"
            f"💡 **ملاحظات**:\n"
            f"• يمكنك استخدام النصوص العربية والإنجليزية\n"
            f"• تجنب النصوص الطويلة جداً\n"
            f"• يمكنك تعديل اللون والحجم من إعدادات المظهر\n\n"
            f"أرسل /cancel للإلغاء",
            buttons=[[Button.inline("❌ إلغاء", f"watermark_type_{task_id}")]]
        )

    async def start_watermark_image_input(self, event, task_id):
        """Start watermark image input process"""
        self.set_user_state(event.sender_id, f'watermark_image_input_{task_id}', {'task_id': task_id})
        await event.edit(
            f"🖼️ رفع صورة العلامة المائية - المهمة #{task_id}\n\n"
            f"أرسل الصورة التي تريد استخدامها كعلامة مائية:\n\n"
            f"📋 **طرق الإرسال المدعومة**:\n"
            f"• 📷 كصورة عادية (Photo)\n"
            f"• 📄 كملف/مستند (Document)\n\n"
            f"🎯 **الصيغ المدعومة**:\n"
            f"• PNG (مُفضل للخلفية الشفافة)\n"
            f"• JPG/JPEG\n"
            f"• BMP, WebP\n\n"
            f"⚙️ **المتطلبات**:\n"
            f"• حجم أقل من 10 ميجابايت\n"
            f"• وضوح جيد للنتيجة المطلوبة\n\n"
            f"أرسل /cancel للإلغاء",
            buttons=[[Button.inline("❌ إلغاء", f"watermark_type_{task_id}")]]
        )

    async def handle_watermark_text_input(self, event, task_id):
        """Handle watermark text input"""
        text = event.message.text.strip()
        
        if not text:
            await event.respond("❌ يرجى إرسال نص صالح للعلامة المائية.")
            return
        
        # Update watermark settings with the text
        self.db.update_watermark_settings(task_id, watermark_text=text)
        
        # Clear user state
        self.clear_user_state(event.sender_id)
        
        await event.respond(
            f"✅ تم حفظ نص العلامة المائية بنجاح!\n\n"
            f"📝 **النص المحفوظ**: {text}\n\n"
            f"يمكنك الآن تعديل إعدادات المظهر من قائمة العلامة المائية.",
            buttons=[[Button.inline("🎨 إعدادات المظهر", f"watermark_appearance_{task_id}")],
                     [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]]
        )

    async def handle_watermark_image_input(self, event, task_id):
        """Handle watermark image input (supports both photos and documents)"""
        media = event.message.media
        document = event.message.document
        photo = event.message.photo
        
        # Check if it's a photo or a document (file)
        if not media and not document and not photo:
            await event.respond("❌ يرجى إرسال صورة أو ملف PNG للعلامة المائية.")
            return
        
        # Validate file type if it's a document
        if document:
            file_name = getattr(document, 'file_name', '') or ''
            mime_type = getattr(document, 'mime_type', '') or ''
            
            # Check if it's an image file
            valid_extensions = ['.png', '.jpg', '.jpeg', '.bmp', '.webp']
            valid_mime_types = ['image/png', 'image/jpeg', 'image/jpg', 'image/bmp', 'image/webp']
            
            is_valid_extension = any(file_name.lower().endswith(ext) for ext in valid_extensions)
            is_valid_mime = mime_type in valid_mime_types
            
            if not is_valid_extension and not is_valid_mime:
                await event.respond(
                    "❌ نوع الملف غير مدعوم!\n\n"
                    "📋 **الصيغ المدعومة**:\n"
                    "• PNG (مُفضل للخلفية الشفافة)\n"
                    "• JPG/JPEG\n"
                    "• BMP\n"
                    "• WebP\n\n"
                    "يرجى رفع ملف بإحدى هذه الصيغ."
                )
                return
                
            # Check file size (limit to 10MB)
            if hasattr(document, 'size') and document.size > 10 * 1024 * 1024:
                await event.respond("❌ حجم الملف كبير جداً! الحد الأقصى 10 ميجابايت.")
                return
        
        try:
            # Create watermark_images directory if not exists
            os.makedirs("watermark_images", exist_ok=True)
            
            # Generate filename
            if document and hasattr(document, 'file_name') and document.file_name:
                # Use original filename if available
                original_name = document.file_name
                file_extension = os.path.splitext(original_name)[1] or '.png'
                safe_filename = f"watermark_{task_id}_{int(time.time())}{file_extension}"
            else:
                # Generate filename for photos
                safe_filename = f"watermark_{task_id}_{int(time.time())}.jpg"
            
            # Download the media
            file_path = await event.message.download_media(
                file=os.path.join("watermark_images", safe_filename)
            )
            
            if not file_path:
                await event.respond("❌ فشل في تحميل الصورة.")
                return
            
            # Verify the downloaded file is actually an image
            try:
                from PIL import Image
                with Image.open(file_path) as img:
                    width, height = img.size
                    format_name = img.format or 'Unknown'
                    logger.info(f"✅ تم تحميل صورة العلامة المائية: {width}x{height}, صيغة: {format_name}")
            except Exception as img_error:
                logger.error(f"❌ الملف المُحمل ليس صورة صالحة: {img_error}")
                # Clean up invalid file
                try:
                    os.remove(file_path)
                except:
                    pass
                await event.respond(
                    "❌ الملف المُرسل ليس صورة صالحة!\n\n"
                    "يرجى إرسال صورة بصيغة PNG، JPG، أو أي صيغة صورة مدعومة."
                )
                return
            
            # Update watermark settings with the image path
            self.db.update_watermark_settings(task_id, watermark_image_path=file_path)
            
            # Clear user state
            self.clear_user_state(event.sender_id)
            
            file_type_display = "📄 ملف PNG" if file_path.lower().endswith('.png') else "📷 صورة"
            
            await event.respond(
                f"✅ تم رفع صورة العلامة المائية بنجاح!\n\n"
                f"📁 **اسم الملف**: {os.path.basename(file_path)}\n"
                f"🎭 **نوع الملف**: {file_type_display}\n"
                f"📏 **الحجم**: {width}x{height} بكسل\n"
                f"📋 **الصيغة**: {format_name}\n\n"
                f"💡 **ملاحظة**: صيغة PNG توفر أفضل جودة مع دعم الشفافية\n\n"
                f"يمكنك الآن تعديل إعدادات المظهر من قائمة العلامة المائية.",
                buttons=[[Button.inline("🎨 إعدادات المظهر", f"watermark_appearance_{task_id}")],
                         [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]]
            )
            
        except Exception as e:
            logger.error(f"خطأ في معالجة صورة العلامة المائية: {e}")
            await event.respond(
                "❌ حدث خطأ في رفع الصورة\n\n"
                "يرجى التأكد من:\n"
                "• الملف هو صورة صالحة\n"
                "• حجم الملف أقل من 10 ميجابايت\n"
                "• الصيغة مدعومة (PNG, JPG, etc.)\n\n"
                "ثم حاول مرة أخرى."
            )
            
            # Clear user state
            self.clear_user_state(event.sender_id)

    async def toggle_watermark_media_type(self, event, task_id, media_type):
        """Toggle watermark application for specific media type"""
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        field_map = {
            'photos': 'apply_to_photos',
            'videos': 'apply_to_videos', 
            'documents': 'apply_to_documents'
        }
        
        field = field_map.get(media_type)
        if not field:
            await event.answer("❌ نوع وسائط غير صحيح")
            return
            
        current_value = watermark_settings.get(field, False)
        new_value = not current_value
        
        # Use dynamic kwargs assignment
        kwargs = {field: new_value}
        self.db.update_watermark_settings(task_id, **kwargs)
        
        media_names = {
            'photos': 'الصور',
            'videos': 'الفيديوهات',
            'documents': 'المستندات'
        }
        
        status = "مفعل" if new_value else "معطل"
        await event.answer(f"✅ {media_names[media_type]}: {status}")
        
        # Refresh display
        await self.show_watermark_media_types(event, task_id)

    async def start_auth(self, event):
        """Start authentication process"""
        user_id = event.sender_id

        # Save conversation state in database
        self.db.set_conversation_state(user_id, 'waiting_phone', json.dumps({}))

        buttons = [
            [Button.inline("❌ إلغاء", b"cancel_auth")]
        ]

        await event.edit(
            "📱 تسجيل الدخول\n\n"
            "أرسل رقم هاتفك مع رمز البلد:\n"
            "مثال: +966501234567\n\n"
            "⚠️ تأكد من صحة الرقم",
            buttons=buttons
        )

    async def start_login(self, event): # New function for login button
        """Start login process"""
        user_id = event.sender_id
        session_data = self.db.get_user_session(user_id)

        if session_data and len(session_data) >= 2 and session_data[2]: # Check for session string
            await event.edit("🔄 أنت مسجل دخولك بالفعل.\n"
                             "هل تريد تسجيل الخروج وإعادة تسجيل الدخول؟",
                             buttons=[
                                 [Button.inline("✅ نعم، إعادة تسجيل الدخول", b"auth_phone")],
                                 [Button.inline("❌ لا، العودة للإعدادات", b"settings")]
                             ])
        else:
            await self.start_auth(event) # If no session, start normal authentication

    async def handle_relogin(self, event):
        """Handle re-login request - clear session and start fresh authentication"""
        user_id = event.sender_id

        # Clear existing session data
        self.db.delete_user_session(user_id)

        # Clear conversation state if any
        self.db.clear_conversation_state(user_id)

        # Start fresh authentication
        await event.edit(
            "🔄 تم تسجيل الخروج من الجلسة السابقة\n\n"
            "📱 سيتم بدء عملية تسجيل دخول جديدة..."
        )

        # Small delay for better UX
        import asyncio
        await asyncio.sleep(1)

        # Start authentication process
        await self.start_auth(event)

    async def handle_auth_message(self, event, state_data):
        """Handle authentication messages"""
        user_id = event.sender_id
        state, data = state_data
        message_text = event.text.strip()

        try:
            if state == 'waiting_phone':
                await self.handle_phone_input(event, message_text)
            elif state == 'waiting_code':
                await self.handle_code_input(event, message_text, data)
            elif state == 'waiting_password':
                await self.handle_password_input(event, message_text, data)
        except Exception as e:
            logger.error(f"خطأ في التسجيل للمستخدم {user_id}: {e}")
            await event.respond(
                "❌ حدث خطأ أثناء التسجيل. حاول مرة أخرى.\n"
                "اضغط /start للبدء من جديد."
            )
            self.db.clear_conversation_state(user_id)

    async def handle_phone_input(self, event, phone: str):
        """Handle phone number input"""
        user_id = event.sender_id

        # Validate phone number format
        if not phone.startswith('+') or len(phone) < 10:
            buttons = [
                [Button.inline("❌ إلغاء", b"cancel_auth")]
            ]

            await event.respond(
                "❌ تنسيق رقم الهاتف غير صحيح\n\n"
                "📞 يجب أن يبدأ الرقم بـ + ويكون بالتنسيق الدولي\n"
                "مثال: +966501234567\n\n"
                "أرسل رقم الهاتف مرة أخرى:",
                buttons=buttons
            )
            return

        # Create temporary Telegram client for authentication
        temp_client = None
        try:
            # Create unique session for this authentication attempt
            session_name = f'auth_{user_id}_{int(datetime.now().timestamp())}'
            temp_client = TelegramClient(session_name, int(API_ID), API_HASH)

            # Connect with timeout
            await asyncio.wait_for(temp_client.connect(), timeout=10)

            if not temp_client.is_connected():
                raise Exception("فشل في الاتصال بخوادم تليجرام")

            # Send code request with timeout
            sent_code = await asyncio.wait_for(
                temp_client.send_code_request(phone),
                timeout=15
            )

            # Store data for next step
            auth_data = {
                'phone': phone,
                'phone_code_hash': sent_code.phone_code_hash,
                'session_name': session_name
            }
            self.db.set_conversation_state(user_id, 'waiting_code', json.dumps(auth_data))

            buttons = [
                [Button.inline("❌ إلغاء", b"cancel_auth")]
            ]

            await event.respond(
                f"✅ تم إرسال رمز التحقق إلى {phone}\n\n"
                f"🔢 أرسل الرمز المكون من 5 أرقام:\n"
                f"• يمكن إضافة حروف لتجنب حظر تليجرام: aa12345\n"
                f"• أو إرسال الأرقام مباشرة: 12345\n\n"
                f"⏰ انتظر بضع ثواني حتى يصل الرمز",
                buttons=buttons
            )

        except asyncio.TimeoutError:
            logger.error("مهلة زمنية في إرسال الرمز")
            await event.respond(
                "❌ مهلة زمنية في الاتصال\n\n"
                "🌐 تأكد من اتصالك بالإنترنت وحاول مرة أخرى"
            )
            self.db.clear_conversation_state(user_id)
        except Exception as e:
            logger.error(f"خطأ في إرسال الرمز: {e}")
            error_message = str(e)

            if "wait of" in error_message and "seconds is required" in error_message:
                # Extract wait time from error message
                try:
                    wait_seconds = int(error_message.split("wait of ")[1].split(" seconds")[0])
                    wait_minutes = wait_seconds // 60
                    wait_hours = wait_minutes // 60

                    if wait_hours > 0:
                        time_str = f"{wait_hours} ساعة و {wait_minutes % 60} دقيقة"
                    elif wait_minutes > 0:
                        time_str = f"{wait_minutes} دقيقة"
                    else:
                        time_str = f"{wait_seconds} ثانية"

                    await event.respond(
                        "⏰ تم طلب رموز كثيرة من تليجرام\n\n"
                        f"🚫 يجب الانتظار: {time_str}\n\n"
                        f"💡 نصائح لتجنب هذه المشكلة:\n"
                        f"• لا تطلب رمز جديد إلا بعد انتهاء الرمز السابق\n"
                        f"• استخدم رقم هاتف صحيح من المرة الأولى\n"
                        f"• انتظر وصول الرمز قبل طلب آخر\n\n"
                        f"حاول مرة أخرى بعد انتهاء فترة الانتظار"
                    )
                except:
                    await event.respond(
                        "⏰ تم طلب رموز كثيرة من تليجرام\n\n"
                        "يجب الانتظار قبل طلب رمز جديد\n"
                        "حاول مرة أخرى بعد فترة"
                    )
            elif "AuthRestartError" in error_message or "Restart the authorization" in error_message:
                await event.respond(
                    "🔄 خطأ في الاتصال مع تليجرام\n\n"
                    "حاول تسجيل الدخول مرة أخرى\n"
                    "اضغط /start للبدء من جديد"
                )
                self.db.clear_conversation_state(user_id)
            else:
                await event.respond(
                    "❌ حدث خطأ في إرسال رمز التحقق\n\n"
                    "🔍 تحقق من:\n"
                    "• رقم الهاتف صحيح ومُفعل\n"
                    "• لديك اتصال إنترنت جيد\n"
                    "• لم تطلب رموز كثيرة مؤخراً\n\n"
                    "حاول مرة أخرى أو اضغط /start"
                )
        finally:
            # Always disconnect the temporary client
            if temp_client and temp_client.is_connected():
                try:
                    await temp_client.disconnect()
                except:
                    pass

    async def handle_code_input(self, event, code: str, data: str):
        """Handle verification code input"""
        user_id = event.sender_id

        # Extract digits from the message (handles formats like aa12345)
        extracted_code = ''.join([char for char in code if char.isdigit()])

        # Validate extracted code
        if len(extracted_code) != 5:
            await event.respond(
                "❌ تنسيق الرمز غير صحيح\n\n"
                "🔢 أرسل الرمز المكون من 5 أرقام\n"
                "يمكن إضافة حروف لتجنب الحظر مثل: aa12345\n"
                "أو إرسال الأرقام مباشرة: 12345"
            )
            return

        # Use the extracted code
        code = extracted_code

        try:
            # data is already a dict from handle_auth_message
            auth_data = data
            phone = auth_data['phone']
            phone_code_hash = auth_data['phone_code_hash']

            # Create client and sign in
            session_name = auth_data.get('session_name', f'auth_{user_id}_{int(datetime.now().timestamp())}')
            temp_client = TelegramClient(session_name, int(API_ID), API_HASH)
            await temp_client.connect()

            try:
                # Try to sign in
                result = await temp_client.sign_in(phone, code, phone_code_hash=phone_code_hash)

                # Get session string properly
                from telethon.sessions import StringSession
                session_string = StringSession.save(temp_client.session)

                # Save session to database
                self.db.save_user_session(user_id, phone, session_string)
                self.db.clear_conversation_state(user_id)

                # Start userbot with this session
                await userbot_instance.start_with_session(user_id, session_string)

                # Send session to Saved Messages
                try:
                    # Create new client with the same session for sending message
                    user_client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
                    await user_client.connect()

                    session_message = (
                        f"🔐 جلسة تسجيل الدخول - بوت التوجيه التلقائي\n\n"
                        f"📱 الرقم: {phone}\n"
                        f"👤 الاسم: {result.first_name}\n"
                        f"🤖 البوت: @7959170262\n"
                        f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                        f"🔑 سلسلة الجلسة:\n"
                        f"`{session_string}`\n\n"
                        f"⚠️ احتفظ بهذه الرسالة آمنة ولا تشاركها مع أحد!"
                    )

                    # Send to Saved Messages (chat with self)
                    await user_client.send_message('me', session_message)
                    await user_client.disconnect()

                    session_saved_text = "✅ تم حفظ الجلسة في رسائلك المحفوظة"
                except Exception as save_error:
                    logger.error(f"خطأ في إرسال الجلسة للرسائل المحفوظة: {save_error}")
                    session_saved_text = "⚠️ تم حفظ الجلسة محلياً فقط"

                buttons = [
                    [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
                    [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
                ]

                await event.respond(
                    f"🎉 تم تسجيل الدخول بنجاح!\n\n"
                    f"👋 مرحباً {result.first_name}!\n"
                    f"✅ تم ربط حسابك بنجاح\n"
                    f"{session_saved_text}\n\n"
                    f"🚀 يمكنك الآن إنشاء مهام التوجيه التلقائي",
                    buttons=buttons
                )

                await temp_client.disconnect()

            except Exception as signin_error:
                if "PASSWORD_NEEDED" in str(signin_error):
                    # 2FA is enabled, ask for password
                    auth_data['session_client'] = temp_client.session.save()
                    self.db.set_conversation_state(user_id, 'waiting_password', json.dumps(auth_data))

                    buttons = [
                        [Button.inline("❌ إلغاء", b"cancel_auth")]
                    ]

                    await event.respond(
                        "🔐 التحقق الثنائي مفعل على حسابك\n\n"
                        "🗝️ أرسل كلمة المرور الخاصة بالتحقق الثنائي:",
                        buttons=buttons
                    )
                else:
                    raise signin_error

        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {e}")
            await event.respond(
                "❌ الرمز غير صحيح أو منتهي الصلاحية\n\n"
                "🔢 أرسل الرمز الصحيح أو اطلب رمز جديد"
            )

    async def handle_password_input(self, event, password: str, data: str):
        """Handle 2FA password input"""
        user_id = event.sender_id

        try:
            # data is already a dict from handle_auth_message
            auth_data = data
            phone = auth_data['phone']
            session_string = auth_data['session_client'] # This is the session string from previous step

            # Create client and sign in with password
            temp_client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
            await temp_client.connect()

            result = await temp_client.sign_in(password=password)

            # Get session string properly
            session_string = StringSession.save(temp_client.session)

            # Save session to database
            self.db.save_user_session(user_id, phone, session_string)
            self.db.clear_conversation_state(user_id)

            # Start userbot with this session
            await userbot_instance.start_with_session(user_id, session_string)

            # Send session to Saved Messages
            try:
                user_client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
                await user_client.connect()

                session_message = (
                    f"🔐 جلسة تسجيل الدخول - بوت التوجيه التلقائي\n\n"
                    f"📱 الرقم: {phone}\n"
                    f"👤 الاسم: {result.first_name}\n"
                    f"🤖 البوت: @7959170262\n"
                    f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"🔑 سلسلة الجلسة:\n"
                    f"`{session_string}`\n\n"
                    f"⚠️ احتفظ بهذه الرسالة آمنة ولا تشاركها مع أحد!"
                )
                await user_client.send_message('me', session_message)
                await user_client.disconnect()
                session_saved_text = "✅ تم حفظ الجلسة في رسائلك المحفوظة"
            except Exception as save_error:
                logger.error(f"خطأ في إرسال الجلسة للرسائل المحفوظة: {save_error}")
                session_saved_text = "⚠️ تم حفظ الجلسة محلياً فقط"

            buttons = [
                [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
                [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
            ]

            await event.respond(
                f"🎉 تم تسجيل الدخول بنجاح!\n\n"
                f"👋 مرحباً {result.first_name}!\n"
                f"✅ تم ربط حسابك بنجاح\n"
                f"{session_saved_text}\n\n"
                f"🚀 يمكنك الآن إنشاء مهام التوجيه التلقائي",
                buttons=buttons
            )
            await temp_client.disconnect()

        except Exception as e:
            logger.error(f"خطأ في التحقق من كلمة المرور: {e}")
            await event.respond(
                "❌ كلمة المرور غير صحيحة أو هناك مشكلة في التحقق الثنائي.\n\n"
                "تأكد من إدخال كلمة المرور الصحيحة وحاول مرة أخرى."
            )

    async def cancel_auth(self, event):
        """Cancel authentication"""
        user_id = event.sender_id
        self.db.clear_conversation_state(user_id)

        buttons = [
            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        ]

        await event.edit(
            "❌ تم إلغاء عملية تسجيل الدخول\n\n"
            "يمكنك المحاولة مرة أخرى في أي وقت",
            buttons=buttons
        )

    # Add missing methods for advanced filters
    async def toggle_working_hours(self, event, task_id):
        """Toggle working hours filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Get current setting
            settings = self.db.get_advanced_filters_settings(task_id)
            current_setting = settings.get('working_hours_enabled', False)
            new_setting = not current_setting
            
            # Update setting
            success = self.db.toggle_advanced_filter(task_id, 'working_hours', new_setting)
            
            if success:
                status = "🟢 مفعل" if new_setting else "🔴 معطل"
                await event.answer(f"✅ تم تحديث فلتر ساعات العمل: {status}")
                
                # Force refresh UserBot tasks
                try:
                    from userbot_service.userbot import userbot_instance
                    if user_id in userbot_instance.clients:
                        await userbot_instance.refresh_user_tasks(user_id)
                        logger.info(f"🔄 تم تحديث مهام UserBot بعد تغيير فلتر ساعات العمل")
                except Exception as e:
                    logger.error(f"خطأ في تحديث مهام UserBot: {e}")
                
                # Return to working hours filter menu
                await self.show_working_hours_filter(event, task_id)
            else:
                await event.answer("❌ فشل في تحديث الإعداد")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل فلتر ساعات العمل: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def start_set_working_hours(self, event, task_id):
        """Start setting working hours"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set conversation state for working hours input
        state_data = {
            'task_id': task_id,
            'step': 'start_hour'
        }
        self.db.set_conversation_state(user_id, 'setting_working_hours', json.dumps(state_data))
        
        await event.edit(
            "🕐 **تحديد ساعات العمل**\n\n"
            "أدخل ساعة البداية (0-23):\n"
            "مثال: 9 للساعة 9 صباحاً\n"
            "أو 13 للساعة 1 ظهراً",
            buttons=[[Button.inline("❌ إلغاء", f"working_hours_filter_{task_id}")]]
        )

    async def toggle_inline_button_filter(self, event, task_id):
        """Toggle inline button filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Get current setting
            settings = self.db.get_advanced_filters_settings(task_id)
            current_setting = settings.get('inline_button_filter_enabled', False)
            new_setting = not current_setting
            
            # Update setting
            success = self.db.toggle_advanced_filter(task_id, 'inline_button', new_setting)
            
            if success:
                status = "🟢 مفعل" if new_setting else "🔴 معطل"
                await event.answer(f"✅ تم تحديث فلتر الأزرار الإنلاين: {status}")
                
                # Force refresh UserBot tasks
                try:
                    from userbot_service.userbot import userbot_instance
                    if user_id in userbot_instance.clients:
                        await userbot_instance.refresh_user_tasks(user_id)
                        logger.info(f"🔄 تم تحديث مهام UserBot بعد تغيير فلتر الأزرار الإنلاين")
                except Exception as e:
                    logger.error(f"خطأ في تحديث مهام UserBot: {e}")
                
                # Return to inline button filter menu
                await self.show_inline_button_filter(event, task_id)
            else:
                await event.answer("❌ فشل في تحديث الإعداد")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل فلتر الأزرار الإنلاين: {e}")
            await event.answer("❌ حدث خطأ في التحديث")
    
    # Add alias for backward compatibility
    async def toggle_inline_button_block(self, event, task_id):
        """Alias for toggle_inline_button_filter"""
        await self.toggle_inline_button_filter(event, task_id)

    async def toggle_working_hours_mode(self, event, task_id):
        """Toggle working hours mode"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Get current settings
            settings = self.db.get_working_hours(task_id)
            current_mode = settings.get('mode', 'work_hours')
            new_mode = 'off_hours' if current_mode == 'work_hours' else 'work_hours'
            
            # Update mode
            success = self.db.update_working_hours(task_id, mode=new_mode)
            
            if success:
                mode_text = "ساعات العمل فقط" if new_mode == 'work_hours' else "خارج ساعات العمل"
                await event.answer(f"✅ تم تحديث وضع ساعات العمل: {mode_text}")
                
                # Force refresh UserBot tasks
                try:
                    from userbot_service.userbot import userbot_instance
                    if user_id in userbot_instance.clients:
                        await userbot_instance.refresh_user_tasks(user_id)
                        logger.info(f"🔄 تم تحديث مهام UserBot بعد تغيير وضع ساعات العمل")
                except Exception as e:
                    logger.error(f"خطأ في تحديث مهام UserBot: {e}")
                
                # Return to working hours filter menu
                await self.show_working_hours_filter(event, task_id)
            else:
                await event.answer("❌ فشل في تحديث الإعداد")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل وضع ساعات العمل: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def handle_task_action(self, event, data):
        """Handle task actions"""
        user_id = event.sender_id

        # Check if user is authenticated
        if not self.db.is_user_authenticated(user_id):
            await event.edit("❌ يجب تسجيل الدخول أولاً")
            return

        if data.startswith("task_manage_"):
            parts = data.split("_")
            if len(parts) >= 3:
                task_id = int(parts[2])
                await self.show_task_details(event, task_id)
        elif data.startswith("task_toggle_"):
            parts = data.split("_")
            if len(parts) >= 3:
                task_id = int(parts[2])
                await self.toggle_task(event, task_id)
        elif data.startswith("task_delete_"):
            parts = data.split("_")
            if len(parts) >= 3:
                task_id = int(parts[2])
                await self.delete_task(event, task_id)

    async def handle_task_message(self, event, state_data):
        """Handle task creation messages"""
        user_id = event.sender_id
        state, data_str = state_data
        message_text = event.text.strip()

        try:
            if state == 'waiting_task_name':
                await self.handle_task_name(event, message_text)
            elif state == 'waiting_source_chat':
                await self.handle_source_chat(event, message_text)
            elif state == 'waiting_target_chat':
                await self.handle_target_chat(event, message_text)
        except Exception as e:
            logger.error(f"خطأ في إنشاء المهمة للمستخدم {user_id}: {e}")
            await event.respond(
                "❌ حدث خطأ أثناء إنشاء المهمة. حاول مرة أخرى."
            )
            self.db.clear_conversation_state(user_id)

    async def show_settings(self, event):
        """Show settings menu"""
        user_id = event.sender_id
        user_settings = self.db.get_user_settings(user_id)
        
        buttons = [
            [Button.inline("🌐 تغيير اللغة", "language_settings")],
            [Button.inline("🕐 تغيير المنطقة الزمنية", "timezone_settings")],
            [Button.inline("🔍 فحص حالة UserBot", "check_userbot")],
            [Button.inline("🔄 إعادة تسجيل الدخول", b"login")],
            [Button.inline("🗑️ حذف جميع المهام", "delete_all_tasks")],
            [Button.inline("🏠 القائمة الرئيسية", "main_menu")]
        ]

        language_name = self.get_language_name(user_settings['language'])
        timezone_name = user_settings['timezone']

        await event.edit(
            f"⚙️ **إعدادات البوت**\n\n"
            f"🌐 اللغة الحالية: {language_name}\n"
            f"🕐 المنطقة الزمنية الحالية: {timezone_name}\n\n"
            "اختر الإعداد الذي تريد تغييره:",
            buttons=buttons
        )

    async def check_userbot_status(self, event):
        """Check UserBot status for user"""
        user_id = event.sender_id

        try:
            from userbot_service.userbot import userbot_instance

            # Check if user has session
            session_data = self.db.get_user_session(user_id)
            if not session_data or len(session_data) < 2: # Corrected check for session_data and its length
                await event.edit(
                    "❌ **حالة UserBot: غير مسجل دخول**\n\n"
                    "🔐 يجب تسجيل الدخول أولاً\n"
                    "📱 اذهب إلى الإعدادات → إعادة تسجيل الدخول",
                    buttons=[[Button.inline("🔄 تسجيل الدخول", "login"), Button.inline("🏠 الرئيسية", "main_menu")]]
                )
                return

            # Check if UserBot is running
            is_userbot_running = user_id in userbot_instance.clients

            if is_userbot_running:
                # Get user tasks
                user_tasks = userbot_instance.user_tasks.get(user_id, [])
                active_tasks = [t for t in user_tasks if t.get('is_active', True)]

                # Get user info
                user_info = await userbot_instance.get_user_info(user_id)
                user_name = "غير معروف"
                if user_info:
                    user_name = f"{user_info.get('first_name', '')} {user_info.get('last_name', '')}".strip()

                status_message = (
                    f"✅ **حالة UserBot: متصل ويعمل**\n\n"
                    f"👤 **معلومات الحساب:**\n"
                    f"• الاسم: {user_name}\n"
                    f"• المعرف: {user_id}\n\n"
                    f"📋 **المهام:**\n"
                    f"• إجمالي المهام: {len(user_tasks)}\n"
                    f"• المهام النشطة: {len(active_tasks)}\n\n"
                )

                if active_tasks:
                    status_message += "🔍 **المهام النشطة:**\n"
                    for i, task in enumerate(active_tasks[:3], 1):
                        task_name = task.get('task_name', f"مهمة {task['id']}")
                        status_message += f"  {i}. {task_name}\n"
                        status_message += f"     📥 {task['source_chat_id']} → 📤 {task['target_chat_id']}\n"

                    if len(active_tasks) > 3:
                        status_message += f"     ... و {len(active_tasks) - 3} مهمة أخرى\n"

                    status_message += "\n✅ **جاهز لتوجيه الرسائل**"
                else:
                    status_message += "⚠️ **لا توجد مهام نشطة**\nأنشئ مهام لبدء التوجيه"

            else:
                status_message = (
                    f"❌ **حالة UserBot: غير متصل**\n\n"
                    f"🔄 **محاولة إعادة التشغيل...**\n"
                    f"يرجى الانتظار..."
                )

                # Try to restart UserBot
                session_data = self.db.get_user_session(user_id)
                if session_data and session_data[2]:  # session_string exists
                    success = await userbot_instance.start_with_session(user_id, session_data[2])
                    if success:
                        status_message = (
                            f"✅ **تم إعادة تشغيل UserBot بنجاح**\n\n"
                            f"🔄 قم بفحص الحالة مرة أخرى للحصول على التفاصيل"
                        )
                    else:
                        status_message = (
                            f"❌ **فشل في إعادة التشغيل**\n\n"
                            f"🔧 **الحلول المقترحة:**\n"
                            f"• إعادة تسجيل الدخول\n"
                            f"• التحقق من اتصال الإنترنت\n"
                            f"• التواصل مع الدعم"
                        )

            buttons = [
                [Button.inline("🔄 فحص مرة أخرى", "check_userbot")],
                [Button.inline("⚙️ الإعدادات", "settings"), Button.inline("🏠 الرئيسية", "main_menu")]
            ]

            try:
                await event.edit(status_message, buttons=buttons)
            except Exception as edit_error:
                # If edit fails, send new message
                await event.respond(status_message, buttons=buttons)

        except Exception as e:
            logger.error(f"خطأ في فحص حالة UserBot للمستخدم {user_id}: {e}")
            try:
                await event.edit(
                    f"❌ **خطأ في فحص حالة UserBot**\n\n"
                    f"🔧 حاول مرة أخرى أو أعد تسجيل الدخول",
                    buttons=[[Button.inline("🔄 إعادة المحاولة", "check_userbot"), Button.inline("🏠 الرئيسية", "main_menu")]]
                )
            except:
                # If edit fails, send new message
                await event.respond(
                    f"❌ **خطأ في فحص حالة UserBot**\n\n"
                    f"🔧 حاول مرة أخرى أو أعد تسجيل الدخول",
                    buttons=[[Button.inline("🔄 إعادة المحاولة", "check_userbot"), Button.inline("🏠 الرئيسية", "main_menu")]]
                )

    async def show_language_settings(self, event):
        """Show language selection menu"""
        buttons = [
            [Button.inline("🇸🇦 العربية", "set_language_ar")],
            [Button.inline("🇺🇸 English", "set_language_en")],
            [Button.inline("🇫🇷 Français", "set_language_fr")],
            [Button.inline("🇩🇪 Deutsch", "set_language_de")],
            [Button.inline("🇪🇸 Español", "set_language_es")],
            [Button.inline("🇷🇺 Русский", "set_language_ru")],
            [Button.inline("🔙 العودة للإعدادات", "settings")]
        ]

        await event.edit(
            "🌐 **اختر اللغة المفضلة:**",
            buttons=buttons
        )

    async def show_timezone_settings(self, event):
        """Show timezone selection menu"""
        buttons = [
            [Button.inline("🇸🇦 الرياض (Asia/Riyadh)", "set_timezone_Asia/Riyadh")],
            [Button.inline("🇰🇼 الكويت (Asia/Kuwait)", "set_timezone_Asia/Kuwait")],
            [Button.inline("🇦🇪 الإمارات (Asia/Dubai)", "set_timezone_Asia/Dubai")],
            [Button.inline("🇶🇦 قطر (Asia/Qatar)", "set_timezone_Asia/Qatar")],
            [Button.inline("🇧🇭 البحرين (Asia/Bahrain)", "set_timezone_Asia/Bahrain")],
            [Button.inline("🇴🇲 عمان (Asia/Muscat)", "set_timezone_Asia/Muscat")],
            [Button.inline("🇯🇴 الأردن (Asia/Amman)", "set_timezone_Asia/Amman")],
            [Button.inline("🇱🇧 لبنان (Asia/Beirut)", "set_timezone_Asia/Beirut")],
            [Button.inline("🇸🇾 سوريا (Asia/Damascus)", "set_timezone_Asia/Damascus")],
            [Button.inline("🇮🇶 العراق (Asia/Baghdad)", "set_timezone_Asia/Baghdad")],
            [Button.inline("🇪🇬 مصر (Africa/Cairo)", "set_timezone_Africa/Cairo")],
            [Button.inline("🇲🇦 المغرب (Africa/Casablanca)", "set_timezone_Africa/Casablanca")],
            [Button.inline("🇩🇿 الجزائر (Africa/Algiers)", "set_timezone_Africa/Algiers")],
            [Button.inline("🇹🇳 تونس (Africa/Tunis)", "set_timezone_Africa/Tunis")],
            [Button.inline("🇱🇾 ليبيا (Africa/Tripoli)", "set_timezone_Africa/Tripoli")],
            [Button.inline("🇺🇸 نيويورك (America/New_York)", "set_timezone_America/New_York")],
            [Button.inline("🇬🇧 لندن (Europe/London)", "set_timezone_Europe/London")],
            [Button.inline("🇩🇪 برلين (Europe/Berlin)", "set_timezone_Europe/Berlin")],
            [Button.inline("🇫🇷 باريس (Europe/Paris)", "set_timezone_Europe/Paris")],
            [Button.inline("🇷🇺 موسكو (Europe/Moscow)", "set_timezone_Europe/Moscow")],
            [Button.inline("🇯🇵 طوكيو (Asia/Tokyo)", "set_timezone_Asia/Tokyo")],
            [Button.inline("🇨🇳 بكين (Asia/Shanghai)", "set_timezone_Asia/Shanghai")],
            [Button.inline("🇮🇳 دلهي (Asia/Kolkata)", "set_timezone_Asia/Kolkata")],
            [Button.inline("🇦🇺 سيدني (Australia/Sydney)", "set_timezone_Australia/Sydney")],
            [Button.inline("🔙 العودة للإعدادات", "settings")]
        ]

        await event.edit(
            "🕐 **اختر المنطقة الزمنية:**",
            buttons=buttons
        )

    async def set_user_language(self, event, language):
        """Set user language preference"""
        user_id = event.sender_id
        success = self.db.update_user_language(user_id, language)
        
        if success:
            language_name = self.get_language_name(language)
            await event.answer(f"✅ تم تغيير اللغة إلى {language_name}")
        else:
            await event.answer("❌ فشل في تغيير اللغة")
        
        await self.show_settings(event)

    async def set_user_timezone(self, event, timezone):
        """Set user timezone preference"""
        user_id = event.sender_id
        success = self.db.update_user_timezone(user_id, timezone)
        
        if success:
            await event.answer(f"✅ تم تغيير المنطقة الزمنية إلى {timezone}")
        else:
            await event.answer("❌ فشل في تغيير المنطقة الزمنية")
        
        await self.show_settings(event)

    def get_language_name(self, language_code):
        """Get language name from code"""
        languages = {
            'ar': '🇸🇦 العربية',
            'en': '🇺🇸 English',
            'fr': '🇫🇷 Français',
            'de': '🇩🇪 Deutsch',
            'es': '🇪🇸 Español',
            'ru': '🇷🇺 Русский'
        }
        return languages.get(language_code, f'{language_code}')


    async def show_media_filters(self, event, task_id):
        """Show media filters management for task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        filters = self.db.get_task_media_filters(task_id)

        # Media types with Arabic names
        media_types = {
            'text': 'نصوص',
            'photo': 'صور',
            'video': 'فيديو',
            'audio': 'صوتيات',
            'document': 'ملفات',
            'voice': 'رسائل صوتية',
            'video_note': 'فيديو دائري',
            'sticker': 'ملصقات',
            'animation': 'صور متحركة',
            'location': 'مواقع',
            'contact': 'جهات اتصال',
            'poll': 'استطلاعات'
        }

        message = f"🎬 فلاتر الوسائط للمهمة: {task_name}\n\n"
        message += "📋 حالة أنواع الوسائط:\n\n"

        buttons = []
        allowed_count = 0
        total_count = len(media_types)

        # Build status message and prepare buttons list
        media_items = list(media_types.items())
        
        for media_type, arabic_name in media_items:
            is_allowed = filters.get(media_type, True)
            status_icon = "✅" if is_allowed else "❌"
            if is_allowed:
                allowed_count += 1
            message += f"{status_icon} {arabic_name}\n"

        message += f"\n📊 الإحصائيات: {allowed_count}/{total_count} مسموح\n\n"
        message += "اختر نوع الوسائط لتغيير حالته:"

        # Create buttons in pairs (2 buttons per row)
        for i in range(0, len(media_items), 2):
            row_buttons = []
            
            for j in range(2):
                if i + j < len(media_items):
                    media_type, arabic_name = media_items[i + j]
                    is_allowed = filters.get(media_type, True)
                    status_emoji = "✅" if is_allowed else "❌"
                    
                    # Use shorter button text for better layout
                    short_names = {
                        'text': 'نص', 'photo': 'صور', 'video': 'فيديو',
                        'audio': 'صوت', 'document': 'ملف', 'voice': 'صوتي',
                        'video_note': 'فيديو دائري', 'sticker': 'ملصق', 'animation': 'متحرك',
                        'location': 'موقع', 'contact': 'جهة اتصال', 'poll': 'استطلاع'
                    }
                    short_name = short_names.get(media_type, arabic_name)
                    
                    row_buttons.append(
                        Button.inline(f"{status_emoji} {short_name}", f"toggle_media_{task_id}_{media_type}")
                    )
            
            if row_buttons:
                buttons.append(row_buttons)

        # Add bulk action buttons
        buttons.extend([
            [Button.inline("✅ السماح للكل", f"allow_all_media_{task_id}"),
             Button.inline("❌ منع الكل", f"block_all_media_{task_id}")],
            [Button.inline("🔄 إعادة تعيين افتراضي", f"reset_media_filters_{task_id}")],
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ])

        await event.edit(message, buttons=buttons)

    async def toggle_media_filter(self, event, task_id, media_type):
        """Toggle media filter for specific type"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        filters = self.db.get_task_media_filters(task_id)
        current_status = filters.get(media_type, True)
        new_status = not current_status

        success = self.db.set_task_media_filter(task_id, media_type, new_status)

        if success:
            status_text = "سُمح" if new_status else "مُنع"
            media_names = {
                'text': 'النصوص', 'photo': 'الصور', 'video': 'الفيديو',
                'audio': 'الصوتيات', 'document': 'الملفات', 'voice': 'الرسائل الصوتية',
                'video_note': 'الفيديو الدائري', 'sticker': 'الملصقات', 'animation': 'الصور المتحركة',
                'location': 'المواقع', 'contact': 'جهات الاتصال', 'poll': 'الاستطلاعات'
            }
            media_name = media_names.get(media_type, media_type)

            await event.answer(f"✅ تم تغيير حالة {media_name} إلى: {status_text}")

            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await self.show_media_filters(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير الفلتر")

    async def set_all_media_filters(self, event, task_id, is_allowed):
        """Set all media filters to allow or block all"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        success = self.db.set_all_media_filters(task_id, is_allowed)

        if success:
            action_text = "السماح لجميع" if is_allowed else "منع جميع"
            await event.answer(f"✅ تم {action_text} أنواع الوسائط")

            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await self.show_media_filters(event, task_id)
        else:
            await event.answer("❌ فشل في تطبيق الفلاتر")

    async def reset_media_filters(self, event, task_id):
        """Reset media filters to default (all allowed)"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        success = self.db.reset_task_media_filters(task_id)

        if success:
            await event.answer("✅ تم إعادة تعيين الفلاتر إلى الوضع الافتراضي (السماح للكل)")

            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await self.show_media_filters(event, task_id)
        else:
            await event.answer("❌ فشل في إعادة تعيين الفلاتر")

    async def _refresh_userbot_tasks(self, user_id):
        """Helper function to refresh UserBot tasks"""
        try:
            from userbot_service.userbot import userbot_instance
            if user_id in userbot_instance.clients:
                await userbot_instance.refresh_user_tasks(user_id)
                logger.info(f"🔄 تم تحديث مهام UserBot بعد تغيير فلاتر الوسائط")
        except Exception as e:
            logger.error(f"خطأ في تحديث مهام UserBot: {e}")

    async def start_edit_hyperlink_settings(self, event, task_id):
        """Start editing hyperlink settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_text_formatting_settings(task_id)
        
        current_text = settings.get('hyperlink_text', 'نص')
        current_url = settings.get('hyperlink_url', 'https://example.com')

        message = f"🔗 تعديل رابط النص\n"
        message += f"📝 المهمة: {task_name}\n\n"
        message += f"الرابط الحالي: {current_url}\n\n"
        message += "📝 أرسل الرابط الجديد:\n\n"
        message += "مثال:\n"
        message += "https://t.me/mychannel\n"
        message += "https://google.com\n"
        message += "https://example.com/page\n\n"
        message += "💡 ملاحظة: سيتم استخدام النص الأصلي للرسالة كنص للرابط\n"
        message += "⚠️ أرسل 'إلغاء' للخروج"

        buttons = [
            [Button.inline("❌ إلغاء", f"text_formatting_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)
        
        # Store the state for this user in database
        state_data = {
            'task_id': task_id,
            'action': 'edit_hyperlink_settings'
        }
        self.db.set_conversation_state(user_id, 'waiting_hyperlink_settings', json.dumps(state_data))

    async def handle_hyperlink_settings(self, event, task_id, message_text):
        """Handle hyperlink settings input from user"""
        user_id = event.sender_id
        
        # Check if user wants to cancel
        if message_text.lower() in ['إلغاء', 'cancel']:
            self.db.clear_conversation_state(user_id)
            await event.respond("❌ تم إلغاء تعديل إعدادات الرابط.")
            await self.show_text_formatting(event, task_id)
            return

        # Parse the input - expecting only the URL
        hyperlink_url = message_text.strip()
        
        # No need for hyperlink text since we use original message text

        # Validate URL
        if not hyperlink_url.startswith(('http://', 'https://')):
            await event.respond(
                "❌ عنوان الرابط يجب أن يبدأ بـ http:// أو https://\n\n"
                "حاول مرة أخرى أو أرسل 'إلغاء'"
            )
            return

        # Update hyperlink settings (no need to update hyperlink_text since we use original text)
        success = self.db.update_text_formatting_settings(
            task_id, 
            hyperlink_url=hyperlink_url
        )

        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        if success:
            await event.respond(
                f"✅ تم تحديث رابط النص بنجاح!\n\n"
                f"• الرابط الجديد: {hyperlink_url}\n"
                f"• سيتم استخدام النص الأصلي كنص الرابط"
            )
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Return to text formatting settings
            await self.show_text_formatting(event, task_id)
        else:
            await event.respond("❌ فشل في تحديث إعدادات الرابط")
            await self.show_text_formatting(event, task_id)

    async def show_word_filters(self, event, task_id):
        """Show word filters management for task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get word filter settings
        whitelist_enabled = self.db.is_word_filter_enabled(task_id, 'whitelist')
        blacklist_enabled = self.db.is_word_filter_enabled(task_id, 'blacklist')
        
        # Get word counts
        whitelist_count = len(self.db.get_filter_words(task_id, 'whitelist'))
        blacklist_count = len(self.db.get_filter_words(task_id, 'blacklist'))

        message = f"📝 فلاتر الكلمات للمهمة: {task_name}\n\n"
        
        # Whitelist section
        whitelist_status = "✅ مفعلة" if whitelist_enabled else "❌ معطلة"
        message += f"⚪ القائمة البيضاء: {whitelist_status}\n"
        message += f"📊 عدد الكلمات: {whitelist_count}\n"
        message += "💡 السماح للرسائل التي تحتوي على كلمات مسموحة فقط\n\n"
        
        # Blacklist section
        blacklist_status = "✅ مفعلة" if blacklist_enabled else "❌ معطلة"
        message += f"⚫ القائمة السوداء: {blacklist_status}\n"
        message += f"📊 عدد الكلمات: {blacklist_count}\n"
        message += "💡 حظر الرسائل التي تحتوي على كلمات محظورة\n\n"
        
        message += "اختر العملية المطلوبة:"

        buttons = [
            [
                Button.inline(f"⚪ القائمة البيضاء ({whitelist_count}) - {'✅ مفعلة' if whitelist_enabled else '❌ معطلة'}", f"manage_whitelist_{task_id}")
            ],
            [
                Button.inline(f"⚫ القائمة السوداء ({blacklist_count}) - {'✅ مفعلة' if blacklist_enabled else '❌ معطلة'}", f"manage_blacklist_{task_id}")
            ],
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)

    async def handle_manage_whitelist(self, event):
        """Handle whitelist management interface"""
        try:
            query = event.data.decode('utf-8')
            parts = query.split('_')
            # For manage_whitelist_6 format
            if len(parts) >= 3:
                task_id = int(parts[2])
            else:
                await event.answer("❌ خطأ في تحليل البيانات", alert=True)
                return
            
            await self.show_whitelist_management(event, task_id)
            
        except Exception as e:
            logger.error(f"خطأ في إدارة القائمة البيضاء: {e}")
            await event.answer("❌ حدث خطأ في النظام", alert=True)

    async def show_whitelist_management(self, event, task_id):
        """Show whitelist management interface"""
        # Get task info
        task = self.db.get_task(task_id, event.sender_id)
        if not task:
            await event.answer("❌ لم يتم العثور على المهمة", alert=True)
            return
        
        # Get whitelist info
        whitelist_enabled = self.db.is_word_filter_enabled(task_id, 'whitelist')
        whitelist_words = self.db.get_filter_words(task_id, 'whitelist')
        whitelist_count = len(whitelist_words)
        
        message = f"⚪ **إدارة القائمة البيضاء**\n"
        message += f"📝 المهمة: {task['task_name']}\n\n"
        message += f"📊 **حالة القائمة:**\n"
        message += f"• الحالة: {'✅ مفعلة' if whitelist_enabled else '❌ معطلة'}\n"
        message += f"• عدد الكلمات: {whitelist_count}\n\n"
        message += "💡 **وصف القائمة البيضاء:**\n"
        message += "• تمرير الرسائل التي تحتوي على هذه الكلمات فقط\n"
        message += "• حظر جميع الرسائل الأخرى\n\n"
        message += "اختر العملية المطلوبة:"

        buttons = [
            [
                Button.inline(f"{'❌ تعطيل' if whitelist_enabled else '✅ تفعيل'} القائمة", f"toggle_word_filter_{task_id}_whitelist")
            ],
            [
                Button.inline(f"📋 عرض الكلمات ({whitelist_count})", f"view_filter_{task_id}_whitelist"),
                Button.inline(f"➕ إضافة كلمات", f"add_multiple_words_{task_id}_whitelist")
            ],
            [
                Button.inline(f"🗑️ إفراغ القائمة", f"clear_filter_{task_id}_whitelist")
            ],
            [Button.inline("🔙 رجوع لفلاتر الكلمات", f"word_filters_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)

    async def handle_manage_blacklist(self, event):
        """Handle blacklist management interface"""
        try:
            query = event.data.decode('utf-8')
            parts = query.split('_')
            # For manage_blacklist_6 format
            if len(parts) >= 3:
                task_id = int(parts[2])
            else:
                await event.answer("❌ خطأ في تحليل البيانات", alert=True)
                return
            
            await self.show_blacklist_management(event, task_id)
            
        except Exception as e:
            logger.error(f"خطأ في إدارة القائمة السوداء: {e}")
            await event.answer("❌ حدث خطأ في النظام", alert=True)

    async def show_blacklist_management(self, event, task_id):
        """Show blacklist management interface"""
        # Get task info
        task = self.db.get_task(task_id, event.sender_id)
        if not task:
            await event.answer("❌ لم يتم العثور على المهمة", alert=True)
            return
        
        # Get blacklist info
        blacklist_enabled = self.db.is_word_filter_enabled(task_id, 'blacklist')
        blacklist_words = self.db.get_filter_words(task_id, 'blacklist')
        blacklist_count = len(blacklist_words)
        
        message = f"⚫ **إدارة القائمة السوداء**\n"
        message += f"📝 المهمة: {task['task_name']}\n\n"
        message += f"📊 **حالة القائمة:**\n"
        message += f"• الحالة: {'✅ مفعلة' if blacklist_enabled else '❌ معطلة'}\n"
        message += f"• عدد الكلمات: {blacklist_count}\n\n"
        message += "💡 **وصف القائمة السوداء:**\n"
        message += "• حظر الرسائل التي تحتوي على هذه الكلمات\n"
        message += "• تمرير جميع الرسائل الأخرى\n\n"
        message += "اختر العملية المطلوبة:"

        buttons = [
            [
                Button.inline(f"{'❌ تعطيل' if blacklist_enabled else '✅ تفعيل'} القائمة", f"toggle_word_filter_{task_id}_blacklist")
            ],
            [
                Button.inline(f"📋 عرض الكلمات ({blacklist_count})", f"view_filter_{task_id}_blacklist"),
                Button.inline(f"➕ إضافة كلمات", f"add_multiple_words_{task_id}_blacklist")
            ],
            [
                Button.inline(f"🗑️ إفراغ القائمة", f"clear_filter_{task_id}_blacklist")
            ],
            [Button.inline("🔙 رجوع لفلاتر الكلمات", f"word_filters_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)

    async def clear_filter_with_confirmation(self, event, task_id, filter_type):
        """Ask for confirmation before clearing a filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        words_count = len(self.db.get_filter_words(task_id, filter_type))
        
        if words_count == 0:
            await event.answer("❌ القائمة فارغة بالفعل")
            return

        message = f"⚠️ **تأكيد حذف {filter_name}**\n\n"
        message += f"📊 عدد الكلمات: {words_count}\n\n"
        message += "❗ هذه العملية لا يمكن التراجع عنها!\n"
        message += "هل أنت متأكد من حذف جميع الكلمات؟"

        buttons = [
            [
                Button.inline("✅ نعم، احذف الكل", f"confirm_clear_{task_id}_{filter_type}"),
                Button.inline("❌ إلغاء", f"manage_{filter_type}_{task_id}")
            ]
        ]

        await event.edit(message, buttons=buttons)

    async def confirm_clear_filter(self, event, task_id, filter_type):
        """Confirm and execute filter clearing"""
        user_id = event.sender_id
        
        # Clear all words from the filter
        success = self.db.clear_filter_words(task_id, filter_type)
        
        if success:
            filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
            await event.answer(f"✅ تم حذف جميع كلمات {filter_name}")
            
            # Refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Return to the specific filter management page
            if filter_type == 'whitelist':
                await self.show_whitelist_management(event, task_id)
            else:
                await self.show_blacklist_management(event, task_id)
        else:
            await event.answer("❌ فشل في حذف الكلمات")

    async def view_filter_words(self, event, task_id, filter_type):
        """View all words in a specific filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task['task_name']
        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        words = self.db.get_filter_words(task_id, filter_type)

        if not words:
            message = f"📋 {filter_name} للمهمة: {task_name}\n\n"
            message += "🚫 القائمة فارغة\n\n"
            message += "💡 يمكنك إضافة كلمات جديدة باستخدام زر 'إضافة كلمات'"
        else:
            message = f"📋 {filter_name} للمهمة: {task_name}\n\n"
            message += f"📊 العدد الإجمالي: {len(words)} كلمة/جملة\n\n"
            
            for i, word in enumerate(words, 1):
                message += f"{i}. {word[2]}\n"  # word[2] is the word content

        # Determine return button based on filter type
        return_button_text = "🔙 رجوع للقائمة البيضاء" if filter_type == 'whitelist' else "🔙 رجوع للقائمة السوداء"
        return_button_callback = f"manage_{filter_type}_{task_id}"
        
        buttons = [
            [
                Button.inline("➕ إضافة كلمات", f"add_multiple_words_{task_id}_{filter_type}"),
                Button.inline("🗑️ إفراغ القائمة", f"clear_filter_{task_id}_{filter_type}") if words else Button.inline("🚫 فارغة", "empty")
            ],
            [Button.inline(return_button_text, return_button_callback)]
        ]

        await event.edit(message, buttons=buttons)

    # ===== Text Cleaning Management =====

    async def show_text_cleaning(self, event, task_id):
        """Show text cleaning settings for task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_text_cleaning_settings(task_id)

        message = f"🧹 تنظيف النصوص للمهمة: {task_name}\n\n"
        message += "📋 إعدادات التنظيف الحالية:\n\n"

        # Define cleaning options with icons
        cleaning_options = [
            ('remove_links', 'تنظيف الروابط', '🔗'),
            ('remove_emojis', 'تنظيف الايموجيات', '😊'),
            ('remove_hashtags', 'حذف الهاشتاقات', '#️⃣'),
            ('remove_phone_numbers', 'تنظيف أرقام الهواتف', '📱'),
            ('remove_empty_lines', 'حذف الأسطر الفارغة', '📝'),
            ('remove_lines_with_keywords', 'حذف الأسطر بكلمات معينة', '🚫'),
            ('remove_caption', 'حذف توضيحات الوسائط', '📸')
        ]

        buttons = []
        enabled_count = 0

        for setting_key, setting_name, icon in cleaning_options:
            is_enabled = settings.get(setting_key, False)
            status_icon = "✅" if is_enabled else "❌"
            if is_enabled:
                enabled_count += 1

            message += f"{status_icon} {icon} {setting_name}\n"

            # Add toggle button
            toggle_text = "❌ تعطيل" if is_enabled else "✅ تفعيل"
            
            # Map setting keys to shorter callback identifiers
            callback_map = {
                'remove_links': 'links',
                'remove_emojis': 'emojis', 
                'remove_hashtags': 'hashtags',
                'remove_phone_numbers': 'phone',
                'remove_empty_lines': 'empty',
                'remove_lines_with_keywords': 'keywords',
                'remove_caption': 'caption'
            }
            
            callback_id = callback_map.get(setting_key, setting_key)
            buttons.append([
                Button.inline(f"{toggle_text} {setting_name}", f"toggle_text_clean_{callback_id}_{task_id}")
            ])

        message += f"\n📊 الإحصائيات: {enabled_count}/{len(cleaning_options)} مُفعل\n\n"

        # Add special button for keyword management
        if settings.get('remove_lines_with_keywords', False):
            keywords_count = len(self.db.get_text_cleaning_keywords(task_id))
            buttons.append([
                Button.inline(f"🔧 إدارة الكلمات المخصصة ({keywords_count})", f"manage_text_clean_keywords_{task_id}")
            ])

        buttons.append([Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")])

        await event.edit(message, buttons=buttons)

    async def toggle_text_cleaning_setting(self, event, task_id, setting_type):
        """Toggle text cleaning setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Map callback identifiers back to database keys
        setting_map = {
            'links': 'remove_links',
            'emojis': 'remove_emojis',
            'hashtags': 'remove_hashtags',
            'phone': 'remove_phone_numbers',
            'empty': 'remove_empty_lines',
            'keywords': 'remove_lines_with_keywords',
            'caption': 'remove_caption'
        }

        db_setting = setting_map.get(setting_type)
        if not db_setting:
            await event.answer("❌ نوع إعداد غير صالح")
            return

        settings = self.db.get_text_cleaning_settings(task_id)
        current_status = settings.get(db_setting, False)
        new_status = not current_status

        success = self.db.update_text_cleaning_setting(task_id, db_setting, new_status)

        if success:
            setting_names = {
                'remove_links': 'تنظيف الروابط',
                'remove_emojis': 'تنظيف الايموجيات',
                'remove_hashtags': 'حذف الهاشتاقات',
                'remove_phone_numbers': 'تنظيف أرقام الهواتف',
                'remove_empty_lines': 'حذف الأسطر الفارغة',
                'remove_lines_with_keywords': 'حذف الأسطر بكلمات معينة',
                'remove_caption': 'حذف توضيحات الوسائط'
            }
            
            setting_name = setting_names.get(db_setting, db_setting)
            status_text = "مُفعل" if new_status else "مُعطل"

            await event.answer(f"✅ تم تغيير {setting_name} إلى: {status_text}")

            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await self.show_text_cleaning(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير الإعداد")

    async def manage_text_cleaning_keywords(self, event, task_id):
        """Manage text cleaning keywords"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        keywords = self.db.get_text_cleaning_keywords(task_id)

        message = f"🚫 إدارة كلمات حذف الأسطر\n"
        message += f"📝 المهمة: {task_name}\n\n"

        if not keywords:
            message += "❌ لا توجد كلمات محددة حالياً\n\n"
            message += "💡 عند إضافة كلمات، سيتم حذف أي سطر يحتوي على إحدى هذه الكلمات من الرسائل قبل التوجيه"
        else:
            message += f"📋 الكلمات المحددة ({len(keywords)}):\n\n"
            for i, keyword in enumerate(keywords[:10], 1):  # Show max 10
                message += f"{i}. {keyword}\n"
            
            if len(keywords) > 10:
                message += f"... و {len(keywords) - 10} كلمة أخرى\n"

        buttons = [
            [Button.inline("➕ إضافة كلمات", f"add_text_clean_keywords_{task_id}")]
        ]

        if keywords:
            buttons.append([Button.inline("🗑️ حذف كلمة", f"remove_text_clean_keyword_{task_id}")])
            buttons.append([Button.inline("🗑️ حذف الكل", f"clear_text_clean_keywords_{task_id}")])

        buttons.append([Button.inline("🔙 رجوع لتنظيف النصوص", f"text_cleaning_{task_id}")])

        await event.edit(message, buttons=buttons)

    async def start_adding_text_cleaning_keywords(self, event, task_id):
        """Start adding text cleaning keywords"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')

        message = f"➕ إضافة كلمات لحذف الأسطر\n"
        message += f"📝 المهمة: {task_name}\n\n"
        message += "📝 أرسل الكلمات أو الجمل التي تريد حذف الأسطر التي تحتويها:\n\n"
        message += "📋 طرق الإدخال:\n"
        message += "• كلمة واحدة في كل سطر\n"
        message += "• عدة كلمات مفصولة بفواصل\n"
        message += "• جمل كاملة\n\n"
        message += "مثال:\n"
        message += "إعلان\n"
        message += "رابط، للمزيد\n"
        message += "انقر هنا للتفاصيل\n\n"
        message += "⚠️ أرسل 'إلغاء' للخروج"

        buttons = [
            [Button.inline("❌ إلغاء", f"manage_text_clean_keywords_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)
        
        # Store the state for this user in database
        state_data = {
            'task_id': task_id,
            'action': 'adding_text_cleaning_keywords'
        }
        self.db.set_conversation_state(user_id, 'adding_text_cleaning_keywords', json.dumps(state_data))

    async def handle_adding_text_cleaning_keywords(self, event, state_data):
        """Handle text cleaning keywords input from user"""
        user_id = event.sender_id
        state, data = state_data
        message_text = event.text.strip()

        try:
            # Handle different data types from conversation state
            if isinstance(data, str):
                if data.strip():  # Check if string is not empty
                    stored_data = json.loads(data)
                else:
                    raise ValueError("Empty data string")
            elif isinstance(data, dict):
                stored_data = data
            else:
                logger.error(f"Invalid data type: {type(data)}, data: {data}")
                raise ValueError(f"Invalid data format: {type(data)}")
            
            task_id = stored_data.get('task_id')
            if not task_id:
                raise KeyError("Missing task_id in stored data")
                
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error(f"خطأ في تحليل بيانات المهمة: {e}, data_type: {type(data)}, data: {data}")
            await event.respond("❌ خطأ في البيانات. حاول مرة أخرى.")
            self.db.clear_conversation_state(user_id)
            return

        # Check if user wants to cancel
        if message_text.lower() in ['إلغاء', 'cancel']:
            self.db.clear_conversation_state(user_id)
            await event.respond("❌ تم إلغاء إضافة الكلمات.")
            await self.manage_text_cleaning_keywords(event, task_id)
            return

        # Parse the input to extract keywords
        keywords_to_add = []
        
        # Split by lines first
        lines = message_text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # Split by comma if there are multiple keywords in a line
                if '،' in line:  # Arabic comma
                    keywords_in_line = [w.strip() for w in line.split('،') if w.strip()]
                elif ',' in line:  # English comma
                    keywords_in_line = [w.strip() for w in line.split(',') if w.strip()]
                else:
                    keywords_in_line = [line]
                
                keywords_to_add.extend(keywords_in_line)

        if not keywords_to_add:
            await event.respond("❌ لم يتم إدخال أي كلمات صالحة. حاول مرة أخرى أو أرسل 'إلغاء' للخروج.")
            return

        # Add keywords to database
        added_count = self.db.add_text_cleaning_keywords(task_id, keywords_to_add)
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        if added_count > 0:
            await event.respond(f"✅ تم إضافة {added_count} كلمة/جملة لحذف الأسطر")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Return to keywords management
            await self.manage_text_cleaning_keywords(event, task_id)
        else:
            await event.respond("⚠️ لم يتم إضافة أي كلمات جديدة (قد تكون موجودة مسبقاً)")
            await self.manage_text_cleaning_keywords(event, task_id)

    async def show_text_formatting(self, event, task_id):
        """Show text formatting settings for task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_text_formatting_settings(task_id)

        message = f"✨ تنسيق النصوص للمهمة: {task_name}\n\n"
        
        is_enabled = settings.get('text_formatting_enabled', False)
        current_format = settings.get('format_type', 'regular')
        
        if is_enabled:
            message += "🟢 تنسيق النصوص: مُفعل\n"
            message += f"📝 التنسيق الحالي: {self._get_format_name(current_format)}\n\n"
        else:
            message += "🔴 تنسيق النصوص: معطل\n\n"

        message += "🎨 أنواع التنسيق المتاحة:\n\n"

        # Format types with examples
        format_types = [
            ('regular', 'عادي', 'نص عادي'),
            ('bold', 'عريض', '**نص عريض**'),
            ('italic', 'مائل', '*نص مائل*'),
            ('underline', 'تحته خط', '__نص تحته خط__'),
            ('strikethrough', 'مخطوط', '~~نص مخطوط~~'),
            ('code', 'كود', '`نص كود`'),
            ('monospace', 'خط ثابت', '```نص بخط ثابت```'),
            ('quote', 'اقتباس', '>نص مقتبس'),
            ('spoiler', 'مخفي', '||نص مخفي||'),
            ('hyperlink', 'رابط', '[نص](رابط)')
        ]

        buttons = []
        
        # Toggle enable/disable button
        toggle_text = "❌ تعطيل" if is_enabled else "✅ تفعيل"
        buttons.append([Button.inline(f"{toggle_text} تنسيق النصوص", f"toggle_text_formatting_{task_id}")])

        if is_enabled:
            # Format type selection buttons
            for fmt_type, fmt_name, example in format_types:
                is_current = fmt_type == current_format
                status_icon = "✅" if is_current else "⚪"
                buttons.append([Button.inline(f"{status_icon} {fmt_name} - {example}", f"set_text_format_{fmt_type}_{task_id}")])

            # Special handling for hyperlink format
            if current_format == 'hyperlink':
                link_text = settings.get('hyperlink_text', 'نص')
                link_url = settings.get('hyperlink_url', 'https://example.com')
                message += f"\n🔗 إعدادات الرابط:\n"
                message += f"• النص: {link_text}\n"
                message += f"• الرابط: {link_url}\n"
                buttons.append([Button.inline("🔧 تعديل إعدادات الرابط", f"edit_hyperlink_{task_id}")])

        buttons.append([Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")])

        await event.edit(message, buttons=buttons)

    def _get_format_name(self, format_type):
        """Get Arabic name for format type"""
        format_names = {
            'regular': 'عادي',
            'bold': 'عريض',
            'italic': 'مائل',
            'underline': 'تحته خط',
            'strikethrough': 'مخطوط',
            'code': 'كود',
            'monospace': 'خط ثابت',
            'quote': 'اقتباس',
            'spoiler': 'مخفي',
            'hyperlink': 'رابط'
        }
        return format_names.get(format_type, format_type)

    async def toggle_text_formatting(self, event, task_id):
        """Toggle text formatting on/off for a task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Toggle the setting
        new_enabled = self.db.toggle_text_formatting(task_id)
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        status_text = "مُفعل" if new_enabled else "معطل"
        await event.answer(f"✅ تم تحديث تنسيق النصوص: {status_text}")
        
        # Show updated settings
        await self.show_text_formatting(event, task_id)

    async def set_text_format_type(self, event, task_id, format_type):
        """Set the text format type for a task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Update format type
        success = self.db.update_text_formatting_settings(task_id, format_type=format_type)
        
        if success:
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            format_name = self._get_format_name(format_type)
            await event.answer(f"✅ تم تحديد نوع التنسيق: {format_name}")
            
            # Show updated settings
            await self.show_text_formatting(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث نوع التنسيق")

    async def start_add_multiple_words(self, event, task_id, filter_type):
        """Start the process to add multiple words to a filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task['task_name']
        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"

        message = f"➕ إضافة كلمات إلى {filter_name}\n"
        message += f"📝 المهمة: {task_name}\n\n"
        message += "📝 أرسل الكلمات أو الجمل التي تريد إضافتها:\n\n"
        message += "📋 طرق الإدخال:\n"
        message += "• كلمة واحدة في كل سطر\n"
        message += "• عدة كلمات مفصولة بفواصل\n"
        message += "• جمل كاملة\n\n"
        message += "مثال:\n"
        message += "كلمة1\n"
        message += "كلمة2، كلمة3\n"
        message += "جملة كاملة للفلترة\n\n"
        message += "⚠️ أرسل 'إلغاء' للخروج"

        buttons = [
            [Button.inline("❌ إلغاء", f"word_filters_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)
        
        # Store the state for this user in database
        state_data = {
            'task_id': task_id,
            'filter_type': filter_type
        }
        self.db.set_conversation_state(user_id, 'adding_multiple_words', json.dumps(state_data))

    async def clear_filter(self, event, task_id, filter_type):
        """Ask for confirmation before clearing a filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task['task_name']
        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        word_count = len(self.db.get_filter_words(task_id, filter_type))

        message = f"⚠️ تأكيد إفراغ {filter_name}\n"
        message += f"📝 المهمة: {task_name}\n\n"
        message += f"🗑️ سيتم حذف {word_count} كلمة/جملة\n\n"
        message += "❗ هذا الإجراء لا يمكن التراجع عنه\n\n"
        message += "هل أنت متأكد من أنك تريد إفراغ القائمة؟"

        buttons = [
            [
                Button.inline("✅ نعم، إفراغ القائمة", f"confirm_clear_{task_id}_{filter_type}"),
                Button.inline("❌ إلغاء", f"word_filters_{task_id}")
            ]
        ]

        await event.edit(message, buttons=buttons)

    async def confirm_clear_filter(self, event, task_id, filter_type):
        """Actually clear the filter after confirmation"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        
        # Clear all words from the filter
        success = self.db.clear_filter_words(task_id, filter_type)

        if success:
            await event.answer(f"✅ تم إفراغ {filter_name} بنجاح")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            await self.show_word_filters(event, task_id)
        else:
            await event.answer("❌ فشل في إفراغ القائمة")

    async def handle_adding_multiple_words(self, event, state_data):
        """Handle multiple words input from user"""
        user_id = event.sender_id
        state, data = state_data
        message_text = event.text.strip()

        task_id = data.get('task_id')
        filter_type = data.get('filter_type')

        if message_text.lower() == 'إلغاء':
            # Cancel adding words
            self.db.clear_conversation_state(user_id)
            await event.respond("❌ تم إلغاء إضافة الكلمات")
            await self.show_word_filters(event, task_id)
            return

        # Parse the input to extract words and phrases
        words_to_add = []
        
        # Split by lines first
        lines = message_text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # Split by comma if there are multiple words in a line
                if '،' in line:  # Arabic comma
                    words_in_line = [w.strip() for w in line.split('،') if w.strip()]
                elif ',' in line:  # English comma
                    words_in_line = [w.strip() for w in line.split(',') if w.strip()]
                else:
                    words_in_line = [line]
                
                words_to_add.extend(words_in_line)

        if not words_to_add:
            await event.respond("❌ لم يتم إدخال أي كلمات صالحة. حاول مرة أخرى أو أرسل 'إلغاء' للخروج.")
            return

        # Add words to filter
        added_count = self.db.add_multiple_filter_words(task_id, filter_type, words_to_add)
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        if added_count > 0:
            filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
            await event.respond(f"✅ تم إضافة {added_count} كلمة/جملة إلى {filter_name}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Send new message instead of trying to edit
            if filter_type == 'whitelist':
                await self.show_whitelist_management_new(event, task_id)
            else:
                await self.show_blacklist_management_new(event, task_id)
        else:
            await event.respond("⚠️ لم يتم إضافة أي كلمات جديدة (قد تكون موجودة مسبقاً)")
            # Send new message instead of trying to edit
            if filter_type == 'whitelist':
                await self.show_whitelist_management_new(event, task_id)
            else:
                await self.show_blacklist_management_new(event, task_id)

    async def toggle_word_filter(self, event, task_id, filter_type):
        """Toggle word filter on/off"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        current_status = self.db.is_word_filter_enabled(task_id, filter_type)
        new_status = not current_status

        success = self.db.set_word_filter_enabled(task_id, filter_type, new_status)

        if success:
            filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
            status_text = "تم تفعيل" if new_status else "تم تعطيل"
            await event.answer(f"✅ {status_text} {filter_name}")

            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            # Return to the specific filter management page with updated button text
            if filter_type == 'whitelist':
                await self.show_whitelist_management(event, task_id)
            else:
                await self.show_blacklist_management(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير حالة الفلتر")

    async def manage_words(self, event, task_id, filter_type):
        """Manage words in a specific filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        words = self.db.get_filter_words(task_id, filter_type)

        message = f"⚙️ إدارة {filter_name}\n\n"
        
        if not words:
            message += "❌ لا توجد كلمات حالياً\n\n"
        else:
            message += f"📋 الكلمات الحالية ({len(words)}):\n\n"
            for i, word_data in enumerate(words[:10], 1):  # Show max 10
                word = word_data['word']
                case_sensitive = "🔤" if word_data['case_sensitive'] else "🔡"
                message += f"{i}. {case_sensitive} {word}\n"
            
            if len(words) > 10:
                message += f"... و {len(words) - 10} كلمة أخرى\n"
            message += "\n"

        message += "اختر العملية:"

        buttons = [
            [Button.inline("➕ إضافة كلمات", f"add_word_{task_id}_{filter_type}")],
        ]

        # Add remove buttons for each word (max 8 to avoid Telegram limits)
        for word_data in words[:8]:
            word = word_data['word']
            display_word = word if len(word) <= 12 else word[:12] + "..."
            buttons.append([
                Button.inline(f"🗑️ حذف {display_word}", f"remove_word_{self.db.get_word_id(task_id, filter_type, word)}_{task_id}_{filter_type}")
            ])

        if words:
            buttons.append([Button.inline("🗑️ إفراغ القائمة", f"clear_filter_{task_id}_{filter_type}")])

        buttons.append([Button.inline("🔙 رجوع لفلاتر الكلمات", f"word_filters_{task_id}")])

        await event.edit(message, buttons=buttons)

    async def start_add_word(self, event, task_id, filter_type):
        """Start adding words to filter"""
        user_id = event.sender_id
        
        # Set conversation state with proper error handling
        import json
        try:
            data = {'task_id': int(task_id), 'filter_type': filter_type, 'action': 'add_words'}
            data_str = json.dumps(data)
            self.db.set_conversation_state(user_id, 'adding_words', data_str)

            logger.info(f"✅ تم حفظ حالة إضافة كلمات للمستخدم {user_id}: {data_str}")
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ حالة إضافة كلمات: {e}")
            await event.answer("❌ حدث خطأ، حاول مرة أخرى")
            return

        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        
        buttons = [
            [Button.inline("❌ إلغاء", f"manage_words_{task_id}_{filter_type}")]
        ]

        await event.edit(
            f"➕ إضافة كلمات إلى {filter_name}\n\n"
            f"📝 أرسل الكلمات أو الجمل المراد إضافتها:\n\n"
            f"🔹 **للكلمة الواحدة:**\n"
            f"• عاجل\n"
            f"• إعلان\n\n"
            f"🔹 **لعدة كلمات (مفصولة بفاصلة):**\n"
            f"• عاجل, خبر مهم, تحديث\n"
            f"• إعلان, دعاية, ترويج\n\n"
            f"💡 يمكن إضافة جمل كاملة أيضاً",
            buttons=buttons
        )

    async def handle_adding_words(self, event, state_data):
        """Handle adding words to filter"""
        user_id = event.sender_id
        state, data_str = state_data

        try:
            import json
            if isinstance(data_str, dict):
                data = data_str
            else:
                data = json.loads(data_str) if data_str else {}
        except Exception as e:
            logger.error(f"خطأ في تحليل البيانات: {e}")
            data = {}

        task_id = data.get('task_id')
        filter_type = data.get('filter_type')
        words_input = event.raw_text.strip()

        if not task_id or not filter_type:
            await event.respond("❌ خطأ في البيانات، حاول مرة أخرى")
            self.db.clear_conversation_state(user_id)
            return

        # Parse words input
        if ',' in words_input:
            words = [word.strip() for word in words_input.split(',') if word.strip()]
        else:
            words = [words_input] if words_input else []

        if not words:
            await event.respond("❌ لم يتم إدخال أي كلمات صحيحة")
            return

        # Add each word
        added_count = 0
        for word in words:
            if len(word) > 200:  # Limit word length
                continue
            
            success = self.db.add_word_to_filter(task_id, filter_type, word)
            if success:
                added_count += 1

        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"

        if added_count > 0:
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await event.respond(f"✅ تم إضافة {added_count} كلمة إلى {filter_name}")
            # Return to the specific filter management page
            if filter_type == 'whitelist':
                await self.handle_manage_whitelist(event)
            else:
                await self.handle_manage_blacklist(event)
        else:
            await event.respond("❌ فشل في إضافة الكلمات أو أنها موجودة بالفعل")

    async def remove_word(self, event, word_id, task_id, filter_type):
        """Remove word from filter"""
        user_id = event.sender_id

        # Get the word first
        word = self.db.get_word_by_id(word_id)
        if not word:
            await event.answer("❌ الكلمة غير موجودة")
            return

        success = self.db.remove_word_from_filter_by_id(word_id)

        if success:
            filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await event.answer(f"✅ تم حذف الكلمة من {filter_name}")
            # Return to the specific filter management page
            if filter_type == 'whitelist':
                await self.handle_manage_whitelist(event)
            else:
                await self.handle_manage_blacklist(event)
        else:
            await event.answer("❌ فشل في حذف الكلمة")

    async def clear_filter(self, event, task_id, filter_type):
        """Clear all words from filter"""
        user_id = event.sender_id

        success = self.db.clear_filter_words(task_id, filter_type)

        if success:
            filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await event.answer(f"✅ تم إفراغ {filter_name}")
            # Return to the specific filter management page
            if filter_type == 'whitelist':
                await self.handle_manage_whitelist(event)
            else:
                await self.handle_manage_blacklist(event)
        else:
            await event.answer("❌ فشل في إفراغ القائمة")

    async def show_about(self, event):
        buttons = [
            [Button.inline("🏠 العودة للرئيسية", b"back_main")]
        ]

        await event.edit(
            "ℹ️ حول البوت\n\n"
            "🤖 بوت التوجيه التلقائي\n"
            "📋 يساعدك في توجيه الرسائل تلقائياً بين المجموعات والقنوات\n\n"
            "🔧 الميزات:\n"
            "• توجيه تلقائي للرسائل\n"
            "• إدارة مهام التوجيه\n"
            "• مراقبة الحالة\n"
            "• واجهة عربية سهلة الاستخدام\n\n"
            "💻 تطوير: نظام بوت تليجرام",
            buttons=buttons
        )

    async def monitor_notifications(self):
        """Monitor for notifications from UserBot to add inline buttons"""
        import os
        import time
        import json
        import glob
        
        logger.info("🔔 بدء مراقبة إشعارات الأزرار الإنلاين...")
        
        while True:
            try:
                # Check for notification files
                notification_files = glob.glob("/tmp/bot_notification_*.json")
                
                for notification_file in notification_files:
                    try:
                        # Read notification
                        with open(notification_file, 'r', encoding='utf-8') as f:
                            notification_data = json.load(f)
                        
                        # Process notification
                        if notification_data.get('action') == 'add_inline_buttons':
                            chat_id = notification_data['chat_id']
                            message_id = notification_data['message_id']
                            task_id = notification_data['task_id']
                            
                            logger.info(f"🔔 معالجة إشعار إضافة أزرار إنلاين: قناة={chat_id}, رسالة={message_id}, مهمة={task_id}")
                            
                            # Add inline buttons to the message
                            await self.add_inline_buttons_to_message(chat_id, message_id, task_id)
                        
                        # Remove processed notification file
                        os.remove(notification_file)
                        
                    except Exception as e:
                        logger.error(f"❌ خطأ في معالجة إشعار {notification_file}: {e}")
                        # Remove problematic file
                        try:
                            os.remove(notification_file)
                        except:
                            pass
                
                # Wait before next check
                await asyncio.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ خطأ في مراقبة الإشعارات: {e}")
                await asyncio.sleep(5)

    async def add_inline_buttons_to_message(self, chat_id: int, message_id: int, task_id: int):
        """Add inline buttons to a specific message"""
        try:
            # Get inline buttons for the task
            buttons_data = self.db.get_inline_buttons(task_id)
            
            if not buttons_data:
                logger.warning(f"❌ لا توجد أزرار إنلاين للمهمة {task_id}")
                return
            
            # Build inline buttons
            inline_buttons = self.build_inline_buttons_from_data(buttons_data)
            
            if not inline_buttons:
                logger.warning(f"❌ فشل في بناء الأزرار الإنلاين للمهمة {task_id}")
                return
            
            # Edit the message to add buttons
            # Convert chat_id to proper entity format for bot
            entity = int(chat_id) if isinstance(chat_id, str) else chat_id
            await self.bot.edit_message(
                entity,
                message_id,
                buttons=inline_buttons
            )
            
            logger.info(f"✅ تم إضافة الأزرار الإنلاين للرسالة {message_id} في القناة {chat_id}")
            
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة الأزرار الإنلاين للرسالة {message_id}: {e}")

    def build_inline_buttons_from_data(self, buttons_data):
        """Build inline buttons from database data"""
        try:
            if not buttons_data:
                return None
            
            # Group buttons by row
            rows = {}
            for button in buttons_data:
                row_num = button['row_position']
                if row_num not in rows:
                    rows[row_num] = []
                rows[row_num].append(button)
            
            # Sort rows and build buttons
            inline_buttons = []
            for row_num in sorted(rows.keys()):
                row_buttons = []
                for button in sorted(rows[row_num], key=lambda x: x['col_position']):
                    # All buttons from database are URL buttons
                    row_buttons.append(Button.url(button['button_text'], button['button_url']))
                
                if row_buttons:
                    inline_buttons.append(row_buttons)
            
            logger.info(f"🔘 تم بناء {len(inline_buttons)} صف من الأزرار الإنلاين")
            return inline_buttons
            
        except Exception as e:
            logger.error(f"❌ خطأ في بناء الأزرار الإنلاين: {e}")
            return None

    async def run(self):
        """Run the bot"""
        logger.info("🚀 بدء تشغيل نظام بوت تليجرام...")

        if await self.start():
            logger.info("✅ البوت يعمل الآن...")
            await self.bot.run_until_disconnected()
        else:
            logger.error("❌ فشل في تشغيل البوت")

    async def show_whitelist_management_new(self, event, task_id):
        """Show whitelist management interface with new message"""
        task = self.db.get_task(task_id, event.sender_id)
        if not task:
            await event.respond("❌ لم يتم العثور على المهمة")
            return
        
        whitelist_enabled = self.db.is_word_filter_enabled(task_id, 'whitelist')
        whitelist_words = self.db.get_filter_words(task_id, 'whitelist')
        whitelist_count = len(whitelist_words)
        
        message = f"⚪ **إدارة القائمة البيضاء**\n"
        message += f"📝 المهمة: {task['task_name']}\n\n"
        message += f"📊 **حالة القائمة:**\n"
        message += f"• الحالة: {'✅ مفعلة' if whitelist_enabled else '❌ معطلة'}\n"
        message += f"• عدد الكلمات: {whitelist_count}\n\n"
        message += "💡 **وصف القائمة البيضاء:**\n"
        message += "• تمرير الرسائل التي تحتوي على هذه الكلمات فقط\n"
        message += "• حظر جميع الرسائل الأخرى\n\n"
        message += "اختر العملية المطلوبة:"

        buttons = [
            [
                Button.inline(f"{'❌ تعطيل' if whitelist_enabled else '✅ تفعيل'} القائمة", f"toggle_word_filter_{task_id}_whitelist")
            ],
            [
                Button.inline(f"📋 عرض الكلمات ({whitelist_count})", f"view_filter_{task_id}_whitelist"),
                Button.inline(f"➕ إضافة كلمات", f"add_multiple_words_{task_id}_whitelist")
            ],
            [
                Button.inline(f"🗑️ إفراغ القائمة", f"clear_filter_{task_id}_whitelist")
            ],
            [Button.inline("🔙 رجوع لفلاتر الكلمات", f"word_filters_{task_id}")]
        ]

        await event.respond(message, buttons=buttons)

    async def show_blacklist_management_new(self, event, task_id):
        """Show blacklist management interface with new message"""
        task = self.db.get_task(task_id, event.sender_id)
        if not task:
            await event.respond("❌ لم يتم العثور على المهمة")
            return
        
        blacklist_enabled = self.db.is_word_filter_enabled(task_id, 'blacklist')
        blacklist_words = self.db.get_filter_words(task_id, 'blacklist')
        blacklist_count = len(blacklist_words)
        
        message = f"⚫ **إدارة القائمة السوداء**\n"
        message += f"📝 المهمة: {task['task_name']}\n\n"
        message += f"📊 **حالة القائمة:**\n"
        message += f"• الحالة: {'✅ مفعلة' if blacklist_enabled else '❌ معطلة'}\n"
        message += f"• عدد الكلمات: {blacklist_count}\n\n"
        message += "💡 **وصف القائمة السوداء:**\n"
        message += "• حظر الرسائل التي تحتوي على هذه الكلمات\n"
        message += "• تمرير جميع الرسائل الأخرى\n\n"
        message += "اختر العملية المطلوبة:"

        buttons = [
            [
                Button.inline(f"{'❌ تعطيل' if blacklist_enabled else '✅ تفعيل'} القائمة", f"toggle_word_filter_{task_id}_blacklist")
            ],
            [
                Button.inline(f"📋 عرض الكلمات ({blacklist_count})", f"view_filter_{task_id}_blacklist"),
                Button.inline(f"➕ إضافة كلمات", f"add_multiple_words_{task_id}_blacklist")
            ],
            [
                Button.inline(f"🗑️ إفراغ القائمة", f"clear_filter_{task_id}_blacklist")
            ],
            [Button.inline("🔙 رجوع لفلاتر الكلمات", f"word_filters_{task_id}")]
        ]

        await event.respond(message, buttons=buttons)

    # Text Replacement Management Functions
    async def show_text_replacements(self, event, task_id):
        """Show text replacement management interface"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Get replacement settings and count
        is_enabled = self.db.is_text_replacement_enabled(task_id)
        replacements = self.db.get_text_replacements(task_id)
        
        status = "🟢 مفعل" if is_enabled else "🔴 معطل"
        toggle_text = "⏸️ إلغاء التفعيل" if is_enabled else "▶️ تفعيل"

        buttons = [
            [Button.inline(toggle_text, f"toggle_replacement_{task_id}")],
            [Button.inline(f"➕ إضافة استبدالات", f"add_replacement_{task_id}")],
            [Button.inline(f"👀 عرض الاستبدالات ({len(replacements)})", f"view_replacements_{task_id}")],
            [Button.inline("🗑️ إفراغ الاستبدالات", f"clear_replacements_{task_id}")],
            [Button.inline("🔙 عودة للمهمة", f"task_manage_{task_id}")]
        ]

        await event.edit(
            f"🔄 استبدال النصوص - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"📝 **عدد الاستبدالات**: {len(replacements)}\n\n"
            f"🔄 **الوظيفة**: استبدال كلمات أو عبارات محددة في الرسائل قبل توجيهها إلى الهدف\n\n"
            f"💡 **مثال**: استبدال 'مرحبا' بـ 'أهلا وسهلا' في جميع الرسائل\n\n"
            f"⚠️ **ملاحظة**: عند تفعيل الاستبدال، سيتم تحويل وضع التوجيه تلقائياً إلى 'نسخ' للرسائل المعدلة",
            buttons=buttons
        )

    async def toggle_text_replacement(self, event, task_id):
        """Toggle text replacement status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        current_status = self.db.is_text_replacement_enabled(task_id)
        new_status = not current_status
        
        # Update replacement status
        self.db.set_text_replacement_enabled(task_id, new_status)
        
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        
        await event.answer(f"✅ {status_text} استبدال النصوص")
        await self.show_text_replacements(event, task_id)

    async def start_add_replacement(self, event, task_id):
        """Start adding text replacements"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_text_replacements', str(task_id))

        buttons = [
            [Button.inline("❌ إلغاء", f"text_replacements_{task_id}")]
        ]

        await event.edit(
            f"➕ إضافة استبدالات نصية\n\n"
            f"📝 **تنسيق الإدخال**: كل استبدال في سطر منفصل بالتنسيق التالي:\n"
            f"`النص_الأصلي >> النص_الجديد`\n\n"
            f"💡 **أمثلة:**\n"
            f"`مرحبا >> أهلا وسهلا`\n"
            f"`عاجل >> 🚨 عاجل 🚨`\n"
            f"`تليجرام >> تلغرام`\n\n"
            f"🔧 **ميزات متقدمة** (اختيارية):\n"
            f"• إضافة `#حساس` في نهاية السطر للحساسية للحروف الكبيرة/الصغيرة\n"
            f"• إضافة `#كلمة` في نهاية السطر للاستبدال ككلمة كاملة فقط\n\n"
            f"**مثال متقدم:**\n"
            f"`Hello >> مرحبا #حساس #كلمة`\n\n"
            f"⚠️ **ملاحظة**: يمكنك إدخال عدة استبدالات في رسالة واحدة",
            buttons=buttons
        )

    async def handle_add_replacements(self, event, task_id, message_text):
        """Handle adding text replacements"""
        user_id = event.sender_id
        
        # Parse replacements from message
        replacements_to_add = []
        
        lines = message_text.split('\n')
        for line in lines:
            line = line.strip()
            if line and '>>' in line:
                # Split by '>>' to get find and replace parts
                parts = line.split('>>', 1)
                if len(parts) == 2:
                    find_text = parts[0].strip()
                    replace_part = parts[1].strip()
                    
                    # Check for advanced options
                    is_case_sensitive = '#حساس' in replace_part
                    is_whole_word = '#كلمة' in replace_part
                    
                    # Clean replace text from options
                    replace_text = replace_part.replace('#حساس', '').replace('#كلمة', '').strip()
                    
                    if find_text and replace_text:
                        replacements_to_add.append((find_text, replace_text, is_case_sensitive, is_whole_word))
        
        if not replacements_to_add:
            await event.respond(
                "❌ لم يتم العثور على استبدالات صحيحة. تأكد من استخدام التنسيق:\n"
                "`النص_الأصلي >> النص_الجديد`"
            )
            return

        # Add replacements to database
        added_count = self.db.add_multiple_text_replacements(task_id, replacements_to_add)
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        buttons = [
            [Button.inline("👀 عرض الاستبدالات", f"view_replacements_{task_id}")],
            [Button.inline("➕ إضافة المزيد", f"add_replacement_{task_id}")],
            [Button.inline("🔙 عودة للإدارة", f"text_replacements_{task_id}")]
        ]

        await event.respond(
            f"✅ تم إضافة {added_count} استبدال نصي\n\n"
            f"📊 إجمالي الاستبدالات المرسلة: {len(replacements_to_add)}\n"
            f"📝 الاستبدالات المضافة: {added_count}\n"
            f"🔄 الاستبدالات المكررة: {len(replacements_to_add) - added_count}\n\n"
            f"✅ استبدال النصوص جاهز للاستخدام!",
            buttons=buttons
        )

    async def view_replacements(self, event, task_id):
        """View text replacements"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        replacements = self.db.get_text_replacements(task_id)

        if not replacements:
            message = f"🔄 استبدالات النصوص\n\n❌ لا توجد استبدالات مضافة حالياً"
        else:
            message = f"🔄 استبدالات النصوص\n\n📋 الاستبدالات المضافة ({len(replacements)}):\n\n"
            
            for i, replacement in enumerate(replacements[:15], 1):  # Show max 15 replacements
                find_text = replacement['find_text']
                replace_text = replacement['replace_text']
                options = []
                
                if replacement['is_case_sensitive']:
                    options.append("حساس للأحرف")
                if replacement['is_whole_word']:
                    options.append("كلمة كاملة")
                
                options_text = f" ({', '.join(options)})" if options else ""
                
                message += f"{i}. `{find_text}` → `{replace_text}`{options_text}\n"
            
            if len(replacements) > 15:
                message += f"\n... و {len(replacements) - 15} استبدال آخر"

        buttons = [
            [Button.inline("➕ إضافة استبدالات", f"add_replacement_{task_id}")],
            [Button.inline("🔙 عودة للإدارة", f"text_replacements_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)

    async def clear_replacements_confirm(self, event, task_id):
        """Confirm clearing text replacements"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        replacements = self.db.get_text_replacements(task_id)

        buttons = [
            [Button.inline("✅ نعم، احذف الكل", f"confirm_clear_replacements_{task_id}")],
            [Button.inline("❌ إلغاء", f"text_replacements_{task_id}")]
        ]

        await event.edit(
            f"⚠️ تأكيد حذف الاستبدالات النصية\n\n"
            f"🗑️ هل أنت متأكد من حذف جميع الاستبدالات ({len(replacements)} استبدال)؟\n\n"
            f"❌ **تحذير**: هذا الإجراء لا يمكن التراجع عنه!\n\n"
            f"سيتم حذف جميع استبدالات النصوص نهائياً.",
            buttons=buttons
        )

    async def clear_replacements_execute(self, event, task_id):
        """Execute clearing text replacements"""
        user_id = event.sender_id
        
        # Clear all replacements
        deleted_count = self.db.clear_text_replacements(task_id)
        
        await event.answer(f"✅ تم حذف جميع الاستبدالات النصية")
        await self.show_text_replacements(event, task_id)

    # Header Settings Methods
    async def show_header_settings(self, event, task_id):
        """Show header settings menu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_message_settings(task_id)
        status = "🟢 مفعل" if settings['header_enabled'] else "🔴 معطل"
        toggle_text = "⏸️ إلغاء التفعيل" if settings['header_enabled'] else "▶️ تفعيل"
        
        current_header = settings['header_text'] if settings['header_text'] else "غير محدد"

        buttons = [
            [Button.inline(toggle_text, f"toggle_header_{task_id}")],
            [Button.inline("✏️ تعديل النص", f"edit_header_{task_id}")],
            [Button.inline("🔙 عودة للإعدادات", f"task_settings_{task_id}")]
        ]

        await event.edit(
            f"📝 رأس الرسالة - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"💬 **النص الحالي**: {current_header}\n\n"
            f"🔄 **الوظيفة**: إضافة نص في بداية كل رسالة قبل توجيهها\n\n"
            f"💡 **مثال**: إضافة 'من قناة الأخبار:' في بداية كل رسالة\n\n"
            f"⚠️ **ملاحظة**: سيتم تحويل وضع التوجيه إلى 'نسخ' عند تفعيل الرأس",
            buttons=buttons
        )

    async def toggle_header(self, event, task_id):
        """Toggle header status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_message_settings(task_id)
        new_status = not settings['header_enabled']
        
        self.db.update_header_settings(task_id, new_status, settings['header_text'])
        
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} رأس الرسالة")
        await self.show_header_settings(event, task_id)

    async def start_edit_header(self, event, task_id):
        """Start editing header text"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_message_settings(task_id)
        current_text = settings['header_text'] if settings['header_text'] else "غير محدد"
        
        self.db.set_conversation_state(user_id, 'waiting_header_text', str(task_id))

        buttons = [
            [Button.inline("❌ إلغاء", f"header_settings_{task_id}")]
        ]

        await event.edit(
            f"✏️ تعديل رأس الرسالة\n\n"
            f"💬 **النص الحالي**: {current_text}\n\n"
            f"📝 أرسل النص الجديد للرأس:\n\n"
            f"💡 **أمثلة**:\n"
            f"• من قناة الأخبار:\n"
            f"• 🚨 عاجل:\n"
            f"• تحديث مهم:\n\n"
            f"⚠️ **ملاحظة**: يمكنك استخدام الرموز والإيموجي",
            buttons=buttons
        )

    async def handle_set_header_text(self, event, task_id, text):
        """Handle setting header text"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        # Update header text and enable it
        self.db.update_header_settings(task_id, True, text.strip())
        
        await event.respond(f"✅ تم تحديث رأس الرسالة بنجاح")
        await self.show_header_settings(event, task_id)

    # Footer Settings Methods
    async def show_footer_settings(self, event, task_id):
        """Show footer settings menu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_message_settings(task_id)
        status = "🟢 مفعل" if settings['footer_enabled'] else "🔴 معطل"
        toggle_text = "⏸️ إلغاء التفعيل" if settings['footer_enabled'] else "▶️ تفعيل"
        
        current_footer = settings['footer_text'] if settings['footer_text'] else "غير محدد"

        buttons = [
            [Button.inline(toggle_text, f"toggle_footer_{task_id}")],
            [Button.inline("✏️ تعديل النص", f"edit_footer_{task_id}")],
            [Button.inline("🔙 عودة للإعدادات", f"task_settings_{task_id}")]
        ]

        await event.edit(
            f"📝 ذيل الرسالة - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"💬 **النص الحالي**: {current_footer}\n\n"
            f"🔄 **الوظيفة**: إضافة نص في نهاية كل رسالة قبل توجيهها\n\n"
            f"💡 **مثال**: إضافة 'انضم لقناتنا: @channel' في نهاية كل رسالة\n\n"
            f"⚠️ **ملاحظة**: سيتم تحويل وضع التوجيه إلى 'نسخ' عند تفعيل الذيل",
            buttons=buttons
        )

    async def toggle_footer(self, event, task_id):
        """Toggle footer status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_message_settings(task_id)
        new_status = not settings['footer_enabled']
        
        self.db.update_footer_settings(task_id, new_status, settings['footer_text'])
        
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} ذيل الرسالة")
        await self.show_footer_settings(event, task_id)

    async def start_edit_footer(self, event, task_id):
        """Start editing footer text"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_message_settings(task_id)
        current_text = settings['footer_text'] if settings['footer_text'] else "غير محدد"
        
        self.db.set_conversation_state(user_id, 'waiting_footer_text', str(task_id))

        buttons = [
            [Button.inline("❌ إلغاء", f"footer_settings_{task_id}")]
        ]

        await event.edit(
            f"✏️ تعديل ذيل الرسالة\n\n"
            f"💬 **النص الحالي**: {current_text}\n\n"
            f"📝 أرسل النص الجديد للذيل:\n\n"
            f"💡 **أمثلة**:\n"
            f"• انضم لقناتنا: @channel\n"
            f"• 🔔 تابعنا للمزيد\n"
            f"• www.example.com\n\n"
            f"⚠️ **ملاحظة**: يمكنك استخدام الرموز والروابط",
            buttons=buttons
        )

    async def handle_set_footer_text(self, event, task_id, text):
        """Handle setting footer text"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        # Update footer text and enable it
        self.db.update_footer_settings(task_id, True, text.strip())
        
        await event.respond(f"✅ تم تحديث ذيل الرسالة بنجاح")
        await self.show_footer_settings(event, task_id)

    # Inline Buttons Methods
    async def show_inline_buttons_settings(self, event, task_id):
        """Show inline buttons settings menu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_message_settings(task_id)
        buttons_list = self.db.get_inline_buttons(task_id)
        
        status = "🟢 مفعل" if settings['inline_buttons_enabled'] else "🔴 معطل"
        toggle_text = "⏸️ إلغاء التفعيل" if settings['inline_buttons_enabled'] else "▶️ تفعيل"

        buttons = [
            [Button.inline(toggle_text, f"toggle_inline_buttons_{task_id}")],
            [Button.inline(f"➕ إضافة أزرار ({len(buttons_list)})", f"add_inline_button_{task_id}")],
            [Button.inline("👀 عرض الأزرار", f"view_inline_buttons_{task_id}")],
            [Button.inline("🗑️ حذف جميع الأزرار", f"clear_inline_buttons_{task_id}")],
            [Button.inline("🔙 عودة للإعدادات", f"task_settings_{task_id}")]
        ]

        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        message_text = (
            f"🔘 أزرار إنلاين - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"🔢 **عدد الأزرار**: {len(buttons_list)}\n\n"
            f"🔄 **الوظيفة**: إضافة أزرار قابلة للنقر أسفل الرسائل المُوجهة\n\n"
            f"💡 **مثال**: زر 'زيارة الموقع' أو 'اشترك في القناة'\n\n"
            f"⚠️ **ملاحظة**: سيتم تحويل وضع التوجيه إلى 'نسخ' عند تفعيل الأزرار\n\n"
            f"🕐 آخر تحديث: {timestamp}"
        )
        
        try:
            await event.edit(message_text, buttons=buttons)
        except Exception as e:
            # If edit fails, send a new message instead
            logger.warning(f"فشل تحرير الرسالة، إرسال رسالة جديدة: {e}")
            await event.respond(message_text, buttons=buttons)

    async def toggle_inline_buttons(self, event, task_id):
        """Toggle inline buttons status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_message_settings(task_id)
        current_status = settings['inline_buttons_enabled']
        
        if current_status:
            # Currently enabled, disable it (but keep the buttons in database)
            self.db.update_inline_buttons_enabled(task_id, False)
            await event.answer("✅ تم إلغاء تفعيل الأزرار الإنلاين")
        else:
            # Currently disabled, enable it if there are buttons
            buttons_list = self.db.get_inline_buttons(task_id)
            if buttons_list:
                self.db.update_inline_buttons_enabled(task_id, True)
                await event.answer("✅ تم تفعيل الأزرار الإنلاين")
            else:
                await event.answer("💡 لتفعيل الأزرار، اضغط 'إضافة أزرار' وأضف زر واحد على الأقل")
        
        await self.show_inline_buttons_settings(event, task_id)

    async def start_add_inline_button(self, event, task_id):
        """Start adding inline button"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        self.db.set_conversation_state(user_id, 'waiting_button_data', str(task_id))

        buttons = [
            [Button.inline("❌ إلغاء", f"inline_buttons_{task_id}")]
        ]

        await event.edit(
            f"➕ إضافة أزرار إنلاين\n\n"
            f"📝 **طريقتان للإضافة**:\n\n"
            f"🔹 **للأزرار المنفصلة** (كل زر في سطر):\n"
            f"`نص الزر الأول - رابط الزر الأول`\n"
            f"`نص الزر الثاني - رابط الزر الثاني`\n\n"
            f"🔹 **لعدة أزرار في صف واحد** (يفصل بينهم |):\n"
            f"`نص الزر الأول - رابط الزر الأول | نص الزر الثاني - رابط الزر الثاني`\n\n"
            f"💡 **أمثلة**:\n"
            f"`زيارة الموقع - https://example.com`\n"
            f"`اشترك بالقناة - https://t.me/channel`\n"
            f"`تابعنا - https://twitter.com/us | دعمنا - https://paypal.com`\n\n"
            f"⚠️ **ملاحظة**: استخدم الشرطة (-) لفصل النص عن الرابط",
            buttons=buttons
        )

    async def handle_add_inline_button(self, event, task_id, text):
        """Handle adding inline buttons with new format"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        lines = text.strip().split('\n')
        added_count = 0
        errors = []
        current_row = 0
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            try:
                # Check if line contains multiple buttons (separated by |)
                if '|' in line:
                    # Multiple buttons in one row
                    button_parts = line.split('|')
                    col_pos = 0
                    for button_part in button_parts:
                        button_part = button_part.strip()
                        if ' - ' in button_part:
                            text_url = button_part.split(' - ', 1)
                            button_text = text_url[0].strip()
                            button_url = text_url[1].strip()
                            
                            if button_text and button_url:
                                self.db.add_inline_button(task_id, button_text, button_url, current_row, col_pos)
                                added_count += 1
                                col_pos += 1
                            else:
                                errors.append(f"نص أو رابط فارغ: {button_part}")
                        else:
                            errors.append(f"تنسيق خاطئ (استخدم -): {button_part}")
                    current_row += 1
                else:
                    # Single button
                    if ' - ' in line:
                        text_url = line.split(' - ', 1)
                        button_text = text_url[0].strip()
                        button_url = text_url[1].strip()
                        
                        if button_text and button_url:
                            self.db.add_inline_button(task_id, button_text, button_url, current_row, 0)
                            added_count += 1
                            current_row += 1
                        else:
                            errors.append(f"نص أو رابط فارغ: {line}")
                    else:
                        errors.append(f"تنسيق خاطئ (استخدم -): {line}")
                        
            except Exception as e:
                errors.append(f"خطأ في السطر: {line}")
        
        result_msg = f"✅ تم إضافة {added_count} زر"
        if errors:
            result_msg += f"\n❌ أخطاء ({len(errors)}):\n" + "\n".join(errors[:3])
        
        await event.respond(result_msg)
        await self.show_inline_buttons_settings(event, task_id)

    async def view_inline_buttons(self, event, task_id):
        """View inline buttons"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        buttons_list = self.db.get_inline_buttons(task_id)

        if not buttons_list:
            message = f"🔘 أزرار إنلاين\n\n❌ لا توجد أزرار مضافة حالياً"
        else:
            message = f"🔘 أزرار إنلاين\n\n📋 الأزرار المضافة ({len(buttons_list)}):\n\n"
            
            # Group buttons by row
            rows = {}
            for button in buttons_list:
                row = button['row_position']
                if row not in rows:
                    rows[row] = []
                rows[row].append(button)
            
            for row_num in sorted(rows.keys()):
                row_buttons = sorted(rows[row_num], key=lambda x: x['col_position'])
                message += f"**الصف {row_num}:**\n"
                for button in row_buttons:
                    message += f"• `{button['button_text']}` → {button['button_url']}\n"
                message += "\n"

        buttons = [
            [Button.inline("➕ إضافة المزيد", f"add_inline_button_{task_id}")],
            [Button.inline("🔙 عودة للإدارة", f"inline_buttons_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)

    async def clear_inline_buttons_confirm(self, event, task_id):
        """Confirm clearing inline buttons"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        buttons_list = self.db.get_inline_buttons(task_id)

        buttons = [
            [Button.inline("✅ نعم، احذف الكل", f"confirm_clear_inline_buttons_{task_id}")],
            [Button.inline("❌ إلغاء", f"inline_buttons_{task_id}")]
        ]

        await event.edit(
            f"⚠️ تأكيد حذف الأزرار الإنلاين\n\n"
            f"🗑️ هل أنت متأكد من حذف جميع الأزرار ({len(buttons_list)} زر)؟\n\n"
            f"❌ **تحذير**: هذا الإجراء لا يمكن التراجع عنه!\n\n"
            f"سيتم حذف جميع الأزرار الإنلاين نهائياً.",
            buttons=buttons
        )

    async def clear_inline_buttons_execute(self, event, task_id):
        """Execute clearing inline buttons"""
        user_id = event.sender_id
        
        # Clear all buttons
        deleted_count = self.db.clear_inline_buttons(task_id)
        
        await event.answer(f"✅ تم حذف جميع الأزرار الإنلاين")
        await self.show_inline_buttons_settings(event, task_id)

    # Forwarding Settings Methods
    async def show_forwarding_settings(self, event, task_id):
        """Show forwarding settings menu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_forwarding_settings(task_id)
        
        # Format status icons and time
        link_preview_status = "🟢 مفعل" if settings['link_preview_enabled'] else "🔴 معطل"
        pin_message_status = "🟢 مفعل" if settings['pin_message_enabled'] else "🔴 معطل"
        silent_status = "🟢 بصمت" if settings['silent_notifications'] else "🔴 مع إشعار"
        auto_delete_status = "🟢 مفعل" if settings['auto_delete_enabled'] else "🔴 معطل"
        sync_edit_status = "🟢 مفعل" if settings['sync_edit_enabled'] else "🔴 معطل"
        sync_delete_status = "🟢 مفعل" if settings['sync_delete_enabled'] else "🔴 معطل"
        split_album_status = "🟢 تقسيم" if settings.get('split_album_enabled', False) else "🔴 إبقاء مجمع"
        
        # Convert seconds to readable format
        delete_time = settings['auto_delete_time']
        if delete_time >= 3600:
            time_display = f"{delete_time // 3600} ساعة"
        elif delete_time >= 60:
            time_display = f"{delete_time // 60} دقيقة"
        else:
            time_display = f"{delete_time} ثانية"



        buttons = [
            # الصف الأول - معاينة الرابط وتثبيت الرسالة
            [Button.inline(f"🔗 معاينة الرابط {link_preview_status.split()[0]}", f"toggle_link_preview_{task_id}"),
             Button.inline(f"📌 تثبيت الرسالة {pin_message_status.split()[0]}", f"toggle_pin_message_{task_id}")],
            
            # الصف الثاني - الإشعارات والألبومات
            [Button.inline(f"🔔 الإشعارات {silent_status.split()[0]}", f"toggle_silent_notifications_{task_id}"),
             Button.inline(f"📸 الألبومات {split_album_status.split()[0]}", f"toggle_split_album_{task_id}")],
            
            # الصف الثالث - الحذف التلقائي ومزامنة التعديل
            [Button.inline(f"🗑️ حذف تلقائي {auto_delete_status.split()[0]}", f"toggle_auto_delete_{task_id}"),
             Button.inline(f"🔄 مزامنة التعديل {sync_edit_status.split()[0]}", f"toggle_sync_edit_{task_id}")],
            
            # الصف الرابع - مزامنة الحذف
            [Button.inline(f"🗂️ مزامنة الحذف {sync_delete_status.split()[0]}", f"toggle_sync_delete_{task_id}")],
        ]
        
        # إضافة زر تعديل المدة إذا كان الحذف التلقائي مفعل
        if settings['auto_delete_enabled']:
            buttons[-1].append(Button.inline(f"⏰ مدة الحذف ({time_display})", f"set_auto_delete_time_{task_id}"))
            
        # الصف الأخير - العودة
        buttons.append([Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")])

        from datetime import datetime
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        message_text = (
            f"🔧 إعدادات التوجيه - المهمة #{task_id}\n\n"
            f"📋 **الإعدادات الحالية**:\n\n"
            f"🔗 **معاينة الرابط**: {link_preview_status}\n"
            f"   └ عرض معاينة للروابط المُوجهة\n\n"
            f"📌 **تثبيت الرسالة**: {pin_message_status}\n"
            f"   └ تثبيت الرسالة في المحادثة الهدف\n\n"
            f"🔔 **الإشعارات**: {silent_status}\n"
            f"   └ إشعار المشتركين عند النشر\n\n"
            f"📸 **الألبومات**: {split_album_status}\n"
            f"   └ تفكيك الألبومات أو إبقاؤها مجمعة\n\n"
            f"🗑️ **الحذف التلقائي**: {auto_delete_status}\n"
        )
        
        if settings['auto_delete_enabled']:
            message_text += f"   └ حذف تلقائي بعد: {time_display}\n\n"
        else:
            message_text += f"   └ الرسائل تبقى إلى الأبد\n\n"
            
        message_text += (
            f"🔄 **مزامنة التعديل**: {sync_edit_status}\n"
            f"   └ تحديث الرسالة في الأهداف عند تعديلها في المصدر\n\n"
            f"🗂️ **مزامنة الحذف**: {sync_delete_status}\n"
            f"   └ حذف الرسالة من الأهداف عند حذفها من المصدر\n\n"
            f"🕐 آخر تحديث: {timestamp}"
        )
        
        try:
            await event.edit(message_text, buttons=buttons)
        except Exception as e:
            logger.warning(f"فشل تحرير الرسالة، إرسال رسالة جديدة: {e}")
            await event.respond(message_text, buttons=buttons)

    async def toggle_link_preview(self, event, task_id):
        """Toggle link preview setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_link_preview(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} معاينة الرابط")
        await self.show_forwarding_settings(event, task_id)

    async def toggle_pin_message(self, event, task_id):
        """Toggle pin message setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_pin_message(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} تثبيت الرسالة")
        await self.show_forwarding_settings(event, task_id)

    async def toggle_silent_notifications(self, event, task_id):
        """Toggle silent notifications setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_silent_notifications(task_id)
        
        status_text = "النشر بصمت" if new_state else "النشر مع إشعار"
        await event.answer(f"✅ تم تفعيل {status_text}")
        await self.show_forwarding_settings(event, task_id)

    async def toggle_auto_delete(self, event, task_id):
        """Toggle auto delete setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_auto_delete(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} الحذف التلقائي")
        await self.show_forwarding_settings(event, task_id)

    async def toggle_sync_edit(self, event, task_id):
        """Toggle sync edit setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_sync_edit(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} مزامنة التعديل")
        await self.show_forwarding_settings(event, task_id)

    async def toggle_sync_delete(self, event, task_id):
        """Toggle sync delete setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_sync_delete(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} مزامنة الحذف")
        await self.show_forwarding_settings(event, task_id)

    async def toggle_split_album(self, event, task_id):
        """Toggle split album setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_split_album(task_id)
        
        status_text = "تم تفعيل تفكيك الألبومات" if new_state else "تم تفعيل إبقاء الألبومات مجمعة"
        await event.answer(f"✅ {status_text}")
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        await self.show_forwarding_settings(event, task_id)

    # ===== Translation Settings =====
    
    async def show_translation_settings(self, event, task_id):
        """Show translation settings for task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_translation_settings(task_id)

        message = f"🌐 إعدادات الترجمة للمهمة: {task_name}\n\n"
        
        if settings['enabled']:
            message += "📊 **الحالة**: 🟢 مفعل\n\n"
            message += f"🗣️ **لغة المصدر**: {settings['source_language']}\n"
            message += f"🎯 **لغة الهدف**: {settings['target_language']}\n\n"
            message += "💡 سيتم ترجمة الرسائل تلقائياً من اللغة المصدر إلى لغة الهدف"
        else:
            message += "📊 **الحالة**: 🔴 معطل\n\n"
            message += "💡 يمكنك تفعيل الترجمة التلقائية للرسائل"

        buttons = [
            [Button.inline(f"{'❌ تعطيل' if settings['enabled'] else '✅ تفعيل'} الترجمة", f"toggle_translation_{task_id}")],
        ]
        
        if settings['enabled']:
            buttons.extend([
                [Button.inline(f"🗣️ تغيير لغة المصدر ({settings['source_language']})", f"set_translation_source_{task_id}")],
                [Button.inline(f"🎯 تغيير لغة الهدف ({settings['target_language']})", f"set_translation_target_{task_id}")],
            ])

        buttons.append([Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")])

        await event.edit(message, buttons=buttons)

    async def toggle_translation(self, event, task_id):
        """Toggle translation setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_translation_settings(task_id)
        new_status = not settings['enabled']
        
        success = self.db.update_translation_settings(task_id, enabled=new_status)

        if success:
            status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
            await event.answer(f"✅ {status_text} الترجمة التلقائية")

            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await self.show_translation_settings(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير إعداد الترجمة")

    async def set_translation_language(self, event, task_id, setting):
        """Start setting translation language (source or target)"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        current_settings = self.db.get_translation_settings(task_id)
        
        setting_name = "لغة المصدر" if setting == "source" else "لغة الهدف"
        current_lang = current_settings['source_language'] if setting == "source" else current_settings['target_language']

        # Language options
        languages = [
            ('ar', 'العربية', '🇸🇦'),
            ('en', 'English', '🇺🇸'),
            ('es', 'Español', '🇪🇸'),
            ('fr', 'Français', '🇫🇷'),
            ('de', 'Deutsch', '🇩🇪'),
            ('it', 'Italiano', '🇮🇹'),
            ('pt', 'Português', '🇵🇹'),
            ('ru', 'Русский', '🇷🇺'),
            ('zh', '中文', '🇨🇳'),
            ('ja', '日本語', '🇯🇵'),
            ('ko', '한국어', '🇰🇷'),
            ('hi', 'हिन्दी', '🇮🇳'),
            ('tr', 'Türkçe', '🇹🇷'),
            ('auto', 'تلقائي', '🔍')
        ]

        buttons = []
        for code, name, flag in languages:
            status = " ✅" if code == current_lang else ""
            buttons.append([Button.inline(f"{flag} {name}{status}", f"set_lang_{setting}_{task_id}_{code}")])

        buttons.append([Button.inline("🔙 رجوع لإعدادات الترجمة", f"translation_settings_{task_id}")])

        message = f"🌐 تعديل {setting_name}\n"
        message += f"📝 المهمة: {task_name}\n\n"
        message += f"📊 اللغة الحالية: {current_lang}\n\n"
        message += "🗂️ اختر اللغة الجديدة:"

        await event.edit(message, buttons=buttons)

    async def set_specific_language(self, event, task_id, setting, language_code):
        """Set specific language for translation"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Update the language setting
        if setting == "source":
            success = self.db.update_translation_settings(task_id, source_language=language_code)
            setting_name = "لغة المصدر"
        else:
            success = self.db.update_translation_settings(task_id, target_language=language_code)
            setting_name = "لغة الهدف"

        if success:
            # Get language name
            languages = {
                'ar': 'العربية', 'en': 'English', 'es': 'Español', 'fr': 'Français',
                'de': 'Deutsch', 'it': 'Italiano', 'pt': 'Português', 'ru': 'Русский',
                'zh': '中文', 'ja': '日本語', 'ko': '한국어', 'hi': 'हिन्दी',
                'tr': 'Türkçe', 'auto': 'تلقائي'
            }
            language_name = languages.get(language_code, language_code)
            
            await event.answer(f"✅ تم تحديث {setting_name} إلى: {language_name}")

            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await self.show_translation_settings(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث اللغة")

    async def start_set_auto_delete_time(self, event, task_id):
        """Start setting auto delete time"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        current_settings = self.db.get_forwarding_settings(task_id)
        current_time = current_settings['auto_delete_time']
        
        # Convert to readable format
        if current_time >= 3600:
            current_display = f"{current_time // 3600} ساعة"
        elif current_time >= 60:
            current_display = f"{current_time // 60} دقيقة"
        else:
            current_display = f"{current_time} ثانية"

        self.db.set_conversation_state(user_id, 'waiting_auto_delete_time', str(task_id))

        buttons = [
            [Button.inline("⏰ 5 دقائق", f"set_delete_time_{task_id}_300")],
            [Button.inline("⏰ 30 دقيقة", f"set_delete_time_{task_id}_1800")],
            [Button.inline("⏰ 1 ساعة", f"set_delete_time_{task_id}_3600")],
            [Button.inline("⏰ 6 ساعات", f"set_delete_time_{task_id}_21600")],
            [Button.inline("⏰ 24 ساعة", f"set_delete_time_{task_id}_86400")],
            [Button.inline("❌ إلغاء", f"forwarding_settings_{task_id}")]
        ]

        await event.edit(
            f"⏰ تحديد مدة الحذف التلقائي\n\n"
            f"📊 **المدة الحالية**: {current_display}\n\n"
            f"🎯 **اختر مدة جديدة**:\n\n"
            f"💡 أو أرسل رقماً بالثواني (مثال: 7200 للساعتين)\n\n"
            f"⚠️ **تنبيه**: سيتم حذف الرسائل تلقائياً بعد المدة المحددة",
            buttons=buttons
        )

    async def handle_set_auto_delete_time(self, event, task_id, time_str):
        """Handle setting auto delete time from text input"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        try:
            seconds = int(time_str.strip())
            if seconds < 60:
                await event.respond("❌ أقل مدة مسموحة هي 60 ثانية")
                return
            elif seconds > 604800:  # 7 days
                await event.respond("❌ أقصى مدة مسموحة هي 7 أيام (604800 ثانية)")
                return
                
            self.db.set_auto_delete_time(task_id, seconds)
            
            # Convert to readable format
            if seconds >= 3600:
                time_display = f"{seconds // 3600} ساعة"
            elif seconds >= 60:
                time_display = f"{seconds // 60} دقيقة"
            else:
                time_display = f"{seconds} ثانية"
                
            await event.respond(f"✅ تم تحديد مدة الحذف التلقائي إلى {time_display}")
            await self.show_forwarding_settings(event, task_id)
            
        except ValueError:
            await event.respond("❌ يرجى إدخال رقم صحيح بالثواني")

    async def set_delete_time_direct(self, event, task_id, seconds):
        """Set auto delete time directly from button"""
        user_id = event.sender_id
        
        self.db.set_auto_delete_time(task_id, seconds)
        
        # Convert to readable format
        if seconds >= 3600:
            time_display = f"{seconds // 3600} ساعة"
        elif seconds >= 60:
            time_display = f"{seconds // 60} دقيقة"
        else:
            time_display = f"{seconds} ثانية"
            
        await event.answer(f"✅ تم تحديد مدة الحذف التلقائي إلى {time_display}")
        await self.show_forwarding_settings(event, task_id)

    # ===== Advanced Filters Management =====
    
    async def show_advanced_filters(self, event, task_id):
        """Show advanced filters main menu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get advanced filter settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        
        # Create status indicators
        def status_icon(enabled):
            return "✅" if enabled else "❌"
        
        day_status = status_icon(advanced_settings['day_filter_enabled'])
        hours_status = status_icon(advanced_settings['working_hours_enabled'])
        lang_status = status_icon(advanced_settings['language_filter_enabled'])
        admin_status = status_icon(advanced_settings['admin_filter_enabled'])
        duplicate_status = status_icon(advanced_settings['duplicate_filter_enabled'])
        inline_btn_status = status_icon(advanced_settings['inline_button_filter_enabled'])
        forwarded_status = status_icon(advanced_settings['forwarded_message_filter_enabled'])
        
        buttons = [
            # الصف الأول - فلتر الأيام وساعات العمل
            [Button.inline(f"📅 فلتر الأيام {day_status}", f"day_filters_{task_id}"),
             Button.inline(f"⏰ ساعات العمل {hours_status}", f"working_hours_filter_{task_id}")],
            
            # الصف الثاني - فلتر اللغة والمشرفين
            [Button.inline(f"🌍 فلتر اللغة {lang_status}", f"language_filters_{task_id}"),
             Button.inline(f"👮‍♂️ فلتر المشرفين {admin_status}", f"admin_filters_{task_id}")],
            
            # الصف الثالث - فلتر التكرار والأزرار
            [Button.inline(f"🔁 فلتر التكرار {duplicate_status}", f"duplicate_filter_{task_id}"),
             Button.inline(f"🔘 فلتر الأزرار {inline_btn_status}", f"inline_button_filter_{task_id}")],
            
            # الصف الرابع - فلتر الرسائل المعاد توجيهها
            [Button.inline(f"↪️ فلتر المعاد توجيهه {forwarded_status}", f"forwarded_msg_filter_{task_id}")],
            
            # الصف الأخير - العودة
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]
        
        await event.edit(
            f"🅰️ الفلاتر المتقدمة: {task_name}\n\n"
            f"📋 حالة الفلاتر:\n"
            f"• فلتر الأيام: {day_status}\n"
            f"• ساعات العمل: {hours_status}\n"
            f"• فلتر اللغة: {lang_status}\n"
            f"• فلتر المشرفين: {admin_status}\n"
            f"• فلتر التكرار: {duplicate_status}\n"
            f"• فلتر الأزرار: {inline_btn_status}\n"
            f"• فلتر المعاد توجيهه: {forwarded_status}\n\n"
            f"💡 يمكنك تخصيص كل فلتر حسب احتياجاتك",
            buttons=buttons
        )

    async def handle_message_approval(self, event, pending_id: int, approved: bool):
        """Handle message approval/rejection"""
        user_id = event.sender_id
        
        try:
            # Get pending message details
            pending_message = self.db.get_pending_message(pending_id)
            if not pending_message or pending_message['user_id'] != user_id:
                await event.answer("❌ الرسالة غير موجودة أو غير مصرح لك بالوصول إليها")
                return
            
            if pending_message['status'] != 'pending':
                await event.answer("❌ هذه الرسالة تم التعامل معها بالفعل")
                return
            
            task_id = pending_message['task_id']
            task = self.db.get_task(task_id, user_id)
            
            if not task:
                await event.answer("❌ المهمة غير موجودة")
                return
            
            if approved:
                # Mark as approved and proceed with forwarding
                self.db.update_pending_message_status(pending_id, 'approved')
                
                # Process the message through userbot
                success = await self._process_approved_message(pending_message, task)
                if not success:
                    await event.answer("⚠️ تمت الموافقة ولكن فشل في إرسال الرسالة")
                
                # Update the message to show approval
                try:
                    new_text = "✅ **تمت الموافقة**\n\n" + "هذه الرسالة تمت الموافقة عليها وتم إرسالها إلى الأهداف."
                    await event.edit(new_text, buttons=None)
                except:
                    await event.answer("✅ تمت الموافقة على الرسالة وتم إرسالها")
                
            else:
                # Mark as rejected
                self.db.update_pending_message_status(pending_id, 'rejected')
                
                # Update the message to show rejection
                try:
                    new_text = "❌ **تم رفض الرسالة**\n\n" + "هذه الرسالة تم رفضها ولن يتم إرسالها."
                    await event.edit(new_text, buttons=None)
                except:
                    await event.answer("❌ تم رفض الرسالة")
                    
            logger.info(f"📋 تم {'قبول' if approved else 'رفض'} الرسالة المعلقة {pending_id} للمستخدم {user_id}")
            
        except Exception as e:
            logger.error(f"خطأ في معالجة الموافقة: {e}")
            await event.answer("❌ حدث خطأ في معالجة الطلب")

    async def _process_approved_message(self, pending_message, task):
        """Process approved message by sending it through userbot"""
        try:
            from userbot_service.userbot import userbot_instance
            import json
            
            user_id = pending_message['user_id']
            message_data = json.loads(pending_message['message_data'])
            
            # Get userbot client
            if user_id not in userbot_instance.clients:
                logger.error(f"❌ UserBot غير متصل للمستخدم {user_id}")
                return False
                
            client = userbot_instance.clients[user_id]
            
            # Get the original message from source
            source_chat_id = int(pending_message['source_chat_id'])
            source_message_id = pending_message['source_message_id']
            
            try:
                message = await client.get_messages(source_chat_id, ids=source_message_id)
                if not message:
                    logger.error(f"❌ لم يتم العثور على الرسالة الأصلية: {source_chat_id}:{source_message_id}")
                    return False
                    
                # Get all targets for this task
                targets = userbot_instance.db.get_task_targets(pending_message['task_id'])
                
                success_count = 0
                for target in targets:
                    try:
                        # Forward the message to each target
                        await userbot_instance._forward_or_copy_message(
                            message, task, user_id, client, target['chat_id']
                        )
                        success_count += 1
                        logger.info(f"✅ تم إرسال رسالة موافق عليها إلى {target['chat_id']}")
                        
                        # Add delay between targets
                        import asyncio
                        await asyncio.sleep(1)
                        
                    except Exception as target_error:
                        logger.error(f"❌ فشل في إرسال الرسالة إلى {target['chat_id']}: {target_error}")
                        continue
                
                logger.info(f"📊 تم إرسال الرسالة الموافق عليها إلى {success_count}/{len(targets)} هدف")
                return success_count > 0
                
            except Exception as msg_error:
                logger.error(f"❌ خطأ في الحصول على الرسالة الأصلية: {msg_error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرسالة الموافق عليها: {e}")
            return False

    async def show_pending_message_details(self, event, pending_id: int):
        """Show detailed information about pending message"""
        user_id = event.sender_id
        
        try:
            pending_message = self.db.get_pending_message(pending_id)
            if not pending_message or pending_message['user_id'] != user_id:
                await event.answer("❌ الرسالة غير موجودة أو غير مصرح لك بالوصول إليها")
                return
            
            import json
            message_data = json.loads(pending_message['message_data'])
            task = self.db.get_task(pending_message['task_id'], user_id)
            
            if not task:
                await event.answer("❌ المهمة غير موجودة")
                return
                
            task_name = task.get('task_name', f"مهمة {pending_message['task_id']}")
            
            details_text = f"""
📋 **تفاصيل الرسالة المعلقة**

📝 **المهمة:** {task_name}
📊 **النوع:** {message_data.get('media_type', 'نص')}
📱 **المصدر:** {pending_message['source_chat_id']}
🆔 **معرف الرسالة:** {pending_message['source_message_id']}
📅 **التاريخ:** {message_data.get('date', 'غير محدد')}

💬 **المحتوى:**
{message_data.get('text', 'لا يوجد نص')}

⚡ اختر إجراء:
"""
            
            keyboard = [
                [
                    Button.inline("✅ موافق", f"approve_{pending_id}"),
                    Button.inline("❌ رفض", f"reject_{pending_id}")
                ]
            ]
            
            await event.edit(details_text, buttons=keyboard)
            
        except Exception as e:
            logger.error(f"خطأ في عرض تفاصيل الرسالة المعلقة: {e}")
            await event.answer("❌ حدث خطأ في عرض التفاصيل")

    async def _process_approved_message(self, pending_message, task):
        """Process approved message through userbot"""
        try:
            from userbot_service.userbot import userbot_instance
            
            user_id = pending_message['user_id']
            source_chat_id = int(pending_message['source_chat_id'])
            source_message_id = pending_message['source_message_id']
            
            # Get the original message from source chat
            if user_id in userbot_instance.clients:
                client = userbot_instance.clients[user_id]
                
                # Get the original message
                original_message = await client.get_messages(source_chat_id, ids=source_message_id)
                
                if original_message:
                    # Process the message through normal forwarding logic
                    await userbot_instance._forward_to_targets(original_message, task, user_id, client)
                    logger.info(f"✅ تم إرسال الرسالة المقبولة {pending_message['id']} للأهداف")
                else:
                    logger.warning(f"⚠️ لم يتم العثور على الرسالة الأصلية {source_message_id}")
                    
        except Exception as e:
            logger.error(f"خطأ في معالجة الرسالة المقبولة: {e}")

    async def show_advanced_features(self, event, task_id):
        """Show advanced features menu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        buttons = [
            # Row 1 - Character & Rate Limits
            [Button.inline("🔢 حد الأحرف", f"character_limit_{task_id}"),
             Button.inline("⏱️ تحكم المعدل", f"rate_limit_{task_id}")],
            
            # Row 2 - Timing Settings
            [Button.inline("⏳ تأخير التوجيه", f"forwarding_delay_{task_id}"),
             Button.inline("📊 فترات الإرسال", f"sending_interval_{task_id}")],
            
            # Row 3 - Publishing Mode
            [Button.inline("📋 وضع النشر", f"toggle_publishing_mode_{task_id}")],
            
            # Row 4 - Back
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]
        
        await event.edit(
            f"⚙️ المميزات المتقدمة: {task_name}\n\n"
            f"🔧 إعدادات التحكم المتقدمة:\n\n"
            f"🔢 حد الأحرف - تحديد طول النصوص\n"
            f"⏱️ تحكم المعدل - السيطرة على سرعة الإرسال\n"
            f"⏳ تأخير التوجيه - تأخير زمني للرسائل\n"
            f"📊 فترات الإرسال - توقيت بين الرسائل\n"
            f"📋 وضع النشر - تلقائي أو يدوي",
            buttons=buttons
        )

    async def show_publishing_mode_settings(self, event, task_id):
        """Show publishing mode settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        # Get publishing mode from forwarding settings
        forwarding_settings = self.db.get_forwarding_settings(task_id)
        current_mode = forwarding_settings.get('publishing_mode', 'auto')
        
        status_text = {
            'auto': '🟢 تلقائي - يتم إرسال الرسائل فوراً',
            'manual': '🟡 يدوي - يتطلب موافقة قبل الإرسال'
        }
        
        buttons = [
            [Button.inline("🔄 تبديل الوضع", f"toggle_publishing_mode_{task_id}")],
            [Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")]
        ]
        
        # If manual mode, show pending messages count
        additional_info = ""
        if current_mode == 'manual':
            pending_count = len(self.db.get_pending_messages(user_id, task_id))
            if pending_count > 0:
                additional_info = f"\n\n📋 الرسائل المعلقة: {pending_count} رسالة في انتظار الموافقة"
        
        await event.edit(
            f"📋 وضع النشر للمهمة: {task_name}\n\n"
            f"📊 الوضع الحالي: {status_text.get(current_mode, 'غير معروف')}\n\n"
            f"📝 شرح الأوضاع:\n"
            f"🟢 تلقائي: الرسائل تُرسل فوراً دون تدخل\n"
            f"🟡 يدوي: الرسائل تُرسل لك للمراجعة والموافقة{additional_info}",
            buttons=buttons
        )

    async def toggle_publishing_mode(self, event, task_id):
        """Toggle publishing mode between auto and manual"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get publishing mode from forwarding settings
        forwarding_settings = self.db.get_forwarding_settings(task_id)
        current_mode = forwarding_settings.get('publishing_mode', 'auto')
        new_mode = 'manual' if current_mode == 'auto' else 'auto'
        
        success = self.db.update_task_publishing_mode(task_id, new_mode)
        
        if success:
            mode_names = {
                'auto': 'تلقائي',
                'manual': 'يدوي'
            }
            
            await event.answer(f"✅ تم تغيير وضع النشر إلى: {mode_names[new_mode]}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            await self.show_publishing_mode_settings(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير وضع النشر")

    async def show_character_limit_settings(self, event, task_id):
        """Show character limit settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_character_limit_settings(task_id)
        
        status_text = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        limit_text = str(settings['max_chars']) if settings['max_chars'] else "غير محدد"
        mode_text = "نطاق محدد" if settings['use_range'] else "حد أقصى فقط"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_char_limit_{task_id}")],
            [Button.inline(f"🔢 تعديل الحد الأقصى ({limit_text})", f"edit_char_limit_{task_id}")],
            [Button.inline(f"⚙️ تغيير الإجراء ({mode_text})", f"toggle_char_mode_{task_id}")],
            [Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")]
        ]
        
        await event.edit(
            f"🔢 إعدادات حد الأحرف للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📏 الحد الأقصى: {limit_text} حرف\n"
            f"⚙️ الإجراء: {mode_text}\n\n"
            f"📝 شرح الأوضاع:\n"
            f"📏 نطاق محدد: يتم قبول النصوص ضمن نطاق محدد\n"
            f"⬆️ حد أقصى فقط: يتم قبول النصوص تحت الحد الأقصى",
            buttons=buttons
        )

    async def show_rate_limit_settings(self, event, task_id):
        """Show rate limit settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_rate_limit_settings(task_id)
        
        status_text = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        limit_text = str(settings['message_count']) if settings['message_count'] else "غير محدد"
        period_text = f"{settings['time_period_seconds']} ثانية" if settings['time_period_seconds'] else "غير محدد"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_rate_limit_{task_id}")],
            [Button.inline(f"📊 تعديل العدد ({limit_text})", f"edit_rate_limit_count_{task_id}")],
            [Button.inline(f"⏱️ تعديل المدة ({period_text})", f"edit_rate_limit_period_{task_id}")],
            [Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")]
        ]
        
        await event.edit(
            f"⏱️ إعدادات تحكم المعدل للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📈 عدد الرسائل: {limit_text} رسالة\n"
            f"⏱️ خلال: {period_text}\n\n"
            f"📝 الوصف:\n"
            f"يحدد هذا الإعداد عدد الرسائل المسموح بإرسالها خلال فترة زمنية محددة",
            buttons=buttons
        )

    async def show_forwarding_delay_settings(self, event, task_id):
        """Show forwarding delay settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_forwarding_delay_settings(task_id)
        
        status_text = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        
        if settings['delay_seconds']:
            if settings['delay_seconds'] >= 3600:
                delay_text = f"{settings['delay_seconds'] // 3600} ساعة"
            elif settings['delay_seconds'] >= 60:
                delay_text = f"{settings['delay_seconds'] // 60} دقيقة"
            else:
                delay_text = f"{settings['delay_seconds']} ثانية"
        else:
            delay_text = "غير محدد"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_forwarding_delay_{task_id}")],
            [Button.inline(f"⏱️ تعديل التأخير ({delay_text})", f"edit_forwarding_delay_{task_id}")],
            [Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")]
        ]
        
        await event.edit(
            f"⏳ إعدادات تأخير التوجيه للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⏱️ مدة التأخير: {delay_text}\n\n"
            f"📝 الوصف:\n"
            f"يضيف تأخير زمني قبل إرسال الرسائل المُوجهة",
            buttons=buttons
        )

    async def show_sending_interval_settings(self, event, task_id):
        """Show sending interval settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_sending_interval_settings(task_id)
        
        status_text = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        
        if settings['interval_seconds']:
            if settings['interval_seconds'] >= 3600:
                interval_text = f"{settings['interval_seconds'] // 3600} ساعة"
            elif settings['interval_seconds'] >= 60:
                interval_text = f"{settings['interval_seconds'] // 60} دقيقة"
            else:
                interval_text = f"{settings['interval_seconds']} ثانية"
        else:
            interval_text = "غير محدد"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_sending_interval_{task_id}")],
            [Button.inline(f"📊 تعديل الفترة ({interval_text})", f"edit_sending_interval_{task_id}")],
            [Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")]
        ]
        
        await event.edit(
            f"📊 إعدادات فترات الإرسال للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⏱️ الفترة بين الرسائل: {interval_text}\n\n"
            f"📝 الوصف:\n"
            f"يحدد الفترة الزمنية بين إرسال كل رسالة والتي تليها",
            buttons=buttons
        )

    async def toggle_forwarding_delay(self, event, task_id):
        """Toggle forwarding delay setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_forwarding_delay(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} تأخير التوجيه")
        await self.show_forwarding_delay_settings(event, task_id)

    async def toggle_sending_interval(self, event, task_id):
        """Toggle sending interval setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_sending_interval(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} فترات الإرسال")
        await self.show_sending_interval_settings(event, task_id)

    async def toggle_rate_limit(self, event, task_id):
        """Toggle rate limit setting"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        new_state = self.db.toggle_rate_limit(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} تحكم المعدل")
        await self.show_rate_limit_settings(event, task_id)

async def run_simple_bot():
    """Run the simple telegram bot"""
    logger.info("🚀 بدء تشغيل نظام بوت تليجرام...")
    
    # Create bot instance  
    bot = SimpleTelegramBot()
    
    # Start the bot
    await bot.start()
    
    # Return bot instance for global access
    return bot

    # ===== Advanced Features Menu =====
    
