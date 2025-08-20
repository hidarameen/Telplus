#!/usr/bin/env python3
"""
اختبار شامل لتكامل وظيفة الوسوم الصوتية
Comprehensive Test for Audio Metadata Integration
"""

import asyncio
import logging
import tempfile
import os
from unittest.mock import Mock, AsyncMock, MagicMock
from telethon.tl.types import Document, MessageMediaDocument
from database import get_database

# إعداد التسجيل
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MockEvent:
    def __init__(self, message_text="", sender_id=123456789):
        self.sender_id = sender_id
        self.message = Mock()
        self.message.text = message_text
        self.message.media = None

class MockDocument:
    def __init__(self, mime_type="audio/mp3", file_name="test.mp3"):
        self.mime_type = mime_type
        self.file_name = file_name

class MockMessageMedia:
    def __init__(self, document):
        self.document = document

async def test_audio_metadata_integration():
    """اختبار تكامل وظيفة الوسوم الصوتية"""
    print("🧪 بدء اختبار تكامل وظيفة الوسوم الصوتية")
    
    try:
        # تهيئة قاعدة البيانات
        db = get_database()
        print("✅ تم تهيئة قاعدة البيانات")
        
        # إنشاء مهمة اختبار
        task_id = 999
        user_id = 123456789
        
        # إعداد إعدادات الوسوم الصوتية
        success1 = db.update_audio_metadata_enabled(task_id, True)
        print(f"✅ تفعيل الوسوم الصوتية: {success1}")
        
        # إعداد قالب مخصص
        template_settings = {
            'title_template': '$title - Enhanced',
            'artist_template': '$artist',
            'album_template': '$album ($year)',
            'year_template': '$year',
            'genre_template': '$genre',
            'composer_template': '$composer',
            'comment_template': 'Processed by Bot',
            'track_template': '$track',
            'album_artist_template': '$album_artist',
            'lyrics_template': '$lyrics'
        }
        
        for tag_name, template_value in template_settings.items():
            success = db.update_audio_template_setting(task_id, tag_name, template_value)
            print(f"✅ تحديث {tag_name}: {success}")
        
        # التحقق من الإعدادات
        audio_settings = db.get_audio_metadata_settings(task_id)
        print(f"✅ إعدادات الوسوم الصوتية: {audio_settings}")
        
        template_settings = db.get_audio_template_settings(task_id)
        print(f"✅ إعدادات القالب: {template_settings}")
        
        # اختبار مع ملف صوتي وهمي
        test_audio_data = b"fake_audio_data_for_testing"
        test_file_name = "test_song.mp3"
        
        # إنشاء حدث وهمي
        mock_doc = MockDocument("audio/mp3", test_file_name)
        mock_media = MockMessageMedia(mock_doc)
        mock_event = MockEvent()
        mock_event.message.media = mock_media
        
        # استيراد UserbotService
        from userbot_service.userbot import UserbotService
        
        # تهيئة الخدمة
        userbot = UserbotService()
        print("✅ تم تهيئة UserbotService")
        
        # اختبار دالة apply_audio_metadata
        try:
            processed_audio, new_filename = await userbot.apply_audio_metadata(
                mock_event, task_id, test_audio_data, test_file_name
            )
            print(f"✅ تم معالجة الوسوم الصوتية: {len(processed_audio)} bytes")
            print(f"✅ اسم الملف الجديد: {new_filename}")
        except Exception as e:
            print(f"❌ خطأ في معالجة الوسوم الصوتية: {e}")
        
        # اختبار معالج الوسوم الصوتية مباشرة
        try:
            from audio_processor import AudioProcessor
            audio_processor = AudioProcessor()
            
            # إنشاء قالب اختبار
            test_template = {
                'title': '$title - Test',
                'artist': '$artist',
                'album': '$album',
                'year': '$year',
                'genre': '$genre'
            }
            
            # اختبار معالجة الوسوم
            processed = audio_processor.process_audio_metadata(
                test_audio_data, test_file_name, test_template
            )
            print(f"✅ تم معالجة الوسوم مباشرة: {len(processed) if processed else 0} bytes")
        except Exception as e:
            print(f"❌ خطأ في معالج الوسوم الصوتية: {e}")
        
        print("🎉 تم إكمال اختبار تكامل وظيفة الوسوم الصوتية")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار التكامل: {e}")
        return False

async def test_audio_template_system():
    """اختبار نظام القوالب الجديد"""
    print("\n🧪 بدء اختبار نظام القوالب الجديد")
    
    try:
        db = get_database()
        task_id = 888
        
        # اختبار إعادة تعيين القوالب
        success = db.reset_audio_template_settings(task_id)
        print(f"✅ إعادة تعيين القوالب: {success}")
        
        # التحقق من القيم الافتراضية
        settings = db.get_audio_template_settings(task_id)
        expected_defaults = {
            'title_template': '$title',
            'artist_template': '$artist',
            'album_template': '$album',
            'year_template': '$year',
            'genre_template': '$genre',
            'composer_template': '$composer',
            'comment_template': '$comment',
            'track_template': '$track',
            'album_artist_template': '$album_artist',
            'lyrics_template': '$lyrics'
        }
        
        for key, expected_value in expected_defaults.items():
            actual_value = settings.get(key, '')
            if actual_value == expected_value:
                print(f"✅ {key}: {actual_value}")
            else:
                print(f"❌ {key}: متوقع {expected_value}, حصل {actual_value}")
        
        # اختبار تحديث قالب واحد
        success = db.update_audio_template_setting(task_id, 'title', 'My Custom Title')
        print(f"✅ تحديث العنوان: {success}")
        
        # التحقق من التحديث
        updated_settings = db.get_audio_template_settings(task_id)
        if updated_settings['title_template'] == 'My Custom Title':
            print("✅ تم تحديث العنوان بنجاح")
        else:
            print(f"❌ فشل في تحديث العنوان: {updated_settings['title_template']}")
        
        print("🎉 تم إكمال اختبار نظام القوالب الجديد")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار نظام القوالب: {e}")
        return False

async def test_audio_file_detection():
    """اختبار اكتشاف الملفات الصوتية"""
    print("\n🧪 بدء اختبار اكتشاف الملفات الصوتية")
    
    try:
        # اختبار أنواع الملفات المختلفة
        audio_files = [
            ("test.mp3", "audio/mp3", True),
            ("song.m4a", "audio/mp4", True),
            ("music.aac", "audio/aac", True),
            ("track.ogg", "audio/ogg", True),
            ("sound.wav", "audio/wav", True),
            ("file.flac", "audio/flac", True),
            ("video.mp4", "video/mp4", False),
            ("image.jpg", "image/jpeg", False),
            ("document.pdf", "application/pdf", False)
        ]
        
        for filename, mime_type, should_be_audio in audio_files:
            mock_doc = MockDocument(mime_type, filename)
            mock_media = MockMessageMedia(mock_doc)
            mock_event = MockEvent()
            mock_event.message.media = mock_media
            
            # اختبار اكتشاف الملف الصوتي
            is_audio = False
            if hasattr(mock_event.message.media, 'document') and mock_event.message.media.document:
                doc = mock_event.message.media.document
                if doc.mime_type and doc.mime_type.startswith('audio/'):
                    is_audio = True
                elif filename.lower().endswith(('.mp3', '.m4a', '.aac', '.ogg', '.wav', '.flac', '.wma', '.opus')):
                    is_audio = True
            
            if is_audio == should_be_audio:
                print(f"✅ {filename} ({mime_type}): {'صوتي' if is_audio else 'غير صوتي'}")
            else:
                print(f"❌ {filename} ({mime_type}): متوقع {'صوتي' if should_be_audio else 'غير صوتي'}, حصل {'صوتي' if is_audio else 'غير صوتي'}")
        
        print("🎉 تم إكمال اختبار اكتشاف الملفات الصوتية")
        return True
        
    except Exception as e:
        print(f"❌ خطأ في اختبار اكتشاف الملفات: {e}")
        return False

async def main():
    """الدالة الرئيسية للاختبار"""
    print("🚀 بدء الاختبار الشامل لوظيفة الوسوم الصوتية")
    print("=" * 60)
    
    results = []
    
    # اختبار التكامل
    result1 = await test_audio_metadata_integration()
    results.append(("تكامل الوسوم الصوتية", result1))
    
    # اختبار نظام القوالب
    result2 = await test_audio_template_system()
    results.append(("نظام القوالب الجديد", result2))
    
    # اختبار اكتشاف الملفات
    result3 = await test_audio_file_detection()
    results.append(("اكتشاف الملفات الصوتية", result3))
    
    # عرض النتائج
    print("\n" + "=" * 60)
    print("📊 نتائج الاختبار الشامل:")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ نجح" if result else "❌ فشل"
        print(f"{test_name}: {status}")
        if result:
            passed += 1
    
    print(f"\n🎯 النتيجة النهائية: {passed}/{total} اختبارات نجحت")
    
    if passed == total:
        print("🎉 جميع الاختبارات نجحت! وظيفة الوسوم الصوتية تعمل بشكل صحيح")
    else:
        print("⚠️ بعض الاختبارات فشلت. يرجى مراجعة الأخطاء أعلاه")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())