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
        elif data.startswith("word_filters_"):
            task_id = int(data.split("_")[2])
            await self._show_word_filters(update, context, task_id)
        elif data.startswith("toggle_word_filter_"):
            parts = data.split("_")
            task_id = int(parts[3])
            filter_type = parts[4]
            await self._toggle_word_filter(update, context, task_id, filter_type)
        elif data.startswith("manage_filter_"):
            parts = data.split("_")
            task_id = int(parts[2])
            filter_type = parts[3]
            await self._manage_filter_words(update, context, task_id, filter_type)
        elif data.startswith("view_filter_"):
            parts = data.split("_")
            task_id = int(parts[2])
            filter_type = parts[3]
            await self._view_filter_words(update, context, task_id, filter_type)
        elif data.startswith("add_filter_"):
            parts = data.split("_")
            task_id = int(parts[2])
            filter_type = parts[3]
            await self._start_add_words(update, context, task_id, filter_type)
        elif data.startswith("clear_filter_"):
            parts = data.split("_")
            task_id = int(parts[2])
            filter_type = parts[3]
            await self._clear_filter_confirm(update, context, task_id, filter_type)
        elif data.startswith("confirm_clear_"):
            parts = data.split("_")
            task_id = int(parts[2])
            filter_type = parts[3]
            await self._clear_filter_execute(update, context, task_id, filter_type)
        elif data.startswith("text_replacements_"):
            task_id = int(data.split("_")[2])
            await self._show_text_replacements(update, context, task_id)
        elif data.startswith("toggle_replacement_"):
            task_id = int(data.split("_")[2])
            await self._toggle_text_replacement(update, context, task_id)
        elif data.startswith("watermark_settings_"):
            task_id = int(data.split("_")[2])
            await self._show_watermark_settings(update, context, task_id)
        elif data.startswith("toggle_watermark_"):
            task_id = int(data.split("_")[2])
            await self._toggle_watermark(update, context, task_id)
        elif data.startswith("watermark_config_"):
            task_id = int(data.split("_")[2])
            await self._show_watermark_config(update, context, task_id)
        elif data.startswith("watermark_media_"):
            task_id = int(data.split("_")[2])
            await self._show_watermark_media_settings(update, context, task_id)
        elif data.startswith("toggle_watermark_photos_"):
            task_id = int(data.split("_")[3])
            await self._toggle_watermark_media_type(update, context, task_id, 'photos')
        elif data.startswith("toggle_watermark_videos_"):
            task_id = int(data.split("_")[3])
            await self._toggle_watermark_media_type(update, context, task_id, 'videos')
        elif data.startswith("toggle_watermark_documents_"):
            task_id = int(data.split("_")[3])
            await self._toggle_watermark_media_type(update, context, task_id, 'documents')
        elif data.startswith("add_replacement_"):
            task_id = int(data.split("_")[2])
            await self._start_add_replacement(update, context, task_id)
        elif data.startswith("view_replacements_"):
            task_id = int(data.split("_")[2])
            await self._view_replacements(update, context, task_id)
        elif data.startswith("clear_replacements_"):
            task_id = int(data.split("_")[2])
            await self._clear_replacements_confirm(update, context, task_id)
        elif data.startswith("confirm_clear_replacements_"):
            task_id = int(data.split("_")[3])
            await self._clear_replacements_execute(update, context, task_id)

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
            [InlineKeyboardButton("🔍 فلاتر الكلمات", callback_data=f"word_filters_{task_id}")],
            [InlineKeyboardButton("🔄 استبدال النصوص", callback_data=f"text_replacements_{task_id}")],
            [InlineKeyboardButton("🏷️ العلامة المائية", callback_data=f"watermark_settings_{task_id}")],
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
            f"⚙️ **الميزات المتاحة:**\n"
            f"• 🔍 فلاتر الكلمات (قائمة بيضاء/سوداء)\n"
            f"• 🔄 استبدال النصوص (تعديل المحتوى)\n"
            f"• 🏷️ العلامة المائية (حماية الوسائط)\n"
            f"• 🗑️ إدارة المهمة (حذف/إيقاف)\n\n"
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
            elif state.startswith('waiting_filter_words_'):
                # Handle adding words to filters
                task_id = int(data.split('_')[0])
                filter_type = data.split('_')[1]
                await self._handle_add_words(update, context, task_id, filter_type, message_text)
            elif state == 'waiting_text_replacements':
                # Handle adding text replacements
                task_id = int(data)
                await self._handle_add_replacements(update, context, task_id, message_text)
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

    # Word Filter Methods
    async def _show_word_filters(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Show word filter management interface"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        # Get filter settings and word counts
        settings = self.db.get_task_word_filter_settings(task_id)
        whitelist_words = self.db.get_filter_words(task_id, 'whitelist')
        blacklist_words = self.db.get_filter_words(task_id, 'blacklist')

        whitelist_status = "🟢 مفعل" if settings['whitelist']['enabled'] else "🔴 معطل"
        blacklist_status = "🟢 مفعل" if settings['blacklist']['enabled'] else "🔴 معطل"

        keyboard = [
            [InlineKeyboardButton(f"📝 القائمة البيضاء ({len(whitelist_words)} كلمة)", 
                                callback_data=f"manage_filter_{task_id}_whitelist")],
            [InlineKeyboardButton(f"🚫 القائمة السوداء ({len(blacklist_words)} كلمة)", 
                                callback_data=f"manage_filter_{task_id}_blacklist")],
            [InlineKeyboardButton("🔙 عودة للمهمة", callback_data=f"task_manage_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"🔍 فلاتر الكلمات - المهمة #{task_id}\n\n"
            f"📝 **القائمة البيضاء**: {whitelist_status}\n"
            f"   • عدد الكلمات: {len(whitelist_words)}\n"
            f"   • الوظيفة: السماح بالرسائل التي تحتوي على هذه الكلمات فقط\n\n"
            f"🚫 **القائمة السوداء**: {blacklist_status}\n"
            f"   • عدد الكلمات: {len(blacklist_words)}\n"
            f"   • الوظيفة: منع الرسائل التي تحتوي على هذه الكلمات\n\n"
            f"💡 **ملاحظة**: يمكن تفعيل أو إلغاء تفعيل أي فلتر حسب حاجتك",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _manage_filter_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int, filter_type: str):
        """Manage words for specific filter type"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        # Get filter settings and words
        settings = self.db.get_task_word_filter_settings(task_id)
        filter_words = self.db.get_filter_words(task_id, filter_type)
        is_enabled = settings[filter_type]['enabled']

        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        filter_emoji = "📝" if filter_type == 'whitelist' else "🚫"
        status = "🟢 مفعل" if is_enabled else "🔴 معطل"
        toggle_text = "⏸️ إلغاء التفعيل" if is_enabled else "▶️ تفعيل"

        keyboard = [
            [InlineKeyboardButton(toggle_text, callback_data=f"toggle_word_filter_{task_id}_{filter_type}")],
            [InlineKeyboardButton(f"👀 عرض الكلمات ({len(filter_words)})", 
                                callback_data=f"view_filter_{task_id}_{filter_type}")],
            [InlineKeyboardButton("➕ إضافة كلمات", callback_data=f"add_filter_{task_id}_{filter_type}")],
        ]
        
        if len(filter_words) > 0:
            keyboard.append([InlineKeyboardButton("🗑️ مسح جميع الكلمات", 
                                                callback_data=f"clear_filter_{task_id}_{filter_type}")])
        
        keyboard.append([InlineKeyboardButton("🔙 عودة للفلاتر", callback_data=f"word_filters_{task_id}")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        description = ("السماح بالرسائل التي تحتوي على الكلمات المدرجة فقط" 
                      if filter_type == 'whitelist' 
                      else "منع الرسائل التي تحتوي على الكلمات المدرجة")

        await update.callback_query.edit_message_text(
            f"{filter_emoji} إدارة {filter_name}\n\n"
            f"📊 الحالة: {status}\n"
            f"📝 عدد الكلمات: {len(filter_words)}\n"
            f"🔧 الوظيفة: {description}\n\n"
            f"اختر إجراء:",
            reply_markup=reply_markup
        )

    async def _toggle_word_filter(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int, filter_type: str):
        """Toggle word filter status"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        settings = self.db.get_task_word_filter_settings(task_id)
        current_status = settings[filter_type]['enabled']
        new_status = not current_status
        
        # Update filter status
        self.db.set_word_filter_status(task_id, filter_type, new_status)
        
        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        
        await update.callback_query.answer(f"✅ {status_text} {filter_name}")
        await self._manage_filter_words(update, context, task_id, filter_type)

    async def _view_filter_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int, filter_type: str):
        """View words in a filter"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        filter_words = self.db.get_filter_words(task_id, filter_type)
        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        filter_emoji = "📝" if filter_type == 'whitelist' else "🚫"

        if not filter_words:
            message = f"{filter_emoji} {filter_name}\n\n❌ لا توجد كلمات مدرجة حالياً"
        else:
            message = f"{filter_emoji} {filter_name}\n\n📋 الكلمات المدرجة ({len(filter_words)}):\n\n"
            for i, word_data in enumerate(filter_words[:20], 1):  # Show max 20 words
                word = word_data[2]  # word_or_phrase from tuple
                message += f"{i}. {word}\n"
            
            if len(filter_words) > 20:
                message += f"\n... و {len(filter_words) - 20} كلمة أخرى"

        keyboard = [
            [InlineKeyboardButton("➕ إضافة كلمات", callback_data=f"add_filter_{task_id}_{filter_type}")],
            [InlineKeyboardButton("🔙 عودة للإدارة", callback_data=f"manage_filter_{task_id}_{filter_type}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(message, reply_markup=reply_markup)

    async def _start_add_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int, filter_type: str):
        """Start adding words to filter"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        
        # Set conversation state
        state_data = f"{task_id}_{filter_type}"
        self.db.set_conversation_state(user_id, f'waiting_filter_words_{filter_type}', state_data)

        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data=f"manage_filter_{task_id}_{filter_type}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"➕ إضافة كلمات إلى {filter_name}\n\n"
            f"📝 أرسل الكلمات أو العبارات التي تريد إضافتها:\n\n"
            f"💡 **طرق الإدخال المتاحة:**\n"
            f"• كل كلمة في سطر منفصل\n"
            f"• فصل بين الكلمات بفواصل (،)\n"
            f"• يمكن إدخال عبارات متكاملة\n\n"
            f"**مثال:**\n"
            f"كلمة واحدة\n"
            f"كلمة ثانية، كلمة ثالثة\n"
            f"عبارة متكاملة\n\n"
            f"⚠️ **ملاحظة**: الكلمات المكررة لن تتم إضافتها مرة أخرى",
            reply_markup=reply_markup
        )

    async def _handle_add_words(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                               task_id: int, filter_type: str, message_text: str):
        """Handle adding words to filter"""
        user_id = update.effective_user.id
        
        # Parse words from message
        words_to_add = []
        
        # Split by lines first, then by commas
        lines = message_text.split('\n')
        for line in lines:
            line = line.strip()
            if line:
                # Split by comma and clean up
                words_in_line = [word.strip() for word in line.split('،')]
                words_to_add.extend([word for word in words_in_line if word])
        
        if not words_to_add:
            await update.message.reply_text(
                "❌ لم يتم العثور على كلمات للإضافة. حاول مرة أخرى."
            )
            return

        # Add words to filter
        added_count = self.db.add_multiple_filter_words(task_id, filter_type, words_to_add)
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        
        keyboard = [
            [InlineKeyboardButton("👀 عرض الكلمات", callback_data=f"view_filter_{task_id}_{filter_type}")],
            [InlineKeyboardButton("➕ إضافة المزيد", callback_data=f"add_filter_{task_id}_{filter_type}")],
            [InlineKeyboardButton("🔙 عودة للإدارة", callback_data=f"manage_filter_{task_id}_{filter_type}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ تم إضافة {added_count} كلمة إلى {filter_name}\n\n"
            f"📊 إجمالي الكلمات المرسلة: {len(words_to_add)}\n"
            f"📝 الكلمات المضافة: {added_count}\n"
            f"🔄 الكلمات المكررة: {len(words_to_add) - added_count}\n\n"
            f"✅ الفلتر جاهز للاستخدام!",
            reply_markup=reply_markup
        )

    async def _clear_filter_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   task_id: int, filter_type: str):
        """Confirm clearing filter"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        filter_words = self.db.get_filter_words(task_id, filter_type)
        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"

        keyboard = [
            [InlineKeyboardButton("✅ نعم، احذف الكل", callback_data=f"confirm_clear_{task_id}_{filter_type}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data=f"manage_filter_{task_id}_{filter_type}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"⚠️ تأكيد حذف {filter_name}\n\n"
            f"🗑️ هل أنت متأكد من حذف جميع الكلمات ({len(filter_words)} كلمة)؟\n\n"
            f"❌ **تحذير**: هذا الإجراء لا يمكن التراجع عنه!\n\n"
            f"سيتم حذف جميع الكلمات من {filter_name} نهائياً.",
            reply_markup=reply_markup
        )

    async def _clear_filter_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                   task_id: int, filter_type: str):
        """Execute filter clearing"""
        user_id = update.effective_user.id
        
        # Clear all words from filter
        filter_id = self.db.get_word_filter_id(task_id, filter_type)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM word_filter_entries WHERE filter_id = ?', (filter_id,))
            deleted_count = cursor.rowcount
            conn.commit()
        
        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
        
        await update.callback_query.answer(f"✅ تم حذف {deleted_count} كلمة من {filter_name}")
        await self._manage_filter_words(update, context, task_id, filter_type)

    # Text Replacement Management Functions
    async def _show_text_replacements(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Show text replacement management interface"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        # Get replacement settings and count
        is_enabled = self.db.is_text_replacement_enabled(task_id)
        replacements = self.db.get_text_replacements(task_id)
        
        status = "🟢 مفعل" if is_enabled else "🔴 معطل"
        toggle_text = "⏸️ إلغاء التفعيل" if is_enabled else "▶️ تفعيل"

        keyboard = [
            [InlineKeyboardButton(toggle_text, callback_data=f"toggle_replacement_{task_id}")],
            [InlineKeyboardButton(f"➕ إضافة استبدالات", callback_data=f"add_replacement_{task_id}")],
            [InlineKeyboardButton(f"👀 عرض الاستبدالات ({len(replacements)})", callback_data=f"view_replacements_{task_id}")],
            [InlineKeyboardButton("🗑️ إفراغ الاستبدالات", callback_data=f"clear_replacements_{task_id}")],
            [InlineKeyboardButton("🔙 عودة للمهمة", callback_data=f"task_manage_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"🔄 استبدال النصوص - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"📝 **عدد الاستبدالات**: {len(replacements)}\n\n"
            f"🔄 **الوظيفة**: استبدال كلمات أو عبارات محددة في الرسائل قبل توجيهها إلى الهدف\n\n"
            f"💡 **مثال**: استبدال 'مرحبا' بـ 'أهلا وسهلا' في جميع الرسائل\n\n"
            f"⚠️ **ملاحظة**: عند تفعيل الاستبدال، سيتم تحويل وضع التوجيه تلقائياً إلى 'نسخ' للرسائل المعدلة",
            reply_markup=reply_markup
        )

    # Watermark Management Functions
    async def _show_watermark_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Show watermark settings management interface"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        # Get watermark settings
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        status = "🟢 مفعل" if watermark_settings.get('enabled', False) else "🔴 معطل"
        toggle_text = "⏸️ إلغاء التفعيل" if watermark_settings.get('enabled', False) else "▶️ تفعيل"
        
        watermark_type = watermark_settings.get('watermark_type', 'text')
        type_display = "📝 نص" if watermark_type == 'text' else "🖼️ صورة"
        
        position_names = {
            'top_left': 'أعلى اليسار',
            'top_right': 'أعلى اليمين',
            'bottom_left': 'أسفل اليسار',
            'bottom_right': 'أسفل اليمين',
            'center': 'الوسط'
        }
        position_display = position_names.get(watermark_settings.get('position', 'bottom_right'), 'أسفل اليمين')

        keyboard = [
            [InlineKeyboardButton(toggle_text, callback_data=f"toggle_watermark_{task_id}")],
            [InlineKeyboardButton("⚙️ إعدادات العلامة", callback_data=f"watermark_config_{task_id}")],
            [InlineKeyboardButton("📱 اختيار الوسائط", callback_data=f"watermark_media_{task_id}")],
            [InlineKeyboardButton("🔙 عودة للمهمة", callback_data=f"task_manage_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Build media settings display
        media_settings = []
        if watermark_settings.get('apply_to_photos', True):
            media_settings.append("📷 الصور")
        if watermark_settings.get('apply_to_videos', True):
            media_settings.append("🎥 الفيديوهات")
        if watermark_settings.get('apply_to_documents', False):
            media_settings.append("📄 المستندات")
        
        media_display = " • ".join(media_settings) if media_settings else "لا يوجد"

        await update.callback_query.edit_message_text(
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
            reply_markup=reply_markup
        )

    async def _toggle_watermark(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Toggle watermark status"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        # Toggle watermark
        new_status = self.db.toggle_watermark(task_id)
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        
        await update.callback_query.answer(f"✅ {status_text} العلامة المائية")
        await self._show_watermark_settings(update, context, task_id)

    async def _show_watermark_config(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Show watermark configuration options"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        keyboard = [
            [InlineKeyboardButton("📝 تعديل النص", callback_data=f"watermark_text_{task_id}")],
            [InlineKeyboardButton("🖼️ رفع صورة", callback_data=f"watermark_image_{task_id}")],
            [InlineKeyboardButton("📍 تغيير الموقع", callback_data=f"watermark_position_{task_id}")],
            [InlineKeyboardButton("🎨 إعدادات المظهر", callback_data=f"watermark_appearance_{task_id}")],
            [InlineKeyboardButton("🔙 عودة للعلامة المائية", callback_data=f"watermark_settings_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"⚙️ تكوين العلامة المائية - المهمة #{task_id}\n\n"
            f"🔧 **خيارات التكوين المتاحة:**\n\n"
            f"📝 **تعديل النص**: تحديد النص المراد إظهاره كعلامة مائية\n"
            f"🖼️ **رفع صورة**: استخدام صورة كعلامة مائية (PNG مفضل)\n"
            f"📍 **تغيير الموقع**: اختيار مكان العلامة على الوسائط\n"
            f"🎨 **إعدادات المظهر**: تخصيص الحجم والشفافية واللون\n\n"
            f"💡 **نصيحة**: يُفضل استخدام صور PNG شفافة للحصول على أفضل نتيجة",
            reply_markup=reply_markup
        )

    async def _show_watermark_media_settings(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Show watermark media type settings"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        # Get current settings
        watermark_settings = self.db.get_watermark_settings(task_id)
        
        photos_enabled = watermark_settings.get('apply_to_photos', True)
        videos_enabled = watermark_settings.get('apply_to_videos', True)
        documents_enabled = watermark_settings.get('apply_to_documents', False)
        
        photos_text = "✅ الصور" if photos_enabled else "❌ الصور"
        videos_text = "✅ الفيديوهات" if videos_enabled else "❌ الفيديوهات"
        documents_text = "✅ المستندات" if documents_enabled else "❌ المستندات"

        keyboard = [
            [InlineKeyboardButton(photos_text, callback_data=f"toggle_watermark_photos_{task_id}")],
            [InlineKeyboardButton(videos_text, callback_data=f"toggle_watermark_videos_{task_id}")],
            [InlineKeyboardButton(documents_text, callback_data=f"toggle_watermark_documents_{task_id}")],
            [InlineKeyboardButton("🔙 عودة للعلامة المائية", callback_data=f"watermark_settings_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"📱 اختيار الوسائط للعلامة المائية - المهمة #{task_id}\n\n"
            f"📋 **حدد أنواع الوسائط التي تريد تطبيق العلامة المائية عليها:**\n\n"
            f"📷 **الصور**: JPG, PNG, WebP وغيرها\n"
            f"🎥 **الفيديوهات**: MP4, AVI, MOV وغيرها\n"
            f"📄 **المستندات**: ملفات الصور في شكل مستندات\n\n"
            f"⚠️ **ملاحظة**: معالجة الفيديوهات قد تستغرق وقتاً أطول\n\n"
            f"✅ = مفعل  ❌ = معطل",
            reply_markup=reply_markup
        )

    async def _toggle_watermark_media_type(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                           task_id: int, media_type: str):
        """Toggle watermark application for specific media type"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        # Toggle media type setting
        field_map = {
            'photos': 'apply_to_photos',
            'videos': 'apply_to_videos', 
            'documents': 'apply_to_documents'
        }
        
        field_name = field_map.get(media_type)
        if not field_name:
            await update.callback_query.answer("❌ نوع وسائط غير صالح")
            return

        new_status = self.db.toggle_watermark_media_type(task_id, field_name)
        
        media_names = {
            'photos': 'الصور',
            'videos': 'الفيديوهات',
            'documents': 'المستندات'
        }
        
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        media_name = media_names.get(media_type, media_type)
        
        await update.callback_query.answer(f"✅ {status_text} العلامة المائية لـ {media_name}")
        await self._show_watermark_media_settings(update, context, task_id)

    async def _toggle_text_replacement(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Toggle text replacement status"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        current_status = self.db.is_text_replacement_enabled(task_id)
        new_status = not current_status
        
        # Update replacement status
        self.db.set_text_replacement_enabled(task_id, new_status)
        
        status_text = "تم تفعيل" if new_status else "تم إلغاء تفعيل"
        
        await update.callback_query.answer(f"✅ {status_text} استبدال النصوص")
        await self._show_text_replacements(update, context, task_id)

    async def _start_add_replacement(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Start adding text replacements"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_text_replacements', str(task_id))

        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data=f"text_replacements_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
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
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _handle_add_replacements(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                     task_id: int, message_text: str):
        """Handle adding text replacements"""
        user_id = update.effective_user.id
        
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
            await update.message.reply_text(
                "❌ لم يتم العثور على استبدالات صحيحة. تأكد من استخدام التنسيق:\n"
                "`النص_الأصلي >> النص_الجديد`"
            )
            return

        # Add replacements to database
        added_count = self.db.add_multiple_text_replacements(task_id, replacements_to_add)
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        keyboard = [
            [InlineKeyboardButton("👀 عرض الاستبدالات", callback_data=f"view_replacements_{task_id}")],
            [InlineKeyboardButton("➕ إضافة المزيد", callback_data=f"add_replacement_{task_id}")],
            [InlineKeyboardButton("🔙 عودة للإدارة", callback_data=f"text_replacements_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ تم إضافة {added_count} استبدال نصي\n\n"
            f"📊 إجمالي الاستبدالات المرسلة: {len(replacements_to_add)}\n"
            f"📝 الاستبدالات المضافة: {added_count}\n"
            f"🔄 الاستبدالات المكررة: {len(replacements_to_add) - added_count}\n\n"
            f"✅ استبدال النصوص جاهز للاستخدام!",
            reply_markup=reply_markup
        )

    async def _view_replacements(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """View text replacements"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
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

        keyboard = [
            [InlineKeyboardButton("➕ إضافة استبدالات", callback_data=f"add_replacement_{task_id}")],
            [InlineKeyboardButton("🔙 عودة للإدارة", callback_data=f"text_replacements_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            message, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    async def _clear_replacements_confirm(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Confirm clearing text replacements"""
        user_id = update.effective_user.id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await update.callback_query.answer("❌ المهمة غير موجودة")
            return

        replacements = self.db.get_text_replacements(task_id)

        keyboard = [
            [InlineKeyboardButton("✅ نعم، احذف الكل", callback_data=f"confirm_clear_replacements_{task_id}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data=f"text_replacements_{task_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.callback_query.edit_message_text(
            f"⚠️ تأكيد حذف الاستبدالات النصية\n\n"
            f"🗑️ هل أنت متأكد من حذف جميع الاستبدالات ({len(replacements)} استبدال)؟\n\n"
            f"❌ **تحذير**: هذا الإجراء لا يمكن التراجع عنه!\n\n"
            f"سيتم حذف جميع استبدالات النصوص نهائياً.",
            reply_markup=reply_markup
        )

    async def _clear_replacements_execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE, task_id: int):
        """Execute clearing text replacements"""
        user_id = update.effective_user.id
        
        # Clear all replacements
        deleted_count = self.db.clear_text_replacements(task_id)
        
        await update.callback_query.answer(f"✅ تم حذف جميع الاستبدالات النصية")
        await self._show_text_replacements(update, context, task_id)