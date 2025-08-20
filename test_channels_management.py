#!/usr/bin/env python3
"""
اختبار شامل لإدارة القنوات
"""

import asyncio
import sys
import os

# إضافة المسار للوحدات
sys.path.append(os.path.join(os.path.dirname(__file__), 'bot_package'))
sys.path.append(os.path.join(os.path.dirname(__file__), 'database'))

from database.database import Database
from database.channels_db import ChannelsDatabase
from channels_management import ChannelsManagement
from telethon import Button

class MockEvent:
    def __init__(self, sender_id=6556918772, data=None):
        self.sender_id = sender_id
        self.data = data.encode('utf-8') if data else b''
        self.chat_id = 123456789
        self.is_private = True
        
    async def answer(self, text):
        print(f"📤 إجابة: {text}")
        return MockMessage()
    
    async def respond(self, text, buttons=None):
        print(f"📤 رد: {text}")
        if buttons:
            print(f"🔘 الأزرار: {len(buttons)} صفوف")
        return MockMessage()

class MockMessage:
    def __init__(self):
        self.id = 12345

class MockBot:
    def __init__(self):
        self.db = Database()
        self.user_messages = {}
        
    async def edit_or_send_message(self, event, text, buttons=None):
        print(f"📝 رسالة: {text}")
        if buttons:
            print(f"🔘 الأزرار: {len(buttons)} صفوف")
            for i, row in enumerate(buttons):
                for j, button in enumerate(row):
                    print(f"  [{i}][{j}]: {button.text} -> {button.data.decode()}")

class MockChannelsManagement(ChannelsManagement):
    def __init__(self, bot):
        super().__init__(bot)
        # Override database methods for testing
        self.db.get_user_channels = self.mock_get_user_channels
        self.db.add_channel = self.mock_add_channel
        self.db.get_channel_info = self.mock_get_channel_info
        self.db.delete_channel = self.mock_delete_channel
        self.db.update_channel_info = self.mock_update_channel_info
        self.db.is_user_authenticated = lambda user_id: True
        self.db.set_conversation_state = lambda user_id, state, data: None
        self.db.get_conversation_state = lambda user_id: None
        self.db.clear_conversation_state = lambda user_id: None
    
    def mock_get_user_channels(self, user_id):
        """Mock user channels for testing"""
        return [
            {
                'chat_id': -1001234567890,
                'chat_name': 'قناة الأخبار',
                'username': 'news_channel',
                'is_admin': True,
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00'
            },
            {
                'chat_id': -1001234567891,
                'chat_name': 'قناة التكنولوجيا',
                'username': 'tech_channel',
                'is_admin': False,
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00'
            },
            {
                'chat_id': -1001234567892,
                'chat_name': 'قناة الرياضة',
                'username': 'sports_channel',
                'is_admin': True,
                'created_at': '2024-01-01 00:00:00',
                'updated_at': '2024-01-01 00:00:00'
            }
        ]
    
    def mock_add_channel(self, user_id, chat_id, chat_name, username=None, is_admin=False):
        """Mock add channel"""
        print(f"✅ تم إضافة القناة: {chat_name} (ID: {chat_id}, Admin: {is_admin})")
        return True
    
    def mock_get_channel_info(self, chat_id, user_id):
        """Mock get channel info"""
        channels = self.mock_get_user_channels(user_id)
        for channel in channels:
            if channel['chat_id'] == chat_id:
                return channel
        return None
    
    def mock_delete_channel(self, chat_id, user_id):
        """Mock delete channel"""
        print(f"✅ تم حذف القناة: {chat_id}")
        return True
    
    def mock_update_channel_info(self, chat_id, user_id, updates):
        """Mock update channel info"""
        print(f"✅ تم تحديث معلومات القناة: {chat_id} - {updates}")
        return True

async def test_channels_menu():
    """اختبار قائمة إدارة القنوات"""
    print("📺 اختبار قائمة إدارة القنوات")
    print("=" * 50)
    
    bot = MockBot()
    channels_mgmt = MockChannelsManagement(bot)
    event = MockEvent()
    
    await channels_mgmt.show_channels_menu(event)
    
    print("\n✅ تم الانتهاء من اختبار قائمة إدارة القنوات")

async def test_add_channel():
    """اختبار إضافة قناة"""
    print("\n➕ اختبار إضافة قناة")
    print("=" * 50)
    
    bot = MockBot()
    channels_mgmt = MockChannelsManagement(bot)
    event = MockEvent()
    
    await channels_mgmt.start_add_channel(event)
    
    print("\n✅ تم الانتهاء من اختبار إضافة قناة")

async def test_add_multiple_channels():
    """اختبار إضافة عدة قنوات"""
    print("\n📤 اختبار إضافة عدة قنوات")
    print("=" * 50)
    
    bot = MockBot()
    channels_mgmt = MockChannelsManagement(bot)
    event = MockEvent()
    
    await channels_mgmt.start_add_multiple_channels(event)
    
    print("\n✅ تم الانتهاء من اختبار إضافة عدة قنوات")

async def test_list_channels():
    """اختبار قائمة القنوات"""
    print("\n📋 اختبار قائمة القنوات")
    print("=" * 50)
    
    bot = MockBot()
    channels_mgmt = MockChannelsManagement(bot)
    event = MockEvent()
    
    await channels_mgmt.list_channels(event)
    
    print("\n✅ تم الانتهاء من اختبار قائمة القنوات")

async def test_edit_channel():
    """اختبار تعديل القناة"""
    print("\n✏️ اختبار تعديل القناة")
    print("=" * 50)
    
    bot = MockBot()
    channels_mgmt = MockChannelsManagement(bot)
    event = MockEvent()
    
    # Test with existing channel
    await channels_mgmt.edit_channel(event, -1001234567890)
    
    print("\n✅ تم الانتهاء من اختبار تعديل القناة")

async def test_delete_channel():
    """اختبار حذف القناة"""
    print("\n🗑️ اختبار حذف القناة")
    print("=" * 50)
    
    bot = MockBot()
    channels_mgmt = MockChannelsManagement(bot)
    event = MockEvent()
    
    # Test with existing channel
    await channels_mgmt.delete_channel(event, -1001234567890)
    
    print("\n✅ تم الانتهاء من اختبار حذف القناة")

async def test_channel_selection():
    """اختبار اختيار القنوات للمصادر والأهداف"""
    print("\n📺 اختبار اختيار القنوات")
    print("=" * 50)
    
    bot = MockBot()
    channels_mgmt = MockChannelsManagement(bot)
    event = MockEvent()
    
    # Test source selection
    await channels_mgmt.show_channel_selection(event, 7, "مصدر")
    
    print("\n")
    
    # Test target selection
    await channels_mgmt.show_channel_selection(event, 7, "هدف")
    
    print("\n✅ تم الانتهاء من اختبار اختيار القنوات")

async def test_channels_database():
    """اختبار قاعدة بيانات القنوات"""
    print("\n🗄️ اختبار قاعدة بيانات القنوات")
    print("=" * 50)
    
    db = Database()
    channels_db = ChannelsDatabase(db)
    user_id = 6556918772
    
    # Test adding channel
    print("🔍 اختبار إضافة قناة:")
    success = channels_db.add_channel(user_id, -1001234567890, "قناة الاختبار", "test_channel", True)
    print(f"✅ إضافة قناة: {success}")
    
    # Test getting user channels
    print("\n🔍 اختبار الحصول على قنوات المستخدم:")
    channels = channels_db.get_user_channels(user_id)
    print(f"✅ عدد القنوات: {len(channels)}")
    for channel in channels:
        print(f"  - {channel['chat_name']} (ID: {channel['chat_id']}, Admin: {channel['is_admin']})")
    
    # Test getting channel info
    print("\n🔍 اختبار الحصول على معلومات قناة:")
    channel_info = channels_db.get_channel_info(-1001234567890, user_id)
    if channel_info:
        print(f"✅ معلومات القناة: {channel_info['chat_name']}")
    else:
        print("❌ لم يتم العثور على القناة")
    
    # Test getting channels count
    print("\n🔍 اختبار إحصائيات القنوات:")
    stats = channels_db.get_channels_count(user_id)
    print(f"✅ الإحصائيات: {stats}")
    
    # Test search channels
    print("\n🔍 اختبار البحث في القنوات:")
    search_results = channels_db.search_channels(user_id, "اختبار")
    print(f"✅ نتائج البحث: {len(search_results)} قناة")
    
    print("\n✅ تم الانتهاء من اختبار قاعدة البيانات")

if __name__ == "__main__":
    print("📺 اختبار شامل لإدارة القنوات")
    print("=" * 60)
    
    # تشغيل الاختبارات
    asyncio.run(test_channels_database())
    asyncio.run(test_channels_menu())
    asyncio.run(test_add_channel())
    asyncio.run(test_add_multiple_channels())
    asyncio.run(test_list_channels())
    asyncio.run(test_edit_channel())
    asyncio.run(test_delete_channel())
    asyncio.run(test_channel_selection())
    
    print("\n🎉 تم الانتهاء من جميع اختبارات إدارة القنوات!")