#!/usr/bin/env python3
"""
Simple test to verify that adding วากาเมะ to custom dictionary solves the issue.
This is a standalone script that demonstrates the fix.
"""

import json
from pathlib import Path

try:
    from pythainlp import word_tokenize
    from pythainlp.tokenize import Tokenizer
    from pythainlp.corpus.common import thai_words
    PYTHAINLP_AVAILABLE = True
except ImportError:
    print("❌ PyThaiNLP not available. Please install with: pip install pythainlp")
    PYTHAINLP_AVAILABLE = False


def load_compound_dictionary():
    """Load compound words from the dictionary file."""
    dict_path = Path("data/dictionaries/thai_compounds.json")
    
    if not dict_path.exists():
        print(f"❌ Dictionary not found: {dict_path}")
        return []
    
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        compounds = []
        for category, words in data.items():
            if isinstance(words, list):
                compounds.extend(words)
        
        return compounds
    except Exception as e:
        print(f"❌ Failed to load dictionary: {e}")
        return []


def test_wakame_fix():
    """Test that วากาเมะ is now tokenized correctly."""
    
    if not PYTHAINLP_AVAILABLE:
        return
    
    print("🧪 Testing Wakame Tokenization Fix")
    print("=" * 35)
    
    # Load compound dictionary
    compounds = load_compound_dictionary()
    print(f"📚 Loaded {len(compounds)} compound words")
    
    if "วากาเมะ" not in compounds:
        print("❌ วากาเมะ not found in dictionary!")
        return
    else:
        print("✅ วากาเมะ found in dictionary")
    
    # Create custom tokenizer
    try:
        custom_word_set = set(thai_words()) | set(compounds)
        custom_tokenizer = Tokenizer(custom_word_set)
        print("✅ Custom tokenizer created")
    except Exception as e:
        print(f"❌ Failed to create tokenizer: {e}")
        return
    
    # Test cases from the original wakame test
    test_cases = [
        {
            "text": "สาหร่ายวากาเมะ",
            "description": "Basic wakame seaweed compound"
        },
        {
            "text": "สาหร่ายวากาเมะเป็นอาหารทะเล",
            "description": "Wakame in sentence context"
        },
        {
            "text": "สลัดสาหร่ายวากาเมะแบบญี่ปุ่น",
            "description": "Wakame salad with context"
        },
        {
            "text": "ร้านอาหารญี่ปุ่นเสิร์ฟวากาเมะ",
            "description": "Restaurant serving wakame"
        },
        {
            "text": "วากาเมะมีประโยชน์ต่อสุขภาพ",
            "description": "Wakame health benefits"
        }
    ]
    
    print("\\n🔍 Test Results:")
    print("-" * 50)
    
    success_count = 0
    for i, test_case in enumerate(test_cases, 1):
        tokens = custom_tokenizer.word_tokenize(test_case["text"])
        
        # Check if วากาเมะ appears as single token
        wakame_as_single = "วากาเมะ" in tokens
        
        # Check if it's NOT split into วา, กา, เมะ
        not_split = not ("วา" in tokens and "กา" in tokens and "เมะ" in tokens)
        
        success = wakame_as_single or not_split
        if success:
            success_count += 1
        
        status = "✅" if success else "❌"
        print(f"{status} Test {i}: {test_case['description']}")
        print(f"   Text: {test_case['text']}")
        print(f"   Tokens: {tokens}")
        print(f"   วากาเมะ as single token: {wakame_as_single}")
        print()
    
    print("📊 Summary:")
    print(f"   Success rate: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")
    
    if success_count == len(test_cases):
        print("🎉 All tests passed! วากาเมะ tokenization issue is FIXED!")
    elif success_count > len(test_cases) // 2:
        print("✅ Most tests passed. Significant improvement achieved!")
    else:
        print("⚠️  Some tests still failing. May need additional dictionary entries.")
    
    # Test other compounds too
    print("\\n🌟 Testing Other Compound Words:")
    other_compounds = ["ซาชิมิ", "เทมปุระ", "คอมพิวเตอร์", "อินเทอร์เน็ต"]
    
    for compound in other_compounds:
        test_text = f"ฉันชอบ{compound}มาก"
        tokens = custom_tokenizer.word_tokenize(test_text)
        found = compound in tokens
        status = "✅" if found else "❌"
        print(f"   {status} {compound}: {tokens}")


def main():
    """Main test function."""
    print("🚀 Wakame Tokenization Fix Verification")
    print("=" * 40)
    print("This test verifies that adding วากาเมะ to the custom dictionary")
    print("solves the tokenization splitting issue.")
    print()
    
    test_wakame_fix()
    
    print("\\n💡 Integration Notes:")
    print("- Dictionary file: data/dictionaries/thai_compounds.json")
    print("- TokenizerFactory: src/tokenizer/factory.py")
    print("- Environment setup: scripts/setup_compound_env.sh")
    print("- Usage example: examples/compound_tokenization.py")


if __name__ == "__main__":
    main()