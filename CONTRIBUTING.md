# 🤝 دليل المساهمة - Contributing Guide

## 🎯 **مرحباً بك في البوت المحسن!**

نحن سعداء لرغبتك في المساهمة في تطوير البوت المحسن لـ Telegram. هذا الدليل سيساعدك في البدء.

---

## 📋 **كيفية المساهمة**

### **1️⃣ الإبلاغ عن مشاكل (Bug Reports)**
- استخدم [GitHub Issues](https://github.com/your-repo/issues)
- اكتب وصفاً واضحاً للمشكلة
- أضف خطوات لإعادة إنتاج المشكلة
- أضف معلومات النظام والبيئة

### **2️⃣ اقتراح ميزات جديدة (Feature Requests)**
- اكتب وصفاً مفصلاً للميزة
- اشرح لماذا هذه الميزة مفيدة
- اقترح كيفية تنفيذها
- أضف أمثلة للاستخدام

### **3️⃣ إرسال Pull Requests**
- Fork المشروع
- أنشئ فرع جديد للميزة
- اكتب كود نظيف ومعلق عليه
- أضف اختبارات
- اكتب رسالة commit واضحة

---

## 🛠️ **متطلبات التطوير**

### **المتطلبات الأساسية**
- Python 3.8+
- FFmpeg
- Git
- pip

### **المكتبات المطلوبة**
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt  # للتطوير
```

### **إعداد البيئة**
```bash
# نسخ المشروع
git clone <repository-url>
cd enhanced-telegram-bot

# إنشاء بيئة افتراضية
python -m venv venv
source venv/bin/activate  # Linux/macOS
# أو
venv\Scripts\activate  # Windows

# تثبيت المتطلبات
pip install -r requirements.txt
```

---

## 📁 **هيكل المشروع**

```
enhanced-telegram-bot/
├── main.py                 # نقطة البداية الرئيسية
├── watermark_processor.py  # معالج العلامة المائية
├── userbot_service/        # خدمة Userbot
├── database/               # قاعدة البيانات
├── bot_package/           # حزمة البوت
├── tests/                  # الاختبارات
├── docs/                   # التوثيق
└── scripts/                # السكريبتات
```

---

## 🧪 **كتابة الاختبارات**

### **إضافة اختبارات جديدة**
```python
# tests/test_watermark.py
import pytest
from watermark_processor import WatermarkProcessor

def test_watermark_creation():
    processor = WatermarkProcessor()
    # اختبار إنشاء العلامة المائية
    
def test_video_processing():
    processor = WatermarkProcessor()
    # اختبار معالجة الفيديو
```

### **تشغيل الاختبارات**
```bash
# جميع الاختبارات
pytest

# اختبارات محددة
pytest tests/test_watermark.py

# مع تغطية
pytest --cov=watermark_processor
```

---

## 📝 **معايير الكود**

### **Python Style Guide**
- اتبع [PEP 8](https://www.python.org/dev/peps/pep-0008/)
- استخدم docstrings للدوال
- اكتب تعليقات باللغة العربية
- استخدم أسماء متغيرات واضحة

### **مثال على الكود الجيد**
```python
def apply_watermark_to_image(image_path: str, watermark_settings: dict) -> Optional[str]:
    """
    تطبيق العلامة المائية على الصورة
    
    Args:
        image_path: مسار الصورة
        watermark_settings: إعدادات العلامة المائية
        
    Returns:
        مسار الصورة مع العلامة المائية أو None في حالة الفشل
    """
    try:
        # معالجة الصورة
        processed_image = process_image(image_path)
        
        # تطبيق العلامة المائية
        watermarked_image = add_watermark(processed_image, watermark_settings)
        
        return save_image(watermarked_image)
        
    except Exception as e:
        logger.error(f"فشل في تطبيق العلامة المائية: {e}")
        return None
```

---

## 🔧 **إعدادات التطوير**

### **Pre-commit Hooks**
```bash
# تثبيت pre-commit
pip install pre-commit

# إعداد hooks
pre-commit install

# تشغيل على جميع الملفات
pre-commit run --all-files
```

### **Linting & Formatting**
```bash
# Black (تنسيق الكود)
black .

# Flake8 (فحص الجودة)
flake8 .

# isort (ترتيب الاستيرادات)
isort .
```

---

## 📚 **كتابة التوثيق**

### **تعليقات الكود**
- اكتب تعليقات باللغة العربية
- اشرح المنطق المعقد
- أضف أمثلة للاستخدام

### **Docstrings**
```python
def optimize_video_compression(input_path: str, output_path: str, 
                              target_size_mb: float = None) -> bool:
    """
    تحسين ضغط الفيديو مع الحفاظ على الجودة
    
    هذه الدالة تستخدم FFmpeg لضغط الفيديو بطريقة ذكية
    تحافظ على الجودة مع تقليل الحجم.
    
    Args:
        input_path: مسار الفيديو المدخل
        output_path: مسار الفيديو المخرج
        target_size_mb: الحجم المستهدف بالميجابايت (اختياري)
        
    Returns:
        True إذا نجحت العملية، False في حالة الفشل
        
    Raises:
        FileNotFoundError: إذا لم يتم العثور على الملف
        RuntimeError: إذا فشلت عملية الضغط
        
    Example:
        >>> success = optimize_video_compression('input.mp4', 'output.mp4', 50)
        >>> print(f"نجحت العملية: {success}")
        نجحت العملية: True
    """
```

---

## 🚀 **عملية المساهمة**

### **1. Fork & Clone**
```bash
# Fork المشروع على GitHub
# ثم clone النسخة الخاصة بك
git clone https://github.com/your-username/enhanced-telegram-bot.git
cd enhanced-telegram-bot

# إضافة upstream
git remote add upstream https://github.com/original-repo/enhanced-telegram-bot.git
```

### **2. إنشاء فرع جديد**
```bash
# تحديث الفرع الرئيسي
git checkout main
git pull upstream main

# إنشاء فرع جديد للميزة
git checkout -b feature/amazing-feature
```

### **3. تطوير الميزة**
```bash
# كتابة الكود
# إضافة الاختبارات
# تحديث التوثيق

# commit التغييرات
git add .
git commit -m "feat: إضافة ميزة جديدة للعلامة المائية"
```

### **4. إرسال Pull Request**
```bash
# push الفرع
git push origin feature/amazing-feature

# إنشاء Pull Request على GitHub
# اكتب وصفاً واضحاً للتغييرات
```

---

## 📋 **قوالب المساهمة**

### **Bug Report Template**
```markdown
## وصف المشكلة
وصف واضح للمشكلة

## خطوات إعادة الإنتاج
1. اذهب إلى '...'
2. انقر على '...'
3. انظر إلى الخطأ

## السلوك المتوقع
ما كان يجب أن يحدث

## معلومات النظام
- OS: [مثل Ubuntu 20.04]
- Python: [مثل 3.9.0]
- FFmpeg: [مثل 4.4]

## سجلات الأخطاء
أضف السجلات هنا
```

### **Feature Request Template**
```markdown
## وصف الميزة
وصف واضح للميزة المطلوبة

## المشكلة التي تحلها
اشرح لماذا هذه الميزة مفيدة

## الحل المقترح
وصف كيفية تنفيذ الميزة

## البدائل المدروسة
أي حلول أخرى فكرت فيها

## معلومات إضافية
أي معلومات أخرى مفيدة
```

---

## 🏷️ **أنواع Commits**

### **Conventional Commits**
```bash
feat: إضافة ميزة جديدة
fix: إصلاح مشكلة
docs: تحديث التوثيق
style: تنسيق الكود
refactor: إعادة هيكلة الكود
test: إضافة اختبارات
chore: مهام الصيانة
```

### **أمثلة**
```bash
git commit -m "feat: إضافة دعم للعلامات المائية المتعددة"
git commit -m "fix: إصلاح مشكلة تسرب الذاكرة في معالج الفيديو"
git commit -m "docs: تحديث دليل البدء السريع"
```

---

## 🔍 **مراجعة الكود**

### **قبل إرسال PR**
- [ ] الكود يتبع معايير PEP 8
- [ ] تم إضافة اختبارات
- [ ] تم تحديث التوثيق
- [ ] الكود يعمل بدون أخطاء
- [ ] تم اختبار جميع الميزات

### **عند مراجعة PR**
- اقرأ الكود بعناية
- اطرح أسئلة واضحة
- اقترح تحسينات
- كن محترماً ومشجعاً

---

## 📞 **الحصول على المساعدة**

### **الموارد**
- [GitHub Issues](https://github.com/your-repo/issues)
- [GitHub Discussions](https://github.com/your-repo/discussions)
- [Telegram Group](https://t.me/your-group)
- [Documentation](https://your-docs.com)

### **التواصل**
- اطرح أسئلة واضحة
- قدم معلومات كافية
- كن صبوراً
- ساعد الآخرين

---

## 🎉 **شكراً لك!**

شكراً لمساهمتك في تطوير البوت المحسن! كل مساهمة، مهما كانت صغيرة، تساعد في جعل البوت أفضل.

---

**⭐ إذا أعجبك المشروع، لا تنس إعطاءه نجمة!**