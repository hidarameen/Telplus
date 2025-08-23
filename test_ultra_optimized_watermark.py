#!/usr/bin/env python3
"""
اختبار شامل للمعالج المحسن للغاية للعلامة المائية
"""

import sys
import os
import time
import tempfile
import asyncio
import subprocess

# إضافة المسار للوحدات
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from watermark_processor import WatermarkProcessor
from watermark_processor_optimized import OptimizedWatermarkProcessor
from watermark_processor_ultra_optimized import UltraOptimizedWatermarkProcessor

class UltraOptimizedTester:
    """اختبار شامل للمعالج المحسن للغاية"""
    
    def __init__(self):
        self.original_processor = WatermarkProcessor()
        self.optimized_processor = OptimizedWatermarkProcessor()
        self.ultra_optimized_processor = UltraOptimizedWatermarkProcessor()
        
    def create_test_video(self, duration=10, fps=30, width=1280, height=720):
        """إنشاء فيديو اختبار"""
        temp_dir = tempfile.gettempdir()
        video_path = os.path.join(temp_dir, "ultra_test_video.mp4")
        
        # إنشاء فيديو باستخدام FFmpeg
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
        
        return None
    
    async def test_all_processors(self):
        """اختبار جميع المعالجات"""
        print("🎯 اختبار شامل لجميع المعالجات")
        print("="*60)
        
        # إنشاء فيديو اختبار
        video_path = self.create_test_video(duration=10, fps=30, width=1280, height=720)
        
        if not video_path or not os.path.exists(video_path):
            print("❌ فشل في إنشاء فيديو اختبار")
            return
        
        video_size = os.path.getsize(video_path) / 1024 / 1024  # MB
        print(f"📹 حجم الفيديو: {video_size:.1f} MB")
        
        # إعدادات العلامة المائية
        watermark_settings = {
            'watermark_type': 'text',
            'watermark_text': 'اختبار شامل',
            'font_size': 32,
            'text_color': '#FFFFFF',
            'opacity': 70,
            'position': 'bottom_right',
            'offset_x': 0,
            'offset_y': 0
        }
        
        # قراءة الفيديو كـ bytes
        with open(video_path, 'rb') as f:
            video_bytes = f.read()
        
        results = {}
        
        # اختبار المعالج الأصلي
        print("\n🔄 اختبار المعالج الأصلي (إطار بإطار):")
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
        results['original'] = {'time': time_original, 'success': success_original}
        
        # اختبار المعالج المحسن
        print("\n⚡ اختبار المعالج المحسن (FFmpeg):")
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
        results['optimized'] = {'time': time_optimized, 'success': success_optimized}
        
        # اختبار المعالج المحسن للغاية
        print("\n🚀 اختبار المعالج المحسن للغاية (معالجة متوازية):")
        start_time = time.time()
        try:
            result_ultra = await self.ultra_optimized_processor.process_media_ultra_fast(
                video_bytes, "test_video.mp4", watermark_settings, 1
            )
            time_ultra = time.time() - start_time
            success_ultra = result_ultra is not None and len(result_ultra) > 0
        except Exception as e:
            time_ultra = time.time() - start_time
            success_ultra = False
            print(f"   ❌ خطأ: {e}")
        
        print(f"   ⏱️ الوقت: {time_ultra:.1f}s")
        print(f"   ✅ النجاح: {success_ultra}")
        results['ultra'] = {'time': time_ultra, 'success': success_ultra}
        
        # تحليل النتائج
        print("\n📊 تحليل النتائج:")
        print("="*60)
        
        if all(result['success'] for result in results.values()):
            # حساب التحسينات
            original_time = results['original']['time']
            optimized_speedup = original_time / results['optimized']['time'] if results['optimized']['time'] > 0 else 0
            ultra_speedup = original_time / results['ultra']['time'] if results['ultra']['time'] > 0 else 0
            
            print(f"🔄 المعالج الأصلي: {original_time:.1f}s (1x)")
            print(f"⚡ المعالج المحسن: {results['optimized']['time']:.1f}s ({optimized_speedup:.1f}x أسرع)")
            print(f"🚀 المعالج المحسن للغاية: {results['ultra']['time']:.1f}s ({ultra_speedup:.1f}x أسرع)")
            
            # إحصائيات المعالج المحسن للغاية
            stats = self.ultra_optimized_processor.get_performance_stats()
            print(f"\n📈 إحصائيات المعالج المحسن للغاية:")
            print(f"   🎯 معدل نجاح الذاكرة المؤقتة: {stats.get('cache_hit_rate', 0):.1f}%")
            print(f"   ⏱️ متوسط وقت المعالجة: {stats.get('avg_processing_time', 0):.2f}s")
            print(f"   📦 عدد العناصر في الذاكرة المؤقتة: {stats.get('cache_size', 0)}")
            print(f"   🎯 عدد النجاحات في الذاكرة المؤقتة: {stats.get('cache_hits', 0)}")
            print(f"   ❌ عدد الفشل في الذاكرة المؤقتة: {stats.get('cache_misses', 0)}")
            
            if ultra_speedup >= 10:
                print("🎉 تحسين مذهل! السرعة 10x أسرع أو أكثر")
            elif ultra_speedup >= 5:
                print("🚀 تحسين ممتاز! السرعة 5x أسرع")
            elif ultra_speedup >= 2:
                print("✅ تحسين جيد! السرعة 2x أسرع")
            else:
                print("⚠️ التحسين محدود")
        else:
            print("❌ فشل في أحد الاختبارات")
        
        # تنظيف الملفات
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
            for result_name, result_data in results.items():
                if result_name == 'original' and result_data.get('result_path'):
                    os.remove(result_data['result_path'])
                elif result_name == 'optimized' and result_data.get('result_path'):
                    os.remove(result_data['result_path'])
        except:
            pass
    
    async def test_cache_efficiency(self):
        """اختبار كفاءة الذاكرة المؤقتة"""
        print("\n🎯 اختبار كفاءة الذاكرة المؤقتة")
        print("="*60)
        
        # إنشاء فيديو صغير للاختبار
        video_path = self.create_test_video(duration=5, fps=30, width=640, height=480)
        
        if not video_path or not os.path.exists(video_path):
            print("❌ فشل في إنشاء فيديو اختبار")
            return
        
        with open(video_path, 'rb') as f:
            video_bytes = f.read()
        
        watermark_settings = {
            'watermark_type': 'text',
            'watermark_text': 'اختبار الذاكرة المؤقتة',
            'font_size': 32,
            'text_color': '#FFFFFF',
            'opacity': 70,
            'position': 'bottom_right',
        }
        
        # اختبار معالجة متكررة لنفس الفيديو
        print("🔄 اختبار معالجة متكررة لنفس الفيديو...")
        
        times = []
        for i in range(5):
            start_time = time.time()
            try:
                result = await self.ultra_optimized_processor.process_media_ultra_fast(
                    video_bytes, f"test_video_{i}.mp4", watermark_settings, 1
                )
                processing_time = time.time() - start_time
                times.append(processing_time)
                print(f"   المحاولة {i+1}: {processing_time:.2f}s")
            except Exception as e:
                print(f"   ❌ خطأ في المحاولة {i+1}: {e}")
        
        if times:
            first_time = times[0]
            avg_time = sum(times[1:]) / len(times[1:]) if len(times) > 1 else first_time
            cache_improvement = first_time / avg_time if avg_time > 0 else 1
            
            print(f"\n📊 نتائج اختبار الذاكرة المؤقتة:")
            print(f"   ⏱️ الوقت الأول: {first_time:.2f}s")
            print(f"   ⏱️ متوسط الوقت اللاحق: {avg_time:.2f}s")
            print(f"   🎯 تحسين الذاكرة المؤقتة: {cache_improvement:.1f}x أسرع")
            
            if cache_improvement >= 5:
                print("🎉 كفاءة ذاكرة مؤقتة ممتازة!")
            elif cache_improvement >= 2:
                print("✅ كفاءة ذاكرة مؤقتة جيدة")
            else:
                print("⚠️ كفاءة ذاكرة مؤقتة محدودة")
        
        # تنظيف
        try:
            if os.path.exists(video_path):
                os.remove(video_path)
        except:
            pass

async def main():
    """الدالة الرئيسية"""
    tester = UltraOptimizedTester()
    
    # اختبار جميع المعالجات
    await tester.test_all_processors()
    
    # اختبار كفاءة الذاكرة المؤقتة
    await tester.test_cache_efficiency()
    
    print("\n🎉 انتهى الاختبار الشامل!")

if __name__ == "__main__":
    asyncio.run(main())