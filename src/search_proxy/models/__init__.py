"""
Search proxy data models and interfaces.
"""

from .requests import SearchRequest, BatchSearchRequest, SearchOptions
from .responses import SearchResponse, SearchHit, QueryInfo, PaginationInfo, TokenizationInfo
from .query import ProcessedQuery, QueryVariant, QueryVariantType, TokenizationResult
from .search import SearchResult, RankedResults, QueryContext

__all__ = [
    # Request models
    "SearchRequest",
    "BatchSearchRequest", 
    "SearchOptions",
    
    # Response models
    "SearchResponse",
    "SearchHit",
    "QueryInfo",
    "PaginationInfo",
    "TokenizationInfo",
    
    # Query processing models
    "ProcessedQuery",
    "QueryVariant",
    "QueryVariantType",
    "TokenizationResult",
    
    # Search execution models
    "SearchResult",
    "RankedResults",
    "QueryContext",
]