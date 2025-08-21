"""
إعدادات الوسوم الصوتية - Audio Metadata Settings
يحتوي على القوالب الافتراضية والإعدادات للوسوم الصوتية
"""

# ===== القالب الافتراضي للوسوم الصوتية =====
DEFAULT_AUDIO_METADATA_TEMPLATE = {
    'title': '$title',
    'artist': '$artist',
    'album': '$album',
    'year': '$year',
    'genre': '$genre',
    'composer': '$composer',
    'comment': 'Enhanced by Telegram Bot',
    'track': '$track',
    'album_artist': '$album_artist',
    'lyrics': '$lyrics'
}

# ===== قوالب جاهزة للاستخدام =====
PREDEFINED_TEMPLATES = {
    'default': {
        'name': '🔹 القالب الافتراضي',
        'template': DEFAULT_AUDIO_METADATA_TEMPLATE.copy()
    },
    
    'enhanced': {
        'name': '🔹 قالب محسن',
        'template': {
            'title': '$title - Enhanced',
            'artist': '$artist',
            'album': '$album ($year)',
            'year': '$year',
            'genre': '$genre',
            'composer': '$composer',
            'comment': 'Enhanced by Telegram Bot - High Quality',
            'track': '$track',
            'album_artist': '$album_artist',
            'lyrics': '$lyrics'
        }
    },
    
    'minimal': {
        'name': '🔹 قالب بسيط',
        'template': {
            'title': '$title',
            'artist': '$artist',
            'album': '$album',
            'year': '$year',
            'genre': '$genre'
        }
    },
    
    'professional': {
        'name': '🔹 قالب احترافي',
        'template': {
            'title': '$title',
            'artist': '$artist',
            'album': '$album',
            'year': '$year',
            'genre': '$genre',
            'composer': '$composer',
            'comment': 'Professional Audio Processing',
            'track': '$track',
            'album_artist': '$album_artist',
            'lyrics': '$lyrics'
        }
    },
    
    'custom_brand': {
        'name': '🔹 قالب مخصص للعلامة التجارية',
        'template': {
            'title': '$title',
            'artist': '$artist',
            'album': '$album',
            'year': '$year',
            'genre': '$genre',
            'composer': '$composer',
            'comment': 'Custom Brand Audio',
            'track': '$track',
            'album_artist': '$album_artist',
            'lyrics': '$lyrics'
        }
    }
}

# ===== أنواع الألبومات الصوتية =====
AUDIO_GENRES = [
    'Pop', 'Rock', 'Hip Hop', 'R&B', 'Country', 'Jazz', 'Classical', 'Electronic',
    'Folk', 'Blues', 'Reggae', 'Metal', 'Punk', 'Indie', 'Alternative', 'Gospel',
    'Soul', 'Funk', 'Disco', 'Techno', 'House', 'Trance', 'Dubstep', 'Ambient',
    'World', 'Latin', 'Arabic', 'Indian', 'Asian', 'African', 'Caribbean', 'Other'
]

# ===== إعدادات صورة الغلاف =====
ALBUM_ART_SETTINGS = {
    'max_size': 1000,  # الحد الأقصى للبكسل
    'quality': 95,      # جودة JPEG
    'formats': ['jpg', 'jpeg', 'png', 'bmp', 'tiff'],
    'preferred_format': 'jpeg'
}

# ===== إعدادات دمج المقاطع الصوتية =====
AUDIO_MERGE_SETTINGS = {
    'intro_position': ['start', 'end'],  # موضع المقدمة
    'supported_formats': ['mp3', 'wav', 'aac', 'ogg'],
    'output_format': 'mp3',
    'output_bitrate': '320k',
    'fade_in': 0.5,    # ثواني
    'fade_out': 0.5    # ثواني
}

# ===== متغيرات القالب المتاحة =====
AVAILABLE_TEMPLATE_VARIABLES = {
    '$title': 'عنوان المقطع الصوتي الأصلي',
    '$artist': 'اسم الفنان الأصلي',
    '$album': 'اسم الألبوم الأصلي',
    '$year': 'سنة الإصدار الأصلية',
    '$genre': 'النوع الموسيقي الأصلي',
    '$composer': 'اسم الملحن الأصلي',
    '$comment': 'التعليق الأصلي',
    '$track': 'رقم المسار الأصلي',
    '$album_artist': 'فنان الألبوم الأصلي',
    '$lyrics': 'كلمات الأغنية الأصلية',
    '$length': 'مدة المقطع الصوتي بالثواني',
    '$format': 'صيغة الملف الصوتي',
    '$bitrate': 'معدل البت الأصلي'
}

# ===== إعدادات الجودة =====
QUALITY_SETTINGS = {
    'high': {
        'bitrate': '320k',
        'sample_rate': 48000,
        'channels': 2
    },
    'medium': {
        'bitrate': '192k',
        'sample_rate': 44100,
        'channels': 2
    },
    'low': {
        'bitrate': '128k',
        'sample_rate': 22050,
        'channels': 2
    }
}

# ===== إعدادات التطبيق =====
APPLICATION_SETTINGS = {
    'enable_audio_metadata': True,      # تفعيل تعديل الوسوم الصوتية
    'enable_album_art': True,           # تفعيل صورة الغلاف
    'enable_audio_merge': True,         # تفعيل دمج المقاطع الصوتية
    'preserve_original_quality': True,  # الحفاظ على الجودة الأصلية
    'convert_to_mp3': True,             # تحويل إلى MP3
    'cache_processed_audio': True,      # تخزين الملفات المعالجة
    'max_cache_size': 50               # الحد الأقصى لحجم Cache
}

# ===== رسائل النظام =====
SYSTEM_MESSAGES = {
    'audio_processing_start': '🎵 بدء معالجة الوسوم الصوتية...',
    'audio_processing_success': '✅ تم معالجة الوسوم الصوتية بنجاح',
    'audio_processing_error': '❌ خطأ في معالجة الوسوم الصوتية',
    'album_art_applied': '🖼️ تم تطبيق صورة الغلاف',
    'album_art_error': '❌ خطأ في تطبيق صورة الغلاف',
    'audio_merge_success': '🔗 تم دمج المقاطع الصوتية بنجاح',
    'audio_merge_error': '❌ خطأ في دمج المقاطع الصوتية',
    'cache_cleared': '🧹 تم مسح cache المقاطع الصوتية',
    'quality_preserved': '🎯 تم الحفاظ على الجودة الأصلية',
    'format_converted': '🔄 تم تحويل الصيغة إلى MP3'
}

# ===== دوال مساعدة =====
def get_template_by_name(template_name: str) -> dict:
    """الحصول على قالب بالاسم"""
    return PREDEFINED_TEMPLATES.get(template_name, PREDEFINED_TEMPLATES['default'])

def get_all_template_names() -> list:
    """الحصول على أسماء جميع القوالب"""
    return list(PREDEFINED_TEMPLATES.keys())

def create_custom_template(**kwargs) -> dict:
    """إنشاء قالب مخصص"""
    template = DEFAULT_AUDIO_METADATA_TEMPLATE.copy()
    template.update(kwargs)
    return template

def validate_template(template: dict) -> bool:
    """التحقق من صحة القالب"""
    required_keys = ['title', 'artist', 'album']
    return all(key in template for key in required_keys)

def get_template_variables(template: dict) -> list:
    """الحصول على المتغيرات المستخدمة في القالب"""
    variables = []
    for value in template.values():
        if isinstance(value, str):
            for var in AVAILABLE_TEMPLATE_VARIABLES.keys():
                if var in value:
                    variables.append(var)
    return list(set(variables))

def format_template_preview(template: dict) -> str:
    """تنسيق معاينة القالب"""
    preview = "📋 معاينة القالب:\n\n"
    for key, value in template.items():
        if value:
            preview += f"🔹 {key.title()}: {value}\n"
    return preview

# ===== إعدادات لوحة التحكم =====
ADMIN_PANEL_SETTINGS = {
    'audio_metadata_tab': {
        'name': '🎵 الوسوم الصوتية',
        'icon': '🎵',
        'description': 'إعدادات تعديل الوسوم الصوتية (ID3v2)',
        'enabled': True
    },
    
    'album_art_tab': {
        'name': '🖼️ صورة الغلاف',
        'icon': '🖼️',
        'description': 'إعدادات صورة الغلاف للمقاطع الصوتية',
        'enabled': True
    },
    
    'audio_merge_tab': {
        'name': '🔗 دمج المقاطع الصوتية',
        'icon': '🔗',
        'description': 'إعدادات دمج مقاطع صوتية إضافية',
        'enabled': True
    },
    
    'quality_tab': {
        'name': '🎯 الجودة',
        'icon': '🎯',
        'description': 'إعدادات جودة الصوت والصورة',
        'enabled': True
    }
}

# ===== إعدادات الواجهة =====
UI_SETTINGS = {
    'show_template_preview': True,
    'show_variable_help': True,
    'show_quality_indicators': True,
    'show_processing_progress': True,
    'enable_drag_drop': True,
    'enable_bulk_processing': True,
    'max_file_size_mb': 100,
    'allowed_file_types': ['.mp3', '.m4a', '.aac', '.ogg', '.wav', '.flac', '.wma', '.opus']
}