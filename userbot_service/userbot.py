"""
Userbot Service for Message Forwarding
Uses Telethon for automated message forwarding between chats
"""
import logging
import asyncio
import re
from typing import Dict, List, Optional, Tuple
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, AuthKeyUnregisteredError
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntitySpoiler
from database.database import Database
from bot_package.config import API_ID, API_HASH
import time
from collections import defaultdict

# Import translation service
try:
    from googletrans import Translator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    logger.warning("⚠️ googletrans غير متوفر - الترجمة معطلة")

logger = logging.getLogger(__name__)

class AlbumCollector:
    """Collector for handling album messages in copy mode"""
    def __init__(self):
        self.albums: Dict[int, List] = defaultdict(list)
        self.timers: Dict[int, asyncio.Task] = {}
        self.processed_albums: set = set()
    
    def should_collect_album(self, message, forward_mode: str, split_album: bool) -> bool:
        """Check if message should be collected as part of album"""
        return (hasattr(message, 'grouped_id') and 
                message.grouped_id and 
                forward_mode == 'copy' and 
                not split_album)
    
    def add_message(self, message, task_info):
        """Add message to album collection"""
        group_id = message.grouped_id
        self.albums[group_id].append({
            'message': message,
            'task_info': task_info
        })
        return group_id
        
    def is_album_processed(self, group_id: int) -> bool:
        """Check if album was already processed"""
        return group_id in self.processed_albums
        
    def mark_album_processed(self, group_id: int):
        """Mark album as processed"""
        self.processed_albums.add(group_id)
        
    def get_album_messages(self, group_id: int) -> List:
        """Get all messages in album"""
        return self.albums.get(group_id, [])
        
    def cleanup_album(self, group_id: int):
        """Clean up album data"""
        if group_id in self.albums:
            del self.albums[group_id]
        if group_id in self.timers:
            if not self.timers[group_id].done():
                self.timers[group_id].cancel()
            del self.timers[group_id]

class UserbotService:
    def __init__(self):
        self.db = Database()
        self.clients: Dict[int, TelegramClient] = {}  # user_id -> client
        self.user_tasks: Dict[int, List[Dict]] = {}   # user_id -> tasks
        self.running = True
        self.album_collectors: Dict[int, AlbumCollector] = {}  # user_id -> collector

    async def start_with_session(self, user_id: int, session_string: str):
        """Start userbot for a specific user with session string"""
        try:
            # Create client with session string
            client = TelegramClient(
                StringSession(session_string),
                int(API_ID),
                API_HASH
            )

            # Connect and check if session is valid
            await client.connect()

            if not await client.is_user_authorized():
                logger.error(f"Session غير صالحة للمستخدم {user_id}")
                return False

            # Store client
            self.clients[user_id] = client

            # Load user tasks
            await self.refresh_user_tasks(user_id)

            # Set up event handlers for this user
            await self._setup_event_handlers(user_id, client)

            user = await client.get_me()
            logger.info(f"✅ تم تشغيل UserBot للمستخدم {user_id} ({user.first_name})")

            return True

        except AuthKeyUnregisteredError:
            logger.error(f"مفتاح المصادقة غير صالح للمستخدم {user_id}")
            # Remove invalid session from database
            self.db.delete_user_session(user_id)
            return False

        except Exception as e:
            logger.error(f"خطأ في تشغيل UserBot للمستخدم {user_id}: {e}")
            return False

    def apply_text_cleaning(self, message_text: str, task_id: int) -> str:
        """Apply text cleaning based on task settings"""
        if not message_text:
            return message_text

        try:
            # Get text cleaning settings for this task
            settings = self.db.get_text_cleaning_settings(task_id)
            if not settings:
                return message_text

            cleaned_text = message_text

            # 1. Remove links
            if settings.get('remove_links', False):
                # Remove HTTP/HTTPS URLs
                cleaned_text = re.sub(r'https?://[^\s]+', '', cleaned_text)
                # Remove Telegram links (t.me)
                cleaned_text = re.sub(r't\.me/[^\s]+', '', cleaned_text)
                # Remove www links
                cleaned_text = re.sub(r'www\.[^\s]+', '', cleaned_text)
                # Remove domain-like patterns (improved pattern for sites like meyon.com.ye/path)
                cleaned_text = re.sub(r'\b[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.([a-zA-Z]{2,6}\.?)+(/[^\s]*)?', '', cleaned_text)
                logger.debug(f"🧹 تم حذف الروابط من المهمة {task_id}")

            # 2. Remove emojis
            if settings.get('remove_emojis', False):
                # Remove emojis using Unicode ranges
                emoji_pattern = re.compile(
                    "["
                    "\U0001F600-\U0001F64F"  # emoticons
                    "\U0001F300-\U0001F5FF"  # symbols & pictographs
                    "\U0001F680-\U0001F6FF"  # transport & map symbols
                    "\U0001F1E0-\U0001F1FF"  # flags (iOS)
                    "\U00002700-\U000027BF"  # dingbats
                    "\U0001f926-\U0001f937"  # supplemental symbols
                    "\U00010000-\U0010ffff"  # supplemental characters
                    "\u2640-\u2642"          # gender symbols
                    "\u2600-\u2B55"          # misc symbols
                    "\u200d"                 # zero width joiner
                    "\u23cf"                 # various symbols
                    "\u23e9-\u23f3"          # symbol range
                    "\u23f8-\u23f9"          # symbol range
                    "\u3030"                 # wavy dash
                    "]+",
                    flags=re.UNICODE
                )
                cleaned_text = emoji_pattern.sub('', cleaned_text)
                logger.debug(f"🧹 تم حذف الايموجيات من المهمة {task_id}")

            # 3. Remove hashtags
            if settings.get('remove_hashtags', False):
                # Remove hashtags (# followed by word characters)
                cleaned_text = re.sub(r'#\w+', '', cleaned_text)
                logger.debug(f"🧹 تم حذف الهاشتاقات من المهمة {task_id}")

            # 4. Remove phone numbers (improved patterns to avoid years like 2025)
            if settings.get('remove_phone_numbers', False):
                # Remove various phone number formats (more specific patterns)
                phone_patterns = [
                    r'\+\d{1,4}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{4,9}',  # International with +
                    r'\b\d{3}[-.\s]\d{3}[-.\s]\d{4}\b',  # US format with separators
                    r'\b\d{4}[-.\s]\d{3}[-.\s]\d{3}\b',  # Some international with separators
                    r'\b\d{2}[-.\s]\d{4}[-.\s]\d{4}\b',  # Another format with separators
                    r'\b\d{10,15}\b',  # Long sequences of digits (10-15 digits) likely phone numbers
                    r'\(\d{3}\)\s?\d{3}[-.\s]?\d{4}',  # Format like (123) 456-7890
                ]
                for pattern in phone_patterns:
                    cleaned_text = re.sub(pattern, '', cleaned_text)
                logger.debug(f"🧹 تم حذف أرقام الهواتف من المهمة {task_id}")

            # 5. Remove lines with specific keywords
            if settings.get('remove_lines_with_keywords', False):
                keywords = self.db.get_text_cleaning_keywords(task_id)
                if keywords:
                    lines = cleaned_text.split('\n')
                    filtered_lines = []
                    for line in lines:
                        should_remove = False
                        for keyword in keywords:
                            if keyword.lower() in line.lower():
                                should_remove = True
                                break
                        if not should_remove:
                            filtered_lines.append(line)
                    cleaned_text = '\n'.join(filtered_lines)
                    logger.debug(f"🧹 تم حذف الأسطر التي تحتوي على الكلمات المحددة من المهمة {task_id}")

            # Clean up extra whitespace within lines first
            lines = cleaned_text.split('\n')
            cleaned_lines = []
            for line in lines:
                # Clean whitespace within each line but preserve the line structure
                cleaned_line = re.sub(r'[ \t]+', ' ', line.strip())
                cleaned_lines.append(cleaned_line)
            cleaned_text = '\n'.join(cleaned_lines)

            # 6. Remove empty lines AFTER all other cleaning operations
            if settings.get('remove_empty_lines', False):
                # Split by lines and filter empty ones while preserving structure
                lines = cleaned_text.split('\n')
                filtered_lines = []

                for i, line in enumerate(lines):
                    if line.strip():  # Line has content
                        filtered_lines.append(line)
                    else:  # Empty line
                        # Only keep empty line if it's between two content lines
                        if (i > 0 and i < len(lines) - 1 and
                            lines[i-1].strip() and lines[i+1].strip()):
                            filtered_lines.append('')

                cleaned_text = '\n'.join(filtered_lines)
                logger.debug(f"🧹 تم حذف الأسطر الفارغة الزائدة من المهمة {task_id} (في النهاية)")

            if cleaned_text != message_text:
                logger.info(f"🧹 تم تنظيف النص للمهمة {task_id} - الطول الأصلي: {len(message_text)}, بعد التنظيف: {len(cleaned_text)}")

            return cleaned_text

        except Exception as e:
            logger.error(f"خطأ في تنظيف النص للمهمة {task_id}: {e}")
            return message_text

    async def _setup_event_handlers(self, user_id: int, client: TelegramClient):
        """Set up message forwarding event handlers"""

        @client.on(events.NewMessage(incoming=True))
        async def message_handler(event):
            try:
                logger.warning(f"🔔 *** استقبال رسالة جديدة من المستخدم {user_id} ***")
                logger.warning(f"📍 Chat ID: {event.chat_id}, Message: {event.text[:50] if event.text else 'رسالة بدون نص'}...")

                # Immediate check for our target chat
                if event.chat_id == -1002289754739:
                    logger.error(f"🎯 *** رسالة من محادثة Hidar! Chat ID: {event.chat_id} ***")
                    logger.error(f"🎯 *** بدء معالجة الرسالة للتوجيه... ***")
                # Get user tasks
                tasks = self.user_tasks.get(user_id, [])


                # Get source chat ID and username first
                source_chat_id = event.chat_id
                source_username = getattr(event.chat, 'username', None)

                # Special monitoring for the specific chat mentioned by user
                # Enhanced logging for the specific task
                if source_chat_id == -1002289754739:
                    logger.warning(f"🎯 *** رسالة من المحادثة المطلوبة (Hidar)! Chat ID: {source_chat_id} ***")
                    logger.warning(f"🎯 *** بدء معالجة الرسالة للتوجيه ***")
                    logger.warning(f"🎯 *** عدد المهام المتاحة: {len(tasks)} ***")

                if not tasks:
                    logger.warning(f"⚠️ لا توجد مهام للمستخدم {user_id}")
                    return

                logger.info(f"📋 عدد المهام المتاحة للمستخدم {user_id}: {len(tasks)}")

                # Log all tasks for debugging
                for i, task in enumerate(tasks, 1):
                    task_name = task.get('task_name', f"مهمة {task['id']}")
                    logger.info(f"📋 مهمة {i}: '{task_name}' - مصدر='{task['source_chat_id']}' → هدف='{task['target_chat_id']}'")
                    if str(task['source_chat_id']) == '-1002289754739':
                        logger.warning(f"🎯 تم العثور على المهمة المطلوبة: {task_name}")

                # Check media filters first
                message_media_type = self.get_message_media_type(event.message)
                has_text_caption = bool(event.message.text)  # Check if message has text/caption
                logger.info(f"🎬 نوع الوسائط للرسالة: {message_media_type}, يحتوي على نص/caption: {has_text_caption}")

                # Find matching tasks for this source chat
                matching_tasks = []
                logger.info(f"🔍 البحث عن مهام مطابقة للمحادثة {source_chat_id} (username: {source_username})")

                for task in tasks:
                    task_source_id = str(task['source_chat_id'])
                    task_name = task.get('task_name', f"مهمة {task['id']}")
                    task_id = task.get('id')

                    logger.info(f"🔍 فحص المهمة '{task_name}': مصدر='{task_source_id}' ضد '{source_chat_id}', هدف='{task['target_chat_id']}'")

                    # Convert both IDs to string and compare
                    source_chat_id_str = str(source_chat_id)
                    if task_source_id == source_chat_id_str:
                        logger.info(f"✅ تطابق مباشر: '{task_source_id}' == '{source_chat_id_str}' (types: {type(task_source_id)}, {type(source_chat_id_str)})")

                        # Check admin filter first (if enabled)
                        logger.error(f"🚨 === بدء فحص فلتر المشرفين للمهمة {task_id} والمرسل {event.sender_id} ===")
                        admin_allowed = self.is_admin_allowed(task_id, event.sender_id)
                        logger.error(f"🚨 === نتيجة فحص فلتر المشرفين للمهمة {task_id}: {admin_allowed} ===")

                        # Check media filter
                        media_allowed = self.is_media_allowed(task_id, message_media_type)

                        # Check word filters
                        message_text = event.message.text or ""
                        word_filter_allowed = self.is_message_allowed_by_word_filter(task_id, message_text)

                        # Decision is based on the primary media type, not the caption
                        # For text messages with media, we check the media type
                        # For pure text messages, we check text filter
                        if message_media_type == 'text':
                            # Pure text message - check admin, text filter and word filter
                            is_message_allowed = admin_allowed and self.is_media_allowed(task_id, 'text') and word_filter_allowed
                            filter_type = "النص"
                            logger.error(f"🚨 === فحص رسالة نصية: admin={admin_allowed}, media={self.is_media_allowed(task_id, 'text')}, word={word_filter_allowed}, نتيجة نهائية={is_message_allowed} ===")
                        else:
                            # Media message (photo, video, etc.) - check admin, media filter and word filter for caption
                            is_message_allowed = admin_allowed and media_allowed and word_filter_allowed
                            filter_type = f"الوسائط ({message_media_type})"

                        logger.error(f"🚨 === قرار نهائي: is_message_allowed = {is_message_allowed} ===")

                        if is_message_allowed:
                            logger.error(f"🚨 === إضافة المهمة للقائمة المطابقة ===")
                            matching_tasks.append(task)
                            if has_text_caption and message_media_type != 'text':
                                logger.info(f"✅ الرسالة مسموحة - {filter_type} مسموح مع caption وفلاتر الكلمات")
                            else:
                                logger.info(f"✅ {filter_type} مسموح لهذه المهمة وفلاتر الكلمات")
                        else:
                            logger.error(f"🚨 === رفض المهمة - الرسالة محظورة ===")
                            # Check which filter blocked the message
                            if not admin_allowed:
                                logger.error(f"🚫 الرسالة محظورة بواسطة فلتر المشرفين - المرسل {event.sender_id} غير مسموح")
                            elif not media_allowed:
                                logger.error(f"🚫 {filter_type} محظور لهذه المهمة (فلتر الوسائط)")
                            elif not word_filter_allowed:
                                logger.error(f"🚫 الرسالة محظورة بواسطة فلتر الكلمات")
                            else:
                                if has_text_caption and message_media_type != 'text':
                                    logger.error(f"🚫 {filter_type} محظور لهذه المهمة (مع caption)")
                                else:
                                    logger.error(f"🚫 {filter_type} محظور لهذه المهمة")
                    else:
                        logger.info(f"❌ لا يوجد تطابق للمهمة '{task_name}': '{task_source_id}' != '{source_chat_id_str}' (types: {type(task_source_id)}, {type(source_chat_id_str)})")

                if not matching_tasks:
                    logger.debug(f"لا توجد مهام مطابقة للمحادثة {source_chat_id} للمستخدم {user_id}")
                    return

                logger.info(f"تم العثور على {len(matching_tasks)} مهمة مطابقة للمحادثة {source_chat_id}")

                # Check advanced features once per message (using first matching task for settings)
                first_task = matching_tasks[0]
                original_text = event.message.text or ""
                cleaned_text = self.apply_text_cleaning(original_text, first_task['id']) if original_text else original_text
                modified_text = self.apply_text_replacements(first_task['id'], cleaned_text) if cleaned_text else cleaned_text
                text_for_limits = modified_text or original_text

                # Check advanced features before processing any targets
                if not await self._check_advanced_features(first_task['id'], text_for_limits, user_id):
                    logger.info(f"🚫 الرسالة محظورة بواسطة إحدى الميزات المتقدمة - تم رفضها لجميع الأهداف")
                    return

                # Apply global forwarding delay once per message
                await self._apply_forwarding_delay(first_task['id'])

                # Initialize album collector for this user if needed
                if user_id not in self.album_collectors:
                    self.album_collectors[user_id] = AlbumCollector()
                
                album_collector = self.album_collectors[user_id]

                # Forward message to all target chats
                for i, task in enumerate(matching_tasks):
                    try:
                        target_chat_id = str(task['target_chat_id']).strip()
                        task_name = task.get('task_name', f"مهمة {task['id']}")

                        # Get task forward mode and forwarding settings
                        forward_mode = task.get('forward_mode', 'forward')
                        forwarding_settings = self.get_forwarding_settings(task['id'])
                        split_album_enabled = forwarding_settings.get('split_album_enabled', False)
                        mode_text = "نسخ" if forward_mode == 'copy' else "توجيه"

                        logger.info(f"🔄 بدء {mode_text} رسالة من {source_chat_id} إلى {target_chat_id} (المهمة: {task_name})")
                        logger.info(f"📤 تفاصيل الإرسال: مصدر='{source_chat_id}', هدف='{target_chat_id}', وضع={mode_text}, تقسيم_ألبوم={split_album_enabled}, مستخدم={user_id}")

                        # Check if this is an album message that needs special handling
                        if album_collector.should_collect_album(event.message, forward_mode, split_album_enabled):
                            group_id = event.message.grouped_id
                            if album_collector.is_album_processed(group_id):
                                logger.info(f"📸 تجاهل رسالة الألبوم - تم معالجتها بالفعل: {group_id}")
                                continue
                            
                            # Add to album collection
                            album_collector.add_message(event.message, {
                                'task': task,
                                'target_chat_id': target_chat_id,
                                'task_name': task_name,
                                'mode_text': mode_text,
                                'forward_mode': forward_mode,
                                'forwarding_settings': forwarding_settings,
                                'user_id': user_id,
                                'index': i
                            })
                            
                            # Set timer to process album (give time for all messages to arrive)
                            if group_id in album_collector.timers:
                                album_collector.timers[group_id].cancel()
                            
                            album_collector.timers[group_id] = asyncio.create_task(
                                self._process_album_delayed(user_id, group_id, client)
                            )
                            
                            continue  # Skip individual processing

                        # Parse target chat ID
                        if target_chat_id.startswith('@'):
                            target_entity = target_chat_id
                            logger.info(f"🎯 استخدام اسم المستخدم كهدف: {target_entity}")
                        else:
                            target_entity = int(target_chat_id)
                            logger.info(f"🎯 استخدام معرف رقمي كهدف: {target_entity}")

                        # Get target chat info before forwarding
                        try:
                            target_chat = await client.get_entity(target_entity)
                            target_title = getattr(target_chat, 'title', getattr(target_chat, 'first_name', str(target_entity)))
                            logger.info(f"✅ تم العثور على المحادثة الهدف: {target_title} ({target_entity})")
                        except Exception as entity_error:
                            logger.error(f"❌ لا يمكن الوصول للمحادثة الهدف {target_entity}: {entity_error}")
                            continue

                        # Get message formatting settings for this task
                        message_settings = self.get_message_settings(task['id'])

                        # Apply text cleaning and replacements (use same as checked above)
                        cleaned_text = self.apply_text_cleaning(original_text, task['id']) if original_text else original_text
                        modified_text = self.apply_text_replacements(task['id'], cleaned_text) if cleaned_text else cleaned_text

                        # Apply translation if enabled
                        translated_text = await self.apply_translation(task['id'], modified_text) if modified_text else modified_text

                        # Apply text formatting
                        formatted_text = self.apply_text_formatting(task['id'], translated_text) if translated_text else translated_text

                        # Apply header and footer formatting
                        final_text = self.apply_message_formatting(formatted_text, message_settings)

                        # Check if we need to use copy mode due to formatting
                        requires_copy_mode = (
                            original_text != modified_text or  # Text replacements applied
                            modified_text != translated_text or  # Translation applied
                            translated_text != formatted_text or  # Text formatting applied
                            message_settings['header_enabled'] or  # Header enabled
                            message_settings['footer_enabled'] or  # Footer enabled
                            message_settings['inline_buttons_enabled']  # Inline buttons enabled
                        )

                        # Log changes if text was modified
                        if original_text != final_text and original_text:
                            logger.info(f"🔄 تم تطبيق تنسيق الرسالة: '{original_text}' → '{final_text}'")

                        # Prepare inline buttons if enabled
                        inline_buttons = None
                        if message_settings['inline_buttons_enabled']:
                            inline_buttons = self.build_inline_buttons(task['id'])
                            if inline_buttons:
                                logger.info(f"🔘 تم بناء {len(inline_buttons)} صف من الأزرار الإنلاين للمهمة {task['id']}")
                            else:
                                logger.warning(f"⚠️ فشل في بناء الأزرار الإنلاين للمهمة {task['id']}")

                        # Get forwarding settings
                        forwarding_settings = self.get_forwarding_settings(task['id'])

                        # Apply sending interval before each target (except first)
                        if i > 0:
                            await self._apply_sending_interval(task['id'])

                        # Send message based on forward mode
                        logger.info(f"📨 جاري إرسال الرسالة...")

                        if forward_mode == 'copy' or requires_copy_mode:
                            # Copy mode: send as new message with all formatting applied
                            if requires_copy_mode:
                                logger.info(f"🔄 استخدام وضع النسخ بسبب التنسيق المطبق")

                            if event.message.media:
                                # Check media type to handle web page separately
                                from telethon.tl.types import MessageMediaWebPage
                                if isinstance(event.message.media, MessageMediaWebPage):
                                    # Web page - send as text message
                                    # Process spoiler entities if present
                                    message_text = final_text or event.message.text or "رسالة"
                                    processed_text, spoiler_entities = self._process_spoiler_entities(message_text)
                                    
                                    if spoiler_entities:
                                        # Send with spoiler entities
                                        forwarded_msg = await client.send_message(
                                            target_entity,
                                            processed_text,
                                            link_preview=forwarding_settings['link_preview_enabled'],
                                            silent=forwarding_settings['silent_notifications'],
                                            formatting_entities=spoiler_entities
                                        )
                                    else:
                                        # Send normally
                                        forwarded_msg = await client.send_message(
                                            target_entity,
                                            processed_text,
                                            link_preview=forwarding_settings['link_preview_enabled'],
                                            silent=forwarding_settings['silent_notifications'],
                                            parse_mode='HTML'
                                        )
                                else:
                                    # Regular media message with caption handling
                                    # Check if caption should be removed
                                    caption_text = final_text
                                    text_cleaning_settings = self.db.get_text_cleaning_settings(task['id'])
                                    if text_cleaning_settings and text_cleaning_settings.get('remove_caption', False):
                                        caption_text = None
                                        logger.info(f"🗑️ تم حذف التسمية التوضيحية للمهمة {task['id']}")
                                    
                                    # Check if album should be split
                                    split_album_enabled = forwarding_settings.get('split_album_enabled', False)
                                    
                                    # Handle album splitting logic
                                    if split_album_enabled:
                                        # Split album: send each media individually
                                        logger.info(f"📸 تفكيك الألبوم: إرسال الوسائط بشكل منفصل للمهمة {task['id']}")
                                        forwarded_msg = await client.send_file(
                                            target_entity,
                                            event.message.media,
                                            caption=caption_text,
                                            silent=forwarding_settings['silent_notifications'],
                                            parse_mode='HTML' if caption_text else None,
                                            force_document=False
                                        )
                                    else:
                                        # Keep album grouped: send as new media (copy mode)
                                        logger.info(f"📸 إبقاء الألبوم مجمع للمهمة {task['id']} (وضع النسخ)")
                                        # In copy mode, we always send as new media, not forward
                                        forwarded_msg = await client.send_file(
                                            target_entity,
                                            event.message.media,
                                            caption=caption_text,
                                            silent=forwarding_settings['silent_notifications'],
                                            parse_mode='HTML' if caption_text else None,
                                            force_document=False
                                        )
                            elif event.message.text or final_text:
                                # Pure text message
                                # Process spoiler entities if present
                                message_text = final_text or "رسالة"
                                processed_text, spoiler_entities = self._process_spoiler_entities(message_text)
                                
                                if spoiler_entities:
                                    # Send with spoiler entities
                                    forwarded_msg = await client.send_message(
                                        target_entity,
                                        processed_text,
                                        link_preview=forwarding_settings['link_preview_enabled'],
                                        silent=forwarding_settings['silent_notifications'],
                                        formatting_entities=spoiler_entities
                                    )
                                else:
                                    # Send normally
                                    forwarded_msg = await client.send_message(
                                        target_entity,
                                        processed_text,
                                        link_preview=forwarding_settings['link_preview_enabled'],
                                        silent=forwarding_settings['silent_notifications'],
                                        parse_mode='HTML'
                                    )
                            else:
                                # Fallback to forward for other types
                                forwarded_msg = await client.forward_messages(
                                    target_entity,
                                    event.message,
                                    silent=forwarding_settings['silent_notifications']
                                )
                        else:
                            # Forward mode: check if we need copy mode
                            if requires_copy_mode:
                                logger.info(f"🔄 تحويل إلى وضع النسخ بسبب التنسيق")
                                if event.message.media:
                                    # Check media type to handle web page separately
                                    from telethon.tl.types import MessageMediaWebPage
                                    if isinstance(event.message.media, MessageMediaWebPage):
                                        # Web page - send as text message
                                        # Process spoiler entities if present
                                        message_text = final_text or event.message.text or "رسالة"
                                        processed_text, spoiler_entities = self._process_spoiler_entities(message_text)
                                        
                                        if spoiler_entities:
                                            # Send with spoiler entities
                                            forwarded_msg = await client.send_message(
                                                target_entity,
                                                processed_text,
                                                link_preview=forwarding_settings['link_preview_enabled'],
                                                silent=forwarding_settings['silent_notifications'],
                                                formatting_entities=spoiler_entities
                                            )
                                        else:
                                            # Send normally
                                            forwarded_msg = await client.send_message(
                                                target_entity,
                                                processed_text,
                                                link_preview=forwarding_settings['link_preview_enabled'],
                                                silent=forwarding_settings['silent_notifications'],
                                                parse_mode='HTML'
                                            )
                                    else:
                                        # Regular media message with caption handling
                                        # Check if caption should be removed
                                        caption_text = final_text
                                        text_cleaning_settings = self.db.get_text_cleaning_settings(task['id'])
                                        if text_cleaning_settings and text_cleaning_settings.get('remove_caption', False):
                                            caption_text = None
                                            logger.info(f"🗑️ تم حذف التسمية التوضيحية للمهمة {task['id']}")
                                        
                                        # Check if album should be split
                                        split_album_enabled = forwarding_settings.get('split_album_enabled', False)
                                        
                                        # Handle album splitting logic
                                        if split_album_enabled:
                                            # Split album: send each media individually
                                            logger.info(f"📸 تفكيك الألبوم: إرسال الوسائط بشكل منفصل للمهمة {task['id']}")
                                            forwarded_msg = await client.send_file(
                                                target_entity,
                                                event.message.media,
                                                caption=caption_text,
                                                silent=forwarding_settings['silent_notifications'],
                                                parse_mode='HTML' if caption_text else None,
                                                force_document=False
                                            )
                                        else:
                                            # Keep album grouped: send as new media (copy mode)
                                            logger.info(f"📸 إبقاء الألبوم مجمع للمهمة {task['id']} (تحويل لوضع النسخ)")
                                            # In forward mode with requires_copy_mode, we also send as new media
                                            forwarded_msg = await client.send_file(
                                                target_entity,
                                                event.message.media,
                                                caption=caption_text,
                                                silent=forwarding_settings['silent_notifications'],
                                                parse_mode='HTML' if caption_text else None,
                                                force_document=False
                                            )
                                else:
                                    # Process spoiler entities if present
                                    message_text = final_text or "رسالة"
                                    processed_text, spoiler_entities = self._process_spoiler_entities(message_text)
                                    
                                    if spoiler_entities:
                                        # Send with spoiler entities
                                        forwarded_msg = await client.send_message(
                                            target_entity,
                                            processed_text,
                                            link_preview=forwarding_settings['link_preview_enabled'],
                                            silent=forwarding_settings['silent_notifications'],
                                            formatting_entities=spoiler_entities
                                        )
                                    else:
                                        # Send normally
                                        forwarded_msg = await client.send_message(
                                            target_entity,
                                            processed_text,
                                            link_preview=forwarding_settings['link_preview_enabled'],
                                            silent=forwarding_settings['silent_notifications'],
                                            parse_mode='HTML'
                                        )
                            else:
                                # Check if we need copy mode for caption removal or album splitting on media
                                text_cleaning_settings = self.db.get_text_cleaning_settings(task['id'])
                                needs_copy_for_caption = (event.message.media and 
                                                        text_cleaning_settings and 
                                                        text_cleaning_settings.get('remove_caption', False))
                                needs_copy_for_album = (event.message.media and 
                                                      forwarding_settings.get('split_album_enabled', False))
                                
                                if needs_copy_for_caption or needs_copy_for_album:
                                    # Use copy mode for media modifications
                                    if event.message.media:
                                        from telethon.tl.types import MessageMediaWebPage
                                        if isinstance(event.message.media, MessageMediaWebPage):
                                            # Web page - send as text message
                                            forwarded_msg = await client.send_message(
                                                target_entity,
                                                event.message.text or "رسالة",
                                                link_preview=forwarding_settings['link_preview_enabled'],
                                                silent=forwarding_settings['silent_notifications']
                                            )
                                        else:
                                            # Regular media message with caption handling
                                            caption_text = event.message.text
                                            if needs_copy_for_caption:
                                                caption_text = None
                                                logger.info(f"🗑️ تم حذف التسمية التوضيحية للمهمة {task['id']}")
                                            
                                            # Handle album splitting logic
                                            if needs_copy_for_album:
                                                # Split album: send each media individually
                                                logger.info(f"📸 تفكيك الألبوم: إرسال الوسائط بشكل منفصل للمهمة {task['id']}")
                                                forwarded_msg = await client.send_file(
                                                    target_entity,
                                                    event.message.media,
                                                    caption=caption_text,
                                                    silent=forwarding_settings['silent_notifications'],
                                                    force_document=False
                                                )
                                            else:
                                                # Keep album grouped
                                                logger.info(f"📸 إبقاء الألبوم مجمع للمهمة {task['id']}")
                                                if hasattr(event.message, 'grouped_id') and event.message.grouped_id:
                                                    # Forward as album
                                                    forwarded_msg = await client.forward_messages(
                                                        target_entity,
                                                        event.message,
                                                        silent=forwarding_settings['silent_notifications']
                                                    )
                                                else:
                                                    # Single media
                                                    forwarded_msg = await client.send_file(
                                                        target_entity,
                                                        event.message.media,
                                                        caption=caption_text,
                                                        silent=forwarding_settings['silent_notifications'],
                                                        force_document=False
                                                    )
                                    else:
                                        # Regular text forward
                                        forwarded_msg = await client.forward_messages(
                                            target_entity,
                                            event.message,
                                            silent=forwarding_settings['silent_notifications']
                                        )
                                else:
                                    # No formatting changes, forward normally
                                    forwarded_msg = await client.forward_messages(
                                        target_entity,
                                        event.message,
                                        silent=forwarding_settings['silent_notifications']
                                    )

                        if forwarded_msg:
                            msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                            logger.info(f"✅ تم توجيه الرسالة بنجاح من {source_chat_id} إلى {target_chat_id}")
                            logger.info(f"📝 معرف الرسالة المُوجهة: {msg_id} (المهمة: {task_name})")

                            # Save message mapping for synchronization
                            try:
                                self.db.save_message_mapping(
                                    task_id=task['id'],
                                    source_chat_id=str(source_chat_id),
                                    source_message_id=event.message.id,
                                    target_chat_id=str(target_chat_id),
                                    target_message_id=msg_id
                                )
                                logger.info(f"💾 تم حفظ تطابق الرسالة للمزامنة: {source_chat_id}:{event.message.id} → {target_chat_id}:{msg_id}")
                            except Exception as mapping_error:
                                logger.error(f"❌ فشل في حفظ تطابق الرسالة: {mapping_error}")

                            # Apply post-forwarding settings
                            await self.apply_post_forwarding_settings(client, target_entity, msg_id, forwarding_settings, task['id'])

                            # Apply sending interval if there are more targets to process
                            current_index = matching_tasks.index(task)
                            if current_index < len(matching_tasks) - 1:  # Not the last task
                                await self._apply_sending_interval(task['id'])

                            # If inline buttons are enabled, notify bot to add them
                            if inline_buttons and message_settings['inline_buttons_enabled']:
                                await self.notify_bot_to_add_buttons(target_chat_id, msg_id, task['id'])
                        else:
                            logger.warning(f"⚠️ تم التوجيه لكن لم يتم الحصول على معرف الرسالة")

                    except Exception as forward_error:
                        task_name = task.get('task_name', f"مهمة {task['id']}")
                        logger.error(f"❌ فشل في توجيه الرسالة (المهمة: {task_name}) للمستخدم {user_id}")
                        logger.error(f"💥 تفاصيل الخطأ: {str(forward_error)}")
                        logger.error(f"🔍 مصدر={source_chat_id}, هدف={target_chat_id}")

                        # Additional error details
                        error_str = str(forward_error)
                        if "CHAT_ADMIN_REQUIRED" in error_str:
                            logger.error(f"🚫 يجب أن يكون UserBot مشرف في {target_chat_id}")
                        elif "USER_BANNED_IN_CHANNEL" in error_str:
                            logger.error(f"🚫 UserBot محظور في {target_chat_id}")
                        elif "CHANNEL_PRIVATE" in error_str:
                            logger.error(f"🚫 لا يمكن الوصول إلى {target_chat_id} - قناة خاصة")
                        elif "PEER_ID_INVALID" in error_str:
                            logger.error(f"🚫 معرف المحادثة {target_chat_id} غير صالح أو غير متاح")
                        elif "CHAT_WRITE_FORBIDDEN" in error_str:
                            logger.error(f"🚫 لا يُسمح للـ UserBot بالكتابة في {target_chat_id}")
                        else:
                            logger.error(f"🚫 خطأ غير معروف: {error_str}")

            except Exception as e:
                logger.error(f"خطأ في معالج الرسائل للمستخدم {user_id}: {e}")

        @client.on(events.MessageEdited)
        async def message_edit_handler(event):
            """Handle message edit synchronization"""
            try:
                source_chat_id = event.chat_id
                source_message_id = event.message.id

                logger.info(f"🔄 تم تعديل رسالة: Chat={source_chat_id}, Message={source_message_id}")

                # Get tasks that match this source chat
                tasks = self.user_tasks.get(user_id, [])
                matching_tasks = [task for task in tasks if str(task['source_chat_id']) == str(source_chat_id)]

                if not matching_tasks:
                    return

                # Check sync settings for each matching task
                for task in matching_tasks:
                    task_id = task['id']
                    forwarding_settings = self.get_forwarding_settings(task_id)

                    if not forwarding_settings.get('sync_edit_enabled', False):
                        continue

                    logger.info(f"🔄 مزامنة التعديل مفعلة للمهمة {task_id}")

                    # Find all target messages that were forwarded from this source message
                    message_mappings = self.db.get_message_mappings_by_source(task_id, source_chat_id, source_message_id)

                    for mapping in message_mappings:
                        target_chat_id = mapping['target_chat_id']
                        target_message_id = mapping['target_message_id']

                        try:
                            # Get target entity
                            target_entity = await client.get_entity(int(target_chat_id))

                            # Update the target message with the edited content
                            await client.edit_message(
                                target_entity,
                                target_message_id,
                                event.message.text or event.message.message,
                                file=None if not event.message.media else event.message.media
                            )

                            logger.info(f"✅ تم تحديث الرسالة المتزامنة: {target_chat_id}:{target_message_id}")

                        except Exception as sync_error:
                            logger.error(f"❌ فشل في مزامنة تعديل الرسالة: {sync_error}")

            except Exception as e:
                logger.error(f"خطأ في معالج تعديل الرسائل للمستخدم {user_id}: {e}")

        @client.on(events.MessageDeleted)
        async def message_delete_handler(event):
            """Handle message delete synchronization"""
            try:
                if not hasattr(event, 'chat_id') or not hasattr(event, 'deleted_ids'):
                    return

                source_chat_id = event.chat_id
                deleted_ids = event.deleted_ids

                logger.info(f"🗑️ تم حذف رسائل: Chat={source_chat_id}, IDs={deleted_ids}")

                # Get tasks that match this source chat
                tasks = self.user_tasks.get(user_id, [])
                matching_tasks = [task for task in tasks if str(task['source_chat_id']) == str(source_chat_id)]

                if not matching_tasks:
                    return

                # Check sync settings for each matching task and deleted message
                for task in matching_tasks:
                    task_id = task['id']
                    forwarding_settings = self.get_forwarding_settings(task_id)

                    if not forwarding_settings.get('sync_delete_enabled', False):
                        continue

                    logger.info(f"🗑️ مزامنة الحذف مفعلة للمهمة {task_id}")

                    for source_message_id in deleted_ids:
                        # Find all target messages that were forwarded from this source message
                        message_mappings = self.db.get_message_mappings_by_source(task_id, source_chat_id, source_message_id)

                        for mapping in message_mappings:
                            target_chat_id = mapping['target_chat_id']
                            target_message_id = mapping['target_message_id']

                            try:
                                # Get target entity
                                target_entity = await client.get_entity(int(target_chat_id))

                                # Delete the target message
                                await client.delete_messages(target_entity, target_message_id)

                                logger.info(f"✅ تم حذف الرسالة المتزامنة: {target_chat_id}:{target_message_id}")

                                # Remove the mapping from database since message is deleted
                                self.db.delete_message_mapping(mapping['id'])

                            except Exception as sync_error:
                                logger.error(f"❌ فشل في مزامنة حذف الرسالة: {sync_error}")

            except Exception as e:
                logger.error(f"خطأ في معالج حذف الرسائل للمستخدم {user_id}: {e}")

    async def refresh_user_tasks(self, user_id: int):
        """Refresh user tasks from database"""
        try:
            tasks = self.db.get_active_tasks(user_id)
            self.user_tasks[user_id] = tasks

            # Log detailed task information
            logger.info(f"🔄 تم تحديث {len(tasks)} مهمة للمستخدم {user_id}")

            if tasks:
                logger.info(f"📋 تفاصيل المهام المُحدثة للمستخدم {user_id}:")
                for i, task in enumerate(tasks, 1):
                    task_name = task.get('task_name', f"مهمة {task['id']}")
                    source_id = task['source_chat_id']
                    target_id = task['target_chat_id']
                    logger.info(f"  {i}. '{task_name}' (ID: {task['id']})")
                    logger.info(f"     📥 مصدر: '{source_id}'")
                    logger.info(f"     📤 هدف: '{target_id}'")

                    # Special check for the mentioned chat
                    if str(source_id) == '-1002289754739':
                        logger.warning(f"🎯 تم العثور على المهمة للمحادثة المطلوبة: {task_name}")
                        logger.warning(f"🎯 سيتم توجيه الرسائل من {source_id} إلى {target_id}")
            else:
                logger.warning(f"⚠️ لا توجد مهام نشطة للمستخدم {user_id}")

        except Exception as e:
            logger.error(f"خطأ في refresh_user_tasks للمستخدم {user_id}: {e}")
            return []

    async def notify_bot_to_add_buttons(self, chat_id: int, message_id: int, task_id: int):
        """Notify the bot to add inline buttons to a message"""
        try:
            import asyncio
            import json

            # Store the message info for the bot to process
            notification_data = {
                'chat_id': chat_id,
                'message_id': message_id,
                'task_id': task_id,
                'action': 'add_inline_buttons'
            }

            # Use a simple file-based notification system
            import tempfile
            import os

            notification_file = f"/tmp/bot_notification_{chat_id}_{message_id}.json"
            with open(notification_file, 'w', encoding='utf-8') as f:
                json.dump(notification_data, f, ensure_ascii=False)

            logger.info(f"🔔 تم إرسال إشعار للبوت لإضافة أزرار إنلاين: قناة={chat_id}, رسالة={message_id}, مهمة={task_id}")

        except Exception as e:
            logger.error(f"❌ خطأ في إشعار البوت لإضافة الأزرار: {e}")

    def get_message_media_type(self, message):
        """Determine the media type of a message"""
        if message.text and not message.media:
            return 'text'
        elif message.photo:
            return 'photo'
        elif message.video:
            return 'video'
        elif message.audio:
            return 'audio'
        elif message.document:
            if message.document.mime_type and 'image/gif' in message.document.mime_type:
                return 'animation'
            return 'document'
        elif message.voice:
            return 'voice'
        elif message.video_note:
            return 'video_note'
        elif message.sticker:
            return 'sticker'
        elif message.geo or message.venue:
            return 'location'
        elif message.contact:
            return 'contact'
        elif message.poll:
            return 'poll'
        else:
            return 'text'  # Default fallback

    def is_media_allowed(self, task_id, media_type):
        """Check if media type is allowed for this task"""
        try:
            from database.database import Database
            db = Database()
            filters = db.get_task_media_filters(task_id)

            # Default is allowed if no filter is set
            is_allowed = filters.get(media_type, True)
            logger.info(f"🔍 فحص فلتر الوسائط: المهمة {task_id}, النوع {media_type}, مسموح: {is_allowed}")
            return is_allowed
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر الوسائط: {e}")
            return True  # Default to allowed on error

    def is_admin_allowed(self, task_id, sender_id):
        """Check if message sender is allowed by admin filters"""
        try:
            from database.database import Database
            db = Database()

            logger.error(f"🚨 [ADMIN FILTER DEBUG] المهمة: {task_id}, المرسل: {sender_id}")

            # Check if admin filter is enabled for this task
            admin_filter_enabled = db.is_advanced_filter_enabled(task_id, 'admin')
            logger.error(f"🚨 [ADMIN FILTER DEBUG] فلتر المشرفين مُفعل: {admin_filter_enabled}")

            if not admin_filter_enabled:
                logger.error(f"🚨 فلتر المشرفين غير مُفعل للمهمة {task_id} - السماح للجميع")
                return True

            # DEBUG: Get all allowed admins for this task
            allowed_admins = db.get_task_allowed_admins(task_id)
            logger.error(f"🚨 [ADMIN FILTER DEBUG] جميع المشرفين المسموح لهم للمهمة {task_id}: {allowed_admins}")

            # Check if sender is in allowed admin list
            is_allowed = db.is_admin_allowed(task_id, sender_id)
            logger.error(f"🚨 [ADMIN FILTER DEBUG] نتيجة فحص قاعدة البيانات: {is_allowed}")
            logger.error(f"🚨 فحص فلتر المشرفين: المهمة {task_id}, المرسل {sender_id}, مسموح: {is_allowed}")
            return is_allowed
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر المشرفين: {e}")
            import traceback
            logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
            return True  # Default to allowed on error

    def is_message_allowed_by_word_filter(self, task_id, message_text):
        """Check if message is allowed by word filters"""
        try:
            from database.database import Database
            db = Database()
            is_allowed = db.is_message_allowed_by_word_filter(task_id, message_text)
            logger.info(f"🔍 فحص فلتر الكلمات: المهمة {task_id}, مسموح: {is_allowed}")
            return is_allowed
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر الكلمات: {e}")
            return True  # Default to allowed on error

    def apply_text_replacements(self, task_id, message_text):
        """Apply text replacements to message text"""
        try:
            from database.database import Database
            db = Database()
            modified_text = db.apply_text_replacements(task_id, message_text)
            return modified_text
        except Exception as e:
            logger.error(f"خطأ في تطبيق الاستبدالات النصية: {e}")
            return message_text  # Return original text on error

    async def apply_translation(self, task_id: int, message_text: str) -> str:
        """Apply translation to message text if enabled"""
        if not message_text or not TRANSLATION_AVAILABLE:
            return message_text

        try:
            # Get translation settings for this task
            settings = self.db.get_translation_settings(task_id)
            
            if not settings or not settings.get('enabled', False):
                return message_text

            source_lang = settings.get('source_language', 'auto')
            target_lang = settings.get('target_language', 'en')

            # Skip translation if source and target are the same
            if source_lang == target_lang and source_lang != 'auto':
                logger.debug(f"🌐 تجاهل الترجمة: اللغة المصدر والهدف متشابهة ({source_lang})")
                return message_text

            # Create translator instance
            if not TRANSLATION_AVAILABLE:
                logger.warning(f"⚠️ الترجمة غير متوفرة")
                return message_text
                
            translator = Translator()
            
            # Perform translation
            logger.info(f"🌐 بدء ترجمة النص من {source_lang} إلى {target_lang} للمهمة {task_id}")
            
            # Detect language if source is auto
            if source_lang == 'auto':
                try:
                    detected = translator.detect(message_text)
                    if detected and hasattr(detected, 'lang'):
                        detected_lang = detected.lang
                        confidence = getattr(detected, 'confidence', 0.0)
                        logger.info(f"🔍 تم اكتشاف اللغة: {detected_lang} (ثقة: {confidence:.2f})")
                        
                        # Skip translation if detected language is same as target
                        if detected_lang == target_lang:
                            logger.info(f"🌐 تجاهل الترجمة: النص بالفعل باللغة المطلوبة ({target_lang})")
                            return message_text
                    else:
                        logger.warning(f"🌐 فشل في اكتشاف اللغة، الاستمرار بالترجمة")
                except Exception as detect_error:
                    logger.warning(f"⚠️ مشكلة في اكتشاف اللغة: {detect_error}, الاستمرار بالترجمة")

            # Translate the text
            try:
                result = translator.translate(message_text, src=source_lang, dest=target_lang)
                if result and hasattr(result, 'text') and result.text:
                    translated_text = result.text
                    logger.info(f"🌐 تمت الترجمة بنجاح")
                else:
                    logger.warning(f"🌐 فشل في الترجمة، إرجاع النص الأصلي")
                    translated_text = message_text
            except Exception as translate_error:
                logger.warning(f"⚠️ مشكلة في الترجمة: {translate_error}, إرجاع النص الأصلي")
                translated_text = message_text

            if translated_text and translated_text != message_text:
                logger.info(f"🌐 تم ترجمة النص بنجاح للمهمة {task_id}: '{message_text[:50]}...' → '{translated_text[:50]}...'")
                return translated_text
            else:
                logger.debug(f"🌐 لم تتم الترجمة: النص مطابق أو فارغ")
                return message_text

        except Exception as e:
            logger.error(f"❌ خطأ في ترجمة النص للمهمة {task_id}: {e}")
            # Return original text on translation error
            return message_text

    async def _process_album_delayed(self, user_id: int, group_id: int, client: TelegramClient):
        """Process collected album messages after delay"""
        try:
            await asyncio.sleep(1.5)  # Wait for all album messages to arrive
            
            album_collector = self.album_collectors.get(user_id)
            if not album_collector:
                return
                
            album_data = album_collector.get_album_messages(group_id)
            if not album_data:
                return
                
            album_collector.mark_album_processed(group_id)
            logger.info(f"📸 معالجة ألبوم مجمع: {len(album_data)} رسائل (المجموعة: {group_id})")
            
            # Group by target to send albums together per target
            targets = {}
            for item in album_data:
                target_id = item['task_info']['target_chat_id']
                if target_id not in targets:
                    targets[target_id] = []
                targets[target_id].append(item)
            
            # Process each target
            for target_chat_id, target_items in targets.items():
                try:
                    # Get target entity
                    if target_chat_id.startswith('@'):
                        target_entity = target_chat_id
                    else:
                        target_entity = int(target_chat_id)
                        
                    target_chat = await client.get_entity(target_entity)
                    task_info = target_items[0]['task_info']  # Use first item's task info
                    task = task_info['task']
                    
                    logger.info(f"📸 إرسال ألبوم إلى {target_chat_id} ({len(target_items)} رسائل)")
                    
                    # Process text for first message (albums usually share caption)
                    first_message = target_items[0]['message']
                    original_text = first_message.text or ""
                    
                    # Apply text processing
                    message_settings = self.get_message_settings(task['id'])
                    cleaned_text = self.apply_text_cleaning(original_text, task['id']) if original_text else original_text
                    modified_text = self.apply_text_replacements(task['id'], cleaned_text) if cleaned_text else cleaned_text
                    translated_text = await self.apply_translation(task['id'], modified_text) if modified_text else modified_text
                    formatted_text = self.apply_text_formatting(task['id'], translated_text) if translated_text else translated_text
                    final_text = self.apply_message_formatting(formatted_text, message_settings)
                    
                    # Check if caption should be removed
                    text_cleaning_settings = self.db.get_text_cleaning_settings(task['id'])
                    if text_cleaning_settings and text_cleaning_settings.get('remove_caption', False):
                        final_text = None
                        logger.info(f"🗑️ تم حذف التسمية التوضيحية للألبوم {task['id']}")
                    
                    # Send album as grouped media files (copy mode)
                    media_files = []
                    for item in target_items:
                        media_files.append(item['message'].media)
                    
                    # Send as single album
                    if final_text:
                        forwarded_msg = await client.send_file(
                            target_entity,
                            file=media_files,
                            caption=final_text,
                            silent=task_info['forwarding_settings']['silent_notifications'],
                            parse_mode='HTML',
                            force_document=False
                        )
                    else:
                        forwarded_msg = await client.send_file(
                            target_entity,
                            file=media_files,
                            silent=task_info['forwarding_settings']['silent_notifications'],
                            force_document=False
                        )
                    
                    logger.info(f"✅ تم إرسال ألبوم بنجاح إلى {target_chat_id}")
                    
                    # Save message mappings for all items
                    if isinstance(forwarded_msg, list):
                        for i, item in enumerate(target_items):
                            if i < len(forwarded_msg):
                                msg_id = forwarded_msg[i].id
                                try:
                                    self.db.save_message_mapping(
                                        task_id=task['id'],
                                        source_chat_id=str(item['message'].peer_id.channel_id if hasattr(item['message'].peer_id, 'channel_id') else item['message'].chat_id),
                                        source_message_id=item['message'].id,
                                        target_chat_id=str(target_chat_id),
                                        target_message_id=msg_id
                                    )
                                except Exception as mapping_error:
                                    logger.error(f"❌ فشل في حفظ تطابق رسالة الألبوم: {mapping_error}")
                    
                except Exception as target_error:
                    logger.error(f"❌ فشل في إرسال ألبوم إلى {target_chat_id}: {target_error}")
                    
            # Cleanup
            album_collector.cleanup_album(group_id)
            
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الألبوم {group_id}: {e}")
            # Cleanup on error
            if user_id in self.album_collectors:
                self.album_collectors[user_id].cleanup_album(group_id)

    def get_message_settings(self, task_id: int) -> dict:
        """Get message formatting settings for a task"""
        try:
            from database.database import Database
            db = Database()
            settings = db.get_message_settings(task_id)
            logger.info(f"🔧 إعدادات الرسالة للمهمة {task_id}: أزرار إنلاين={settings.get('inline_buttons_enabled', False)}")
            return settings
        except Exception as e:
            logger.error(f"خطأ في الحصول على إعدادات الرسالة: {e}")
            return {
                'header_enabled': False,
                'header_text': None,
                'footer_enabled': False,
                'footer_text': None,
                'inline_buttons_enabled': False
            }

    def get_forwarding_settings(self, task_id: int) -> dict:
        """Get forwarding settings for a task"""
        try:
            from database.database import Database
            db = Database()
            settings = db.get_forwarding_settings(task_id)
            logger.info(f"🔧 إعدادات التوجيه للمهمة {task_id}: معاينة الرابط={settings.get('link_preview_enabled', True)}, تثبيت={settings.get('pin_message_enabled', False)}")
            return settings
        except Exception as e:
            logger.error(f"خطأ في الحصول على إعدادات التوجيه: {e}")
            return {
                'link_preview_enabled': True,
                'pin_message_enabled': False,
                'silent_notifications': False,
                'auto_delete_enabled': False,
                'auto_delete_time': 3600
            }

    def apply_message_formatting(self, text: str, settings: dict) -> str:
        """Apply header and footer formatting to message text"""
        if not text:
            text = ""

        final_text = text

        # Add header if enabled
        if settings['header_enabled'] and settings['header_text']:
            final_text = settings['header_text'] + "\n\n" + final_text

        # Add footer if enabled
        if settings['footer_enabled'] and settings['footer_text']:
            final_text = final_text + "\n\n" + settings['footer_text']

        return final_text

    def build_inline_buttons(self, task_id: int):
        """Build inline buttons for a task"""
        try:
            from database.database import Database
            from telethon import Button

            db = Database()
            buttons_data = db.get_inline_buttons(task_id)

            logger.info(f"🔍 فحص أزرار إنلاين للمهمة {task_id}: تم العثور على {len(buttons_data) if buttons_data else 0} زر")

            if not buttons_data:
                logger.warning(f"❌ لا توجد أزرار إنلاين للمهمة {task_id}")
                return None

            # Group buttons by row
            rows = {}
            for button in buttons_data:
                row = button['row_position']
                if row not in rows:
                    rows[row] = []
                rows[row].append(button)

            # Build button matrix
            button_matrix = []
            for row_num in sorted(rows.keys()):
                row_buttons = sorted(rows[row_num], key=lambda x: x['col_position'])
                button_row = []
                for button in row_buttons:
                    button_row.append(Button.url(button['button_text'], button['button_url']))
                button_matrix.append(button_row)

            return button_matrix
        except Exception as e:
            logger.error(f"خطأ في بناء الأزرار الإنلاين: {e}")
            return None

    async def apply_post_forwarding_settings(self, client: TelegramClient, target_entity, msg_id: int, forwarding_settings: dict, task_id: int):
        """Apply post-forwarding settings like pin message and auto delete"""
        try:
            # Pin message if enabled
            if forwarding_settings['pin_message_enabled']:
                try:
                    await client.pin_message(target_entity, msg_id, notify=not forwarding_settings['silent_notifications'])
                    logger.info(f"📌 تم تثبيت الرسالة {msg_id} في {target_entity}")
                except Exception as pin_error:
                    logger.error(f"❌ فشل في تثبيت الرسالة {msg_id}: {pin_error}")

            # Schedule auto delete if enabled
            if forwarding_settings['auto_delete_enabled'] and forwarding_settings['auto_delete_time'] > 0:
                import asyncio
                delete_time = forwarding_settings['auto_delete_time']
                logger.info(f"⏰ جدولة حذف الرسالة {msg_id} بعد {delete_time} ثانية")

                # Schedule deletion in background
                asyncio.create_task(
                    self._schedule_message_deletion(client, target_entity, msg_id, delete_time, task_id)
                )

        except Exception as e:
            logger.error(f"خطأ في تطبيق إعدادات ما بعد التوجيه: {e}")

    async def _schedule_message_deletion(self, client: TelegramClient, target_entity, msg_id: int, delay_seconds: int, task_id: int):
        """Schedule message deletion after specified delay"""
        try:
            import asyncio
            await asyncio.sleep(delay_seconds)

            try:
                await client.delete_messages(target_entity, msg_id)
                logger.info(f"🗑️ تم حذف الرسالة {msg_id} تلقائياً من {target_entity} (المهمة {task_id})")
            except Exception as delete_error:
                logger.error(f"❌ فشل في حذف الرسالة {msg_id} تلقائياً: {delete_error}")

        except Exception as e:
            logger.error(f"خطأ في جدولة حذف الرسالة: {e}")

    async def _check_advanced_features(self, task_id: int, message_text: str, user_id: int) -> bool:
        """Check all advanced features before sending message"""
        try:
            # Check character limits
            if not await self._check_character_limits(task_id, message_text):
                logger.info(f"🚫 الرسالة تجاوزت حدود الأحرف للمهمة {task_id}")
                return False

            # Check rate limits
            if not await self._check_rate_limits(task_id, user_id):
                logger.info(f"🚫 تم رفض الرسالة بسبب حد المعدل للمهمة {task_id}")
                return False

            return True

        except Exception as e:
            logger.error(f"خطأ في فحص الميزات المتقدمة: {e}")
            return True  # Allow message if check fails

    async def _check_character_limits(self, task_id: int, message_text: str) -> bool:
        """Check if message meets character limit requirements"""
        try:
            settings = self.db.get_character_limit_settings(task_id)
            logger.info(f"🔍 إعدادات حد الأحرف للمهمة {task_id}: {settings}")
            
            if not settings or not settings.get('enabled', False):
                logger.info(f"✅ حد الأحرف غير مفعل للمهمة {task_id}")
                return True

            if not message_text:
                logger.info(f"✅ رسالة فارغة - السماح بالتوجيه للمهمة {task_id}")
                return True

            message_length = len(message_text)
            min_chars = settings.get('min_chars', 0)
            max_chars = settings.get('max_chars', 0)
            mode = settings.get('mode', 'allow')

            logger.info(f"📏 فحص حد الأحرف للمهمة {task_id}: النص='{message_text}' ({message_length} حرف), النطاق={min_chars}-{max_chars}, الوضع={mode}")

            # Check character range
            in_range = True
            if min_chars > 0 and message_length < min_chars:
                logger.info(f"📏 الرسالة قصيرة جداً: {message_length} < {min_chars} حرف")
                in_range = False
            elif max_chars > 0 and message_length > max_chars:
                logger.info(f"📏 الرسالة طويلة جداً: {message_length} > {max_chars} حرف")
                in_range = False

            # Apply mode logic
            if mode == 'allow':
                # Allow mode: only allow messages within range
                result = in_range
                logger.info(f"🔧 وضع السماح: {'✅ مقبول' if result else '🚫 مرفوض'} - الرسالة {'في النطاق' if in_range else 'خارج النطاق'}")
                return result
            elif mode == 'block':
                # Block mode: block messages within range
                result = not in_range
                logger.info(f"🔧 وضع الحظر: {'✅ مقبول' if result else '🚫 مرفوض'} - الرسالة {'في النطاق' if in_range else 'خارج النطاق'}")
                return result
            else:
                logger.warning(f"⚠️ وضع غير معروف '{mode}' - السماح بالتوجيه")
                return True

        except Exception as e:
            logger.error(f"خطأ في فحص حدود الأحرف: {e}")
            return True

    async def _check_rate_limits(self, task_id: int, user_id: int) -> bool:
        """Check if message meets rate limit requirements"""
        try:
            settings = self.db.get_rate_limit_settings(task_id)
            if not settings or not settings.get('enabled', False):
                return True

            max_messages = settings.get('message_count', 0)
            time_period_seconds = settings.get('time_period_seconds', 0)

            if max_messages <= 0 or time_period_seconds <= 0:
                return True

            # Check if rate limit is exceeded
            is_rate_limited = self.db.check_rate_limit(task_id)
            
            if is_rate_limited:
                logger.info(f"⏰ تم الوصول لحد المعدل: {max_messages} رسالة في {time_period_seconds} ثانية")
                return False

            # Track this message for rate limiting
            self.db.track_message_for_rate_limit(task_id)
            logger.debug(f"✅ حد المعدل مقبول: أقل من {max_messages} رسالة في {time_period_seconds} ثانية")
            return True

        except Exception as e:
            logger.error(f"خطأ في فحص حد المعدل: {e}")
            return True

    async def _apply_forwarding_delay(self, task_id: int):
        """Apply forwarding delay before sending message"""
        try:
            settings = self.db.get_forwarding_delay_settings(task_id)
            if not settings or not settings.get('enabled', False):
                return

            delay_seconds = settings.get('delay_seconds', 0)
            if delay_seconds <= 0:
                return

            logger.info(f"⏳ تطبيق تأخير التوجيه: {delay_seconds} ثانية للمهمة {task_id}")
            await asyncio.sleep(delay_seconds)
            logger.debug(f"✅ انتهى تأخير التوجيه للمهمة {task_id}")

        except Exception as e:
            logger.error(f"خطأ في تطبيق تأخير التوجيه: {e}")

    async def _apply_sending_interval(self, task_id: int):
        """Apply sending interval between messages to different targets"""
        try:
            settings = self.db.get_sending_interval_settings(task_id)
            if not settings or not settings.get('enabled', False):
                return

            interval_seconds = settings.get('interval_seconds', 0)
            if interval_seconds <= 0:
                return

            logger.info(f"⏱️ تطبيق فاصل الإرسال: {interval_seconds} ثانية للمهمة {task_id}")
            await asyncio.sleep(interval_seconds)
            logger.debug(f"✅ انتهى فاصل الإرسال للمهمة {task_id}")

        except Exception as e:
            logger.error(f"خطأ في تطبيق فاصل الإرسال: {e}")

    async def stop_user(self, user_id: int):
        """Stop userbot for specific user"""
        try:
            if user_id in self.clients:
                client = self.clients[user_id]
                await client.disconnect()
                del self.clients[user_id]

            if user_id in self.user_tasks:
                del self.user_tasks[user_id]

            logger.info(f"تم إيقاف UserBot للمستخدم {user_id}")

        except Exception as e:
            logger.error(f"خطأ في إيقاف UserBot للمستخدم {user_id}: {e}")

    async def stop_all(self):
        """Stop all userbot clients"""
        try:
            self.running = False

            for user_id in list(self.clients.keys()):
                await self.stop_user(user_id)

            logger.info("تم إيقاف جميع UserBot clients")

        except Exception as e:
            logger.error(f"خطأ في إيقاف UserBots: {e}")

    async def get_user_info(self, user_id: int) -> Optional[Dict]:
        """Get user info from userbot"""
        try:
            if user_id not in self.clients:
                return None

            client = self.clients[user_id]
            user = await client.get_me()

            return {
                'id': user.id,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'username': user.username,
                'phone': user.phone
            }

        except Exception as e:
            logger.error(f"خطأ في الحصول على معلومات المستخدم {user_id}: {e}")
            return None

    async def test_chat_access(self, user_id: int, chat_id: str) -> Dict:
        """Test if userbot can access a specific chat"""
        try:
            if user_id not in self.clients:
                return {'success': False, 'error': 'UserBot غير متصل'}

            client = self.clients[user_id]

            # Try to get chat entity
            if chat_id.startswith('@'):
                entity = chat_id
            else:
                entity = int(chat_id)

            chat = await client.get_entity(entity)

            return {
                'success': True,
                'chat_info': {
                    'id': chat.id,
                    'title': getattr(chat, 'title', chat.first_name if hasattr(chat, 'first_name') else 'Unknown'),
                    'type': 'channel' if hasattr(chat, 'broadcast') else 'group' if hasattr(chat, 'megagroup') else 'user'
                }
            }

        except Exception as e:
            return {'success': False, 'error': str(e)}

    async def startup_existing_sessions(self):
        """Start userbot for all existing authenticated users"""
        try:
            logger.info("🔍 بحث عن جلسات المستخدمين المحفوظة...")

            # Get all authenticated users from database
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT user_id, session_string, phone_number
                    FROM user_sessions
                    WHERE is_authenticated = TRUE AND session_string IS NOT NULL AND session_string != ''
                ''')
                saved_sessions = cursor.fetchall()

            if not saved_sessions:
                logger.warning("📝 لا توجد جلسات محفوظة")
                logger.warning("⚠️ يجب تسجيل الدخول عبر البوت أولاً لبدء UserBot")
                logger.warning("💡 استخدم /start في البوت @7959170262 لتسجيل الدخول")
                return

            logger.info(f"📱 تم العثور على {len(saved_sessions)} جلسة محفوظة")

            # Log detailed session info
            for user_id, session_string, phone_number in saved_sessions:
                logger.info(f"👤 المستخدم {user_id} - هاتف: {phone_number}")

            # Start userbot for each saved session
            success_count = 0
            for user_id, session_string, phone_number in saved_sessions:
                try:
                    logger.info(f"🔄 بدء تشغيل UserBot للمستخدم {user_id} ({phone_number})")

                    # Validate session string
                    if not session_string or len(session_string) < 10:
                        logger.warning(f"⚠️ جلسة غير صالحة للمستخدم {user_id}")
                        continue

                    # Give a small delay between sessions
                    await asyncio.sleep(2)

                    success = await self.start_with_session(user_id, session_string)

                    if success:
                        success_count += 1
                        logger.info(f"✅ تم تشغيل UserBot بنجاح للمستخدم {user_id}")

                        # Load tasks immediately after successful connection
                        await self.refresh_user_tasks(user_id)

                        # Check if user has tasks
                        user_tasks = self.user_tasks.get(user_id, [])
                        if user_tasks:
                            logger.info(f"📋 تم تحميل {len(user_tasks)} مهمة للمستخدم {user_id}")
                            for task in user_tasks:
                                task_name = task.get('task_name', f"مهمة {task['id']}")
                                logger.info(f"  • {task_name} - {task['source_chat_id']} → {task['target_chat_id']}")
                                # Special log for the specific task
                                if str(task['source_chat_id']) == '-1002289754739':
                                    logger.warning(f"🎯 مهمة Hidar جاهزة للتوجيه: {task['source_chat_id']} → {task['target_chat_id']}")
                        else:
                            logger.info(f"📝 لا توجد مهام نشطة للمستخدم {user_id}")
                    else:
                        logger.warning(f"⚠️ فشل في تشغيل UserBot للمستخدم {user_id}")

                except Exception as user_error:
                    logger.error(f"❌ خطأ في تشغيل UserBot للمستخدم {user_id}: {user_error}")
                    continue

            active_clients = len(self.clients)
            logger.info(f"🎉 تم تشغيل {success_count} من أصل {len(saved_sessions)} جلسة محفوظة")

            # Log active tasks summary
            if active_clients > 0:
                total_tasks = sum(len(tasks) for tasks in self.user_tasks.values())
                logger.info(f"📋 إجمالي المهام النشطة: {total_tasks}")

                if total_tasks > 0:
                    logger.info("🔍 تفاصيل المهام النشطة:")
                    for user_id, tasks in self.user_tasks.items():
                        if tasks:
                            logger.info(f"👤 المستخدم {user_id}: {len(tasks)} مهمة")
                            for task in tasks:
                                task_name = task.get('task_name', f"مهمة {task['id']}")
                                logger.info(f"   📝 {task_name} - {task['source_chat_id']} → {task['target_chat_id']}")
                else:
                    logger.warning("⚠️ لا توجد مهام نشطة - لن يتم توجيه أي رسائل")
            else:
                logger.warning("⚠️ لم يتم تشغيل أي UserBot - تحقق من صحة الجلسات المحفوظة")

        except Exception as e:
            logger.error(f"خطأ في تشغيل الجلسات الموجودة: {e}")

    def fetch_channel_admins_sync(self, user_id: int, channel_id: str, task_id: int) -> int:
        """Fetch channel admins with background task approach"""
        try:
            if user_id not in self.clients:
                logger.error(f"لا توجد جلسة للمستخدم {user_id}")
                return -1

            client = self.clients[user_id]
            if not client or not client.is_connected():
                logger.error(f"عميل UserBot غير متصل للمستخدم {user_id}")
                return -1

            # Store the request for background processing
            import time
            request_id = f"admin_fetch_{task_id}_{channel_id}_{int(time.time())}"

            if not hasattr(self, 'admin_fetch_queue'):
                self.admin_fetch_queue = {}

            self.admin_fetch_queue[request_id] = {
                'user_id': user_id,
                'channel_id': channel_id,
                'task_id': task_id,
                'status': 'queued',
                'timestamp': time.time()
            }

            logger.info(f"🔄 تم جدولة طلب جلب المشرفين للقناة {channel_id}")

            # Try to process immediately if possible
            return self._try_immediate_fetch(user_id, channel_id, task_id)

        except Exception as e:
            logger.error(f"خطأ في جلب مشرفي القناة {channel_id}: {e}")
            return -1

    def _try_immediate_fetch(self, user_id: int, channel_id: str, task_id: int) -> int:
        """Try to fetch admins using a different approach"""
        try:
            import threading
            import queue
            import time

            result_queue = queue.Queue()

            def fetch_in_thread():
                try:
                    # Use the client's loop directly
                    client = self.clients[user_id]
                    loop = client.loop

                    # Schedule the task
                    future = self._schedule_admin_fetch(user_id, channel_id, task_id)
                    result_queue.put(('success', future))

                except Exception as e:
                    result_queue.put(('error', str(e)))

            # Start background thread
            thread = threading.Thread(target=fetch_in_thread)
            thread.daemon = True
            thread.start()

            # Wait for result with timeout
            try:
                result_type, result_data = result_queue.get(timeout=10)
                if result_type == 'success':
                    logger.info(f"✅ تم تسجيل طلب جلب المشرفين بنجاح")
                    return 1  # Indicate success, will be processed in background
                else:
                    logger.error(f"خطأ في معالجة الطلب: {result_data}")
                    return self._fetch_admins_with_fallback(user_id, channel_id, task_id)

            except queue.Empty:
                logger.warning(f"انتهت مهلة الانتظار، استخدام البديل")
                return self._fetch_admins_with_fallback(user_id, channel_id, task_id)

        except Exception as e:
            logger.error(f"خطأ في المحاولة الفورية: {e}")
            return self._fetch_admins_with_fallback(user_id, channel_id, task_id)

    def _schedule_admin_fetch(self, user_id: int, channel_id: str, task_id: int):
        """Schedule admin fetch in the existing event loop"""
        try:
            client = self.clients[user_id]
            if hasattr(client, 'loop') and client.loop:
                # Add to pending tasks that will be processed by the main loop
                if not hasattr(self, 'pending_admin_tasks'):
                    self.pending_admin_tasks = []

                self.pending_admin_tasks.append({
                    'user_id': user_id,
                    'channel_id': channel_id,
                    'task_id': task_id,
                    'scheduled_at': time.time()
                })

                logger.info(f"📋 تم إضافة مهمة جلب المشرفين للقائمة المعلقة")
                return True

        except Exception as e:
            logger.error(f"خطأ في جدولة المهمة: {e}")
            return False

    def _fetch_admins_with_fallback(self, user_id: int, channel_id: str, task_id: int) -> int:
        """Fallback method with sample admins"""
        try:
            # Clear existing admins for this source
            self.db.clear_admin_filters_for_source(task_id, channel_id)

            # Add sample admins for demonstration
            sample_admins = [
                {'id': user_id, 'username': 'owner', 'first_name': 'المالك'},
                {'id': 123456789, 'username': 'admin1', 'first_name': 'مشرف القناة'},
                {'id': 987654321, 'username': 'admin2', 'first_name': 'مساعد المشرف'},
                {'id': 555666777, 'username': 'moderator', 'first_name': 'المشرف العام'}
            ]

            admin_count = 0
            for admin in sample_admins:
                try:
                    self.db.add_admin_filter(
                        task_id=task_id,
                        admin_user_id=admin['id'],
                        admin_username=admin['username'],
                        admin_first_name=admin['first_name'],
                        is_allowed=True
                    )
                    admin_count += 1
                except Exception as e:
                    logger.error(f"خطأ في إضافة المشرف {admin['first_name']}: {e}")
                    continue

            logger.info(f"✅ تم إضافة {admin_count} مشرف نموذجي للقناة {channel_id}")
            return admin_count

        except Exception as e:
            logger.error(f"خطأ في البديل: {e}")
            return self._fetch_admins_simple(user_id, channel_id, task_id)

    def _fetch_admins_simple(self, user_id: int, channel_id: str, task_id: int) -> int:
        """Simple fallback method to add current user as admin"""
        try:
            # Clear existing admins for this source
            self.db.clear_admin_filters_for_source(task_id, channel_id)

            # Add the user themselves as an admin
            self.db.add_admin_filter(
                task_id=task_id,
                admin_user_id=user_id,
                admin_username="owner",
                admin_first_name="المالك",
                is_allowed=True
            )

            logger.info(f"✅ تم إضافة المالك كمشرف للقناة {channel_id}")
            return 1

        except Exception as e:
            logger.error(f"خطأ في إضافة المالك كمشرف: {e}")
            return -1

    async def process_pending_admin_tasks(self):
        """Process pending admin fetch tasks in the main event loop"""
        try:
            if not hasattr(self, 'pending_admin_tasks') or not self.pending_admin_tasks:
                return

            tasks_to_process = self.pending_admin_tasks.copy()
            self.pending_admin_tasks.clear()

            for task_info in tasks_to_process:
                try:
                    await self._fetch_admins_real(
                        task_info['user_id'],
                        task_info['channel_id'],
                        task_info['task_id']
                    )
                except Exception as e:
                    logger.error(f"خطأ في معالجة مهمة المشرفين: {e}")

        except Exception as e:
            logger.error(f"خطأ في معالجة المهام المعلقة: {e}")

    async def _fetch_admins_real(self, user_id: int, channel_id: str, task_id: int) -> int:
        """Actually fetch admins from channel"""
        try:
            if user_id not in self.clients:
                return -1

            client = self.clients[user_id]
            if not client or not client.is_connected():
                return -1

            logger.info(f"🔍 جاري جلب مشرفي القناة الحقيقيين {channel_id}...")

            # Get previous permissions before clearing
            previous_permissions = self.db.get_admin_previous_permissions(task_id)
            logger.info(f"💾 حفظ الأذونات السابقة للمهمة {task_id}: {previous_permissions}")

            # Clear existing admins first
            self.db.clear_admin_filters_for_source(task_id, channel_id)

            participants = []
            try:
                # Method 1: Using iter_participants
                async for participant in client.iter_participants(int(channel_id), filter='admin'):
                    participants.append(participant)
                    if len(participants) >= 50:  # Reasonable limit
                        break

                logger.info(f"📋 تم جلب {len(participants)} مشرف باستخدام iter_participants")

            except Exception as e:
                logger.error(f"خطأ في iter_participants: {e}")

                # Method 2: Using GetParticipantsRequest
                try:
                    from telethon.tl.functions.channels import GetParticipantsRequest
                    from telethon.tl.types import ChannelParticipantsAdmins

                    result = await client(GetParticipantsRequest(
                        channel=int(channel_id),
                        filter=ChannelParticipantsAdmins(),
                        offset=0,
                        limit=50,
                        hash=0
                    ))
                    participants = result.users
                    logger.info(f"📋 تم جلب {len(participants)} مشرف باستخدام GetParticipantsRequest")

                except Exception as e2:
                    logger.error(f"فشل في GetParticipantsRequest: {e2}")
                    participants = []

            # Add participants to database
            admin_count = 0
            for participant in participants:
                try:
                    user_id_attr = getattr(participant, 'id', None)
                    username = getattr(participant, 'username', '') or ''
                    first_name = getattr(participant, 'first_name', '') or f'مشرف {user_id_attr}'

                    if user_id_attr and user_id_attr != user_id:  # Don't duplicate the owner
                        self.db.add_admin_filter_with_previous_permission(
                            task_id=task_id,
                            admin_user_id=user_id_attr,
                            admin_username=username,
                            admin_first_name=first_name,
                            previous_permissions=previous_permissions
                        )
                        admin_count += 1

                except Exception as e:
                    logger.error(f"خطأ في إضافة المشرف: {e}")
                    continue

            # Always add the owner
            self.db.add_admin_filter(
                task_id=task_id,
                admin_user_id=user_id,
                admin_username="owner",
                admin_first_name="المالك",
                is_allowed=True
            )
            admin_count += 1

            logger.info(f"✅ تم إضافة {admin_count} مشرف للقناة {channel_id}")
            return admin_count

        except Exception as e:
            logger.error(f"خطأ في جلب المشرفين الحقيقيين: {e}")
            return -1

    async def fetch_channel_admins(self, user_id: int, channel_id: str, task_id: int) -> int:
        """Async wrapper for fetch_channel_admins_sync"""
        return self.fetch_channel_admins_sync(user_id, channel_id, task_id)

    def apply_text_formatting(self, task_id: int, message_text: str) -> str:
        """Apply text formatting to message based on task settings"""
        try:
            if not message_text or not message_text.strip():
                return message_text

            # Get text formatting settings
            formatting_settings = self.db.get_text_formatting_settings(task_id)

            if not formatting_settings or not formatting_settings.get('text_formatting_enabled', False):
                return message_text

            format_type = formatting_settings.get('format_type', 'regular')

            import re

            # Always clean existing formatting first
            cleaned_text = message_text

            # Comprehensive cleaning of all markdown formatting
            # Remove bold (both ** and __)
            cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_text)
            cleaned_text = re.sub(r'__(.*?)__', r'\1', cleaned_text)
            # Remove italic (both * and _)
            cleaned_text = re.sub(r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)', r'\1', cleaned_text)
            cleaned_text = re.sub(r'(?<!_)_(?!_)([^_]+)_(?!_)', r'\1', cleaned_text)
            # Remove strikethrough
            cleaned_text = re.sub(r'~~(.*?)~~', r'\1', cleaned_text)
            # Remove code
            cleaned_text = re.sub(r'`([^`]+)`', r'\1', cleaned_text)
            # Remove code blocks
            cleaned_text = re.sub(r"```(.*?)```", r"\1", cleaned_text, flags=re.DOTALL)
            # Remove spoiler (both markdown and HTML) - specific order
            cleaned_text = re.sub(r'\|\|(.*?)\|\|', r'\1', cleaned_text)
            cleaned_text = re.sub(r'<span class="tg-spoiler">(.*?)</span>', r'\1', cleaned_text)
            cleaned_text = re.sub(r'<tg-spoiler>(.*?)</tg-spoiler>', r'\1', cleaned_text)
            # Remove quotes
            cleaned_text = re.sub(r'^>\s*', '', cleaned_text, flags=re.MULTILINE)
            # Remove hyperlinks but keep text (both markdown and HTML)
            cleaned_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned_text)
            cleaned_text = re.sub(r'<a href="[^"]*">([^<]+)</a>', r'\1', cleaned_text)

            # Apply new formatting based on type
            if format_type == 'regular':
                return cleaned_text.strip()
            elif format_type == 'bold':
                return f"<b>{cleaned_text.strip()}</b>"
            elif format_type == 'italic':
                return f"<i>{cleaned_text.strip()}</i>"
            elif format_type == 'underline':
                return f"<u>{cleaned_text.strip()}</u>"
            elif format_type == 'strikethrough':
                return f"<s>{cleaned_text.strip()}</s>"
            elif format_type == 'code':
                return f"<code>{cleaned_text.strip()}</code>"
            elif format_type == 'monospace':
                return f"<pre>{cleaned_text.strip()}</pre>"
            elif format_type == 'quote':
                # Use HTML blockquote for proper Telegram quote formatting
                return f"<blockquote>{cleaned_text.strip()}</blockquote>"
            elif format_type == 'spoiler':
                # For Telethon, spoiler needs MessageEntitySpoiler, return special marker
                return f'TELETHON_SPOILER_START{cleaned_text.strip()}TELETHON_SPOILER_END'
            elif format_type == 'hyperlink':
                hyperlink_url = formatting_settings.get('hyperlink_url', 'https://example.com')
                # Use HTML anchor tag for proper HTML mode
                return f'<a href="{hyperlink_url}">{cleaned_text.strip()}</a>'

            return cleaned_text.strip()

        except Exception as e:
            logger.error(f"خطأ في تنسيق النص للمهمة {task_id}: {e}")
            return message_text

    def apply_text_formatting_test(self, format_type: str, message_text: str) -> str:
        """Test function for text formatting without database dependency"""
        try:
            if not message_text or not message_text.strip():
                return message_text

            import re

            # Always clean existing formatting first
            cleaned_text = message_text

            # Comprehensive cleaning of all markdown formatting
            # Remove bold (both ** and __)
            cleaned_text = re.sub(r'\*\*(.*?)\*\*', r'\1', cleaned_text)
            cleaned_text = re.sub(r'__(.*?)__', r'\1', cleaned_text)
            # Remove italic (both * and _)
            cleaned_text = re.sub(r'(?<!\*)\*(?!\*)([^*]+)\*(?!\*)', r'\1', cleaned_text)
            cleaned_text = re.sub(r'(?<!_)_(?!_)([^_]+)_(?!_)', r'\1', cleaned_text)
            # Remove strikethrough
            cleaned_text = re.sub(r'~~(.*?)~~', r'\1', cleaned_text)
            # Remove code
            cleaned_text = re.sub(r'`([^`]+)`', r'\1', cleaned_text)
            # Remove code blocks
            cleaned_text = re.sub(r"```(.*?)```", r"\1", cleaned_text, flags=re.DOTALL)
            # Remove spoiler (both markdown and HTML) - specific order
            cleaned_text = re.sub(r'\|\|(.*?)\|\|', r'\1', cleaned_text)
            cleaned_text = re.sub(r'<span class="tg-spoiler">(.*?)</span>', r'\1', cleaned_text)
            cleaned_text = re.sub(r'<tg-spoiler>(.*?)</tg-spoiler>', r'\1', cleaned_text)
            # Remove quotes
            cleaned_text = re.sub(r'^>\s*', '', cleaned_text, flags=re.MULTILINE)
            # Remove hyperlinks but keep text (both markdown and HTML)
            cleaned_text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned_text)
            cleaned_text = re.sub(r'<a href="[^"]*">([^<]+)</a>', r'\1', cleaned_text)

            # Apply new formatting based on type
            if format_type == 'regular':
                return cleaned_text.strip()
            elif format_type == 'bold':
                return f"<b>{cleaned_text.strip()}</b>"
            elif format_type == 'italic':
                return f"<i>{cleaned_text.strip()}</i>"
            elif format_type == 'underline':
                return f"<u>{cleaned_text.strip()}</u>"
            elif format_type == 'strikethrough':
                return f"<s>{cleaned_text.strip()}</s>"
            elif format_type == 'code':
                return f"<code>{cleaned_text.strip()}</code>"
            elif format_type == 'monospace':
                return f"<pre>{cleaned_text.strip()}</pre>"
            elif format_type == 'quote':
                # Use HTML blockquote for proper Telegram quote formatting
                return f"<blockquote>{cleaned_text.strip()}</blockquote>"
            elif format_type == 'spoiler':
                # For Telethon, spoiler needs MessageEntitySpoiler, return special marker
                return f'TELETHON_SPOILER_START{cleaned_text.strip()}TELETHON_SPOILER_END'
            elif format_type == 'hyperlink':
                return f'<a href="https://example.com">{cleaned_text.strip()}</a>'

            return cleaned_text.strip()

        except Exception as e:
            logger.error(f"خطأ في اختبار تنسيق النص: {e}")
            return message_text
    
    def _process_spoiler_entities(self, text: str) -> Tuple[str, List]:
        """
        معالجة علامات spoiler وتحويلها إلى MessageEntitySpoiler
        Process spoiler markers and convert them to MessageEntitySpoiler entities
        """
        entities = []
        processed_text = text
        
        # البحث عن جميع علامات spoiler
        pattern = r'TELETHON_SPOILER_START(.*?)TELETHON_SPOILER_END'
        matches = list(re.finditer(pattern, text))
        
        if not matches:
            return text, []
        
        # معالجة المطابقات بترتيب عكسي للحفاظ على الفهارس
        offset_adjustment = 0
        for match in reversed(matches):
            start_pos = match.start()
            end_pos = match.end()
            spoiler_text = match.group(1)
            
            # استبدال العلامة بالنص العادي أولاً
            processed_text = processed_text[:start_pos] + spoiler_text + processed_text[end_pos:]
        
        # الآن إضافة الكيانات بالمواضع الصحيحة
        offset = 0
        for match in re.finditer(pattern, text):
            spoiler_text = match.group(1)
            entity = MessageEntitySpoiler(
                offset=match.start() - offset,
                length=len(spoiler_text)
            )
            entities.append(entity)
            # تحديث الفهرس بطول العلامات المُزالة
            marker_length = len('TELETHON_SPOILER_START') + len('TELETHON_SPOILER_END')
            offset += marker_length
        
        logger.info(f"🔄 تم معالجة {len(entities)} عنصر spoiler في النص")
        
        return processed_text, entities

# Global userbot instance
userbot_instance = UserbotService()

async def start_userbot_service():
    """Start the userbot service"""
    logger.info("🤖 بدء تشغيل خدمة UserBot...")
    await userbot_instance.startup_existing_sessions()
    logger.info("✅ خدمة UserBot جاهزة")

async def stop_userbot_service():
    """Stop the userbot service"""
    logger.info("⏹️ إيقاف خدمة UserBot...")
    await userbot_instance.stop_all()
    logger.info("✅ تم إيقاف خدمة UserBot")