"""
Query tokenization service for Thai search queries.

This module provides specialized processing for Thai search queries,
handling partial compound word searches and maintaining search intent.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Set, Tuple
from dataclasses import dataclass
from enum import Enum

from .thai_segmenter import ThaiSegmenter, TokenizationResult
from .token_processor import TokenProcessor, ContentType
from ..utils.logging import get_structured_logger, SearchMetrics, performance_monitor


logger = get_structured_logger(__name__)


class QueryType(Enum):
    """Search query type classification."""
    SIMPLE = "simple"
    COMPOUND = "compound"
    PARTIAL = "partial"
    MIXED = "mixed"
    PHRASE = "phrase"


@dataclass
class QueryToken:
    """Processed query token with search metadata."""
    
    original: str
    processed: str
    query_type: QueryType
    is_partial: bool = False
    compound_parts: Optional[List[str]] = None
    search_variants: Optional[List[str]] = None
    boost_score: float = 1.0


@dataclass
class QueryProcessingResult:
    """Result of query processing for search optimization."""
    
    original_query: str
    processed_query: str
    query_tokens: List[QueryToken]
    search_variants: List[str]
    suggested_completions: List[str]
    processing_metadata: Dict[str, Any]


class QueryProcessor:
    """
    Processes Thai search queries for optimal search results.
    
    Handles partial compound word searches, query expansion,
    and search intent preservation.
    """
    
    def __init__(
        self,
        thai_segmenter: Optional[ThaiSegmenter] = None,
        token_processor: Optional[TokenProcessor] = None,
        enable_query_expansion: bool = True,
        enable_partial_matching: bool = True
    ):
        """
        Initialize query processor.
        
        Args:
            thai_segmenter: Thai segmentation engine
            token_processor: Token processing utilities
            enable_query_expansion: Whether to expand queries with variants
            enable_partial_matching: Whether to support partial matching
        """
        self.thai_segmenter = thai_segmenter or ThaiSegmenter()
        self.token_processor = token_processor or TokenProcessor()
        self.enable_query_expansion = enable_query_expansion
        self.enable_partial_matching = enable_partial_matching
        
        # Common Thai compound word patterns for partial matching
        self.compound_patterns = [
            r'การ(.+)',  # การ + word
            r'(.+)ความ(.+)',  # word + ความ + word
            r'(.+)โรง(.+)',  # word + โรง + word
            r'(.+)ศาสตร์',  # word + ศาสตร์
            r'(.+)วิทยา',  # word + วิทยา
            r'(.+)กรรม',  # word + กรรม
            r'(.+)ภาพ',  # word + ภาพ
        ]
        
        # Common Thai prefixes and suffixes for expansion
        self.thai_prefixes = ['การ', 'ความ', 'นัก', 'ผู้', 'คน', 'เจ้า']
        self.thai_suffixes = ['ศาสตร์', 'วิทยา', 'กรรม', 'ภาพ', 'การ', 'ความ']
        
        logger.info("QueryProcessor initialized")
    
    @performance_monitor("search_query_processing")
    def process_search_query(self, query: str) -> QueryProcessingResult:
        """
        Process search query for optimal Thai text matching.
        
        Args:
            query: Search query string
            
        Returns:
            QueryProcessingResult with processed query and variants
        """
        if not query or not query.strip():
            logger.debug("Empty query received")
            return QueryProcessingResult(
                original_query=query,
                processed_query=query,
                query_tokens=[],
                search_variants=[],
                suggested_completions=[],
                processing_metadata={"empty_query": True}
            )
        
        # Clean and normalize query
        normalized_query = self._normalize_query(query)
        
        # Tokenize the query
        tokenization_result = self.thai_segmenter.segment_text(normalized_query)
        
        # Process each token for search optimization
        query_tokens = []
        search_variants = set()
        suggested_completions = set()
        
        for token in tokenization_result.tokens:
            if not token.strip():
                continue
                
            query_token = self._process_query_token(token)
            query_tokens.append(query_token)
            
            # Add search variants
            if query_token.search_variants:
                search_variants.update(query_token.search_variants)
            
            # Generate completions for partial tokens
            if query_token.is_partial:
                completions = self._generate_completions(token)
                suggested_completions.update(completions)
        
        # Generate processed query for MeiliSearch
        processed_query = self._build_processed_query(query_tokens)
        
        # Add query expansion variants if enabled
        if self.enable_query_expansion:
            expansion_variants = self._expand_query(normalized_query, query_tokens)
            search_variants.update(expansion_variants)
        
        metadata = {
            "original_token_count": len(tokenization_result.tokens),
            "processed_token_count": len(query_tokens),
            "thai_tokens": sum(1 for t in query_tokens if self._is_thai_text(t.original)),
            "partial_tokens": sum(1 for t in query_tokens if t.is_partial),
            "compound_tokens": sum(1 for t in query_tokens if t.query_type == QueryType.COMPOUND),
            "processing_time_ms": tokenization_result.processing_time_ms,
            "query_expansion_enabled": self.enable_query_expansion,
            "partial_matching_enabled": self.enable_partial_matching
        }
        
        return QueryProcessingResult(
            original_query=query,
            processed_query=processed_query,
            query_tokens=query_tokens,
            search_variants=list(search_variants),
            suggested_completions=list(suggested_completions)[:10],  # Limit suggestions
            processing_metadata=metadata
        )
    
    def process_partial_compound_query(self, query: str) -> QueryProcessingResult:
        """
        Specialized processing for partial compound word queries.
        
        Args:
            query: Partial compound word query
            
        Returns:
            QueryProcessingResult optimized for compound word matching
        """
        # First, process as regular query
        base_result = self.process_search_query(query)
        
        # Enhance with compound-specific processing
        enhanced_tokens = []
        additional_variants = set()
        
        for token in base_result.query_tokens:
            if self._is_potential_compound_part(token.original):
                # Generate compound word variants
                compound_variants = self._generate_compound_variants(token.original)
                
                enhanced_token = QueryToken(
                    original=token.original,
                    processed=token.processed,
                    query_type=QueryType.COMPOUND,
                    is_partial=True,
                    compound_parts=self._extract_compound_parts(token.original),
                    search_variants=list(compound_variants),
                    boost_score=1.2  # Boost compound matches
                )
                
                enhanced_tokens.append(enhanced_token)
                additional_variants.update(compound_variants)
            else:
                enhanced_tokens.append(token)
        
        # Combine variants
        all_variants = set(base_result.search_variants)
        all_variants.update(additional_variants)
        
        return QueryProcessingResult(
            original_query=base_result.original_query,
            processed_query=base_result.processed_query,
            query_tokens=enhanced_tokens,
            search_variants=list(all_variants),
            suggested_completions=base_result.suggested_completions,
            processing_metadata={
                **base_result.processing_metadata,
                "compound_enhanced": True,
                "additional_variants": len(additional_variants)
            }
        )
    
    def _normalize_query(self, query: str) -> str:
        """Normalize search query for consistent processing."""
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        
        # Normalize Thai characters (if needed)
        # This could include normalizing different forms of the same character
        
        # Remove common search operators that might interfere
        # Keep them for advanced search processing later
        
        return normalized
    
    def _process_query_token(self, token: str) -> QueryToken:
        """Process individual query token for search optimization."""
        if not token.strip():
            return QueryToken(
                original=token,
                processed=token,
                query_type=QueryType.SIMPLE
            )
        
        # Classify query type
        query_type = self._classify_query_type(token)
        
        # Check if token is partial (incomplete)
        is_partial = self._is_partial_token(token)
        
        # Generate search variants
        search_variants = self._generate_token_variants(token)
        
        # Process token for MeiliSearch compatibility
        processed_token = self._process_token_for_search(token, query_type)
        
        # Extract compound parts if applicable
        compound_parts = None
        if query_type == QueryType.COMPOUND:
            compound_parts = self._extract_compound_parts(token)
        
        return QueryToken(
            original=token,
            processed=processed_token,
            query_type=query_type,
            is_partial=is_partial,
            compound_parts=compound_parts,
            search_variants=search_variants,
            boost_score=self._calculate_boost_score(token, query_type)
        )
    
    def _classify_query_type(self, token: str) -> QueryType:
        """Classify the type of query token."""
        if not self._is_thai_text(token):
            return QueryType.SIMPLE
        
        # Check for compound patterns
        for pattern in self.compound_patterns:
            if re.match(pattern, token):
                return QueryType.COMPOUND
        
        # Check for mixed content
        if self._has_mixed_content(token):
            return QueryType.MIXED
        
        # Check if it looks like a phrase
        if ' ' in token.strip():
            return QueryType.PHRASE
        
        # Check for partial indicators
        if self._is_partial_token(token):
            return QueryType.PARTIAL
        
        return QueryType.SIMPLE
    
    def _is_partial_token(self, token: str) -> bool:
        """Check if token appears to be partial/incomplete."""
        if not self._is_thai_text(token):
            return False
        
        # Heuristics for partial tokens
        # Very short tokens might be partial
        if len(token) <= 2:
            return True
        
        # Tokens ending with common prefixes might be partial
        for prefix in self.thai_prefixes:
            if token.endswith(prefix) and len(token) > len(prefix):
                return True
        
        # Tokens starting with common suffixes might be partial
        for suffix in self.thai_suffixes:
            if token.startswith(suffix) and len(token) > len(suffix):
                return True
        
        return False
    
    def _generate_token_variants(self, token: str) -> List[str]:
        """Generate search variants for a token."""
        variants = set()
        
        if not self._is_thai_text(token):
            return [token]
        
        # Add the original token
        variants.add(token)
        
        # Generate prefix/suffix variants for partial matching
        if self.enable_partial_matching:
            # Add wildcard variants (conceptual - MeiliSearch handles this)
            variants.add(f"{token}*")
            variants.add(f"*{token}")
            variants.add(f"*{token}*")
        
        # Generate compound variants
        if len(token) > 4:
            compound_variants = self._generate_compound_variants(token)
            variants.update(compound_variants)
        
        return list(variants)
    
    def _generate_compound_variants(self, token: str) -> Set[str]:
        """Generate compound word variants for better matching."""
        variants = set()
        
        # Try different compound splitting approaches
        for pattern in self.compound_patterns:
            match = re.match(pattern, token)
            if match:
                groups = match.groups()
                
                # Add individual parts
                for group in groups:
                    if group and len(group) > 1:
                        variants.add(group)
                
                # Add recombined variants
                if len(groups) >= 2:
                    variants.add(''.join(groups))
        
        # Try splitting at common boundaries
        mid_point = len(token) // 2
        if mid_point > 2:
            variants.add(token[:mid_point])
            variants.add(token[mid_point:])
        
        return variants
    
    def _extract_compound_parts(self, token: str) -> Optional[List[str]]:
        """Extract parts of compound words."""
        for pattern in self.compound_patterns:
            match = re.match(pattern, token)
            if match:
                parts = [part for part in match.groups() if part]
                if len(parts) > 1:
                    return parts
        
        # Fallback: simple split
        if len(token) > 6:
            mid_point = len(token) // 2
            return [token[:mid_point], token[mid_point:]]
        
        return None
    
    def _process_token_for_search(self, token: str, query_type: QueryType) -> str:
        """Process token for MeiliSearch search compatibility."""
        if not self._is_thai_text(token):
            return token
        
        # For Thai tokens, we might want to add word boundaries
        # but for search queries, we typically want to be more permissive
        
        if query_type == QueryType.COMPOUND:
            # For compound queries, add separators to help matching
            return f"{token}{self.token_processor.THAI_WORD_SEPARATOR}"
        
        return token
    
    def _calculate_boost_score(self, token: str, query_type: QueryType) -> float:
        """Calculate relevance boost score for token."""
        base_score = 1.0
        
        # Boost compound words as they're more specific
        if query_type == QueryType.COMPOUND:
            base_score *= 1.2
        
        # Boost longer tokens as they're more specific
        if len(token) > 6:
            base_score *= 1.1
        
        # Reduce score for very short tokens as they might be too general
        if len(token) <= 2:
            base_score *= 0.8
        
        return base_score
    
    def _build_processed_query(self, query_tokens: List[QueryToken]) -> str:
        """Build processed query string for MeiliSearch."""
        processed_parts = []
        
        for token in query_tokens:
            if token.processed.strip():
                processed_parts.append(token.processed)
        
        return ' '.join(processed_parts)
    
    def _expand_query(self, query: str, query_tokens: List[QueryToken]) -> Set[str]:
        """Expand query with related terms and variants."""
        expansions = set()
        
        # Add synonym expansions (would be populated from a synonym dictionary)
        # For now, just add some basic expansions
        
        # Add partial word expansions
        for token in query_tokens:
            if token.is_partial and token.search_variants:
                expansions.update(token.search_variants)
        
        return expansions
    
    def _generate_completions(self, partial_token: str) -> Set[str]:
        """Generate completion suggestions for partial tokens."""
        completions = set()
        
        if not self._is_thai_text(partial_token):
            return completions
        
        # Generate completions based on common patterns
        for prefix in self.thai_prefixes:
            if partial_token.startswith(prefix):
                # Add common completions for this prefix
                completions.add(f"{partial_token}การ")
                completions.add(f"{partial_token}ความ")
        
        for suffix in self.thai_suffixes:
            if partial_token.endswith(suffix):
                # Add common completions for this suffix
                completions.add(f"การ{partial_token}")
                completions.add(f"ความ{partial_token}")
        
        return completions
    
    def _is_potential_compound_part(self, token: str) -> bool:
        """Check if token might be part of a compound word."""
        if not self._is_thai_text(token):
            return False
        
        # Check against compound patterns
        for pattern in self.compound_patterns:
            if re.search(pattern, token):
                return True
        
        # Check for common compound indicators
        compound_indicators = self.thai_prefixes + self.thai_suffixes
        for indicator in compound_indicators:
            if indicator in token:
                return True
        
        return False
    
    def _has_mixed_content(self, token: str) -> bool:
        """Check if token has mixed Thai/non-Thai content."""
        thai_chars = sum(1 for c in token if self._is_thai_char(c))
        non_thai_chars = sum(1 for c in token if c.isalnum() and not self._is_thai_char(c))
        
        return thai_chars > 0 and non_thai_chars > 0
    
    def _is_thai_char(self, char: str) -> bool:
        """Check if character is Thai."""
        return '\u0e00' <= char <= '\u0e7f'
    
    def _is_thai_text(self, text: str) -> bool:
        """Check if text is primarily Thai."""
        if not text:
            return False
        thai_chars = sum(1 for char in text if self._is_thai_char(char))
        return thai_chars / len(text) > 0.3  # More permissive for queries
    
    def get_stats(self) -> Dict[str, Any]:
        """Get query processor statistics and configuration."""
        return {
            "query_expansion_enabled": self.enable_query_expansion,
            "partial_matching_enabled": self.enable_partial_matching,
            "compound_patterns_count": len(self.compound_patterns),
            "thai_prefixes_count": len(self.thai_prefixes),
            "thai_suffixes_count": len(self.thai_suffixes),
            "segmenter_engine": self.thai_segmenter.engine,
            "processor_separators": len(self.token_processor.separators)
        }