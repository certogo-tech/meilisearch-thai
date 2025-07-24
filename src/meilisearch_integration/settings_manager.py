"""
Custom tokenization settings manager for Thai text in MeiliSearch.

This module provides functions to configure MeiliSearch separator and non-separator tokens,
update dictionary and synonym settings for Thai text, and validate tokenization configuration.
"""

import logging
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field, field_validator


logger = logging.getLogger(__name__)


class TokenizerEngine(str, Enum):
    """Supported Thai tokenizer engines."""
    PYTHAINLP = "pythainlp"
    ATTACUT = "attacut"
    DEEPCUT = "deepcut"


@dataclass
class ThaiTokenizationConfig:
    """Configuration for Thai tokenization settings."""
    # Thai word separators - invisible characters used to mark word boundaries
    separator_tokens: List[str] = field(default_factory=lambda: [
        "​",      # Zero-width space (U+200B)
        "​​",     # Double zero-width space
        " ",      # Regular space
        "\t",     # Tab
        "\n",     # Newline
    ])
    
    # Thai characters that should not be treated as separators
    non_separator_tokens: List[str] = field(default_factory=lambda: [
        "ๆ",      # Thai character maiyamok (repetition mark)
        "ฯ",      # Thai character paiyannoi (abbreviation mark)
        "ฯลฯ",    # Thai abbreviation "etc."
        "์",      # Thai character thanthakhat (silent mark)
        "ั",      # Thai character mai han-akat
        "ิ",      # Thai character sara i
        "ี",      # Thai character sara ii
        "ึ",      # Thai character sara ue
        "ื",      # Thai character sara uee
        "ุ",      # Thai character sara u
        "ู",      # Thai character sara uu
        "ำ",      # Thai character sara am
        "่",      # Thai character mai ek
        "้",      # Thai character mai tho
        "๊",      # Thai character mai tri
        "๋",      # Thai character mai chattawa
    ])
    
    # Custom dictionary for compound words
    custom_dictionary: List[str] = field(default_factory=list)
    
    # Synonyms for variant spellings
    synonyms: Dict[str, List[str]] = field(default_factory=dict)
    
    # Stop words to exclude from indexing
    stop_words: List[str] = field(default_factory=lambda: [
        "และ", "หรือ", "แต่", "เพราะ", "ถ้า", "เมื่อ", "ที่", "ซึ่ง",
        "ใน", "บน", "ที่", "จาก", "ไป", "มา", "ได้", "เป็น", "คือ",
        "มี", "ไม่", "ไม่ใช่", "ก็", "จึง", "เลย", "แล้ว", "อยู่"
    ])
    
    # Ranking rules for search relevance
    ranking_rules: List[str] = field(default_factory=lambda: [
        "words",
        "typo", 
        "proximity",
        "attribute",
        "sort",
        "exactness"
    ])
    
    # Searchable attributes with weights
    searchable_attributes: List[str] = field(default_factory=lambda: [
        "title",
        "content", 
        "thai_content",
        "tokenized_content"
    ])
    
    # Attributes to display in search results
    displayed_attributes: List[str] = field(default_factory=lambda: [
        "id",
        "title",
        "content",
        "thai_content",
        "metadata"
    ])
    
    # Attributes that can be used for filtering
    filterable_attributes: List[str] = field(default_factory=lambda: [
        "metadata.category",
        "metadata.language", 
        "metadata.created_at",
        "metadata.updated_at"
    ])
    
    # Attributes that can be used for sorting
    sortable_attributes: List[str] = field(default_factory=lambda: [
        "metadata.created_at",
        "metadata.updated_at",
        "title"
    ])


class MeiliSearchSettings(BaseModel):
    """Pydantic model for MeiliSearch settings validation."""
    
    separatorTokens: List[str] = Field(default_factory=list)
    nonSeparatorTokens: List[str] = Field(default_factory=list)
    dictionary: List[str] = Field(default_factory=list)
    synonyms: Dict[str, List[str]] = Field(default_factory=dict)
    stopWords: List[str] = Field(default_factory=list)
    rankingRules: List[str] = Field(default_factory=list)
    searchableAttributes: List[str] = Field(default_factory=list)
    displayedAttributes: List[str] = Field(default_factory=list)
    filterableAttributes: List[str] = Field(default_factory=list)
    sortableAttributes: List[str] = Field(default_factory=list)
    
    @field_validator('separatorTokens')
    @classmethod
    def validate_separator_tokens(cls, v):
        """Validate separator tokens."""
        if not v:
            raise ValueError("Separator tokens cannot be empty")
        return v
    
    @field_validator('rankingRules')
    @classmethod
    def validate_ranking_rules(cls, v):
        """Validate ranking rules."""
        valid_rules = {"words", "typo", "proximity", "attribute", "sort", "exactness"}
        for rule in v:
            if rule not in valid_rules:
                raise ValueError(f"Invalid ranking rule: {rule}")
        return v


class TokenizationSettingsManager:
    """
    Manager for Thai tokenization settings in MeiliSearch.
    
    Provides methods to configure separator tokens, dictionary settings,
    and validate tokenization configuration before applying to MeiliSearch.
    """
    
    def __init__(self, config: Optional[ThaiTokenizationConfig] = None):
        """Initialize settings manager with configuration."""
        self.config = config or ThaiTokenizationConfig()
        self._validated_settings: Optional[MeiliSearchSettings] = None
        
    def create_meilisearch_settings(self) -> Dict[str, Any]:
        """
        Create MeiliSearch settings dictionary from Thai tokenization config.
        
        Returns:
            Dictionary containing MeiliSearch-compatible settings
        """
        settings = {
            "separatorTokens": self.config.separator_tokens,
            "nonSeparatorTokens": self.config.non_separator_tokens,
            "dictionary": self.config.custom_dictionary,
            "synonyms": self.config.synonyms,
            "stopWords": self.config.stop_words,
            "rankingRules": self.config.ranking_rules,
            "searchableAttributes": self.config.searchable_attributes,
            "displayedAttributes": self.config.displayed_attributes,
            "filterableAttributes": self.config.filterable_attributes,
            "sortableAttributes": self.config.sortable_attributes
        }
        
        logger.info("Created MeiliSearch settings with Thai tokenization configuration")
        return settings
    
    def validate_settings(self, settings: Dict[str, Any]) -> MeiliSearchSettings:
        """
        Validate MeiliSearch settings before applying.
        
        Args:
            settings: Dictionary of MeiliSearch settings
            
        Returns:
            Validated MeiliSearchSettings object
            
        Raises:
            ValueError: If settings are invalid
        """
        try:
            validated = MeiliSearchSettings(**settings)
            self._validated_settings = validated
            logger.info("Settings validation successful")
            return validated
        except Exception as e:
            logger.error(f"Settings validation failed: {e}")
            raise ValueError(f"Invalid MeiliSearch settings: {e}")
    
    def add_custom_dictionary_words(self, words: List[str]) -> None:
        """
        Add words to custom dictionary for compound word recognition.
        
        Args:
            words: List of Thai words to add to dictionary
        """
        if not words:
            return
            
        # Remove duplicates and empty strings
        new_words = [word.strip() for word in words if word.strip()]
        existing_words = set(self.config.custom_dictionary)
        
        for word in new_words:
            if word not in existing_words:
                self.config.custom_dictionary.append(word)
                existing_words.add(word)
        
        logger.info(f"Added {len(new_words)} words to custom dictionary")
    
    def add_synonyms(self, synonym_map: Dict[str, List[str]]) -> None:
        """
        Add synonym mappings for variant spellings.
        
        Args:
            synonym_map: Dictionary mapping canonical forms to variant spellings
        """
        if not synonym_map:
            return
            
        for canonical, variants in synonym_map.items():
            if canonical.strip():
                # Clean and deduplicate variants
                clean_variants = [v.strip() for v in variants if v.strip()]
                if clean_variants:
                    if canonical in self.config.synonyms:
                        # Merge with existing variants
                        existing = set(self.config.synonyms[canonical])
                        existing.update(clean_variants)
                        self.config.synonyms[canonical] = list(existing)
                    else:
                        self.config.synonyms[canonical] = clean_variants
        
        logger.info(f"Added synonyms for {len(synonym_map)} canonical forms")
    
    def update_separator_tokens(self, tokens: List[str]) -> None:
        """
        Update separator tokens for Thai word boundaries.
        
        Args:
            tokens: List of separator tokens
        """
        if not tokens:
            raise ValueError("Separator tokens cannot be empty")
            
        self.config.separator_tokens = [token for token in tokens if token]
        logger.info(f"Updated separator tokens: {len(self.config.separator_tokens)} tokens")
    
    def update_non_separator_tokens(self, tokens: List[str]) -> None:
        """
        Update non-separator tokens for Thai characters.
        
        Args:
            tokens: List of non-separator tokens
        """
        self.config.non_separator_tokens = [token for token in tokens if token]
        logger.info(f"Updated non-separator tokens: {len(self.config.non_separator_tokens)} tokens")
    
    def update_stop_words(self, stop_words: List[str]) -> None:
        """
        Update stop words list.
        
        Args:
            stop_words: List of stop words to exclude from indexing
        """
        clean_words = [word.strip() for word in stop_words if word.strip()]
        self.config.stop_words = clean_words
        logger.info(f"Updated stop words: {len(clean_words)} words")
    
    def update_searchable_attributes(self, attributes: List[str]) -> None:
        """
        Update searchable attributes configuration.
        
        Args:
            attributes: List of attributes to make searchable
        """
        if not attributes:
            raise ValueError("Searchable attributes cannot be empty")
            
        self.config.searchable_attributes = [attr.strip() for attr in attributes if attr.strip()]
        logger.info(f"Updated searchable attributes: {self.config.searchable_attributes}")
    
    def get_thai_specific_settings(self) -> Dict[str, Any]:
        """
        Get Thai-specific tokenization settings.
        
        Returns:
            Dictionary containing only Thai-specific settings
        """
        return {
            "separatorTokens": self.config.separator_tokens,
            "nonSeparatorTokens": self.config.non_separator_tokens,
            "dictionary": self.config.custom_dictionary,
            "synonyms": self.config.synonyms,
            "stopWords": self.config.stop_words
        }
    
    def get_search_settings(self) -> Dict[str, Any]:
        """
        Get search-related settings.
        
        Returns:
            Dictionary containing search configuration
        """
        return {
            "rankingRules": self.config.ranking_rules,
            "searchableAttributes": self.config.searchable_attributes,
            "displayedAttributes": self.config.displayed_attributes,
            "filterableAttributes": self.config.filterable_attributes,
            "sortableAttributes": self.config.sortable_attributes
        }
    
    def reset_to_defaults(self) -> None:
        """Reset configuration to default Thai tokenization settings."""
        self.config = ThaiTokenizationConfig()
        self._validated_settings = None
        logger.info("Reset tokenization settings to defaults")
    
    def export_config(self) -> Dict[str, Any]:
        """
        Export current configuration as dictionary.
        
        Returns:
            Dictionary representation of current configuration
        """
        return {
            "separator_tokens": self.config.separator_tokens,
            "non_separator_tokens": self.config.non_separator_tokens,
            "custom_dictionary": self.config.custom_dictionary,
            "synonyms": self.config.synonyms,
            "stop_words": self.config.stop_words,
            "ranking_rules": self.config.ranking_rules,
            "searchable_attributes": self.config.searchable_attributes,
            "displayed_attributes": self.config.displayed_attributes,
            "filterable_attributes": self.config.filterable_attributes,
            "sortable_attributes": self.config.sortable_attributes
        }
    
    def import_config(self, config_dict: Dict[str, Any]) -> None:
        """
        Import configuration from dictionary.
        
        Args:
            config_dict: Dictionary containing configuration
        """
        try:
            # Map dictionary keys to dataclass fields
            field_mapping = {
                "separator_tokens": "separator_tokens",
                "non_separator_tokens": "non_separator_tokens", 
                "custom_dictionary": "custom_dictionary",
                "synonyms": "synonyms",
                "stop_words": "stop_words",
                "ranking_rules": "ranking_rules",
                "searchable_attributes": "searchable_attributes",
                "displayed_attributes": "displayed_attributes",
                "filterable_attributes": "filterable_attributes",
                "sortable_attributes": "sortable_attributes"
            }
            
            # Create new config with imported values
            config_kwargs = {}
            for dict_key, field_name in field_mapping.items():
                if dict_key in config_dict:
                    config_kwargs[field_name] = config_dict[dict_key]
            
            self.config = ThaiTokenizationConfig(**config_kwargs)
            self._validated_settings = None
            logger.info("Imported tokenization configuration")
            
        except Exception as e:
            logger.error(f"Failed to import configuration: {e}")
            raise ValueError(f"Invalid configuration format: {e}")


def create_default_thai_settings() -> TokenizationSettingsManager:
    """
    Create a settings manager with default Thai tokenization configuration.
    
    Returns:
        TokenizationSettingsManager with default Thai settings
    """
    return TokenizationSettingsManager()


def create_minimal_thai_settings() -> TokenizationSettingsManager:
    """
    Create a settings manager with minimal Thai tokenization configuration.
    
    Returns:
        TokenizationSettingsManager with minimal settings for basic Thai support
    """
    minimal_config = ThaiTokenizationConfig(
        separator_tokens=["​", " ", "\n"],  # Basic separators only
        non_separator_tokens=["ๆ", "ฯ"],   # Essential Thai marks only
        custom_dictionary=[],               # No custom dictionary
        synonyms={},                        # No synonyms
        stop_words=[],                      # No stop words
        searchable_attributes=["title", "content"],  # Basic searchable fields
        displayed_attributes=["id", "title", "content"],  # Basic display fields
        filterable_attributes=[],           # No filtering
        sortable_attributes=["title"]       # Basic sorting
    )
    
    return TokenizationSettingsManager(minimal_config)


async def configure_thai_tokenization(client, index_name: str, settings_manager: Optional[TokenizationSettingsManager] = None) -> Dict[str, Any]:
    """
    Configure Thai tokenization settings for a MeiliSearch index.
    
    Args:
        client: MeiliSearch client instance
        index_name: Name of the index to configure
        settings_manager: Optional settings manager instance
        
    Returns:
        Dictionary with configuration status
    """
    try:
        # Use provided settings manager or create a default one
        manager = settings_manager or create_default_thai_settings()
        
        # Create Thai tokenization settings
        thai_settings = manager.create_meilisearch_settings()
        
        # Apply settings to the index
        result = await client.update_index_settings(index_name, thai_settings)
        
        logger.info(f"Thai tokenization settings applied to index: {index_name}")
        return {
            "status": "configured",
            "index": index_name,
            "task_uid": result.get("task_uid")
        }
        
    except Exception as e:
        logger.error(f"Failed to configure Thai tokenization for index {index_name}: {e}")
        raise


def validate_thai_text_settings(settings: Dict[str, Any]) -> bool:
    """
    Validate that settings are appropriate for Thai text processing.
    
    Args:
        settings: MeiliSearch settings dictionary
        
    Returns:
        True if settings are valid for Thai text, False otherwise
    """
    try:
        # Check for required Thai separator tokens
        separator_tokens = settings.get("separatorTokens", [])
        if "​" not in separator_tokens:  # Zero-width space
            logger.warning("Missing zero-width space separator for Thai text")
            return False
        
        # Check for Thai non-separator tokens
        non_separator_tokens = settings.get("nonSeparatorTokens", [])
        thai_marks = ["ๆ", "ฯ", "์"]
        if not any(mark in non_separator_tokens for mark in thai_marks):
            logger.warning("Missing Thai character marks in non-separator tokens")
            return False
        
        # Validate searchable attributes
        searchable = settings.get("searchableAttributes", [])
        if not searchable:
            logger.warning("No searchable attributes configured")
            return False
        
        logger.info("Thai text settings validation passed")
        return True
        
    except Exception as e:
        logger.error(f"Settings validation error: {e}")
        return False