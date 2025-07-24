"""
Document processing pipeline for Thai text tokenization and MeiliSearch indexing.

This module provides document preprocessing that identifies and tokenizes Thai content,
implements batch processing for multiple documents, and preserves original text
while creating searchable tokens.
"""

import asyncio
import logging
import re
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from ..tokenizer.thai_segmenter import ThaiSegmenter, TokenizationResult
from ..tokenizer.token_processor import TokenProcessor, TokenProcessingResult, ContentType
from .client import MeiliSearchClient, DocumentModel


logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Status of document processing."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class ProcessingMetadata:
    """Metadata for document processing."""
    language: str = "th"
    tokenization_version: str = "1.0"
    processed_at: Optional[datetime] = None
    processing_time_ms: float = 0.0
    token_count: int = 0
    thai_content_detected: bool = False
    mixed_content: bool = False
    error_message: Optional[str] = None


@dataclass
class ProcessedDocument:
    """Document after Thai tokenization processing."""
    id: str
    title: str
    content: str
    thai_content: Optional[str] = None
    tokenized_content: Optional[str] = None
    metadata: ProcessingMetadata = field(default_factory=ProcessingMetadata)
    original_document: Optional[Dict[str, Any]] = None
    status: ProcessingStatus = ProcessingStatus.PENDING


@dataclass
class BatchProcessingResult:
    """Result of batch document processing."""
    total_documents: int
    processed_count: int
    failed_count: int
    skipped_count: int
    processing_time_ms: float
    processed_documents: List[ProcessedDocument]
    errors: List[Dict[str, Any]]


class ThaiContentDetector:
    """Utility class for detecting Thai content in text."""
    
    # Thai Unicode ranges
    THAI_RANGE = (0x0E00, 0x0E7F)
    THAI_PATTERN = re.compile(r'[\u0E00-\u0E7F]+')
    
    @classmethod
    def contains_thai(cls, text: str) -> bool:
        """Check if text contains Thai characters."""
        if not text:
            return False
        return bool(cls.THAI_PATTERN.search(text))
    
    @classmethod
    def get_thai_ratio(cls, text: str) -> float:
        """Get ratio of Thai characters to total characters."""
        if not text:
            return 0.0
        
        thai_chars = sum(1 for c in text if '\u0e00' <= c <= '\u0e7f')
        # Count all characters that are letters (including Thai characters)
        total_chars = sum(1 for c in text if c.isalpha() or '\u0e00' <= c <= '\u0e7f')
        
        return thai_chars / total_chars if total_chars > 0 else 0.0
    
    @classmethod
    def extract_thai_content(cls, text: str) -> List[str]:
        """Extract Thai text segments from mixed content."""
        return cls.THAI_PATTERN.findall(text)
    
    @classmethod
    def is_mixed_content(cls, text: str) -> bool:
        """Check if text contains both Thai and non-Thai content."""
        if not text:
            return False
        
        has_thai = cls.contains_thai(text)
        has_non_thai = bool(re.search(r'[a-zA-Z0-9]', text))
        
        return has_thai and has_non_thai


class DocumentProcessor:
    """
    Document processing pipeline for Thai text tokenization.
    
    Handles identification and tokenization of Thai content, batch processing,
    and preservation of original text while creating searchable tokens.
    """
    
    def __init__(
        self,
        thai_segmenter: Optional[ThaiSegmenter] = None,
        token_processor: Optional[TokenProcessor] = None,
        meilisearch_client: Optional[MeiliSearchClient] = None,
        batch_size: int = 100,
        max_concurrent: int = 10
    ):
        """Initialize document processor with components."""
        self.thai_segmenter = thai_segmenter or ThaiSegmenter()
        self.token_processor = token_processor or TokenProcessor()
        self.meilisearch_client = meilisearch_client
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.content_detector = ThaiContentDetector()
        
    async def process_document(
        self,
        document: Dict[str, Any],
        preserve_original: bool = True
    ) -> ProcessedDocument:
        """
        Process a single document with Thai tokenization.
        
        Args:
            document: Document dictionary with text content
            preserve_original: Whether to preserve original text
            
        Returns:
            ProcessedDocument with tokenized content
        """
        start_time = datetime.now()
        
        try:
            # Extract document fields
            doc_id = document.get("id", "")
            title = document.get("title", "")
            content = document.get("content", "")
            
            if not doc_id:
                raise ValueError("Document must have an 'id' field")
            
            # Initialize processed document
            processed_doc = ProcessedDocument(
                id=doc_id,
                title=title,
                content=content,
                original_document=document.copy() if preserve_original else None,
                status=ProcessingStatus.PROCESSING
            )
            
            # Detect Thai content
            title_has_thai = self.content_detector.contains_thai(title)
            content_has_thai = self.content_detector.contains_thai(content)
            
            if not (title_has_thai or content_has_thai):
                # No Thai content - skip tokenization
                processed_doc.status = ProcessingStatus.SKIPPED
                processed_doc.metadata.thai_content_detected = False
                logger.debug(f"Document {doc_id}: No Thai content detected, skipping tokenization")
                return processed_doc
            
            # Process Thai content
            processed_doc.metadata.thai_content_detected = True
            processed_doc.metadata.mixed_content = (
                self.content_detector.is_mixed_content(title) or
                self.content_detector.is_mixed_content(content)
            )
            
            # Combine text for processing
            full_text = f"{title} {content}".strip()
            
            # Extract and preserve Thai content
            thai_segments = self.content_detector.extract_thai_content(full_text)
            processed_doc.thai_content = " ".join(thai_segments) if thai_segments else None
            
            # Tokenize Thai content
            if thai_segments:
                tokenized_segments = []
                total_tokens = 0
                
                for segment in thai_segments:
                    if segment.strip():
                        # Tokenize Thai segment
                        tokenization_result = await asyncio.to_thread(
                            self.thai_segmenter.segment_text,
                            segment
                        )
                        
                        # Process tokens for MeiliSearch
                        token_result = await asyncio.to_thread(
                            self.token_processor.process_tokenization_result,
                            tokenization_result
                        )
                        
                        tokenized_segments.append(token_result.processed_text)
                        total_tokens += len(token_result.tokens)
                
                processed_doc.tokenized_content = " ".join(tokenized_segments)
                processed_doc.metadata.token_count = total_tokens
            
            # Update metadata
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            processed_doc.metadata.processed_at = datetime.now()
            processed_doc.metadata.processing_time_ms = processing_time
            processed_doc.status = ProcessingStatus.COMPLETED
            
            logger.info(
                f"Document {doc_id}: Processed successfully "
                f"({total_tokens} tokens, {processing_time:.2f}ms)"
            )
            
            return processed_doc
            
        except Exception as e:
            # Handle processing errors
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Processing failed: {str(e)}"
            
            # Create a minimal processed document for error cases
            doc_id = document.get("id", "unknown")
            title = document.get("title", "")
            content = document.get("content", "")
            
            processed_doc = ProcessedDocument(
                id=doc_id,
                title=title,
                content=content,
                status=ProcessingStatus.FAILED,
                metadata=ProcessingMetadata(
                    error_message=error_msg,
                    processing_time_ms=processing_time
                )
            )
            
            logger.error(f"Document {doc_id}: {error_msg}")
            return processed_doc
    
    async def process_batch(
        self,
        documents: List[Dict[str, Any]],
        preserve_original: bool = True
    ) -> BatchProcessingResult:
        """
        Process multiple documents in batches with concurrency control.
        
        Args:
            documents: List of document dictionaries
            preserve_original: Whether to preserve original text
            
        Returns:
            BatchProcessingResult with processing statistics
        """
        start_time = datetime.now()
        
        if not documents:
            return BatchProcessingResult(
                total_documents=0,
                processed_count=0,
                failed_count=0,
                skipped_count=0,
                processing_time_ms=0.0,
                processed_documents=[],
                errors=[]
            )
        
        logger.info(f"Starting batch processing of {len(documents)} documents")
        
        # Process documents in batches with concurrency control
        processed_documents = []
        errors = []
        
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def process_with_semaphore(doc):
            async with semaphore:
                return await self.process_document(doc, preserve_original)
        
        # Process all documents
        tasks = [process_with_semaphore(doc) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Collect results and errors
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_info = {
                    "document_index": i,
                    "document_id": documents[i].get("id", "unknown"),
                    "error": str(result)
                }
                errors.append(error_info)
                logger.error(f"Batch processing error for document {i}: {result}")
            else:
                processed_documents.append(result)
        
        # Calculate statistics
        total_documents = len(documents)
        processed_count = len([d for d in processed_documents if d.status == ProcessingStatus.COMPLETED])
        failed_count = len([d for d in processed_documents if d.status == ProcessingStatus.FAILED]) + len(errors)
        skipped_count = len([d for d in processed_documents if d.status == ProcessingStatus.SKIPPED])
        
        processing_time = (datetime.now() - start_time).total_seconds() * 1000
        
        result = BatchProcessingResult(
            total_documents=total_documents,
            processed_count=processed_count,
            failed_count=failed_count,
            skipped_count=skipped_count,
            processing_time_ms=processing_time,
            processed_documents=processed_documents,
            errors=errors
        )
        
        logger.info(
            f"Batch processing completed: {processed_count} processed, "
            f"{failed_count} failed, {skipped_count} skipped "
            f"({processing_time:.2f}ms total)"
        )
        
        return result
    
    async def index_processed_documents(
        self,
        processed_documents: List[ProcessedDocument],
        index_name: str,
        update_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Index processed documents in MeiliSearch.
        
        Args:
            processed_documents: List of processed documents
            index_name: MeiliSearch index name
            update_existing: Whether to update existing documents
            
        Returns:
            Indexing result with statistics
        """
        if not self.meilisearch_client:
            raise ValueError("MeiliSearch client not configured")
        
        if not processed_documents:
            return {"indexed_count": 0, "errors": []}
        
        # Filter successfully processed documents
        documents_to_index = [
            doc for doc in processed_documents 
            if doc.status == ProcessingStatus.COMPLETED
        ]
        
        if not documents_to_index:
            logger.warning("No successfully processed documents to index")
            return {"indexed_count": 0, "errors": ["No documents to index"]}
        
        # Convert to MeiliSearch document format
        meilisearch_docs = []
        for doc in documents_to_index:
            meilisearch_doc = {
                "id": doc.id,
                "title": doc.title,
                "content": doc.content,
                "thai_content": doc.thai_content,
                "tokenized_content": doc.tokenized_content,
                "metadata": {
                    "language": doc.metadata.language,
                    "tokenization_version": doc.metadata.tokenization_version,
                    "processed_at": doc.metadata.processed_at.isoformat() if doc.metadata.processed_at else None,
                    "processing_time_ms": doc.metadata.processing_time_ms,
                    "token_count": doc.metadata.token_count,
                    "thai_content_detected": doc.metadata.thai_content_detected,
                    "mixed_content": doc.metadata.mixed_content
                }
            }
            meilisearch_docs.append(meilisearch_doc)
        
        try:
            # Index documents in MeiliSearch
            result = await self.meilisearch_client.add_documents(
                index_name=index_name,
                documents=meilisearch_docs,
                primary_key="id"
            )
            
            logger.info(f"Indexed {len(meilisearch_docs)} documents in index '{index_name}'")
            
            return {
                "indexed_count": len(meilisearch_docs),
                "task_uid": result.get("taskUid"),
                "index_name": index_name,
                "errors": []
            }
            
        except Exception as e:
            error_msg = f"Failed to index documents: {str(e)}"
            logger.error(error_msg)
            return {
                "indexed_count": 0,
                "errors": [error_msg]
            }
    
    async def process_and_index(
        self,
        documents: List[Dict[str, Any]],
        index_name: str,
        preserve_original: bool = True,
        update_existing: bool = True
    ) -> Dict[str, Any]:
        """
        Complete pipeline: process documents and index them in MeiliSearch.
        
        Args:
            documents: List of document dictionaries
            index_name: MeiliSearch index name
            preserve_original: Whether to preserve original text
            update_existing: Whether to update existing documents
            
        Returns:
            Combined processing and indexing results
        """
        # Process documents
        batch_result = await self.process_batch(documents, preserve_original)
        
        # Index processed documents
        index_result = await self.index_processed_documents(
            batch_result.processed_documents,
            index_name,
            update_existing
        )
        
        # Combine results
        return {
            "processing": {
                "total_documents": batch_result.total_documents,
                "processed_count": batch_result.processed_count,
                "failed_count": batch_result.failed_count,
                "skipped_count": batch_result.skipped_count,
                "processing_time_ms": batch_result.processing_time_ms,
                "errors": batch_result.errors
            },
            "indexing": index_result
        }
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics and configuration."""
        return {
            "batch_size": self.batch_size,
            "max_concurrent": self.max_concurrent,
            "thai_segmenter_engine": getattr(self.thai_segmenter, 'engine', 'unknown'),
            "meilisearch_configured": self.meilisearch_client is not None
        }


def create_document_processor(
    meilisearch_client: Optional[MeiliSearchClient] = None,
    batch_size: int = 100,
    max_concurrent: int = 10
) -> DocumentProcessor:
    """
    Create a document processor with default configuration.
    
    Args:
        meilisearch_client: Optional MeiliSearch client
        batch_size: Batch size for processing
        max_concurrent: Maximum concurrent operations
        
    Returns:
        Configured DocumentProcessor instance
    """
    return DocumentProcessor(
        meilisearch_client=meilisearch_client,
        batch_size=batch_size,
        max_concurrent=max_concurrent
    )