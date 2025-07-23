"""Configuration management for Thai tokenizer."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class TokenizerConfig(BaseModel):
    """Configuration for Thai tokenizer engine."""
    engine: str = Field("pythainlp", description="Tokenization engine")
    model_version: Optional[str] = Field(None, description="Model version")
    custom_dictionary: Optional[List[str]] = Field(None, description="Custom dictionary words")


class MeiliSearchConfig(BaseModel):
    """Configuration for MeiliSearch connection."""
    host: str = Field(..., description="MeiliSearch host URL")
    api_key: str = Field(..., description="MeiliSearch API key")
    index_name: str = Field("documents", description="Default index name")


class ProcessingConfig(BaseModel):
    """Configuration for processing parameters."""
    batch_size: int = Field(100, description="Batch processing size")
    max_retries: int = Field(3, description="Maximum retry attempts")
    timeout_ms: int = Field(5000, description="Timeout in milliseconds")


class ThaiTokenizerSettings(BaseSettings):
    """Main application settings."""
    
    # Service configuration
    service_name: str = Field("thai-tokenizer", description="Service name")
    version: str = Field("0.1.0", description="Service version")
    log_level: str = Field("INFO", description="Logging level")
    
    # MeiliSearch configuration
    meilisearch_host: str = Field("http://localhost:7700", description="MeiliSearch host")
    meilisearch_api_key: str = Field("masterKey", description="MeiliSearch API key")
    meilisearch_index: str = Field("documents", description="Default index name")
    
    # Tokenizer configuration
    tokenizer_engine: str = Field("pythainlp", description="Tokenization engine")
    tokenizer_model: Optional[str] = Field(None, description="Tokenizer model version")
    
    # Processing configuration
    batch_size: int = Field(100, description="Batch processing size")
    max_retries: int = Field(3, description="Maximum retry attempts")
    timeout_ms: int = Field(5000, description="Request timeout in milliseconds")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


class ConfigManager:
    """Manager for application configuration."""
    
    def __init__(self):
        self.settings = ThaiTokenizerSettings()
    
    def get_meilisearch_config(self) -> MeiliSearchConfig:
        """Get MeiliSearch configuration."""
        return MeiliSearchConfig(
            host=self.settings.meilisearch_host,
            api_key=self.settings.meilisearch_api_key,
            index_name=self.settings.meilisearch_index
        )
    
    def get_tokenizer_config(self) -> TokenizerConfig:
        """Get tokenizer configuration."""
        return TokenizerConfig(
            engine=self.settings.tokenizer_engine,
            model_version=self.settings.tokenizer_model
        )
    
    def get_processing_config(self) -> ProcessingConfig:
        """Get processing configuration."""
        return ProcessingConfig(
            batch_size=self.settings.batch_size,
            max_retries=self.settings.max_retries,
            timeout_ms=self.settings.timeout_ms
        )
    
    def update_meilisearch_config(self, config: MeiliSearchConfig) -> None:
        """Update MeiliSearch configuration."""
        self.settings.meilisearch_host = config.host
        self.settings.meilisearch_api_key = config.api_key
        self.settings.meilisearch_index = config.index_name
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary."""
        return self.settings.model_dump()