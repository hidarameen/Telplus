#!/usr/bin/env python3
"""
مثال تكامل النظام المحسن مع البوت
Integration Example of Optimized System with Bot
"""

import asyncio
import logging
from typing import Optional, Dict, Any

from advanced_queue_system import AdvancedQueueSystem, TaskPriority
from optimized_media_handler import OptimizedMediaHandler, MediaProcessingRequest

logger = logging.getLogger(__name__)

class OptimizedBotIntegration:
    """تكامل النظام المحسن مع البوت"""
    
    def __init__(self, bot_instance):
        """تهيئة التكامل"""
        self.bot = bot_instance
        self.media_handler = OptimizedMediaHandler(bot_instance)
        
        # إعدادات ديناميكية
        self.dynamic_settings = {
            'auto_optimize': True,
            'priority_users': [],  # مستخدمون ذوو أولوية عالية
            'batch_processing': True,
            'max_batch_size': 10
        }
        
        # مجموعة معالجة دفعية
        self.batch_queue = []
        self.batch_timer = None
        
    async def handle_media_message(self, event, task_info: Dict, 
                                 processing_type: str = "both",
                                 watermark_settings: Optional[Dict] = None,
                                 audio_settings: Optional[Dict] = None) -> bool:
        """معالجة رسالة وسائط محسنة"""
        
        try:
            # تحديد الأولوية
            priority = self._determine_priority(event)
            
            # إنشاء طلب المعالجة
            request = MediaProcessingRequest(
                event=event,
                task_info=task_info,
                processing_type=processing_type,
                watermark_settings=watermark_settings,
                audio_settings=audio_settings,
                priority=priority,
                progress_callback=self._create_progress_callback(event)
            )
            
            # معالجة دفعية أو فردية
            if self.dynamic_settings['batch_processing'] and priority != TaskPriority.URGENT:
                await self._add_to_batch(request)
            else:
                await self._process_immediate(request)
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في معالجة رسالة الوسائط: {e}")
            await self._send_error_message(event, str(e))
            return False
    
    def _determine_priority(self, event) -> TaskPriority:
        """تحديد أولوية المعالجة"""
        user_id = event.sender_id
        
        # مستخدمون ذوو أولوية عالية
        if user_id in self.dynamic_settings['priority_users']:
            return TaskPriority.HIGH
        
        # حجم الملف
        if hasattr(event.message, 'media') and hasattr(event.message.media, 'document'):
            file_size = event.message.media.document.size
            
            # ملفات كبيرة أولوية منخفضة لتجنب التأثير على الأداء
            if file_size > 100 * 1024 * 1024:  # أكبر من 100MB
                return TaskPriority.LOW
            elif file_size > 50 * 1024 * 1024:  # أكبر من 50MB
                return TaskPriority.NORMAL
        
        return TaskPriority.NORMAL
    
    def _create_progress_callback(self, event):
        """إنشاء callback لتتبع التقدم"""
        async def progress_callback(task_id: str, progress: float):
            if progress % 25 == 0:  # تحديث كل 25%
                try:
                    await event.reply(f"🔄 تقدم المعالجة: {progress:.0f}%")
                except Exception as e:
                    logger.error(f"خطأ في إرسال تحديث التقدم: {e}")
        
        return progress_callback
    
    async def _add_to_batch(self, request: MediaProcessingRequest):
        """إضافة للمعالجة الدفعية"""
        self.batch_queue.append(request)
        
        logger.info(f"تمت إضافة طلب للدفعة ({len(self.batch_queue)}/{self.dynamic_settings['max_batch_size']})")
        
        # بدء timer إذا كانت هذه أول عملية في الدفعة
        if len(self.batch_queue) == 1:
            self.batch_timer = asyncio.create_task(self._batch_timer())
        
        # معالجة فورية إذا امتلأت الدفعة
        if len(self.batch_queue) >= self.dynamic_settings['max_batch_size']:
            await self._process_batch()
    
    async def _batch_timer(self):
        """مؤقت المعالجة الدفعية"""
        await asyncio.sleep(10)  # انتظار 10 ثوانِ
        
        if self.batch_queue:
            await self._process_batch()
    
    async def _process_batch(self):
        """معالجة الدفعة"""
        if not self.batch_queue:
            return
        
        logger.info(f"بدء معالجة دفعة من {len(self.batch_queue)} طلب")
        
        # إلغاء المؤقت
        if self.batch_timer and not self.batch_timer.done():
            self.batch_timer.cancel()
        
        # نسخ الدفعة وتنظيف القائمة
        current_batch = self.batch_queue.copy()
        self.batch_queue.clear()
        
        # معالجة دفعية
        try:
            await self.media_handler.batch_process_media(current_batch)
        except Exception as e:
            logger.error(f"خطأ في المعالجة الدفعية: {e}")
            
            # معالجة فردية كبديل
            for request in current_batch:
                try:
                    await self._process_immediate(request)
                except Exception as individual_error:
                    logger.error(f"خطأ في المعالجة الفردية البديلة: {individual_error}")
    
    async def _process_immediate(self, request: MediaProcessingRequest):
        """معالجة فورية"""
        logger.info(f"معالجة فورية لطلب من المستخدم {request.event.sender_id}")
        
        await self.media_handler.process_media_message(request)
    
    async def _send_error_message(self, event, error: str):
        """إرسال رسالة خطأ للمستخدم"""
        try:
            await event.reply(f"❌ حدث خطأ في المعالجة: {error}")
        except Exception as e:
            logger.error(f"فشل في إرسال رسالة الخطأ: {e}")
    
    async def optimize_for_current_load(self):
        """تحسين الإعدادات حسب الحمولة الحالية"""
        
        # الحصول على إحصائيات الأداء
        stats = self.media_handler.get_performance_stats()
        
        queue_stats = stats['queue_system']['stats']
        active_tasks = queue_stats.get('active_tasks', 0)
        failed_tasks = queue_stats.get('failed_tasks', 0)
        total_tasks = queue_stats.get('total_tasks', 1)
        
        # حساب معدل الفشل
        failure_rate = failed_tasks / total_tasks if total_tasks > 0 else 0
        
        # تحسين حسب الحمولة
        if active_tasks > 20:  # حمولة عالية
            logger.info("🔧 تحسين للحمولة العالية...")
            
            # تقليل التزامن
            optimization_settings = {
                'max_concurrent_downloads': 2,
                'max_concurrent_uploads': 3,
                'chunk_size': 10 * 1024 * 1024,  # 10MB
                'compression_quality': 75
            }
            
            # زيادة حجم الدفعة لتقليل التكرار
            self.dynamic_settings['max_batch_size'] = 15
            
        elif failure_rate > 0.1:  # معدل فشل عالي
            logger.info("🔧 تحسين لتقليل معدل الفشل...")
            
            # إعدادات أكثر تحفظاً
            optimization_settings = {
                'max_concurrent_downloads': 3,
                'max_concurrent_uploads': 4,
                'chunk_size': 15 * 1024 * 1024,  # 15MB
                'retry_attempts': 5
            }
            
        else:  # حمولة عادية
            logger.info("🔧 تحسين للأداء الأمثل...")
            
            # إعدادات متوازنة
            optimization_settings = {
                'max_concurrent_downloads': 6,
                'max_concurrent_uploads': 8,
                'chunk_size': 20 * 1024 * 1024,  # 20MB
                'compression_quality': 85
            }
        
        # تطبيق الإعدادات
        self.media_handler.update_optimization_settings(optimization_settings)
        
        logger.info(f"تم تحسين الإعدادات: {len(optimization_settings)} إعداد محدث")
    
    async def handle_watermark_command(self, event, task_info: Dict):
        """معالجة أمر العلامة المائية"""
        
        watermark_settings = {
            'enabled': True,
            'text': task_info.get('watermark_text', ''),
            'position': task_info.get('watermark_position', 'bottom-right'),
            'opacity': task_info.get('watermark_opacity', 0.7),
            'font_size': task_info.get('watermark_font_size', 24)
        }
        
        return await self.handle_media_message(
            event, task_info, 
            processing_type="watermark",
            watermark_settings=watermark_settings
        )
    
    async def handle_audio_tags_command(self, event, task_info: Dict):
        """معالجة أمر الوسوم الصوتية"""
        
        audio_settings = {
            'enabled': True,
            'template': task_info.get('audio_template', 'default'),
            'album_art': task_info.get('album_art_enabled', False),
            'merge_audio': task_info.get('audio_merge_enabled', False)
        }
        
        return await self.handle_media_message(
            event, task_info,
            processing_type="audio_tags", 
            audio_settings=audio_settings
        )
    
    async def handle_combined_processing(self, event, task_info: Dict):
        """معالجة مدمجة (علامة مائية + وسوم صوتية)"""
        
        watermark_settings = {
            'enabled': True,
            'text': task_info.get('watermark_text', ''),
            'position': task_info.get('watermark_position', 'bottom-right')
        }
        
        audio_settings = {
            'enabled': True,
            'template': task_info.get('audio_template', 'default'),
            'album_art': task_info.get('album_art_enabled', False)
        }
        
        return await self.handle_media_message(
            event, task_info,
            processing_type="both",
            watermark_settings=watermark_settings,
            audio_settings=audio_settings
        )
    
    async def get_processing_status(self, event):
        """الحصول على حالة المعالجة"""
        
        stats = self.media_handler.get_performance_stats()
        
        message = f"""
📊 **حالة نظام المعالجة المحسن**

🔄 **نظام الانتظار:**
• المهام النشطة: {stats['queue_system']['stats'].get('active_tasks', 0)}
• المهام المكتملة: {stats['queue_system']['stats'].get('completed_tasks', 0)}
• المهام الفاشلة: {stats['queue_system']['stats'].get('failed_tasks', 0)}

📁 **معالج الملفات:**
• الجلسات النشطة: {stats['file_processor'].get('active_sessions', 0)}
• حجم الذاكرة المؤقتة: {stats['file_processor'].get('cache_size', 0)}

⚡ **الأداء:**
• متوسط سرعة التحميل: {stats['media_handler'].get('average_download_speed', 0):.2f} MB/s
• متوسط سرعة الرفع: {stats['media_handler'].get('average_upload_speed', 0):.2f} MB/s
• المعالجة الناجحة: {stats['media_handler'].get('successful_processed', 0)}

🔧 **الدفعة الحالية:**
• في الانتظار: {len(self.batch_queue)}
• الحد الأقصى: {self.dynamic_settings['max_batch_size']}
"""
        
        await event.reply(message)
    
    def add_priority_user(self, user_id: int):
        """إضافة مستخدم ذو أولوية عالية"""
        if user_id not in self.dynamic_settings['priority_users']:
            self.dynamic_settings['priority_users'].append(user_id)
            logger.info(f"تمت إضافة مستخدم ذو أولوية عالية: {user_id}")
    
    def remove_priority_user(self, user_id: int):
        """إزالة مستخدم من الأولوية العالية"""
        if user_id in self.dynamic_settings['priority_users']:
            self.dynamic_settings['priority_users'].remove(user_id)
            logger.info(f"تمت إزالة مستخدم من الأولوية العالية: {user_id}")
    
    async def emergency_shutdown(self):
        """إيقاف طارئ للنظام"""
        logger.warning("🚨 بدء الإيقاف الطارئ للنظام...")
        
        # إلغاء المؤقت
        if self.batch_timer and not self.batch_timer.done():
            self.batch_timer.cancel()
        
        # معالجة الدفعة المتبقية بسرعة
        if self.batch_queue:
            logger.info(f"معالجة طارئة لـ {len(self.batch_queue)} طلب متبقي")
            
            # معالجة بأولوية عاجلة
            for request in self.batch_queue:
                request.priority = TaskPriority.URGENT
                await self._process_immediate(request)
            
            self.batch_queue.clear()
        
        # إيقاف المعالج
        self.media_handler.shutdown()
        
        logger.info("✅ تم الإيقاف الطارئ بنجاح")
    
    async def start_auto_optimization(self):
        """بدء التحسين التلقائي"""
        if not self.dynamic_settings['auto_optimize']:
            return
        
        logger.info("🤖 بدء التحسين التلقائي...")
        
        while self.dynamic_settings['auto_optimize']:
            try:
                await self.optimize_for_current_load()
                await asyncio.sleep(60)  # تحسين كل دقيقة
            except Exception as e:
                logger.error(f"خطأ في التحسين التلقائي: {e}")
                await asyncio.sleep(30)  # إعادة المحاولة بعد 30 ثانية

# مثال للاستخدام في البوت
def integrate_with_bot(bot_instance):
    """دمج النظام المحسن مع البوت"""
    
    # إنشاء التكامل
    integration = OptimizedBotIntegration(bot_instance)
    
    # بدء التحسين التلقائي
    asyncio.create_task(integration.start_auto_optimization())
    
    return integration