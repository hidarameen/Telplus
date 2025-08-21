# Telegram Bot System

## Overview

This is a comprehensive Telegram bot system designed for automated message forwarding, media processing, and channel management. The bot supports both regular bot functionality and userbot features for enhanced message forwarding capabilities. Key features include watermark processing for images and videos, audio metadata management, translation services, publishing mode controls, and advanced filtering options.

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