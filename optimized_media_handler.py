#!/usr/bin/env python3
"""
معالج الوسائط المحسن مع دعم التحميل والرفع المتوازي
Optimized Media Handler with Parallel Upload/Download Support
"""

import asyncio
import logging
import time
import tempfile
import os
from typing import Dict, Optional, Any, Callable, Union, Tuple
from dataclasses import dataclass
import aiofiles
from telethon import TelegramClient
from telethon.tl.types import Message, DocumentAttributeVideo, DocumentAttributeAudio

from advanced_queue_system import AdvancedQueueSystem, MediaTask, TaskPriority
from parallel_file_processor import ParallelFileProcessor
from send_file_helper import send_file_with_custom_name

logger = logging.getLogger(__name__)

@dataclass
class MediaProcessingRequest:
    """طلب معالجة وسائط"""
    event: Any
    task_info: Dict
    processing_type: str
    watermark_settings: Optional[Dict] = None
    audio_settings: Optional[Dict] = None
    priority: TaskPriority = TaskPriority.NORMAL
    progress_callback: Optional[Callable] = None

class OptimizedMediaHandler:
    """معالج الوسائط المحسن"""
    
    def __init__(self, bot_instance=None):
        """تهيئة المعالج"""
        self.bot = bot_instance
        self.queue_system = AdvancedQueueSystem(max_workers=16)
        self.file_processor = ParallelFileProcessor(max_workers=8, chunk_size=20*1024*1024)  # 20MB chunks
        
        # إعدادات التحسين
        self.optimization_settings = {
            'max_concurrent_downloads': 4,
            'max_concurrent_uploads': 6,
            'download_timeout': 300,  # 5 دقائق
            'upload_timeout': 600,    # 10 دقائق
            'retry_attempts': 3,
            'chunk_size': 20 * 1024 * 1024,  # 20MB
            'enable_compression': True,
            'compression_quality': 85
        }
        
        # سيمافورات للتحكم في التزامن
        self.download_semaphore = asyncio.Semaphore(self.optimization_settings['max_concurrent_downloads'])
        self.upload_semaphore = asyncio.Semaphore(self.optimization_settings['max_concurrent_uploads'])
        
        # إحصائيات الأداء
        self.performance_stats = {
            'total_processed': 0,
            'successful_processed': 0,
            'failed_processed': 0,
            'average_download_speed': 0,
            'average_upload_speed': 0,
            'average_processing_time': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    async def process_media_message(self, request: MediaProcessingRequest) -> Optional[Message]:
        """معالجة رسالة وسائط"""
        try:
            start_time = time.time()
            
            # استخراج الوسائط
            media_data, filename, file_size = await self._extract_media_from_message(request.event)
            
            if not media_data:
                logger.error("فشل في استخراج الوسائط من الرسالة")
                return None
            
            # تحديد نوع الوسائط
            media_type = self._detect_media_type(filename)
            
            # إنشاء مهمة معالجة
            task = MediaTask(
                user_id=request.event.sender_id,
                chat_id=request.event.chat_id,
                message_id=request.event.id,
                media_data=media_data,
                filename=filename,
                file_size=file_size,
                media_type=media_type,
                processing_type=request.processing_type,
                watermark_settings=request.watermark_settings,
                audio_settings=request.audio_settings,
                priority=request.priority,
                progress_callback=request.progress_callback,
                completion_callback=self._create_completion_callback(request)
            )
            
            # إضافة المهمة للطابور
            task_id = self.queue_system.add_task(task)
            
            logger.info(f"تمت إضافة مهمة معالجة الوسائط: {task_id}")
            
            # تحديث الإحصائيات
            self.performance_stats['total_processed'] += 1
            
            return task_id
            
        except Exception as e:
            logger.error(f"خطأ في معالجة رسالة الوسائط: {e}")
            self.performance_stats['failed_processed'] += 1
            return None
    
    async def _extract_media_from_message(self, event) -> Tuple[Optional[bytes], Optional[str], int]:
        """استخراج الوسائط من الرسالة"""
        try:
            message = event.message if hasattr(event, 'message') else event
            
            if not message.media:
                return None, None, 0
            
            # تحديد اسم الملف وحجمه
            filename = "unknown"
            file_size = 0
            
            if hasattr(message.media, 'document'):
                doc = message.media.document
                file_size = doc.size
                
                # البحث عن اسم الملف في الخصائص
                for attr in doc.attributes:
                    if hasattr(attr, 'file_name') and attr.file_name:
                        filename = attr.file_name
                        break
            
            # تحميل الوسائط مع التحسين
            async with self.download_semaphore:
                media_data = await self._optimized_download(message, file_size)
            
            return media_data, filename, file_size
            
        except Exception as e:
            logger.error(f"خطأ في استخراج الوسائط: {e}")
            return None, None, 0
    
    async def _optimized_download(self, message, file_size: int) -> Optional[bytes]:
        """تحميل محسن للوسائط"""
        try:
            download_start = time.time()
            
            # استخدام التحميل المقسم للملفات الكبيرة
            if file_size > self.optimization_settings['chunk_size']:
                logger.info(f"تحميل مقسم للملف الكبير ({file_size} بايت)")
                media_data = await self._chunked_download(message, file_size)
            else:
                logger.info(f"تحميل عادي للملف الصغير ({file_size} بايت)")
                media_data = await message.download_media(bytes)
            
            download_time = time.time() - download_start
            download_speed = (file_size / (1024 * 1024)) / download_time if download_time > 0 else 0
            
            # تحديث إحصائيات السرعة
            current_avg = self.performance_stats['average_download_speed']
            self.performance_stats['average_download_speed'] = (current_avg + download_speed) / 2
            
            logger.info(f"تم التحميل بسرعة {download_speed:.2f} MB/s")
            
            return media_data
            
        except Exception as e:
            logger.error(f"خطأ في التحميل المحسن: {e}")
            return None
    
    async def _chunked_download(self, message, file_size: int) -> Optional[bytes]:
        """تحميل مقسم للملفات الكبيرة"""
        try:
            chunks = []
            chunk_size = self.optimization_settings['chunk_size']
            
            # تحميل الأجزاء بشكل متوازي
            async def download_chunk(offset: int, limit: int):
                return await message.download_media(bytes, offset=offset, limit=limit)
            
            # إنشاء مهام التحميل
            tasks = []
            for offset in range(0, file_size, chunk_size):
                limit = min(chunk_size, file_size - offset)
                task = asyncio.create_task(download_chunk(offset, limit))
                tasks.append(task)
            
            # تنفيذ التحميل المتوازي
            chunk_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # دمج الأجزاء
            for i, result in enumerate(chunk_results):
                if isinstance(result, Exception):
                    logger.error(f"فشل في تحميل الجزء {i}: {result}")
                    return None
                chunks.append(result)
            
            return b''.join(chunks)
            
        except Exception as e:
            logger.error(f"خطأ في التحميل المقسم: {e}")
            return None
    
    def _detect_media_type(self, filename: str) -> str:
        """تحديد نوع الوسائط"""
        if not filename:
            return "unknown"
        
        ext = filename.lower().split('.')[-1] if '.' in filename else ""
        
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp']:
            return "image"
        elif ext in ['mp4', 'avi', 'mkv', 'mov', 'wmv', 'flv', 'webm']:
            return "video"
        elif ext in ['mp3', 'm4a', 'aac', 'ogg', 'wav', 'flac']:
            return "audio"
        else:
            return "document"
    
    def _create_completion_callback(self, request: MediaProcessingRequest) -> Callable:
        """إنشاء callback للإكمال"""
        async def completion_callback(task: MediaTask, result: Dict):
            try:
                if not result or 'processed_data' not in result:
                    logger.error(f"نتيجة معالجة غير صالحة للمهمة {task.task_id}")
                    self.performance_stats['failed_processed'] += 1
                    return
                
                # رفع الملف المعالج
                success = await self._upload_processed_media(
                    request.event,
                    result['processed_data'],
                    result['filename'],
                    task.media_type
                )
                
                if success:
                    self.performance_stats['successful_processed'] += 1
                    logger.info(f"تم إكمال معالجة ورفع المهمة {task.task_id}")
                else:
                    self.performance_stats['failed_processed'] += 1
                    logger.error(f"فشل في رفع المهمة {task.task_id}")
                
            except Exception as e:
                logger.error(f"خطأ في callback الإكمال: {e}")
                self.performance_stats['failed_processed'] += 1
        
        return completion_callback
    
    async def _upload_processed_media(self, event, processed_data: bytes, 
                                    filename: str, media_type: str) -> bool:
        """رفع الوسائط المعالجة"""
        try:
            upload_start = time.time()
            
            async with self.upload_semaphore:
                # استخدام الرفع المحسن
                if len(processed_data) > self.optimization_settings['chunk_size']:
                    success = await self._chunked_upload(event, processed_data, filename, media_type)
                else:
                    success = await self._simple_upload(event, processed_data, filename, media_type)
            
            upload_time = time.time() - upload_start
            upload_speed = (len(processed_data) / (1024 * 1024)) / upload_time if upload_time > 0 else 0
            
            # تحديث إحصائيات السرعة
            current_avg = self.performance_stats['average_upload_speed']
            self.performance_stats['average_upload_speed'] = (current_avg + upload_speed) / 2
            
            logger.info(f"تم الرفع بسرعة {upload_speed:.2f} MB/s")
            
            return success
            
        except Exception as e:
            logger.error(f"خطأ في رفع الوسائط المعالجة: {e}")
            return False
    
    async def _simple_upload(self, event, data: bytes, filename: str, media_type: str) -> bool:
        """رفع بسيط"""
        try:
            # تحديد الخصائص حسب نوع الوسائط
            attributes = []
            
            if media_type == "video":
                # إضافة خصائص الفيديو
                attributes.append(DocumentAttributeVideo(
                    duration=0,  # يمكن تحسينه لاحقاً
                    w=0,
                    h=0,
                    supports_streaming=True
                ))
            elif media_type == "audio":
                # إضافة خصائص الصوت
                attributes.append(DocumentAttributeAudio(
                    duration=0,  # يمكن تحسينه لاحقاً
                    voice=False
                ))
            
            # رفع الملف
            await send_file_with_custom_name(
                event,
                data,
                filename,
                caption=f"✅ تم معالجة الملف: {filename}",
                attributes=attributes
            )
            
            return True
            
        except Exception as e:
            logger.error(f"خطأ في الرفع البسيط: {e}")
            return False
    
    async def _chunked_upload(self, event, data: bytes, filename: str, media_type: str) -> bool:
        """رفع مقسم للملفات الكبيرة"""
        try:
            # إنشاء جلسة رفع
            session_id = self.file_processor.create_resumable_upload_session(filename, len(data))
            
            # دالة رفع الجزء
            def upload_chunk(chunk_data: bytes):
                # هنا يمكن استخدام Telegram's upload API مباشرة
                # أو حفظ مؤقت ثم رفع
                return True
            
            # رفع متوازي
            result = await self.file_processor.smart_file_transfer(
                data, filename, upload_chunk,
                progress_callback=lambda current, total, progress: 
                    logger.info(f"تقدم الرفع: {progress:.1f}%")
            )
            
            if result:
                # رفع الملف النهائي
                return await self._simple_upload(event, data, filename, media_type)
            
            return False
            
        except Exception as e:
            logger.error(f"خطأ في الرفع المقسم: {e}")
            return False
    
    async def batch_process_media(self, requests: list[MediaProcessingRequest]) -> list:
        """معالجة دفعية للوسائط"""
        logger.info(f"بدء المعالجة الدفعية لـ {len(requests)} طلب")
        
        # إنشاء مهام متوازية
        tasks = []
        for request in requests:
            task = asyncio.create_task(self.process_media_message(request))
            tasks.append(task)
        
        # تنفيذ المعالجة المتوازية
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # تحليل النتائج
        successful = sum(1 for r in results if not isinstance(r, Exception) and r is not None)
        failed = len(results) - successful
        
        logger.info(f"المعالجة الدفعية: {successful} نجح، {failed} فشل")
        
        return results
    
    def get_performance_stats(self) -> Dict:
        """الحصول على إحصائيات الأداء"""
        queue_stats = self.queue_system.get_queue_stats()
        processor_stats = self.file_processor.get_stats()
        
        return {
            'media_handler': self.performance_stats.copy(),
            'queue_system': queue_stats,
            'file_processor': processor_stats,
            'optimization_settings': self.optimization_settings.copy()
        }
    
    def update_optimization_settings(self, settings: Dict):
        """تحديث إعدادات التحسين"""
        self.optimization_settings.update(settings)
        
        # تحديث السيمافورات
        if 'max_concurrent_downloads' in settings:
            self.download_semaphore = asyncio.Semaphore(settings['max_concurrent_downloads'])
        
        if 'max_concurrent_uploads' in settings:
            self.upload_semaphore = asyncio.Semaphore(settings['max_concurrent_uploads'])
        
        logger.info("تم تحديث إعدادات التحسين")
    
    async def optimize_for_connection(self, connection_speed_mbps: float):
        """تحسين الإعدادات حسب سرعة الاتصال"""
        
        if connection_speed_mbps < 1:  # اتصال بطيء
            settings = {
                'max_concurrent_downloads': 2,
                'max_concurrent_uploads': 2,
                'chunk_size': 5 * 1024 * 1024,  # 5MB
                'compression_quality': 70
            }
        elif connection_speed_mbps < 10:  # اتصال متوسط
            settings = {
                'max_concurrent_downloads': 4,
                'max_concurrent_uploads': 4,
                'chunk_size': 10 * 1024 * 1024,  # 10MB
                'compression_quality': 80
            }
        else:  # اتصال سريع
            settings = {
                'max_concurrent_downloads': 8,
                'max_concurrent_uploads': 6,
                'chunk_size': 20 * 1024 * 1024,  # 20MB
                'compression_quality': 90
            }
        
        self.update_optimization_settings(settings)
        logger.info(f"تم تحسين الإعدادات لسرعة {connection_speed_mbps} Mbps")
    
    def cleanup_resources(self):
        """تنظيف الموارد"""
        logger.info("تنظيف موارد معالج الوسائط...")
        
        # تنظيف الجلسات القديمة
        self.file_processor.cleanup_old_sessions()
        
        # إعادة تعيين الإحصائيات إذا لزم الأمر
        # يمكن إضافة منطق إضافي هنا
    
    def shutdown(self):
        """إغلاق المعالج"""
        logger.info("إغلاق معالج الوسائط المحسن...")
        
        self.queue_system.shutdown()
        self.file_processor.shutdown()
        
        logger.info("تم إغلاق معالج الوسائط المحسن")

# مثيل عام للمعالج
media_handler = OptimizedMediaHandler()