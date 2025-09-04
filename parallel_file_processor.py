#!/usr/bin/env python3
"""
معالج الملفات المتوازي مع تقسيم الملفات
Parallel File Processor with File Chunking
"""

import asyncio
import logging
import threading
import time
import os
import tempfile
import hashlib
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import aiofiles
import aiohttp

logger = logging.getLogger(__name__)

@dataclass
class FileChunk:
    """جزء من ملف"""
    index: int
    data: bytes
    size: int
    hash: str
    start_byte: int
    end_byte: int

@dataclass
class ChunkedUploadSession:
    """جلسة رفع مقسمة"""
    session_id: str
    filename: str
    total_size: int
    chunk_size: int
    total_chunks: int
    uploaded_chunks: List[int]
    failed_chunks: List[int]
    progress: float
    created_at: float

class ParallelFileProcessor:
    """معالج الملفات المتوازي"""
    
    def __init__(self, max_workers: int = 8, chunk_size: int = 10 * 1024 * 1024):
        """
        تهيئة المعالج
        
        Args:
            max_workers: عدد العمال المتوازيين
            chunk_size: حجم كل جزء (افتراضي 10MB)
        """
        self.max_workers = max_workers
        self.chunk_size = chunk_size
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        
        # جلسات الرفع النشطة
        self.active_sessions: Dict[str, ChunkedUploadSession] = {}
        self.session_lock = threading.RLock()
        
        # إحصائيات
        self.stats = {
            'total_files_processed': 0,
            'total_bytes_processed': 0,
            'average_speed_mbps': 0,
            'successful_uploads': 0,
            'failed_uploads': 0
        }
        
        # ذاكرة مؤقتة للأجزاء
        self.chunk_cache = {}
        self.cache_lock = threading.RLock()
    
    def create_file_chunks(self, data: bytes, filename: str) -> List[FileChunk]:
        """تقسيم ملف إلى أجزاء"""
        chunks = []
        total_size = len(data)
        
        logger.info(f"تقسيم الملف {filename} ({total_size} بايت) إلى أجزاء بحجم {self.chunk_size}")
        
        for i in range(0, total_size, self.chunk_size):
            start_byte = i
            end_byte = min(i + self.chunk_size, total_size)
            chunk_data = data[start_byte:end_byte]
            
            chunk = FileChunk(
                index=len(chunks),
                data=chunk_data,
                size=len(chunk_data),
                hash=hashlib.md5(chunk_data).hexdigest(),
                start_byte=start_byte,
                end_byte=end_byte
            )
            chunks.append(chunk)
        
        logger.info(f"تم تقسيم الملف إلى {len(chunks)} جزء")
        return chunks
    
    async def parallel_download(self, url: str, headers: Dict = None, 
                              progress_callback: Callable = None) -> bytes:
        """تحميل متوازي للملفات"""
        
        async with aiohttp.ClientSession() as session:
            # الحصول على معلومات الملف
            async with session.head(url, headers=headers) as response:
                if response.status != 200:
                    raise Exception(f"فشل في الحصول على معلومات الملف: {response.status}")
                
                total_size = int(response.headers.get('Content-Length', 0))
                supports_range = 'bytes' in response.headers.get('Accept-Ranges', '')
            
            if not supports_range or total_size < self.chunk_size:
                # تحميل عادي إذا لم يدعم التحميل المقسم
                return await self._simple_download(session, url, headers, progress_callback)
            
            # تحميل مقسم
            return await self._chunked_download(session, url, headers, total_size, progress_callback)
    
    async def _simple_download(self, session: aiohttp.ClientSession, url: str, 
                             headers: Dict, progress_callback: Callable) -> bytes:
        """تحميل بسيط"""
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                raise Exception(f"فشل في التحميل: {response.status}")
            
            data = await response.read()
            
            if progress_callback:
                progress_callback(len(data), len(data))
            
            return data
    
    async def _chunked_download(self, session: aiohttp.ClientSession, url: str,
                              headers: Dict, total_size: int, 
                              progress_callback: Callable) -> bytes:
        """تحميل مقسم"""
        
        # تقسيم النطاقات
        ranges = []
        for start in range(0, total_size, self.chunk_size):
            end = min(start + self.chunk_size - 1, total_size - 1)
            ranges.append((start, end))
        
        logger.info(f"تحميل مقسم: {len(ranges)} جزء")
        
        # تحميل الأجزاء بشكل متوازي
        chunks = [None] * len(ranges)
        downloaded_bytes = 0
        
        async def download_chunk(index: int, start: int, end: int):
            nonlocal downloaded_bytes
            
            chunk_headers = headers.copy() if headers else {}
            chunk_headers['Range'] = f'bytes={start}-{end}'
            
            async with session.get(url, headers=chunk_headers) as response:
                if response.status not in [200, 206]:
                    raise Exception(f"فشل في تحميل الجزء {index}: {response.status}")
                
                chunk_data = await response.read()
                chunks[index] = chunk_data
                
                downloaded_bytes += len(chunk_data)
                
                if progress_callback:
                    progress_callback(downloaded_bytes, total_size)
        
        # تنفيذ التحميل المتوازي
        tasks = []
        for i, (start, end) in enumerate(ranges):
            task = asyncio.create_task(download_chunk(i, start, end))
            tasks.append(task)
        
        await asyncio.gather(*tasks)
        
        # دمج الأجزاء
        result = b''.join(chunks)
        logger.info(f"تم تحميل {len(result)} بايت بنجاح")
        
        return result
    
    def parallel_upload_chunks(self, chunks: List[FileChunk], upload_func: Callable,
                             progress_callback: Callable = None) -> List[Any]:
        """رفع الأجزاء بشكل متوازي"""
        
        logger.info(f"بدء رفع {len(chunks)} جزء بشكل متوازي")
        start_time = time.time()
        
        # رفع الأجزاء
        futures = []
        for chunk in chunks:
            future = self.executor.submit(upload_func, chunk)
            futures.append((chunk.index, future))
        
        # جمع النتائج
        results = [None] * len(chunks)
        completed_chunks = 0
        
        for chunk_index, future in as_completed([f[1] for f in futures]):
            try:
                # العثور على الفهرس الصحيح
                original_index = None
                for idx, (ci, f) in enumerate(futures):
                    if f == future:
                        original_index = ci
                        break
                
                if original_index is not None:
                    result = future.result()
                    results[original_index] = result
                    completed_chunks += 1
                    
                    if progress_callback:
                        progress = (completed_chunks / len(chunks)) * 100
                        progress_callback(completed_chunks, len(chunks), progress)
                
            except Exception as e:
                logger.error(f"فشل في رفع الجزء: {e}")
                # يمكن إضافة منطق إعادة المحاولة هنا
        
        end_time = time.time()
        total_time = end_time - start_time
        total_size = sum(chunk.size for chunk in chunks)
        speed_mbps = (total_size / (1024 * 1024)) / total_time if total_time > 0 else 0
        
        logger.info(f"تم رفع {len(chunks)} جزء في {total_time:.2f} ثانية ({speed_mbps:.2f} MB/s)")
        
        # تحديث الإحصائيات
        self.stats['total_files_processed'] += 1
        self.stats['total_bytes_processed'] += total_size
        self.stats['successful_uploads'] += completed_chunks
        self.stats['average_speed_mbps'] = (
            (self.stats['average_speed_mbps'] + speed_mbps) / 2
        )
        
        return results
    
    def optimize_chunk_size(self, file_size: int, connection_speed: float = None) -> int:
        """تحسين حجم الأجزاء حسب حجم الملف وسرعة الاتصال"""
        
        # حجم أساسي
        if file_size < 1024 * 1024:  # أقل من 1MB
            return min(file_size, 256 * 1024)  # 256KB
        elif file_size < 10 * 1024 * 1024:  # أقل من 10MB
            return 1024 * 1024  # 1MB
        elif file_size < 100 * 1024 * 1024:  # أقل من 100MB
            return 5 * 1024 * 1024  # 5MB
        else:
            return 10 * 1024 * 1024  # 10MB
        
        # يمكن إضافة منطق أكثر تعقيداً حسب سرعة الاتصال
    
    async def smart_file_transfer(self, data: bytes, filename: str,
                                upload_func: Callable, 
                                progress_callback: Callable = None) -> Any:
        """نقل ملف ذكي مع تحسين تلقائي"""
        
        file_size = len(data)
        logger.info(f"بدء النقل الذكي للملف {filename} ({file_size} بايت)")
        
        # تحسين حجم الأجزاء
        optimal_chunk_size = self.optimize_chunk_size(file_size)
        
        # إذا كان الملف صغير، رفع مباشر
        if file_size <= optimal_chunk_size:
            logger.info("الملف صغير - رفع مباشر")
            if progress_callback:
                progress_callback(0, 1, 0)
            
            result = await asyncio.get_event_loop().run_in_executor(
                self.executor, upload_func, data
            )
            
            if progress_callback:
                progress_callback(1, 1, 100)
            
            return result
        
        # رفع مقسم
        logger.info(f"الملف كبير - رفع مقسم بأجزاء {optimal_chunk_size} بايت")
        
        # تقسيم الملف
        chunks = self.create_file_chunks(data, filename)
        
        # رفع متوازي
        def chunk_upload_wrapper(chunk: FileChunk):
            return upload_func(chunk.data)
        
        results = self.parallel_upload_chunks(chunks, chunk_upload_wrapper, progress_callback)
        
        return results
    
    def create_resumable_upload_session(self, filename: str, total_size: int) -> str:
        """إنشاء جلسة رفع قابلة للاستكمال"""
        
        session_id = hashlib.md5(f"{filename}_{total_size}_{time.time()}".encode()).hexdigest()
        
        session = ChunkedUploadSession(
            session_id=session_id,
            filename=filename,
            total_size=total_size,
            chunk_size=self.chunk_size,
            total_chunks=(total_size + self.chunk_size - 1) // self.chunk_size,
            uploaded_chunks=[],
            failed_chunks=[],
            progress=0.0,
            created_at=time.time()
        )
        
        with self.session_lock:
            self.active_sessions[session_id] = session
        
        logger.info(f"تم إنشاء جلسة رفع: {session_id} للملف {filename}")
        return session_id
    
    def get_session_status(self, session_id: str) -> Optional[ChunkedUploadSession]:
        """الحصول على حالة جلسة الرفع"""
        with self.session_lock:
            return self.active_sessions.get(session_id)
    
    def resume_upload_session(self, session_id: str, data: bytes,
                            upload_func: Callable, progress_callback: Callable = None):
        """استكمال جلسة رفع"""
        
        with self.session_lock:
            session = self.active_sessions.get(session_id)
            if not session:
                raise ValueError(f"جلسة غير موجودة: {session_id}")
        
        # تقسيم البيانات
        chunks = self.create_file_chunks(data, session.filename)
        
        # تحديد الأجزاء المتبقية
        remaining_chunks = []
        for chunk in chunks:
            if chunk.index not in session.uploaded_chunks:
                remaining_chunks.append(chunk)
        
        if not remaining_chunks:
            logger.info(f"جميع الأجزاء تم رفعها للجلسة {session_id}")
            return
        
        logger.info(f"استكمال رفع {len(remaining_chunks)} جزء للجلسة {session_id}")
        
        # رفع الأجزاء المتبقية
        def chunk_upload_wrapper(chunk: FileChunk):
            try:
                result = upload_func(chunk.data)
                
                # تحديث الجلسة
                with self.session_lock:
                    session.uploaded_chunks.append(chunk.index)
                    if chunk.index in session.failed_chunks:
                        session.failed_chunks.remove(chunk.index)
                    
                    session.progress = (len(session.uploaded_chunks) / session.total_chunks) * 100
                
                return result
            except Exception as e:
                # إضافة للأجزاء الفاشلة
                with self.session_lock:
                    if chunk.index not in session.failed_chunks:
                        session.failed_chunks.append(chunk.index)
                raise e
        
        results = self.parallel_upload_chunks(remaining_chunks, chunk_upload_wrapper, progress_callback)
        
        # تنظيف الجلسة إذا اكتملت
        with self.session_lock:
            if len(session.uploaded_chunks) == session.total_chunks:
                del self.active_sessions[session_id]
                logger.info(f"تم إكمال وحذف الجلسة {session_id}")
        
        return results
    
    def get_stats(self) -> Dict:
        """الحصول على إحصائيات المعالج"""
        return {
            'stats': self.stats.copy(),
            'active_sessions': len(self.active_sessions),
            'cache_size': len(self.chunk_cache)
        }
    
    def cleanup_old_sessions(self, max_age_hours: int = 24):
        """تنظيف الجلسات القديمة"""
        current_time = time.time()
        max_age_seconds = max_age_hours * 3600
        
        with self.session_lock:
            expired_sessions = []
            for session_id, session in self.active_sessions.items():
                if current_time - session.created_at > max_age_seconds:
                    expired_sessions.append(session_id)
            
            for session_id in expired_sessions:
                del self.active_sessions[session_id]
                logger.info(f"تم حذف الجلسة المنتهية الصلاحية: {session_id}")
    
    def shutdown(self):
        """إغلاق المعالج"""
        logger.info("إغلاق معالج الملفات المتوازي...")
        self.executor.shutdown(wait=True)
        
        with self.session_lock:
            self.active_sessions.clear()
        
        with self.cache_lock:
            self.chunk_cache.clear()
        
        logger.info("تم إغلاق معالج الملفات المتوازي")

# مثيل عام للمعالج
parallel_processor = ParallelFileProcessor()