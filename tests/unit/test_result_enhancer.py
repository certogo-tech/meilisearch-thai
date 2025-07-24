"""Unit tests for search result enhancer."""

import pytest
from unittest.mock import Mock, patch

from src.tokenizer.result_enhancer import (
    SearchResultEnhancer, HighlightType, HighlightSpan, 
    EnhancedSearchHit, SearchResultEnhancement
)
from src.tokenizer.thai_segmenter import ThaiSegmenter, TokenizationResult
from src.tokenizer.query_processor import QueryProcessor, QueryProcessingResult, QueryToken, QueryType


class TestSearchResultEnhancer:
    """Test cases for SearchResultEnhancer class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.enhancer = SearchResultEnhancer()
    
    def test_init_default(self):
        """Test SearchResultEnhancer initialization with defaults."""
        enhancer = SearchResultEnhancer()
        
        assert enhancer.enable_compound_highlighting is True
        assert enhancer.enable_relevance_boosting is True
        assert isinstance(enhancer.thai_segmenter, ThaiSegmenter)
        assert isinstance(enhancer.query_processor, QueryProcessor)
        assert len(enhancer.highlight_patterns) > 0
    
    def test_init_custom_components(self):
        """Test SearchResultEnhancer initialization with custom components."""
        mock_segmenter = Mock(spec=ThaiSegmenter)
        mock_processor = Mock(spec=QueryProcessor)
        
        enhancer = SearchResultEnhancer(
            thai_segmenter=mock_segmenter,
            query_processor=mock_processor,
            enable_compound_highlighting=False,
            enable_relevance_boosting=False
        )
        
        assert enhancer.thai_segmenter is mock_segmenter
        assert enhancer.query_processor is mock_processor
        assert enhancer.enable_compound_highlighting is False
        assert enhancer.enable_relevance_boosting is False
    
    def test_enhance_empty_results(self):
        """Test enhancement of empty search results."""
        empty_results = {"hits": []}
        
        enhancement = self.enhancer.enhance_search_results(
            empty_results, "test query"
        )
        
        assert enhancement.original_results == empty_results
        assert enhancement.enhanced_hits == []
        assert enhancement.enhancement_metadata["empty_results"] is True
    
    def test_enhance_none_results(self):
        """Test enhancement of None search results."""
        enhancement = self.enhancer.enhance_search_results(
            None, "test query"
        )
        
        assert enhancement.enhanced_hits == []
        assert enhancement.enhancement_metadata["empty_results"] is True
    
    @patch('src.tokenizer.result_enhancer.QueryProcessor')
    def test_analyze_query_for_enhancement(self, mock_processor_class):
        """Test query analysis for enhancement."""
        # Mock the query processor
        mock_processor = Mock()
        mock_tokens = [
            Mock(
                original="การศึกษา",
                query_type=QueryType.COMPOUND,
                is_partial=True
            ),
            Mock(
                original="API",
                query_type=QueryType.SIMPLE,
                is_partial=False
            )
        ]
        mock_result = Mock(
            processed_query="การศึกษา API",
            query_tokens=mock_tokens,
            search_variants=["การศึกษา", "ศึกษา", "API"]
        )
        mock_processor.process_search_query.return_value = mock_result
        mock_processor_class.return_value = mock_processor
        
        enhancer = SearchResultEnhancer()
        analysis = enhancer._analyze_query_for_enhancement("การศึกษา API")
        
        assert analysis["has_compound_words"] is True
        assert analysis["has_partial_matches"] is True
        assert analysis["is_mixed_language"] is True
        assert "การศึกษา" in analysis["compound_tokens"]
        assert "การศึกษา" in analysis["partial_tokens"]
        assert len(analysis["thai_tokens"]) == 1
    
    def test_calculate_enhanced_score_no_boosting(self):
        """Test enhanced score calculation with boosting disabled."""
        enhancer = SearchResultEnhancer(enable_relevance_boosting=False)
        
        hit = {"_score": 1.5}
        query_analysis = {"has_compound_words": True}
        
        score = enhancer._calculate_enhanced_score(hit, query_analysis)
        assert score == 1.5  # Should remain unchanged
    
    def test_calculate_enhanced_score_with_boosting(self):
        """Test enhanced score calculation with boosting enabled."""
        hit = {
            "_score": 1.0,
            "title": "การศึกษาไทย",
            "content": "เกี่ยวกับการศึกษาในประเทศไทย"
        }
        query_analysis = {
            "has_compound_words": True,
            "compound_tokens": ["การศึกษา"],
            "thai_tokens": ["การศึกษา"]
        }
        
        score = self.enhancer._calculate_enhanced_score(hit, query_analysis)
        assert score > 1.0  # Should be boosted
    
    def test_calculate_compound_boost(self):
        """Test compound word boost calculation."""
        hit = {
            "title": "การศึกษาไทย",
            "content": "เกี่ยวกับการศึกษา"
        }
        query_analysis = {
            "compound_tokens": ["การศึกษา", "วิทยาศาสตร์"]
        }
        
        boost = self.enhancer._calculate_compound_boost(hit, query_analysis)
        assert boost > 1.0  # Should boost for การศึกษา match
        assert boost <= 2.0  # Should be capped
    
    def test_calculate_compound_boost_no_compounds(self):
        """Test compound boost with no compound tokens."""
        hit = {"title": "test", "content": "content"}
        query_analysis = {"compound_tokens": []}
        
        boost = self.enhancer._calculate_compound_boost(hit, query_analysis)
        assert boost == 1.0  # No boost
    
    def test_calculate_thai_match_boost(self):
        """Test Thai match boost calculation."""
        hit = {
            "title": "สวัสดีครับ",
            "content": "การทดสอบ"
        }
        query_analysis = {
            "thai_tokens": ["สวัสดี", "การทดสอบ"]
        }
        
        boost = self.enhancer._calculate_thai_match_boost(hit, query_analysis)
        assert boost > 1.0  # Should boost for Thai matches
        assert boost <= 1.8  # Should be capped
    
    def test_calculate_field_importance_boost(self):
        """Test field importance boost calculation."""
        # Hit with highlighted title
        hit_with_title = {"title": "<em>การศึกษา</em>"}
        boost = self.enhancer._calculate_field_importance_boost(hit_with_title)
        assert boost > 1.0  # Should boost for title matches
        
        # Hit without highlighted title
        hit_without_title = {"content": "some content"}
        boost = self.enhancer._calculate_field_importance_boost(hit_without_title)
        assert boost == 1.0  # No boost
    
    def test_extract_existing_highlights(self):
        """Test extraction of existing highlight spans."""
        highlighted_text = "This is <em>highlighted</em> text with <strong>more</strong> highlights"
        
        spans = self.enhancer._extract_existing_highlights(highlighted_text)
        
        assert len(spans) == 2
        assert spans[0].text == "highlighted"
        assert spans[0].highlight_type == HighlightType.EXACT_MATCH
        assert spans[1].text == "more"
    
    def test_extract_existing_highlights_no_highlights(self):
        """Test extraction with no existing highlights."""
        plain_text = "This is plain text without highlights"
        
        spans = self.enhancer._extract_existing_highlights(plain_text)
        
        assert len(spans) == 0
    
    def test_add_compound_highlighting(self):
        """Test adding compound word highlighting."""
        text = "การศึกษาไทยมีความสำคัญ"
        query_analysis = {
            "compound_tokens": ["การศึกษา"]
        }
        
        spans, compounds = self.enhancer._add_compound_highlighting(text, query_analysis)
        
        assert len(spans) > 0
        assert len(compounds) > 0
        assert "การศึกษา" in compounds
        
        # Check for exact match span
        exact_spans = [s for s in spans if s.highlight_type == HighlightType.COMPOUND_MATCH]
        assert len(exact_spans) > 0
    
    def test_add_compound_highlighting_no_compounds(self):
        """Test compound highlighting with no compound tokens."""
        text = "สวัสดีครับ"
        query_analysis = {"compound_tokens": []}
        
        spans, compounds = self.enhancer._add_compound_highlighting(text, query_analysis)
        
        assert len(spans) == 0
        assert len(compounds) == 0
    
    def test_find_fuzzy_matches(self):
        """Test fuzzy matching for partial tokens."""
        # Mock the segmenter directly on the enhancer instance
        mock_segmenter = Mock()
        mock_segmenter.segment_text.return_value = TokenizationResult(
            original_text="การศึกษาไทย",
            tokens=["การศึกษา", "ไทย"],
            word_boundaries=[0, 8, 11]
        )
        
        enhancer = SearchResultEnhancer()
        enhancer.thai_segmenter = mock_segmenter
        
        text = "การศึกษาไทย"
        query_token = "การ"
        
        # Use lower confidence threshold to match partial words
        matches = enhancer._find_fuzzy_matches(text, query_token, min_confidence=0.3)
        
        assert len(matches) > 0
        # Should find การศึกษา as it contains การ
        match_texts = [match[2] for match in matches]
        assert "การศึกษา" in match_texts
    
    def test_find_fuzzy_matches_non_thai(self):
        """Test fuzzy matching for non-Thai tokens."""
        text = "Hello world"
        query_token = "hello"
        
        matches = self.enhancer._find_fuzzy_matches(text, query_token)
        
        assert len(matches) == 0  # Should not match non-Thai
    
    def test_merge_overlapping_spans(self):
        """Test merging of overlapping highlight spans."""
        spans = [
            HighlightSpan(0, 5, "การศึ", HighlightType.EXACT_MATCH, 1.0),
            HighlightSpan(3, 8, "ศึกษา", HighlightType.COMPOUND_MATCH, 0.8),
            HighlightSpan(10, 15, "ไทย", HighlightType.EXACT_MATCH, 1.0)
        ]
        
        merged = self.enhancer._merge_overlapping_spans(spans)
        
        assert len(merged) == 2  # First two should be merged
        assert merged[0].start == 0
        assert merged[0].end == 8
        assert merged[0].confidence == 1.0  # Should keep higher confidence
        assert merged[1].start == 10
        assert merged[1].end == 15
    
    def test_merge_overlapping_spans_no_overlap(self):
        """Test merging with no overlapping spans."""
        spans = [
            HighlightSpan(0, 5, "การศึ", HighlightType.EXACT_MATCH, 1.0),
            HighlightSpan(10, 15, "ไทย", HighlightType.EXACT_MATCH, 1.0)
        ]
        
        merged = self.enhancer._merge_overlapping_spans(spans)
        
        assert len(merged) == 2  # Should remain unchanged
        assert merged[0].start == 0
        assert merged[1].start == 10
    
    def test_create_tokenized_version(self):
        """Test creation of tokenized text version."""
        # Mock the segmenter directly on the enhancer instance
        mock_segmenter = Mock()
        mock_segmenter.segment_text.return_value = TokenizationResult(
            original_text="การศึกษาไทย",
            tokens=["การศึกษา", "ไทย"],
            word_boundaries=[0, 8, 11]
        )
        
        enhancer = SearchResultEnhancer()
        enhancer.thai_segmenter = mock_segmenter
        
        text = "การศึกษาไทย"
        
        tokenized = enhancer._create_tokenized_version(text)
        
        assert "|" in tokenized  # Should contain separators
        assert "การศึกษา|" in tokenized
        assert "ไทย|" in tokenized
    
    def test_split_compound_word(self):
        """Test compound word splitting."""
        compound = "การศึกษา"
        
        parts = self.enhancer._split_compound_word(compound)
        
        assert len(parts) > 0
        # Should split into meaningful parts
        assert all(len(part.strip()) > 1 for part in parts)
    
    def test_get_searchable_text(self):
        """Test extraction of searchable text from hit."""
        hit = {
            "title": "การศึกษา",
            "content": "เกี่ยวกับการศึกษา",
            "description": "คำอธิบาย",
            "other_field": "ไม่เกี่ยวข้อง"
        }
        
        text = self.enhancer._get_searchable_text(hit)
        
        assert "การศึกษา" in text
        assert "เกี่ยวกับการศึกษา" in text
        assert "คำอธิบาย" in text
        assert "ไม่เกี่ยวข้อง" not in text  # Should not include non-searchable fields
    
    def test_has_highlighted_content(self):
        """Test detection of highlighted content."""
        highlighted = "This has <em>highlighted</em> content"
        plain = "This is plain text"
        
        assert self.enhancer._has_highlighted_content(highlighted) is True
        assert self.enhancer._has_highlighted_content(plain) is False
    
    def test_is_thai_text(self):
        """Test Thai text detection."""
        assert self.enhancer._is_thai_text("การศึกษา") is True
        assert self.enhancer._is_thai_text("hello") is False
        assert self.enhancer._is_thai_text("API การใช้งาน") is True  # Mixed but >30% Thai
        assert self.enhancer._is_thai_text("") is False
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        stats = self.enhancer.get_stats()
        
        assert "compound_highlighting_enabled" in stats
        assert "relevance_boosting_enabled" in stats
        assert "highlight_patterns_count" in stats
        assert "segmenter_engine" in stats
        assert "query_processor_enabled" in stats
        
        assert isinstance(stats["highlight_patterns_count"], int)
        assert stats["highlight_patterns_count"] > 0


class TestSearchResultEnhancementIntegration:
    """Integration tests for search result enhancement."""
    
    def test_end_to_end_enhancement(self):
        """Test end-to-end search result enhancement."""
        enhancer = SearchResultEnhancer()
        
        # Mock search results
        search_results = {
            "hits": [
                {
                    "_score": 1.0,
                    "title": "การศึกษาไทย",
                    "content": "เกี่ยวกับการศึกษาในประเทศไทย",
                    "_formatted": {
                        "title": "<em>การศึกษา</em>ไทย",
                        "content": "เกี่ยวกับ<em>การศึกษา</em>ในประเทศไทย"
                    }
                }
            ],
            "query": "การศึกษา",
            "processingTimeMs": 10
        }
        
        enhancement = enhancer.enhance_search_results(
            search_results, "การศึกษา", ["title", "content"]
        )
        
        assert len(enhancement.enhanced_hits) == 1
        hit = enhancement.enhanced_hits[0]
        
        assert hit.enhanced_score >= 1.0  # Should be boosted
        assert len(hit.highlight_spans) > 0
        assert len(hit.compound_matches) > 0
        assert "การศึกษา" in hit.compound_matches
        assert "title" in hit.original_text_preserved
        assert "content" in hit.original_text_preserved
    
    def test_enhancement_with_mixed_content(self):
        """Test enhancement with mixed Thai-English content."""
        enhancer = SearchResultEnhancer()
        
        search_results = {
            "hits": [
                {
                    "_score": 1.0,
                    "title": "API การใช้งาน",
                    "content": "วิธีการใช้ API สำหรับการพัฒนา"
                }
            ]
        }
        
        enhancement = enhancer.enhance_search_results(
            search_results, "API การใช้งาน"
        )
        
        assert len(enhancement.enhanced_hits) == 1
        assert enhancement.query_analysis["is_mixed_language"] is True
    
    def test_enhancement_disabled_features(self):
        """Test enhancement with disabled features."""
        enhancer = SearchResultEnhancer(
            enable_compound_highlighting=False,
            enable_relevance_boosting=False
        )
        
        search_results = {
            "hits": [
                {
                    "_score": 1.0,
                    "title": "การศึกษาไทย",
                    "content": "เกี่ยวกับการศึกษา"
                }
            ]
        }
        
        enhancement = enhancer.enhance_search_results(
            search_results, "การศึกษา"
        )
        
        hit = enhancement.enhanced_hits[0]
        assert hit.enhanced_score == 1.0  # Should not be boosted
        # Should have fewer highlights without compound highlighting
    
    def test_enhancement_performance(self):
        """Test enhancement performance with multiple hits."""
        enhancer = SearchResultEnhancer()
        
        # Create multiple hits
        hits = []
        for i in range(10):
            hits.append({
                "_score": 1.0 + (i * 0.1),
                "title": f"การศึกษา {i}",
                "content": f"เนื้อหาเกี่ยวกับการศึกษา {i}"
            })
        
        search_results = {"hits": hits}
        
        enhancement = enhancer.enhance_search_results(
            search_results, "การศึกษา"
        )
        
        assert len(enhancement.enhanced_hits) == 10
        # Results should be sorted by enhanced score
        scores = [hit.enhanced_score for hit in enhancement.enhanced_hits]
        assert scores == sorted(scores, reverse=True)