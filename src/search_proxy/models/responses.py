"""
Response models for the search proxy service.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SearchHit(BaseModel):
    """Individual search result hit."""
    
    id: str = Field(..., description="Document ID")
    score: float = Field(..., description="Relevance score")
    document: Dict[str, Any] = Field(..., description="Document content")
    highlight: Optional[Dict[str, Any]] = Field(default=None, description="Highlighted text snippets")
    ranking_info: Optional[Dict[str, Any]] = Field(default=None, description="Ranking calculation details")
    
    # Additional hit metadata
    match_type: Optional[str] = Field(default=None, description="Type of match (exact, tokenized, compound)")
    query_variant_source: Optional[str] = Field(default=None, description="Which query variant produced this hit")
    original_meilisearch_score: Optional[float] = Field(default=None, description="Original Meilisearch relevance score")
    thai_content_ratio: Optional[float] = Field(default=None, ge=0.0, le=1.0, description="Ratio of Thai content in document")
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "doc_123",
                "score": 0.95,
                "document": {
                    "title": "Thai Document Example",
                    "content": "เอกสารภาษาไทยตัวอย่าง"
                },
                "highlight": {
                    "content": ["<em>เอกสาร</em>ภาษาไทยตัวอย่าง"]
                },
                "ranking_info": {
                    "base_score": 0.85,
                    "thai_boost": 0.1,
                    "exact_match_boost": 0.0
                },
                "match_type": "tokenized",
                "query_variant_source": "newmm_tokenized",
                "original_meilisearch_score": 0.85,
                "thai_content_ratio": 0.9
            }
        }


class QueryInfo(BaseModel):
    """Information about query processing."""
    
    original_query: str = Field(..., description="Original search query")
    processed_query: str = Field(..., description="Final processed query")
    thai_content_detected: bool = Field(..., description="Whether Thai content was detected")
    mixed_content: bool = Field(..., description="Whether mixed Thai-English content was detected")
    query_variants_used: int = Field(..., description="Number of query variants generated")
    fallback_used: bool = Field(default=False, description="Whether fallback tokenization was used")


class TokenizationInfo(BaseModel):
    """Detailed tokenization information for debugging."""
    
    tokenization_engine: str = Field(..., description="Primary tokenization engine used")
    tokenization_time_ms: float = Field(..., description="Time spent on tokenization")
    tokens: List[str] = Field(..., description="Generated tokens")
    fallback_engines_used: List[str] = Field(default_factory=list, description="Fallback engines used")
    tokenization_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in tokenization quality")
    
    # Additional debugging information
    original_text_length: int = Field(..., ge=0, description="Length of original text")
    token_count: int = Field(..., ge=0, description="Number of tokens generated")
    average_token_length: float = Field(..., ge=0.0, description="Average length of tokens")
    compound_words_detected: int = Field(default=0, ge=0, description="Number of compound words detected")
    mixed_language_segments: int = Field(default=0, ge=0, description="Number of mixed language segments")
    
    # Engine-specific details
    engine_details: Optional[Dict[str, Any]] = Field(default=None, description="Engine-specific tokenization details")
    alternative_tokenizations: Optional[List[Dict[str, Any]]] = Field(default=None, description="Alternative tokenization results")
    
    class Config:
        json_schema_extra = {
            "example": {
                "tokenization_engine": "newmm",
                "tokenization_time_ms": 12.5,
                "tokens": ["ค้นหา", "เอกสาร", "ภาษาไทย"],
                "fallback_engines_used": [],
                "tokenization_confidence": 0.95,
                "original_text_length": 20,
                "token_count": 3,
                "average_token_length": 6.67,
                "compound_words_detected": 1,
                "mixed_language_segments": 0,
                "engine_details": {
                    "dictionary_matches": 2,
                    "unknown_words": 0
                }
            }
        }


class PaginationInfo(BaseModel):
    """Pagination information for search results."""
    
    offset: int = Field(..., ge=0, description="Current offset")
    limit: int = Field(..., ge=1, description="Results per page")
    total_hits: int = Field(..., ge=0, description="Total number of matching documents")
    has_next_page: bool = Field(..., description="Whether more results are available")
    has_previous_page: bool = Field(..., description="Whether previous results exist")


class SearchResponse(BaseModel):
    """Response model for search operations."""
    
    hits: List[SearchHit] = Field(..., description="Search result hits")
    total_hits: int = Field(..., ge=0, description="Total number of matching documents")
    processing_time_ms: float = Field(..., description="Total processing time")
    query_info: QueryInfo = Field(..., description="Query processing information")
    pagination: PaginationInfo = Field(..., description="Pagination details")
    tokenization_info: Optional[TokenizationInfo] = Field(default=None, description="Tokenization details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Response timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "hits": [
                    {
                        "id": "doc_1",
                        "score": 0.95,
                        "document": {"title": "Thai Document", "content": "เอกสารภาษาไทย"},
                        "highlights": {"content": ["<em>เอกสาร</em>ภาษาไทย"]}
                    }
                ],
                "total_hits": 42,
                "processing_time_ms": 87.5,
                "query_info": {
                    "original_query": "ค้นหาเอกสาร",
                    "processed_query": "ค้นหา เอกสาร",
                    "thai_content_detected": True,
                    "mixed_content": False,
                    "query_variants_used": 3
                },
                "pagination": {
                    "offset": 0,
                    "limit": 20,
                    "total_hits": 42,
                    "has_next_page": True,
                    "has_previous_page": False
                }
            }
        }


class SearchErrorResponse(BaseModel):
    """Error response model for search operations."""
    
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    fallback_used: bool = Field(default=False, description="Whether fallback processing was attempted")
    partial_results: Optional[List[SearchHit]] = Field(default=None, description="Partial results if available")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    
    class Config:
        json_schema_extra = {
            "example": {
                "error": "TOKENIZATION_FAILED",
                "message": "Thai tokenization failed, using fallback search",
                "fallback_used": True,
                "partial_results": []
            }
        }