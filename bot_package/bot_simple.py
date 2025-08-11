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

    async def start(self):
        """Start the bot"""
        if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
            logger.error("❌ BOT_TOKEN غير محدد في متغيرات البيئة")
            return False

        # Create bot client
        self.bot = TelegramClient('bot_session', int(API_ID), API_HASH)
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
        # Only respond to /start in private chats
        if not event.is_private:
            logger.info(f"🚫 تجاهل أمر /start في محادثة غير خاصة: {event.chat_id}")
            return

        user_id = event.sender_id

        # Check if user is authenticated
        if self.db.is_user_authenticated(user_id):
            # Show main menu
            buttons = [
                [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
                [Button.inline("⚙️ الإعدادات", b"settings")],
                [Button.inline("ℹ️ حول البوت", b"about")]
            ]

            await event.respond(
                f"🎉 أهلاً بك في بوت التوجيه التلقائي!\n\n"
                f"👋 مرحباً {event.sender.first_name}\n"
                f"🔑 أنت مسجل دخولك بالفعل\n\n"
                f"اختر ما تريد فعله:",
                buttons=buttons
            )
        else:
            # Show authentication menu
            buttons = [
                [Button.inline("📱 تسجيل الدخول برقم الهاتف", b"auth_phone")]
            ]

            await event.respond(
                f"🤖 مرحباً بك في بوت التوجيه التلقائي!\n\n"
                f"📋 هذا البوت يساعدك في:\n"
                f"• توجيه الرسائل تلقائياً\n"
                f"• إدارة مهام التوجيه\n"
                f"• مراقبة المحادثات\n\n"
                f"🔐 يجب تسجيل الدخول أولاً:",
                buttons=buttons
            )


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
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد موقع العلامة المائية: {e}")
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
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للصور: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_videos_"): # Handler for toggle watermark videos
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_watermark_media_type(event, task_id, 'videos')
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للفيديو: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_documents_"): # Handler for toggle watermark documents
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_watermark_media_type(event, task_id, 'documents')
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للمستندات: {e}, data='{data}', parts={parts}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_inline_block_"): # Handler for toggle inline button block
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_inline_button_block(event, task_id)
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

    async def handle_message(self, event):
        """Handle text messages"""
        # Skip if it's a command
        if event.text.startswith('/'):
            return

        user_id = event.sender_id

        # Check if user is in authentication or task creation process
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
            elif state == 'waiting_watermark_text': # Handle setting watermark text
                task_id = int(data)
                await self.handle_watermark_text_input(event, task_id, event.text)
                return
            elif state == 'waiting_watermark_image': # Handle setting watermark image
                task_id = int(data)
                await self.handle_watermark_image_input(event, task_id)
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


    async def show_main_menu(self, event):
        """Show main menu"""
        buttons = [
            [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
            [Button.inline("⚙️ الإعدادات", b"settings")],
            [Button.inline("ℹ️ حول البوت", b"about")]
        ]

        await event.edit(
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

            await event.edit(status_message, buttons=buttons)

        except Exception as e:
            logger.error(f"خطأ في فحص حالة UserBot للمستخدم {user_id}: {e}")
            await event.edit(
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

    # ===== Watermark Settings =====
    
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
        position = watermark_settings.get('position', 'bottom-right')
        position_map = {
            'top-left': 'أعلى يسار',
            'top-right': 'أعلى يمين', 
            'bottom-left': 'أسفل يسار',
            'bottom-right': 'أسفل يمين',
            'center': 'الوسط'
        }
        position_display = position_map.get(position, position)

        buttons = [
            [Button.inline(toggle_text, f"toggle_watermark_{task_id}")],
            [Button.inline("⚙️ إعدادات العلامة", f"watermark_config_{task_id}")],
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
            f"• الحجم: {watermark_settings.get('size_percentage', 10)}%\n"
            f"• الشفافية: {watermark_settings.get('opacity', 70)}%\n"
            f"• حجم الخط: {watermark_settings.get('font_size', 24)}px\n\n"
            f"🏷️ **الوظيفة**: إضافة علامة مائية نصية أو صورة على الوسائط المرسلة لحماية الحقوق\n\n"
            f"📝 **نص العلامة**: {watermark_settings.get('watermark_text', 'غير محدد')[:30]}{'...' if len(watermark_settings.get('watermark_text', '')) > 30 else ''}\n"
            f"🖼️ **صورة العلامة**: {'محددة' if watermark_settings.get('watermark_image_path') else 'غير محددة'}",
            buttons=buttons
        )

    async def toggle_watermark(self, event, task_id):
        """Toggle watermark status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Toggle watermark
        new_status = self.db.toggle_watermark(task_id)
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        
        await event.answer(f"✅ {status_text} العلامة المائية")
        await self.show_watermark_settings(event, task_id)

    async def show_watermark_config(self, event, task_id):
        """Show watermark configuration options"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        buttons = [
            [Button.inline("📝 تعديل النص", f"watermark_text_{task_id}")],
            [Button.inline("🖼️ رفع صورة", f"watermark_image_{task_id}")],
            [Button.inline("📍 تغيير الموقع", f"watermark_position_{task_id}")],
            [Button.inline("🎨 إعدادات المظهر", f"watermark_appearance_{task_id}")],
            [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]
        ]

        await event.edit(
            f"⚙️ تكوين العلامة المائية - المهمة #{task_id}\n\n"
            f"🔧 **خيارات التكوين المتاحة:**\n\n"
            f"📝 **تعديل النص**: تحديد النص المراد إظهاره كعلامة مائية\n"
            f"🖼️ **رفع صورة**: استخدام صورة كعلامة مائية (PNG مفضل)\n"
            f"📍 **تغيير الموقع**: اختيار مكان العلامة على الوسائط\n"
            f"🎨 **إعدادات المظهر**: تخصيص الحجم والشفافية واللون\n\n"
            f"💡 **نصيحة**: يُفضل استخدام صور PNG شفافة للحصول على أفضل نتيجة",
            buttons=buttons
        )

    async def show_watermark_media_settings(self, event, task_id):
        """Show watermark media type settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Get current settings
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        photos_enabled = watermark_settings.get('apply_to_photos', True)
        videos_enabled = watermark_settings.get('apply_to_videos', True)
        documents_enabled = watermark_settings.get('apply_to_documents', False)
        
        photos_text = "✅ الصور" if photos_enabled else "❌ الصور"
        videos_text = "✅ الفيديوهات" if videos_enabled else "❌ الفيديوهات"
        documents_text = "✅ المستندات" if documents_enabled else "❌ المستندات"

        buttons = [
            [Button.inline(photos_text, f"toggle_watermark_photos_{task_id}")],
            [Button.inline(videos_text, f"toggle_watermark_videos_{task_id}")],
            [Button.inline(documents_text, f"toggle_watermark_documents_{task_id}")],
            [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]
        ]

        await event.edit(
            f"📱 اختيار الوسائط للعلامة المائية - المهمة #{task_id}\n\n"
            f"📋 **حدد أنواع الوسائط التي تريد تطبيق العلامة المائية عليها:**\n\n"
            f"📷 **الصور**: JPG, PNG, WebP وغيرها\n"
            f"🎥 **الفيديوهات**: MP4, AVI, MOV وغيرها\n"
            f"📄 **المستندات**: ملفات الصور في شكل مستندات\n\n"
            f"⚠️ **ملاحظة**: معالجة الفيديوهات قد تستغرق وقتاً أطول\n\n"
            f"✅ = مفعل  ❌ = معطل",
            buttons=buttons
        )

    async def toggle_watermark_media_type(self, event, task_id, media_type):
        """Toggle watermark application for specific media type"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Toggle media type setting
        field_map = {
            'photos': 'apply_to_photos',
            'videos': 'apply_to_videos', 
            'documents': 'apply_to_documents'
        }
        
        field_name = field_map.get(media_type)
        if not field_name:
            await event.answer("❌ نوع وسائط غير صالح")
            return

        new_status = self.db.toggle_watermark_media_type(task_id, field_name)
        
        media_names = {
            'photos': 'الصور',
            'videos': 'الفيديوهات',
            'documents': 'المستندات'
        }
        
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        media_name = media_names.get(media_type, media_type)
        
        await event.answer(f"✅ {status_text} العلامة المائية لـ{media_name}")
        await self.show_watermark_media_settings(event, task_id)

    async def start_set_watermark_text(self, event, task_id):
        """Start setting watermark text"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_watermark_text', str(task_id))
        
        # Get current text
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_text = watermark_settings.get('watermark_text', '')

        await event.edit(
            f"📝 تعديل نص العلامة المائية - المهمة #{task_id}\n\n"
            f"🏷️ **النص الحالي**: {current_text if current_text else 'غير محدد'}\n\n"
            f"✍️ أرسل النص الجديد للعلامة المائية:\n\n"
            f"💡 **أمثلة على النصوص:**\n"
            f"• @channelname\n"
            f"• حقوق الطبع محفوظة\n"
            f"• تليجرام: @username\n"
            f"• موقعنا: example.com\n\n"
            f"❌ أرسل 'إلغاء' للخروج",
            buttons=[[Button.inline("❌ إلغاء", f"watermark_config_{task_id}")]]
        )

    async def start_set_watermark_image(self, event, task_id):
        """Start setting watermark image"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_watermark_image', str(task_id))

        await event.edit(
            f"🖼️ رفع صورة العلامة المائية - المهمة #{task_id}\n\n"
            f"📤 **أرسل الصورة الآن:**\n\n"
            f"✅ **متطلبات الصورة:**\n"
            f"• صيغة PNG مفضلة (للشفافية)\n"
            f"• حجم مناسب (لا يزيد عن 5MB)\n"
            f"• خلفية شفافة للحصول على أفضل نتيجة\n"
            f"• أبعاد مربعة أو مستطيلة\n\n"
            f"💡 **نصيحة**: استخدم صور PNG بخلفية شفافة\n\n"
            f"📎 **هام**: أرسل الصورة كملف (Document) وليس كصورة عادية\n\n"
            f"❌ أرسل 'إلغاء' للخروج",
            buttons=[[Button.inline("❌ إلغاء", f"watermark_config_{task_id}")]]
        )

    async def show_watermark_position_settings(self, event, task_id):
        """Show watermark position settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Get current position
        watermark_settings = self.db.get_watermark_settings(task_id)
        current_position = watermark_settings.get('position', 'bottom-right')

        positions = [
            ('top-left', 'أعلى يسار', '↖️'),
            ('top-right', 'أعلى يمين', '↗️'),
            ('center', 'الوسط', '🎯'),
            ('bottom-left', 'أسفل يسار', '↙️'),
            ('bottom-right', 'أسفل يمين', '↘️')
        ]

        buttons = []
        for pos_code, pos_name, emoji in positions:
            status = " ✅" if pos_code == current_position else ""
            buttons.append([Button.inline(f"{emoji} {pos_name}{status}", f"set_watermark_position_{task_id}_{pos_code}")])

        buttons.append([Button.inline("🔙 عودة للتكوين", f"watermark_config_{task_id}")])

        await event.edit(
            f"📍 تحديد موقع العلامة المائية - المهمة #{task_id}\n\n"
            f"🎯 **الموقع الحالي**: {dict(positions)[current_position]}\n\n"
            f"📋 **اختر الموقع الجديد**:\n\n"
            f"💡 **نصيحة**: الزاوية اليمنى السفلى هي الأكثر شيوعاً",
            buttons=buttons
        )

    async def show_watermark_appearance_settings(self, event, task_id):
        """Show watermark appearance settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Get current settings
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        buttons = [
            [Button.inline("📏 تعديل الحجم", f"edit_watermark_size_{task_id}")],
            [Button.inline("🔍 تعديل الشفافية", f"edit_watermark_opacity_{task_id}")],
            [Button.inline("🖋️ تعديل حجم الخط", f"edit_watermark_font_size_{task_id}")],
            [Button.inline("🎨 تعديل اللون", f"edit_watermark_color_{task_id}")],
            [Button.inline("🔙 عودة للتكوين", f"watermark_config_{task_id}")]
        ]

        await event.edit(
            f"🎨 إعدادات مظهر العلامة المائية - المهمة #{task_id}\n\n"
            f"🔧 **الإعدادات الحالية:**\n"
            f"• الحجم: {watermark_settings.get('size_percentage', 10)}%\n"
            f"• الشفافية: {watermark_settings.get('opacity', 70)}%\n"
            f"• حجم الخط: {watermark_settings.get('font_size', 24)}px\n"
            f"• اللون: {watermark_settings.get('text_color', '#FFFFFF')}\n\n"
            f"⚙️ **اختر الإعداد للتعديل**:",
            buttons=buttons
        )

    async def set_watermark_position(self, event, task_id, position):
        """Set watermark position"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Update position in database
        success = self.db.update_watermark_settings(task_id, position=position)
        
        if success:
            position_names = {
                'top-left': 'أعلى يسار',
                'top-right': 'أعلى يمين',
                'center': 'الوسط',
                'bottom-left': 'أسفل يسار',
                'bottom-right': 'أسفل يمين'
            }
            position_name = position_names.get(position, position)
            await event.answer(f"✅ تم تحديث موقع العلامة المائية إلى: {position_name}")
            await self.show_watermark_position_settings(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث الموقع")

    async def handle_watermark_text_input(self, event, task_id, text):
        """Handle watermark text input"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        # Check if user wants to cancel
        if text.lower() in ['إلغاء', 'cancel']:
            await event.respond("❌ تم إلغاء تعديل النص")
            await self.show_watermark_config(event, task_id)
            return
        
        # Update text in database
        success = self.db.update_watermark_settings(task_id, watermark_text=text, watermark_type='text')
        
        if success:
            await event.respond(f"✅ تم تحديث نص العلامة المائية: {text[:50]}{'...' if len(text) > 50 else ''}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            await self.show_watermark_config(event, task_id)
        else:
            await event.respond("❌ فشل في تحديث النص")

    async def handle_watermark_image_input(self, event, task_id):
        """Handle watermark image upload"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        try:
            # Check if it's a document (file)
            if event.message.document:
                file = event.message.document
                
                # Check file size (max 5MB)
                if file.size > 5 * 1024 * 1024:
                    await event.respond("❌ حجم الملف كبير جداً. الحد الأقصى 5MB")
                    return
                
                # Check file type
                file_name = getattr(file, 'attributes', [{}])[0].get('file_name', '') if hasattr(file, 'attributes') else ''
                if not file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                    await event.respond("❌ يجب أن تكون الصورة بصيغة PNG, JPG, JPEG أو WebP")
                    return
                
                # Download file
                download_path = await event.download_media(file=file, path="watermark_images/")
                
                if download_path:
                    # Update image path in database
                    success = self.db.update_watermark_settings(task_id, watermark_image_path=download_path, watermark_type='image')
                    
                    if success:
                        await event.respond(f"✅ تم رفع صورة العلامة المائية بنجاح\n📁 المسار: {download_path}")
                        
                        # Force refresh UserBot tasks
                        await self._refresh_userbot_tasks(user_id)
                        
                        await self.show_watermark_config(event, task_id)
                    else:
                        await event.respond("❌ فشل في حفظ مسار الصورة")
                else:
                    await event.respond("❌ فشل في تحميل الصورة")
                    
            elif event.message.photo:
                await event.respond("❌ يرجى إرسال الصورة كملف (Document) وليس كصورة عادية للحصول على جودة أفضل")
            else:
                await event.respond("❌ يرجى إرسال صورة صالحة أو 'إلغاء' للخروج")
                
        except Exception as e:
            logger.error(f"خطأ في معالجة صورة العلامة المائية: {e}")
            await event.respond("❌ حدث خطأ في معالجة الصورة")
    
    async def show_day_filters(self, event, task_id):
        """Show day filters management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get advanced filters settings and day filters
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        day_filters = self.db.get_day_filters(task_id)
        
        # Create status display
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['day_filter_enabled'] else "🔴 غير مُفَعَّل"
        
        # Create day buttons
        day_buttons = []
        for day in day_filters:
            status = "✅" if day['is_allowed'] else "❌"
            day_buttons.append([Button.inline(f"{status} {day['day_name']}", f"toggle_day_{task_id}_{day['day_number']}")])
        
        # Add control buttons
        control_buttons = [
            [Button.inline("✅ تحديد الكل", f"select_all_days_{task_id}"), 
             Button.inline("❌ إلغاء تحديد الكل", f"deselect_all_days_{task_id}")],
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_day_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        buttons = day_buttons + control_buttons
        
        await event.edit(
            f"📅 فلتر الأيام: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n\n"
            f"🗓️ الأيام المسموحة للتوجيه:\n"
            f"✅ = مسموح | ❌ = محظور\n\n"
            f"💡 ملاحظة: عند تفعيل الفلتر، سيتم توجيه الرسائل فقط في الأيام المحددة بعلامة ✅",
            buttons=buttons
        )
    
    async def toggle_day_filter(self, event, task_id, day_number):
        """Toggle day filter for specific day"""
        user_id = event.sender_id
        
        # Get current day filter status
        day_filters = self.db.get_day_filters(task_id)
        current_status = None
        
        for day in day_filters:
            if day['day_number'] == day_number:
                current_status = day['is_allowed']
                break
        
        if current_status is None:
            current_status = True  # Default is allowed
            
        # Toggle the status
        new_status = not current_status
        self.db.set_day_filter(task_id, day_number, new_status)
        
        status_text = "مسموح" if new_status else "محظور"
        day_names = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
        day_name = day_names[day_number] if day_number < len(day_names) else f"يوم {day_number}"
        
        await event.answer(f"✅ تم تعديل {day_name}: {status_text}")
        await self.show_day_filters(event, task_id)
    
    async def select_all_days(self, event, task_id, select_all):
        """Select or deselect all days"""
        user_id = event.sender_id
        
        self.db.set_all_day_filters(task_id, select_all)
        
        status_text = "تحديد" if select_all else "إلغاء تحديد"
        await event.answer(f"✅ تم {status_text} جميع الأيام")
        await self.show_day_filters(event, task_id)
    
    async def show_working_hours_filter(self, event, task_id):
        """Show working hours filter management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        working_hours = self.db.get_working_hours(task_id)
        
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['working_hours_enabled'] else "🔴 غير مُفَعَّل"
        
        if working_hours:
            start_time = f"{working_hours['start_hour']:02d}:{working_hours['start_minute']:02d}"
            end_time = f"{working_hours['end_hour']:02d}:{working_hours['end_minute']:02d}"
            time_display = f"من {start_time} إلى {end_time}"
        else:
            time_display = "غير محدد (24 ساعة)"
            
        buttons = [
            [Button.inline("⏰ تعديل ساعات العمل", f"set_working_hours_{task_id}")],
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_working_hours_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"⏰ فلتر ساعات العمل: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n"
            f"🕐 ساعات التوجيه: {time_display}\n\n"
            f"💡 ملاحظة: عند تفعيل هذا الفلتر، سيتم توجيه الرسائل فقط خلال الساعات المحددة",
            buttons=buttons
        )
    
    async def show_language_filters(self, event, task_id):
        """Show language filters management with allow/block modes"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        language_data = self.db.get_language_filters(task_id)
        
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['language_filter_enabled'] else "🔴 غير مُفَعَّل"
        filter_mode = language_data['mode']  # 'allow' or 'block'
        languages = language_data['languages']
        
        # Mode display
        mode_text = "وضع السماح" if filter_mode == 'allow' else "وضع الحظر"
        mode_description = "السماح للغات المحددة فقط" if filter_mode == 'allow' else "حظر اللغات المحددة"
        mode_emoji = "✅" if filter_mode == 'allow' else "🚫"
        
        # Create language buttons
        lang_buttons = []
        if languages:
            for lang in languages:
                # In allow mode: selected = allowed, in block mode: selected = blocked
                if filter_mode == 'allow':
                    status = "✅" if lang['is_allowed'] else "⚪"
                else:
                    status = "🚫" if lang['is_allowed'] else "⚪"
                lang_buttons.append([Button.inline(f"{status} {lang['language_name']}", f"toggle_lang_selection_{task_id}_{lang['language_code']}")])
        
        # Quick add language buttons
        common_languages = [
            ('ar', 'العربية'),
            ('en', 'English'),
            ('fr', 'Français'),
            ('es', 'Español'),
            ('de', 'Deutsch'),
            ('ru', 'Русский'),
            ('tr', 'Türkçe'),
            ('fa', 'فارسی'),
            ('ur', 'اردو'),
            ('hi', 'हिन्दी')
        ]
        
        # Filter out already added languages
        existing_codes = [lang['language_code'] for lang in languages]
        available_languages = [(code, name) for code, name in common_languages if code not in existing_codes]
        
        # Add quick language selection buttons (2 per row)
        quick_lang_buttons = []
        for i in range(0, len(available_languages), 2):
            row = []
            for j in range(2):
                if i + j < len(available_languages):
                    code, name = available_languages[i + j]
                    row.append(Button.inline(f"➕ {name}", f"quick_add_lang_{task_id}_{code}_{name}"))
            if row:
                quick_lang_buttons.append(row)
        
        # Control buttons
        control_buttons = [
            [Button.inline(f"⚙️ تغيير إلى: {mode_emoji} {mode_text}", f"toggle_language_mode_{task_id}")],
            [Button.inline("➕ إضافة لغة مخصصة", f"add_custom_language_{task_id}")],
            [Button.inline("🗑️ مسح جميع اللغات", f"clear_all_languages_{task_id}")] if languages else [],
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_language_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        # Remove empty lists
        control_buttons = [btn for btn in control_buttons if btn]
        
        # Combine all buttons
        buttons = lang_buttons + quick_lang_buttons + control_buttons
        
        # Message text
        message = (
            f"🌍 فلتر اللغة: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n"
            f"⚙️ الوضع الحالي: {mode_emoji} {mode_text}\n"
            f"📝 الوصف: {mode_description}\n\n"
        )
        
        if languages:
            message += f"🗣️ اللغات المُكونة:\n"
            if filter_mode == 'allow':
                message += f"✅ = مُختارة للسماح | ⚪ = غير مُختارة\n\n"
            else:
                message += f"🚫 = مُختارة للحظر | ⚪ = غير مُختارة\n\n"
        else:
            message += f"📝 لا توجد لغات محددة\n\n"
        
        if available_languages:
            message += f"➕ اللغات الشائعة المتاحة:\n"
        
        message += (
            f"\n💡 الأوضاع:\n"
            f"• ✅ وضع السماح: توجيه الرسائل باللغات المحددة فقط\n"
            f"• 🚫 وضع الحظر: منع توجيه الرسائل باللغات المحددة"
        )
        
        await event.edit(message, buttons=buttons)
    
    async def quick_add_language(self, event, task_id, language_code, language_name):
        """Quick add a language to filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Add language filter (default to allowed)
        success = self.db.add_language_filter(task_id, language_code, language_name, True)
        
        if success:
            await event.answer(f"✅ تم إضافة {language_name}")
            await self.show_language_filters(event, task_id)
        else:
            await event.answer(f"❌ فشل في إضافة {language_name}")
    
    async def toggle_language_selection(self, event, task_id, language_code):
        """Toggle language selection status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Toggle language selection
        success = self.db.toggle_language_filter(task_id, language_code)
        
        if success:
            await event.answer("✅ تم تحديث اللغة")
            await self.show_language_filters(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث اللغة")
    
    async def toggle_language_mode(self, event, task_id):
        """Toggle between allow and block mode"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Get current mode and toggle
        current_mode = self.db.get_language_filter_mode(task_id)
        new_mode = 'block' if current_mode == 'allow' else 'allow'
        
        success = self.db.set_language_filter_mode(task_id, new_mode)
        
        if success:
            mode_text = "وضع الحظر" if new_mode == 'block' else "وضع السماح"
            await event.answer(f"✅ تم التبديل إلى {mode_text}")
            await self.show_language_filters(event, task_id)
        else:
            await event.answer("❌ فشل في تبديل الوضع")
    
    async def clear_all_languages(self, event, task_id):
        """Clear all language filters"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Clear all languages (you'll need to add this method to database)
        language_data = self.db.get_language_filters(task_id)
        languages = language_data['languages']
        
        cleared_count = 0
        for lang in languages:
            if self.db.remove_language_filter(task_id, lang['language_code']):
                cleared_count += 1
        
        if cleared_count > 0:
            await event.answer(f"✅ تم مسح {cleared_count} لغة")
            await self.show_language_filters(event, task_id)
        else:
            await event.answer("❌ لا توجد لغات لمسحها")
    
    async def show_admin_filters(self, event, task_id):
        """Show admin filters management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['admin_filter_enabled'] else "🔴 غير مُفَعَّل"
        
        # Show admin list button instead of individual admins
        admin_buttons = [
            [Button.inline("👥 قائمة المشرفين", f"admin_list_{task_id}")]
        ]
        
        # Add control buttons
        control_buttons = [
            [Button.inline("👨‍💼 تحديث قائمة المشرفين", f"refresh_admins_{task_id}")],
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_admin_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        buttons = admin_buttons + control_buttons
        
        await event.edit(
            f"👨‍💼 فلتر المشرفين: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n\n"
            f"👥 إدارة المشرفين:\n"
            f"✅ = مسموح | ❌ = محظور\n\n"
            f"💡 ملاحظة: عند تفعيل هذا الفلتر، سيتم توجيه رسائل المشرفين المحددين فقط",
            buttons=buttons
        )
    
    async def show_admin_list(self, event, task_id):
        """Show list of source channels for admin management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get source channels
        source_chats = self.db.get_task_sources(task_id)
        
        if not source_chats:
            # Try to get from legacy data
            if task.get('source_chat_id'):
                source_chats = [{
                    'chat_id': task['source_chat_id'],
                    'chat_name': task['source_chat_name'] or 'قناة مصدر'
                }]
        
        source_buttons = []
        if source_chats:
            for source in source_chats:
                chat_id = source['chat_id']
                chat_name = source.get('chat_name', f'القناة {chat_id}')
                source_buttons.append([Button.inline(f"📢 {chat_name} ({chat_id})", f"source_admins_{task_id}_{chat_id}")])
        else:
            source_buttons.append([Button.inline("📢 لا توجد قنوات مصدر", "none")])
        
        # Control buttons
        control_buttons = [
            [Button.inline("🔙 رجوع لفلتر المشرفين", f"admin_filters_{task_id}")]
        ]
        
        buttons = source_buttons + control_buttons
        
        await event.edit(
            f"📋 قائمة المشرفين: {task_name}\n\n"
            f"📢 قنوات المصدر المرتبطة بالمهمة:\n"
            f"اختر قناة لعرض مشرفيها\n\n"
            f"💡 ملاحظة: يمكنك إدارة المشرفين لكل قناة بشكل منفصل",
            buttons=buttons
        )
    
    async def show_source_admins(self, event, task_id, source_chat_id):
        """Show admins for a specific source channel"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get admins for this source
        admin_filters = self.db.get_admin_filters_for_source(task_id, source_chat_id)
        
        admin_buttons = []
        if admin_filters:
            for admin in admin_filters:
                status = "✅" if admin['is_allowed'] else "❌"
                name = admin['admin_first_name'] or admin['admin_username'] or f"المستخدم {admin['admin_user_id']}"
                admin_buttons.append([Button.inline(f"{status} {name}", f"toggle_admin_{task_id}_{admin['admin_user_id']}_{source_chat_id}")])
        
        # Control buttons - only one refresh button
        control_buttons = [
            [Button.inline("🔄 تحديث قائمة المشرفين", f"refresh_source_admins_{task_id}_{source_chat_id}")],
            [Button.inline("🔙 رجوع لقائمة القنوات", f"admin_list_{task_id}")]
        ]
        
        buttons = admin_buttons + control_buttons
        
        status_text = f"👥 قائمة المشرفين:\n✅ = مسموح | ❌ = محظور" if admin_filters else f"📋 لم يتم جلب المشرفين بعد\n🔄 اضغط 'تحديث قائمة المشرفين' للحصول على قائمة المشرفين من تليجرام"
        
        await event.edit(
            f"👨‍💼 مشرفو القناة: {source_chat_id}\n"
            f"🔗 المهمة: {task_name}\n\n"
            f"{status_text}\n\n"
            f"💡 بعد جلب المشرفين، يمكنك اختيار من يُسمح له بإرسال الرسائل",
            buttons=buttons
        )
    
    async def toggle_admin(self, event, task_id, admin_user_id, source_chat_id=None):
        """Toggle admin filter status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Toggle admin status
        success = self.db.toggle_admin_filter(task_id, admin_user_id)
        
        if success:
            await event.answer("✅ تم تغيير حالة المشرف")
            
            # Refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Stay in the same source admin view if source_chat_id is provided
            if source_chat_id:
                await self.show_source_admins(event, task_id, source_chat_id)
            else:
                # Fallback to first source if no specific source provided
                sources = self.db.get_task_sources(task_id)
                if sources:
                    first_source = sources[0]['chat_id']
                    await self.show_source_admins(event, task_id, first_source)
                else:
                    await self.show_admin_filters(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير حالة المشرف")
    
    async def refresh_source_admin_list(self, event, task_id, source_chat_id):
        """Refresh admin list for a specific source channel using Bot API"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        await event.answer("🔄 جاري تحديث مشرفي هذه القناة...")
        
        try:
            # Use bot API to fetch admins
            admin_count = await self.fetch_channel_admins_with_bot(task_id, source_chat_id)
            
            if admin_count > 0:
                await event.edit(f"✅ تم تحديث {admin_count} مشرف للقناة")
                # Add small delay before showing results
                await asyncio.sleep(0.3)
                await self.show_source_admins(event, task_id, source_chat_id)
            elif admin_count == 0:
                await event.edit("✅ لا يوجد مشرفون في هذه القناة")
                await asyncio.sleep(0.3)
                await self.show_source_admins(event, task_id, source_chat_id)
            else:
                await event.edit("❌ فشل في الحصول على المشرفين. تأكد من أن البوت عضو في القناة وله صلاحيات كافية")
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث مشرفي القناة {source_chat_id}: {e}")
            await event.edit("❌ حدث خطأ أثناء تحديث مشرفي القناة. جرب مرة أخرى")

    async def fetch_channel_admins_with_bot(self, task_id: int, channel_id: str) -> int:
        """Fetch channel admins using Bot API instead of UserBot"""
        try:
            # Get previous permissions before clearing
            previous_permissions = self.db.get_admin_previous_permissions(task_id)
            logger.info(f"💾 حفظ الأذونات السابقة للمهمة {task_id}: {previous_permissions}")
            
            # Clear existing admins for this source first
            self.db.clear_admin_filters_for_source(task_id, channel_id)
            
            # Convert channel_id to proper format
            try:
                if channel_id.startswith('-100'):
                    # Convert to proper channel ID format
                    channel_entity = int(channel_id)
                elif channel_id.startswith('@'):
                    # Username format
                    channel_entity = channel_id
                else:
                    # Try to get entity by ID
                    channel_entity = int(channel_id) if channel_id.lstrip('-').isdigit() else channel_id
            except ValueError:
                # If conversion fails, use as string
                channel_entity = channel_id
            
            # Get the channel entity first
            try:
                channel = await self.bot.get_entity(channel_entity)
            except Exception as e:
                logger.error(f"فشل في الحصول على معلومات القناة {channel_id}: {e}")
                raise e
            
            # Get chat administrators using proper method
            try:
                from telethon.tl.functions.channels import GetParticipantsRequest
                from telethon.tl.types import ChannelParticipantsAdmins
                
                # Request admins with proper parameters
                participants = await self.bot(GetParticipantsRequest(
                    channel=channel,
                    filter=ChannelParticipantsAdmins(),
                    offset=0,
                    limit=100,
                    hash=0
                ))
                
                admin_count = 0
                for participant in participants.participants:
                    try:
                        # Find user info from participants.users
                        user = next((u for u in participants.users if u.id == participant.user_id), None)
                        if not user:
                            continue
                            
                        user_id = user.id
                        username = getattr(user, 'username', '') or ''
                        first_name = getattr(user, 'first_name', '') or f'مشرف {user_id}'
                        
                        # Add admin to database with previous permissions
                        self.db.add_admin_filter_with_previous_permission(
                            task_id=task_id,
                            admin_user_id=user_id,
                            admin_username=username,
                            admin_first_name=first_name,
                            previous_permissions=previous_permissions
                        )
                        admin_count += 1
                        
                    except Exception as e:
                        logger.error(f"خطأ في إضافة المشرف {participant}: {e}")
                        continue
                
                logger.info(f"✅ تم إضافة {admin_count} مشرف للقناة {channel_id} باستخدام Bot API")
                return admin_count
                
            except Exception as api_error:
                logger.error(f"فشل استدعاء GetParticipantsRequest: {api_error}")
                raise api_error
            
        except Exception as e:
            logger.error(f"خطأ في جلب المشرفين باستخدام Bot API: {e}")
            # Fallback: Add bot owner as admin
            try:
                # Get the first user from the task to use as owner
                task = self.db.get_task_with_sources_targets(task_id, None)
                if task:
                    owner_id = task.get('user_id')
                    if owner_id:
                        self.db.add_admin_filter(
                            task_id=task_id,
                            admin_user_id=owner_id,
                            admin_username="owner",
                            admin_first_name="المالك",
                            is_allowed=True
                        )
                        logger.info(f"✅ تم إضافة المالك كمشرف للقناة {channel_id}")
                        return 1
            except Exception as fallback_error:
                logger.error(f"خطأ في إضافة المالك كمشرف: {fallback_error}")
            
            return -1
    
    async def show_duplicate_filter(self, event, task_id):
        """Show duplicate filter management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        duplicate_settings = self.db.get_duplicate_settings(task_id)
        
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['duplicate_filter_enabled'] else "🔴 غير مُفَعَّل"
        
        text_check = "✅" if duplicate_settings['check_text_similarity'] else "❌"
        media_check = "✅" if duplicate_settings['check_media_similarity'] else "❌"
        threshold = duplicate_settings['similarity_threshold'] * 100
        time_window = duplicate_settings['time_window_hours']
        
        buttons = [
            [Button.inline("⚙️ تعديل إعدادات التكرار", f"duplicate_settings_{task_id}")],
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_duplicate_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"🔄 فلتر التكرار: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n\n"
            f"⚙️ الإعدادات الحالية:\n"
            f"• {text_check} فحص تشابه النص\n"
            f"• {media_check} فحص تشابه الوسائط\n"
            f"• نسبة التشابه: {threshold:.0f}%\n"
            f"• النافذة الزمنية: {time_window} ساعة\n\n"
            f"💡 ملاحظة: عند تفعيل هذا الفلتر، سيتم منع توجيه الرسائل المكررة خلال النافذة الزمنية المحددة",
            buttons=buttons
        )
    
    async def show_inline_button_filter(self, event, task_id):
        """Show inline button filter management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        inline_button_setting = self.db.get_inline_button_filter_setting(task_id)
        
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['inline_button_filter_enabled'] else "🔴 غير مُفَعَّل"
        mode_status = "🚫 حظر الرسالة" if inline_button_setting else "🗑️ حذف الأزرار"
        
        buttons = [
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_inline_button_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع: {mode_status}", f"toggle_inline_block_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"🔘 فلتر الأزرار الشفافة: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n"
            f"⚙️ وضع المعالجة: {mode_status}\n\n"
            f"💡 الأوضاع المتاحة:\n"
            f"• 🚫 وضع الحظر: يمنع توجيه الرسائل التي تحتوي على أزرار شفافة\n"
            f"• 🗑️ وضع الحذف: يحذف الأزرار ويوجه الرسالة فقط",
            buttons=buttons
        )
    
    async def show_forwarded_message_filter(self, event, task_id):
        """Show forwarded message filter management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        forwarded_setting = self.db.get_forwarded_message_filter_setting(task_id)
        
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['forwarded_message_filter_enabled'] else "🔴 غير مُفَعَّل"
        mode_status = "🚫 حظر الرسالة" if forwarded_setting else "📋 إرسال كنسخة"
        
        buttons = [
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_forwarded_message_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع: {mode_status}", f"toggle_forwarded_block_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"↗️ فلتر الرسائل المعاد توجيهها: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n"
            f"⚙️ وضع المعالجة: {mode_status}\n\n"
            f"💡 الأوضاع المتاحة:\n"
            f"• 🚫 وضع الحظر: يمنع توجيه الرسائل المعاد توجيهها\n"
            f"• 📋 وضع النسخ: يحذف علامة التوجيه ويرسل الرسالة كنسخة جديدة",
            buttons=buttons
        )
    
    async def toggle_advanced_filter(self, event, task_id, filter_type):
        """Toggle advanced filter on/off"""
        user_id = event.sender_id
        
        # Get current status
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        
        # Map filter types to their column names
        filter_column_map = {
            'day': 'day_filter_enabled',
            'day_filter': 'day_filter_enabled',
            'working_hours': 'working_hours_enabled',
            'language': 'language_filter_enabled', 
            'language_filter': 'language_filter_enabled',
            'admin': 'admin_filter_enabled',
            'admin_filter': 'admin_filter_enabled',
            'duplicate': 'duplicate_filter_enabled',
            'duplicate_filter': 'duplicate_filter_enabled',
            'inline_button': 'inline_button_filter_enabled',
            'inline_button_filter': 'inline_button_filter_enabled',
            'forwarded_message': 'forwarded_message_filter_enabled',
            'forwarded_message_filter': 'forwarded_message_filter_enabled'
        }
        
        column_name = filter_column_map.get(filter_type, f'{filter_type}_enabled')
        current_status = advanced_settings.get(column_name, False)
        new_status = not current_status
        
        # Update the filter
        success = self.db.update_advanced_filter_setting(task_id, filter_type, new_status)
        
        if success:
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
            filter_names = {
                'day': 'فلتر الأيام',
                'day_filter': 'فلتر الأيام',
                'working_hours': 'فلتر ساعات العمل',
                'language': 'فلتر اللغة',
                'language_filter': 'فلتر اللغة',
                'admin': 'فلتر المشرفين',
                'admin_filter': 'فلتر المشرفين',
                'duplicate': 'فلتر التكرار',
                'duplicate_filter': 'فلتر التكرار',
                'inline_button': 'فلتر الأزرار',
                'inline_button_filter': 'فلتر الأزرار',
                'forwarded_message': 'فلتر المعاد توجيهه',
                'forwarded_message_filter': 'فلتر المعاد توجيهه'
            }
            filter_name = filter_names.get(filter_type, f'الفلتر {filter_type}')
            
            await event.answer(f"✅ {status_text} {filter_name}")
            
            # Return to appropriate menu with correct interface refresh
            if filter_type in ['day', 'day_filter']:
                await self.show_day_filters(event, task_id)
            elif filter_type == 'working_hours':
                await self.show_working_hours_filter(event, task_id)
            elif filter_type in ['language', 'language_filter']:
                await self.show_language_filters(event, task_id)
            elif filter_type in ['admin_filter', 'admin']:
                await self.show_admin_filters(event, task_id)
            elif filter_type in ['duplicate', 'duplicate_filter']:
                await self.show_duplicate_filter(event, task_id)
            elif filter_type in ['inline_button', 'inline_button_filter']:
                await self.show_inline_button_filter(event, task_id)
            elif filter_type in ['forwarded_message', 'forwarded_message_filter']:
                await self.show_forwarded_message_filter(event, task_id)
            else:
                await self.show_advanced_filters_menu(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث الفلتر")
    
    async def toggle_inline_button_mode(self, event, task_id):
        """Toggle inline button filter mode between remove and block"""
        user_id = event.sender_id
        
        # Get current setting (True = block, False = remove)
        current_setting = self.db.get_inline_button_filter_setting(task_id)
        new_setting = not current_setting
        
        # Update setting
        success = self.db.set_inline_button_filter(task_id, new_setting)
        
        if success:
            mode_text = "حظر الرسائل" if new_setting else "حذف الأزرار وتوجيه الرسالة"
            await event.answer(f"✅ تم تغيير وضع الفلتر إلى: {mode_text}")
            await self.show_inline_button_filter(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث الإعداد")
    
    async def toggle_forwarded_message_mode(self, event, task_id):
        """Toggle forwarded message filter mode between remove and block"""
        user_id = event.sender_id
        
        # Get current setting (True = block, False = remove forward mark)
        current_setting = self.db.get_forwarded_message_filter_setting(task_id)
        new_setting = not current_setting
        
        # Update setting
        success = self.db.set_forwarded_message_filter(task_id, new_setting)
        
        if success:
            mode_text = "حظر الرسائل المعاد توجيهها" if new_setting else "حذف علامة التوجيه وإرسال كنسخة"
            await event.answer(f"✅ تم تغيير وضع الفلتر إلى: {mode_text}")
            await self.show_forwarded_message_filter(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث الإعداد")

    async def toggle_forwarded_message_block(self, event, task_id):
        """Toggle forwarded message filter mode between block and delete"""
        await self.toggle_forwarded_message_mode(event, task_id)

    async def toggle_inline_button_block(self, event, task_id):
        """Toggle inline button filter mode between block and delete"""  
        await self.toggle_inline_button_mode(event, task_id)

    async def toggle_text_check(self, event, task_id):
        """Toggle text similarity check for duplicate filter"""
        user_id = event.sender_id
        
        # Get current settings
        settings = self.db.get_duplicate_settings(task_id)
        new_status = not settings['check_text_similarity']
        
        # Update setting
        success = self.db.update_duplicate_text_check(task_id, new_status)
        
        if success:
            status_text = "تم تفعيل" if new_status else "تم إلغاء"
            await event.answer(f"✅ {status_text} فحص تشابه النص")
            await self.show_duplicate_settings(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث الإعداد")

    async def toggle_media_check(self, event, task_id):
        """Toggle media similarity check for duplicate filter"""
        user_id = event.sender_id
        
        # Get current settings
        settings = self.db.get_duplicate_settings(task_id)
        new_status = not settings['check_media_similarity']
        
        # Update setting
        success = self.db.update_duplicate_media_check(task_id, new_status)
        
        if success:
            status_text = "تم تفعيل" if new_status else "تم إلغاء"
            await event.answer(f"✅ {status_text} فحص تشابه الوسائط")
            await self.show_duplicate_settings(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث الإعداد")

    async def set_duplicate_threshold(self, event, task_id):
        """Set duplicate filter similarity threshold"""
        user_id = event.sender_id
        
        # Start conversation to get threshold value
        self.user_states[user_id] = {
            'state': 'awaiting_threshold',
            'task_id': task_id,
            'action': 'set_duplicate_threshold'
        }
        
        await event.edit(
            "🎯 أدخل نسبة التشابه المطلوبة (من 1 إلى 100):\n\n"
            "💡 مثال: 85 يعني 85% تشابه\n"
            "⚠️ كلما قل الرقم، كلما زادت الحساسية لاكتشاف التكرار",
            buttons=[
                [Button.inline("❌ إلغاء", f"duplicate_settings_{task_id}")]
            ]
        )

    async def set_duplicate_time_window(self, event, task_id):
        """Set duplicate filter time window"""
        user_id = event.sender_id
        
        # Start conversation to get time window value
        self.user_states[user_id] = {
            'state': 'awaiting_time_window',
            'task_id': task_id,
            'action': 'set_duplicate_time_window'
        }
        
        await event.edit(
            "⏰ أدخل النافذة الزمنية بالساعات (من 1 إلى 168 ساعة):\n\n"
            "💡 مثال: 24 يعني 24 ساعة (يوم واحد)\n"
            "⚠️ الرسائل المتشابهة خلال هذه الفترة سيتم اعتبارها مكررة",
            buttons=[
                [Button.inline("❌ إلغاء", f"duplicate_settings_{task_id}")]
            ]
        )

    async def handle_threshold_input(self, event, task_id, text):
        """Handle threshold input for duplicate filter"""
        user_id = event.sender_id
        
        try:
            threshold = float(text.strip())
            
            if threshold < 1 or threshold > 100:
                await event.respond("❌ النسبة يجب أن تكون بين 1 و 100")
                return
                
            # Update setting
            success = self.db.update_duplicate_threshold(task_id, threshold / 100.0)
            
            if success:
                # Clear user state
                if user_id in self.user_states:
                    del self.user_states[user_id]
                    
                await event.respond(f"✅ تم تحديث نسبة التشابه إلى: {threshold}%")
                await self.show_duplicate_settings(event, task_id)
            else:
                await event.respond("❌ فشل في تحديث النسبة")
                
        except ValueError:
            await event.respond("❌ يجب إدخال رقم صحيح\nمثال: 85")
        except Exception as e:
            logger.error(f"خطأ في تعديل نسبة التشابه: {e}")
            await event.respond("❌ حدث خطأ في تحديث النسبة")

    async def handle_time_window_input(self, event, task_id, text):
        """Handle time window input for duplicate filter"""
        user_id = event.sender_id
        
        try:
            time_window = int(text.strip())
            
            if time_window < 1 or time_window > 168:
                await event.respond("❌ النافذة الزمنية يجب أن تكون بين 1 و 168 ساعة")
                return
                
            # Update setting
            success = self.db.update_duplicate_time_window(task_id, time_window)
            
            if success:
                # Clear user state
                if user_id in self.user_states:
                    del self.user_states[user_id]
                    
                await event.respond(f"✅ تم تحديث النافذة الزمنية إلى: {time_window} ساعة")
                await self.show_duplicate_settings(event, task_id)
            else:
                await event.respond("❌ فشل في تحديث النافذة الزمنية")
                
        except ValueError:
            await event.respond("❌ يجب إدخال رقم صحيح\nمثال: 24")
        except Exception as e:
            logger.error(f"خطأ في تعديل النافذة الزمنية: {e}")
            await event.respond("❌ حدث خطأ في تحديث النافذة الزمنية")
    
    async def show_working_hours_filter(self, event, task_id):
        """Show working hours filter configuration"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get advanced filter status
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        enabled = advanced_settings.get('working_hours_enabled', False)
        
        # Get working hours configuration
        working_hours = self.db.get_working_hours(task_id)
        
        if not working_hours:
            # Initialize default configuration
            self.db.set_working_hours_mode(task_id, 'work_hours', 0)
            self.db.initialize_working_hours_schedule(task_id)
            working_hours = self.db.get_working_hours(task_id)
        
        mode = working_hours.get('mode', 'work_hours')
        enabled_hours = working_hours.get('enabled_hours', [])
        
        status_text = "🟢 مُفَعَّل" if enabled else "🔴 مُعطل"
        mode_text = "ساعات العمل" if mode == 'work_hours' else "ساعات النوم"
        
        enabled_count = len(enabled_hours)
        
        message = f"⏰ **فلتر ساعات العمل: {task.get('task_name', 'مهمة بدون اسم')}**\n\n"
        message += f"📊 **الحالة**: {status_text}\n"
        message += f"⚙️ **الوضع**: {mode_text}\n"
        message += f"🕐 **الساعات المُحددة**: {enabled_count}/24\n\n"
        
        if mode == 'work_hours':
            message += "🟢 **وضع ساعات العمل**: البوت يعمل فقط في الساعات المُحددة\n"
        else:
            message += "🔴 **وضع ساعات النوم**: البوت يتوقف في الساعات المُحددة ويعمل في الباقي\n"
        
        message += f"\n💡 **الساعات المُحددة حالياً**: "
        if enabled_hours:
            hour_ranges = self._format_hour_ranges(enabled_hours)
            message += hour_ranges
        else:
            message += "لا توجد ساعات محددة"

        # Create buttons
        buttons = [
            [Button.inline(f"{'🔴 إيقاف' if enabled else '🟢 تفعيل'}", f"toggle_working_hours_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع: {mode_text}", f"toggle_working_hours_mode_{task_id}")],
            [Button.inline("🕐 جدولة الساعات", f"schedule_working_hours_{task_id}")],
            [Button.inline("✅ تحديد الكل", f"select_all_hours_{task_id}"),
             Button.inline("❌ إلغاء الكل", f"clear_all_hours_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(message, buttons=buttons)

    def _format_hour_ranges(self, hours):
        """Format list of hours into readable ranges"""
        if not hours:
            return "لا توجد"
            
        hours = sorted(hours)
        ranges = []
        start = hours[0]
        end = hours[0]
        
        for i in range(1, len(hours)):
            if hours[i] == end + 1:
                end = hours[i]
            else:
                if start == end:
                    ranges.append(f"{start:02d}:00")
                else:
                    ranges.append(f"{start:02d}:00-{end:02d}:59")
                start = end = hours[i]
        
        # Add the last range
        if start == end:
            ranges.append(f"{start:02d}:00")
        else:
            ranges.append(f"{start:02d}:00-{end:02d}:59")
            
        return ", ".join(ranges)

    async def schedule_working_hours(self, event, task_id):
        """Show hourly schedule interface"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        working_hours = self.db.get_working_hours(task_id)
        if not working_hours:
            self.db.set_working_hours_mode(task_id, 'work_hours')
            self.db.initialize_working_hours_schedule(task_id)
            working_hours = self.db.get_working_hours(task_id)
            
        schedule = working_hours.get('schedule', {})
        mode = working_hours.get('mode', 'work_hours')
        
        message = f"🕐 **جدولة ساعات العمل: {task.get('task_name', 'مهمة بدون اسم')}**\n\n"
        message += f"⚙️ **الوضع الحالي**: {'ساعات العمل' if mode == 'work_hours' else 'ساعات النوم'}\n\n"
        message += "انقر على الساعة لتفعيلها/تعطيلها:\n\n"
        
        # Create 4 rows of 6 hours each
        buttons = []
        for row in range(4):
            button_row = []
            for col in range(6):
                hour = row * 6 + col
                is_enabled = schedule.get(hour, False)
                emoji = "🟢" if is_enabled else "⚫"
                button_row.append(Button.inline(f"{emoji} {hour:02d}", f"toggle_hour_{task_id}_{hour}"))
            buttons.append(button_row)
        
        # Add control buttons
        buttons.append([
            Button.inline("✅ تحديد الكل", f"select_all_hours_{task_id}"),
            Button.inline("❌ إلغاء الكل", f"clear_all_hours_{task_id}")
        ])
        buttons.append([Button.inline("🔙 رجوع لساعات العمل", f"working_hours_filter_{task_id}")])
        
        # Send/Edit message with error handling
        try:
            await event.edit(message, buttons=buttons)
        except Exception as e:
            if "MessageNotModifiedError" in str(e) or "Content of the message was not modified" in str(e):
                # Message content is the same, just answer the callback
                await event.answer("✅ تم التحديث")
            else:
                logger.error(f"خطأ في تحديث رسالة جدولة ساعات العمل: {e}")
                try:
                    await event.respond(message, buttons=buttons)
                except:
                    await event.answer("❌ خطأ في تحديث الواجهة")

    async def toggle_working_hours(self, event, task_id):
        """Toggle working hours filter on/off"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        success = self.db.toggle_advanced_filter(task_id, 'working_hours')
        if success:
            status = self.db.get_advanced_filters_settings(task_id)
            enabled = status.get('working_hours_enabled', False)
            status_text = "تم تفعيل" if enabled else "تم إيقاف"
            await event.answer(f"✅ {status_text} فلتر ساعات العمل")
            # Refresh the working hours interface to show updated status
            await self.show_working_hours_filter(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير حالة الفلتر")

    async def toggle_working_hours_mode(self, event, task_id):
        """Toggle between work_hours and sleep_hours mode"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        working_hours = self.db.get_working_hours(task_id)
        if not working_hours:
            self.db.set_working_hours_mode(task_id, 'work_hours')
            self.db.initialize_working_hours_schedule(task_id)
            current_mode = 'work_hours'
        else:
            current_mode = working_hours.get('mode', 'work_hours')
        
        new_mode = 'sleep_hours' if current_mode == 'work_hours' else 'work_hours'
        success = self.db.set_working_hours_mode(task_id, new_mode)
        
        if success:
            mode_text = "ساعات النوم" if new_mode == 'sleep_hours' else "ساعات العمل"
            await event.answer(f"✅ تم تغيير الوضع إلى: {mode_text}")
            # Refresh the working hours interface to show updated mode
            await self.show_working_hours_filter(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير الوضع")

    async def toggle_hour(self, event, task_id, hour):
        """Toggle specific hour on/off"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        new_state = self.db.toggle_working_hour(task_id, hour)
        status_text = "تم تفعيل" if new_state else "تم إيقاف"
        await event.answer(f"✅ {status_text} الساعة {hour:02d}:00")
        await self.schedule_working_hours(event, task_id)

    async def select_all_hours(self, event, task_id):
        """Enable all 24 hours"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        success = self.db.set_all_working_hours(task_id, True)
        if success:
            await event.answer("✅ تم تفعيل جميع الساعات")
            await self.schedule_working_hours(event, task_id)
        else:
            await event.answer("❌ فشل في تفعيل الساعات")

    async def clear_all_hours(self, event, task_id):
        """Disable all 24 hours"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        success = self.db.set_all_working_hours(task_id, False)
        if success:
            await event.answer("✅ تم إيقاف جميع الساعات")
            await self.schedule_working_hours(event, task_id)
        else:
            await event.answer("❌ فشل في إيقاف الساعات")

    # Legacy function - keep for backward compatibility
    async def start_set_working_hours(self, event, task_id):
        """Legacy: Start conversation to set working hours"""
        await self.show_working_hours_filter(event, task_id)
    
    async def start_add_language(self, event, task_id):
        """Start conversation to add language filter"""
        await event.edit("🌍 إضافة فلتر لغة\n\nأرسل رمز اللغة (مثال: ar للعربية، en للإنجليزية)\nأو اسم اللغة كاملاً")
        
        # Set conversation state using database system
        user_id = event.sender_id
        self.db.set_conversation_state(user_id, 'add_language', json.dumps({'task_id': task_id}))
    
    async def show_duplicate_settings(self, event, task_id):
        """Show duplicate detection settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_duplicate_settings(task_id)
        
        text_check = "✅ مُفعل" if settings['check_text_similarity'] else "❌ مُعطل"
        media_check = "✅ مُفعل" if settings['check_media_similarity'] else "❌ مُعطل"
        threshold = settings['similarity_threshold'] * 100
        time_window = settings['time_window_hours']
        
        buttons = [
            [Button.inline(f"📝 فحص النص ({text_check})", f"toggle_text_check_{task_id}")],
            [Button.inline(f"🖼️ فحص الوسائط ({media_check})", f"toggle_media_check_{task_id}")],
            [Button.inline(f"📊 نسبة التشابه: {threshold:.0f}%", f"set_threshold_{task_id}")],
            [Button.inline(f"⏱️ النافذة الزمنية: {time_window}ساعة", f"set_time_window_{task_id}")],
            [Button.inline("🔙 رجوع لفلتر التكرار", f"duplicate_filter_{task_id}")]
        ]
        
        await event.edit(
            f"⚙️ إعدادات فلتر التكرار: {task_name}\n\n"
            f"🔍 فحص النص: {text_check}\n"
            f"🖼️ فحص الوسائط: {media_check}\n"
            f"📊 نسبة التشابه: {threshold:.0f}%\n"
            f"⏱️ النافذة الزمنية: {time_window} ساعة\n\n"
            f"💡 النافذة الزمنية تحدد المدة التي يتم فحص التكرار خلالها",
            buttons=buttons
        )
    
    async def refresh_admin_list(self, event, task_id):
        """Refresh the admin list for all source chats"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        await event.answer("🔄 جاري تحديث قائمة المشرفين...")
        
        try:
            # Get all source chats for this task
            source_chats = self.db.get_task_sources(task_id)
            updated_count = 0
            
            for source_chat in source_chats:
                source_id = source_chat['chat_id']
                try:
                    # Access userbot through userbot_instance
                    from userbot_service.userbot import userbot_instance
                    if user_id in userbot_instance.clients:
                        userbot_client = userbot_instance.clients[user_id]
                        
                        # Check if client is connected
                        if userbot_client and userbot_client.is_connected():
                            participants = await userbot_client.get_participants(int(source_id), filter='admin')
                            
                            # Clear existing admins for this task
                            self.db.clear_admin_filters_for_source(task_id, source_id)
                            
                            # Add new admins
                            for participant in participants:
                                self.db.add_admin_filter(task_id, participant.id, 
                                                       participant.username or "", 
                                                       participant.first_name or "", True)
                            updated_count += 1
                        else:
                            logger.error(f"❌ عميل UserBot غير متصل للمستخدم {user_id}")
                        
                except Exception as e:
                    logger.error(f"❌ فشل في تحديث مشرفي {source_id}: {e}")
            
            if updated_count > 0:
                await event.edit(f"✅ تم تحديث قائمة المشرفين لـ {updated_count} مصدر")
                await self.show_admin_filters(event, task_id)
            else:
                await event.edit("❌ فشل في تحديث قائمة المشرفين")
                
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث المشرفين: {e}")
            await event.edit("❌ حدث خطأ أثناء التحديث")
    
    async def handle_set_working_hours(self, event, task_id, text):
        """Handle setting working hours from user input"""
        try:
            # Parse time format: HH:MM-HH:MM
            if '-' not in text:
                await event.respond("❌ صيغة غير صحيحة. استخدم: ساعة:دقيقة-ساعة:دقيقة (مثال: 09:00-17:30)")
                return
            
            start_time, end_time = text.strip().split('-')
            
            # Parse start time
            start_hour, start_minute = map(int, start_time.split(':'))
            end_hour, end_minute = map(int, end_time.split(':'))
            
            # Validate time ranges
            if not (0 <= start_hour <= 23 and 0 <= start_minute <= 59 and 
                    0 <= end_hour <= 23 and 0 <= end_minute <= 59):
                await event.respond("❌ ساعات أو دقائق غير صحيحة")
                return
                
            # Set working hours
            success = self.db.set_working_hours(task_id, start_hour, start_minute, end_hour, end_minute)
            
            if success:
                await event.respond(f"✅ تم تحديد ساعات العمل من {start_time} إلى {end_time}")
                user_id = event.sender_id
                self.db.clear_conversation_state(user_id)
                await self.show_working_hours_filter(event, task_id)
            else:
                await event.respond("❌ فشل في حفظ ساعات العمل")
                # Clear conversation state even on failure
                user_id = event.sender_id
                self.db.clear_conversation_state(user_id)
                
        except ValueError:
            await event.respond("❌ صيغة غير صحيحة. استخدم: ساعة:دقيقة-ساعة:دقيقة (مثال: 09:00-17:30)")
            # Clear conversation state on error
            user_id = event.sender_id
            self.db.clear_conversation_state(user_id)
        except Exception as e:
            logger.error(f"❌ خطأ في تحديد ساعات العمل: {e}")
            await event.respond("❌ حدث خطأ أثناء التحديد")
            # Clear conversation state on error
            user_id = event.sender_id
            self.db.clear_conversation_state(user_id)
    
    async def handle_add_language_filter(self, event, task_id, text):
        """Handle adding language filter from user input"""
        try:
            language_input = text.strip().lower()
            
            # Common language mappings
            language_map = {
                'ar': 'العربية', 'arabic': 'العربية', 'عربي': 'العربية', 'عربية': 'العربية',
                'en': 'English', 'english': 'English', 'انجليزي': 'English', 'إنجليزي': 'English',
                'fr': 'Français', 'french': 'Français', 'فرنسي': 'Français',
                'es': 'Español', 'spanish': 'Español', 'اسباني': 'Español',
                'de': 'Deutsch', 'german': 'Deutsch', 'الماني': 'Deutsch',
                'ru': 'Русский', 'russian': 'Русский', 'روسي': 'Русский',
                'tr': 'Türkçe', 'turkish': 'Türkçe', 'تركي': 'Türkçe'
            }
            
            # Find language code and name
            if language_input in language_map:
                lang_code = language_input
                lang_name = language_map[language_input]
            else:
                # Check if it's a full language name
                lang_code = None
                lang_name = None
                for code, name in language_map.items():
                    if name.lower() == language_input or language_input in name.lower():
                        lang_code = code if len(code) == 2 else language_input
                        lang_name = name
                        break
                
                if not lang_code:
                    # Use input as both code and name
                    lang_code = language_input[:2]
                    lang_name = language_input.title()
            
            # Add language filter
            success = self.db.add_language_filter(task_id, lang_code, lang_name, True)
            
            if success:
                await event.respond(f"✅ تم إضافة فلتر اللغة: {lang_name}")
                user_id = event.sender_id
                self.db.clear_conversation_state(user_id)
                
                # Send language filters menu as a new message
                try:
                    # Create a minimal callback event-like object to reuse the display function
                    await self._send_language_filters_menu(event.chat_id, task_id)
                except Exception as e:
                    logger.error(f"خطأ في عرض قائمة فلاتر اللغة: {e}")
                    await event.respond("✅ تم إضافة الفلتر بنجاح")
            else:
                await event.respond("❌ فشل في إضافة فلتر اللغة أو أنها موجودة مسبقاً")
                # Clear conversation state even on failure to avoid getting stuck
                user_id = event.sender_id
                self.db.clear_conversation_state(user_id)
                
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة فلتر اللغة: {e}")
            await event.respond("❌ حدث خطأ أثناء الإضافة")
            # Clear conversation state on error
            user_id = event.sender_id
            self.db.clear_conversation_state(user_id)

    async def _send_language_filters_menu(self, chat_id, task_id):
        """Send language filters menu as a new message"""
        try:
            user_id = chat_id  # Assume chat_id is the user_id for private chats
            task = self.db.get_task(task_id, user_id)
            
            if not task:
                return
                
            # Get language filters and create message content
            language_data = self.db.get_language_filters(task_id)
            filter_mode = language_data['mode']  # 'allow' or 'block'
            languages = language_data['languages']
            
            # Get advanced filter status
            advanced_settings = self.db.get_advanced_filters_settings(task_id)
            enabled = advanced_settings.get('language_filter_enabled', False)
            
            status_text = "🟢 مُفَعَّل" if enabled else "🔴 مُعطل"
            mode_text = "السماح" if filter_mode == 'allow' else "الحظر"
            
            message = f"🌍 **فلتر اللغة: {task.get('task_name', 'مهمة بدون اسم')}**\n\n"
            message += f"📊 **الحالة**: {status_text}\n"
            message += f"⚙️ **الوضع**: {mode_text}\n"
            message += f"📝 **عدد اللغات**: {len(languages)}\n\n"
            
            if filter_mode == 'allow':
                message += "🟢 **وضع السماح**: يسمح فقط بالرسائل باللغات المُحددة\n"
            else:
                message += "🔴 **وضع الحظر**: يحظر الرسائل باللغات المُحددة\n"
            
            # Show languages
            if languages:
                message += "\n📋 **اللغات المُحددة**:\n"
                for i, lang in enumerate(languages, 1):
                    selection_status = "✅" if lang['is_allowed'] else "❌"
                    message += f"{i}. {selection_status} {lang['language_name']} ({lang['language_code']})\n"
            else:
                message += "\n❌ لا توجد لغات محددة"
            
            # Create buttons
            buttons = [
                [Button.inline(f"{'🔴 إيقاف' if enabled else '🟢 تفعيل'}", f"toggle_language_filter_{task_id}")],
                [Button.inline(f"⚙️ تغيير الوضع: {mode_text}", f"toggle_language_mode_{task_id}")],
                [Button.inline("➕ إضافة لغة مخصصة", f"add_custom_language_{task_id}")],
                [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
            ]
            
            # Send the message
            await self.client.send_message(chat_id, message, buttons=buttons)
            
        except Exception as e:
            logger.error(f"خطأ في إرسال قائمة فلاتر اللغة: {e}")

    async def manage_text_cleaning(self, event, task_id):
        """Manage text cleaning settings for a task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Get current text cleaning settings
        settings = self.db.get_text_cleaning_settings(task_id)
        
        # Create status indicators
        links_status = "🟢" if settings.get('remove_links', False) else "🔴"
        emojis_status = "🟢" if settings.get('remove_emojis', False) else "🔴"
        hashtags_status = "🟢" if settings.get('remove_hashtags', False) else "🔴"
        phones_status = "🟢" if settings.get('remove_phone_numbers', False) else "🔴"
        empty_lines_status = "🟢" if settings.get('remove_empty_lines', False) else "🔴"
        keywords_status = "🟢" if settings.get('remove_lines_with_keywords', False) else "🔴"

        # Get keywords count
        keywords = self.db.get_text_cleaning_keywords(task_id)
        keywords_count = len(keywords)

        message = f"🧹 **تنظيف النصوص للمهمة: {task.get('task_name', 'مهمة بدون اسم')}**\n\n"
        message += "📋 **إعدادات التنظيف الحالية:**\n\n"
        message += f"{links_status} حذف الروابط\n"
        message += f"{emojis_status} حذف الايموجيات\n"
        message += f"{hashtags_status} حذف الهاشتاقات\n"
        message += f"{phones_status} حذف أرقام الهواتف\n"
        message += f"{empty_lines_status} حذف الأسطر الفارغة\n"
        message += f"{keywords_status} حذف أسطر بكلمات محددة ({keywords_count} كلمة)\n\n"
        message += "اختر نوع التنظيف للتفعيل/الإلغاء:"

        buttons = [
            [Button.inline(f"{links_status} الروابط", f"clean_toggle_remove_links_{task_id}")],
            [Button.inline(f"{emojis_status} الايموجيات", f"clean_toggle_remove_emojis_{task_id}")],
            [Button.inline(f"{hashtags_status} الهاشتاقات", f"clean_toggle_remove_hashtags_{task_id}")],
            [Button.inline(f"{phones_status} أرقام الهواتف", f"clean_toggle_remove_phone_numbers_{task_id}")],
            [Button.inline(f"{empty_lines_status} الأسطر الفارغة", f"clean_toggle_remove_empty_lines_{task_id}")],
            [Button.inline(f"{keywords_status} الكلمات المحددة ({keywords_count})", f"manage_text_clean_keywords_{task_id}")],
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]

        await event.edit(message, buttons=buttons)

    async def handle_text_cleaning_toggle(self, event, data):
        """Handle text cleaning toggle actions"""
        try:
            # Parse callback data: clean_toggle_setting_name_task_id
            parts = data.split("_")
            if len(parts) >= 4:
                setting_name = "_".join(parts[2:-1])  # Get setting name (can contain underscores)
                task_id = int(parts[-1])
                
                user_id = event.sender_id
                task = self.db.get_task(task_id, user_id)
                
                if not task:
                    await event.answer("❌ المهمة غير موجودة")
                    return

                # Get current setting value
                settings = self.db.get_text_cleaning_settings(task_id)
                current_value = settings.get(setting_name, False)
                new_value = not current_value

                # Update the setting
                success = self.db.update_text_cleaning_setting(task_id, setting_name, new_value)
                
                if success:
                    status_text = "تم تفعيل" if new_value else "تم إلغاء"
                    setting_display = {
                        'remove_links': 'حذف الروابط',
                        'remove_emojis': 'حذف الايموجيات',
                        'remove_hashtags': 'حذف الهاشتاقات',
                        'remove_phone_numbers': 'حذف أرقام الهواتف',
                        'remove_empty_lines': 'حذف الأسطر الفارغة',
                        'remove_lines_with_keywords': 'حذف الأسطر بالكلمات المحددة'
                    }.get(setting_name, setting_name)
                    
                    await event.answer(f"✅ {status_text} {setting_display}")
                    
                    # Force refresh UserBot tasks
                    try:
                        from userbot_service.userbot import userbot_instance
                        if user_id in userbot_instance.clients:
                            await userbot_instance.refresh_user_tasks(user_id)
                            logger.info(f"🔄 تم تحديث مهام UserBot بعد تغيير إعدادات تنظيف النص للمهمة {task_id}")
                    except Exception as e:
                        logger.error(f"خطأ في تحديث مهام UserBot: {e}")

                    # Refresh the text cleaning settings display
                    await self.manage_text_cleaning(event, task_id)
                else:
                    await event.answer("❌ فشل في تحديث الإعداد")
                    
        except Exception as e:
            logger.error(f"خطأ في تفعيل/إلغاء إعداد تنظيف النص: {e}")
            await event.answer("❌ حدث خطأ")

    async def manage_text_cleaning_keywords(self, event, task_id):
        """Manage text cleaning keywords for a task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Get current keywords
        keywords = self.db.get_text_cleaning_keywords(task_id)
        
        message = f"🧹 **إدارة كلمات تنظيف النصوص**\n"
        message += f"المهمة: {task.get('task_name', 'مهمة بدون اسم')}\n\n"
        
        if not keywords:
            message += "❌ لا توجد كلمات محددة حالياً\n\n"
            message += "عند تفعيل هذه الميزة، سيتم حذف أي سطر يحتوي على الكلمات المحددة"
        else:
            message += f"📋 **الكلمات المحددة ({len(keywords)}):**\n\n"
            for i, keyword in enumerate(keywords[:20], 1):  # Show max 20
                message += f"{i}. {keyword}\n"
            
            if len(keywords) > 20:
                message += f"\n... و {len(keywords) - 20} كلمة أخرى"

        buttons = [
            [Button.inline("➕ إضافة كلمات", f"add_text_clean_keywords_{task_id}")],
        ]
        
        if keywords:
            buttons.append([Button.inline("🗑️ مسح جميع الكلمات", f"clear_text_clean_keywords_{task_id}")])
        
        buttons.append([Button.inline("🔙 رجوع لتنظيف النصوص", f"text_cleaning_{task_id}")])

        await event.edit(message, buttons=buttons)

    async def clear_text_cleaning_keywords(self, event, task_id):
        """Clear all text cleaning keywords for a task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Get current keywords count
        keywords = self.db.get_text_cleaning_keywords(task_id)
        keywords_count = len(keywords)

        if keywords_count == 0:
            await event.answer("❌ لا توجد كلمات لحذفها")
            return

        # Clear all keywords
        success = self.db.clear_text_cleaning_keywords(task_id)
        
        if success:
            await event.answer(f"✅ تم حذف جميع الكلمات ({keywords_count} كلمة)")
            
            # Force refresh UserBot tasks
            try:
                from userbot_service.userbot import userbot_instance
                if user_id in userbot_instance.clients:
                    await userbot_instance.refresh_user_tasks(user_id)
                    logger.info(f"🔄 تم تحديث مهام UserBot بعد حذف كلمات تنظيف النص للمهمة {task_id}")
            except Exception as e:
                logger.error(f"خطأ في تحديث مهام UserBot: {e}")

            # Return to keywords management
            await self.manage_text_cleaning_keywords(event, task_id)
        else:
            await event.answer("❌ فشل في حذف الكلمات")

    # ===== Advanced Features Management =====
    
    async def show_advanced_features(self, event, task_id):
        """Show advanced features menu for task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get current settings status
        char_limit = self.db.get_character_limit_settings(task_id)
        rate_limit = self.db.get_rate_limit_settings(task_id)
        forwarding_delay = self.db.get_forwarding_delay_settings(task_id)
        sending_interval = self.db.get_sending_interval_settings(task_id)
        
        char_status = "🟢" if char_limit['enabled'] else "🔴"
        rate_status = "🟢" if rate_limit['enabled'] else "🔴"
        delay_status = "🟢" if forwarding_delay['enabled'] else "🔴"
        interval_status = "🟢" if sending_interval['enabled'] else "🔴"

        buttons = [
            # الصف الأول - حد الأحرف وحد الرسائل
            [Button.inline(f"📏 حد الأحرف {char_status}", f"character_limit_{task_id}"),
             Button.inline(f"📊 حد الرسائل {rate_status}", f"rate_limit_{task_id}")],
            
            # الصف الثاني - تأخير التوجيه وفاصل الإرسال
            [Button.inline(f"⏱️ تأخير التوجيه {delay_status}", f"forwarding_delay_{task_id}"),
             Button.inline(f"⏲️ فاصل الإرسال {interval_status}", f"sending_interval_{task_id}")],
            
            # الصف الأخير - العودة
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]

        message = f"⚡ الميزات المتقدمة للمهمة: {task_name}\n\n"
        message += "📋 الميزات المتاحة:\n\n"
        message += f"{char_status} **حد الأحرف**: "
        if char_limit['enabled']:
            message += f"مفعل ({char_limit['mode']}: {char_limit['min_chars']}-{char_limit['max_chars']} حرف)\n"
        else:
            message += "معطل\n"
            
        message += f"{rate_status} **حد الرسائل**: "
        if rate_limit['enabled']:
            message += f"مفعل ({rate_limit['message_count']} رسائل/{rate_limit['time_period_seconds']} ثانية)\n"
        else:
            message += "معطل\n"
            
        message += f"{delay_status} **تأخير التوجيه**: "
        if forwarding_delay['enabled']:
            message += f"مفعل ({forwarding_delay['delay_seconds']} ثواني)\n"
        else:
            message += "معطل\n"
            
        message += f"{interval_status} **فاصل الإرسال**: "
        if sending_interval['enabled']:
            message += f"مفعل ({sending_interval['interval_seconds']} ثواني بين الأهداف)\n"
        else:
            message += "معطل\n"

        await event.edit(message, buttons=buttons)

    async def show_character_limit_settings(self, event, task_id):
        """Show character limit settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_character_limit_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        status = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        mode_text = "سماح" if settings['mode'] == 'allow' else "حظر"
        
        buttons = [
            [Button.inline(f"{'❌ تعطيل' if settings['enabled'] else '✅ تفعيل'}", f"toggle_char_limit_{task_id}")],
        ]
        
        if settings['enabled']:
            buttons.extend([
                [Button.inline(f"🔄 تغيير الوضع ({mode_text})", f"toggle_char_mode_{task_id}")],
                [Button.inline(f"📏 تعديل النطاق ({settings['min_chars']}-{settings['max_chars']})", f"edit_char_range_{task_id}")],
            ])
        
        buttons.append([Button.inline("🔙 رجوع للميزات المتقدمة", f"advanced_features_{task_id}")])

        message = f"📏 حد الأحرف للمهمة: {task_name}\n\n"
        message += f"📊 **الحالة**: {status}\n"
        if settings['enabled']:
            message += f"⚙️ **الوضع**: {mode_text}\n"
            message += f"📐 **النطاق**: {settings['min_chars']} - {settings['max_chars']} حرف\n\n"
        message += "\n💡 **وصف الميزة**:\n"
        message += "• السماح: توجيه الرسائل ضمن النطاق المحدد فقط\n"
        message += "• الحظر: منع الرسائل ضمن النطاق المحدد\n"
        message += "• يتم حساب النص بدون المسافات والتنسيق"

        await event.edit(message, buttons=buttons)

    async def show_rate_limit_settings(self, event, task_id):
        """Show rate limit settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_rate_limit_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        status = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        
        buttons = [
            [Button.inline(f"{'❌ تعطيل' if settings['enabled'] else '✅ تفعيل'}", f"toggle_rate_limit_{task_id}")],
        ]
        
        if settings['enabled']:
            buttons.extend([
                [Button.inline(f"📊 تعديل العدد ({settings['message_count']})", f"edit_rate_count_{task_id}")],
                [Button.inline(f"⏱️ تعديل الفترة ({settings['time_period_seconds']}ث)", f"edit_rate_period_{task_id}")],
            ])
        
        buttons.append([Button.inline("🔙 رجوع للميزات المتقدمة", f"advanced_features_{task_id}")])

        message = f"📊 حد الرسائل للمهمة: {task_name}\n\n"
        message += f"📊 **الحالة**: {status}\n"
        if settings['enabled']:
            message += f"📈 **الحد الأقصى**: {settings['message_count']} رسائل\n"
            message += f"⏰ **الفترة الزمنية**: {settings['time_period_seconds']} ثانية\n\n"
        message += "\n💡 **وصف الميزة**:\n"
        message += "• تحديد عدد أقصى من الرسائل خلال فترة زمنية معينة\n"
        message += "• منع إرسال الرسائل الزائدة عن الحد المحدد\n"
        message += "• يساعد في تجنب التبليغ عن الإرسال المكثف"

        await event.edit(message, buttons=buttons)

    async def show_forwarding_delay_settings(self, event, task_id):
        """Show forwarding delay settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_forwarding_delay_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        status = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        
        buttons = [
            [Button.inline(f"{'❌ تعطيل' if settings['enabled'] else '✅ تفعيل'}", f"toggle_forwarding_delay_{task_id}")],
        ]
        
        if settings['enabled']:
            buttons.append([Button.inline(f"⏱️ تعديل التأخير ({settings['delay_seconds']}ث)", f"edit_forwarding_delay_{task_id}")])
        
        buttons.append([Button.inline("🔙 رجوع للميزات المتقدمة", f"advanced_features_{task_id}")])

        message = f"⏱️ تأخير التوجيه للمهمة: {task_name}\n\n"
        message += f"📊 **الحالة**: {status}\n"
        if settings['enabled']:
            message += f"⏰ **التأخير**: {settings['delay_seconds']} ثانية\n\n"
        message += "\n💡 **وصف الميزة**:\n"
        message += "• تأخير زمني بعد استلام الرسالة من المصدر قبل التوجيه\n"
        message += "• يساعد في تجنب التوجيه الفوري المشبوه\n"
        message += "• مفيد للرسائل الحساسة أو المهمة"

        await event.edit(message, buttons=buttons)

    async def show_sending_interval_settings(self, event, task_id):
        """Show sending interval settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_sending_interval_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        status = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        
        buttons = [
            [Button.inline(f"{'❌ تعطيل' if settings['enabled'] else '✅ تفعيل'}", f"toggle_sending_interval_{task_id}")],
        ]
        
        if settings['enabled']:
            buttons.append([Button.inline(f"⏱️ تعديل الفاصل ({settings['interval_seconds']}ث)", f"edit_sending_interval_{task_id}")])
        
        buttons.append([Button.inline("🔙 رجوع للميزات المتقدمة", f"advanced_features_{task_id}")])

        message = f"⏱️ فاصل الإرسال للمهمة: {task_name}\n\n"
        message += f"📊 **الحالة**: {status}\n"
        if settings['enabled']:
            message += f"⏰ **الفاصل**: {settings['interval_seconds']} ثانية بين كل هدف\n\n"
        message += "\n💡 **وصف الميزة**:\n"
        message += "• فترة انتظار بين إرسال الرسالة لكل هدف\n"
        message += "• يقلل الضغط على تليجرام ويتجنب التبليغ\n"
        message += "• مثال: إرسال للهدف الأول، انتظار، ثم إرسال للهدف الثاني"

        await event.edit(message, buttons=buttons)

    # ===== Advanced Features Toggle & Edit Functions =====
    
    async def toggle_character_limit(self, event, task_id):
        """Toggle character limit on/off"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Toggle the setting
        new_enabled = self.db.toggle_character_limit(task_id)
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        status_text = "تم تفعيل" if new_enabled else "تم تعطيل"
        await event.answer(f"✅ {status_text} حد الأحرف")
        
        # Show updated settings
        await self.show_character_limit_settings(event, task_id)

    async def toggle_character_limit_mode(self, event, task_id):
        """Toggle character limit mode between allow/block"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Toggle the mode
        new_mode = self.db.toggle_character_limit_mode(task_id)
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        mode_text = "سماح" if new_mode == 'allow' else "حظر"
        await event.answer(f"✅ تم تغيير الوضع إلى: {mode_text}")
        
        # Show updated settings
        await self.show_character_limit_settings(event, task_id)

    async def toggle_rate_limit(self, event, task_id):
        """Toggle rate limit on/off"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Toggle the setting
        new_enabled = self.db.toggle_rate_limit(task_id)
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        status_text = "تم تفعيل" if new_enabled else "تم تعطيل"
        await event.answer(f"✅ {status_text} حد الرسائل")
        
        # Show updated settings
        await self.show_rate_limit_settings(event, task_id)

    async def toggle_forwarding_delay(self, event, task_id):
        """Toggle forwarding delay on/off"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Toggle the setting
        new_enabled = self.db.toggle_forwarding_delay(task_id)
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        status_text = "تم تفعيل" if new_enabled else "تم تعطيل"
        await event.answer(f"✅ {status_text} تأخير التوجيه")
        
        # Show updated settings
        await self.show_forwarding_delay_settings(event, task_id)

    async def toggle_sending_interval(self, event, task_id):
        """Toggle sending interval on/off"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Toggle the setting
        new_enabled = self.db.toggle_sending_interval(task_id)
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        status_text = "تم تفعيل" if new_enabled else "تم تعطيل"
        await event.answer(f"✅ {status_text} فاصل الإرسال")
        
        # Show updated settings
        await self.show_sending_interval_settings(event, task_id)

    # ===== Edit Settings Functions =====
    
    async def start_edit_character_range(self, event, task_id):
        """Start editing character range"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_character_limit_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')

        buttons = [
            [Button.inline("🔙 إلغاء", f"character_limit_{task_id}")]
        ]

        message = f"📏 تعديل نطاق الأحرف للمهمة: {task_name}\n\n"
        message += f"📊 النطاق الحالي: {settings['min_chars']} - {settings['max_chars']} حرف\n\n"
        message += "📝 أرسل النطاق الجديد في صورة:\n"
        message += "الحد_الأدنى-الحد_الأقصى\n\n"
        message += "مثال: 10-500"

        await event.edit(message, buttons=buttons)
        
        # Set conversation state for this user and task
        self.db.set_conversation_state(user_id, 'editing_char_range', str(task_id))

    async def start_edit_rate_count(self, event, task_id):
        """Start editing rate count"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_rate_limit_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')

        buttons = [
            [Button.inline("🔙 إلغاء", f"rate_limit_{task_id}")]
        ]

        message = f"📊 تعديل عدد الرسائل للمهمة: {task_name}\n\n"
        message += f"📈 العدد الحالي: {settings['message_count']} رسائل\n\n"
        message += "📝 أرسل العدد الجديد (رقم صحيح موجب)\n\n"
        message += "مثال: 10"

        await event.edit(message, buttons=buttons)
        
        # Set conversation state for this user and task
        self.db.set_conversation_state(user_id, 'editing_rate_count', str(task_id))

    async def start_edit_rate_period(self, event, task_id):
        """Start editing rate period"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_rate_limit_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')

        buttons = [
            [Button.inline("🔙 إلغاء", f"rate_limit_{task_id}")]
        ]

        message = f"⏱️ تعديل فترة الرسائل للمهمة: {task_name}\n\n"
        message += f"⏰ الفترة الحالية: {settings['time_period_seconds']} ثانية\n\n"
        message += "📝 أرسل الفترة الجديدة بالثواني (رقم صحيح موجب)\n\n"
        message += "مثال: 60 (للدقيقة الواحدة)"

        await event.edit(message, buttons=buttons)
        
        # Set conversation state for this user and task
        self.db.set_conversation_state(user_id, 'editing_rate_period', str(task_id))

    async def start_edit_forwarding_delay(self, event, task_id):
        """Start editing forwarding delay"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_forwarding_delay_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')

        buttons = [
            [Button.inline("🔙 إلغاء", f"forwarding_delay_{task_id}")]
        ]

        message = f"⏱️ تعديل تأخير التوجيه للمهمة: {task_name}\n\n"
        message += f"⏰ التأخير الحالي: {settings['delay_seconds']} ثانية\n\n"
        message += "📝 أرسل التأخير الجديد بالثواني (رقم صحيح موجب)\n\n"
        message += "مثال: 5 (للانتظار 5 ثوان قبل التوجيه)"

        await event.edit(message, buttons=buttons)
        
        # Set conversation state for this user and task
        self.db.set_conversation_state(user_id, 'editing_forwarding_delay', str(task_id))

    async def start_edit_sending_interval(self, event, task_id):
        """Start editing sending interval"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_sending_interval_settings(task_id)
        task_name = task.get('task_name', 'مهمة بدون اسم')

        buttons = [
            [Button.inline("🔙 إلغاء", f"sending_interval_{task_id}")]
        ]

        message = f"⏱️ تعديل فاصل الإرسال للمهمة: {task_name}\n\n"
        message += f"⏰ الفاصل الحالي: {settings['interval_seconds']} ثانية\n\n"
        message += "📝 أرسل الفاصل الجديد بالثواني (رقم صحيح موجب)\n\n"
        message += "مثال: 2 (للانتظار ثانيتين بين كل هدف)"

        await event.edit(message, buttons=buttons)
        
        # Set conversation state for this user and task
        self.db.set_conversation_state(user_id, 'editing_sending_interval', str(task_id))

    # ===== Edit Handler Functions =====
    
    async def handle_edit_character_range(self, event, task_id, text):
        """Handle character range editing"""
        user_id = event.sender_id
        
        try:
            # Parse the range in format: min-max
            if '-' not in text:
                await event.respond("❌ صيغة خاطئة. يجب أن تكون: الحد_الأدنى-الحد_الأقصى\nمثال: 10-500")
                return
            
            parts = text.strip().split('-')
            if len(parts) != 2:
                await event.respond("❌ صيغة خاطئة. يجب أن تكون: الحد_الأدنى-الحد_الأقصى\nمثال: 10-500")
                return
            
            min_chars = int(parts[0].strip())
            max_chars = int(parts[1].strip())
            
            if min_chars < 0 or max_chars < 0:
                await event.respond("❌ الأرقام يجب أن تكون موجبة")
                return
            
            if min_chars >= max_chars:
                await event.respond("❌ الحد الأدنى يجب أن يكون أقل من الحد الأقصى")
                return
            
            # Update the settings
            success = self.db.update_character_limit_settings(task_id, min_chars=min_chars, max_chars=max_chars)
            
            if success:
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Clear conversation state
                self.db.clear_conversation_state(user_id)
                
                await event.respond(f"✅ تم تحديث نطاق الأحرف إلى: {min_chars} - {max_chars}")
                
                # Show updated settings
                await self.show_character_limit_settings(event, task_id)
            else:
                await event.respond("❌ حدث خطأ في تحديث إعدادات النطاق في قاعدة البيانات")
                self.db.clear_conversation_state(user_id)
            
        except ValueError:
            await event.respond("❌ يجب إدخال أرقام صحيحة فقط\nمثال: 10-500")
        except Exception as e:
            logger.error(f"خطأ في تعديل نطاق الأحرف: {e}")
            await event.respond("❌ حدث خطأ في تحديث النطاق")
            self.db.clear_conversation_state(user_id)

    async def handle_edit_rate_count(self, event, task_id, text):
        """Handle rate count editing"""
        user_id = event.sender_id
        
        try:
            count = int(text.strip())
            
            if count <= 0:
                await event.respond("❌ العدد يجب أن يكون رقماً موجباً أكبر من الصفر")
                return
            
            # Update the settings
            success = self.db.update_rate_limit_settings(task_id, message_count=count)
            
            if success:
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Clear conversation state
                self.db.clear_conversation_state(user_id)
                
                await event.respond(f"✅ تم تحديث عدد الرسائل إلى: {count}")
                
                # Show updated settings
                await self.show_rate_limit_settings(event, task_id)
            else:
                await event.respond("❌ حدث خطأ في تحديث إعدادات عدد الرسائل في قاعدة البيانات")
                self.db.clear_conversation_state(user_id)
            
        except ValueError:
            await event.respond("❌ يجب إدخال رقم صحيح موجب\nمثال: 10")
        except Exception as e:
            logger.error(f"خطأ في تعديل عدد الرسائل: {e}")
            await event.respond("❌ حدث خطأ في تحديث عدد الرسائل")
            self.db.clear_conversation_state(user_id)

    async def handle_edit_rate_period(self, event, task_id, text):
        """Handle rate period editing"""
        user_id = event.sender_id
        
        try:
            period = int(text.strip())
            
            if period <= 0:
                await event.respond("❌ الفترة يجب أن تكون رقماً موجباً أكبر من الصفر")
                return
            
            # Update the settings
            success = self.db.update_rate_limit_settings(task_id, time_period_seconds=period)
            
            if success:
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Clear conversation state
                self.db.clear_conversation_state(user_id)
                
                await event.respond(f"✅ تم تحديث فترة الرسائل إلى: {period} ثانية")
                
                # Show updated settings
                await self.show_rate_limit_settings(event, task_id)
            else:
                await event.respond("❌ حدث خطأ في تحديث إعدادات فترة الرسائل في قاعدة البيانات")
                self.db.clear_conversation_state(user_id)
            
        except ValueError:
            await event.respond("❌ يجب إدخال رقم صحيح موجب\nمثال: 60")
        except Exception as e:
            logger.error(f"خطأ في تعديل فترة الرسائل: {e}")
            await event.respond("❌ حدث خطأ في تحديث فترة الرسائل")
            self.db.clear_conversation_state(user_id)

    async def handle_edit_forwarding_delay(self, event, task_id, text):
        """Handle forwarding delay editing"""
        user_id = event.sender_id
        
        try:
            delay = int(text.strip())
            
            if delay < 0:
                await event.respond("❌ التأخير يجب أن يكون رقماً صفراً أو موجباً")
                return
            
            # Update the settings
            success = self.db.update_forwarding_delay_settings(task_id, delay_seconds=delay)
            
            if success:
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Clear conversation state
                self.db.clear_conversation_state(user_id)
                
                await event.respond(f"✅ تم تحديث تأخير التوجيه إلى: {delay} ثانية")
                
                # Show updated settings
                await self.show_forwarding_delay_settings(event, task_id)
            else:
                await event.respond("❌ حدث خطأ في تحديث إعدادات تأخير التوجيه في قاعدة البيانات")
                self.db.clear_conversation_state(user_id)
            
        except ValueError:
            await event.respond("❌ يجب إدخال رقم صحيح\nمثال: 5")
        except Exception as e:
            logger.error(f"خطأ في تعديل تأخير التوجيه: {e}")
            await event.respond("❌ حدث خطأ في تحديث تأخير التوجيه")
            self.db.clear_conversation_state(user_id)

    async def handle_edit_sending_interval(self, event, task_id, text):
        """Handle sending interval editing"""
        user_id = event.sender_id
        
        try:
            interval = int(text.strip())
            
            if interval < 0:
                await event.respond("❌ الفاصل يجب أن يكون رقماً صفراً أو موجباً")
                return
            
            # Update the settings
            success = self.db.update_sending_interval_settings(task_id, interval_seconds=interval)
            
            if success:
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Clear conversation state
                self.db.clear_conversation_state(user_id)
                
                await event.respond(f"✅ تم تحديث فاصل الإرسال إلى: {interval} ثانية")
                
                # Show updated settings
                await self.show_sending_interval_settings(event, task_id)
            else:
                await event.respond("❌ حدث خطأ في تحديث إعدادات فاصل الإرسال في قاعدة البيانات")
                self.db.clear_conversation_state(user_id)
            
        except ValueError:
            await event.respond("❌ يجب إدخال رقم صحيح\nمثال: 2")
        except Exception as e:
            logger.error(f"خطأ في تعديل فاصل الإرسال: {e}")
            await event.respond("❌ حدث خطأ في تحديث فاصل الإرسال")
            self.db.clear_conversation_state(user_id)

# Create bot instance
simple_bot = SimpleTelegramBot()

def run_simple_bot():
    """Run the simple bot"""
    asyncio.run(simple_bot.run())

if __name__ == '__main__':
    run_simple_bot()
    # ===== User Settings Functions =====
    
    async def show_timezone_settings(self, event):
        """Show timezone settings menu"""
        user_id = event.sender_id
        user_settings = self.db.get_user_settings(user_id)
        current_timezone = user_settings.get("timezone", "Asia/Riyadh")
        
        # Common timezone options for Arabic users
        timezones = [
            ("Asia/Riyadh", "🇸🇦 السعودية (GMT+3)"),
            ("Asia/Dubai", "🇦🇪 الإمارات (GMT+4)"),
            ("Asia/Kuwait", "🇰🇼 الكويت (GMT+3)"),
            ("Asia/Qatar", "🇶🇦 قطر (GMT+3)"),
            ("Asia/Bahrain", "🇧🇭 البحرين (GMT+3)"),
            ("Asia/Baghdad", "🇮🇶 العراق (GMT+3)"),
            ("Asia/Damascus", "🇸🇾 سوريا (GMT+3)"),
            ("Asia/Beirut", "🇱🇧 لبنان (GMT+2)"),
            ("Africa/Cairo", "🇪🇬 مصر (GMT+2)"),
            ("Africa/Casablanca", "🇲🇦 المغرب (GMT+1)"),
            ("Africa/Tunis", "🇹🇳 تونس (GMT+1)"),
            ("Africa/Algiers", "🇩🇿 الجزائر (GMT+1)"),
            ("Asia/Amman", "🇯🇴 الأردن (GMT+3)"),
            ("Asia/Jerusalem", "🇵🇸 فلسطين (GMT+2)"),
            ("Europe/London", "🇬🇧 لندن (GMT+0)"),
            ("Europe/Paris", "🇫🇷 باريس (GMT+1)"),
            ("Europe/Berlin", "🇩🇪 برلين (GMT+1)"),
            ("America/New_York", "🇺🇸 نيويورك (GMT-5)"),
            ("America/Los_Angeles", "🇺🇸 لوس أنجلوس (GMT-8)"),
            ("Asia/Tokyo", "🇯🇵 طوكيو (GMT+9)")
        ]
        
        buttons = []
        for tz_code, tz_name in timezones:
            status = "✅" if tz_code == current_timezone else "⚪"
            buttons.append([Button.inline(f"{status} {tz_name}", f"set_timezone_{tz_code}")])
        
        buttons.append([Button.inline("🔙 القائمة الرئيسية", "main_menu")])
        
        await event.edit(
            f"🌍 **إعدادات المنطقة الزمنية**\\n\\n"
            f"📍 **المنطقة الزمنية الحالية**: {current_timezone}\\n\\n"
            f"🕐 **أهمية المنطقة الزمنية**:\\n"
            f"• تؤثر على فلتر ساعات العمل والنوم\\n"
            f"• تحدد أوقات تشغيل وإيقاف المهام\\n"
            f"• تؤثر على فلتر الأيام حسب توقيتك المحلي\\n\\n"
            f"اختر منطقتك الزمنية:",
            buttons=buttons
        )
        
    async def show_language_settings(self, event):
        """Show language settings menu"""
        user_id = event.sender_id
        user_settings = self.db.get_user_settings(user_id)
        current_language = user_settings.get("language", "ar")
        
        languages = [
            ("ar", "🇸🇦 العربية"),
            ("en", "🇺🇸 English"),
            ("fr", "🇫🇷 Français"),
            ("es", "🇪🇸 Español"),
            ("de", "🇩🇪 Deutsch"),
            ("it", "🇮🇹 Italiano"),
            ("ru", "🇷🇺 Русский"),
            ("tr", "🇹🇷 Türkçe"),
            ("fa", "🇮🇷 فارسی"),
            ("ur", "🇵🇰 اردو")
        ]
        
        buttons = []
        for lang_code, lang_name in languages:
            status = "✅" if lang_code == current_language else "⚪"
            buttons.append([Button.inline(f"{status} {lang_name}", f"set_language_{lang_code}")])
        
        buttons.append([Button.inline("🔙 القائمة الرئيسية", "main_menu")])
        
        await event.edit(
            f"🌐 **إعدادات اللغة**\\n\\n"
            f"📝 **اللغة الحالية**: {current_language}\\n\\n"
            f"💬 **ملاحظة**: حالياً البوت يعمل باللغة العربية فقط\\n"
            f"هذا الإعداد محفوظ للمستقبل عند إضافة دعم لغات أخرى\\n\\n"
            f"اختر لغتك المفضلة:",
            buttons=buttons
        )
        
    async def set_user_timezone(self, event, timezone):
        """Set user timezone"""
        user_id = event.sender_id
        
        success = self.db.update_user_timezone(user_id, timezone)
        if success:
            await event.answer(f"✅ تم تحديث المنطقة الزمنية إلى: {timezone}")
            await self.show_timezone_settings(event)
        else:
            await event.answer("❌ فشل في تحديث المنطقة الزمنية")
            
    async def set_user_language(self, event, language):
        """Set user language"""
        user_id = event.sender_id
        
        success = self.db.update_user_language(user_id, language)
        if success:
            await event.answer(f"✅ تم تحديث اللغة إلى: {language}")
            await self.show_language_settings(event)
        else:
            await event.answer("❌ فشل في تحديث اللغة")

