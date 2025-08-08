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
            elif data.startswith("advanced_filters_"): # Handler for advanced filters
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_advanced_filters(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة للفلاتر المتقدمة: {e}, data='{data}', parts={parts}")
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
            elif data.startswith("duplicate_filter_"): # Handler for duplicate filter
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_duplicate_filter(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلتر التكرار: {e}, data='{data}', parts={parts}")
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
            elif data.startswith("toggle_advanced_filter_"): # Handler for toggling advanced filters
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        filter_type = parts[3]
                        task_id = int(parts[4])
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
            elif state == 'waiting_auto_delete_time': # Handle setting auto delete time
                task_id = int(data)
                await self.handle_set_auto_delete_time(event, task_id, event.text)
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

        buttons = [
            [Button.inline(f"🔄 تغيير وضع التوجيه ({forward_mode_text})", f"toggle_forward_mode_{task_id}")],
            [Button.inline(f"📥 إدارة المصادر ({sources_count})", f"manage_sources_{task_id}")],
            [Button.inline(f"📤 إدارة الأهداف ({targets_count})", f"manage_targets_{task_id}")],
            [Button.inline("🔧 إعدادات التوجيه", f"forwarding_settings_{task_id}")],
            [Button.inline("🎬 فلاتر الوسائط", f"media_filters_{task_id}")],
            [Button.inline("📝 فلاتر الكلمات", f"word_filters_{task_id}")],
            [Button.inline("🔄 استبدال النصوص", f"text_replacements_{task_id}")],
            [Button.inline(f"{header_status} رأس الرسالة", f"header_settings_{task_id}")],
            [Button.inline(f"{footer_status} ذيل الرسالة", f"footer_settings_{task_id}")],
            [Button.inline(f"{buttons_status} أزرار إنلاين", f"inline_buttons_{task_id}")],
            [Button.inline("🅰️ الفلاتر المتقدمة", f"advanced_filters_{task_id}")],
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
        buttons = [
            [Button.inline("🔍 فحص حالة UserBot", "check_userbot")],
            [Button.inline("🔄 إعادة تسجيل الدخول", b"login")],
            [Button.inline("🗑️ حذف جميع المهام", "delete_all_tasks")],
            [Button.inline("🏠 القائمة الرئيسية", "main_menu")]
        ]

        await event.edit(
            "⚙️ **الإعدادات**\n\n"
            "اختر إعداد:",
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

        for media_type, arabic_name in media_types.items():
            is_allowed = filters.get(media_type, True)
            status_icon = "✅" if is_allowed else "❌"
            if is_allowed:
                allowed_count += 1

            message += f"{status_icon} {arabic_name}\n"

            # Add toggle button
            toggle_text = "❌ منع" if is_allowed else "✅ سماح"
            buttons.append([
                Button.inline(f"{toggle_text} {arabic_name}", f"toggle_media_{task_id}_{media_type}")
            ])

        message += f"\n📊 الإحصائيات: {allowed_count}/{total_count} مسموح\n\n"
        message += "اختر نوع الوسائط لتغيير حالته:"

        # Add bulk action buttons
        buttons.append([
            Button.inline("✅ السماح للكل", f"allow_all_media_{task_id}"),
            Button.inline("❌ منع الكل", f"block_all_media_{task_id}")
        ])
        buttons.append([Button.inline("🔄 إعادة تعيين افتراضي", f"reset_media_filters_{task_id}")])
        buttons.append([Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")])

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
        
        # Convert seconds to readable format
        delete_time = settings['auto_delete_time']
        if delete_time >= 3600:
            time_display = f"{delete_time // 3600} ساعة"
        elif delete_time >= 60:
            time_display = f"{delete_time // 60} دقيقة"
        else:
            time_display = f"{delete_time} ثانية"

        buttons = [
            [Button.inline(f"🔗 معاينة الرابط ({link_preview_status})", f"toggle_link_preview_{task_id}")],
            [Button.inline(f"📌 تثبيت الرسالة ({pin_message_status})", f"toggle_pin_message_{task_id}")],
            [Button.inline(f"🔔 الإشعارات ({silent_status})", f"toggle_silent_notifications_{task_id}")],
            [Button.inline(f"🗑️ الحذف التلقائي ({auto_delete_status})", f"toggle_auto_delete_{task_id}")],
            [Button.inline(f"🔄 مزامنة التعديل ({sync_edit_status})", f"toggle_sync_edit_{task_id}")],
            [Button.inline(f"🗂️ مزامنة الحذف ({sync_delete_status})", f"toggle_sync_delete_{task_id}")],
        ]
        
        if settings['auto_delete_enabled']:
            buttons.append([Button.inline(f"⏰ تعديل المدة ({time_display})", f"set_auto_delete_time_{task_id}")])
            
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
            [Button.inline(f"{day_status} فلتر الأيام", f"day_filters_{task_id}")],
            [Button.inline(f"{hours_status} ساعات العمل", f"working_hours_filter_{task_id}")],
            [Button.inline(f"{lang_status} فلتر اللغة", f"language_filters_{task_id}")],
            [Button.inline(f"{admin_status} فلتر المشرفين", f"admin_filters_{task_id}")],
            [Button.inline(f"{duplicate_status} فلتر التكرار", f"duplicate_filter_{task_id}")],
            [Button.inline(f"{inline_btn_status} فلتر الأزرار الشفافة", f"inline_button_filter_{task_id}")],
            [Button.inline(f"{forwarded_status} فلتر الرسائل المعاد توجيهها", f"forwarded_msg_filter_{task_id}")],
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]
        
        await event.edit(
            f"🅰️ الفلاتر المتقدمة: {task_name}\n\n"
            f"📋 حالة الفلاتر:\n"
            f"• {day_status} فلتر الأيام - تحديد أيام التوجيه المسموحة\n"
            f"• {hours_status} ساعات العمل - تحديد ساعات التوجيه\n" 
            f"• {lang_status} فلتر اللغة - السماح/حظر لغات محددة\n"
            f"• {admin_status} فلتر المشرفين - السماح/حظر مشرفين محددين\n"
            f"• {duplicate_status} فلتر التكرار - منع توجيه الرسائل المكررة\n"
            f"• {inline_btn_status} فلتر الأزرار - حظر الرسائل التي تحتوي على أزرار\n"
            f"• {forwarded_status} فلتر المعاد توجيهه - حظر الرسائل المعاد توجيهها\n\n"
            f"اختر الفلتر الذي تريد إدارته:",
            buttons=buttons
        )
    
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
        """Show language filters management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        language_filters = self.db.get_language_filters(task_id)
        
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['language_filter_enabled'] else "🔴 غير مُفَعَّل"
        
        # Create language buttons
        lang_buttons = []
        if language_filters:
            for lang in language_filters:
                status = "✅" if lang['is_allowed'] else "❌"
                lang_buttons.append([Button.inline(f"{status} {lang['language_name']}", f"toggle_lang_{task_id}_{lang['language_code']}")])
        else:
            lang_buttons.append([Button.inline("📝 لا توجد لغات محددة", "none")])
        
        # Add control buttons
        control_buttons = [
            [Button.inline("➕ إضافة لغة", f"add_language_{task_id}")],
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_language_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        buttons = lang_buttons + control_buttons
        
        await event.edit(
            f"🌍 فلتر اللغة: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n\n"
            f"🗣️ اللغات المُكونة:\n"
            f"✅ = مسموح | ❌ = محظور\n\n"
            f"💡 ملاحظة: عند تفعيل هذا الفلتر، سيتم توجيه الرسائل حسب اللغات المحددة",
            buttons=buttons
        )
    
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
        admin_filters = self.db.get_admin_filters(task_id)
        
        enabled_status = "🟢 مُفَعَّل" if advanced_settings['admin_filter_enabled'] else "🔴 غير مُفَعَّل"
        
        # Create admin buttons
        admin_buttons = []
        if admin_filters:
            for admin in admin_filters:
                status = "✅" if admin['is_allowed'] else "❌"
                name = admin['admin_first_name'] or admin['admin_username'] or f"المستخدم {admin['admin_user_id']}"
                admin_buttons.append([Button.inline(f"{status} {name}", f"toggle_admin_{task_id}_{admin['admin_user_id']}")])
        else:
            admin_buttons.append([Button.inline("👥 لا يوجد مشرفون محددون", "none")])
        
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
            f"👥 المشرفون المُكونون:\n"
            f"✅ = مسموح | ❌ = محظور\n\n"
            f"💡 ملاحظة: عند تفعيل هذا الفلتر، سيتم توجيه رسائل المشرفين المحددين فقط",
            buttons=buttons
        )
    
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
        block_status = "🚫 يحظر" if inline_button_setting else "✅ يسمح"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحظر ({block_status})", f"toggle_inline_block_{task_id}")],
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_inline_button_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"🔘 فلتر الأزرار الشفافة: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n"
            f"🎯 وضع الحظر: {block_status}\n\n"
            f"💡 ملاحظة: عند تفعيل هذا الفلتر، سيتم حظر/السماح بالرسائل التي تحتوي على أزرار إنلاين حسب الإعداد المحدد",
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
        block_status = "🚫 يحظر" if forwarded_setting else "✅ يسمح"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحظر ({block_status})", f"toggle_forwarded_block_{task_id}")],
            [Button.inline(f"🔄 {enabled_status}", f"toggle_advanced_filter_forwarded_message_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        await event.edit(
            f"↗️ فلتر الرسائل المعاد توجيهها: {task_name}\n\n"
            f"📊 حالة الفلتر: {enabled_status}\n"
            f"🎯 وضع الحظر: {block_status}\n\n"
            f"💡 ملاحظة: عند تفعيل هذا الفلتر، سيتم حظر/السماح بالرسائل التي تم توجيهها من قنوات أخرى إلى المصدر",
            buttons=buttons
        )
    
    async def toggle_advanced_filter(self, event, task_id, filter_type):
        """Toggle advanced filter on/off"""
        user_id = event.sender_id
        
        # Get current status
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        current_status = advanced_settings.get(f'{filter_type}_enabled', False)
        new_status = not current_status
        
        # Update the filter
        success = self.db.update_advanced_filter_setting(task_id, filter_type, new_status)
        
        if success:
            status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
            filter_names = {
                'day_filter': 'فلتر الأيام',
                'working_hours': 'فلتر ساعات العمل',
                'language_filter': 'فلتر اللغة',
                'admin_filter': 'فلتر المشرفين',
                'duplicate_filter': 'فلتر التكرار',
                'inline_button_filter': 'فلتر الأزرار الشفافة',
                'forwarded_message_filter': 'فلتر الرسائل المعاد توجيهها'
            }
            filter_name = filter_names.get(filter_type, f'الفلتر {filter_type}')
            
            await event.answer(f"✅ {status_text} {filter_name}")
            
            # Return to appropriate menu
            if filter_type == 'day_filter':
                await self.show_day_filters(event, task_id)
            elif filter_type == 'working_hours':
                await self.show_working_hours_filter(event, task_id)
            elif filter_type == 'language_filter':
                await self.show_language_filters(event, task_id)
            elif filter_type == 'admin_filter':
                await self.show_admin_filters(event, task_id)
            elif filter_type == 'duplicate_filter':
                await self.show_duplicate_filter(event, task_id)
            elif filter_type == 'inline_button_filter':
                await self.show_inline_button_filter(event, task_id)
            elif filter_type == 'forwarded_message_filter':
                await self.show_forwarded_message_filter(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث الفلتر")

# Create bot instance
simple_bot = SimpleTelegramBot()

def run_simple_bot():
    """Run the simple bot"""
    asyncio.run(simple_bot.run())

if __name__ == '__main__':
    run_simple_bot()