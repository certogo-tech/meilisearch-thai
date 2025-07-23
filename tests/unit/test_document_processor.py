"""
Unit tests for document processing pipeline.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.meilisearch.document_processor import (
    DocumentProcessor,
    ProcessedDocument,
    ProcessingStatus,
    ProcessingMetadata,
    BatchProcessingResult,
    ThaiContentDetector,
    create_document_processor
)
from src.tokenizer.thai_segmenter import ThaiSegmenter, TokenizationResult
from src.tokenizer.token_processor import TokenProcessor, TokenProcessingResult, ProcessedToken, ContentType
from src.meilisearch.client import MeiliSearchClient


class TestThaiContentDetector:
    """Test cases for ThaiContentDetector."""
    
    def test_contains_thai_with_thai_text(self):
        """Test detection of Thai content."""
        thai_text = "สวัสดีครับ"
        assert ThaiContentDetector.contains_thai(thai_text) is True
    
    def test_contains_thai_with_english_text(self):
        """Test detection with English text."""
        english_text = "Hello world"
        assert ThaiContentDetector.contains_thai(english_text) is False
    
    def test_contains_thai_with_mixed_text(self):
        """Test detection with mixed Thai-English text."""
        mixed_text = "Hello สวัสดี world"
        assert ThaiContentDetector.contains_thai(mixed_text) is True
    
    def test_contains_thai_with_empty_text(self):
        """Test detection with empty text."""
        assert ThaiContentDetector.contains_thai("") is False
        assert ThaiContentDetector.contains_thai(None) is False
    
    def test_get_thai_ratio_pure_thai(self):
        """Test Thai ratio calculation for pure Thai text."""
        thai_text = "สวัสดีครับ"
        ratio = ThaiContentDetector.get_thai_ratio(thai_text)
        assert ratio == 1.0
    
    def test_get_thai_ratio_mixed_content(self):
        """Test Thai ratio calculation for mixed content."""
        mixed_text = "Hello สวัสดี"  # 6 Thai chars, 5 English chars
        ratio = ThaiContentDetector.get_thai_ratio(mixed_text)
        assert abs(ratio - 0.545) < 0.01  # Approximately 6/11
    
    def test_get_thai_ratio_no_alphabetic(self):
        """Test Thai ratio with no alphabetic characters."""
        numeric_text = "123 456"
        ratio = ThaiContentDetector.get_thai_ratio(numeric_text)
        assert ratio == 0.0
    
    def test_extract_thai_content(self):
        """Test extraction of Thai content segments."""
        mixed_text = "Hello สวัสดี world ครับ"
        thai_segments = ThaiContentDetector.extract_thai_content(mixed_text)
        assert thai_segments == ["สวัสดี", "ครับ"]
    
    def test_is_mixed_content_true(self):
        """Test mixed content detection - positive case."""
        mixed_text = "Hello สวัสดี 123"
        assert ThaiContentDetector.is_mixed_content(mixed_text) is True
    
    def test_is_mixed_content_false_thai_only(self):
        """Test mixed content detection - Thai only."""
        thai_text = "สวัสดีครับ"
        assert ThaiContentDetector.is_mixed_content(thai_text) is False
    
    def test_is_mixed_content_false_english_only(self):
        """Test mixed content detection - English only."""
        english_text = "Hello world"
        assert ThaiContentDetector.is_mixed_content(english_text) is False


class TestDocumentProcessor:
    """Test cases for DocumentProcessor."""
    
    @pytest.fixture
    def mock_thai_segmenter(self):
        """Mock Thai segmenter."""
        segmenter = Mock(spec=ThaiSegmenter)
        segmenter.segment_text.return_value = TokenizationResult(
            original_text="สวัสดีครับ",
            tokens=["สวัสดี", "ครับ"],
            word_boundaries=[0, 6],
            processing_time_ms=10.0
        )
        return segmenter
    
    @pytest.fixture
    def mock_token_processor(self):
        """Mock token processor."""
        processor = Mock(spec=TokenProcessor)
        processor.process_tokenization_result.return_value = TokenProcessingResult(
            original_text="สวัสดีครับ",
            processed_text="สวัสดี​ครับ",
            tokens=[
                ProcessedToken("สวัสดี", "สวัสดี", ContentType.THAI),
                ProcessedToken("ครับ", "ครับ", ContentType.THAI)
            ],
            meilisearch_separators=["​"],
            processing_metadata={"token_count": 2}
        )
        return processor
    
    @pytest.fixture
    def mock_meilisearch_client(self):
        """Mock MeiliSearch client."""
        client = Mock(spec=MeiliSearchClient)
        client.add_documents = AsyncMock(return_value={"taskUid": "123"})
        return client
    
    @pytest.fixture
    def document_processor(self, mock_thai_segmenter, mock_token_processor, mock_meilisearch_client):
        """Document processor with mocked dependencies."""
        return DocumentProcessor(
            thai_segmenter=mock_thai_segmenter,
            token_processor=mock_token_processor,
            meilisearch_client=mock_meilisearch_client,
            batch_size=10,
            max_concurrent=5
        )
    
    @pytest.mark.asyncio
    async def test_process_document_with_thai_content(self, document_processor):
        """Test processing document with Thai content."""
        document = {
            "id": "doc1",
            "title": "Thai Title สวัสดี",
            "content": "Thai content ครับ"
        }
        
        result = await document_processor.process_document(document)
        
        assert result.id == "doc1"
        assert result.status == ProcessingStatus.COMPLETED
        assert result.metadata.thai_content_detected is True
        assert result.metadata.mixed_content is True
        assert result.thai_content is not None
        assert result.tokenized_content is not None
        assert result.metadata.token_count > 0
    
    @pytest.mark.asyncio
    async def test_process_document_without_thai_content(self, document_processor):
        """Test processing document without Thai content."""
        document = {
            "id": "doc1",
            "title": "English Title",
            "content": "English content"
        }
        
        result = await document_processor.process_document(document)
        
        assert result.id == "doc1"
        assert result.status == ProcessingStatus.SKIPPED
        assert result.metadata.thai_content_detected is False
        assert result.thai_content is None
        assert result.tokenized_content is None
    
    @pytest.mark.asyncio
    async def test_process_document_missing_id(self, document_processor):
        """Test processing document without ID."""
        document = {
            "title": "Title",
            "content": "Content"
        }
        
        result = await document_processor.process_document(document)
        
        assert result.status == ProcessingStatus.FAILED
        assert "must have an 'id' field" in result.metadata.error_message
    
    @pytest.mark.asyncio
    async def test_process_document_preserve_original(self, document_processor):
        """Test processing with original document preservation."""
        document = {
            "id": "doc1",
            "title": "Thai สวัสดี",
            "content": "Content ครับ",
            "extra_field": "extra_value"
        }
        
        result = await document_processor.process_document(document, preserve_original=True)
        
        assert result.original_document is not None
        assert result.original_document["extra_field"] == "extra_value"
    
    @pytest.mark.asyncio
    async def test_process_document_no_preserve_original(self, document_processor):
        """Test processing without original document preservation."""
        document = {
            "id": "doc1",
            "title": "Thai สวัสดี",
            "content": "Content ครับ"
        }
        
        result = await document_processor.process_document(document, preserve_original=False)
        
        assert result.original_document is None
    
    @pytest.mark.asyncio
    async def test_process_batch_success(self, document_processor):
        """Test successful batch processing."""
        documents = [
            {"id": "doc1", "title": "Thai สวัสดี", "content": "Content ครับ"},
            {"id": "doc2", "title": "English Title", "content": "English content"},
            {"id": "doc3", "title": "Mixed สวัสดี", "content": "Mixed content"}
        ]
        
        result = await document_processor.process_batch(documents)
        
        assert result.total_documents == 3
        assert result.processed_count == 2  # 2 with Thai content
        assert result.skipped_count == 1   # 1 without Thai content
        assert result.failed_count == 0
        assert len(result.processed_documents) == 3
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_process_batch_empty_list(self, document_processor):
        """Test batch processing with empty document list."""
        result = await document_processor.process_batch([])
        
        assert result.total_documents == 0
        assert result.processed_count == 0
        assert result.failed_count == 0
        assert result.skipped_count == 0
        assert len(result.processed_documents) == 0
        assert len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_process_batch_with_errors(self, document_processor):
        """Test batch processing with some document errors."""
        documents = [
            {"id": "doc1", "title": "Thai สวัสดี", "content": "Content ครับ"},
            {"title": "No ID", "content": "This will fail"},  # Missing ID
            {"id": "doc3", "title": "Thai ครับ", "content": "Content"}
        ]
        
        result = await document_processor.process_batch(documents)
        
        assert result.total_documents == 3
        assert result.processed_count == 2  # 2 successful
        assert result.failed_count == 1    # 1 failed (missing ID)
        assert result.skipped_count == 0
        assert len(result.processed_documents) == 3
    
    @pytest.mark.asyncio
    async def test_index_processed_documents_success(self, document_processor):
        """Test successful indexing of processed documents."""
        processed_docs = [
            ProcessedDocument(
                id="doc1",
                title="Title",
                content="Content",
                thai_content="สวัสดี",
                tokenized_content="สวัสดี​ครับ",
                status=ProcessingStatus.COMPLETED,
                metadata=ProcessingMetadata(
                    processed_at=datetime.now(),
                    token_count=2
                )
            )
        ]
        
        result = await document_processor.index_processed_documents(
            processed_docs, "test_index"
        )
        
        assert result["indexed_count"] == 1
        assert result["index_name"] == "test_index"
        assert len(result["errors"]) == 0
        
        # Verify MeiliSearch client was called
        document_processor.meilisearch_client.add_documents.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_index_processed_documents_no_client(self, mock_thai_segmenter, mock_token_processor):
        """Test indexing without MeiliSearch client."""
        processor = DocumentProcessor(
            thai_segmenter=mock_thai_segmenter,
            token_processor=mock_token_processor,
            meilisearch_client=None
        )
        
        processed_docs = [
            ProcessedDocument(
                id="doc1",
                title="Title",
                content="Content",
                status=ProcessingStatus.COMPLETED
            )
        ]
        
        with pytest.raises(ValueError, match="MeiliSearch client not configured"):
            await processor.index_processed_documents(processed_docs, "test_index")
    
    @pytest.mark.asyncio
    async def test_index_processed_documents_empty_list(self, document_processor):
        """Test indexing with empty document list."""
        result = await document_processor.index_processed_documents([], "test_index")
        
        assert result["indexed_count"] == 0
        assert len(result["errors"]) == 0
    
    @pytest.mark.asyncio
    async def test_index_processed_documents_only_failed(self, document_processor):
        """Test indexing with only failed documents."""
        processed_docs = [
            ProcessedDocument(
                id="doc1",
                title="Title",
                content="Content",
                status=ProcessingStatus.FAILED
            )
        ]
        
        result = await document_processor.index_processed_documents(
            processed_docs, "test_index"
        )
        
        assert result["indexed_count"] == 0
        assert "No documents to index" in result["errors"]
    
    @pytest.mark.asyncio
    async def test_index_processed_documents_meilisearch_error(self, document_processor):
        """Test indexing with MeiliSearch error."""
        # Mock MeiliSearch client to raise exception
        document_processor.meilisearch_client.add_documents.side_effect = Exception("MeiliSearch error")
        
        processed_docs = [
            ProcessedDocument(
                id="doc1",
                title="Title",
                content="Content",
                status=ProcessingStatus.COMPLETED,
                metadata=ProcessingMetadata(processed_at=datetime.now())
            )
        ]
        
        result = await document_processor.index_processed_documents(
            processed_docs, "test_index"
        )
        
        assert result["indexed_count"] == 0
        assert len(result["errors"]) == 1
        assert "Failed to index documents" in result["errors"][0]
    
    @pytest.mark.asyncio
    async def test_process_and_index_complete_pipeline(self, document_processor):
        """Test complete processing and indexing pipeline."""
        documents = [
            {"id": "doc1", "title": "Thai สวัสดี", "content": "Content ครับ"},
            {"id": "doc2", "title": "Thai ครับ", "content": "More content"}
        ]
        
        result = await document_processor.process_and_index(
            documents, "test_index"
        )
        
        # Check processing results
        assert result["processing"]["total_documents"] == 2
        assert result["processing"]["processed_count"] == 2
        assert result["processing"]["failed_count"] == 0
        
        # Check indexing results
        assert result["indexing"]["indexed_count"] == 2
        assert result["indexing"]["index_name"] == "test_index"
    
    def test_get_processing_stats(self, document_processor):
        """Test getting processing statistics."""
        stats = document_processor.get_processing_stats()
        
        assert stats["batch_size"] == 10
        assert stats["max_concurrent"] == 5
        assert stats["meilisearch_configured"] is True
        assert "thai_segmenter_engine" in stats


class TestUtilityFunctions:
    """Test cases for utility functions."""
    
    def test_create_document_processor_default(self):
        """Test creating document processor with defaults."""
        processor = create_document_processor()
        
        assert isinstance(processor, DocumentProcessor)
        assert processor.batch_size == 100
        assert processor.max_concurrent == 10
        assert processor.meilisearch_client is None
    
    def test_create_document_processor_custom(self):
        """Test creating document processor with custom parameters."""
        mock_client = Mock(spec=MeiliSearchClient)
        
        processor = create_document_processor(
            meilisearch_client=mock_client,
            batch_size=50,
            max_concurrent=5
        )
        
        assert processor.meilisearch_client is mock_client
        assert processor.batch_size == 50
        assert processor.max_concurrent == 5


class TestProcessingMetadata:
    """Test cases for ProcessingMetadata."""
    
    def test_default_metadata(self):
        """Test default metadata values."""
        metadata = ProcessingMetadata()
        
        assert metadata.language == "th"
        assert metadata.tokenization_version == "1.0"
        assert metadata.processed_at is None
        assert metadata.processing_time_ms == 0.0
        assert metadata.token_count == 0
        assert metadata.thai_content_detected is False
        assert metadata.mixed_content is False
        assert metadata.error_message is None
    
    def test_custom_metadata(self):
        """Test custom metadata values."""
        now = datetime.now()
        metadata = ProcessingMetadata(
            language="en",
            tokenization_version="2.0",
            processed_at=now,
            processing_time_ms=100.5,
            token_count=10,
            thai_content_detected=True,
            mixed_content=True,
            error_message="Test error"
        )
        
        assert metadata.language == "en"
        assert metadata.tokenization_version == "2.0"
        assert metadata.processed_at == now
        assert metadata.processing_time_ms == 100.5
        assert metadata.token_count == 10
        assert metadata.thai_content_detected is True
        assert metadata.mixed_content is True
        assert metadata.error_message == "Test error"


class TestProcessedDocument:
    """Test cases for ProcessedDocument."""
    
    def test_default_processed_document(self):
        """Test default processed document values."""
        doc = ProcessedDocument(
            id="test_id",
            title="Test Title",
            content="Test Content"
        )
        
        assert doc.id == "test_id"
        assert doc.title == "Test Title"
        assert doc.content == "Test Content"
        assert doc.thai_content is None
        assert doc.tokenized_content is None
        assert isinstance(doc.metadata, ProcessingMetadata)
        assert doc.original_document is None
        assert doc.status == ProcessingStatus.PENDING
    
    def test_custom_processed_document(self):
        """Test custom processed document values."""
        metadata = ProcessingMetadata(token_count=5)
        original_doc = {"id": "test", "extra": "data"}
        
        doc = ProcessedDocument(
            id="test_id",
            title="Test Title",
            content="Test Content",
            thai_content="สวัสดี",
            tokenized_content="สวัสดี​ครับ",
            metadata=metadata,
            original_document=original_doc,
            status=ProcessingStatus.COMPLETED
        )
        
        assert doc.thai_content == "สวัสดี"
        assert doc.tokenized_content == "สวัสดี​ครับ"
        assert doc.metadata.token_count == 5
        assert doc.original_document == original_doc
        assert doc.status == ProcessingStatus.COMPLETED


class TestBatchProcessingResult:
    """Test cases for BatchProcessingResult."""
    
    def test_batch_processing_result(self):
        """Test batch processing result structure."""
        processed_docs = [
            ProcessedDocument(id="1", title="Title 1", content="Content 1"),
            ProcessedDocument(id="2", title="Title 2", content="Content 2")
        ]
        
        errors = [{"document_id": "3", "error": "Test error"}]
        
        result = BatchProcessingResult(
            total_documents=3,
            processed_count=2,
            failed_count=1,
            skipped_count=0,
            processing_time_ms=150.5,
            processed_documents=processed_docs,
            errors=errors
        )
        
        assert result.total_documents == 3
        assert result.processed_count == 2
        assert result.failed_count == 1
        assert result.skipped_count == 0
        assert result.processing_time_ms == 150.5
        assert len(result.processed_documents) == 2
        assert len(result.errors) == 1
        assert result.errors[0]["error"] == "Test error"