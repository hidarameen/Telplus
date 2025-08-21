# Makefile للبوت المحسن
# Enhanced Bot Makefile

.PHONY: help install start stop test clean health-check docker-build docker-run docker-stop

# المتغيرات
PYTHON = python3
PIP = pip3
DOCKER = docker
DOCKER_COMPOSE = docker-compose

# المساعدة
help:
	@echo "🚀 البوت المحسن لـ Telegram - Enhanced Telegram Bot"
	@echo "=================================================="
	@echo ""
	@echo "الأوامر المتاحة:"
	@echo "  install        - تثبيت المتطلبات"
	@echo "  start          - تشغيل البوت"
	@echo "  stop           - إيقاف البوت"
	@echo "  test           - تشغيل الاختبارات"
	@echo "  clean          - تنظيف الملفات المؤقتة"
	@echo "  health-check   - فحص صحة البوت"
	@echo "  docker-build   - بناء صورة Docker"
	@echo "  docker-run     - تشغيل البوت بـ Docker"
	@echo "  docker-stop    - إيقاف البوت في Docker"
	@echo "  logs           - عرض السجلات"
	@echo "  backup         - نسخ احتياطي"
	@echo "  update         - تحديث البوت"
	@echo ""

# تثبيت المتطلبات
install:
	@echo "📦 تثبيت المتطلبات..."
	@chmod +x install_dependencies.sh
	@./install_dependencies.sh

# تشغيل البوت
start:
	@echo "🚀 تشغيل البوت..."
	@chmod +x start.sh
	@./start.sh

# إيقاف البوت
stop:
	@echo "🛑 إيقاف البوت..."
	@pkill -f "python.*main.py" || echo "البوت غير مشغل"

# تشغيل الاختبارات
test:
	@echo "🧪 تشغيل الاختبارات..."
	@$(PYTHON) -m pytest tests/ -v

# تنظيف الملفات المؤقتة
clean:
	@echo "🧹 تنظيف الملفات المؤقتة..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -delete
	@find . -type f -name "*.tmp" -delete
	@find . -type f -name "*.temp" -delete
	@find . -type f -name "temp_watermarked_*" -delete
	@find . -type f -name "watermarked_*" -delete
	@find . -type f -name "ffmpeg_*" -delete
	@rm -rf logs/*.log
	@rm -rf .pytest_cache/
	@rm -rf .coverage
	@echo "✅ تم التنظيف"

# فحص صحة البوت
health-check:
	@echo "🏥 فحص صحة البوت..."
	@chmod +x health_check.py
	@$(PYTHON) health_check.py

# بناء صورة Docker
docker-build:
	@echo "🐳 بناء صورة Docker..."
	@$(DOCKER) build -t enhanced-telegram-bot .

# تشغيل البوت بـ Docker
docker-run:
	@echo "🐳 تشغيل البوت بـ Docker..."
	@$(DOCKER_COMPOSE) up -d

# إيقاف البوت في Docker
docker-stop:
	@echo "🐳 إيقاف البوت في Docker..."
	@$(DOCKER_COMPOSE) down

# عرض السجلات
logs:
	@echo "📋 عرض السجلات..."
	@tail -f logs/bot.log || echo "لا توجد سجلات"

# نسخ احتياطي
backup:
	@echo "💾 إنشاء نسخة احتياطية..."
	@mkdir -p backups
	@tar -czf backups/bot_backup_$(shell date +%Y%m%d_%H%M%S).tar.gz \
		--exclude='__pycache__' \
		--exclude='*.pyc' \
		--exclude='.git' \
		--exclude='backups' \
		--exclude='*.db' \
		--exclude='logs' \
		--exclude='temp' \
		--exclude='tmp' \
		.
	@echo "✅ تم إنشاء النسخة الاحتياطية"

# تحديث البوت
update:
	@echo "🔄 تحديث البوت..."
	@git pull origin main
	@$(PIP) install -r requirements.txt --upgrade
	@echo "✅ تم التحديث"

# إعادة تشغيل البوت
restart: stop start

# إعادة تشغيل البوت في Docker
docker-restart: docker-stop docker-run

# عرض حالة البوت
status:
	@echo "📊 حالة البوت..."
	@ps aux | grep "python.*main.py" | grep -v grep || echo "البوت غير مشغل"

# عرض حالة Docker
docker-status:
	@echo "🐳 حالة Docker..."
	@$(DOCKER_COMPOSE) ps

# عرض استخدام الموارد
resources:
	@echo "💻 استخدام الموارد..."
	@echo "الذاكرة:"
	@free -h
	@echo ""
	@echo "المساحة:"
	@df -h
	@echo ""
	@echo "المعالج:"
	@top -bn1 | grep "Cpu(s)"

# تثبيت FFmpeg
install-ffmpeg:
	@echo "🎬 تثبيت FFmpeg..."
	@if command -v apt-get >/dev/null 2>&1; then \
		sudo apt update && sudo apt install -y ffmpeg; \
	elif command -v yum >/dev/null 2>&1; then \
		sudo yum install -y ffmpeg; \
	elif command -v dnf >/dev/null 2>&1; then \
		sudo dnf install -y ffmpeg; \
	elif command -v brew >/dev/null 2>&1; then \
		brew install ffmpeg; \
	else \
		echo "❌ نظام تشغيل غير مدعوم"; \
		exit 1; \
	fi
	@echo "✅ تم تثبيت FFmpeg"

# إنشاء البيئة
setup-env:
	@echo "🔧 إعداد البيئة..."
	@cp .env.example .env
	@echo "✅ تم إنشاء ملف .env"
	@echo "⚠️ يرجى تعديل الإعدادات في ملف .env"

# تثبيت كامل
full-install: install-ffmpeg install setup-env
	@echo "🎉 تم التثبيت الكامل!"
	@echo "🚀 البوت جاهز للتشغيل"

# عرض الإصدار
version:
	@echo "📋 إصدار البوت: 2.0.0"
	@echo "📅 تاريخ الإصدار: 2024-08-15"
	@echo "🐍 إصدار Python: $(shell python3 --version)"
	@echo "🐳 إصدار Docker: $(shell docker --version 2>/dev/null || echo 'غير مثبت')"

# عرض المساعدة
.DEFAULT_GOAL := help