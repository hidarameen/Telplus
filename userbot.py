import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from database import Database
import config
import os

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

class ForwardingUserBot:
    def __init__(self):
        self.db = Database()
        self.client = None
        self.active_tasks = {}
        self.session_string = None
    
    async def load_session(self, phone_number=None):
        """Load user session from database or file"""
        if phone_number:
            session_string = self.db.get_user_session(phone_number)
            if session_string:
                self.session_string = session_string
                return True
        
        # Try to load from session file
        session_file = f"{config.SESSION_FILE}.session"
        if os.path.exists(session_file):
            try:
                self.client = TelegramClient(config.SESSION_FILE, config.API_ID, config.API_HASH)
                await self.client.start()
                return True
            except Exception as e:
                logger.error(f"فشل في تحميل الجلسة: {e}")
                return False
        
        return False
    
    async def create_session_from_string(self, session_string):
        """Create client from session string"""
        try:
            self.client = TelegramClient(
                StringSession(session_string), 
                config.API_ID, 
                config.API_HASH
            )
            await self.client.start()
            self.session_string = session_string
            return True
        except Exception as e:
            logger.error(f"فشل في إنشاء الجلسة: {e}")
            return False
    
    async def start_client(self):
        """Start the userbot client"""
        if not self.client:
            logger.error("لم يتم العثور على جلسة نشطة")
            return False
        
        if not self.client.is_connected():
            await self.client.start()
        
        # Load active tasks
        await self.load_tasks()
        
        # Set up message handler
        @self.client.on(events.NewMessage())
        async def handle_new_message(event):
            await self.process_message(event)
        
        logger.info("🚀 تم تشغيل UserBot بنجاح")
        return True
    
    async def load_tasks(self):
        """Load active forwarding tasks"""
        tasks = self.db.get_active_tasks()
        self.active_tasks = {}
        
        for task in tasks:
            # Convert chat identifiers to entity IDs
            source_entities = []
            target_entities = []
            
            try:
                for source_chat in task['source_chats']:
                    entity = await self.get_chat_entity(source_chat)
                    if entity:
                        source_entities.append(entity.id)
                
                for target_chat in task['target_chats']:
                    entity = await self.get_chat_entity(target_chat)
                    if entity:
                        target_entities.append(entity.id)
                
                if source_entities and target_entities:
                    self.active_tasks[task['id']] = {
                        'name': task['name'],
                        'source_chats': source_entities,
                        'target_chats': target_entities
                    }
                    logger.info(f"✅ تم تحميل المهمة: {task['name']}")
            
            except Exception as e:
                logger.error(f"❌ فشل في تحميل المهمة {task['name']}: {e}")
        
        logger.info(f"📊 تم تحميل {len(self.active_tasks)} مهمة نشطة")
    
    async def get_chat_entity(self, chat_identifier):
        """Get chat entity from identifier (username, phone, or ID)"""
        try:
            if chat_identifier.startswith('@'):
                return await self.client.get_entity(chat_identifier)
            elif chat_identifier.startswith('+'):
                return await self.client.get_entity(chat_identifier)
            elif chat_identifier.isdigit() or (chat_identifier.startswith('-') and chat_identifier[1:].isdigit()):
                return await self.client.get_entity(int(chat_identifier))
            else:
                # Try as username without @
                return await self.client.get_entity(f"@{chat_identifier}")
        except Exception as e:
            logger.error(f"فشل في العثور على المحادثة {chat_identifier}: {e}")
            return None
    
    async def process_message(self, event):
        """Process incoming messages for forwarding"""
        chat_id = event.chat_id
        
        # Check if message is from a source chat
        for task_id, task in self.active_tasks.items():
            if chat_id in task['source_chats']:
                await self.forward_message(event, task['target_chats'], task['name'])
    
    async def forward_message(self, event, target_chats, task_name):
        """Forward message to target chats"""
        try:
            for target_chat_id in target_chats:
                await self.client.forward_messages(
                    entity=target_chat_id,
                    messages=event.message,
                    from_peer=event.chat_id
                )
            
            logger.info(f"📤 تم توجيه رسالة من {event.chat_id} إلى {len(target_chats)} محادثة (المهمة: {task_name})")
        
        except Exception as e:
            logger.error(f"❌ فشل في توجيه الرسالة: {e}")
    
    async def reload_tasks(self):
        """Reload tasks from database"""
        await self.load_tasks()
        logger.info("🔄 تم إعادة تحميل المهام")
    
    async def stop(self):
        """Stop the userbot"""
        if self.client:
            await self.client.disconnect()
        logger.info("⏹️ تم إيقاف UserBot")

# Global userbot instance
userbot_instance = ForwardingUserBot()

async def start_userbot(session_string=None, phone_number=None):
    """Start the userbot service"""
    global userbot_instance
    
    if session_string:
        success = await userbot_instance.create_session_from_string(session_string)
    else:
        success = await userbot_instance.load_session(phone_number)
    
    if success:
        await userbot_instance.start_client()
        return True
    else:
        logger.error("فشل في تشغيل UserBot")
        return False

async def reload_userbot_tasks():
    """Reload userbot tasks"""
    global userbot_instance
    if userbot_instance.client:
        await userbot_instance.reload_tasks()

def run_userbot():
    """Run the userbot in a separate process"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(start_userbot())
        loop.run_forever()
    except KeyboardInterrupt:
        logger.info("تم إيقاف UserBot")
    finally:
        loop.run_until_complete(userbot_instance.stop())
        loop.close()

if __name__ == '__main__':
    run_userbot()
