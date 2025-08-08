"""
Simple Telegram Bot using Telethon
Handles both bot API and user API functionality
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
        self.conversation_states = {}
        
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
        """Handle callback queries"""
        user_id = event.sender_id
        data = event.data.decode('utf-8')
        
        try:
            if data == "manage_tasks":
                await self.show_tasks_menu(event)
            elif data == "create_task":
                await self.start_create_task(event)
            elif data == "list_tasks":
                await self.list_tasks(event)
            elif data.startswith("task_manage_"):
                task_id = int(data.split("_")[2])
                await self.show_task_details(event, task_id)
            elif data.startswith("task_toggle_"):
                task_id = int(data.split("_")[2])
                await self.toggle_task(event, task_id)
            elif data.startswith("task_delete_"):
                task_id = int(data.split("_")[2])
                await self.delete_task(event, task_id)
            elif data == "auth_phone":
                await self.start_auth(event)
            elif data == "back_main":
                await self.show_main_menu(event)
            elif data == "settings":
                await self.show_settings(event)
            elif data == "about":
                await self.show_about(event)
        except Exception as e:
            logger.error(f"خطأ في معالجة الاستعلام: {e}")
            await event.answer("❌ حدث خطأ، حاول مرة أخرى")
    
    async def handle_message(self, event):
        """Handle text messages"""
        user_id = event.sender_id
        
        # Check if user is in conversation state
        if user_id in self.conversation_states:
            await self.handle_conversation_message(event)
        elif event.raw_text.startswith('/'):
            # Handle commands
            if event.raw_text == '/start':
                await self.handle_start(event)
    
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
        
        # Set conversation state
        self.conversation_states[user_id] = {
            'state': 'waiting_source_chat',
            'data': {}
        }
        
        buttons = [
            [Button.inline("❌ إلغاء", b"manage_tasks")]
        ]
        
        await event.edit(
            "➕ إنشاء مهمة توجيه جديدة\n\n"
            "📥 **الخطوة 1: تحديد المصدر**\n\n"
            "أرسل معرف أو رابط المجموعة/القناة المصدر:\n\n"
            "أمثلة:\n"
            "• @channelname\n"
            "• https://t.me/channelname\n"
            "• -1001234567890\n\n"
            "⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات قراءة الرسائل",
            buttons=buttons
        )
    
    async def list_tasks(self, event):
        """List user tasks"""
        user_id = event.sender_id
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
        
        # Build tasks list
        message = "📋 قائمة المهام:\n\n"
        buttons = []
        
        for i, task in enumerate(tasks[:10], 1):  # Show max 10 tasks
            status = "🟢 نشطة" if task['is_active'] else "🔴 متوقفة"
            message += f"{i}. {status}\n"
            message += f"   📥 من: {task['source_chat_name'] or task['source_chat_id']}\n"
            message += f"   📤 إلى: {task['target_chat_name'] or task['target_chat_id']}\n\n"
            
            # Add task button
            buttons.append([
                Button.inline(f"⚙️ مهمة {i}", f"task_manage_{task['id']}")
            ])
        
        buttons.append([Button.inline("➕ إنشاء مهمة جديدة", b"create_task")])
        buttons.append([Button.inline("🏠 القائمة الرئيسية", b"back_main")])
        
        await event.edit(message, buttons=buttons)
    
    async def show_task_details(self, event, task_id):
        """Show task details"""
        user_id = event.sender_id
        task = self.db.get_task(task_id, user_id)
        
        if not task:
            await event.answer("❌ المهمة غير موجودة")
            return
        
        status = "🟢 نشطة" if task['is_active'] else "🔴 متوقفة"
        toggle_text = "⏸️ إيقاف" if task['is_active'] else "▶️ تشغيل"
        
        buttons = [
            [Button.inline(toggle_text, f"task_toggle_{task_id}")],
            [Button.inline("🗑️ حذف المهمة", f"task_delete_{task_id}")],
            [Button.inline("📋 عرض المهام", b"list_tasks")]
        ]
        
        await event.edit(
            f"⚙️ تفاصيل المهمة #{task['id']}\n\n"
            f"📊 الحالة: {status}\n\n"
            f"📥 **المصدر:**\n"
            f"• اسم: {task['source_chat_name'] or 'غير محدد'}\n"
            f"• معرف: `{task['source_chat_id']}`\n\n"
            f"📤 **الوجهة:**\n"
            f"• اسم: {task['target_chat_name'] or 'غير محدد'}\n"
            f"• معرف: `{task['target_chat_id']}`\n\n"
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
        
        # Update userbot tasks
        try:
            from userbot_service.userbot import userbot_instance
            await userbot_instance.refresh_user_tasks(user_id)
        except:
            pass
        
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
        
        # Update userbot tasks
        try:
            from userbot_service.userbot import userbot_instance
            await userbot_instance.refresh_user_tasks(user_id)
        except:
            pass
        
        await event.answer("✅ تم حذف المهمة بنجاح")
        await self.list_tasks(event)
    
    async def handle_conversation_message(self, event):
        """Handle conversation messages for task creation"""
        user_id = event.sender_id
        
        if user_id not in self.conversation_states:
            return
        
        state_info = self.conversation_states[user_id]
        message_text = event.raw_text.strip()
        
        try:
            if state_info['state'] == 'waiting_source_chat':
                await self.handle_source_chat(event, message_text)
            elif state_info['state'] == 'waiting_target_chat':
                await self.handle_target_chat(event, message_text)
            elif state_info['state'] == 'waiting_phone':
                await self.handle_phone_input(event, message_text)
            elif state_info['state'] == 'waiting_code':
                await self.handle_code_input(event, message_text)
            elif state_info['state'] == 'waiting_password':
                await self.handle_password_input(event, message_text)
        except Exception as e:
            logger.error(f"خطأ في معالجة رسالة المحادثة: {e}")
            await event.respond("❌ حدث خطأ، حاول مرة أخرى")
            if user_id in self.conversation_states:
                del self.conversation_states[user_id]
    
    async def handle_source_chat(self, event, chat_input):
        """Handle source chat input"""
        user_id = event.sender_id
        
        # Parse chat input
        source_chat_id, source_chat_name = self.parse_chat_input(chat_input)
        
        if not source_chat_id:
            await event.respond(
                "❌ تنسيق معرف المجموعة/القناة غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890"
            )
            return
        
        # Store source chat data
        self.conversation_states[user_id] = {
            'state': 'waiting_target_chat',
            'data': {
                'source_chat_id': source_chat_id,
                'source_chat_name': source_chat_name
            }
        }
        
        buttons = [
            [Button.inline("❌ إلغاء", b"manage_tasks")]
        ]
        
        await event.respond(
            f"✅ تم تحديد المصدر: {source_chat_name or source_chat_id}\n\n"
            f"📤 **الخطوة 2: تحديد الوجهة**\n\n"
            f"أرسل معرف أو رابط المجموعة/القناة المراد توجيه الرسائل إليها:\n\n"
            f"أمثلة:\n"
            f"• @targetchannel\n"
            f"• https://t.me/targetchannel\n"
            f"• -1001234567890\n\n"
            f"⚠️ تأكد من أن البوت مضاف للمجموعة/القناة وله صلاحيات إرسال الرسائل",
            buttons=buttons
        )
    
    async def handle_target_chat(self, event, chat_input):
        """Handle target chat input"""
        user_id = event.sender_id
        
        # Parse target chat
        target_chat_id, target_chat_name = self.parse_chat_input(chat_input)
        
        if not target_chat_id:
            await event.respond(
                "❌ تنسيق معرف المجموعة/القناة غير صحيح\n\n"
                "استخدم أحد الأشكال التالية:\n"
                "• @channelname\n"
                "• https://t.me/channelname\n"
                "• -1001234567890"
            )
            return
        
        # Get source chat data
        source_data = self.conversation_states[user_id]['data']
        source_chat_id = source_data['source_chat_id']
        source_chat_name = source_data['source_chat_name']
        
        # Create task in database
        task_id = self.db.create_task(
            user_id, 
            source_chat_id, 
            source_chat_name,
            target_chat_id, 
            target_chat_name
        )
        
        # Clear conversation state
        del self.conversation_states[user_id]
        
        # Update userbot tasks
        try:
            from userbot_service.userbot import userbot_instance
            await userbot_instance.refresh_user_tasks(user_id)
        except:
            pass
        
        buttons = [
            [Button.inline("📋 عرض المهام", b"list_tasks")],
            [Button.inline("➕ إنشاء مهمة أخرى", b"create_task")],
            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        ]
        
        await event.respond(
            f"🎉 تم إنشاء المهمة بنجاح!\n\n"
            f"🆔 رقم المهمة: #{task_id}\n"
            f"📥 من: {source_chat_name or source_chat_id}\n"
            f"📤 إلى: {target_chat_name or target_chat_id}\n"
            f"🟢 الحالة: نشطة\n\n"
            f"✅ سيتم توجيه جميع الرسائل الجديدة تلقائياً",
            buttons=buttons
        )
    
    def parse_chat_input(self, chat_input):
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
    
    async def start_auth(self, event):
        """Start authentication process"""
        user_id = event.sender_id
        
        self.conversation_states[user_id] = {
            'state': 'waiting_phone',
            'data': {}
        }
        
        buttons = [
            [Button.inline("❌ إلغاء", b"back_main")]
        ]
        
        await event.edit(
            "📱 تسجيل الدخول\n\n"
            "أرسل رقم هاتفك مع رمز البلد:\n"
            "مثال: +966501234567\n\n"
            "⚠️ تأكد من صحة الرقم",
            buttons=buttons
        )
    
    async def handle_phone_input(self, event, phone):
        """Handle phone number input"""
        user_id = event.sender_id
        
        try:
            # Start userbot authentication
            from userbot_service.userbot import userbot_instance
            result = await userbot_instance.start_auth(user_id, phone)
            
            if result['success']:
                self.conversation_states[user_id]['state'] = 'waiting_code'
                self.conversation_states[user_id]['data']['phone'] = phone
                
                await event.respond(
                    f"📨 تم إرسال رمز التحقق إلى {phone}\n\n"
                    f"أرسل الرمز المكون من 5 أرقام:"
                )
            else:
                await event.respond(f"❌ خطأ: {result['error']}")
                del self.conversation_states[user_id]
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل الدخول: {e}")
            await event.respond("❌ حدث خطأ في تسجيل الدخول")
            if user_id in self.conversation_states:
                del self.conversation_states[user_id]
    
    async def handle_code_input(self, event, code):
        """Handle verification code input"""
        user_id = event.sender_id
        phone = self.conversation_states[user_id]['data']['phone']
        
        try:
            from userbot_service.userbot import userbot_instance
            result = await userbot_instance.verify_code(user_id, code)
            
            if result['success']:
                if result['need_password']:
                    self.conversation_states[user_id]['state'] = 'waiting_password'
                    await event.respond(
                        "🔐 يلزم كلمة مرور التحقق بخطوتين\n\n"
                        "أرسل كلمة المرور:"
                    )
                else:
                    # Authentication complete
                    del self.conversation_states[user_id]
                    
                    buttons = [
                        [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
                        [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
                    ]
                    
                    await event.respond(
                        f"✅ تم تسجيل الدخول بنجاح!\n\n"
                        f"📱 الرقم: {phone}\n"
                        f"🤖 يمكنك الآن إنشاء مهام التوجيه التلقائي",
                        buttons=buttons
                    )
            else:
                await event.respond(f"❌ خطأ: {result['error']}")
                if user_id in self.conversation_states:
                    del self.conversation_states[user_id]
                
        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {e}")
            await event.respond("❌ حدث خطأ في التحقق من الرمز")
            if user_id in self.conversation_states:
                del self.conversation_states[user_id]
    
    async def handle_password_input(self, event, password):
        """Handle 2FA password input"""
        user_id = event.sender_id
        phone = self.conversation_states[user_id]['data']['phone']
        
        try:
            from userbot_service.userbot import userbot_instance
            result = await userbot_instance.verify_password(user_id, password)
            
            if result['success']:
                # Authentication complete
                del self.conversation_states[user_id]
                
                buttons = [
                    [Button.inline("📝 إدارة مهام التوجيه", b"manage_tasks")],
                    [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
                ]
                
                await event.respond(
                    f"✅ تم تسجيل الدخول بنجاح!\n\n"
                    f"📱 الرقم: {phone}\n"
                    f"🤖 يمكنك الآن إنشاء مهام التوجيه التلقائي",
                    buttons=buttons
                )
            else:
                await event.respond(f"❌ خطأ: {result['error']}")
                if user_id in self.conversation_states:
                    del self.conversation_states[user_id]
                
        except Exception as e:
            logger.error(f"خطأ في التحقق من كلمة المرور: {e}")
            await event.respond("❌ حدث خطأ في التحقق من كلمة المرور")
            if user_id in self.conversation_states:
                del self.conversation_states[user_id]
    
    async def show_settings(self, event):
        """Show settings menu"""
        buttons = [
            [Button.inline("🔄 إعادة تسجيل الدخول", b"auth_phone")],
            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        ]
        
        await event.edit(
            "⚙️ الإعدادات\n\nاختر إعداد:",
            buttons=buttons
        )
    
    async def show_about(self, event):
        """Show about information"""
        buttons = [
            [Button.inline("🏠 القائمة الرئيسية", b"back_main")]
        ]
        
        await event.edit(
            "ℹ️ حول البوت\n\n"
            "🤖 بوت التوجيه التلقائي\n"
            "📋 يساعدك في توجيه الرسائل تلقائياً بين المجموعات والقنوات\n\n"
            "🔧 الميزات:\n"
            "• توجيه تلقائي للرسائل\n"
            "• إدارة مهام التوجيه\n"
            "• مراقبة الحالة\n"
            "• واجهة عربية سهلة الاستخدام",
            buttons=buttons
        )
    
    async def handle_callback(self, event):
        """Handle button callbacks"""
        user_id = event.sender_id
        data = event.data.decode()
        
        if data == "auth_phone":
            await self.start_phone_auth(event)
        elif data == "manage_tasks":
            if self.db.is_user_authenticated(user_id):
                await self.show_tasks_menu(event)
            else:
                await event.edit("❌ يجب تسجيل الدخول أولاً")
        elif data == "create_task":
            if self.db.is_user_authenticated(user_id):
                await self.start_create_task(event)
            else:
                await event.edit("❌ يجب تسجيل الدخول أولاً")
        elif data == "list_tasks":
            if self.db.is_user_authenticated(user_id):
                await self.list_tasks(event)
            else:
                await event.edit("❌ يجب تسجيل الدخول أولاً")
        elif data.startswith("task_"):
            if self.db.is_user_authenticated(user_id):
                await self.handle_task_action(event, data)
            else:
                await event.edit("❌ يجب تسجيل الدخول أولاً")
        elif data == "settings":
            await self.show_settings_menu(event)
        elif data == "about":
            await self.show_about(event)
        elif data == "back_main":
            await self.show_main_menu(event)
        elif data == "cancel_auth":
            await self.cancel_auth(event)
    
    async def handle_message(self, event):
        """Handle text messages"""
        # Skip if it's a command
        if event.text.startswith('/'):
            return
            
        user_id = event.sender_id
        
        # Check if user is in authentication process
        state_data = self.db.get_conversation_state(user_id)
        
        if state_data:
            await self.handle_auth_message(event, state_data)
            return
        
        # Check if user is in task creation process
        state_data = self.db.get_conversation_state(user_id)
        if state_data:
            state, data = state_data
            if state.startswith('waiting_'):
                await self.handle_task_message(event, state_data)
                return
        
        # Default response
        await event.respond("👋 أهلاً! استخدم /start لعرض القائمة الرئيسية")
    
    async def start_phone_auth(self, event):
        """Start phone authentication"""
        user_id = event.sender_id
        
        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_phone')
        
        buttons = [
            [Button.inline("❌ إلغاء", b"cancel_auth")]
        ]
        
        await event.edit(
            "📱 تسجيل الدخول إلى تليجرام\n\n"
            "🔐 لتتمكن من استخدام ميزة التوجيه التلقائي، نحتاج لتسجيل دخولك إلى حساب تليجرام الخاص بك.\n\n"
            "📞 أرسل رقم هاتفك بالتنسيق الدولي:\n"
            "مثال: +966501234567\n"
            "أو: +201234567890\n\n"
            "⚠️ تأكد من إدخال الرقم بشكل صحيح مع رمز البلد",
            buttons=buttons
        )
    
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
        try:
            temp_client = TelegramClient(':memory:', int(API_ID), API_HASH)
            await temp_client.connect()
            
            # Send code request
            sent_code = await temp_client.send_code_request(phone)
            
            # Store data for next step
            auth_data = {
                'phone': phone,
                'phone_code_hash': sent_code.phone_code_hash
            }
            self.db.set_conversation_state(user_id, 'waiting_code', json.dumps(auth_data))
            
            buttons = [
                [Button.inline("❌ إلغاء", b"cancel_auth")]
            ]
            
            await event.respond(
                f"✅ تم إرسال رمز التحقق إلى {phone}\n\n"
                "🔢 أرسل الرمز المكون من 5 أرقام:\n"
                "• يمكن إضافة حروف لتجنب حظر تليجرام: aa12345\n"
                "• أو إرسال الأرقام مباشرة: 12345\n\n"
                "⏰ انتظر بضع ثواني حتى يصل الرمز",
                buttons=buttons
            )
            
            await temp_client.disconnect()
            
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
                        f"⏰ تم طلب رموز كثيرة من تليجرام\n\n"
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
            auth_data = json.loads(data)
            phone = auth_data['phone']
            phone_code_hash = auth_data['phone_code_hash']
            
            # Create client and sign in
            temp_client = TelegramClient(':memory:', int(API_ID), API_HASH)
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
        """Show tasks menu"""
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
    
    # Placeholder methods for other functionality
    async def start_create_task(self, event):
        await event.edit("⚠️ ميزة إنشاء المهام قيد التطوير...")
    
    async def list_tasks(self, event):
        await event.edit("⚠️ ميزة عرض المهام قيد التطوير...")
    
    async def handle_task_action(self, event, data):
        await event.edit("⚠️ إدارة المهام قيد التطوير...")
    
    async def handle_task_message(self, event, state_data):
        await event.respond("⚠️ إنشاء المهام قيد التطوير...")
    
    async def show_settings_menu(self, event):
        await event.edit("⚠️ الإعدادات قيد التطوير...")
    
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
    
    async def handle_password_input(self, event, password: str, data: str):
        """Handle 2FA password input - placeholder"""
        await event.respond("⚠️ التحقق الثنائي قيد التطوير...")
    
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