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