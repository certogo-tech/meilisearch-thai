#!/usr/bin/env python3
"""
Simple test script to verify config manager functionality.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))

from src.tokenizer.config_manager import (
    ConfigManager, 
    MeiliSearchConfig, 
    TokenizerConfig,
    ConfigurationError
)


def test_config_manager():
    """Test the configuration manager functionality."""
    print("Testing configuration manager...")
    
    # Initialize config manager
    config_manager = ConfigManager()
    
    try:
        # Test basic configuration retrieval
        print("\n1. Testing basic configuration...")
        config_dict = config_manager.to_dict()
        print(f"✓ Configuration retrieved with {len(config_dict)} keys")
        
        # Test MeiliSearch configuration update
        print("\n2. Testing MeiliSearch configuration update...")
        meilisearch_config = MeiliSearchConfig(
            host="http://localhost:7700",
            api_key="test_key",
            index_name="test_index"
        )
        config_manager.update_meilisearch_config(meilisearch_config)
        print("✓ MeiliSearch configuration updated")
        
        # Test tokenizer configuration update
        print("\n3. Testing tokenizer configuration update...")
        tokenizer_config = TokenizerConfig(
            engine="newmm",
            model_version="latest",
            custom_dictionary=["test_word1", "test_word2"],
            keep_whitespace=True,
            handle_compounds=True,
            fallback_engine="pythainlp"
        )
        config_manager.update_tokenizer_config(tokenizer_config)
        print("✓ Tokenizer configuration updated")
        
        # Test dictionary management
        print("\n4. Testing dictionary management...")
        
        # Add words
        test_words = ["คำทดสอบ1", "คำทดสอบ2", "คำทดสอบ3"]
        config_manager.add_custom_dictionary_words(test_words)
        print(f"✓ Added {len(test_words)} words to dictionary")
        
        # Get dictionary
        dictionary = config_manager._custom_dictionary
        print(f"✓ Dictionary now has {len(dictionary)} words")
        
        # Remove words
        config_manager.remove_custom_dictionary_words(["คำทดสอบ1"])
        print("✓ Removed words from dictionary")
        
        # Test validation
        print("\n5. Testing configuration validation...")
        validation_report = config_manager.validate_configuration()
        print(f"✓ Validation completed: {validation_report['valid']}")
        if validation_report['errors']:
            print(f"  Errors: {validation_report['errors']}")
        if validation_report['warnings']:
            print(f"  Warnings: {validation_report['warnings']}")
        
        # Test configuration retrieval methods
        print("\n6. Testing configuration retrieval methods...")
        meilisearch_config = config_manager.get_meilisearch_config()
        print(f"✓ MeiliSearch config: {meilisearch_config.host}")
        
        tokenizer_config = config_manager.get_tokenizer_config()
        print(f"✓ Tokenizer config: {tokenizer_config.engine}")
        
        processing_config = config_manager.get_processing_config()
        print(f"✓ Processing config: batch_size={processing_config.batch_size}")
        
        # Test stats
        print("\n7. Testing configuration stats...")
        stats = config_manager.get_stats()
        print(f"✓ Stats: service={stats['service_name']}, engine={stats['tokenizer_engine']}")
        
        print("\n✅ All configuration manager tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_config_manager()
    sys.exit(0 if success else 1)