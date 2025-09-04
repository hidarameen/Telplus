#!/usr/bin/env python3
"""
نظام الانتظار المتقدم للمعالجة المتوازية
Advanced Queue System for Parallel Processing
"""

import asyncio
import logging
import threading
import time
import uuid
import heapq
import json
import os
from typing import Dict, Optional, List, Any, Callable, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor, as_completed
from queue import Queue, PriorityQueue
from enum import Enum
import multiprocessing

logger = logging.getLogger(__name__)

class TaskPriority(Enum):
    """أولوية المهام"""
    LOW = 1      # منخفضة
    NORMAL = 2   # عادية
    HIGH = 3     # عالية
    URGENT = 4   # عاجلة
    CRITICAL = 5 # حرجة

class TaskStatus(Enum):
    """حالة المهمة"""
    PENDING = "pending"       # في الانتظار
    PROCESSING = "processing" # قيد المعالجة
    COMPLETED = "completed"   # مكتملة
    FAILED = "failed"        # فشلت
    CANCELLED = "cancelled"  # ملغاة

@dataclass
class MediaTask:
    """مهمة معالجة وسائط"""
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: int = 0
    chat_id: int = 0
    message_id: int = 0
    
    # بيانات الوسائط
    media_data: bytes = b''
    filename: str = ""
    file_size: int = 0
    media_type: str = ""  # image, video, audio
    
    # إعدادات المعالجة
    processing_type: str = ""  # watermark, audio_tags, both
    watermark_settings: Optional[Dict] = None
    audio_settings: Optional[Dict] = None
    
    # معلومات المهمة
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    
    # معلومات إضافية
    estimated_time: float = 0  # الوقت المقدر بالثواني
    progress: float = 0        # نسبة الإنجاز 0-100
    error_message: str = ""
    retry_count: int = 0
    max_retries: int = 3
    
    # callbacks
    progress_callback: Optional[Callable] = None
    completion_callback: Optional[Callable] = None
    
    def __lt__(self, other):
        """للمقارنة في PriorityQueue"""
        return self.priority.value > other.priority.value

class ChunkedFile:
    """ملف مقسم إلى أجزاء"""
    def __init__(self, data: bytes, chunk_size: int = 20 * 1024 * 1024):  # 20MB
        self.original_size = len(data)
        self.chunk_size = chunk_size
        self.chunks = []
        self.chunk_count = 0
        
        # تقسيم البيانات
        for i in range(0, len(data), chunk_size):
            chunk = data[i:i + chunk_size]
            self.chunks.append({
                'index': self.chunk_count,
                'data': chunk,
                'size': len(chunk),
                'hash': self._calculate_hash(chunk)
            })
            self.chunk_count += 1
    
    def _calculate_hash(self, data: bytes) -> str:
        """حساب hash للجزء"""
        import hashlib
        return hashlib.md5(data).hexdigest()
    
    def get_chunk(self, index: int) -> Optional[Dict]:
        """الحصول على جزء محدد"""
        if 0 <= index < len(self.chunks):
            return self.chunks[index]
        return None
    
    def reassemble(self) -> bytes:
        """إعادة تجميع الأجزاء"""
        result = b''
        for chunk in self.chunks:
            result += chunk['data']
        return result

class AdvancedQueueSystem:
    """نظام الانتظار المتقدم"""
    
    def __init__(self, max_workers: int = None):
        """تهيئة النظام"""
        self.max_workers = max_workers or min(32, multiprocessing.cpu_count() * 4)
        
        # طوابير المهام
        self.high_priority_queue = PriorityQueue()
        self.normal_priority_queue = PriorityQueue()
        self.low_priority_queue = PriorityQueue()
        
        # معالجات المهام
        self.thread_executor = ThreadPoolExecutor(max_workers=self.max_workers)
        self.process_executor = ProcessPoolExecutor(max_workers=min(8, multiprocessing.cpu_count()))
        
        # إحصائيات
        self.stats = {
            'total_tasks': 0,
            'completed_tasks': 0,
            'failed_tasks': 0,
            'active_tasks': 0,
            'average_processing_time': 0,
            'queue_sizes': {
                'high': 0,
                'normal': 0,
                'low': 0
            }
        }
        
        # مهام نشطة
        self.active_tasks: Dict[str, MediaTask] = {}
        self.task_lock = threading.RLock()
        
        # نظام الذاكرة المؤقتة للنتائج
        self.result_cache = {}
        self.cache_lock = threading.RLock()
        
        # بدء المعالجة
        self.running = True
        self.worker_threads = []
        self._start_workers()
    
    def _start_workers(self):
        """بدء العمال"""
        # عامل للمهام عالية الأولوية
        for i in range(4):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(self.high_priority_queue, f"high_priority_worker_{i}"),
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)
        
        # عمال للمهام عادية الأولوية
        for i in range(self.max_workers - 6):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(self.normal_priority_queue, f"normal_priority_worker_{i}"),
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)
        
        # عمال للمهام منخفضة الأولوية
        for i in range(2):
            thread = threading.Thread(
                target=self._worker_loop,
                args=(self.low_priority_queue, f"low_priority_worker_{i}"),
                daemon=True
            )
            thread.start()
            self.worker_threads.append(thread)
    
    def _worker_loop(self, queue: PriorityQueue, worker_name: str):
        """حلقة العامل"""
        logger.info(f"بدء العامل: {worker_name}")
        
        while self.running:
            try:
                # انتظار مهمة جديدة
                task = queue.get(timeout=1)
                if task is None:
                    continue
                
                logger.info(f"العامل {worker_name} يعالج المهمة {task.task_id}")
                
                # معالجة المهمة
                self._process_task(task, worker_name)
                
                # إنهاء المهمة
                queue.task_done()
                
            except Exception as e:
                logger.error(f"خطأ في العامل {worker_name}: {e}")
                continue
    
    def _process_task(self, task: MediaTask, worker_name: str):
        """معالجة مهمة"""
        try:
            # تحديث حالة المهمة
            with self.task_lock:
                task.status = TaskStatus.PROCESSING
                task.started_at = time.time()
                self.active_tasks[task.task_id] = task
                self.stats['active_tasks'] += 1
            
            # معالجة حسب النوع
            if task.processing_type == "watermark":
                result = self._process_watermark(task)
            elif task.processing_type == "audio_tags":
                result = self._process_audio_tags(task)
            elif task.processing_type == "both":
                result = self._process_both(task)
            else:
                raise ValueError(f"نوع معالجة غير مدعوم: {task.processing_type}")
            
            # تحديث النتيجة
            with self.task_lock:
                task.status = TaskStatus.COMPLETED
                task.completed_at = time.time()
                task.progress = 100
                
                # حفظ في الذاكرة المؤقتة
                cache_key = self._generate_cache_key(task)
                with self.cache_lock:
                    self.result_cache[cache_key] = result
                
                # إحصائيات
                self.stats['completed_tasks'] += 1
                self.stats['active_tasks'] -= 1
                
                # حساب متوسط وقت المعالجة
                processing_time = task.completed_at - task.started_at
                current_avg = self.stats['average_processing_time']
                total_completed = self.stats['completed_tasks']
                self.stats['average_processing_time'] = (
                    (current_avg * (total_completed - 1) + processing_time) / total_completed
                )
            
            # استدعاء callback الإكمال
            if task.completion_callback:
                try:
                    task.completion_callback(task, result)
                except Exception as e:
                    logger.error(f"خطأ في callback الإكمال: {e}")
            
            logger.info(f"تم إنجاز المهمة {task.task_id} في {processing_time:.2f} ثانية")
            
        except Exception as e:
            logger.error(f"خطأ في معالجة المهمة {task.task_id}: {e}")
            
            # تحديث حالة الفشل
            with self.task_lock:
                task.status = TaskStatus.FAILED
                task.error_message = str(e)
                task.completed_at = time.time()
                self.stats['failed_tasks'] += 1
                self.stats['active_tasks'] -= 1
                
                # إعادة المحاولة إذا لم تتجاوز الحد الأقصى
                if task.retry_count < task.max_retries:
                    task.retry_count += 1
                    task.status = TaskStatus.PENDING
                    logger.info(f"إعادة محاولة للمهمة {task.task_id} (المحاولة {task.retry_count})")
                    self.add_task(task)
    
    def add_task(self, task: MediaTask) -> str:
        """إضافة مهمة جديدة"""
        # التحقق من الذاكرة المؤقتة أولاً
        cache_key = self._generate_cache_key(task)
        with self.cache_lock:
            if cache_key in self.result_cache:
                logger.info(f"نتيجة المهمة {task.task_id} موجودة في الذاكرة المؤقتة")
                if task.completion_callback:
                    task.completion_callback(task, self.result_cache[cache_key])
                return task.task_id
        
        # تقدير وقت المعالجة
        task.estimated_time = self._estimate_processing_time(task)
        
        # إضافة للطابور المناسب
        if task.priority in [TaskPriority.URGENT, TaskPriority.CRITICAL]:
            self.high_priority_queue.put(task)
            self.stats['queue_sizes']['high'] += 1
        elif task.priority == TaskPriority.HIGH:
            self.normal_priority_queue.put(task)
            self.stats['queue_sizes']['normal'] += 1
        else:
            self.low_priority_queue.put(task)
            self.stats['queue_sizes']['low'] += 1
        
        self.stats['total_tasks'] += 1
        logger.info(f"تمت إضافة المهمة {task.task_id} بأولوية {task.priority.name}")
        
        return task.task_id
    
    def _generate_cache_key(self, task: MediaTask) -> str:
        """إنشاء مفتاح الذاكرة المؤقتة"""
        import hashlib
        key_data = f"{task.processing_type}_{task.filename}_{len(task.media_data)}"
        if task.watermark_settings:
            key_data += f"_{json.dumps(task.watermark_settings, sort_keys=True)}"
        if task.audio_settings:
            key_data += f"_{json.dumps(task.audio_settings, sort_keys=True)}"
        
        return hashlib.md5(key_data.encode()).hexdigest()
    
    def _estimate_processing_time(self, task: MediaTask) -> float:
        """تقدير وقت المعالجة"""
        base_time = 1.0  # ثانية واحدة أساسية
        
        # حسب حجم الملف
        size_factor = task.file_size / (1024 * 1024)  # MB
        if task.media_type == "video":
            base_time += size_factor * 2  # فيديو أبطأ
        elif task.media_type == "image":
            base_time += size_factor * 0.5
        else:
            base_time += size_factor * 1
        
        # حسب نوع المعالجة
        if task.processing_type == "both":
            base_time *= 1.5
        
        return max(base_time, 0.5)  # على الأقل نصف ثانية
    
    def _process_watermark(self, task: MediaTask) -> Dict:
        """معالجة العلامة المائية"""
        # هنا يتم استدعاء معالج العلامة المائية المحسن
        from watermark_processor_ultra_optimized import UltraOptimizedWatermarkProcessor
        
        processor = UltraOptimizedWatermarkProcessor()
        
        # تحديث التقدم
        if task.progress_callback:
            task.progress_callback(task.task_id, 25)
        
        # معالجة العلامة المائية
        result_data = processor.process_media_bytes(
            task.media_data,
            task.filename,
            task.watermark_settings or {}
        )
        
        if task.progress_callback:
            task.progress_callback(task.task_id, 100)
        
        return {
            'processed_data': result_data,
            'filename': task.filename,
            'processing_type': 'watermark'
        }
    
    def _process_audio_tags(self, task: MediaTask) -> Dict:
        """معالجة الوسوم الصوتية"""
        # هنا يتم استدعاء معالج الوسوم الصوتية
        from audio_processor import AudioProcessor
        
        processor = AudioProcessor()
        
        if task.progress_callback:
            task.progress_callback(task.task_id, 25)
        
        # معالجة الوسوم
        result_data = processor.process_audio_tags(
            task.media_data,
            task.filename,
            task.audio_settings or {}
        )
        
        if task.progress_callback:
            task.progress_callback(task.task_id, 100)
        
        return {
            'processed_data': result_data,
            'filename': task.filename,
            'processing_type': 'audio_tags'
        }
    
    def _process_both(self, task: MediaTask) -> Dict:
        """معالجة كلا النوعين"""
        if task.progress_callback:
            task.progress_callback(task.task_id, 10)
        
        # معالجة العلامة المائية أولاً
        watermark_result = self._process_watermark(task)
        
        if task.progress_callback:
            task.progress_callback(task.task_id, 60)
        
        # ثم معالجة الوسوم الصوتية
        task.media_data = watermark_result['processed_data']
        audio_result = self._process_audio_tags(task)
        
        if task.progress_callback:
            task.progress_callback(task.task_id, 100)
        
        return {
            'processed_data': audio_result['processed_data'],
            'filename': task.filename,
            'processing_type': 'both'
        }
    
    def get_task_status(self, task_id: str) -> Optional[MediaTask]:
        """الحصول على حالة المهمة"""
        with self.task_lock:
            return self.active_tasks.get(task_id)
    
    def cancel_task(self, task_id: str) -> bool:
        """إلغاء مهمة"""
        with self.task_lock:
            task = self.active_tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.status = TaskStatus.CANCELLED
                return True
        return False
    
    def get_queue_stats(self) -> Dict:
        """الحصول على إحصائيات الطوابير"""
        return {
            'stats': self.stats.copy(),
            'queue_sizes': {
                'high_priority': self.high_priority_queue.qsize(),
                'normal_priority': self.normal_priority_queue.qsize(),
                'low_priority': self.low_priority_queue.qsize()
            },
            'active_tasks': len(self.active_tasks),
            'cache_size': len(self.result_cache)
        }
    
    def shutdown(self):
        """إيقاف النظام"""
        logger.info("إيقاف نظام الانتظار...")
        self.running = False
        
        # إنهاء العمال
        for _ in self.worker_threads:
            self.high_priority_queue.put(None)
            self.normal_priority_queue.put(None)
            self.low_priority_queue.put(None)
        
        # انتظار انتهاء العمال
        for thread in self.worker_threads:
            thread.join(timeout=5)
        
        # إغلاق المعالجات
        self.thread_executor.shutdown(wait=True)
        self.process_executor.shutdown(wait=True)
        
        logger.info("تم إيقاف نظام الانتظار")

# مثيل عام للنظام
queue_system = AdvancedQueueSystem()