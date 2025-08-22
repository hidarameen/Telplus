#!/usr/bin/env python3
"""
Telegram Error Monitor - Real-time monitoring of rate limiting
مراقب أخطاء تليجرام - مراقبة فورية لحدود المعدل
"""

import time
import logging
from datetime import datetime, timedelta

class TelegramErrorMonitor:
    def __init__(self):
        self.last_rate_limit = None
        self.rate_limit_count = 0
        
    def log_rate_limit(self, required_wait: int):
        """تسجيل حدود المعدل"""
        now = datetime.now()
        self.last_rate_limit = now
        self.rate_limit_count += 1
        
        expected_clear_time = now + timedelta(seconds=required_wait)
        
        print(f"🚨 Rate Limit #{self.rate_limit_count}")
        print(f"⏰ Required Wait: {required_wait} seconds ({required_wait//60}m {required_wait%60}s)")
        print(f"🕐 Clear Time: {expected_clear_time.strftime('%H:%M:%S')}")
        print(f"📊 Total Rate Limits Today: {self.rate_limit_count}")

# Global monitor instance
error_monitor = TelegramErrorMonitor()
