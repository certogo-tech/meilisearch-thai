"""
Query processing models for the search proxy service.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, model_validator


class QueryVariantType(str, Enum):
    """Types of query variants that can be generated."""
    
    ORIGINAL = "original"
    TOKENIZED = "tokenized"
    COMPOUND_SPLIT = "compound_split"
    FALLBACK = "fallback"
    MIXED_LANGUAGE = "mixed_language"


class TokenizationResult(BaseModel):
    """Result of text tokenization."""
    
    engine: str = Field(..., min_length=1, description="Tokenization engine used")
    tokens: List[str] = Field(..., description="Generated tokens")
    processing_time_ms: float = Field(..., ge=0.0, description="Time spent tokenizing")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in tokenization quality")
    success: bool = Field(..., description="Whether tokenization was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if tokenization failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "engine": "newmm",
                "tokens": ["ค้นหา", "เอกสาร", "ภาษาไทย"],
                "processing_time_ms": 15.2,
                "confidence": 0.95,
                "success": True,
                "error_message": None
            }
        }
    
    @model_validator(mode='after')
    def validate_tokenization_result(self):
        """Validate model after initialization."""
        if self.success and not self.tokens:
            raise ValueError("Successful tokenization must have tokens")
        if not self.success and self.error_message is None:
            raise ValueError("Failed tokenization must have error message")
        return self
    
    @property
    def token_count(self) -> int:
        """Get the number of tokens."""
        return len(self.tokens)
    
    @property
    def is_high_confidence(self) -> bool:
        """Check if tokenization has high confidence (>= 0.8)."""
        return self.confidence >= 0.8
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary for logging."""
        return {
            "engine": self.engine,
            "token_count": self.token_count,
            "processing_time_ms": self.processing_time_ms,
            "confidence": self.confidence,
            "success": self.success
        }


class QueryVariant(BaseModel):
    """A variant of the original query for search execution."""
    
    query_text: str = Field(..., min_length=1, max_length=1000, description="The query text for this variant")
    variant_type: QueryVariantType = Field(..., description="Type of query variant")
    tokenization_engine: str = Field(..., min_length=1, description="Tokenization engine used")
    weight: float = Field(..., ge=0.0, le=1.0, description="Weight for result ranking")
    search_options: Dict[str, Any] = Field(default_factory=dict, description="Meilisearch-specific options")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional variant metadata")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query_text": "ค้นหา เอกสาร",
                "variant_type": "tokenized",
                "tokenization_engine": "newmm",
                "weight": 0.9,
                "search_options": {"matching_strategy": "last"},
                "metadata": {"token_count": 2}
            }
        }
    
    @model_validator(mode='after')
    def validate_query_variant(self):
        """Validate model after initialization."""
        # Ensure query text is not just whitespace
        if not self.query_text.strip():
            raise ValueError("Query text cannot be empty or whitespace only")
        return self
    
    @property
    def is_original(self) -> bool:
        """Check if this is the original query variant."""
        return self.variant_type == QueryVariantType.ORIGINAL
    
    @property
    def is_tokenized(self) -> bool:
        """Check if this is a tokenized variant."""
        return self.variant_type in [
            QueryVariantType.TOKENIZED, 
            QueryVariantType.COMPOUND_SPLIT,
            QueryVariantType.MIXED_LANGUAGE
        ]
    
    @property
    def is_fallback(self) -> bool:
        """Check if this is a fallback variant."""
        return self.variant_type == QueryVariantType.FALLBACK
    
    @property
    def is_high_weight(self) -> bool:
        """Check if this variant has high weight (>= 0.8)."""
        return self.weight >= 0.8
    
    def to_search_dict(self) -> Dict[str, Any]:
        """Convert to dictionary suitable for search execution."""
        return {
            "query": self.query_text,
            "weight": self.weight,
            "options": self.search_options,
            "variant_type": self.variant_type.value,
            "engine": self.tokenization_engine
        }
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary for logging."""
        return {
            "variant_type": self.variant_type.value,
            "tokenization_engine": self.tokenization_engine,
            "weight": self.weight,
            "query_length": len(self.query_text),
            "has_search_options": bool(self.search_options),
            "metadata_keys": list(self.metadata.keys())
        }


class ProcessedQuery(BaseModel):
    """Complete result of query processing."""
    
    original_query: str = Field(..., min_length=1, max_length=1000, description="Original search query")
    tokenization_results: List[TokenizationResult] = Field(..., description="Results from different tokenization engines")
    query_variants: List[QueryVariant] = Field(..., min_items=1, description="Generated query variants for search")
    processing_time_ms: float = Field(..., ge=0.0, description="Total query processing time")
    thai_content_detected: bool = Field(..., description="Whether Thai content was detected")
    mixed_content: bool = Field(..., description="Whether mixed Thai-English content was detected")
    primary_language: str = Field(..., description="Primary language detected in query")
    fallback_used: bool = Field(default=False, description="Whether fallback processing was used")
    
    class Config:
        json_schema_extra = {
            "example": {
                "original_query": "ค้นหาเอกสารภาษาไทย",
                "tokenization_results": [
                    {
                        "engine": "newmm",
                        "tokens": ["ค้นหา", "เอกสาร", "ภาษาไทย"],
                        "processing_time_ms": 15.2,
                        "confidence": 0.95,
                        "success": True
                    }
                ],
                "query_variants": [
                    {
                        "query_text": "ค้นหาเอกสารภาษาไทย",
                        "variant_type": "original",
                        "tokenization_engine": "none",
                        "weight": 0.8
                    },
                    {
                        "query_text": "ค้นหา เอกสาร ภาษาไทย",
                        "variant_type": "tokenized",
                        "tokenization_engine": "newmm",
                        "weight": 1.0
                    }
                ],
                "processing_time_ms": 25.7,
                "thai_content_detected": True,
                "mixed_content": False,
                "primary_language": "thai"
            }
        }
    
    @model_validator(mode='after')
    def validate_processed_query(self):
        """Validate model after initialization."""
        # Ensure original query is not just whitespace
        if not self.original_query.strip():
            raise ValueError("Original query cannot be empty or whitespace only")
        
        # Ensure at least one query variant exists
        if not self.query_variants:
            raise ValueError("At least one query variant must be provided")
        
        # Validate primary language
        valid_languages = ["thai", "english", "mixed", "unknown"]
        if self.primary_language not in valid_languages:
            raise ValueError(f"Primary language must be one of: {valid_languages}")
        
        return self
    
    @property
    def successful_tokenizations(self) -> List[TokenizationResult]:
        """Get only successful tokenization results."""
        return [result for result in self.tokenization_results if result.success]
    
    @property
    def failed_tokenizations(self) -> List[TokenizationResult]:
        """Get only failed tokenization results."""
        return [result for result in self.tokenization_results if not result.success]
    
    @property
    def high_confidence_tokenizations(self) -> List[TokenizationResult]:
        """Get tokenization results with high confidence (>= 0.8)."""
        return [result for result in self.tokenization_results if result.is_high_confidence]
    
    @property
    def original_variants(self) -> List[QueryVariant]:
        """Get original query variants."""
        return [variant for variant in self.query_variants if variant.is_original]
    
    @property
    def tokenized_variants(self) -> List[QueryVariant]:
        """Get tokenized query variants."""
        return [variant for variant in self.query_variants if variant.is_tokenized]
    
    @property
    def fallback_variants(self) -> List[QueryVariant]:
        """Get fallback query variants."""
        return [variant for variant in self.query_variants if variant.is_fallback]
    
    @property
    def high_weight_variants(self) -> List[QueryVariant]:
        """Get high-weight query variants (>= 0.8)."""
        return [variant for variant in self.query_variants if variant.is_high_weight]
    
    @property
    def total_tokenization_time(self) -> float:
        """Get total time spent on tokenization."""
        return sum(result.processing_time_ms for result in self.tokenization_results)
    
    @property
    def average_tokenization_confidence(self) -> float:
        """Get average confidence across successful tokenizations."""
        successful = self.successful_tokenizations
        if not successful:
            return 0.0
        return sum(result.confidence for result in successful) / len(successful)
    
    def get_best_variant(self) -> QueryVariant:
        """Get the query variant with the highest weight."""
        return max(self.query_variants, key=lambda v: v.weight)
    
    def get_variants_by_type(self, variant_type: QueryVariantType) -> List[QueryVariant]:
        """Get query variants of a specific type."""
        return [variant for variant in self.query_variants if variant.variant_type == variant_type]
    
    def to_search_execution_data(self) -> List[Dict[str, Any]]:
        """Convert to data structure suitable for search execution."""
        return [variant.to_search_dict() for variant in self.query_variants]
    
    def to_summary_dict(self) -> Dict[str, Any]:
        """Convert to summary dictionary for logging and monitoring."""
        return {
            "original_query_length": len(self.original_query),
            "processing_time_ms": self.processing_time_ms,
            "thai_content_detected": self.thai_content_detected,
            "mixed_content": self.mixed_content,
            "primary_language": self.primary_language,
            "fallback_used": self.fallback_used,
            "tokenization_results_count": len(self.tokenization_results),
            "successful_tokenizations": len(self.successful_tokenizations),
            "failed_tokenizations": len(self.failed_tokenizations),
            "high_confidence_tokenizations": len(self.high_confidence_tokenizations),
            "query_variants_count": len(self.query_variants),
            "original_variants": len(self.original_variants),
            "tokenized_variants": len(self.tokenized_variants),
            "fallback_variants": len(self.fallback_variants),
            "high_weight_variants": len(self.high_weight_variants),
            "total_tokenization_time": self.total_tokenization_time,
            "average_confidence": self.average_tokenization_confidence,
            "best_variant_weight": self.get_best_variant().weight,
            "engines_used": list(set(result.engine for result in self.tokenization_results))
        }