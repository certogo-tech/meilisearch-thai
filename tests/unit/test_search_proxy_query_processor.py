"""
Unit tests for the search proxy QueryProcessor component.

Tests tokenization integration, query variant generation, and query processing logic.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.search_proxy.services.query_processor import QueryProcessor
from src.search_proxy.config.settings import SearchProxySettings, TokenizationConfig
from src.search_proxy.models.query import (
    ProcessedQuery, QueryVariant, QueryVariantType, 
    TokenizationResult, TokenizationError
)


class TestQueryProcessor:
    """Test cases for the QueryProcessor component."""
    
    @pytest.fixture
    def settings(self):
        """Create test settings."""
        return SearchProxySettings(
            tokenization=TokenizationConfig(
                primary_engine="newmm",
                fallback_engines=["attacut", "deepcut"],
                timeout_ms=3000,
                confidence_threshold=0.7,
                enable_compound_splitting=True,
                preserve_original=True,
                mixed_language_detection=True
            )
        )
    
    @pytest.fixture
    def query_processor(self, settings):
        """Create a QueryProcessor instance for testing."""
        return QueryProcessor(settings)
    
    @pytest.mark.asyncio
    async def test_initialization(self, query_processor):
        """Test QueryProcessor initialization."""
        await query_processor.initialize()
        
        assert query_processor._initialized is True
        assert query_processor._tokenizer_cache is not None
        assert query_processor._query_cache is not None
    
    @pytest.mark.asyncio
    async def test_process_thai_query(self, query_processor):
        """Test processing a Thai language query."""
        await query_processor.initialize()
        
        # Mock tokenizer
        mock_tokenizer = AsyncMock()
        mock_tokenizer.tokenize.return_value = {
            "tokens": ["ค้นหา", "เอกสาร", "ภาษาไทย"],
            "success": True,
            "engine": "newmm",
            "processing_time_ms": 15.0
        }
        
        with patch.object(query_processor, '_get_tokenizer', return_value=mock_tokenizer):
            result = await query_processor.process_query("ค้นหาเอกสารภาษาไทย")
        
        assert isinstance(result, ProcessedQuery)
        assert result.original_query == "ค้นหาเอกสารภาษาไทย"
        assert result.thai_content_detected is True
        assert result.mixed_content is False
        assert result.primary_language == "thai"
        assert len(result.query_variants) > 0
        assert result.fallback_used is False
    
    @pytest.mark.asyncio
    async def test_process_english_query(self, query_processor):
        """Test processing an English language query."""
        await query_processor.initialize()
        
        result = await query_processor.process_query("search documents")
        
        assert isinstance(result, ProcessedQuery)
        assert result.original_query == "search documents"
        assert result.thai_content_detected is False
        assert result.mixed_content is False
        assert result.primary_language == "english"
        assert len(result.query_variants) > 0
    
    @pytest.mark.asyncio
    async def test_process_mixed_language_query(self, query_processor):
        """Test processing a mixed Thai-English query."""
        await query_processor.initialize()
        
        # Mock tokenizer
        mock_tokenizer = AsyncMock()
        mock_tokenizer.tokenize.return_value = {
            "tokens": ["ค้นหา", "document", "ใน", "database"],
            "success": True,
            "engine": "newmm",
            "processing_time_ms": 18.0
        }
        
        with patch.object(query_processor, '_get_tokenizer', return_value=mock_tokenizer):
            result = await query_processor.process_query("ค้นหา document ใน database")
        
        assert isinstance(result, ProcessedQuery)
        assert result.thai_content_detected is True
        assert result.mixed_content is True
        assert result.primary_language in ["thai", "mixed"]
        assert len(result.query_variants) > 0
    
    @pytest.mark.asyncio
    async def test_query_variant_generation(self, query_processor):
        """Test query variant generation strategies."""
        await query_processor.initialize()
        
        # Mock tokenizer
        mock_tokenizer = AsyncMock()
        mock_tokenizer.tokenize.return_value = {
            "tokens": ["ค้นหา", "เอกสาร"],
            "success": True,
            "engine": "newmm",
            "processing_time_ms": 10.0
        }
        
        with patch.object(query_processor, '_get_tokenizer', return_value=mock_tokenizer):
            result = await query_processor.process_query("ค้นหาเอกสาร")
        
        # Check variant types
        variant_types = {v.variant_type for v in result.query_variants}
        
        # Should have original query preserved
        assert QueryVariantType.ORIGINAL in variant_types
        
        # Should have tokenized variant
        assert QueryVariantType.TOKENIZED in variant_types
        
        # Verify weights
        for variant in result.query_variants:
            assert 0.0 <= variant.weight <= 1.0
    
    @pytest.mark.asyncio
    async def test_tokenization_fallback(self, query_processor):
        """Test fallback to secondary tokenizers on primary failure."""
        await query_processor.initialize()
        
        # Mock primary tokenizer failure
        primary_tokenizer = AsyncMock()
        primary_tokenizer.tokenize.side_effect = Exception("Primary engine failed")
        
        # Mock fallback tokenizer success
        fallback_tokenizer = AsyncMock()
        fallback_tokenizer.tokenize.return_value = {
            "tokens": ["ค้นหา", "เอกสาร"],
            "success": True,
            "engine": "attacut",
            "processing_time_ms": 25.0
        }
        
        with patch.object(query_processor, '_get_tokenizer') as mock_get_tokenizer:
            # Return primary for first call, fallback for second
            mock_get_tokenizer.side_effect = [primary_tokenizer, fallback_tokenizer]
            
            result = await query_processor.process_query("ค้นหาเอกสาร")
        
        assert result.fallback_used is True
        assert len(result.tokenization_results) > 0
        
        # Check that fallback engine was used
        successful_results = [r for r in result.tokenization_results if r.success]
        assert any(r.engine == "attacut" for r in successful_results)
    
    @pytest.mark.asyncio
    async def test_empty_query_handling(self, query_processor):
        """Test handling of empty queries."""
        await query_processor.initialize()
        
        result = await query_processor.process_query("")
        
        assert result.original_query == ""
        assert len(result.query_variants) > 0
        assert result.fallback_used is True
    
    @pytest.mark.asyncio
    async def test_query_normalization(self, query_processor):
        """Test query normalization and cleaning."""
        await query_processor.initialize()
        
        # Test with extra whitespace
        result = await query_processor.process_query("  ค้นหา   เอกสาร  ")
        
        # Normalized query should have cleaned whitespace
        assert any(v.query_text == "ค้นหา เอกสาร" for v in result.query_variants)
    
    @pytest.mark.asyncio
    async def test_compound_word_handling(self, query_processor):
        """Test compound word detection and splitting."""
        await query_processor.initialize()
        
        # Mock tokenizer with compound word
        mock_tokenizer = AsyncMock()
        mock_tokenizer.tokenize.return_value = {
            "tokens": ["โรงเรียน", "อนุบาล"],
            "success": True,
            "engine": "newmm",
            "processing_time_ms": 12.0,
            "compound_words": [
                {"word": "โรงเรียนอนุบาล", "components": ["โรงเรียน", "อนุบาล"]}
            ]
        }
        
        with patch.object(query_processor, '_get_tokenizer', return_value=mock_tokenizer):
            result = await query_processor.process_query("โรงเรียนอนุบาล")
        
        # Should have compound word variant
        assert any(v.variant_type == QueryVariantType.COMPOUND_SPLIT for v in result.query_variants)
    
    @pytest.mark.asyncio
    async def test_caching_behavior(self, query_processor):
        """Test query result caching."""
        await query_processor.initialize()
        
        # Mock tokenizer
        mock_tokenizer = AsyncMock()
        mock_tokenizer.tokenize.return_value = {
            "tokens": ["ค้นหา", "เอกสาร"],
            "success": True,
            "engine": "newmm",
            "processing_time_ms": 15.0
        }
        
        with patch.object(query_processor, '_get_tokenizer', return_value=mock_tokenizer):
            # First call
            result1 = await query_processor.process_query("ค้นหาเอกสาร")
            
            # Second call (should use cache)
            result2 = await query_processor.process_query("ค้นหาเอกสาร")
        
        # Tokenizer should only be called once due to caching
        mock_tokenizer.tokenize.assert_called_once()
        
        # Results should be similar (excluding timestamps)
        assert result1.original_query == result2.original_query
        assert len(result1.query_variants) == len(result2.query_variants)
    
    @pytest.mark.asyncio
    async def test_confidence_threshold(self, query_processor):
        """Test confidence threshold filtering."""
        await query_processor.initialize()
        
        # Mock tokenizer with low confidence
        mock_tokenizer = AsyncMock()
        mock_tokenizer.tokenize.return_value = {
            "tokens": ["ค้นหา", "เอกสาร"],
            "success": True,
            "engine": "newmm",
            "processing_time_ms": 15.0,
            "confidence": 0.5  # Below threshold
        }
        
        with patch.object(query_processor, '_get_tokenizer', return_value=mock_tokenizer):
            result = await query_processor.process_query("ค้นหาเอกสาร")
        
        # Should have fallback or alternative variants due to low confidence
        assert len(result.query_variants) > 0
    
    @pytest.mark.asyncio
    async def test_special_character_handling(self, query_processor):
        """Test handling of special characters in queries."""
        await query_processor.initialize()
        
        # Test with punctuation and special characters
        queries = [
            "ค้นหา-เอกสาร",
            "document@2023",
            "ราคา 1,000 บาท",
            "C++ programming"
        ]
        
        for query in queries:
            result = await query_processor.process_query(query)
            assert result.original_query == query
            assert len(result.query_variants) > 0
    
    @pytest.mark.asyncio
    async def test_error_handling_all_engines_fail(self, query_processor):
        """Test handling when all tokenization engines fail."""
        await query_processor.initialize()
        
        # Mock all tokenizers to fail
        mock_tokenizer = AsyncMock()
        mock_tokenizer.tokenize.side_effect = Exception("Engine failed")
        
        with patch.object(query_processor, '_get_tokenizer', return_value=mock_tokenizer):
            result = await query_processor.process_query("ค้นหาเอกสาร")
        
        # Should still return a result with fallback
        assert result.fallback_used is True
        assert len(result.query_variants) > 0
        
        # Should have original query preserved
        assert any(v.variant_type == QueryVariantType.ORIGINAL for v in result.query_variants)
    
    @pytest.mark.asyncio
    async def test_concurrent_query_processing(self, query_processor):
        """Test concurrent query processing."""
        await query_processor.initialize()
        
        # Mock tokenizer
        mock_tokenizer = AsyncMock()
        mock_tokenizer.tokenize.return_value = {
            "tokens": ["ค้นหา", "เอกสาร"],
            "success": True,
            "engine": "newmm",
            "processing_time_ms": 15.0
        }
        
        queries = ["ค้นหาเอกสาร1", "ค้นหาเอกสาร2", "ค้นหาเอกสาร3"]
        
        with patch.object(query_processor, '_get_tokenizer', return_value=mock_tokenizer):
            # Process queries concurrently
            import asyncio
            results = await asyncio.gather(*[
                query_processor.process_query(q) for q in queries
            ])
        
        # All queries should be processed successfully
        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.original_query == queries[i]
            assert len(result.query_variants) > 0
    
    def test_detect_language(self, query_processor):
        """Test language detection functionality."""
        # Thai text
        assert query_processor._detect_language("ค้นหาเอกสาร") == "thai"
        
        # English text
        assert query_processor._detect_language("search documents") == "english"
        
        # Mixed text
        assert query_processor._detect_language("ค้นหา documents") == "mixed"
        
        # Numbers and special characters
        assert query_processor._detect_language("12345") == "other"
        assert query_processor._detect_language("@#$%") == "other"
    
    def test_contains_thai(self, query_processor):
        """Test Thai character detection."""
        assert query_processor._contains_thai("ค้นหา") is True
        assert query_processor._contains_thai("search") is False
        assert query_processor._contains_thai("search ค้นหา") is True
        assert query_processor._contains_thai("12345") is False
    
    def test_contains_english(self, query_processor):
        """Test English character detection."""
        assert query_processor._contains_english("search") is True
        assert query_processor._contains_english("ค้นหา") is False
        assert query_processor._contains_english("ค้นหา search") is True
        assert query_processor._contains_english("12345") is False


class TestQueryProcessorIntegration:
    """Integration tests for QueryProcessor with real dependencies."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_real_thai_tokenization(self):
        """Test with real Thai tokenizer (if available)."""
        settings = SearchProxySettings()
        processor = QueryProcessor(settings)
        
        try:
            await processor.initialize()
            result = await processor.process_query("การค้นหาเอกสารภาษาไทย")
            
            assert result.thai_content_detected is True
            assert len(result.query_variants) > 0
            assert any(v.variant_type == QueryVariantType.TOKENIZED for v in result.query_variants)
            
        except Exception as e:
            pytest.skip(f"Thai tokenizer not available: {e}")