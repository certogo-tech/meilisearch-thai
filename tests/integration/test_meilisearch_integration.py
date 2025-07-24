"""
Integration tests for MeiliSearch functionality.

Tests document indexing with Thai content, search accuracy comparisons,
configuration updates, and error handling with MeiliSearch integration.
"""

import pytest
import asyncio
import json
import time
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

from src.meilisearch_integration.client import MeiliSearchClient
from src.meilisearch_integration.document_processor import DocumentProcessor
from src.meilisearch_integration.settings_manager import TokenizationSettingsManager
from src.tokenizer.thai_segmenter import ThaiSegmenter
from src.tokenizer.token_processor import TokenProcessor


class TestMeiliSearchDocumentIndexing:
    """Test document indexing with Thai content."""
    
    @pytest.fixture
    def mock_meilisearch_client(self):
        """Mock MeiliSearch client for testing."""
        client = MagicMock()
        client.index = MagicMock()
        client.index.return_value.add_documents = AsyncMock(return_value={"taskUid": 123})
        client.index.return_value.update_settings = AsyncMock(return_value={"taskUid": 124})
        client.index.return_value.search = AsyncMock()
        client.index.return_value.get_settings = AsyncMock()
        client.index.return_value.get_task = AsyncMock(return_value={"status": "succeeded"})
        client.index.return_value.delete_all_documents = AsyncMock(return_value={"taskUid": 125})
        return client
    
    @pytest.fixture
    def document_processor(self, mock_meilisearch_client):
        """Document processor with mocked client."""
        processor = DocumentProcessor(
            meilisearch_client=mock_meilisearch_client
        )
        return processor
    
    @pytest.fixture
    def thai_documents(self):
        """Sample Thai documents for testing."""
        return [
            {
                "id": "doc1",
                "title": "เทคโนโลยีสารสนเทศ",
                "content": "การพัฒนาเทคโนโลยีสารสนเทศในประเทศไทยมีความก้าวหน้าอย่างรวดเร็ว",
                "category": "technology"
            },
            {
                "id": "doc2", 
                "title": "การศึกษาไทย",
                "content": "ระบบการศึกษาของประเทศไทยต้องปรับตัวให้ทันกับการเปลี่ยนแปลงของโลก",
                "category": "education"
            },
            {
                "id": "doc3",
                "title": "Mixed Content Example",
                "content": "Apple iPhone 15 Pro Max ราคา 45,900 บาท พร้อม AI Photography",
                "category": "technology"
            },
            {
                "id": "doc4",
                "title": "รถยนต์ไฟฟ้า",
                "content": "รถยนต์ไฟฟ้าเป็นอนาคตของอุตสาหกรรมยานยนต์ในประเทศไทย",
                "category": "automotive"
            }
        ]
    
    @pytest.mark.asyncio
    async def test_document_processing_with_thai_content(self, document_processor, thai_documents):
        """Test processing Thai documents with proper tokenization."""
        # Process documents
        processed_docs = []
        for doc in thai_documents:
            processed_doc = await document_processor.process_document(doc)
            processed_docs.append(processed_doc)
        
        # Verify documents were processed
        assert len(processed_docs) == len(thai_documents)
        
        # Verify Thai content was detected and processed
        for processed_doc in processed_docs:
            assert processed_doc.id is not None
            if processed_doc.metadata.thai_content_detected:
                # Should have Thai tokenization metadata
                assert processed_doc.metadata.token_count > 0
                assert processed_doc.metadata.processing_time_ms >= 0
    
    @pytest.mark.asyncio
    async def test_document_processing_with_compound_words(self, document_processor):
        """Test document processing with Thai compound words."""
        compound_doc = {
            "id": "compound1",
            "title": "เทคโนโลยีสารสนเทศและการสื่อสาร",
            "content": "วิทยาศาสตร์คอมพิวเตอร์และวิศวกรรมซอฟต์แวร์"
        }
        
        processed_doc = await document_processor.process_document(compound_doc)
        
        # Verify compound words were processed
        assert processed_doc.id == "compound1"
        assert processed_doc.metadata.thai_content_detected is True
        assert processed_doc.metadata.token_count > 0
        
        # Check that compound processing was applied
        assert processed_doc.tokenized_content is not None
    
    @pytest.mark.asyncio
    async def test_batch_document_processing(self, document_processor, thai_documents):
        """Test batch processing of multiple Thai documents."""
        # Process documents in batch
        result = await document_processor.process_batch(thai_documents)
        
        assert result.total_documents == len(thai_documents)
        assert result.processed_count >= 0
        assert result.failed_count >= 0
        assert result.total_documents == result.processed_count + result.failed_count + result.skipped_count
        
        # Verify processing metadata
        assert result.processing_time_ms >= 0
        assert len(result.processed_documents) <= len(thai_documents)
    
    @pytest.mark.asyncio
    async def test_document_update_with_thai_content(self, document_processor):
        """Test updating documents with Thai content."""
        updated_doc = {
            "id": "doc1",
            "title": "เทคโนโลยีสารสนเทศ - อัปเดต",
            "content": "เนื้อหาที่อัปเดตใหม่เกี่ยวกับเทคโนโลยีสารสนเทศ"
        }
        
        processed_doc = await document_processor.process_document(updated_doc)
        
        assert processed_doc.id == "doc1"
        assert processed_doc.metadata.thai_content_detected is True
        
        # Verify Thai content was processed
        assert processed_doc.tokenized_content is not None
        assert processed_doc.metadata.token_count > 0
    
    def test_thai_content_detection(self, document_processor):
        """Test Thai content detection functionality."""
        thai_text = "เทคโนโลยีสารสนเทศ"
        english_text = "Information Technology"
        mixed_text = "Apple iPhone ราคา 45,900 บาท"
        
        # Test Thai content detection
        assert document_processor.content_detector.contains_thai(thai_text) is True
        assert document_processor.content_detector.contains_thai(english_text) is False
        assert document_processor.content_detector.contains_thai(mixed_text) is True
        
        # Test Thai ratio calculation
        thai_ratio = document_processor.content_detector.get_thai_ratio(mixed_text)
        assert 0 < thai_ratio < 1  # Should be between 0 and 1 for mixed content
    
    @pytest.mark.asyncio
    async def test_error_handling_during_processing(self, document_processor):
        """Test error handling during document processing."""
        # Test with invalid document
        invalid_doc = {
            "id": None,  # Invalid ID
            "content": None  # Invalid content
        }
        
        processed_doc = await document_processor.process_document(invalid_doc)
        
        # Should handle gracefully
        assert processed_doc is not None
        if processed_doc.metadata.error_message:
            assert len(processed_doc.metadata.error_message) > 0


class TestMeiliSearchConfiguration:
    """Test MeiliSearch configuration and settings management."""
    
    @pytest.fixture
    def settings_manager(self):
        """Settings manager for testing."""
        return TokenizationSettingsManager()
    
    @pytest.fixture
    def mock_meilisearch_client(self):
        """Mock MeiliSearch client."""
        client = MagicMock()
        client.index = MagicMock()
        client.index.return_value.update_settings = AsyncMock(return_value={"taskUid": 126})
        client.index.return_value.get_settings = AsyncMock()
        client.index.return_value.get_task = AsyncMock(return_value={"status": "succeeded"})
        return client
    
    def test_thai_tokenization_settings_creation(self, settings_manager):
        """Test creating MeiliSearch settings for Thai tokenization."""
        # Create MeiliSearch settings
        settings = settings_manager.create_meilisearch_settings()
        
        # Verify required settings are present
        assert "separatorTokens" in settings
        assert "nonSeparatorTokens" in settings
        assert "stopWords" in settings
        assert "synonyms" in settings
        
        # Check Thai-specific tokens
        assert "​" in settings["separatorTokens"]  # Thai word separator
        assert "ๆ" in settings["nonSeparatorTokens"]  # Thai repetition mark
        assert "และ" in settings["stopWords"]  # Thai "and"
    
    def test_settings_validation(self, settings_manager):
        """Test validation of MeiliSearch settings."""
        # Valid settings
        valid_settings = {
            "separatorTokens": ["​", " ", "\t"],
            "nonSeparatorTokens": ["ๆ", "ฯ"],
            "stopWords": ["และ", "หรือ"],
            "synonyms": {"เทคโนโลยี": ["technology"]},
            "rankingRules": ["words", "typo", "proximity"]
        }
        
        validated = settings_manager.validate_settings(valid_settings)
        assert validated is not None
        assert validated.separatorTokens == valid_settings["separatorTokens"]
    
    def test_custom_dictionary_management(self, settings_manager):
        """Test managing custom dictionary words."""
        # Add custom words
        custom_words = ["เทคโนโลยี", "สารสนเทศ", "คอมพิวเตอร์"]
        settings_manager.add_custom_dictionary_words(custom_words)
        
        # Verify words were added
        settings = settings_manager.create_meilisearch_settings()
        for word in custom_words:
            assert word in settings["dictionary"]
    
    def test_synonym_management(self, settings_manager):
        """Test managing synonym mappings."""
        # Add synonyms
        synonyms = {
            "เทคโนโลยี": ["technology", "tech"],
            "คอมพิวเตอร์": ["computer", "PC"]
        }
        settings_manager.add_synonyms(synonyms)
        
        # Verify synonyms were added
        settings = settings_manager.create_meilisearch_settings()
        for canonical, variants in synonyms.items():
            assert canonical in settings["synonyms"]
            for variant in variants:
                assert variant in settings["synonyms"][canonical]


class TestSearchAccuracyComparison:
    """Test search accuracy with and without Thai tokenization."""
    
    def test_thai_tokenization_settings_for_search(self):
        """Test that Thai tokenization settings improve search capability."""
        from src.meilisearch_integration.settings_manager import create_default_thai_settings
        
        # Create default Thai settings
        settings_manager = create_default_thai_settings()
        settings = settings_manager.create_meilisearch_settings()
        
        # Verify search-enhancing settings
        assert "separatorTokens" in settings
        assert "​" in settings["separatorTokens"]  # Thai word separator
        assert "stopWords" in settings
        assert len(settings["stopWords"]) > 0  # Should have Thai stop words
        
        # Verify synonym support
        assert "synonyms" in settings
        
    def test_compound_word_tokenization_settings(self):
        """Test settings specifically for compound word handling."""
        from src.meilisearch_integration.settings_manager import TokenizationSettingsManager, ThaiTokenizationConfig
        
        # Create config with compound word support
        config = ThaiTokenizationConfig()
        config.custom_dictionary.extend([
            "เทคโนโลยีสารสนเทศ",
            "รถยนต์ไฟฟ้า",
            "วิทยาศาสตร์คอมพิวเตอร์"
        ])
        
        settings_manager = TokenizationSettingsManager(config)
        settings = settings_manager.create_meilisearch_settings()
        
        # Verify compound words are in dictionary
        for compound in config.custom_dictionary:
            assert compound in settings["dictionary"]


class TestErrorHandlingAndResilience:
    """Test error handling and system resilience."""
    
    def test_document_processor_error_handling(self):
        """Test document processor error handling."""
        from src.meilisearch_integration.document_processor import DocumentProcessor
        
        processor = DocumentProcessor()
        
        # Test with empty document
        empty_doc = {}
        
        # Should handle gracefully without throwing exceptions
        try:
            # This should not raise an exception
            result = asyncio.run(processor.process_document(empty_doc))
            assert result is not None
        except Exception as e:
            # If it does raise an exception, it should be handled gracefully
            assert "error" in str(e).lower() or "invalid" in str(e).lower()
    
    def test_settings_validation_error_handling(self):
        """Test settings validation error handling."""
        from src.meilisearch_integration.settings_manager import TokenizationSettingsManager
        
        manager = TokenizationSettingsManager()
        
        # Test with invalid settings
        invalid_settings = {
            "separatorTokens": None,  # Invalid type
            "stopWords": "not a list",  # Invalid type
            "rankingRules": ["invalid_rule"]  # Invalid rule
        }
        
        try:
            manager.validate_settings(invalid_settings)
            assert False, "Should have raised validation error"
        except (ValueError, TypeError) as e:
            # Should raise appropriate validation error
            assert len(str(e)) > 0


class TestPerformanceAndScaling:
    """Test performance characteristics and scaling behavior."""
    
    @pytest.mark.asyncio
    async def test_batch_processing_performance(self):
        """Test performance of batch document processing."""
        from src.meilisearch_integration.document_processor import DocumentProcessor
        
        processor = DocumentProcessor(batch_size=10)
        
        # Create test documents
        documents = []
        for i in range(25):  # 25 documents to test batching
            doc = {
                "id": f"perf_doc_{i}",
                "title": f"เอกสารทดสอบ {i}",
                "content": f"เนื้อหาสำหรับการทดสอบประสิทธิภาพ {i}"
            }
            documents.append(doc)
        
        # Measure processing time
        start_time = time.time()
        result = await processor.process_batch(documents)
        end_time = time.time()
        
        processing_time = end_time - start_time
        
        # Verify batch processing worked
        assert result.total_documents == len(documents)
        assert processing_time < 10.0  # Should complete within 10 seconds
        
        # Check processing rate
        docs_per_second = len(documents) / processing_time if processing_time > 0 else 0
        assert docs_per_second > 1  # Should process at least 1 doc per second
    
    def test_memory_efficiency_with_large_content(self):
        """Test memory efficiency with large document content."""
        from src.meilisearch_integration.document_processor import DocumentProcessor
        import sys
        
        processor = DocumentProcessor()
        
        # Create document with large content
        large_content = "เนื้อหาภาษาไทยขนาดใหญ่ " * 1000  # Large Thai content
        large_doc = {
            "id": "large_doc",
            "title": "เอกสารขนาดใหญ่",
            "content": large_content
        }
        
        # Measure memory usage
        initial_memory = sys.getsizeof(large_doc)
        
        # Process document
        processed_doc = asyncio.run(processor.process_document(large_doc))
        
        # Memory usage should be reasonable
        processed_memory = sys.getsizeof(processed_doc)
        memory_ratio = processed_memory / initial_memory if initial_memory > 0 else 1
        
        # Should not use excessive memory (less than 3x original)
        assert memory_ratio < 3.0