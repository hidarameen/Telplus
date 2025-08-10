# Overview

This project is a Telegram message forwarding automation system designed to streamline and automate message distribution between Telegram chats. It provides comprehensive tools for managing forwarding tasks, including advanced filtering, content modification, and flexible control over message delivery. The system aims to offer a robust and user-friendly platform for automating Telegram communication, accessible via an Arabic-language Telegram bot for task management.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## UI/UX Decisions
The system features a Flask-based web application with Jinja2 templating and Bootstrap 5, providing full RTL support for its Arabic interface. Client-side interactions utilize vanilla JavaScript for form validation and real-time updates. Custom CSS ensures proper Arabic typography and responsive design. The Telegram bot interface is entirely in Arabic, facilitating intuitive management of forwarding tasks.

## Technical Implementations
The core functionality relies on two main services: a Telegram bot for user interaction (using `python-telegram-bot`) and a Telethon-based userbot for automated message forwarding using user account sessions. These services operate concurrently in separate threads. Phone-based authentication with SMS verification and 2FA support is implemented for session management. Advanced features include comprehensive text cleaning (link, emoji, hashtag, phone number removal, keyword-based line filtering), sophisticated text formatting (supporting various Telegram markdown types including spoilers and hyperlinks), and advanced message filtering (by day, working hours, language, admin, duplicate, inline buttons, forwarded messages). Additional forwarding settings include link preview control, message pinning, notification control, and auto-delete with customizable timing. Message processing incorporates character limits, rate limiting per source message, forwarding delay, and sending intervals between targets.

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
- **Database**:
    - SQLite (with a custom wrapper)
- **Configuration**:
    - Environment variables