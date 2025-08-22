#!/usr/bin/env python3
"""
Background Media Processor
معالج الوسائط في الخلفية - يعمل بشكل مستقل عن عمليات البوت الأساسية
"""

import asyncio
import logging
import threading
import time
import uuid
from typing import Dict, Optional, Tuple, Any
from dataclasses import dataclass
from queue import Queue
from concurrent.futures import ThreadPoolExecutor
import weakref

logger = logging.getLogger(__name__)

@dataclass
class MediaProcessingTask:
    """مهمة معالجة وسائط"""
    task_id: str
    event: Any
    task_info: dict
    media_bytes: bytes
    filename: str
    processing_type: str  # 'watermark', 'audio_tags', 'both'
    watermark_settings: Optional[dict] = None
    audio_settings: Optional[dict] = None
    completion_callback: Optional[callable] = None
    priority: int = 1  # 1=عادي، 2=عالي، 3=فوري
    created_at: float = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = time.time()

@dataclass 
class ProcessingResult:
    """نتيجة معالجة الوسائط"""
    task_id: str
    success: bool
    processed_media: Optional[bytes] = None
    processed_filename: Optional[str] = None
    error: Optional[str] = None
    processing_time: float = 0
    cache_key: Optional[str] = None

class BackgroundMediaProcessor:
    """معالج الوسائط في الخلفية مع نظام انتظار للإرسال المجمع"""
    
    def __init__(self, max_workers: int = 3):
        self.max_workers = max_workers
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.processing_queue = asyncio.Queue()
        self.results_cache: Dict[str, ProcessingResult] = {}
        self.active_tasks: Dict[str, MediaProcessingTask] = {}
        self.completion_callbacks: Dict[str, callable] = {}
        
        # إعدادات الانتظار والإرسال المجمع
        self.batch_send_delay = 2.0  # ثانيتان انتظار قبل الإرسال المجمع
        self.batch_queues: Dict[str, list] = {}  # batch_key -> list of messages
        self.batch_timers: Dict[str, asyncio.Task] = {}
        
        # إحصائيات الأداء
        self.stats = {
            'total_processed': 0,
            'cache_hits': 0,
            'processing_errors': 0,
            'average_processing_time': 0,
            'current_queue_size': 0
        }
        
        self.running = False
        self.processor_task = None
        
        # استيراد معالجات الوسائط
        self._init_media_processors()
        
    def _init_media_processors(self):
        """تهيئة معالجات الوسائط"""
        try:
            from watermark_processor import WatermarkProcessor
            from audio_processor import AudioProcessor
            
            self.watermark_processor = WatermarkProcessor()
            self.audio_processor = AudioProcessor()
            logger.info("✅ تم تهيئة معالجات الوسائط بنجاح")
        except Exception as e:
            logger.error(f"❌ فشل في تهيئة معالجات الوسائط: {e}")
            self.watermark_processor = None
            self.audio_processor = None
    
    async def start(self):
        """بدء معالج الوسائط في الخلفية"""
        if self.running:
            return
            
        self.running = True
        self.processor_task = asyncio.create_task(self._background_processor())
        logger.info(f"🚀 تم بدء معالج الوسائط في الخلفية مع {self.max_workers} عامل")
    
    async def stop(self):
        """إيقاف معالج الوسائط"""
        self.running = False
        if self.processor_task:
            self.processor_task.cancel()
            try:
                await self.processor_task
            except asyncio.CancelledError:
                pass
        
        # إلغاء جميع مؤقتات الإرسال المجمع
        for timer in self.batch_timers.values():
            if not timer.done():
                timer.cancel()
                
        self.executor.shutdown(wait=True)
        logger.info("⏹️ تم إيقاف معالج الوسائط في الخلفية")
    
    async def _background_processor(self):
        """المعالج الأساسي في الخلفية"""
        logger.info("🔄 بدء حلقة معالجة الوسائط في الخلفية")
        
        while self.running:
            try:
                # انتظار مهمة جديدة مع timeout
                try:
                    task = await asyncio.wait_for(self.processing_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    # تحديث الإحصائيات كل ثانية
                    self.stats['current_queue_size'] = self.processing_queue.qsize()
                    continue
                
                # معالجة المهمة
                result = await self._process_task(task)
                
                # حفظ النتيجة في الذاكرة المؤقتة
                self.results_cache[task.task_id] = result
                
                # تشغيل callback إذا كان موجود
                if task.completion_callback:
                    try:
                        if asyncio.iscoroutinefunction(task.completion_callback):
                            await task.completion_callback(result)
                        else:
                            task.completion_callback(result)
                    except Exception as e:
                        logger.error(f"❌ خطأ في callback للمهمة {task.task_id}: {e}")
                
                # تحديث الإحصائيات
                self._update_stats(result)
                
                # إزالة المهمة من القائمة النشطة
                self.active_tasks.pop(task.task_id, None)
                
            except Exception as e:
                logger.error(f"❌ خطأ في معالج الوسائط: {e}")
                await asyncio.sleep(0.1)
    
    async def _process_task(self, task: MediaProcessingTask) -> ProcessingResult:
        """معالجة مهمة واحدة"""
        start_time = time.time()
        
        try:
            logger.info(f"🎬 بدء معالجة {task.processing_type} للمهمة {task.task_id}")
            
            # فحص الذاكرة المؤقتة أولاً
            cache_key = self._generate_cache_key(task)
            if cache_key in self.results_cache:
                cached_result = self.results_cache[cache_key]
                if cached_result.success:
                    logger.info(f"🔄 استخدام نتيجة محفوظة للمهمة {task.task_id}")
                    self.stats['cache_hits'] += 1
                    return cached_result
            
            # تحديد نوع المعالجة المطلوبة
            processed_media = task.media_bytes
            processed_filename = task.filename
            
            if task.processing_type in ['watermark', 'both']:
                if self.watermark_processor and task.watermark_settings:
                    # معالجة العلامة المائية في thread منفصل
                    processed_media = await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        self._apply_watermark_sync,
                        processed_media,
                        task.filename,
                        task.watermark_settings,
                        task.task_info.get('id', 0)
                    )
            
            if task.processing_type in ['audio_tags', 'both']:
                if self.audio_processor and task.audio_settings:
                    # معالجة الوسوم الصوتية في thread منفصل
                    processed_media, processed_filename = await asyncio.get_event_loop().run_in_executor(
                        self.executor,
                        self._apply_audio_tags_sync,
                        processed_media,
                        task.filename,
                        task.audio_settings,
                        task.task_info.get('id', 0)
                    )
            
            processing_time = time.time() - start_time
            
            result = ProcessingResult(
                task_id=task.task_id,
                success=True,
                processed_media=processed_media,
                processed_filename=processed_filename,
                processing_time=processing_time,
                cache_key=cache_key
            )
            
            logger.info(f"✅ تمت معالجة {task.processing_type} للمهمة {task.task_id} في {processing_time:.2f}s")
            return result
            
        except Exception as e:
            processing_time = time.time() - start_time
            logger.error(f"❌ فشل في معالجة {task.processing_type} للمهمة {task.task_id}: {e}")
            
            return ProcessingResult(
                task_id=task.task_id,
                success=False,
                error=str(e),
                processing_time=processing_time
            )
    
    def _apply_watermark_sync(self, media_bytes: bytes, filename: str, 
                             watermark_settings: dict, task_id: int) -> bytes:
        """تطبيق العلامة المائية - نسخة متزامنة"""
        if not self.watermark_processor:
            return media_bytes
            
        return self.watermark_processor.process_media_once_for_all_targets(
            media_bytes, filename, watermark_settings, task_id
        )
    
    def _apply_audio_tags_sync(self, media_bytes: bytes, filename: str,
                              audio_settings: dict, task_id: int) -> Tuple[bytes, str]:
        """تطبيق الوسوم الصوتية - نسخة متزامنة"""
        if not self.audio_processor:
            return media_bytes, filename
            
        # استدعاء معالج الصوت (يحتاج تطبيق حقيقي)
        # لحالياً، إرجاع البيانات الأصلية
        return media_bytes, filename
    
    def _generate_cache_key(self, task: MediaProcessingTask) -> str:
        """إنشاء مفتاح ذاكرة مؤقتة فريد"""
        import hashlib
        
        # حساب hash للبيانات الأساسية
        content_hash = hashlib.md5(task.media_bytes[:1024]).hexdigest()  # أول 1KB فقط للسرعة
        
        # إضافة معرفات الإعدادات
        watermark_hash = str(hash(str(task.watermark_settings))) if task.watermark_settings else "none"
        audio_hash = str(hash(str(task.audio_settings))) if task.audio_settings else "none"
        
        return f"{content_hash}_{task.processing_type}_{watermark_hash}_{audio_hash}"
    
    def _update_stats(self, result: ProcessingResult):
        """تحديث إحصائيات الأداء"""
        self.stats['total_processed'] += 1
        
        if not result.success:
            self.stats['processing_errors'] += 1
        
        # تحديث متوسط وقت المعالجة
        current_avg = self.stats['average_processing_time']
        total = self.stats['total_processed']
        self.stats['average_processing_time'] = (
            (current_avg * (total - 1) + result.processing_time) / total
        )
    
    async def queue_media_processing(self, event, task_info: dict, processing_type: str,
                                   watermark_settings: dict = None, audio_settings: dict = None,
                                   priority: int = 1, completion_callback: callable = None) -> str:
        """إضافة مهمة معالجة وسائط إلى القائمة"""
        
        if not self.running:
            await self.start()
        
        # تحميل بيانات الوسائط
        try:
            media_bytes = await event.message.download_media(bytes)
            if not media_bytes:
                raise Exception("فشل في تحميل بيانات الوسائط")
        except Exception as e:
            logger.error(f"❌ فشل في تحميل الوسائط: {e}")
            return None
        
        # الحصول على اسم الملف
        filename = self._extract_filename(event)
        
        # إنشاء معرف فريد للمهمة
        task_id = str(uuid.uuid4())
        
        # إنشاء مهمة المعالجة
        processing_task = MediaProcessingTask(
            task_id=task_id,
            event=event,
            task_info=task_info,
            media_bytes=media_bytes,
            filename=filename,
            processing_type=processing_type,
            watermark_settings=watermark_settings,
            audio_settings=audio_settings,
            completion_callback=completion_callback,
            priority=priority
        )
        
        # إضافة إلى القائمة النشطة
        self.active_tasks[task_id] = processing_task
        
        # إضافة إلى قائمة المعالجة
        await self.processing_queue.put(processing_task)
        
        logger.info(f"📝 تم إضافة مهمة معالجة {processing_type} للقائمة: {task_id}")
        return task_id
    
    def _extract_filename(self, event) -> str:
        """استخراج اسم الملف من الحدث"""
        try:
            if hasattr(event.message.media, 'document') and event.message.media.document:
                doc = event.message.media.document
                if hasattr(doc, 'attributes'):
                    for attr in doc.attributes:
                        if hasattr(attr, 'file_name') and attr.file_name:
                            return attr.file_name
                            
                # استخدام نوع MIME لتحديد الامتداد
                if doc.mime_type:
                    ext_map = {
                        'image/jpeg': '.jpg', 'image/png': '.png', 'video/mp4': '.mp4',
                        'audio/mpeg': '.mp3', 'audio/mp4': '.m4a', 'audio/ogg': '.ogg'
                    }
                    ext = ext_map.get(doc.mime_type, '.bin')
                    return f"media_{doc.id}{ext}"
            
            return "media_file.bin"
        except:
            return "media_file.bin"
    
    async def get_processing_result(self, task_id: str, timeout: float = 30.0) -> Optional[ProcessingResult]:
        """الحصول على نتيجة المعالجة مع انتظار"""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            if task_id in self.results_cache:
                return self.results_cache[task_id]
            await asyncio.sleep(0.1)
        
        logger.warning(f"⏰ انتهت مهلة انتظار نتيجة المعالجة للمهمة {task_id}")
        return None
    
    def is_processing_complete(self, task_id: str) -> bool:
        """فحص ما إذا كانت المعالجة مكتملة"""
        return task_id in self.results_cache
    
    def get_stats(self) -> dict:
        """الحصول على إحصائيات الأداء"""
        self.stats['current_queue_size'] = self.processing_queue.qsize()
        self.stats['active_tasks'] = len(self.active_tasks)
        return self.stats.copy()
    
    # ===== نظام الإرسال المجمع مع الانتظار =====
    
    async def queue_batch_send(self, batch_key: str, message_data: dict, delay: float = None):
        """إضافة رسالة إلى قائمة الإرسال المجمع"""
        if delay is None:
            delay = self.batch_send_delay
            
        # إضافة الرسالة إلى مجموعة الإرسال
        if batch_key not in self.batch_queues:
            self.batch_queues[batch_key] = []
        
        self.batch_queues[batch_key].append(message_data)
        
        # إلغاء المؤقت السابق إن وجد
        if batch_key in self.batch_timers:
            self.batch_timers[batch_key].cancel()
        
        # إنشاء مؤقت جديد
        self.batch_timers[batch_key] = asyncio.create_task(
            self._batch_send_delayed(batch_key, delay)
        )
        
        logger.info(f"📨 تم إضافة رسالة للإرسال المجمع: {batch_key} (العدد: {len(self.batch_queues[batch_key])})")
    
    async def _batch_send_delayed(self, batch_key: str, delay: float):
        """إرسال مجموعة الرسائل بعد التأخير"""
        try:
            await asyncio.sleep(delay)
            
            if batch_key in self.batch_queues:
                messages = self.batch_queues[batch_key]
                logger.info(f"📤 إرسال مجموعة من {len(messages)} رسالة للمفتاح: {batch_key}")
                
                # تشغيل callback الإرسال المجمع
                for message_data in messages:
                    if 'send_callback' in message_data:
                        callback = message_data['send_callback']
                        try:
                            if asyncio.iscoroutinefunction(callback):
                                await callback(message_data)
                            else:
                                callback(message_data)
                        except Exception as e:
                            logger.error(f"❌ خطأ في إرسال رسالة مجمعة: {e}")
                
                # تنظيف
                del self.batch_queues[batch_key]
                if batch_key in self.batch_timers:
                    del self.batch_timers[batch_key]
                    
        except asyncio.CancelledError:
            logger.debug(f"تم إلغاء مؤقت الإرسال المجمع: {batch_key}")
        except Exception as e:
            logger.error(f"❌ خطأ في الإرسال المجمع: {e}")

# إنشاء instance عالمي
background_processor = BackgroundMediaProcessor()

# وظائف مساعدة للاستخدام السهل
async def process_media_in_background(event, task_info: dict, processing_type: str,
                                    watermark_settings: dict = None, audio_settings: dict = None,
                                    priority: int = 1) -> Optional[str]:
    """معالجة الوسائط في الخلفية"""
    return await background_processor.queue_media_processing(
        event, task_info, processing_type, watermark_settings, audio_settings, priority
    )

async def get_processed_media(task_id: str, timeout: float = 30.0) -> Optional[ProcessingResult]:
    """الحصول على نتيجة معالجة الوسائط"""
    return await background_processor.get_processing_result(task_id, timeout)

async def queue_batch_message(batch_key: str, message_data: dict, delay: float = 2.0):
    """إضافة رسالة للإرسال المجمع"""
    await background_processor.queue_batch_send(batch_key, message_data, delay)

def get_processor_stats() -> dict:
    """الحصول على إحصائيات المعالج"""
    return background_processor.get_stats()