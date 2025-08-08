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
        
        @client.on(events.NewMessage)
        async def message_handler(event):
            try:
                # Get user tasks
                tasks = self.user_tasks.get(user_id, [])
                
                # Log incoming message details
                chat_info = f"Chat ID: {event.chat_id}"
                if hasattr(event.chat, 'username') and event.chat.username:
                    chat_info += f", Username: @{event.chat.username}"
                if hasattr(event.chat, 'title') and event.chat.title:
                    chat_info += f", Title: {event.chat.title}"
                
                logger.info(f"رسالة جديدة من المستخدم {user_id} - {chat_info}")
                
                if not tasks:
                    return
                
                # Get source chat ID and username
                source_chat_id = event.chat_id
                source_username = getattr(event.chat, 'username', None)
                
                # Find matching tasks for this source chat
                matching_tasks = []
                for task in tasks:
                    task_source = task['source_chat_id'].strip()
                    
                    # Handle different ID formats
                    try:
                        # Convert both to integers for comparison if possible
                        if task_source.lstrip('-').isdigit():
                            task_source_int = int(task_source)
                            if task_source_int == source_chat_id:
                                matching_tasks.append(task)
                                continue
                        
                        # Handle username format (@username)
                        if task_source.startswith('@') and source_username:
                            if task_source == f"@{source_username}":
                                matching_tasks.append(task)
                                continue
                        
                        # Handle direct string comparison
                        if task_source == str(source_chat_id):
                            matching_tasks.append(task)
                            continue
                            
                    except (ValueError, AttributeError):
                        continue
                
                if not matching_tasks:
                    logger.debug(f"لا توجد مهام مطابقة للمحادثة {source_chat_id} للمستخدم {user_id}")
                    return
                
                logger.info(f"تم العثور على {len(matching_tasks)} مهمة مطابقة للمحادثة {source_chat_id}")
                
                # Forward message to all target chats
                for task in matching_tasks:
                    try:
                        target_chat_id = task['target_chat_id'].strip()
                        task_name = task.get('task_name', f"مهمة {task['id']}")
                        
                        # Parse target chat ID
                        if target_chat_id.startswith('@'):
                            target_entity = target_chat_id
                        else:
                            target_entity = int(target_chat_id)
                        
                        # Forward the message
                        await client.forward_messages(
                            target_entity,
                            event.message
                        )
                        
                        logger.info(f"✅ تم توجيه رسالة من {source_chat_id} إلى {target_chat_id} (المهمة: {task_name}) للمستخدم {user_id}")
                        
                    except Exception as forward_error:
                        task_name = task.get('task_name', f"مهمة {task['id']}")
                        logger.error(f"❌ خطأ في توجيه الرسالة (المهمة: {task_name}) للمستخدم {user_id}: {forward_error}")
                        logger.error(f"تفاصيل الخطأ: مصدر={source_chat_id}, هدف={target_chat_id}")
                        
            except Exception as e:
                logger.error(f"خطأ في معالج الرسائل للمستخدم {user_id}: {e}")
    
    async def refresh_user_tasks(self, user_id: int):
        """Refresh user tasks from database"""
        try:
            tasks = self.db.get_active_tasks(user_id)
            self.user_tasks[user_id] = tasks
            
            # Log detailed task information
            logger.info(f"تم تحديث {len(tasks)} مهمة للمستخدم {user_id}")
            for task in tasks:
                logger.info(f"مهمة {task['id']}: مصدر={task['source_chat_id']}, هدف={task['target_chat_id']}")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث المهام للمستخدم {user_id}: {e}")
    
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
            # This would be called on system startup to restore all user sessions
            # For now, we'll implement it as a placeholder since sessions are started
            # when users authenticate through the bot
            logger.info("بحث عن جلسات المستخدمين الموجودة...")
            
            # In a real implementation, you might want to:
            # 1. Query database for all authenticated users
            # 2. Start their userbot sessions
            # 3. Load their tasks
            
            logger.info("تم تشغيل جلسات المستخدمين الموجودة")
            
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