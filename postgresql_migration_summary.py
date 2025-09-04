#!/usr/bin/env python3
"""
PostgreSQL Migration Summary and Validation Script
This script validates that all SQLite task settings functions have been migrated to PostgreSQL
"""

import os
import re
import sys

def extract_functions_from_file(file_path):
    """Extract function definitions from a Python file"""
    functions = []
    if not os.path.exists(file_path):
        return functions
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Find all function definitions
        pattern = r'def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\('
        matches = re.findall(pattern, content)
        functions = list(set(matches))  # Remove duplicates
        
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
    
    return sorted(functions)

def categorize_functions(functions):
    """Categorize functions by their purpose"""
    categories = {
        'task_settings': [],
        'text_processing': [],
        'inline_buttons': [],
        'headers_footers': [],
        'audio_settings': [],
        'advanced_filters': [],
        'user_management': [],
        'core_database': [],
        'other': []
    }
    
    for func in functions:
        if any(keyword in func.lower() for keyword in ['text_cleaning', 'text_formatting', 'keyword']):
            categories['text_processing'].append(func)
        elif any(keyword in func.lower() for keyword in ['inline_button', 'button']):
            categories['inline_buttons'].append(func)
        elif any(keyword in func.lower() for keyword in ['header', 'footer']):
            categories['headers_footers'].append(func)
        elif any(keyword in func.lower() for keyword in ['audio', 'metadata', 'template']):
            categories['audio_settings'].append(func)
        elif any(keyword in func.lower() for keyword in ['filter', 'duplicate', 'rate_limit', 'character_limit', 'working_hours']):
            categories['advanced_filters'].append(func)
        elif any(keyword in func.lower() for keyword in ['user', 'session', 'auth']):
            categories['user_management'].append(func)
        elif any(keyword in func.lower() for keyword in ['task', 'setting']):
            categories['task_settings'].append(func)
        elif any(keyword in func.lower() for keyword in ['get_connection', 'init_database', 'create_table']):
            categories['core_database'].append(func)
        else:
            categories['other'].append(func)
    
    return categories

def main():
    print("🔄 PostgreSQL Migration Summary and Validation")
    print("=" * 60)
    
    # File paths
    sqlite_file = '/workspace/database/database_sqlite.py'
    postgresql_file = '/workspace/database/database_postgresql.py'
    main_db_file = '/workspace/database/database.py'
    
    print("\n📂 Analyzing database files...")
    
    # Extract functions from each file
    sqlite_functions = extract_functions_from_file(sqlite_file)
    postgresql_functions = extract_functions_from_file(postgresql_file)
    main_db_functions = extract_functions_from_file(main_db_file)
    
    print(f"SQLite functions found: {len(sqlite_functions)}")
    print(f"PostgreSQL functions found: {len(postgresql_functions)}")
    print(f"Main database functions found: {len(main_db_functions)}")
    
    # Combine all SQLite-based functions that need migration
    all_sqlite_functions = set(sqlite_functions + main_db_functions)
    
    print(f"\nTotal unique SQLite functions: {len(all_sqlite_functions)}")
    
    # Categorize functions
    sqlite_categories = categorize_functions(all_sqlite_functions)
    postgresql_categories = categorize_functions(postgresql_functions)
    
    print("\n📊 Migration Coverage Analysis")
    print("-" * 40)
    
    total_coverage = 0
    total_functions = 0
    
    for category, sqlite_funcs in sqlite_categories.items():
        if not sqlite_funcs:
            continue
            
        postgresql_funcs = postgresql_categories.get(category, [])
        coverage = len(set(sqlite_funcs) & set(postgresql_funcs))
        total_coverage += coverage
        total_functions += len(sqlite_funcs)
        
        percentage = (coverage / len(sqlite_funcs)) * 100 if sqlite_funcs else 0
        
        print(f"\n{category.upper().replace('_', ' ')}:")
        print(f"  SQLite functions: {len(sqlite_funcs)}")
        print(f"  PostgreSQL equivalents: {coverage}")
        print(f"  Coverage: {percentage:.1f}%")
        
        # Show missing functions
        missing = set(sqlite_funcs) - set(postgresql_funcs)
        if missing:
            print(f"  Missing: {', '.join(sorted(missing))}")
    
    overall_percentage = (total_coverage / total_functions) * 100 if total_functions else 0
    print(f"\n🎯 OVERALL MIGRATION COVERAGE: {overall_percentage:.1f}%")
    print(f"   ({total_coverage}/{total_functions} functions migrated)")
    
    # Key task settings functions check
    print("\n🔍 Key Task Settings Functions Verification:")
    print("-" * 45)
    
    key_functions = [
        'get_message_settings',
        'update_header_settings', 
        'update_footer_settings',
        'get_inline_buttons',
        'add_inline_button',
        'update_inline_button',
        'delete_inline_button',
        'clear_inline_buttons',
        'get_text_cleaning_settings',
        'update_text_cleaning_setting',
        'get_text_cleaning_keywords',
        'add_text_cleaning_keywords',
        'remove_text_cleaning_keyword',
        'clear_text_cleaning_keywords',
        'get_text_formatting_settings',
        'update_text_formatting_settings',
        'toggle_text_formatting',
        'get_audio_metadata_settings',
        'update_audio_metadata_setting',
        'get_character_limit_settings',
        'update_character_limit_settings',
        'get_rate_limit_settings',
        'get_working_hours',
        'get_duplicate_settings'
    ]
    
    for func in key_functions:
        status = "✅" if func in postgresql_functions else "❌"
        print(f"  {status} {func}")
    
    # Migration completeness summary
    print("\n📋 MIGRATION SUMMARY:")
    print("=" * 30)
    
    if overall_percentage >= 95:
        print("🎉 EXCELLENT: Migration is nearly complete!")
    elif overall_percentage >= 80:
        print("✅ GOOD: Most functions have been migrated")
    elif overall_percentage >= 60:
        print("⚠️ PARTIAL: Significant work remains")
    else:
        print("❌ INCOMPLETE: Major migration work needed")
    
    print(f"\n📈 Migration Progress: {overall_percentage:.1f}% Complete")
    print(f"🔧 Functions Migrated: {total_coverage}/{total_functions}")
    
    # New PostgreSQL-only functions
    postgresql_only = set(postgresql_functions) - all_sqlite_functions
    if postgresql_only:
        print(f"\n🆕 New PostgreSQL-only functions: {len(postgresql_only)}")
        for func in sorted(postgresql_only):
            print(f"  + {func}")
    
    print("\n" + "=" * 60)
    print("✅ Migration analysis complete!")

if __name__ == "__main__":
    main()