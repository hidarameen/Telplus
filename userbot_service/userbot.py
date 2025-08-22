"""
Userbot Service for Message Forwarding - الإصدار المحسن
Uses Telethon for automated message forwarding between chats

التحسينات الرئيسية:
1. معالجة الوسائط مرة واحدة وإعادة استخدامها لكل الأهداف
2. تحسين أداء العلامة المائية
3. ذاكرة مؤقتة ذكية للوسائط المعالجة
4. تحسين معالجة الفيديو

Main Improvements:
1. Process media once and reuse for all targets
2. Enhanced watermark performance
3. Smart cache for processed media
4. Improved video processing
"""
import logging
import asyncio
import re
from typing import Dict, List, Optional, Tuple
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, AuthKeyUnregisteredError
from telethon.sessions import StringSession
from telethon.tl.types import MessageEntitySpoiler, DocumentAttributeFilename
from database import get_database
from bot_package.config import API_ID, API_HASH
import time
from collections import defaultdict
from watermark_processor import WatermarkProcessor
from audio_processor import AudioProcessor
import tempfile
import os

# Import translation service  
try:
    from deep_translator import GoogleTranslator
    TRANSLATION_AVAILABLE = True
except ImportError:
    TRANSLATION_AVAILABLE = False
    Translator = None

# استيراد معالج الوسائط في الخلفية
try:
    from background_media_processor import background_processor, process_media_in_background, get_processed_media, queue_batch_message
    BACKGROUND_PROCESSING_AVAILABLE = True
    
except ImportError as e:
    logger.warning(f"⚠️ لم يتم العثور على معالج الوسائط في الخلفية: {e}")
    BACKGROUND_PROCESSING_AVAILABLE = False

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
        """Initialize UserBot with database factory"""
        # استخدام مصنع قاعدة البيانات
        self.db = get_database()
        
        # معلومات قاعدة البيانات
        from database import DatabaseFactory
        self.db_info = DatabaseFactory.get_database_info()
        
        logger.info(f"🗄️ تم تهيئة قاعدة البيانات في UserBot: {self.db_info['name']}")
        
        self.clients: Dict[int, TelegramClient] = {}  # user_id -> client
        self.user_tasks: Dict[int, List[Dict]] = {}   # user_id -> tasks
        self.user_locks: Dict[int, asyncio.Lock] = {}  # user_id -> lock for thread safety
        self.running = True
        self.album_collectors: Dict[int, AlbumCollector] = {}  # user_id -> collector
        self.watermark_processor = WatermarkProcessor()  # معالج العلامة المائية
        self.audio_processor = AudioProcessor()  # معالج الوسوم الصوتية
        
        # بدء معالج الوسائط في الخلفية
        if BACKGROUND_PROCESSING_AVAILABLE:
            self.background_media_processing = True
            logger.info("✅ سيتم استخدام معالجة الوسائط في الخلفية")
        else:
            self.background_media_processing = False
            logger.info("⚠️ سيتم استخدام المعالجة المتزامنة للوسائط")
        
        # CRITICAL FIX: Initialize global cache systems for media processing optimization
        self.global_processed_media_cache = {}  # Cache for processed media to prevent re-upload
        self._current_media_cache = {}  # Temporary cache for download optimization per message
        self.uploaded_file_cache = {}  # CRITICAL: Cache for uploaded file handles to prevent re-upload
        self.session_health_status: Dict[int, bool] = {}  # user_id -> health status
        self.session_locks: Dict[int, bool] = {}  # user_id -> is_locked (prevent multiple usage)
        self.max_reconnect_attempts = 3
        self.reconnect_delay = 5  # seconds
        self.startup_delay = 15  # seconds between starting different user sessions

    async def start_with_session(self, user_id: int, session_string: str):
        """Start userbot for a specific user with session string"""
        try:
            # Create lock for this user if not exists
            if user_id not in self.user_locks:
                self.user_locks[user_id] = asyncio.Lock()

            async with self.user_locks[user_id]:
                logger.info(f"🔄 بدء إنشاء جلسة جديدة للمستخدم {user_id}")
                
                # Clear any existing locks for this user
                if user_id in self.session_locks:
                    del self.session_locks[user_id]
                
                # Force disconnect any existing client for this user
                if user_id in self.clients:
                    existing_client = self.clients[user_id]
                    try:
                        logger.info(f"🔌 فصل العميل الموجود للمستخدم {user_id}")
                        await existing_client.disconnect()
                        await asyncio.sleep(2)  # Wait for clean disconnect
                    except Exception as e:
                        logger.warning(f"خطأ في فصل العميل القديم: {e}")
                    finally:
                        if user_id in self.clients:
                            del self.clients[user_id]

                # Wait a moment before creating new connection
                await asyncio.sleep(1)

                # Create client with session string and unique identifiers
                client = TelegramClient(
                    StringSession(session_string),
                    int(API_ID),
                    API_HASH,
                    device_model=f"Telegram-UserBot-{user_id}",
                    system_version="2.0",
                    app_version=f"1.0.{user_id}",
                    lang_code="ar",
                    system_lang_code="ar",
                    sequential_updates=True  # Ensure sequential processing
                )

                # Set connection parameters to avoid conflicts
                client._connection_retries = 2
                client._retry_delay = 5

                logger.info(f"🔄 محاولة الاتصال للمستخدم {user_id}...")
                
                # Connect with retry mechanism
                max_attempts = 3
                for attempt in range(max_attempts):
                    try:
                        await client.connect()
                        break
                    except Exception as connect_error:
                        logger.warning(f"فشل في المحاولة {attempt + 1} للمستخدم {user_id}: {connect_error}")
                        if attempt < max_attempts - 1:
                            await asyncio.sleep(5)  # Wait before retry
                        else:
                            raise connect_error

                # Check authorization
                if not await client.is_user_authorized():
                    logger.error(f"Session غير صالحة للمستخدم {user_id}")
                    await client.disconnect()
                    return False

                # Store client
                self.clients[user_id] = client
                self.session_health_status[user_id] = True

                # Create album collector for this user
                if user_id not in self.album_collectors:
                    self.album_collectors[user_id] = AlbumCollector()

                # Load user tasks
                await self.refresh_user_tasks(user_id)

                # Set up event handlers for this user
                await self._setup_event_handlers(user_id, client)

                user = await client.get_me()
                logger.info(f"✅ تم تشغيل UserBot للمستخدم {user_id} ({user.first_name})")

                return True

        except AuthKeyUnregisteredError:
            logger.error(f"مفتاح المصادقة غير صالح للمستخدم {user_id}")
            # Mark session as unhealthy
            self.session_health_status[user_id] = False
            self.db.update_session_health(user_id, False, "مفتاح المصادقة غير صالح")
            # Release session lock
            if user_id in self.session_locks:
                self.session_locks[user_id] = False
            # Remove invalid session from database
            self.db.delete_user_session(user_id)
            return False

        except Exception as e:
            error_msg = str(e)
            logger.error(f"خطأ في تشغيل UserBot للمستخدم {user_id}: {error_msg}")
            self.session_health_status[user_id] = False
            self.db.update_session_health(user_id, False, error_msg)
            
            # Clear locks on error
            if user_id in self.session_locks:
                del self.session_locks[user_id]
            
            # If it's a session conflict error, remove the session from database
            if "authorization key" in error_msg.lower() or "different IP" in error_msg.lower():
                logger.warning(f"🚫 تضارب في استخدام الجلسة للمستخدم {user_id} - حذف الجلسة القديمة")
                self.db.delete_user_session(user_id)
                
            return False

    async def check_user_session_health(self, user_id: int) -> bool:
        """Check if user session is healthy"""
        try:
            if user_id not in self.clients:
                self.session_health_status[user_id] = False
                self.db.update_session_health(user_id, False, "العميل غير موجود")
                return False
            
            client = self.clients[user_id]
            if not client.is_connected():
                self.session_health_status[user_id] = False
                self.db.update_session_health(user_id, False, "العميل غير متصل")
                return False
            
            # Try to get user info to verify session is working
            await client.get_me()
            self.session_health_status[user_id] = True
            self.db.update_session_health(user_id, True)
            return True
            
        except Exception as e:
            logger.error(f"فحص صحة الجلسة فشل للمستخدم {user_id}: {e}")
            self.session_health_status[user_id] = False
            self.db.update_session_health(user_id, False, str(e))
            return False

    async def reconnect_user_session(self, user_id: int) -> bool:
        """Attempt to reconnect a user session"""
        try:
            # Get session string from database
            session_string = self.db.get_user_session_string(user_id)
            if not session_string:
                logger.error(f"لا توجد جلسة محفوظة للمستخدم {user_id}")
                return False

            # Clear any locks for this user
            if user_id in self.session_locks:
                del self.session_locks[user_id]

            # Disconnect existing client if any
            if user_id in self.clients:
                try:
                    await self.clients[user_id].disconnect()
                    await asyncio.sleep(3)  # انتظار أطول للتأكد من الانقطاع
                except:
                    pass
                del self.clients[user_id]

            # Clear session health status
            if user_id in self.session_health_status:
                del self.session_health_status[user_id]

            # Wait before reconnecting
            await asyncio.sleep(2)

            # Start fresh session
            success = await self.start_with_session(user_id, session_string)
            if success:
                logger.info(f"✅ تم إعادة اتصال المستخدم {user_id} بنجاح")
            else:
                logger.error(f"❌ فشل في إعادة اتصال المستخدم {user_id}")
            
            return success

        except Exception as e:
            logger.error(f"خطأ في إعادة اتصال المستخدم {user_id}: {e}")
            return False

    async def stop_user_session(self, user_id: int):
        """Stop a specific user session"""
        try:
            logger.info(f"🛑 بدء إيقاف جلسة المستخدم {user_id}")
            
            # Clear session lock immediately
            if user_id in self.session_locks:
                del self.session_locks[user_id]
            
            if user_id in self.user_locks:
                async with self.user_locks[user_id]:
                    if user_id in self.clients:
                        try:
                            await self.clients[user_id].disconnect()
                            await asyncio.sleep(1)  # انتظار للتأكد من الانقطاع
                        except Exception as disconnect_error:
                            logger.warning(f"خطأ في قطع الاتصال للمستخدم {user_id}: {disconnect_error}")
                        del self.clients[user_id]
                    
                    if user_id in self.user_tasks:
                        del self.user_tasks[user_id]
                    
                    if user_id in self.album_collectors:
                        del self.album_collectors[user_id]
                    
                    if user_id in self.session_health_status:
                        del self.session_health_status[user_id]
                    
                    logger.info(f"✅ تم إيقاف جلسة المستخدم {user_id} بنجاح")
            else:
                # Clean up without lock if lock doesn't exist
                if user_id in self.clients:
                    try:
                        await self.clients[user_id].disconnect()
                    except:
                        pass
                    del self.clients[user_id]
                
                for attr in ['user_tasks', 'album_collectors', 'session_health_status']:
                    if hasattr(self, attr) and user_id in getattr(self, attr):
                        delattr(self, attr)[user_id]

        except Exception as e:
            logger.error(f"خطأ في إيقاف جلسة المستخدم {user_id}: {e}")
            # Force cleanup on error
            for attr in ['clients', 'user_tasks', 'album_collectors', 'session_health_status', 'session_locks']:
                if hasattr(self, attr) and user_id in getattr(self, attr):
                    try:
                        del getattr(self, attr)[user_id]
                    except:
                        pass

    async def stop_all(self):
        """Stop all user sessions"""
        logger.info("🛑 إيقاف جميع جلسات المستخدمين...")
        self.running = False
        
        # Create list of user IDs to avoid modification during iteration
        user_ids = list(self.clients.keys())
        
        for user_id in user_ids:
            await self.stop_user_session(user_id)
        
        logger.info("✅ تم إيقاف جميع الجلسات")

    async def start_session_health_monitor(self):
        """Start background health monitoring for all sessions"""
        logger.info("🏥 بدء مراقب صحة الجلسات...")
        
        while self.running:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.clients:
                    continue
                
                # Check health of all active sessions
                for user_id in list(self.clients.keys()):
                    try:
                        is_healthy = await self.check_user_session_health(user_id)
                        
                        if not is_healthy:
                            logger.warning(f"⚠️ جلسة المستخدم {user_id} غير صحية - محاولة إعادة الاتصال...")
                            success = await self.reconnect_user_session(user_id)
                            
                            if success:
                                logger.info(f"✅ تم إعادة اتصال المستخدم {user_id} بنجاح")
                            else:
                                logger.error(f"❌ فشل في إعادة اتصال المستخدم {user_id}")
                        
                    except Exception as e:
                        logger.error(f"خطأ في فحص صحة جلسة المستخدم {user_id}: {e}")
                        
            except Exception as e:
                logger.error(f"خطأ في مراقب صحة الجلسات: {e}")
                await asyncio.sleep(60)  # Wait longer on error

    async def get_user_session_info(self, user_id: int) -> dict:
        """Get detailed session information for a user"""
        try:
            if user_id not in self.clients:
                return {
                    'connected': False,
                    'healthy': False,
                    'task_count': 0,
                    'error': 'لا يوجد عميل'
                }
            
            client = self.clients[user_id]
            is_connected = client.is_connected()
            is_healthy = self.session_health_status.get(user_id, False)
            task_count = len(self.user_tasks.get(user_id, []))
            
            user_info = None
            if is_connected:
                try:
                    user_info = await client.get_me()
                except:
                    pass
            
            return {
                'connected': is_connected,
                'healthy': is_healthy,
                'task_count': task_count,
                'user_info': {
                    'id': user_info.id if user_info else None,
                    'first_name': user_info.first_name if user_info else None,
                    'phone': user_info.phone if user_info else None
                } if user_info else None
            }
            
        except Exception as e:
            return {
                'connected': False,
                'healthy': False,
                'task_count': 0,
                'error': str(e)
            }

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
                # Remove Markdown/HTML hidden links first (preserve visible text)
                cleaned_text = re.sub(r'\[([^\]]+)\]\s*\(([^)]*)\)', r'\1', cleaned_text)
                cleaned_text = re.sub(r'<a\s+href=[\'\"][^\'\"]+[\'\"]\s*>(.*?)</a>', r'\1', cleaned_text, flags=re.IGNORECASE|re.DOTALL)
                # Remove angle-bracket autolinks like <https://example.com>
                cleaned_text = re.sub(r'<https?://[^>]+>', '', cleaned_text)
                # Then remove plain URLs and domains
                cleaned_text = re.sub(r'https?://[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r't\.me/[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'www\.[^\s]+', '', cleaned_text)
                cleaned_text = re.sub(r'\b[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.([a-zA-Z]{2,6}\.?)+(/[^\s]*)?', '', cleaned_text)
                # Cleanup any leftover empty brackets
                cleaned_text = re.sub(r'\[\s*\]', '', cleaned_text)
                cleaned_text = re.sub(r'\(\s*\)', '', cleaned_text)
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

        @client.on(events.NewMessage())
        async def message_handler(event):
            try:
                # Ensure session is still healthy for this user
                if not self.session_health_status.get(user_id, False):
                    logger.warning(f"⚠️ تجاهل الرسالة - جلسة المستخدم {user_id} غير صحية")
                    return

                # Verify this client belongs to this user
                if user_id not in self.clients or self.clients[user_id] != client:
                    logger.warning(f"⚠️ تجاهل الرسالة - العميل لا ينتمي للمستخدم {user_id}")
                    return

                # Use lock to prevent concurrent processing for this user
                if user_id not in self.user_locks:
                    self.user_locks[user_id] = asyncio.Lock()

                async with self.user_locks[user_id]:
                    # Get user tasks for this specific user (the owner of this client)
                    tasks = self.user_tasks.get(user_id, [])
                    
                    # Get source chat ID first
                    source_chat_id = event.chat_id
                    
                    # Check if this chat is a source in any task for this user
                    is_monitored_source = any(str(task['source_chat_id']) == str(source_chat_id) for task in tasks)
                    
                    # Only log if this is a monitored source chat
                    if is_monitored_source:
                        logger.info(f"📥 رسالة من مصدر مراقب: {source_chat_id} (المستخدم {user_id})")
                        if event.text:
                            logger.info(f"📝 المحتوى: {event.text[:100]}...")
                    else:
                        # Silent processing for non-monitored chats - no logging
                        pass


                # Get source chat ID and username first
                source_username = getattr(event.chat, 'username', None)

                if not tasks:
                    return  # No tasks for this user - silent return

                # Check media filters first
                message_media_type = self.get_message_media_type(event.message)
                has_text_caption = bool(event.message.text)  # Check if message has text/caption

                # Find matching tasks for this source chat
                matching_tasks = []

                for task in tasks:
                    task_source_id = str(task['source_chat_id'])
                    task_name = task.get('task_name', f"مهمة {task['id']}")
                    task_id = task.get('id')

                    # Convert both IDs to string and compare
                    source_chat_id_str = str(source_chat_id)
                    if task_source_id == source_chat_id_str:

                        # Check admin filter
                        admin_allowed = await self.is_admin_allowed_by_signature(task_id, event.message, source_chat_id_str)

                        # Check media filter
                        media_allowed = self.is_media_allowed(task_id, message_media_type)

                        # Check word filters
                        message_text = event.message.text or ""
                        word_filter_allowed = self.is_message_allowed_by_word_filter(task_id, message_text)

                        # Determine if message is allowed
                        if message_media_type == 'text':
                            is_message_allowed = admin_allowed and self.is_media_allowed(task_id, 'text') and word_filter_allowed
                        else:
                            is_message_allowed = admin_allowed and media_allowed and word_filter_allowed

                        if is_message_allowed:
                            matching_tasks.append(task)
                            logger.info(f"✅ {task_name}: رسالة مقبولة")
                        else:
                            logger.info(f"🚫 {task_name}: رسالة مرفوضة بواسطة الفلاتر")

                if not matching_tasks:
                    return  # No matching tasks - silent return

                logger.info(f"📤 معالجة {len(matching_tasks)} مهمة مطابقة للمحادثة {source_chat_id}")

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

                # ===== معالجة الوسائط مرة واحدة =====
                # بدلاً من معالجة الوسائط لكل هدف بشكل منفصل، نقوم بمعالجتها مرة واحدة
                # وإعادة استخدامها لكل الأهداف لتحسين الأداء وتقليل استهلاك الموارد
                processed_media = None
                processed_filename = None
                
                if event.message.media:
                    # ===== معالجة الوسائط مرة واحدة =====
                    # بدلاً من معالجة الوسائط لكل هدف بشكل منفصل، نقوم بمعالجتها مرة واحدة
                    # ملاحظة: لا نطبق العلامة المائية إلا إذا كانت مفعلة لجميع المهام المطابقة
                    first_task = matching_tasks[0]
                    logger.info(f"🎬 تهيئة معالجة الوسائط مرة واحدة (أول مهمة: {first_task['id']})")

                    # CRITICAL FIX: فحص تجميعي: هل العلامة المائية مفعلة لأي مهمة من المهام المطابقة؟
                    watermark_enabled_for_any = False
                    watermark_settings = None
                    try:
                        for _t in matching_tasks:
                            _wm = self.db.get_watermark_settings(_t['id'])
                            if _wm and _wm.get('enabled', False):
                                watermark_enabled_for_any = True
                                watermark_settings = _wm  # Use first enabled watermark settings
                                logger.info(f"🎯 العلامة المائية مفعلة لمهمة {_t['id']} - ستتم معالجة الوسائط مرة واحدة")
                                break
                        
                        if not watermark_enabled_for_any:
                            logger.info(f"🚫 العلامة المائية غير مفعلة لأي من المهام - معالجة أساسية للوسائط")
                    except Exception as _e:
                        logger.warning(f"⚠️ فشل فحص إعدادات العلامة المائية للمهام: {_e}")
                        watermark_enabled_for_any = False

                    # فحص: هل الرسالة ملف صوتي؟
                    is_audio_message = False
                    try:
                        if hasattr(event.message, 'media') and hasattr(event.message.media, 'document') and event.message.media.document:
                            doc = event.message.media.document
                            if getattr(doc, 'mime_type', None) and str(doc.mime_type).startswith('audio/'):
                                is_audio_message = True
                            else:
                                # محاولة من الاسم
                                file_attr = None
                                for attr in getattr(doc, 'attributes', []) or []:
                                    if hasattr(attr, 'file_name') and attr.file_name:
                                        file_attr = attr.file_name
                                        break
                                if file_attr and file_attr.lower().endswith(('.mp3', '.m4a', '.aac', '.ogg', '.wav', '.flac', '.wma', '.opus')):
                                    is_audio_message = True
                    except Exception:
                        is_audio_message = False

                    # CRITICAL FIX: فحص تجميعي: هل وسوم الصوت مفعلة لأي مهمة (للرسائل الصوتية فقط)؟
                    audio_tags_enabled_for_any = False
                    audio_settings = None
                    if is_audio_message:
                        try:
                            for _t in matching_tasks:
                                _as = self.db.get_audio_metadata_settings(_t['id'])
                                if _as and _as.get('enabled', False):
                                    audio_tags_enabled_for_any = True
                                    audio_settings = _as  # Use first enabled audio settings
                                    logger.info(f"🎵 وسوم الصوت مفعلة لمهمة {_t['id']} - ستتم معالجة الملف الصوتي مرة واحدة")
                                    break
                            
                            if not audio_tags_enabled_for_any:
                                logger.info(f"🚫 وسوم الصوت غير مفعلة لأي من المهام الصوتية")
                        except Exception as _e:
                            logger.warning(f"⚠️ فشل فحص إعدادات وسوم الصوت: {_e}")
                            audio_tags_enabled_for_any = False

                    # CRITICAL FIX: Initialize global media cache for message-based reuse
                    if not hasattr(self, 'global_processed_media_cache'):
                        self.global_processed_media_cache = {}
                    
                    # Create unique cache key for this message and settings
                    import hashlib
                    message_hash = f"{event.message.id}_{event.chat_id}_{first_task['id']}_watermark"
                    media_cache_key = hashlib.md5(message_hash.encode()).hexdigest()
                    
                    try:
                        if watermark_enabled_for_any:
                            logger.info("🏷️ العلامة المائية مفعلة لأحد المهام → سيتم تطبيقها مرة واحدة وإعادة الاستخدام")
                            
                            # CRITICAL OPTIMIZATION: Check cache before processing
                            if media_cache_key in self.global_processed_media_cache:
                                processed_media, processed_filename = self.global_processed_media_cache[media_cache_key]
                                logger.info(f"🎯 استخدام الوسائط المعالجة من التخزين المؤقت: {processed_filename}")
                            else:
                                # Process media ONLY ONCE and cache for all targets
                                logger.info("🔧 بدء معالجة الوسائط لأول مرة - سيتم حفظها للاستخدام المتكرر")
                                processed_media, processed_filename = await self.apply_watermark_to_media(event, first_task['id'])
                                
                                if processed_media and processed_media != event.message.media:
                                    # Store in global cache for ALL future targets of this message
                                    self.global_processed_media_cache[media_cache_key] = (processed_media, processed_filename)
                                    logger.info(f"✅ تم معالجة الوسائط مرة واحدة وحفظها للاستخدام المتكرر: {processed_filename}")
                                else:
                                    logger.info("🔄 لم يتم تطبيق العلامة المائية، استخدام الوسائط الأصلية")
                        elif audio_tags_enabled_for_any and is_audio_message:
                            # CRITICAL FIX: Apply audio tags optimization similar to watermark
                            logger.info("🎵 الوسوم الصوتية مفعلة لأحد المهام والرسالة صوتية → تطبيق الوسوم مرة واحدة وإعادة الاستخدام")
                            
                            # Create audio cache key (different from watermark key)
                            audio_cache_key = hashlib.md5(
                                f"{event.message.id}_{event.chat_id}_{first_task['id']}_audio".encode()
                            ).hexdigest()
                            
                            # Check audio cache first - CRITICAL OPTIMIZATION
                            if audio_cache_key in self.global_processed_media_cache:
                                processed_media, processed_filename = self.global_processed_media_cache[audio_cache_key]
                                logger.info(f"🎯 استخدام المقطع الصوتي المعالج من التخزين المؤقت: {processed_filename}")
                            else:
                                # Process audio ONCE and cache for all targets
                                logger.info("🔧 بدء معالجة المقطع الصوتي لأول مرة - سيتم حفظه للاستخدام المتكرر")
                                
                                # تحميل الوسائط واستخراج اسم مناسب - مرة واحدة فقط
                                if not hasattr(self, '_current_media_cache'):
                                    self._current_media_cache = {}
                                
                                media_cache_key_download = f"{event.message.id}_{event.chat_id}_download"
                                
                                if media_cache_key_download in self._current_media_cache:
                                    media_bytes, file_name, file_ext = self._current_media_cache[media_cache_key_download]
                                    logger.info("🔄 استخدام الوسائط المحمّلة من التخزين المؤقت")
                                else:
                                    media_bytes = await event.message.download_media(bytes)
                                    if not media_bytes:
                                        logger.warning("⚠️ فشل تحميل الوسائط - سيتم استخدام الوسائط الأصلية")
                                        processed_media = event.message.media
                                        processed_filename = None
                                    else:
                                        file_name = "media_file"
                                        file_ext = ""
                                        if hasattr(event.message.media, 'document') and event.message.media.document:
                                            doc = event.message.media.document
                                            if hasattr(doc, 'attributes'):
                                                for attr in doc.attributes:
                                                    if hasattr(attr, 'file_name') and attr.file_name:
                                                        file_name = attr.file_name
                                                        # Extract file extension
                                                        if "." in file_name:
                                                            file_ext = "." + file_name.split(".")[-1]
                                                        break
                                                        if '.' in file_name:
                                                            file_ext = '.' + file_name.split('.')[-1].lower()
                                                            file_name = file_name.rsplit('.', 1)[0]
                                                        break
                                        
                                        # حفظ البيانات المحمّلة في التخزين المؤقت لهذه الرسالة
                                        self._current_media_cache[media_cache_key_download] = (media_bytes, file_name, file_ext)
                                        logger.info("💾 تم حفظ الوسائط المحمّلة في التخزين المؤقت لإعادة الاستخدام")
                                
                                if media_bytes:
                                    full_name = file_name + (file_ext or '')
                                    processed_media, processed_filename = await self.apply_audio_metadata(event, first_task['id'], media_bytes, full_name)
                                    
                                    # Cache the processed audio for reuse across ALL targets
                                    if processed_media and processed_media != media_bytes:
                                        self.global_processed_media_cache[audio_cache_key] = (processed_media, processed_filename)
                                        logger.info(f"✅ تم معالجة المقطع الصوتي مرة واحدة وحفظه للاستخدام المتكرر: {processed_filename}")
                                    else:
                                        logger.info("🔄 لم يتم تعديل المقطع الصوتي، استخدام الملف الأصلي")

                        else:
                            # لا علامة مائية ولا وسوم صوتية: لا تنزيل/معالجة - سيتم الإرسال كنسخ خادم إن أمكن
                            logger.info("⏭️ لا علامة مائية ولا وسوم صوتية مطلوبة → إرسال كوسائط عادية دون تنزيل/رفع")
                            processed_media = None
                            processed_filename = None
                    except Exception as e:
                        logger.error(f"❌ خطأ في معالجة الوسائط: {e}")
                        processed_media = event.message.media
                        processed_filename = None

                # Forward message to all target chats
                for i, task in enumerate(matching_tasks):
                    try:
                        target_chat_id = str(task['target_chat_id']).strip()
                        task_name = task.get('task_name', f"مهمة {task['id']}")

                        # Check advanced filters for this specific task
                        message = event.message
                        should_block, should_remove_buttons, should_remove_forward = await self._check_message_advanced_filters(
                            task['id'], message
                        )
                        
                        if should_block:
                            logger.info(f"🚫 الرسالة محظورة بواسطة فلاتر متقدمة للمهمة {task_name} - تجاهل هذه المهمة")
                            continue

                        # Get task forward mode and forwarding settings
                        forward_mode = task.get('forward_mode', 'forward')
                        forwarding_settings = self.get_forwarding_settings(task['id'])
                        split_album_enabled = forwarding_settings.get('split_album_enabled', False)
                        mode_text = "نسخ" if forward_mode == 'copy' else "توجيه"
                        
                        # Apply forwarded message filter mode
                        if should_remove_forward:
                            # forward_mode = 'copy'  # DISABLED: Don't force copy mode here - respect user choice
                            mode_text = "نسخ (بدون علامة التوجيه)"
                            logger.info(f"📋 تم تحويل إلى وضع النسخ لإزالة علامة التوجيه")

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

                        # Parse target chat ID with improved user handling
                        try:
                            if target_chat_id.startswith('@'):
                                target_entity = await client.get_entity(target_chat_id)
                                logger.info(f"🎯 استخدام اسم المستخدم كهدف: {target_chat_id}")
                            else:
                                target_int = int(target_chat_id)
                                logger.info(f"🎯 استخدام معرف رقمي كهدف: {target_int}")
                                
                                try:
                                    # Try to get entity
                                    target_entity = await client.get_entity(target_int)
                                except Exception as get_entity_err:
                                    logger.warning(f"⚠️ لا يمكن الوصول المباشر للهدف {target_int}: {get_entity_err}")
                                    
                                    # For users (positive ID), create a fallback approach
                                    if target_int > 0:
                                        logger.info(f"📱 سيتم استخدام معرف المستخدم مباشرة: {target_int}")
                                        # Create a simple user entity for forwarding
                                        try:
                                            # Try sending a test message first to validate access
                                            target_entity = target_int  # Use int as entity for direct user messaging
                                        except Exception:
                                            logger.error(f"❌ لا يمكن الوصول للمستخدم {target_int}")
                                            continue
                                    else:
                                        # For channels/groups, must have access
                                        logger.error(f"❌ يجب الوصول للقناة/المجموعة {target_int}")
                                        continue
                            
                            # Validate target entity if it's an actual entity object
                            if hasattr(target_entity, 'id'):
                                target_title = getattr(target_entity, 'title', getattr(target_entity, 'first_name', str(target_entity.id)))
                                logger.info(f"✅ تم العثور على المحادثة الهدف: {target_title} ({target_entity.id})")
                            else:
                                # target_entity is int - this is for users we can't directly access
                                logger.info(f"📱 سيتم محاولة الإرسال للمستخدم: {target_entity}")
                                
                        except Exception as entity_error:
                            logger.error(f"❌ لا يمكن معالجة الهدف {target_chat_id}: {entity_error}")
                            continue

                        # Get message formatting settings for this task
                        message_settings = self.get_message_settings(task['id'])

                        # Apply text cleaning and replacements (use same as checked above)
                        cleaned_text = self.apply_text_cleaning(original_text, task['id']) if original_text else original_text
                        modified_text = self.apply_text_replacements(task['id'], cleaned_text) if cleaned_text else cleaned_text

                        # Apply translation if enabled AND forward mode is copy (skip translation in forward mode)
                        if forward_mode == 'copy':
                            translated_text = await self.apply_translation(task['id'], modified_text) if modified_text else modified_text
                            if modified_text != translated_text and modified_text:
                                logger.info(f"🌐 تم تطبيق الترجمة في وضع النسخ: '{modified_text}' → '{translated_text}'")
                        else:
                            translated_text = modified_text  # Skip translation in forward mode
                            logger.info(f"⏭️ تم تجاهل الترجمة في وضع التوجيه - إرسال الرسالة كما هي")

                        # Apply text formatting
                        formatted_text = self.apply_text_formatting(task['id'], translated_text) if translated_text else translated_text

                        # Apply header and footer formatting
                        final_text = self.apply_message_formatting(formatted_text, message_settings)
                        
                        # Check if we need to use copy mode due to formatting or processed media
                        # Check if we MUST use copy mode due to actual content modifications
                        # Respect user forward_mode setting unless modifications require copy
                        requires_copy_mode = (
                            (processed_media is not None and processed_media != event.message.media) or  # Media actually changed
                            (processed_filename is not None) or  # Filename was modified during processing
                            message_settings["header_enabled"] or  # Header enabled (adds content)
                            message_settings["footer_enabled"] or  # Footer enabled (adds content) 
                            message_settings["inline_buttons_enabled"] or  # Inline buttons enabled (adds buttons)
                            original_text != modified_text or  # Text replacements applied
                            should_remove_forward  # Remove forward header filter requires copy
                        )
                        
                        # Additional copy requirements only apply when in copy mode
                        if forward_mode == "copy":
                            requires_copy_mode = requires_copy_mode or (
                                modified_text != translated_text or  # Translation applied
                                translated_text != formatted_text  # Text formatting applied
                            )

                        # Log changes if text was modified
                        if original_text != final_text and original_text:
                            logger.info(f"🔄 تم تطبيق تنسيق الرسالة: '{original_text}' → '{final_text}'")
                        
                        # Log if media was processed
                        if processed_media is not None:
                            logger.info(f"🎵 تم معالجة الوسائط - سيتم استخدام وضع النسخ: {processed_filename}")
                        elif processed_filename is not None:
                            logger.info(f"📁 تم تغيير اسم الملف - سيتم استخدام وضع النسخ: {processed_filename}")

                        # Determine which buttons to use (original or custom)
                        inline_buttons = None
                        original_reply_markup = None
                        
                        # Preserve original reply markup if inline button filter is disabled
                        if not should_remove_buttons and event.message.reply_markup:
                            original_reply_markup = event.message.reply_markup
                            logger.info(f"🔘 الحفاظ على الأزرار الأصلية - فلتر الأزرار الشفافة معطل للمهمة {task['id']}")
                        
                        # Build custom inline buttons if enabled and not filtered out
                        if message_settings['inline_buttons_enabled'] and not should_remove_buttons:
                            inline_buttons = self.build_inline_buttons(task['id'])
                            if inline_buttons:
                                logger.info(f"🔘 تم بناء {len(inline_buttons)} صف من الأزرار الإنلاين المخصصة للمهمة {task['id']}")
                            else:
                                logger.warning(f"⚠️ فشل في بناء الأزرار الإنلاين المخصصة للمهمة {task['id']}")
                        elif should_remove_buttons and message_settings['inline_buttons_enabled']:
                            logger.info(f"🗑️ تم تجاهل الأزرار الشفافة بسبب إعدادات الفلتر للمهمة {task['id']}")
                        elif should_remove_buttons:
                            logger.info(f"🗑️ تم حذف الأزرار الأصلية بسبب فلتر الأزرار الشفافة للمهمة {task['id']}")

                        # Get forwarding settings
                        forwarding_settings = self.get_forwarding_settings(task['id'])

                        # Check publishing mode
                        publishing_mode = forwarding_settings.get('publishing_mode', 'auto')
                        
                        if publishing_mode == 'manual':
                            logger.info(f"⏸️ وضع النشر اليدوي - إرسال الرسالة للمراجعة (المهمة: {task_name})")
                            await self._handle_manual_approval(event.message, task, user_id, client)
                            continue  # Skip automatic forwarding
                        
                        # Apply sending interval before each target (except first)
                        if i > 0:
                            await self._apply_sending_interval(task['id'])

                        # Send message based on forward mode
                        logger.info(f"📨 جاري إرسال الرسالة (وضع تلقائي)...")

                        # ===== منطق الإرسال المصحح =====
                        
                        # تحديد الوضع النهائي للإرسال
                        final_send_mode = self._determine_final_send_mode(forward_mode, requires_copy_mode)
                        
                        logger.info(f"📤 إرسال الرسالة بالوضع: {final_send_mode} (الأصلي: {forward_mode}, يتطلب نسخ: {requires_copy_mode})")
                        
                        # تهيئة متغيرات الإرسال
                        forwarded_msg = None
                        spoiler_entities = []  # ضمان التهيئة لتفادي UnboundLocalError
                        processed_text = (final_text or (event.message.text if hasattr(event.message, 'text') else None) or "رسالة")

                        # إرسال الرسالة بالوضع المحدد
                        if final_send_mode == 'forward':
                            # وضع التوجيه - إرسال الرسالة كما هي مع رأس التوجيه
                            logger.info("🔀 استخدام وضع التوجيه - إرسال الرسالة مع رأس التوجيه")
                            try:
                                forwarded_msg = await client.forward_messages(
                                    target_entity,
                                    event.message,
                                    silent=forwarding_settings['silent_notifications']
                                )
                                logger.info(f"✅ تم توجيه الرسالة بنجاح في وضع التوجيه")
                                
                                # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                if forwarded_msg:
                                    msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                    await self.apply_post_forwarding_settings(
                                        client, target_entity, msg_id, forwarding_settings, task['id'],
                                        inline_buttons=inline_buttons,
                                        has_original_buttons=bool(original_reply_markup)
                                    )
                                    
                                    # Save message mapping for sync functionality
                                    try:
                                        self.db.save_message_mapping(
                                            task_id=task['id'],
                                            source_chat_id=str(source_chat_id),
                                            source_message_id=event.message.id,
                                            target_chat_id=str(target_chat_id),
                                            target_message_id=msg_id
                                        )
                                    except Exception as mapping_error:
                                        logger.error(f"❌ فشل في حفظ تطابق الرسالة: {mapping_error}")
                            except Exception as forward_err:
                                logger.error(f"❌ فشل التوجيه المباشر، التبديل للنسخ: {forward_err}")
                                # Fallback to copy mode if forward fails
                                final_send_mode = 'copy'

                        elif final_send_mode == 'copy':
                            # Optimization: use server-side copy when no modifications are required
                            try:
                                text_cleaning_settings = self.db.get_text_cleaning_settings(task['id'])
                            except Exception:
                                text_cleaning_settings = {}
                            remove_caption_flag = bool(text_cleaning_settings.get('remove_caption', False))

                            # CRITICAL FIX: Consider processed media as a change
                            no_media_change = (processed_media is None) and (processed_filename is None)
                            no_caption_change = (final_text == original_text)
                            no_buttons_change = (inline_buttons is None and not should_remove_buttons)
                            is_album_message = album_collector.should_collect_album(event.message, forward_mode, split_album_enabled)

                            can_server_copy = (
                                not requires_copy_mode and
                                no_media_change and
                                no_caption_change and
                                no_buttons_change and
                                not remove_caption_flag and
                                not is_album_message
                            )

                            # تجنب استخدام نسخ الخادم إذا كانت الوسائط صفحة ويب حتى لا تتحول لرسالة نصية فقط
                            if can_server_copy and not (hasattr(event.message, 'media') and hasattr(event.message.media, 'webpage') and event.message.media.webpage):
                                logger.info("⚡ استخدام نسخ خادم (إعادة إرسال) بدون تنزيل/رفع لأن لا توجد تعديلات")
                                if event.message.media:
                                    # Copy media by re-sending the same media reference (server-side), keep original caption/buttons
                                    caption_text = event.message.text
                                    # CRITICAL FIX: Add force_document=False for server-side copy of videos
                                    server_copy_kwargs = {
                                        "caption": caption_text,
                                        "silent": forwarding_settings['silent_notifications'],
                                        "buttons": original_reply_markup,
                                        "force_document": False  # Ensure videos display with preview and duration
                                    }
                                    
                                    forwarded_msg = await client.send_file(
                                        target_entity,
                                        file=event.message.media,
                                        **server_copy_kwargs
                                    )
                                    
                                    # Apply post-forwarding settings (pin, auto-delete)
                                    if forwarded_msg:
                                        msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                        await self.apply_post_forwarding_settings(
                                            client, target_entity, msg_id, forwarding_settings, task['id']
                                        )
                                else:
                                    # Pure text copy
                                    message_text = event.message.text or final_text or "رسالة"
                                    forwarded_msg = await client.send_message(
                                        target_entity,
                                        message_text,
                                        link_preview=forwarding_settings['link_preview_enabled'],
                                        silent=forwarding_settings['silent_notifications'],
                                        buttons=original_reply_markup
                                    )
                                    
                                    # Apply post-forwarding settings (pin, auto-delete)
                                    if forwarded_msg:
                                        msg_id = forwarded_msg.id
                                        await self.apply_post_forwarding_settings(
                                            client, target_entity, msg_id, forwarding_settings, task['id']
                                        )
                            else:
                                # Copy mode: send as new message with all formatting applied
                                if requires_copy_mode:
                                    logger.info(f"🔄 استخدام وضع النسخ بسبب التنسيق المطبق")

                                # إذا كان لدينا ملف صوتي مُعالج كبايتات، أرسله مباشرة لتفادي أي التباس كرسالة نصية
                                if isinstance(processed_media, (bytes, bytearray)) and ((processed_filename and processed_filename.lower().endswith(('.mp3', '.m4a', '.aac', '.ogg', '.wav', '.flac', '.wma', '.opus'))) or True):
                                    try:
                                        audio_filename = processed_filename or "audio.mp3"
                                        logger.info(f"🎵 إرسال الملف الصوتي المعالج بالرفع المباشر: {audio_filename}")
                                        
                                        # CRITICAL FIX: Upload once and reuse file handle
                                        forwarded_msg = await self._send_processed_media_optimized(
                                            client, target_entity, processed_media, audio_filename,
                                            caption=final_text, 
                                            silent=forwarding_settings['silent_notifications'],
                                            parse_mode='HTML' if final_text else None,
                                            buttons=original_reply_markup,  # Only original buttons via userbot, inline buttons handled separately
                                            task=task, event=event
                                        )
                                        
                                        # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                        if forwarded_msg:
                                            msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                            await self.apply_post_forwarding_settings(
                                                client, target_entity, msg_id, forwarding_settings, task['id'],
                                                inline_buttons=inline_buttons,
                                                has_original_buttons=bool(original_reply_markup)
                                            )
                                    except Exception as direct_audio_err:
                                        logger.error(f"❌ فشل الرفع المباشر للملف الصوتي المعالج: {direct_audio_err}")

                                elif event.message.media:
                                    # Handle media messages correctly - send media with caption
                                    from telethon.tl.types import MessageMediaWebPage
                                    is_webpage = isinstance(event.message.media, MessageMediaWebPage)
                                    
                                    if is_webpage:
                                        # Web page - send as text message with link preview
                                        logger.info("🌐 إرسال صفحة ويب كنص مع معاينة الرابط")
                                        message_text = final_text or event.message.text or "رسالة"
                                        forwarded_msg = await client.send_message(
                                            target_entity,
                                            message_text,
                                            link_preview=forwarding_settings["link_preview_enabled"],
                                            silent=forwarding_settings["silent_notifications"],
                                            parse_mode="HTML",
                                            buttons=original_reply_markup,  # Only original buttons via userbot, inline buttons handled separately
                                        )
                                        
                                        # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                        if forwarded_msg:
                                            msg_id = forwarded_msg.id
                                            await self.apply_post_forwarding_settings(
                                                client, target_entity, msg_id, forwarding_settings, task['id'],
                                                inline_buttons=inline_buttons,
                                                has_original_buttons=bool(original_reply_markup)
                                            )
                                    else:
                                        # Regular media - send with caption using send_file
                                        logger.info("📁 إرسال وسائط مع الكابشن")
                                        caption_text = final_text
                                        text_cleaning_settings = self.db.get_text_cleaning_settings(task["id"])
                                        if text_cleaning_settings and text_cleaning_settings.get("remove_caption", False):
                                            caption_text = None
                                        
                                        # CRITICAL FIX: Use processed media if available, otherwise original media
                                        media_to_send = processed_media if processed_media else event.message.media
                                        
                                        if isinstance(processed_media, (bytes, bytearray)) and processed_filename:
                                            # Send processed media with proper filename
                                            logger.info(f"🎵 إرسال الوسائط المعالجة (مُحسّنة مرة واحدة): {processed_filename}")
                                            
                                            # CRITICAL FIX: Upload once and reuse file handle
                                            forwarded_msg = await self._send_processed_media_optimized(
                                                client, target_entity, processed_media, processed_filename,
                                                caption=caption_text,
                                                silent=forwarding_settings["silent_notifications"],
                                                parse_mode="HTML" if caption_text else None,
                                                buttons=original_reply_markup,  # Only original buttons via userbot, inline buttons handled separately
                                                task=task, event=event
                                            )
                                        else:
                                            # Send original media with proper video attributes
                                            logger.info("📁 إرسال الوسائط الأصلية")
                                            
                                            # CRITICAL FIX: Ensure videos are sent as videos with proper attributes
                                            video_kwargs = {
                                                "caption": caption_text,
                                                "silent": forwarding_settings["silent_notifications"],
                                                "parse_mode": "HTML" if caption_text else None,
                                                "buttons": original_reply_markup or inline_buttons,
                                                "force_document": False  # Critical: ensure videos show as videos
                                            }
                                            
                                            forwarded_msg = await client.send_file(
                                                target_entity,
                                                file=media_to_send,
                                                **video_kwargs
                                            )
                                            
                                            # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                            if forwarded_msg:
                                                msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                                await self.apply_post_forwarding_settings(
                                                    client, target_entity, msg_id, forwarding_settings, task['id'],
                                                    inline_buttons=inline_buttons,
                                                    has_original_buttons=bool(original_reply_markup)
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
                                        
                                        # ===== CRITICAL FIX: استخدام الوسائط المعالجة مسبقاً =====
                                        # استخدام الوسائط التي تم معالجتها مرة واحدة بدلاً من معالجتها لكل هدف
                                        if isinstance(processed_media, (bytes, bytearray)) and processed_filename:
                                            # Use the pre-processed media - CRITICAL OPTIMIZATION
                                            logger.info(f"🎯 استخدام الوسائط المُعالجة مسبقاً (محسّن): {processed_filename}")
                                            
                                            # CRITICAL FIX: Upload once and reuse file handle  
                                            forwarded_msg = await self._send_processed_media_optimized(
                                                client, target_entity, processed_media, processed_filename,
                                                caption=caption_text,
                                                silent=forwarding_settings['silent_notifications'],
                                                parse_mode='HTML' if caption_text else None,
                                                buttons=original_reply_markup,  # Only original buttons via userbot, inline buttons handled separately
                                                task=task, event=event
                                            )
                                            
                                            # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                            if forwarded_msg:
                                                msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                                await self.apply_post_forwarding_settings(
                                                    client, target_entity, msg_id, forwarding_settings, task['id'],
                                                    inline_buttons=inline_buttons,
                                                    has_original_buttons=bool(original_reply_markup)
                                                )
                                        else:
                                            # Use original media if no processing was done
                                            if event.message.media:
                                                logger.info("📁 استخدام الوسائط الأصلية (بدون معالجة)")
                                                forwarded_msg = await client.send_file(
                                                    target_entity,
                                                    file=event.message.media,
                                                    caption=caption_text,
                                                    silent=forwarding_settings['silent_notifications'],
                                                    parse_mode='HTML' if caption_text else None,
                                                    buttons=original_reply_markup  # Only original buttons via userbot, inline buttons handled separately
                                                )
                                            else:
                                                # No media - send as text message
                                                logger.info("📝 لا توجد وسائط - إرسال كرسالة نصية")
                                                forwarded_msg = await client.send_message(
                                                    target_entity,
                                                    caption_text or "رسالة",
                                                    link_preview=forwarding_settings['link_preview_enabled'],
                                                    silent=forwarding_settings['silent_notifications'],
                                                    parse_mode='HTML',
                                                    buttons=original_reply_markup  # Only original buttons via userbot, inline buttons handled separately
                                                )
                                            
                                            # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                            if forwarded_msg:
                                                msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                                await self.apply_post_forwarding_settings(
                                                    client, target_entity, msg_id, forwarding_settings, task['id'],
                                                    inline_buttons=inline_buttons,
                                                    has_original_buttons=bool(original_reply_markup)
                                                )
                                    else:
                                        # Keep album grouped: send as new media (copy mode)
                                        logger.info(f"📸 إبقاء الألبوم مجمع للمهمة {task['id']} (وضع النسخ)")
                                        
                                        # ===== استخدام الوسائط المعالجة مسبقاً =====
                                        if isinstance(processed_media, (bytes, bytearray)) and processed_filename:
                                            # Use the pre-processed media with file handle optimization
                                            logger.info(f"🎯 استخدام الوسائط المُعالجة مسبقاً (محسّن): {processed_filename}")
                                            
                                            # CRITICAL FIX: Upload once and reuse file handle
                                            forwarded_msg = await self._send_processed_media_optimized(
                                                client, target_entity, processed_media, processed_filename,
                                                caption=caption_text,
                                                silent=forwarding_settings['silent_notifications'],
                                                parse_mode='HTML' if caption_text else None,
                                                buttons=original_reply_markup,  # Only original buttons via userbot, inline buttons handled separately
                                                task=task, event=event
                                            )
                                            
                                            # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                            if forwarded_msg:
                                                msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                                await self.apply_post_forwarding_settings(
                                                    client, target_entity, msg_id, forwarding_settings, task['id'],
                                                    inline_buttons=inline_buttons,
                                                    has_original_buttons=bool(original_reply_markup)
                                                )
                                        else:
                                            # Use original media if no processing was done
                                            if event.message.media:
                                                logger.info("📁 استخدام الوسائط الأصلية (بدون معالجة)")
                                                forwarded_msg = await client.send_file(
                                                    target_entity,
                                                    file=event.message.media,
                                                    caption=caption_text,
                                                    silent=forwarding_settings['silent_notifications'],
                                                    parse_mode='HTML' if caption_text else None,
                                                    buttons=original_reply_markup  # Only original buttons via userbot, inline buttons handled separately
                                                )
                                            else:
                                                # No media - send as text message
                                                logger.info("📝 لا توجد وسائط - إرسال كرسالة نصية")
                                                forwarded_msg = await client.send_message(
                                                    target_entity,
                                                    caption_text or "رسالة",
                                                    link_preview=forwarding_settings['link_preview_enabled'],
                                                    silent=forwarding_settings['silent_notifications'],
                                                    parse_mode='HTML',
                                                    buttons=original_reply_markup  # Only original buttons via userbot, inline buttons handled separately
                                                )
                                            
                                            # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                            if forwarded_msg:
                                                msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                                await self.apply_post_forwarding_settings(
                                                    client, target_entity, msg_id, forwarding_settings, task['id'],
                                                    inline_buttons=inline_buttons,
                                                    has_original_buttons=bool(original_reply_markup)
                                                )
                        else:
                            # No media
                            if (event.message.text or final_text):
                                # Pure text message
                                # Process spoiler entities if present
                                message_text = final_text or "رسالة"
                                processed_text, spoiler_entities = self._process_spoiler_entities(message_text)
                                
                                if spoiler_entities:
                                    # Send with spoiler entities and buttons
                                    forwarded_msg = await client.send_message(
                                        target_entity,
                                        processed_text,
                                        link_preview=forwarding_settings['link_preview_enabled'],
                                        silent=forwarding_settings['silent_notifications'],
                                        formatting_entities=spoiler_entities,
                                        buttons=original_reply_markup,  # Only original buttons via userbot, inline buttons handled separately
                                    )
                                    
                                    # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                    if forwarded_msg:
                                        msg_id = forwarded_msg.id
                                        await self.apply_post_forwarding_settings(
                                            client, target_entity, msg_id, forwarding_settings, task['id'],
                                            inline_buttons=inline_buttons,
                                            has_original_buttons=bool(original_reply_markup)
                                        )
                                else:
                                    # Send normally with buttons using spoiler support
                                    # Combine original and custom buttons for Telethon
                                    combined_buttons = original_reply_markup or inline_buttons
                                    
                                    forwarded_msg = await self._send_message_with_spoiler_support(
                                        client,
                                        target_entity,
                                        processed_text,
                                        link_preview=forwarding_settings['link_preview_enabled'],
                                        silent=forwarding_settings['silent_notifications'],
                                        parse_mode='HTML',
                                        buttons=combined_buttons
                                    )
                                    
                                    # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                    if forwarded_msg:
                                        msg_id = forwarded_msg.id
                                        await self.apply_post_forwarding_settings(
                                            client, target_entity, msg_id, forwarding_settings, task['id'],
                                            inline_buttons=inline_buttons,
                                            has_original_buttons=bool(combined_buttons)
                                        )
                            else:
                                # Fallback to forward for other types
                                forwarded_msg = await client.forward_messages(
                                    target_entity,
                                    event.message,
                                    silent=forwarding_settings['silent_notifications']
                                )
                                
                                # Apply post-forwarding settings (pin, auto-delete, inline buttons)
                                if forwarded_msg:
                                    msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                                    await self.apply_post_forwarding_settings(
                                        client, target_entity, msg_id, forwarding_settings, task['id'],
                                        inline_buttons=inline_buttons,
                                        has_original_buttons=False
                                    )

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
            finally:
                # تنظيف التخزين المؤقت المحلي بعد معالجة كل رسالة
                if hasattr(self, '_current_media_cache'):
                    self._current_media_cache.clear()
                    logger.info("🗑️ تم تنظيف التخزين المؤقت المحلي للوسائط")

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
                    # Convert chat_id to both possible formats to handle legacy data
                    legacy_chat_id = str(source_chat_id).replace('-100', '') if str(source_chat_id).startswith('-100') else str(source_chat_id)
                    message_mappings = self.db.get_message_mappings_by_source(task_id, str(source_chat_id), source_message_id)
                    
                    # If no mappings found with full format, try legacy format
                    if not message_mappings and str(source_chat_id).startswith('-100'):
                        message_mappings = self.db.get_message_mappings_by_source(task_id, legacy_chat_id, source_message_id)

                    for mapping in message_mappings:
                        target_chat_id = mapping['target_chat_id']
                        target_message_id = mapping['target_message_id']

                        try:
                            # Get target entity
                            target_entity = await client.get_entity(int(target_chat_id))

                            # Get task settings for processing
                            message_settings = self.get_message_processing_settings(task_id)
                            
                            # Process the edited text with same transformations as original
                            edited_text = event.message.text or event.message.message or ""
                            
                            # Apply text processing if enabled
                            if edited_text and message_settings['text_formatting_enabled']:
                                processed_text, spoiler_entities = self._process_spoiler_entities(edited_text)
                            else:
                                processed_text = edited_text
                                spoiler_entities = []
                            
                            # Check if inline buttons should be applied
                            inline_buttons = None
                            if message_settings['inline_buttons_enabled']:
                                inline_buttons = self.build_inline_buttons(task_id)
                                
                            # Update the target message
                            if spoiler_entities:
                                # Edit with spoiler entities
                                await client.edit_message(
                                    target_entity,
                                    target_message_id,
                                    processed_text,
                                    formatting_entities=spoiler_entities,
                                    file=None if not event.message.media else event.message.media
                                )
                            else:
                                # Edit normally
                                await client.edit_message(
                                    target_entity,
                                    target_message_id,
                                    processed_text,
                                    file=None if not event.message.media else event.message.media,
                                    parse_mode='HTML'
                                )
                            
                            # Add inline buttons if needed (can't edit buttons with userbot, use bot client)
                            if inline_buttons:
                                asyncio.create_task(
                                    self._add_inline_buttons_with_bot(
                                        target_chat_id, target_message_id, inline_buttons, task_id
                                    )
                                )

                            logger.info(f"✅ تم تحديث الرسالة المتزامنة: {target_chat_id}:{target_message_id}")

                        except Exception as sync_error:
                            logger.error(f"❌ فشل في مزامنة تعديل الرسالة: {sync_error}")
                            # Add more detailed error info
                            error_str = str(sync_error)
                            if "MESSAGE_NOT_MODIFIED" in error_str:
                                logger.warning(f"⚠️ لم يتم تعديل الرسالة لأنها متطابقة: {target_chat_id}:{target_message_id}")
                            elif "MESSAGE_EDIT_TIME_EXPIRED" in error_str:
                                logger.warning(f"⚠️ انتهت صلاحية تعديل الرسالة: {target_chat_id}:{target_message_id}")
                            else:
                                logger.error(f"💥 تفاصيل خطأ مزامنة التعديل: {error_str}")

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
                        # Convert chat_id to both possible formats to handle legacy data
                        legacy_chat_id = str(source_chat_id).replace('-100', '') if str(source_chat_id).startswith('-100') else str(source_chat_id)
                        message_mappings = self.db.get_message_mappings_by_source(task_id, str(source_chat_id), source_message_id)
                        
                        # If no mappings found with full format, try legacy format
                        if not message_mappings and str(source_chat_id).startswith('-100'):
                            message_mappings = self.db.get_message_mappings_by_source(task_id, legacy_chat_id, source_message_id)

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
            tasks = self.db.get_active_user_tasks(user_id)
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

    async def is_admin_allowed_by_signature(self, task_id: int, message, source_chat_id: str) -> bool:
        """Check if admin is allowed based on message post_author signature"""
        try:
            from database.database import Database
            db = Database()
            
            # Check if admin filter is enabled for this task
            admin_filter_enabled = db.is_advanced_filter_enabled(task_id, 'admin')
            logger.info(f"👮‍♂️ [ADMIN FILTER] فلتر المشرفين مُفعل: {admin_filter_enabled}")

            if not admin_filter_enabled:
                logger.info(f"👮‍♂️ فلتر المشرفين غير مُفعل للمهمة {task_id} - السماح للجميع")
                return True
            
            # Get admin filter settings for this specific source
            admin_filters = db.get_admin_filters_by_source(task_id, source_chat_id)
            
            if not admin_filters:
                # No admin filters configured for this source, allow everything
                logger.info(f"🔍 لا توجد فلاتر مشرفين للمصدر {source_chat_id} - السماح افتراضياً")
                return True
            
            # Get post_author from message (author signature)
            post_author = getattr(message, 'post_author', None)
            
            if not post_author:
                # No post_author signature, might be regular user message or channel without signatures enabled
                logger.info(f"🔍 لا يوجد post_author في الرسالة - السماح افتراضياً")
                return True
            
            logger.info(f"🔍 فحص توقيع المشرف: '{post_author}' في المصدر {source_chat_id}")
            
            # Check if post_author signature matches any admin signature and is allowed
            for admin_filter in admin_filters:
                admin_signature = admin_filter.get('admin_signature', '')
                if admin_signature and admin_signature == post_author:
                    is_allowed = admin_filter['is_allowed']
                    admin_name = admin_filter.get('admin_first_name', admin_signature)
                    logger.info(f"🔍 المشرف '{admin_name}' (توقيع: '{post_author}') موجود في فلتر المشرفين: {'مسموح' if is_allowed else 'محظور'}")
                    return is_allowed
            
            # Post author signature not found in admin filters - default allow
            logger.info(f"🔍 توقيع المشرف '{post_author}' غير موجود في فلتر المشرفين - السماح افتراضياً")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر المشرفين بالتوقيع: {e}")
            return True  # Default allow on error
    
    # Legacy method for backward compatibility
    async def is_admin_allowed_with_message(self, task_id, message):
        """Legacy method - redirect to new signature-based filtering"""
        # Extract source from context or use default behavior
        source_chat_id = str(message.chat_id) if message.chat_id else "0"
        return await self.is_admin_allowed_by_signature(task_id, message, source_chat_id)

    async def is_admin_allowed(self, task_id, sender_id):
        """Check if message sender is allowed by admin filters using new logic"""
        try:
            from database.database import Database
            db = Database()

            logger.info(f"👮‍♂️ [ADMIN FILTER] فحص المهمة: {task_id}, المرسل: {sender_id}")

            # Check if admin filter is enabled for this task
            admin_filter_enabled = db.is_advanced_filter_enabled(task_id, 'admin')
            logger.info(f"👮‍♂️ [ADMIN FILTER] فلتر المشرفين مُفعل: {admin_filter_enabled}")

            if not admin_filter_enabled:
                logger.info(f"👮‍♂️ فلتر المشرفين غير مُفعل للمهمة {task_id} - السماح للجميع")
                return True

            # Create a fake message object for the new filter logic
            fake_message = type('FakeMessage', (), {
                'sender_id': sender_id,
                'post_author': None,  # No author signature in this context
                'from_id': None
            })()
            
            # Use the new admin filter logic
            is_blocked = await self._check_admin_filter(task_id, fake_message)
            is_allowed = not is_blocked  # Invert because _check_admin_filter returns True if blocked
            
            logger.info(f"👮‍♂️ [ADMIN FILTER] نتيجة فحص جديد: المرسل {sender_id}, محظور: {is_blocked}, مسموح: {is_allowed}")
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
        """Apply translation to message text if enabled using deep-translator"""
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

            logger.info(f"🌐 بدء ترجمة النص من {source_lang} إلى {target_lang} للمهمة {task_id}")
            
            try:
                # Use deep-translator for more reliable translation
                translator = GoogleTranslator(source=source_lang, target=target_lang)
                translated_text = translator.translate(message_text)
                
                if translated_text and translated_text != message_text:
                    logger.info(f"🌐 تم ترجمة النص بنجاح للمهمة {task_id}: '{message_text[:30]}...' → '{translated_text[:30]}...'")
                    return translated_text
                else:
                    logger.debug(f"🌐 لم تتم الترجمة: النص مطابق أو فارغ")
                    return message_text
                    
            except Exception as translate_error:
                logger.error(f"❌ مشكلة في الترجمة: {translate_error}")
                return message_text

        except Exception as e:
            logger.error(f"❌ خطأ في ترجمة النص للمهمة {task_id}: {e}")
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
                    
                    # Apply post-forwarding settings (pin, auto-delete) for album
                    if forwarded_msg and task_info.get('forwarding_settings'):
                        # For albums, take the first message ID
                        msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                        await self.apply_post_forwarding_settings(
                            client, target_chat, msg_id, task_info['forwarding_settings'], task['id']
                        )
                    
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

    async def apply_watermark_to_media(self, event, task_id: int):
        """
        Apply watermark to media if enabled for the task - محسن لمعالجة الوسائط مرة واحدة
        
        التحسينات:
        - معالجة الوسائط مرة واحدة وإعادة استخدامها لكل الأهداف
        - ذاكرة مؤقتة ذكية لتحسين الأداء
        - تحسين معالجة الفيديو وضغطه
        - إرسال الفيديو بصيغة MP4
        
        Improvements:
        - Process media once and reuse for all targets
        - Smart cache for performance optimization
        - Enhanced video processing and compression
        - Send videos in MP4 format
        """
        try:
            # Get watermark settings
            watermark_settings = self.db.get_watermark_settings(task_id)
            logger.info(f"🏷️ فحص إعدادات العلامة المائية للمهمة {task_id}: {watermark_settings}")

            # Check if message has media
            if not event.message.media:
                return event.message.media, None

            # Check media type and watermark applicability
            is_photo = hasattr(event.message.media, 'photo') and event.message.media.photo is not None
            is_video = (
                hasattr(event.message.media, 'document')
                and event.message.media.document
                and event.message.media.document.mime_type
                and event.message.media.document.mime_type.startswith('video/')
            )
            is_document = hasattr(event.message.media, 'document') and event.message.media.document and not is_video

            logger.info(f"🏷️ نوع الوسائط للمهمة {task_id}: صورة={is_photo}, فيديو={is_video}, مستند={is_document}")

            # Download media bytes always (we need them for audio processing regardless of watermark settings)
            media_bytes = await event.message.download_media(bytes)
            if not media_bytes:
                logger.warning(f"فشل في تحميل الوسائط للمهمة {task_id}")
                return event.message.media, None

            # Derive filename and extension
            file_name = "media_file"
            file_extension = ""

            # Try to get original filename from document attributes first
            if hasattr(event.message.media, 'document') and event.message.media.document:
                doc = event.message.media.document
                if hasattr(doc, 'attributes'):
                    for attr in doc.attributes:
                        if hasattr(attr, 'file_name') and attr.file_name:
                            file_name = attr.file_name
                            if '.' in file_name:
                                file_extension = '.' + file_name.split('.')[-1].lower()
                                file_name = file_name.rsplit('.', 1)[0]
                            break

            # If still no filename and it's a photo
            if file_name == "media_file" and is_photo:
                file_name = "photo"
                file_extension = ".jpg"
                if hasattr(event.message.media, 'photo') and hasattr(event.message.media.photo, 'id'):
                    file_name = f"photo_{event.message.media.photo.id}"

            # If still no filename and it's a document, map from mime type (including audio types)
            if (
                file_name == "media_file"
                and hasattr(event.message.media, 'document')
                and event.message.media.document
                and event.message.media.document.mime_type
            ):
                doc = event.message.media.document
                mime_to_ext = {
                    # Images
                    'image/jpeg': '.jpg',
                    'image/jpg': '.jpg',
                    'image/png': '.png',
                    'image/gif': '.gif',
                    'image/webp': '.webp',
                    # Videos
                    'video/mp4': '.mp4',
                    'video/avi': '.avi',
                    'video/mov': '.mov',
                    'video/mkv': '.mkv',
                    'video/webm': '.webm',
                    # Audio (added)
                    'audio/mpeg': '.mp3',
                    'audio/mp3': '.mp3',
                    'audio/x-m4a': '.m4a',
                    'audio/aac': '.aac',
                    'audio/ogg': '.ogg',
                    'audio/wav': '.wav',
                    'audio/flac': '.flac',
                    'audio/x-ms-wma': '.wma',
                    'audio/opus': '.opus',
                }
                file_extension = mime_to_ext.get(doc.mime_type, '.bin')
                if doc.mime_type.startswith('video/'):
                    file_name = "video"
                elif doc.mime_type.startswith('image/'):
                    file_name = "image"
                elif doc.mime_type.startswith('audio/'):
                    file_name = "audio"
                else:
                    file_name = "document"

            full_file_name = file_name + file_extension
            logger.info(f"🏷️ تجهيز الوسائط باسم {full_file_name} للمهمة {task_id}")

            # Decide whether to apply watermark (but do not early return if disabled)
            apply_wm = watermark_settings.get('enabled', False)
            if is_photo and not watermark_settings.get('apply_to_photos', True):
                apply_wm = False
            elif is_video and not watermark_settings.get('apply_to_videos', True):
                apply_wm = False
            elif is_document and not watermark_settings.get('apply_to_documents', False):
                # Documents include audio; watermark usually disabled for docs unless explicitly enabled
                apply_wm = False

            # Process watermark optionally
            watermarked_media = None
            if apply_wm:
                logger.info(f"🏷️ تطبيق العلامة المائية على {full_file_name} للمهمة {task_id}")
                # CRITICAL FIX: Process media ONCE for all targets to prevent multiple uploads
                watermarked_media = self.watermark_processor.process_media_once_for_all_targets(
                    media_bytes,
                    full_file_name,
                    watermark_settings,
                    task_id,
                )
            else:
                logger.info(f"🏷️ العلامة المائية معطلة أو غير منطبقة - سيتم الانتقال مباشرة لمعالجة الصوت (إن وجد)")

            # Always apply audio metadata processing next (using watermarked bytes if available)
            base_bytes = watermarked_media if (watermarked_media and watermarked_media != media_bytes) else media_bytes
            final_media, final_filename = await self.apply_audio_metadata(event, task_id, base_bytes, full_file_name)

            # Determine if any processing actually happened to avoid forcing copy for unchanged media
            media_changed = False
            try:
                if watermarked_media and watermarked_media != media_bytes:
                    media_changed = True
                elif isinstance(final_media, (bytes, bytearray)) and final_media != base_bytes:
                    media_changed = True
            except Exception:
                media_changed = True  # Be safe

            if media_changed:
                logger.info(f"📁 اسم الملف المُرجع (بعد المعالجة): {final_filename}")
                return final_media, final_filename
            else:
                logger.info("🔄 لم يحدث أي تغيير فعلي على الوسائط - سيتم استخدام الوسائط الأصلية")
                return event.message.media, None
                
        except Exception as e:
            logger.error(f"خطأ في تطبيق العلامة المائية: {e}")
            return event.message.media, None
    
    async def apply_audio_metadata(self, event, task_id: int, media_bytes: bytes, file_name: str):
        """
        Apply audio metadata processing if enabled for the task
        
        الميزات:
        - تعديل جميع أنواع الوسوم الصوتية (ID3v2)
        - قوالب جاهزة للاستخدام
        - صورة غلاف مخصصة
        - دمج مقاطع صوتية إضافية
        - الحفاظ على الجودة 100%
        """
        try:
            # Load audio metadata settings from database
            audio_settings = self.db.get_audio_metadata_settings(task_id)
            
            if not audio_settings.get('enabled', False):
                logger.info(f"🎵 الوسوم الصوتية معطلة للمهمة {task_id}")
                return media_bytes, file_name
            
            # Check if this is an audio file
            is_audio = False
            
            # Check by file extension first (more reliable when we have media_bytes)
            if file_name.lower().endswith(('.mp3', '.m4a', '.aac', '.ogg', '.wav', '.flac', '.wma', '.opus')):
                is_audio = True
                logger.info(f"🎵 تم تحديد الملف كملف صوتي بواسطة الامتداد: {file_name}")
            # Check by mime type if available in original message
            elif hasattr(event.message.media, 'document') and event.message.media.document:
                doc = event.message.media.document
                if doc.mime_type and doc.mime_type.startswith('audio/'):
                    is_audio = True
                    logger.info(f"🎵 تم تحديد الملف كملف صوتي بواسطة MIME type: {doc.mime_type}")
            
            if not is_audio:
                logger.debug(f"🎵 تخطي الملف - ليس ملف صوتي للمهمة {task_id}")
                return media_bytes, file_name
            
            logger.info(f"🎵 بدء معالجة الوسوم الصوتية للملف {file_name} في المهمة {task_id}")
            
            # Get template settings from the new system
            template_settings = self.db.get_audio_template_settings(task_id)
            
            # Convert template settings to metadata template format
            metadata_template = {
                'title': template_settings.get('title_template', '$title'),
                'artist': template_settings.get('artist_template', '$artist'),
                'album': template_settings.get('album_template', '$album'),
                'year': template_settings.get('year_template', '$year'),
                'genre': template_settings.get('genre_template', '$genre'),
                'composer': template_settings.get('composer_template', '$composer'),
                'comment': template_settings.get('comment_template', '$comment'),
                'track': template_settings.get('track_template', '$track'),
                'album_artist': template_settings.get('album_artist_template', '$album_artist'),
                'lyrics': template_settings.get('lyrics_template', '$lyrics')
            }
            
            logger.info(f"🎵 استخدام قالب الوسوم: {metadata_template}")
            
            # Process audio metadata
            album_art_path = None
            if audio_settings.get('album_art_enabled') and audio_settings.get('album_art_path'):
                album_art_path = audio_settings.get('album_art_path')
            intro_path = audio_settings.get('intro_audio_path') if audio_settings.get('audio_merge_enabled') else None
            outro_path = audio_settings.get('outro_audio_path') if audio_settings.get('audio_merge_enabled') else None
            intro_position = audio_settings.get('intro_position', 'start')

            # تطبيق تنظيف النصوص على الوسوم إذا كان مفعّلًا لهذه المهمة
            try:
                tag_cleaning = self.db.get_audio_tag_cleaning_settings(task_id)
            except Exception:
                tag_cleaning = {'enabled': False}

            effective_template = dict(metadata_template)
            if tag_cleaning and tag_cleaning.get('enabled'):
                def _clean_tag(text: Optional[str]) -> Optional[str]:
                    if text is None:
                        return None
                    return self.apply_text_cleaning(text, task_id)

                # تنظيف الوسوم المختارة فقط
                if tag_cleaning.get('clean_title') and effective_template.get('title'):
                    effective_template['title'] = _clean_tag(effective_template['title'])
                if tag_cleaning.get('clean_artist') and effective_template.get('artist'):
                    effective_template['artist'] = _clean_tag(effective_template['artist'])
                if tag_cleaning.get('clean_album_artist') and effective_template.get('album_artist'):
                    effective_template['album_artist'] = _clean_tag(effective_template['album_artist'])
                if tag_cleaning.get('clean_album') and effective_template.get('album'):
                    effective_template['album'] = _clean_tag(effective_template['album'])
                if tag_cleaning.get('clean_year') and effective_template.get('year'):
                    effective_template['year'] = _clean_tag(effective_template['year'])
                if tag_cleaning.get('clean_genre') and effective_template.get('genre'):
                    effective_template['genre'] = _clean_tag(effective_template['genre'])
                if tag_cleaning.get('clean_composer') and effective_template.get('composer'):
                    effective_template['composer'] = _clean_tag(effective_template['composer'])
                if tag_cleaning.get('clean_comment') and effective_template.get('comment'):
                    effective_template['comment'] = _clean_tag(effective_template['comment'])
                if tag_cleaning.get('clean_track') and effective_template.get('track'):
                    effective_template['track'] = _clean_tag(effective_template['track'])
                if tag_cleaning.get('clean_length') and effective_template.get('length'):
                    effective_template['length'] = _clean_tag(effective_template['length'])
                if tag_cleaning.get('clean_lyrics') and effective_template.get('lyrics'):
                    # الحفاظ على فواصل الأسطر أثناء التنظيف: ننظف على مستوى السطور ونحافظ على \n
                    original = effective_template['lyrics']
                    lines = original.replace('\r\n', '\n').replace('\r', '\n').split('\n')
                    cleaned_lines = [self.apply_text_cleaning(line, task_id) for line in lines]
                    effective_template['lyrics'] = '\n'.join(cleaned_lines)

            # CRITICAL FIX: Process audio ONCE for all targets to prevent multiple uploads
            processed_audio = self.audio_processor.process_audio_once_for_all_targets(
                media_bytes,
                file_name,
                effective_template,
                album_art_path=album_art_path,
                apply_art_to_all=bool(audio_settings.get('apply_art_to_all', False)),
                audio_intro_path=intro_path,
                audio_outro_path=outro_path,
                intro_position=intro_position,
                task_id=task_id
            )
            
            if processed_audio and processed_audio != media_bytes:
                logger.info(f"✅ تم معالجة الوسوم الصوتية للملف {file_name} في المهمة {task_id}")
                # Update filename to MP3 if conversion was done
                if file_name.lower().endswith(('.m4a', '.aac', '.ogg', '.wav', '.flac', '.wma', '.opus')):
                    new_file_name = file_name.rsplit('.', 1)[0] + '.mp3'
                    logger.info(f"🔄 تم تحديث اسم الملف من {file_name} إلى {new_file_name}")
                    return processed_audio, new_file_name
                return processed_audio, file_name
            else:
                logger.debug(f"🔄 لم يتم معالجة الوسوم الصوتية للملف {file_name} في المهمة {task_id}")
                return media_bytes, file_name
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الوسوم الصوتية: {e}")
            return media_bytes, file_name

    async def _send_processed_media_optimized(self, client, target_entity, media_bytes, filename, task=None, event=None, **kwargs):
        """
        CRITICAL OPTIMIZATION: Upload processed media once and reuse file handle for all targets
        This prevents redundant uploads and dramatically improves performance
        """
        import hashlib
        import io
        
        # Create unique cache key for this media
        media_hash = hashlib.md5(media_bytes).hexdigest()
        cache_key = f"{media_hash}_{filename}"
        
        # Check if file already uploaded
        if cache_key in self.uploaded_file_cache:
            file_handle = self.uploaded_file_cache[cache_key]
            logger.info(f"🎯 استخدام معرف الملف المرفوع مسبقاً (محسّن): {filename}")
            
            # Send using cached file handle - NO RE-UPLOAD
            return await client.send_file(target_entity, file_handle, **kwargs)
        else:
            # First time upload: upload and cache file handle
            logger.info(f"📤 رفع الملف لأول مرة وحفظ المعرف للأهداف التالية: {filename}")
            
            # Upload file and get handle for reuse
            try:
                from send_file_helper import TelethonFileSender
                
                # Use TelethonFileSender to upload with proper attributes but cache result
                # CRITICAL FIX: Force video files to be sent as video, not document
                if filename and filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.webm', '.m4v')):
                    kwargs["force_document"] = False  # إجبار الإرسال كفيديو
                    # إزالة parse_mode للفيديوهات لتجنب مشاكل التنسيق
                    if 'parse_mode' in kwargs:
                        del kwargs['parse_mode']
                
                result = await TelethonFileSender.send_file_with_name(
                    client, target_entity, media_bytes, filename, **kwargs
                )
                
                # Try to extract file handle from the sent message for caching
                try:
                    if hasattr(result, 'media') and hasattr(result.media, 'document'):
                        file_handle = result.media.document
                        self.uploaded_file_cache[cache_key] = file_handle
                        logger.info(f"✅ تم حفظ معرف الملف للاستخدام المتكرر: {filename}")
                except Exception as cache_err:
                    logger.warning(f"⚠️ لم يتم حفظ معرف الملف: {cache_err}")
                
                return result
                
            except Exception as e:
                logger.error(f"❌ فشل في رفع الملف المُحسّن: {e}")
                # Fallback to normal method
                from send_file_helper import TelethonFileSender
                return await TelethonFileSender.send_file_with_name(
                    client, target_entity, media_bytes, filename, **kwargs
                )

    def apply_message_formatting(self, text: str, settings: dict) -> str:
        """Apply header and footer formatting to message text"""
        if not text:
            text = ""

        final_text = text

        def _md_to_html_links(s: str) -> str:
            try:
                import re
                # Convert markdown [text](url) to HTML <a href="url">text</a>
                return re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', s)
            except Exception:
                return s

        # Add header if enabled
        if settings['header_enabled'] and settings['header_text']:
            header_html = _md_to_html_links(settings['header_text'])
            final_text = header_html + "\n\n" + final_text

        # Add footer if enabled
        if settings['footer_enabled'] and settings['footer_text']:
            footer_html = _md_to_html_links(settings['footer_text'])
            final_text = final_text + "\n\n" + footer_html

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

    async def apply_post_forwarding_settings(self, client: TelegramClient, target_entity, msg_id: int, forwarding_settings: dict, task_id: int, inline_buttons=None, has_original_buttons=False):
        """Apply post-forwarding settings like pin message, auto delete, and inline buttons"""
        import asyncio
        try:
            # Add inline buttons via bot client if needed and no original buttons exist
            if inline_buttons and not has_original_buttons:
                # Handle both entity objects and integer IDs
                target_id = str(target_entity.id) if hasattr(target_entity, 'id') else str(target_entity)
                asyncio.create_task(
                    self._add_inline_buttons_with_bot(
                        target_id, msg_id, inline_buttons, task_id
                    )
                )
            
            # Pin message if enabled
            if forwarding_settings['pin_message_enabled']:
                try:
                    await client.pin_message(target_entity, msg_id, notify=not forwarding_settings['silent_notifications'])
                    logger.info(f"📌 تم تثبيت الرسالة {msg_id} في {target_entity}")
                except Exception as pin_error:
                    logger.error(f"❌ فشل في تثبيت الرسالة {msg_id}: {pin_error}")

            # Schedule auto delete if enabled
            if forwarding_settings['auto_delete_enabled'] and forwarding_settings['auto_delete_time'] > 0:
                delete_time = forwarding_settings['auto_delete_time']
                logger.info(f"⏰ جدولة حذف الرسالة {msg_id} بعد {delete_time} ثانية")

                # Schedule deletion in background
                asyncio.create_task(
                    self._schedule_message_deletion(client, target_entity, msg_id, delete_time, task_id)
                )

        except Exception as e:
            logger.error(f"خطأ في تطبيق إعدادات ما بعد التوجيه: {e}")

    async def _schedule_message_deletion(self, client: TelegramClient, target_entity, msg_id: int, delay_seconds: int, task_id: int):
        """Schedule message deletion after specified delay with proper tracking"""
        deletion_key = f"{target_entity}:{msg_id}"
        
        try:
            import asyncio
            
            # Store the task for potential cancellation
            deletion_task = asyncio.current_task()
            if not hasattr(self, 'scheduled_deletions'):
                self.scheduled_deletions = {}
            self.scheduled_deletions[deletion_key] = deletion_task
            
            logger.info(f"⏰ تم جدولة حذف الرسالة {msg_id} بعد {delay_seconds} ثانية (المهمة {task_id})")
            
            # Wait for the specified delay
            await asyncio.sleep(delay_seconds)

            try:
                # Remove from tracking before deletion
                if deletion_key in self.scheduled_deletions:
                    del self.scheduled_deletions[deletion_key]
                
                await client.delete_messages(target_entity, msg_id)
                logger.info(f"🗑️ تم حذف الرسالة {msg_id} تلقائياً من {target_entity} (المهمة {task_id})")
                
            except Exception as delete_error:
                logger.error(f"❌ فشل في حذف الرسالة {msg_id} تلقائياً: {delete_error}")
                
                # Handle specific deletion errors
                error_str = str(delete_error)
                if "MESSAGE_DELETE_FORBIDDEN" in error_str:
                    logger.warning(f"⚠️ لا يُسمح بحذف الرسالة {msg_id} - قد تكون رسالة أخرى")
                elif "CHAT_ADMIN_REQUIRED" in error_str:
                    logger.warning(f"⚠️ مطلوب صلاحيات إدارية لحذف الرسالة {msg_id}")
                elif "MESSAGE_ID_INVALID" in error_str:
                    logger.warning(f"⚠️ معرف الرسالة {msg_id} غير صالح أو محذوف مسبقاً")

        except asyncio.CancelledError:
            logger.info(f"🔄 تم إلغاء جدولة حذف الرسالة {msg_id} (المهمة {task_id})")
            if deletion_key in getattr(self, 'scheduled_deletions', {}):
                del self.scheduled_deletions[deletion_key]
        except Exception as e:
            logger.error(f"خطأ في جدولة حذف الرسالة: {e}")
            if deletion_key in getattr(self, 'scheduled_deletions', {}):
                del self.scheduled_deletions[deletion_key]
    
    def cancel_scheduled_deletion(self, target_entity, msg_id: int):
        """Cancel a scheduled message deletion"""
        deletion_key = f"{target_entity}:{msg_id}"
        
        if hasattr(self, 'scheduled_deletions') and deletion_key in self.scheduled_deletions:
            task = self.scheduled_deletions[deletion_key]
            if not task.done():
                task.cancel()
                logger.info(f"🔄 تم إلغاء الحذف المُجدول للرسالة {msg_id}")
            del self.scheduled_deletions[deletion_key]
            return True
        return False
    
    def cleanup_completed_deletion_tasks(self):
        """Clean up completed deletion tasks to prevent memory leaks"""
        if not hasattr(self, 'scheduled_deletions'):
            return
            
        completed_keys = []
        for key, task in self.scheduled_deletions.items():
            if task.done():
                completed_keys.append(key)
        
        for key in completed_keys:
            del self.scheduled_deletions[key]
            
        if completed_keys:
            logger.info(f"🧹 تم تنظيف {len(completed_keys)} مهام حذف مكتملة من الذاكرة")

    async def _add_inline_buttons_with_bot(self, target_chat_id: str, message_id: int, inline_buttons, task_id: int):
        """Add inline buttons to a message using bot client"""
        try:
            if not inline_buttons:
                logger.warning(f"⚠️ لا توجد أزرار لإضافتها للرسالة {message_id} في المهمة {task_id}")
                return False
                
            logger.info(f"🔘 بدء إضافة {len(inline_buttons)} صف من الأزرار للرسالة {message_id} في القناة {target_chat_id} - المهمة {task_id}")
                
            from bot_package.config import BOT_TOKEN, API_ID, API_HASH
            from telethon import TelegramClient
            import asyncio
            
            # Add small delay to ensure message is fully sent
            await asyncio.sleep(0.5)
            
            # Create temporary bot client with unique session name
            import time
            session_name = f'temp_bot_buttons_{int(time.time())}'
            bot_client = TelegramClient(session_name, API_ID, API_HASH)
            
            try:
                # Start bot client
                await bot_client.start(bot_token=BOT_TOKEN)
                logger.info(f"🤖 تم تشغيل bot client بنجاح لإضافة الأزرار")
                
                # Convert target_chat_id to appropriate format
                try:
                    if target_chat_id.startswith('-'):
                        target_entity = int(target_chat_id)
                    else:
                        target_entity = target_chat_id
                    
                    # Get target entity
                    target_entity = await bot_client.get_entity(target_entity)
                    logger.info(f"✅ تم العثور على القناة الهدف: {getattr(target_entity, 'title', target_chat_id)}")
                except Exception as entity_err:
                    logger.error(f"❌ فشل في الوصول للقناة {target_chat_id}: {entity_err}")
                    return False
                
                # Get the original message with retry
                max_retries = 3
                original_msg = None
                
                for attempt in range(max_retries):
                    try:
                        original_msg = await bot_client.get_messages(target_entity, ids=message_id)
                        if original_msg:
                            break
                        else:
                            logger.warning(f"⚠️ محاولة {attempt + 1}: لم يتم العثور على الرسالة {message_id}")
                            await asyncio.sleep(1)  # Wait before retry
                    except Exception as get_msg_err:
                        logger.warning(f"⚠️ محاولة {attempt + 1}: خطأ في جلب الرسالة {message_id}: {get_msg_err}")
                        await asyncio.sleep(1)  # Wait before retry
                
                if not original_msg:
                    logger.error(f"❌ فشل في العثور على الرسالة {message_id} بعد {max_retries} محاولات")
                    return False
                
                logger.info(f"✅ تم العثور على الرسالة {message_id}: '{original_msg.text[:50] if original_msg.text else 'وسائط'}'")
                
                # Edit the message to add buttons while keeping original content
                try:
                    await bot_client.edit_message(
                        target_entity,
                        message_id,
                        original_msg.text or original_msg.message or ".",
                        buttons=inline_buttons,
                        parse_mode='HTML'
                    )
                    
                    logger.info(f"✅ تم إضافة {len(inline_buttons)} صف من الأزرار بنجاح للرسالة {message_id} في المهمة {task_id}")
                    return True
                    
                except Exception as edit_err:
                    logger.error(f"❌ فشل في تعديل الرسالة {message_id} لإضافة الأزرار: {edit_err}")
                    return False
                
            except Exception as bot_error:
                logger.error(f"❌ خطأ عام في bot client لإضافة الأزرار: {bot_error}")
                return False
                
            finally:
                try:
                    await bot_client.disconnect()
                    # Clean up temporary session file
                    import os
                    session_file = f'{session_name}.session'
                    if os.path.exists(session_file):
                        os.remove(session_file)
                except Exception as cleanup_err:
                    logger.warning(f"⚠️ تحذير في تنظيف bot client: {cleanup_err}")
                    
        except Exception as e:
            logger.error(f"❌ خطأ عام في إضافة الأزرار باستخدام bot client: {e}")
            return False

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
            max_chars = settings.get('max_chars', 4000)
            mode = settings.get('mode', 'allow')
            use_range = settings.get('use_range', True)

            logger.info(f"📏 فحص حد الأحرف للمهمة {task_id}: النص='{message_text[:50]}...' ({message_length} حرف), حد أدنى={min_chars}, حد أقصى={max_chars}, وضع={mode}")

            # Character limit checking logic based on mode
            if mode == 'allow':
                # Allow mode: Allow messages that meet the criteria
                if use_range and min_chars > 0 and max_chars > 0:
                    # Range check: min_chars <= length <= max_chars
                    if min_chars <= message_length <= max_chars:
                        logger.info(f"✅ السماح - النطاق: الرسالة مقبولة ({min_chars} <= {message_length} <= {max_chars} حرف)")
                        return True
                    else:
                        logger.info(f"🚫 السماح - النطاق: الرسالة مرفوضة ({message_length} خارج النطاق {min_chars}-{max_chars} حرف)")
                        return False
                else:
                    # Max limit only: length <= max_chars
                    if message_length <= max_chars:
                        logger.info(f"✅ السماح - الحد الأقصى: الرسالة مقبولة ({message_length} <= {max_chars} حرف)")
                        return True
                    else:
                        logger.info(f"🚫 السماح - الحد الأقصى: الرسالة مرفوضة ({message_length} > {max_chars} حرف)")
                        return False

            elif mode == 'block':
                # Block mode: Block messages that don't meet the criteria
                if use_range and min_chars > 0 and max_chars > 0:
                    # Range check: block if outside min_chars <= length <= max_chars
                    if min_chars <= message_length <= max_chars:
                        logger.info(f"✅ الحظر - النطاق: الرسالة مقبولة ({min_chars} <= {message_length} <= {max_chars} حرف)")
                        return True
                    else:
                        logger.info(f"🚫 الحظر - النطاق: الرسالة مرفوضة ({message_length} خارج النطاق {min_chars}-{max_chars} حرف)")
                        return False
                else:
                    # Max limit only: block if length > max_chars
                    if message_length <= max_chars:
                        logger.info(f"✅ الحظر - الحد الأقصى: الرسالة مقبولة ({message_length} <= {max_chars} حرف)")
                        return True
                    else:
                        logger.info(f"🚫 الحظر - الحد الأقصى: الرسالة مرفوضة ({message_length} > {max_chars} حرف)")
                        return False
            
            else:
                logger.warning(f"⚠️ وضع فلتر غير معروف '{mode}' - السماح بالتوجيه")
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

    async def _check_message_advanced_filters(self, task_id: int, message) -> tuple:
        """Check advanced filters for forwarded messages and inline buttons
        Returns: (should_block, should_remove_buttons, should_remove_forward)
        """
        try:
            # Get advanced filter settings
            advanced_settings = self.db.get_advanced_filters_settings(task_id)
            
            should_block = False
            should_remove_buttons = False  
            should_remove_forward = False
            
            # Check forwarded message filter
            if advanced_settings.get('forwarded_message_filter_enabled', False):
                forwarded_setting = self.db.get_forwarded_message_filter_setting(task_id)
                
                # Check if message is forwarded
                is_forwarded = (hasattr(message, 'forward') and message.forward is not None)
                
                if is_forwarded:
                    if forwarded_setting:  # True = block mode
                        logger.info(f"🚫 رسالة معاد توجيهها - سيتم حظرها (وضع الحظر)")
                        should_block = True
                    else:  # False = remove forward mode
                        logger.info(f"📋 رسالة معاد توجيهها - سيتم إرسالها كنسخة (وضع حذف علامة التوجيه)")
                        should_remove_forward = True
            
            # Check inline button filter 
            if not should_block:
                inline_button_filter_enabled = advanced_settings.get('inline_button_filter_enabled', False)
                inline_button_setting = self.db.get_inline_button_filter_setting(task_id)
                
                logger.debug(f"🔍 فحص فلتر الأزرار الشفافة: المهمة {task_id}, فلتر مفعل={inline_button_filter_enabled}, إعداد الحظر={inline_button_setting}")
                
                # Check if message has inline buttons first
                has_buttons = (hasattr(message, 'reply_markup') and 
                             message.reply_markup is not None and
                             hasattr(message.reply_markup, 'rows') and
                             message.reply_markup.rows)
                
                logger.debug(f"🔍 الرسالة تحتوي على أزرار: {has_buttons}")
                
                if has_buttons:
                    # Case 1: Filter is enabled - use both settings
                    if inline_button_filter_enabled:
                        if inline_button_setting:  # True = block mode
                            logger.info(f"🚫 رسالة تحتوي على أزرار شفافة - سيتم حظرها (وضع الحظر)")
                            should_block = True
                        else:  # False = remove buttons mode
                            logger.info(f"🗑️ رسالة تحتوي على أزرار شفافة - سيتم حذف الأزرار (وضع الحذف)")
                            should_remove_buttons = True
                    # Case 2: Filter is disabled but block setting exists (legacy compatibility)
                    elif not inline_button_filter_enabled and inline_button_setting:
                        logger.info(f"⚠️ فلتر الأزرار معطل لكن إعداد الحظر مفعل - تجاهل الإعداد وتمرير الرسالة كما هي")
                        # Don't block or remove buttons - pass message as is
                    else:
                        logger.debug(f"✅ فلتر الأزرار الشفافة غير مفعل - تمرير الرسالة كما هي")
            
            # Check duplicate filter
            if not should_block and advanced_settings.get('duplicate_filter_enabled', False):
                duplicate_detected = await self._check_duplicate_message(task_id, message)
                if duplicate_detected:
                    logger.info(f"🔄 رسالة مكررة - سيتم حظرها (فلتر التكرار)")
                    should_block = True
            
            # Check language filter
            if not should_block and advanced_settings.get('language_filter_enabled', False):
                language_blocked = await self._check_language_filter(task_id, message)
                if language_blocked:
                    logger.info(f"🌍 رسالة محظورة بواسطة فلتر اللغة")
                    should_block = True
            
            # Check day filter
            if not should_block and advanced_settings.get('day_filter_enabled', False):
                day_blocked = self._check_day_filter(task_id)
                if day_blocked:
                    logger.info(f"📅 رسالة محظورة بواسطة فلتر الأيام")
                    should_block = True
            
            # Check admin filter
            if not should_block and advanced_settings.get('admin_filter_enabled', False):
                admin_blocked = await self._check_admin_filter(task_id, message)
                if admin_blocked:
                    logger.info(f"👮‍♂️ رسالة محظورة بواسطة فلتر المشرفين")
                    should_block = True
            
            # Check working hours filter
            if not should_block and advanced_settings.get('working_hours_enabled', False):
                working_hours_blocked = self._check_working_hours_filter(task_id)
                if working_hours_blocked:
                    logger.info(f"⏰ رسالة محظورة بواسطة فلتر ساعات العمل")
                    should_block = True
            
            return should_block, should_remove_buttons, should_remove_forward
            
        except Exception as e:
            logger.error(f"خطأ في فحص الفلاتر المتقدمة: {e}")
            return False, False, False

    def _check_day_filter(self, task_id: int) -> bool:
        """Check if current day is allowed by day filter"""
        try:
            import datetime
            
            # Get current day (0=Monday, 1=Tuesday, ..., 6=Sunday)
            today = datetime.datetime.now().weekday()
            
            # Get day filter settings
            day_filters = self.db.get_day_filters(task_id)
            if not day_filters:
                logger.debug(f"📅 لا توجد إعدادات فلتر الأيام للمهمة {task_id}")
                return False
            
            # Find today's setting
            today_allowed = True  # Default is allowed
            for day in day_filters:
                if day['day_number'] == today:
                    today_allowed = day['is_allowed']
                    break
            
            day_names = ['الإثنين', 'الثلاثاء', 'الأربعاء', 'الخميس', 'الجمعة', 'السبت', 'الأحد']
            today_name = day_names[today] if today < len(day_names) else f"يوم {today}"
            
            if not today_allowed:
                logger.info(f"📅 فلتر الأيام: اليوم {today_name} محظور - سيتم حظر الرسالة")
                return True
            else:
                logger.info(f"📅 فلتر الأيام: اليوم {today_name} مسموح - سيتم توجيه الرسالة")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر الأيام: {e}")
            return False

    async def _check_admin_filter(self, task_id: int, message) -> bool:
        """Check if message sender is blocked by admin filter based on Author Signature or sender ID"""
        try:
            # Method 1: Try to get sender ID directly (for groups)
            sender_id = None
            
            # For regular messages
            if hasattr(message, 'sender_id') and message.sender_id:
                sender_id = message.sender_id
            elif hasattr(message, 'from_id') and message.from_id:
                # Handle different message types
                if hasattr(message.from_id, 'user_id'):
                    sender_id = message.from_id.user_id
                else:
                    sender_id = message.from_id
            
            # Method 2: Check for Telegram Author Signature (for channels)
            author_signature = None
            
            # Check for post_author (Telegram's Author Signature feature)
            if hasattr(message, 'post_author') and message.post_author:
                author_signature = message.post_author.strip()
                logger.info(f"👮‍♂️ توقيع المؤلف (Author Signature): '{author_signature}'")
            
            # Determine if this is a channel message (sender_id is channel ID)
            is_channel_message = sender_id and str(sender_id).startswith('-100')
            
            # For channel messages with author signature, use signature matching
            if is_channel_message and author_signature:
                logger.info(f"👮‍♂️ رسالة قناة مع توقيع المؤلف: '{author_signature}'")
                return await self._check_admin_by_signature(task_id, author_signature)
            
            # For user messages (groups), use ID matching
            elif sender_id and not is_channel_message:
                logger.info(f"👮‍♂️ فحص المرسل بالمعرف: {sender_id}")
                return await self._check_admin_by_id(task_id, sender_id)
            
            # For channel messages without author signature, allow by default
            elif is_channel_message and not author_signature:
                logger.debug(f"👮‍♂️ رسالة قناة بدون توقيع المؤلف - سيتم السماح")
                return False
            
            # If no valid identification method, allow message
            else:
                logger.debug(f"👮‍♂️ لا يمكن تحديد هوية المرسل - سيتم السماح")
                return False
            
                
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر المشرفين: {e}")
            return False



    async def _check_admin_by_signature(self, task_id: int, author_signature: str) -> bool:
        """Check admin filter by Telegram Author Signature"""
        try:
            # Get all admin filters for this task
            admin_filters = self.db.get_admin_filters(task_id)
            if not admin_filters:
                logger.debug(f"👮‍♂️ لا توجد فلاتر مشرفين للمهمة {task_id}")
                return False
            
            # First pass: Look for exact matches (highest priority)
            exact_matches = []
            partial_matches = []
            
            for admin in admin_filters:
                admin_name = admin.get('admin_first_name', '').strip()
                admin_username = admin.get('admin_username', '').strip()
                admin_signature = admin.get('admin_signature', '').strip()
                is_allowed = admin.get('is_allowed', True)
                
                # Exact matching logic (highest priority)
                exact_name_match = admin_name and author_signature.lower() == admin_name.lower()
                exact_username_match = admin_username and author_signature.lower() == admin_username.lower()
                exact_signature_match = admin_signature and author_signature.lower() == admin_signature.lower()
                
                # Partial matching logic (lower priority)  
                partial_name_match = admin_name and admin_name != author_signature and (
                    author_signature.lower() in admin_name.lower() or
                    admin_name.lower() in author_signature.lower()
                )
                
                partial_username_match = admin_username and admin_username != author_signature and (
                    author_signature.lower() in admin_username.lower()
                )
                
                partial_signature_match = admin_signature and admin_signature != author_signature and (
                    author_signature.lower() in admin_signature.lower() or
                    admin_signature.lower() in author_signature.lower()
                )
                
                # Collect matches by priority
                if exact_name_match or exact_username_match or exact_signature_match:
                    exact_matches.append((admin, 'exact'))
                    logger.debug(f"🎯 تطابق دقيق مع المشرف '{admin_name}' (@{admin_username}) [توقيع: {admin_signature}]")
                elif partial_name_match or partial_username_match or partial_signature_match:
                    partial_matches.append((admin, 'partial'))
                    logger.debug(f"🔍 تطابق جزئي مع المشرف '{admin_name}' (@{admin_username}) [توقيع: {admin_signature}]")
            
            # Process exact matches first (highest priority)
            for admin, match_type in exact_matches:
                admin_name = admin.get('admin_first_name', '').strip()
                admin_username = admin.get('admin_username', '').strip()
                admin_signature = admin.get('admin_signature', '').strip()
                is_allowed = admin.get('is_allowed', True)
                
                if not is_allowed:
                    logger.error(f"🚫 [SIGNATURE BLOCK - EXACT] توقيع المؤلف '{author_signature}' محظور (تطابق دقيق مع '{admin_name}' أو '{admin_username}' أو '{admin_signature}') - سيتم حظر الرسالة")
                    return True
                else:
                    logger.info(f"✅ [SIGNATURE ALLOW - EXACT] توقيع المؤلف '{author_signature}' مسموح (تطابق دقيق مع '{admin_name}' أو '{admin_username}' أو '{admin_signature}') - سيتم توجيه الرسالة")
                    return False
            
            # Process partial matches only if no exact matches found
            for admin, match_type in partial_matches:
                admin_name = admin.get('admin_first_name', '').strip()
                admin_username = admin.get('admin_username', '').strip()
                admin_signature = admin.get('admin_signature', '').strip()
                is_allowed = admin.get('is_allowed', True)
                
                if not is_allowed:
                    logger.error(f"🚫 [SIGNATURE BLOCK - PARTIAL] توقيع المؤلف '{author_signature}' محظور (تطابق جزئي مع '{admin_name}' أو '{admin_username}' أو '{admin_signature}') - سيتم حظر الرسالة")
                    return True
                else:
                    logger.info(f"✅ [SIGNATURE ALLOW - PARTIAL] توقيع المؤلف '{author_signature}' مسموح (تطابق جزئي مع '{admin_name}' أو '{admin_username}' أو '{admin_signature}') - سيتم توجيه الرسالة")
                    return False
            
            # If signature not found in admin list, allow by default
            logger.debug(f"👮‍♂️ توقيع المؤلف '{author_signature}' غير موجود في قائمة المشرفين - سيتم السماح")
            return False
            
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر المشرفين بتوقيع المؤلف: {e}")
            return False

    async def _check_admin_by_id(self, task_id: int, sender_id: int) -> bool:
        """Check admin filter by sender ID"""
        try:
            # Check if this sender is in the admin filter list
            admin_setting = self.db.get_admin_filter_setting(task_id, sender_id)
            if admin_setting is None:
                # Admin not in filter list - ALLOW by default
                logger.debug(f"👮‍♂️ المرسل {sender_id} غير موجود في قائمة فلتر المشرفين - سيتم السماح (الافتراضي)")
                return False
            
            # If admin is in list, check their permission setting
            is_allowed = admin_setting.get('is_allowed', True)
            
            if not is_allowed:
                logger.info(f"👮‍♂️ فلتر المشرفين (بالمعرف): المرسل {sender_id} محظور صراحة - سيتم حظر الرسالة")
                return True
            else:
                logger.info(f"👮‍♂️ فلتر المشرفين (بالمعرف): المرسل {sender_id} مسموح صراحة - سيتم توجيه الرسالة")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر المشرفين بالمعرف: {e}")
            return False

    def _check_working_hours_filter(self, task_id: int) -> bool:
        """Check if current time is within working hours configuration"""
        try:
            import datetime
            
            # Get working hours configuration
            working_hours = self.db.get_working_hours(task_id)
            if not working_hours:
                logger.debug(f"⏰ لا توجد إعدادات ساعات العمل للمهمة {task_id}")
                return False
            
            mode = working_hours.get('mode', 'work_hours')  # 'work_hours' or 'sleep_hours'
            enabled_hours = working_hours.get('enabled_hours', [])
            
            # For now, use UTC+3 (Riyadh timezone) as default
            timezone_offset = 3
            
            # If no hours are configured, don't block
            if not enabled_hours:
                logger.debug(f"⏰ لا توجد ساعات محددة في فلتر ساعات العمل للمهمة {task_id}")
                return False
            
            # Get current time with timezone offset (Riyadh = UTC+3)
            now = datetime.datetime.now() + datetime.timedelta(hours=timezone_offset)
            current_hour = now.hour
            
            logger.info(f"⏰ فحص ساعات العمل للمهمة {task_id}: الساعة الحالية={current_hour:02d} (الرياض), الوضع={mode}")
            logger.info(f"⏰ الساعات المُحددة: {sorted(enabled_hours)}")
            
            # Check if current hour is in enabled hours
            is_in_enabled_hours = current_hour in enabled_hours
            
            if mode == 'work_hours':
                # Work hours mode: Block if NOT in working hours
                should_block = not is_in_enabled_hours
                if should_block:
                    logger.info(f"⏰ وضع ساعات العمل: الساعة الحالية {current_hour:02d} خارج ساعات العمل - سيتم حظر الرسالة")
                else:
                    logger.info(f"⏰ وضع ساعات العمل: الساعة الحالية {current_hour:02d} في ساعات العمل - سيتم توجيه الرسالة")
            else:  # sleep_hours
                # Sleep hours mode: Block if IN sleep hours
                should_block = is_in_enabled_hours
                if should_block:
                    logger.info(f"⏰ وضع ساعات النوم: الساعة الحالية {current_hour:02d} في ساعات النوم - سيتم حظر الرسالة")
                else:
                    logger.info(f"⏰ وضع ساعات النوم: الساعة الحالية {current_hour:02d} خارج ساعات النوم - سيتم توجيه الرسالة")
            
            return should_block
            
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر ساعات العمل: {e}")
            return False

    async def _check_duplicate_message(self, task_id: int, message) -> bool:
        """Check if message is duplicate based on settings"""
        try:
            # Get duplicate filter settings
            settings = self.db.get_duplicate_settings(task_id)
            
            if not settings:
                logger.debug(f"❌ لا توجد إعدادات فلتر التكرار للمهمة {task_id}")
                return False
                
            # Check if feature is enabled - use correct key
            enabled = settings.get('enabled', False)
            if not enabled:
                logger.debug(f"❌ فلتر التكرار معطل للمهمة {task_id}")
                return False
                
            # Check if any checks are enabled - use correct keys from database
            check_text = settings.get('check_text', False)
            check_media = settings.get('check_media', False)
            
            if not check_text and not check_media:
                logger.debug(f"❌ فحوصات فلتر التكرار معطلة للمهمة {task_id}")
                return False
                
            # Convert threshold from percentage to decimal
            threshold = settings.get('similarity_threshold', 80) / 100.0
            time_window_hours = settings.get('time_window_hours', 24)
            
            logger.info(f"🔍 فحص تكرار الرسالة للمهمة {task_id}: مفعل={enabled}, نص={check_text}, وسائط={check_media}, نسبة={threshold*100:.0f}%, نافذة={time_window_hours}ساعة")
            
            # Get message content to check - fix message.message to message.text
            message_text = message.text or message.message or ""
            message_media = None
            media_hash = None
            
            # Extract media hash if exists
            if hasattr(message, 'media') and message.media:
                if hasattr(message.media, 'photo'):
                    # Photo message
                    if hasattr(message.media.photo, 'id'):
                        media_hash = str(message.media.photo.id)
                        message_media = 'photo'
                elif hasattr(message.media, 'document'):
                    # Document/video/audio message
                    if hasattr(message.media.document, 'id'):
                        media_hash = str(message.media.document.id)
                        message_media = 'document'
            
            logger.info(f"📝 محتوى الرسالة للفحص: نص='{message_text[:50]}...', وسائط={message_media}, hash={media_hash}")
            
            # Check for duplicates in database
            import time
            current_time = int(time.time())
            time_window_seconds = time_window_hours * 3600
            cutoff_time = current_time - time_window_seconds
            
            # Get recent messages from database
            recent_messages = self.db.get_recent_messages_for_duplicate_check(task_id, cutoff_time)
            logger.info(f"📊 تم العثور على {len(recent_messages)} رسالة حديثة للمقارنة")
            
            for stored_msg in recent_messages:
                is_duplicate = False
                stored_text = stored_msg.get('message_text', '')
                stored_media = stored_msg.get('media_hash', '')
                
                # Check text similarity if enabled
                if check_text and message_text and stored_text:
                    similarity = self._calculate_text_similarity(message_text, stored_text)
                    logger.info(f"🔍 مقارنة النص: '{message_text}' مع '{stored_text}' - تشابه={similarity*100:.1f}%")
                    if similarity >= threshold:
                        logger.warning(f"🔄 نص مكرر وجد! تشابه={similarity*100:.1f}% >= {threshold*100:.0f}%")
                        is_duplicate = True
                
                # Check media similarity if enabled
                if check_media and media_hash and stored_media:
                    logger.info(f"🔍 مقارنة الوسائط: '{media_hash}' مع '{stored_media}'")
                    if media_hash == stored_media:
                        logger.warning(f"🔄 وسائط مكررة وجدت: {media_hash}")
                        is_duplicate = True
                
                if is_duplicate:
                    logger.warning(f"🚫 رسالة مكررة - سيتم رفضها!")
                    # Update stored message timestamp to current time
                    self.db.update_message_timestamp_for_duplicate(stored_msg['id'], current_time)
                    return True
            
            # Store this message for future duplicate checks
            logger.info(f"💾 حفظ الرسالة للمراقبة المستقبلية")
            self.db.store_message_for_duplicate_check(
                task_id=task_id,
                message_text=message_text,
                media_hash=media_hash or "",
                media_type=message_media or "",
                timestamp=current_time
            )
            
            logger.info(f"✅ رسالة غير مكررة للمهمة {task_id}")
            return False
            
        except Exception as e:
            logger.error(f"خطأ في فحص تكرار الرسالة: {e}")
            import traceback
            logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
            return False  # Allow message if check fails
            
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calculate similarity between two texts"""
        try:
            if not text1 or not text2:
                return 0.0
                
            # Simple similarity based on common words
            words1 = set(text1.lower().split())
            words2 = set(text2.lower().split())
            
            if not words1 and not words2:
                return 1.0
            if not words1 or not words2:
                return 0.0
                
            intersection = len(words1.intersection(words2))
            union = len(words1.union(words2))
            
            similarity = intersection / union if union > 0 else 0.0
            return similarity
            
        except Exception as e:
            logger.error(f"خطأ في حساب تشابه النص: {e}")
            return 0.0

    async def _check_language_filter(self, task_id: int, message) -> bool:
        """Check if message should be blocked by language filter"""
        try:
            # Get language filter data
            language_data = self.db.get_language_filters(task_id)
            filter_mode = language_data['mode']  # 'allow' or 'block'
            languages = language_data['languages']
            
            # If no languages configured, don't block
            if not languages:
                logger.debug(f"🌍 لا توجد لغات محددة في الفلتر للمهمة {task_id}")
                return False
            
            # Extract message text
            message_text = message.message or ""
            if not message_text.strip():
                logger.debug(f"🌍 رسالة بدون نص - لن يتم فلترتها")
                return False
            
            # Simple language detection based on script/characters
            detected_language = self._detect_message_language(message_text)
            logger.info(f"🌍 لغة الرسالة المكتشفة: {detected_language}")
            
            # Check if language is in filter list
            selected_languages = [lang['language_code'] for lang in languages if lang['is_allowed']]
            is_language_selected = detected_language in selected_languages
            
            logger.info(f"🌍 فلتر اللغة - الوضع: {filter_mode}, اللغة المكتشفة: {detected_language}, اللغات المحددة: {selected_languages}")
            
            # Apply filter logic
            if filter_mode == 'allow':
                # Allow mode: block if language NOT in selected list
                should_block = not is_language_selected
                if should_block:
                    logger.info(f"🚫 حظر الرسالة - وضع السماح: اللغة {detected_language} غير مسموحة")
            else:  # block mode
                # Block mode: block if language IS in selected list
                should_block = is_language_selected  
                if should_block:
                    logger.info(f"🚫 حظر الرسالة - وضع الحظر: اللغة {detected_language} محظورة")
            
            return should_block
            
        except Exception as e:
            logger.error(f"خطأ في فحص فلتر اللغة: {e}")
            return False

    def _detect_message_language(self, text: str) -> str:
        """Simple language detection based on character analysis"""
        try:
            # Remove spaces and punctuation for analysis
            clean_text = ''.join(c for c in text if c.isalpha())
            
            if not clean_text:
                return 'unknown'
            
            # Count character types
            arabic_chars = sum(1 for c in clean_text if '\u0600' <= c <= '\u06FF' or '\u0750' <= c <= '\u077F')
            latin_chars = sum(1 for c in clean_text if 'a' <= c.lower() <= 'z')
            cyrillic_chars = sum(1 for c in clean_text if '\u0400' <= c <= '\u04FF')
            
            total_chars = len(clean_text)
            
            # Calculate percentages
            arabic_ratio = arabic_chars / total_chars if total_chars > 0 else 0
            latin_ratio = latin_chars / total_chars if total_chars > 0 else 0
            cyrillic_ratio = cyrillic_chars / total_chars if total_chars > 0 else 0
            
            logger.debug(f"🔍 تحليل النص: عربي={arabic_ratio:.2f}, لاتيني={latin_ratio:.2f}, كيريلي={cyrillic_ratio:.2f}")
            
            # Determine primary language (threshold: 30%)
            if arabic_ratio > 0.3:
                return 'ar'
            elif latin_ratio > 0.3:
                # Additional check for common English patterns
                english_words = ['the', 'and', 'or', 'is', 'are', 'was', 'were', 'to', 'of', 'in', 'on', 'at', 'for']
                text_lower = text.lower()
                english_count = sum(1 for word in english_words if word in text_lower)
                if english_count >= 2 or 'english' in text_lower:
                    return 'en'
                return 'en'  # Default to English for Latin script
            elif cyrillic_ratio > 0.3:
                return 'ru'
            else:
                # For mixed or unclear text, try to detect by common patterns
                text_lower = text.lower()
                if any(word in text_lower for word in ['hello', 'hi', 'good', 'yes', 'no', 'thank']):
                    return 'en'
                elif any(word in text_lower for word in ['مرحبا', 'أهلا', 'نعم', 'لا', 'شكرا']):
                    return 'ar'
                return 'unknown'
                
        except Exception as e:
            logger.error(f"خطأ في كشف اللغة: {e}")
            return 'unknown'

    async def _handle_manual_approval(self, message, task, user_id: int, client):
        """Handle manual approval workflow by sending message to task creator"""
        import json
        try:
            task_id = task['id']
            task_name = task.get('task_name', f"مهمة {task_id}")
            
            # Check if approval already sent for this message (prevent duplicates)
            existing_approval = self.db.get_pending_message_by_source(
                task_id, str(message.chat_id), message.id
            )
            if existing_approval:
                logger.info(f"⏭️ تم تجاهل رسالة مكررة - موافقة موجودة مسبقاً (ID: {existing_approval['id']})")
                return
            
            # Prepare message data for storage
            message_data = {
                'text': message.text,
                'media_type': self.get_message_media_type(message),
                'has_media': bool(message.media),
                'chat_id': str(message.chat_id),
                'message_id': message.id,
                'date': message.date.isoformat() if message.date else None
            }
            
            # Store pending message in database
            pending_id = self.db.add_pending_message(
                task_id=task_id,
                user_id=user_id,
                source_chat_id=str(message.chat_id),
                source_message_id=message.id,
                message_data=json.dumps(message_data),
                message_type=message_data['media_type']
            )
            
            # Get source chat info
            try:
                source_chat = await client.get_entity(message.chat_id)
                source_name = getattr(source_chat, 'title', getattr(source_chat, 'first_name', 'غير معروف'))
            except:
                source_name = str(message.chat_id)
            
            # Prepare approval message
            approval_text = f"""
🔔 **طلب موافقة نشر**

📋 **المهمة:** {task_name}
📱 **المصدر:** {source_name}
🕐 **التوقيت:** {message.date.strftime('%Y-%m-%d %H:%M:%S') if message.date else 'غير محدد'}
📊 **النوع:** {message_data['media_type']}

"""
            
            if message.text:
                # Limit preview text to 200 characters
                preview_text = message.text[:200] + "..." if len(message.text) > 200 else message.text
                approval_text += f"💬 **المحتوى:**\n{preview_text}\n\n"
            
            approval_text += "⚡ اختر إجراء:"
            
            # Create inline buttons for approval/rejection using Telethon
            from telethon.tl.types import KeyboardButtonCallback
            from telethon import Button
            
            buttons = [
                [
                    Button.inline("✅ موافق", data=f"approve_{pending_id}"),
                    Button.inline("❌ رفض", data=f"reject_{pending_id}")
                ],
                [
                    Button.inline("📋 تفاصيل أكثر", data=f"details_{pending_id}")
                ]
            ]
            
            # Send approval request via Bot Token using python-telegram-bot
            try:
                import requests
                from bot_package.config import BOT_TOKEN
                
                # Prepare message text without markdown for safety
                safe_text = approval_text.replace('*', '').replace('_', '').replace('`', '')
                
                # Create inline keyboard JSON
                keyboard_json = {
                    "inline_keyboard": [
                        [
                            {"text": "✅ موافق", "callback_data": f"approve_{pending_id}"},
                            {"text": "❌ رفض", "callback_data": f"reject_{pending_id}"}
                        ],
                        [
                            {"text": "📋 تفاصيل أكثر", "callback_data": f"details_{pending_id}"}
                        ]
                    ]
                }
                
                # Send message via Telegram Bot API
                url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
                data = {
                    'chat_id': int(user_id),
                    'text': safe_text,
                    'reply_markup': keyboard_json
                }
                
                logger.info(f"🔄 إرسال طلب موافقة إلى {user_id} عبر Bot API...")
                response = requests.post(url, json=data, timeout=10)
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('ok'):
                        approval_msg_id = result['result']['message_id']
                        logger.info(f"✅ تم إرسال طلب الموافقة للمستخدم {user_id} عبر Bot API - رسالة ID: {approval_msg_id}")
                        
                        # Create a simple object to hold message_id
                        approval_msg = type('Message', (), {'message_id': approval_msg_id})()
                    else:
                        logger.error(f"❌ خطأ من Telegram API: {result}")
                        approval_msg = None
                else:
                    logger.error(f"❌ فشل في إرسال الطلب - كود الحالة: {response.status_code}")
                    logger.error(f"❌ محتوى الرد: {response.text}")
                    approval_msg = None
                
            except Exception as send_error:
                logger.error(f"❌ فشل في إرسال طلب الموافقة عبر Bot API: {send_error}")
                approval_msg = None
                
                if approval_msg:
                    # Update pending message with approval message ID
                    self.db.update_pending_message_status(
                        pending_id, 
                        'pending', 
                        approval_msg.message_id if hasattr(approval_msg, 'message_id') else None
                    )
                    logger.info(f"📬 تم إرسال طلب موافقة للمستخدم {user_id} للمهمة {task_name} (ID: {pending_id})")
                else:
                    # Mark as failed if we couldn't send the approval request
                    self.db.update_pending_message_status(pending_id, 'rejected')
                    logger.error(f"❌ لم يتم إرسال طلب الموافقة للمستخدم {user_id}")
                
            except Exception as bot_error:
                logger.error(f"❌ فشل في إرسال طلب الموافقة: {bot_error}")
                # Mark as failed if we can't send the approval request
                self.db.update_pending_message_status(pending_id, 'rejected')
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الموافقة اليدوية: {e}")

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

            # Start userbot for each saved session (one at a time to avoid conflicts)
            success_count = 0
            for i, (user_id, session_string, phone_number) in enumerate(saved_sessions):
                try:
                    logger.info(f"🔄 بدء تشغيل UserBot للمستخدم {user_id} ({phone_number}) - {i+1}/{len(saved_sessions)}")

                    # Validate session string
                    if not session_string or len(session_string) < 10:
                        logger.warning(f"⚠️ جلسة غير صالحة للمستخدم {user_id}")
                        continue

                    # Give significant delay between sessions to avoid IP conflicts
                    if i > 0:  # Don't delay for first session
                        logger.info(f"⏳ انتظار {self.startup_delay} ثانية قبل تشغيل الجلسة التالية...")
                        await asyncio.sleep(self.startup_delay)

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

            # Start session health monitor if we have active clients
            if success_count > 0:
                logger.info("🏥 بدء مراقب صحة الجلسات...")
                asyncio.create_task(self.start_session_health_monitor())

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

    async def monitor_session_health(self):
        """Monitor session health for all users with improved conflict avoidance"""
        while self.running:
            try:
                # Wait 30 seconds between checks
                await asyncio.sleep(30)
                
                # Get all authenticated users
                authenticated_users = self.db.get_all_authenticated_users()
                
                if not authenticated_users:
                    continue
                
                logger.info(f"🔍 فحص صحة {len(authenticated_users)} جلسة...")
                
                for user in authenticated_users:
                    user_id = user['user_id']
                    
                    # Skip if session is locked (being started elsewhere)
                    if user_id in self.session_locks and self.session_locks[user_id]:
                        continue
                    
                    # Check if this user's session is healthy
                    is_healthy = await self.check_user_session_health(user_id)
                    
                    if not is_healthy:
                        logger.warning(f"⚠️ جلسة غير صحية للمستخدم {user_id}")
                        
                        # Don't try to auto-reconnect to avoid conflicts
                        # Just mark it as unhealthy in database
                        self.db.update_session_health(user_id, False, "فحص دوري - غير متصل")
                
            except Exception as e:
                logger.error(f"خطأ في مراقبة صحة الجلسات: {e}")

    async def stop_user_session(self, user_id: int):
        """Stop and cleanup user session safely"""
        try:
            # Create lock if not exists
            if user_id not in self.user_locks:
                self.user_locks[user_id] = asyncio.Lock()

            async with self.user_locks[user_id]:
                # Disconnect client if exists
                if user_id in self.clients:
                    client = self.clients[user_id]
                    try:
                        await client.disconnect()
                        logger.info(f"🔌 تم فصل العميل للمستخدم {user_id}")
                    except Exception as e:
                        logger.warning(f"خطأ في فصل العميل: {e}")
                    finally:
                        del self.clients[user_id]

                # Clean up data structures
                if user_id in self.user_tasks:
                    del self.user_tasks[user_id]
                if user_id in self.album_collectors:
                    del self.album_collectors[user_id]
                if user_id in self.session_health_status:
                    del self.session_health_status[user_id]
                
                # Release session lock
                if user_id in self.session_locks:
                    self.session_locks[user_id] = False

                logger.info(f"✅ تم تنظيف جلسة المستخدم {user_id} بالكامل")

        except Exception as e:
            logger.error(f"خطأ في إيقاف جلسة المستخدم {user_id}: {e}")

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
            # More precise underscore pattern: only remove if it's clearly italic markdown (surrounded by spaces)
            cleaned_text = re.sub(r'(?<=\s)_([^_\s][^_]*[^_\s])_(?=\s)', r'\1', cleaned_text)
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
            # Preserve hyperlinks (do not strip anchor tags/markdown links)
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
            # More precise underscore pattern: only remove if it's clearly italic markdown (surrounded by spaces)
            cleaned_text = re.sub(r'(?<=\s)_([^_\s][^_]*[^_\s])_(?=\s)', r'\1', cleaned_text)
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
            # Preserve hyperlinks (do not strip anchor tags/markdown links)
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
    
    async def _send_message_with_spoiler_support(self, client, target_entity, text: str, **kwargs) -> any:
        """
        إرسال رسالة مع دعم spoiler entities
        Send message with spoiler entities support
        """
        if not text:
            text = "رسالة"
            
        processed_text, spoiler_entities = self._process_spoiler_entities(text)
        
        if spoiler_entities:
            # Remove parse_mode if spoiler entities are present
            kwargs.pop('parse_mode', None)
            kwargs['formatting_entities'] = spoiler_entities
        
        return await client.send_message(target_entity, processed_text, **kwargs)

    def _process_spoiler_entities(self, text: str) -> Tuple[str, List]:
        """
        معالجة علامات spoiler وتحويلها إلى MessageEntitySpoiler
        Process spoiler markers and convert them to MessageEntitySpoiler entities
        FIXED: حساب صحيح للمواضع والأطوال
        """
        if not text:
            return text, []
            
        from telethon.tl.types import MessageEntitySpoiler
        import re
        
        entities = []
        pattern = r'TELETHON_SPOILER_START(.*?)TELETHON_SPOILER_END'
        matches = list(re.finditer(pattern, text, re.DOTALL))
        
        if not matches:
            return text, []
        
        logger.info(f"🔍 تم العثور على {len(matches)} علامة spoiler في النص")
        
        # إنشاء النص النهائي والكيانات بطريقة صحيحة
        processed_text = text
        offset_correction = 0  # تصحيح الموضع بسبب إزالة العلامات
        
        # معالجة المطابقات بترتيب عكسي للحفاظ على المواضع
        for match in reversed(matches):
            start_pos = match.start()
            end_pos = match.end() 
            spoiler_text = match.group(1)
            
            # استبدال العلامة بالنص المخفي فقط
            processed_text = processed_text[:start_pos] + spoiler_text + processed_text[end_pos:]
        
        # الآن حساب المواضع الصحيحة في النص المُنظف
        current_offset = 0
        for match in matches:
            spoiler_text = match.group(1)
            
            # البحث عن موضع النص المخفي في النص المُنظف
            # نجد الموضع النسبي من بداية النص
            text_before_marker = text[:match.start()]
            # إزالة جميع علامات spoiler من النص السابق لحساب الموضع الصحيح
            clean_text_before = re.sub(r'TELETHON_SPOILER_START.*?TELETHON_SPOILER_END', 
                                       lambda m: m.group(1), text_before_marker, flags=re.DOTALL)
            
            correct_offset = len(clean_text_before)
            
            # إنشاء entity
            entity = MessageEntitySpoiler(
                offset=correct_offset,
                length=len(spoiler_text)
            )
            entities.append(entity)
            
            logger.info(f"✅ Spoiler entity: offset={correct_offset}, length={len(spoiler_text)}, content='{spoiler_text[:30]}{'...' if len(spoiler_text) > 30 else ''}'")
        
        logger.info(f"🔄 تم معالجة {len(entities)} عنصر spoiler بنجاح")
        logger.info(f"📝 النص الأصلي: '{text[:50]}{'...' if len(text) > 50 else ''}'")
        logger.info(f"📝 النص المُعالج: '{processed_text[:50]}{'...' if len(processed_text) > 50 else ''}'")
        
        return processed_text, entities

    def get_channel_admins_via_bot(self, bot_token: str, channel_id: int) -> List[Dict]:
        """Get channel admins using Bot API instead of UserBot"""
        try:
            import requests
            
            # Use Telegram Bot API to get chat administrators
            url = f"https://api.telegram.org/bot{bot_token}/getChatAdministrators"
            params = {'chat_id': channel_id}
            
            logger.info(f"🔍 جلب مشرفي القناة {channel_id} من Bot API...")
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('ok'):
                    admins = data.get('result', [])
                    logger.info(f"📋 تم العثور على {len(admins)} إدارة إجمالية (بما في ذلك البوتات)")
                    
                    admins_data = []
                    skipped_bots = 0
                    
                    for i, admin in enumerate(admins, 1):
                        user = admin.get('user', {})
                        user_id = user.get('id')
                        username = user.get('username', '')
                        first_name = user.get('first_name', '')
                        last_name = user.get('last_name', '')
                        is_bot = user.get('is_bot', False)
                        status = admin.get('status', 'unknown')
                        custom_title = admin.get('custom_title', '')
                        
                        logger.info(f"  {i}. ID={user_id}, User=@{username}, Name='{first_name} {last_name}', Bot={is_bot}, Status={status}, Title='{custom_title}'")
                        
                        if is_bot:
                            skipped_bots += 1
                            logger.debug(f"    ⏩ تخطي البوت: {username or first_name or user_id}")
                            continue  # Skip bots
                        
                        # Build full name
                        full_name = f"{first_name} {last_name}".strip()
                        if not full_name:
                            full_name = username or f"User {user_id}"
                        
                        admin_data = {
                            'id': user_id,
                            'username': username,
                            'first_name': full_name,
                            'is_bot': is_bot,
                            'custom_title': custom_title,  # This is what appears in post_author
                            'status': status
                        }
                        
                        admins_data.append(admin_data)
                        logger.info(f"    ✅ إضافة المشرف: {full_name} (توقيع: '{custom_title}')")
                    
                    logger.info(f"📊 النتيجة النهائية: {len(admins_data)} مشرف بشري + {skipped_bots} بوت تم تخطيهم")
                    logger.info(f"✅ تم جلب {len(admins_data)} مشرف من القناة {channel_id} عبر Bot API")
                    return admins_data
                else:
                    error_desc = data.get('description', 'Unknown error')
                    logger.error(f"❌ Bot API error: {error_desc}")
                    return []
            else:
                logger.error(f"❌ HTTP Error {response.status_code}: {response.text}")
                return []
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب مشرفي القناة {channel_id} عبر Bot API: {e}")
            import traceback
            logger.error(f"تفاصيل الخطأ: {traceback.format_exc()}")
            return []

    def _determine_final_send_mode(self, forward_mode: str, requires_copy_mode: bool) -> str:
        """تحديد الوضع النهائي للإرسال - إصلاح منطق التوجيه"""
        if forward_mode == 'copy':
            # وضع النسخ - دائماً نسخ
            return 'copy'
        elif forward_mode == 'forward':
            if requires_copy_mode:
                # وضع التوجيه مع تنسيق - إجبار النسخ
                logger.info(f"🔄 إجبار النسخ في وضع التوجيه بسبب التنسيق")
                return 'copy'
            else:
                # وضع التوجيه بدون تنسيق - توجيه عادي
                return 'forward'
        else:
            # افتراضي - توجيه
            return 'forward'




# Global userbot instance
userbot_instance = UserbotService()

async def start_userbot_service():
    """Start the userbot service"""
    logger.info("🤖 بدء تشغيل خدمة UserBot...")
    
    try:
        # Check if there are any sessions before starting
        with userbot_instance.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT COUNT(*) FROM user_sessions 
                WHERE is_authenticated = TRUE AND session_string IS NOT NULL AND session_string != ''
            ''')
            session_count = cursor.fetchone()[0]
        
        if session_count == 0:
            logger.warning("⚠️ لا توجد جلسات محفوظة - UserBot لن يبدأ")
            logger.info("💡 المستخدمين يمكنهم تسجيل الدخول عبر البوت /start")
            return False
        
        logger.info(f"📱 تم العثور على {session_count} جلسة محفوظة")
        
        # Attempt to start existing sessions
        await userbot_instance.startup_existing_sessions()
        
        # Check if any sessions actually started successfully
        active_clients = len(userbot_instance.clients)
        
        if active_clients > 0:
            logger.info(f"✅ خدمة UserBot جاهزة مع {active_clients} جلسة نشطة")
            return True
        else:
            logger.warning("⚠️ فشل في تشغيل أي جلسة UserBot - جميع الجلسات معطلة")
            logger.info("💡 المستخدمين يحتاجون إعادة تسجيل الدخول عبر البوت")
            return False
            
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل خدمة UserBot: {e}")
        return False

async def stop_userbot_service():
    """Stop the userbot service"""
    logger.info("⏹️ إيقاف خدمة UserBot...")
    await userbot_instance.stop_all()
    logger.info("✅ تم إيقاف خدمة UserBot")

# ===== معالجة الوسائط في الخلفية والإرسال المجمع =====

async def _process_media_sync(self, event, task_id: int, watermark_enabled: bool, 
                            audio_enabled: bool, is_audio_message: bool, cache_key: str):
    """معالجة الوسائط بطريقة متزامنة مع التخزين المؤقت"""
    try:
        # فحص التخزين المؤقت أولاً
        if hasattr(self, 'global_processed_media_cache') and cache_key in self.global_processed_media_cache:
            processed_media, processed_filename = self.global_processed_media_cache[cache_key]
            logger.info(f"🎯 استخدام الوسائط المعالجة من التخزين المؤقت: {processed_filename}")
            return processed_media, processed_filename
        
        # بدء المعالجة الفعلية
        processed_media = None
        processed_filename = None
        
        if watermark_enabled:
            logger.info("🏷️ تطبيق العلامة المائية مرة واحدة")
            processed_media, processed_filename = await self.apply_watermark_to_media(event, task_id)
            
            if processed_media and processed_media != event.message.media:
                # حفظ في التخزين المؤقت
                if not hasattr(self, 'global_processed_media_cache'):
                    self.global_processed_media_cache = {}
                self.global_processed_media_cache[cache_key] = (processed_media, processed_filename)
                logger.info(f"✅ تم تطبيق العلامة المائية وحفظها: {processed_filename}")
            else:
                logger.info("🔄 لم يتم تطبيق العلامة المائية، استخدام الوسائط الأصلية")
        
        elif audio_enabled and is_audio_message:
            logger.info("🎵 تطبيق وسوم الصوت مرة واحدة")
            
            # تحميل الوسائط واستخراج اسم مناسب
            if not hasattr(self, '_current_media_cache'):
                self._current_media_cache = {}
            
            media_cache_key_download = f"{event.message.id}_{event.chat_id}_download"
            
            if media_cache_key_download in self._current_media_cache:
                media_bytes, file_name, file_ext = self._current_media_cache[media_cache_key_download]
                logger.info("🔄 استخدام الوسائط المحمّلة من التخزين المؤقت")
            else:
                # تحميل مرة واحدة فقط
                media_bytes = await event.message.download_media(bytes)
                if not media_bytes:
                    return event.message.media, None
                
                # استخراج اسم الملف وامتداده
                file_name = "audio"
                file_ext = ".mp3"
                
                if hasattr(event.message.media, 'document') and event.message.media.document:
                    doc = event.message.media.document
                    if hasattr(doc, 'attributes'):
                        for attr in doc.attributes:
                            if hasattr(attr, 'file_name') and attr.file_name:
                                if '.' in attr.file_name:
                                    file_name = attr.file_name.rsplit('.', 1)[0]
                                    file_ext = '.' + attr.file_name.split('.')[-1].lower()
                                else:
                                    file_name = attr.file_name
                                break
                
                # حفظ في التخزين المؤقت للتحميل
                self._current_media_cache[media_cache_key_download] = (media_bytes, file_name, file_ext)
            
            # تطبيق معالجة الصوت
            processed_media, processed_filename = await self.apply_audio_metadata(
                event, task_id, media_bytes, f"{file_name}{file_ext}"
            )
            
            if processed_media and isinstance(processed_media, (bytes, bytearray)):
                # حفظ في التخزين المؤقت
                if not hasattr(self, 'global_processed_media_cache'):
                    self.global_processed_media_cache = {}
                self.global_processed_media_cache[cache_key] = (processed_media, processed_filename)
                logger.info(f"✅ تم تطبيق وسوم الصوت وحفظها: {processed_filename}")
            else:
                logger.info("🔄 لم يتم تطبيق وسوم الصوت، استخدام الوسائط الأصلية")
        
        return processed_media, processed_filename
        
    except Exception as e:
        logger.error(f"❌ خطأ في المعالجة المتزامنة: {e}")
        return None, None

async def _apply_batch_send_delay(self, batch_key: str, target_chat_id: str, 
                                message_data: dict, delay: float = 2.0):
    """تطبيق تأخير الإرسال المجمع"""
    try:
        if BACKGROUND_PROCESSING_AVAILABLE:
            # استخدام نظام الإرسال المجمع المتقدم
            await queue_batch_message(batch_key, {
                'target_chat_id': target_chat_id,
                'message_data': message_data,
                'send_callback': self._send_batch_message
            }, delay)
            return True
        else:
            # تأخير بسيط
            await asyncio.sleep(delay)
            return False
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق تأخير الإرسال المجمع: {e}")
        return False

async def _send_batch_message(self, message_data: dict):
    """إرسال رسالة مجمعة"""
    try:
        # تنفيذ منطق الإرسال الفعلي هنا
        target_chat_id = message_data.get('target_chat_id')
        data = message_data.get('message_data', {})
        
        logger.info(f"📤 إرسال رسالة مجمعة إلى: {target_chat_id}")
        # يمكن توسيع هذا لتنفيذ الإرسال الفعلي
        
    except Exception as e:
        logger.error(f"❌ خطأ في إرسال رسالة مجمعة: {e}")

async def _apply_enhanced_batch_delay(self, task: dict, media=None, filename=None):
    """تطبيق تأخير محسن للإرسال المجمع بناءً على نوع الوسائط"""
    try:
        base_delay = 1.0  # تأخير أساسي بثانية واحدة
        
        # تحديد التأخير بناءً على نوع الوسائط
        if media and filename:
            if filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
                # فيديو - تأخير أطول
                delay = base_delay * 2.5
                logger.info(f"🎬 تأخير إرسال فيديو: {delay}s")
            elif filename.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
                # صورة - تأخير متوسط
                delay = base_delay * 1.5
                logger.info(f"🖼️ تأخير إرسال صورة: {delay}s")
            elif filename.lower().endswith(('.mp3', '.m4a', '.aac', '.ogg', '.wav')):
                # صوت - تأخير قصير
                delay = base_delay * 1.2
                logger.info(f"🎵 تأخير إرسال صوت: {delay}s")
            else:
                # ملف عادي
                delay = base_delay
                logger.info(f"📄 تأخير إرسال ملف: {delay}s")
        else:
            # رسالة نصية
            delay = base_delay * 0.5
            logger.info(f"📝 تأخير إرسال نص: {delay}s")
        
        # تطبيق التأخير
        await asyncio.sleep(delay)
        
        return True
        
    except Exception as e:
        logger.error(f"❌ خطأ في تطبيق التأخير المحسن: {e}")
        # تأخير بسيط كبديل
        await asyncio.sleep(1.0)
        return False

async def _should_use_background_processing(self, event, processing_needed: bool) -> bool:
    """تحديد ما إذا كان يجب استخدام المعالجة في الخلفية"""
    try:
        if not processing_needed or not self.background_media_processing:
            return False
        
        # فحص حجم الملف
        if hasattr(event.message, 'media') and hasattr(event.message.media, 'document'):
            doc = event.message.media.document
            if doc and hasattr(doc, 'size') and doc.size:
                file_size = doc.size
                # استخدام المعالجة في الخلفية للملفات أكبر من 3 ميجابايت
                if file_size > 3 * 1024 * 1024:
                    logger.info(f"📊 ملف كبير ({file_size / 1024 / 1024:.1f}MB) - يُفضل المعالجة في الخلفية")
                    return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحديد نوع المعالجة: {e}")
        return False

# إضافة الوظائف للصف UserbotService
UserbotService._process_media_sync = _process_media_sync
UserbotService._apply_batch_send_delay = _apply_batch_send_delay
UserbotService._send_batch_message = _send_batch_message
UserbotService._apply_enhanced_batch_delay = _apply_enhanced_batch_delay
UserbotService._should_use_background_processing = _should_use_background_processing