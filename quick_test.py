#!/usr/bin/env python3
"""
Quick test for message receiving
"""
import asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from database.database import Database
from bot_package.config import API_ID, API_HASH

async def test_message_receiving():
    """Test if messages are received"""
    
    db = Database()
    sessions = db.get_all_authenticated_users()
    
    if not sessions:
        print("❌ لا توجد جلسات")
        return
    
    user_id, phone, session_string = sessions[0]
    print(f"🔗 الاتصال كـ {phone}...")
    
    client = TelegramClient(StringSession(session_string), int(API_ID), API_HASH)
    
    @client.on(events.NewMessage(incoming=True))
    async def message_handler(event):
        print(f"🔔 رسالة مستقبلة من Chat ID: {event.chat_id}")
        print(f"📝 النص: {event.text[:50] if event.text else 'بدون نص'}...")
        
        if event.chat_id == -1002289754739:
            print("🎯 *** هذه المحادثة المصدر! ***")
            print("🔄 سيتم توجيه الرسالة الآن...")
        else:
            print(f"ℹ️ محادثة أخرى (ليست المصدر)")
    
    await client.start()
    print("✅ متصل ومراقب للرسائل...")
    print("📝 أرسل رسالة في المحادثة المصدر الآن...")
    
    # Monitor for 20 seconds
    await asyncio.sleep(20)
    
    print("⏰ انتهت مدة المراقبة")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(test_message_receiving())