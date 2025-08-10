# Overview

This project is a Telegram message forwarding automation system. It leverages Telethon to provide a comprehensive solution for managing and automating message forwarding between Telegram chats. The system comprises a Telegram bot for task management via an Arabic-language interface and a userbot service for the actual message forwarding. Its core capabilities include advanced message filtering, content modification, and flexible forwarding controls, aiming to provide a robust and user-friendly platform for automating Telegram communication.

# User Preferences

Preferred communication style: Simple, everyday language.

# Recent Changes

- **August 10, 2025 (CRITICAL BUG FIX - DATABASE SETTINGS UPDATE ERROR RESOLVED)**: Fixed error messages appearing when updating advanced feature settings:
  - **ROOT CAUSE IDENTIFIED**: Database update functions returned False when no existing records found, causing error messages after successful settings creation
  - **ISSUE SYMPTOMS**: Users saw both success and error messages like "✅ تم تحديث فاصل الإرسال إلى: 10 ثانية" followed by "❌ حدث خطأ في تحديث فاصل الإرسال"
  - **ARCHITECTURAL FIX**: Modified update functions to create default records before attempting updates using INSERT OR IGNORE pattern
  - **FUNCTIONS UPDATED**: Fixed update_rate_limit_settings, update_forwarding_delay_settings, update_sending_interval_settings, update_character_limit_settings
  - **DATABASE LOGIC**: Update functions now check for existing records and create defaults if missing, then always return True on successful update
  - **USER EXPERIENCE**: Settings updates now show only success messages without confusing error messages
  - **TESTING CONFIRMED**: All advanced feature settings (message period, message count, forwarding delay, sending interval) update without errors
  - **STATUS**: Database update error messages eliminated - clean user experience restored

- **August 10, 2025 (CRITICAL BUG FIX - RATE LIMITING LOGIC COMPLETELY FIXED)**: Fixed rate limiting to work per source message instead of per target:
  - **ROOT CAUSE IDENTIFIED**: Rate limits were being checked separately for each target destination, causing first target to pass and subsequent targets to be blocked
  - **ARCHITECTURE RESTRUCTURE**: Moved rate limit checking to occur once per source message before target processing loop
  - **FIXED FLOW**: Advanced features (character limits, rate limits) now checked once per message using first matching task settings
  - **PROPER BEHAVIOR**: One source message now forwards to ALL targets if within rate limit, then blocks subsequent messages until time window expires
  - **TIMING FIXES**: 
    - Forwarding delay applied once per source message (before all targets)
    - Sending interval applied between targets (not per message)
  - **USER EXPERIENCE**: Rate limit of "1 message per 10 seconds" now correctly allows 1 source message to reach all destinations, then blocks for 10 seconds
  - **LOGGING ENHANCED**: Clear Arabic logging shows when rate limits block messages for all targets vs individual targets
  - **STATUS**: Rate limiting now works as intended - per source message, not per destination

- **August 10, 2025 (CRITICAL BUG FIX - CHARACTER LIMITS LOGIC COMPLETELY FIXED)**: Fixed character limit checking to use original message text instead of formatted HTML:
  - **ROOT CAUSE IDENTIFIED**: Character limits were checking HTML-formatted text (with hyperlinks) instead of original message content
  - **EXAMPLE**: Message "مرحبا" (5 chars) was blocked because formatted version `<a href="...">مرحبا</a>` (42 chars) exceeded 10-char limit
  - **ARCHITECTURE FIX**: Moved character limit checking to occur before text formatting is applied
  - **PROPER SEQUENCE**: Text cleaning → Character limits check → Text formatting → Send
  - **ACCURATE COUNTING**: Now correctly counts only the actual message characters, not HTML markup
  - **USER EXPERIENCE**: Messages within configured character range (3-10) are now properly allowed through
  - **STATUS**: Character limits now work as intended with accurate character counting on original message text

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

- **August 9, 2025 (MAJOR IMPLEMENTATION - ADVANCED FEATURES PIPELINE INTEGRATION)**: Implemented missing advanced features in message forwarding pipeline:
  - **ROOT CAUSE IDENTIFIED**: Advanced features were configurable through bot interface but not actually applied during message forwarding in userbot service
  - **IMPLEMENTED FEATURES**: Added complete pipeline integration for all 4 advanced features:
    1. **Character Limits**: Min/max character validation before message sending with proper logging
    2. **Rate Limiting**: Message count tracking with time-based limits and database integration
    3. **Forwarding Delay**: Configurable delay before each message send with async sleep
    4. **Sending Interval**: Configurable delay between messages to different targets
  - **PIPELINE INTEGRATION**: Added `_check_advanced_features()` method called before every message send
  - **DATABASE CONNECTIVITY**: Connected to existing database methods with correct field names (min_chars, max_chars, message_count, time_period_seconds)
  - **LOGGING ENHANCEMENTS**: Added comprehensive Arabic logging for all advanced feature actions
  - **ASYNC IMPLEMENTATION**: All delays and intervals use proper asyncio.sleep() for non-blocking operation
  - **ERROR HANDLING**: Graceful fallback when feature checks fail to prevent message blocking
  - **INTEGRATION POINTS**: Advanced features now active at both forwarding delay (before send) and sending interval (between targets)
  - **STATUS**: Advanced features now fully functional in actual message forwarding - character limits block/allow messages, rate limits prevent spam, delays control timing

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