import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import PhoneNumberInvalidError, PhoneCodeInvalidError, SessionPasswordNeededError
from telegram_bot.config import API_ID, API_HASH
from database.database import Database

logger = logging.getLogger(__name__)

class TelegramAuthenticator:
    def __init__(self):
        self.db = Database()
        self.temp_client = None
        self.temp_phone = None
        self.temp_code = None
        
    async def send_verification_code(self, phone_number):
        """Send verification code to phone"""
        try:
            self.temp_client = TelegramClient(StringSession(), API_ID, API_HASH)
            await self.temp_client.connect()
            
            result = await self.temp_client.send_code_request(phone_number)
            self.temp_phone = phone_number
            
            logger.info(f"تم إرسال رمز التحقق إلى {phone_number}")
            return True, "تم إرسال رمز التحقق إلى هاتفك"
            
        except PhoneNumberInvalidError:
            return False, "رقم الهاتف غير صحيح"
        except Exception as e:
            logger.error(f"خطأ في إرسال رمز التحقق: {e}")
            return False, f"حدث خطأ: {str(e)}"
    
    async def verify_code(self, code, password=None):
        """Verify the code and authenticate user"""
        if not self.temp_client or not self.temp_phone:
            return False, "يرجى طلب رمز التحقق أولاً", None
        
        try:
            # Try to sign in with code
            await self.temp_client.sign_in(self.temp_phone, code)
            
        except SessionPasswordNeededError:
            if password:
                try:
                    await self.temp_client.sign_in(password=password)
                except Exception as e:
                    return False, "كلمة المرور غير صحيحة", None
            else:
                self.temp_code = code
                return False, "مطلوب كلمة مرور المصادقة الثنائية", "password_required"
        
        except PhoneCodeInvalidError:
            return False, "رمز التحقق غير صحيح", None
        except Exception as e:
            logger.error(f"خطأ في التحقق: {e}")
            return False, f"حدث خطأ: {str(e)}", None
        
        # Get session string
        try:
            session_string = self.temp_client.session.save()
            await self.temp_client.disconnect()
            
            # Save session to database
            self.db.save_user_session(self.temp_phone, session_string)
            
            logger.info(f"تم تسجيل الدخول بنجاح للرقم {self.temp_phone}")
            return True, "تم تسجيل الدخول بنجاح", session_string
            
        except Exception as e:
            logger.error(f"خطأ في حفظ الجلسة: {e}")
            return False, f"خطأ في حفظ الجلسة: {str(e)}", None
    
    async def verify_password(self, password):
        """Verify two-factor authentication password"""
        if not self.temp_client or not self.temp_phone or not self.temp_code:
            return False, "يرجى البدء من جديد", None
        
        try:
            # Sign in with the stored code first
            await self.temp_client.sign_in(self.temp_phone, self.temp_code)
        except SessionPasswordNeededError:
            try:
                await self.temp_client.sign_in(password=password)
            except Exception as e:
                return False, "كلمة المرور غير صحيحة", None
        except Exception as e:
            logger.error(f"خطأ في التحقق من كلمة المرور: {e}")
            return False, f"حدث خطأ: {str(e)}", None
        
        # Get session string
        try:
            session_string = self.temp_client.session.save()
            await self.temp_client.disconnect()
            
            # Save session to database
            self.db.save_user_session(self.temp_phone, session_string)
            
            logger.info(f"تم تسجيل الدخول بنجاح بالمصادقة الثنائية للرقم {self.temp_phone}")
            return True, "تم تسجيل الدخول بنجاح", session_string
            
        except Exception as e:
            logger.error(f"خطأ في حفظ الجلسة: {e}")
            return False, f"خطأ في حفظ الجلسة: {str(e)}", None
    
    def get_session_by_phone(self, phone_number):
        """Get existing session for phone number"""
        return self.db.get_user_session(phone_number)
    
    def cleanup(self):
        """Clean up temporary client"""
        self.temp_client = None
        self.temp_phone = None
        self.temp_code = None