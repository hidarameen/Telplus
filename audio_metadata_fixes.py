"""
إصلاحات قسم الوسوم الصوتية
"""

async def show_album_art_options_fixed(self, event, task_id: int):
    """Show album art options - Fixed version"""
    user_id = event.sender_id
    task = self.db.get_task(task_id, user_id)
    
    if not task:
        await event.answer("❌ المهمة غير موجودة")
        return
    
    task_name = task.get('task_name', 'مهمة بدون اسم')
    
    # Get current album art options
    settings = self.db.get_audio_metadata_settings(task_id)
    art_enabled = settings.get('album_art_enabled', False)
    apply_to_all = settings.get('apply_art_to_all', False)
    
    art_status = "🟢 مفعل" if art_enabled else "🔴 معطل"
    apply_all_status = "🟢 نعم" if apply_to_all else "🔴 لا"
    
    buttons = [
        [Button.inline(f"🔄 تبديل صورة الغلاف ({art_status.split()[0]})", f"toggle_album_art_enabled_{task_id}")],
        [Button.inline(f"📦 تطبيق على جميع الملفات ({apply_all_status.split()[0]})", f"toggle_apply_art_to_all_{task_id}")],
        [Button.inline("🔙 رجوع لإعدادات صورة الغلاف", f"album_art_settings_{task_id}")]
    ]
    
    message_text = (
        f"⚙️ خيارات تطبيق صورة الغلاف للمهمة: {task_name}\n\n"
        f"📝 الوصف:\n"
        f"• تطبيق على جميع الملفات: استبدال جميع صور الغلاف\n"
        f"• تطبيق على الملفات بدون صورة: إضافة صورة فقط للملفات الفارغة\n"
        f"• الحفاظ على الجودة 100%\n"
        f"• دعم الصيغ: JPG, PNG, BMP, TIFF\n\n"
        f"📊 الحالة الحالية:\n"
        f"• تفعيل صورة الغلاف: {art_status}\n"
        f"• تطبيق على الجميع: {apply_all_status}\n\n"
        f"اختر الإعداد الذي تريد تعديله:"
    )
    
    await self.edit_or_send_message(event, message_text, buttons=buttons)

async def show_intro_audio_settings_fixed(self, event, task_id: int):
    """Show intro audio settings - Fixed version"""
    user_id = event.sender_id
    task = self.db.get_task(task_id, user_id)
    
    if not task:
        await event.answer("❌ المهمة غير موجودة")
        return
    
    task_name = task.get('task_name', 'مهمة بدون اسم')
    
    # Get current intro settings
    settings = self.db.get_audio_metadata_settings(task_id)
    intro_path = settings.get('intro_path', '')
    
    intro_path_display = intro_path if intro_path else "غير محدد"
    
    buttons = [
        [Button.inline("🎵 رفع مقطع مقدمة", f"upload_intro_audio_{task_id}")],
        [Button.inline("🗑️ حذف مقطع مقدمة", f"remove_intro_audio_{task_id}")] if intro_path else [],
        [Button.inline("🔙 رجوع لإعدادات دمج المقاطع", f"audio_merge_settings_{task_id}")]
    ]
    
    # Remove empty button rows
    buttons = [row for row in buttons if row]
    
    message_text = (
        f"🎵 إعدادات مقطع المقدمة للمهمة: {task_name}\n\n"
        f"📝 الوصف:\n"
        f"• إضافة مقطع صوتي في بداية كل ملف\n"
        f"• دعم جميع الصيغ الصوتية\n"
        f"• جودة عالية 320k MP3\n"
        f"• يمكن اختيار موضع المقدمة\n\n"
        f"📊 الحالة الحالية:\n"
        f"• مقطع مقدمة: {intro_path_display}\n\n"
        f"اختر الإعداد الذي تريد تعديله:"
    )
    
    await self.edit_or_send_message(event, message_text, buttons=buttons)

async def show_outro_audio_settings_fixed(self, event, task_id: int):
    """Show outro audio settings - Fixed version"""
    user_id = event.sender_id
    task = self.db.get_task(task_id, user_id)
    
    if not task:
        await event.answer("❌ المهمة غير موجودة")
        return
    
    task_name = task.get('task_name', 'مهمة بدون اسم')
    
    # Get current outro settings
    settings = self.db.get_audio_metadata_settings(task_id)
    outro_path = settings.get('outro_path', '')
    
    outro_path_display = outro_path if outro_path else "غير محدد"
    
    buttons = [
        [Button.inline("🎵 رفع مقطع خاتمة", f"upload_outro_audio_{task_id}")],
        [Button.inline("🗑️ حذف مقطع خاتمة", f"remove_outro_audio_{task_id}")] if outro_path else [],
        [Button.inline("🔙 رجوع لإعدادات دمج المقاطع", f"audio_merge_settings_{task_id}")]
    ]
    
    # Remove empty button rows
    buttons = [row for row in buttons if row]
    
    message_text = (
        f"🎵 إعدادات مقطع الخاتمة للمهمة: {task_name}\n\n"
        f"📝 الوصف:\n"
        f"• إضافة مقطع صوتي في نهاية كل ملف\n"
        f"• دعم جميع الصيغ الصوتية\n"
        f"• جودة عالية 320k MP3\n"
        f"• يتم إضافته دائماً في النهاية\n\n"
        f"📊 الحالة الحالية:\n"
        f"• مقطع خاتمة: {outro_path_display}\n\n"
        f"اختر الإعداد الذي تريد تعديله:"
    )
    
    await self.edit_or_send_message(event, message_text, buttons=buttons)

async def show_merge_options_fixed(self, event, task_id: int):
    """Show merge options - Fixed version"""
    user_id = event.sender_id
    task = self.db.get_task(task_id, user_id)
    
    if not task:
        await event.answer("❌ المهمة غير موجودة")
        return
    
    task_name = task.get('task_name', 'مهمة بدون اسم')
    
    # Get current merge options
    settings = self.db.get_audio_metadata_settings(task_id)
    intro_position = settings.get('intro_position', 'start')
    
    intro_position_display = "البداية" if intro_position == 'start' else "النهاية"
    
    buttons = [
        [Button.inline(f"🎵 موضع المقدمة: {intro_position_display}", f"set_intro_position_{'end' if intro_position == 'start' else 'start'}_{task_id}")],
        [Button.inline("🔙 رجوع لإعدادات دمج المقاطع", f"audio_merge_settings_{task_id}")]
    ]
    
    message_text = (
        f"⚙️ خيارات دمج المقاطع للمهمة: {task_name}\n\n"
        f"📝 الوصف:\n"
        f"• اختيار موضع مقطع المقدمة\n"
        f"• البداية: مقدمة + ملف أصلي + خاتمة\n"
        f"• النهاية: ملف أصلي + مقدمة + خاتمة\n"
        f"• مقطع الخاتمة يبقى دائماً في النهاية\n\n"
        f"📊 الحالة الحالية:\n"
        f"• موضع المقدمة: {intro_position_display}\n\n"
        f"اختر الإعداد الذي تريد تعديله:"
    )
    
    await self.edit_or_send_message(event, message_text, buttons=buttons)

# ===== معالجات الأزرار الجديدة =====

async def toggle_album_art_enabled(self, event, task_id):
    """Toggle album art enabled/disabled"""
    try:
        settings = self.db.get_audio_metadata_settings(task_id)
        current_state = settings.get('album_art_enabled', False)
        new_state = not current_state
        
        self.db.update_audio_metadata_setting(task_id, 'album_art_enabled', new_state)
        
        status = "🟢 مفعل" if new_state else "🔴 معطل"
        await event.answer(f"✅ تم {'تفعيل' if new_state else 'تعطيل'} صورة الغلاف: {status}")
        
        # Refresh the album art settings page
        await self.album_art_settings(event, task_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تبديل حالة صورة الغلاف: {e}")
        await event.answer("❌ حدث خطأ في تبديل الحالة")

async def toggle_apply_art_to_all(self, event, task_id):
    """Toggle apply art to all files"""
    try:
        settings = self.db.get_audio_metadata_settings(task_id)
        current_state = settings.get('apply_art_to_all', False)
        new_state = not current_state
        
        self.db.update_audio_metadata_setting(task_id, 'apply_art_to_all', new_state)
        
        status = "🟢 نعم" if new_state else "🔴 لا"
        await event.answer(f"✅ تم {'تفعيل' if new_state else 'تعطيل'} تطبيق صورة الغلاف على جميع الملفات: {status}")
        
        # Refresh the album art settings page
        await self.album_art_settings(event, task_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تبديل تطبيق صورة الغلاف: {e}")
        await event.answer("❌ حدث خطأ في تبديل الحالة")

async def toggle_audio_merge(self, event, task_id):
    """Toggle audio merge enabled/disabled"""
    try:
        settings = self.db.get_audio_metadata_settings(task_id)
        current_state = settings.get('audio_merge_enabled', False)
        new_state = not current_state
        
        self.db.update_audio_metadata_setting(task_id, 'audio_merge_enabled', new_state)
        
        status = "🟢 مفعل" if new_state else "🔴 معطل"
        await event.answer(f"✅ تم {'تفعيل' if new_state else 'تعطيل'} دمج المقاطع الصوتية: {status}")
        
        # Refresh the audio merge settings page
        await self.audio_merge_settings(event, task_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تبديل حالة دمج المقاطع: {e}")
        await event.answer("❌ حدث خطأ في تبديل الحالة")

async def toggle_preserve_quality(self, event, task_id):
    """Toggle preserve quality setting"""
    try:
        settings = self.db.get_audio_metadata_settings(task_id)
        current_state = settings.get('preserve_quality', True)
        new_state = not current_state
        
        self.db.update_audio_metadata_setting(task_id, 'preserve_quality', new_state)
        
        status = "🟢 مفعل" if new_state else "🔴 معطل"
        await event.answer(f"✅ تم {'تفعيل' if new_state else 'تعطيل'} الحفاظ على الجودة: {status}")
        
        # Refresh the advanced audio settings page
        await self.advanced_audio_settings(event, task_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تبديل الحفاظ على الجودة: {e}")
        await event.answer("❌ حدث خطأ في تبديل الحالة")

async def toggle_convert_to_mp3(self, event, task_id):
    """Toggle convert to MP3 setting"""
    try:
        settings = self.db.get_audio_metadata_settings(task_id)
        current_state = settings.get('convert_to_mp3', False)
        new_state = not current_state
        
        self.db.update_audio_metadata_setting(task_id, 'convert_to_mp3', new_state)
        
        status = "🟢 مفعل" if new_state else "🔴 معطل"
        await event.answer(f"✅ تم {'تفعيل' if new_state else 'تعطيل'} التحويل إلى MP3: {status}")
        
        # Refresh the advanced audio settings page
        await self.advanced_audio_settings(event, task_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تبديل التحويل إلى MP3: {e}")
        await event.answer("❌ حدث خطأ في تبديل الحالة")

async def set_intro_position(self, event, task_id, position):
    """Set intro position (start/end)"""
    try:
        self.db.update_audio_metadata_setting(task_id, 'intro_position', position)
        
        position_text = "البداية" if position == 'start' else "النهاية"
        await event.answer(f"✅ تم تعيين موضع المقدمة إلى: {position_text}")
        
        # Refresh the merge options page
        await self.show_merge_options_fixed(event, task_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في تعيين موضع المقدمة: {e}")
        await event.answer("❌ حدث خطأ في تعيين الموضع")

# ===== دوال رفع الملفات =====

async def upload_album_art(self, event, task_id):
    """Handle album art upload"""
    try:
        # Set conversation state to wait for album art
        self.db.set_conversation_state(event.sender_id, f"waiting_album_art_{task_id}")
        
        await event.answer("📤 يرجى إرسال صورة الغلاف التي تريد استخدامها")
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء رفع صورة الغلاف: {e}")
        await event.answer("❌ حدث خطأ في بدء رفع الصورة")

async def upload_intro_audio(self, event, task_id):
    """Handle intro audio upload"""
    try:
        # Set conversation state to wait for intro audio
        self.db.set_conversation_state(event.sender_id, f"waiting_intro_audio_{task_id}")
        
        await event.answer("📤 يرجى إرسال مقطع المقدمة الصوتي")
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء رفع مقطع المقدمة: {e}")
        await event.answer("❌ حدث خطأ في بدء رفع المقطع")

async def upload_outro_audio(self, event, task_id):
    """Handle outro audio upload"""
    try:
        # Set conversation state to wait for outro audio
        self.db.set_conversation_state(event.sender_id, f"waiting_outro_audio_{task_id}")
        
        await event.answer("📤 يرجى إرسال مقطع الخاتمة الصوتي")
        
    except Exception as e:
        logger.error(f"❌ خطأ في بدء رفع مقطع الخاتمة: {e}")
        await event.answer("❌ حدث خطأ في بدء رفع المقطع")

# ===== دوال حذف الملفات =====

async def remove_intro_audio(self, event, task_id):
    """Remove intro audio"""
    try:
        self.db.update_audio_metadata_setting(task_id, 'intro_path', '')
        
        await event.answer("✅ تم حذف مقطع المقدمة")
        
        # Refresh the intro audio settings page
        await self.show_intro_audio_settings_fixed(event, task_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في حذف مقطع المقدمة: {e}")
        await event.answer("❌ حدث خطأ في حذف المقطع")

async def remove_outro_audio(self, event, task_id):
    """Remove outro audio"""
    try:
        self.db.update_audio_metadata_setting(task_id, 'outro_path', '')
        
        await event.answer("✅ تم حذف مقطع الخاتمة")
        
        # Refresh the outro audio settings page
        await self.show_outro_audio_settings_fixed(event, task_id)
        
    except Exception as e:
        logger.error(f"❌ خطأ في حذف مقطع الخاتمة: {e}")
        await event.answer("❌ حدث خطأ في حذف المقطع")