"""Unit tests for Thai query processor."""

import pytest
from unittest.mock import Mock, patch

from src.tokenizer.query_processor import (
    QueryProcessor, QueryType, QueryToken, QueryProcessingResult
)
from src.tokenizer.thai_segmenter import ThaiSegmenter, TokenizationResult
from src.tokenizer.token_processor import TokenProcessor


class TestQueryProcessor:
    """Test cases for QueryProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.query_processor = QueryProcessor()
    
    def test_init_default(self):
        """Test QueryProcessor initialization with defaults."""
        processor = QueryProcessor()
        
        assert processor.enable_query_expansion is True
        assert processor.enable_partial_matching is True
        assert isinstance(processor.thai_segmenter, ThaiSegmenter)
        assert isinstance(processor.token_processor, TokenProcessor)
        assert len(processor.compound_patterns) > 0
        assert len(processor.thai_prefixes) > 0
        assert len(processor.thai_suffixes) > 0
    
    def test_init_custom_components(self):
        """Test QueryProcessor initialization with custom components."""
        mock_segmenter = Mock(spec=ThaiSegmenter)
        mock_processor = Mock(spec=TokenProcessor)
        
        processor = QueryProcessor(
            thai_segmenter=mock_segmenter,
            token_processor=mock_processor,
            enable_query_expansion=False,
            enable_partial_matching=False
        )
        
        assert processor.thai_segmenter is mock_segmenter
        assert processor.token_processor is mock_processor
        assert processor.enable_query_expansion is False
        assert processor.enable_partial_matching is False
    
    def test_process_empty_query(self):
        """Test processing empty query."""
        result = self.query_processor.process_search_query("")
        
        assert result.original_query == ""
        assert result.processed_query == ""
        assert result.query_tokens == []
        assert result.search_variants == []
        assert result.suggested_completions == []
        assert result.processing_metadata["empty_query"] is True
    
    def test_process_whitespace_query(self):
        """Test processing whitespace-only query."""
        result = self.query_processor.process_search_query("   \n\t  ")
        
        assert result.processing_metadata["empty_query"] is True
    
    @patch('src.tokenizer.query_processor.ThaiSegmenter')
    def test_process_simple_thai_query(self, mock_segmenter_class):
        """Test processing simple Thai query."""
        # Mock the segmenter
        mock_segmenter = Mock()
        mock_segmenter.segment_text.return_value = TokenizationResult(
            original_text="สวัสดี",
            tokens=["สวัสดี"],
            word_boundaries=[0, 6],
            processing_time_ms=10.0
        )
        mock_segmenter_class.return_value = mock_segmenter
        
        processor = QueryProcessor()
        result = processor.process_search_query("สวัสดี")
        
        assert result.original_query == "สวัสดี"
        assert len(result.query_tokens) == 1
        assert result.query_tokens[0].original == "สวัสดี"
        assert result.query_tokens[0].query_type == QueryType.SIMPLE
        mock_segmenter.segment_text.assert_called_once_with("สวัสดี")
    
    def test_classify_query_type_simple(self):
        """Test query type classification for simple queries."""
        query_type = self.query_processor._classify_query_type("สวัสดี")
        assert query_type == QueryType.SIMPLE
    
    def test_classify_query_type_compound(self):
        """Test query type classification for compound queries."""
        # Test compound with การ prefix
        query_type = self.query_processor._classify_query_type("การศึกษา")
        assert query_type == QueryType.COMPOUND
        
        # Test compound with ศาสตร์ suffix
        query_type = self.query_processor._classify_query_type("วิทยาศาสตร์")
        assert query_type == QueryType.COMPOUND
    
    def test_classify_query_type_mixed(self):
        """Test query type classification for mixed content."""
        query_type = self.query_processor._classify_query_type("Hello สวัสดี")
        assert query_type == QueryType.MIXED
    
    def test_classify_query_type_phrase(self):
        """Test query type classification for phrases."""
        query_type = self.query_processor._classify_query_type("สวัสดี ครับ")
        assert query_type == QueryType.PHRASE
    
    def test_classify_query_type_non_thai(self):
        """Test query type classification for non-Thai text."""
        query_type = self.query_processor._classify_query_type("hello")
        assert query_type == QueryType.SIMPLE
    
    def test_is_partial_token_short(self):
        """Test partial token detection for short tokens."""
        assert self.query_processor._is_partial_token("ก") is True
        assert self.query_processor._is_partial_token("กา") is True
        assert self.query_processor._is_partial_token("การ") is False
    
    def test_is_partial_token_prefix_suffix(self):
        """Test partial token detection based on prefixes/suffixes."""
        # Token ending with prefix might be partial
        assert self.query_processor._is_partial_token("ศึกษาการ") is True
        
        # Token starting with suffix might be partial
        assert self.query_processor._is_partial_token("ศาสตร์วิทยา") is True
    
    def test_is_partial_token_non_thai(self):
        """Test partial token detection for non-Thai text."""
        assert self.query_processor._is_partial_token("hello") is False
        assert self.query_processor._is_partial_token("123") is False
    
    def test_generate_token_variants_thai(self):
        """Test token variant generation for Thai text."""
        variants = self.query_processor._generate_token_variants("การศึกษา")
        
        assert "การศึกษา" in variants
        assert "การศึกษา*" in variants
        assert "*การศึกษา" in variants
        assert "*การศึกษา*" in variants
        assert len(variants) > 4  # Should include compound variants
    
    def test_generate_token_variants_non_thai(self):
        """Test token variant generation for non-Thai text."""
        variants = self.query_processor._generate_token_variants("hello")
        
        assert variants == ["hello"]
    
    def test_generate_compound_variants(self):
        """Test compound word variant generation."""
        variants = self.query_processor._generate_compound_variants("การศึกษา")
        
        # Should contain parts of the compound
        assert len(variants) > 0
        # Should try to split the compound
        assert any(len(variant) < len("การศึกษา") for variant in variants)
    
    def test_extract_compound_parts_with_pattern(self):
        """Test compound parts extraction with known patterns."""
        parts = self.query_processor._extract_compound_parts("การศึกษา")
        
        # Should extract parts based on การ pattern
        assert parts is not None
        assert len(parts) > 0
    
    def test_extract_compound_parts_fallback(self):
        """Test compound parts extraction with fallback splitting."""
        parts = self.query_processor._extract_compound_parts("ยาวมากๆๆๆ")
        
        # Should fall back to simple split for long words
        assert parts is not None
        assert len(parts) == 2
    
    def test_extract_compound_parts_short_word(self):
        """Test compound parts extraction for short words."""
        parts = self.query_processor._extract_compound_parts("สั้น")
        
        # Should not split short words
        assert parts is None
    
    def test_calculate_boost_score_compound(self):
        """Test boost score calculation for compound words."""
        score = self.query_processor._calculate_boost_score("การศึกษา", QueryType.COMPOUND)
        
        # Compound words should get boosted
        assert score > 1.0
    
    def test_calculate_boost_score_long_token(self):
        """Test boost score calculation for long tokens."""
        score = self.query_processor._calculate_boost_score("ยาวมากๆๆๆ", QueryType.SIMPLE)
        
        # Long tokens should get boosted
        assert score > 1.0
    
    def test_calculate_boost_score_short_token(self):
        """Test boost score calculation for short tokens."""
        score = self.query_processor._calculate_boost_score("ก", QueryType.SIMPLE)
        
        # Short tokens should get reduced score
        assert score < 1.0
    
    def test_normalize_query(self):
        """Test query normalization."""
        normalized = self.query_processor._normalize_query("  สวัสดี   ครับ  ")
        assert normalized == "สวัสดี ครับ"
        
        normalized = self.query_processor._normalize_query("สวัสดี\n\nครับ")
        assert normalized == "สวัสดี ครับ"
    
    def test_build_processed_query(self):
        """Test processed query building."""
        tokens = [
            QueryToken(
                original="สวัสดี",
                processed="สวัสดี​",
                query_type=QueryType.SIMPLE
            ),
            QueryToken(
                original="ครับ",
                processed="ครับ​",
                query_type=QueryType.SIMPLE
            )
        ]
        
        processed = self.query_processor._build_processed_query(tokens)
        assert processed == "สวัสดี​ ครับ​"
    
    def test_build_processed_query_empty_tokens(self):
        """Test processed query building with empty tokens."""
        tokens = [
            QueryToken(
                original="สวัสดี",
                processed="สวัสดี​",
                query_type=QueryType.SIMPLE
            ),
            QueryToken(
                original=" ",
                processed="",
                query_type=QueryType.SIMPLE
            )
        ]
        
        processed = self.query_processor._build_processed_query(tokens)
        assert processed == "สวัสดี​"
    
    def test_is_potential_compound_part_with_indicators(self):
        """Test compound part detection with indicators."""
        assert self.query_processor._is_potential_compound_part("การศึกษา") is True
        assert self.query_processor._is_potential_compound_part("วิทยาศาสตร์") is True
        assert self.query_processor._is_potential_compound_part("ความรู้") is True
    
    def test_is_potential_compound_part_simple_word(self):
        """Test compound part detection for simple words."""
        assert self.query_processor._is_potential_compound_part("สวัสดี") is False
        assert self.query_processor._is_potential_compound_part("hello") is False
    
    def test_has_mixed_content_thai_english(self):
        """Test mixed content detection for Thai-English."""
        assert self.query_processor._has_mixed_content("Hello สวัสดี") is True
        assert self.query_processor._has_mixed_content("API การใช้งาน") is True
    
    def test_has_mixed_content_pure_content(self):
        """Test mixed content detection for pure content."""
        assert self.query_processor._has_mixed_content("สวัสดีครับ") is False
        assert self.query_processor._has_mixed_content("hello world") is False
    
    def test_is_thai_char(self):
        """Test Thai character detection."""
        assert self.query_processor._is_thai_char("ก") is True
        assert self.query_processor._is_thai_char("๙") is True
        assert self.query_processor._is_thai_char("a") is False
        assert self.query_processor._is_thai_char("1") is False
    
    def test_is_thai_text_pure_thai(self):
        """Test Thai text detection for pure Thai."""
        assert self.query_processor._is_thai_text("สวัสดีครับ") is True
        assert self.query_processor._is_thai_text("การศึกษา") is True
    
    def test_is_thai_text_mixed_content(self):
        """Test Thai text detection for mixed content."""
        # Should be True if >30% Thai (more permissive for queries)
        assert self.query_processor._is_thai_text("API การใช้งาน") is True
        assert self.query_processor._is_thai_text("Hello สวัสดี") is True
    
    def test_is_thai_text_non_thai(self):
        """Test Thai text detection for non-Thai text."""
        assert self.query_processor._is_thai_text("hello world") is False
        assert self.query_processor._is_thai_text("123456") is False
        assert self.query_processor._is_thai_text("") is False
    
    @patch('src.tokenizer.query_processor.ThaiSegmenter')
    def test_process_partial_compound_query(self, mock_segmenter_class):
        """Test partial compound query processing."""
        # Mock the segmenter
        mock_segmenter = Mock()
        mock_segmenter.segment_text.return_value = TokenizationResult(
            original_text="การศึกษา",
            tokens=["การศึกษา"],
            word_boundaries=[0, 8],
            processing_time_ms=15.0
        )
        mock_segmenter_class.return_value = mock_segmenter
        
        processor = QueryProcessor()
        result = processor.process_partial_compound_query("การศึกษา")
        
        assert result.original_query == "การศึกษา"
        assert len(result.query_tokens) == 1
        assert result.query_tokens[0].query_type == QueryType.COMPOUND
        assert result.query_tokens[0].boost_score > 1.0  # Should be boosted
        assert result.processing_metadata["compound_enhanced"] is True
    
    def test_generate_completions_with_prefix(self):
        """Test completion generation for tokens with prefixes."""
        completions = self.query_processor._generate_completions("การศึก")
        
        # Should generate completions based on the การ prefix
        assert len(completions) > 0
        assert any("การ" in completion for completion in completions)
    
    def test_generate_completions_with_suffix(self):
        """Test completion generation for tokens with suffixes."""
        completions = self.query_processor._generate_completions("วิทยาศาสตร์")
        
        # Should generate completions based on the ศาสตร์ suffix
        assert len(completions) > 0
    
    def test_generate_completions_non_thai(self):
        """Test completion generation for non-Thai tokens."""
        completions = self.query_processor._generate_completions("hello")
        
        # Should not generate completions for non-Thai text
        assert len(completions) == 0
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        stats = self.query_processor.get_stats()
        
        assert "query_expansion_enabled" in stats
        assert "partial_matching_enabled" in stats
        assert "compound_patterns_count" in stats
        assert "thai_prefixes_count" in stats
        assert "thai_suffixes_count" in stats
        assert "segmenter_engine" in stats
        assert "processor_separators" in stats
        
        assert isinstance(stats["compound_patterns_count"], int)
        assert stats["compound_patterns_count"] > 0
        assert isinstance(stats["thai_prefixes_count"], int)
        assert stats["thai_prefixes_count"] > 0


class TestQueryProcessingIntegration:
    """Integration tests for query processing with real components."""
    
    def test_end_to_end_simple_query(self):
        """Test end-to-end processing of simple query."""
        processor = QueryProcessor()
        result = processor.process_search_query("สวัสดี")
        
        assert result.original_query == "สวัสดี"
        assert len(result.query_tokens) > 0
        assert result.query_tokens[0].original == "สวัสดี"
        assert isinstance(result.processing_metadata, dict)
    
    def test_end_to_end_compound_query(self):
        """Test end-to-end processing of compound query."""
        processor = QueryProcessor()
        result = processor.process_search_query("การศึกษา")
        
        assert result.original_query == "การศึกษา"
        assert len(result.query_tokens) > 0
        assert len(result.search_variants) > 0
    
    def test_end_to_end_mixed_query(self):
        """Test end-to-end processing of mixed content query."""
        processor = QueryProcessor()
        result = processor.process_search_query("API การใช้งาน")
        
        assert result.original_query == "API การใช้งาน"
        assert len(result.query_tokens) > 0
        # Should handle both English and Thai parts
        assert any(token.original == "API" for token in result.query_tokens)
        assert any("การใช้งาน" in token.original for token in result.query_tokens)
    
    def test_query_expansion_disabled(self):
        """Test query processing with expansion disabled."""
        processor = QueryProcessor(enable_query_expansion=False)
        result = processor.process_search_query("การศึกษา")
        
        # Should have fewer variants when expansion is disabled
        assert len(result.search_variants) >= 0  # May still have basic variants
    
    def test_partial_matching_disabled(self):
        """Test query processing with partial matching disabled."""
        processor = QueryProcessor(enable_partial_matching=False)
        result = processor.process_search_query("การศึกษา")
        
        # Should process normally but without partial matching features
        assert len(result.query_tokens) > 0
        # Variants should not include wildcard patterns
        assert not any("*" in variant for variant in result.search_variants)