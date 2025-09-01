"""
معالج الرسائل المحسن
يحل مشكلة الاحتفاظ بحالة المستخدم بعد انتهاء العملية
"""

import logging
import time
from typing import Dict, Any, Optional, Callable
from telethon import events
from .state_manager import StateManager, StateType, create_temporary_state, create_persistent_state

logger = logging.getLogger(__name__)

class MessageHandler:
    """معالج الرسائل المحسن"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.state_manager = StateManager()
        self.setup_state_handlers()
        
    def setup_state_handlers(self):
        """إعداد معالجات الحالات"""
        # معالجات الحالات المؤقتة
        self.state_manager.set_state_handler('editing_audio_tag_', self.handle_audio_tag_edit)
        self.state_manager.set_state_handler('editing_char_', self.handle_character_edit)
        self.state_manager.set_state_handler('editing_rate_', self.handle_rate_edit)
        self.state_manager.set_state_handler('editing_forwarding_', self.handle_forwarding_edit)
        self.state_manager.set_state_handler('editing_sending_', self.handle_sending_edit)
        self.state_manager.set_state_handler('editing_signature_', self.handle_signature_edit)
        
        # معالجات الحالات المؤقتة للرفع
        self.state_manager.set_state_handler('awaiting_', self.handle_upload_state)
        
        # معالجات الحالات المؤقتة للنصوص
        self.state_manager.set_state_handler('watermark_text_input_', self.handle_watermark_text)
        self.state_manager.set_state_handler('watermark_image_input_', self.handle_watermark_image)
        
    async def handle_message(self, event):
        """معالجة الرسائل مع إدارة محسنة للحالة"""
        # تخطي الأوامر
        if event.text.startswith('/'):
            return
            
        user_id = event.sender_id
        message_text = event.text
        
        # تنظيف الحالات المنتهية الصلاحية
        self.state_manager.cleanup_expired_states()
        
        # التحقق من وجود حالة نشطة
        current_state = self.state_manager.get_user_state(user_id)
        
        if current_state:
            # معالجة الحالة النشطة
            await self._handle_active_state(event, current_state, message_text)
        else:
            # معالجة الرسالة كرسالة عادية
            await self._handle_normal_message(event, message_text)
    
    async def _handle_active_state(self, event, state: str, message_text: str):
        """معالجة الحالة النشطة"""
        user_id = event.sender_id
        
        try:
            # الحصول على معالج الحالة
            handler = self.state_manager.get_state_handler(state)
            
            if handler:
                # استدعاء المعالج المخصص
                await handler(event, state, message_text)
            else:
                # معالجة الحالات العامة
                await self._handle_general_state(event, state, message_text)
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الحالة النشطة للمستخدم {user_id}: {e}")
            await self._handle_state_error(event, state, e)
    
    async def _handle_general_state(self, event, state: str, message_text: str):
        """معالجة الحالات العامة"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        # معالجة الحالات المختلفة
        if state.startswith('editing_audio_tag_'):
            await self.handle_audio_tag_edit(event, state, message_text)
        elif state.startswith('editing_char_'):
            await self.handle_character_edit(event, state, message_text)
        elif state.startswith('editing_rate_'):
            await self.handle_rate_edit(event, state, message_text)
        elif state.startswith('editing_forwarding_'):
            await self.handle_forwarding_edit(event, state, message_text)
        elif state.startswith('editing_sending_'):
            await self.handle_sending_edit(event, state, message_text)
        elif state.startswith('editing_signature_'):
            await self.handle_signature_edit(event, state, message_text)
        elif state.startswith('awaiting_'):
            await self.handle_upload_state(event, state, message_text)
        elif state.startswith('watermark_text_input_'):
            await self.handle_watermark_text(event, state, message_text)
        elif state.startswith('watermark_image_input_'):
            await self.handle_watermark_image(event, state, message_text)
        else:
            # حالة غير معروفة - مسح الحالة
            logger.warning(f"حالة غير معروفة للمستخدم {user_id}: {state}")
            self.state_manager.clear_user_state(user_id)
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ في الحالة، تم إعادة تعيينها")
    
    async def _handle_normal_message(self, event, message_text: str):
        """معالجة الرسائل العادية"""
        # التحقق من النظام القديم للحالات
        state_data = self.bot.db.get_conversation_state(event.sender_id)
        
        if state_data:
            # معالجة الحالات القديمة
            await self._handle_legacy_state(event, state_data, message_text)
        else:
            # رسالة عادية - تجاهلها أو معالجتها حسب الحاجة
            logger.debug(f"رسالة عادية من المستخدم {event.sender_id}: {message_text[:50]}...")
    
    async def _handle_legacy_state(self, event, state_data, message_text: str):
        """معالجة الحالات القديمة"""
        state, data = state_data
        
        # معالجة حالات المصادقة
        if state in ['waiting_phone', 'waiting_code', 'waiting_password', 'waiting_session']:
            await self.bot.handle_auth_message(event, state_data)
        # معالجة حالات إنشاء المهام
        elif state in ['waiting_task_name', 'waiting_source_chat', 'waiting_target_chat']:
            await self.bot.handle_task_message(event, state_data)
        # معالجة حالات إضافة المصادر/الأهداف
        elif state in ['adding_source', 'adding_target']:
            await self.bot.handle_add_source_target(event, state_data)
        else:
            # حالات أخرى - مسح الحالة القديمة
            self.bot.db.clear_conversation_state(event.sender_id)
            await self.bot.edit_or_send_message(event, "❌ تم إعادة تعيين الحالة")
    
    async def _handle_state_error(self, event, state: str, error: Exception):
        """معالجة أخطاء الحالة"""
        user_id = event.sender_id
        
        # زيادة عدد المحاولات
        retry_count = self.state_manager.increment_retry(user_id)
        
        if retry_count >= 3:
            # تجاوز الحد الأقصى - مسح الحالة
            self.state_manager.clear_user_state(user_id)
            await self.bot.edit_or_send_message(
                event, 
                "❌ حدث خطأ متكرر، تم إعادة تعيين الحالة\nاضغط /start للعودة للقائمة الرئيسية"
            )
        else:
            # إعادة المحاولة
            await self.bot.edit_or_send_message(
                event, 
                f"❌ حدث خطأ، المحاولة {retry_count}/3\nيرجى المحاولة مرة أخرى"
            )
    
    # معالجات الحالات المخصصة
    async def handle_audio_tag_edit(self, event, state: str, message_text: str):
        """معالجة تعديل الوسوم الصوتية"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            tag_name = state.replace('editing_audio_tag_', '')
            task_id = user_data.get('task_id')
            new_template = message_text.strip()
            
            if not new_template:
                await self.bot.edit_or_send_message(event, "❌ لا يمكن أن يكون القالب فارغاً")
                return
            
            success = self.bot.db.update_audio_template_setting(task_id, tag_name, new_template)
            if success:
                await self.bot.edit_or_send_message(event, f"✅ تم تحديث قالب {tag_name} بنجاح")
                await self.bot.audio_template_settings(event, task_id)
            else:
                await self.bot.edit_or_send_message(event, "❌ فشل في تحديث القالب")
                
        except Exception as e:
            logger.error(f"خطأ في تحديث قالب الوسم الصوتي: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    async def handle_character_edit(self, event, state: str, message_text: str):
        """معالجة تعديل حدود الأحرف"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            task_id = user_data.get('task_id')
            
            if state == 'editing_char_min':
                await self._handle_char_min_edit(event, task_id, message_text)
            elif state == 'editing_char_max':
                await self._handle_char_max_edit(event, task_id, message_text)
            elif state == 'editing_char_range':
                # إدخال بالشكل "50-1000"
                try:
                    parts = message_text.replace('—', '-').split('-')
                    if len(parts) == 2:
                        min_chars = int(parts[0].strip())
                        max_chars = int(parts[1].strip())
                        if 1 <= min_chars <= 10000 and 1 <= max_chars <= 10000 and min_chars <= max_chars:
                            success = self.bot.db.update_character_limit_settings(
                                task_id,
                                min_chars=min_chars,
                                max_chars=max_chars,
                                use_range=True,
                                length_mode='range'
                            )
                            if success:
                                await self.bot.edit_or_send_message(event, f"✅ تم تحديث النطاق إلى من {min_chars} إلى {max_chars} حرف")
                                await self.bot._refresh_userbot_tasks(event.sender_id)
                            else:
                                await self.bot.edit_or_send_message(event, "❌ فشل في تحديث النطاق")
                        else:
                            await self.bot.edit_or_send_message(event, "❌ يرجى إدخال نطاق صحيح بين 1 و 10000 وبصيغة '50-1000'")
                    else:
                        await self.bot.edit_or_send_message(event, "❌ يرجى إدخال النطاق بصيغة '50-1000'")
                except Exception:
                    await self.bot.edit_or_send_message(event, "❌ يرجى إدخال النطاق بصيغة صحيحة مثل '50-1000'")
                
        except Exception as e:
            logger.error(f"خطأ في تعديل حدود الأحرف: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    async def _handle_char_min_edit(self, event, task_id: int, message_text: str):
        """معالجة تعديل الحد الأدنى للأحرف"""
        try:
            min_chars = int(message_text.strip())
            if 1 <= min_chars <= 10000:
                success = self.bot.db.update_character_limit_values(task_id, min_chars=min_chars)
                if success:
                    await self.bot.edit_or_send_message(event, f"✅ تم تحديث الحد الأدنى إلى {min_chars} حرف")
                    await self.bot._refresh_userbot_tasks(event.sender_id)
                else:
                    await self.bot.edit_or_send_message(event, "❌ فشل في تحديث الحد الأدنى")
            else:
                await self.bot.edit_or_send_message(event, "❌ يجب أن يكون الرقم بين 1 و 10000")
        except ValueError:
            await self.bot.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
    
    async def _handle_char_max_edit(self, event, task_id: int, message_text: str):
        """معالجة تعديل الحد الأقصى للأحرف"""
        try:
            max_chars = int(message_text.strip())
            if 1 <= max_chars <= 10000:
                success = self.bot.db.update_character_limit_values(task_id, max_chars=max_chars)
                if success:
                    await self.bot.edit_or_send_message(event, f"✅ تم تحديث الحد الأقصى إلى {max_chars} حرف")
                    await self.bot._refresh_userbot_tasks(event.sender_id)
                else:
                    await self.bot.edit_or_send_message(event, "❌ فشل في تحديث الحد الأقصى")
            else:
                await self.bot.edit_or_send_message(event, "❌ يجب أن يكون الرقم بين 1 و 10000")
        except ValueError:
            await self.bot.edit_or_send_message(event, "❌ يرجى إدخال رقم صحيح")
    
    async def handle_rate_edit(self, event, state: str, message_text: str):
        """معالجة تعديل حدود المعدل"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            task_id = user_data.get('task_id')
            
            if state == 'editing_rate_count':
                await self.bot.handle_edit_rate_count(event, task_id, message_text)
                await self.bot.send_rate_limit_settings(event, task_id)
            elif state == 'editing_rate_period':
                await self.bot.handle_edit_rate_period(event, task_id, message_text)
                await self.bot.send_rate_limit_settings(event, task_id)
                
        except Exception as e:
            logger.error(f"خطأ في تعديل حدود المعدل: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    async def handle_forwarding_edit(self, event, state: str, message_text: str):
        """معالجة تعديل تأخير التوجيه"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            task_id = user_data.get('task_id')
            await self.bot.handle_edit_forwarding_delay(event, task_id, message_text)
            await self.bot.send_forwarding_delay_settings(event, task_id)
        except Exception as e:
            logger.error(f"خطأ في تعديل تأخير التوجيه: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    async def handle_sending_edit(self, event, state: str, message_text: str):
        """معالجة تعديل فترات الإرسال"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            task_id = user_data.get('task_id')
            await self.bot.handle_edit_sending_interval(event, task_id, message_text)
            await self.bot.send_sending_interval_settings(event, task_id)
        except Exception as e:
            logger.error(f"خطأ في تعديل فترات الإرسال: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    async def handle_signature_edit(self, event, state: str, message_text: str):
        """معالجة تعديل توقيع المشرف"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            parts = state.split('_')
            if len(parts) >= 4:
                task_id = int(parts[2])
                admin_user_id = int(parts[3])
                source_chat_id = user_data.get('source_chat_id', '')
                
                if source_chat_id:
                    await self.bot.handle_signature_input(event, task_id, admin_user_id, source_chat_id)
                else:
                    await self.bot.edit_or_send_message(event, "❌ خطأ في تحديد المصدر")
            else:
                await self.bot.edit_or_send_message(event, "❌ خطأ في تحليل البيانات")
        except Exception as e:
            logger.error(f"خطأ في معالجة إدخال توقيع المشرف: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    async def handle_upload_state(self, event, state: str, message_text: str):
        """معالجة حالات الرفع"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            task_id = user_data.get('task_id')
            
            if state == 'awaiting_album_art_upload':
                await self._handle_album_art_upload(event, task_id)
            elif state == 'awaiting_intro_audio_upload':
                await self._handle_intro_audio_upload(event, task_id)
            elif state == 'awaiting_outro_audio_upload':
                await self._handle_outro_audio_upload(event, task_id)
                
        except Exception as e:
            logger.error(f"خطأ في رفع الملف: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ أثناء رفع الملف")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    async def _handle_album_art_upload(self, event, task_id: int):
        """معالجة رفع صورة الغلاف"""
        import os
        os.makedirs('album_art', exist_ok=True)
        file_path = None
        
        if event.message.photo or (event.message.document and 'image' in (event.message.document.mime_type or '')):
            file_path = f"album_art/album_art_{task_id}.jpg"
            await self.bot.bot.download_media(event.message, file=file_path)
        else:
            await self.bot.edit_or_send_message(event, "❌ يرجى إرسال صورة كصورة أو ملف.")
            return
            
        if file_path and os.path.exists(file_path):
            self.bot.db.set_album_art_settings(task_id, path=file_path, enabled=True)
            await self.bot.edit_or_send_message(event, "✅ تم حفظ صورة الغلاف")
            await self.bot.album_art_settings(event, task_id)
        else:
            await self.bot.edit_or_send_message(event, "❌ فشل في حفظ الصورة")
    
    async def _handle_intro_audio_upload(self, event, task_id: int):
        """معالجة رفع مقطع المقدمة"""
        import os
        os.makedirs('audio_segments', exist_ok=True)
        file_path = f"audio_segments/intro_{task_id}.mp3"
        
        if event.message.document and (event.message.document.mime_type or '').startswith('audio/'):
            await self.bot.bot.download_media(event.message, file=file_path)
            self.bot.db.set_audio_merge_settings(task_id, intro_path=file_path)
            await self.bot.edit_or_send_message(event, "✅ تم حفظ مقطع المقدمة")
            await self.bot.audio_merge_settings(event, task_id)
        else:
            await self.bot.edit_or_send_message(event, "❌ يرجى إرسال ملف صوتي.")
    
    async def _handle_outro_audio_upload(self, event, task_id: int):
        """معالجة رفع مقطع الخاتمة"""
        import os
        os.makedirs('audio_segments', exist_ok=True)
        file_path = f"audio_segments/outro_{task_id}.mp3"
        
        if event.message.document and (event.message.document.mime_type or '').startswith('audio/'):
            await self.bot.bot.download_media(event.message, file=file_path)
            self.bot.db.set_audio_merge_settings(task_id, outro_path=file_path)
            await self.bot.edit_or_send_message(event, "✅ تم حفظ مقطع الخاتمة")
            await self.bot.audio_merge_settings(event, task_id)
        else:
            await self.bot.edit_or_send_message(event, "❌ يرجى إرسال ملف صوتي.")
    
    async def handle_watermark_text(self, event, state: str, message_text: str):
        """معالجة إدخال نص العلامة المائية"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            task_id = user_data.get('task_id')
            await self.bot.handle_watermark_text_input(event, task_id)
        except Exception as e:
            logger.error(f"خطأ في معالجة إدخال نص العلامة المائية: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    async def handle_watermark_image(self, event, state: str, message_text: str):
        """معالجة إدخال صورة العلامة المائية"""
        user_id = event.sender_id
        user_data = self.state_manager.get_user_data(user_id)
        
        try:
            task_id = user_data.get('task_id')
            await self.bot.handle_watermark_image_input(event, task_id)
        except Exception as e:
            logger.error(f"خطأ في معالجة إدخال صورة العلامة المائية: {e}")
            await self.bot.edit_or_send_message(event, "❌ حدث خطأ، يرجى المحاولة مرة أخرى")
        finally:
            self.state_manager.clear_user_state(user_id)
    
    # دوال مساعدة لإدارة الحالات
    def set_temporary_state(self, user_id: int, state: str, data: Dict[str, Any] = None, timeout: float = 300):
        """تعيين حالة مؤقتة"""
        self.state_manager.set_user_state(
            user_id, state, data, 
            StateType.TEMPORARY, timeout
        )
    
    def set_persistent_state(self, user_id: int, state: str, data: Dict[str, Any] = None):
        """تعيين حالة دائمة"""
        self.state_manager.set_user_state(
            user_id, state, data, 
            StateType.PERSISTENT
        )
    
    def clear_state(self, user_id: int):
        """مسح حالة المستخدم"""
        self.state_manager.clear_user_state(user_id)
    
    def get_state_info(self, user_id: int):
        """الحصول على معلومات الحالة"""
        return self.state_manager.get_state_info(user_id)
    
    def get_all_states_info(self):
        """الحصول على معلومات جميع الحالات"""
        return self.state_manager.get_all_states_info()