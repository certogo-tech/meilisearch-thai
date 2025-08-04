"""
Request models for the search proxy service.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, validator


class SearchOptions(BaseModel):
    """Configuration options for search operations."""
    
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of results to return")
    offset: int = Field(default=0, ge=0, description="Number of results to skip")
    filters: Optional[Dict[str, Any]] = Field(default=None, description="Meilisearch filters to apply")
    sort: Optional[List[str]] = Field(default=None, description="Sort criteria")
    highlight: bool = Field(default=True, description="Enable result highlighting")
    attributes_to_retrieve: Optional[List[str]] = Field(default=None, description="Specific attributes to retrieve")
    attributes_to_highlight: Optional[List[str]] = Field(default=None, description="Attributes to highlight")
    crop_length: int = Field(default=200, ge=10, le=1000, description="Length of text crops in highlights")
    crop_marker: str = Field(default="...", description="Marker for cropped text")
    matching_strategy: str = Field(default="last", description="Meilisearch matching strategy")
    
    # Thai-specific search options
    force_tokenization: bool = Field(default=False, description="Force tokenization even for non-Thai content")
    tokenization_engine: Optional[str] = Field(default=None, description="Preferred tokenization engine (newmm, attacut, deepcut)")
    enable_compound_search: bool = Field(default=True, description="Enable compound word search variants")
    boost_exact_matches: float = Field(default=1.5, ge=0.1, le=5.0, description="Score boost for exact matches")
    boost_thai_matches: float = Field(default=1.2, ge=0.1, le=5.0, description="Score boost for Thai tokenized matches")
    
    # Performance options
    max_query_variants: int = Field(default=5, ge=1, le=10, description="Maximum number of query variants to generate")
    search_timeout_ms: int = Field(default=5000, ge=100, le=30000, description="Search timeout in milliseconds")
    
    class Config:
        json_schema_extra = {
            "example": {
                "limit": 20,
                "offset": 0,
                "highlight": True,
                "force_tokenization": False,
                "tokenization_engine": "newmm",
                "enable_compound_search": True,
                "boost_exact_matches": 1.5,
                "boost_thai_matches": 1.2,
                "max_query_variants": 5,
                "search_timeout_ms": 5000
            }
        }


class SearchRequest(BaseModel):
    """Request model for single search operations."""
    
    query: str = Field(..., min_length=1, max_length=1000, description="Search query text")
    index_name: str = Field(..., min_length=1, max_length=100, description="Target Meilisearch index")
    options: SearchOptions = Field(default_factory=SearchOptions, description="Search configuration options")
    include_tokenization_info: bool = Field(default=False, description="Include tokenization details in response")
    
    @validator('query')
    def validate_query(cls, v):
        """Validate query text."""
        if not v or not v.strip():
            raise ValueError("Query cannot be empty or whitespace only")
        return v.strip()
    
    @validator('index_name')
    def validate_index_name(cls, v):
        """Validate index name format."""
        if not v or not v.strip():
            raise ValueError("Index name cannot be empty")
        
        # Basic validation for Meilisearch index name format
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
            raise ValueError("Index name can only contain letters, numbers, underscores, and hyphens")
        
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "ค้นหาเอกสารภาษาไทย",
                "index_name": "documents",
                "options": {
                    "limit": 10,
                    "highlight": True,
                    "tokenization_engine": "newmm",
                    "boost_thai_matches": 1.2
                },
                "include_tokenization_info": False
            }
        }


class BatchSearchRequest(BaseModel):
    """Request model for batch search operations."""
    
    queries: List[str] = Field(..., min_items=1, max_items=50, description="List of search queries")
    index_name: str = Field(..., min_length=1, max_length=100, description="Target Meilisearch index")
    options: SearchOptions = Field(default_factory=SearchOptions, description="Search configuration options")
    include_tokenization_info: bool = Field(default=False, description="Include tokenization details in responses")
    
    @validator('queries')
    def validate_queries(cls, v):
        """Validate all queries in the batch."""
        if not v:
            raise ValueError("Queries list cannot be empty")
        
        validated_queries = []
        for i, query in enumerate(v):
            if not query or not query.strip():
                raise ValueError(f"Query {i+1} cannot be empty or whitespace only")
            
            if len(query.strip()) > 1000:
                raise ValueError(f"Query {i+1} is too long (max 1000 characters)")
            
            validated_queries.append(query.strip())
        
        return validated_queries
    
    @validator('index_name')
    def validate_index_name(cls, v):
        """Validate index name format."""
        if not v or not v.strip():
            raise ValueError("Index name cannot be empty")
        
        # Basic validation for Meilisearch index name format
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', v.strip()):
            raise ValueError("Index name can only contain letters, numbers, underscores, and hyphens")
        
        return v.strip()
    
    class Config:
        json_schema_extra = {
            "example": {
                "queries": ["ค้นหาเอกสาร", "Thai document search", "การค้นหาข้อมูล"],
                "index_name": "documents",
                "options": {
                    "limit": 5,
                    "highlight": True,
                    "tokenization_engine": "newmm",
                    "enable_compound_search": True
                },
                "include_tokenization_info": True
            }
        }