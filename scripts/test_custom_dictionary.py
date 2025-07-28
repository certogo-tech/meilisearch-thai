#!/usr/bin/env python3
"""
Quick test script to validate custom dictionary approach for compound words.
This demonstrates adding "วากาเมะ" to the custom dictionary to solve the immediate issue.
"""

import json
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Simple test using PyThaiNLP directly to avoid import issues
try:
    from pythainlp import word_tokenize
    from pythainlp.tokenize import Tokenizer
    from pythainlp.corpus.common import thai_words
    PYTHAINLP_AVAILABLE = True
except ImportError:
    PYTHAINLP_AVAILABLE = False
    print("PyThaiNLP not available. Please install with: pip install pythainlp")


def load_compound_dictionary(dict_path: str) -> list:
    """Load compound words from JSON dictionary file."""
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Combine all compound word lists
        compounds = []
        for category, words in data.items():
            if isinstance(words, list):
                compounds.extend(words)
        
        print(f"Loaded {len(compounds)} compound words from dictionary")
        return compounds
    
    except Exception as e:
        print(f"Failed to load dictionary: {e}")
        return []


def test_wakame_tokenization():
    """Test wakame tokenization with and without custom dictionary."""
    
    if not PYTHAINLP_AVAILABLE:
        print("Cannot run test without PyThaiNLP")
        return
    
    test_texts = [
        "สาหร่ายวากาเมะ",
        "สาหร่ายวากาเมะเป็นอาหารทะเล",
        "สลัดสาหร่ายวากาเมะแบบญี่ปุ่น",
        "ร้านอาหารญี่ปุ่นเสิร์ฟวากาเมะ",
        "วากาเมะมีประโยชน์ต่อสุขภาพ"
    ]
    
    print("=== Testing WITHOUT Custom Dictionary ===")
    
    for text in test_texts:
        tokens = word_tokenize(text, engine="newmm")
        print(f"Text: {text}")
        print(f"Tokens: {tokens}")
        print(f"Contains 'วากาเมะ' as single token: {'วากาเมะ' in tokens}")
        print()
    
    print("=== Testing WITH Custom Dictionary ===")
    
    # Load custom dictionary
    dict_path = Path(__file__).parent.parent / "data" / "dictionaries" / "thai_compounds.json"
    custom_words = load_compound_dictionary(str(dict_path))
    
    # Create custom tokenizer with compound words
    try:
        custom_word_set = set(thai_words()) | set(custom_words)
        custom_tokenizer = Tokenizer(custom_word_set)
        
        for text in test_texts:
            tokens = custom_tokenizer.word_tokenize(text)
            print(f"Text: {text}")
            print(f"Tokens: {tokens}")
            print(f"Contains 'วากาเมะ' as single token: {'วากาเมะ' in tokens}")
            print()
            
    except Exception as e:
        print(f"Failed to create custom tokenizer: {e}")
        return
    
    print("=== Comparison Summary ===")
    print("Expected: 'วากาเมะ' should appear as a single token, not split into ['วา', 'กา', 'เมะ']")


def test_other_compounds():
    """Test other compound words from the dictionary."""
    
    if not PYTHAINLP_AVAILABLE:
        print("Cannot run test without PyThaiNLP")
        return
    
    dict_path = Path(__file__).parent.parent / "data" / "dictionaries" / "thai_compounds.json"
    custom_words = load_compound_dictionary(str(dict_path))
    
    try:
        custom_word_set = set(thai_words()) | set(custom_words)
        custom_tokenizer = Tokenizer(custom_word_set)
        
        test_compounds = [
            "ซาชิมิ",
            "เทมปุระ", 
            "คอมพิวเตอร์",
            "อินเทอร์เน็ต",
            "โตโยต้า"
        ]
        
        print("=== Testing Other Compound Words ===")
        for compound in test_compounds:
            text = f"ฉันชอบ{compound}มาก"
            tokens = custom_tokenizer.word_tokenize(text)
            print(f"Text: {text}")
            print(f"Tokens: {tokens}")
            print(f"Contains '{compound}' as single token: {compound in tokens}")
            print()
            
    except Exception as e:
        print(f"Failed to test compounds: {e}")


if __name__ == "__main__":
    print("Testing Custom Dictionary Approach for Thai Compound Words")
    print("=" * 60)
    
    test_wakame_tokenization()
    test_other_compounds()
    
    print("\nConclusion:")
    print("Adding compound words to the custom dictionary should preserve them as single tokens")
    print("during tokenization, solving the immediate wakame splitting issue.")