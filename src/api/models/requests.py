"""Request models for the Thai tokenizer API."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class TokenizeRequest(BaseModel):
    """Request model for text tokenization."""
    text: str = Field(..., description="Thai text to tokenize")
    include_confidence: bool = Field(False, description="Include confidence scores")


class IndexDocumentRequest(BaseModel):
    """Request model for document indexing."""
    id: str = Field(..., description="Document ID")
    title: str = Field(..., description="Document title")
    content: str = Field(..., description="Document content")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")


class MeiliSearchConfigRequest(BaseModel):
    """Request model for MeiliSearch configuration."""
    host: str = Field(..., description="MeiliSearch host URL")
    api_key: str = Field(..., description="MeiliSearch API key")
    index_name: str = Field(..., description="Index name")


class TokenizerConfigRequest(BaseModel):
    """Request model for tokenizer configuration."""
    engine: str = Field("newmm", description="Tokenization engine (pythainlp, newmm, attacut, deepcut)")
    model_version: Optional[str] = Field(None, description="Model version")
    custom_dictionary: Optional[List[str]] = Field(None, description="Custom dictionary words")
    keep_whitespace: bool = Field(True, description="Whether to preserve whitespace in tokenization")
    handle_compounds: bool = Field(True, description="Whether to apply compound word processing")
    fallback_engine: Optional[str] = Field("newmm", description="Fallback engine if primary fails")
    batch_size: int = Field(100, description="Batch processing size")
    max_retries: int = Field(3, description="Maximum retry attempts")
    timeout_ms: int = Field(5000, description="Timeout in milliseconds")


class QueryProcessingRequest(BaseModel):
    """Request model for search query processing."""
    query: str = Field(..., description="Search query to process")
    enable_partial_matching: bool = Field(True, description="Enable partial compound word matching")
    enable_query_expansion: bool = Field(True, description="Enable query expansion with variants")
    include_suggestions: bool = Field(False, description="Include completion suggestions")
    max_suggestions: int = Field(10, description="Maximum number of suggestions to return")


class SearchResultEnhancementRequest(BaseModel):
    """Request model for search result enhancement."""
    search_results: Dict[str, Any] = Field(..., description="Raw search results from MeiliSearch")
    original_query: str = Field(..., description="Original search query")
    highlight_fields: Optional[List[str]] = Field(None, description="Fields to enhance highlighting for")
    enable_compound_highlighting: bool = Field(True, description="Enable compound word highlighting")
    enable_relevance_boosting: bool = Field(True, description="Enable relevance score boosting")