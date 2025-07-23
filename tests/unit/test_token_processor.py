"""
Unit tests for token processing utilities.

Tests token processing for MeiliSearch compatibility, including
custom separator insertion and mixed content handling.
"""

import pytest
from unittest.mock import patch, MagicMock

from src.tokenizer.token_processor import (
    TokenProcessor, ProcessedToken, TokenProcessingResult,
    ContentType
)
from src.tokenizer.thai_segmenter import TokenizationResult


class TestTokenProcessor:
    """Test cases for TokenProcessor class."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.processor = TokenProcessor()
    
    def test_initialization_default(self):
        """Test default initialization."""
        processor = TokenProcessor()
        assert processor.preserve_original is True
        assert processor.handle_compounds is True
        assert len(processor.separators) > 0
        assert TokenProcessor.THAI_WORD_SEPARATOR in processor.separators
    
    def test_initialization_custom(self):
        """Test initialization with custom parameters."""
        custom_seps = ["@", "#"]
        processor = TokenProcessor(
            custom_separators=custom_seps,
            preserve_original=False,
            handle_compounds=False
        )
        
        assert processor.preserve_original is False
        assert processor.handle_compounds is False
        assert "@" in processor.separators
        assert "#" in processor.separators
    
    def test_process_empty_tokenization_result(self):
        """Test processing empty tokenization result."""
        empty_result = TokenizationResult(
            original_text="",
            tokens=[],
            word_boundaries=[]
        )
        
        result = self.processor.process_tokenization_result(empty_result)
        
        assert result.original_text == ""
        assert result.processed_text == ""
        assert result.tokens == []
        assert result.processing_metadata["empty_input"] is True
    
    def test_process_simple_thai_tokenization(self):
        """Test processing simple Thai tokenization result."""
        tokenization_result = TokenizationResult(
            original_text="สวัสดี",
            tokens=["สวัสดี"],
            word_boundaries=[0, 6]
        )
        
        result = self.processor.process_tokenization_result(tokenization_result)
        
        assert result.original_text == "สวัสดี"
        assert len(result.tokens) == 1
        assert result.tokens[0].content_type == ContentType.THAI
        assert result.tokens[0].original == "สวัสดี"
        assert TokenProcessor.THAI_WORD_SEPARATOR in result.tokens[0].processed
    
    def test_process_mixed_thai_english_tokenization(self):
        """Test processing mixed Thai-English content."""
        tokenization_result = TokenizationResult(
            original_text="Hello สวัสดี",
            tokens=["Hello", " ", "สวัสดี"],
            word_boundaries=[0, 5, 6, 12]
        )
        
        result = self.processor.process_tokenization_result(tokenization_result)
        
        assert result.original_text == "Hello สวัสดี"
        assert len(result.tokens) == 3
        
        # Check content types
        content_types = [token.content_type for token in result.tokens]
        assert ContentType.ENGLISH in content_types
        assert ContentType.THAI in content_types
        assert ContentType.WHITESPACE in content_types
    
    def test_classify_content_type(self):
        """Test content type classification."""
        test_cases = [
            ("สวัสดี", ContentType.THAI),
            ("Hello", ContentType.ENGLISH),
            ("123", ContentType.NUMERIC),
            ("!!!", ContentType.PUNCTUATION),
            ("   ", ContentType.WHITESPACE),
            ("Hi1!", ContentType.MIXED),  # Balanced mixed content: 2 letters, 1 digit, 1 punct
            ("", ContentType.WHITESPACE)
        ]
        
        for text, expected_type in test_cases:
            result_type = self.processor._classify_content_type(text)
            assert result_type == expected_type, f"Failed for '{text}': got {result_type}, expected {expected_type}"
    
    def test_process_single_token_thai(self):
        """Test processing single Thai token."""
        token = "สวัสดี"
        processed_token = self.processor._process_single_token(token)
        
        assert processed_token.original == token
        assert processed_token.content_type == ContentType.THAI
        assert TokenProcessor.THAI_WORD_SEPARATOR in processed_token.processed
        assert processed_token.is_compound is False
    
    def test_process_single_token_english(self):
        """Test processing single English token."""
        token = "Hello"
        processed_token = self.processor._process_single_token(token)
        
        assert processed_token.original == token
        assert processed_token.content_type == ContentType.ENGLISH
        assert processed_token.processed.strip() == token
        assert processed_token.is_compound is False
    
    def test_process_single_token_whitespace(self):
        """Test processing whitespace token."""
        token = "   "
        processed_token = self.processor._process_single_token(token)
        
        assert processed_token.original == token
        assert processed_token.content_type == ContentType.WHITESPACE
        assert processed_token.processed == token
    
    def test_compound_word_detection(self):
        """Test compound word detection."""
        # Long Thai words that might be compounds
        potential_compounds = [
            "เทคโนโลยีสารสนเทศ",  # Information technology
            "รถยนต์ไฟฟ้า",  # Electric car
            "โรงเรียนมัธยมศึกษา"  # Secondary school
        ]
        
        for word in potential_compounds:
            is_compound = self.processor._is_potential_compound(word)
            # Should detect as potential compound (long Thai text)
            assert is_compound, f"Should detect '{word}' as potential compound"
    
    def test_compound_word_processing(self):
        """Test compound word processing with separators."""
        processor = TokenProcessor(handle_compounds=True)
        
        # Long Thai word that should be processed as compound
        token = "เทคโนโลยีสารสนเทศ"
        processed_token = processor._process_single_token(token)
        
        assert processed_token.original == token
        assert processed_token.content_type == ContentType.THAI
        # Should contain word separator
        assert TokenProcessor.THAI_WORD_SEPARATOR in processed_token.processed
    
    def test_mixed_content_processing(self):
        """Test mixed content processing."""
        text = "Hello สวัสดี World โลก 123"
        result = self.processor.process_mixed_content(text)
        
        assert result.original_text == text
        assert len(result.tokens) > 0
        assert result.processing_metadata["mixed_content"] is True
        
        # Should have different content types
        content_types = {token.content_type for token in result.tokens}
        assert len(content_types) > 1  # Mixed content should have multiple types
    
    def test_segment_mixed_content(self):
        """Test mixed content segmentation."""
        text = "Hello สวัสดี 123"
        segments = self.processor._segment_mixed_content(text)
        
        assert len(segments) > 1
        
        # Check that we have different content types
        content_types = {content_type for _, content_type in segments}
        assert ContentType.ENGLISH in content_types
        assert ContentType.THAI in content_types
    
    def test_thai_character_detection(self):
        """Test Thai character detection."""
        assert self.processor._is_thai_char('ก')
        assert self.processor._is_thai_char('๙')
        assert not self.processor._is_thai_char('a')
        assert not self.processor._is_thai_char('1')
        assert not self.processor._is_thai_char(' ')
    
    def test_thai_text_detection(self):
        """Test Thai text detection."""
        assert self.processor._is_thai_text("สวัสดี")
        assert self.processor._is_thai_text("สวัสดี123")  # Majority Thai
        assert not self.processor._is_thai_text("Hello")
        assert not self.processor._is_thai_text("123")
        assert not self.processor._is_thai_text("")
    
    def test_separator_position_finding(self):
        """Test separator position finding."""
        text = f"Hello{TokenProcessor.THAI_WORD_SEPARATOR}World"
        positions = self.processor._find_separator_positions(text)
        
        assert len(positions) > 0
        assert 5 in positions  # Position of separator after "Hello"
    
    def test_meilisearch_settings_generation(self):
        """Test MeiliSearch settings generation."""
        settings = self.processor.get_meilisearch_settings()
        
        assert "separatorTokens" in settings
        assert "nonSeparatorTokens" in settings
        assert "dictionary" in settings
        assert "synonyms" in settings
        assert "stopWords" in settings
        
        # Check that Thai separators are included
        assert TokenProcessor.THAI_WORD_SEPARATOR in settings["separatorTokens"]
        assert TokenProcessor.THAI_COMPOUND_SEPARATOR in settings["separatorTokens"]
        
        # Check Thai stop words
        assert "และ" in settings["stopWords"]  # Thai "and"
        assert "เป็น" in settings["stopWords"]  # Thai "is/are"
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        stats = self.processor.get_stats()
        
        required_keys = [
            "separator_count", "custom_separators", "preserve_original",
            "handle_compounds", "thai_word_separator", "compound_separator"
        ]
        
        for key in required_keys:
            assert key in stats
        
        assert stats["separator_count"] > 0
        assert isinstance(stats["custom_separators"], list)
        assert isinstance(stats["preserve_original"], bool)
        assert isinstance(stats["handle_compounds"], bool)
    
    def test_common_long_word_detection(self):
        """Test detection of common long words that shouldn't be split."""
        common_words = [
            "ประเทศไทย",  # Thailand
            "กรุงเทพมหานคร",  # Bangkok
            "มหาวิทยาลัย"  # University
        ]
        
        for word in common_words:
            is_common = self.processor._is_common_long_word(word)
            assert is_common, f"Should recognize '{word}' as common long word"
    
    def test_compound_word_splitting(self):
        """Test compound word splitting logic."""
        # Test with a potential compound
        compound = "เทคโนโลยีสารสนเทศ"
        sub_tokens = self.processor._split_compound_word(compound)
        
        # Should return at least the original token
        assert len(sub_tokens) >= 1
        assert isinstance(sub_tokens, list)
        assert all(isinstance(token, str) for token in sub_tokens)
    
    def test_processing_metadata(self):
        """Test processing metadata generation."""
        tokenization_result = TokenizationResult(
            original_text="สวัสดี Hello",
            tokens=["สวัสดี", " ", "Hello"],
            word_boundaries=[0, 6, 7, 12],
            processing_time_ms=10.5,
            engine="newmm"
        )
        
        result = self.processor.process_tokenization_result(tokenization_result)
        metadata = result.processing_metadata
        
        assert "original_token_count" in metadata
        assert "processed_token_count" in metadata
        assert "thai_tokens" in metadata
        assert "compound_tokens" in metadata
        assert "processing_engine" in metadata
        assert "processing_time_ms" in metadata
        
        assert metadata["original_token_count"] == 3
        assert metadata["processing_engine"] == "newmm"
        assert metadata["processing_time_ms"] == 10.5


class TestProcessedToken:
    """Test cases for ProcessedToken dataclass."""
    
    def test_processed_token_creation(self):
        """Test ProcessedToken creation and attributes."""
        token = ProcessedToken(
            original="สวัสดี",
            processed="สวัสดี​",
            content_type=ContentType.THAI,
            is_compound=False,
            sub_tokens=None,
            separator_positions=[6]
        )
        
        assert token.original == "สวัสดี"
        assert token.processed == "สวัสดี​"
        assert token.content_type == ContentType.THAI
        assert token.is_compound is False
        assert token.sub_tokens is None
        assert token.separator_positions == [6]
    
    def test_processed_token_defaults(self):
        """Test ProcessedToken with default values."""
        token = ProcessedToken(
            original="test",
            processed="test",
            content_type=ContentType.ENGLISH
        )
        
        assert token.is_compound is False
        assert token.sub_tokens is None
        assert token.separator_positions is None


class TestTokenProcessingResult:
    """Test cases for TokenProcessingResult dataclass."""
    
    def test_token_processing_result_creation(self):
        """Test TokenProcessingResult creation."""
        tokens = [
            ProcessedToken(
                original="สวัสดี",
                processed="สวัสดี​",
                content_type=ContentType.THAI
            )
        ]
        
        result = TokenProcessingResult(
            original_text="สวัสดี",
            processed_text="สวัสดี​",
            tokens=tokens,
            meilisearch_separators=["​", " "],
            processing_metadata={"test": True}
        )
        
        assert result.original_text == "สวัสดี"
        assert result.processed_text == "สวัสดี​"
        assert len(result.tokens) == 1
        assert result.tokens[0].content_type == ContentType.THAI
        assert "​" in result.meilisearch_separators
        assert result.processing_metadata["test"] is True


class TestContentType:
    """Test cases for ContentType enum."""
    
    def test_content_type_values(self):
        """Test ContentType enum values."""
        assert ContentType.THAI.value == "thai"
        assert ContentType.ENGLISH.value == "english"
        assert ContentType.NUMERIC.value == "numeric"
        assert ContentType.PUNCTUATION.value == "punctuation"
        assert ContentType.WHITESPACE.value == "whitespace"
        assert ContentType.MIXED.value == "mixed"


@pytest.fixture
def sample_tokenization_results():
    """Fixture providing sample tokenization results for testing."""
    return {
        "simple_thai": TokenizationResult(
            original_text="สวัสดี",
            tokens=["สวัสดี"],
            word_boundaries=[0, 6]
        ),
        "mixed_content": TokenizationResult(
            original_text="Hello สวัสดี World",
            tokens=["Hello", " ", "สวัสดี", " ", "World"],
            word_boundaries=[0, 5, 6, 12, 13, 18]
        ),
        "compound_word": TokenizationResult(
            original_text="เทคโนโลยีสารสนเทศ",
            tokens=["เทคโนโลยีสารสนเทศ"],
            word_boundaries=[0, 21]
        ),
        "numbers_punctuation": TokenizationResult(
            original_text="ราคา 1,500 บาท!",
            tokens=["ราคา", " ", "1,500", " ", "บาท", "!"],
            word_boundaries=[0, 4, 5, 10, 11, 15, 16]
        )
    }


class TestTokenProcessorIntegration:
    """Integration tests for TokenProcessor with various content types."""
    
    def test_process_various_tokenization_results(self, sample_tokenization_results):
        """Test processing various types of tokenization results."""
        processor = TokenProcessor()
        
        for result_type, tokenization_result in sample_tokenization_results.items():
            processing_result = processor.process_tokenization_result(tokenization_result)
            
            # Basic assertions for all result types
            assert processing_result.original_text == tokenization_result.original_text
            assert len(processing_result.tokens) == len(tokenization_result.tokens)
            assert len(processing_result.meilisearch_separators) > 0
            assert isinstance(processing_result.processing_metadata, dict)
            
            # Type-specific assertions
            if result_type == "simple_thai":
                thai_tokens = [t for t in processing_result.tokens if t.content_type == ContentType.THAI]
                assert len(thai_tokens) == 1
                assert TokenProcessor.THAI_WORD_SEPARATOR in thai_tokens[0].processed
            
            elif result_type == "mixed_content":
                content_types = {t.content_type for t in processing_result.tokens}
                assert ContentType.THAI in content_types
                assert ContentType.ENGLISH in content_types
            
            elif result_type == "compound_word":
                compound_tokens = [t for t in processing_result.tokens if t.is_compound]
                # May or may not detect as compound depending on implementation
                assert len(processing_result.tokens) >= 1
            
            elif result_type == "numbers_punctuation":
                content_types = {t.content_type for t in processing_result.tokens}
                assert ContentType.NUMERIC in content_types
                assert ContentType.PUNCTUATION in content_types
    
    def test_end_to_end_processing(self):
        """Test end-to-end processing from segmentation to MeiliSearch format."""
        from src.tokenizer.thai_segmenter import ThaiSegmenter
        
        # Create segmenter and processor
        segmenter = ThaiSegmenter()
        processor = TokenProcessor()
        
        # Test text with various content types
        text = "สวัสดี Hello เทคโนโลยี 123 !"
        
        # Segment text
        segmentation_result = segmenter.segment_text(text)
        
        # Process for MeiliSearch
        processing_result = processor.process_tokenization_result(segmentation_result)
        
        # Verify end-to-end processing
        assert processing_result.original_text == text
        assert len(processing_result.tokens) > 0
        assert len(processing_result.meilisearch_separators) > 0
        
        # Check that MeiliSearch settings are valid
        settings = processor.get_meilisearch_settings()
        assert isinstance(settings, dict)
        assert "separatorTokens" in settings
        assert TokenProcessor.THAI_WORD_SEPARATOR in settings["separatorTokens"]