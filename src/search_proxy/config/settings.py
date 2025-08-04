"""
Configuration settings for the search proxy service.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


class TokenizationConfig(BaseModel):
    """Configuration for Thai tokenization engines."""
    
    primary_engine: str = Field(default="newmm", description="Primary tokenization engine")
    fallback_engines: List[str] = Field(default_factory=lambda: ["attacut", "deepcut"], description="Fallback engines in order")
    timeout_ms: int = Field(default=5000, ge=100, le=30000, description="Tokenization timeout in milliseconds")
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum confidence for tokenization")
    enable_compound_splitting: bool = Field(default=True, description="Enable compound word splitting")
    preserve_original: bool = Field(default=True, description="Always preserve original query as variant")
    mixed_language_detection: bool = Field(default=True, description="Enable mixed Thai-English detection")
    
    class Config:
        json_schema_extra = {
            "example": {
                "primary_engine": "newmm",
                "fallback_engines": ["attacut", "deepcut"],
                "timeout_ms": 3000,
                "confidence_threshold": 0.8,
                "enable_compound_splitting": True
            }
        }


class SearchConfig(BaseModel):
    """Configuration for search execution."""
    
    parallel_searches: bool = Field(default=True, description="Enable parallel search execution")
    max_concurrent_searches: int = Field(default=5, ge=1, le=20, description="Maximum concurrent searches")
    timeout_ms: int = Field(default=10000, ge=1000, le=60000, description="Search timeout in milliseconds")
    retry_attempts: int = Field(default=2, ge=0, le=5, description="Number of retry attempts for failed searches")
    retry_delay_ms: int = Field(default=100, ge=50, le=5000, description="Delay between retry attempts")
    enable_fallback_search: bool = Field(default=True, description="Enable fallback search on tokenization failure")
    max_query_variants: int = Field(default=5, ge=1, le=10, description="Maximum number of query variants to generate")
    deduplication_enabled: bool = Field(default=True, description="Enable result deduplication")
    
    class Config:
        json_schema_extra = {
            "example": {
                "parallel_searches": True,
                "max_concurrent_searches": 10,
                "timeout_ms": 5000,
                "retry_attempts": 2,
                "enable_fallback_search": True
            }
        }


class RankingConfig(BaseModel):
    """Configuration for result ranking and scoring."""
    
    algorithm: str = Field(default="weighted_score", description="Ranking algorithm to use")
    boost_exact_matches: float = Field(default=2.0, ge=1.0, le=5.0, description="Boost factor for exact matches")
    boost_thai_matches: float = Field(default=1.5, ge=1.0, le=3.0, description="Boost factor for Thai tokenized matches")
    boost_compound_matches: float = Field(default=1.3, ge=1.0, le=3.0, description="Boost factor for compound word matches")
    decay_factor: float = Field(default=0.1, ge=0.0, le=1.0, description="Score decay factor for lower-ranked results")
    min_score_threshold: float = Field(default=0.1, ge=0.0, le=1.0, description="Minimum score threshold for results")
    max_results_per_variant: int = Field(default=100, ge=10, le=1000, description="Maximum results per query variant")
    enable_score_normalization: bool = Field(default=True, description="Enable score normalization across variants")
    
    class Config:
        json_schema_extra = {
            "example": {
                "algorithm": "optimized_score",
                "boost_exact_matches": 1.8,
                "boost_thai_matches": 1.3,
                "decay_factor": 0.05,
                "min_score_threshold": 0.2
            }
        }


class PerformanceConfig(BaseModel):
    """Configuration for performance monitoring and limits."""
    
    enable_metrics: bool = Field(default=True, description="Enable performance metrics collection")
    enable_detailed_logging: bool = Field(default=False, description="Enable detailed operation logging")
    max_query_length: int = Field(default=1000, ge=1, le=10000, description="Maximum allowed query length")
    max_batch_size: int = Field(default=50, ge=1, le=100, description="Maximum batch search size")
    memory_limit_mb: int = Field(default=256, ge=64, le=2048, description="Memory limit in MB")
    cache_enabled: bool = Field(default=True, description="Enable result caching")
    cache_ttl_seconds: int = Field(default=300, ge=60, le=3600, description="Cache TTL in seconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "enable_metrics": True,
                "max_query_length": 500,
                "max_batch_size": 25,
                "memory_limit_mb": 128,
                "cache_enabled": True
            }
        }


class SearchProxySettings(BaseSettings):
    """Main configuration settings for the search proxy service."""
    
    # Service identification
    service_name: str = Field(default="thai-search-proxy", description="Service name")
    service_version: str = Field(default="1.0.0", description="Service version")
    environment: str = Field(default="development", description="Deployment environment")
    
    # Component configurations
    tokenization: TokenizationConfig = Field(default_factory=TokenizationConfig, description="Tokenization settings")
    search: SearchConfig = Field(default_factory=SearchConfig, description="Search execution settings")
    ranking: RankingConfig = Field(default_factory=RankingConfig, description="Result ranking settings")
    performance: PerformanceConfig = Field(default_factory=PerformanceConfig, description="Performance settings")
    
    # External service configurations
    meilisearch_url: str = Field(default="http://localhost:7700", description="Meilisearch server URL")
    meilisearch_api_key: Optional[str] = Field(default=None, description="Meilisearch API key")
    meilisearch_timeout_ms: int = Field(default=30000, ge=1000, le=120000, description="Meilisearch timeout")
    
    # Logging and monitoring
    log_level: str = Field(default="INFO", description="Logging level")
    enable_structured_logging: bool = Field(default=True, description="Enable structured JSON logging")
    enable_health_checks: bool = Field(default=True, description="Enable health check endpoints")
    health_check_interval_seconds: int = Field(default=30, ge=10, le=300, description="Health check interval")
    
    # Feature flags
    enable_experimental_features: bool = Field(default=False, description="Enable experimental features")
    enable_a_b_testing: bool = Field(default=False, description="Enable A/B testing for ranking algorithms")
    
    class Config:
        env_prefix = "SEARCH_PROXY_"
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        
        json_schema_extra = {
            "example": {
                "service_name": "thai-search-proxy",
                "environment": "production",
                "tokenization": {
                    "primary_engine": "newmm",
                    "timeout_ms": 3000
                },
                "search": {
                    "max_concurrent_searches": 10,
                    "timeout_ms": 5000
                },
                "ranking": {
                    "algorithm": "optimized_score",
                    "boost_exact_matches": 1.8
                },
                "meilisearch_url": "http://meilisearch:7700",
                "log_level": "INFO"
            }
        }


# Environment-specific configuration presets
def get_development_settings() -> SearchProxySettings:
    """Get configuration optimized for development environment."""
    return SearchProxySettings(
        environment="development",
        tokenization=TokenizationConfig(
            timeout_ms=5000,
            confidence_threshold=0.7
        ),
        search=SearchConfig(
            max_concurrent_searches=3,
            timeout_ms=10000,
            retry_attempts=1
        ),
        ranking=RankingConfig(
            algorithm="weighted_score",
            boost_exact_matches=2.0
        ),
        performance=PerformanceConfig(
            enable_detailed_logging=True,
            max_batch_size=10,
            cache_ttl_seconds=60
        ),
        log_level="DEBUG"
    )


def get_production_settings() -> SearchProxySettings:
    """Get configuration optimized for production environment."""
    return SearchProxySettings(
        environment="production",
        tokenization=TokenizationConfig(
            timeout_ms=3000,
            confidence_threshold=0.8,
            fallback_engines=["attacut"]  # Fewer fallbacks for performance
        ),
        search=SearchConfig(
            max_concurrent_searches=10,
            timeout_ms=5000,
            retry_attempts=2
        ),
        ranking=RankingConfig(
            algorithm="optimized_score",
            boost_exact_matches=1.8,
            boost_thai_matches=1.3
        ),
        performance=PerformanceConfig(
            enable_detailed_logging=False,
            max_batch_size=50,
            memory_limit_mb=256,
            cache_ttl_seconds=300
        ),
        log_level="INFO"
    )