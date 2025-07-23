"""
Unit tests for configuration management system.

Tests configuration validation, error handling, and custom dictionary support.
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

from src.tokenizer.config_manager import (
    ConfigManager, TokenizerConfig, MeiliSearchConfig, ProcessingConfig,
    CustomSeparatorConfig, ThaiTokenizerSettings, ConfigurationError,
    TokenizerEngine, LogLevel
)


class TestTokenizerConfig:
    """Test cases for TokenizerConfig model."""
    
    def test_tokenizer_config_defaults(self):
        """Test default tokenizer configuration."""
        config = TokenizerConfig()
        
        assert config.engine == TokenizerEngine.NEWMM
        assert config.model_version is None
        assert config.custom_dictionary == []
        assert config.keep_whitespace is True
        assert config.handle_compounds is True
        assert config.fallback_engine == TokenizerEngine.NEWMM
    
    def test_tokenizer_config_custom(self):
        """Test custom tokenizer configuration."""
        custom_dict = ["คำศัพท์", "เทคนิค"]
        config = TokenizerConfig(
            engine=TokenizerEngine.ATTACUT,
            model_version="1.0.0",
            custom_dictionary=custom_dict,
            keep_whitespace=False,
            handle_compounds=False,
            fallback_engine=TokenizerEngine.DEEPCUT
        )
        
        assert config.engine == TokenizerEngine.ATTACUT
        assert config.model_version == "1.0.0"
        assert config.custom_dictionary == custom_dict
        assert config.keep_whitespace is False
        assert config.handle_compounds is False
        assert config.fallback_engine == TokenizerEngine.DEEPCUT
    
    def test_custom_dictionary_validation(self):
        """Test custom dictionary validation."""
        # Test with duplicates and empty strings
        config = TokenizerConfig(
            custom_dictionary=["word1", "word2", "word1", "", "  ", "word3"]
        )
        
        # Should remove duplicates and empty strings
        assert len(config.custom_dictionary) == 3
        assert "word1" in config.custom_dictionary
        assert "word2" in config.custom_dictionary
        assert "word3" in config.custom_dictionary
        assert "" not in config.custom_dictionary


class TestMeiliSearchConfig:
    """Test cases for MeiliSearchConfig model."""
    
    def test_meilisearch_config_defaults(self):
        """Test default MeiliSearch configuration."""
        config = MeiliSearchConfig()
        
        assert config.host == "http://localhost:7700"
        assert config.api_key == "masterKey"
        assert config.index_name == "documents"
        assert config.timeout_ms == 5000
        assert config.max_retries == 3
    
    def test_meilisearch_config_custom(self):
        """Test custom MeiliSearch configuration."""
        config = MeiliSearchConfig(
            host="https://search.example.com",
            api_key="custom-key",
            index_name="thai_docs",
            timeout_ms=10000,
            max_retries=5
        )
        
        assert config.host == "https://search.example.com"
        assert config.api_key == "custom-key"
        assert config.index_name == "thai_docs"
        assert config.timeout_ms == 10000
        assert config.max_retries == 5
    
    def test_host_validation(self):
        """Test host URL validation."""
        # Valid hosts
        valid_hosts = [
            "http://localhost:7700",
            "https://search.example.com",
            "http://192.168.1.100:7700"
        ]
        
        for host in valid_hosts:
            config = MeiliSearchConfig(host=host)
            assert config.host == host.rstrip('/')
        
        # Invalid hosts should raise validation error
        with pytest.raises(ValueError, match="Host must start with http"):
            MeiliSearchConfig(host="localhost:7700")
    
    def test_index_name_validation(self):
        """Test index name validation."""
        # Valid index names
        valid_names = ["documents", "thai_docs", "search-index", "index123"]
        
        for name in valid_names:
            config = MeiliSearchConfig(index_name=name)
            assert config.index_name == name
        
        # Invalid index names
        invalid_names = ["", "index with spaces", "index@special"]
        
        for name in invalid_names:
            with pytest.raises(ValueError, match="Index name must contain only"):
                MeiliSearchConfig(index_name=name)
    
    def test_timeout_validation(self):
        """Test timeout validation."""
        # Valid timeouts
        config = MeiliSearchConfig(timeout_ms=5000)
        assert config.timeout_ms == 5000
        
        # Invalid timeouts (too low or too high)
        with pytest.raises(ValueError):
            MeiliSearchConfig(timeout_ms=500)  # Too low
        
        with pytest.raises(ValueError):
            MeiliSearchConfig(timeout_ms=70000)  # Too high


class TestProcessingConfig:
    """Test cases for ProcessingConfig model."""
    
    def test_processing_config_defaults(self):
        """Test default processing configuration."""
        config = ProcessingConfig()
        
        assert config.batch_size == 100
        assert config.max_concurrent == 10
        assert config.chunk_size == 1000
        assert config.enable_caching is True
        assert config.cache_ttl_seconds == 3600
    
    def test_processing_config_validation(self):
        """Test processing configuration validation."""
        # Valid configuration
        config = ProcessingConfig(
            batch_size=50,
            max_concurrent=5,
            chunk_size=500,
            enable_caching=False,
            cache_ttl_seconds=1800
        )
        
        assert config.batch_size == 50
        assert config.max_concurrent == 5
        assert config.chunk_size == 500
        assert config.enable_caching is False
        assert config.cache_ttl_seconds == 1800
        
        # Invalid values should raise validation errors
        with pytest.raises(ValueError):
            ProcessingConfig(batch_size=0)  # Too low
        
        with pytest.raises(ValueError):
            ProcessingConfig(max_concurrent=101)  # Too high


class TestCustomSeparatorConfig:
    """Test cases for CustomSeparatorConfig model."""
    
    def test_separator_config_defaults(self):
        """Test default separator configuration."""
        config = CustomSeparatorConfig()
        
        assert config.additional_separators == []
        assert "ๆ" in config.non_separator_tokens
        assert "ฯ" in config.non_separator_tokens
        assert config.preserve_punctuation is True
    
    def test_separator_config_custom(self):
        """Test custom separator configuration."""
        config = CustomSeparatorConfig(
            additional_separators=["@", "#"],
            non_separator_tokens=["ๆ", "custom"],
            preserve_punctuation=False
        )
        
        assert config.additional_separators == ["@", "#"]
        assert config.non_separator_tokens == ["ๆ", "custom"]
        assert config.preserve_punctuation is False


class TestThaiTokenizerSettings:
    """Test cases for ThaiTokenizerSettings."""
    
    def test_settings_defaults(self):
        """Test default settings."""
        settings = ThaiTokenizerSettings()
        
        assert settings.service_name == "thai-tokenizer"
        assert settings.version == "0.1.0"
        assert settings.log_level == LogLevel.INFO
        assert settings.debug is False
        assert settings.tokenizer_engine == TokenizerEngine.NEWMM
        assert settings.processing_batch_size == 100
    
    @patch.dict('os.environ', {
        'THAI_TOKENIZER_SERVICE_NAME': 'custom-tokenizer',
        'THAI_TOKENIZER_LOG_LEVEL': 'DEBUG',
        'THAI_TOKENIZER_DEBUG': 'true'
    })
    def test_settings_from_environment(self):
        """Test settings loading from environment variables."""
        settings = ThaiTokenizerSettings()
        
        assert settings.service_name == "custom-tokenizer"
        assert settings.log_level == LogLevel.DEBUG
        assert settings.debug is True


class TestConfigManager:
    """Test cases for ConfigManager class."""
    
    def test_config_manager_initialization(self):
        """Test config manager initialization."""
        manager = ConfigManager()
        
        assert manager.settings is not None
        assert isinstance(manager.settings, ThaiTokenizerSettings)
        assert manager._custom_dictionary == []
    
    def test_get_meilisearch_config(self):
        """Test getting MeiliSearch configuration."""
        manager = ConfigManager()
        config = manager.get_meilisearch_config()
        
        assert isinstance(config, MeiliSearchConfig)
        assert config.host == manager.settings.meilisearch_host
        assert config.api_key == manager.settings.meilisearch_api_key
        assert config.index_name == manager.settings.meilisearch_index
    
    def test_get_tokenizer_config(self):
        """Test getting tokenizer configuration."""
        manager = ConfigManager()
        config = manager.get_tokenizer_config()
        
        assert isinstance(config, TokenizerConfig)
        assert config.engine == manager.settings.tokenizer_engine
        assert config.custom_dictionary == manager._custom_dictionary
    
    def test_get_processing_config(self):
        """Test getting processing configuration."""
        manager = ConfigManager()
        config = manager.get_processing_config()
        
        assert isinstance(config, ProcessingConfig)
        assert config.batch_size == manager.settings.processing_batch_size
        assert config.max_concurrent == manager.settings.processing_max_concurrent
    
    def test_update_meilisearch_config(self):
        """Test updating MeiliSearch configuration."""
        manager = ConfigManager()
        
        new_config = MeiliSearchConfig(
            host="https://new-host.com",
            api_key="new-key",
            index_name="new_index"
        )
        
        manager.update_meilisearch_config(new_config)
        
        assert manager.settings.meilisearch_host == "https://new-host.com"
        assert manager.settings.meilisearch_api_key == "new-key"
        assert manager.settings.meilisearch_index == "new_index"
    
    def test_update_tokenizer_config(self):
        """Test updating tokenizer configuration."""
        manager = ConfigManager()
        
        new_config = TokenizerConfig(
            engine=TokenizerEngine.ATTACUT,
            custom_dictionary=["word1", "word2"],
            keep_whitespace=False
        )
        
        manager.update_tokenizer_config(new_config)
        
        assert manager.settings.tokenizer_engine == TokenizerEngine.ATTACUT
        assert manager._custom_dictionary == ["word1", "word2"]
        assert manager.settings.tokenizer_keep_whitespace is False
    
    def test_add_custom_dictionary_words(self):
        """Test adding custom dictionary words."""
        manager = ConfigManager()
        
        words = ["คำใหม่", "เทคโนโลยี", "สารสนเทศ"]
        manager.add_custom_dictionary_words(words)
        
        assert len(manager._custom_dictionary) == 3
        for word in words:
            assert word in manager._custom_dictionary
        
        # Test adding duplicates
        manager.add_custom_dictionary_words(["คำใหม่", "คำอื่น"])
        assert len(manager._custom_dictionary) == 4  # Only one new word added
        assert "คำอื่น" in manager._custom_dictionary
    
    def test_remove_custom_dictionary_words(self):
        """Test removing custom dictionary words."""
        manager = ConfigManager()
        
        # Add some words first
        words = ["word1", "word2", "word3"]
        manager.add_custom_dictionary_words(words)
        
        # Remove some words
        manager.remove_custom_dictionary_words(["word1", "word3"])
        
        assert len(manager._custom_dictionary) == 1
        assert "word2" in manager._custom_dictionary
        assert "word1" not in manager._custom_dictionary
        assert "word3" not in manager._custom_dictionary
    
    def test_validate_configuration(self):
        """Test configuration validation."""
        manager = ConfigManager()
        validation_report = manager.validate_configuration()
        
        assert isinstance(validation_report, dict)
        assert "valid" in validation_report
        assert "errors" in validation_report
        assert "warnings" in validation_report
        assert "components" in validation_report
        
        # Should be valid by default
        assert validation_report["valid"] is True
        assert len(validation_report["errors"]) == 0
    
    def test_configuration_error_handling(self):
        """Test configuration error handling."""
        manager = ConfigManager()
        
        # Test invalid MeiliSearch config creation should fail at validation
        with pytest.raises(ValueError):
            MeiliSearchConfig(host="invalid-host")
    
    def test_to_dict(self):
        """Test converting configuration to dictionary."""
        manager = ConfigManager()
        config_dict = manager.to_dict()
        
        assert isinstance(config_dict, dict)
        assert "service_name" in config_dict
        assert "custom_dictionary" in config_dict
        assert "validation_report" in config_dict
    
    def test_get_stats(self):
        """Test getting configuration statistics."""
        manager = ConfigManager()
        stats = manager.get_stats()
        
        assert isinstance(stats, dict)
        required_keys = [
            "service_name", "version", "tokenizer_engine",
            "custom_dictionary_size", "meilisearch_host",
            "debug_mode", "validation_status"
        ]
        
        for key in required_keys:
            assert key in stats
    
    def test_config_file_loading(self):
        """Test loading configuration from file."""
        config_data = {
            "service_name": "test-tokenizer",
            "log_level": "DEBUG",
            "meilisearch_host": "http://test-host:7700"
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(config_data, f)
            config_file = f.name
        
        try:
            manager = ConfigManager(config_file=config_file)
            
            assert manager.settings.service_name == "test-tokenizer"
            assert manager.settings.log_level == LogLevel.DEBUG
            assert manager.settings.meilisearch_host == "http://test-host:7700"
            
        finally:
            Path(config_file).unlink()
    
    def test_custom_dictionary_file_loading(self):
        """Test loading custom dictionary from file."""
        dictionary_words = ["คำที่หนึ่ง", "คำที่สอง", "คำที่สาม"]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(dictionary_words, f)
            dict_file = f.name
        
        try:
            # Mock environment variable for dictionary path
            with patch.dict('os.environ', {'THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH': dict_file}):
                manager = ConfigManager()
                
                assert len(manager._custom_dictionary) == 3
                for word in dictionary_words:
                    assert word in manager._custom_dictionary
                    
        finally:
            Path(dict_file).unlink()
    
    def test_save_to_file(self):
        """Test saving configuration to file."""
        manager = ConfigManager()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            save_file = f.name
        
        try:
            manager.save_to_file(save_file)
            
            # Verify file was created and contains valid JSON
            assert Path(save_file).exists()
            
            with open(save_file, 'r') as f:
                saved_config = json.load(f)
            
            assert isinstance(saved_config, dict)
            assert "service_name" in saved_config
            
        finally:
            Path(save_file).unlink()


class TestConfigurationError:
    """Test cases for ConfigurationError exception."""
    
    def test_configuration_error(self):
        """Test ConfigurationError exception."""
        error_message = "Test configuration error"
        
        with pytest.raises(ConfigurationError, match=error_message):
            raise ConfigurationError(error_message)


class TestEnums:
    """Test cases for configuration enums."""
    
    def test_tokenizer_engine_enum(self):
        """Test TokenizerEngine enum values."""
        assert TokenizerEngine.PYTHAINLP.value == "pythainlp"
        assert TokenizerEngine.NEWMM.value == "newmm"
        assert TokenizerEngine.ATTACUT.value == "attacut"
        assert TokenizerEngine.DEEPCUT.value == "deepcut"
    
    def test_log_level_enum(self):
        """Test LogLevel enum values."""
        assert LogLevel.DEBUG.value == "DEBUG"
        assert LogLevel.INFO.value == "INFO"
        assert LogLevel.WARNING.value == "WARNING"
        assert LogLevel.ERROR.value == "ERROR"
        assert LogLevel.CRITICAL.value == "CRITICAL"


@pytest.fixture
def sample_config_data():
    """Fixture providing sample configuration data."""
    return {
        "service_name": "test-tokenizer",
        "version": "1.0.0",
        "log_level": "DEBUG",
        "meilisearch_host": "http://test-host:7700",
        "meilisearch_api_key": "test-key",
        "tokenizer_engine": "attacut",
        "processing_batch_size": 50
    }


@pytest.fixture
def sample_dictionary_words():
    """Fixture providing sample dictionary words."""
    return [
        "เทคโนโลยี",
        "สารสนเทศ",
        "คอมพิวเตอร์",
        "โปรแกรม",
        "ระบบ"
    ]


class TestConfigManagerIntegration:
    """Integration tests for ConfigManager."""
    
    def test_full_configuration_workflow(self, sample_config_data, sample_dictionary_words):
        """Test complete configuration workflow."""
        # Create config manager
        manager = ConfigManager()
        
        # Update configurations
        meilisearch_config = MeiliSearchConfig(
            host=sample_config_data["meilisearch_host"],
            api_key=sample_config_data["meilisearch_api_key"]
        )
        manager.update_meilisearch_config(meilisearch_config)
        
        tokenizer_config = TokenizerConfig(
            engine=TokenizerEngine.ATTACUT,
            custom_dictionary=sample_dictionary_words
        )
        manager.update_tokenizer_config(tokenizer_config)
        
        # Validate configuration
        validation_report = manager.validate_configuration()
        assert validation_report["valid"] is True
        
        # Get all configurations
        ms_config = manager.get_meilisearch_config()
        tok_config = manager.get_tokenizer_config()
        proc_config = manager.get_processing_config()
        
        # Verify configurations
        assert ms_config.host == sample_config_data["meilisearch_host"]
        assert tok_config.engine == TokenizerEngine.ATTACUT
        assert len(tok_config.custom_dictionary) == len(sample_dictionary_words)
        assert isinstance(proc_config, ProcessingConfig)
        
        # Get statistics
        stats = manager.get_stats()
        assert stats["tokenizer_engine"] == "attacut"
        assert stats["custom_dictionary_size"] == len(sample_dictionary_words)
        assert stats["validation_status"] is True