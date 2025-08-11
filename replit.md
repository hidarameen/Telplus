# Overview
This project is a Telegram message forwarding automation system designed to streamline and automate message distribution between Telegram chats. It offers comprehensive tools for managing forwarding tasks, including advanced filtering, content modification, and flexible control over message delivery. The system aims to provide a robust and user-friendly platform for automating Telegram communication, accessible via an Arabic-language Telegram bot for task management.

# User Preferences
Preferred communication style: Simple, everyday language.

# Recent Changes
- Fixed watermark filename issue: Images with watermarks were being sent as "unnamed" files without extensions. Added missing `file_name` parameter in the photo watermark sending logic to preserve original filenames and extensions like .jpg, .png, etc. (2025-08-11)

# System Architecture
## UI/UX Decisions
The system features a Flask-based web application with Jinja2 templating and Bootstrap 5, providing full RTL support for its Arabic interface. Client-side interactions utilize vanilla JavaScript for form validation and real-time updates. Custom CSS ensures proper Arabic typography and responsive design. The Telegram bot interface is entirely in Arabic, facilitating intuitive management of forwarding tasks.

## Technical Implementations
The core functionality relies on a Telegram bot for user interaction (using `python-telegram-bot`) and a Telethon-based userbot for automated message forwarding using user account sessions. These services operate concurrently in separate threads. Phone-based authentication with SMS verification and 2FA support is implemented for session management. Advanced features include comprehensive text cleaning (link, emoji, hashtag, phone number removal, keyword-based line filtering), sophisticated text formatting (supporting various Telegram markdown types including spoilers and hyperlinks), advanced message filtering (by day, working hours, language, admin, duplicate, inline buttons, forwarded messages), and watermark functionality for media protection (supporting both text and image watermarks with full customization of position, size, opacity, and color on photos, videos, and documents). Additional forwarding settings include link preview control, message pinning, notification control, and auto-delete with customizable timing. Message processing incorporates character limits, rate limiting per source message, forwarding delay, and sending intervals between targets. The system supports preserving original inline buttons from forwarded messages in copy mode, alongside custom inline buttons, and includes an advanced admin filtering system utilizing Telegram's native Author Signature feature for channel messages. Working hours filtering has enhanced toggle functionality and dual modes (work hours/sleep hours) with a 24-hour visual scheduling interface. The language filter has been upgraded to support allow/block modes and quick selection of common languages, alongside custom language support.

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