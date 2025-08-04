"""
Search execution models for the search proxy service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from .query import QueryVariant
from .responses import SearchHit


class SearchResult(BaseModel):
    """Result from a single search execution."""
    
    query_variant: QueryVariant = Field(..., description="Query variant used for this search")
    hits: List[SearchHit] = Field(..., description="Search result hits")
    total_hits: int = Field(..., ge=0, description="Total matching documents")
    processing_time_ms: float = Field(..., description="Search execution time")
    success: bool = Field(..., description="Whether search was successful")
    error_message: Optional[str] = Field(default=None, description="Error message if search failed")
    meilisearch_metadata: Dict[str, Any] = Field(default_factory=dict, description="Raw Meilisearch response metadata")


class QueryContext(BaseModel):
    """Context information for query processing and ranking."""
    
    original_query: str = Field(..., description="Original search query")
    processed_query: str = Field(..., description="Final processed query")
    thai_content_ratio: float = Field(..., ge=0.0, le=1.0, description="Ratio of Thai content in query")
    mixed_content: bool = Field(default=False, description="Whether query contains mixed Thai-English content")
    primary_language: str = Field(..., description="Primary language detected")
    query_length: int = Field(..., ge=0, description="Length of original query")
    tokenization_confidence: float = Field(..., ge=0.0, le=1.0, description="Average tokenization confidence")
    variant_count: int = Field(..., ge=1, description="Number of query variants generated")
    processing_time_ms: float = Field(..., ge=0.0, description="Query processing time")
    search_intent: Optional[str] = Field(default=None, description="Detected search intent")


class RankingMetadata(BaseModel):
    """Metadata about result ranking calculations."""
    
    base_score: float = Field(..., description="Original Meilisearch score")
    thai_boost: float = Field(default=1.0, description="Thai content boost factor")
    exact_match_boost: float = Field(default=1.0, description="Exact match boost factor")
    tokenization_boost: float = Field(default=1.0, description="Tokenization quality boost")
    final_score: float = Field(..., description="Final calculated relevance score")
    ranking_factors: Dict[str, float] = Field(default_factory=dict, description="Individual ranking factor contributions")


class RankedResults(BaseModel):
    """Final ranked and merged search results."""
    
    hits: List[SearchHit] = Field(..., description="Ranked search result hits")
    total_unique_hits: int = Field(..., ge=0, description="Total unique documents found")
    deduplication_count: int = Field(..., ge=0, description="Number of duplicate results removed")
    ranking_time_ms: float = Field(..., description="Time spent ranking results")
    ranking_algorithm: str = Field(..., description="Ranking algorithm used")
    query_context: QueryContext = Field(..., description="Query processing context")
    
    class Config:
        json_schema_extra = {
            "example": {
                "hits": [
                    {
                        "id": "doc_1",
                        "score": 0.95,
                        "document": {"title": "Thai Document"},
                        "ranking_info": {
                            "base_score": 0.8,
                            "thai_boost": 1.2,
                            "final_score": 0.95
                        }
                    }
                ],
                "total_unique_hits": 42,
                "deduplication_count": 3,
                "ranking_time_ms": 12.5,
                "ranking_algorithm": "weighted_score"
            }
        }