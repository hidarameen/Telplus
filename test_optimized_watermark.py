#!/usr/bin/env python3
"""
اختبار السرعة المحسنة لوظيفة العلامة المائية
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

# إضافة المسار للوحدات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from watermark_processor import WatermarkProcessor
from watermark_processor_optimized import OptimizedWatermarkProcessor

class SpeedComparisonTester:
    """مقارنة السرعة بين المعالج الأصلي والمحسن"""
    
    def __init__(self):
        self.original_processor = WatermarkProcessor()
        self.optimized_processor = OptimizedWatermarkProcessor()
        
    def create_test_video(self, duration=10, fps=30, width=1280, height=720):
        """إنشاء فيديو اختبار"""
        temp_dir = tempfile.gettempdir()
        video_path = os.path.join(temp_dir, "speed_test_video.mp4")
        
        # إنشاء فيديو باستخدام FFmpeg إذا كان متوفراً
        if self.original_processor.ffmpeg_available:
            cmd = [
                'ffmpeg', '-y', '-f', 'lavfi', '-i', 
                f'testsrc=duration={duration}:size={width}x{height}:rate={fps}',
                '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                video_path
            ]
            
            try:
                subprocess.run(cmd, check=True, capture_output=True, timeout=60)
                return video_path
            except:
                pass
        
        # إنشاء فيديو باستخدام OpenCV كبديل
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
    
    def test_original_vs_optimized(self):
        """مقارنة السرعة بين المعالج الأصلي والمحسن"""
        print("⚡ مقارنة السرعة بين المعالج الأصلي والمحسن")
        print("="*60)
        
        # إعدادات العلامة المائية
        watermark_settings = {
            'watermark_type': 'text',
            'watermark_text': 'اختبار السرعة',
            'font_size': 32,
            'text_color': '#FFFFFF',
            'opacity': 70,
            'position': 'bottom_right',
            'offset_x': 0,
            'offset_y': 0
        }
        
        # إنشاء فيديو اختبار
        print("🎬 إنشاء فيديو اختبار...")
        video_path = self.create_test_video(duration=10, fps=30, width=1280, height=720)
        
        if not video_path or not os.path.exists(video_path):
            print("❌ فشل في إنشاء فيديو اختبار")
            return
        
        video_size = os.path.getsize(video_path) / 1024 / 1024  # MB
        print(f"📹 حجم الفيديو: {video_size:.1f} MB")
        
        # اختبار المعالج الأصلي
        print("\n🔄 اختبار المعالج الأصلي...")
        start_time = time.time()
        try:
            result_original = self.original_processor.apply_watermark_to_video(video_path, watermark_settings)
            time_original = time.time() - start_time
            success_original = result_original is not None and os.path.exists(result_original)
        except Exception as e:
            time_original = time.time() - start_time
            success_original = False
            print(f"   ❌ خطأ: {e}")
        
        print(f"   ⏱️ الوقت: {time_original:.1f}s")
        print(f"   ✅ النجاح: {success_original}")
        
        # اختبار المعالج المحسن
        print("\n⚡ اختبار المعالج المحسن...")
        start_time = time.time()
        try:
            result_optimized = self.optimized_processor.apply_watermark_to_video_fast(video_path, watermark_settings)
            time_optimized = time.time() - start_time
            success_optimized = result_optimized is not None and os.path.exists(result_optimized)
        except Exception as e:
            time_optimized = time.time() - start_time
            success_optimized = False
            print(f"   ❌ خطأ: {e}")
        
        print(f"   ⏱️ الوقت: {time_optimized:.1f}s")
        print(f"   ✅ النجاح: {success_optimized}")
        
        # تحليل النتائج
        print("\n📊 تحليل النتائج:")
        print("="*60)
        
        if success_original and success_optimized:
            speedup = time_original / time_optimized if time_optimized > 0 else 0
            time_saved = time_original - time_optimized
            percentage_improvement = ((time_original - time_optimized) / time_original) * 100
            
            print(f"🚀 تحسين السرعة: {speedup:.1f}x أسرع")
            print(f"⏰ الوقت المحفوظ: {time_saved:.1f}s")
            print(f"📈 نسبة التحسين: {percentage_improvement:.1f}%")
            
            if speedup >= 4:
                print("🎉 تم تحقيق الهدف! السرعة 4x أسرع أو أكثر")
            elif speedup >= 2:
                print("✅ تحسين جيد! السرعة 2x أسرع")
            else:
                print("⚠️ التحسين محدود، قد تحتاج لمزيد من التحسينات")
        else:
            print("❌ فشل في أحد الاختبارات")
        
        # تنظيف الملفات
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            if success_original and result_original and os.path.exists(result_original):
                os.remove(result_original)
            if success_optimized and result_optimized and os.path.exists(result_optimized):
                os.remove(result_optimized)
        except:
            pass
    
    def test_different_video_sizes(self):
        """اختبار سرعات مختلفة لأحجام فيديو مختلفة"""
        print("\n📏 اختبار سرعات مختلفة لأحجام فيديو مختلفة")
        print("="*60)
        
        video_configs = [
            {'duration': 5, 'fps': 30, 'width': 640, 'height': 480, 'name': 'صغير'},
            {'duration': 10, 'fps': 30, 'width': 1280, 'height': 720, 'name': 'متوسط'},
            {'duration': 15, 'fps': 30, 'width': 1920, 'height': 1080, 'name': 'كبير'},
        ]
        
        watermark_settings = {
            'watermark_type': 'text',
            'watermark_text': 'اختبار السرعة',
            'font_size': 32,
            'text_color': '#FFFFFF',
            'opacity': 70,
            'position': 'bottom_right',
        }
        
        results = {}
        
        for config in video_configs:
            print(f"\n🎬 اختبار فيديو {config['name']} ({config['width']}x{config['height']}):")
            
            # إنشاء فيديو
            video_path = self.create_test_video(
                config['duration'], config['fps'], config['width'], config['height']
            )
            
            if not video_path or not os.path.exists(video_path):
                print("   ❌ فشل في إنشاء فيديو")
                continue
            
            video_size = os.path.getsize(video_path) / 1024 / 1024  # MB
            print(f"   📁 الحجم: {video_size:.1f} MB")
            
            # اختبار المعالج المحسن فقط (للتوفير)
            start_time = time.time()
            try:
                result = self.optimized_processor.apply_watermark_to_video_fast(video_path, watermark_settings)
                processing_time = time.time() - start_time
                success = result is not None and os.path.exists(result)
            except Exception as e:
                processing_time = time.time() - start_time
                success = False
                print(f"   ❌ خطأ: {e}")
            
            print(f"   ⏱️ الوقت: {processing_time:.1f}s")
            print(f"   ✅ النجاح: {success}")
            
            # حساب السرعة
            total_frames = config['duration'] * config['fps']
            frames_per_second = total_frames / processing_time if processing_time > 0 else 0
            print(f"   🎬 الإطارات/الثانية: {frames_per_second:.1f}")
            
            results[config['name']] = {
                'size_mb': video_size,
                'processing_time': processing_time,
                'frames_per_second': frames_per_second,
                'success': success
            }
            
            # تنظيف
            try:
                if os.path.exists(video_path):
                    os.remove(video_path)
                if success and result and os.path.exists(result):
                    os.remove(result)
            except:
                pass
        
        # تحليل النتائج
        print("\n📊 تحليل الأداء حسب الحجم:")
        print("="*60)
        
        for name, result in results.items():
            if result['success']:
                print(f"{name}: {result['processing_time']:.1f}s ({result['frames_per_second']:.1f} FPS)")
            else:
                print(f"{name}: فشل في المعالجة")

if __name__ == "__main__":
    tester = SpeedComparisonTester()
    tester.test_original_vs_optimized()
    tester.test_different_video_sizes()