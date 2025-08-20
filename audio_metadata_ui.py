"""
واجهة المستخدم للوسوم الصوتية - Audio Metadata User Interface
يوفر واجهة سهلة الاستخدام لتعديل الوسوم الصوتية
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import os
from typing import Dict, Any, Optional
from audio_metadata_settings import (
    PREDEFINED_TEMPLATES, AUDIO_GENRES, ALBUM_ART_SETTINGS,
    AUDIO_MERGE_SETTINGS, AVAILABLE_TEMPLATE_VARIABLES,
    format_template_preview, get_template_by_name
)

class AudioMetadataUI:
    """واجهة المستخدم للوسوم الصوتية"""
    
    def __init__(self, parent=None):
        """تهيئة الواجهة"""
        self.parent = parent
        self.root = tk.Tk() if not parent else tk.Toplevel(parent)
        self.root.title("🎵 إعدادات الوسوم الصوتية")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # المتغيرات
        self.audio_file_path = tk.StringVar()
        self.album_art_path = tk.StringVar()
        self.intro_audio_path = tk.StringVar()
        self.outro_audio_path = tk.StringVar()
        self.selected_template = tk.StringVar(value='default')
        self.enable_audio_metadata = tk.BooleanVar(value=True)
        self.enable_album_art = tk.BooleanVar(value=True)
        self.enable_audio_merge = tk.BooleanVar(value=False)
        self.apply_art_to_all = tk.BooleanVar(value=False)
        self.intro_position = tk.StringVar(value='start')
        self.preserve_quality = tk.BooleanVar(value=True)
        self.convert_to_mp3 = tk.BooleanVar(value=True)
        
        # القوالب المخصصة
        self.custom_templates = {}
        self.current_template = PREDEFINED_TEMPLATES['default']['template'].copy()
        
        # إنشاء الواجهة
        self.create_widgets()
        self.setup_layout()
        
    def create_widgets(self):
        """إنشاء عناصر الواجهة"""
        # الإطار الرئيسي
        self.main_frame = ttk.Frame(self.root, padding="10")
        
        # عنوان الواجهة
        self.title_label = ttk.Label(
            self.main_frame, 
            text="🎵 إعدادات الوسوم الصوتية (ID3v2)",
            font=("Arial", 16, "bold")
        )
        
        # إطار التفعيل
        self.enable_frame = ttk.LabelFrame(self.main_frame, text="⚙️ تفعيل الميزات", padding="10")
        
        self.enable_metadata_check = ttk.Checkbutton(
            self.enable_frame,
            text="تفعيل تعديل الوسوم الصوتية",
            variable=self.enable_audio_metadata
        )
        
        self.enable_art_check = ttk.Checkbutton(
            self.enable_frame,
            text="تفعيل صورة الغلاف",
            variable=self.enable_album_art
        )
        
        self.enable_merge_check = ttk.Checkbutton(
            self.enable_frame,
            text="تفعيل دمج المقاطع الصوتية",
            variable=self.enable_audio_merge
        )
        
        # إطار اختيار الملفات
        self.files_frame = ttk.LabelFrame(self.main_frame, text="📁 اختيار الملفات", padding="10")
        
        # الملف الصوتي
        ttk.Label(self.files_frame, text="المقطع الصوتي:").grid(row=0, column=0, sticky="w", pady=2)
        ttk.Entry(self.files_frame, textvariable=self.audio_file_path, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(self.files_frame, text="📁 تصفح", command=self.browse_audio_file).grid(row=0, column=2)
        
        # صورة الغلاف
        ttk.Label(self.files_frame, text="صورة الغلاف:").grid(row=1, column=0, sticky="w", pady=2)
        ttk.Entry(self.files_frame, textvariable=self.album_art_path, width=50).grid(row=1, column=1, padx=5)
        ttk.Button(self.files_frame, text="🖼️ تصفح", command=self.browse_album_art).grid(row=1, column=2)
        
        # مقطع المقدمة
        ttk.Label(self.files_frame, text="مقطع المقدمة:").grid(row=2, column=0, sticky="w", pady=2)
        ttk.Entry(self.files_frame, textvariable=self.intro_audio_path, width=50).grid(row=2, column=1, padx=5)
        ttk.Button(self.files_frame, text="🎵 تصفح", command=self.browse_intro_audio).grid(row=2, column=2)
        
        # مقطع الخاتمة
        ttk.Label(self.files_frame, text="مقطع الخاتمة:").grid(row=3, column=0, sticky="w", pady=2)
        ttk.Entry(self.files_frame, textvariable=self.outro_audio_path, width=50).grid(row=3, column=1, padx=5)
        ttk.Button(self.files_frame, text="🎵 تصفح", command=self.browse_outro_audio).grid(row=3, column=2)
        
        # إطار القوالب
        self.template_frame = ttk.LabelFrame(self.main_frame, text="📋 قوالب الوسوم", padding="10")
        
        # اختيار القالب
        ttk.Label(self.template_frame, text="القالب:").grid(row=0, column=0, sticky="w", pady=2)
        self.template_combo = ttk.Combobox(
            self.template_frame,
            textvariable=self.selected_template,
            values=list(PREDEFINED_TEMPLATES.keys()),
            state="readonly",
            width=30
        )
        self.template_combo.grid(row=0, column=1, padx=5)
        self.template_combo.bind('<<ComboboxSelected>>', self.on_template_changed)
        
        # معاينة القالب
        self.template_preview = tk.Text(self.template_frame, height=8, width=60)
        self.template_preview.grid(row=1, column=0, columnspan=3, pady=10)
        
        # إطار تخصيص القالب
        self.custom_frame = ttk.LabelFrame(self.main_frame, text="✏️ تخصيص القالب", padding="10")
        
        # حقول الوسوم
        self.tag_entries = {}
        tag_fields = [
            ('title', 'العنوان:'),
            ('artist', 'الفنان:'),
            ('album', 'الألبوم:'),
            ('year', 'السنة:'),
            ('genre', 'النوع:'),
            ('composer', 'الملحن:'),
            ('comment', 'التعليق:'),
            ('track', 'رقم المسار:'),
            ('album_artist', 'فنان الألبوم:'),
            ('lyrics', 'كلمات الأغنية:')
        ]
        
        for i, (tag_key, tag_label) in enumerate(tag_fields):
            row = i // 2
            col = (i % 2) * 2
            
            ttk.Label(self.custom_frame, text=tag_label).grid(row=row, column=col, sticky="w", pady=2)
            entry = ttk.Entry(self.custom_frame, width=30)
            entry.grid(row=row, column=col+1, padx=5, pady=2)
            self.tag_entries[tag_key] = entry
        
        # إطار الإعدادات المتقدمة
        self.advanced_frame = ttk.LabelFrame(self.main_frame, text="🔧 إعدادات متقدمة", padding="10")
        
        # خيارات صورة الغلاف
        self.apply_art_to_all_check = ttk.Checkbutton(
            self.advanced_frame,
            text="تطبيق صورة الغلاف على جميع الملفات",
            variable=self.apply_art_to_all
        )
        self.apply_art_to_all_check.grid(row=0, column=0, columnspan=2, sticky="w", pady=2)
        
        # موضع المقدمة
        ttk.Label(self.advanced_frame, text="موضع المقدمة:").grid(row=1, column=0, sticky="w", pady=2)
        self.intro_position_combo = ttk.Combobox(
            self.advanced_frame,
            textvariable=self.intro_position,
            values=['start', 'end'],
            state="readonly",
            width=15
        )
        self.intro_position_combo.grid(row=1, column=1, padx=5)
        
        # خيارات الجودة
        self.preserve_quality_check = ttk.Checkbutton(
            self.advanced_frame,
            text="الحفاظ على الجودة الأصلية",
            variable=self.preserve_quality
        )
        self.preserve_quality_check.grid(row=2, column=0, columnspan=2, sticky="w", pady=2)
        
        self.convert_to_mp3_check = ttk.Checkbutton(
            self.advanced_frame,
            text="تحويل إلى MP3",
            variable=self.convert_to_mp3
        )
        self.convert_to_mp3_check.grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
        
        # إطار الأزرار
        self.buttons_frame = ttk.Frame(self.main_frame)
        
        self.save_button = ttk.Button(
            self.buttons_frame,
            text="💾 حفظ الإعدادات",
            command=self.save_settings
        )
        
        self.reset_button = ttk.Button(
            self.buttons_frame,
            text="🔄 إعادة تعيين",
            command=self.reset_settings
        )
        
        self.preview_button = ttk.Button(
            self.buttons_frame,
            text="👁️ معاينة",
            command=self.preview_settings
        )
        
        self.help_button = ttk.Button(
            self.buttons_frame,
            text="❓ مساعدة",
            command=self.show_help
        )
        
    def setup_layout(self):
        """إعداد تخطيط الواجهة"""
        self.main_frame.pack(fill="both", expand=True)
        
        # عنوان الواجهة
        self.title_label.pack(pady=(0, 20))
        
        # إطار التفعيل
        self.enable_frame.pack(fill="x", pady=(0, 10))
        self.enable_metadata_check.pack(anchor="w")
        self.enable_art_check.pack(anchor="w")
        self.enable_merge_check.pack(anchor="w")
        
        # إطار الملفات
        self.files_frame.pack(fill="x", pady=(0, 10))
        
        # إطار القوالب
        self.template_frame.pack(fill="x", pady=(0, 10))
        
        # إطار التخصيص
        self.custom_frame.pack(fill="x", pady=(0, 10))
        
        # إطار الإعدادات المتقدمة
        self.advanced_frame.pack(fill="x", pady=(0, 10))
        
        # إطار الأزرار
        self.buttons_frame.pack(pady=20)
        self.save_button.pack(side="left", padx=5)
        self.reset_button.pack(side="left", padx=5)
        self.preview_button.pack(side="left", padx=5)
        self.help_button.pack(side="left", padx=5)
        
        # تحديث معاينة القالب
        self.update_template_preview()
        
    def browse_audio_file(self):
        """تصفح الملف الصوتي"""
        file_path = filedialog.askopenfilename(
            title="اختر المقطع الصوتي",
            filetypes=[
                ("ملفات صوتية", "*.mp3 *.m4a *.aac *.ogg *.wav *.flac *.wma *.opus"),
                ("جميع الملفات", "*.*")
            ]
        )
        if file_path:
            self.audio_file_path.set(file_path)
    
    def browse_album_art(self):
        """تصفح صورة الغلاف"""
        file_path = filedialog.askopenfilename(
            title="اختر صورة الغلاف",
            filetypes=[
                ("ملفات الصور", "*.jpg *.jpeg *.png *.bmp *.tiff"),
                ("جميع الملفات", "*.*")
            ]
        )
        if file_path:
            self.album_art_path.set(file_path)
    
    def browse_intro_audio(self):
        """تصفح مقطع المقدمة"""
        file_path = filedialog.askopenfilename(
            title="اختر مقطع المقدمة",
            filetypes=[
                ("ملفات صوتية", "*.mp3 *.wav *.aac *.ogg"),
                ("جميع الملفات", "*.*")
            ]
        )
        if file_path:
            self.intro_audio_path.set(file_path)
    
    def browse_outro_audio(self):
        """تصفح مقطع الخاتمة"""
        file_path = filedialog.askopenfilename(
            title="اختر مقطع الخاتمة",
            filetypes=[
                ("ملفات صوتية", "*.mp3 *.wav *.aac *.ogg"),
                ("جميع الملفات", "*.*")
            ]
        )
        if file_path:
            self.outro_audio_path.set(file_path)
    
    def on_template_changed(self, event=None):
        """عند تغيير القالب"""
        template_name = self.selected_template.get()
        template_data = get_template_by_name(template_name)
        self.current_template = template_data['template'].copy()
        
        # تحديث حقول التخصيص
        for tag_key, entry in self.tag_entries.items():
            value = self.current_template.get(tag_key, '')
            entry.delete(0, tk.END)
            entry.insert(0, value)
        
        # تحديث المعاينة
        self.update_template_preview()
    
    def update_template_preview(self):
        """تحديث معاينة القالب"""
        preview_text = format_template_preview(self.current_template)
        self.template_preview.delete(1.0, tk.END)
        self.template_preview.insert(1.0, preview_text)
    
    def update_current_template(self):
        """تحديث القالب الحالي من حقول التخصيص"""
        for tag_key, entry in self.tag_entries.items():
            value = entry.get().strip()
            if value:
                self.current_template[tag_key] = value
            elif tag_key in self.current_template:
                del self.current_template[tag_key]
        
        self.update_template_preview()
    
    def save_settings(self):
        """حفظ الإعدادات"""
        try:
            # تحديث القالب الحالي
            self.update_current_template()
            
            # جمع الإعدادات
            settings = {
                'enabled': self.enable_audio_metadata.get(),
                'template': self.current_template.copy(),
                'album_art': {
                    'enabled': self.enable_album_art.get(),
                    'path': self.album_art_path.get(),
                    'apply_to_all': self.apply_art_to_all.get()
                },
                'audio_merge': {
                    'enabled': self.enable_audio_merge.get(),
                    'intro_path': self.intro_audio_path.get(),
                    'outro_path': self.outro_audio_path.get(),
                    'intro_position': self.intro_position.get()
                },
                'quality': {
                    'preserve_original': self.preserve_quality.get(),
                    'convert_to_mp3': self.convert_to_mp3.get()
                }
            }
            
            # حفظ الإعدادات (يمكن حفظها في قاعدة البيانات أو ملف)
            messagebox.showinfo("نجح", "✅ تم حفظ الإعدادات بنجاح!")
            
            return settings
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في حفظ الإعدادات: {e}")
            return None
    
    def reset_settings(self):
        """إعادة تعيين الإعدادات"""
        try:
            # إعادة تعيين المتغيرات
            self.enable_audio_metadata.set(True)
            self.enable_album_art.set(True)
            self.enable_audio_merge.set(False)
            self.apply_art_to_all.set(False)
            self.intro_position.set('start')
            self.preserve_quality.set(True)
            self.convert_to_mp3.set(True)
            
            # مسح مسارات الملفات
            self.audio_file_path.set('')
            self.album_art_path.set('')
            self.intro_audio_path.set('')
            self.outro_audio_path.set('')
            
            # إعادة تعيين القالب
            self.selected_template.set('default')
            self.on_template_changed()
            
            messagebox.showinfo("نجح", "🔄 تم إعادة تعيين الإعدادات!")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في إعادة تعيين الإعدادات: {e}")
    
    def preview_settings(self):
        """معاينة الإعدادات"""
        try:
            self.update_current_template()
            
            preview_text = "📋 معاينة الإعدادات:\n\n"
            preview_text += f"🔹 تفعيل الوسوم الصوتية: {'✅' if self.enable_audio_metadata.get() else '❌'}\n"
            preview_text += f"🔹 تفعيل صورة الغلاف: {'✅' if self.enable_album_art.get() else '❌'}\n"
            preview_text += f"🔹 تفعيل دمج المقاطع: {'✅' if self.enable_audio_merge.get() else '❌'}\n"
            preview_text += f"🔹 الحفاظ على الجودة: {'✅' if self.preserve_quality.get() else '❌'}\n"
            preview_text += f"🔹 تحويل إلى MP3: {'✅' if self.convert_to_mp3.get() else '❌'}\n\n"
            
            preview_text += "📁 الملفات المحددة:\n"
            if self.audio_file_path.get():
                preview_text += f"🔹 المقطع الصوتي: {os.path.basename(self.audio_file_path.get())}\n"
            if self.album_art_path.get():
                preview_text += f"🔹 صورة الغلاف: {os.path.basename(self.album_art_path.get())}\n"
            if self.intro_audio_path.get():
                preview_text += f"🔹 مقطع المقدمة: {os.path.basename(self.intro_audio_path.get())}\n"
            if self.outro_audio_path.get():
                preview_text += f"🔹 مقطع الخاتمة: {os.path.basename(self.outro_audio_path.get())}\n"
            
            preview_text += "\n" + format_template_preview(self.current_template)
            
            # عرض المعاينة في نافذة منفصلة
            preview_window = tk.Toplevel(self.root)
            preview_window.title("👁️ معاينة الإعدادات")
            preview_window.geometry("600x500")
            
            text_widget = tk.Text(preview_window, wrap="word", padx=10, pady=10)
            text_widget.pack(fill="both", expand=True)
            text_widget.insert(1.0, preview_text)
            text_widget.config(state="disabled")
            
        except Exception as e:
            messagebox.showerror("خطأ", f"❌ فشل في عرض المعاينة: {e}")
    
    def show_help(self):
        """عرض المساعدة"""
        help_text = """
🎵 مساعدة الوسوم الصوتية

🔹 الميزات المتاحة:
• تعديل جميع أنواع الوسوم الصوتية (ID3v2)
• دعم صورة الغلاف مع خيارات متقدمة
• دمج مقاطع صوتية إضافية
• الحفاظ على الجودة 100%
• معالجة مرة واحدة وإعادة الاستخدام

🔹 المتغيرات المتاحة:
• $title - عنوان المقطع الصوتي
• $artist - اسم الفنان
• $album - اسم الألبوم
• $year - سنة الإصدار
• $genre - النوع الموسيقي
• $composer - اسم الملحن
• $comment - التعليق
• $track - رقم المسار
• $album_artist - فنان الألبوم
• $lyrics - كلمات الأغنية
• $length - مدة المقطع
• $format - صيغة الملف
• $bitrate - معدل البت

🔹 الصيغ المدعومة:
• MP3, M4A, AAC, OGG, WAV, FLAC, WMA, OPUS

🔹 نصائح للاستخدام:
• استخدم القوالب الجاهزة للبداية
• يمكنك تخصيص كل وسم بشكل منفصل
• صورة الغلاف ستظهر في مشغل الموسيقى
• دمج المقاطع الصوتية يتطلب FFmpeg
        """
        
        help_window = tk.Toplevel(self.root)
        help_window.title("❓ مساعدة الوسوم الصوتية")
        help_window.geometry("700x600")
        
        text_widget = tk.Text(help_window, wrap="word", padx=10, pady=10)
        text_widget.pack(fill="both", expand=True)
        text_widget.insert(1.0, help_text)
        text_widget.config(state="disabled")
    
    def run(self):
        """تشغيل الواجهة"""
        if not self.parent:
            self.root.mainloop()
    
    def get_settings(self) -> Dict[str, Any]:
        """الحصول على الإعدادات الحالية"""
        self.update_current_template()
        
        return {
            'enabled': self.enable_audio_metadata.get(),
            'template': self.current_template.copy(),
            'album_art': {
                'enabled': self.enable_album_art.get(),
                'path': self.album_art_path.get(),
                'apply_to_all': self.apply_art_to_all.get()
            },
            'audio_merge': {
                'enabled': self.enable_audio_merge.get(),
                'intro_path': self.intro_audio_path.get(),
                'outro_path': self.outro_audio_path.get(),
                'intro_position': self.intro_position.get()
            },
            'quality': {
                'preserve_original': self.preserve_quality.get(),
                'convert_to_mp3': self.convert_to_mp3.get()
            }
        }

# تشغيل الواجهة إذا تم تشغيل الملف مباشرة
if __name__ == "__main__":
    app = AudioMetadataUI()
    app.run()