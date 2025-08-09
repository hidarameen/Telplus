#!/usr/bin/env python3
"""
اختبار أنواع parse_mode المختلفة في Telethon
"""

def test_parse_modes():
    """اختبار أنواع parse_mode المختلفة"""
    
    test_text = "نص اقتباس"
    
    print("🧪 اختبار أنواع parse_mode لتنسيق الاقتباس")
    print("="*50)
    
    # اختبار تنسيقات مختلفة
    formats = {
        "markdown": f"> {test_text}",
        "html": f"<blockquote>{test_text}</blockquote>",
        "markdown_v2": f">{test_text}",
        "plain": f"> {test_text}"
    }
    
    for format_name, formatted_text in formats.items():
        print(f"\n📝 {format_name.upper()}:")
        print(f"   النص: '{formatted_text}'")
        
        if format_name == "markdown":
            print("   parse_mode='md'")
        elif format_name == "html":
            print("   parse_mode='html'")
        elif format_name == "markdown_v2":
            print("   parse_mode='MarkdownV2'")
        else:
            print("   parse_mode=None")
    
    print("\n" + "="*50)
    print("💡 ملاحظات:")
    print("- markdown (md): يستخدم > في بداية السطر")
    print("- HTML: يستخدم <blockquote> tags")
    print("- MarkdownV2: تنسيق markdown محدث")
    print("- يجب أن يعمل واحد منها على الأقل!")

if __name__ == "__main__":
    test_parse_modes()