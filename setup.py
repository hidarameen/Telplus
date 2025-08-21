#!/usr/bin/env python3
"""
إعداد البوت المحسن لـ Telegram
Enhanced Telegram Bot Setup
"""

import os
import re
from setuptools import setup, find_packages

# قراءة الإصدار من ملف VERSION
def get_version():
    with open('VERSION', 'r') as f:
        return f.read().strip()

# قراءة README
def read_readme():
    with open('README.md', 'r', encoding='utf-8') as f:
        return f.read()

# قراءة المتطلبات
def read_requirements():
    with open('requirements.txt', 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

# قراءة متطلبات التطوير
def read_dev_requirements():
    try:
        with open('requirements-dev.txt', 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError:
        return []

# إعداد المشروع
setup(
    name="enhanced-telegram-bot",
    version=get_version(),
    author="Enhanced Bot Team",
    author_email="team@your-domain.com",
    description="بوت Telegram محسن مع وظائف متقدمة للعلامة المائية ومعالجة الوسائط",
    long_description=read_readme(),
    long_description_content_type="text/markdown",
    url="https://github.com/your-repo/enhanced-telegram-bot",
    project_urls={
        "Bug Tracker": "https://github.com/your-repo/enhanced-telegram-bot/issues",
        "Documentation": "https://github.com/your-repo/enhanced-telegram-bot#readme",
        "Source Code": "https://github.com/your-repo/enhanced-telegram-bot",
        "Changelog": "https://github.com/your-repo/enhanced-telegram-bot/blob/main/CHANGELOG.md",
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Communications :: Chat",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
        "Topic :: Multimedia :: Video",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Monitoring",
        "Topic :: Utilities",
    ],
    keywords=[
        "telegram", "bot", "watermark", "media", "processing",
        "enhanced", "optimization", "ffmpeg", "opencv", "pillow",
        "async", "telethon", "python", "arabic", "enhanced-bot"
    ],
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=read_requirements(),
    extras_require={
        "dev": read_dev_requirements(),
        "test": [
            "pytest>=8.3.3",
            "pytest-asyncio>=0.24.0",
            "pytest-cov>=6.0.0",
        ],
        "docs": [
            "sphinx>=7.2.0",
            "sphinx-rtd-theme>=2.0.0",
            "myst-parser>=2.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "enhanced-bot=main:main",
            "bot-health-check=health_check:main",
        ],
    },
    include_package_data=True,
    package_data={
        "": [
            "*.txt", "*.md", "*.yml", "*.yaml", "*.toml",
            "*.sh", "Dockerfile", "LICENSE", "VERSION",
        ],
    },
    data_files=[
        ("", ["README.md", "CHANGELOG.md", "LICENSE", "VERSION", ".env.example"]),
        ("scripts", ["install_dependencies.sh", "start.sh"]),
        ("docker", ["Dockerfile", "docker-compose.yml"]),
        ("docs", ["QUICK_START.md", "CONTRIBUTING.md", "SECURITY.md", "SUPPORT.md", "ROADMAP.md"]),
    ],
    zip_safe=False,
    platforms=["any"],
    license="MIT",
    maintainer="Enhanced Bot Team",
    maintainer_email="maintainers@your-domain.com",
    download_url="https://github.com/your-repo/enhanced-telegram-bot/archive/v{}.tar.gz".format(get_version()),
    provides=["enhanced_telegram_bot"],
    requires_python=">=3.8",
    setup_requires=[
        "setuptools>=69.0.0",
        "wheel>=0.42.0",
    ],
    test_suite="tests",
    tests_require=[
        "pytest>=8.3.3",
        "pytest-asyncio>=0.24.0",
        "pytest-cov>=6.0.0",
    ],
    options={
        "bdist_wheel": {
            "universal": True,
        },
    },
    # معلومات إضافية
    long_description_content_type="text/markdown",
    include_package_data=True,
    exclude_package_data={
        "": [
            "*.pyc", "*.pyo", "__pycache__", ".git", ".env",
            "*.db", "*.log", "logs/", "temp/", "tmp/",
            ".pytest_cache/", ".coverage", "*.egg-info/",
            "build/", "dist/", ".venv/", "venv/", "env/"
        ],
    },
)