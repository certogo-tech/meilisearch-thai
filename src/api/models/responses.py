"""Response models for the Thai tokenizer API."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime


class TokenizationResult(BaseModel):
    """Response model for tokenization results."""
    original_text: str = Field(..., description="Original input text")
    tokens: List[str] = Field(..., description="Segmented tokens")
    word_boundaries: List[int] = Field(..., description="Word boundary positions")
    confidence_scores: Optional[List[float]] = Field(None, description="Confidence scores per token")
    processing_time_ms: int = Field(..., description="Processing time in milliseconds")


class DocumentProcessingResult(BaseModel):
    """Response model for document processing."""
    document_id: str = Field(..., description="Document ID")
    status: str = Field(..., description="Processing status")
    tokenized_fields: Dict[str, TokenizationResult] = Field(..., description="Tokenized field results")
    indexed_at: datetime = Field(..., description="Indexing timestamp")


class HealthCheckResponse(BaseModel):
    """Response model for health check."""
    status: str = Field(..., description="Service status")
    version: str = Field(..., description="Service version")
    uptime_seconds: int = Field(..., description="Service uptime")
    dependencies: Dict[str, str] = Field(..., description="Dependency status")


class ConfigurationResponse(BaseModel):
    """Response model for configuration status."""
    status: str = Field(..., description="Configuration status")
    message: str = Field(..., description="Status message")
    applied_at: datetime = Field(..., description="Configuration applied timestamp")


class QueryToken(BaseModel):
    """Response model for processed query tokens."""
    original: str = Field(..., description="Original token")
    processed: str = Field(..., description="Processed token for search")
    query_type: str = Field(..., description="Query type classification")
    is_partial: bool = Field(False, description="Whether token appears partial")
    compound_parts: Optional[List[str]] = Field(None, description="Compound word parts")
    search_variants: Optional[List[str]] = Field(None, description="Search variants")
    boost_score: float = Field(1.0, description="Relevance boost score")


class QueryProcessingResult(BaseModel):
    """Response model for query processing results."""
    original_query: str = Field(..., description="Original search query")
    processed_query: str = Field(..., description="Processed query for MeiliSearch")
    query_tokens: List[QueryToken] = Field(..., description="Processed query tokens")
    search_variants: List[str] = Field(..., description="Alternative search variants")
    suggested_completions: List[str] = Field(..., description="Query completion suggestions")
    processing_metadata: Dict[str, Any] = Field(..., description="Processing metadata")


class HighlightSpan(BaseModel):
    """Response model for highlighted spans in search results."""
    start: int = Field(..., description="Start position of highlight")
    end: int = Field(..., description="End position of highlight")
    text: str = Field(..., description="Highlighted text")
    highlight_type: str = Field(..., description="Type of highlighting")
    confidence: float = Field(..., description="Confidence score")
    matched_query: Optional[str] = Field(None, description="Query that matched this span")


class EnhancedSearchHit(BaseModel):
    """Response model for enhanced search result hit."""
    original_hit: Dict[str, Any] = Field(..., description="Original search hit")
    enhanced_score: float = Field(..., description="Enhanced relevance score")
    highlight_spans: List[HighlightSpan] = Field(..., description="Enhanced highlight spans")
    compound_matches: List[str] = Field(..., description="Compound word matches found")
    original_text_preserved: Dict[str, str] = Field(..., description="Original text for each field")
    tokenized_text: Dict[str, str] = Field(..., description="Tokenized text for each field")
    relevance_factors: Dict[str, float] = Field(..., description="Detailed relevance factors")


class SearchResultEnhancementResult(BaseModel):
    """Response model for search result enhancement."""
    original_results: Dict[str, Any] = Field(..., description="Original search results")
    enhanced_hits: List[EnhancedSearchHit] = Field(..., description="Enhanced search hits")
    query_analysis: Dict[str, Any] = Field(..., description="Query analysis results")
    enhancement_metadata: Dict[str, Any] = Field(..., description="Enhancement metadata")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }


class ErrorResponse(BaseModel):
    """Response model for errors."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(..., description="Error timestamp")
    
    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }