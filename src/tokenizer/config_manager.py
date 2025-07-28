"""
Configuration management system for Thai tokenizer.

This module provides comprehensive configuration management with validation,
error handling, and support for custom dictionaries and tokenization parameters.
"""

import logging
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from enum import Enum

from pydantic import BaseModel, Field, field_validator, ValidationError, ConfigDict
from pydantic_settings import BaseSettings


logger = logging.getLogger(__name__)


class TokenizerEngine(str, Enum):
    """Supported tokenization engines."""
    PYTHAINLP = "pythainlp"
    NEWMM = "newmm"
    ATTACUT = "attacut"
    DEEPCUT = "deepcut"


class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class TokenizerConfig(BaseModel):
    """Configuration for Thai tokenizer engine."""
    
    engine: TokenizerEngine = Field(
        TokenizerEngine.NEWMM,
        description="Tokenization engine to use"
    )
    model_version: Optional[str] = Field(
        None,
        description="Specific model version (engine-dependent)"
    )
    custom_dictionary: List[str] = Field(
        default_factory=list,
        description="Custom dictionary words for enhanced tokenization"
    )
    keep_whitespace: bool = Field(
        True,
        description="Whether to preserve whitespace in tokenization"
    )
    handle_compounds: bool = Field(
        True,
        description="Whether to apply compound word processing"
    )
    fallback_engine: Optional[TokenizerEngine] = Field(
        TokenizerEngine.NEWMM,
        description="Fallback engine if primary fails"
    )
    
    @field_validator('custom_dictionary')
    @classmethod
    def validate_custom_dictionary(cls, v):
        """Validate custom dictionary entries."""
        if not isinstance(v, list):
            raise ValueError("Custom dictionary must be a list")
        
        # Filter out empty strings and duplicates
        valid_words = []
        seen = set()
        for word in v:
            if isinstance(word, str) and word.strip() and word not in seen:
                valid_words.append(word.strip())
                seen.add(word.strip())
        
        return valid_words


class MeiliSearchConfig(BaseModel):
    """Configuration for MeiliSearch connection."""
    
    host: str = Field(
        "http://localhost:7700",
        description="MeiliSearch host URL"
    )
    api_key: str = Field(
        "masterKey",
        description="MeiliSearch API key"
    )
    index_name: str = Field(
        "documents",
        description="Default index name"
    )
    timeout_ms: int = Field(
        5000,
        ge=1000,
        le=60000,
        description="Request timeout in milliseconds"
    )
    max_retries: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed requests"
    )
    
    @field_validator('host')
    @classmethod
    def validate_host(cls, v):
        """Validate MeiliSearch host URL."""
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Host must start with http:// or https://")
        return v.rstrip('/')
    
    @field_validator('index_name')
    @classmethod
    def validate_index_name(cls, v):
        """Validate index name format."""
        if not v or not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError("Index name must contain only alphanumeric characters, hyphens, and underscores")
        return v


class ProcessingConfig(BaseModel):
    """Configuration for processing parameters."""
    
    batch_size: int = Field(
        100,
        ge=1,
        le=1000,
        description="Batch processing size for documents"
    )
    max_concurrent: int = Field(
        10,
        ge=1,
        le=100,
        description="Maximum concurrent processing tasks"
    )
    chunk_size: int = Field(
        1000,
        ge=100,
        le=10000,
        description="Text chunk size for large documents"
    )
    enable_caching: bool = Field(
        True,
        description="Whether to enable result caching"
    )
    cache_ttl_seconds: int = Field(
        3600,
        ge=60,
        le=86400,
        description="Cache time-to-live in seconds"
    )


class CustomSeparatorConfig(BaseModel):
    """Configuration for custom separators."""
    
    additional_separators: List[str] = Field(
        default_factory=list,
        description="Additional separator tokens"
    )
    non_separator_tokens: List[str] = Field(
        default_factory=lambda: ["ๆ", "ฯ", "ฯลฯ"],
        description="Tokens that should not be treated as separators"
    )
    preserve_punctuation: bool = Field(
        True,
        description="Whether to preserve punctuation as separate tokens"
    )
    
    @field_validator('additional_separators', 'non_separator_tokens')
    @classmethod
    def validate_token_lists(cls, v):
        """Validate token lists."""
        if not isinstance(v, list):
            return []
        return [token for token in v if isinstance(token, str) and token]


class ThaiTokenizerSettings(BaseSettings):
    """Main application settings with environment variable support."""
    
    # Service configuration
    service_name: str = Field("thai-tokenizer", description="Service name")
    version: str = Field("0.1.0", description="Service version")
    log_level: LogLevel = Field(LogLevel.INFO, description="Logging level")
    debug: bool = Field(False, description="Enable debug mode")
    
    # MeiliSearch configuration
    meilisearch_host: str = Field("http://localhost:7700", description="MeiliSearch host")
    meilisearch_api_key: str = Field("masterKey", description="MeiliSearch API key")
    meilisearch_index: str = Field("documents", description="Default index name")
    meilisearch_timeout_ms: int = Field(5000, description="MeiliSearch timeout")
    meilisearch_max_retries: int = Field(3, description="MeiliSearch max retries")
    
    # Tokenizer configuration
    tokenizer_engine: TokenizerEngine = Field(TokenizerEngine.NEWMM, description="Tokenization engine")
    tokenizer_model: Optional[str] = Field(None, description="Tokenizer model version")
    tokenizer_keep_whitespace: bool = Field(True, description="Keep whitespace in tokens")
    tokenizer_handle_compounds: bool = Field(True, description="Handle compound words")
    tokenizer_fallback_engine: Optional[TokenizerEngine] = Field(TokenizerEngine.NEWMM, description="Fallback engine")
    
    # Processing configuration
    processing_batch_size: int = Field(100, description="Batch processing size")
    processing_max_concurrent: int = Field(10, description="Max concurrent tasks")
    processing_chunk_size: int = Field(1000, description="Text chunk size")
    processing_enable_caching: bool = Field(True, description="Enable caching")
    processing_cache_ttl: int = Field(3600, description="Cache TTL seconds")
    
    # Custom dictionary path
    custom_dictionary_path: Optional[str] = Field(None, description="Path to custom dictionary file")
    
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="THAI_TOKENIZER_"
    )


class ConfigurationError(Exception):
    """Custom exception for configuration errors."""
    pass


class ConfigManager:
    """
    Comprehensive configuration manager with validation and error handling.
    
    Provides centralized configuration management with support for:
    - Environment variables
    - Configuration files
    - Runtime updates
    - Validation and error handling
    - Custom dictionaries
    """
    
    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Optional path to configuration file
        """
        self.config_file = Path(config_file) if config_file else None
        self._settings = None
        self._custom_dictionary = []
        
        try:
            self._load_settings()
            self._load_custom_dictionary()
            logger.info("Configuration loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise ConfigurationError(f"Configuration initialization failed: {e}")
    
    def _load_settings(self) -> None:
        """Load settings from environment and config file."""
        try:
            self._settings = ThaiTokenizerSettings()
            
            # Override with config file if provided
            if self.config_file and self.config_file.exists():
                self._load_from_file()
                
        except ValidationError as e:
            raise ConfigurationError(f"Settings validation failed: {e}")
    
    def _load_from_file(self) -> None:
        """Load configuration from JSON file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Update settings with file data
            for key, value in config_data.items():
                if hasattr(self._settings, key):
                    setattr(self._settings, key, value)
                    
            logger.info(f"Configuration loaded from {self.config_file}")
            
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Failed to load config file {self.config_file}: {e}")
    
    def _load_custom_dictionary(self) -> None:
        """Load custom dictionary from file if specified."""
        if not self._settings.custom_dictionary_path:
            # Try default compound words dictionary
            default_dict_path = Path("data/dictionaries/thai_compounds.json")
            if default_dict_path.exists():
                self._settings.custom_dictionary_path = str(default_dict_path)
                logger.info(f"Using default compound dictionary: {default_dict_path}")
            else:
                return
        
        dict_path = Path(self._settings.custom_dictionary_path)
        if not dict_path.exists():
            logger.warning(f"Custom dictionary file not found: {dict_path}")
            return
        
        try:
            with open(dict_path, 'r', encoding='utf-8') as f:
                if dict_path.suffix.lower() == '.json':
                    data = json.load(f)
                    
                    # Handle different JSON formats
                    if isinstance(data, list):
                        # Simple list format
                        self._custom_dictionary = data
                    elif isinstance(data, dict):
                        # Compound words format with categories
                        compound_words = []
                        for category, words in data.items():
                            if isinstance(words, list):
                                compound_words.extend(words)
                            elif isinstance(words, str):
                                compound_words.append(words)
                        self._custom_dictionary = compound_words
                    else:
                        logger.warning(f"Unexpected JSON format in dictionary file: {dict_path}")
                        self._custom_dictionary = []
                else:
                    # Assume text file with one word per line
                    self._custom_dictionary = [
                        line.strip() for line in f 
                        if line.strip() and not line.startswith('#')
                    ]
            
            # Remove duplicates and empty entries
            self._custom_dictionary = list(set(word.strip() for word in self._custom_dictionary if word.strip()))
            
            logger.info(f"Loaded {len(self._custom_dictionary)} custom dictionary entries")
            
            # Log some examples for debugging
            if self._custom_dictionary:
                examples = self._custom_dictionary[:5]
                logger.info(f"Dictionary examples: {examples}")
            
        except Exception as e:
            logger.error(f"Failed to load custom dictionary: {e}")
            self._custom_dictionary = []
    
    @property
    def settings(self) -> ThaiTokenizerSettings:
        """Get current settings."""
        if self._settings is None:
            raise ConfigurationError("Settings not initialized")
        return self._settings
    
    def get_meilisearch_config(self) -> MeiliSearchConfig:
        """Get validated MeiliSearch configuration."""
        try:
            return MeiliSearchConfig(
                host=self.settings.meilisearch_host,
                api_key=self.settings.meilisearch_api_key,
                index_name=self.settings.meilisearch_index,
                timeout_ms=self.settings.meilisearch_timeout_ms,
                max_retries=self.settings.meilisearch_max_retries
            )
        except ValidationError as e:
            raise ConfigurationError(f"Invalid MeiliSearch configuration: {e}")
    
    def get_tokenizer_config(self) -> TokenizerConfig:
        """Get validated tokenizer configuration."""
        try:
            return TokenizerConfig(
                engine=self.settings.tokenizer_engine,
                model_version=self.settings.tokenizer_model,
                custom_dictionary=self._custom_dictionary,
                keep_whitespace=self.settings.tokenizer_keep_whitespace,
                handle_compounds=self.settings.tokenizer_handle_compounds,
                fallback_engine=self.settings.tokenizer_fallback_engine
            )
        except ValidationError as e:
            raise ConfigurationError(f"Invalid tokenizer configuration: {e}")
    
    def get_processing_config(self) -> ProcessingConfig:
        """Get validated processing configuration."""
        try:
            return ProcessingConfig(
                batch_size=self.settings.processing_batch_size,
                max_concurrent=self.settings.processing_max_concurrent,
                chunk_size=self.settings.processing_chunk_size,
                enable_caching=self.settings.processing_enable_caching,
                cache_ttl_seconds=self.settings.processing_cache_ttl
            )
        except ValidationError as e:
            raise ConfigurationError(f"Invalid processing configuration: {e}")
    
    def get_separator_config(self) -> CustomSeparatorConfig:
        """Get separator configuration."""
        return CustomSeparatorConfig()
    
    def update_meilisearch_config(self, config: MeiliSearchConfig) -> None:
        """Update MeiliSearch configuration with validation."""
        try:
            # Validate the new configuration
            validated_config = MeiliSearchConfig(**config.model_dump())
            
            # Update settings
            self.settings.meilisearch_host = validated_config.host
            self.settings.meilisearch_api_key = validated_config.api_key
            self.settings.meilisearch_index = validated_config.index_name
            self.settings.meilisearch_timeout_ms = validated_config.timeout_ms
            self.settings.meilisearch_max_retries = validated_config.max_retries
            
            logger.info("MeiliSearch configuration updated")
            
        except ValidationError as e:
            raise ConfigurationError(f"Invalid MeiliSearch configuration update: {e}")
    
    def update_tokenizer_config(self, config: TokenizerConfig) -> None:
        """Update tokenizer configuration with validation."""
        try:
            # Validate the new configuration
            validated_config = TokenizerConfig(**config.model_dump())
            
            # Update settings
            self.settings.tokenizer_engine = validated_config.engine
            self.settings.tokenizer_model = validated_config.model_version
            self.settings.tokenizer_keep_whitespace = validated_config.keep_whitespace
            self.settings.tokenizer_handle_compounds = validated_config.handle_compounds
            self.settings.tokenizer_fallback_engine = validated_config.fallback_engine
            
            # Update custom dictionary
            self._custom_dictionary = validated_config.custom_dictionary
            
            logger.info("Tokenizer configuration updated")
            
        except ValidationError as e:
            raise ConfigurationError(f"Invalid tokenizer configuration update: {e}")
    
    def add_custom_dictionary_words(self, words: List[str]) -> None:
        """Add words to custom dictionary with validation."""
        if not isinstance(words, list):
            raise ConfigurationError("Words must be provided as a list")
        
        valid_words = []
        for word in words:
            if isinstance(word, str) and word.strip():
                clean_word = word.strip()
                if clean_word not in self._custom_dictionary:
                    valid_words.append(clean_word)
        
        self._custom_dictionary.extend(valid_words)
        logger.info(f"Added {len(valid_words)} words to custom dictionary")
    
    def remove_custom_dictionary_words(self, words: List[str]) -> None:
        """Remove words from custom dictionary."""
        if not isinstance(words, list):
            raise ConfigurationError("Words must be provided as a list")
        
        removed_count = 0
        for word in words:
            if isinstance(word, str) and word.strip() in self._custom_dictionary:
                self._custom_dictionary.remove(word.strip())
                removed_count += 1
        
        logger.info(f"Removed {removed_count} words from custom dictionary")
    
    def save_to_file(self, file_path: Optional[Union[str, Path]] = None) -> None:
        """Save current configuration to file."""
        target_path = Path(file_path) if file_path else self.config_file
        
        if not target_path:
            raise ConfigurationError("No file path specified for saving configuration")
        
        try:
            config_dict = self.to_dict()
            
            # Ensure directory exists
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(target_path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configuration saved to {target_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to save configuration: {e}")
    
    def validate_configuration(self) -> Dict[str, Any]:
        """Validate all configuration components and return validation report."""
        validation_report = {
            "valid": True,
            "errors": [],
            "warnings": [],
            "components": {}
        }
        
        # Validate MeiliSearch config
        try:
            meilisearch_config = self.get_meilisearch_config()
            validation_report["components"]["meilisearch"] = "valid"
        except ConfigurationError as e:
            validation_report["valid"] = False
            validation_report["errors"].append(f"MeiliSearch: {e}")
            validation_report["components"]["meilisearch"] = "invalid"
        
        # Validate tokenizer config
        try:
            tokenizer_config = self.get_tokenizer_config()
            validation_report["components"]["tokenizer"] = "valid"
        except ConfigurationError as e:
            validation_report["valid"] = False
            validation_report["errors"].append(f"Tokenizer: {e}")
            validation_report["components"]["tokenizer"] = "invalid"
        
        # Validate processing config
        try:
            processing_config = self.get_processing_config()
            validation_report["components"]["processing"] = "valid"
        except ConfigurationError as e:
            validation_report["valid"] = False
            validation_report["errors"].append(f"Processing: {e}")
            validation_report["components"]["processing"] = "invalid"
        
        # Check for warnings
        if len(self._custom_dictionary) == 0:
            validation_report["warnings"].append("No custom dictionary words configured")
        
        if self.settings.debug:
            validation_report["warnings"].append("Debug mode is enabled")
        
        return validation_report
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all configuration to dictionary."""
        config_dict = self.settings.model_dump()
        config_dict["custom_dictionary"] = self._custom_dictionary
        config_dict["validation_report"] = self.validate_configuration()
        return config_dict
    
    def get_stats(self) -> Dict[str, Any]:
        """Get configuration statistics."""
        return {
            "service_name": self.settings.service_name,
            "version": self.settings.version,
            "tokenizer_engine": self.settings.tokenizer_engine.value,
            "custom_dictionary_size": len(self._custom_dictionary),
            "meilisearch_host": self.settings.meilisearch_host,
            "debug_mode": self.settings.debug,
            "config_file": str(self.config_file) if self.config_file else None,
            "validation_status": self.validate_configuration()["valid"]
        }