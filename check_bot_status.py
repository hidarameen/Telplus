#!/usr/bin/env python3
"""
Check bot status and permissions
"""
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from bot_package.config import BOT_TOKEN, API_ID, API_HASH
import aiohttp

async def check_bot_info():
    """Check basic bot information"""
    print("🤖 فحص معلومات البوت...")
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getMe"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                result = await response.json()
                
                if result.get('ok'):
                    bot_info = result['result']
                    print(f"✅ معلومات البوت:")
                    print(f"   الاسم: {bot_info.get('first_name', 'غير محدد')}")
                    print(f"   المعرف: @{bot_info.get('username', 'غير محدد')}")
                    print(f"   المعرف الرقمي: {bot_info.get('id', 'غير محدد')}")
                    print(f"   يمكن أن ينضم للمجموعات: {bot_info.get('can_join_groups', False)}")
                    print(f"   يمكن أن يقرأ الرسائل: {bot_info.get('can_read_all_group_messages', False)}")
                    print(f"   يدعم الويب هوك: {bot_info.get('supports_inline_queries', False)}")
                    return bot_info
                else:
                    print(f"❌ فشل في الحصول على معلومات البوت: {result.get('description', 'خطأ غير معروف')}")
                    return None
                    
    except Exception as e:
        print(f"❌ خطأ في فحص معلومات البوت: {e}")
        return None

async def check_bot_permissions(chat_id: str):
    """Check bot permissions in a specific chat"""
    print(f"\n🔧 فحص صلاحيات البوت في القناة {chat_id}...")
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember"
        payload = {
            "chat_id": chat_id,
            "user_id": BOT_TOKEN.split(':')[0] if ':' in BOT_TOKEN else None
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get('ok'):
                    member = result['result']
                    status = member.get('status', '')
                    
                    print(f"✅ حالة البوت في القناة: {status}")
                    
                    if status == 'creator':
                        print("   🎯 البوت هو مالك القناة")
                        return True
                    elif status == 'administrator':
                        print("   👑 البوت هو مشرف في القناة")
                        permissions = member.get('permissions', {})
                        print(f"   الصلاحيات:")
                        for perm, value in permissions.items():
                            print(f"     {perm}: {value}")
                        return True
                    elif status == 'member':
                        print("   👤 البوت هو عضو في القناة")
                        can_post = member.get('can_post_messages', False)
                        print(f"   يمكن النشر: {can_post}")
                        return can_post
                    elif status == 'left':
                        print("   🚪 البوت غادر القناة")
                        return False
                    elif status == 'kicked':
                        print("   🚫 البوت محظور من القناة")
                        return False
                    else:
                        print(f"   ❓ حالة غير معروفة: {status}")
                        return False
                else:
                    error_code = result.get('error_code', 'unknown')
                    error_desc = result.get('description', 'unknown error')
                    print(f"❌ فشل في فحص الصلاحيات: {error_code} - {error_desc}")
                    return False
                    
    except Exception as e:
        print(f"❌ خطأ في فحص الصلاحيات: {e}")
        return False

async def test_bot_actions(chat_id: str):
    """Test basic bot actions"""
    print(f"\n🧪 اختبار إجراءات البوت في القناة {chat_id}...")
    
    try:
        # Test sending a message
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": "🧪 رسالة اختبار من البوت - سيتم حذفها تلقائياً"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get('ok'):
                    message_id = result['result']['message_id']
                    print(f"✅ تم إرسال رسالة اختبار بنجاح (ID: {message_id})")
                    
                    # Try to delete the test message
                    delete_url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
                    delete_payload = {
                        "chat_id": chat_id,
                        "message_id": message_id
                    }
                    
                    async with session.post(delete_url, json=delete_payload) as delete_response:
                        delete_result = await delete_response.json()
                        if delete_result.get('ok'):
                            print("✅ تم حذف رسالة الاختبار بنجاح")
                        else:
                            print("⚠️ لم يتم حذف رسالة الاختبار")
                    
                    return True
                else:
                    error_code = result.get('error_code', 'unknown')
                    error_desc = result.get('description', 'unknown error')
                    print(f"❌ فشل في إرسال رسالة الاختبار: {error_code} - {error_desc}")
                    return False
                    
    except Exception as e:
        print(f"❌ خطأ في اختبار الإجراءات: {e}")
        return False

async def check_chat_info(chat_id: str):
    """Get information about the chat"""
    print(f"\n📋 معلومات القناة {chat_id}...")
    
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChat"
        payload = {"chat_id": chat_id}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload) as response:
                result = await response.json()
                
                if result.get('ok'):
                    chat_info = result['result']
                    chat_type = chat_info.get('type', 'unknown')
                    title = chat_info.get('title', chat_info.get('first_name', 'غير محدد'))
                    
                    print(f"✅ معلومات القناة:")
                    print(f"   النوع: {chat_type}")
                    print(f"   الاسم: {title}")
                    print(f"   المعرف: @{chat_info.get('username', 'غير محدد')}")
                    print(f"   المعرف الرقمي: {chat_info.get('id', 'غير محدد')}")
                    
                    if chat_type == 'channel':
                        print(f"   عدد الأعضاء: {chat_info.get('member_count', 'غير محدد')}")
                        print(f"   عدد المشتركين: {chat_info.get('subscriber_count', 'غير محدد')}")
                    
                    return chat_info
                else:
                    error_code = result.get('error_code', 'unknown')
                    error_desc = result.get('description', 'unknown error')
                    print(f"❌ فشل في الحصول على معلومات القناة: {error_code} - {error_desc}")
                    return None
                    
    except Exception as e:
        print(f"❌ خطأ في فحص معلومات القناة: {e}")
        return None

async def main():
    """Main function"""
    print("🚀 فحص حالة البوت وصلاحياته")
    print("=" * 50)
    
    # Check bot info
    bot_info = await check_bot_info()
    if not bot_info:
        print("❌ لا يمكن الحصول على معلومات البوت. تأكد من صحة BOT_TOKEN")
        return
    
    # Get chat ID from user
    chat_id = input("\nأدخل معرف القناة (مثال: -1001234567890 أو @channel_name): ").strip()
    
    if not chat_id:
        print("❌ يجب إدخال معرف القناة")
        return
    
    # Check chat info
    chat_info = await check_chat_info(chat_id)
    if not chat_info:
        print("❌ لا يمكن الوصول للقناة. تأكد من صحة المعرف")
        return
    
    # Check bot permissions
    has_permissions = await check_bot_permissions(chat_id)
    
    if has_permissions:
        print("\n✅ البوت لديه صلاحيات كافية في القناة")
        
        # Test bot actions
        test_success = await test_bot_actions(chat_id)
        
        if test_success:
            print("\n🎉 البوت يعمل بشكل صحيح!")
        else:
            print("\n⚠️ البوت لديه صلاحيات لكن هناك مشكلة في الإجراءات")
    else:
        print("\n❌ البوت ليس لديه صلاحيات كافية في القناة")
        print("💡 الحلول:")
        print("   1. أضف البوت للقناة")
        print("   2. امنح البوت صلاحية النشر")
        print("   3. اجعل البوت مشرف في القناة")
    
    print("\n" + "=" * 50)
    print("✅ انتهى فحص حالة البوت")

if __name__ == "__main__":
    asyncio.run(main())