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
                    task_id = int(parts[2])
                    await self.toggle_task(event, task_id)
            elif data.startswith("task_delete_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = int(parts[2])
                    await self.delete_task(event, task_id)
            elif data.startswith("task_manage_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = int(parts[2])
                    await self.show_task_details(event, task_id)
            elif data.startswith("task_settings_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = int(parts[2])
                    await self.show_task_settings(event, task_id)
            elif data.startswith("toggle_forward_mode_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    task_id = int(parts[3])
                    await self.toggle_forward_mode(event, task_id)
            elif data.startswith("manage_sources_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = int(parts[2])
                    await self.manage_task_sources(event, task_id)
            elif data.startswith("manage_targets_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = int(parts[2])
                    await self.manage_task_targets(event, task_id)
            elif data.startswith("add_source_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = int(parts[2])
                    await self.start_add_source(event, task_id)
            elif data.startswith("add_target_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = int(parts[2])
                    await self.start_add_target(event, task_id)
            elif data.startswith("remove_source_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    source_id = int(parts[2])
                    task_id = int(parts[3])
                    await self.remove_source(event, source_id, task_id)
            elif data.startswith("remove_target_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    target_id = int(parts[2])
                    task_id = int(parts[3])
                    await self.remove_target(event, target_id, task_id)
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
            elif data.startswith("media_filters_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    task_id = int(parts[2])
                    await self.show_media_filters(event, task_id)
            elif data.startswith("toggle_media_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    task_id = int(parts[2])
                    media_type = parts[3]
                    await self.toggle_media_filter(event, task_id, media_type)
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

        except Exception as e:
            logger.error(f"خطأ في معالج الأزرار: {e}")
            await event.answer("❌ حدث خطأ، حاول مرة أخرى")

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

            # If this chat is a target chat, don't respond
            if target_tasks:
                logger.info(f"🚫 تجاهل الرسالة في المحادثة الهدف {chat_id}")
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

        buttons = [
            [Button.inline(f"🔄 تغيير وضع التوجيه ({forward_mode_text})", f"toggle_forward_mode_{task_id}")],
            [Button.inline(f"📥 إدارة المصادر ({sources_count})", f"manage_sources_{task_id}")],
            [Button.inline(f"📤 إدارة الأهداف ({targets_count})", f"manage_targets_{task_id}")],
            [Button.inline("🎬 فلاتر الوسائط", f"media_filters_{task_id}")],
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
            await event.answer("✅ تم تغيير وضع التوجيه إلى {mode_text}")

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

    async def run(self):
        """Run the bot"""
        logger.info("🚀 بدء تشغيل نظام بوت تليجرام...")

        if await self.start():
            logger.info("✅ البوت يعمل الآن...")
            await self.bot.run_until_disconnected()
        else:
            logger.error("❌ فشل في تشغيل البوت")

# Create bot instance
simple_bot = SimpleTelegramBot()

def run_simple_bot():
    """Run the simple bot"""
    asyncio.run(simple_bot.run())

if __name__ == '__main__':
    run_simple_bot()