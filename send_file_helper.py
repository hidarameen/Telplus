"""
مساعد لإرسال الملفات مع اسم مخصص في Telethon
يحل مشكلة إرسال البيانات الخام (bytes) مع اسم ملف صحيح
"""
import io
import logging
from typing import Union, Optional

logger = logging.getLogger(__name__)

class TelethonFileSender:
    """مساعد لإرسال الملفات مع أسماء صحيحة"""
    
    @staticmethod
    async def send_file_with_name(client, entity, file_data: Union[bytes, any], filename: str, **kwargs):
        """
        إرسال ملف مع اسم مخصص
        يحل مشكلة Telethon مع البيانات الخام والأسماء المخصصة
        """
        try:
            # إذا كانت البيانات هي bytes، نحتاج لاستخدام upload_file أولاً
            if isinstance(file_data, bytes):
                logger.info(f"📤 إرسال ملف bytes مع اسم: {filename}")
                
                # رفع الملف أولاً مع الاسم المخصص
                file_handle = await client.upload_file(
                    file=io.BytesIO(file_data),
                    file_name=filename
                )
                
                # إرسال الملف المرفوع
                return await client.send_file(entity, file_handle, **kwargs)
            else:
                # للأنواع الأخرى، استخدم الطريقة العادية
                logger.info(f"📤 إرسال ملف عادي مع اسم: {filename}")
                return await client.send_file(entity, file_data, file_name=filename, **kwargs)
                
        except Exception as e:
            logger.error(f"❌ خطأ في إرسال الملف {filename}: {e}")
            # في حالة الخطأ، حاول الإرسال بدون اسم مخصص
            return await client.send_file(entity, file_data, **kwargs)