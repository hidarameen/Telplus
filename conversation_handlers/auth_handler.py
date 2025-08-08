"""
Authentication Handler for Telegram Login
"""
import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telethon import TelegramClient
from telethon.errors import PhoneCodeInvalidError, PhoneNumberInvalidError, SessionPasswordNeededError
from database.database import Database
from userbot_service.userbot import userbot_instance
from bot_package.config import API_ID, API_HASH
import json

logger = logging.getLogger(__name__)

class AuthHandler:
    def __init__(self):
        self.db = Database()
    
    async def start_phone_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start phone number authentication"""
        user_id = update.effective_user.id
        
        # Set conversation state
        self.db.set_conversation_state(user_id, 'waiting_phone')
        
        keyboard = [
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_auth")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "📱 تسجيل الدخول إلى تليجرام\n\n"
            "🔐 لتتمكن من استخدام ميزة التوجيه التلقائي، نحتاج لتسجيل دخولك إلى حساب تليجرام الخاص بك.\n\n"
            "📞 أرسل رقم هاتفك بالتنسيق الدولي:\n"
            "مثال: +966501234567\n"
            "أو: +201234567890\n\n"
            "⚠️ تأكد من إدخال الرقم بشكل صحيح مع رمز البلد",
            reply_markup=reply_markup
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """Handle authentication messages"""
        user_id = update.effective_user.id
        state_data = self.db.get_conversation_state(user_id)
        
        if not state_data:
            return False
        
        state, data = state_data
        message_text = update.message.text.strip()
        
        try:
            if state == 'waiting_phone':
                await self._handle_phone_input(update, context, message_text)
            elif state == 'waiting_code':
                await self._handle_code_input(update, context, message_text, data)
            elif state == 'waiting_password':
                await self._handle_password_input(update, context, message_text, data)
            else:
                return False
        except Exception as e:
            logger.error(f"خطأ في التسجيل للمستخدم {user_id}: {e}")
            await update.message.reply_text(
                "❌ حدث خطأ أثناء التسجيل. حاول مرة أخرى.\n"
                "اضغط /start للبدء من جديد."
            )
            self.db.clear_conversation_state(user_id)
        
        return True
    
    async def _handle_phone_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, phone: str):
        """Handle phone number input"""
        user_id = update.effective_user.id
        
        # Validate phone number format
        if not phone.startswith('+') or len(phone) < 10:
            keyboard = [
                [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_auth")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                "❌ تنسيق رقم الهاتف غير صحيح\n\n"
                "📞 يجب أن يبدأ الرقم بـ + ويكون بالتنسيق الدولي\n"
                "مثال: +966501234567\n\n"
                "أرسل رقم الهاتف مرة أخرى:",
                reply_markup=reply_markup
            )
            return
        
        # Create temporary Telegram client
        try:
            temp_client = TelegramClient(':memory:', API_ID, API_HASH)
            await temp_client.connect()
            
            # Send code request
            sent_code = await temp_client.send_code_request(phone)
            
            # Store data for next step
            auth_data = {
                'phone': phone,
                'phone_code_hash': sent_code.phone_code_hash
            }
            self.db.set_conversation_state(user_id, 'waiting_code', json.dumps(auth_data))
            
            keyboard = [
                [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_auth")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✅ تم إرسال رمز التحقق إلى {phone}\n\n"
                "🔢 أرسل الرمز المكون من 5 أرقام:\n"
                "مثال: 12345\n\n"
                "⏰ انتظر بضع ثواني حتى يصل الرمز",
                reply_markup=reply_markup
            )
            
            await temp_client.disconnect()
            
        except PhoneNumberInvalidError:
            await update.message.reply_text(
                "❌ رقم الهاتف غير صحيح\n\n"
                "تأكد من:\n"
                "• إدخال رقم هاتف مسجل في تليجرام\n"
                "• التنسيق الدولي الصحيح مع رمز البلد\n\n"
                "أرسل رقم الهاتف مرة أخرى:"
            )
        except Exception as e:
            logger.error(f"خطأ في إرسال الرمز: {e}")
            await update.message.reply_text(
                "❌ حدث خطأ في إرسال رمز التحقق\n"
                "حاول مرة أخرى بعد قليل"
            )
            self.db.clear_conversation_state(user_id)
    
    async def _handle_code_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE, 
                                code: str, data: str):
        """Handle verification code input"""
        user_id = update.effective_user.id
        
        # Validate code format
        if not code.isdigit() or len(code) != 5:
            await update.message.reply_text(
                "❌ تنسيق الرمز غير صحيح\n\n"
                "🔢 أرسل الرمز المكون من 5 أرقام بدون مسافات\n"
                "مثال: 12345"
            )
            return
        
        try:
            auth_data = json.loads(data)
            phone = auth_data['phone']
            phone_code_hash = auth_data['phone_code_hash']
            
            # Create client and sign in
            temp_client = TelegramClient(':memory:', API_ID, API_HASH)
            await temp_client.connect()
            
            try:
                # Try to sign in
                result = await temp_client.sign_in(phone, code, phone_code_hash=phone_code_hash)
                
                # Get session string
                session_string = temp_client.session.save()
                
                # Save session to database
                self.db.save_user_session(user_id, phone, session_string)
                self.db.clear_conversation_state(user_id)
                
                # Start userbot with this session
                await userbot_instance.start_with_session(user_id, session_string)
                
                keyboard = [
                    [InlineKeyboardButton("📝 إدارة مهام التوجيه", callback_data="manage_tasks")],
                    [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"🎉 تم تسجيل الدخول بنجاح!\n\n"
                    f"👋 مرحباً {result.first_name}!\n"
                    f"✅ تم ربط حسابك بنجاح\n\n"
                    f"🚀 يمكنك الآن إنشاء مهام التوجيه التلقائي",
                    reply_markup=reply_markup
                )
                
                await temp_client.disconnect()
                
            except SessionPasswordNeededError:
                # 2FA is enabled, ask for password
                auth_data['session_client'] = temp_client.session.save()
                self.db.set_conversation_state(user_id, 'waiting_password', json.dumps(auth_data))
                
                keyboard = [
                    [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_auth")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    "🔐 التحقق الثنائي مفعل على حسابك\n\n"
                    "🗝️ أرسل كلمة المرور الخاصة بالتحقق الثنائي:",
                    reply_markup=reply_markup
                )
                
        except PhoneCodeInvalidError:
            await update.message.reply_text(
                "❌ الرمز غير صحيح\n\n"
                "🔢 تأكد من إدخال الرمز بشكل صحيح\n"
                "أرسل الرمز مرة أخرى:"
            )
        except Exception as e:
            logger.error(f"خطأ في التحقق من الرمز: {e}")
            await update.message.reply_text(
                "❌ حدث خطأ في التحقق من الرمز\n"
                "حاول مرة أخرى"
            )
    
    async def _handle_password_input(self, update: Update, context: ContextTypes.DEFAULT_TYPE,
                                   password: str, data: str):
        """Handle 2FA password input"""
        user_id = update.effective_user.id
        
        try:
            auth_data = json.loads(data)
            phone = auth_data['phone']
            session_data = auth_data['session_client']
            
            # Create client with existing session
            temp_client = TelegramClient(':memory:', API_ID, API_HASH)
            temp_client.session.load(session_data)
            await temp_client.connect()
            
            # Try to complete sign in with password
            result = await temp_client.sign_in(password=password)
            
            # Get final session string
            session_string = temp_client.session.save()
            
            # Save session to database
            self.db.save_user_session(user_id, phone, session_string)
            self.db.clear_conversation_state(user_id)
            
            # Start userbot with this session
            await userbot_instance.start_with_session(user_id, session_string)
            
            keyboard = [
                [InlineKeyboardButton("📝 إدارة مهام التوجيه", callback_data="manage_tasks")],
                [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"🎉 تم تسجيل الدخول بنجاح!\n\n"
                f"👋 مرحباً {result.first_name}!\n"
                f"✅ تم ربط حسابك بنجاح\n\n"
                f"🚀 يمكنك الآن إنشاء مهام التوجيه التلقائي",
                reply_markup=reply_markup
            )
            
            await temp_client.disconnect()
            
        except Exception as e:
            logger.error(f"خطأ في كلمة المرور: {e}")
            await update.message.reply_text(
                "❌ كلمة المرور غير صحيحة\n\n"
                "🗝️ أرسل كلمة مرور التحقق الثنائي مرة أخرى:"
            )
    
    async def cancel_auth(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Cancel authentication process"""
        user_id = update.effective_user.id
        self.db.clear_conversation_state(user_id)
        
        keyboard = [
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "❌ تم إلغاء عملية تسجيل الدخول\n\n"
            "يمكنك المحاولة مرة أخرى في أي وقت",
            reply_markup=reply_markup
        )