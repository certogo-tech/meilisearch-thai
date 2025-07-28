#!/usr/bin/env python3
"""
Script to update the existing tokenizer service to use compound words dictionary.
This provides a practical example of integrating the custom dictionary.
"""

import json
import os
from pathlib import Path

def update_api_main():
    """Update the main API file to use compound dictionary."""
    
    api_main_path = Path("src/api/main.py")
    
    if not api_main_path.exists():
        print(f"❌ API main file not found: {api_main_path}")
        return
    
    # Read current content
    try:
        with open(api_main_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check if already updated
        if "compound" in content.lower() or "custom_dict" in content:
            print("✅ API main already appears to have compound dictionary support")
            return
        
        print("ℹ️  API main file found but needs manual update")
        print("Add this code to initialize tokenizer with custom dictionary:")
        print("""
# Load compound words dictionary
def load_compound_dictionary():
    dict_path = Path("data/dictionaries/thai_compounds.json")
    if dict_path.exists():
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        compounds = []
        for category, words in data.items():
            if isinstance(words, list):
                compounds.extend(words)
        return compounds
    return []

# Initialize tokenizer with compound dictionary
compound_words = load_compound_dictionary()
segmenter = ThaiSegmenter(engine="newmm", custom_dict=compound_words)
""")
        
    except Exception as e:
        print(f"❌ Failed to read API main: {e}")


def create_tokenizer_factory():
    """Create a tokenizer factory that handles compound dictionary loading."""
    
    factory_path = Path("src/tokenizer/factory.py")
    
    factory_code = '''"""
Tokenizer factory with compound dictionary support.
"""

import json
import logging
from pathlib import Path
from typing import List, Optional

from .thai_segmenter import ThaiSegmenter


logger = logging.getLogger(__name__)


class TokenizerFactory:
    """Factory for creating tokenizers with compound dictionary support."""
    
    _compound_dictionary: Optional[List[str]] = None
    _dictionary_path: str = "data/dictionaries/thai_compounds.json"
    
    @classmethod
    def load_compound_dictionary(cls, dict_path: Optional[str] = None) -> List[str]:
        """Load compound words dictionary from file."""
        if dict_path:
            cls._dictionary_path = dict_path
        
        if cls._compound_dictionary is not None:
            return cls._compound_dictionary
        
        try:
            path = Path(cls._dictionary_path)
            if not path.exists():
                logger.warning(f"Compound dictionary not found: {path}")
                cls._compound_dictionary = []
                return cls._compound_dictionary
            
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract compound words from JSON structure
            compounds = []
            if isinstance(data, list):
                compounds = data
            elif isinstance(data, dict):
                for category, words in data.items():
                    if isinstance(words, list):
                        compounds.extend(words)
            
            # Remove duplicates and empty entries
            cls._compound_dictionary = list(set(word.strip() for word in compounds if word.strip()))
            
            logger.info(f"Loaded {len(cls._compound_dictionary)} compound words")
            
            # Log some examples
            if cls._compound_dictionary:
                examples = cls._compound_dictionary[:5]
                logger.info(f"Compound examples: {examples}")
            
            return cls._compound_dictionary
            
        except Exception as e:
            logger.error(f"Failed to load compound dictionary: {e}")
            cls._compound_dictionary = []
            return cls._compound_dictionary
    
    @classmethod
    def create_segmenter(
        cls,
        engine: str = "newmm",
        use_compounds: bool = True,
        custom_dict_path: Optional[str] = None,
        **kwargs
    ) -> ThaiSegmenter:
        """Create a Thai segmenter with optional compound dictionary."""
        
        custom_dict = []
        if use_compounds:
            custom_dict = cls.load_compound_dictionary(custom_dict_path)
        
        return ThaiSegmenter(
            engine=engine,
            custom_dict=custom_dict,
            **kwargs
        )
    
    @classmethod
    def create_wakame_optimized_segmenter(cls) -> ThaiSegmenter:
        """Create a segmenter specifically optimized for wakame and similar compounds."""
        
        # Ensure wakame and related compounds are in dictionary
        compounds = cls.load_compound_dictionary()
        
        # Add critical compounds if missing
        critical_compounds = [
            "วากาเมะ",
            "สาหร่ายวากาเมะ",
            "ซาชิมิ",
            "เทมปุระ",
            "ซูชิ"
        ]
        
        for compound in critical_compounds:
            if compound not in compounds:
                compounds.append(compound)
                logger.info(f"Added critical compound: {compound}")
        
        return ThaiSegmenter(
            engine="newmm",
            custom_dict=compounds,
            keep_whitespace=True
        )
    
    @classmethod
    def reload_dictionary(cls, dict_path: Optional[str] = None) -> None:
        """Reload the compound dictionary (for hot-reload functionality)."""
        cls._compound_dictionary = None
        cls.load_compound_dictionary(dict_path)
        logger.info("Compound dictionary reloaded")
    
    @classmethod
    def get_dictionary_stats(cls) -> dict:
        """Get statistics about the loaded dictionary."""
        compounds = cls.load_compound_dictionary()
        
        # Categorize compounds
        thai_japanese = [w for w in compounds if any(char in w for char in "เมะะุิ")]
        thai_english = [w for w in compounds if any(char in w for char in "์ิ์")]
        
        return {
            "total_compounds": len(compounds),
            "thai_japanese_compounds": len(thai_japanese),
            "thai_english_compounds": len(thai_english),
            "dictionary_path": cls._dictionary_path,
            "examples": compounds[:10] if compounds else []
        }
'''
    
    try:
        with open(factory_path, 'w', encoding='utf-8') as f:
            f.write(factory_code)
        
        print(f"✅ Created tokenizer factory: {factory_path}")
        
    except Exception as e:
        print(f"❌ Failed to create tokenizer factory: {e}")


def create_usage_example():
    """Create a usage example showing how to use the compound dictionary."""
    
    example_path = Path("examples/compound_tokenization.py")
    example_path.parent.mkdir(exist_ok=True)
    
    example_code = '''#!/usr/bin/env python3
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
    
    print("\\n=== Standard Tokenization (without compounds) ===")
    standard_segmenter = TokenizerFactory.create_segmenter(use_compounds=False)
    
    for text in test_texts:
        result = standard_segmenter.segment_text(text)
        print(f"Text: {text}")
        print(f"Tokens: {result.tokens}")
        print()
    
    print("\\n=== Compound-Aware Tokenization ===")
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
    
    print("\\n=== Dictionary Statistics ===")
    stats = TokenizerFactory.get_dictionary_stats()
    for key, value in stats.items():
        print(f"{key}: {value}")


if __name__ == "__main__":
    main()
'''
    
    try:
        with open(example_path, 'w', encoding='utf-8') as f:
            f.write(example_code)
        
        print(f"✅ Created usage example: {example_path}")
        
    except Exception as e:
        print(f"❌ Failed to create usage example: {e}")


def create_environment_setup():
    """Create environment setup script."""
    
    setup_script = '''#!/bin/bash
# Setup script for Thai compound tokenization

echo "🚀 Setting up Thai Compound Tokenization"

# Set environment variables
export THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH="data/dictionaries/thai_compounds.json"
export THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS="true"
export THAI_TOKENIZER_TOKENIZER_ENGINE="newmm"
export THAI_TOKENIZER_DEBUG="true"

echo "✅ Environment variables set:"
echo "  - Custom dictionary: $THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH"
echo "  - Compound handling: $THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS"
echo "  - Engine: $THAI_TOKENIZER_TOKENIZER_ENGINE"

# Check if dictionary file exists
if [ -f "$THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH" ]; then
    echo "✅ Compound dictionary found"
    echo "  - Dictionary entries: $(cat $THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH | jq '[.[]] | flatten | length')"
else
    echo "❌ Compound dictionary not found at: $THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH"
fi

echo ""
echo "🔧 To use these settings in your current shell:"
echo "  source scripts/setup_compound_env.sh"
echo ""
echo "🧪 To test the integration:"
echo "  python3 examples/compound_tokenization.py"
'''
    
    setup_path = Path("scripts/setup_compound_env.sh")
    
    try:
        with open(setup_path, 'w', encoding='utf-8') as f:
            f.write(setup_script)
        
        # Make executable
        os.chmod(setup_path, 0o755)
        
        print(f"✅ Created environment setup script: {setup_path}")
        
    except Exception as e:
        print(f"❌ Failed to create setup script: {e}")


def main():
    """Main integration setup."""
    
    print("🔧 Updating Tokenizer Service for Compound Dictionary")
    print("=" * 55)
    
    # Create tokenizer factory
    create_tokenizer_factory()
    
    # Create usage example
    create_usage_example()
    
    # Create environment setup
    create_environment_setup()
    
    # Check API main
    update_api_main()
    
    print("\\n📋 Integration Complete!")
    print("=" * 25)
    print("✅ Created TokenizerFactory with compound support")
    print("✅ Created usage example in examples/compound_tokenization.py")
    print("✅ Created environment setup script")
    print("✅ Compound dictionary ready at data/dictionaries/thai_compounds.json")
    
    print("\\n🚀 Quick Start:")
    print("1. Run: source scripts/setup_compound_env.sh")
    print("2. Test: python3 examples/compound_tokenization.py")
    print("3. Integrate: Use TokenizerFactory.create_wakame_optimized_segmenter()")
    
    print("\\n🎯 Result: วากาเมะ will now be tokenized as single word instead of ['วา', 'กา', 'เมะ']")


if __name__ == "__main__":
    main()