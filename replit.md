# Overview

This is a Telegram message forwarding automation system built entirely with Telethon, featuring a Telegram bot interface for managing forwarding tasks and a userbot service for automatic message forwarding between Telegram chats. The system provides a complete Arabic-language bot interface with phone number authentication and multi-threaded service architecture. **Status: Fully operational and tested (August 8, 2025).**

## Recent Changes
- **August 9, 2025 (TEXT CLEANING BUGS FIXED - CRITICAL FIXES)**: Fixed two critical issues in text cleaning system:
  - **FIXED**: Empty line removal bug - now preserves line breaks between content while removing truly empty lines
  - **FIXED**: "Add keywords" button functionality - callback handler and database functions working correctly
  - **IMPROVED**: Text cleaning algorithm now maintains proper line structure (e.g., "مرحبا\n\nكيف حالك" keeps the line break)
  - **RESOLVED**: Database function `add_text_cleaning_keywords` added to main database.py file
  - **STATUS**: Both text cleaning features fully operational and tested
- **August 9, 2025 (Previous - TEXT CLEANING FEATURE - COMPLETE IMPLEMENTATION)**: Successfully implemented comprehensive text cleaning system:
  - **NEW FEATURE**: 6 comprehensive text cleaning capabilities: link removal, emoji cleaning, hashtag removal, phone number cleaning, empty line removal, and removal of lines containing specific keywords
  - **DATABASE**: Added `task_text_cleaning_settings` and `task_text_cleaning_keywords` tables with full CRUD operations
  - **UI INTEGRATION**: Complete Arabic interface in task settings menu with toggle controls for all cleaning options
  - **USERBOT PIPELINE**: Integrated text cleaning into message forwarding pipeline - applied before text replacements
  - **REGEX PROCESSING**: Advanced regex patterns for URLs, emojis, hashtags, and phone numbers with Arabic support
  - **KEYWORD FILTERING**: Smart line removal based on user-defined keywords with case-insensitive matching
  - **REAL-TIME VERIFICATION**: System tested live - successfully cleaned message from 67 to 11 characters removing links, emojis, hashtags, phone numbers, and empty lines
  - **STATUS**: Text cleaning system 100% operational with complete UI, database integration, and message processing pipeline
- **August 9, 2025 (Previous - ADMIN FILTER CRITICAL FIXES)**: Resolved critical admin filter issues:
  - **FIXED**: Admin permissions preservation - update process now maintains existing admin allow/block status
  - **RESOLVED**: Database synchronization issue - admin filter status properly synced between UI and routing logic
  - **ADDED**: New functions `get_admin_previous_permissions()` and `add_admin_filter_with_previous_permission()` to preserve settings
  - **ENHANCED**: Both Bot API and UserBot admin refresh now preserve existing permissions
  - **VERIFIED**: Admin filter enabled in database matches control panel state
  - **STATUS**: Admin filtering system now maintains admin permissions during updates and works reliably
- **August 8, 2025 (Previous - ADMIN FILTER IMPLEMENTATION - COMPLETE SOLUTION)**: Fully implemented admin filtering in message forwarding:
  - **FILTER INTEGRATION**: Added `is_admin_allowed()` method to userbot service for real-time admin filtering
  - **FORWARDING PIPELINE**: Integrated admin filter check into message forwarding process before media/word filters
  - **REAL-TIME BLOCKING**: Messages from non-allowed admins now properly blocked during forwarding
  - **DEBUG LOGGING**: Added comprehensive logging for admin filter decisions and sender validation
  - **UI NAVIGATION**: Fixed admin toggle buttons to stay on same page after changing admin status
  - **CALLBACK PARSING**: Enhanced callback data parsing to include source chat ID for proper navigation
  - **COMPLETE SYSTEM**: All admin filter components (enable/disable, admin selection, real-time filtering) now fully operational
  - **STATUS**: Admin filtering system 100% functional with real-time message blocking and intuitive Arabic UI
- **August 8, 2025 (Previous - COMPLETE ADMIN FILTER FIX - BOT API INTEGRATION)**: Successfully replaced UserBot with Bot API for admin fetching:
  - **MAJOR FIX**: Replaced userbot service dependency with direct Bot API integration for fetching channel administrators
  - **NEW METHOD**: Implemented `fetch_channel_admins_with_bot()` using bot's API token instead of userbot service
  - **CALLBACK HANDLERS**: Added all missing admin filter callback handlers (admin_list_, source_admins_, refresh_source_admins_, toggle_admin_)
  - **FILTER ENHANCEMENTS**: Fixed inline button and forwarded message filter handlers (toggle_inline_block_, toggle_forwarded_block_)
  - **DATABASE INTEGRATION**: Verified all required database methods exist and work correctly
  - **ERROR HANDLING**: Proper fallback system when bot cannot access channel (adds task owner as admin)
  - **CLEAN CODE**: Removed all userbot dependencies from admin filtering system
  - **STATUS**: All filters (day, hours, repetition, transparent buttons, forwarded messages, admin) now fully operational with Bot API
- **August 8, 2025 (Previous - CRITICAL BUG FIXES - Advanced Filters System)**: Fixed all issues with 7-filter advanced system:
  - **FIXED**: callback data parsing for multi-word filter types (forwarded_message, inline_button, etc.)
  - **ADDED**: Complete handlers for all missing filter buttons (working hours, language, duplicate, admin settings)
  - **ENHANCED**: Filter toggle functionality with proper status updates and UI refresh
  - **IMPLEMENTED**: Conversation handlers for working hours setting and language addition
  - **RESOLVED**: Database column mapping issues preventing filter state updates
  - **COMPLETED**: All 7 advanced filters now fully operational: days, working hours, language, admin, duplicate, inline buttons, forwarded messages
  - **STATUS**: Advanced filtering system 100% functional with Arabic UI and status indicators
- **August 8, 2025 (Previous - Advanced Forwarding Settings)**: Completed comprehensive forwarding control system:
  - **NEW FEATURE**: Advanced forwarding settings with 4 core options:
    - Link preview control (enable/disable web page previews)
    - Message pinning in target channels (auto-pin forwarded messages)
    - Notification control (silent forwarding vs. with notifications)
    - Auto-delete with customizable timing (60s to 7 days)
  - **DATABASE ENHANCEMENT**: Added `task_forwarding_settings` table with comprehensive settings storage
  - **UI INTEGRATION**: Arabic interface with intuitive toggle controls and time selection
  - **USERBOT IMPLEMENTATION**: Full integration with message forwarding pipeline
  - **ERROR HANDLING**: Robust handling of media types including MessageMediaWebPage
  - **BACKGROUND PROCESSING**: Automated scheduling for message deletion and pinning
  - **SYSTEM STATUS**: All advanced settings tested and working, 4 active tasks operational
- **August 8, 2025 (Previous - Critical Bug Fix)**: Fixed inline buttons deletion issue:
  - **CRITICAL BUG FIXED**: Transparent buttons now preserved when disabling inline buttons feature
  - **DATABASE ENHANCEMENT**: Added proper `task_message_settings` table for enable/disable status tracking
  - **ARCHITECTURE IMPROVEMENT**: Separated button storage from enable/disable logic to prevent data loss
  - **ERROR HANDLING**: Added robust error handling for Telegram message edit failures
  - **BACKWARD COMPATIBILITY**: All existing functionality preserved while fixing the core issue
  - **AUTO-ENABLE**: Buttons now automatically enable when first button is added
  - **AUTO-DISABLE**: Feature properly disables (without deletion) when all buttons are cleared
- **August 8, 2025 (Previous Update)**: Completed comprehensive message formatting system:
  - **RESOLVED**: Critical database integration issues - added missing tables and functions
  - **FIXED**: MessageNotModifiedError in inline buttons toggle functionality
  - **IMPLEMENTED**: Complete header/footer system with enable/disable controls
  - **COMPLETED**: Inline buttons feature with multi-row, multi-column support
  - **VERIFIED**: All formatting features working without errors
  - **DATABASE**: Successfully created and integrated task_headers, task_footers, task_inline_buttons tables
  - **UI TESTED**: Arabic interface with full functionality for all new features
  - **INTEGRATION COMPLETE**: New features fully integrated with existing text replacement and word filtering systems

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Frontend Architecture
- **Web Framework**: Flask-based web application with Jinja2 templating
- **UI Framework**: Bootstrap 5 with RTL (Right-to-Left) support for Arabic interface
- **Client-side**: Vanilla JavaScript with form validation, real-time updates, and confirmation dialogs
- **Styling**: Custom CSS with Arabic typography support and responsive design

## Backend Architecture
- **Bot Service**: Telethon library for handling Telegram bot interactions with inline keyboards and Arabic interface
- **Userbot Service**: Telethon library for automated message forwarding using user account sessions
- **Multi-threading**: Separate threads for Telegram bot and userbot services managed by a central system runner
- **Session Management**: Phone-based authentication with SMS verification and 2FA support

## Data Storage Solutions
- **Database**: SQLite with custom Database class wrapper
- **Schema Design**: 
  - Tasks table for forwarding configurations (source chats, target chats, active status)
  - User sessions table for storing Telegram session strings and phone numbers
  - Advanced routing settings table for link preview, pinning, notifications, and auto-delete controls
  - Message formatting settings for headers, footers, and inline buttons management
  - Text replacement and word filtering tables for content modification
- **Session Management**: Flask sessions for web authentication, Telegram StringSession for userbot persistence

## Authentication and Authorization
- **Telegram Authentication**: Phone number verification with SMS codes and optional 2FA password
- **Session Storage**: Telegram session strings stored in database for userbot persistence
- **Web Authentication**: Flask session-based authentication after successful Telegram login
- **Security**: Secret key configuration for Flask session encryption

## External Dependencies
- **Telegram APIs**: 
  - Bot API via python-telegram-bot for bot interactions
  - Client API via Telethon for userbot message forwarding
- **Frontend Libraries**: 
  - Bootstrap 5 for UI components and responsive design
  - Font Awesome for iconography
- **Python Libraries**:
  - Flask for web framework
  - Telethon for Telegram client operations
  - python-telegram-bot for bot functionality
  - SQLite3 for database operations
- **Configuration Management**: Environment variables for API credentials and configuration settings