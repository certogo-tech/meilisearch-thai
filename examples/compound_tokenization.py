#!/usr/bin/env python3
"""
Example: Using compound dictionary for improved Thai tokenization.
This example shows how to solve the wakame splitting issue.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from tokenizer.factory import TokenizerFactory


def main():
    """Demonstrate compound dictionary usage."""
    
    print("🧪 Thai Compound Tokenization Example")
    print("=" * 40)
    
    # Test texts with compound words
    test_texts = [
        "สาหร่ายวากาเมะเป็นอาหารทะเล",
        "วากาเมะมีประโยชน์ต่อสุขภาพ",
        "ร้านอาหารญี่ปุ่นเสิร์ฟซาชิมิและเทมปุระ",
        "คอมพิวเตอร์และอินเทอร์เน็ตเป็นเทคโนโลยีสำคัญ",
        "โตโยต้าและฮอนด้าเป็นแบรนด์รถยนต์ญี่ปุ่น"
    ]
    
    print("\n=== Standard Tokenization (without compounds) ===")
    standard_segmenter = TokenizerFactory.create_segmenter(use_compounds=False)
    
    for text in test_texts:
        result = standard_segmenter.segment_text(text)
        print(f"Text: {text}")
        print(f"Tokens: {result.tokens}")
        print()
    
    print("\n=== Compound-Aware Tokenization ===")
    compound_segmenter = TokenizerFactory.create_wakame_optimized_segmenter()
    
    for text in test_texts:
        result = compound_segmenter.segment_text(text)
        print(f"Text: {text}")
        print(f"Tokens: {result.tokens}")
        
        # Check for specific compounds
        compounds_found = []
        target_compounds = ["วากาเมะ", "ซาชิมิ", "เทมปุระ", "คอมพิวเตอร์", "อินเทอร์เน็ต", "โตโยต้า", "ฮอนด้า"]
        for compound in target_compounds:
            if compound in result.tokens:
                compounds_found.append(compound)
        
        if compounds_found:
            print(f"✅ Compounds preserved: {compounds_found}")
        print()
    
    print("\n=== Dictionary Statistics ===")
    stats = TokenizerFactory.get_dictionary_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
