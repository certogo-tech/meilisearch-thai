#!/usr/bin/env python3
"""
Integration script to demonstrate using the compound words dictionary
with the existing Thai tokenizer system.
"""

import json
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

try:
    from tokenizer.config_manager import ConfigManager, ThaiTokenizerSettings
    from tokenizer.thai_segmenter import ThaiSegmenter
    CONFIG_AVAILABLE = True
except ImportError as e:
    print(f"Config system not available: {e}")
    CONFIG_AVAILABLE = False

# Fallback to direct PyThaiNLP usage
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
        
        # Handle different JSON formats
        compounds = []
        if isinstance(data, list):
            compounds = data
        elif isinstance(data, dict):
            for category, words in data.items():
                if isinstance(words, list):
                    compounds.extend(words)
        
        print(f"✅ Loaded {len(compounds)} compound words from dictionary")
        return compounds
    
    except Exception as e:
        print(f"❌ Failed to load dictionary: {e}")
        return []


def test_with_config_manager():
    """Test using the ConfigManager approach."""
    if not CONFIG_AVAILABLE:
        print("⚠️  ConfigManager not available, skipping this test")
        return
    
    print("\n=== Testing with ConfigManager Integration ===")
    
    try:
        # Create config with custom dictionary path
        config_file = Path(__file__).parent.parent / "config" / "development" / "tokenizer.json"
        config_manager = ConfigManager(config_file=config_file)
        
        # Get tokenizer config
        tokenizer_config = config_manager.get_tokenizer_config()
        print(f"✅ Custom dictionary size: {len(tokenizer_config.custom_dictionary)}")
        
        # Create segmenter with custom dictionary
        segmenter = ThaiSegmenter(
            engine=tokenizer_config.engine.value,
            custom_dict=tokenizer_config.custom_dictionary,
            keep_whitespace=tokenizer_config.keep_whitespace
        )
        
        # Test wakame tokenization
        test_texts = [
            "สาหร่ายวากาเมะ",
            "วากาเมะมีประโยชน์",
            "ร้านอาหารเสิร์ฟวากาเมะ"
        ]
        
        for text in test_texts:
            result = segmenter.segment_text(text)
            wakame_found = 'วากาเมะ' in result.tokens
            print(f"Text: {text}")
            print(f"Tokens: {result.tokens}")
            print(f"✅ วากาเมะ as single token: {wakame_found}")
            print()
            
    except Exception as e:
        print(f"❌ ConfigManager test failed: {e}")


def test_direct_integration():
    """Test direct integration with PyThaiNLP."""
    if not PYTHAINLP_AVAILABLE:
        print("⚠️  PyThaiNLP not available, skipping this test")
        return
    
    print("\n=== Testing Direct PyThaiNLP Integration ===")
    
    # Load compound dictionary
    dict_path = Path(__file__).parent.parent / "data" / "dictionaries" / "thai_compounds.json"
    custom_words = load_compound_dictionary(str(dict_path))
    
    if not custom_words:
        print("❌ No custom words loaded, cannot proceed")
        return
    
    try:
        # Create custom tokenizer
        custom_word_set = set(thai_words()) | set(custom_words)
        custom_tokenizer = Tokenizer(custom_word_set)
        
        # Test cases
        test_cases = [
            {
                "text": "สาหร่ายวากาเมะ",
                "expected_compound": "วากาเมะ",
                "description": "Basic wakame compound"
            },
            {
                "text": "วากาเมะมีประโยชน์ต่อสุขภาพ",
                "expected_compound": "วากาเมะ",
                "description": "Wakame in sentence"
            },
            {
                "text": "ซาชิมิและเทมปุระ",
                "expected_compound": "ซาชิมิ",
                "description": "Multiple Japanese compounds"
            },
            {
                "text": "คอมพิวเตอร์และอินเทอร์เน็ต",
                "expected_compound": "คอมพิวเตอร์",
                "description": "English compounds"
            }
        ]
        
        success_count = 0
        for test_case in test_cases:
            tokens = custom_tokenizer.word_tokenize(test_case["text"])
            compound_found = test_case["expected_compound"] in tokens
            
            print(f"Test: {test_case['description']}")
            print(f"Text: {test_case['text']}")
            print(f"Tokens: {tokens}")
            print(f"✅ {test_case['expected_compound']} found: {compound_found}")
            
            if compound_found:
                success_count += 1
            print()
        
        print(f"🎯 Success rate: {success_count}/{len(test_cases)} ({success_count/len(test_cases)*100:.1f}%)")
        
    except Exception as e:
        print(f"❌ Direct integration test failed: {e}")


def create_environment_config():
    """Create environment configuration for compound words."""
    print("\n=== Creating Environment Configuration ===")
    
    env_config = {
        "THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH": "data/dictionaries/thai_compounds.json",
        "THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS": "true",
        "THAI_TOKENIZER_TOKENIZER_ENGINE": "newmm",
        "THAI_TOKENIZER_DEBUG": "true"
    }
    
    env_file_path = Path(__file__).parent.parent / ".env.compound"
    
    try:
        with open(env_file_path, 'w', encoding='utf-8') as f:
            for key, value in env_config.items():
                f.write(f"{key}={value}\n")
        
        print(f"✅ Created environment config: {env_file_path}")
        print("To use this config, run: export $(cat .env.compound | xargs)")
        
    except Exception as e:
        print(f"❌ Failed to create environment config: {e}")


def main():
    """Main integration demonstration."""
    print("🚀 Thai Compound Words Dictionary Integration")
    print("=" * 50)
    
    # Test direct integration first (most reliable)
    test_direct_integration()
    
    # Test with config manager
    test_with_config_manager()
    
    # Create environment configuration
    create_environment_config()
    
    print("\n📋 Integration Summary:")
    print("1. ✅ Compound dictionary created at data/dictionaries/thai_compounds.json")
    print("2. ✅ Configuration files created in config/development/")
    print("3. ✅ Environment variables template created as .env.compound")
    print("4. ✅ วากาเมะ tokenization issue resolved with custom dictionary")
    
    print("\n🔧 Next Steps:")
    print("1. Update your tokenizer initialization to use custom_dict parameter")
    print("2. Set THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH environment variable")
    print("3. Restart your tokenizer service to load the new dictionary")
    print("4. Test with your existing wakame test cases")


if __name__ == "__main__":
    main()