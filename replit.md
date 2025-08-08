# Overview

This is a Telegram message forwarding automation system built entirely with Telethon, featuring a Telegram bot interface for managing forwarding tasks and a userbot service for automatic message forwarding between Telegram chats. The system provides a complete Arabic-language bot interface with phone number authentication and multi-threaded service architecture. **Status: Fully operational and tested (August 8, 2025).**

## Recent Changes
- **August 8, 2025 (Latest Update)**: Added comprehensive message formatting system:
  - **NEW FEATURE**: Header/Footer system for adding text before/after messages
  - **IMPLEMENTED**: Inline buttons feature supporting multiple buttons per row across multiple rows  
  - **ADDED**: Auto-conversion to copy mode when any formatting is applied
  - **CREATED**: Complete UI management for headers, footers, and inline buttons
  - **INTEGRATED**: Full UserBot support for all new formatting features
  - **ENHANCED**: Message processing with header, footer, and button application
  - **UI COMPLETE**: Arabic interface with enable/disable toggles and content editing
  - **DATABASE**: Added task_headers, task_footers, task_inline_buttons tables
  - **VERIFIED**: All previous functionality (text replacements, word filters) remains operational

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