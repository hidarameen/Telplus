"""
Task Management Handler for Telegram Bot
"""
import logging
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.database import Database
from userbot_service.userbot import userbot_instance

logger = logging.getLogger(__name__)

class TaskHandler:
    def __init__(self):
        self.db = Database()

    async def show_tasks_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show tasks management menu"""
        user_id = update.effective_user.id
        tasks = self.db.get_user_tasks(user_id)

        keyboard = [
            [InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data="create_task")],
            [InlineKeyboardButton("📋 عرض المهام", callback_data="list_tasks")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        tasks_count = len(tasks)
        active_count = len([t for t in tasks if t['is_active']])

        await update.callback_query.edit_message_text(
            f"📝 إدارة مهام التوجيه\n\n"
            f"📊 الإحصائيات:\n"
            f"• إجمالي المهام: {tasks_count}\n"
            f"• المهام النشطة: {active_count}\n"
            f"• المهام المتوقفة: {tasks_count - active_count}\n\n"
            f"اختر إجراء:",
            reply_markup=reply_markup
        )

    async def start_create_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start creating new task"""
        user_id = update.effective_user.id

        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_source_chat')

        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data="manage_tasks")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            "➕ إنشاء مهمة توجيه جديدة\n\n"
            "📥 **الخطوة 1: تحديد المصدر**\n\n"
            "أرسل معرف أو رابط المجموعة/القناة المصدر:\n\n"
            "أمثلة:\n"
            "• @channelname\n"
            "• https://t.me/channelname\n"
            "• -1001234567890\n\n"
            "⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات قراءة الرسائل",
            reply_markup=reply_markup
        )

    async def list_tasks(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """List user tasks"""
        user_id = update.effective_user.id
        tasks = self.db.get_user_tasks(user_id)

        if not tasks:
            keyboard = [
                [InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data="create_task")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.callback_query.edit_message_text(
                "📋 قائمة المهام\n\n"
                "❌ لا توجد مهام حالياً\n\n"
                "أنشئ مهمتك الأولى للبدء!",
                reply_markup=reply_markup
            )
            return

        # Build tasks list
        message = "📋 قائمة المهام:\n\n"
        keyboard = []

        for i, task in enumerate(tasks[:10], 1):  # Show max 10 tasks
            status = "🟢 نشطة" if task['is_active'] else "🔴 متوقفة"
            message += f"{i}. {status}\n"
            message += f"   📥 من: {task['source_chat_name'] or task['source_chat_id']}\n"
            message += f"   📤 إلى: {task['target_chat_name'] or task['target_chat_id']}\n\n"

            # Add task button
            keyboard.append([
                InlineKeyboardButton(
                    f"⚙️ مهمة {i}", 
                    callback_data=f"task_manage_{task['id']}"
                )
            ])

        keyboard.append([InlineKeyboardButton("➕ إنشاء مهمة جديدة", callback_data="create_task")])
        keyboard.append([InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            message,
            reply_markup=reply_markup
        )

    async def handle_task_action(self, update: Update, context: ContextTypes.DEFAULT_TYPE, data: str):
        """Handle task actions"""
        user_id = update.effective_user.id

        if data.startswith("task_manage_"):
            task_id = int(data.split("_")[2])
            await self._show_task_details(update, context, task_id)
        elif data.startswith("task_toggle_"):
            task_id = int(data.split("_")[2])
            await self._toggle_task_status(update, context, task_id)
        elif data.startswith("task_delete_"):
            task_id = int(data.split("_")[2])
            await self._delete_task(update, context, task_id)

    async def _show_task_details(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Show task details"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        status = "🟢 نشطة" if task['is_active'] else "🔴 متوقفة"
        toggle_text = "⏸️ إيقاف" if task['is_active'] else "▶️ تشغيل"
        toggle_action = f"task_toggle_{task_id}"

        keyboard = [
            [InlineKeyboardButton(toggle_text, callback_data=toggle_action)],
            [InlineKeyboardButton("🗑️ حذف المهمة", callback_data=f"task_delete_{task_id}")],
            [InlineKeyboardButton("📋 عرض المهام", callback_data="list_tasks")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"⚙️ تفاصيل المهمة #{task['id']}\n\n"
            f"📊 الحالة: {status}\n\n"
            f"📥 **المصدر:**\n"
            f"• اسم: {task['source_chat_name'] or 'غير محدد'}\n"
            f"• معرف: `{task['source_chat_id']}`\n\n"
            f"📤 **الوجهة:**\n"
            f"• اسم: {task['target_chat_name'] or 'غير محدد'}\n"
            f"• معرف: `{task['target_chat_id']}`\n\n"
            f"📅 تاريخ الإنشاء: {task['created_at'][:16]}",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _toggle_task_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Toggle task status"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        new_status = not task['is_active']
        self.db.update_task_status(task_id, user_id, new_status)

        # Update userbot tasks
        await userbot_instance.refresh_user_tasks(user_id)

        status_text = "تم تشغيل" if new_status else "تم إيقاف"
        await update.callback_query.answer(f"✅ {status_text} المهمة بنجاح")

        # Refresh task details
        await self._show_task_details(update, context, task_id)

    async def _delete_task(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Delete task"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)

        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        self.db.delete_task(task_id, user_id)

        # Update userbot tasks
        await userbot_instance.refresh_user_tasks(user_id)

        await update.callback_query.answer("✅ تم حذف المهمة بنجاح")
        await self.list_tasks(update, context)

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle task creation messages"""
        user_id = update.effective_user.id
        state_data = self.db.get_conversation_state(user_id)

        if not state_data:
            return False

        state, data = state_data
        message_text = update.message.text.strip()

        try:
            if state == 'waiting_source_chat':
                await self._handle_source_chat(update, context, message_text)
            elif state == 'waiting_target_chat':
                await self._handle_target_chat(update, context, message_text, data)
            else:
                return False
        except Exception as e:
            logger.error(f"خطأ في إنشاء المهمة للمستخدم {user_id}: {e}")
            await update.message.reply_text(
                "❌ حدث خطأ أثناء إنشاء المهمة. حاول مرة أخرى."
            )
            self.db.clear_conversation_state(user_id)

        return True

    async def _handle_source_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE, chat_input: str):
        """Handle source chat input"""
        user_id = update.effective_user.id

        # Parse chat input
        source_chat_id, source_chat_name = await self._parse_chat_input(chat_input)

        if not source_chat_id:
            await update.message.reply_text(
                "❌ تنسيق معرف المجموعة/القناة غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890"
            )
            return

        # Store source chat data
        task_data = {
            'source_chat_id': source_chat_id,
            'source_chat_name': source_chat_name
        }
        self.db.set_conversation_state(user_id, 'waiting_target_chat', json.dumps(task_data))

        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data="manage_tasks")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ تم تحديد المصدر: {source_chat_name or source_chat_id}\n\n"
            f"📤 **الخطوة 2: تحديد الوجهة**\n\n"
            f"أرسل معرف أو رابط المجموعة/القناة المراد توجيه الرسائل إليها:\n\n"
            f"أمثلة:\n"
            f"• @targetchannel\n"
            f"• https://t.me/targetchannel\n"
            f"• -1001234567890\n\n"
            f"⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات إرسال الرسائل",
            reply_markup=reply_markup
        )

    async def _handle_target_chat(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                 chat_input: str, data: str):
        """Handle target chat input"""
        user_id = update.effective_user.id

        # Parse target chat
        target_chat_id, target_chat_name = await self._parse_chat_input(chat_input)

        if not target_chat_id:
            await update.message.reply_text(
                "❌ تنسيق معرف المجموعة/القناة غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890"
            )
            return

        # Get source chat data
        task_data = json.loads(data)
        source_chat_id = task_data['source_chat_id']
        source_chat_name = task_data['source_chat_name']

        # Create task in database
        task_id = self.db.create_task(
            user_id, 
            source_chat_id, 
            source_chat_name,
            target_chat_id, 
            target_chat_name
        )

        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        # Update userbot tasks and ensure UserBot is running
        if user_id not in userbot_instance.clients:
            # Try to start UserBot if not running
            session_data = self.db.get_user_session(user_id)
            if session_data and session_data[2]:  # session_string exists
                logger.info(f"🔄 بدء تشغيل UserBot للمستخدم {user_id} عند إنشاء مهمة")
                await userbot_instance.start_with_session(user_id, session_data[2])

        await userbot_instance.refresh_user_tasks(user_id)

        keyboard = [
            [InlineKeyboardButton("📋 عرض المهام", callback_data="list_tasks")],
            [InlineKeyboardButton("➕ إنشاء مهمة أخرى", callback_data="create_task")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🎉 تم إنشاء المهمة بنجاح!\n\n"
            f"🆔 رقم المهمة: #{task_id}\n"
            f"📥 من: {source_chat_name or source_chat_id}\n"
            f"📤 إلى: {target_chat_name or target_chat_id}\n"
            f"🟢 الحالة: نشطة\n\n"
            f"✅ سيتم توجيه جميع الرسائل الجديدة تلقائياً",
            reply_markup=reply_markup
        )

    async def _parse_chat_input(self, chat_input: str) -> tuple:
        """Parse chat input and return chat_id and name"""
        chat_input = chat_input.strip()

        if chat_input.startswith('@'):
            # Username format
            username = chat_input[1:]
            return chat_input, username
        elif chat_input.startswith('https://t.me/'):
            # URL format
            username = chat_input.split('/')[-1]
            return f"@{username}", username
        elif chat_input.startswith('-') and chat_input[1:].isdigit():
            # Chat ID format
            return chat_input, None
        else:
            # Try to parse as numeric ID
            try:
                chat_id = int(chat_input)
                return str(chat_id), None
            except ValueError:
                return None, None