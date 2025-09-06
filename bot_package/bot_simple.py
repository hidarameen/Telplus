"""
Simple Telegram Bot using Telethon
Handles bot API and user API functionality
"""
import logging
import asyncio
from telethon import TelegramClient, events
from telethon.tl.custom import Button
from telethon.tl import types as tl_types
from telethon.utils import get_peer_id
from database.channels_db import ChannelsDatabase
from telethon.sessions import StringSession
from database import get_database
from userbot_service.userbot import userbot_instance
from bot_package.config import BOT_TOKEN, API_ID, API_HASH
import json
import time
import os
from datetime import datetime
from channels_management import ChannelsManagement

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class SimpleTelegramBot:
    def __init__(self):
        # استخدام مصنع قاعدة البيانات
        self.db = get_database()
        
        # معلومات قاعدة البيانات
        from database import DatabaseFactory
        self.db_info = DatabaseFactory.get_database_info()
        
        logger.info(f"🗄️ تم تهيئة قاعدة البيانات: {self.db_info['name']}")
        
        self.bot = None
        self.conversation_states = {}
        self.user_states = {}  # For handling user input states
        self.user_messages = {}  # Track user messages for editing: {user_id: {message_id, chat_id, timestamp}}
        
        # تهيئة مدير وضع النشر
        from .publishing_mode_manager import PublishingModeManager
        self.publishing_manager = PublishingModeManager(self)
        
        # Initialize Channels Management
        self.channels_management = ChannelsManagement(self)

    def set_user_state(self, user_id, state, data=None):
        """Set user conversation state"""
        self.user_states[user_id] = {'state': state, 'data': data or {}}
    
    def get_user_state(self, user_id):
        """Get user conversation state"""
        return self.user_states.get(user_id, {}).get('state', None)
        
    def get_user_data(self, user_id):
        """Get user conversation data"""
        return self.user_states.get(user_id, {}).get('data', {})
    
    def clear_user_state(self, user_id):
        """Clear user conversation state"""
        self.user_states.pop(user_id, None)
    
    def extract_task_id_from_data(self, data):
        """Extract task_id from conversation state data (handles both dict and string)"""
        if isinstance(data, dict):
            # PostgreSQL wraps string data in {"data": "value"}
            return int(data.get('data', 0))
        else:
            # SQLite returns raw string
            return int(data) if data else 0

    def track_user_message(self, user_id, message_id, chat_id):
        """Track a message sent to user for potential editing"""
        self.user_messages[user_id] = {
            'message_id': message_id,
            'chat_id': chat_id,
            'timestamp': time.time()
        }

    def get_user_message(self, user_id):
        """Get the last message sent to user"""
        return self.user_messages.get(user_id)

    def clear_user_message(self, user_id):
        """Clear tracked message for user"""
        self.user_messages.pop(user_id, None)

    async def delete_previous_message(self, user_id):
        """Delete the previous tracked message for user"""
        if user_id in self.user_messages:
            try:
                tracked_msg = self.user_messages[user_id]
                if hasattr(self, 'bot') and self.bot:
                    await self.bot.delete_messages(tracked_msg['chat_id'], tracked_msg['message_id'])
                    logger.debug(f"🗑️ تم حذف الرسالة السابقة للمستخدم {user_id}")
            except Exception as e:
                logger.warning(f"فشل في حذف الرسالة السابقة للمستخدم {user_id}: {e}")
            finally:
                self.user_messages.pop(user_id, None)

    async def force_new_message(self, event, text, buttons=None):
        """Force send a new message and delete the previous one"""
        user_id = event.sender_id
        # Detect if this is a callback (button press)
        is_callback = False
        try:
            from telethon import events as _events
            is_callback = isinstance(event, _events.CallbackQuery.Event)
        except Exception:
            # Fallback heuristic
            is_callback = hasattr(event, 'query') and hasattr(event, 'edit')

        if is_callback:
            # For button presses: do NOT delete/resend, just edit in place
            try:
                # Answer the callback to remove the loading state (best-effort)
                if hasattr(event, 'answer'):
                    await event.answer()
            except Exception:
                pass
            return await self.edit_or_send_message(event, text, buttons, force_new=False)

        # For text messages and others: delete previous and send new
        await self.delete_previous_message(user_id)
        return await self.edit_or_send_message(event, text, buttons, force_new=True)

    # ===== Channels Management Delegates =====
    async def show_channels_menu(self, event):
        return await self.channels_management.show_channels_menu(event)

    async def start_add_channel(self, event):
        return await self.channels_management.start_add_channel(event)

    async def start_add_multiple_channels(self, event):
        return await self.channels_management.start_add_multiple_channels(event)

    async def finish_add_channels(self, event):
        return await self.channels_management.finish_add_channels(event)

    async def list_channels(self, event):
        return await self.channels_management.list_channels(event)

    async def delete_channel(self, event, channel_id: int):
        return await self.channels_management.delete_channel(event, channel_id)

    async def edit_channel(self, event, channel_id: int):
        return await self.channels_management.edit_channel(event, channel_id)

    async def refresh_channel_info(self, event, channel_id: int):
        return await self.channels_management.refresh_channel_info(event, channel_id)

    async def edit_or_send_message(self, event, text, buttons=None, force_new=False):
        """Edit existing message or send new one with improved logic"""
        user_id = event.sender_id
        
        # Detect if this is a callback (button press)
        is_callback = False
        try:
            from telethon import events as _events
            is_callback = isinstance(event, _events.CallbackQuery.Event)
        except Exception:
            # Fallback heuristic
            is_callback = hasattr(event, 'query') and hasattr(event, 'edit')

        # If this is a callback and not forcing a new message, prefer editing the callback message directly
        if not force_new and is_callback:
            try:
                # Best-effort: answer callback to clear the loader
                if hasattr(event, 'answer'):
                    await event.answer()
            except Exception:
                pass
            try:
                # Prefer editing the message that triggered the callback
                if hasattr(event, 'edit'):
                    await event.edit(text, buttons=buttons)
                    # Ensure tracking points to the same message (keeps the panel consistent)
                    try:
                        msg_id = getattr(event.message, 'id', None)
                        chat_id = getattr(event, 'chat_id', None) or getattr(event.message, 'chat_id', None)
                        if msg_id and chat_id:
                            self.track_user_message(user_id, msg_id, chat_id)
                    except Exception:
                        pass
                    logger.debug(f"✅ تم تعديل رسالة اللوحة من خلال الرد على الزر للمستخدم {user_id}")
                    return None
            except Exception as e:
                logger.warning(f"تعذر تعديل رسالة رد الفعل مباشرة، المحاولة عبر tracked message: {e}")

        # Always try to edit tracked message first unless force_new is True
        if not force_new and user_id in self.user_messages:
            try:
                tracked_msg = self.user_messages[user_id]
                # Check if message is not too old (10 minutes instead of 5)
                if time.time() - tracked_msg['timestamp'] < 600 and hasattr(self, 'bot') and self.bot:
                    await self.bot.edit_message(
                        tracked_msg['chat_id'],
                        tracked_msg['message_id'],
                        text,
                        buttons=buttons
                    )
                    # Update timestamp
                    tracked_msg['timestamp'] = time.time()
                    logger.debug(f"✅ تم تعديل الرسالة للمستخدم {user_id}")
                    return None  # No new message object returned for edits
                else:
                    logger.debug(f"📝 الرسالة قديمة جداً، إرسال رسالة جديدة للمستخدم {user_id}")
            except Exception as e:
                logger.warning(f"فشل في تعديل الرسالة للمستخدم {user_id}: {e}")
        
        # Send new message if edit fails or force_new is True
        try:
            message = await event.respond(text, buttons=buttons)
            self.track_user_message(user_id, message.id, event.chat_id)
            logger.debug(f"📤 تم إرسال رسالة جديدة للمستخدم {user_id}")
            return message
        except Exception as e:
            logger.error(f"فشل في إرسال رسالة جديدة للمستخدم {user_id}: {e}")
            return None

    async def start(self):
        """Start the bot"""
        if not BOT_TOKEN or BOT_TOKEN == 'your_bot_token_here':
            logger.error("❌ BOT_TOKEN غير محدد في متغيرات البيئة")
            return False

        # Create bot client with session file in persistent directory
        import os
        import stat
        data_dir = os.getenv('DATA_DIR', '/app/data')
        sessions_dir = os.getenv('SESSIONS_DIR', os.path.join(data_dir, 'sessions'))
        try:
            os.makedirs(sessions_dir, exist_ok=True)
        except Exception:
            pass
        session_name_path = os.path.join(sessions_dir, 'simple_bot_session')
        self.bot = TelegramClient(session_name_path, API_ID, API_HASH)
        await self.bot.start(bot_token=BOT_TOKEN)
        
        # Ensure session file has correct permissions after creation
        session_file = session_name_path if session_name_path.endswith('.session') else f'{session_name_path}.session'
        if os.path.exists(session_file):
            os.chmod(session_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)  # 666
            logger.info(f"✅ تم تصحيح صلاحيات ملف الجلسة: {session_file}")
        
        # Also fix any journal files
        journal_file = f'{session_file}-journal'
        if os.path.exists(journal_file):
            os.chmod(journal_file, stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)  # 666
            logger.info(f"✅ تم تصحيح صلاحيات ملف journal: {journal_file}")

        # Add event handlers
        self.bot.add_event_handler(self.handle_start, events.NewMessage(pattern='/start'))
        self.bot.add_event_handler(self.handle_login, events.NewMessage(pattern='/login'))
        self.bot.add_event_handler(self.handle_callback, events.CallbackQuery())
        self.bot.add_event_handler(self.handle_message, events.NewMessage())

        # Start notification monitoring task
        asyncio.create_task(self.monitor_notifications())
        # Start periodic cleanup of expired pending messages
        asyncio.create_task(self._cleanup_expired_pending_messages_loop())

        logger.info("✅ Bot started successfully!")
        return True

    # ===== Audio Metadata method wrappers (inside class) =====
    async def audio_metadata_settings(self, event, task_id):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        task_name = task.get('task_name', 'مهمة بدون اسم')
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        status_text = "🟢 مفعل" if audio_settings['enabled'] else "🔴 معطل"
        template_text = audio_settings.get('template', 'default').title()
        art_status = "🟢 مفعل" if audio_settings.get('album_art_enabled') else "🔴 معطل"
        merge_status = "🟢 مفعل" if audio_settings.get('audio_merge_enabled') else "🔴 معطل"
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_audio_metadata_{task_id}")],
            [Button.inline(f"⚙️ إعدادات القالب ({template_text})", f"audio_template_settings_{task_id}")],
            [Button.inline(f"🖼️ صورة الغلاف ({art_status})", f"album_art_settings_{task_id}")],
            [Button.inline(f"🔗 دمج المقاطع ({merge_status})", f"audio_merge_settings_{task_id}")],
            [Button.inline("⚙️ إعدادات متقدمة", f"advanced_audio_settings_{task_id}")],
            [Button.inline("🧹 تنظيف نصوص الوسوم", f"audio_text_cleaning_{task_id}")],
            [Button.inline("🔄 استبدال نصوص الوسوم", f"audio_text_replacements_{task_id}")],
            [Button.inline("📝 فلاتر كلمات الوسوم", f"audio_word_filters_{task_id}")],
            [Button.inline("📄 هيدر وفوتر الوسوم", f"audio_header_footer_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات المهمة", f"task_settings_{task_id}")]
        ]
        message_text = (
            f"🎵 إعدادات الوسوم الصوتية للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📋 القالب: {template_text}\n"
            f"🖼️ صورة الغلاف: {art_status}\n"
            f"🔗 دمج المقاطع: {merge_status}\n\n"
            f"📝 الوصف:\n"
            f"تعديل الوسوم الصوتية (ID3v2) للملفات الصوتية قبل إعادة التوجيه\n"
            f"• دعم جميع أنواع الوسوم (Title, Artist, Album, Year, Genre, etc.)\n"
            f"• قوالب جاهزة للاستخدام\n"
            f"• صورة غلاف مخصصة\n"
            f"• دمج مقاطع صوتية إضافية\n"
            f"• الحفاظ على الجودة 100%"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def show_recurring_posts(self, event, task_id: int):
        """عرض وإدارة المنشورات المتكررة للمهمة"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        posts = self.db.list_recurring_posts(task_id)
        count = len(posts)

        buttons = []
        # List existing posts
        for p in posts[:20]:
            status = "🟢" if p.get('enabled') else "🔴"
            name = p.get('name') or f"منشور #{p['id']}"
            buttons.append([
                Button.inline(f"{status} {name}", f"recurring_edit_{p['id']}")
            ])
        if count > 20:
            buttons.append([Button.inline(f"+ {count-20} أخرى...", b"noop")])

        buttons.extend([
            [Button.inline("➕ إضافة منشور عبر إعادة التوجيه", f"recurring_add_{task_id}")],
            [Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")]
        ])

        message_text = (
            f"🔁 المنشورات المتكررة للمهمة: {task.get('task_name','')}\n\n"
            f"• العدد: {count}\n"
            f"• النشر لكل الأهداف المحددة في المهمة\n"
            f"• يدعم الوسائط، الأزرار الإنلاين، والـ Markdown\n\n"
            f"اختر إجراء:"
        )

        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_add_recurring_post(self, event, task_id: int):
        """بدء إضافة منشور متكرر عبر إعادة توجيه رسالة من قناة محددة"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return

        # Save state to capture forwarded message
        self.db.set_conversation_state(user_id, 'waiting_recurring_forward', str(task_id))

        buttons = [
            [Button.inline("❌ إلغاء", f"recurring_posts_{task_id}")]
        ]
        txt = (
            "➕ أرسل الآن الرسالة عبر إعادة التوجيه من القناة المصدر التي تريد تكرارها.\n\n"
            "- سيتم حفظ الرسالة كنموذج للنشر المتكرر.\n"
            "- بعد الإرسال سنطلب الفترة بالثواني وخيار حذف المنشور السابق قبل إعادة النشر."
        )
        await self.edit_or_send_message(event, txt, buttons=buttons)

    async def toggle_recurring_post(self, event, recurring_id: int):
        post = self.db.get_recurring_post(recurring_id)
        if not post:
            await event.answer("❌ غير موجود")
            return
        new_state = not bool(post.get('enabled'))
        self.db.update_recurring_post(recurring_id, enabled=new_state)
        await event.answer("✅ تم التحديث")
        await self.show_recurring_posts(event, post['task_id'])

    async def delete_recurring_post_action(self, event, recurring_id: int):
        post = self.db.get_recurring_post(recurring_id)
        if not post:
            await event.answer("❌ غير موجود")
            return
        self.db.delete_recurring_post(recurring_id)
        await event.answer("✅ تم الحذف")
        await self.show_recurring_posts(event, post['task_id'])

    async def start_edit_recurring_post(self, event, recurring_id: int):
        post = self.db.get_recurring_post(recurring_id)
        if not post:
            await event.answer("❌ غير موجود")
            return
        status = "🟢 مفعل" if post.get('enabled') else "🔴 معطل"
        del_prev = "🟢 نعم" if post.get('delete_previous') else "🔴 لا"
        interval = post.get('interval_seconds', 0)
        name = post.get('name') or f"منشور #{post['id']}"

        buttons = [
            [Button.inline("🔄 تبديل الحالة", f"recurring_toggle_{recurring_id}")],
            [Button.inline("⏱️ تعديل الفترة", f"recurring_set_interval_{recurring_id}")],
            [Button.inline("🧹 تبديل حذف السابق", f"recurring_toggle_delete_{recurring_id}"),
             Button.inline("🔘 حفظ أزرار الأصلية", f"recurring_toggle_preserve_{recurring_id}")],
            [Button.inline("🗑️ حذف", f"recurring_delete_{recurring_id}")],
            [Button.inline("🔙 رجوع", f"recurring_posts_{post['task_id']}")]
        ]
        msg = (
            f"✏️ إعدادات المنشور المتكرر\n\n"
            f"الاسم: {name}\n"
            f"الحالة: {status}\n"
            f"الفترة: {interval} ثانية\n"
            f"حذف السابق: {del_prev}\n"
        )
        await self.edit_or_send_message(event, msg, buttons=buttons)

    async def start_set_recurring_interval(self, event, recurring_id: int):
        post = self.db.get_recurring_post(recurring_id)
        if not post:
            await event.answer("❌ غير موجود")
            return
        user_id = event.sender_id
        self.db.set_conversation_state(user_id, 'editing_recurring_interval', str(recurring_id))
        await self.edit_or_send_message(event, "⏱️ أرسل الآن الفترة بالثواني (مثال: 3600)")
    async def audio_text_cleaning(self, event, task_id):
        """Show audio text cleaning settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get text cleaning settings for audio tags
        try:
            audio_cleaning = self.db.get_audio_text_cleaning_settings(task_id)
            status_text = "🟢 مفعل" if audio_cleaning.get('enabled', False) else "🔴 معطل"
        except (AttributeError, KeyError):
            status_text = "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_audio_text_cleaning_{task_id}")],
            [Button.inline("🧹 حذف الروابط", f"audio_clean_links_{task_id}"),
             Button.inline("😀 حذف الرموز التعبيرية", f"audio_clean_emojis_{task_id}")],
            [Button.inline("# حذف الهاشتاج", f"audio_clean_hashtags_{task_id}"),
             Button.inline("📞 حذف أرقام الهاتف", f"audio_clean_phones_{task_id}")],
            [Button.inline("📝 حذف السطور الفارغة", f"audio_clean_empty_{task_id}"),
             Button.inline("🔤 حذف كلمات محددة", f"audio_clean_keywords_{task_id}")],
            [Button.inline("🎯 اختيار الوسوم للتنظيف", f"audio_clean_tag_selection_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"🧹 تنظيف نصوص الوسوم الصوتية - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n\n"
            f"🔧 **خيارات التنظيف المتاحة:**\n"
            f"• حذف الروابط من الوسوم\n"
            f"• حذف الرموز التعبيرية\n"
            f"• حذف علامات الهاشتاج\n"
            f"• حذف أرقام الهاتف\n"
            f"• حذف السطور الفارغة\n"
            f"• حذف كلمات وعبارات محددة\n\n"
            f"💡 **ملاحظة:** سيتم تطبيق التنظيف على الوسوم المحددة فقط\n"
            f"(العنوان، الفنان، التعليق، كلمات الأغنية، إلخ)"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def audio_text_replacements(self, event, task_id):
        """Show audio text replacements settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        try:
            audio_replacements = self.db.get_audio_text_replacements_settings(task_id)
            status_text = "🟢 مفعل" if audio_replacements.get('enabled', False) else "🔴 معطل"
        except (AttributeError, KeyError):
            status_text = "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_audio_text_replacements_{task_id}")],
            [Button.inline("➕ إضافة استبدال جديد", f"add_audio_replacement_{task_id}")],
            [Button.inline("📋 عرض الاستبدالات", f"view_audio_replacements_{task_id}")],
            [Button.inline("🗑️ حذف جميع الاستبدالات", f"clear_audio_replacements_{task_id}")],
            [Button.inline("🎯 اختيار الوسوم للاستبدال", f"audio_replace_tag_selection_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"🔄 استبدال نصوص الوسوم الصوتية - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n\n"
            f"🔧 **وظائف الاستبدال:**\n"
            f"• استبدال كلمات أو عبارات محددة\n"
            f"• دعم البحث الحساس/غير الحساس للأحرف\n"
            f"• استبدال الكلمات الكاملة فقط\n"
            f"• تطبيق على وسوم محددة\n\n"
            f"💡 **مثال:** استبدال 'ft.' بـ 'featuring' في وسم الفنان"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def toggle_audio_text_cleaning(self, event, task_id):
        """Toggle audio tag text cleaning enabled state"""
        try:
            current = self.db.get_audio_tag_text_cleaning_settings(task_id)
            new_state = not bool(current.get('enabled', False))
            self.db.update_audio_text_cleaning_enabled(task_id, new_state)
            await event.answer("✅ تم التبديل")
        except Exception:
            await event.answer("❌ حدث خطأ أثناء التبديل")
        await self.audio_text_cleaning(event, task_id)

    async def toggle_audio_text_replacements(self, event, task_id):
        """Toggle audio tag text replacements enabled state"""
        try:
            current = self.db.get_audio_text_replacements_settings(task_id)
            new_state = not bool(current.get('enabled', False))
            self.db.update_audio_text_replacements_enabled(task_id, new_state)
            await event.answer("✅ تم التبديل")
        except Exception:
            await event.answer("❌ حدث خطأ أثناء التبديل")
        await self.audio_text_replacements(event, task_id)

    async def toggle_audio_metadata(self, event, task_id):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        current = self.db.get_audio_metadata_settings(task_id)
        new_status = not bool(current.get('enabled', False))
        self.db.update_audio_metadata_enabled(task_id, new_status)
        await event.answer(f"✅ تم {'تفعيل' if new_status else 'تعطيل'} الوسوم الصوتية")
        await self.audio_metadata_settings(event, task_id)

    async def audio_template_settings(self, event, task_id):
        """Show audio template settings with individual tag configuration"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        template_settings = self.db.get_audio_template_settings(task_id)
        
        # Create buttons for each tag
        buttons = [
            [Button.inline("🔹 العنوان (Title)", f"edit_audio_tag_{task_id}_title")],
            [Button.inline("🔹 الفنان (Artist)", f"edit_audio_tag_{task_id}_artist")],
            [Button.inline("🔹 فنان الألبوم (Album Artist)", f"edit_audio_tag_{task_id}_album_artist")],
            [Button.inline("🔹 الألبوم (Album)", f"edit_audio_tag_{task_id}_album")],
            [Button.inline("🔹 السنة (Year)", f"edit_audio_tag_{task_id}_year")],
            [Button.inline("🔹 النوع (Genre)", f"edit_audio_tag_{task_id}_genre")],
            [Button.inline("🔹 الملحن (Composer)", f"edit_audio_tag_{task_id}_composer")],
            [Button.inline("🔹 تعليق (Comment)", f"edit_audio_tag_{task_id}_comment")],
            [Button.inline("🔹 رقم المسار (Track)", f"edit_audio_tag_{task_id}_track")],
            [Button.inline("🔹 المدة (Length)", f"edit_audio_tag_{task_id}_length")],
            [Button.inline("🔹 كلمات الأغنية (Lyrics)", f"edit_audio_tag_{task_id}_lyrics")],
            [Button.inline("🔄 إعادة تعيين للافتراضي", f"reset_audio_template_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        # Show current template values
        message_text = (
            f"⚙️ إعدادات قالب الوسوم الصوتية للمهمة: {task_name}\n\n"
            f"📋 القوالب الحالية:\n\n"
            f"🔹 **العنوان**: `{template_settings['title_template']}`\n"
            f"🔹 **الفنان**: `{template_settings['artist_template']}`\n"
            f"🔹 **فنان الألبوم**: `{template_settings['album_artist_template']}`\n"
            f"🔹 **الألبوم**: `{template_settings['album_template']}`\n"
            f"🔹 **السنة**: `{template_settings['year_template']}`\n"
            f"🔹 **النوع**: `{template_settings['genre_template']}`\n"
            f"🔹 **الملحن**: `{template_settings['composer_template']}`\n"
            f"🔹 **التعليق**: `{template_settings['comment_template']}`\n"
            f"🔹 **رقم المسار**: `{template_settings['track_template']}`\n"
            f"🔹 **المدة**: `{template_settings['length_template']}`\n"
            f"🔹 **كلمات الأغنية**: `{template_settings['lyrics_template']}`\n\n"
            f"💡 **المتغيرات المتاحة**:\n"
            f"• `$title` - العنوان الأصلي\n"
            f"• `$artist` - الفنان الأصلي\n"
            f"• `$album` - الألبوم الأصلي\n"
            f"• `$year` - السنة الأصلية\n"
            f"• `$genre` - النوع الأصلي\n"
            f"• `$track` - رقم المسار الأصلي\n"
            f"• `$length` - المدة الأصلية\n"
            f"• `$lyrics` - كلمات الأغنية الأصلية\n\n"
            f"📝 **مثال على الاستخدام**:\n"
            f"• `$title - Official` لإضافة نص للعنوان\n"
            f"• `$artist ft. Guest` لإضافة فنان ضيف\n"
            f"• `$album (Remastered)` لإضافة وصف للألبوم\n\n"
            f"اختر الوسم الذي تريد تعديله:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_edit_audio_tag(self, event, task_id, tag_name):
        """Start editing a specific audio tag template"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        template_settings = self.db.get_audio_template_settings(task_id)
        current_value = template_settings.get(f'{tag_name}_template', f'${tag_name}')
        
        # Set user state for editing this tag
        self.set_user_state(user_id, f'editing_audio_tag_{tag_name}', {
            'task_id': task_id,
            'tag_name': tag_name,
            'current_value': current_value
        })
        
        # Tag display names
        tag_display_names = {
            'title': 'العنوان (Title)',
            'artist': 'الفنان (Artist)',
            'album_artist': 'فنان الألبوم (Album Artist)',
            'album': 'الألبوم (Album)',
            'year': 'السنة (Year)',
            'genre': 'النوع (Genre)',
            'composer': 'الملحن (Composer)',
            'comment': 'التعليق (Comment)',
            'track': 'رقم المسار (Track)',
            'length': 'المدة (Length)',
            'lyrics': 'كلمات الأغنية (Lyrics)'
        }
        
        tag_display_name = tag_display_names.get(tag_name, tag_name)
        
        buttons = [
            [Button.inline("❌ إلغاء", f"audio_template_settings_{task_id}")]
        ]
        
        message_text = (
            f"✏️ تحرير قالب {tag_display_name}\n\n"
            f"📋 القيمة الحالية:\n"
            f"`{current_value}`\n\n"
            f"💡 **المتغيرات المتاحة**:\n"
            f"• `$title` - العنوان الأصلي\n"
            f"• `$artist` - الفنان الأصلي\n"
            f"• `$album` - الألبوم الأصلي\n"
            f"• `$year` - السنة الأصلية\n"
            f"• `$genre` - النوع الأصلي\n"
            f"• `$track` - رقم المسار الأصلي\n"
            f"• `$length` - المدة الأصلية\n"
            f"• `$lyrics` - كلمات الأغنية الأصلية\n\n"
            f"📝 **أمثلة على الاستخدام**:\n"
            f"• `$title - Official`\n"
            f"• `$artist ft. Guest`\n"
            f"• `$album (Remastered)`\n"
            f"• `$title\\n$artist` (متعدد الأسطر)\n\n"
            f"🔤 أرسل القالب الجديد الآن:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def reset_audio_template(self, event, task_id):
        """Reset audio template settings to default values"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        success = self.db.reset_audio_template_settings(task_id)
        if success:
            await event.answer("✅ تم إعادة تعيين قالب الوسوم للقيم الافتراضية")
            await self.audio_template_settings(event, task_id)
        else:
            await event.answer("❌ فشل في إعادة تعيين القالب")

    async def set_audio_template(self, event, task_id, template_name):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        self.db.update_audio_metadata_template(task_id, template_name)
        template_display_name = {
            'default': 'الافتراضي',
            'enhanced': 'محسن',
            'minimal': 'بسيط',
            'professional': 'احترافي',
            'custom': 'مخصص'
        }.get(template_name, template_name)
        await event.answer(f"✅ تم اختيار قالب '{template_display_name}'")
        await self.audio_metadata_settings(event, task_id)

    async def album_art_settings(self, event, task_id):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        task_name = task.get('task_name', 'مهمة بدون اسم')
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        art_status = "🟢 مفعل" if audio_settings.get('album_art_enabled') else "🔴 معطل"
        apply_all_status = "🟢 نعم" if audio_settings.get('apply_art_to_all') else "🔴 لا"
        art_path = audio_settings.get('album_art_path') or 'غير محدد'
        buttons = [
            [Button.inline("🖼️ رفع صورة غلاف", f"upload_album_art_{task_id}")],
            [Button.inline("⚙️ خيارات التطبيق", f"album_art_options_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        message_text = (
            f"🖼️ إعدادات صورة الغلاف للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• رفع صورة غلاف مخصصة للملفات الصوتية\n"
            f"• خيار تطبيقها على جميع الملفات\n"
            f"• خيار تطبيقها فقط على الملفات بدون صورة\n"
            f"• الحفاظ على الجودة 100%\n"
            f"• دعم الصيغ: JPG, PNG, BMP, TIFF\n\n"
            f"الحالة: {art_status}\n"
            f"تطبيق على الجميع: {apply_all_status}\n"
            f"المسار الحالي: {art_path}\n\n"
            f"اختر الإعداد الذي تريد تعديله أو ارفع صورة جديدة:"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def audio_merge_settings(self, event, task_id):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        task_name = task.get('task_name', 'مهمة بدون اسم')
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        merge_status = "🟢 مفعل" if audio_settings.get('audio_merge_enabled') else "🔴 معطل"
        intro_path = audio_settings.get('intro_audio_path') or 'غير محدد'
        outro_path = audio_settings.get('outro_audio_path') or 'غير محدد'
        intro_position = 'البداية' if audio_settings.get('intro_position') == 'start' else 'النهاية'
        buttons = [
            [Button.inline("🎚️ تبديل حالة الدمج", f"toggle_audio_merge_{task_id}")],
            [Button.inline("🎵 مقطع مقدمة", f"intro_audio_settings_{task_id}")],
            [Button.inline("🎵 مقطع خاتمة", f"outro_audio_settings_{task_id}")],
            [Button.inline("⚙️ خيارات الدمج", f"merge_options_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        message_text = (
            f"🔗 إعدادات دمج المقاطع الصوتية للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• إضافة مقطع مقدمة في البداية\n"
            f"• إضافة مقطع خاتمة في النهاية\n"
            f"• اختيار موضع المقدمة (بداية أو نهاية)\n"
            f"• دعم جميع الصيغ الصوتية\n"
            f"• جودة عالية 320k MP3\n\n"
            f"حالة الدمج: {merge_status}\n"
            f"مقدمة: {intro_path}\n"
            f"خاتمة: {outro_path}\n"
            f"موضع المقدمة: {intro_position}\n\n"
            f"اختر الإعداد الذي تريد تعديله:"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def advanced_audio_settings(self, event, task_id):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        task_name = task.get('task_name', 'مهمة بدون اسم')
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        preserve_status = "🟢" if audio_settings.get('preserve_original') else "🔴"
        convert_status = "🟢" if audio_settings.get('convert_to_mp3') else "🔴"
        buttons = [
            [Button.inline(f"{preserve_status} الحفاظ على الجودة", f"toggle_preserve_quality_{task_id}")],
            [Button.inline(f"{convert_status} التحويل إلى MP3", f"toggle_convert_to_mp3_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        message_text = (
            f"⚙️ الإعدادات المتقدمة للوسوم الصوتية للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• الحفاظ على الجودة الأصلية 100%\n"
            f"• تحويل إلى MP3 مع الحفاظ على الدقة\n"
            f"• معالجة مرة واحدة وإعادة الاستخدام\n"
            f"• Cache ذكي للملفات المعالجة\n"
            f"• إعدادات الأداء والسرعة\n\n"
            f"اختر الإعداد الذي تريد تعديله:"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def show_album_art_options(self, event, task_id: int):
        settings = self.db.get_audio_metadata_settings(task_id)
        art_status = "🟢 مفعل" if settings.get('album_art_enabled') else "🔴 معطل"
        apply_all_status = "🟢 نعم" if settings.get('apply_art_to_all') else "🔴 لا"
        buttons = [
            [Button.inline(f"🔄 تبديل صورة الغلاف ({art_status})", f"toggle_album_art_enabled_{task_id}")],
            [Button.inline(f"📦 تطبيق على جميع الملفات ({apply_all_status})", f"toggle_apply_art_to_all_{task_id}")],
            [Button.inline("🔙 رجوع", f"album_art_settings_{task_id}")]
        ]
        await self.force_new_message(event, "⚙️ خيارات صورة الغلاف:", buttons=buttons)

    async def show_intro_audio_settings(self, event, task_id: int):
        settings = self.db.get_audio_metadata_settings(task_id)
        intro_path = settings.get('intro_audio_path') or 'غير محدد'
        buttons = [
            [Button.inline("⬆️ رفع مقدمة", f"upload_intro_audio_{task_id}")],
            [Button.inline("🗑️ حذف المقدمة", f"remove_intro_audio_{task_id}")],
            [Button.inline("🔙 رجوع", f"audio_merge_settings_{task_id}")]
        ]
        await self.force_new_message(event, f"🎵 مقدمة حالية: {intro_path}", buttons=buttons)

    async def show_outro_audio_settings(self, event, task_id: int):
        settings = self.db.get_audio_metadata_settings(task_id)
        outro_path = settings.get('outro_audio_path') or 'غير محدد'
        buttons = [
            [Button.inline("⬆️ رفع خاتمة", f"upload_outro_audio_{task_id}")],
            [Button.inline("🗑️ حذف الخاتمة", f"remove_outro_audio_{task_id}")],
            [Button.inline("🔙 رجوع", f"audio_merge_settings_{task_id}")]
        ]
        await self.force_new_message(event, f"🎵 خاتمة حالية: {outro_path}", buttons=buttons)

    async def show_merge_options(self, event, task_id: int):
        settings = self.db.get_audio_metadata_settings(task_id)
        pos = settings.get('intro_position', 'start')
        pos_text = 'البداية' if pos == 'start' else 'النهاية'
        buttons = [
            [Button.inline("⬆️ المقدمة في البداية", f"set_intro_position_start_{task_id}")],
            [Button.inline("⬇️ المقدمة في النهاية", f"set_intro_position_end_{task_id}")],
            [Button.inline("🔙 رجوع", f"audio_merge_settings_{task_id}")]
        ]
        await self.force_new_message(event, f"⚙️ موضع المقدمة الحالي: {pos_text}", buttons=buttons)

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
            # Check UserBot status for better welcome message
            from userbot_service.userbot import userbot_instance
            is_userbot_running = user_id in userbot_instance.clients
            
            # Show main menu
            buttons = [
                [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
                [Button.inline("🔍 فحص حالة UserBot", b"check_userbot")],
                [Button.inline("⚙️ الإعدادات", b"settings")],
                [Button.inline("ℹ️ حول البوت", b"about")]
            ]

            # Enhanced welcome message with system status
            system_status = "🟢 نشط" if is_userbot_running else "🟡 مطلوب فحص"
            
            logger.info(f"📤 إرسال قائمة رئيسية للمستخدم المُصادق عليه: {user_id}")
            message_text = (
                f"🎉 أهلاً بك في بوت التوجيه التلقائي!\n\n"
                f"👋 مرحباً {event.sender.first_name}\n"
                f"🔑 حالة تسجيل الدخول: نشطة\n"
                f"🤖 UserBot: {system_status}\n\n"
                f"💡 النظام الجديد:\n"
                f"• بوت التحكم منفصل عن UserBot\n"
                f"• يمكنك إدارة المهام دائماً\n"
                f"• إذا تعطل UserBot، أعد تسجيل الدخول\n\n"
                f"اختر ما تريد فعله:"
            )
            await self.force_new_message(event, message_text, buttons=buttons)
            logger.info(f"✅ تم إرسال الرد بنجاح للمستخدم: {user_id}")
        else:
            # Show authentication menu
            buttons = [
                [Button.inline("📱 تسجيل الدخول برقم الهاتف", b"auth_phone")],
                [Button.inline("🔑 تسجيل الدخول بجلسة جاهزة", b"login_session")]
            ]

            logger.info(f"📤 إرسال قائمة تسجيل الدخول للمستخدم غير المُصادق عليه: {user_id}")
            message_text = (
                f"🤖 مرحباً بك في بوت التوجيه التلقائي!\n\n"
                f"📋 هذا البوت يساعدك في:\n"
                f"• توجيه الرسائل تلقائياً\n"
                f"• إدارة مهام التوجيه\n"
                f"• مراقبة المحادثات\n\n"
                f"🔐 يجب تسجيل الدخول أولاً:"
            )
            await self.force_new_message(event, message_text, buttons=buttons)
            logger.info(f"✅ تم إرسال رد التسجيل بنجاح للمستخدم: {user_id}")

    async def handle_login(self, event):
        """Handle /login command"""
        logger.info(f"📥 تم استلام أمر /login من المستخدم: {event.sender_id}")
        
        # Only respond to /login in private chats
        if not event.is_private:
            logger.info(f"🚫 تجاهل أمر /login في محادثة غير خاصة: {event.chat_id}")
            return

        user_id = event.sender_id
        
        # Check if user is already authenticated
        if self.db.is_user_authenticated(user_id):
            buttons = [
                [Button.inline("🔄 إعادة تسجيل الدخول", b"relogin")],
                [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
            ]
            
            message_text = (
                "🔄 أنت مسجل دخولك بالفعل!\n\n"
                "هل تريد:\n"
                "• إعادة تسجيل الدخول بجلسة جديدة؟\n"
                "• العودة للقائمة الرئيسية؟"
            )
            await self.force_new_message(event, message_text, buttons=buttons)
            return
        
        # Show login options
        buttons = [
            [Button.inline("📱 تسجيل الدخول برقم الهاتف", b"auth_phone")],
            [Button.inline("🔑 تسجيل الدخول بجلسة جاهزة", b"login_session")]
        ]
        
        message_text = (
            "🔐 تسجيل الدخول - بوت التوجيه التلقائي\n\n"
            "اختر طريقة تسجيل الدخول:\n\n"
            "📱 **تسجيل الدخول برقم الهاتف**:\n"
            "• إرسال رمز التحقق\n"
            "• إدخال كلمة المرور (إذا كانت مفعلة)\n\n"
            "🔑 **تسجيل الدخول بجلسة جاهزة**:\n"
            "• استخدام جلسة تليثون موجودة\n"
            "• أسرع وأسهل\n\n"
            "💡 **كيفية الحصول على الجلسة**:\n"
            "• استخدم @SessionStringBot\n"
            "• أو استخدم @StringSessionBot\n"
            "• أو استخدم @UseTGXBot"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_callback(self, event):
        """Handle button callbacks"""
        try:
            data = event.data.decode('utf-8')
            user_id = event.sender_id

            if data == "auth_phone":
                await self.start_auth(event)
            elif data == "login_session":
                await self.start_session_login(event)
            elif data == "relogin":
                await self.handle_relogin(event)
            elif data == "back_main":
                await self.handle_start(event)
            elif data == "manage_tasks":
                await self.show_tasks_menu(event)
            elif data == "manage_channels":
                await self.show_channels_menu(event)
            elif data == "add_channel":
                await self.start_add_channel(event)
            elif data == "list_channels":
                await self.list_channels(event)
            elif data == "add_multiple_channels":
                # Redirect to single add flow which now supports multi-line input
                await self.start_add_channel(event)
            elif data == "finish_add_channels":
                await self.finish_add_channels(event)
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
            elif data == "choose_sources":
                await self.start_choose_sources(event)
            elif data == "choose_targets":
                await self.start_choose_targets(event)
            elif data.startswith("choose_add_sources_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_choose_sources_for_task(event, task_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("choose_add_targets_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_choose_targets_for_task(event, task_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("toggle_sel_source_"):
                chat_id = data.replace("toggle_sel_source_", "", 1)
                await self.toggle_channel_selection(event, "source", chat_id)
            elif data.startswith("toggle_sel_target_"):
                chat_id = data.replace("toggle_sel_target_", "", 1)
                await self.toggle_channel_selection(event, "target", chat_id)
            elif data == "finish_sel_source":
                await self.finish_channel_selection(event, "source")
            elif data == "finish_sel_target":
                await self.finish_channel_selection(event, "target")
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
                try:
                    # Extract task_id from data like "advanced_features_123"
                    task_id = int(data.replace("advanced_features_", ""))
                    await self.show_advanced_features(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة للميزات المتقدمة: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("recurring_posts_"):
                try:
                    task_id = int(data.replace("recurring_posts_", ""))
                    await self.show_recurring_posts(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في معرف المهمة للمنشورات المتكررة: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("recurring_add_"):
                try:
                    task_id = int(data.replace("recurring_add_", ""))
                    await self.start_add_recurring_post(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ")
            elif data.startswith("recurring_toggle_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        recurring_id = int(parts[2])
                        await self.toggle_recurring_post(event, recurring_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_delete_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        recurring_id = int(parts[2])
                        await self.delete_recurring_post_action(event, recurring_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_edit_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        recurring_id = int(parts[2])
                        await self.start_edit_recurring_post(event, recurring_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_set_interval_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        recurring_id = int(parts[3])
                        await self.start_set_recurring_interval(event, recurring_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_toggle_delete_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        recurring_id = int(parts[3]) if len(parts) > 3 else int(parts[2])
                        post = self.db.get_recurring_post(recurring_id)
                        if post:
                            new_val = not bool(post.get('delete_previous'))
                            self.db.update_recurring_post(recurring_id, delete_previous=new_val)
                            await event.answer("✅ تم التحديث")
                            await self.start_edit_recurring_post(event, recurring_id)
                    except Exception:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_toggle_preserve_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        recurring_id = int(parts[3]) if len(parts) > 3 else int(parts[2])
                        post = self.db.get_recurring_post(recurring_id)
                        if post:
                            new_val = not bool(post.get('preserve_original_buttons', True))
                            self.db.update_recurring_post(recurring_id, preserve_original_buttons=new_val)
                            await event.answer("✅ تم التحديث")
                            await self.start_edit_recurring_post(event, recurring_id)
                    except Exception:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_posts_"):
                try:
                    task_id = int(data.replace("recurring_posts_", ""))
                    await self.show_recurring_posts(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في معرف المهمة للمنشورات المتكررة: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("recurring_add_"):
                try:
                    task_id = int(data.replace("recurring_add_", ""))
                    await self.start_add_recurring_post(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ")
            elif data.startswith("recurring_toggle_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        recurring_id = int(parts[2])
                        await self.toggle_recurring_post(event, recurring_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_delete_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        recurring_id = int(parts[2])
                        await self.delete_recurring_post_action(event, recurring_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_edit_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        recurring_id = int(parts[2])
                        await self.start_edit_recurring_post(event, recurring_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
            elif data.startswith("recurring_set_interval_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        recurring_id = int(parts[3])
                        await self.start_set_recurring_interval(event, recurring_id)
                    except ValueError:
                        await event.answer("❌ خطأ")
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
            # ===== Audio Metadata Event Handlers =====
            elif data.startswith("audio_metadata_settings_"):
                try:
                    task_id = int(data.replace("audio_metadata_settings_", ""))
                    await self.audio_metadata_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات الوسوم الصوتية: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_audio_metadata_"):
                try:
                    task_id = int(data.replace("toggle_audio_metadata_", ""))
                    await self.toggle_audio_metadata(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الوسوم الصوتية: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_template_settings_"):
                try:
                    task_id = int(data.replace("audio_template_settings_", ""))
                    await self.audio_template_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات قالب الوسوم: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_audio_tag_"):
                try:
                    # Extract task_id and tag_name from "edit_audio_tag_7_title"
                    remaining = data.replace("edit_audio_tag_", "")
                    parts = remaining.split("_", 1)
                    if len(parts) >= 2:
                        task_id = int(parts[0])
                        tag_name = parts[1]
                        await self.start_edit_audio_tag(event, task_id, tag_name)
                    else:
                        await event.answer("❌ خطأ في تحليل البيانات")
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتحرير وسم الصوت: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("reset_audio_template_"):
                try:
                    task_id = int(data.replace("reset_audio_template_", ""))
                    await self.reset_audio_template(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعادة تعيين قالب الوسوم: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_audio_template_"):
                try:
                    # Extract task_id and template_name from "set_audio_template_7_default"
                    remaining = data.replace("set_audio_template_", "")
                    parts = remaining.split("_", 1)
                    if len(parts) >= 2:
                        task_id = int(parts[0])
                        template_name = parts[1]
                        await self.set_audio_template(event, task_id, template_name)
                    else:
                        await event.answer("❌ خطأ في تحليل البيانات")
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتعيين قالب الوسوم: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("album_art_settings_"):
                try:
                    task_id = int(data.replace("album_art_settings_", ""))
                    await self.album_art_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات صورة الغلاف: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("album_art_options_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.show_album_art_options(event, task_id)
                    except ValueError:
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("upload_album_art_"):
                try:
                    task_id = int(data.replace("upload_album_art_", ""))
                    self.set_user_state(user_id, 'awaiting_album_art_upload', {'task_id': task_id})
                    await self.force_new_message(event, "🖼️ أرسل الآن صورة الغلاف كصورة أو ملف.")
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_album_art_enabled_"):
                try:
                    task_id = int(data.replace("toggle_album_art_enabled_", ""))
                    settings = self.db.get_audio_metadata_settings(task_id)
                    self.db.set_album_art_settings(task_id, enabled=not bool(settings.get('album_art_enabled')))
                    await event.answer("✅ تم التبديل")
                    await self.album_art_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_apply_art_to_all_"):
                try:
                    task_id = int(data.replace("toggle_apply_art_to_all_", ""))
                    settings = self.db.get_audio_metadata_settings(task_id)
                    self.db.set_album_art_settings(task_id, apply_to_all=not bool(settings.get('apply_art_to_all')))
                    await event.answer("✅ تم التبديل")
                    await self.album_art_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_preserve_quality_"):
                try:
                    task_id = int(data.replace("toggle_preserve_quality_", ""))
                    settings = self.db.get_audio_metadata_settings(task_id)
                    current_state = settings.get('preserve_quality', True)
                    self.db.update_audio_metadata_setting(task_id, 'preserve_quality', not current_state)
                    await event.answer("✅ تم التبديل")
                    await self.advanced_audio_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_convert_to_mp3_"):
                try:
                    task_id = int(data.replace("toggle_convert_to_mp3_", ""))
                    settings = self.db.get_audio_metadata_settings(task_id)
                    current_state = settings.get('convert_to_mp3', False)
                    self.db.update_audio_metadata_setting(task_id, 'convert_to_mp3', not current_state)
                    await event.answer("✅ تم التبديل")
                    await self.advanced_audio_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("delete_channel_"):
                try:
                    channel_id = int(data.replace("delete_channel_", ""))
                    await self.delete_channel(event, channel_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_channel_"):
                try:
                    channel_id = int(data.replace("edit_channel_", ""))
                    await self.edit_channel(event, channel_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("refresh_channel_"):
                try:
                    channel_id = int(data.replace("refresh_channel_", ""))
                    await self.refresh_channel_info(event, channel_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_merge_settings_"):
                try:
                    task_id = int(data.replace("audio_merge_settings_", ""))
                    await self.audio_merge_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات دمج المقاطع: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_audio_merge_"):
                try:
                    task_id = int(data.replace("toggle_audio_merge_", ""))
                    settings = self.db.get_audio_metadata_settings(task_id)
                    self.db.set_audio_merge_settings(task_id, enabled=not bool(settings.get('audio_merge_enabled')))
                    await event.answer("✅ تم التبديل")
                    await self.audio_merge_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("intro_audio_settings_"):
                try:
                    task_id = int(data.replace("intro_audio_settings_", ""))
                    await self.show_intro_audio_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("outro_audio_settings_"):
                try:
                    task_id = int(data.replace("outro_audio_settings_", ""))
                    await self.show_outro_audio_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("upload_intro_audio_"):
                try:
                    task_id = int(data.replace("upload_intro_audio_", ""))
                    self.set_user_state(user_id, 'awaiting_intro_audio_upload', {'task_id': task_id})
                    await self.force_new_message(event, "🎵 أرسل الآن ملف المقدمة (Audio)")
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("remove_intro_audio_"):
                try:
                    task_id = int(data.replace("remove_intro_audio_", ""))
                    self.db.set_audio_merge_settings(task_id, intro_path='')
                    await event.answer("✅ تم حذف مقطع المقدمة")
                    await self.audio_merge_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("upload_outro_audio_"):
                try:
                    task_id = int(data.replace("upload_outro_audio_", ""))
                    self.set_user_state(user_id, 'awaiting_outro_audio_upload', {'task_id': task_id})
                    await self.force_new_message(event, "🎵 أرسل الآن ملف الخاتمة (Audio)")
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("remove_outro_audio_"):
                try:
                    task_id = int(data.replace("remove_outro_audio_", ""))
                    self.db.set_audio_merge_settings(task_id, outro_path='')
                    await event.answer("✅ تم حذف مقطع الخاتمة")
                    await self.audio_merge_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("merge_options_"):
                try:
                    task_id = int(data.replace("merge_options_", ""))
                    await self.show_merge_options(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_intro_position_"):
                try:
                    remaining = data.replace("set_intro_position_", "")
                    pos, task_id_str = remaining.rsplit("_", 1)
                    task_id = int(task_id_str)
                    if pos in ['start', 'end']:
                        self.db.set_audio_merge_settings(task_id, intro_position=pos)
                        await event.answer("✅ تم تحديث موضع المقدمة")
                        await self.audio_merge_settings(event, task_id)
                    else:
                        await event.answer("❌ موقع غير صحيح")
                except Exception:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("advanced_audio_settings_"):
                try:
                    task_id = int(data.replace("advanced_audio_settings_", ""))
                    await self.advanced_audio_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة للإعدادات المتقدمة للوسوم: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_text_cleaning_"):
                try:
                    task_id = int(data.replace("audio_text_cleaning_", ""))
                    await self.audio_text_cleaning(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتنظيف نصوص الوسوم: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_text_replacements_"):
                try:
                    task_id = int(data.replace("audio_text_replacements_", ""))
                    await self.audio_text_replacements(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لاستبدال نصوص الوسوم: {e}")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_audio_text_cleaning_"):
                try:
                    task_id = int(data.replace("toggle_audio_text_cleaning_", ""))
                    await self.toggle_audio_text_cleaning(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_audio_text_replacements_"):
                try:
                    task_id = int(data.replace("toggle_audio_text_replacements_", ""))
                    await self.toggle_audio_text_replacements(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            # Audio cleaning buttons handlers
            elif data.startswith("audio_clean_links_"):
                try:
                    task_id = int(data.replace("audio_clean_links_", ""))
                    await self.toggle_audio_clean_option(event, task_id, 'links')
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_clean_emojis_"):
                try:
                    task_id = int(data.replace("audio_clean_emojis_", ""))
                    await self.toggle_audio_clean_option(event, task_id, 'emojis')
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_clean_hashtags_"):
                try:
                    task_id = int(data.replace("audio_clean_hashtags_", ""))
                    await self.toggle_audio_clean_option(event, task_id, 'hashtags')
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_clean_phones_"):
                try:
                    task_id = int(data.replace("audio_clean_phones_", ""))
                    await self.toggle_audio_clean_option(event, task_id, 'phones')
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_clean_empty_"):
                try:
                    task_id = int(data.replace("audio_clean_empty_", ""))
                    await self.toggle_audio_clean_option(event, task_id, 'empty_lines')
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_clean_keywords_"):
                try:
                    task_id = int(data.replace("audio_clean_keywords_", ""))
                    await self.audio_clean_keywords_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            # Audio replacements buttons handlers
            elif data.startswith("add_audio_replacement_"):
                try:
                    task_id = int(data.replace("add_audio_replacement_", ""))
                    await self.add_audio_replacement(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("view_audio_replacements_"):
                try:
                    task_id = int(data.replace("view_audio_replacements_", ""))
                    await self.view_audio_replacements(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("clear_audio_replacements_"):
                try:
                    task_id = int(data.replace("clear_audio_replacements_", ""))
                    await self.clear_audio_replacements(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            # Audio word filters handlers
            elif data.startswith("audio_word_filters_"):
                try:
                    task_id = int(data.replace("audio_word_filters_", ""))
                    await self.audio_word_filters(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_audio_word_filters_"):
                try:
                    task_id = int(data.replace("toggle_audio_word_filters_", ""))
                    await self.toggle_audio_word_filters(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_whitelist_"):
                try:
                    task_id = int(data.replace("audio_whitelist_", ""))
                    await self.audio_whitelist_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_blacklist_"):
                try:
                    task_id = int(data.replace("audio_blacklist_", ""))
                    await self.audio_blacklist_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            # Audio header/footer handlers
            elif data.startswith("audio_header_footer_"):
                try:
                    task_id = int(data.replace("audio_header_footer_", ""))
                    await self.audio_header_footer(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_audio_header_footer_"):
                try:
                    task_id = int(data.replace("toggle_audio_header_footer_", ""))
                    await self.toggle_audio_header_footer(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_header_settings_"):
                try:
                    task_id = int(data.replace("audio_header_settings_", ""))
                    await self.audio_header_settings(event, task_id)
                except ValueError:
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("audio_footer_settings_"):
                try:
                    task_id = int(data.replace("audio_footer_settings_", ""))
                    await self.audio_footer_settings(event, task_id)
                except ValueError:
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
            elif data.startswith("cycle_char_mode_"): # Cycle character limit mode
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.cycle_character_limit_mode(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتدوير وضع حد الأحرف: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("cycle_length_mode_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.cycle_length_mode(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتدوير نوع الحد: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_char_min_"): # Edit character minimum limit
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_edit_char_min(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل الحد الأدنى: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_char_max_"): # Edit character maximum limit
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_edit_char_max(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل الحد الأقصى: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_char_range_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_edit_character_range(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل النطاق: {e}")
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
                try:
                    # Extract task_id from data like "watermark_settings_123"
                    task_id = int(data.replace("watermark_settings_", ""))
                    await self.show_watermark_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_"): # Toggle watermark
                try:
                    # Extract task_id from data like "toggle_watermark_123"
                    task_id = int(data.replace("toggle_watermark_", ""))
                    await self.toggle_watermark(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_appearance_"): # Watermark appearance settings
                try:
                    # Extract task_id from data like "watermark_appearance_123"
                    task_id = int(data.replace("watermark_appearance_", ""))
                    await self.show_watermark_appearance(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات مظهر العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_type_"): # Watermark type settings
                try:
                    # Extract task_id from data like "watermark_type_123"
                    task_id = int(data.replace("watermark_type_", ""))
                    await self.show_watermark_type(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات نوع العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_media_"): # Watermark media types
                try:
                    # Extract task_id from data like "watermark_media_123"
                    task_id = int(data.replace("watermark_media_", ""))
                    await self.show_watermark_media_types(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لأنواع الوسائط للعلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_size_up_"): # Increase watermark size
                try:
                    # Extract task_id from data like "watermark_size_up_123"
                    task_id = int(data.replace("watermark_size_up_", ""))
                    await self.adjust_watermark_size(event, task_id, increase=True)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لزيادة حجم العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_size_down_"): # Decrease watermark size
                try:
                    # Extract task_id from data like "watermark_size_down_123"
                    task_id = int(data.replace("watermark_size_down_", ""))
                    await self.adjust_watermark_size(event, task_id, increase=False)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتقليل حجم العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_opacity_up_"): # Increase watermark opacity
                try:
                    # Extract task_id from data like "watermark_opacity_up_123"
                    task_id = int(data.replace("watermark_opacity_up_", ""))
                    await self.adjust_watermark_opacity(event, task_id, increase=True)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لزيادة شفافية العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_opacity_down_"): # Decrease watermark opacity
                try:
                    # Extract task_id from data like "watermark_opacity_down_123"
                    task_id = int(data.replace("watermark_opacity_down_", ""))
                    await self.adjust_watermark_opacity(event, task_id, increase=False)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتقليل شفافية العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_font_up_"): # Increase watermark font size
                try:
                    # Extract task_id from data like "watermark_font_up_123"
                    task_id = int(data.replace("watermark_font_up_", ""))
                    await self.adjust_watermark_font_size(event, task_id, increase=True)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لزيادة حجم خط العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_font_down_"): # Decrease watermark font size
                try:
                    # Extract task_id from data like "watermark_font_down_123"
                    task_id = int(data.replace("watermark_font_down_", ""))
                    await self.adjust_watermark_font_size(event, task_id, increase=False)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتقليل حجم خط العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_default_up_"): # Increase default watermark size
                try:
                    # Extract task_id from data like "watermark_default_up_123"
                    task_id = int(data.replace("watermark_default_up_", ""))
                    await self.adjust_watermark_default_size(event, task_id, increase=True)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لزيادة الحجم الافتراضي: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_default_down_"): # Decrease default watermark size
                try:
                    # Extract task_id from data like "watermark_default_down_123"
                    task_id = int(data.replace("watermark_default_down_", ""))
                    await self.adjust_watermark_default_size(event, task_id, increase=False)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتقليل الحجم الافتراضي: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_apply_default_"): # Apply default size
                try:
                    # Extract task_id from data like "watermark_apply_default_123"
                    task_id = int(data.replace("watermark_apply_default_", ""))
                    await self.apply_default_watermark_size(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتطبيق الحجم الافتراضي: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_offset_left_"): # Move watermark left
                try:
                    # Extract task_id from data like "watermark_offset_left_123"
                    task_id = int(data.replace("watermark_offset_left_", ""))
                    await self.adjust_watermark_offset(event, task_id, axis='x', increase=False)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة للإزاحة يساراً: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_offset_right_"): # Move watermark right
                try:
                    # Extract task_id from data like "watermark_offset_right_123"
                    task_id = int(data.replace("watermark_offset_right_", ""))
                    await self.adjust_watermark_offset(event, task_id, axis='x', increase=True)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة للإزاحة يميناً: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_offset_up_"): # Move watermark up
                try:
                    # Extract task_id from data like "watermark_offset_up_123"
                    task_id = int(data.replace("watermark_offset_up_", ""))
                    await self.adjust_watermark_offset(event, task_id, axis='y', increase=False)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة للإزاحة أعلى: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_offset_down_"): # Move watermark down
                try:
                    # Extract task_id from data like "watermark_offset_down_123"
                    task_id = int(data.replace("watermark_offset_down_", ""))
                    await self.adjust_watermark_offset(event, task_id, axis='y', increase=True)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة للإزاحة أسفل: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_reset_offset_"): # Reset watermark offset
                try:
                    # Extract task_id from data like "watermark_reset_offset_123"
                    task_id = int(data.replace("watermark_reset_offset_", ""))
                    await self.reset_watermark_offset(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعادة تعيين الإزاحة: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_position_selector_"): # Show watermark position selector
                try:
                    # Extract task_id from data like "watermark_position_selector_123"
                    task_id = int(data.replace("watermark_position_selector_", ""))
                    await self.show_watermark_position_selector(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لعرض أختيار موضع العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_watermark_position_"): # Set watermark position
                try:
                    # Extract task_id and position from data like "set_watermark_position_top_left_123"
                    # Remove "set_watermark_position_" prefix
                    remaining = data.replace("set_watermark_position_", "")
                    
                    # Find the last underscore to separate position from task_id
                    last_underscore = remaining.rfind("_")
                    if last_underscore != -1:
                        position = remaining[:last_underscore]
                        task_id = int(remaining[last_underscore + 1:])
                        
                        # Validate position
                        valid_positions = ['top_left', 'top', 'top_right', 'bottom_left', 'bottom', 'bottom_right', 'center']
                        if position in valid_positions:
                            await self.set_watermark_position(event, task_id, position)
                        else:
                            logger.error(f"❌ موقع غير صحيح: {position}")
                            await event.answer("❌ موقع غير صحيح")
                    else:
                        logger.error(f"❌ تنسيق بيانات غير صحيح: {data}")
                        await event.answer("❌ خطأ في تنسيق البيانات")
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتعيين موضع العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_watermark_type_"): # Set watermark type
                try:
                    # Extract watermark_type and task_id from data like "set_watermark_type_text_123"
                    # Remove "set_watermark_type_" prefix
                    remaining = data.replace("set_watermark_type_", "")
                    
                    # Find the last underscore to separate watermark_type from task_id
                    last_underscore = remaining.rfind("_")
                    if last_underscore != -1:
                        watermark_type = remaining[:last_underscore]
                        task_id = int(remaining[last_underscore + 1:])
                        
                        # Validate watermark_type
                        valid_types = ['text', 'image']
                        if watermark_type in valid_types:
                            await self.set_watermark_type(event, task_id, watermark_type)
                        else:
                            logger.error(f"❌ نوع علامة مائية غير صحيح: {watermark_type}")
                            await event.answer("❌ نوع علامة مائية غير صحيح")
                    else:
                        logger.error(f"❌ تنسيق بيانات غير صحيح: {data}")
                        await event.answer("❌ خطأ في تنسيق البيانات")
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل نوع العلامة المائية: {e}, data='{data}'")
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
            elif data.startswith("edit_rate_limit_count_"): # Handler for editing rate limit count
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[4])
                        await self.start_edit_rate_count(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل عدد الرسائل: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_rate_limit_period_"): # Handler for editing rate limit period
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[4])
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
            elif data.startswith("manage_languages_"): # Handler for managing languages
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_language_management(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإدارة اللغات: {e}, data='{data}', parts={parts}")
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
                try:
                    # Extract task_id from data like "watermark_config_123"
                    task_id = int(data.replace("watermark_config_", ""))
                    await self.show_watermark_config(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتكوين العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_media_"): # Handler for watermark media settings
                try:
                    # Extract task_id from data like "watermark_media_123"
                    task_id = int(data.replace("watermark_media_", ""))
                    await self.show_watermark_media_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات وسائط العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_text_"): # Handler for watermark text setting
                try:
                    # Extract task_id from data like "watermark_text_123"
                    task_id = int(data.replace("watermark_text_", ""))
                    await self.start_set_watermark_text(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل نص العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_image_"): # Handler for watermark image setting
                try:
                    # Extract task_id from data like "watermark_image_123"
                    task_id = int(data.replace("watermark_image_", ""))
                    await self.start_set_watermark_image(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل صورة العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_position_"): # Handler for watermark position setting
                try:
                    # Extract task_id from data like "watermark_position_123"
                    task_id = int(data.replace("watermark_position_", ""))
                    await self.show_watermark_position_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل موقع العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("watermark_appearance_"): # Handler for watermark appearance setting
                try:
                    # Extract task_id from data like "watermark_appearance_123"
                    task_id = int(data.replace("watermark_appearance_", ""))
                    await self.show_watermark_appearance_settings(event, task_id)
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتعديل مظهر العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_photos_"): # Handler for toggle watermark photos
                try:
                    # Extract task_id from data like "toggle_watermark_photos_123"
                    task_id = int(data.replace("toggle_watermark_photos_", ""))
                    await self.toggle_watermark_media_type(event, task_id, 'photos')
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للصور: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_videos_"): # Handler for toggle watermark videos
                try:
                    # Extract task_id from data like "toggle_watermark_videos_123"
                    task_id = int(data.replace("toggle_watermark_videos_", ""))
                    await self.toggle_watermark_media_type(event, task_id, 'videos')
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للفيديوهات: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_watermark_documents_"): # Handler for toggle watermark documents
                try:
                    # Extract task_id from data like "toggle_watermark_documents_123"
                    task_id = int(data.replace("toggle_watermark_documents_", ""))
                    await self.toggle_watermark_media_type(event, task_id, 'documents')
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل العلامة المائية للمستندات: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_watermark_position_"): # Handler for set watermark position
                try:
                    # Extract task_id and position from data like "set_watermark_position_top_left_123"
                    # Remove "set_watermark_position_" prefix
                    remaining = data.replace("set_watermark_position_", "")
                    
                    # Find the last underscore to separate position from task_id
                    last_underscore = remaining.rfind("_")
                    if last_underscore != -1:
                        position = remaining[:last_underscore]
                        task_id = int(remaining[last_underscore + 1:])
                        
                        # Validate position
                        valid_positions = ['top_left', 'top', 'top_right', 'bottom_left', 'bottom', 'bottom_right', 'center']
                        if position in valid_positions:
                            await self.set_watermark_position(event, task_id, position)
                        else:
                            logger.error(f"❌ موقع غير صحيح: {position}")
                            await event.answer("❌ موقع غير صحيح")
                    else:
                        logger.error(f"❌ تنسيق بيانات غير صحيح: {data}")
                        await event.answer("❌ خطأ في تنسيق البيانات")
                except (ValueError, IndexError) as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد موقع العلامة المائية: {e}, data='{data}'")
                    await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_watermark_"): # Handler for editing watermark appearance
                try:
                    # Extract setting_type and task_id from data like "edit_watermark_size_123"
                    # Remove "edit_watermark_" prefix
                    remaining = data.replace("edit_watermark_", "")
                    
                    # Find the last underscore to separate setting_type from task_id
                    last_underscore = remaining.rfind("_")
                    if last_underscore != -1:
                        setting_type = remaining[:last_underscore]
                        task_id = int(remaining[last_underscore + 1:])
                        
                        # Validate setting_type
                        valid_settings = ['size', 'opacity', 'font_size', 'color']
                        if setting_type in valid_settings:
                            await self.start_edit_watermark_setting(event, task_id, setting_type)
                        else:
                            logger.error(f"❌ نوع إعداد غير صحيح: {setting_type}")
                            await event.answer("❌ نوع إعداد غير صحيح")
                    else:
                        logger.error(f"❌ تنسيق بيانات غير صحيح: {data}")
                        await event.answer("❌ خطأ في تنسيق البيانات")
                except ValueError as e:
                    logger.error(f"❌ خطأ في تحليل معرف المهمة لتحرير العلامة المائية: {e}, data='{data}'")
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
                        await self.toggle_inline_button_block_mode(event, task_id)
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
            elif data.startswith("remove_text_clean_keyword_"):
                try:
                    task_id = int(data.replace("remove_text_clean_keyword_", ""))
                    user_id = event.sender_id
                    self.db.set_conversation_state(user_id, 'removing_text_cleaning_keyword', json.dumps({'task_id': task_id}))
                    await self.edit_or_send_message(event, "🗑️ أرسل الآن الكلمة/العبارة المراد حذفها من القائمة.")
                except ValueError:
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
                        # Ensure day_number is within valid range (0-6)
                        if 0 <= day_number <= 6:
                            await self.toggle_day_filter(event, task_id, day_number)
                        else:
                            logger.error(f"❌ رقم اليوم خارج النطاق المسموح: {day_number}")
                            await event.answer("❌ رقم اليوم غير صحيح")
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
            elif data.startswith("confirm_clear_replacements_"): # Handler for confirming clear replacements
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.clear_replacements_execute(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتأكيد حذف الاستبدالات: {e}, data='{data}', parts={parts}")
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
            elif data.startswith("toggle_header_scope_texts_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[-1])
                        settings = self.db.get_message_settings(task_id)
                        new_val = not bool(settings.get('apply_header_to_texts', True))
                        self.db.update_message_settings_scope(task_id, apply_header_to_texts=new_val)
                        await event.answer("✅ تم تحديث نطاق الرأس للنصوص")
                        await self.show_header_settings(event, task_id)
                    except Exception as e:
                        logger.error(f"خطأ تحديث نطاق الرأس للنصوص: {e}")
                        await event.answer("❌ فشل في التحديث")
            elif data.startswith("toggle_header_scope_media_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[-1])
                        settings = self.db.get_message_settings(task_id)
                        new_val = not bool(settings.get('apply_header_to_media', True))
                        self.db.update_message_settings_scope(task_id, apply_header_to_media=new_val)
                        await event.answer("✅ تم تحديث نطاق الرأس للوسائط")
                        await self.show_header_settings(event, task_id)
                    except Exception as e:
                        logger.error(f"خطأ تحديث نطاق الرأس للوسائط: {e}")
                        await event.answer("❌ فشل في التحديث")
            elif data.startswith("toggle_footer_scope_texts_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[-1])
                        settings = self.db.get_message_settings(task_id)
                        new_val = not bool(settings.get('apply_footer_to_texts', True))
                        self.db.update_message_settings_scope(task_id, apply_footer_to_texts=new_val)
                        await event.answer("✅ تم تحديث نطاق الذيل للنصوص")
                        await self.show_footer_settings(event, task_id)
                    except Exception as e:
                        logger.error(f"خطأ تحديث نطاق الذيل للنصوص: {e}")
                        await event.answer("❌ فشل في التحديث")
            elif data.startswith("toggle_footer_scope_media_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[-1])
                        settings = self.db.get_message_settings(task_id)
                        new_val = not bool(settings.get('apply_footer_to_media', True))
                        self.db.update_message_settings_scope(task_id, apply_footer_to_media=new_val)
                        await event.answer("✅ تم تحديث نطاق الذيل للوسائط")
                        await self.show_footer_settings(event, task_id)
                    except Exception as e:
                        logger.error(f"خطأ تحديث نطاق الذيل للوسائط: {e}")
                        await event.answer("❌ فشل في التحديث")
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
                        await self.publishing_manager.show_publishing_mode_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات وضع النشر: {e}")
                        await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("toggle_publishing_mode_"):
                # Handle publishing mode toggle
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.publishing_manager.toggle_publishing_mode(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل وضع النشر: {e}")
                        await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("show_pending_messages_"):
                # Handle showing pending messages
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.publishing_manager.show_pending_messages(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لعرض الرسائل المعلقة: {e}")
                        await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("show_pending_details_"):
                # Handle showing pending message details
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        pending_id = int(parts[3])
                        await self.publishing_manager.show_pending_message_details(event, pending_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف الرسالة المعلقة: {e}")
                        await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("approve_message_"):
                # Handle message approval
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        pending_id = int(parts[2])
                        await self.publishing_manager.handle_message_approval(event, pending_id, True)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف الرسالة للموافقة: {e}")
                        await event.answer("❌ خطأ في معالجة الطلب")
            elif data.startswith("word_filters_help_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.word_filters_help(event, task_id)
                    except ValueError:
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("reject_message_"):
                # Handle message rejection
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        pending_id = int(parts[2])
                        await self.publishing_manager.handle_message_approval(event, pending_id, False)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف الرسالة للرفض: {e}")
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
            elif data.startswith("toggle_preserve_reply_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_preserve_reply(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل الحفاظ على الرد: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("pin_settings_"):
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_pin_settings(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لإعدادات التثبيت: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_sync_pin_"):
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_sync_pin(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل مزامنة التثبيت: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_clear_pin_notif_"):
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[4])
                        await self.toggle_clear_pin_notification(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل مسح إشعار التثبيت: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_pin_clear_time_"):
                parts = data.split("_")
                if len(parts) >= 6:
                    try:
                        task_id = int(parts[3])
                        seconds = int(parts[4]) if parts[4].isdigit() else int(parts[5])
                        await self.set_pin_clear_time_direct(event, task_id, seconds)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة/الوقت لمسح إشعار التثبيت: {e}")
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
                        await self.toggle_inline_button_block_mode(event, task_id)
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
            elif data.startswith("set_working_hours_schedule_"): # Handler for setting working hours schedule
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[4])  # "set_working_hours_schedule_TASK_ID"
                        await self.show_working_hours_schedule(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لجدول ساعات العمل: {e}")
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
                        await self.show_working_hours_schedule(event, task_id)
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
            elif data.startswith("quick_remove_lang_"): # Handler for quick language removal
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[3])
                        language_code = parts[4]
                        language_name = "_".join(parts[5:]) if len(parts) > 5 else parts[4]
                        await self.quick_remove_language(event, task_id, language_code, language_name)
                    except ValueError as e:
                        logger.error(f"خطأ في حذف اللغة السريعة: {e}")
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
            elif data.startswith("quick_add_languages_"): # Handler for quick add languages
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.show_quick_add_languages(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في الإضافة السريعة للغات: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("duplicate_filter_") and not data.startswith("duplicate_filter_enabled"): # Handler for duplicate filter main page
                parts = data.split("_")
                if len(parts) >= 3:
                    try:
                        task_id = int(parts[2])
                        await self.show_duplicate_filter(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لفلتر التكرار: {e}")
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
            elif data.startswith("toggle_duplicate_text_"): # Handler for toggling duplicate text check
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_duplicate_text_check(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل فحص النص: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("toggle_duplicate_media_"): # Handler for toggling duplicate media check
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.toggle_duplicate_media_check(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتبديل فحص الوسائط: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_duplicate_threshold_"): # Handler for setting duplicate threshold
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_set_duplicate_threshold(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد نسبة التشابه: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("set_duplicate_time_"): # Handler for setting duplicate time window
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.start_set_duplicate_time(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة لتحديد النافذة الزمنية: {e}")
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
            elif data.startswith("toggle_source_admin_"): # Handler for toggling specific source admin
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[3])
                        admin_user_id = int(parts[4])
                        source_chat_id = parts[5]
                        await self.toggle_source_admin_filter(event, task_id, admin_user_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المشرف: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("refresh_source_admins_"): # Handler for refreshing source admins
                parts = data.split("_")
                if len(parts) >= 5:
                    try:
                        task_id = int(parts[3])
                        source_chat_id = parts[4]
                        await self.refresh_source_admins(event, task_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحديث مشرفي المصدر: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("refresh_all_admins_"): # Handler for refreshing all admins
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[3])
                        await self.refresh_all_admins(event, task_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحديث جميع المشرفين: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("enable_all_source_admins_"): # Handler for enabling all source admins
                parts = data.split("_")
                if len(parts) >= 6:
                    try:
                        task_id = int(parts[4])
                        source_chat_id = parts[5]
                        await self.enable_all_source_admins(event, task_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تفعيل جميع المشرفين: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("disable_all_source_admins_"): # Handler for disabling all source admins
                parts = data.split("_")
                if len(parts) >= 6:
                    try:
                        task_id = int(parts[4])
                        source_chat_id = parts[5]
                        await self.disable_all_source_admins(event, task_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تعطيل جميع المشرفين: {e}")
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
            elif data.startswith("manage_signatures_"): # Handler for managing admin signatures
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        source_chat_id = parts[3]
                        await self.manage_admin_signatures(event, task_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة/المصدر: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("edit_admin_signature_"): # Handler for editing admin signature
                parts = data.split("_")
                if len(parts) >= 6:
                    try:
                        task_id = int(parts[3])
                        admin_user_id = int(parts[4])
                        source_chat_id = parts[5]
                        await self.edit_admin_signature(event, task_id, admin_user_id, source_chat_id)
                    except ValueError as e:
                        logger.error(f"❌ خطأ في تحليل معرف المهمة/المشرف/المصدر: {e}")
                        await event.answer("❌ خطأ في تحليل البيانات")
            elif data.startswith("manage_signatures_"): # Handler for managing admin signatures
                parts = data.split("_")
                if len(parts) >= 4:
                    try:
                        task_id = int(parts[2])
                        source_chat_id = parts[3]
                        await self.manage_admin_signatures(event, task_id, source_chat_id)
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
                
                # Return to the appropriate filter menu based on filter type with error handling
                try:
                    if filter_type == 'duplicate_filter_enabled':
                        await self.show_duplicate_filter(event, task_id)
                    elif filter_type == 'inline_button_filter_enabled':
                        await self.show_inline_button_filter(event, task_id)
                    elif filter_type == 'forwarded_message_filter_enabled':
                        await self.show_forwarded_message_filter(event, task_id)
                    elif filter_type == 'language_filter_enabled':
                        await self.show_language_filters(event, task_id)
                    elif filter_type == 'admin_filter_enabled':
                        await self.show_admin_filters(event, task_id)
                    elif filter_type == 'day_filter_enabled':
                        await self.show_day_filters(event, task_id)
                    elif filter_type == 'working_hours_enabled':
                        await self.show_working_hours_filter(event, task_id)
                    else:
                        await self.show_advanced_filters(event, task_id)
                except Exception as e:
                    if "Content of the message was not modified" in str(e):
                        logger.debug(f"المحتوى لم يتغير، الفلتر {filter_type} محدث بنجاح")
                        # Add timestamp to force refresh
                        import time
                        timestamp = int(time.time()) % 100
                        try:
                            if filter_type == 'duplicate_filter_enabled':
                                await self.force_refresh_duplicate_filter(event, task_id, timestamp)
                        except:
                            pass  # If still fails, at least the setting was updated
                    else:
                        raise e
            else:
                await event.answer("❌ فشل في تحديث الإعداد")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل الفلتر المتقدم: {e}")
            await event.answer("❌ حدث خطأ في التحديث")
            
    async def force_refresh_duplicate_filter(self, event, task_id, timestamp):
        """Force refresh duplicate filter display with timestamp"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            return
            
        # Get current settings
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        is_enabled = advanced_settings.get('duplicate_filter_enabled', False)
        
        # Get duplicate specific settings
        settings = self.db.get_duplicate_settings(task_id)
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
        
        message_text = (
            f"🔄 فلتر التكرار - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📏 نسبة التشابه: {threshold}%\n"
            f"⏱️ النافذة الزمنية: {time_window} ساعة\n"
            f"📝 فحص النص: {'✅' if check_text else '❌'}\n"
            f"🎬 فحص الوسائط: {'✅' if check_media else '❌'}\n\n"
            f"💡 هذا الفلتر يمنع توجيه الرسائل المتكررة\n"
            f"⏰ محدث: {timestamp}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        for i, day in enumerate(days):  # Use 0-based indexing (Monday=0, Sunday=6)
            is_selected = any(df['day_number'] == i and df['is_allowed'] for df in day_filters)
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
        
        # Add unique timestamp to force UI refresh
        import time
        import random
        timestamp = int(time.time() * 1000) % 10000 + random.randint(1, 999)
        
        # Count selected days
        selected_days_count = sum(1 for df in day_filters if df['is_allowed'])
        
        message_text = (
            f"📅 فلتر الأيام - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📋 الأيام المحددة: {selected_days_count}/7\n\n"
            f"اختر الأيام المسموح بالتوجيه فيها:\n"
            f"⏰ آخر تحديث: {timestamp}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def toggle_day_filter(self, event, task_id, day_number):
        """Toggle specific day filter"""
        user_id = event.sender_id
        
        try:
            # Get current day filters
            day_filters = self.db.get_day_filters(task_id)
            is_selected = any(df['day_number'] == day_number and df['is_allowed'] for df in day_filters)
            
            if is_selected:
                # Remove the day by setting to False
                success = self.db.set_day_filter(task_id, day_number, False)
                action = "تم إلغاء تحديد"
            else:
                # Add the day by setting to True
                success = self.db.set_day_filter(task_id, day_number, True)
                action = "تم تحديد"
            
            if success:
                days = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]
                day_name = days[day_number] if 0 <= day_number < len(days) else f"اليوم {day_number}"
                await event.answer(f"✅ {action} {day_name}")
                
                # Force refresh UserBot tasks
                try:
                    from userbot_service.userbot import userbot_instance
                    if user_id in userbot_instance.clients:
                        await userbot_instance.refresh_user_tasks(user_id)
                except Exception as e:
                    logger.error(f"خطأ في تحديث مهام UserBot: {e}")
                
                # Refresh with error handling for "Content not modified"
                try:
                    await self.show_day_filters(event, task_id)
                except Exception as refresh_error:
                    if "Content of the message was not modified" in str(refresh_error):
                        logger.debug("المحتوى لم يتغير، تجاهل الخطأ")
                    else:
                        logger.error(f"خطأ في تحديث واجهة فلتر الأيام: {refresh_error}")
                        raise refresh_error
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
                # Add all days using set_day_filter (0-6 for Monday-Sunday)
                for day_num in range(0, 7):
                    self.db.set_day_filter(task_id, day_num, True)
                await event.answer("✅ تم تحديد جميع الأيام")
            else:
                # Remove all days using set_day_filter with False (0-6 for Monday-Sunday)
                for day_num in range(0, 7):
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
        
        message_text = (
            f"🔍 الفلاتر المتقدمة - المهمة #{task_id}\n\n"
            f"📊 حالة الفلاتر:\n"
            f"• {day_status} فلتر الأيام\n"
            f"• {hours_status} ساعات العمل\n"
            f"• {lang_status} فلتر اللغات\n"
            f"• {admin_status} فلتر المشرفين\n"
            f"• {duplicate_status} فلتر التكرار\n"
            f"• {inline_status} الأزرار الإنلاين\n"
            f"• {forwarded_status} الرسائل المُوجهة\n\n"
            f"اختر الفلتر الذي تريد إدارته:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def show_advanced_features(self, event, task_id):
        """Show advanced features menu"""
        user_id = event.sender_id if hasattr(event, 'sender_id') else None
        
        # Try to get task with user_id first, then without if user_id is None
        task = self.db.get_task(task_id, user_id) if user_id else self.db.get_task(task_id)
        
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
            [Button.inline("🔁 المنشورات المتكررة", f"recurring_posts_{task_id}")],
            [Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")]
        ]
        
        message_text = (
            f"⚡ الميزات المتقدمة - المهمة #{task_id}\n\n"
            f"📊 حالة الميزات:\n"
            f"• {char_status} حدود الأحرف\n"
            f"• {rate_status} حد المعدل\n"
            f"• {delay_status} تأخير التوجيه\n"
            f"• {interval_status} فاصل الإرسال\n\n"
            f"اختر الميزة التي تريد إدارتها:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_message(self, event):
        """Handle text messages"""
        # Skip if it's a command
        if event.text.startswith('/'):
            return

        user_id = event.sender_id
        message_text = event.text

        # If user forwarded a message and is in add-channel state, try to extract channel
        try:
            state_tuple = self.db.get_conversation_state(user_id)
            if state_tuple and state_tuple[0] in ['waiting_channel_link', 'waiting_multiple_channels']:
                fwd = event.message.fwd_from
                if fwd and getattr(fwd, 'from_id', None):
                    try:
                        # Resolve original chat from the forwarded message
                        orig_peer_id = get_peer_id(fwd.from_id)
                        from userbot_service.userbot import userbot_instance
                        client = userbot_instance.clients.get(user_id)
                        if client:
                            orig = await client.get_entity(orig_peer_id)
                            link = getattr(orig, 'username', None) and f"@{orig.username}" or str(getattr(orig, 'id', ''))
                            if link:
                                # Reuse existing channel processing
                                added = await self.channels_management.process_channel_link(event, link)
                                if state_tuple[0] == 'waiting_multiple_channels' and added:
                                    # Append into current list
                                    refreshed = self.db.get_conversation_state(user_id)
                                    try:
                                        data_json = json.loads(refreshed[1]) if refreshed and refreshed[1] else {}
                                    except Exception:
                                        data_json = {}
                                    lst = data_json.get('channels', [])
                                    lst.append(added)
                                    data_json['channels'] = lst
                                    self.db.set_conversation_state(user_id, 'waiting_multiple_channels', json.dumps(data_json))
                                    await event.answer("✅ تم إضافة القناة عبر الرسالة المحولة. أرسل أخرى أو اضغط إنهاء.")
                                else:
                                    # Single add: clear and show list
                                    self.db.clear_conversation_state(user_id)
                                    await self.list_channels(event)
                                return
                    except Exception as e:
                        logger.debug(f"تعذر استخراج القناة من الرسالة المحولة: {e}")
        except Exception:
            pass

        # New: handle recurring post forward capture
        try:
            state_tuple = self.db.get_conversation_state(user_id)
            if state_tuple and state_tuple[0] == 'waiting_recurring_forward':
                task_id = int(state_tuple[1]) if state_tuple[1] else None
                fwd = event.message.fwd_from
                if not fwd or not getattr(fwd, 'from_id', None):
                    await self.edit_or_send_message(event, "❌ يجب إعادة توجيه رسالة من القناة المصدر.")
                    return
                # Determine original source chat and message id
                orig_peer_id = get_peer_id(fwd.from_id)
                from userbot_service.userbot import userbot_instance
                client = userbot_instance.clients.get(user_id)
                if not client:
                    await self.edit_or_send_message(event, "❌ UserBot غير متصل. يرجى تسجيل الدخول.")
                    return
                try:
                    # Normalize entity and get original message id
                    source_chat_id = str(orig_peer_id)
                    source_message_id = getattr(fwd, 'channel_post', None) or getattr(fwd, 'msg_id', None) or event.message.id
                    if not source_message_id:
                        source_message_id = event.message.id
                    # Ask for interval seconds
                    import json
                    payload = {
                        'task_id': task_id,
                        'source_chat_id': source_chat_id,
                        'source_message_id': int(source_message_id)
                    }
                    self.db.set_conversation_state(user_id, 'editing_recurring_interval_init', json.dumps(payload))
                    await self.edit_or_send_message(event, "⏱️ أدخل الفترة بالثواني للنشر المتكرر (مثال: 3600)")
                    return
                except Exception as e:
                    logger.error(f"خطأ في استخراج معلومات الرسالة المحولة: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ أثناء قراءة الرسالة.")
                    return
        except Exception:
            pass

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
                    await self.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
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
                    await self.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                    self.clear_user_state(user_id)
                    return

            elif current_user_state == 'awaiting_album_art_upload':
                task_id = current_user_data.get('task_id')
                try:
                    import os
                    os.makedirs('album_art', exist_ok=True)
                    file_path = None
                    if event.message.photo or (event.message.document and 'image' in (event.message.document.mime_type or '')):
                        file_path = f"album_art/album_art_{task_id}.jpg"
                        await self.bot.download_media(event.message, file=file_path)
                    else:
                        await self.edit_or_send_message(event, "❌ يرجى إرسال صورة كصورة أو ملف.")
                        return
                    if file_path and os.path.exists(file_path):
                        self.db.set_album_art_settings(task_id, path=file_path, enabled=True)
                        await self.edit_or_send_message(event, "✅ تم حفظ صورة الغلاف")
                        await self.album_art_settings(event, task_id)
                    else:
                        await self.edit_or_send_message(event, "❌ فشل في حفظ الصورة")
                except Exception as e:
                    logger.error(f"خطأ في حفظ صورة الغلاف: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ أثناء رفع الصورة")
                finally:
                    self.clear_user_state(user_id)
                return

            elif current_user_state == 'awaiting_intro_audio_upload':
                task_id = current_user_data.get('task_id')
                try:
                    import os
                    os.makedirs('audio_segments', exist_ok=True)
                    file_path = f"audio_segments/intro_{task_id}.mp3"
                    if event.message.document and (event.message.document.mime_type or '').startswith('audio/'):
                        await self.bot.download_media(event.message, file=file_path)
                        self.db.set_audio_merge_settings(task_id, intro_path=file_path)
                        await self.edit_or_send_message(event, "✅ تم حفظ مقطع المقدمة")
                        await self.audio_merge_settings(event, task_id)
                    else:
                        await self.edit_or_send_message(event, "❌ يرجى إرسال ملف صوتي.")
                        return
                except Exception as e:
                    logger.error(f"خطأ في حفظ مقطع المقدمة: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ أثناء رفع المقطع")
                finally:
                    self.clear_user_state(user_id)
                return

            elif current_user_state == 'awaiting_outro_audio_upload':
                task_id = current_user_data.get('task_id')
                try:
                    import os
                    os.makedirs('audio_segments', exist_ok=True)
                    file_path = f"audio_segments/outro_{task_id}.mp3"
                    if event.message.document and (event.message.document.mime_type or '').startswith('audio/'):
                        await self.bot.download_media(event.message, file=file_path)
                        self.db.set_audio_merge_settings(task_id, outro_path=file_path)
                        await self.edit_or_send_message(event, "✅ تم حفظ مقطع الخاتمة")
                        await self.audio_merge_settings(event, task_id)
                    else:
                        await self.edit_or_send_message(event, "❌ يرجى إرسال ملف صوتي.")
                        return
                except Exception as e:
                    logger.error(f"خطأ في حفظ مقطع الخاتمة: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ أثناء رفع المقطع")
                finally:
                    self.clear_user_state(user_id)
                return
            elif current_user_state.startswith('editing_audio_tag_'):
                try:
                    tag_name = current_user_state.replace('editing_audio_tag_', '')
                    task_id = current_user_data.get('task_id')
                    new_template = message_text.strip()
                    
                    # Validate template (basic validation)
                    if not new_template:
                        await self.edit_or_send_message(event, "❌ لا يمكن أن يكون القالب فارغاً")
                        return
                    
                    # Update the template
                    success = self.db.update_audio_template_setting(task_id, tag_name, new_template)
                    if success:
                        await self.edit_or_send_message(event, f"✅ تم تحديث قالب {tag_name} بنجاح")
                        await self.audio_template_settings(event, task_id)
                    else:
                        await self.edit_or_send_message(event, "❌ فشل في تحديث القالب")
                except Exception as e:
                    logger.error(f"خطأ في تحديث قالب الوسم الصوتي: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                finally:
                    self.clear_user_state(user_id)
                return
                    
            elif current_user_state == 'editing_char_min': # Handle editing character minimum
                task_id = current_user_data.get('task_id')
                if task_id:
                    try:
                        min_chars = int(message_text.strip())
                        if 1 <= min_chars <= 10000:
                            success = self.db.update_character_limit_values(task_id, min_chars=min_chars)
                            if success:
                                await self.edit_or_send_message(event, f"✅ تم تحديث الحد الأدنى إلى {min_chars} حرف")
                                # Force refresh UserBot tasks
                                await self._refresh_userbot_tasks(user_id)
                            else:
                                await self.edit_or_send_message(event, "❌ فشل في تحديث الحد الأدنى")
                        else:
                            await self.edit_or_send_message(event, "❌ يجب أن يكون الرقم بين 1 و 10000")
                            return
                    except ValueError:
                        await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
                        return
                    
                    self.clear_user_state(user_id)
                    await self.show_character_limit_settings(event, task_id)
                return
                
            elif current_user_state == 'editing_char_max': # Handle editing character maximum
                task_id = current_user_data.get('task_id')
                if task_id:
                    try:
                        max_chars = int(message_text.strip())
                        if 1 <= max_chars <= 10000:
                            success = self.db.update_character_limit_values(task_id, max_chars=max_chars)
                            if success:
                                await self.edit_or_send_message(event, f"✅ تم تحديث الحد الأقصى إلى {max_chars} حرف")
                                # Force refresh UserBot tasks
                                await self._refresh_userbot_tasks(user_id)
                            else:
                                await self.edit_or_send_message(event, "❌ فشل في تحديث الحد الأقصى")
                        else:
                            await self.edit_or_send_message(event, "❌ يجب أن يكون الرقم بين 1 و 10000")
                            return
                    except ValueError:
                        await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
                        return
                    
                    self.clear_user_state(user_id)
                    await self.show_character_limit_settings(event, task_id)
                return
                
            elif current_user_state == 'editing_forwarding_delay': # Handle editing forwarding delay
                task_id = current_user_data.get('task_id')
                if task_id:
                    await self.handle_edit_forwarding_delay(event, task_id, message_text)
                    self.clear_user_state(user_id)
                    # Send new message instead of editing
                    await self.send_forwarding_delay_settings(event, task_id)
                return
                
            elif current_user_state == 'editing_sending_interval': # Handle editing sending interval
                task_id = current_user_data.get('task_id')
                if task_id:
                    await self.handle_edit_sending_interval(event, task_id, message_text)
                    self.clear_user_state(user_id)
                    # Send new message instead of editing
                    await self.send_sending_interval_settings(event, task_id)
                return
            elif current_user_state.startswith('edit_signature_'): # Handle editing admin signature
                try:
                    parts = current_user_state.split('_')
                    if len(parts) >= 4:
                        task_id = int(parts[2])
                        admin_user_id = int(parts[3])
                        source_chat_id = current_user_data.get('source_chat_id', '')
                        if not source_chat_id:
                            # Try to extract from state if not in data
                            source_chat_id = parts[4] if len(parts) > 4 else ''
                        
                        if source_chat_id:
                            await self.handle_signature_input(event, task_id, admin_user_id, source_chat_id)
                        else:
                            await self.edit_or_send_message(event, "❌ خطأ في تحديد المصدر")
                            self.clear_user_state(user_id)
                    else:
                        await self.edit_or_send_message(event, "❌ خطأ في تحليل البيانات")
                        self.clear_user_state(user_id)
                except Exception as e:
                    logger.error(f"خطأ في معالجة إدخال توقيع المشرف: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                    self.clear_user_state(user_id)
                return
                
            elif current_user_state == 'editing_rate_count': # Handle editing rate count
                task_id = current_user_data.get('task_id')
                if task_id:
                    await self.handle_edit_rate_count(event, task_id, message_text)
                    self.clear_user_state(user_id)
                    # Send new message instead of editing
                    await self.send_rate_limit_settings(event, task_id)
                return
                
            elif current_user_state == 'editing_rate_period': # Handle editing rate period
                task_id = current_user_data.get('task_id')
                if task_id:
                    await self.handle_edit_rate_period(event, task_id, message_text)
                    self.clear_user_state(user_id)
                    # Send new message instead of editing
                    await self.send_rate_limit_settings(event, task_id)
                return

        # Check if user is in authentication or task creation process (old system)
        state_data = self.db.get_conversation_state(user_id)

        if state_data:
            state, data_str = state_data
            logger.debug(f"قراءة حالة المستخدم {user_id}: state={state}, data_type={type(data_str)}")
            try:
                if isinstance(data_str, dict):
                    data = data_str
                else:
                    data = json.loads(data_str) if data_str else {}
                    if data and state in ['waiting_code', 'waiting_password']:
                        logger.info(f"بيانات المصادقة المُحللة للمستخدم {user_id}: {list(data.keys())}")
            except Exception as e:
                logger.error(f"خطأ في تحليل بيانات الحالة للمستخدم {user_id}: {e}")
                logger.error(f"البيانات الأصلية: {data_str}")
                data = {}

            state_data = (state, data)

            # Handle authentication states
            if state in ['waiting_phone', 'waiting_code', 'waiting_password', 'waiting_session']:
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
                    message_text = (
                        "❌ حدث خطأ أثناء إضافة المصدر/الهدف\n\n"
                        "حاول مرة أخرى أو اضغط /start للعودة للقائمة الرئيسية"
                    )
                    await self.edit_or_send_message(event, message_text)
                    self.db.clear_conversation_state(user_id)
                return
            # Handle channels management states (single/multiple add)
            elif state == 'waiting_channel_link':
                try:
                    # Accept multiple channels in one message (each line is a channel)
                    lines = [ln.strip() for ln in message_text.splitlines() if ln.strip()]
                    if not lines:
                        await self.edit_or_send_message(event, "❌ يرجى إرسال رابط/معرف/رقم قناة واحد على الأقل")
                        return

                    added_list = []
                    error_count = 0
                    for ln in lines:
                        try:
                            added = await self.channels_management.process_channel_link(event, ln, silent=True)
                            if added:
                                added_list.append(added)
                            else:
                                error_count += 1
                        except Exception:
                            error_count += 1

                    # Clear state regardless to avoid being stuck
                    self.db.clear_conversation_state(user_id)

                    # Summary message
                    if added_list:
                        preview = "\n".join(
                            [f"• {item.get('chat_name') or item.get('chat_id')}" for item in added_list[:5]]
                        )
                        more = f"\n... و {len(added_list)-5} قناة أخرى" if len(added_list) > 5 else ""
                        summary = (
                            f"✅ تم إضافة {len(added_list)} قناة" + (f"، وفشل {error_count}" if error_count else "") + "\n\n" + preview + more
                        )
                        await self.edit_or_send_message(event, summary)
                    else:
                        await self.edit_or_send_message(event, "❌ لم يتم إضافة أي قناة. تأكد من صحة المدخلات أو عضويتك في القنوات")

                    # Show updated channels list
                    await self.list_channels(event)
                    return
                except Exception as e:
                    logger.error(f"خطأ في معالجة روابط القنوات للمستخدم {user_id}: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ أثناء إضافة القنوات. حاول مرة أخرى.")
                    self.db.clear_conversation_state(user_id)
                    return
            elif state == 'waiting_multiple_channels':
                # Backward-compat fallback: treat same as waiting_channel_link (multi-line supported)
                try:
                    lines = [ln.strip() for ln in message_text.splitlines() if ln.strip()]
                    added_list = []
                    error_count = 0
                    for ln in lines:
                        try:
                            added = await self.channels_management.process_channel_link(event, ln, silent=True)
                            if added:
                                added_list.append(added)
                            else:
                                error_count += 1
                        except Exception:
                            error_count += 1
                    self.db.clear_conversation_state(user_id)
                    if added_list:
                        await self.edit_or_send_message(event, f"✅ تم إضافة {len(added_list)} قناة")
                        await self.list_channels(event)
                    else:
                        await self.edit_or_send_message(event, "❌ لم يتم إضافة أي قناة")
                    return
                except Exception:
                    self.db.clear_conversation_state(user_id)
                    await self.edit_or_send_message(event, "❌ حدث خطأ أثناء إضافة القنوات")
                    return
            elif state == 'adding_multiple_words': # Handle adding multiple words state
                await self.handle_adding_multiple_words(event, state_data)
                return
            elif state == 'adding_text_cleaning_keywords': # Handle adding text cleaning keywords
                await self.handle_adding_text_cleaning_keywords(event, state_data)
                return
            elif state == 'removing_text_cleaning_keyword': # Handle removing one keyword
                try:
                    user_id = event.sender_id
                    state, data = state_data
                    if isinstance(data, str):
                        stored = json.loads(data) if data.strip() else {}
                    else:
                        stored = data or {}
                    task_id = int(stored.get('task_id'))
                    text = (event.text or '').strip()
                    self.db.clear_conversation_state(user_id)
                    await self.handle_removing_text_cleaning_keyword(event, task_id, text)
                except Exception as e:
                    logger.error(f"خطأ في حذف كلمة التنظيف: {e}")
                    await event.answer("❌ فشل في حذف الكلمة")
                return
            elif state.startswith('watermark_text_input_'): # Handle watermark text input
                try:
                    # Handle both dict and non-dict data
                    if isinstance(data, dict):
                        task_id = data.get('task_id')
                    else:
                        task_id = None
                    
                    if task_id:
                        await self.handle_watermark_text_input(event, task_id)
                    else:
                        # Extract task_id from state if not in data
                        task_id = int(state.split('_')[-1])
                        await self.handle_watermark_text_input(event, task_id)
                except Exception as e:
                    logger.error(f"خطأ في معالجة إدخال نص العلامة المائية: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                    self.clear_user_state(user_id)
                return
            elif state.startswith('watermark_image_input_'): # Handle watermark image input
                try:
                    # Handle both dict and non-dict data
                    if isinstance(data, dict):
                        task_id = data.get('task_id')
                    else:
                        task_id = None
                    
                    if task_id:
                        await self.handle_watermark_image_input(event, task_id)
                    else:
                        # Extract task_id from state if not in data
                        task_id = int(state.split('_')[-1])
                        await self.handle_watermark_image_input(event, task_id)
                except Exception as e:
                    logger.error(f"خطأ في معالجة إدخال صورة العلامة المائية: {e}")
                    await self.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
                    self.clear_user_state(user_id)
                return
            elif state == 'waiting_watermark_size': # Handle setting watermark size
                task_id = self.extract_task_id_from_data(data)
                await self.handle_watermark_setting_input(event, task_id, 'size', event.text)
                return
            elif state == 'waiting_watermark_opacity': # Handle setting watermark opacity
                task_id = self.extract_task_id_from_data(data)
                await self.handle_watermark_setting_input(event, task_id, 'opacity', event.text)
                return
            elif state == 'waiting_watermark_font_size': # Handle setting watermark font size
                task_id = self.extract_task_id_from_data(data)
                await self.handle_watermark_setting_input(event, task_id, 'font_size', event.text)
                return
            elif state == 'waiting_watermark_color': # Handle setting watermark color
                task_id = self.extract_task_id_from_data(data)
                await self.handle_watermark_setting_input(event, task_id, 'color', event.text)
                return

            elif state == 'waiting_text_replacements': # Handle adding text replacements
                task_id = self.extract_task_id_from_data(data)
                await self.handle_add_replacements(event, task_id, event.text)
                return
            elif state == 'waiting_header_text': # Handle editing header text
                task_id = self.extract_task_id_from_data(data)
                await self.handle_set_header_text(event, task_id, event.text)
                return
            elif state == 'waiting_footer_text': # Handle editing footer text
                task_id = self.extract_task_id_from_data(data)
                await self.handle_set_footer_text(event, task_id, event.text)
                return
            elif state == 'waiting_button_data': # Handle adding inline button
                task_id = self.extract_task_id_from_data(data)
                await self.handle_add_inline_button(event, task_id, event.text)
                return
            elif state == 'editing_char_range': # Handle character range editing
                task_id = self.extract_task_id_from_data(data)
                await self.handle_edit_character_range(event, task_id)
                return

            elif state == 'editing_forwarding_delay': # Handle forwarding delay editing
                task_id = self.extract_task_id_from_data(data)
                await self.handle_edit_forwarding_delay(event, task_id, event.text)
                return
            elif state == 'editing_sending_interval': # Handle sending interval editing
                task_id = self.extract_task_id_from_data(data)
                await self.handle_edit_sending_interval(event, task_id, event.text)
                return
            elif state == 'waiting_auto_delete_time': # Handle setting auto delete time
                task_id = self.extract_task_id_from_data(data)
                await self.handle_set_auto_delete_time(event, task_id, event.text)
                return
            elif state == 'set_working_hours': # Handle setting working hours
                task_id = data.get('task_id')
                await self.handle_set_working_hours(event, task_id, event.text)
                return
            elif state == 'add_language': # Handle adding language filter
                task_id = data.get('task_id')
                await self.handle_add_language_filter(event, task_id, message_text)
                return
            elif state == 'waiting_language_filter': # Handle adding language filter
                task_id = self.extract_task_id_from_data(data)
                await self.handle_add_language_filter(event, task_id, message_text)
                return
            elif state == 'waiting_hyperlink_settings': # Handle editing hyperlink settings
                task_id = data.get('task_id')
                await self.handle_hyperlink_settings(event, task_id, event.text)
                return

        # Handle conversation_states for duplicate filter settings
        if user_id in self.conversation_states:
            state_info = self.conversation_states[user_id]
            state = state_info.get('state')
            task_id = state_info.get('task_id')
            
            if state == 'set_duplicate_threshold':
                try:
                    threshold = int(message_text.strip())
                    if 1 <= threshold <= 100:
                        # Update the setting
                        success = self.db.update_duplicate_setting(task_id, 'similarity_threshold', threshold)
                        if success:
                            # Clear conversation state
                            del self.conversation_states[user_id]
                            # Force refresh UserBot tasks
                            await self._refresh_userbot_tasks(user_id)
                            # Send success message and then show settings
                            await self.edit_or_send_message(event, f"✅ تم تحديد نسبة التشابه إلى {threshold}%")
                            # Show settings after brief delay
                            import asyncio
                            await asyncio.sleep(1.5)
                            await self.show_duplicate_settings(event, task_id)
                        else:
                            await self.edit_or_send_message(event, "❌ فشل في تحديث نسبة التشابه")
                    else:
                        await self.edit_or_send_message(event, "❌ يرجى إدخال نسبة من 1 إلى 100")
                except ValueError:
                    await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح للنسبة")
                return
                
            elif state == 'set_duplicate_time':
                try:
                    hours = int(message_text.strip())
                    if 1 <= hours <= 168:  # 1 hour to 1 week
                        # Update the setting
                        success = self.db.update_duplicate_setting(task_id, 'time_window_hours', hours)
                        if success:
                            # Clear conversation state
                            del self.conversation_states[user_id]
                            # Force refresh UserBot tasks
                            await self._refresh_userbot_tasks(user_id)
                            # Send success message and then show settings
                            await self.edit_or_send_message(event, f"✅ تم تحديد النافذة الزمنية إلى {hours} ساعة")
                            # Show settings after brief delay
                            import asyncio
                            await asyncio.sleep(1.5)
                            await self.show_duplicate_settings(event, task_id)
                        else:
                            await self.edit_or_send_message(event, "❌ فشل في تحديث النافذة الزمنية")
                    else:
                        await self.edit_or_send_message(event, "❌ يرجى إدخال عدد ساعات من 1 إلى 168 (أسبوع)")
                except ValueError:
                    await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح للساعات")
                return

        # Check if this chat is a target chat for any active forwarding task
        chat_id = event.chat_id

        # Get all active tasks from database
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                try:
                    cursor.execute('''
                        SELECT target_chat_id FROM tasks
                        WHERE is_active = TRUE AND target_chat_id = %s
                    ''', (str(chat_id),))
                except Exception:
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
        # Disable auto-reply greeting by default
        logger.info(f"ℹ️ لا يوجد رد تلقائي: user={event.sender_id}, chat={event.chat_id}")

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
            
            # الصف الثامن - العلامة المائية والوسوم الصوتية
            [Button.inline(f"🏷️ العلامة المائية {watermark_status}", f"watermark_settings_{task_id}"),
             Button.inline("🎵 الوسوم الصوتية", f"audio_metadata_settings_{task_id}")],
            
            # الصف التاسع - الفلاتر والميزات المتقدمة
            [Button.inline("🔍 الفلاتر المتقدمة", f"advanced_filters_{task_id}"),
             Button.inline("⚡ الميزات المتقدمة", f"advanced_features_{task_id}")],
            
            # الصف الأخير - العودة
            [Button.inline("🔙 رجوع لتفاصيل المهمة", f"task_manage_{task_id}")]
        ]

        message_text = (
            f"⚙️ إعدادات المهمة: {task_name}\n\n"
            f"📋 الإعدادات الحالية:\n"
            f"• وضع التوجيه: {forward_mode_text}\n"
            f"• عدد المصادر: {sources_count}\n"
            f"• عدد الأهداف: {targets_count}\n"
            f"• فلاتر الوسائط: متاحة\n\n"
            f"اختر الإعداد الذي تريد تعديله:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
            [Button.inline("➕ إضافة مصدر", f"add_source_{task_id}"),
             Button.inline("🧭 اختيار من القنوات", f"choose_add_sources_{task_id}")]
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

        await self.edit_or_send_message(event, message, buttons=buttons)

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
            [Button.inline("➕ إضافة هدف", f"add_target_{task_id}"),
             Button.inline("🧭 اختيار من القنوات", f"choose_add_targets_{task_id}")]
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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        message_text = (
            "➕ إضافة مصدر جديد\n\n"
            "أرسل معرف أو رابط المجموعة/القناة المراد إضافتها كمصدر:\n\n"
            "أمثلة:\n"
            "• @channelname\n"
            "• https://t.me/channelname\n"
            "• -1001234567890\n\n"
            "⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات قراءة الرسائل"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

        message_text = (
            "➕ إضافة هدف جديد\n\n"
            "أرسل معرف أو رابط المجموعة/القناة المراد إضافتها كهدف:\n\n"
            "أمثلة:\n"
            "• @channelname\n"
            "• https://t.me/channelname\n"
            "• -1001234567890\n\n"
            "⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات إرسال الرسائل"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        """Show working hours filter settings with original interface"""
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
            schedule = settings.get('schedule', {})
        else:
            mode = 'work_hours'
            schedule = {}
        
        status_text = "🟢 مفعل" if is_enabled else "🔴 معطل"
        
        # Mode descriptions - clearer explanation
        if mode == 'work_hours':
            mode_text = "🏢 وضع ساعات العمل"
            mode_description = "يتم توجيه الرسائل **فقط** في الساعات الخضراء (ساعات العمل)"
        else:  # sleep_hours
            mode_text = "😴 وضع ساعات النوم"
            mode_description = "يتم حظر الرسائل في الساعات الخضراء (ساعات النوم)"
        
        # Count active hours
        active_hours = sum(1 for enabled in schedule.values() if enabled)
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_working_hours_{task_id}")],
            [Button.inline(f"⚙️ {mode_text}", f"toggle_working_hours_mode_{task_id}")],
            [Button.inline(f"🕐 تحديد الساعات ({active_hours}/24)", f"set_working_hours_schedule_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        message_text = (
            f"⏰ **فلتر ساعات العمل** - المهمة #{task_id}\n\n"
            f"📊 **الحالة:** {status_text}\n"
            f"⚙️ **الوضع:** {mode_text}\n"
            f"🕐 **الساعات النشطة:** {active_hours}/24\n\n"
            f"💡 **الوصف:** {mode_description}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def show_working_hours(self, event, task_id):
        """Show working hours schedule interface"""
        return await self.show_working_hours_schedule(event, task_id)
    
    async def show_working_hours_schedule(self, event, task_id):
        """Show working hours schedule interface"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        settings = self.db.get_working_hours(task_id)
        if settings:
            mode = settings.get('mode', 'work_hours')
            schedule = settings.get('schedule', {})
        else:
            mode = 'work_hours'
            schedule = {}
            # Initialize default schedule
            self.db.initialize_working_hours_schedule(task_id)
        
        # Create 24-hour grid (4 rows x 6 columns)
        buttons = []
        for row in range(4):
            row_buttons = []
            for col in range(6):
                hour = row * 6 + col
                is_enabled = schedule.get(hour, False)
                status = "🟢" if is_enabled else "🔴"
                row_buttons.append(
                    Button.inline(f"{status}{hour:02d}", f"toggle_hour_{task_id}_{hour}")
                )
            buttons.append(row_buttons)
        
        # Add control buttons
        buttons.append([
            Button.inline("✅ تحديد الكل", f"select_all_hours_{task_id}"),
            Button.inline("❌ إلغاء الكل", f"clear_all_hours_{task_id}")
        ])
        buttons.append([
            Button.inline("🔙 رجوع لفلتر ساعات العمل", f"working_hours_filter_{task_id}")
        ])
        
        # Mode description - clearer explanation
        if mode == 'work_hours':
            description = (
                "🏢 **وضع ساعات العمل:**\n"
                "🟢 الساعات الخضراء = ساعات العمل → **يتم توجيه الرسائل**\n"
                "🔴 الساعات الحمراء = خارج ساعات العمل → **يتم حظر الرسائل**"
            )
        else:  # sleep_hours
            description = (
                "😴 **وضع ساعات النوم:**\n"
                "🟢 الساعات الخضراء = ساعات النوم → **يتم حظر الرسائل**\n"
                "🔴 الساعات الحمراء = خارج ساعات النوم → **يتم توجيه الرسائل**"
            )
        
        # Add timestamp to force UI refresh
        import time
        timestamp = int(time.time()) % 100
        
        message_text = (
            f"🕐 **جدولة ساعات العمل** - المهمة #{task_id}\n\n"
            f"⚙️ **الوضع:** {'🏢 ساعات العمل' if mode == 'work_hours' else '😴 ساعات النوم'}\n\n"
            f"{description}\n\n"
            f"اضغط على الساعة لتبديل حالتها:\n"
            f"⏰ آخر تحديث: {timestamp}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def select_all_hours(self, event, task_id):
        """Select all working hours"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Enable all hours using database function
            self.db.set_all_working_hours(task_id, True)
            
            await event.answer("✅ تم تحديد جميع الساعات")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Refresh the schedule display with try-catch for content unchanged error
            try:
                await self.show_working_hours_schedule(event, task_id)
            except Exception as e:
                if "Content of the message was not modified" not in str(e):
                    raise e
                logger.debug("المحتوى لم يتغير، جميع الساعات محدثة بنجاح")
            
        except Exception as e:
            logger.error(f"خطأ في تحديد جميع الساعات للمهمة {task_id}: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def clear_all_hours(self, event, task_id):
        """Clear all working hours"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Disable all hours using database function
            self.db.set_all_working_hours(task_id, False)
            
            await event.answer("✅ تم إلغاء تحديد جميع الساعات")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Refresh the schedule display with try-catch for content unchanged error
            try:
                await self.show_working_hours_schedule(event, task_id)
            except Exception as e:
                if "Content of the message was not modified" not in str(e):
                    raise e
                logger.debug("المحتوى لم يتغير، جميع الساعات محدثة بنجاح")
            
        except Exception as e:
            logger.error(f"خطأ في إلغاء جميع الساعات للمهمة {task_id}: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def toggle_duplicate_text_check(self, event, task_id):
        """Toggle duplicate text checking"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Get current settings
            settings = self.db.get_duplicate_settings(task_id)
            current_value = settings.get('check_text', True)
            new_value = not current_value
            
            # Update the setting
            success = self.db.update_duplicate_setting(task_id, 'check_text', new_value)
            
            if success:
                status = "تم تفعيل" if new_value else "تم تعطيل"
                await event.answer(f"✅ {status} فحص النص")
                
                # Refresh the settings page
                await self.show_duplicate_settings(event, task_id)
            else:
                await event.answer("❌ فشل في تحديث الإعداد")
            
        except Exception as e:
            logger.error(f"خطأ في تبديل فحص النص: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def toggle_duplicate_media_check(self, event, task_id):
        """Toggle duplicate media checking"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Get current settings
            settings = self.db.get_duplicate_settings(task_id)
            current_value = settings.get('check_media', True)
            new_value = not current_value
            
            # Update the setting
            success = self.db.update_duplicate_setting(task_id, 'check_media', new_value)
            
            if success:
                status = "تم تفعيل" if new_value else "تم تعطيل"
                await event.answer(f"✅ {status} فحص الوسائط")
                
                # Refresh the settings page
                await self.show_duplicate_settings(event, task_id)
            else:
                await event.answer("❌ فشل في تحديث الإعداد")
            
        except Exception as e:
            logger.error(f"خطأ في تبديل فحص الوسائط: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def start_set_duplicate_threshold(self, event, task_id):
        """Start setting duplicate threshold conversation"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set conversation state
        self.conversation_states[user_id] = {
            'state': 'set_duplicate_threshold',
            'task_id': task_id,
            'step': 'waiting_threshold'
        }
        
        current_settings = self.db.get_duplicate_settings(task_id)
        current_threshold = current_settings.get('similarity_threshold', 80)
        
        message_text = (
            f"📏 تحديد نسبة التشابه - المهمة #{task_id}\n\n"
            f"📊 النسبة الحالية: {current_threshold}%\n\n"
            f"💡 أدخل نسبة التشابه المطلوبة (من 1 إلى 100):\n"
            f"• نسبة عالية (90-100%) = تطابق شبه تام\n"
            f"• نسبة متوسطة (60-89%) = تشابه كبير\n"
            f"• نسبة منخفضة (1-59%) = تشابه بسيط"
        )
        
        buttons = [[Button.inline("❌ إلغاء", f"duplicate_settings_{task_id}")]]
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_set_duplicate_time(self, event, task_id):
        """Start setting duplicate time window conversation"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set conversation state
        self.conversation_states[user_id] = {
            'state': 'set_duplicate_time',
            'task_id': task_id,
            'step': 'waiting_time'
        }
        
        current_settings = self.db.get_duplicate_settings(task_id)
        current_time = current_settings.get('time_window_hours', 24)
        
        message_text = (
            f"⏱️ تحديد النافذة الزمنية - المهمة #{task_id}\n\n"
            f"📊 النافذة الحالية: {current_time} ساعة\n\n"
            f"💡 أدخل النافذة الزمنية بالساعات (من 1 إلى 168):\n"
            f"• 1-6 ساعات = مراقبة قصيرة المدى\n"
            f"• 24 ساعة = مراقبة يومية (افتراضي)\n"
            f"• 168 ساعة = مراقبة أسبوعية"
        )
        
        buttons = [[Button.inline("❌ إلغاء", f"duplicate_settings_{task_id}")]]
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        # Add timestamp to force UI refresh
        import time
        timestamp = int(time.time()) % 100
        
        message_text = (
            f"🌍 فلتر اللغات - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"🗣️ عدد اللغات: {len(languages)}\n"
            f"⚙️ الوضع: {mode_text}\n\n"
            f"💡 هذا الفلتر يتحكم في الرسائل حسب لغة النص\n"
            f"⏰ آخر تحديث: {timestamp}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def show_language_management(self, event, task_id):
        """Show language management interface"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        # Get current language filters
        filter_settings = self.db.get_language_filters(task_id)
        languages = filter_settings.get('languages', [])
        mode = filter_settings.get('mode', 'allow')
        
        # Add timestamp to force UI refresh
        import time
        import random
        timestamp = int(time.time() * 1000) % 10000 + random.randint(1, 999)
        
        if not languages:
            message = (
                f"🌍 إدارة اللغات - المهمة #{task_id}\n\n"
                f"❌ لم يتم إضافة أي لغات بعد\n\n"
                f"💡 استخدم الأزرار أدناه لإضافة اللغات المطلوبة\n"
                f"⏰ آخر تحديث: {timestamp}"
            )
        else:
            # Build language list with status
            language_list = ""
            selected_count = 0
            for lang in languages:
                is_selected = lang['is_allowed']
                if is_selected:
                    selected_count += 1
                status_icon = "✅" if is_selected else "❌"
                language_list += f"{status_icon} {lang['language_name']} ({lang['language_code']})\n"
            
            mode_text = "حظر المحددة" if mode == 'block' else "السماح للمحددة فقط"
            
            message = (
                f"🌍 إدارة اللغات - المهمة #{task_id}\n\n"
                f"📊 الوضع: {mode_text}\n"
                f"🗂️ إجمالي اللغات: {len(languages)}\n"
                f"✅ المفعلة: {selected_count}\n"
                f"❌ المعطلة: {len(languages) - selected_count}\n\n"
                f"📋 قائمة اللغات:\n"
                f"{language_list}\n"
                f"⏰ آخر تحديث: {timestamp}"
            )
        
        # Create buttons
        buttons = []
        
        # Language selection buttons (max 5 per row for readability)
        if languages:
            lang_buttons = []
            for i, lang in enumerate(languages):
                status_icon = "✅" if lang['is_allowed'] else "❌"
                button_text = f"{status_icon} {lang['language_code'].upper()}"
                callback_data = f"toggle_lang_selection_{task_id}_{lang['language_code']}"
                lang_buttons.append(Button.inline(button_text, callback_data))
                
                # Add row every 5 buttons
                if (i + 1) % 5 == 0 or i == len(languages) - 1:
                    buttons.append(lang_buttons)
                    lang_buttons = []
        
        # Management buttons
        buttons.extend([
            [Button.inline("➕ إضافة لغة جديدة", f"add_language_{task_id}")],
            [Button.inline("🚀 إضافة سريعة", f"quick_add_languages_{task_id}")],
        ])
        
        if languages:
            buttons.append([
                Button.inline("🗑️ حذف جميع اللغات", f"clear_all_languages_{task_id}")
            ])
        
        buttons.append([
            Button.inline("🔙 رجوع لفلتر اللغات", f"language_filters_{task_id}")
        ])
        
        try:
            await self.edit_or_send_message(event, message, buttons=buttons)
        except Exception as refresh_error:
            if "Content of the message was not modified" in str(refresh_error):
                logger.debug("المحتوى لم يتغير، تجاهل الخطأ")
            else:
                logger.error(f"خطأ في تحديث واجهة إدارة اللغات: {refresh_error}")
                raise refresh_error

    async def show_quick_add_languages(self, event, task_id):
        """Show quick language addition interface"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        # Add timestamp to force UI refresh
        import time
        import random
        timestamp = int(time.time() * 1000) % 10000 + random.randint(1, 999)
        
        # Get current languages
        filter_settings = self.db.get_language_filters(task_id)
        existing_languages = [lang['language_code'] for lang in filter_settings.get('languages', [])]
        
        message = (
            f"🚀 إضافة سريعة للغات - المهمة #{task_id}\n\n"
            f"📋 اختر اللغات المطلوبة من القائمة السريعة:\n\n"
            f"⏰ آخر تحديث: {timestamp}"
        )
        
        # Common languages list
        common_languages = [
            ('ar', 'العربية', '🇸🇦'),
            ('en', 'English', '🇺🇸'),
            ('es', 'Español', '🇪🇸'),
            ('fr', 'Français', '🇫🇷'),
            ('de', 'Deutsch', '🇩🇪'),
            ('ru', 'Русский', '🇷🇺'),
            ('zh', '中文', '🇨🇳'),
            ('ja', '日本語', '🇯🇵'),
            ('ko', '한국어', '🇰🇷'),
            ('it', 'Italiano', '🇮🇹'),
            ('pt', 'Português', '🇵🇹'),
            ('hi', 'हिन्दी', '🇮🇳'),
            ('tr', 'Türkçe', '🇹🇷'),
            ('fa', 'فارسی', '🇮🇷'),
            ('ur', 'اردو', '🇵🇰')
        ]
        
        # Create buttons for languages
        buttons = []
        lang_buttons = []
        
        for i, (code, name, flag) in enumerate(common_languages):
            # Check if language already exists
            if code in existing_languages:
                button_text = f"✅ {flag} {name}"
                callback_data = f"quick_remove_lang_{task_id}_{code}_{name}"
            else:
                button_text = f"➕ {flag} {name}"
                callback_data = f"quick_add_lang_{task_id}_{code}_{name}"
            
            lang_buttons.append(Button.inline(button_text, callback_data))
            
            # Add row every 2 buttons for better readability
            if (i + 1) % 2 == 0 or i == len(common_languages) - 1:
                buttons.append(lang_buttons)
                lang_buttons = []
        
        # Add action buttons
        buttons.extend([
            [Button.inline("✨ إضافة لغة مخصصة", f"add_language_{task_id}")],
            [Button.inline("🔙 رجوع لإدارة اللغات", f"manage_languages_{task_id}")]
        ])
        
        try:
            await self.edit_or_send_message(event, message, buttons=buttons)
        except Exception as refresh_error:
            if "Content of the message was not modified" in str(refresh_error):
                logger.debug("المحتوى لم يتغير، تجاهل الخطأ")
            else:
                logger.error(f"خطأ في تحديث واجهة الإضافة السريعة للغات: {refresh_error}")
                raise refresh_error

    async def start_add_language(self, event, task_id):
        """Start adding custom language"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
        
        # Set conversation state for adding language
        self.db.set_conversation_state(user_id, 'waiting_language_filter', str(task_id))

        buttons = [
            [Button.inline("❌ إلغاء", f"manage_languages_{task_id}")]
        ]

        message_text = (
            f"➕ إضافة لغة جديدة - المهمة #{task_id}\n\n"
            f"📝 أرسل كود اللغة واسمها بالشكل التالي:\n\n"
            f"**أمثلة:**\n"
            f"• `en English`\n"
            f"• `ar العربية`\n"
            f"• `fr Français`\n"
            f"• `de Deutsch`\n\n"
            f"💡 **تنسيق الإدخال:**\n"
            f"`[كود اللغة] [اسم اللغة]`\n\n"
            f"⚠️ **ملاحظة**: كود اللغة يجب أن يكون من 2-3 أحرف"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def quick_add_language(self, event, task_id, language_code, language_name):
        """Quick add language from predefined list"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Add language with default allowed status
            success = self.db.add_language_filter(task_id, language_code, language_name, True)
            
            if success:
                await event.answer(f"✅ تم إضافة {language_name} ({language_code})")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the quick add languages display
                await self.show_quick_add_languages(event, task_id)
            else:
                await event.answer(f"❌ فشل في إضافة {language_name}")
                
        except Exception as e:
            logger.error(f"خطأ في الإضافة السريعة للغة: {e}")
            await event.answer("❌ حدث خطأ أثناء إضافة اللغة")

    async def quick_remove_language(self, event, task_id, language_code, language_name):
        """Quick remove language from predefined list"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Remove language filter
            success = self.db.remove_language_filter(task_id, language_code)
            
            if success:
                await event.answer(f"✅ تم حذف {language_name} ({language_code})")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the quick add languages display
                await self.show_quick_add_languages(event, task_id)
            else:
                await event.answer(f"❌ فشل في حذف {language_name}")
                
        except Exception as e:
            logger.error(f"خطأ في حذف اللغة السريعة: {e}")
            await event.answer("❌ حدث خطأ أثناء حذف اللغة")

    async def toggle_language_selection(self, event, task_id, language_code):
        """Toggle language selection status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        try:
            # Toggle language filter status
            success = self.db.toggle_language_filter(task_id, language_code)
            
            if success:
                await event.answer(f"✅ تم تحديث فلتر اللغة {language_code}")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the language management display
                await self.show_language_management(event, task_id)
            else:
                await event.answer(f"❌ فشل في تحديث فلتر اللغة {language_code}")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل اللغة: {e}")
            await event.answer("❌ حدث خطأ أثناء تحديث اللغة")

    async def clear_all_languages(self, event, task_id):
        """Clear all languages for a task"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get current languages count
            filter_settings = self.db.get_language_filters(task_id)
            languages_count = len(filter_settings.get('languages', []))
            
            if languages_count == 0:
                await event.answer("❌ لا توجد لغات لحذفها")
                return
                
            # Clear all languages
            success = self.db.clear_language_filters(task_id)
            
            if success:
                await event.answer(f"✅ تم حذف {languages_count} لغة")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the language management display
                await self.show_language_management(event, task_id)
            else:
                await event.answer("❌ فشل في حذف اللغات")
                
        except Exception as e:
            logger.error(f"خطأ في حذف جميع اللغات: {e}")
            await event.answer("❌ حدث خطأ أثناء حذف اللغات")

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
        
        message_text = (
            f"👥 فلتر المشرفين - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"👤 عدد المشرفين: {len(admins)}\n\n"
            f"💡 هذا الفلتر يتحكم في الرسائل حسب صلاحيات المرسل"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def show_duplicate_filter(self, event, task_id):
        """Show duplicate filter settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings from advanced filters
        advanced_settings = self.db.get_advanced_filters_settings(task_id)
        is_enabled = advanced_settings.get('duplicate_filter_enabled', False)
        
        # Get duplicate specific settings
        settings = self.db.get_duplicate_settings(task_id)
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
        
        message_text = (
            f"🔄 فلتر التكرار - المهمة #{task_id}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📏 نسبة التشابه: {threshold}%\n"
            f"⏱️ النافذة الزمنية: {time_window} ساعة\n"
            f"📝 فحص النص: {'✅' if check_text else '❌'}\n"
            f"🎬 فحص الوسائط: {'✅' if check_media else '❌'}\n\n"
            f"💡 هذا الفلتر يمنع توجيه الرسائل المتكررة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def _get_duplicate_settings_buttons(self, task_id):
        """Get buttons for duplicate settings menu"""
        # Get current settings
        settings = self.db.get_duplicate_settings(task_id)
        threshold = settings.get('similarity_threshold', 80)
        time_window = settings.get('time_window_hours', 24)
        check_text = settings.get('check_text', True)
        check_media = settings.get('check_media', True)
        
        buttons = [
            [Button.inline(f"📏 نسبة التشابه ({threshold}%)", f"set_duplicate_threshold_{task_id}")],
            [Button.inline(f"⏱️ النافذة الزمنية ({time_window}ساعة)", f"set_duplicate_time_{task_id}")],
            [Button.inline(f"📝 فحص النص {'✅' if check_text else '❌'}", f"toggle_duplicate_text_{task_id}")],
            [Button.inline(f"🎬 فحص الوسائط {'✅' if check_media else '❌'}", f"toggle_duplicate_media_{task_id}")],
            [Button.inline("🔙 رجوع لفلتر التكرار", f"duplicate_filter_{task_id}")]
        ]
        
        return buttons

    async def show_duplicate_settings(self, event, task_id):
        """Show duplicate filter detailed settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings
        settings = self.db.get_duplicate_settings(task_id)
        threshold = settings.get('similarity_threshold', 80)
        time_window = settings.get('time_window_hours', 24)
        check_text = settings.get('check_text', True)
        check_media = settings.get('check_media', True)
        
        buttons = [
            [Button.inline(f"📏 نسبة التشابه ({threshold}%)", f"set_duplicate_threshold_{task_id}")],
            [Button.inline(f"⏱️ النافذة الزمنية ({time_window}ساعة)", f"set_duplicate_time_{task_id}")],
            [Button.inline(f"📝 فحص النص {'✅' if check_text else '❌'}", f"toggle_duplicate_text_{task_id}")],
            [Button.inline(f"🎬 فحص الوسائط {'✅' if check_media else '❌'}", f"toggle_duplicate_media_{task_id}")],
            [Button.inline("🔙 رجوع لفلتر التكرار", f"duplicate_filter_{task_id}")]
        ]
        
        # Add timestamp to force UI refresh
        import time
        timestamp = int(time.time()) % 100
        
        message_text = (
            f"⚙️ إعدادات فلتر التكرار - المهمة #{task_id}\n\n"
            f"📏 نسبة التشابه: {threshold}%\n"
            f"⏱️ النافذة الزمنية: {time_window} ساعة\n"
            f"📝 فحص النص: {'مفعل' if check_text else 'معطل'}\n"
            f"🎬 فحص الوسائط: {'مفعل' if check_media else 'معطل'}\n\n"
            f"💡 اضبط هذه الإعدادات لتحكم أدق في كشف التكرار\n"
            f"⏰ آخر تحديث: {timestamp}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def toggle_inline_button_block_mode(self, event, task_id):
        """Toggle inline button filter mode between block message and remove buttons"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get current setting and toggle it
            current_setting = self.db.get_inline_button_filter_setting(task_id)
            new_setting = not current_setting  # Toggle: False=remove buttons, True=block message
            
            success = self.db.set_inline_button_filter(task_id, new_setting)
            
            if success:
                mode_text = "حظر الرسائل" if new_setting else "حذف الأزرار"
                await event.answer(f"✅ تم تغيير الوضع إلى: {mode_text}")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the display
                await self.show_inline_button_filter(event, task_id)
            else:
                await event.answer("❌ فشل في تغيير الوضع")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل وضع فلتر الأزرار الإنلاين: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def show_main_menu(self, event):
        """Show main menu"""
        user_id = event.sender_id
        
        # Check UserBot status for status indicator
        try:
            from userbot_service.userbot import userbot_instance
            is_userbot_running = user_id in userbot_instance.clients
            userbot_status = "🟢 نشط" if is_userbot_running else "🟡 مطلوب فحص"
        except:
            userbot_status = "🔍 غير معروف"
        
        buttons = [
            [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
            [Button.inline("🔍 فحص حالة UserBot", b"check_userbot")],
            [Button.inline("⚙️ الإعدادات", b"settings")],
            [Button.inline("ℹ️ حول البوت", b"about")]
        ]

        message_text = (
            f"🏠 **القائمة الرئيسية**\n\n"
            f"🤖 حالة النظام:\n"
            f"• بوت التحكم: 🟢 نشط\n"
            f"• UserBot: {userbot_status}\n\n"
            f"اختر ما تريد فعله:"
        )

        await self.force_new_message(event, message_text, buttons=buttons)

    async def show_tasks_menu(self, event):
        """Show tasks management menu"""
        user_id = event.sender_id
        tasks = self.db.get_user_tasks(user_id)

        buttons = [
            [Button.inline("➕ إنشاء مهمة جديدة", b"create_task")],
            [Button.inline("📋 عرض المهام", b"list_tasks")],
            [Button.inline("📺 إدارة القنوات", b"manage_channels")],
            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        ]

        tasks_count = len(tasks)
        active_count = len([t for t in tasks if t['is_active']])

        message_text = (
            f"📝 إدارة مهام التوجيه\n\n"
            f"📊 الإحصائيات:\n"
            f"• إجمالي المهام: {tasks_count}\n"
            f"• المهام النشطة: {active_count}\n"
            f"• المهام المتوقفة: {tasks_count - active_count}\n\n"
            f"اختر إجراء:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_create_task(self, event):
        """Start creating new task"""
        user_id = event.sender_id

        # Check if user is authenticated
        if not self.db.is_user_authenticated(user_id):
            await self.edit_or_send_message(event, "❌ يجب تسجيل الدخول أولاً لإنشاء المهام")
            return

        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_task_name', json.dumps({}))

        buttons = [
            [Button.inline("❌ إلغاء", b"manage_tasks")]
        ]

        message_text = (
            "➕ إنشاء مهمة توجيه جديدة\n\n"
            "🏷️ **الخطوة 1: تحديد اسم المهمة**\n\n"
            "أدخل اسماً لهذه المهمة (أو اضغط تخطي لاستخدام اسم افتراضي):\n\n"
            "• اسم المهمة: (مثال: مهمة متابعة الأخبار)"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def list_tasks(self, event):
        """List user tasks"""
        user_id = event.sender_id

        # Check if user is authenticated
        if not self.db.is_user_authenticated(user_id):
            await self.edit_or_send_message(event, "❌ يجب تسجيل الدخول أولاً لعرض المهام")
            return

        tasks = self.db.get_user_tasks(user_id)

        if not tasks:
            buttons = [
                [Button.inline("➕ إنشاء مهمة جديدة", b"create_task")],
                [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
            ]

            message_text = (
                "📋 قائمة المهام\n\n"
                "❌ لا توجد مهام حالياً\n\n"
                "أنشئ مهمتك الأولى للبدء!"
            )
            
            await self.force_new_message(event, message_text, buttons=buttons)
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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        message_text = (
            f"⚙️ تفاصيل المهمة #{task['id']}\n\n"
            f"🏷️ اسم المهمة: {task_name}\n"
            f"📊 الحالة: {status}\n"
            f"📋 وضع التوجيه: {forward_mode_text}\n\n"
            f"{sources_text}"
            f"{targets_text}\n"
            f"📅 تاريخ الإنشاء: {task['created_at'][:16]}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        logger.debug(f"Processing state: {state}, data_str type: {type(data_str)}, data_str: {data_str}")
        try:
            if isinstance(data_str, dict):
                data = data_str
            elif isinstance(data_str, str) and data_str:
                data = json.loads(data_str)
            else:
                data = {}
            logger.debug(f"Parsed data: {data}")
        except (json.JSONDecodeError, TypeError) as e:
            logger.error(f"خطأ في تحليل البيانات: {e}, البيانات: {data_str}")
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
            elif state == 'editing_recurring_interval_init':
                # First-time interval entry after forward
                try:
                    interval = int(message_text)
                    if interval < 60 or interval > 60*60*24*7:
                        await self.edit_or_send_message(event, "❌ يجب أن تكون الفترة بين 60 ثانية و 7 أيام")
                        return
                    payload = data or {}
                    task_id = int(payload.get('task_id'))
                    source_chat_id = payload.get('source_chat_id')
                    source_message_id = int(payload.get('source_message_id'))
                    new_id = self.db.create_recurring_post(
                        task_id=task_id,
                        source_chat_id=source_chat_id,
                        source_message_id=source_message_id,
                        interval_seconds=interval,
                        delete_previous=False,
                        preserve_original_buttons=True
                    )
                    self.db.clear_conversation_state(user_id)
                    if new_id:
                        await self.edit_or_send_message(event, f"✅ تم إضافة منشور متكرر (#{new_id})\nالفترة: {interval} ثانية")
                        await self.show_recurring_posts(event, task_id)
                    else:
                        await self.edit_or_send_message(event, "❌ فشل في إضافة المنشور المتكرر")
                except ValueError:
                    await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
            elif state == 'editing_recurring_interval':
                try:
                    recurring_id = int(data_str)
                except Exception:
                    recurring_id = None
                if not recurring_id:
                    await self.edit_or_send_message(event, "❌ بيانات غير صالحة")
                    return
                try:
                    interval = int(message_text)
                    if interval < 60 or interval > 60*60*24*7:
                        await self.edit_or_send_message(event, "❌ يجب أن تكون الفترة بين 60 ثانية و 7 أيام")
                        return
                    ok = self.db.update_recurring_post(recurring_id, interval_seconds=interval)
                    self.db.clear_conversation_state(user_id)
                    if ok:
                        post = self.db.get_recurring_post(recurring_id)
                        await self.edit_or_send_message(event, f"✅ تم تحديث الفترة إلى {interval} ثانية")
                        if post:
                            await self.start_edit_recurring_post(event, recurring_id)
                    else:
                        await self.edit_or_send_message(event, "❌ فشل في التحديث")
                except ValueError:
                    await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
        except Exception as e:
            logger.error(f"خطأ في معالجة رسالة المحادثة: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ، حاول مرة أخرى")
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
            message_text = (
                "❌ خطأ في البيانات، حاول مرة أخرى\n\n"
                f"🔍 تفاصيل المشكلة:\n"
                f"• معرف المهمة: {task_id}\n"
                f"• الإجراء: {action}\n"
                f"• الحالة: {state}"
            )
            await self.edit_or_send_message(event, message_text)
            self.db.clear_conversation_state(user_id)
            return

        # Debug: log received data
        logger.info(f"🔍 إضافة مصدر/هدف: task_id={task_id}, action={action}, input='{chat_input}'")

        # Parse chat input
        chat_ids, chat_names = self.parse_chat_input(chat_input)

        if not chat_ids:
            message_text = (
                "❌ تنسيق معرف المجموعة/القناة غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890\n\n"
                "لعدة معرفات، افصل بينها بفاصلة: @channel1, @channel2"
            )
            await self.edit_or_send_message(event, message_text)
            return

        # Add each chat
        added_count = 0
        for i, chat_id in enumerate(chat_ids):
            chat_name = chat_names[i] if chat_names and i < len(chat_names) else None

            # Try to resolve a better display name via UserBot (channel/group title or user's full name)
            try:
                from userbot_service.userbot import userbot_instance
                if user_id in userbot_instance.clients:
                    client = userbot_instance.clients[user_id]

                    # Build lookup identifier for Telethon
                    lookup = chat_id
                    chat_id_str = str(chat_id)
                    if isinstance(chat_id, str):
                        if chat_id_str.startswith('-') and chat_id_str[1:].isdigit():
                            lookup = int(chat_id_str)
                        elif chat_id_str.isdigit():
                            lookup = int(chat_id_str)
                        else:
                            # keep usernames like @name as-is
                            lookup = chat_id_str
                    else:
                        # numeric provided
                        lookup = int(chat_id)

                    try:
                        chat = await client.get_entity(lookup)
                        resolved_name = getattr(chat, 'title', None)
                        if not resolved_name:
                            first_name = getattr(chat, 'first_name', None)
                            last_name = getattr(chat, 'last_name', None)
                            if first_name or last_name:
                                resolved_name = ' '.join([n for n in [first_name, last_name] if n])
                        if not resolved_name:
                            resolved_name = getattr(chat, 'username', None)

                        # Use resolved name if it's better than current
                        if resolved_name and (not chat_name or str(chat_name).strip() in [None, '', chat_id_str.lstrip('@')]):
                            chat_name = resolved_name
                    except Exception:
                        pass
            except Exception:
                pass

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

            await self.edit_or_send_message(event, f"✅ تم إضافة {added_count} {plural} بنجاح!")

            # Return to appropriate management menu
            if action == 'add_source':
                await self.manage_task_sources(event, task_id)
            else:
                await self.manage_task_targets(event, task_id)
        else:
            await self.edit_or_send_message(event, "❌ فشل في إضافة المدخلات")

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

        # Offer selection from added channels
        buttons = [[Button.inline("🧭 اختيار من القنوات المضافة", b"choose_sources")],
                   [Button.inline("❌ إلغاء", b"manage_tasks")]]
        message_text = (
            f"✅ اسم المهمة: {task_name}\n\n"
            f"📥 **الخطوة 2: تحديد المصادر**\n\n"
            f"يمكنك:\n"
            f"• الضغط على 'اختيار من القنوات المضافة' لاختيار عدة قنوات\n"
            f"• أو إرسال المعرفات/الروابط يدوياً كما تحب"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_source_chat(self, event, chat_input):
        """Handle source chat input using database conversation state"""
        user_id = event.sender_id

        # Parse chat input
        source_chat_ids, source_chat_names = self.parse_chat_input(chat_input)

        if not source_chat_ids:
            message_text = (
                "❌ تنسيق معرفات المجموعات/القنوات غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890\n\n"
                "لعدة مصادر، افصل بينها بفاصلة: @channel1, @channel2"
            )
            await self.edit_or_send_message(event, message_text)
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
            [Button.inline("🧭 اختيار الأهداف من القنوات", b"choose_targets")],
            [Button.inline("❌ إلغاء", b"manage_tasks")]
        ]

        message_text = (
            f"✅ تم تحديد المصادر: {', '.join([str(name) for name in source_chat_names if name])}\n\n"
            f"📤 **الخطوة 3: تحديد الوجهة**\n\n"
            f"أرسل معرف أو رابط المجموعة/القناة المراد توجيه الرسائل إليها:\n\n"
            f"أمثلة:\n"
            f"• @targetchannel\n"
            f"• https://t.me/targetchannel\n"
            f"• -1001234567890\n\n"
            f"⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات إرسال الرسائل"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_target_chat(self, event, chat_input):
        """Handle target chat input using database conversation state"""
        user_id = event.sender_id

        # Parse target chat
        target_chat_ids, target_chat_names = self.parse_chat_input(chat_input)

        if not target_chat_ids:
            message_text = (
                "❌ تنسيق معرفات المجموعات/القنوات غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890\n\n"
                "لعدة أهداف، افصل بينها بفاصلة: @channel1, @channel2"
            )
            await self.edit_or_send_message(event, message_text)
            return

        # Get source chat data from database
        state_data = self.db.get_conversation_state(user_id)
        if not state_data:
            await self.edit_or_send_message(event, "❌ حدث خطأ، يرجى البدء من جديد")
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
                await self.edit_or_send_message(event, "❌ حدث خطأ في البيانات، يرجى البدء من جديد")
                return
        else:
            await self.edit_or_send_message(event, "❌ لم يتم تحديد المصدر، يرجى البدء من جديد")
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

        message_text = (
            f"🎉 تم إنشاء المهمة بنجاح!\n\n"
            f"🆔 رقم المهمة: #{task_id}\n"
            f"🏷️ اسم المهمة: {task_name}\n"
            f"📥 المصادر: {', '.join([str(name) for name in (source_chat_names or source_chat_ids)])}\n"
            f"📤 الوجهة: {target_chat_name}\n"
            f"🟢 الحالة: نشطة\n\n"
            f"✅ سيتم توجيه جميع الرسائل الجديدة تلقائياً"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_choose_sources(self, event):
        user_id = event.sender_id
        # read user channels from channels management DB
        channels = ChannelsDatabase(self.db).get_user_channels(user_id)
        if not channels:
            await event.answer("❌ لا توجد قنوات مضافة")
            return
        # store temporary selection in state
        sel = {'mode': 'source', 'selected': []}
        self.set_user_state(user_id, 'choosing_channels', sel)
        await self.show_channel_chooser(event, channels, 'source')

    async def start_choose_targets(self, event):
        user_id = event.sender_id
        channels = ChannelsDatabase(self.db).get_user_channels(user_id)
        if not channels:
            await event.answer("❌ لا توجد قنوات مضافة")
            return
        sel = {'mode': 'target', 'selected': []}
        self.set_user_state(user_id, 'choosing_channels', sel)
        await self.show_channel_chooser(event, channels, 'target')

    async def start_choose_sources_for_task(self, event, task_id):
        user_id = event.sender_id
        channels = ChannelsDatabase(self.db).get_user_channels(user_id)
        if not channels:
            await event.answer("❌ لا توجد قنوات مضافة")
            return
        sel = {'mode': 'source_for_task', 'task_id': task_id, 'selected': []}
        self.set_user_state(user_id, 'choosing_channels', sel)
        await self.show_channel_chooser(event, channels, 'source')

    async def start_choose_targets_for_task(self, event, task_id):
        user_id = event.sender_id
        channels = ChannelsDatabase(self.db).get_user_channels(user_id)
        if not channels:
            await event.answer("❌ لا توجد قنوات مضافة")
            return
        sel = {'mode': 'target_for_task', 'task_id': task_id, 'selected': []}
        self.set_user_state(user_id, 'choosing_channels', sel)
        await self.show_channel_chooser(event, channels, 'target')

    async def show_channel_chooser(self, event, channels, selection_type: str):
        user_id = event.sender_id
        # Read current selection to reflect in UI
        selected_now = set((self.get_user_data(user_id) or {}).get('selected') or [])

        rows = []
        for ch in channels[:30]:
            chat_id = str(ch.get('chat_id'))
            name = ch.get('chat_name') or chat_id
            is_admin = ch.get('is_admin', False)
            role_icon = "👑" if is_admin else "👤"
            sel_icon = "✅" if chat_id in selected_now else "☐"
            label = f"{sel_icon} {role_icon} {name}"
            rows.append([Button.inline(label, f"toggle_sel_{selection_type}_" + chat_id)])

        # Footer controls
        rows.append([Button.inline("✅ إنهاء التحديد", f"finish_sel_{selection_type}")])

        # Include a small summary so edits always differ when selection changes
        count = len(selected_now)
        title = "المصادر" if selection_type == 'source' else "الأهداف"
        text = f"اختر {title}:\nالمختارة: {count}"
        await self.edit_or_send_message(event, text, buttons=rows)

    async def toggle_channel_selection(self, event, selection_type: str, chat_id: str):
        user_id = event.sender_id
        state_name = self.get_user_state(user_id)
        if state_name != 'choosing_channels':
            await event.answer("❌ لا توجد عملية اختيار نشطة")
            return
        data = self.get_user_data(user_id) or {}
        selected = set(data.get('selected') or [])
        if chat_id in selected:
            selected.remove(chat_id)
        else:
            selected.add(chat_id)
        data['selected'] = list(selected)
        self.set_user_state(user_id, 'choosing_channels', data)
        # Refresh chooser and force new message if edit would be identical
        channels = ChannelsDatabase(self.db).get_user_channels(user_id)
        await self.show_channel_chooser(event, channels, selection_type)

    async def finish_channel_selection(self, event, selection_type: str):
        user_id = event.sender_id
        state_name = self.get_user_state(user_id)
        if state_name != 'choosing_channels':
            await event.answer("❌ لا توجد عملية اختيار نشطة")
            return
        data = self.get_user_data(user_id) or {}
        selected_ids = data.get('selected') or []
        if not selected_ids:
            await event.answer("❌ لم يتم اختيار أي قناة")
            return

        # If during task creation
        conv_state = self.db.get_conversation_state(user_id)
        if conv_state:
            st, payload = conv_state
            try:
                payload_json = json.loads(payload) if payload else {}
            except Exception:
                payload_json = {}

            if st == 'waiting_source_chat' and selection_type == 'source':
                payload_json['source_chat_ids'] = selected_ids
                payload_json['source_chat_names'] = selected_ids
                self.db.set_conversation_state(user_id, 'waiting_target_chat', json.dumps(payload_json))
                # Show target selection options immediately
                buttons = [
                    [Button.inline("🧭 اختيار الأهداف من القنوات", b"choose_targets")],
                    [Button.inline("❌ إلغاء", b"manage_tasks")]
                ]
                await self.edit_or_send_message(event, "✅ تم تحديد المصادر. الآن اختر/أرسل الأهداف.", buttons=buttons, force_new=True)
                return
            if st == 'waiting_target_chat' and selection_type == 'target':
                source_ids = payload_json.get('source_chat_ids') or []
                source_names = payload_json.get('source_chat_names') or source_ids
                target_ids = selected_ids
                target_names = selected_ids
                task_name = payload_json.get('task_name', 'مهمة توجيه')
                task_id = self.db.create_task_with_multiple_sources_targets(
                    user_id, task_name, source_ids, source_names, target_ids, target_names
                )
                self.clear_user_state(user_id)
                self.db.clear_conversation_state(user_id)
                # Jump to task management panel
                await self.show_task_details(event, task_id)
                return

        # If managing an existing task
        mode = data.get('mode')
        task_id = data.get('task_id')
        if mode == 'source_for_task' and task_id:
            for cid in selected_ids:
                self.db.add_task_source(task_id, cid, cid)
            await self.manage_task_sources(event, task_id)
            return
        if mode == 'target_for_task' and task_id:
            for cid in selected_ids:
                self.db.add_task_target(task_id, cid, cid)
            await self.manage_task_targets(event, task_id)
            return

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

        message_text = (
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
            f"🖼️ **صورة العلامة**: {'محددة' if watermark_settings.get('watermark_image_path') else 'غير محددة'}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        message_text = (
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
            f"🔻 تقليل القيمة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        message_text = (
            f"📍 اختيار موقع العلامة المائية - المهمة #{task_id}\n\n"
            f"الموقع الحالي: {position_map.get(current_position, current_position)}\n\n"
            f"اختر الموقع المطلوب:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        message_text = (
            f"🎭 نوع العلامة المائية - المهمة #{task_id}\n\n"
            f"اختر نوع العلامة المائية:\n\n"
            f"📝 **نص**: إضافة نص مخصص\n"
            f"🖼️ **صورة**: استخدام صورة PNG شفافة\n\n"
            f"النوع الحالي: {'📝 نص' if current_type == 'text' else '🖼️ صورة'}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        message_text = (
            f"📱 أنواع الوسائط للعلامة المائية - المهمة #{task_id}\n\n"
            f"اختر أنواع الوسائط التي تريد تطبيق العلامة المائية عليها:\n\n"
            f"📷 **الصور**: JPG, PNG, WebP\n"
            f"🎥 **الفيديوهات**: MP4, AVI, MOV\n"
            f"📄 **المستندات**: ملفات الصور المرسلة كمستندات\n\n"
            f"✅ = مفعل  |  ❌ = معطل"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        message_text = (
            f"📝 إدخال نص العلامة المائية - المهمة #{task_id}\n\n"
            f"أرسل النص الذي تريد استخدامه كعلامة مائية:\n\n"
            f"💡 **ملاحظات**:\n"
            f"• يمكنك استخدام النصوص العربية والإنجليزية\n"
            f"• تجنب النصوص الطويلة جداً\n"
            f"• يمكنك تعديل اللون والحجم من إعدادات المظهر\n\n"
            f"أرسل /cancel للإلغاء"
        )
        
        buttons = [[Button.inline("❌ إلغاء", f"watermark_type_{task_id}")]]
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_watermark_image_input(self, event, task_id):
        """Start watermark image input process"""
        self.set_user_state(event.sender_id, f'watermark_image_input_{task_id}', {'task_id': task_id})
        message_text = (
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
            f"أرسل /cancel للإلغاء"
        )
        
        buttons = [[Button.inline("❌ إلغاء", f"watermark_type_{task_id}")]]
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_watermark_text_input(self, event, task_id):
        """Handle watermark text input"""
        text = event.message.text.strip()
        
        if not text:
            await self.edit_or_send_message(event, "❌ يرجى إرسال نص صالح للعلامة المائية.")
            return
        
        # Update watermark settings with the text
        self.db.update_watermark_settings(task_id, watermark_text=text)
        
        # Clear user state
        self.clear_user_state(event.sender_id)
        
        message_text = (
            f"✅ تم حفظ نص العلامة المائية بنجاح!\n\n"
            f"📝 **النص المحفوظ**: {text}\n\n"
            f"يمكنك الآن تعديل إعدادات المظهر من قائمة العلامة المائية."
        )
        
        buttons = [
            [Button.inline("🎨 إعدادات المظهر", f"watermark_appearance_{task_id}")],
            [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]
        ]
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_watermark_image_input(self, event, task_id):
        """Handle watermark image input (supports both photos and documents)"""
        media = event.message.media
        document = event.message.document
        photo = event.message.photo
        
        # Check if it's a photo or a document (file)
        if not media and not document and not photo:
            await self.edit_or_send_message(event, "❌ يرجى إرسال صورة أو ملف PNG للعلامة المائية.")
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
                await self.edit_or_send_message(event, 
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
                await self.edit_or_send_message(event, "❌ حجم الملف كبير جداً! الحد الأقصى 10 ميجابايت.")
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
                await self.edit_or_send_message(event, "❌ فشل في تحميل الصورة.")
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
                await self.edit_or_send_message(event,
                    "❌ الملف المُرسل ليس صورة صالحة!\n\n"
                    "يرجى إرسال صورة بصيغة PNG، JPG، أو أي صيغة صورة مدعومة."
                )
                return
            
            # Update watermark settings with the image path
            self.db.update_watermark_settings(task_id, watermark_image_path=file_path)
            
            # Clear user state
            self.clear_user_state(event.sender_id)
            
            file_type_display = "📄 ملف PNG" if file_path.lower().endswith('.png') else "📷 صورة"
            
            message_text = (
                f"✅ تم رفع صورة العلامة المائية بنجاح!\n\n"
                f"📁 **اسم الملف**: {os.path.basename(file_path)}\n"
                f"🎭 **نوع الملف**: {file_type_display}\n"
                f"📏 **الحجم**: {width}x{height} بكسل\n"
                f"📋 **الصيغة**: {format_name}\n\n"
                f"💡 **ملاحظة**: صيغة PNG توفر أفضل جودة مع دعم الشفافية\n\n"
                f"يمكنك الآن تعديل إعدادات المظهر من قائمة العلامة المائية."
            )
            
            buttons = [
                [Button.inline("🎨 إعدادات المظهر", f"watermark_appearance_{task_id}")],
                [Button.inline("🔙 عودة للعلامة المائية", f"watermark_settings_{task_id}")]
            ]
            
            await self.force_new_message(event, message_text, buttons=buttons)
            
        except Exception as e:
            logger.error(f"خطأ في معالجة صورة العلامة المائية: {e}")
            await self.edit_or_send_message(event,
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

        message_text = (
            "📱 تسجيل الدخول\n\n"
            "أرسل رقم هاتفك مع رمز البلد:\n"
            "مثال: +966501234567\n\n"
            "⚠️ تأكد من صحة الرقم"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_session_login(self, event):
        """Start session-based login process"""
        user_id = event.sender_id

        # Save conversation state in database
        self.db.set_conversation_state(user_id, 'waiting_session', json.dumps({}))

        buttons = [
            [Button.inline("❌ إلغاء", b"cancel_auth")]
        ]

        message_text = (
            "🔑 تسجيل الدخول بجلسة جاهزة\n\n"
            "📋 **كيفية الحصول على الجلسة**:\n"
            "• استخدم @SessionStringBot\n"
            "• أو استخدم @StringSessionBot\n"
            "• أو استخدم @UseTGXBot\n\n"
            "📝 **أرسل الجلسة الآن**:\n"
            "• انسخ الجلسة من البوت\n"
            "• أرسلها هنا\n"
            "• مثال: 1BQANOTEz...\n\n"
            "⚠️ **تحذير**:\n"
            "• لا تشارك الجلسة مع أحد\n"
            "• احتفظ بها آمنة\n"
            "• الجلسة تمنح الوصول الكامل لحسابك"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_login(self, event): # New function for login button
        """Start login process"""
        user_id = event.sender_id
        session_data = self.db.get_user_session(user_id)

        if session_data and len(session_data) >= 2 and session_data[2]: # Check for session string
            message_text = (
                "🔄 أنت مسجل دخولك بالفعل.\n"
                "هل تريد تسجيل الخروج وإعادة تسجيل الدخول؟"
            )
            buttons = [
                [Button.inline("✅ نعم، إعادة تسجيل الدخول", b"auth_phone")],
                [Button.inline("❌ لا، العودة للإعدادات", b"settings")]
            ]
            await self.force_new_message(event, message_text, buttons=buttons)
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
        message_text = (
            "🔄 تم تسجيل الخروج من الجلسة السابقة\n\n"
            "📱 سيتم بدء عملية تسجيل دخول جديدة..."
        )
        await self.edit_or_send_message(event, message_text)

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

        # Ensure legacy data is parsed into a dictionary
        try:
            if isinstance(data, dict):
                parsed_data = data
            elif isinstance(data, str) and data:
                parsed_data = json.loads(data)
            else:
                parsed_data = {}
                logger.warning(f"بيانات فارغة لحالة المصادقة للمستخدم {user_id} في الحالة {state}")
        except Exception as e:
            logger.error(f"خطأ في تحليل بيانات حالة المصادقة للمستخدم {user_id}: {e}")
            logger.error(f"البيانات الأصلية: {data}")
            parsed_data = {}

        try:
            if state == 'waiting_phone':
                await self.handle_phone_input(event, message_text)
            elif state == 'waiting_code':
                await self.handle_code_input(event, message_text, parsed_data)
            elif state == 'waiting_password':
                await self.handle_password_input(event, message_text, parsed_data)
            elif state == 'waiting_session':
                await self.handle_session_input(event, message_text)
        except Exception as e:
            logger.error(f"خطأ في التسجيل للمستخدم {user_id}: {e}")
            message_text = (
                "❌ حدث خطأ أثناء التسجيل. حاول مرة أخرى.\n"
                "اضغط /start للبدء من جديد."
            )
            await self.edit_or_send_message(event, message_text)
            self.db.clear_conversation_state(user_id)

    async def handle_phone_input(self, event, phone: str):
        """Handle phone number input"""
        user_id = event.sender_id

        # Validate phone number format
        if not phone.startswith('+') or len(phone) < 10:
            buttons = [
                [Button.inline("❌ إلغاء", b"cancel_auth")]
            ]

            message_text = (
                "❌ تنسيق رقم الهاتف غير صحيح\n\n"
                "📞 يجب أن يبدأ الرقم بـ + ويكون بالتنسيق الدولي\n"
                "مثال: +966501234567\n\n"
                "أرسل رقم الهاتف مرة أخرى:"
            )
            await self.force_new_message(event, message_text, buttons=buttons)
            return

        # Create temporary Telegram client for authentication
        temp_client = None
        try:
            # Create unique session for this authentication attempt in persistent sessions directory
            data_dir = os.getenv('DATA_DIR', '/app/data')
            sessions_dir = os.getenv('SESSIONS_DIR', os.path.join(data_dir, 'sessions'))
            try:
                os.makedirs(sessions_dir, exist_ok=True)
            except Exception:
                pass
            session_name = f'auth_{user_id}_{int(datetime.now().timestamp())}'
            session_path = os.path.join(sessions_dir, session_name)
            temp_client = TelegramClient(session_path, int(API_ID), API_HASH)

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
                'session_name': session_path
            }
            auth_data_json = json.dumps(auth_data)
            logger.info(f"حفظ بيانات المصادقة للمستخدم {user_id}: {list(auth_data.keys())}")
            self.db.set_conversation_state(user_id, 'waiting_code', auth_data_json)

            buttons = [
                [Button.inline("❌ إلغاء", b"cancel_auth")]
            ]

            message_text = (
                f"✅ تم إرسال رمز التحقق إلى {phone}\n\n"
                f"🔢 أرسل الرمز المكون من 5 أرقام:\n"
                f"• يمكن إضافة حروف لتجنب حظر تليجرام: aa12345\n"
                f"• أو إرسال الأرقام مباشرة: 12345\n\n"
                f"⏰ انتظر بضع ثواني حتى يصل الرمز"
            )
            await self.force_new_message(event, message_text, buttons=buttons)

        except asyncio.TimeoutError:
            logger.error("مهلة زمنية في إرسال الرمز")
            message_text = (
                "❌ مهلة زمنية في الاتصال\n\n"
                "🌐 تأكد من اتصالك بالإنترنت وحاول مرة أخرى"
            )
            await self.edit_or_send_message(event, message_text)
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

                    message_text = (
                        "⏰ تم طلب رموز كثيرة من تليجرام\n\n"
                        f"🚫 يجب الانتظار: {time_str}\n\n"
                        f"💡 نصائح لتجنب هذه المشكلة:\n"
                        f"• لا تطلب رمز جديد إلا بعد انتهاء الرمز السابق\n"
                        f"• استخدم رقم هاتف صحيح من المرة الأولى\n"
                        f"• انتظر وصول الرمز قبل طلب آخر\n\n"
                        f"حاول مرة أخرى بعد انتهاء فترة الانتظار"
                    )
                    await self.edit_or_send_message(event, message_text)
                except:
                    message_text = (
                        "⏰ تم طلب رموز كثيرة من تليجرام\n\n"
                        "يجب الانتظار قبل طلب رمز جديد\n"
                        "حاول مرة أخرى بعد فترة"
                    )
                    await self.edit_or_send_message(event, message_text)
            elif "AuthRestartError" in error_message or "Restart the authorization" in error_message:
                message_text = (
                    "🔄 خطأ في الاتصال مع تليجرام\n\n"
                    "حاول تسجيل الدخول مرة أخرى\n"
                    "اضغط /start للبدء من جديد"
                )
                await self.edit_or_send_message(event, message_text)
                self.db.clear_conversation_state(user_id)
            else:
                message_text = (
                    "❌ حدث خطأ في إرسال رمز التحقق\n\n"
                    "🔍 تحقق من:\n"
                    "• رقم الهاتف صحيح ومُفعل\n"
                    "• لديك اتصال إنترنت جيد\n"
                    "• لم تطلب رموز كثيرة مؤخراً\n\n"
                    "حاول مرة أخرى أو اضغط /start"
                )
                await self.edit_or_send_message(event, message_text)
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
            message_text = (
                "❌ تنسيق الرمز غير صحيح\n\n"
                "🔢 أرسل الرمز المكون من 5 أرقام\n"
                "يمكن إضافة حروف لتجنب الحظر مثل: aa12345\n"
                "أو إرسال الأرقام مباشرة: 12345"
            )
            await self.edit_or_send_message(event, message_text)
            return

        # Use the extracted code
        code = extracted_code

        try:
            # data is already a dict from handle_auth_message
            auth_data = data
            
            # Validate that required keys exist
            if not isinstance(auth_data, dict):
                logger.error(f"auth_data is not a dict: {type(auth_data)}, value: {auth_data}")
                message_text = (
                    "❌ حدث خطأ في بيانات المصادقة\n\n"
                    "يرجى البدء من جديد بالضغط على /start"
                )
                await self.edit_or_send_message(event, message_text)
                self.db.clear_conversation_state(user_id)
                return
            
            if 'phone' not in auth_data or 'phone_code_hash' not in auth_data:
                logger.error(f"Missing required keys in auth_data: {auth_data}")
                logger.error(f"Keys present: {list(auth_data.keys())}")
                message_text = (
                    "❌ بيانات المصادقة غير مكتملة\n\n"
                    "يرجى البدء من جديد بالضغط على /start"
                )
                await self.edit_or_send_message(event, message_text)
                self.db.clear_conversation_state(user_id)
                return
            
            phone = auth_data['phone']
            phone_code_hash = auth_data['phone_code_hash']

            # Create client and sign in
            data_dir = os.getenv('DATA_DIR', '/app/data')
            sessions_dir = os.getenv('SESSIONS_DIR', os.path.join(data_dir, 'sessions'))
            try:
                os.makedirs(sessions_dir, exist_ok=True)
            except Exception:
                pass
            session_name = auth_data.get('session_name', f'auth_{user_id}_{int(datetime.now().timestamp())}')
            # If old auth_data stored a bare name, place it under sessions_dir
            if not os.path.isabs(session_name):
                session_name = os.path.join(sessions_dir, session_name)
            temp_client = TelegramClient(session_name, int(API_ID), API_HASH)
            await temp_client.connect()

            try:
                # Try to sign in
                result = await temp_client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                
                # If we reach this point, login was successful without 2FA
                logger.info(f"✅ تم تسجيل الدخول بنجاح بدون تحقق ثنائي للمستخدم {user_id}")
                
                # Complete login process
                await self._complete_login_process(event, temp_client, result, phone, user_id)

            except Exception as signin_error:
                from telethon.errors import SessionPasswordNeededError
                error_message = str(signin_error)
                logger.error(f"خطأ في تسجيل الدخول: {error_message}")
                logger.error(f"نوع الخطأ: {type(signin_error).__name__}")
                
                # Check for 2FA requirement using both exception type and message
                is_2fa_required = (
                    isinstance(signin_error, SessionPasswordNeededError) or
                    "PASSWORD_NEEDED" in error_message or 
                    "Two-steps verification is enabled" in error_message or
                    "password is required" in error_message or
                    "SessionPasswordNeededError" in error_message
                )
                
                if is_2fa_required:
                    logger.info(f"🔐 التحقق الثنائي مطلوب للمستخدم {user_id}")
                    # 2FA is enabled, ask for password
                    from telethon.sessions import StringSession
                    auth_data['session_client'] = StringSession.save(temp_client.session)
                    self.db.set_conversation_state(user_id, 'waiting_password', json.dumps(auth_data))

                    buttons = [
                        [Button.inline("❌ إلغاء", b"cancel_auth")]
                    ]

                    message_text = (
                        "🔐 التحقق الثنائي مفعل على حسابك\n\n"
                        "🗝️ أرسل كلمة المرور الخاصة بالتحقق الثنائي:\n\n"
                        "💡 هذه هي كلمة المرور التي أنشأتها عند تفعيل التحقق بخطوتين في تليجرام"
                    )
                    await self.force_new_message(event, message_text, buttons=buttons)
                    
                    # We saved the session string; disconnect temp client to avoid leaks
                    try:
                        await temp_client.disconnect()
                    except Exception:
                        pass
                    return
                else:
                    # Other error, disconnect and report
                    await temp_client.disconnect()
                    message_text = (
                        "❌ الرمز غير صحيح أو منتهي الصلاحية\n\n"
                        "🔢 أرسل الرمز الصحيح أو اطلب رمز جديد"
                    )
                    await self.edit_or_send_message(event, message_text)
                    return

        except KeyError as e:
            logger.error(f"خطأ في البيانات المطلوبة للتحقق: {e}")
            message_text = (
                "❌ خطأ في البيانات المطلوبة للتحقق\n\n"
                "🔄 يرجى البدء من جديد بإرسال رقم الهاتف"
            )
            await self.edit_or_send_message(event, message_text)
            # Clear the conversation state to allow restart
            self.db.clear_conversation_state(user_id)
        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {e}")
            message_text = (
                "❌ الرمز غير صحيح أو منتهي الصلاحية\n\n"
                "🔢 أرسل الرمز الصحيح أو اطلب رمز جديد"
            )
            await self.edit_or_send_message(event, message_text)

    async def handle_session_input(self, event, session_string: str):
        """Handle session string input"""
        user_id = event.sender_id
        
        # Clean the session string
        session_string = session_string.strip()
        
        # Basic validation
        if not session_string or len(session_string) < 100:
            message_text = (
                "❌ الجلسة غير صحيحة\n\n"
                "📋 تأكد من:\n"
                "• نسخ الجلسة كاملة\n"
                "• الجلسة تبدأ بـ 1 أو 2\n"
                "• طول الجلسة أكثر من 100 حرف\n\n"
                "🔍 **كيفية الحصول على الجلسة**:\n"
                "• استخدم @SessionStringBot\n"
                "• أو استخدم @StringSessionBot\n"
                "• أو استخدم @UseTGXBot\n\n"
                "أرسل الجلسة مرة أخرى:"
            )
            await self.edit_or_send_message(event, message_text)
            return
        
        try:
            # Validate session string by trying to create a client
            from telethon.sessions import StringSession
            from telethon import TelegramClient
            
            # Create temporary client to test session
            temp_client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
            
            # Connect with timeout
            await asyncio.wait_for(temp_client.connect(), timeout=15)
            
            if not temp_client.is_connected():
                raise Exception("فشل في الاتصال بخوادم تليجرام")
            
            # Check if session is authorized
            if not await temp_client.is_user_authorized():
                await temp_client.disconnect()
                message_text = (
                    "❌ الجلسة غير صالحة أو منتهية الصلاحية\n\n"
                    "🔍 **الأسباب المحتملة**:\n"
                    "• الجلسة منتهية الصلاحية\n"
                    "• تم تسجيل الخروج من الجلسة\n"
                    "• تم تغيير كلمة المرور\n\n"
                    "💡 **الحل**:\n"
                    "• احصل على جلسة جديدة\n"
                    "• أو استخدم تسجيل الدخول برقم الهاتف"
                )
                await self.edit_or_send_message(event, message_text)
                self.db.clear_conversation_state(user_id)
                return
            
            # Get user info
            user = await temp_client.get_me()
            
            # Get phone number from session
            phone = getattr(user, 'phone', None)
            if not phone:
                phone = "غير متوفر"
            
            # Save session to database
            self.db.save_user_session(user_id, phone, session_string)
            
            # Clear conversation state
            self.db.clear_conversation_state(user_id)
            
            # Disconnect temp client
            await temp_client.disconnect()
            
            # Start UserBot with this session
            from userbot_service.userbot import userbot_instance
            success = await userbot_instance.start_with_session(user_id, session_string)
            
            if success:
                # Send session to Saved Messages
                try:
                    user_client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
                    await user_client.connect()
                    
                    session_message = (
                        f"🔐 جلسة تسجيل الدخول - بوت التوجيه التلقائي\n\n"
                        f"📱 الرقم: {phone}\n"
                        f"👤 الاسم: {user.first_name}\n"
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
                
                message_text = (
                    f"🎉 تم تسجيل الدخول بنجاح!\n\n"
                    f"👋 مرحباً {user.first_name}!\n"
                    f"✅ تم ربط حسابك بنجاح\n"
                    f"📱 الرقم: {phone}\n"
                    f"{session_saved_text}\n\n"
                    f"🚀 يمكنك الآن إنشاء مهام التوجيه التلقائي"
                )
                await self.force_new_message(event, message_text, buttons=buttons)
                
            else:
                message_text = (
                    "⚠️ تم حفظ الجلسة ولكن فشل في تشغيل خدمة التوجيه\n\n"
                    "🔍 **الأسباب المحتملة**:\n"
                    "• مشكلة في الاتصال\n"
                    "• الجلسة قديمة\n"
                    "• مشكلة في الخادم\n\n"
                    "💡 **الحل**:\n"
                    "• حاول مرة أخرى\n"
                    "• أو استخدم جلسة جديدة"
                )
                await self.edit_or_send_message(event, message_text)
                
        except asyncio.TimeoutError:
            message_text = (
                "❌ مهلة زمنية في الاتصال\n\n"
                "🌐 تأكد من اتصالك بالإنترنت وحاول مرة أخرى"
            )
            await self.edit_or_send_message(event, message_text)
            self.db.clear_conversation_state(user_id)
            
        except Exception as e:
            logger.error(f"خطأ في التحقق من الجلسة: {e}")
            error_message = str(e)
            
            if "AUTH_KEY_UNREGISTERED" in error_message:
                message_text = (
                    "❌ الجلسة غير صالحة أو منتهية الصلاحية\n\n"
                    "🔍 **الأسباب المحتملة**:\n"
                    "• الجلسة منتهية الصلاحية\n"
                    "• تم تسجيل الخروج من الجلسة\n"
                    "• تم تغيير كلمة المرور\n\n"
                    "💡 **الحل**:\n"
                    "• احصل على جلسة جديدة\n"
                    "• أو استخدم تسجيل الدخول برقم الهاتف"
                )
            elif "PHONE_CODE_INVALID" in error_message:
                message_text = (
                    "❌ رمز التحقق غير صحيح\n\n"
                    "🔍 **الأسباب المحتملة**:\n"
                    "• الرمز منتهي الصلاحية\n"
                    "• الرمز غير صحيح\n\n"
                    "💡 **الحل**:\n"
                    "• اطلب رمز جديد\n"
                    "• أو استخدم تسجيل الدخول بجلسة جاهزة"
                )
            else:
                message_text = (
                    f"❌ حدث خطأ في التحقق من الجلسة\n\n"
                    f"🔍 **تفاصيل الخطأ**:\n"
                    f"{error_message}\n\n"
                    f"💡 **الحل**:\n"
                    f"• تأكد من صحة الجلسة\n"
                    f"• أو استخدم تسجيل الدخول برقم الهاتف"
                )
            
            await self.edit_or_send_message(event, message_text)
            self.db.clear_conversation_state(user_id)

    async def handle_password_input(self, event, password: str, data: str):
        """Handle 2FA password input"""
        user_id = event.sender_id

        try:
            # data is already a dict from handle_auth_message
            auth_data = data
            
            # Validate that required keys exist
            if not isinstance(auth_data, dict):
                logger.error(f"auth_data is not a dict: {type(auth_data)}, value: {auth_data}")
                message_text = (
                    "❌ حدث خطأ في بيانات المصادقة\n\n"
                    "يرجى البدء من جديد بالضغط على /start"
                )
                await self.edit_or_send_message(event, message_text)
                self.db.clear_conversation_state(user_id)
                return
            
            if 'phone' not in auth_data or 'session_client' not in auth_data:
                logger.error(f"Missing required keys in auth_data: {auth_data}")
                logger.error(f"Keys present: {list(auth_data.keys())}")
                message_text = (
                    "❌ بيانات المصادقة غير مكتملة\n\n"
                    "يرجى البدء من جديد بالضغط على /start"
                )
                await self.edit_or_send_message(event, message_text)
                self.db.clear_conversation_state(user_id)
                return
            
            phone = auth_data['phone']
            session_string = auth_data['session_client'] # This is the session string from previous step

            # Create client and sign in with password
            from telethon.sessions import StringSession
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

            message_text = (
                f"🎉 تم تسجيل الدخول بنجاح!\n\n"
                f"👋 مرحباً {result.first_name}!\n"
                f"✅ تم ربط حسابك بنجاح\n"
                f"{session_saved_text}\n\n"
                f"🚀 يمكنك الآن إنشاء مهام التوجيه التلقائي"
            )
            await self.force_new_message(event, message_text, buttons=buttons)
            await temp_client.disconnect()

        except KeyError as e:
            logger.error(f"خطأ في البيانات المطلوبة للتحقق الثنائي: {e}")
            message_text = (
                "❌ خطأ في البيانات المطلوبة للتحقق الثنائي\n\n"
                "🔄 يرجى البدء من جديد بإرسال رقم الهاتف"
            )
            await self.edit_or_send_message(event, message_text)
            # Clear the conversation state to allow restart
            self.db.clear_conversation_state(user_id)
        except Exception as e:
            logger.error(f"خطأ في التحقق من كلمة المرور: {e}")
            message_text = (
                "❌ كلمة المرور غير صحيحة أو هناك مشكلة في التحقق الثنائي.\n\n"
                "تأكد من إدخال كلمة المرور الصحيحة وحاول مرة أخرى."
            )
            await self.edit_or_send_message(event, message_text)

    async def cancel_auth(self, event):
        """Cancel authentication"""
        user_id = event.sender_id
        self.db.clear_conversation_state(user_id)

        buttons = [
            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        ]

        message_text = (
            "❌ تم إلغاء عملية تسجيل الدخول\n\n"
            "يمكنك المحاولة مرة أخرى في أي وقت"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        message_text = (
            "🕐 **تحديد ساعات العمل**\n\n"
            "أدخل ساعة البداية (0-23):\n"
            "مثال: 9 للساعة 9 صباحاً\n"
            "أو 13 للساعة 1 ظهراً"
        )
        buttons = [[Button.inline("❌ إلغاء", f"working_hours_filter_{task_id}")]]
        await self.force_new_message(event, message_text, buttons=buttons)

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
            new_mode = 'sleep_hours' if current_mode == 'work_hours' else 'work_hours'
            
            # Log the mode change for debugging
            logger.info(f"🔄 تبديل وضع ساعات العمل للمهمة {task_id}: {current_mode} -> {new_mode}")
            
            # Update mode
            success = self.db.update_working_hours(task_id, mode=new_mode)
            
            if success:
                # Verify the update was saved correctly
                updated_settings = self.db.get_working_hours(task_id)
                saved_mode = updated_settings.get('mode', 'unknown')
                logger.info(f"✅ تم حفظ الوضع الجديد في قاعدة البيانات: {saved_mode}")
                
                mode_text = "ساعات العمل فقط" if new_mode == 'work_hours' else "خارج ساعات العمل"
                await event.answer(f"✅ تم تحديث وضع ساعات العمل: {mode_text}")
                
                # Force refresh UserBot tasks and clear any cache
                try:
                    from userbot_service.userbot import userbot_instance
                    if user_id in userbot_instance.clients:
                        await userbot_instance.refresh_user_tasks(user_id)
                        # Clear any cached settings if they exist
                        if hasattr(userbot_instance, 'working_hours_cache'):
                            userbot_instance.working_hours_cache.pop(task_id, None)
                        logger.info(f"🔄 تم تحديث مهام UserBot وإزالة الذاكرة المؤقتة بعد تغيير وضع ساعات العمل")
                except Exception as e:
                    logger.error(f"خطأ في تحديث مهام UserBot: {e}")
                
                # Return to working hours filter menu
                await self.show_working_hours_filter(event, task_id)
            else:
                logger.error(f"❌ فشل في حفظ وضع ساعات العمل للمهمة {task_id}")
                await event.answer("❌ فشل في تحديث الإعداد")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل وضع ساعات العمل: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def handle_task_action(self, event, data):
        """Handle task actions"""
        user_id = event.sender_id

        # Check if user is authenticated
        if not self.db.is_user_authenticated(user_id):
            await self.edit_or_send_message(event, "❌ يجب تسجيل الدخول أولاً")
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
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء إنشاء المهمة. حاول مرة أخرى.")
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

        message_text = (
            f"⚙️ **إعدادات البوت**\n\n"
            f"🌐 اللغة الحالية: {language_name}\n"
            f"🕐 المنطقة الزمنية الحالية: {timezone_name}\n\n"
            "اختر الإعداد الذي تريد تغييره:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def check_userbot_status(self, event):
        """Check UserBot status for user"""
        user_id = event.sender_id

        try:
            from userbot_service.userbot import userbot_instance

            # Check if user has session
            session_data = self.db.get_user_session(user_id)
            if not session_data or len(session_data) < 2: # Corrected check for session_data and its length
                message_text = (
                    "❌ **حالة UserBot: غير مسجل دخول**\n\n"
                    "🔐 يجب تسجيل الدخول أولاً\n"
                    "📱 اذهب إلى الإعدادات → إعادة تسجيل الدخول"
                )
                buttons = [[Button.inline("🔄 تسجيل الدخول", "login"), Button.inline("🏠 الرئيسية", "main_menu")]]
                await self.force_new_message(event, message_text, buttons=buttons)
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
                # Check if session exists but UserBot not running
                session_health = self.db.get_user_session_health(user_id)
                
                if session_health and not session_health.get('is_healthy', False):
                    # Session exists but unhealthy
                    last_error = session_health.get('last_error', 'غير معروف')
                    status_message = (
                        f"⚠️ **حالة UserBot: جلسة معطلة**\n\n"
                        f"📝 **السبب:** {last_error}\n\n"
                        f"🔧 **الحلول:**\n"
                        f"• إعادة تسجيل الدخول (مستحسن)\n"
                        f"• محاولة إعادة التشغيل\n\n"
                        f"💡 **ملاحظة:** بوت التحكم يعمل بشكل منفصل\n"
                        f"ويمكنك إدارة المهام حتى لو كان UserBot معطل"
                    )
                else:
                    # Try to restart UserBot if session exists
                    status_message = (
                        f"🔄 **حالة UserBot: محاولة إعادة التشغيل...**\n\n"
                        f"⏳ يرجى الانتظار..."
                    )

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
                                f"🚨 **مطلوب إعادة تسجيل الدخول**\n\n"
                                f"📝 **الأسباب المحتملة:**\n"
                                f"• تم استخدام الجلسة من جهاز آخر\n"
                                f"• انتهت صلاحية الجلسة\n"
                                f"• تغيير في إعدادات الأمان\n\n"
                                f"✅ **بوت التحكم يعمل بشكل طبيعي**"
                            )
                    else:
                        status_message = (
                            f"❌ **حالة UserBot: غير مسجل دخول**\n\n"
                            f"🔐 لا توجد جلسة محفوظة\n"
                            f"📱 يجب تسجيل الدخول أولاً"
                        )

            # Dynamic buttons based on UserBot status
            if is_userbot_running:
                buttons = [
                    [Button.inline("🔄 فحص مرة أخرى", "check_userbot")],
                    [Button.inline("⚙️ الإعدادات", "settings"), Button.inline("🏠 الرئيسية", "main_menu")]
                ]
            else:
                buttons = [
                    [Button.inline("🔄 إعادة تسجيل الدخول", "login")],
                    [Button.inline("🔄 فحص مرة أخرى", "check_userbot")],
                    [Button.inline("⚙️ الإعدادات", "settings"), Button.inline("🏠 الرئيسية", "main_menu")]
                ]

            await self.edit_or_send_message(event, status_message, buttons=buttons)

        except Exception as e:
            logger.error(f"خطأ في فحص حالة UserBot للمستخدم {user_id}: {e}")
            message_text = (
                f"❌ **خطأ في فحص حالة UserBot**\n\n"
                f"🔧 حاول مرة أخرى أو أعد تسجيل الدخول"
            )
            buttons = [[Button.inline("🔄 إعادة المحاولة", "check_userbot"), Button.inline("🏠 الرئيسية", "main_menu")]]
            await self.force_new_message(event, message_text, buttons=buttons)

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

        await self.edit_or_send_message(event, "🌐 **اختر اللغة المفضلة:**", buttons=buttons)

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

        await self.edit_or_send_message(event, "🕐 **اختر المنطقة الزمنية:**", buttons=buttons)

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

    async def start_edit_rate_count(self, event, task_id):
        """Start editing rate limit count"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set user state
        self.set_user_state(user_id, 'editing_rate_count', {'task_id': task_id})
        
        current_settings = self.db.get_rate_limit_settings(task_id)
        current_count = current_settings['message_count']
        
        buttons = [
            [Button.inline("❌ إلغاء", f"rate_limit_{task_id}")]
        ]
        
        message_text = (
            f"✏️ تعديل عدد الرسائل المسموحة\n\n"
            f"📊 القيمة الحالية: {current_count} رسالة\n\n"
            f"📝 أدخل عدد الرسائل الجديد (رقم من 1 إلى 1000):\n\n"
            f"💡 مثال: 5 (للسماح بـ 5 رسائل فقط)"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_edit_rate_period(self, event, task_id):
        """Start editing rate limit time period"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set user state
        self.set_user_state(user_id, 'editing_rate_period', {'task_id': task_id})
        
        current_settings = self.db.get_rate_limit_settings(task_id)
        current_period = current_settings['time_period_seconds']
        
        buttons = [
            [Button.inline("❌ إلغاء", f"rate_limit_{task_id}")]
        ]
        
        message_text = (
            f"✏️ تعديل فترة التحكم بالمعدل\n\n"
            f"📊 القيمة الحالية: {current_period} ثانية\n\n"
            f"📝 أدخل الفترة الجديدة بالثواني (من 1 إلى 3600):\n\n"
            f"💡 مثال: 60 (دقيقة واحدة)"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_edit_forwarding_delay(self, event, task_id):
        """Start editing forwarding delay"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set user state
        self.set_user_state(user_id, 'editing_forwarding_delay', {'task_id': task_id})
        
        current_settings = self.db.get_forwarding_delay_settings(task_id)
        current_delay = current_settings.get('delay_seconds', 0)
        
        buttons = [
            [Button.inline("❌ إلغاء", f"forwarding_settings_{task_id}")]
        ]
        
        message_text = (
            f"✏️ تعديل تأخير التوجيه\n\n"
            f"📊 القيمة الحالية: {current_delay} ثانية\n\n"
            f"📝 أدخل التأخير الجديد بالثواني (من 0 إلى 300):\n\n"
            f"💡 مثال: 5 (تأخير 5 ثواني قبل التوجيه)"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_edit_sending_interval(self, event, task_id):
        """Start editing sending interval"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set user state
        self.set_user_state(user_id, 'editing_sending_interval', {'task_id': task_id})
        
        current_settings = self.db.get_sending_interval_settings(task_id)
        current_interval = current_settings.get('interval_seconds', 0)
        
        buttons = [
            [Button.inline("❌ إلغاء", f"forwarding_settings_{task_id}")]
        ]
        
        message_text = (
            f"✏️ تعديل فاصل الإرسال\n\n"
            f"📊 القيمة الحالية: {current_interval} ثانية\n\n"
            f"📝 أدخل الفاصل الجديد بالثواني (من 0 إلى 60):\n\n"
            f"💡 مثال: 2 (فاصل ثانيتين بين إرسال الرسائل)"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        await self.edit_or_send_message(event, message, buttons=buttons)
        
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
            await self.edit_or_send_message(event, "❌ تم إلغاء تعديل إعدادات الرابط.")
            await self.show_text_formatting(event, task_id)
            return

        # Parse the input - expecting only the URL
        hyperlink_url = message_text.strip()
        
        # No need for hyperlink text since we use original message text

        # Validate URL
        if not hyperlink_url.startswith(('http://', 'https://')):
            await self.edit_or_send_message(event, 
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
            await self.edit_or_send_message(event, 
                f"✅ تم تحديث رابط النص بنجاح!\n\n"
                f"• الرابط الجديد: {hyperlink_url}\n"
                f"• سيتم استخدام النص الأصلي كنص الرابط"
            )
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Return to text formatting settings
            await self.show_text_formatting(event, task_id)
        else:
            await self.edit_or_send_message(event, "❌ فشل في تحديث إعدادات الرابط")
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

        await self.edit_or_send_message(event, message, buttons=buttons)

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
            [Button.inline("ℹ️ تعليمات التنسيق", f"word_filters_help_{task_id}")],
            [Button.inline("🔙 رجوع لفلاتر الكلمات", f"word_filters_{task_id}")]
        ]

        await self.edit_or_send_message(event, message, buttons=buttons)

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
            [Button.inline("ℹ️ تعليمات التنسيق", f"word_filters_help_{task_id}")],
            [Button.inline("🔙 رجوع لفلاتر الكلمات", f"word_filters_{task_id}")]
        ]

        await self.edit_or_send_message(event, message, buttons=buttons)

    async def word_filters_help(self, event, task_id):
        """Show help for adding words with flags"""
        help_text = (
            "ℹ️ تعليمات تنسيق الكلمات\n\n"
            "- أضف '#حساس' لجعل المطابقة حساسة لحالة الأحرف\n"
            "- أضف '#كلمة' لمطابقة الكلمة كاملة فقط (تجاهل مثل نعمات)\n\n"
            "أمثلة:\n"
            "- نعم #كلمة\n"
            "- Promo #حساس\n"
            "- Offer #حساس #كلمة\n"
        )
        buttons = [[Button.inline("🔙 رجوع لفلاتر الكلمات", f"word_filters_{task_id}")]]
        await self.edit_or_send_message(event, help_text, buttons=buttons)

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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        await self.edit_or_send_message(event, message, buttons=buttons)

    async def clear_text_cleaning_keywords(self, event, task_id: int):
        """Clear all keywords for text-cleaning line removal"""
        try:
            cleared = self.db.clear_text_cleaning_keywords(task_id)
            await event.answer("✅ تم حذف جميع الكلمات")
            await self.manage_text_cleaning_keywords(event, task_id)
        except Exception as e:
            logger.error(f"خطأ في مسح كلمات التنظيف: {e}")
            await event.answer("❌ فشل في مسح الكلمات")

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

        await self.edit_or_send_message(event, message, buttons=buttons)
        
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
            await self.edit_or_send_message(event, "❌ خطأ في البيانات. حاول مرة أخرى.")
            self.db.clear_conversation_state(user_id)
            return

        # Check if user wants to cancel
        if message_text.lower() in ['إلغاء', 'cancel']:
            self.db.clear_conversation_state(user_id)
            await self.edit_or_send_message(event, "❌ تم إلغاء إضافة الكلمات.")
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
            await self.edit_or_send_message(event, "❌ لم يتم إدخال أي كلمات صالحة. حاول مرة أخرى أو أرسل 'إلغاء' للخروج.")
            return

        # Add keywords to database
        added_count = self.db.add_text_cleaning_keywords(task_id, keywords_to_add)
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        if added_count > 0:
            await self.edit_or_send_message(event, f"✅ تم إضافة {added_count} كلمة/جملة لحذف الأسطر")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Return to keywords management
            await self.manage_text_cleaning_keywords(event, task_id)
        else:
            await self.edit_or_send_message(event, "⚠️ لم يتم إضافة أي كلمات جديدة (قد تكون موجودة مسبقاً)")
            await self.manage_text_cleaning_keywords(event, task_id)

    async def show_text_formatting(self, event, task_id, force_refresh=False):
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
            message += "🟢 حالة التنسيق: مُفعل ✅\n"
            message += f"📝 النوع المحدد: {self._get_format_name(current_format)}\n\n"
            message += "🎨 اختر نوع التنسيق المطلوب:\n"
        else:
            message += "🔴 حالة التنسيق: معطل ❌\n\n"
            message += "💡 لعرض خيارات التنسيق، اضغط على زر التفعيل أولاً\n"

        buttons = []
        
        # Toggle enable/disable button
        toggle_text = "❌ تعطيل" if is_enabled else "✅ تفعيل"
        buttons.append([Button.inline(f"{toggle_text} تنسيق النصوص", f"toggle_text_formatting_{task_id}")])

        if is_enabled:
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
            
            # Format type selection buttons (2 per row for better layout)
            for i in range(0, len(format_types), 2):
                row = []
                for j in range(2):
                    if i + j < len(format_types):
                        fmt_type, fmt_name, example = format_types[i + j]
                        is_current = fmt_type == current_format
                        status_icon = "✅" if is_current else "⚪"
                        row.append(Button.inline(f"{status_icon} {fmt_name}", f"set_text_format_{fmt_type}_{task_id}"))
                buttons.append(row)

            # Special handling for hyperlink format
            if current_format == 'hyperlink':
                link_text = settings.get('hyperlink_text', 'نص')
                link_url = settings.get('hyperlink_url', 'https://example.com')
                message += f"\n🔗 إعدادات الرابط الحالية:\n"
                message += f"• النص: {link_text}\n"
                message += f"• الرابط: {link_url}\n"
                buttons.append([Button.inline("🔧 تعديل إعدادات الرابط", f"edit_hyperlink_{task_id}")])

        buttons.append([Button.inline("🔙 رجوع للإعدادات", f"task_settings_{task_id}")])

        # Add timestamp or force refresh to avoid MessageNotModifiedError
        if force_refresh:
            import datetime
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            message += f"\n🕐 آخر تحديث: {timestamp}"

        await self.edit_or_send_message(event, message, buttons=buttons)

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
        
        # Show updated settings with force refresh to ensure content changes
        await self.show_text_formatting(event, task_id, force_refresh=True)

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
            
            # Show updated settings with force refresh to update selected format
            await self.show_text_formatting(event, task_id, force_refresh=True)
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

        await self.edit_or_send_message(event, message, buttons=buttons)
        
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

        await self.edit_or_send_message(event, message, buttons=buttons)

    # Duplicate function removed - using the one at line 6212

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
            await self.edit_or_send_message(event, "❌ تم إلغاء إضافة الكلمات")
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
            await self.edit_or_send_message(event, "❌ لم يتم إدخال أي كلمات صالحة. حاول مرة أخرى أو أرسل 'إلغاء' للخروج.")
            return

        # Add words to filter
        added_count = self.db.add_multiple_filter_words(task_id, filter_type, words_to_add)
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        if added_count > 0:
            filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"
            await self.edit_or_send_message(event, f"✅ تم إضافة {added_count} كلمة/جملة إلى {filter_name}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Send new message instead of trying to edit
            if filter_type == 'whitelist':
                await self.show_whitelist_management_new(event, task_id)
            else:
                await self.show_blacklist_management_new(event, task_id)
        else:
            await self.edit_or_send_message(event, "⚠️ لم يتم إضافة أي كلمات جديدة (قد تكون موجودة مسبقاً)")
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

        await self.edit_or_send_message(event, message, buttons=buttons)

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
            await self.edit_or_send_message(event, "❌ خطأ في البيانات، حاول مرة أخرى")
            self.db.clear_conversation_state(user_id)
            return

        # Parse words input
        if ',' in words_input:
            words = [word.strip() for word in words_input.split(',') if word.strip()]
        else:
            words = [words_input] if words_input else []

        if not words:
            await self.edit_or_send_message(event, "❌ لم يتم إدخال أي كلمات صحيحة")
            return

        # Add each word (support flags: #حساس for case-sensitive, #كلمة for whole-word)
        added_count = 0
        for word in words:
            if len(word) > 200:  # Limit word length
                continue

            is_case_sensitive = False
            is_whole_word = False
            # Flags at the end of the token
            if word.endswith('#حساس'):
                is_case_sensitive = True
                word = word.replace('#حساس', '').strip()
            if word.endswith('#كلمة'):
                is_whole_word = True
                word = word.replace('#كلمة', '').strip()
            # Also support both flags regardless of order
            if '#حساس' in word:
                is_case_sensitive = True
                word = word.replace('#حساس', '').strip()
            if '#كلمة' in word:
                is_whole_word = True
                word = word.replace('#كلمة', '').strip()

            success = self.db.add_word_to_filter(task_id, filter_type, word, is_case_sensitive=is_case_sensitive, is_whole_word=is_whole_word)
            if success:
                added_count += 1

        # Clear conversation state
        self.db.clear_conversation_state(user_id)

        filter_name = "القائمة البيضاء" if filter_type == 'whitelist' else "القائمة السوداء"

        if added_count > 0:
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)

            await self.edit_or_send_message(event, f"✅ تم إضافة {added_count} كلمة إلى {filter_name}")
            # Return to the specific filter management page
            if filter_type == 'whitelist':
                await self.handle_manage_whitelist(event)
            else:
                await self.handle_manage_blacklist(event)
        else:
            await self.edit_or_send_message(event, "❌ فشل في إضافة الكلمات أو أنها موجودة بالفعل")

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

    # Duplicate function removed - using the one at line 6712

    async def show_about(self, event):
        buttons = [
            [Button.inline("🏠 العودة للرئيسية", b"back_main")]
        ]

        message_text = (
            "ℹ️ **حول البوت**\n\n"
            "🤖 **بوت التوجيه التلقائي المطور**\n"
            "📋 يساعدك في توجيه الرسائل تلقائياً بين المجموعات والقنوات\n\n"
            "🆕 **التحديث الجديد (أغسطس 2025):**\n"
            "🔄 نظام منفصل ومستقل\n"
            "• بوت التحكم منفصل عن UserBot\n"
            "• يعمل حتى لو تعطل UserBot\n"
            "• إعادة تسجيل دخول سهلة\n"
            "• مراقبة صحة الجلسات تلقائياً\n\n"
            "🔧 **الميزات الأساسية:**\n"
            "• توجيه تلقائي للرسائل\n"
            "• إدارة مهام التوجيه\n"
            "• فلاتر متقدمة ومتنوعة\n"
            "• واجهة عربية سهلة الاستخدام\n"
            "• نظام إعادة تشغيل ذكي\n\n"
            "💡 **مميزات الاستقرار:**\n"
            "• لا توقف في حالة انقطاع الجلسات\n"
            "• إعادة اتصال تلقائية\n"
            "• رسائل خطأ واضحة ومفيدة\n"
            "• حلول سريعة للمشاكل\n\n"
            "💻 **تطوير:** نظام بوت تليجرام متطور"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

    async def _cleanup_expired_pending_messages_loop(self):
        """Periodically mark expired pending messages as expired."""
        import asyncio
        logger.info("🧹 بدء مهمة تنظيف الرسائل المعلقة منتهية الصلاحية")
        while True:
            try:
                cleaned = self.db.cleanup_expired_pending_messages()
                if cleaned:
                    logger.info(f"🧹 تم وسم {cleaned} رسائل معلقة كمنتهية الصلاحية")
            except Exception as e:
                logger.debug(f"خطأ في تنظيف الرسائل المعلقة: {e}")
            await asyncio.sleep(300)

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
            await self.edit_or_send_message(event, "❌ لم يتم العثور على المهمة")
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

        await self.edit_or_send_message(event, message, buttons=buttons)

    async def show_blacklist_management_new(self, event, task_id):
        """Show blacklist management interface with new message"""
        task = self.db.get_task(task_id, event.sender_id)
        if not task:
            await self.edit_or_send_message(event, "❌ لم يتم العثور على المهمة")
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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        message_text = (
            f"🔄 استبدال النصوص - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"📝 **عدد الاستبدالات**: {len(replacements)}\n\n"
            f"🔄 **الوظيفة**: استبدال كلمات أو عبارات محددة في الرسائل قبل توجيهها إلى الهدف\n\n"
            f"💡 **مثال**: استبدال 'مرحبا' بـ 'أهلا وسهلا' في جميع الرسائل\n\n"
            f"⚠️ **ملاحظة**: عند تفعيل الاستبدال، سيتم تحويل وضع التوجيه تلقائياً إلى 'نسخ' للرسائل المعدلة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

        message_text = (
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
            f"⚠️ **ملاحظة**: يمكنك إدخال عدة استبدالات في رسالة واحدة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
            await self.edit_or_send_message(event,
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

        message_text = (
            f"✅ تم إضافة {added_count} استبدال نصي\n\n"
            f"📊 إجمالي الاستبدالات المرسلة: {len(replacements_to_add)}\n"
            f"📝 الاستبدالات المضافة: {added_count}\n"
            f"🔄 الاستبدالات المكررة: {len(replacements_to_add) - added_count}\n\n"
            f"✅ استبدال النصوص جاهز للاستخدام!"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        message_text = (
            f"⚠️ تأكيد حذف الاستبدالات النصية\n\n"
            f"🗑️ هل أنت متأكد من حذف جميع الاستبدالات ({len(replacements)} استبدال)؟\n\n"
            f"❌ **تحذير**: هذا الإجراء لا يمكن التراجع عنه!\n\n"
            f"سيتم حذف جميع استبدالات النصوص نهائياً."
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
            [Button.inline(f"تطبيق على النصوص: {'✅' if settings.get('apply_header_to_texts', True) else '❌'}", f"toggle_header_scope_texts_{task_id}")],
            [Button.inline(f"تطبيق على الوسائط: {'✅' if settings.get('apply_header_to_media', True) else '❌'}", f"toggle_header_scope_media_{task_id}")],
            [Button.inline("🔙 عودة للإعدادات", f"task_settings_{task_id}")]
        ]

        message_text = (
            f"📝 رأس الرسالة - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"💬 **النص الحالي**: {current_header}\n\n"
            f"🔄 **الوظيفة**: إضافة نص في بداية كل رسالة قبل توجيهها\n\n"
            f"💡 **مثال**: إضافة 'من قناة الأخبار:' في بداية كل رسالة\n\n"
            f"⚠️ **ملاحظة**: سيتم تحويل وضع التوجيه إلى 'نسخ' عند تفعيل الرأس"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

        message_text = (
            f"✏️ تعديل رأس الرسالة\n\n"
            f"💬 **النص الحالي**: {current_text}\n\n"
            f"📝 أرسل النص الجديد للرأس:\n\n"
            f"💡 **أمثلة**:\n"
            f"• من قناة الأخبار:\n"
            f"• 🚨 عاجل:\n"
            f"• تحديث مهم:\n\n"
            f"⚠️ **ملاحظة**: يمكنك استخدام الرموز والإيموجي"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_set_header_text(self, event, task_id, text):
        """Handle setting header text"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        # Validate task_id
        if not task_id or task_id == 0:
            await self.edit_or_send_message(event, "❌ خطأ: معرف المهمة غير صالح")
            return
            
        # Check if task exists and belongs to user
        task = self.db.get_task(task_id, user_id)
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة أو لا تملك صلاحية الوصول إليها")
            return
        
        # Update header text and enable it
        self.db.update_header_settings(task_id, True, text.strip())
        
        await self.edit_or_send_message(event, f"✅ تم تحديث رأس الرسالة بنجاح")
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
            [Button.inline(f"تطبيق على النصوص: {'✅' if settings.get('apply_footer_to_texts', True) else '❌'}", f"toggle_footer_scope_texts_{task_id}")],
            [Button.inline(f"تطبيق على الوسائط: {'✅' if settings.get('apply_footer_to_media', True) else '❌'}", f"toggle_footer_scope_media_{task_id}")],
            [Button.inline("🔙 عودة للإعدادات", f"task_settings_{task_id}")]
        ]

        message_text = (
            f"📝 ذيل الرسالة - المهمة #{task_id}\n\n"
            f"📊 **الحالة**: {status}\n"
            f"💬 **النص الحالي**: {current_footer}\n\n"
            f"🔄 **الوظيفة**: إضافة نص في نهاية كل رسالة قبل توجيهها\n\n"
            f"💡 **مثال**: إضافة 'انضم لقناتنا: @channel' في نهاية كل رسالة\n\n"
            f"⚠️ **ملاحظة**: سيتم تحويل وضع التوجيه إلى 'نسخ' عند تفعيل الذيل"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

        message_text = (
            f"✏️ تعديل ذيل الرسالة\n\n"
            f"💬 **النص الحالي**: {current_text}\n\n"
            f"📝 أرسل النص الجديد للذيل:\n\n"
            f"💡 **أمثلة**:\n"
            f"• انضم لقناتنا: @channel\n"
            f"• 🔔 تابعنا للمزيد\n"
            f"• www.example.com\n\n"
            f"⚠️ **ملاحظة**: يمكنك استخدام الرموز والروابط"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_set_footer_text(self, event, task_id, text):
        """Handle setting footer text"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        # Validate task_id
        if not task_id or task_id == 0:
            await self.edit_or_send_message(event, "❌ خطأ: معرف المهمة غير صالح")
            return
            
        # Check if task exists and belongs to user
        task = self.db.get_task(task_id, user_id)
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة أو لا تملك صلاحية الوصول إليها")
            return
        
        # Update footer text and enable it
        self.db.update_footer_settings(task_id, True, text.strip())
        
        await self.edit_or_send_message(event, f"✅ تم تحديث ذيل الرسالة بنجاح")
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
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

        message_text = (
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
            f"⚠️ **ملاحظة**: استخدم الشرطة (-) لفصل النص عن الرابط"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_add_inline_button(self, event, task_id, text):
        """Handle adding inline buttons with new format"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        # Validate task_id
        if not task_id or task_id == 0:
            await self.edit_or_send_message(event, "❌ خطأ: معرف المهمة غير صالح")
            return
            
        # Check if task exists and belongs to user
        task = self.db.get_task(task_id, user_id)
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة أو لا تملك صلاحية الوصول إليها")
            return
        
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
        
        await self.edit_or_send_message(event, result_msg)
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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        message_text = (
            f"⚠️ تأكيد حذف الأزرار الإنلاين\n\n"
            f"🗑️ هل أنت متأكد من حذف جميع الأزرار ({len(buttons_list)} زر)؟\n\n"
            f"❌ **تحذير**: هذا الإجراء لا يمكن التراجع عنه!\n\n"
            f"سيتم حذف جميع الأزرار الإنلاين نهائياً."
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        sync_pin_status = "🟢 مفعل" if settings.get('sync_pin_enabled', False) else "🔴 معطل"
        clear_pin_notif_status = "🟢 مسح" if settings.get('clear_pin_notification', False) else "🔴 إبقاء"
        clear_pin_time = settings.get('pin_notification_clear_time', 0)
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
             Button.inline(f"📌 إعدادات التثبيت", f"pin_settings_{task_id}")],
            
            # الصف الثاني - الإشعارات والألبومات
            [Button.inline(f"🔔 الإشعارات {silent_status.split()[0]}", f"toggle_silent_notifications_{task_id}"),
             Button.inline(f"📸 الألبومات {split_album_status.split()[0]}", f"toggle_split_album_{task_id}")],
            
            # الصف الثالث - الحذف التلقائي ومزامنة التعديل
            [Button.inline(f"🗑️ حذف تلقائي {auto_delete_status.split()[0]}", f"toggle_auto_delete_{task_id}"),
             Button.inline(f"🔄 مزامنة التعديل {sync_edit_status.split()[0]}", f"toggle_sync_edit_{task_id}")],
            
            # الصف الرابع - مزامنة الحذف والحفاظ على الرد
            [Button.inline(f"🗂️ مزامنة الحذف {sync_delete_status.split()[0]}", f"toggle_sync_delete_{task_id}"),
             Button.inline(f"↩️ الحفاظ على الرد {('🟢' if settings.get('preserve_reply_enabled', True) else '🔴')}", f"toggle_preserve_reply_{task_id}")],
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
            f"📌 **إعدادات التثبيت**: {pin_message_status}\n"
            f"   └ مزامنة التثبيت: {sync_pin_status} | مسح إشعار التثبيت: {clear_pin_notif_status}"
            + (f" | وقت المسح: {clear_pin_time}ث" if clear_pin_time else "") + "\n\n"
            f"🕐 آخر تحديث: {timestamp}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

    async def toggle_preserve_reply(self, event, task_id):
        """Toggle preserving reply mapping"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        new_state = self.db.toggle_preserve_reply(task_id)
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} الحفاظ على الرد")
        await self.show_forwarding_settings(event, task_id)

    async def show_pin_settings(self, event, task_id):
        """Show pin-related settings submenu"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        settings = self.db.get_forwarding_settings(task_id)
        pin_message_status = "🟢 مفعل" if settings['pin_message_enabled'] else "🔴 معطل"
        sync_pin_status = "🟢 مفعل" if settings.get('sync_pin_enabled', False) else "🔴 معطل"
        clear_pin_status = "🟢 مسح" if settings.get('clear_pin_notification', False) else "🔴 إبقاء"
        clear_time = settings.get('pin_notification_clear_time', 0)
        buttons = [
            [Button.inline(f"📌 تثبيت تلقائي {pin_message_status.split()[0]}", f"toggle_pin_message_{task_id}")],
            [Button.inline(f"🔄 مزامنة التثبيت {sync_pin_status.split()[0]}", f"toggle_sync_pin_{task_id}")],
            [Button.inline(f"🧹 مسح إشعار التثبيت {clear_pin_status.split()[0]}", f"toggle_clear_pin_notif_{task_id}")],
        ]
        # Add time options for clearing pin notification
        time_options = [0, 5, 10, 30, 60, 300]
        time_buttons_row = []
        for t in time_options:
            label = "فوري" if t == 0 else f"{t}s"
            time_buttons_row.append(Button.inline(label, f"set_pin_clear_time_{task_id}_{t}"))
        buttons.append(time_buttons_row)
        buttons.append([Button.inline("🔙 رجوع", f"forwarding_settings_{task_id}")])
        text = (
            f"📌 إعدادات التثبيت للمهمة #{task_id}\n\n"
            f"• التثبيت التلقائي عند الإرسال: {pin_message_status}\n"
            f"• مزامنة التثبيت/إلغاء التثبيت من المصدر: {sync_pin_status}\n"
            f"• مسح إشعار التثبيت: {clear_pin_status}\n"
            f"• وقت المسح الحالي: {clear_time} ثانية"
        )
        await self.edit_or_send_message(event, text, buttons=buttons)

    async def toggle_sync_pin(self, event, task_id):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        new_state = self.db.toggle_sync_pin(task_id)
        await event.answer(f"✅ {'تم تفعيل' if new_state else 'تم إلغاء تفعيل'} مزامنة التثبيت")
        await self.show_pin_settings(event, task_id)

    async def toggle_clear_pin_notification(self, event, task_id):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        new_state = self.db.toggle_clear_pin_notification(task_id)
        await event.answer(f"✅ {'تم تفعيل' if new_state else 'تم إلغاء'} مسح إشعار التثبيت")
        await self.show_pin_settings(event, task_id)

    async def start_set_pin_clear_time(self, event, task_id):
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        # Present quick options again (handled by callbacks with set_pin_clear_time_{task_id}_{seconds})
        await self.show_pin_settings(event, task_id)

    async def set_pin_clear_time_direct(self, event, task_id, seconds):
        self.db.set_pin_notification_clear_time(task_id, int(seconds))
        await event.answer(f"✅ تم تعيين وقت مسح إشعار التثبيت إلى {seconds} ثانية")
        await self.show_pin_settings(event, task_id)

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

        await self.edit_or_send_message(event, message, buttons=buttons)

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

        message_text = (
            f"⏰ تحديد مدة الحذف التلقائي\n\n"
            f"📊 **المدة الحالية**: {current_display}\n\n"
            f"🎯 **اختر مدة جديدة**:\n\n"
            f"💡 أو أرسل رقماً بالثواني (مثال: 7200 للساعتين)\n\n"
            f"⚠️ **تنبيه**: سيتم حذف الرسائل تلقائياً بعد المدة المحددة"
        )
        await self.force_new_message(event, message_text, buttons=buttons)

    async def handle_set_auto_delete_time(self, event, task_id, time_str):
        """Handle setting auto delete time from text input"""
        user_id = event.sender_id
        
        # Clear conversation state
        self.db.clear_conversation_state(user_id)
        
        try:
            seconds = int(time_str.strip())
            if seconds < 60:
                await self.edit_or_send_message(event, "❌ أقل مدة مسموحة هي 60 ثانية")
                return
            elif seconds > 604800:  # 7 days
                await self.edit_or_send_message(event, "❌ أقصى مدة مسموحة هي 7 أيام (604800 ثانية)")
                return
                
            self.db.set_auto_delete_time(task_id, seconds)
            
            # Convert to readable format
            if seconds >= 3600:
                time_display = f"{seconds // 3600} ساعة"
            elif seconds >= 60:
                time_display = f"{seconds // 60} دقيقة"
            else:
                time_display = f"{seconds} ثانية"
                
            await self.edit_or_send_message(event, f"✅ تم تحديد مدة الحذف التلقائي إلى {time_display}")
            await self.show_forwarding_settings(event, task_id)
            
        except ValueError:
            await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح بالثواني")

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
    # Duplicate function removed - using the one at line 2130

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
                        target_chat_id = target['chat_id']

                        # Use the same full sending pipeline as auto mode
                        ub = userbot_instance
                        message_settings = ub.get_message_settings(task['id'])
                        forwarding_settings = ub.get_forwarding_settings(task['id'])

                        # Resolve target entity
                        try:
                            target_entity = await client.get_entity(int(target_chat_id))
                        except Exception:
                            target_entity = await client.get_entity(str(target_chat_id))

                        # Prepare final text
                        original_text = message.text or ""
                        cleaned_text = ub.apply_text_cleaning(original_text, task['id']) if original_text else original_text
                        modified_text = ub.apply_text_replacements(task['id'], cleaned_text) if cleaned_text else cleaned_text
                        translated_text = await ub.apply_translation(task['id'], modified_text) if modified_text else modified_text
                        formatted_text = ub.apply_text_formatting(task['id'], translated_text) if translated_text else translated_text
                        final_text = ub.apply_message_formatting(formatted_text, message_settings, is_media=bool(message.media))

                        forward_mode = task.get('forward_mode', 'forward')
                        applies_header = message_settings.get('header_enabled', False)
                        applies_footer = message_settings.get('footer_enabled', False)
                        requires_copy_mode = (
                            applies_header or applies_footer or
                            (original_text != modified_text) or
                            # If formatting changed the text (e.g., spoiler), prefer copy mode
                            (translated_text != formatted_text) or
                            message_settings.get('inline_buttons_enabled', False)
                        )
                        final_mode = ub._determine_final_send_mode(forward_mode, requires_copy_mode)

                        if final_mode == 'forward' and not (message.media and hasattr(message.media, 'webpage') and message.media.webpage):
                            forwarded_msg = await client.forward_messages(
                                target_entity,
                                message,
                                silent=forwarding_settings.get('silent_notifications', False)
                            )
                            msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                        else:
                            if message.media:
                                forwarded_msg = await client.send_file(
                                    target_entity,
                                    file=message.media,
                                    caption=final_text or None,
                                    silent=forwarding_settings.get('silent_notifications', False),
                                    force_document=False,
                                    parse_mode='HTML' if final_text else None
                                )
                            else:
                                forwarded_msg = await client.send_message(
                                    target_entity,
                                    final_text or (message.text or ""),
                                    silent=forwarding_settings.get('silent_notifications', False),
                                    parse_mode='HTML' if final_text else None
                                )
                            msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id

                        # Post-forwarding settings and mapping
                        try:
                            inline_buttons = None
                            if message_settings.get('inline_buttons_enabled', False):
                                inline_buttons = ub.build_inline_buttons(task['id'])
                            await ub.apply_post_forwarding_settings(client, target_entity, msg_id, forwarding_settings, task['id'], inline_buttons=inline_buttons, has_original_buttons=bool(getattr(message, 'reply_markup', None)))
                            ub.db.save_message_mapping(
                                task_id=task['id'],
                                source_chat_id=str(source_chat_id),
                                source_message_id=source_message_id,
                                target_chat_id=str(target_chat_id),
                                target_message_id=msg_id
                            )
                        except Exception as post_err:
                            logger.debug(f"خطأ في تطبيق إعدادات ما بعد الإرسال/حفظ التطابق: {post_err}")

                        success_count += 1
                        logger.info(f"✅ تم إرسال رسالة موافق عليها إلى {target_chat_id}")

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

    # Duplicate function removed - using the one at line 8362

    # Duplicate function removed - using the one at line 2176

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
        
        message_text = (
            f"📋 وضع النشر للمهمة: {task_name}\n\n"
            f"📊 الوضع الحالي: {status_text.get(current_mode, 'غير معروف')}\n\n"
            f"📝 شرح الأوضاع:\n"
            f"🟢 تلقائي: الرسائل تُرسل فوراً دون تدخل\n"
            f"🟡 يدوي: الرسائل تُرسل لك للمراجعة والموافقة{additional_info}"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        # Length mode display (min/max/range) - allow-only
        length_mode_map = {
            'max': 'الحد الأقصى',
            'min': 'الحد الأدنى',
            'range': 'نطاق محدد'
        }
        current_length_mode = settings.get('length_mode', 'range')
        mode_text = length_mode_map.get(current_length_mode, current_length_mode)
        
        # Values display
        values_text = ""
        if current_length_mode == 'range':
            values_text = f"من {settings.get('min_chars', 0)} إلى {settings.get('max_chars', 4000)} حرف"
        elif current_length_mode == 'max':
            values_text = f"الحد الأقصى: {settings.get('max_chars', 4000)} حرف"
        elif current_length_mode == 'min':
            values_text = f"الحد الأدنى: {settings.get('min_chars', 0)} حرف"
        
        # Buttons: enable/disable + cycle length mode (dynamic text)
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_char_limit_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع ({mode_text})", f"cycle_length_mode_{task_id}")],
        ]
        
        # Show only the relevant edit button for the current mode
        if current_length_mode == 'min':
            buttons.append([Button.inline("✏️ تعديل الحد الأدنى", f"edit_char_min_{task_id}")])
        elif current_length_mode == 'max':
            buttons.append([Button.inline("✏️ تعديل الحد الأقصى", f"edit_char_max_{task_id}")])
        else:  # range
            buttons.append([Button.inline("✏️ تعديل النطاق (مثال: 50-1000)", f"edit_char_range_{task_id}")])
        
        buttons.append([Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")])
        
        # Descriptions per length mode (allow-only semantics)
        length_mode_descriptions = {
            'min': 'يسمح فقط بالرسائل التي طولها أكبر أو يساوي الحد الأدنى',
            'max': 'يسمح فقط بالرسائل التي طولها أقل أو يساوي الحد الأقصى',
            'range': 'يسمح فقط بالرسائل التي طولها بين الحدين الأدنى والأقصى'
        }
        
        message_text = (
            f"🔢 إعدادات حد الأحرف للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⚙️ الوضع: {mode_text}\n"
            f"📏 القيم: {values_text}\n\n"
            f"📝 الوصف:\n"
            f"{length_mode_descriptions.get(current_length_mode, 'وضع غير محدد')}\n"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def toggle_character_limit(self, event, task_id):
        """Toggle character limit on/off"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        new_state = self.db.toggle_character_limit(task_id)
        
        status_text = "تم تفعيل" if new_state else "تم إلغاء تفعيل"
        await event.answer(f"✅ {status_text} حد الأحرف")
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        # Refresh display
        await self.show_character_limit_settings(event, task_id)

    async def cycle_character_limit_mode(self, event, task_id):
        """Cycle through character limit modes"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        new_mode = self.db.cycle_character_limit_mode(task_id)
        
        mode_names = {
            'allow': '✅ السماح',
            'block': '❌ الحظر'
        }
        
        await event.answer(f"✅ تم تغيير الوضع إلى: {mode_names.get(new_mode, new_mode)}")
        
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        
        # Refresh display
        await self.show_character_limit_settings(event, task_id)

    async def cycle_length_mode(self, event, task_id):
        """Cycle through length modes: max -> min -> range"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Cycle in DB
        new_length_mode = self.db.cycle_length_mode(task_id)
        length_mode_names = {
            'max': 'الحد الأقصى',
            'min': 'الحد الأدنى',
            'range': 'نطاق محدد'
        }
        await event.answer(f"✅ تم تغيير نوع الحد إلى: {length_mode_names.get(new_length_mode, new_length_mode)}")
        # Force refresh UserBot tasks
        await self._refresh_userbot_tasks(user_id)
        await self.show_character_limit_settings(event, task_id)

    async def start_edit_char_min(self, event, task_id):
        """Start editing character minimum limit"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set user state
        self.set_user_state(user_id, 'editing_char_min', {'task_id': task_id})
        
        current_settings = self.db.get_character_limit_settings(task_id)
        current_min = current_settings['min_chars']
        
        buttons = [
            [Button.inline("❌ إلغاء", f"character_limit_{task_id}")]
        ]
        
        message_text = (
            f"✏️ تعديل الحد الأدنى لعدد الأحرف\n\n"
            f"📊 القيمة الحالية: {current_min} حرف\n\n"
            f"📝 أدخل الحد الأدنى الجديد (رقم من 1 إلى 10000):\n\n"
            f"💡 مثال: 50"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_edit_char_max(self, event, task_id):
        """Start editing character maximum limit"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set user state
        self.set_user_state(user_id, 'editing_char_max', {'task_id': task_id})
        
        current_settings = self.db.get_character_limit_settings(task_id)
        current_max = current_settings['max_chars']
        
        buttons = [
            [Button.inline("❌ إلغاء", f"character_limit_{task_id}")]
        ]
        
        message_text = (
            f"✏️ تعديل الحد الأقصى لعدد الأحرف\n\n"
            f"📊 القيمة الحالية: {current_max} حرف\n\n"
            f"📝 أدخل الحد الأقصى الجديد (رقم من 1 إلى 10000):\n\n"
            f"💡 مثال: 1000"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def start_edit_character_range(self, event, task_id):
        """Start editing character range (min-max)"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Set user state
        self.set_user_state(user_id, 'editing_char_range', {'task_id': task_id})
        
        current_settings = self.db.get_character_limit_settings(task_id)
        current_min = current_settings.get('min_chars', 0)
        current_max = current_settings.get('max_chars', 4000)
        
        buttons = [
            [Button.inline("❌ إلغاء", f"character_limit_{task_id}")]
        ]
        
        message_text = (
            f"✏️ تعديل نطاق عدد الأحرف\n\n"
            f"📊 القيمة الحالية: من {current_min} إلى {current_max} حرف\n\n"
            f"📝 أدخل النطاق الجديد بصيغة 'الحد الأدنى-الحد الأقصى' (مثال: 50-1000)\n\n"
            f"💡 ملاحظة: سيتم التبديل تلقائياً إلى وضع النطاق"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        message_text = (
            f"⏱️ إعدادات تحكم المعدل للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"📈 عدد الرسائل: {limit_text} رسالة\n"
            f"⏱️ خلال: {period_text}\n\n"
            f"📝 الوصف:\n"
            f"يحدد هذا الإعداد عدد الرسائل المسموح بإرسالها خلال فترة زمنية محددة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        message_text = (
            f"⏳ إعدادات تأخير التوجيه للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⏱️ مدة التأخير: {delay_text}\n\n"
            f"📝 الوصف:\n"
            f"يضيف تأخير زمني قبل إرسال الرسائل المُوجهة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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
        
        message_text = (
            f"📊 إعدادات فترات الإرسال للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⏱️ الفترة بين الرسائل: {interval_text}\n\n"
            f"📝 الوصف:\n"
            f"يحدد الفترة الزمنية بين إرسال كل رسالة والتي تليها"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

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

    async def show_admin_list(self, event, task_id):
        """Show source list for admin filter management"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get source chat IDs for this task
        sources = self.db.get_task_sources(task_id)
        if not sources:
            await event.edit(
                f"⚠️ لا توجد مصادر للمهمة: {task_name}\n\n"
                f"يجب إضافة مصادر أولاً لعرض قائمة المشرفين",
                buttons=[[Button.inline("🔙 رجوع", f"admin_filters_{task_id}")]]
            )
            return
        
        buttons = []
        for source in sources:
            chat_id = str(source['chat_id'])
            chat_name = source['chat_name'] or f"محادثة {chat_id}"
            
            # Get admin count for this source
            source_admins = self.db.get_admin_filters_by_source(task_id, chat_id)
            admin_count = len(source_admins)
            enabled_count = len([a for a in source_admins if a['is_allowed']])
            
            button_text = f"📋 {chat_name}"
            if admin_count > 0:
                button_text += f" ({enabled_count}/{admin_count})"
            
            buttons.append([
                Button.inline(button_text, f"source_admins_{task_id}_{chat_id}")
            ])
        
        buttons.extend([
            [Button.inline("🔄 تحديث من جميع المصادر", f"refresh_all_admins_{task_id}")],
            [Button.inline("🔙 رجوع", f"admin_filters_{task_id}")]
        ])
        
        await event.edit(
            f"👥 اختر المصدر لإدارة المشرفين - {task_name}\n\n"
            f"📋 اختر مصدر لعرض قائمة المشرفين الخاصة به:\n\n"
            f"💡 كل مصدر له قائمة مشرفين منفصلة\n"
            f"📊 الأرقام تعني (المفعل/الإجمالي)",
            buttons=buttons
        )

    async def refresh_admin_list(self, event, task_id):
        """Refresh admin list"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        await event.answer("🔄 جاري تحديث قائمة المشرفين...")
        
        # Force refresh the admin list display
        await self.show_admin_list(event, task_id)

    async def handle_watermark_setting_input(self, event, task_id, setting_type):
        """Handle watermark setting input"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        message_text = event.message.text.strip()
        
        try:
            if setting_type == 'text':
                success = self.db.update_watermark_text(task_id, message_text)
                setting_name = "نص العلامة المائية"
            elif setting_type == 'position_x':
                value = int(message_text)
                success = self.db.update_watermark_position(task_id, x=value)
                setting_name = "موقع X للعلامة المائية"
            elif setting_type == 'position_y':
                value = int(message_text)
                success = self.db.update_watermark_position(task_id, y=value)
                setting_name = "موقع Y للعلامة المائية"
            else:
                await self.edit_or_send_message(event, "❌ نوع إعداد غير مدعوم")
                return
                
            if success:
                await self.edit_or_send_message(event, f"✅ تم تحديث {setting_name}")
            else:
                await self.edit_or_send_message(event, f"❌ فشل في تحديث {setting_name}")
                
        except ValueError:
            await self.edit_or_send_message(event, "❌ قيمة غير صحيحة. يرجى إدخال رقم صحيح")
        except Exception as e:
            logger.error(f"خطأ في تحديث إعداد العلامة المائية: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء التحديث")
        
        # Clear user state
        self.clear_user_state(user_id)

    async def handle_edit_character_range(self, event, task_id):
        """Handle character range input (e.g. "50-1000")"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        message_text = event.message.text.strip()
        
        try:
            parts = message_text.replace('—', '-').split('-')
            if len(parts) != 2:
                await self.edit_or_send_message(event, "❌ يرجى إدخال النطاق بصيغة '50-1000'")
                return
            min_chars = int(parts[0].strip())
            max_chars = int(parts[1].strip())
            if not (1 <= min_chars <= 10000 and 1 <= max_chars <= 10000 and min_chars <= max_chars):
                await self.edit_or_send_message(event, "❌ يرجى إدخال نطاق صحيح بين 1 و 10000 وبصيغة '50-1000'")
                return
            success = self.db.update_character_limit_settings(task_id, min_chars=min_chars, max_chars=max_chars, use_range=True, length_mode='range')
            if success:
                await self.edit_or_send_message(event, f"✅ تم تحديث النطاق إلى من {min_chars} إلى {max_chars} حرف")
                await self._refresh_userbot_tasks(user_id)
            else:
                await self.edit_or_send_message(event, "❌ فشل في تحديث النطاق")
        except Exception as e:
            logger.error(f"خطأ في تحديث نطاق حد الأحرف: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء التحديث")
        
        # Clear user state
        self.clear_user_state(user_id)

    async def handle_edit_rate_count(self, event, task_id, message_text=None):
        """Handle rate count input"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        if message_text is None:
            message_text = event.message.text.strip()
        else:
            message_text = message_text.strip()
        
        try:
            value = int(message_text)
            if value < 1 or value > 1000:
                await self.edit_or_send_message(event, "❌ يجب أن يكون العدد بين 1 و 1000")
                return
                
            success = self.db.update_rate_limit_settings(task_id, message_count=value)
            
            if success:
                # Show success message with back button
                buttons = [
                    [Button.inline("🔙 رجوع لإعدادات حد المعدل", f"rate_limit_{task_id}")]
                ]
                await self.edit_or_send_message(event, 
                    f"✅ تم تحديث عدد الرسائل المسموحة بنجاح!\n\n"
                    f"📊 العدد الجديد: {value} رسالة\n"
                    f"🎯 المهمة: {task.get('task_name', 'مهمة بدون اسم')}",
                    buttons=buttons
                )
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
            else:
                await self.edit_or_send_message(event, "❌ فشل في تحديث عدد الرسائل")
                
        except ValueError:
            await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
        except Exception as e:
            logger.error(f"خطأ في تحديث عدد الرسائل: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء التحديث")
        
        # Clear user state
        self.clear_user_state(user_id)

    async def handle_edit_rate_period(self, event, task_id, message_text=None):
        """Handle rate period input"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        if message_text is None:
            message_text = event.message.text.strip()
        else:
            message_text = message_text.strip()
        
        try:
            value = int(message_text)
            if value < 1 or value > 3600:
                await self.edit_or_send_message(event, "❌ يجب أن تكون الفترة بين 1 و 3600 ثانية")
                return
                
            success = self.db.update_rate_limit_settings(task_id, time_period_seconds=value)
            
            if success:
                # Show success message with back button
                period_minutes = value // 60 if value >= 60 else 0
                period_display = f"{period_minutes} دقيقة" if period_minutes > 0 else f"{value} ثانية"
                
                buttons = [
                    [Button.inline("🔙 رجوع لإعدادات حد المعدل", f"rate_limit_{task_id}")]
                ]
                await self.edit_or_send_message(event, 
                    f"✅ تم تحديث فترة التحكم بالمعدل بنجاح!\n\n"
                    f"⏰ الفترة الجديدة: {period_display}\n"
                    f"🎯 المهمة: {task.get('task_name', 'مهمة بدون اسم')}",
                    buttons=buttons
                )
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
            else:
                await self.edit_or_send_message(event, "❌ فشل في تحديث فترة التحكم")
                
        except ValueError:
            await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
        except Exception as e:
            logger.error(f"خطأ في تحديث فترة التحكم: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء التحديث")
        
        # Clear user state
        self.clear_user_state(user_id)

    async def handle_edit_forwarding_delay(self, event, task_id, message_text=None):
        """Handle forwarding delay input"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        if message_text is None:
            message_text = event.message.text.strip()
        else:
            message_text = message_text.strip()
        
        try:
            value = int(message_text)
            if value < 0 or value > 300:
                await self.edit_or_send_message(event, "❌ يجب أن يكون التأخير بين 0 و 300 ثانية")
                return
                
            success = self.db.update_forwarding_delay_settings(task_id, delay_seconds=value)
            
            if success:
                await self.edit_or_send_message(event, f"✅ تم تحديث تأخير التوجيه إلى {value} ثانية")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
            else:
                await self.edit_or_send_message(event, "❌ فشل في تحديث تأخير التوجيه")
                
        except ValueError:
            await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
        except Exception as e:
            logger.error(f"خطأ في تحديث تأخير التوجيه: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء التحديث")
        
        # Clear user state
        self.clear_user_state(user_id)

    async def handle_edit_sending_interval(self, event, task_id, message_text=None):
        """Handle sending interval input"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        if message_text is None:
            message_text = event.message.text.strip()
        else:
            message_text = message_text.strip()
        
        try:
            value = int(message_text)
            if value < 0 or value > 60:
                await self.edit_or_send_message(event, "❌ يجب أن يكون الفاصل بين 0 و 60 ثانية")
                return
                
            success = self.db.update_sending_interval_settings(task_id, interval_seconds=value)
            
            if success:
                await self.edit_or_send_message(event, f"✅ تم تحديث فاصل الإرسال إلى {value} ثانية")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
            else:
                await self.edit_or_send_message(event, "❌ فشل في تحديث فاصل الإرسال")
                
        except ValueError:
            await self.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
        except Exception as e:
            logger.error(f"خطأ في تحديث فترة الإرسال: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء التحديث")
        
        # Clear user state
        self.clear_user_state(user_id)

    async def handle_set_working_hours(self, event, task_id):
        """Handle working hours input"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.respond("❌ المهمة غير موجودة")
            return
            
        message_text = event.message.text.strip()
        
        try:
            # Parse hours range (e.g., "9-17" or "9:00-17:30")
            if '-' in message_text:
                start_str, end_str = message_text.split('-', 1)
                start_hour = int(start_str.strip().split(':')[0])
                end_hour = int(end_str.strip().split(':')[0])
                
                if start_hour < 0 or start_hour > 23 or end_hour < 0 or end_hour > 23:
                    await event.respond("❌ الساعات يجب أن تكون بين 0-23")
                    return
                    
                success = self.db.set_working_hours_range(task_id, start_hour, end_hour)
                
                if success:
                    await event.respond(f"✅ تم تحديث ساعات العمل من {start_hour}:00 إلى {end_hour}:00")
                else:
                    await event.respond("❌ فشل في تحديث ساعات العمل")
            else:
                await event.respond("❌ تنسيق غير صحيح. استخدم تنسيق مثل: 9-17")
                
        except ValueError:
            await event.respond("❌ تنسيق غير صحيح. استخدم تنسيق مثل: 9-17")
        except Exception as e:
            logger.error(f"خطأ في تحديث ساعات العمل: {e}")
            await event.respond("❌ حدث خطأ أثناء التحديث")
        
        # Clear user state
        self.clear_user_state(user_id)

    async def handle_add_language_filter(self, event, task_id):
        """Handle adding language filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        message_text = event.text.strip()
        
        try:
            # Parse language input (e.g., "en English" or "ar العربية")
            parts = message_text.split(' ', 1)
            if len(parts) != 2:
                await self.edit_or_send_message(event, 
                    "❌ تنسيق غير صحيح\n\n"
                    "📝 استخدم التنسيق: `[كود اللغة] [اسم اللغة]`\n"
                    "مثال: `en English` أو `ar العربية`"
                )
                return
            
            language_code = parts[0].strip().lower()
            language_name = parts[1].strip()
            
            # Validate language code (2-3 characters)
            if not (2 <= len(language_code) <= 3):
                await self.edit_or_send_message(event, 
                    "❌ كود اللغة غير صحيح\n\n"
                    "📝 كود اللغة يجب أن يكون من 2-3 أحرف\n"
                    "مثال: `en`, `ar`, `fr`"
                )
                return
            
            # Add language filter
            success = self.db.add_language_filter(task_id, language_code, language_name, True)
            
            if success:
                # Clear conversation state
                self.db.clear_conversation_state(user_id)
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Show success message
                await self.edit_or_send_message(event, 
                    f"✅ تم إضافة اللغة بنجاح!\n\n"
                    f"🌍 اللغة: {language_name}\n"
                    f"🔤 الكود: {language_code.upper()}\n"
                    f"📊 الحالة: 🟢 مفعلة"
                )
                
                # Refresh language management after brief delay
                import asyncio
                await asyncio.sleep(1.5)
                await self.show_language_management(event, task_id)
            else:
                await self.edit_or_send_message(event, "❌ فشل في إضافة اللغة")
                
        except Exception as e:
            logger.error(f"خطأ في إضافة فلتر اللغة: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء الإضافة")
            
        # Clear conversation state
        self.db.clear_conversation_state(user_id)

    async def toggle_language_mode(self, event, task_id):
        """Toggle language filter mode between allow and block"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current mode and toggle it
        current_mode = self.db.get_language_filter_mode(task_id)
        new_mode = 'block' if current_mode == 'allow' else 'allow'
        
        success = self.db.set_language_filter_mode(task_id, new_mode)
        
        if success:
            mode_names = {
                'allow': 'السماح فقط للغات المحددة',
                'block': 'حظر اللغات المحددة'
            }
            await event.answer(f"✅ تم تغيير وضع الفلتر إلى: {mode_names[new_mode]}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Refresh the language filters display
            await self.show_language_filters(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير وضع الفلتر")

    async def toggle_admin(self, event, task_id, admin_id, source_chat_id=None):
        """Toggle admin filter status"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Toggle admin filter status
        success = self.db.toggle_admin_filter(task_id, int(admin_id))
        
        if success:
            await event.answer("✅ تم تحديث إعدادات المشرف")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Refresh the appropriate admin list display
            if source_chat_id:
                await self.show_source_admins(event, task_id, source_chat_id)
            else:
                await self.show_admin_list(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث إعدادات المشرف")

    async def toggle_language_filter(self, event, task_id, language_code):
        """Toggle specific language filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Toggle language filter status
        success = self.db.toggle_language_filter(task_id, language_code)
        
        if success:
            await event.answer(f"✅ تم تحديث فلتر اللغة {language_code}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Refresh the language filters display
            await self.show_language_filters(event, task_id)
        else:
            await event.answer("❌ فشل في تحديث فلتر اللغة")

    async def toggle_button_mode(self, event, task_id):
        """Toggle button filter mode"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current mode and toggle it
        current_settings = self.db.get_button_filter_settings(task_id)
        current_mode = current_settings.get('action_mode', 'remove_buttons')
        new_mode = 'block_message' if current_mode == 'remove_buttons' else 'remove_buttons'
        
        success = self.db.set_button_filter_mode(task_id, new_mode)
        
        if success:
            mode_names = {
                'remove_buttons': 'حذف الأزرار',
                'block_message': 'حظر الرسالة'
            }
            await event.answer(f"✅ تم تغيير الوضع إلى: {mode_names[new_mode]}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Refresh the button filters display
            await self.show_button_filters(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير الوضع")

    async def toggle_forwarded_mode(self, event, task_id):
        """Toggle forwarded message filter mode"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current mode and toggle it
        current_settings = self.db.get_forwarded_filter_settings(task_id)
        current_mode = current_settings.get('mode', 'allow')
        new_mode = 'block' if current_mode == 'allow' else 'allow'
        
        success = self.db.set_forwarded_filter_mode(task_id, new_mode)
        
        if success:
            mode_names = {
                'allow': 'السماح بالرسائل المُوجهة',
                'block': 'حظر الرسائل المُوجهة'
            }
            await event.answer(f"✅ تم تغيير الوضع إلى: {mode_names[new_mode]}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Refresh the forwarded message filter display
            await self.show_forwarded_message_filter(event, task_id)
        else:
            await event.answer("❌ فشل في تغيير الوضع")

    async def toggle_duplicate_mode(self, event, task_id):
        """Toggle duplicate filter mode"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        # Get current settings and toggle repeat mode
        current_settings = self.db.get_duplicate_settings(task_id)
        current_repeat_mode = current_settings.get('repeat_mode_enabled', False)
        new_repeat_mode = not current_repeat_mode
        
        success = self.db.set_duplicate_settings(task_id, repeat_mode_enabled=new_repeat_mode)
        
        if success:
            mode_text = "تفعيل وضع التكرار" if new_repeat_mode else "تعطيل وضع التكرار"
            await event.answer(f"✅ تم {mode_text}")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Refresh the duplicate filter display
            try:
                await self.show_duplicate_filter(event, task_id)
            except Exception as e:
                if "Content of the message was not modified" not in str(e):
                    raise e
                logger.debug("المحتوى لم يتغير، وضع التكرار محدث بنجاح")
        else:
            await event.answer("❌ فشل في تغيير وضع التكرار")

    async def toggle_hour(self, event, task_id, hour):
        """Toggle specific hour in working hours schedule"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get current working hours
            current_settings = self.db.get_working_hours(task_id)
            schedule = current_settings.get('schedule', {})
            
            # Toggle the hour using database function directly
            new_state = self.db.toggle_working_hour(task_id, hour)
            success = True
            
            action = "تم تفعيل" if new_state else "تم تعطيل"
            await event.answer(f"✅ {action} الساعة {hour:02d}:00")
            
            # Force refresh UserBot tasks
            await self._refresh_userbot_tasks(user_id)
            
            # Force refresh by editing with updated content and timestamp
            try:
                await self.show_working_hours_schedule(event, task_id)
            except Exception as e:
                if "Content of the message was not modified" not in str(e):
                    raise e
                # If content unchanged, just answer user
                logger.debug("المحتوى لم يتغير، نص الساعة محدث بنجاح")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل الساعة {hour} للمهمة {task_id}: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    def _get_bot_token(self):
        """Get BOT_TOKEN from various sources"""
        try:
            # Try to import from config.py
            from config import BOT_TOKEN
            return BOT_TOKEN
        except ImportError:
            # Try to get from environment
            import os
            BOT_TOKEN = os.getenv('BOT_TOKEN')
            if BOT_TOKEN:
                return BOT_TOKEN
            
            # Try to get from userbot instance
            try:
                from userbot_service.userbot import userbot_instance
                if hasattr(userbot_instance, 'bot_token'):
                    return userbot_instance.bot_token
            except:
                pass
            
            return None

    async def show_source_admins(self, event, task_id, source_chat_id):
        """Show admins for a specific source chat"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get admins from UserBot
            from userbot_service.userbot import userbot_instance
            if user_id not in userbot_instance.clients:
                await event.answer("❌ UserBot غير متصل")
                return
                
            # Get chat admins
            client = userbot_instance.clients[user_id]
            try:
                from telethon.tl.types import ChannelParticipantsAdmins
                
                # First get from database (cached) with statistics
                admin_data = self.db.get_admin_filters_by_source_with_stats(task_id, str(source_chat_id))
                cached_admins = admin_data['admins']
                stats = admin_data['stats']
                
                # Get source name
                sources = self.db.get_task_sources(task_id)
                source_name = next((s['chat_name'] for s in sources if str(s['chat_id']) == str(source_chat_id)), f"محادثة {source_chat_id}")
                
                if not cached_admins:
                    # If no cached admins, try to fetch from Telegram using UserBot's event loop
                    await event.edit(f"🔄 جاري جلب المشرفين من {source_name}...")
                    
                    # Use Bot API to get admins instead of UserBot
                    from config import BOT_TOKEN
                    admins_data = userbot_instance.get_channel_admins_via_bot(BOT_TOKEN, int(source_chat_id))
                    
                    if admins_data:
                        logger.info(f"📋 تم جلب {len(admins_data)} مشرف من التليجرام للمصدر {source_chat_id}")
                        
                        # Clear existing admins for this source first
                        self.db.clear_admin_filters_for_source(task_id, str(source_chat_id))
                        logger.info(f"🗑️ تم حذف المشرفين السابقين للمصدر {source_chat_id}")
                        
                        # Save to database
                        saved_count = 0
                        for admin_data_item in admins_data:
                            try:
                                self.db.add_admin_filter(
                                    task_id, 
                                    admin_data_item['id'], 
                                    admin_data_item.get('username'),
                                    admin_data_item.get('first_name', ''),
                                    True,  # Default allow
                                    str(source_chat_id),
                                    admin_data_item.get('custom_title', '')  # Save admin signature
                                )
                                saved_count += 1
                                logger.debug(f"✅ تم حفظ المشرف: {admin_data_item.get('first_name', 'Unknown')} (ID: {admin_data_item['id']})")
                            except Exception as e:
                                logger.error(f"❌ خطأ في حفظ المشرف {admin_data_item.get('first_name', 'Unknown')}: {e}")
                        
                        logger.info(f"💾 تم حفظ {saved_count} من {len(admins_data)} مشرف في قاعدة البيانات")
                        
                        # Reload from database
                        admin_data = self.db.get_admin_filters_by_source_with_stats(task_id, str(source_chat_id))
                        cached_admins = admin_data['admins']
                        stats = admin_data['stats']
                        logger.info(f"📊 تم تحميل {len(cached_admins)} مشرف من قاعدة البيانات")
                
                if not cached_admins:
                    await event.edit(
                        f"⚠️ لا يوجد مشرفين في {source_name}\n\n"
                        f"💡 تأكد من أن المصدر قناة أو مجموعة عامة وأنك عضو فيها",
                        buttons=[[Button.inline("🔙 رجوع", f"admin_list_{task_id}")]]
                    )
                    return
                
                # Create buttons for ALL admins without arbitrary limits
                buttons = []
                logger.info(f"📋 عرض جميع الـ {len(cached_admins)} مشرف للمصدر {source_chat_id}")
                
                # Show ALL admins, no arbitrary limits
                for admin in cached_admins:
                    is_allowed = admin['is_allowed']
                    icon = "✅" if is_allowed else "❌"
                    
                    name = admin['admin_first_name'] or admin['admin_username'] or f"User {admin['admin_user_id']}"
                    admin_signature = admin.get('admin_signature', '')
                    
                    # Add signature info if available
                    if admin_signature:
                        name = f"{name} ({admin_signature})"
                    
                    # Truncate if too long for button
                    if len(name) > 30:
                        name = name[:27] + "..."
                        
                    button_text = f"{icon} {name}"
                    
                    buttons.append([Button.inline(
                        button_text, 
                        f"toggle_source_admin_{task_id}_{admin['admin_user_id']}_{source_chat_id}"
                    )])
                
                # Show all admins without arbitrary limits - Telegram has reasonable built-in limits
                total_admins = len(cached_admins)
                max_buttons_per_message = 100  # Telegram's actual limit
                
                if total_admins > max_buttons_per_message:
                    logger.warning(f"📄 عدد المشرفين كبير جداً ({total_admins}), قد تحتاج لتحديث الواجهة")
                    # Note: Keep all buttons - Telegram will handle the limit gracefully
                    logger.info(f"📊 عرض جميع الـ {total_admins} مشرف (تحت حد التليجرام)")
                else:
                    logger.info(f"📊 عرض جميع الـ {total_admins} مشرف")
                
                # Add control buttons
                buttons.extend([
                    [
                        Button.inline("🔄 تحديث من التليجرام", f"refresh_source_admins_{task_id}_{source_chat_id}"),
                        Button.inline("✅ تفعيل الكل", f"enable_all_source_admins_{task_id}_{source_chat_id}")
                    ],
                    [
                        Button.inline("❌ تعطيل الكل", f"disable_all_source_admins_{task_id}_{source_chat_id}"),
                        Button.inline("✏️ إدارة التوقيعات", f"manage_signatures_{task_id}_{source_chat_id}")
                    ],
                    [
                        Button.inline("🔙 رجوع", f"admin_list_{task_id}")
                    ]
                ])
                
                # Use stats from database
                enabled_count = stats['allowed']
                total_count = stats['total']
                
                await event.edit(
                    f"👥 مشرفو المصدر: {source_name}\n\n"
                    f"📊 المفعل: {enabled_count} من أصل {total_count}\n"
                    f"✅ مفعل - سيتم قبول رسائل هذا المشرف\n"
                    f"❌ معطل - سيتم تجاهل رسائل هذا المشرف\n\n"
                    f"💡 فقط رسائل المشرفين المفعلين ستمر عبر الفلتر\n"
                    f"🔍 يتم الفلترة حسب توقيع المشرف (post_author)",
                    buttons=buttons
                )
                
            except Exception as e:
                logger.error(f"خطأ في جلب مشرفي المصدر {source_chat_id}: {e}")
                await event.edit(
                    f"❌ فشل في جلب قائمة المشرفين من {source_name}\n\n"
                    f"الخطأ: {str(e)}\n\n"
                    f"💡 تأكد من أن المصدر قناة وأنك عضو فيها",
                    buttons=[[Button.inline("🔙 رجوع", f"admin_list_{task_id}")]]
                )
                
        except Exception as e:
            logger.error(f"خطأ في عرض مشرفي المصدر: {e}")
            await event.answer("❌ حدث خطأ")

    async def toggle_source_admin_filter(self, event, task_id, admin_user_id, source_chat_id):
        """Toggle admin filter for specific source"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Toggle admin filter
            success = self.db.toggle_admin_filter(task_id, admin_user_id, source_chat_id)
            
            if success:
                # Check new state
                admin_filters = self.db.get_admin_filters_by_source(task_id, source_chat_id)
                admin_filter = next((af for af in admin_filters if af['admin_user_id'] == admin_user_id), None)
                
                if admin_filter:
                    status = "تم تفعيل" if admin_filter['is_allowed'] else "تم تعطيل"
                    admin_name = admin_filter['admin_first_name'] or admin_filter['admin_username'] or f"User {admin_user_id}"
                    await event.answer(f"✅ {status} المشرف {admin_name}")
                else:
                    await event.answer("❌ لم يتم العثور على المشرف")
                
                # Refresh the display
                await self.show_source_admins(event, task_id, source_chat_id)
            else:
                await event.answer("❌ فشل في تحديث إعدادات المشرف")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل فلتر المشرف {admin_user_id}: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def refresh_source_admins(self, event, task_id, source_chat_id):
        """Refresh admin list for specific source from Telegram"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get admins from UserBot
            from userbot_service.userbot import userbot_instance
            if user_id not in userbot_instance.clients:
                await event.answer("❌ UserBot غير متصل")
                return
                
            await event.edit("🔄 جاري تحديث قائمة المشرفين من التليجرام...")
            
            client = userbot_instance.clients[user_id]
            
            # Get previous permissions to preserve them
            existing_admins = self.db.get_admin_filters_by_source(task_id, source_chat_id)
            previous_permissions = {admin['admin_user_id']: admin['is_allowed'] for admin in existing_admins}
            
            # Clear existing entries for this source
            self.db.clear_admin_filters_for_source(task_id, source_chat_id)
            
            # Use Bot API to get admins instead of UserBot
            BOT_TOKEN = self._get_bot_token()
            if not BOT_TOKEN:
                await event.edit(
                    f"❌ لا يمكن العثور على BOT_TOKEN\n\n"
                    f"💡 تأكد من إعداد BOT_TOKEN في ملف config.py أو متغير البيئة",
                    buttons=[[Button.inline("🔙 رجوع", f"source_admins_{task_id}_{source_chat_id}")]]
                )
                return
            
            admins_data = userbot_instance.get_channel_admins_via_bot(BOT_TOKEN, int(source_chat_id))
            
            if admins_data:
                # Save new admins with preserved permissions
                for admin_data in admins_data:
                    # Use previous permission if exists, otherwise default to True
                    is_allowed = previous_permissions.get(admin_data['id'], True)
                        
                    self.db.add_admin_filter(
                        task_id, 
                        admin_data['id'], 
                        admin_data.get('username'),
                        admin_data.get('first_name', ''),
                        is_allowed,
                        str(source_chat_id),
                        admin_data.get('custom_title', '')  # Save admin signature
                    )
            
                await event.answer(f"✅ تم تحديث {len(admins_data)} مشرف")
            else:
                await event.answer("❌ فشل في جلب المشرفين من التليجرام")
            
            # Refresh the display
            await self.show_source_admins(event, task_id, source_chat_id)
            
        except Exception as e:
            logger.error(f"خطأ في تحديث مشرفي المصدر {source_chat_id}: {e}")
            # Handle "Content of the message was not modified" error - this is actually success
            if "Content of the message was not modified" in str(e):
                logger.info(f"✅ المشرفين محدثين بالفعل للمصدر {source_chat_id}")
                await event.answer("✅ تم تحديث المشرفين بنجاح", alert=False)
                # Always try to refresh display even if content wasn't modified
                try:
                    await self.show_source_admins(event, task_id, source_chat_id)
                except Exception as refresh_error:
                    if "Content of the message was not modified" in str(refresh_error):
                        # If even the refresh shows no changes, just acknowledge success
                        logger.info("✅ لا توجد تغييرات في قائمة المشرفين")
                    else:
                        logger.error(f"خطأ في تحديث العرض: {refresh_error}")
            else:
                # Real error occurred
                try:
                    await event.edit(
                        f"❌ فشل في جلب قائمة المشرفين\n\n"
                        f"الخطأ: {str(e)}\n\n"
                        f"💡 تأكد من أن المصدر قناة وأنك عضو فيها",
                        buttons=[[Button.inline("🔙 رجوع", f"source_admins_{task_id}_{source_chat_id}")]]
                    )
                except Exception as edit_error:
                    logger.error(f"خطأ في تحديث رسالة الخطأ: {edit_error}")
                    await event.answer(f"❌ خطأ: {str(e)}", alert=True)

    async def refresh_all_admins(self, event, task_id):
        """Refresh admin lists for all sources"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get all sources for this task
            sources = self.db.get_task_sources(task_id)
            if not sources:
                await event.answer("❌ لا توجد مصادر للمهمة")
                return
                
            await event.edit("🔄 جاري تحديث قوائم المشرفين لجميع المصادر...")
            
            total_updated = 0
            failed_sources = []
            
            for source in sources:
                source_chat_id = str(source['chat_id'])
                source_name = source['chat_name'] or f"محادثة {source_chat_id}"
                
                try:
                    # Call refresh for each source without UI updates
                    from userbot_service.userbot import userbot_instance
                    if user_id not in userbot_instance.clients:
                        continue
                        
                    client = userbot_instance.clients[user_id]
                    
                    # Get previous permissions
                    existing_admins = self.db.get_admin_filters_by_source(task_id, source_chat_id)
                    previous_permissions = {admin['admin_user_id']: admin['is_allowed'] for admin in existing_admins}
                    
                    # Clear existing entries for this source
                    self.db.clear_admin_filters_for_source(task_id, source_chat_id)
                    
                    # Use Bot API to get admins instead of UserBot
                    BOT_TOKEN = self._get_bot_token()
                    if not BOT_TOKEN:
                        logger.error(f"لا يمكن العثور على BOT_TOKEN للمصدر {source_chat_id}")
                        continue
                    
                    admins_data = userbot_instance.get_channel_admins_via_bot(BOT_TOKEN, int(source_chat_id))
                    
                    if admins_data:
                        # Save new admins
                        for admin_data in admins_data:
                            is_allowed = previous_permissions.get(admin_data['id'], True)
                                
                            self.db.add_admin_filter(
                                task_id, 
                                admin_data['id'], 
                                admin_data.get('username'),
                                admin_data.get('first_name', ''),
                                is_allowed,
                                source_chat_id,
                                admin_data.get('admin_signature', '')  # Save admin signature
                            )
                        
                        total_updated += len(admins_data)
                    
                except Exception as e:
                    logger.error(f"خطأ في تحديث مشرفي {source_name}: {e}")
                    failed_sources.append(source_name)
            
            # Show results
            message = f"✅ تم تحديث {total_updated} مشرف من {len(sources)} مصادر"
            if failed_sources:
                message += f"\n\n❌ فشل التحديث من: {', '.join(failed_sources)}"
            
            await event.answer(message)
            
            # Refresh the main admin list display
            await self.show_admin_list(event, task_id)
            
        except Exception as e:
            logger.error(f"خطأ في تحديث جميع المشرفين: {e}")
            # Handle "Content of the message was not modified" error
            if "Content of the message was not modified" in str(e):
                await event.answer("✅ تم تحديث جميع المشرفين بنجاح")
                # Refresh the main admin list display
                await self.show_admin_list(event, task_id)
            else:
                try:
                    await event.answer(f"❌ خطأ: {str(e)}")
                except:
                    await event.answer(f"❌ خطأ: {str(e)}")

    async def enable_all_source_admins(self, event, task_id, source_chat_id):
        """Enable all admins for specific source"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get all admins for this source
            admins = self.db.get_admin_filters_by_source(task_id, source_chat_id)
            if not admins:
                await event.answer("❌ لا يوجد مشرفين في هذا المصدر")
                return
            
            # Create permissions dict for bulk update
            admin_permissions = {admin['admin_user_id']: True for admin in admins}
            
            # Bulk update all admins to allowed
            updated_count = self.db.bulk_update_admin_permissions(task_id, source_chat_id, admin_permissions)
                
            await event.answer(f"✅ تم تفعيل {updated_count} مشرف")
            
            # Refresh the display
            await self.show_source_admins(event, task_id, source_chat_id)
            
        except Exception as e:
            logger.error(f"خطأ في تفعيل جميع المشرفين: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def disable_all_source_admins(self, event, task_id, source_chat_id):
        """Disable all admins for specific source"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get all admins for this source
            admins = self.db.get_admin_filters_by_source(task_id, source_chat_id)
            if not admins:
                await event.answer("❌ لا يوجد مشرفين في هذا المصدر")
                return
            
            # Create permissions dict for bulk update
            admin_permissions = {admin['admin_user_id']: False for admin in admins}
            
            # Bulk update all admins to blocked
            updated_count = self.db.bulk_update_admin_permissions(task_id, source_chat_id, admin_permissions)
                
            await event.answer(f"❌ تم تعطيل {updated_count} مشرف")
            
            # Refresh the display
            await self.show_source_admins(event, task_id, source_chat_id)
            
        except Exception as e:
            logger.error(f"خطأ في تعطيل جميع المشرفين: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def refresh_source_admin_list(self, event, task_id, source_chat_id):
        """Refresh the admin list for a source"""
        await self.show_source_admins(event, task_id, source_chat_id)

    async def manage_admin_signatures(self, event, task_id, source_chat_id):
        """Manage admin signatures for a specific source"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get admins with their signatures
            admins = self.db.get_admin_filters_by_source(task_id, source_chat_id)
            if not admins:
                await event.answer("❌ لا يوجد مشرفين في هذا المصدر")
                return
            
            # Get source name
            sources = self.db.get_task_sources(task_id)
            source_name = next((s['chat_name'] for s in sources if str(s['chat_id']) == str(source_chat_id)), f"محادثة {source_chat_id}")
            
            # Create buttons for signature management
            buttons = []
            for admin in admins:
                admin_name = admin['admin_first_name'] or admin['admin_username'] or f"User {admin['admin_user_id']}"
                admin_signature = admin.get('admin_signature', '')
                
                # Truncate if too long for button
                if len(admin_name) > 25:
                    admin_name = admin_name[:22] + "..."
                
                if admin_signature:
                    button_text = f"✏️ {admin_name} ({admin_signature})"
                else:
                    button_text = f"➕ {admin_name} (بدون توقيع)"
                
                buttons.append([Button.inline(
                    button_text, 
                    f"edit_admin_signature_{task_id}_{admin['admin_user_id']}_{source_chat_id}"
                )])
            
            # Add control buttons
            buttons.extend([
                [Button.inline("🔄 تحديث من التليجرام", f"refresh_source_admins_{task_id}_{source_chat_id}")],
                [Button.inline("🔙 رجوع", f"source_admins_{task_id}_{source_chat_id}")]
            ])
            
            await event.edit(
                f"✏️ إدارة توقيعات المشرفين - {source_name}\n\n"
                f"📝 التوقيع هو الاسم الذي يظهر في رسائل المشرف\n"
                f"🔍 يتم استخدامه لفلترة الرسائل حسب المؤلف\n\n"
                f"💡 اضغط على المشرف لتعديل توقيعه",
                buttons=buttons
            )
            
        except Exception as e:
            logger.error(f"خطأ في إدارة توقيعات المشرفين: {e}")
            await event.answer("❌ حدث خطأ")

    async def edit_admin_signature(self, event, task_id, admin_user_id, source_chat_id):
        """Edit admin signature"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get admin info
            admin = self.db.get_admin_filter_setting(task_id, admin_user_id)
            if not admin:
                await event.answer("❌ المشرف غير موجود")
                return
            
            admin_name = admin['admin_first_name'] or admin['admin_username'] or f"User {admin_user_id}"
            current_signature = admin.get('admin_signature', '')
            
            # Set user state for signature input
            self.set_user_state(user_id, f"edit_signature_{task_id}_{admin_user_id}", {'source_chat_id': source_chat_id})
            
            buttons = [[Button.inline("🔙 رجوع", f"manage_signatures_{task_id}_{source_chat_id}")]]
            
            if current_signature:
                message = (
                    f"✏️ تعديل توقيع المشرف: {admin_name}\n\n"
                    f"📝 التوقيع الحالي: {current_signature}\n\n"
                    f"💬 أرسل التوقيع الجديد أو 'حذف' لحذف التوقيع"
                )
            else:
                message = (
                    f"✏️ إضافة توقيع للمشرف: {admin_name}\n\n"
                    f"💬 أرسل التوقيع الجديد"
                )
            
            await event.edit(message, buttons=buttons)
            
        except Exception as e:
            logger.error(f"خطأ في تعديل توقيع المشرف: {e}")
            await event.answer("❌ حدث خطأ")

    async def handle_signature_input(self, event, task_id, admin_user_id, source_chat_id):
        """Handle admin signature input"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        message_text = event.message.text.strip()
        
        try:
            if message_text.lower() == 'حذف':
                # Remove signature
                success = self.db.update_admin_signature(task_id, admin_user_id, source_chat_id, '')
                if success:
                    await self.edit_or_send_message(event, "✅ تم حذف توقيع المشرف")
                else:
                    await self.edit_or_send_message(event, "❌ فشل في حذف التوقيع")
            else:
                # Update signature
                success = self.db.update_admin_signature(task_id, admin_user_id, source_chat_id, message_text)
                if success:
                    await self.edit_or_send_message(event, f"✅ تم تحديث توقيع المشرف إلى: {message_text}")
                else:
                    await self.edit_or_send_message(event, "❌ فشل في تحديث التوقيع")
            
            # Clear user state
            self.clear_user_state(user_id)
            
            # Return to signature management
            await self.manage_admin_signatures(event, task_id, source_chat_id)
            
        except Exception as e:
            logger.error(f"خطأ في معالجة توقيع المشرف: {e}")
            await self.edit_or_send_message(event, "❌ حدث خطأ أثناء التحديث")
            self.clear_user_state(user_id)

    # Duplicate function removed - using the one at line 9137

    async def toggle_language(self, event, task_id, language_code):
        """Toggle specific language in language filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get current language filters
            language_filters = self.db.get_language_filters(task_id)
            is_selected = any(lf['language_code'] == language_code for lf in language_filters)
            
            if is_selected:
                # Remove language
                success = self.db.remove_language_filter(task_id, language_code)
                action = "تم إلغاء تحديد"
            else:
                # Add language
                success = self.db.add_language_filter(task_id, language_code)
                action = "تم تحديد"
            
            if success:
                language_names = {
                    'ar': 'العربية', 'en': 'الإنجليزية', 'es': 'الإسبانية',
                    'fr': 'الفرنسية', 'de': 'الألمانية', 'ru': 'الروسية',
                    'tr': 'التركية', 'fa': 'الفارسية', 'ur': 'الأردية'
                }
                lang_name = language_names.get(language_code, language_code)
                await event.answer(f"✅ {action} {lang_name}")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the language filter display
                try:
                    await self.show_language_filter(event, task_id)
                except Exception as e:
                    if "Content of the message was not modified" not in str(e):
                        raise e
                    logger.debug("المحتوى لم يتغير، اللغة محدثة بنجاح")
            else:
                await event.answer("❌ فشل في تحديث اللغة")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل فلتر اللغة {language_code}: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    # Duplicate function removed - using the one at line 9107

    async def toggle_forwarding_filter_mode(self, event, task_id):
        """Toggle forwarding filter mode"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get current setting and toggle
            current_setting = self.db.get_forwarded_message_filter_setting(task_id)
            new_setting = not current_setting
            
            success = self.db.set_forwarded_message_filter(task_id, new_setting)
            
            if success:
                action = "تم تفعيل" if new_setting else "تم تعطيل"
                await event.answer(f"✅ {action} فلتر الرسائل المُعاد توجيهها")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the filter display
                try:
                    await self.show_forwarded_filter(event, task_id)
                except Exception as e:
                    if "Content of the message was not modified" not in str(e):
                        raise e
                    logger.debug("المحتوى لم يتغير، فلتر التوجيه محدث بنجاح")
            else:
                await event.answer("❌ فشل في تغيير الفلتر")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل فلتر الرسائل المُعاد توجيهها: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def toggle_transparent_button_filter(self, event, task_id):
        """Toggle transparent button filter"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get current setting and toggle
            current_setting = self.db.get_inline_button_filter_setting(task_id)
            new_setting = not current_setting
            
            success = self.db.set_inline_button_filter(task_id, new_setting)
            
            if success:
                action = "تم تفعيل" if new_setting else "تم تعطيل"
                await event.answer(f"✅ {action} فلتر الأزرار الشفافة")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the filter display - use generic filter menu
                try:
                    await self.show_advanced_filters(event, task_id)
                except Exception as e:
                    if "Content of the message was not modified" not in str(e):
                        raise e
                    logger.debug("المحتوى لم يتغير، فلتر الأزرار الشفافة محدث بنجاح")
            else:
                await event.answer("❌ فشل في تغيير الفلتر")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل فلتر الأزرار الشفافة: {e}")
            await event.answer("❌ حدث خطأ في التحديث")
    
    async def show_inline_button_filter(self, event, task_id):
        """Show inline button filter settings for specific callback"""
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
        
        # Add timestamp to force UI refresh
        import time
        timestamp = int(time.time()) % 100
        
        try:
            await event.edit(
                f"🔘 فلتر الأزرار الإنلاين - المهمة #{task_id}\n\n"
                f"📊 الحالة: {status_text}\n"
                f"⚙️ الوضع: {mode_text}\n\n"
                f"💡 هذا الفلتر يتحكم في الرسائل التي تحتوي على أزرار إنلاين\n"
                f"⏰ آخر تحديث: {timestamp}",
                buttons=buttons
            )
        except Exception as e:
            if "Content of the message was not modified" not in str(e):
                raise e
            logger.debug("المحتوى لم يتغير، فلتر الأزرار الإنلاين محدث بنجاح")
    
    async def show_forwarded_message_filter(self, event, task_id):
        """Show forwarded message filter settings for specific callback"""
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
        mode_text = "حظر الرسائل المُوجهة" if block_setting else "نسخ بدون علامة توجيه"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_advanced_filter_forwarded_message_filter_enabled_{task_id}")],
            [Button.inline(f"⚙️ تغيير الوضع ({mode_text})", f"toggle_forwarded_block_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر المتقدمة", f"advanced_filters_{task_id}")]
        ]
        
        # Add timestamp to force UI refresh
        import time
        timestamp = int(time.time()) % 100
        
        try:
            await event.edit(
                f"↗️ فلتر الرسائل المُوجهة - المهمة #{task_id}\n\n"
                f"📊 الحالة: {status_text}\n"
                f"⚙️ الوضع: {mode_text}\n\n"
                f"💡 هذا الفلتر يتحكم في الرسائل المُوجهة من مصادر أخرى\n"
                f"⏰ آخر تحديث: {timestamp}",
                buttons=buttons
            )
        except Exception as e:
            if "Content of the message was not modified" not in str(e):
                raise e
            logger.debug("المحتوى لم يتغير، فلتر الرسائل المُوجهة محدث بنجاح")

    async def toggle_forwarded_message_block(self, event, task_id):
        """Toggle forwarded message block mode"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
            
        try:
            # Get current setting and toggle
            current_setting = self.db.get_forwarded_message_filter_setting(task_id)
            new_setting = not current_setting
            
            success = self.db.set_forwarded_message_filter(task_id, new_setting)
            
            if success:
                mode_text = "حظر الرسائل المُعاد توجيهها" if new_setting else "السماح بالرسائل المُعاد توجيهها"
                await event.answer(f"✅ تم تغيير الوضع إلى: {mode_text}")
                
                # Force refresh UserBot tasks
                await self._refresh_userbot_tasks(user_id)
                
                # Refresh the display
                try:
                    await self.show_forwarded_message_filter(event, task_id)
                except Exception as e:
                    if "Content of the message was not modified" not in str(e):
                        raise e
                    logger.debug("المحتوى لم يتغير، فلتر الرسائل المُعاد توجيهها محدث بنجاح")
            else:
                await event.answer("❌ فشل في تغيير الوضع")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل وضع فلتر الرسائل المُعاد توجيهها: {e}")
            await event.answer("❌ حدث خطأ في التحديث")

    async def _complete_login_process(self, event, temp_client, result, phone, user_id):
        """Complete the login process for accounts (with or without 2FA)"""
        try:
            # Get session string
            from telethon.sessions import StringSession
            session_string = StringSession.save(temp_client.session)
            
            # Save to database
            self.db.save_user_session(user_id, phone, session_string)
            
            # Clear conversation state
            self.db.clear_conversation_state(user_id)
            
            logger.info(f"✅ تم حفظ الجلسة للمستخدم {user_id}")
            
            # Disconnect temp client
            await temp_client.disconnect()
            
            # Start UserBot for this user (asynchronously)
            from userbot_service.userbot import userbot_instance
            
            # Show immediate success message
            buttons = [
                [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
                [Button.inline("⚙️ الإعدادات", b"settings")],
                [Button.inline("ℹ️ حول البوت", b"about")]
            ]
            
            await self.edit_or_send_message(event, 
                f"🎉 تم تسجيل الدخول بنجاح!\n\n"
                f"📱 الرقم: {phone}\n"
                f"⏳ جاري تشغيل خدمة التوجيه التلقائي...\n\n"
                f"اختر ما تريد فعله:",
                buttons=buttons
            )
            
            # Start UserBot in the background
            asyncio.create_task(self._start_userbot_background(user_id, session_string, event))
                
        except Exception as e:
            logger.error(f"❌ خطأ في إتمام عملية تسجيل الدخول: {e}")
            await self.edit_or_send_message(event, 
                "❌ حدث خطأ في إتمام تسجيل الدخول\n\n"
                "حاول مرة أخرى باستخدام /start"
            )

    async def _start_userbot_background(self, user_id: int, session_string: str, event):
        """Start UserBot in background and update user"""
        try:
            from userbot_service.userbot import userbot_instance
            success = await userbot_instance.start_with_session(user_id, session_string)
            
            if success:
                logger.info(f"✅ تم تشغيل UserBot للمستخدم {user_id} في الخلفية")
                # Optionally send a notification to user that UserBot is ready
                try:
                    await self.edit_or_send_message(event, "✅ تم تشغيل خدمة التوجيه التلقائي بنجاح!")
                except:
                    # User might have moved on, that's fine
                    pass
            else:
                logger.error(f"❌ فشل في تشغيل UserBot للمستخدم {user_id}")
                try:
                    await self.edit_or_send_message(event, 
                        "⚠️ فشل في تشغيل خدمة التوجيه التلقائي\n"
                        "يمكنك المحاولة مرة أخرى باستخدام /start"
                    )
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"خطأ في تشغيل UserBot في الخلفية للمستخدم {user_id}: {e}")
            try:
                await self.edit_or_send_message(event, 
                    "⚠️ حدث خطأ في تشغيل خدمة التوجيه\n"
                    "يمكنك المحاولة مرة أخرى باستخدام /start"
                )
            except:
                pass

    # Send new message versions (for input responses)
    async def send_forwarding_delay_settings(self, event, task_id):
        """Send new forwarding delay settings message"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
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
        
        await self.edit_or_send_message(event, 
            f"⏳ إعدادات تأخير التوجيه للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⏱️ مدة التأخير: {delay_text}\n\n"
            f"📝 الوصف:\n"
            f"يضيف تأخير زمني قبل إرسال الرسائل المُوجهة",
            buttons=buttons
        )

    async def send_sending_interval_settings(self, event, task_id):
        """Send new sending interval settings message"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
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
        
        await self.edit_or_send_message(event, 
            f"📊 إعدادات فترات الإرسال للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"⏱️ الفترة بين الرسائل: {interval_text}\n\n"
            f"📝 الوصف:\n"
            f"يحدد الفترة الزمنية بين إرسال كل رسالة والتي تليها",
            buttons=buttons
        )

    async def send_rate_limit_settings(self, event, task_id):
        """Send new rate limit settings message"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await self.edit_or_send_message(event, "❌ المهمة غير موجودة")
            return
            
        task_name = task.get('task_name', 'مهمة بدون اسم')
        settings = self.db.get_rate_limit_settings(task_id)
        
        status_text = "🟢 مفعل" if settings['enabled'] else "🔴 معطل"
        
        period_minutes = settings['time_period_seconds'] // 60
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_rate_limit_{task_id}")],
            [Button.inline(f"🔢 تعديل العدد ({settings['message_count']})", f"edit_rate_count_{task_id}")],
            [Button.inline(f"⏰ تعديل الفترة ({period_minutes} دقيقة)", f"edit_rate_period_{task_id}")],
            [Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")]
        ]
        
        await self.edit_or_send_message(event, 
            f"⚡ إعدادات حد المعدل للمهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n"
            f"🔢 عدد الرسائل: {settings['message_count']}\n"
            f"⏰ خلال فترة: {period_minutes} دقيقة\n\n"
            f"📝 الوصف:\n"
            f"يحدد هذا الإعداد عدد الرسائل المسموح بإرسالها خلال فترة زمنية محددة",
            buttons=buttons
        )

async def run_simple_bot():
    """Run the simple telegram bot"""
    logger.info("🚀 بدء تشغيل نظام بوت تليجرام...")
    
    # Create bot instance  
    bot = SimpleTelegramBot()
    
    # Start the bot
    await bot.start()
    
    # Return bot instance for global access
    return bot

# Removed erroneous redefinition of class SimpleTelegramBot
    
    async def select_audio_template(self, event, task_id):
        """Select audio metadata template"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        buttons = [
            [Button.inline("🔹 القالب الافتراضي", f"set_audio_template_{task_id}_default")],
            [Button.inline("🔹 قالب محسن", f"set_audio_template_{task_id}_enhanced")],
            [Button.inline("🔹 قالب بسيط", f"set_audio_template_{task_id}_minimal")],
            [Button.inline("🔹 قالب احترافي", f"set_audio_template_{task_id}_professional")],
            [Button.inline("🔹 قالب مخصص", f"set_audio_template_{task_id}_custom")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"📋 اختيار قالب الوسوم الصوتية للمهمة: {task_name}\n\n"
            f"🔹 القوالب المتاحة:\n\n"
            f"**🔹 القالب الافتراضي**:\n"
            f"يحافظ على الوسوم الأصلية مع إضافة تعليق\n\n"
            f"**🔹 قالب محسن**:\n"
            f"يضيف 'Enhanced' للعنوان ويحسن التعليق\n\n"
            f"**🔹 قالب بسيط**:\n"
            f"يحتوي على الوسوم الأساسية فقط\n\n"
            f"**🔹 قالب احترافي**:\n"
            f"مناسب للاستخدام التجاري والمهني\n\n"
            f"**🔹 قالب مخصص**:\n"
            f"للعلامات التجارية والتخصيص الكامل\n\n"
            f"اختر القالب المناسب لاحتياجاتك:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)
    
    async def set_audio_template(self, event, task_id, template_name):
        """Set audio metadata template"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        # Persist template
        self.db.update_audio_metadata_template(task_id, template_name)
        
        template_display_name = {
            'default': 'الافتراضي',
            'enhanced': 'محسن',
            'minimal': 'بسيط',
            'professional': 'احترافي',
            'custom': 'مخصص'
        }.get(template_name, template_name)
        
        await event.answer(f"✅ تم اختيار قالب '{template_display_name}'")
        
        # Return to audio metadata settings
        await self.audio_metadata_settings(event, task_id)
    
    async def album_art_settings(self, event, task_id):
        """Show album art settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get current album art settings
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        art_enabled = audio_settings.get('album_art_enabled', False)
        apply_to_all = audio_settings.get('apply_art_to_all', False)
        art_path = audio_settings.get('album_art_path', '')
        
        art_status = "🟢 مفعل" if art_enabled else "🔴 معطل"
        apply_all_status = "🟢 نعم" if apply_to_all else "🔴 لا"
        art_path_display = art_path if art_path else "غير محدد"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({art_status.split()[0]})", f"toggle_album_art_enabled_{task_id}")],
            [Button.inline("🖼️ رفع صورة غلاف", f"upload_album_art_{task_id}")],
            [Button.inline(f"⚙️ تطبيق على الجميع ({apply_all_status.split()[0]})", f"toggle_apply_art_to_all_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"🖼️ إعدادات صورة الغلاف للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• رفع صورة غلاف مخصصة للملفات الصوتية\n"
            f"• خيار تطبيقها على جميع الملفات\n"
            f"• خيار تطبيقها فقط على الملفات بدون صورة\n"
            f"• الحفاظ على الجودة 100%\n"
            f"• دعم الصيغ: JPG, PNG, BMP, TIFF\n\n"
            f"📊 الحالة الحالية:\n"
            f"• الحالة: {art_status}\n"
            f"• تطبيق على الجميع: {apply_all_status}\n"
            f"• المسار الحالي: {art_path_display}\n\n"
            f"اختر الإعداد الذي تريد تعديله أو ارفع صورة جديدة:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)
    
    async def audio_merge_settings(self, event, task_id):
        """Show audio merge settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get current audio merge settings
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        merge_enabled = audio_settings.get('audio_merge_enabled', False)
        intro_path = audio_settings.get('intro_path', '')
        outro_path = audio_settings.get('outro_path', '')
        intro_position = audio_settings.get('intro_position', 'start')
        
        merge_status = "🟢 مفعل" if merge_enabled else "🔴 معطل"
        intro_path_display = intro_path if intro_path else "غير محدد"
        outro_path_display = outro_path if outro_path else "غير محدد"
        intro_position_display = "البداية" if intro_position == 'start' else "النهاية"
        
        buttons = [
            [Button.inline(f"🎚️ تبديل حالة الدمج ({merge_status.split()[0]})", f"toggle_audio_merge_{task_id}")],
            [Button.inline("🎵 مقطع مقدمة", f"intro_audio_settings_{task_id}")],
            [Button.inline("🎵 مقطع خاتمة", f"outro_audio_settings_{task_id}")],
            [Button.inline("⚙️ خيارات الدمج", f"merge_options_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"🔗 إعدادات دمج المقاطع الصوتية للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• إضافة مقطع مقدمة في البداية\n"
            f"• إضافة مقطع خاتمة في النهاية\n"
            f"• اختيار موضع المقدمة (بداية أو نهاية)\n"
            f"• دعم جميع الصيغ الصوتية\n"
            f"• جودة عالية 320k MP3\n\n"
            f"📊 الحالة الحالية:\n"
            f"• حالة الدمج: {merge_status}\n"
            f"• مقدمة: {intro_path_display}\n"
            f"• خاتمة: {outro_path_display}\n"
            f"• موضع المقدمة: {intro_position_display}\n\n"
            f"اختر الإعداد الذي تريد تعديله:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)
    
    async def advanced_audio_settings(self, event, task_id):
        """Show advanced audio settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get current advanced settings
        audio_settings = self.db.get_audio_metadata_settings(task_id)
        preserve_quality = audio_settings.get('preserve_quality', True)
        convert_to_mp3 = audio_settings.get('convert_to_mp3', False)
        
        preserve_status = "🟢" if preserve_quality else "🔴"
        convert_status = "🟢" if convert_to_mp3 else "🔴"
        
        buttons = [
            [Button.inline(f"{preserve_status} الحفاظ على الجودة", f"toggle_preserve_quality_{task_id}")],
            [Button.inline(f"{convert_status} التحويل إلى MP3", f"toggle_convert_to_mp3_{task_id}")],
            [Button.inline("🔙 رجوع لإعدادات الوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"⚙️ الإعدادات المتقدمة للوسوم الصوتية للمهمة: {task_name}\n\n"
            f"📝 الوصف:\n"
            f"• الحفاظ على الجودة الأصلية 100%\n"
            f"• تحويل إلى MP3 مع الحفاظ على الدقة\n"
            f"• معالجة مرة واحدة وإعادة الاستخدام\n"
            f"• Cache ذكي للملفات المعالجة\n"
            f"• إعدادات الأداء والسرعة\n\n"
            f"📊 الحالة الحالية:\n"
            f"• الحفاظ على الجودة: {preserve_status} {'مفعل' if preserve_quality else 'معطل'}\n"
            f"• التحويل إلى MP3: {convert_status} {'مفعل' if convert_to_mp3 else 'معطل'}\n\n"
            f"اختر الإعداد الذي تريد تعديله:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def show_album_art_options(self, event, task_id: int):
        settings = self.db.get_audio_metadata_settings(task_id)
        art_status = "🟢 مفعل" if settings.get('album_art_enabled') else "🔴 معطل"
        apply_all_status = "🟢 نعم" if settings.get('apply_art_to_all') else "🔴 لا"
        buttons = [
            [Button.inline(f"🔄 تبديل صورة الغلاف ({art_status})", f"toggle_album_art_enabled_{task_id}")],
            [Button.inline(f"📦 تطبيق على جميع الملفات ({apply_all_status})", f"toggle_apply_art_to_all_{task_id}")],
            [Button.inline("🔙 رجوع", f"album_art_settings_{task_id}")]
        ]
        await self.force_new_message(event, "⚙️ خيارات صورة الغلاف:", buttons=buttons)

    async def show_intro_audio_settings(self, event, task_id: int):
        settings = self.db.get_audio_metadata_settings(task_id)
        intro_path = settings.get('intro_audio_path') or 'غير محدد'
        buttons = [
            [Button.inline("⬆️ رفع مقدمة", f"upload_intro_audio_{task_id}")],
            [Button.inline("🗑️ حذف المقدمة", f"remove_intro_audio_{task_id}")],
            [Button.inline("🔙 رجوع", f"audio_merge_settings_{task_id}")]
        ]
        await self.force_new_message(event, f"🎵 مقدمة حالية: {intro_path}", buttons=buttons)

    async def show_outro_audio_settings(self, event, task_id: int):
        settings = self.db.get_audio_metadata_settings(task_id)
        outro_path = settings.get('outro_audio_path') or 'غير محدد'
        buttons = [
            [Button.inline("⬆️ رفع خاتمة", f"upload_outro_audio_{task_id}")],
            [Button.inline("🗑️ حذف الخاتمة", f"remove_outro_audio_{task_id}")],
            [Button.inline("🔙 رجوع", f"audio_merge_settings_{task_id}")]
        ]
        await self.force_new_message(event, f"🎵 خاتمة حالية: {outro_path}", buttons=buttons)

    async def show_merge_options(self, event, task_id: int):
        settings = self.db.get_audio_metadata_settings(task_id)
        pos = settings.get('intro_position', 'start')
        pos_text = 'البداية' if pos == 'start' else 'النهاية'
        buttons = [
            [Button.inline("⬆️ المقدمة في البداية", f"set_intro_position_start_{task_id}")],
            [Button.inline("⬇️ المقدمة في النهاية", f"set_intro_position_end_{task_id}")],
            [Button.inline("🔙 رجوع", f"audio_merge_settings_{task_id}")]
        ]
        await self.force_new_message(event, f"⚙️ موضع المقدمة الحالي: {pos_text}", buttons=buttons)

    # ===== Audio Text Processing Methods =====
    async def audio_text_cleaning(self, event, task_id):
        """Show audio text cleaning settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get text cleaning settings for audio tags
        try:
            audio_cleaning = self.db.get_audio_text_cleaning_settings(task_id)
            status_text = "🟢 مفعل" if audio_cleaning.get('enabled', False) else "🔴 معطل"
        except (AttributeError, KeyError):
            status_text = "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_audio_text_cleaning_{task_id}")],
            [Button.inline("🧹 حذف الروابط", f"audio_clean_links_{task_id}"),
             Button.inline("😀 حذف الرموز التعبيرية", f"audio_clean_emojis_{task_id}")],
            [Button.inline("# حذف الهاشتاج", f"audio_clean_hashtags_{task_id}"),
             Button.inline("📞 حذف أرقام الهاتف", f"audio_clean_phones_{task_id}")],
            [Button.inline("📝 حذف السطور الفارغة", f"audio_clean_empty_{task_id}"),
             Button.inline("🔤 حذف كلمات محددة", f"audio_clean_keywords_{task_id}")],
            [Button.inline("🎯 اختيار الوسوم للتنظيف", f"audio_clean_tag_selection_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"🧹 تنظيف نصوص الوسوم الصوتية - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n\n"
            f"🔧 **خيارات التنظيف المتاحة:**\n"
            f"• حذف الروابط من الوسوم\n"
            f"• حذف الرموز التعبيرية\n"
            f"• حذف علامات الهاشتاج\n"
            f"• حذف أرقام الهاتف\n"
            f"• حذف السطور الفارغة\n"
            f"• حذف كلمات وعبارات محددة\n\n"
            f"💡 **ملاحظة:** سيتم تطبيق التنظيف على الوسوم المحددة فقط\n"
            f"(العنوان، الفنان، التعليق، كلمات الأغنية، إلخ)"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)
    
    async def audio_word_filters(self, event, task_id):
        """Show audio word filters settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        try:
            audio_filters = self.db.get_audio_word_filters_settings(task_id)
            status_text = "🟢 مفعل" if audio_filters.get('enabled', False) else "🔴 معطل"
        except (AttributeError, KeyError):
            status_text = "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_audio_word_filters_{task_id}")],
            [Button.inline("✅ الكلمات المقبولة", f"audio_whitelist_{task_id}"),
             Button.inline("❌ الكلمات المرفوضة", f"audio_blacklist_{task_id}")],
            [Button.inline("🎯 اختيار الوسوم للفلترة", f"audio_filter_tag_selection_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"📝 فلاتر كلمات الوسوم الصوتية - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n\n"
            f"🔧 **أنواع الفلاتر:**\n"
            f"• **القائمة البيضاء:** الكلمات المسموحة فقط\n"
            f"• **القائمة السوداء:** الكلمات الممنوعة\n\n"
            f"💡 **الاستخدام:** فلترة محتوى الوسوم حسب كلمات محددة\n"
            f"مثل السماح بأسماء فنانين معينين فقط أو منع كلمات غير مرغوبة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)
    
    async def audio_header_footer(self, event, task_id):
        """Show audio header/footer settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        try:
            audio_header_footer = self.db.get_audio_header_footer_settings(task_id)
            status_text = "🟢 مفعل" if audio_header_footer.get('enabled', False) else "🔴 معطل"
        except (AttributeError, KeyError):
            status_text = "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_audio_header_footer_{task_id}")],
            [Button.inline("📄 إعداد الهيدر", f"audio_header_settings_{task_id}"),
             Button.inline("📝 إعداد الفوتر", f"audio_footer_settings_{task_id}")],
            [Button.inline("🎯 اختيار الوسوم للهيدر/فوتر", f"audio_hf_tag_selection_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"📄 هيدر وفوتر الوسوم الصوتية - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n\n"
            f"🔧 **الوظائف:**\n"
            f"• إضافة نص في بداية الوسوم (هيدر)\n"
            f"• إضافة نص في نهاية الوسوم (فوتر)\n"
            f"• تطبيق على وسوم محددة\n\n"
            f"💡 **مثال:** إضافة اسم القناة في بداية عنوان الأغنية\n"
            f"أو إضافة حقوق الطبع في نهاية التعليق"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)
    
    async def audio_tag_selection(self, event, task_id):
        """Show audio tag selection for text processing"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get current tag selection settings
        try:
            selected_tags = self.db.get_audio_selected_tags(task_id)
        except (AttributeError, KeyError):
            selected_tags = []
        
        available_tags = [
            ('title', 'العنوان'),
            ('artist', 'الفنان'),
            ('album_artist', 'فنان الألبوم'),
            ('album', 'الألبوم'),
            ('composer', 'الملحن'),
            ('comment', 'التعليق'),
            ('lyrics', 'كلمات الأغنية'),
            ('genre', 'النوع')
        ]
        
        buttons = []
        for tag_key, tag_name in available_tags:
            status = "✅" if tag_key in selected_tags else "⬜"
            buttons.append([Button.inline(f"{status} {tag_name}", f"toggle_audio_tag_{task_id}_{tag_key}")])
        
        buttons.extend([
            [Button.inline("✅ تحديد الكل", f"select_all_audio_tags_{task_id}"),
             Button.inline("❌ إلغاء الكل", f"deselect_all_audio_tags_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ])
        
        message_text = (
            f"🎯 اختيار الوسوم للمعالجة - المهمة: {task_name}\n\n"
            f"📝 **اختر الوسوم التي تريد تطبيق معالجة النصوص عليها:**\n\n"
            f"✅ = مُحدد للمعالجة\n"
            f"⬜ = غير مُحدد\n\n"
            f"💡 **ملاحظة:** ستطبق جميع عمليات معالجة النصوص\n"
            f"(التنظيف، الاستبدال، الفلاتر، الهيدر/فوتر) على الوسوم المحددة فقط"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    # ===== Audio Text Processing Functions =====
    
    
    async def audio_word_filters(self, event, task_id):
        """Show audio word filters settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        try:
            settings = self.db.get_audio_word_filters_settings(task_id)
            status_text = "🟢 مفعل" if settings.get('enabled', False) else "🔴 معطل"
        except Exception:
            status_text = "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_audio_word_filters_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"📝 فلاتر كلمات الوسوم الصوتية - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n\n"
            f"🔧 **أنواع الفلاتر:**\n"
            f"• **القائمة البيضاء:** الكلمات المسموحة فقط\n"
            f"• **القائمة السوداء:** الكلمات الممنوعة\n\n"
            f"💡 **الاستخدام:** فلترة محتوى الوسوم حسب كلمات محددة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def audio_header_footer(self, event, task_id):
        """Show audio header/footer settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        try:
            settings = self.db.get_audio_tag_header_footer_settings(task_id)
            status_text = "🟢 مفعل" if (settings.get('header_enabled', False) or settings.get('footer_enabled', False)) else "🔴 معطل"
        except Exception:
            status_text = "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status_text})", f"toggle_audio_header_footer_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ]
        
        message_text = (
            f"📄 هيدر وفوتر الوسوم الصوتية - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status_text}\n\n"
            f"🔧 **الوظائف:**\n"
            f"• إضافة نص في بداية الوسوم (هيدر)\n"
            f"• إضافة نص في نهاية الوسوم (فوتر)\n"
            f"• تطبيق على وسوم محددة\n\n"
            f"💡 **مثال:** إضافة اسم القناة في بداية عنوان الأغنية"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def audio_tag_selection(self, event, task_id):
        """Show audio tag selection for text processing"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        # Get selected tags
        try:
            selected_tags = self.db.get_audio_selected_tags(task_id)
        except Exception:
            selected_tags = []
        
        # Available audio tags for processing
        available_tags = [
            ('title', 'العنوان (Title)'),
            ('artist', 'الفنان (Artist)'),
            ('album_artist', 'فنان الألبوم (Album Artist)'),
            ('album', 'الألبوم (Album)'),
            ('year', 'السنة (Year)'),
            ('genre', 'النوع (Genre)'),
            ('composer', 'الملحن (Composer)'),
            ('comment', 'تعليق (Comment)'),
            ('track', 'رقم المسار (Track)'),
            ('lyrics', 'كلمات الأغنية (Lyrics)')
        ]
        
        buttons = []
        for tag_key, tag_name in available_tags:
            status = "✅" if tag_key in selected_tags else "⬜"
            buttons.append([Button.inline(f"{status} {tag_name}", f"toggle_audio_tag_{task_id}_{tag_key}")])
        
        buttons.extend([
            [Button.inline("✅ تحديد الكل", f"select_all_audio_tags_{task_id}"),
             Button.inline("❌ إلغاء الكل", f"deselect_all_audio_tags_{task_id}")],
            [Button.inline("🔙 رجوع للوسوم الصوتية", f"audio_metadata_settings_{task_id}")]
        ])
        
        message_text = (
            f"🎯 اختيار الوسوم للمعالجة - المهمة: {task_name}\n\n"
            f"📊 الوسوم المحددة: {len(selected_tags)}/{len(available_tags)}\n\n"
            f"💡 **الوظيفة:** تحديد الوسوم التي ستخضع لمعالجة النصوص\n"
            f"(تنظيف، استبدال، فلاتر، هيدر/فوتر)\n\n"
            f"🔘 اضغط على الوسم لتبديل اختياره:"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    # ===== Audio Metadata Enhanced Interface =====
    async def update_audio_metadata_interface(self):
        """Update audio metadata interface to show new buttons"""
        # This function can be called to refresh the interface with new text processing buttons
        pass

    # ===== Audio Cleaning Functions =====
    async def toggle_audio_clean_option(self, event, task_id: int, option: str):
        """Toggle specific audio cleaning option"""
        try:
            current_settings = self.db.get_audio_text_cleaning_settings(task_id)
            if not current_settings:
                current_settings = {'enabled': False}
            
            option_key = f'clean_{option}'
            current_state = current_settings.get(option_key, False)
            new_state = not current_state
            
            # Update the specific cleaning option
            self.db.update_audio_cleaning_option(task_id, option_key, new_state)
            
            status = "مفعل" if new_state else "معطل"
            await event.answer(f"✅ تم تحديث خيار {self.get_clean_option_name(option)}: {status}")
            
            # Return to cleaning settings
            await self.audio_text_cleaning(event, task_id)
            
        except Exception as e:
            logger.error(f"Error toggling audio clean option {option}: {e}")
            await event.answer("❌ حدث خطأ أثناء التحديث")

    def get_clean_option_name(self, option: str) -> str:
        """Get Arabic name for cleaning option"""
        names = {
            'links': 'حذف الروابط',
            'emojis': 'حذف الرموز التعبيرية', 
            'hashtags': 'حذف الهاشتاج',
            'phones': 'حذف أرقام الهاتف',
            'empty_lines': 'حذف السطور الفارغة'
        }
        return names.get(option, option)

    async def audio_clean_keywords_settings(self, event, task_id: int):
        """Show audio cleaning keywords settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        try:
            keywords = self.db.get_audio_clean_keywords(task_id)
            keywords_list = keywords if isinstance(keywords, list) else []
        except Exception:
            keywords_list = []
        
        buttons = [
            [Button.inline("➕ إضافة كلمة/عبارة", f"add_audio_clean_keyword_{task_id}")],
            [Button.inline("📋 عرض القائمة", f"view_audio_clean_keywords_{task_id}")],
            [Button.inline("🗑️ حذف جميع الكلمات", f"clear_audio_clean_keywords_{task_id}")],
            [Button.inline("🔙 رجوع للتنظيف", f"audio_text_cleaning_{task_id}")]
        ]
        
        message_text = (
            f"🔤 كلمات التنظيف - المهمة: {task_name}\n\n"
            f"📊 عدد الكلمات/العبارات: {len(keywords_list)}\n\n"
            f"💡 **الوظيفة:** حذف كلمات وعبارات محددة من الوسوم الصوتية\n\n"
            f"🔧 **كيفية الاستخدام:**\n"
            f"• أضف الكلمات/العبارات المراد حذفها\n"
            f"• سيتم البحث عنها وحذفها من جميع الوسوم المحددة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    # ===== Audio Replacements Functions =====
    async def add_audio_replacement(self, event, task_id: int):
        """Add new audio text replacement"""
        user_id = event.sender_id
        self.set_user_state(user_id, 'adding_audio_replacement', {'task_id': task_id, 'step': 'search_text'})
        
        message_text = (
            "➕ إضافة استبدال جديد\n\n"
            "🔍 أرسل النص المراد البحث عنه واستبداله:"
        )
        
        buttons = [[Button.inline("❌ إلغاء", f"audio_text_replacements_{task_id}")]]
        await self.force_new_message(event, message_text, buttons=buttons)

    async def view_audio_replacements(self, event, task_id: int):
        """View current audio text replacements"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        try:
            replacements = self.db.get_audio_replacements_list(task_id)
            if not replacements:
                replacements = []
        except Exception:
            replacements = []
        
        if not replacements:
            message_text = f"📋 قائمة الاستبدالات - المهمة: {task_name}\n\n❌ لا توجد استبدالات محفوظة"
        else:
            message_text = f"📋 قائمة الاستبدالات - المهمة: {task_name}\n\n"
            for i, replacement in enumerate(replacements, 1):
                search_text = replacement.get('search_text', '')
                replace_text = replacement.get('replace_text', '')
                case_sensitive = replacement.get('case_sensitive', False)
                whole_words = replacement.get('whole_words', False)
                
                options = []
                if case_sensitive:
                    options.append("حساس للأحرف")
                if whole_words:
                    options.append("كلمات كاملة")
                
                options_str = f" ({', '.join(options)})" if options else ""
                
                message_text += f"{i}. '{search_text}' → '{replace_text}'{options_str}\n"
        
        buttons = [
            [Button.inline("🔙 رجوع", f"audio_text_replacements_{task_id}")]
        ]
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def clear_audio_replacements(self, event, task_id: int):
        """Clear all audio text replacements"""
        try:
            self.db.clear_audio_replacements(task_id)
            await event.answer("✅ تم حذف جميع الاستبدالات")
            await self.audio_text_replacements(event, task_id)
        except Exception as e:
            logger.error(f"Error clearing audio replacements: {e}")
            await event.answer("❌ حدث خطأ أثناء الحذف")

    # ===== Audio Word Filters Functions =====
    async def toggle_audio_word_filters(self, event, task_id: int):
        """Toggle audio word filters enabled state"""
        try:
            current = self.db.get_audio_word_filters_settings(task_id)
            new_state = not bool(current.get('enabled', False))
            self.db.update_audio_word_filters_enabled(task_id, new_state)
            await event.answer("✅ تم التبديل")
        except Exception:
            await event.answer("❌ حدث خطأ أثناء التبديل")
        await self.audio_word_filters(event, task_id)

    async def audio_whitelist_settings(self, event, task_id: int):
        """Show audio whitelist settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        try:
            whitelist = self.db.get_audio_whitelist(task_id)
            whitelist_words = whitelist if isinstance(whitelist, list) else []
        except Exception:
            whitelist_words = []
        
        buttons = [
            [Button.inline("➕ إضافة كلمة", f"add_audio_whitelist_word_{task_id}")],
            [Button.inline("📋 عرض القائمة", f"view_audio_whitelist_{task_id}")],
            [Button.inline("🗑️ حذف جميع الكلمات", f"clear_audio_whitelist_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر", f"audio_word_filters_{task_id}")]
        ]
        
        message_text = (
            f"✅ القائمة البيضاء - المهمة: {task_name}\n\n"
            f"📊 عدد الكلمات المسموحة: {len(whitelist_words)}\n\n"
            f"💡 **الوظيفة:** السماح فقط بالكلمات الموجودة في هذه القائمة\n"
            f"أي كلمة غير موجودة في القائمة سيتم حذفها من الوسوم"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def audio_blacklist_settings(self, event, task_id: int):
        """Show audio blacklist settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        try:
            blacklist = self.db.get_audio_blacklist(task_id)
            blacklist_words = blacklist if isinstance(blacklist, list) else []
        except Exception:
            blacklist_words = []
        
        buttons = [
            [Button.inline("➕ إضافة كلمة", f"add_audio_blacklist_word_{task_id}")],
            [Button.inline("📋 عرض القائمة", f"view_audio_blacklist_{task_id}")],
            [Button.inline("🗑️ حذف جميع الكلمات", f"clear_audio_blacklist_{task_id}")],
            [Button.inline("🔙 رجوع للفلاتر", f"audio_word_filters_{task_id}")]
        ]
        
        message_text = (
            f"❌ القائمة السوداء - المهمة: {task_name}\n\n"
            f"📊 عدد الكلمات الممنوعة: {len(blacklist_words)}\n\n"
            f"💡 **الوظيفة:** منع الكلمات الموجودة في هذه القائمة\n"
            f"أي كلمة موجودة في القائمة سيتم حذفها من الوسوم"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    # ===== Audio Header/Footer Functions =====
    async def toggle_audio_header_footer(self, event, task_id: int):
        """Toggle audio header/footer enabled state"""
        try:
            current = self.db.get_audio_header_footer_settings(task_id)
            header_enabled = current.get('header_enabled', False)
            footer_enabled = current.get('footer_enabled', False)
            
            # If both are disabled, enable header
            if not header_enabled and not footer_enabled:
                self.db.update_audio_header_footer_enabled(task_id, header_enabled=True, footer_enabled=False)
                await event.answer("✅ تم تفعيل الهيدر")
            # If header only is enabled, enable footer too
            elif header_enabled and not footer_enabled:
                self.db.update_audio_header_footer_enabled(task_id, header_enabled=True, footer_enabled=True)
                await event.answer("✅ تم تفعيل الفوتر أيضاً")
            # If both are enabled, disable both
            else:
                self.db.update_audio_header_footer_enabled(task_id, header_enabled=False, footer_enabled=False)
                await event.answer("✅ تم تعطيل الهيدر والفوتر")
                
        except Exception:
            await event.answer("❌ حدث خطأ أثناء التبديل")
        await self.audio_header_footer(event, task_id)

    async def audio_header_settings(self, event, task_id: int):
        """Show audio header settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        try:
            settings = self.db.get_audio_header_footer_settings(task_id)
            header_text = settings.get('header_text', '')
            header_enabled = settings.get('header_enabled', False)
        except Exception:
            header_text = ''
            header_enabled = False
        
        status = "🟢 مفعل" if header_enabled else "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status})", f"toggle_audio_header_only_{task_id}")],
            [Button.inline("✏️ تحرير نص الهيدر", f"edit_audio_header_text_{task_id}")],
            [Button.inline("🗑️ حذف نص الهيدر", f"clear_audio_header_text_{task_id}")],
            [Button.inline("🔙 رجوع للهيدر/فوتر", f"audio_header_footer_{task_id}")]
        ]
        
        header_preview = header_text if header_text else "لا يوجد نص"
        
        message_text = (
            f"📄 إعدادات الهيدر - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status}\n"
            f"📝 النص الحالي: {header_preview}\n\n"
            f"💡 **الوظيفة:** إضافة نص في بداية الوسوم المحددة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    async def audio_footer_settings(self, event, task_id: int):
        """Show audio footer settings"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        task_name = task.get('task_name', 'مهمة بدون اسم')
        
        try:
            settings = self.db.get_audio_header_footer_settings(task_id)
            footer_text = settings.get('footer_text', '')
            footer_enabled = settings.get('footer_enabled', False)
        except Exception:
            footer_text = ''
            footer_enabled = False
        
        status = "🟢 مفعل" if footer_enabled else "🔴 معطل"
        
        buttons = [
            [Button.inline(f"🔄 تبديل الحالة ({status})", f"toggle_audio_footer_only_{task_id}")],
            [Button.inline("✏️ تحرير نص الفوتر", f"edit_audio_footer_text_{task_id}")],
            [Button.inline("🗑️ حذف نص الفوتر", f"clear_audio_footer_text_{task_id}")],
            [Button.inline("🔙 رجوع للهيدر/فوتر", f"audio_header_footer_{task_id}")]
        ]
        
        footer_preview = footer_text if footer_text else "لا يوجد نص"
        
        message_text = (
            f"📝 إعدادات الفوتر - المهمة: {task_name}\n\n"
            f"📊 الحالة: {status}\n"
            f"📝 النص الحالي: {footer_preview}\n\n"
            f"💡 **الوظيفة:** إضافة نص في نهاية الوسوم المحددة"
        )
        
        await self.force_new_message(event, message_text, buttons=buttons)

    # ===== Advanced Features Menu =====
