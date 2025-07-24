"""
Unit tests for MeiliSearch tokenization settings manager.
"""

import pytest
from unittest.mock import patch

from src.meilisearch_integration.settings_manager import (
    TokenizationSettingsManager,
    ThaiTokenizationConfig,
    MeiliSearchSettings,
    TokenizerEngine,
    create_default_thai_settings,
    create_minimal_thai_settings,
    validate_thai_text_settings
)


class TestThaiTokenizationConfig:
    """Test cases for ThaiTokenizationConfig."""
    
    def test_default_config_creation(self):
        """Test creating config with default values."""
        config = ThaiTokenizationConfig()
        
        assert "​" in config.separator_tokens  # Zero-width space
        assert "ๆ" in config.non_separator_tokens  # Thai repetition mark
        assert isinstance(config.custom_dictionary, list)
        assert isinstance(config.synonyms, dict)
        assert "และ" in config.stop_words  # Thai "and"
        assert "words" in config.ranking_rules
        assert "title" in config.searchable_attributes
    
    def test_custom_config_creation(self):
        """Test creating config with custom values."""
        config = ThaiTokenizationConfig(
            separator_tokens=["​", " "],
            custom_dictionary=["รถยนต์", "คอมพิวเตอร์"],
            synonyms={"กรุงเทพ": ["กรุงเทพมหานคร", "บางกอก"]}
        )
        
        assert config.separator_tokens == ["​", " "]
        assert "รถยนต์" in config.custom_dictionary
        assert "กรุงเทพ" in config.synonyms
        assert config.synonyms["กรุงเทพ"] == ["กรุงเทพมหานคร", "บางกอก"]


class TestMeiliSearchSettings:
    """Test cases for MeiliSearchSettings validation."""
    
    def test_valid_settings(self):
        """Test validation of valid settings."""
        settings_data = {
            "separatorTokens": ["​", " "],
            "nonSeparatorTokens": ["ๆ", "ฯ"],
            "dictionary": ["test"],
            "synonyms": {"word": ["variant"]},
            "stopWords": ["และ"],
            "rankingRules": ["words", "typo"],
            "searchableAttributes": ["title"],
            "displayedAttributes": ["id", "title"],
            "filterableAttributes": ["category"],
            "sortableAttributes": ["title"]
        }
        
        settings = MeiliSearchSettings(**settings_data)
        
        assert settings.separatorTokens == ["​", " "]
        assert settings.nonSeparatorTokens == ["ๆ", "ฯ"]
        assert settings.rankingRules == ["words", "typo"]
    
    def test_empty_separator_tokens_validation(self):
        """Test validation fails for empty separator tokens."""
        with pytest.raises(ValueError, match="Separator tokens cannot be empty"):
            MeiliSearchSettings(separatorTokens=[])
    
    def test_invalid_ranking_rules_validation(self):
        """Test validation fails for invalid ranking rules."""
        with pytest.raises(ValueError, match="Invalid ranking rule"):
            MeiliSearchSettings(
                separatorTokens=["​"],
                rankingRules=["words", "invalid_rule"]
            )


class TestTokenizationSettingsManager:
    """Test cases for TokenizationSettingsManager."""
    
    def test_manager_creation_with_defaults(self):
        """Test creating manager with default configuration."""
        manager = TokenizationSettingsManager()
        
        assert isinstance(manager.config, ThaiTokenizationConfig)
        assert manager._validated_settings is None
    
    def test_manager_creation_with_custom_config(self):
        """Test creating manager with custom configuration."""
        config = ThaiTokenizationConfig(
            separator_tokens=["​", " "],
            custom_dictionary=["test"]
        )
        manager = TokenizationSettingsManager(config)
        
        assert manager.config.separator_tokens == ["​", " "]
        assert manager.config.custom_dictionary == ["test"]
    
    def test_create_meilisearch_settings(self):
        """Test creating MeiliSearch settings dictionary."""
        manager = TokenizationSettingsManager()
        settings = manager.create_meilisearch_settings()
        
        assert "separatorTokens" in settings
        assert "nonSeparatorTokens" in settings
        assert "dictionary" in settings
        assert "synonyms" in settings
        assert "stopWords" in settings
        assert "rankingRules" in settings
        assert isinstance(settings["separatorTokens"], list)
        assert isinstance(settings["synonyms"], dict)
    
    def test_validate_settings_success(self):
        """Test successful settings validation."""
        manager = TokenizationSettingsManager()
        settings = {
            "separatorTokens": ["​", " "],
            "nonSeparatorTokens": ["ๆ"],
            "rankingRules": ["words", "typo"]
        }
        
        validated = manager.validate_settings(settings)
        
        assert isinstance(validated, MeiliSearchSettings)
        assert manager._validated_settings is not None
    
    def test_validate_settings_failure(self):
        """Test settings validation failure."""
        manager = TokenizationSettingsManager()
        invalid_settings = {
            "separatorTokens": [],  # Empty - should fail
            "rankingRules": ["invalid_rule"]  # Invalid rule
        }
        
        with pytest.raises(ValueError, match="Invalid MeiliSearch settings"):
            manager.validate_settings(invalid_settings)
    
    def test_add_custom_dictionary_words(self):
        """Test adding words to custom dictionary."""
        manager = TokenizationSettingsManager()
        initial_count = len(manager.config.custom_dictionary)
        
        new_words = ["รถยนต์", "คอมพิวเตอร์", "โทรศัพท์"]
        manager.add_custom_dictionary_words(new_words)
        
        assert len(manager.config.custom_dictionary) == initial_count + 3
        for word in new_words:
            assert word in manager.config.custom_dictionary
    
    def test_add_custom_dictionary_words_with_duplicates(self):
        """Test adding dictionary words with duplicates."""
        manager = TokenizationSettingsManager()
        manager.config.custom_dictionary = ["รถยนต์"]
        
        # Add words including duplicate
        new_words = ["รถยนต์", "คอมพิวเตอร์", "รถยนต์"]
        manager.add_custom_dictionary_words(new_words)
        
        # Should only add unique words
        assert manager.config.custom_dictionary.count("รถยนต์") == 1
        assert "คอมพิวเตอร์" in manager.config.custom_dictionary
    
    def test_add_custom_dictionary_words_empty_list(self):
        """Test adding empty list to dictionary."""
        manager = TokenizationSettingsManager()
        initial_dict = manager.config.custom_dictionary.copy()
        
        manager.add_custom_dictionary_words([])
        
        assert manager.config.custom_dictionary == initial_dict
    
    def test_add_synonyms(self):
        """Test adding synonym mappings."""
        manager = TokenizationSettingsManager()
        
        synonyms = {
            "กรุงเทพ": ["กรุงเทพมหานคร", "บางกอก"],
            "รถยนต์": ["รถ", "ยานยนต์"]
        }
        manager.add_synonyms(synonyms)
        
        assert "กรุงเทพ" in manager.config.synonyms
        assert "บางกอก" in manager.config.synonyms["กรุงเทพ"]
        assert "รถยนต์" in manager.config.synonyms
        assert "ยานยนต์" in manager.config.synonyms["รถยนต์"]
    
    def test_add_synonyms_merge_existing(self):
        """Test merging synonyms with existing ones."""
        manager = TokenizationSettingsManager()
        manager.config.synonyms = {"กรุงเทพ": ["บางกอก"]}
        
        new_synonyms = {"กรุงเทพ": ["กรุงเทพมหานคร", "กทม"]}
        manager.add_synonyms(new_synonyms)
        
        # Should merge variants
        variants = manager.config.synonyms["กรุงเทพ"]
        assert "บางกอก" in variants
        assert "กรุงเทพมหานคร" in variants
        assert "กทม" in variants
    
    def test_update_separator_tokens(self):
        """Test updating separator tokens."""
        manager = TokenizationSettingsManager()
        
        new_tokens = ["​", " ", "\t"]
        manager.update_separator_tokens(new_tokens)
        
        assert manager.config.separator_tokens == new_tokens
    
    def test_update_separator_tokens_empty_fails(self):
        """Test updating separator tokens with empty list fails."""
        manager = TokenizationSettingsManager()
        
        with pytest.raises(ValueError, match="Separator tokens cannot be empty"):
            manager.update_separator_tokens([])
    
    def test_update_non_separator_tokens(self):
        """Test updating non-separator tokens."""
        manager = TokenizationSettingsManager()
        
        new_tokens = ["ๆ", "ฯ", "์"]
        manager.update_non_separator_tokens(new_tokens)
        
        assert manager.config.non_separator_tokens == new_tokens
    
    def test_update_stop_words(self):
        """Test updating stop words."""
        manager = TokenizationSettingsManager()
        
        stop_words = ["และ", "หรือ", "แต่"]
        manager.update_stop_words(stop_words)
        
        assert manager.config.stop_words == stop_words
    
    def test_update_searchable_attributes(self):
        """Test updating searchable attributes."""
        manager = TokenizationSettingsManager()
        
        attributes = ["title", "content", "description"]
        manager.update_searchable_attributes(attributes)
        
        assert manager.config.searchable_attributes == attributes
    
    def test_update_searchable_attributes_empty_fails(self):
        """Test updating searchable attributes with empty list fails."""
        manager = TokenizationSettingsManager()
        
        with pytest.raises(ValueError, match="Searchable attributes cannot be empty"):
            manager.update_searchable_attributes([])
    
    def test_get_thai_specific_settings(self):
        """Test getting Thai-specific settings."""
        manager = TokenizationSettingsManager()
        settings = manager.get_thai_specific_settings()
        
        expected_keys = {
            "separatorTokens", "nonSeparatorTokens", "dictionary", 
            "synonyms", "stopWords"
        }
        assert set(settings.keys()) == expected_keys
    
    def test_get_search_settings(self):
        """Test getting search-related settings."""
        manager = TokenizationSettingsManager()
        settings = manager.get_search_settings()
        
        expected_keys = {
            "rankingRules", "searchableAttributes", "displayedAttributes",
            "filterableAttributes", "sortableAttributes"
        }
        assert set(settings.keys()) == expected_keys
    
    def test_reset_to_defaults(self):
        """Test resetting configuration to defaults."""
        manager = TokenizationSettingsManager()
        
        # Modify configuration
        manager.config.custom_dictionary = ["test"]
        manager._validated_settings = MeiliSearchSettings(separatorTokens=["​"])
        
        # Reset to defaults
        manager.reset_to_defaults()
        
        assert manager.config.custom_dictionary == []
        assert manager._validated_settings is None
    
    def test_export_config(self):
        """Test exporting configuration."""
        manager = TokenizationSettingsManager()
        config_dict = manager.export_config()
        
        expected_keys = {
            "separator_tokens", "non_separator_tokens", "custom_dictionary",
            "synonyms", "stop_words", "ranking_rules", "searchable_attributes",
            "displayed_attributes", "filterable_attributes", "sortable_attributes"
        }
        assert set(config_dict.keys()) == expected_keys
        assert isinstance(config_dict["separator_tokens"], list)
        assert isinstance(config_dict["synonyms"], dict)
    
    def test_import_config(self):
        """Test importing configuration."""
        manager = TokenizationSettingsManager()
        
        config_dict = {
            "separator_tokens": ["​", " "],
            "custom_dictionary": ["test1", "test2"],
            "synonyms": {"word": ["variant"]},
            "stop_words": ["และ", "หรือ"]
        }
        
        manager.import_config(config_dict)
        
        assert manager.config.separator_tokens == ["​", " "]
        assert manager.config.custom_dictionary == ["test1", "test2"]
        assert manager.config.synonyms == {"word": ["variant"]}
        assert manager.config.stop_words == ["และ", "หรือ"]
    
    def test_import_config_invalid_format(self):
        """Test importing invalid configuration format."""
        manager = TokenizationSettingsManager()
        
        # Invalid config - this will cause TypeError when creating ThaiTokenizationConfig
        invalid_config = {
            "separator_tokens": "not_a_list",  # Should be list
        }
        
        with pytest.raises(ValueError, match="Invalid configuration format"):
            manager.import_config(invalid_config)


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_create_default_thai_settings(self):
        """Test creating default Thai settings manager."""
        manager = create_default_thai_settings()
        
        assert isinstance(manager, TokenizationSettingsManager)
        assert isinstance(manager.config, ThaiTokenizationConfig)
        assert "​" in manager.config.separator_tokens
        assert "ๆ" in manager.config.non_separator_tokens
    
    def test_create_minimal_thai_settings(self):
        """Test creating minimal Thai settings manager."""
        manager = create_minimal_thai_settings()
        
        assert isinstance(manager, TokenizationSettingsManager)
        assert len(manager.config.separator_tokens) == 3  # Basic separators only
        assert len(manager.config.non_separator_tokens) == 2  # Essential marks only
        assert manager.config.custom_dictionary == []
        assert manager.config.synonyms == {}
        assert manager.config.stop_words == []
    
    def test_validate_thai_text_settings_valid(self):
        """Test validation of valid Thai text settings."""
        settings = {
            "separatorTokens": ["​", " ", "\n"],
            "nonSeparatorTokens": ["ๆ", "ฯ", "์"],
            "searchableAttributes": ["title", "content"]
        }
        
        assert validate_thai_text_settings(settings) is True
    
    def test_validate_thai_text_settings_missing_separator(self):
        """Test validation fails for missing Thai separator."""
        settings = {
            "separatorTokens": [" ", "\n"],  # Missing zero-width space
            "nonSeparatorTokens": ["ๆ", "ฯ"],
            "searchableAttributes": ["title"]
        }
        
        assert validate_thai_text_settings(settings) is False
    
    def test_validate_thai_text_settings_missing_thai_marks(self):
        """Test validation fails for missing Thai character marks."""
        settings = {
            "separatorTokens": ["​", " "],
            "nonSeparatorTokens": [],  # Missing Thai marks
            "searchableAttributes": ["title"]
        }
        
        assert validate_thai_text_settings(settings) is False
    
    def test_validate_thai_text_settings_no_searchable_attributes(self):
        """Test validation fails for no searchable attributes."""
        settings = {
            "separatorTokens": ["​", " "],
            "nonSeparatorTokens": ["ๆ"],
            "searchableAttributes": []  # Empty
        }
        
        assert validate_thai_text_settings(settings) is False
    
    def test_validate_thai_text_settings_exception_handling(self):
        """Test validation handles exceptions gracefully."""
        invalid_settings = None  # Will cause exception
        
        assert validate_thai_text_settings(invalid_settings) is False


class TestTokenizerEngine:
    """Test cases for TokenizerEngine enum."""
    
    def test_tokenizer_engine_values(self):
        """Test TokenizerEngine enum values."""
        assert TokenizerEngine.PYTHAINLP == "pythainlp"
        assert TokenizerEngine.ATTACUT == "attacut"
        assert TokenizerEngine.DEEPCUT == "deepcut"
    
    def test_tokenizer_engine_membership(self):
        """Test TokenizerEngine membership."""
        assert "pythainlp" in TokenizerEngine
        assert "attacut" in TokenizerEngine
        assert "deepcut" in TokenizerEngine
        assert "invalid" not in TokenizerEngine