#!/usr/bin/env python3
"""
CRITICAL MEDIA OPTIMIZATION FIX
This implements the core solution to prevent repeated media uploads when watermarks are enabled.

Current Issue:
- Bot processes watermark for each target separately
- Results in multiple uploads of the same media file
- Poor performance with multiple targets

Solution:
- Process media once before target loop
- Cache processed media globally per message
- Reuse cached media for all targets
- Significant performance improvement
"""

import os
import sys
import hashlib
import asyncio
import logging

logger = logging.getLogger(__name__)

async def apply_critical_media_fix():
    """Apply the critical media caching fix to the userbot service"""
    
    # Read the current userbot file
    userbot_file_path = "userbot_service/userbot.py"
    
    if not os.path.exists(userbot_file_path):
        logger.error(f"File not found: {userbot_file_path}")
        return False
    
    with open(userbot_file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # The section we need to replace (exact match needed)
    old_section = '''                    try:
                        if watermark_enabled_for_all:
                            logger.info("🏷️ العلامة المائية مفعلة لكل المهام → سيتم تطبيقها مرة واحدة وإعادة الاستخدام")
                            processed_media, processed_filename = await self.apply_watermark_to_media(event, first_task['id'])
                            if processed_media and processed_media != event.message.media:
                                logger.info(f"✅ تم معالجة الوسائط بنجاح: {processed_filename}")
                            else:
                                logger.info("🔄 لم يتم تطبيق العلامة المائية، استخدام الوسائط الأصلية")'''
    
    # The optimized replacement section
    new_section = '''                    # CRITICAL FIX: Initialize global media cache for message-based reuse
                    if not hasattr(self, 'global_processed_media_cache'):
                        self.global_processed_media_cache = {}
                    
                    # Create unique cache key for this message and settings
                    import hashlib
                    message_hash = f"{event.message.id}_{event.chat_id}_{first_task['id']}_watermark"
                    media_cache_key = hashlib.md5(message_hash.encode()).hexdigest()
                    
                    try:
                        if watermark_enabled_for_all:
                            logger.info("🏷️ العلامة المائية مفعلة لكل المهام → سيتم تطبيقها مرة واحدة وإعادة الاستخدام")
                            
                            # CRITICAL OPTIMIZATION: Check cache before processing
                            if media_cache_key in self.global_processed_media_cache:
                                processed_media, processed_filename = self.global_processed_media_cache[media_cache_key]
                                logger.info(f"🎯 استخدام الوسائط المعالجة من التخزين المؤقت: {processed_filename}")
                            else:
                                # Process media ONLY ONCE and cache for all targets
                                logger.info("🔧 بدء معالجة الوسائط لأول مرة - سيتم حفظها للاستخدام المتكرر")
                                processed_media, processed_filename = await self.apply_watermark_to_media(event, first_task['id'])
                                
                                if processed_media and processed_media != event.message.media:
                                    # Store in global cache for ALL future targets of this message
                                    self.global_processed_media_cache[media_cache_key] = (processed_media, processed_filename)
                                    logger.info(f"✅ تم معالجة الوسائط مرة واحدة وحفظها للاستخدام المتكرر: {processed_filename}")
                                else:
                                    logger.info("🔄 لم يتم تطبيق العلامة المائية، استخدام الوسائط الأصلية")'''
    
    # Apply the replacement
    if old_section in content:
        optimized_content = content.replace(old_section, new_section)
        
        # Write the optimized version
        with open(userbot_file_path, 'w', encoding='utf-8') as f:
            f.write(optimized_content)
        
        logger.info("✅ تم تطبيق الإصلاح الحرج لتحسين معالجة الوسائط")
        return True
    else:
        logger.error("❌ لم يتم العثور على القسم المراد استبداله")
        return False

if __name__ == "__main__":
    asyncio.run(apply_critical_media_fix())