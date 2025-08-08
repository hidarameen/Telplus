"""
Userbot Service for Message Forwarding
Uses Telethon for automated message forwarding between chats
"""
import logging
import asyncio
from typing import Dict, List, Optional
from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, AuthKeyUnregisteredError
from telethon.sessions import StringSession
from database.database import Database
from bot_package.config import API_ID, API_HASH
import time

logger = logging.getLogger(__name__)

class UserbotService:
    def __init__(self):
        self.db = Database()
        self.clients: Dict[int, TelegramClient] = {}  # user_id -> client
        self.user_tasks: Dict[int, List[Dict]] = {}   # user_id -> tasks
        self.running = True

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
                logger.info(f"🎬 نوع الوسائط للرسالة: {message_media_type}")

                # Find matching tasks for this source chat
                matching_tasks = []
                logger.info(f"🔍 البحث عن مهام مطابقة للمحادثة {source_chat_id} (username: {source_username})")

                for task in tasks:
                    task_source_id = str(task['source_chat_id'])
                    task_name = task.get('task_name', f"مهمة {task['id']}")
                    task_id = task.get('id')

                    logger.info(f"🔍 فحص المهمة '{task_name}': مصدر='{task_source_id}' ضد '{source_chat_id}', هدف='{task['target_chat_id']}'")

                    # Direct ID comparison (string to string)
                    if task_source_id == source_chat_id:
                        logger.info(f"✅ تطابق مباشر: '{task_source_id}' == '{source_chat_id}'")

                        # Check media filter
                        if self.is_media_allowed(task_id, message_media_type):
                            matching_tasks.append(task)
                            logger.info(f"✅ الوسائط مسموحة لهذه المهمة: {message_media_type}")
                        else:
                            logger.info(f"🚫 الوسائط محظورة لهذه المهمة: {message_media_type}")
                    else:
                        logger.info(f"❌ لا يوجد تطابق للمهمة '{task_name}': '{task_source_id}' != '{source_chat_id}'")

                if not matching_tasks:
                    logger.debug(f"لا توجد مهام مطابقة للمحادثة {source_chat_id} للمستخدم {user_id}")
                    return

                logger.info(f"تم العثور على {len(matching_tasks)} مهمة مطابقة للمحادثة {source_chat_id}")

                # Forward message to all target chats
                for task in matching_tasks:
                    try:
                        target_chat_id = str(task['target_chat_id']).strip()
                        task_name = task.get('task_name', f"مهمة {task['id']}")

                        # Get task forward mode
                        forward_mode = task.get('forward_mode', 'forward')
                        mode_text = "نسخ" if forward_mode == 'copy' else "توجيه"

                        logger.info(f"🔄 بدء {mode_text} رسالة من {source_chat_id} إلى {target_chat_id} (المهمة: {task_name})")
                        logger.info(f"📤 تفاصيل الإرسال: مصدر='{source_chat_id}', هدف='{target_chat_id}', وضع={mode_text}, مستخدم={user_id}")

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

                        # Send message based on forward mode
                        logger.info(f"📨 جاري إرسال الرسالة...")

                        if forward_mode == 'copy':
                            # Copy mode: send as new message
                            if event.message.text:
                                # Text message
                                forwarded_msg = await client.send_message(
                                    target_entity,
                                    event.message.text
                                )
                            elif event.message.media:
                                # Media message
                                forwarded_msg = await client.send_file(
                                    target_entity,
                                    event.message.media,
                                    caption=event.message.text or ""
                                )
                            else:
                                # Fallback to forward for other types
                                forwarded_msg = await client.forward_messages(
                                    target_entity,
                                    event.message
                                )
                        else:
                            # Forward mode: forward message normally
                            forwarded_msg = await client.forward_messages(
                                target_entity,
                                event.message
                            )

                        if forwarded_msg:
                            msg_id = forwarded_msg[0].id if isinstance(forwarded_msg, list) else forwarded_msg.id
                            logger.info(f"✅ تم توجيه الرسالة بنجاح من {source_chat_id} إلى {target_chat_id}")
                            logger.info(f"📝 معرف الرسالة المُوجهة: {msg_id} (المهمة: {task_name})")
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
                                logger.info(f"  • {task_name}: {task['source_chat_id']} → {task['target_chat_id']}")
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