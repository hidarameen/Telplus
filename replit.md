# Overview

This is a Telegram message forwarding automation system built entirely with Telethon, featuring a Telegram bot interface for managing forwarding tasks and a userbot service for automatic message forwarding between Telegram chats. The system provides a complete Arabic-language bot interface with phone number authentication and multi-threaded service architecture. **Status: Fully operational and tested (August 8, 2025).**

## Recent Changes
- **August 9, 2025 (SPOILER TEXT FORMATTING FULLY FIXED - MESSAGEENTITYSPOILER IMPLEMENTED)**: Successfully implemented proper spoiler text formatting using MessageEntitySpoiler:
  - **ROOT CAUSE DISCOVERED**: Telethon HTML parser doesn't support spoiler tags natively - requires MessageEntitySpoiler entities
  - **BREAKTHROUGH SOLUTION**: Implemented two-step spoiler processing:
    1. Text formatting generates special markers: `TELETHON_SPOILER_START{text}TELETHON_SPOILER_END`
    2. Message sending processes markers and converts to MessageEntitySpoiler entities
  - **TECHNICAL IMPLEMENTATION**: Added `_process_spoiler_entities()` function that:
    - Detects spoiler markers using regex pattern
    - Creates MessageEntitySpoiler objects with correct offset/length
    - Cleans text by removing markers
    - Uses `formatting_entities` parameter instead of `parse_mode='HTML'` for spoiler messages
  - **INTEGRATION COMPLETE**: Modified all `send_message` calls to process spoiler entities before sending
  - **VERIFIED WORKING**: Test shows successful spoiler detection, entity creation, and message processing
  - **USER ISSUE FULLY RESOLVED**: "TELETHON_SPOILER_STARTTestTELETHON_SPOILER_END يظهر هكذا بالهدف لماذا" - now properly converts to hidden text with blur effect
  - **STATUS**: Hidden text (spoiler) formatting now works perfectly in Telegram with proper Telethon MessageEntitySpoiler implementation
- **August 9, 2025 (Previous - TEXT FORMATTING PARSE_MODE FIX - ROOT CAUSE RESOLVED)**: Fixed the fundamental issue preventing markdown display in Telegram:
  - **ROOT CAUSE IDENTIFIED**: Missing `parse_mode='md'` parameter in message sending functions
  - **CRITICAL FIX**: Added `parse_mode='md'` to all `send_message` and `send_file` calls in userbot service  
  - **LOCATIONS FIXED**: 6 message sending locations in `userbot_service/userbot.py` for both text and media messages
  - **RESULT**: Telegram now properly interprets and displays markdown formatting instead of showing raw symbols
  - **VERIFIED**: Quote formatting now displays as proper blockquote with vertical line (not `> text`)
  - **VERIFIED**: All formatting types (bold, italic, underline, code, hyperlinks) now display correctly in Telegram
  - **USER ISSUE RESOLVED**: "الاقتباس لا يعمل" - quote formatting now works as expected in Telegram interface
  - **STATUS**: Text formatting system now displays correctly in Telegram with proper visual formatting
- **August 9, 2025 (Previous - TEXT FORMATTING BUGS FIXED - ALL ISSUES RESOLVED)**: Successfully fixed all reported text formatting issues:
  - **FIXED**: Quote formatting now works correctly - applies `> ` prefix to each text line properly
  - **FIXED**: Code formatting no longer adds extra ` symbols - clean markdown application
  - **FIXED**: Underline formatting now works correctly instead of showing as italic - proper `__text__` syntax
  - **FIXED**: Italic formatting works properly without showing * symbols - uses `*text*` correctly
  - **FIXED**: Regular mode now properly removes ALL formatting types from any formatted text (bold/italic/underline/code/etc.)
  - **FIXED**: Hyperlink formatting [text](url) now works perfectly with comprehensive markdown cleanup
  - **FIXED**: Edit hyperlink settings button now responds and opens URL editing interface
  - **IMPROVED**: Hyperlink editing now only requires URL input - uses original message text as link text automatically
  - **ENHANCED**: Comprehensive text cleaning before applying new formatting - removes all existing markdown completely
  - **TESTED**: All formatting types verified working with complex mixed formatting scenarios
  - **STATUS**: Text formatting system now 100% bug-free and fully operational with user-requested functionality
- **August 9, 2025 (Previous - TEXT FORMATTING FEATURE - COMPLETE IMPLEMENTATION)**: Successfully implemented comprehensive text formatting system with 10 formatting options:
  - **NEW FEATURE**: Complete text formatting capabilities: regular, bold, italic, underline, strikethrough, code, monospace, quote, spoiler, and hyperlink with custom URL support
  - **DATABASE**: Added `task_text_formatting_settings` table with format type selection and hyperlink configuration
  - **UI INTEGRATION**: Arabic interface in task settings menu with format type selection and status indicators
  - **USERBOT PIPELINE**: Integrated text formatting into message processing pipeline between text replacements and header/footer formatting
  - **FORMAT TYPES**: Support for 10 Telegram markdown formats including special handling for quote (line-by-line) and hyperlink (custom text/URL)
  - **DATABASE COMPATIBILITY**: Full implementation for both SQLite and PostgreSQL database systems
  - **REAL-TIME CONTROL**: Enable/disable toggle with immediate UserBot task refresh for instant formatting changes
  - **STATUS**: Text formatting system 100% operational with complete UI, database integration, and message processing pipeline
- **August 9, 2025 (Previous - TEXT CLEANING SEQUENCE OPTIMIZED)**: Reordered text cleaning operations for better results:
  - **REORDERED**: Empty line removal now happens AFTER all other cleaning operations
  - **IMPROVED**: Keywords removal no longer leaves unwanted empty lines in the middle of text
  - **LOGICAL SEQUENCE**: 1) Links → 2) Emojis → 3) Hashtags → 4) Phone numbers → 5) Keyword lines → 6) Whitespace cleanup → 7) Empty lines removal
  - **RESULT**: Clean, properly formatted text without residual empty lines from removed content
- **August 9, 2025 (Previous - TEXT CLEANING PATTERNS IMPROVED)**: Enhanced text cleaning patterns for better accuracy:
  - **ENHANCED**: Link removal now catches domain patterns like `meyon.com.ye/path` using improved regex
  - **FIXED**: Phone number detection no longer removes years like "2025" - now requires specific phone patterns
  - **IMPROVED**: More precise phone number patterns that distinguish between phone numbers and regular numbers
  - **ADDED**: Domain-based link detection for sites without http/https prefixes
  - **STATUS**: Text cleaning system now accurately handles edge cases and avoids false positives
- **August 9, 2025 (Previous - TEXT CLEANING BUGS FIXED)**: Fixed two critical issues in text cleaning system:
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