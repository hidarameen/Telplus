# Overview
This project is a Telegram message forwarding automation system designed to streamline and automate message distribution between Telegram chats. It offers comprehensive tools for managing forwarding tasks, including advanced filtering, content modification, and flexible control over message delivery. The system aims to provide a robust and user-friendly platform for automating Telegram communication, accessible via an Arabic-language Telegram bot for task management.

# User Preferences
Preferred communication style: Simple, everyday language.

# Recent Changes - August 11, 2025

- **WATERMARK DISPLAY AND FUNCTIONALITY FIXES**: Successfully resolved critical watermark issues reported by user:
  - **FIXED WATERMARK SIZE**: Increased default watermark size from 10% to 20% and expanded maximum size from 50% to 80%
  - **FIXED TEXT WATERMARK SIZE**: Enhanced font size calculation from img_width//50 to img_width//25 for better visibility
  - **FIXED FILE FORMAT PRESERVATION**: Corrected file handling to preserve original extensions (.png, .jpg, etc.) and maintain proper file names instead of sending as "unnamed" files
  - **ENHANCED FILE NAMING**: Improved MIME type to extension mapping and filename extraction from Telegram document attributes
  - **FIXED IMAGE FORMAT HANDLING**: Modified watermark processor to preserve original image format (PNG, JPEG) instead of forcing JPEG conversion
  - **ADDED APPEARANCE CONTROLS**: Implemented missing watermark appearance settings interface with working resize buttons:
    - Size adjustment (5-80% in 5% increments)
    - Opacity adjustment (10-100% in 10% increments) 
    - Font size adjustment (12-72px in 4px increments)
  - **RESOLVED CV2 COMPATIBILITY**: Fixed cv2.VideoWriter_fourcc import issue for video watermark processing
  - **DATABASE SCHEMA UPDATE**: Modified size_percentage constraint to allow larger watermarks (5-80% range)
  - **USER INTERFACE**: All resize and appearance control buttons now functional in bot interface
  - **DATE**: August 11, 2025

- **WATERMARK FEATURE COMPLETE FIX**: Successfully resolved all remaining watermark functionality issues:
  - **FIXED SUB-BUTTON HANDLERS**: Corrected all appearance sub-button event handlers for size, opacity, font size, and color settings
  - **FIXED POSITION BUTTON**: Resolved position change button not working due to incorrect parameter parsing
  - **FIXED IMAGE UPLOAD**: Corrected download_media API usage and path handling for PNG image uploads
  - **ENHANCED MEDIA TYPE DETECTION**: Improved media type checking in UserBot for proper watermark application
  - **COMPREHENSIVE LOGGING**: Added detailed logging for watermark processing and application
  - **FULL INTEGRATION**: All watermark features now working correctly in forwarded messages
  - **USER INTERFACE**: Complete watermark management through task settings with all controls functional
  - **DATE**: August 11, 2025

- **WATERMARK FEATURE IMPLEMENTATION**: Successfully integrated comprehensive watermark functionality for media protection:
  - **CORE FUNCTIONALITY**: Added `WatermarkProcessor` class supporting both text and image watermarks on videos and images
  - **USER INTERFACE**: Added watermark settings to task management interface with dedicated "🏷️ العلامة المائية" section
  - **CUSTOMIZATION OPTIONS**: Implemented full control over:
    - Watermark type (text/image with transparent PNG support)
    - Position (top-left, top-right, bottom-left, bottom-right, center)
    - Size percentage (5-50%)
    - Opacity/transparency (10-100%)
    - Text color (including original color preservation)
    - Font size configuration
  - **MEDIA TYPE SELECTION**: Added granular control for applying watermarks to:
    - Photos (JPG, PNG, WebP)
    - Videos (MP4, AVI, MOV)
    - Documents (image files as documents)
  - **DATABASE INTEGRATION**: Created `task_watermark_settings` table with comprehensive configuration storage
  - **USERBOT INTEGRATION**: Enhanced message forwarding to automatically apply watermarks when enabled:
    - Integrated in all media forwarding scenarios
    - Supports album splitting and grouping
    - Maintains original filename structure
  - **TASK HANDLER**: Added complete watermark management interface:
    - Toggle watermark on/off
    - Configure watermark settings
    - Select media types for application
    - Real-time settings preview
  - **TECHNICAL IMPLEMENTATION**: Used OpenCV and Pillow for robust image/video processing
  - **USER EXPERIENCE**: All watermark controls accessible through task settings with intuitive Arabic interface
  - **DATE**: August 11, 2025

- **COMPLETE INLINE BUTTON PRESERVATION FIX**: Resolved critical root cause where original inline buttons were being stripped from forwarded messages in copy mode:
  - **ROOT CAUSE IDENTIFIED**: While filter logic was working correctly, the forwarding mechanism in copy mode was recreating messages without preserving original `reply_markup` from source messages
  - **COMPREHENSIVE SOLUTION**: Implemented preservation of original `reply_markup` when inline button filter is disabled:
    - Added `original_reply_markup` variable to capture original message buttons
    - Updated all 14 `client.send_message` and `client.send_file` calls to pass buttons correctly
    - Enhanced logging to show when original buttons are preserved vs. removed
  - **EMERGENCY PARAMETER FIX**: Discovered and fixed critical Telethon API compatibility issue:
    - **ERROR**: `MessageMethods.send_message() got an unexpected keyword argument 'reply_markup'`
    - **SOLUTION**: Converted all `reply_markup` parameters to `buttons` parameters for Telethon compatibility
    - **METHOD**: Combined original and custom buttons into single `buttons=original_reply_markup or inline_buttons` parameter
    - **CLEANUP**: Removed 14 duplicate button parameter lines from code
  - **DUAL BUTTON SUPPORT**: System now supports both custom inline buttons (from database) and original buttons (from source message) simultaneously
  - **COMPLETE COVERAGE**: All forwarding scenarios now preserve buttons: text messages, media messages, web pages, albums (split/grouped), spoiler messages
  - **SMART LOGIC**: Original buttons preserved only when filter is disabled, removed when filter is enabled
  - **VERIFICATION**: Bot now running successfully in console with successful message forwarding
  - **IMPACT**: Users can now forward messages with inline buttons in copy mode while filter is disabled
  - **CONSOLE CONFIRMATION**: Logs show "🔘 الحفاظ على الأزرار الأصلية - فلتر الأزرار الشفافة معطل" and successful forwarding
  - **DATE**: August 11, 2025

- **INLINE BUTTON FILTER LOGIC FIX**: Fixed critical issue where inline buttons were being removed despite filter being disabled:
  - **ROOT CAUSE**: Logic incorrectly processed messages when `inline_button_filter_enabled=0` but `block_messages_with_buttons=1`
  - **SOLUTION**: Implemented proper filter enablement check that respects the filter being disabled
  - **NEW BEHAVIOR**: When filter is disabled, messages with inline buttons pass through unchanged regardless of block setting
  - **COMPATIBILITY**: Added legacy compatibility handling for existing configurations with conflicting settings
  - **VERIFICATION**: Comprehensive test suite confirms buttons are preserved when filter is disabled
  - **LOGGING**: Enhanced debug logging to track filter decisions and settings conflicts
  - **DATE**: August 11, 2025

# System Architecture
## UI/UX Decisions
The system features a Flask-based web application with Jinja2 templating and Bootstrap 5, providing full RTL support for its Arabic interface. Client-side interactions utilize vanilla JavaScript for form validation and real-time updates. Custom CSS ensures proper Arabic typography and responsive design. The Telegram bot interface is entirely in Arabic, facilitating intuitive management of forwarding tasks.

## Technical Implementations
The core functionality relies on two main services: a Telegram bot for user interaction (using `python-telegram-bot`) and a Telethon-based userbot for automated message forwarding using user account sessions. These services operate concurrently in separate threads. Phone-based authentication with SMS verification and 2FA support is implemented for session management. Advanced features include comprehensive text cleaning (link, emoji, hashtag, phone number removal, keyword-based line filtering), sophisticated text formatting (supporting various Telegram markdown types including spoilers and hyperlinks), advanced message filtering (by day, working hours, language, admin, duplicate, inline buttons, forwarded messages), and **watermark functionality for media protection** (supporting both text and image watermarks with full customization of position, size, opacity, and color on photos, videos, and documents). Additional forwarding settings include link preview control, message pinning, notification control, and auto-delete with customizable timing. Message processing incorporates character limits, rate limiting per source message, forwarding delay, and sending intervals between targets. The system now supports preserving original inline buttons from forwarded messages in copy mode, alongside custom inline buttons, and includes an advanced admin filtering system utilizing Telegram's native Author Signature feature for channel messages. Working hours filtering has been enhanced with toggle functionality and dual modes (work hours/sleep hours) with a 24-hour visual scheduling interface. The language filter has been upgraded to support allow/block modes and quick selection of common languages, alongside custom language support.

## System Design Choices
The system is designed for multi-threaded operation to manage concurrent bot and userbot services. It prioritizes a complete Arabic user experience for both the web interface and the Telegram bot. Architectural decisions focus on modularity, allowing independent development and integration of features such as text cleaning, formatting, and various filtering mechanisms. The database schema stores diverse configurations, including forwarding tasks, user sessions, advanced routing settings, message formatting preferences, text replacements, and word filters. Session management is handled through Flask sessions for web authentication and Telethon's StringSession for persistent userbot operation. Security is managed through Flask session encryption and Telegram's built-in authentication mechanisms.

# External Dependencies
- **Telegram APIs**:
    - Telethon
    - python-telegram-bot
- **Frontend Libraries**:
    - Bootstrap 5
    - Font Awesome
- **Python Libraries**:
    - Flask
    - deep-translator
    - opencv-python (for watermark processing)
    - pillow (for image manipulation)
- **Database**:
    - SQLite (with a custom wrapper)
- **Configuration**:
    - Environment variables