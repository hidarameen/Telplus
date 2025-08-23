#!/usr/bin/env python3
"""
اختبار مبسط لأداء وظيفة العلامة المائية
"""

import sys
import os
import time
import tempfile
import io
from PIL import Image, ImageDraw, ImageFont
import cv2
import numpy as np
import subprocess
import json

# إضافة المسار للوحدات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from watermark_processor import WatermarkProcessor

class SimpleWatermarkTester:
    """مختبر مبسط لأداء وظيفة العلامة المائية"""
    
    def __init__(self):
        self.processor = WatermarkProcessor()
        
    def get_system_info(self):
        """الحصول على معلومات النظام"""
        print("🖥️ معلومات النظام:")
        
        # فحص المعالج
        try:
            with open('/proc/cpuinfo', 'r') as f:
                cpu_info = f.read()
                cpu_count = cpu_info.count('processor')
                print(f"   المعالج: {cpu_count} نواة")
        except:
            print("   المعالج: غير معروف")
        
        # فحص الذاكرة
        try:
            with open('/proc/meminfo', 'r') as f:
                mem_info = f.read()
                total_mem = int(mem_info.split('MemTotal:')[1].split('\n')[0].strip().split()[0])
                print(f"   الذاكرة: {total_mem // 1024 // 1024} GB")
        except:
            print("   الذاكرة: غير معروفة")
        
        print(f"   FFmpeg متوفر: {self.processor.ffmpeg_available}")
        
        # فحص المكتبات
        try:
            import PIL
            print(f"   PIL/Pillow: {PIL.__version__}")
        except:
            print("   PIL/Pillow: غير متوفر")
            
        try:
            print(f"   OpenCV: {cv2.__version__}")
        except:
            print("   OpenCV: غير متوفر")
            
        try:
            import numpy
            print(f"   NumPy: {numpy.__version__}")
        except:
            print("   NumPy: غير متوفر")
    
    def create_test_image(self, width=1920, height=1080, format='JPEG'):
        """إنشاء صورة اختبار"""
        # إنشاء صورة ملونة
        image = Image.new('RGB', (width, height), color=(100, 150, 200))
        draw = ImageDraw.Draw(image)
        
        # إضافة بعض العناصر للصورة
        for i in range(10):
            x1 = np.random.randint(0, width)
            y1 = np.random.randint(0, height)
            x2 = x1 + np.random.randint(50, 200)
            y2 = y1 + np.random.randint(50, 200)
            color = (np.random.randint(0, 255), np.random.randint(0, 255), np.random.randint(0, 255))
            draw.rectangle([x1, y1, x2, y2], fill=color)
        
        # حفظ الصورة في bytes
        img_bytes = io.BytesIO()
        image.save(img_bytes, format=format, quality=95)
        return img_bytes.getvalue()
    
    def create_test_video(self, duration=5, fps=30, width=1280, height=720):
        """إنشاء فيديو اختبار"""
        temp_dir = tempfile.gettempdir()
        video_path = os.path.join(temp_dir, "test_video.mp4")
        
        # إنشاء فيديو باستخدام OpenCV
        fourcc = cv2.VideoWriter.fourcc(*'mp4v')
        out = cv2.VideoWriter(video_path, fourcc, fps, (width, height))
        
        if not out.isOpened():
            return None
        
        # إنشاء إطارات بسيطة
        for i in range(duration * fps):
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            # إضافة لون متغير
            color = (i % 255, (i * 2) % 255, (i * 3) % 255)
            frame[:] = color
            out.write(frame)
        
        out.release()
        return video_path
    
    def test_image_watermark_performance(self):
        """اختبار أداء العلامة المائية على الصور"""
        print("\n🖼️ اختبار أداء العلامة المائية على الصور")
        print("="*60)
        
        image_sizes = [
            (640, 480),    # صغيرة
            (1280, 720),   # متوسطة
            (1920, 1080),  # كبيرة
        ]
        
        watermark_settings = {
            'watermark_type': 'text',
            'watermark_text': 'اختبار العلامة المائية',
            'font_size': 32,
            'text_color': '#FFFFFF',
            'opacity': 70,
            'position': 'bottom_right',
            'offset_x': 0,
            'offset_y': 0
        }
        
        results = {}
        
        for width, height in image_sizes:
            print(f"\n📏 اختبار صورة {width}x{height}:")
            
            # إنشاء صورة اختبار
            start_time = time.time()
            image_bytes = self.create_test_image(width, height)
            creation_time = time.time() - start_time
            
            # تطبيق العلامة المائية
            start_time = time.time()
            try:
                processed_image = self.processor.apply_watermark_to_image(image_bytes, watermark_settings)
                processing_time = time.time() - start_time
                success = processed_image is not None
            except Exception as e:
                processing_time = time.time() - start_time
                success = False
                print(f"   ❌ خطأ: {e}")
            
            # حساب حجم الملف
            original_size = len(image_bytes) / 1024  # KB
            processed_size = len(processed_image) / 1024 if processed_image else 0  # KB
            
            results[f"{width}x{height}"] = {
                'creation_time': creation_time,
                'processing_time': processing_time,
                'original_size': original_size,
                'processed_size': processed_size,
                'success': success
            }
            
            print(f"   ⏱️ وقت الإنشاء: {creation_time:.3f}s")
            print(f"   ⏱️ وقت المعالجة: {processing_time:.3f}s")
            print(f"   📁 الحجم الأصلي: {original_size:.1f} KB")
            print(f"   📁 الحجم المعالج: {processed_size:.1f} KB")
            print(f"   ✅ النجاح: {success}")
        
        return results
    
    def test_video_watermark_performance(self):
        """اختبار أداء العلامة المائية على الفيديوهات"""
        print("\n🎬 اختبار أداء العلامة المائية على الفيديوهات")
        print("="*60)
        
        video_configs = [
            {'duration': 3, 'fps': 30, 'width': 640, 'height': 480},   # صغير
            {'duration': 5, 'fps': 30, 'width': 1280, 'height': 720}, # متوسط
        ]
        
        watermark_settings = {
            'watermark_type': 'text',
            'watermark_text': 'اختبار العلامة المائية',
            'font_size': 32,
            'text_color': '#FFFFFF',
            'opacity': 70,
            'position': 'bottom_right',
            'offset_x': 0,
            'offset_y': 0
        }
        
        results = {}
        
        for config in video_configs:
            duration = config['duration']
            fps = config['fps']
            width = config['width']
            height = config['height']
            
            print(f"\n📹 اختبار فيديو {width}x{height}, {fps} FPS, {duration}s:")
            
            # إنشاء فيديو اختبار
            start_time = time.time()
            video_path = self.create_test_video(duration, fps, width, height)
            creation_time = time.time() - start_time
            
            if not video_path or not os.path.exists(video_path):
                print("   ❌ فشل في إنشاء فيديو اختبار")
                continue
            
            # تطبيق العلامة المائية
            start_time = time.time()
            try:
                processed_video = self.processor.apply_watermark_to_video(video_path, watermark_settings)
                processing_time = time.time() - start_time
                success = processed_video is not None and os.path.exists(processed_video)
            except Exception as e:
                processing_time = time.time() - start_time
                success = False
                print(f"   ❌ خطأ: {e}")
            
            # حساب حجم الملف
            original_size = os.path.getsize(video_path) / 1024 / 1024  # MB
            processed_size = os.path.getsize(processed_video) / 1024 / 1024 if processed_video and os.path.exists(processed_video) else 0  # MB
            
            # حساب سرعة المعالجة
            total_frames = duration * fps
            frames_per_second = total_frames / processing_time if processing_time > 0 else 0
            
            results[f"{width}x{height}_{duration}s"] = {
                'creation_time': creation_time,
                'processing_time': processing_time,
                'original_size': original_size,
                'processed_size': processed_size,
                'frames_per_second': frames_per_second,
                'success': success
            }
            
            print(f"   ⏱️ وقت الإنشاء: {creation_time:.3f}s")
            print(f"   ⏱️ وقت المعالجة: {processing_time:.3f}s")
            print(f"   📁 الحجم الأصلي: {original_size:.1f} MB")
            print(f"   📁 الحجم المعالج: {processed_size:.1f} MB")
            print(f"   🎬 الإطارات/الثانية: {frames_per_second:.1f}")
            print(f"   ✅ النجاح: {success}")
            
            # تنظيف الملفات المؤقتة
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
                if processed_video and os.path.exists(processed_video):
                    os.remove(processed_video)
            except:
                pass
        
        return results
    
    def test_cache_performance(self):
        """اختبار أداء الذاكرة المؤقتة"""
        print("\n💾 اختبار أداء الذاكرة المؤقتة")
        print("="*60)
        
        watermark_settings = {
            'watermark_type': 'text',
            'watermark_text': 'اختبار التخزين المؤقت',
            'font_size': 32,
            'text_color': '#FFFFFF',
            'opacity': 70,
            'position': 'bottom_right'
        }
        
        # إنشاء صورة اختبار
        image_bytes = self.create_test_image(1280, 720)
        
        # اختبار بدون ذاكرة مؤقتة
        start_time = time.time()
        for i in range(5):
            self.processor.apply_watermark_to_image(image_bytes, watermark_settings)
        time_without_cache = time.time() - start_time
        
        # اختبار مع ذاكرة مؤقتة
        start_time = time.time()
        for i in range(5):
            self.processor.process_media_once_for_all_targets(image_bytes, f"test_{i}.jpg", watermark_settings, 1)
        time_with_cache = time.time() - start_time
        
        cache_efficiency = ((time_without_cache - time_with_cache) / time_without_cache) * 100
        
        print(f"⏱️ وقت بدون ذاكرة مؤقتة: {time_without_cache:.3f}s")
        print(f"⏱️ وقت مع ذاكرة مؤقتة: {time_with_cache:.3f}s")
        print(f"📈 كفاءة الذاكرة المؤقتة: {cache_efficiency:.1f}%")
        
        return {
            'time_without_cache': time_without_cache,
            'time_with_cache': time_with_cache,
            'cache_efficiency': cache_efficiency
        }
    
    def analyze_code_complexity(self):
        """تحليل تعقيد الكود"""
        print("\n🔍 تحليل تعقيد الكود")
        print("="*60)
        
        # قراءة ملف watermark_processor.py
        try:
            with open('watermark_processor.py', 'r', encoding='utf-8') as f:
                content = f.read()
            
            lines = content.split('\n')
            total_lines = len(lines)
            code_lines = len([line for line in lines if line.strip() and not line.strip().startswith('#')])
            comment_lines = len([line for line in lines if line.strip().startswith('#')])
            empty_lines = len([line for line in lines if not line.strip()])
            
            # حساب عدد الوظائف
            functions = [line for line in lines if line.strip().startswith('def ')]
            classes = [line for line in lines if line.strip().startswith('class ')]
            
            print(f"📊 إحصائيات الكود:")
            print(f"   إجمالي السطور: {total_lines}")
            print(f"   سطور الكود: {code_lines}")
            print(f"   سطور التعليقات: {comment_lines}")
            print(f"   السطور الفارغة: {empty_lines}")
            print(f"   عدد الوظائف: {len(functions)}")
            print(f"   عدد الكلاسات: {len(classes)}")
            
            # تحليل الوظائف المعقدة
            complex_functions = []
            for func in functions:
                func_name = func.split('def ')[1].split('(')[0]
                # البحث عن السطور في كل وظيفة
                start_idx = lines.index(func)
                indent_level = len(func) - len(func.lstrip())
                
                func_lines = 0
                for i in range(start_idx + 1, len(lines)):
                    if lines[i].strip() and len(lines[i]) - len(lines[i].lstrip()) <= indent_level:
                        break
                    if lines[i].strip():
                        func_lines += 1
                
                if func_lines > 50:  # وظيفة معقدة
                    complex_functions.append((func_name, func_lines))
            
            if complex_functions:
                print(f"\n⚠️ الوظائف المعقدة (أكثر من 50 سطر):")
                for func_name, lines_count in complex_functions:
                    print(f"   {func_name}: {lines_count} سطر")
            else:
                print(f"\n✅ لا توجد وظائف معقدة")
                
        except Exception as e:
            print(f"❌ خطأ في تحليل الكود: {e}")
    
    def generate_performance_report(self):
        """إنشاء تقرير شامل للأداء"""
        print("\n📊 تقرير أداء وظيفة العلامة المائية")
        print("="*60)
        
        # معلومات النظام
        self.get_system_info()
        
        # تحليل تعقيد الكود
        self.analyze_code_complexity()
        
        # اختبار الصور
        image_results = self.test_image_watermark_performance()
        
        # اختبار الفيديوهات
        video_results = self.test_video_watermark_performance()
        
        # اختبار الذاكرة المؤقتة
        cache_results = self.test_cache_performance()
        
        # تحليل النتائج
        print("\n📈 تحليل النتائج:")
        print("="*60)
        
        # تحليل أداء الصور
        if image_results:
            print("\n🖼️ أداء الصور:")
            avg_processing_time = sum(r['processing_time'] for r in image_results.values()) / len(image_results)
            print(f"   متوسط وقت المعالجة: {avg_processing_time:.3f}s")
            
            # أفضل وأسوأ أداء
            best_performance = min(image_results.items(), key=lambda x: x[1]['processing_time'])
            worst_performance = max(image_results.items(), key=lambda x: x[1]['processing_time'])
            print(f"   أفضل أداء: {best_performance[0]} ({best_performance[1]['processing_time']:.3f}s)")
            print(f"   أسوأ أداء: {worst_performance[0]} ({worst_performance[1]['processing_time']:.3f}s)")
        
        # تحليل أداء الفيديو
        if video_results:
            print("\n🎬 أداء الفيديو:")
            successful_videos = {k: v for k, v in video_results.items() if v['success']}
            if successful_videos:
                avg_fps = sum(r['frames_per_second'] for r in successful_videos.values()) / len(successful_videos)
                print(f"   متوسط الإطارات/الثانية: {avg_fps:.1f}")
                
                # أفضل وأسوأ أداء
                best_video = max(successful_videos.items(), key=lambda x: x[1]['frames_per_second'])
                worst_video = min(successful_videos.items(), key=lambda x: x[1]['frames_per_second'])
                print(f"   أفضل أداء: {best_video[0]} ({best_video[1]['frames_per_second']:.1f} FPS)")
                print(f"   أسوأ أداء: {worst_video[0]} ({worst_video[1]['frames_per_second']:.1f} FPS)")
        
        # تحليل الذاكرة المؤقتة
        print(f"\n💾 كفاءة الذاكرة المؤقتة: {cache_results['cache_efficiency']:.1f}%")
        
        # التوصيات
        print("\n💡 التوصيات:")
        print("="*60)
        
        if 'avg_processing_time' in locals() and avg_processing_time > 1.0:
            print("⚠️ وقت معالجة الصور بطيء - فكر في تحسين الخوارزمية")
        else:
            print("✅ أداء معالجة الصور جيد")
        
        if 'avg_fps' in locals() and avg_fps < 10:
            print("⚠️ معالجة الفيديو بطيئة - فكر في استخدام FFmpeg أو تحسين الإعدادات")
        else:
            print("✅ أداء معالجة الفيديو جيد")
        
        if cache_results['cache_efficiency'] < 50:
            print("⚠️ كفاءة الذاكرة المؤقتة منخفضة - فكر في تحسين استراتيجية التخزين المؤقت")
        else:
            print("✅ كفاءة الذاكرة المؤقتة جيدة")
        
        return {
            'image_results': image_results,
            'video_results': video_results,
            'cache_results': cache_results
        }

if __name__ == "__main__":
    tester = SimpleWatermarkTester()
    results = tester.generate_performance_report()