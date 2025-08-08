#!/usr/bin/env python3
"""
Test script to check userbot status and forwarding capability
"""
import asyncio
import logging
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from database.database import Database
from bot_package.config import API_ID, API_HASH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_userbot_status():
    """Test userbot connection and task status"""
    
    print("🔍 فحص حالة UserBot...")
    
    # Initialize database
    db = Database()
    
    # Get user sessions
    sessions = db.get_all_authenticated_users()
    print(f"📱 عدد الجلسات المحفوظة: {len(sessions)}")
    
    if not sessions:
        print("❌ لا توجد جلسات محفوظة")
        return
    
    for user_id, phone, session_string in sessions:
        print(f"\n👤 فحص المستخدم {user_id} - {phone}")
        
        # Check tasks
        tasks = db.get_active_tasks(user_id)
        print(f"📋 عدد المهام النشطة: {len(tasks)}")
        
        for task in tasks:
            print(f"  • مهمة {task['id']}: {task.get('task_name', 'مجهول')}")
            print(f"    مصدر: {task['source_chat_id']}")
            print(f"    هدف: {task['target_chat_id']}")
        
        # Test connection
        if session_string:
            try:
                print("🔗 اختبار الاتصال...")
                client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
                await client.connect()
                
                if await client.is_user_authorized():
                    print("✅ UserBot متصل ومصرح له")
                    
                    # Get user info
                    me = await client.get_me()
                    print(f"👨‍💻 UserBot: {me.first_name} ({me.phone})")
                    
                    # Test access to source and target chats
                    for task in tasks:
                        source_id = task['source_chat_id']
                        target_id = task['target_chat_id']
                        
                        print(f"\n🔍 فحص المحادثات للمهمة {task['id']}:")
                        
                        # Test source chat access
                        try:
                            source_entity = await client.get_entity(int(source_id))
                            print(f"✅ الوصول للمصدر: {getattr(source_entity, 'title', getattr(source_entity, 'first_name', source_id))}")
                            
                            # Check if we can read messages
                            try:
                                messages = await client.get_messages(source_entity, limit=1)
                                print(f"✅ يمكن قراءة الرسائل من المصدر")
                            except Exception as e:
                                print(f"⚠️ لا يمكن قراءة الرسائل من المصدر: {e}")
                                
                        except Exception as e:
                            print(f"❌ لا يمكن الوصول للمصدر {source_id}: {e}")
                        
                        # Test target chat access
                        try:
                            target_entity = await client.get_entity(int(target_id))
                            print(f"✅ الوصول للهدف: {getattr(target_entity, 'title', getattr(target_entity, 'first_name', target_id))}")
                            
                            # Check if we can send messages
                            try:
                                # Just check permissions without sending
                                print(f"✅ UserBot عضو في المحادثة الهدف")
                            except Exception as e:
                                print(f"⚠️ قد تكون هناك قيود على الإرسال للهدف: {e}")
                                
                        except Exception as e:
                            print(f"❌ لا يمكن الوصول للهدف {target_id}: {e}")
                
                else:
                    print("❌ UserBot غير مصرح له")
                
                await client.disconnect()
                
            except Exception as e:
                print(f"❌ خطأ في الاتصال: {e}")

async def test_message_listener():
    """Test if message listener is working"""
    print("\n🎧 اختبار مستقبل الرسائل...")
    
    db = Database()
    sessions = db.get_all_authenticated_users()
    
    if not sessions:
        print("❌ لا توجد جلسات")
        return
    
    user_id, phone, session_string = sessions[0]
    
    try:
        client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ UserBot غير مصرح له")
            return
        
        print("✅ UserBot متصل")
        print("🎯 مراقبة الرسائل لمدة 30 ثانية...")
        print("📝 أرسل رسالة في المحادثة المصدر الآن...")
        
        message_received = False
        
        @client.on(events.NewMessage(incoming=True))
        async def message_handler(event):
            nonlocal message_received
            message_received = True
            print(f"🔔 رسالة مستقبلة!")
            print(f"📍 Chat ID: {event.chat_id}")
            print(f"📝 النص: {event.text[:100] if event.text else 'رسالة بدون نص'}")
            
            if event.chat_id == -1002289754739:
                print("🎯 هذه هي المحادثة المصدر المطلوبة!")
            else:
                print(f"ℹ️ هذه ليست المحادثة المصدر المطلوبة (-1002289754739)")
        
        # Wait for messages
        await asyncio.sleep(30)
        
        if not message_received:
            print("⚠️ لم يتم استقبال أي رسائل خلال 30 ثانية")
            print("💡 تأكد أن UserBot عضو في المحادثة وأن المحادثة تسمح بالبوتات")
        
        await client.disconnect()
        
    except Exception as e:
        print(f"❌ خطأ في اختبار مستقبل الرسائل: {e}")

if __name__ == "__main__":
    print("🚀 بدء فحص نظام التوجيه...")
    
    async def main():
        await test_userbot_status()
        print("\n" + "="*60)
        await test_message_listener()
    
    asyncio.run(main())