"""
Unit tests for Thai word segmentation module.

Tests various Thai text patterns including compound words, mixed content,
and edge cases to ensure accurate tokenization.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.tokenizer.thai_segmenter import ThaiSegmenter, TokenizationResult


class TestThaiSegmenter:
    """Test cases for ThaiSegmenter class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.segmenter = ThaiSegmenter()
    
    def test_initialization_default(self):
        """Test default initialization."""
        segmenter = ThaiSegmenter()
        assert segmenter.engine == "newmm"
        assert segmenter.keep_whitespace is True
        assert segmenter.custom_dict == []
    
    def test_initialization_custom(self):
        """Test initialization with custom parameters."""
        custom_dict = ["คำศัพท์", "เทคนิค"]
        segmenter = ThaiSegmenter(
            engine="attacut",
            custom_dict=custom_dict,
            keep_whitespace=False
        )
        assert segmenter.engine == "attacut"
        assert segmenter.keep_whitespace is False
        assert segmenter.custom_dict == custom_dict
    
    def test_segment_empty_text(self):
        """Test segmentation of empty text."""
        result = self.segmenter.segment_text("")
        assert result.original_text == ""
        assert result.tokens == []
        assert result.word_boundaries == []
        assert result.engine == "newmm"
    
    def test_segment_whitespace_only(self):
        """Test segmentation of whitespace-only text."""
        result = self.segmenter.segment_text("   ")
        assert result.original_text == "   "
        assert result.tokens == []
        assert result.word_boundaries == []
    
    def test_segment_simple_thai_text(self):
        """Test segmentation of simple Thai text."""
        text = "สวัสดี"
        result = self.segmenter.segment_text(text)
        
        assert result.original_text == text
        assert len(result.tokens) >= 1
        assert result.processing_time_ms > 0
        assert result.engine.startswith("newmm")
    
    def test_segment_compound_words(self):
        """Test segmentation of Thai compound words."""
        test_cases = [
            {
                "text": "รถยนต์ไฟฟ้า",  # Electric car
                "description": "Technical compound term",
                "min_tokens": 1  # Some compounds might not be split
            },
            {
                "text": "โรงเรียนมัธยมศึกษา",  # Secondary school
                "description": "Educational compound term",
                "min_tokens": 1
            },
            {
                "text": "ความรับผิดชอบ",  # Responsibility
                "description": "Abstract concept compound",
                "min_tokens": 1
            },
            {
                "text": "เทคโนโลยีสารสนเทศ",  # Information technology
                "description": "Technical compound with foreign origin",
                "min_tokens": 1
            }
        ]
        
        for case in test_cases:
            result = self.segmenter.segment_compound_words(case["text"])
            assert result.original_text == case["text"]
            assert len(result.tokens) >= case["min_tokens"], \
                f"Failed for {case['description']}: got {result.tokens}"
            assert result.processing_time_ms > 0
            
            # Test that compound word processing at least attempts enhancement
            regular_result = self.segmenter.segment_text(case["text"])
            # Compound processing should not produce fewer tokens than regular
            assert len(result.tokens) >= len(regular_result.tokens)
    
    def test_segment_mixed_content(self):
        """Test segmentation of mixed Thai-English content."""
        text = "Hello สวัสดี World โลก"
        result = self.segmenter.segment_text(text)
        
        assert result.original_text == text
        assert len(result.tokens) > 2
        # Should contain both Thai and English tokens
        thai_tokens = [t for t in result.tokens if self.segmenter._is_thai_text(t)]
        english_tokens = [t for t in result.tokens if not self.segmenter._is_thai_text(t) and t.strip()]
        
        assert len(thai_tokens) > 0, f"No Thai tokens found in: {result.tokens}"
        assert len(english_tokens) > 0, f"No English tokens found in: {result.tokens}"
    
    def test_segment_numbers_and_punctuation(self):
        """Test segmentation with numbers and punctuation."""
        text = "ราคา 1,500 บาท!"
        result = self.segmenter.segment_text(text)
        
        assert result.original_text == text
        assert len(result.tokens) > 1
        # Should preserve numbers and punctuation
        assert any("1,500" in token or "1500" in token for token in result.tokens)
    
    def test_segment_special_characters(self):
        """Test segmentation with Thai special characters."""
        text = "ๆ ฯลฯ ฯ"  # Thai repetition and abbreviation marks
        result = self.segmenter.segment_text(text)
        
        assert result.original_text == text
        assert len(result.tokens) > 0
    
    def test_word_boundaries_calculation(self):
        """Test word boundary calculation accuracy."""
        text = "สวัสดี โลก"
        result = self.segmenter.segment_text(text)
        
        # Boundaries should start with 0 and end with text length
        assert result.word_boundaries[0] == 0
        assert result.word_boundaries[-1] <= len(text)
        # Should have one more boundary than tokens
        assert len(result.word_boundaries) == len(result.tokens) + 1
    
    def test_is_thai_char(self):
        """Test Thai character detection."""
        assert self.segmenter._is_thai_char('ก')
        assert self.segmenter._is_thai_char('๙')
        assert not self.segmenter._is_thai_char('a')
        assert not self.segmenter._is_thai_char('1')
        assert not self.segmenter._is_thai_char(' ')
    
    def test_is_thai_text(self):
        """Test Thai text detection."""
        assert self.segmenter._is_thai_text("สวัสดี")
        assert self.segmenter._is_thai_text("สวัสดี123")  # Mixed but majority Thai
        assert not self.segmenter._is_thai_text("Hello")
        assert not self.segmenter._is_thai_text("123")
        assert not self.segmenter._is_thai_text("")
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        stats = self.segmenter.get_stats()
        
        assert "engine" in stats
        assert "custom_dict_size" in stats
        assert "keep_whitespace" in stats
        assert "has_custom_tokenizer" in stats
        
        assert stats["engine"] == "newmm"
        assert stats["custom_dict_size"] == 0
        assert stats["keep_whitespace"] is True
        assert stats["has_custom_tokenizer"] is False
    
    @patch('src.tokenizer.thai_segmenter.word_tokenize')
    def test_tokenization_error_fallback(self, mock_tokenize):
        """Test fallback behavior when tokenization fails."""
        mock_tokenize.side_effect = Exception("Tokenization failed")
        
        text = "สวัสดี"
        result = self.segmenter.segment_text(text)
        
        assert result.original_text == text
        assert len(result.tokens) > 0
        assert result.engine == "fallback_char"
    
    def test_custom_dictionary_integration(self):
        """Test custom dictionary integration."""
        custom_dict = ["เทคโนโลยี", "สารสนเทศ"]
        segmenter = ThaiSegmenter(custom_dict=custom_dict)
        
        stats = segmenter.get_stats()
        assert stats["custom_dict_size"] == 2
        assert stats["has_custom_tokenizer"] is True
    
    def test_performance_measurement(self):
        """Test that processing time is measured."""
        text = "สวัสดีครับ ผมชื่อ จอห์น"
        result = self.segmenter.segment_text(text)
        
        assert result.processing_time_ms > 0
        assert result.processing_time_ms < 1000  # Should be fast for short text
    
    def test_long_text_segmentation(self):
        """Test segmentation of longer Thai text."""
        text = (
            "ประเทศไทยเป็นประเทศที่มีวัฒนธรรมและประเพณีที่หลากหลาย "
            "มีภาษาไทยเป็นภาษาราชการ และมีระบบการศึกษาที่พัฒนาอย่างต่อเนื่อง"
        )
        result = self.segmenter.segment_text(text)
        
        assert result.original_text == text
        assert len(result.tokens) > 10  # Should segment into many tokens
        assert result.processing_time_ms > 0
    
    def test_compound_word_enhancement(self):
        """Test compound word enhancement functionality."""
        # Text with potential compound words
        text = "เทคโนโลยีสารสนเทศและการสื่อสาร"
        
        regular_result = self.segmenter.segment_text(text)
        compound_result = self.segmenter.segment_compound_words(text)
        
        # Compound segmentation might produce more tokens
        assert compound_result.original_text == text
        assert len(compound_result.tokens) >= len(regular_result.tokens)
    
    def test_whitespace_handling(self):
        """Test whitespace handling in different modes."""
        text = "สวัสดี โลก"
        
        # With whitespace preservation
        segmenter_with_ws = ThaiSegmenter(keep_whitespace=True)
        result_with_ws = segmenter_with_ws.segment_text(text)
        
        # Without whitespace preservation
        segmenter_no_ws = ThaiSegmenter(keep_whitespace=False)
        result_no_ws = segmenter_no_ws.segment_text(text)
        
        # Results should differ in whitespace handling
        assert result_with_ws.original_text == text
        assert result_no_ws.original_text == text
        
        # With whitespace should have more tokens (including spaces)
        ws_tokens = [t for t in result_with_ws.tokens if t.strip()]
        no_ws_tokens = [t for t in result_no_ws.tokens if t.strip()]
        
        assert len(ws_tokens) >= len(no_ws_tokens)


class TestTokenizationResult:
    """Test cases for TokenizationResult dataclass."""
    
    def test_tokenization_result_creation(self):
        """Test TokenizationResult creation and attributes."""
        result = TokenizationResult(
            original_text="สวัสดี",
            tokens=["สวัสดี"],
            word_boundaries=[0, 6],
            confidence_scores=[0.95],
            processing_time_ms=10.5,
            engine="newmm"
        )
        
        assert result.original_text == "สวัสดี"
        assert result.tokens == ["สวัสดี"]
        assert result.word_boundaries == [0, 6]
        assert result.confidence_scores == [0.95]
        assert result.processing_time_ms == 10.5
        assert result.engine == "newmm"
    
    def test_tokenization_result_defaults(self):
        """Test TokenizationResult with default values."""
        result = TokenizationResult(
            original_text="test",
            tokens=["test"],
            word_boundaries=[0, 4]
        )
        
        assert result.confidence_scores is None
        assert result.processing_time_ms == 0.0
        assert result.engine == "newmm"


@pytest.fixture
def sample_thai_texts():
    """Fixture providing sample Thai texts for testing."""
    return {
        "simple": "สวัสดี",
        "compound": "รถยนต์ไฟฟ้า",
        "mixed": "Hello สวัสดี World",
        "long": "ประเทศไทยมีวัฒนธรรมที่หลากหลายและมีประวัติศาสตร์ยาวนาน",
        "technical": "เทคโนโลยีสารสนเทศและการสื่อสาร",
        "formal": "กระทรวงศึกษาธิการได้ประกาศนโยบายการศึกษา",
        "informal": "เฮ้ย! ไปไหนมา กินข้าวยัง",
        "numbers": "ราคา 1,500 บาท ลดราคา 20%",
        "punctuation": "สวัสดีครับ! คุณสบายดีไหม?",
        "special_chars": "ๆ ฯลฯ ฯ"
    }


class TestThaiSegmenterIntegration:
    """Integration tests using sample Thai texts."""
    
    def test_various_text_patterns(self, sample_thai_texts):
        """Test segmentation across various Thai text patterns."""
        segmenter = ThaiSegmenter()
        
        for text_type, text in sample_thai_texts.items():
            result = segmenter.segment_text(text)
            
            # Basic assertions for all text types
            assert result.original_text == text
            assert len(result.tokens) > 0, f"No tokens for {text_type}: {text}"
            assert result.processing_time_ms >= 0
            assert len(result.word_boundaries) == len(result.tokens) + 1
            
            # Type-specific assertions
            if text_type == "compound":
                compound_result = segmenter.segment_compound_words(text)
                assert len(compound_result.tokens) >= 2, \
                    f"Compound word not properly segmented: {compound_result.tokens}"
            
            elif text_type == "mixed":
                thai_tokens = [t for t in result.tokens if segmenter._is_thai_text(t)]
                assert len(thai_tokens) > 0, "No Thai tokens in mixed content"
            
            elif text_type == "numbers":
                # Should preserve numbers
                has_numbers = any(any(c.isdigit() for c in token) for token in result.tokens)
                assert has_numbers, "Numbers not preserved in tokenization"