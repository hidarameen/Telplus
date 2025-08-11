# Overview

This project is a Telegram message forwarding automation system designed to streamline and automate message distribution between Telegram chats. It provides comprehensive tools for managing forwarding tasks, including advanced filtering, content modification, and flexible control over message delivery. The system aims to offer a robust and user-friendly platform for automating Telegram communication, accessible via an Arabic-language Telegram bot for task management.

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes - August 11, 2025

- **FILTER SYSTEM CRITICAL FIXES**: Resolved all major filter functionality issues with complete testing and verification:
  - **DAY FILTER INTEGRATION**: Fixed missing day filter check in message processing - now properly blocks messages on restricted days
  - **ADMIN FILTER COMPLETE OVERHAUL**: Fixed admin filter system with proper Telethon sender ID detection and database integration
  - **WORKING HOURS TIMEZONE FIX**: Corrected timezone handling to use Riyadh time (UTC+3) for accurate hour-based filtering
  - **BUTTON INTERFACE FIXES**: Resolved `show_admin_filter` error by correcting function reference to `show_admin_filters`
  - **DATABASE INTEGRATION**: Added missing `get_admin_filter_setting` function for proper admin permission checking
  - **MESSAGE SENDER DETECTION**: Implemented proper sender ID extraction from Telethon message objects for admin filtering
  - **FILTER VERIFICATION**: All filters (day, working hours, admin) now working with real-time logging and blocking confirmation

- **TASK SETTINGS UI REDESIGN**: Completely redesigned task settings interface with improved organization and visual appeal:
  - **TWO-COLUMN LAYOUT**: Reorganized all buttons to display 2 buttons per row for better space utilization
  - **ENHANCED EMOJIS**: Upgraded emoji selection for better visual identification of each feature
  - **ORGANIZED SECTIONS**: Grouped related settings logically (sources/targets, filters, formatting, etc.)
  - **CONSISTENT DESIGN**: Applied same layout pattern to all sub-menus (forwarding settings, advanced filters, advanced features, media filters)
  - **IMPROVED STATUS INDICATORS**: Enhanced visual status indicators throughout all settings menus

- **BOT SETTINGS INTERFACE ENHANCEMENT**: Added comprehensive user preference management in Telegram bot:
  - **LANGUAGE SETTINGS**: Added language change button in main settings menu with 6 language options (Arabic, English, French, German, Spanish, Russian)
  - **TIMEZONE SETTINGS**: Added timezone change button with 24 timezone options covering Middle East, Europe, America, Asia, and Australia
  - **USER PREFERENCES STORAGE**: Integrated with existing user_settings database table for persistent preference storage
  - **REAL-TIME FEEDBACK**: Users receive confirmation messages when settings are successfully changed
  - **NAVIGATION FLOW**: Added proper back navigation between settings menus and main menu
  - **DUPLICATE BUTTON FIX**: Removed duplicate language/timezone buttons from main menu, keeping them only in settings

- **COMPREHENSIVE FILTER INTERFACE FIXES**: Resolved all major UI responsiveness issues across the filter system:
  - **TOGGLE BUTTONS FIXED**: All filter toggle buttons now properly update interface text and status indicators
  - **WORKING HOURS MODE TOGGLE**: Fixed button handler to correctly parse task IDs and refresh interfaces
  - **ADVANCED FILTER IMPROVEMENTS**: Enhanced `toggle_advanced_filter` function with proper interface refresh for all filter types
  - **USER FEEDBACK ENHANCEMENT**: Added detailed status messages showing whether filters are enabled/disabled
  - **DATABASE INTEGRATION**: Improved UserBot task refresh after filter changes to ensure real-time updates

- **FILTER-SPECIFIC ENHANCEMENTS**:
  - **DUPLICATE FILTER**: Toggle button updates interface immediately with clear status indicators
  - **LANGUAGE FILTER**: Toggle button properly refreshes language filter menu with current status
  - **FORWARDED MESSAGE FILTER**: Toggle button updates forwarded message filter interface
  - **DAY FILTER**: Toggle button refreshes day filter interface with visual status updates
  - **WORKING HOURS FILTER**: Enhanced toggle functionality with proper interface refresh

# Previous Changes - August 10, 2025

- **ENHANCED WORKING HOURS SYSTEM**: Completely redesigned working hours with advanced scheduling:
  - **TOGGLE FUNCTIONALITY**: Enable/disable working hours filter with one click
  - **DUAL MODES**: Work hours mode (works only during selected hours) vs Sleep hours mode (stops during selected hours)
  - **24-HOUR SCHEDULE**: Visual hourly grid interface for precise hour selection
  - **BULK OPERATIONS**: Select all/clear all hours with single button clicks
  - **SMART INTERFACE**: Real-time hour ranges display and visual indicators
  - **DATABASE REDESIGN**: New table structure with task_working_hours and task_working_hours_schedule
  - **USERBOT INTEGRATION**: Complete integration with message filtering logic

- **LANGUAGE FILTER IMPROVEMENTS**: Fixed critical issues and enhanced user experience:
  - **MESSAGE DISPLAY FIX**: Resolved "حدث خطأ أثناء الإضافة" error when adding custom languages
  - **IMPROVED ERROR HANDLING**: Better conversation state management and error recovery
  - **ENHANCED MENU SYSTEM**: Proper message sending after language addition

- **LANGUAGE FILTER MAJOR UPGRADE**: Completely redesigned language filter with advanced allow/block modes:
  - **ALLOW/BLOCK MODES**: Toggle between allowing specific languages or blocking specific languages
  - **QUICK LANGUAGE SELECTION**: One-click addition of 10 common languages (Arabic, English, French, etc.)
  - **CUSTOM LANGUAGE SUPPORT**: Manual addition of any language with custom codes and names
  - **VISUAL SELECTION INTERFACE**: Clear visual indicators (✅/🚫/⚪) for selected/unselected languages
  - **TOGGLE FUNCTIONALITY**: Working toggle button for enable/disable filter
  - **DATABASE ENHANCEMENTS**: Added language_filter_mode column to support new functionality
  - **USER INTERFACE**: Complete Arabic interface with intuitive controls and descriptions

- **DUPLICATE FILTER COMPLETION**: Fixed all remaining issues with duplicate message filtering:
  - **DATABASE COLUMNS**: Added missing similarity_threshold and time_window_hours columns
  - **USER INPUT HANDLING**: Added proper user state management for threshold and time window input
  - **FULLY FUNCTIONAL**: All buttons respond correctly and filtering works as expected

- **TRANSLATION BYPASS FOR FORWARD MODE**: Added intelligent translation bypass when forwarding mode is set to "forward" (not copy):
  - **FORWARD MODE**: Skips translation completely and sends message as-is to preserve original content
  - **COPY MODE**: Applies translation normally with all text processing features
  - **LOGGING**: Added detailed Arabic logs showing when translation is skipped vs applied

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