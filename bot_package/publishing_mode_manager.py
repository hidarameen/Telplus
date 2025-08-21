"""
مدير وضع النشر المحسن
يحل مشاكل زر تبديل الوضع وعدم عمل التوجيه عند الموافقة
"""

import logging
import json
import asyncio
from typing import Dict, List, Optional, Any
from telethon.tl.custom import Button
from telethon import events

logger = logging.getLogger(__name__)

class PublishingModeManager:
    """مدير وضع النشر المحسن"""
    
    def __init__(self, bot_instance):
        self.bot = bot_instance
        self.db = bot_instance.db
        
    async def show_publishing_mode_settings(self, event, task_id: int):
        """عرض إعدادات وضع النشر"""
        try:
            user_id = event.sender_id
            task = self.db.get_task(task_id, user_id)
            
            if not task:
                await self.bot.safe_answer(event, "❌ المهمة غير موجودة")
                return
                
            task_name = task.get('task_name', 'مهمة بدون اسم')
            
            # الحصول على وضع النشر من إعدادات التوجيه
            forwarding_settings = self.db.get_forwarding_settings(task_id)
            current_mode = forwarding_settings.get('publishing_mode', 'auto')
            
            # نصوص الحالة
            status_text = {
                'auto': '🟢 تلقائي - يتم إرسال الرسائل فوراً',
                'manual': '🟡 يدوي - يتطلب موافقة قبل الإرسال'
            }
            
            # الأزرار
            buttons = [
                [Button.inline("🔄 تبديل الوضع", f"toggle_publishing_mode_{task_id}")],
                [Button.inline("📋 الرسائل المعلقة", f"show_pending_messages_{task_id}")],
                [Button.inline("🔙 رجوع للمميزات المتقدمة", f"advanced_features_{task_id}")]
            ]
            
            # معلومات إضافية للحالة اليدوية
            additional_info = ""
            if current_mode == 'manual':
                pending_count = self.db.get_pending_messages_count(user_id)
                if pending_count > 0:
                    additional_info = f"\n\n📋 الرسائل المعلقة: {pending_count} رسالة في انتظار الموافقة"
                else:
                    additional_info = "\n\n📋 لا توجد رسائل معلقة حالياً"
            
            # نص الرسالة
            message_text = (
                f"📋 **وضع النشر للمهمة: {task_name}**\n\n"
                f"📊 **الوضع الحالي:** {status_text.get(current_mode, 'غير معروف')}\n\n"
                f"📝 **شرح الأوضاع:**\n"
                f"🟢 **تلقائي:** الرسائل تُرسل فوراً دون تدخل\n"
                f"🟡 **يدوي:** الرسائل تُرسل لك للمراجعة والموافقة{additional_info}\n\n"
                f"⚙️ **الخيارات المتاحة:**\n"
                f"• 🔄 تبديل الوضع\n"
                f"• 📋 عرض الرسائل المعلقة\n"
                f"• 🔙 العودة للمميزات المتقدمة"
            )
            
            await self.bot.edit_or_send_message(event, message_text, buttons=buttons)
            
        except Exception as e:
            logger.error(f"خطأ في عرض إعدادات وضع النشر: {e}")
            await self.bot.safe_answer(event, "❌ حدث خطأ في عرض الإعدادات")
    
    async def toggle_publishing_mode(self, event, task_id: int):
        """تبديل وضع النشر بين تلقائي ويدوي"""
        try:
            user_id = event.sender_id
            task = self.db.get_task(task_id, user_id)
            
            if not task:
                await self.bot.safe_answer(event, "❌ المهمة غير موجودة")
                return
                
            # الحصول على الوضع الحالي
            forwarding_settings = self.db.get_forwarding_settings(task_id)
            current_mode = forwarding_settings.get('publishing_mode', 'auto')
            new_mode = 'manual' if current_mode == 'auto' else 'auto'
            
            # تحديث الوضع في قاعدة البيانات
            success = self.db.update_task_publishing_mode(task_id, new_mode)
            
            if success:
                mode_names = {
                    'auto': 'تلقائي',
                    'manual': 'يدوي'
                }
                
                # رسالة التأكيد
                await self.bot.safe_answer(event, f"✅ تم تغيير وضع النشر إلى: {mode_names[new_mode]}")
                
                # تحديث UserBot
                await self.bot._refresh_userbot_tasks(user_id)
                
                # إعادة عرض الإعدادات
                await self.show_publishing_mode_settings(event, task_id)
                
                logger.info(f"✅ تم تغيير وضع النشر للمهمة {task_id} إلى {new_mode} بواسطة المستخدم {user_id}")
            else:
                await self.bot.safe_answer(event, "❌ فشل في تغيير وضع النشر")
                logger.error(f"❌ فشل في تغيير وضع النشر للمهمة {task_id}")
                
        except Exception as e:
            logger.error(f"خطأ في تبديل وضع النشر: {e}")
            await self.bot.safe_answer(event, "❌ حدث خطأ في تبديل الوضع")
    
    async def show_pending_messages(self, event, task_id: int):
        """عرض الرسائل المعلقة"""
        try:
            user_id = event.sender_id
            task = self.db.get_task(task_id, user_id)
            
            if not task:
                await self.bot.safe_answer(event, "❌ المهمة غير موجودة")
                return
            
            # الحصول على الرسائل المعلقة
            pending_messages = self.db.get_pending_messages(user_id, task_id)
            
            if not pending_messages:
                message_text = (
                    f"📋 **الرسائل المعلقة للمهمة: {task.get('task_name', 'مهمة بدون اسم')}**\n\n"
                    f"✅ لا توجد رسائل معلقة حالياً"
                )
                buttons = [
                    [Button.inline("🔙 رجوع لإعدادات وضع النشر", f"publishing_mode_{task_id}")]
                ]
            else:
                message_text = (
                    f"📋 **الرسائل المعلقة للمهمة: {task.get('task_name', 'مهمة بدون اسم')}**\n\n"
                    f"📊 عدد الرسائل: {len(pending_messages)}\n\n"
                    f"اختر رسالة للمراجعة:"
                )
                
                buttons = []
                for msg in pending_messages[:5]:  # عرض أول 5 رسائل فقط
                    try:
                        msg_data = json.loads(msg['message_data'])
                        preview = msg_data.get('text', 'رسالة بدون نص')[:50]
                        buttons.append([
                            Button.inline(
                                f"📝 {preview}...", 
                                f"show_pending_details_{msg['id']}"
                            )
                        ])
                    except:
                        buttons.append([
                            Button.inline(
                                f"📝 رسالة {msg['id']}", 
                                f"show_pending_details_{msg['id']}"
                            )
                        ])
                
                buttons.append([Button.inline("🔙 رجوع لإعدادات وضع النشر", f"publishing_mode_{task_id}")])
            
            await self.bot.edit_or_send_message(event, message_text, buttons=buttons)
            
        except Exception as e:
            logger.error(f"خطأ في عرض الرسائل المعلقة: {e}")
            await self.bot.safe_answer(event, "❌ حدث خطأ في عرض الرسائل المعلقة")
    
    async def show_pending_message_details(self, event, pending_id: int):
        """عرض تفاصيل الرسالة المعلقة"""
        try:
            user_id = event.sender_id
            
            # الحصول على تفاصيل الرسالة المعلقة
            pending_message = self.db.get_pending_message(pending_id)
            if not pending_message or pending_message['user_id'] != user_id:
                await self.bot.safe_answer(event, "❌ الرسالة غير موجودة أو غير مصرح لك بالوصول إليها")
                return
            
            if pending_message['status'] != 'pending':
                await self.bot.safe_answer(event, "❌ هذه الرسالة تم التعامل معها بالفعل")
                return
            
            # الحصول على تفاصيل المهمة
            task = self.db.get_task(pending_message['task_id'], user_id)
            if not task:
                await self.bot.safe_answer(event, "❌ المهمة غير موجودة")
                return
            
            # تحليل بيانات الرسالة
            try:
                message_data = json.loads(pending_message['message_data'])
            except:
                message_data = {'text': 'لا يمكن قراءة محتوى الرسالة'}
            
            task_name = task.get('task_name', f"مهمة {pending_message['task_id']}")
            
            # نص التفاصيل
            details_text = (
                f"📋 **تفاصيل الرسالة المعلقة**\n\n"
                f"📝 **المهمة:** {task_name}\n"
                f"📊 **النوع:** {message_data.get('media_type', 'نص')}\n"
                f"📱 **المصدر:** {pending_message['source_chat_id']}\n"
                f"🆔 **معرف الرسالة:** {pending_message['source_message_id']}\n"
                f"📅 **التاريخ:** {message_data.get('date', 'غير محدد')}\n\n"
                f"💬 **المحتوى:**\n"
                f"{message_data.get('text', 'لا يوجد نص')}\n\n"
                f"⚡ **اختر إجراء:**"
            )
            
            # الأزرار
            keyboard = [
                [
                    Button.inline("✅ موافق", f"approve_message_{pending_id}"),
                    Button.inline("❌ رفض", f"reject_message_{pending_id}")
                ],
                [Button.inline("🔙 رجوع للرسائل المعلقة", f"show_pending_messages_{pending_message['task_id']}")]
            ]
            
            await self.bot.edit_or_send_message(event, details_text, buttons=keyboard)
            
        except Exception as e:
            logger.error(f"خطأ في عرض تفاصيل الرسالة المعلقة: {e}")
            await self.bot.safe_answer(event, "❌ حدث خطأ في عرض التفاصيل")
    
    async def handle_message_approval(self, event, pending_id: int, approved: bool):
        """معالجة الموافقة على الرسالة"""
        try:
            user_id = event.sender_id
            
            # الحصول على تفاصيل الرسالة المعلقة
            pending_message = self.db.get_pending_message(pending_id)
            if not pending_message or pending_message['user_id'] != user_id:
                await self.bot.safe_answer(event, "❌ الرسالة غير موجودة أو غير مصرح لك بالوصول إليها")
                return
            
            if pending_message['status'] != 'pending':
                await self.bot.safe_answer(event, "❌ هذه الرسالة تم التعامل معها بالفعل")
                return
            
            task_id = pending_message['task_id']
            task = self.db.get_task(task_id, user_id)
            
            if not task:
                await self.bot.safe_answer(event, "❌ المهمة غير موجودة")
                return
            
            if approved:
                # تحديث حالة الرسالة إلى موافق عليها
                success = self.db.update_pending_message_status(pending_id, 'approved')
                if not success:
                    await self.bot.safe_answer(event, "❌ فشل في تحديث حالة الرسالة")
                    return
                
                # معالجة الرسالة الموافق عليها
                forwarding_success = await self._process_approved_message(pending_message, task)
                
                if forwarding_success:
                    # تحديث الرسالة لإظهار الموافقة
                    new_text = (
                        "✅ **تمت الموافقة**\n\n"
                        "هذه الرسالة تمت الموافقة عليها وتم إرسالها إلى الأهداف بنجاح."
                    )
                    await event.edit(new_text, buttons=None)
                    await self.bot.safe_answer(event, "✅ تمت الموافقة على الرسالة وتم إرسالها بنجاح")
                else:
                    # تحديث الرسالة لإظهار الموافقة مع تحذير
                    new_text = (
                        "⚠️ **تمت الموافقة مع تحذير**\n\n"
                        "تمت الموافقة على الرسالة ولكن فشل في إرسالها إلى بعض الأهداف."
                    )
                    await event.edit(new_text, buttons=None)
                    await self.bot.safe_answer(event, "⚠️ تمت الموافقة ولكن فشل في إرسال الرسالة")
                
                logger.info(f"✅ تمت الموافقة على الرسالة المعلقة {pending_id} للمستخدم {user_id}")
                
            else:
                # تحديث حالة الرسالة إلى مرفوضة
                success = self.db.update_pending_message_status(pending_id, 'rejected')
                if not success:
                    await self.bot.safe_answer(event, "❌ فشل في تحديث حالة الرسالة")
                    return
                
                # تحديث الرسالة لإظهار الرفض
                new_text = (
                    "❌ **تم رفض الرسالة**\n\n"
                    "هذه الرسالة تم رفضها ولن يتم إرسالها إلى الأهداف."
                )
                await event.edit(new_text, buttons=None)
                await self.bot.safe_answer(event, "❌ تم رفض الرسالة")
                
                logger.info(f"❌ تم رفض الرسالة المعلقة {pending_id} للمستخدم {user_id}")
                
        except Exception as e:
            logger.error(f"خطأ في معالجة الموافقة: {e}")
            await self.bot.safe_answer(event, "❌ حدث خطأ في معالجة الطلب")
    
    async def _process_approved_message(self, pending_message: Dict, task: Dict) -> bool:
        """معالجة الرسالة الموافق عليها وإرسالها للأهداف"""
        try:
            from userbot_service.userbot import userbot_instance
            
            user_id = pending_message['user_id']
            task_id = pending_message['task_id']
            
            # التحقق من وجود UserBot للمستخدم
            if user_id not in userbot_instance.clients:
                logger.error(f"❌ UserBot غير متصل للمستخدم {user_id}")
                return False
            
            client = userbot_instance.clients[user_id]
            
            # الحصول على الرسالة الأصلية من المصدر
            source_chat_id = int(pending_message['source_chat_id'])
            source_message_id = pending_message['source_message_id']
            
            try:
                message = await client.get_messages(source_chat_id, ids=source_message_id)
                if not message:
                    logger.error(f"❌ لم يتم العثور على الرسالة الأصلية: {source_chat_id}:{source_message_id}")
                    return False
                
                # الحصول على جميع الأهداف للمهمة
                targets = self.db.get_task_targets(task_id)
                if not targets:
                    logger.error(f"❌ لا توجد أهداف للمهمة {task_id}")
                    return False
                
                success_count = 0
                total_targets = len(targets)
                
                for target in targets:
                    try:
                        target_chat_id = target['chat_id']
                        
                        # إرسال الرسالة إلى الهدف
                        await self._forward_message_to_target(
                            message, task, user_id, client, target_chat_id
                        )
                        success_count += 1
                        logger.info(f"✅ تم إرسال رسالة موافق عليها إلى {target_chat_id}")
                        
                        # تأخير بين الأهداف
                        await asyncio.sleep(1)
                        
                    except Exception as target_error:
                        logger.error(f"❌ فشل في إرسال الرسالة إلى {target['chat_id']}: {target_error}")
                        continue
                
                logger.info(f"📊 تم إرسال الرسالة الموافق عليها إلى {success_count}/{total_targets} هدف")
                return success_count > 0
                
            except Exception as msg_error:
                logger.error(f"❌ خطأ في الحصول على الرسالة الأصلية: {msg_error}")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة الرسالة الموافق عليها: {e}")
            return False
    
    async def _forward_message_to_target(self, message, task: Dict, user_id: int, client, target_chat_id: str):
        """إرسال الرسالة إلى هدف محدد"""
        try:
            # استخدام دالة التوجيه من UserBot
            from userbot_service.userbot import userbot_instance
            
            # الحصول على إعدادات التوجيه
            forwarding_settings = self.db.get_forwarding_settings(task['id'])
            
            # إعدادات التوجيه
            forward_mode = forwarding_settings.get('forward_mode', 'forward')
            preserve_original = forwarding_settings.get('preserve_original', False)
            
            if forward_mode == 'forward':
                # توجيه مباشر
                await client.forward_messages(target_chat_id, message)
            else:
                # نسخ الرسالة
                await client.send_message(target_chat_id, message)
                
            logger.info(f"✅ تم إرسال الرسالة إلى {target_chat_id} بنجاح")
            
        except Exception as e:
            logger.error(f"❌ فشل في إرسال الرسالة إلى {target_chat_id}: {e}")
            raise e
    
    async def create_pending_message(self, task_id: int, user_id: int, source_chat_id: str, 
                                   source_message_id: int, message_data: Dict) -> bool:
        """إنشاء رسالة معلقة جديدة"""
        try:
            # حفظ الرسالة المعلقة في قاعدة البيانات
            success = self.db.create_pending_message(
                task_id=task_id,
                user_id=user_id,
                source_chat_id=source_chat_id,
                source_message_id=source_message_id,
                message_data=json.dumps(message_data),
                message_type=message_data.get('media_type', 'text')
            )
            
            if success:
                logger.info(f"✅ تم إنشاء رسالة معلقة للمهمة {task_id} للمستخدم {user_id}")
                
                # إرسال إشعار للمستخدم
                await self._send_pending_notification(user_id, task_id, source_chat_id, source_message_id)
                
            return success
            
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء رسالة معلقة: {e}")
            return False
    
    async def _send_pending_notification(self, user_id: int, task_id: int, source_chat_id: str, source_message_id: int):
        """إرسال إشعار للمستخدم بوجود رسالة معلقة"""
        try:
            # الحصول على تفاصيل المهمة
            task = self.db.get_task(task_id, user_id)
            if not task:
                return
            
            task_name = task.get('task_name', f"مهمة {task_id}")
            
            # نص الإشعار
            notification_text = (
                f"📋 **رسالة معلقة جديدة**\n\n"
                f"📝 **المهمة:** {task_name}\n"
                f"📱 **المصدر:** {source_chat_id}\n"
                f"🆔 **معرف الرسالة:** {source_message_id}\n\n"
                f"⚡ **يجب عليك مراجعة هذه الرسالة والموافقة عليها قبل إرسالها للأهداف.**"
            )
            
            # الأزرار
            buttons = [
                [
                    Button.inline("📋 عرض الرسائل المعلقة", f"show_pending_messages_{task_id}"),
                    Button.inline("⚙️ إعدادات وضع النشر", f"publishing_mode_{task_id}")
                ]
            ]
            
            # إرسال الإشعار للمستخدم
            # ملاحظة: هذا يتطلب إرسال رسالة خاصة للمستخدم
            # يمكن تنفيذها حسب احتياجات البوت
            
            logger.info(f"📋 تم إرسال إشعار رسالة معلقة للمستخدم {user_id}")
            
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال إشعار الرسالة المعلقة: {e}")
    
    def get_publishing_mode(self, task_id: int) -> str:
        """الحصول على وضع النشر للمهمة"""
        try:
            forwarding_settings = self.db.get_forwarding_settings(task_id)
            return forwarding_settings.get('publishing_mode', 'auto')
        except Exception as e:
            logger.error(f"❌ خطأ في الحصول على وضع النشر للمهمة {task_id}: {e}")
            return 'auto'  # افتراضي تلقائي في حالة الخطأ
    
    def is_manual_mode(self, task_id: int) -> bool:
        """التحقق من أن الوضع يدوي"""
        return self.get_publishing_mode(task_id) == 'manual'
    
    def is_auto_mode(self, task_id: int) -> bool:
        """التحقق من أن الوضع تلقائي"""
        return self.get_publishing_mode(task_id) == 'auto'