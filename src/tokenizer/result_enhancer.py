"""
Search result enhancement for Thai compound words.

This module provides post-processing for search results to improve
highlighting, relevance scoring, and result presentation for Thai text.
"""

import logging
import re
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass
from enum import Enum

from .thai_segmenter import ThaiSegmenter
from .query_processor import QueryProcessor, QueryToken


logger = logging.getLogger(__name__)


class HighlightType(Enum):
    """Types of highlighting for search results."""
    EXACT_MATCH = "exact"
    PARTIAL_MATCH = "partial"
    COMPOUND_MATCH = "compound"
    FUZZY_MATCH = "fuzzy"


@dataclass
class HighlightSpan:
    """Highlighted span in search result."""
    
    start: int
    end: int
    text: str
    highlight_type: HighlightType
    confidence: float = 1.0
    matched_query: Optional[str] = None


@dataclass
class EnhancedSearchHit:
    """Enhanced search result with Thai-specific improvements."""
    
    original_hit: Dict[str, Any]
    enhanced_score: float
    highlight_spans: List[HighlightSpan]
    compound_matches: List[str]
    original_text_preserved: Dict[str, str]
    tokenized_text: Dict[str, str]
    relevance_factors: Dict[str, float]


@dataclass
class SearchResultEnhancement:
    """Complete search result enhancement."""
    
    original_results: Dict[str, Any]
    enhanced_hits: List[EnhancedSearchHit]
    query_analysis: Dict[str, Any]
    enhancement_metadata: Dict[str, Any]


class SearchResultEnhancer:
    """
    Enhances search results for Thai compound words.
    
    Provides improved highlighting, relevance scoring, and result
    presentation specifically optimized for Thai text search.
    """
    
    def __init__(
        self,
        thai_segmenter: Optional[ThaiSegmenter] = None,
        query_processor: Optional[QueryProcessor] = None,
        enable_compound_highlighting: bool = True,
        enable_relevance_boosting: bool = True
    ):
        """
        Initialize search result enhancer.
        
        Args:
            thai_segmenter: Thai segmentation engine
            query_processor: Query processing utilities
            enable_compound_highlighting: Whether to enhance compound word highlighting
            enable_relevance_boosting: Whether to boost relevance scores
        """
        self.thai_segmenter = thai_segmenter or ThaiSegmenter()
        self.query_processor = query_processor or QueryProcessor()
        self.enable_compound_highlighting = enable_compound_highlighting
        self.enable_relevance_boosting = enable_relevance_boosting
        
        # Highlighting patterns
        self.highlight_patterns = {
            'meilisearch_default': r'<em>(.*?)</em>',
            'html_strong': r'<strong>(.*?)</strong>',
            'html_mark': r'<mark>(.*?)</mark>',
            'custom_highlight': r'\[HIGHLIGHT\](.*?)\[/HIGHLIGHT\]'
        }
        
        logger.info("SearchResultEnhancer initialized")
    
    def enhance_search_results(
        self,
        search_results: Dict[str, Any],
        original_query: str,
        highlight_fields: Optional[List[str]] = None
    ) -> SearchResultEnhancement:
        """
        Enhance search results with Thai-specific improvements.
        
        Args:
            search_results: Raw search results from MeiliSearch
            original_query: Original search query
            highlight_fields: Fields to enhance highlighting for
            
        Returns:
            SearchResultEnhancement with improved results
        """
        if not search_results or not search_results.get('hits'):
            return SearchResultEnhancement(
                original_results=search_results,
                enhanced_hits=[],
                query_analysis={},
                enhancement_metadata={"empty_results": True}
            )
        
        # Analyze the query for enhancement context
        query_analysis = self._analyze_query_for_enhancement(original_query)
        
        # Process each hit
        enhanced_hits = []
        for hit in search_results.get('hits', []):
            enhanced_hit = self._enhance_single_hit(
                hit, 
                query_analysis, 
                highlight_fields or ['title', 'content']
            )
            enhanced_hits.append(enhanced_hit)
        
        # Sort by enhanced relevance if enabled
        if self.enable_relevance_boosting:
            enhanced_hits.sort(key=lambda x: x.enhanced_score, reverse=True)
        
        metadata = {
            "total_hits": len(enhanced_hits),
            "compound_matches": sum(len(hit.compound_matches) for hit in enhanced_hits),
            "average_enhancement": sum(hit.enhanced_score for hit in enhanced_hits) / len(enhanced_hits) if enhanced_hits else 0,
            "query_has_compounds": query_analysis.get("has_compound_words", False),
            "enhancement_enabled": {
                "compound_highlighting": self.enable_compound_highlighting,
                "relevance_boosting": self.enable_relevance_boosting
            }
        }
        
        return SearchResultEnhancement(
            original_results=search_results,
            enhanced_hits=enhanced_hits,
            query_analysis=query_analysis,
            enhancement_metadata=metadata
        )
    
    def _analyze_query_for_enhancement(self, query: str) -> Dict[str, Any]:
        """Analyze query to determine enhancement strategies."""
        # Process query to understand its structure
        query_result = self.query_processor.process_search_query(query)
        
        # Extract compound words and partial matches
        compound_tokens = [
            token for token in query_result.query_tokens 
            if token.query_type.value == "compound"
        ]
        
        partial_tokens = [
            token for token in query_result.query_tokens 
            if token.is_partial
        ]
        
        # Identify Thai vs non-Thai content
        thai_tokens = [
            token for token in query_result.query_tokens 
            if self._is_thai_text(token.original)
        ]
        
        return {
            "processed_query": query_result.processed_query,
            "total_tokens": len(query_result.query_tokens),
            "compound_tokens": [token.original for token in compound_tokens],
            "partial_tokens": [token.original for token in partial_tokens],
            "thai_tokens": [token.original for token in thai_tokens],
            "search_variants": query_result.search_variants,
            "has_compound_words": len(compound_tokens) > 0,
            "has_partial_matches": len(partial_tokens) > 0,
            "is_mixed_language": len(thai_tokens) != len(query_result.query_tokens)
        }
    
    def _enhance_single_hit(
        self,
        hit: Dict[str, Any],
        query_analysis: Dict[str, Any],
        highlight_fields: List[str]
    ) -> EnhancedSearchHit:
        """Enhance a single search result hit."""
        # Calculate enhanced relevance score
        enhanced_score = self._calculate_enhanced_score(hit, query_analysis)
        
        # Extract and enhance highlights
        highlight_spans = []
        compound_matches = []
        original_text = {}
        tokenized_text = {}
        
        for field in highlight_fields:
            if field in hit:
                # Get original text
                original_text[field] = hit[field]
                
                # Get highlighted version if available
                highlighted_field = f"_formatted.{field}" if "_formatted" in hit else field
                highlighted_text = hit.get("_formatted", {}).get(field, hit.get(field, ""))
                
                # Enhance highlighting for this field
                field_highlights, field_compounds = self._enhance_field_highlighting(
                    original_text[field],
                    highlighted_text,
                    query_analysis
                )
                
                highlight_spans.extend(field_highlights)
                compound_matches.extend(field_compounds)
                
                # Create tokenized version
                tokenized_text[field] = self._create_tokenized_version(original_text[field])
        
        # Calculate relevance factors
        relevance_factors = self._calculate_relevance_factors(
            hit, query_analysis, highlight_spans, compound_matches
        )
        
        return EnhancedSearchHit(
            original_hit=hit,
            enhanced_score=enhanced_score,
            highlight_spans=highlight_spans,
            compound_matches=list(set(compound_matches)),  # Remove duplicates
            original_text_preserved=original_text,
            tokenized_text=tokenized_text,
            relevance_factors=relevance_factors
        )
    
    def _calculate_enhanced_score(
        self,
        hit: Dict[str, Any],
        query_analysis: Dict[str, Any]
    ) -> float:
        """Calculate enhanced relevance score for Thai content."""
        # Start with original score if available
        base_score = hit.get('_score', 1.0)
        
        if not self.enable_relevance_boosting:
            return base_score
        
        enhancement_factor = 1.0
        
        # Boost for compound word matches
        if query_analysis.get("has_compound_words", False):
            compound_boost = self._calculate_compound_boost(hit, query_analysis)
            enhancement_factor *= compound_boost
        
        # Boost for exact Thai matches
        thai_boost = self._calculate_thai_match_boost(hit, query_analysis)
        enhancement_factor *= thai_boost
        
        # Boost for field importance (title vs content)
        field_boost = self._calculate_field_importance_boost(hit)
        enhancement_factor *= field_boost
        
        return base_score * enhancement_factor
    
    def _calculate_compound_boost(
        self,
        hit: Dict[str, Any],
        query_analysis: Dict[str, Any]
    ) -> float:
        """Calculate boost factor for compound word matches."""
        boost = 1.0
        compound_tokens = query_analysis.get("compound_tokens", [])
        
        if not compound_tokens:
            return boost
        
        # Check if hit contains compound words from query
        hit_text = self._get_searchable_text(hit)
        
        for compound in compound_tokens:
            if compound in hit_text:
                boost *= 1.3  # Boost for exact compound match
            else:
                # Check for partial compound matches
                compound_parts = self._split_compound_word(compound)
                partial_matches = sum(1 for part in compound_parts if part in hit_text)
                if partial_matches > 0:
                    boost *= 1.0 + (0.1 * partial_matches)  # Smaller boost for partial matches
        
        return min(boost, 2.0)  # Cap the boost
    
    def _calculate_thai_match_boost(
        self,
        hit: Dict[str, Any],
        query_analysis: Dict[str, Any]
    ) -> float:
        """Calculate boost factor for Thai text matches."""
        boost = 1.0
        thai_tokens = query_analysis.get("thai_tokens", [])
        
        if not thai_tokens:
            return boost
        
        hit_text = self._get_searchable_text(hit)
        
        # Boost for exact Thai token matches
        exact_matches = sum(1 for token in thai_tokens if token in hit_text)
        if exact_matches > 0:
            boost *= 1.0 + (0.2 * exact_matches)
        
        return min(boost, 1.8)  # Cap the boost
    
    def _calculate_field_importance_boost(self, hit: Dict[str, Any]) -> float:
        """Calculate boost based on field importance."""
        boost = 1.0
        
        # Title matches are more important than content matches
        title = hit.get('title', '')
        if title and self._has_highlighted_content(title):
            boost *= 1.4
        
        return boost
    
    def _enhance_field_highlighting(
        self,
        original_text: str,
        highlighted_text: str,
        query_analysis: Dict[str, Any]
    ) -> Tuple[List[HighlightSpan], List[str]]:
        """Enhance highlighting for a specific field."""
        highlight_spans = []
        compound_matches = []
        
        if not self.enable_compound_highlighting:
            # Just extract existing highlights
            spans = self._extract_existing_highlights(highlighted_text)
            return spans, []
        
        # Extract existing highlights
        existing_spans = self._extract_existing_highlights(highlighted_text)
        highlight_spans.extend(existing_spans)
        
        # Add compound word highlighting
        compound_spans, compounds = self._add_compound_highlighting(
            original_text, query_analysis
        )
        highlight_spans.extend(compound_spans)
        compound_matches.extend(compounds)
        
        # Add partial match highlighting
        partial_spans = self._add_partial_match_highlighting(
            original_text, query_analysis
        )
        highlight_spans.extend(partial_spans)
        
        # Remove overlapping spans and sort by position
        highlight_spans = self._merge_overlapping_spans(highlight_spans)
        
        return highlight_spans, compound_matches
    
    def _extract_existing_highlights(self, highlighted_text: str) -> List[HighlightSpan]:
        """Extract existing highlight spans from formatted text."""
        spans = []
        
        for pattern_name, pattern in self.highlight_patterns.items():
            for match in re.finditer(pattern, highlighted_text):
                span = HighlightSpan(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(1),
                    highlight_type=HighlightType.EXACT_MATCH,
                    confidence=1.0
                )
                spans.append(span)
        
        return spans
    
    def _add_compound_highlighting(
        self,
        text: str,
        query_analysis: Dict[str, Any]
    ) -> Tuple[List[HighlightSpan], List[str]]:
        """Add highlighting for compound word matches."""
        spans = []
        compounds = []
        
        compound_tokens = query_analysis.get("compound_tokens", [])
        
        for compound in compound_tokens:
            # Find exact compound matches
            for match in re.finditer(re.escape(compound), text):
                span = HighlightSpan(
                    start=match.start(),
                    end=match.end(),
                    text=match.group(),
                    highlight_type=HighlightType.COMPOUND_MATCH,
                    confidence=1.0,
                    matched_query=compound
                )
                spans.append(span)
                compounds.append(compound)
            
            # Find partial compound matches
            compound_parts = self._split_compound_word(compound)
            for part in compound_parts:
                if len(part) > 2:  # Only highlight meaningful parts
                    for match in re.finditer(re.escape(part), text):
                        span = HighlightSpan(
                            start=match.start(),
                            end=match.end(),
                            text=match.group(),
                            highlight_type=HighlightType.PARTIAL_MATCH,
                            confidence=0.7,
                            matched_query=f"{compound} (part: {part})"
                        )
                        spans.append(span)
        
        return spans, compounds
    
    def _add_partial_match_highlighting(
        self,
        text: str,
        query_analysis: Dict[str, Any]
    ) -> List[HighlightSpan]:
        """Add highlighting for partial matches."""
        spans = []
        
        partial_tokens = query_analysis.get("partial_tokens", [])
        
        for token in partial_tokens:
            # Use fuzzy matching for partial tokens
            fuzzy_matches = self._find_fuzzy_matches(text, token)
            for match_start, match_end, matched_text, confidence in fuzzy_matches:
                span = HighlightSpan(
                    start=match_start,
                    end=match_end,
                    text=matched_text,
                    highlight_type=HighlightType.FUZZY_MATCH,
                    confidence=confidence,
                    matched_query=token
                )
                spans.append(span)
        
        return spans
    
    def _find_fuzzy_matches(
        self,
        text: str,
        query_token: str,
        min_confidence: float = 0.6
    ) -> List[Tuple[int, int, str, float]]:
        """Find fuzzy matches for partial tokens."""
        matches = []
        
        if not self._is_thai_text(query_token):
            return matches
        
        # Simple fuzzy matching based on substring containment
        # In a production system, you might use more sophisticated algorithms
        
        # Look for tokens that contain the query token
        words = self._extract_thai_words(text)
        for word_start, word_end, word in words:
            if query_token in word:
                confidence = len(query_token) / len(word)
                if confidence >= min_confidence:
                    matches.append((word_start, word_end, word, confidence))
            elif word in query_token:
                confidence = len(word) / len(query_token)
                if confidence >= min_confidence:
                    matches.append((word_start, word_end, word, confidence))
        
        return matches
    
    def _extract_thai_words(self, text: str) -> List[Tuple[int, int, str]]:
        """Extract Thai words with their positions."""
        words = []
        
        # Use the Thai segmenter to find word boundaries
        result = self.thai_segmenter.segment_text(text)
        
        current_pos = 0
        for token in result.tokens:
            if self._is_thai_text(token) and len(token.strip()) > 0:
                start_pos = text.find(token, current_pos)
                if start_pos >= 0:
                    end_pos = start_pos + len(token)
                    words.append((start_pos, end_pos, token))
                    current_pos = end_pos
        
        return words
    
    def _merge_overlapping_spans(self, spans: List[HighlightSpan]) -> List[HighlightSpan]:
        """Merge overlapping highlight spans."""
        if not spans:
            return spans
        
        # Sort by start position
        sorted_spans = sorted(spans, key=lambda x: x.start)
        merged = [sorted_spans[0]]
        
        for current in sorted_spans[1:]:
            last = merged[-1]
            
            # Check for overlap
            if current.start <= last.end:
                # Merge spans - keep the one with higher confidence
                if current.confidence > last.confidence:
                    merged[-1] = HighlightSpan(
                        start=min(last.start, current.start),
                        end=max(last.end, current.end),
                        text=current.text,
                        highlight_type=current.highlight_type,
                        confidence=current.confidence,
                        matched_query=current.matched_query
                    )
                else:
                    merged[-1] = HighlightSpan(
                        start=min(last.start, current.start),
                        end=max(last.end, current.end),
                        text=last.text,
                        highlight_type=last.highlight_type,
                        confidence=last.confidence,
                        matched_query=last.matched_query
                    )
            else:
                merged.append(current)
        
        return merged
    
    def _create_tokenized_version(self, text: str) -> str:
        """Create tokenized version of text for display."""
        result = self.thai_segmenter.segment_text(text)
        
        # Add visible separators for Thai word boundaries
        tokenized_parts = []
        for token in result.tokens:
            if self._is_thai_text(token):
                tokenized_parts.append(f"{token}|")  # Use | as visible separator
            else:
                tokenized_parts.append(token)
        
        return "".join(tokenized_parts)
    
    def _calculate_relevance_factors(
        self,
        hit: Dict[str, Any],
        query_analysis: Dict[str, Any],
        highlight_spans: List[HighlightSpan],
        compound_matches: List[str]
    ) -> Dict[str, float]:
        """Calculate detailed relevance factors."""
        factors = {}
        
        # Highlight density
        total_highlighted_chars = sum(span.end - span.start for span in highlight_spans)
        total_text_chars = len(self._get_searchable_text(hit))
        factors["highlight_density"] = total_highlighted_chars / max(total_text_chars, 1)
        
        # Compound match factor
        factors["compound_matches"] = len(compound_matches)
        
        # Thai content factor
        thai_spans = [span for span in highlight_spans if self._is_thai_text(span.text)]
        factors["thai_match_ratio"] = len(thai_spans) / max(len(highlight_spans), 1)
        
        # Confidence factor
        avg_confidence = sum(span.confidence for span in highlight_spans) / max(len(highlight_spans), 1)
        factors["average_confidence"] = avg_confidence
        
        # Field distribution
        factors["title_matches"] = 1.0 if self._has_highlighted_content(hit.get('title', '')) else 0.0
        factors["content_matches"] = 1.0 if self._has_highlighted_content(hit.get('content', '')) else 0.0
        
        return factors
    
    def _split_compound_word(self, compound: str) -> List[str]:
        """Split compound word into parts."""
        # Use the Thai segmenter to split compound words
        result = self.thai_segmenter.segment_compound_words(compound)
        return [token for token in result.tokens if len(token.strip()) > 1]
    
    def _get_searchable_text(self, hit: Dict[str, Any]) -> str:
        """Get all searchable text from a hit."""
        searchable_fields = ['title', 'content', 'description', 'text']
        text_parts = []
        
        for field in searchable_fields:
            if field in hit and hit[field]:
                text_parts.append(str(hit[field]))
        
        return " ".join(text_parts)
    
    def _has_highlighted_content(self, text: str) -> bool:
        """Check if text contains highlighting markup."""
        for pattern in self.highlight_patterns.values():
            if re.search(pattern, text):
                return True
        return False
    
    def _is_thai_text(self, text: str) -> bool:
        """Check if text is primarily Thai."""
        if not text:
            return False
        thai_chars = sum(1 for char in text if '\u0e00' <= char <= '\u0e7f')
        return thai_chars / len(text) > 0.3
    
    def get_stats(self) -> Dict[str, Any]:
        """Get enhancer statistics and configuration."""
        return {
            "compound_highlighting_enabled": self.enable_compound_highlighting,
            "relevance_boosting_enabled": self.enable_relevance_boosting,
            "highlight_patterns_count": len(self.highlight_patterns),
            "segmenter_engine": self.thai_segmenter.engine,
            "query_processor_enabled": self.query_processor is not None
        }