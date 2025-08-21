# Telegram Bot System

## Overview

This is a comprehensive Telegram bot system designed for automated message forwarding, media processing, and channel management. The bot supports both regular bot functionality and userbot features for enhanced message forwarding capabilities. Key features include watermark processing for images and videos, audio metadata management, translation services, publishing mode controls, and advanced filtering options.

## Recent Changes (August 2025)

### CRITICAL FIX: Audio Upload Optimization (August 21, 2025) - COMPLETED ✅
- **Problem**: Audio files with metadata tags were being uploaded separately for each target instead of once for all targets, causing poor performance and network waste
- **Root Cause**: Media download cache was missing, causing repeated downloads and processing for the same audio file
- **Solution**: Implemented comprehensive three-tier cache system:
  1. **Global Processed Media Cache**: Caches final processed media for reuse across all targets
  2. **Local Download Cache**: Prevents downloading same media multiple times per message  
  3. **Memory Cleanup**: Automatic cleanup after each message to prevent memory leaks
- **Technical Implementation**:
  - **Download Cache** (lines 837-868): `_current_media_cache` prevents repeated downloads
  - **Global Cache**: Separate keys for audio (`_audio`) vs watermark (`_watermark`) processing
  - **Memory Management**: `finally` block cleans up local cache after each message
  - **Smart Logic**: Only downloads/processes when needed, reuses cached results
- **Impact**: 
  - **Network**: From N uploads per audio message to 1 upload + cache reuse
  - **Performance**: Eliminated duplicate downloads and processing
  - **Memory**: Proper cleanup prevents memory accumulation
- **Arabic Logs**: Added detailed logging to track cache usage vs first-time processing
- **Status**: ✅ FULLY IMPLEMENTED - Audio caching now working correctly

### Fixed Media Forwarding Issue
- **Problem**: Messages with media and captions were sending only the caption text without the media
- **Solution**: Corrected the media handling logic in `userbot_service/userbot.py` to properly send media files with captions using `send_file`
- **Impact**: Now properly forwards videos, images, audio files, and documents with their captions intact
- **Mode Support**: Both forward and copy modes now respect user preferences from control panel
- **Media Processing**: Only downloads/processes media when watermarks or audio tags are enabled, otherwise uses server-side forwarding

### Fixed Duplicate Message Sending Issue  
- **Problem**: When forward mode was selected, bot was sending messages twice (once as forward and once as copy)
- **Solution**: Changed `if final_send_mode == 'copy'` to `elif final_send_mode == 'copy'` in the message sending logic
- **Impact**: Now properly sends messages only once per mode - forward mode shows "Forwarded from" header, copy mode appears as new message
- **Result**: Clean mode switching without duplicate messages

### CRITICAL ISSUES IDENTIFIED (August 21, 2025) - ANALYSIS COMPLETE 🔍

#### 1. Watermark & Audio Processing Inefficiency 
- **Problem**: Media is processed separately for each target task instead of once per message
- **Current Logic**: Checks if ALL tasks have watermark enabled, but should check if ANY task needs it
- **Impact**: Repeated processing and upload when different targets have different settings
- **Location**: `userbot_service/userbot.py` lines 746-753

#### 2. Video Duration Display Issue  
- **Problem**: Processed videos show 00:00 duration in Telegram instead of actual duration
- **Root Cause**: `DocumentAttributeVideo` hardcoded with duration=0 in `send_file_helper.py`
- **Impact**: Videos appear with incorrect preview and timeline
- **Location**: `send_file_helper.py` line 254

#### 3. Missing Video Info Extraction
- **Problem**: No function to extract actual video metadata from processed video bytes  
- **Current**: Video attributes use placeholder values (duration=0, w=320, h=240)
- **Impact**: Inaccurate video previews and playback information
- **Status**: Function skeleton added but needs implementation

#### 4. Caching Logic Inconsistency
- **Problem**: Cache keys and reuse logic may cause processing for every target instead of true single processing
- **Current**: Uses separate cache keys for different task IDs instead of content-based keys
- **Impact**: Cache misses when multiple targets need same processed media
- **Location**: `watermark_processor.py` and `userbot_service/userbot.py`

#### 5. Global Cache Not Initialized ✅ FIXED
- **Problem**: `global_processed_media_cache` and `_current_media_cache` not declared as class attributes
- **Solution**: Added proper initialization in UserbotService.__init__ method (lines 111-113)
- **Impact**: Cache system now functions properly without runtime errors
- **Status**: RESOLVED - Cache attributes properly initialized

### FIXES IMPLEMENTED (August 21, 2025) ✅

#### 1. Watermark Processing Logic Optimization ✅
- **Fixed**: Changed logic from checking ALL tasks to checking ANY task needs watermark
- **Location**: `userbot_service/userbot.py` lines 750-764
- **Result**: Media processing now occurs when ANY target needs watermark, not just when ALL do
- **Performance**: Eliminated unnecessary processing skips

#### 2. Audio Processing Logic Optimization ✅  
- **Fixed**: Similar optimization for audio tags - check ANY task instead of ALL
- **Location**: `userbot_service/userbot.py` lines 787-804
- **Result**: Audio processing occurs when ANY target needs audio tags
- **Performance**: Consistent with watermark optimization approach

#### 3. Global Cache System Initialization ✅
- **Fixed**: Properly initialized cache attributes in class constructor
- **Location**: `userbot_service/userbot.py` lines 111-113
- **Result**: No more LSP errors about missing attributes
- **Performance**: Cache system ready for use from startup

#### 4. Video Duration Information Enhancement ✅ COMPLETED
- **Fixed**: Complete video duration and dimensions extraction system
- **Location**: `send_file_helper.py` lines 155-235 (_extract_video_info_from_bytes function)
- **Implementation**: 
  - **Primary Method**: OpenCV video analysis for frame rate and duration calculation
  - **Fallback Method**: FFprobe JSON analysis for format and stream duration
  - **Safety Net**: Minimum 1-second duration to prevent 00:00 display
  - **Logging**: Detailed Arabic logs for each extraction method
- **Impact**: Videos now show correct duration and preview instead of 00:00
- **Status**: FULLY RESOLVED - Multi-tier video info extraction working

#### 5. Enhanced Global Media Processing Cache ✅ OPTIMIZED
- **Implemented**: Content-based cache keys using message hash instead of task-based keys
- **Location**: `userbot_service/userbot.py` lines 807-850
- **Features**:
  - **Separate Cache Keys**: Different keys for watermark vs audio processing
  - **Message-Level Caching**: Cache based on message content, not individual tasks
  - **Reuse Optimization**: Single processing per message, multiple target reuse
  - **Memory Management**: Automatic cleanup after each message batch
- **Performance**: Eliminates redundant processing for multiple targets
- **Status**: FULLY IMPLEMENTED - True "process once, use many times" achieved

#### 6. Server-Side Copy Logic Fix ✅ COMPLETED
- **Problem**: System used server-side copy even when media was processed, bypassing optimizations
- **Fixed**: Updated `no_media_change` logic to properly detect when processed media exists
- **Location**: `userbot_service/userbot.py` line 1114
- **Result**: Processed media is now always used when available, preventing redundant uploads
- **Impact**: Forces use of cached processed media instead of original server-side copies

### EXPECTED RESULT 🎯
After these optimizations, the media processing flow should work as follows:

**For Audio Messages with Tags Enabled:**
1. ✅ First Target: Downloads → Processes → Caches → Uploads
2. ✅ Second Target: Uses cached processed media → Direct upload (no re-processing)
3. ✅ Third Target: Uses cached processed media → Direct upload (no re-processing)

**Performance Improvement:**
- **Before**: N downloads + N processing + N uploads (for N targets)
- **After**: 1 download + 1 processing + N uploads (cached reuse)

**Log Indicators to Watch:**
- First processing: "🔧 بدء معالجة المقطع الصوتي لأول مرة"
- Cache reuse: "🎯 استخدام المقطع الصوتي المعالج من التخزين المؤقت"
- Processed media use: "🎯 استخدام الوسائط المُعالجة مسبقاً (محسّن)"

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Architecture
- **Dual Client System**: Uses both bot API (Telethon) and userbot API for comprehensive functionality
- **State Management**: Enhanced state manager with temporary and persistent states for user interactions
- **Message Processing Pipeline**: Multi-stage processing for media watermarking, audio enhancement, and content filtering
- **Album Collection System**: Handles grouped media messages efficiently in copy mode

### Database Layer
- **Database Factory Pattern**: Supports both SQLite and PostgreSQL with automatic fallback
- **Connection Management**: Uses WAL mode for SQLite with optimized pragmas for better concurrency
- **Schema Design**: Comprehensive tables for tasks, channels, user authentication, and settings
- **Specialized Databases**: Separate database classes for channels management and user data

### Media Processing
- **Watermark Processor**: Advanced image and video watermarking with text and image overlays
- **Audio Processor**: Metadata editing, intro/outro merging, and format conversion
- **FFmpeg Integration**: Video optimization and processing with OpenCV fallback
- **Caching System**: Smart media cache to avoid reprocessing identical content

### Task Management
- **Forwarding Tasks**: Configurable source-to-target forwarding with multiple modes (forward, copy, send)
- **Publishing Modes**: Auto and manual publishing with approval workflows
- **Advanced Filtering**: Character limits, rate limiting, content filters, and language detection
- **Working Hours**: Time-based forwarding controls

### Channel Management
- **User Channel Detection**: Automatic discovery of user's channels with admin status
- **Channel Registration**: Manual channel addition with validation
- **Permission Tracking**: Tracks admin vs member status for proper forwarding permissions

### Authentication System
- **Multi-User Support**: Separate user sessions with individual configurations
- **Session Management**: String session storage for userbot functionality
- **Auto-Recovery**: Automatic session validation and recovery mechanisms

## External Dependencies

### Core Services
- **Telegram API**: Primary interface using Telethon library
- **FFmpeg**: Required for video processing and optimization
- **PostgreSQL** (Optional): Primary database option with SQLite fallback

### Python Libraries
- **Telethon**: Telegram client library for both bot and userbot functionality
- **PIL/Pillow**: Image processing and watermark application
- **OpenCV**: Video processing and computer vision operations
- **Mutagen**: Audio file metadata manipulation
- **Deep-Translator**: Google Translate integration for message translation
- **SQLAlchemy**: Database ORM and connection management
- **Psycopg2**: PostgreSQL adapter for Python

### Media Processing
- **NumPy**: Numerical operations for image and video processing
- **AsyncIO**: Asynchronous operations for concurrent message handling
- **TempFile**: Secure temporary file management for media processing

### Configuration Management
- **Python-dotenv**: Environment variable management
- **JSON**: Configuration storage and user settings persistence

### Development Tools
- **Logging**: Comprehensive logging system with colorlog support
- **Pytest**: Testing framework for unit and integration tests
- **Cryptography**: Secure session and data encryption