# Telegram Bot System

## Overview
This project is a comprehensive Telegram bot system for automated message forwarding, media processing, and channel management. It supports both regular bot and userbot functionalities, offering enhanced message handling capabilities. Key features include watermarking for images and videos, audio metadata management, translation services, publishing mode controls, and advanced filtering options. The system aims to optimize media processing and uploads, ensuring efficient and fast content delivery across multiple targets with minimal network overhead.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Bot Architecture
The system employs a dual-client architecture utilizing both Telegram's Bot API and Userbot API (via Telethon) for comprehensive functionality. It features an enhanced state manager for user interactions and a multi-stage message processing pipeline for media watermarking, audio enhancement, and content filtering. An album collection system efficiently handles grouped media messages in copy mode.

### Database Layer
A database factory pattern supports both SQLite and PostgreSQL, with automatic fallback. It uses WAL mode for SQLite with optimized pragmas for concurrency. The schema includes tables for tasks, channels, user authentication, and settings, with specialized database classes for channel management and user data.

### Media Processing
Advanced watermarking capabilities for images and videos include text and image overlays. Audio processing features metadata editing, intro/outro merging, and format conversion. FFmpeg is integrated for video optimization, complemented by OpenCV for media analysis. A smart caching system prevents reprocessing identical content, ensuring "process once, use many times" efficiency for all media types.

### Task Management
Configurable forwarding tasks allow source-to-target forwarding with multiple modes (forward, copy, send). Publishing modes include auto and manual with approval workflows. Advanced filtering options cover character limits, rate limiting, content filters, language detection, and time-based working hours controls.

### Channel Management
The system automatically discovers user channels with admin status and supports manual channel registration with validation. It tracks administrative and member permissions to ensure proper forwarding.

### Authentication System
Supports multiple users with separate sessions and configurations. Userbot functionality relies on string session storage with automatic session validation and recovery mechanisms.

## External Dependencies

### Core Services
- **Telegram API**: Primary interface via Telethon library.
- **FFmpeg**: Essential for video processing and optimization.
- **PostgreSQL**: Optional primary database; SQLite is used as a fallback.

### Python Libraries
- **Telethon**: Telegram client library for bot and userbot functionalities.
- **PIL/Pillow**: Used for image processing and watermark application.
- **OpenCV**: Utilized for video processing and computer vision tasks.
- **Mutagen**: For manipulating audio file metadata.
- **Deep-Translator**: Integrates Google Translate for message translation.
- **SQLAlchemy**: Serves as the ORM for database interactions.
- **Psycopg2**: PostgreSQL adapter.

### Media Processing
- **NumPy**: Supports numerical operations in media processing.
- **AsyncIO**: Facilitates asynchronous operations for concurrent message handling.
- **TempFile**: Manages secure temporary files during media processing.

### Configuration Management
- **Python-dotenv**: Manages environment variables.
- **JSON**: Used for storing configurations and user settings.