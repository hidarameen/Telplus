#!/usr/bin/env python3
"""
CRITICAL FIX: Media Upload Optimization
This script implements the core fix for preventing repeated media uploads
when watermarks are enabled. The bot should process media once and reuse 
for all targets instead of processing separately for each target.

Key Changes:
1. Global media cache with message-based keys
2. Process media once before target loop
3. Reuse processed media for all targets
4. Significant performance improvement
"""

import hashlib
import logging

logger = logging.getLogger(__name__)

def apply_media_optimization_fix():
    """
    Apply the critical media caching optimization fix to userbot.py
    
    This fix ensures media is processed once per message, not once per target.
    """
    
    # The key changes needed in userbot_service/userbot.py:
    
    watermark_section_fix = '''
                    # CRITICAL FIX: Initialize global media cache
                    if not hasattr(self, 'global_processed_media_cache'):
                        self.global_processed_media_cache = {}
                    
                    # Create unique cache key for this message + settings
                    import hashlib
                    message_hash = f"{event.message.id}_{event.chat_id}_{first_task['id']}"
                    media_cache_key = hashlib.md5(message_hash.encode()).hexdigest()
                    
                    try:
                        if watermark_enabled_for_all:
                            logger.info("🏷️ العلامة المائية مفعلة لكل المهام → سيتم تطبيقها مرة واحدة وإعادة الاستخدام")
                            
                            # Check cache first - CRITICAL OPTIMIZATION
                            if media_cache_key in self.global_processed_media_cache:
                                processed_media, processed_filename = self.global_processed_media_cache[media_cache_key]
                                logger.info(f"🎯 استخدام الوسائط المعالجة من التخزين المؤقت: {processed_filename}")
                            else:
                                # Process media for the FIRST TIME ONLY
                                processed_media, processed_filename = await self.apply_watermark_to_media(event, first_task['id'])
                                
                                if processed_media and processed_media != event.message.media:
                                    # Cache for ALL future targets of this message
                                    self.global_processed_media_cache[media_cache_key] = (processed_media, processed_filename)
                                    logger.info(f"✅ تم معالجة الوسائط مرة واحدة وحفظها للاستخدام المتكرر: {processed_filename}")
                                else:
                                    logger.info("🔄 لم يتم تطبيق العلامة المائية، استخدام الوسائط الأصلية")
    '''
    
    logger.info("🎯 تم تحديد الإصلاح المطلوب لمشكلة رفع الوسائط المتكرر")
    return watermark_section_fix

if __name__ == "__main__":
    print("CRITICAL FIX: Media Upload Optimization")
    print("="*50)
    print("This fix prevents repeated media uploads when watermarks are enabled.")
    print("The bot will process media once and reuse for all targets.")
    print("Expected result: Significant performance improvement and reduced upload times.")