#!/usr/bin/env python3
"""
مكون تثبيت FFmpeg تلقائياً
"""

import os
import sys
import subprocess
import platform
import logging
from typing import Tuple, Optional

logger = logging.getLogger(__name__)

class FFmpegInstaller:
    """مثبت FFmpeg التلقائي"""
    
    def __init__(self):
        self.system = platform.system().lower()
        self.distribution = self._get_distribution()
    
    def _get_distribution(self) -> str:
        """الحصول على توزيعة Linux"""
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read().lower()
                if 'ubuntu' in content or 'debian' in content:
                    return 'ubuntu'
                elif 'centos' in content or 'rhel' in content or 'fedora' in content:
                    return 'centos'
                elif 'alpine' in content:
                    return 'alpine'
                else:
                    return 'unknown'
        except:
            return 'unknown'
    
    def check_ffmpeg_installed(self) -> bool:
        """التحقق من تثبيت FFmpeg"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, text=True, timeout=10)
            return result.returncode == 0
        except:
            return False
    
    def install_ffmpeg_ubuntu(self) -> Tuple[bool, str]:
        """تثبيت FFmpeg على Ubuntu/Debian"""
        try:
            logger.info("🔄 تحديث قائمة الحزم...")
            subprocess.run(['sudo', 'apt', 'update'], 
                         capture_output=True, text=True, check=True)
            
            logger.info("📦 تثبيت FFmpeg...")
            result = subprocess.run(['sudo', 'apt', 'install', 'ffmpeg', '-y'], 
                                  capture_output=True, text=True, check=True)
            
            logger.info("✅ تم تثبيت FFmpeg بنجاح")
            return True, "تم تثبيت FFmpeg بنجاح"
            
        except subprocess.CalledProcessError as e:
            error_msg = f"فشل في تثبيت FFmpeg: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"خطأ غير متوقع: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def install_ffmpeg_centos(self) -> Tuple[bool, str]:
        """تثبيت FFmpeg على CentOS/RHEL/Fedora"""
        try:
            logger.info("🔄 تحديث قائمة الحزم...")
            subprocess.run(['sudo', 'yum', 'update', '-y'], 
                         capture_output=True, text=True, check=True)
            
            logger.info("📦 تثبيت FFmpeg...")
            result = subprocess.run(['sudo', 'yum', 'install', 'ffmpeg', '-y'], 
                                  capture_output=True, text=True, check=True)
            
            logger.info("✅ تم تثبيت FFmpeg بنجاح")
            return True, "تم تثبيت FFmpeg بنجاح"
            
        except subprocess.CalledProcessError as e:
            error_msg = f"فشل في تثبيت FFmpeg: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"خطأ غير متوقع: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def install_ffmpeg_alpine(self) -> Tuple[bool, str]:
        """تثبيت FFmpeg على Alpine"""
        try:
            logger.info("🔄 تحديث قائمة الحزم...")
            subprocess.run(['apk', 'update'], 
                         capture_output=True, text=True, check=True)
            
            logger.info("📦 تثبيت FFmpeg...")
            result = subprocess.run(['apk', 'add', 'ffmpeg'], 
                                  capture_output=True, text=True, check=True)
            
            logger.info("✅ تم تثبيت FFmpeg بنجاح")
            return True, "تم تثبيت FFmpeg بنجاح"
            
        except subprocess.CalledProcessError as e:
            error_msg = f"فشل في تثبيت FFmpeg: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"خطأ غير متوقع: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def install_ffmpeg_macos(self) -> Tuple[bool, str]:
        """تثبيت FFmpeg على macOS"""
        try:
            logger.info("📦 تثبيت FFmpeg باستخدام Homebrew...")
            result = subprocess.run(['brew', 'install', 'ffmpeg'], 
                                  capture_output=True, text=True, check=True)
            
            logger.info("✅ تم تثبيت FFmpeg بنجاح")
            return True, "تم تثبيت FFmpeg بنجاح"
            
        except subprocess.CalledProcessError as e:
            error_msg = f"فشل في تثبيت FFmpeg: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"خطأ غير متوقع: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def install_ffmpeg_windows(self) -> Tuple[bool, str]:
        """تثبيت FFmpeg على Windows"""
        try:
            logger.info("📦 تثبيت FFmpeg باستخدام Chocolatey...")
            result = subprocess.run(['choco', 'install', 'ffmpeg', '-y'], 
                                  capture_output=True, text=True, check=True)
            
            logger.info("✅ تم تثبيت FFmpeg بنجاح")
            return True, "تم تثبيت FFmpeg بنجاح"
            
        except subprocess.CalledProcessError as e:
            error_msg = f"فشل في تثبيت FFmpeg: {e.stderr}"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"خطأ غير متوقع: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def install_ffmpeg(self) -> Tuple[bool, str]:
        """تثبيت FFmpeg حسب النظام"""
        logger.info(f"🔍 النظام: {self.system}, التوزيعة: {self.distribution}")
        
        # التحقق من التثبيت الحالي
        if self.check_ffmpeg_installed():
            logger.info("✅ FFmpeg مثبت بالفعل")
            return True, "FFmpeg مثبت بالفعل"
        
        # التثبيت حسب النظام
        if self.system == 'linux':
            if self.distribution == 'ubuntu':
                return self.install_ffmpeg_ubuntu()
            elif self.distribution == 'centos':
                return self.install_ffmpeg_centos()
            elif self.distribution == 'alpine':
                return self.install_ffmpeg_alpine()
            else:
                return False, f"توزيعة غير مدعومة: {self.distribution}"
        elif self.system == 'darwin':  # macOS
            return self.install_ffmpeg_macos()
        elif self.system == 'windows':
            return self.install_ffmpeg_windows()
        else:
            return False, f"نظام غير مدعوم: {self.system}"
    
    def get_installation_instructions(self) -> str:
        """الحصول على تعليمات التثبيت اليدوي"""
        instructions = {
            'ubuntu': """
📋 تعليمات تثبيت FFmpeg على Ubuntu/Debian:
```bash
sudo apt update
sudo apt install ffmpeg -y
```

🔍 للتحقق من التثبيت:
```bash
ffmpeg -version
```
            """,
            'centos': """
📋 تعليمات تثبيت FFmpeg على CentOS/RHEL/Fedora:
```bash
sudo yum update -y
sudo yum install ffmpeg -y
```

🔍 للتحقق من التثبيت:
```bash
ffmpeg -version
```
            """,
            'alpine': """
📋 تعليمات تثبيت FFmpeg على Alpine:
```bash
apk update
apk add ffmpeg
```

🔍 للتحقق من التثبيت:
```bash
ffmpeg -version
```
            """,
            'darwin': """
📋 تعليمات تثبيت FFmpeg على macOS:
```bash
# تثبيت Homebrew أولاً (إذا لم يكن مثبتاً)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# تثبيت FFmpeg
brew install ffmpeg
```

🔍 للتحقق من التثبيت:
```bash
ffmpeg -version
```
            """,
            'windows': """
📋 تعليمات تثبيت FFmpeg على Windows:
```powershell
# تثبيت Chocolatey أولاً (إذا لم يكن مثبتاً)
Set-ExecutionPolicy Bypass -Scope Process -Force; [System.Net.ServicePointManager]::SecurityProtocol = [System.Net.ServicePointManager]::SecurityProtocol -bor 3072; iex ((New-Object System.Net.WebClient).DownloadString('https://community.chocolatey.org/install.ps1'))

# تثبيت FFmpeg
choco install ffmpeg -y
```

🔍 للتحقق من التثبيت:
```cmd
ffmpeg -version
```
            """
        }
        
        return instructions.get(self.system, f"تعليمات غير متوفرة للنظام: {self.system}")

# إنشاء instance عالمي
ffmpeg_installer = FFmpegInstaller()