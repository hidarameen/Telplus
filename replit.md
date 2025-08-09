# Overview

This project is a Telegram message forwarding automation system. It leverages Telethon to provide a comprehensive solution for managing and automating message forwarding between Telegram chats. The system comprises a Telegram bot for task management via an Arabic-language interface and a userbot service for the actual message forwarding. Its core capabilities include advanced message filtering, content modification, and flexible forwarding controls, aiming to provide a robust and user-friendly platform for automating Telegram communication.

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes

- **August 9, 2025 (CRITICAL BUG FIX - ADVANCED FEATURES EDIT BUTTONS FULLY RESOLVED)**: Fixed non-working sub-buttons for character limits, message limits, forwarding delay, and sending interval:
  - **ROOT CAUSE PHASE 1**: Missing callback handlers and database interaction methods for editing specific values
  - **FIXED PHASE 1**: Added complete callback handlers for `edit_char_range_`, `edit_rate_count_`, `edit_rate_period_`, `edit_forwarding_delay_`, `edit_sending_interval_`
  - **IMPLEMENTED PHASE 1**: 5 new editing methods with conversation state management and user input validation
  - **ROOT CAUSE PHASE 2**: Database update return values not being checked - showing success messages even when database updates failed
  - **FIXED PHASE 2**: Added proper return value checking for all database update methods to ensure success/failure feedback is accurate
  - **DATABASE VERIFICATION**: Confirmed all tables exist and updates work correctly - character_limit, rate_limit, forwarding_delay, sending_interval settings all updating properly in SQLite
  - **IMPROVED ERROR HANDLING**: Now shows specific database error messages when updates fail, preventing false success notifications
  - **CONVERSATION HANDLING**: Complete text input processing for all edit states with proper error handling and validation
  - **DATABASE INTEGRATION**: Connected to existing database update methods using correct parameter names and patterns
  - **USER EXPERIENCE**: Users can click edit buttons, enter new values through text input, and get accurate success/failure feedback
  - **VALIDATION**: Comprehensive input validation for ranges, positive numbers, and format requirements
  - **STATUS**: All advanced feature edit buttons now fully operational with accurate feedback and verified database integration working perfectly

# System Architecture

## UI/UX Decisions
The system features a Flask-based web application with Jinja2 templating, utilizing Bootstrap 5 for its UI framework with full RTL (Right-to-Left) support for the Arabic interface. Client-side interactions are handled by vanilla JavaScript, including form validation and real-time updates. Custom CSS ensures proper Arabic typography and responsive design. The Telegram bot interface is entirely in Arabic, offering intuitive management of forwarding tasks.

## Technical Implementations
The core functionality relies on two main services: a Telegram bot for user interaction (via `python-telegram-bot`) and a Telethon-based userbot for automated message forwarding using user account sessions. These services operate in separate threads managed by a central runner. Phone-based authentication with SMS verification and 2FA support is implemented for session management. Advanced features include comprehensive text cleaning (link, emoji, hashtag, phone number removal, keyword-based line filtering), sophisticated text formatting (supporting various Telegram markdown types including spoilers and hyperlinks), and advanced message filtering (by day, working hours, language, admin, duplicate, inline buttons, forwarded messages). Additional forwarding settings include link preview control, message pinning, notification control, and auto-delete with customizable timing.

## System Design Choices
The system is designed for multi-threaded operation to manage the bot and userbot services concurrently. It prioritizes a complete Arabic user experience for both the web interface and the Telegram bot. Architectural decisions focus on modularity, allowing for independent development and integration of features such as text cleaning, formatting, and various filtering mechanisms. Database schema is designed to store diverse configurations, including forwarding tasks, user sessions, advanced routing settings, message formatting preferences, text replacements, and word filters. Session management is handled through Flask sessions for web authentication and Telethon's StringSession for persistent userbot operation. Security is managed through Flask session encryption and Telegram's built-in authentication mechanisms.

# External Dependencies

- **Telegram APIs**:
    - Telethon (for userbot operations and client API interactions)
    - python-telegram-bot (for Telegram Bot API interactions)
- **Frontend Libraries**:
    - Bootstrap 5
    - Font Awesome
- **Python Libraries**:
    - Flask
    - SQLite3
- **Database**:
    - SQLite (with a custom wrapper)
- **Configuration**:
    - Environment variables for sensitive credentials and settings
```