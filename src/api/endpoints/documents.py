"""Document processing endpoints for the Thai tokenizer API."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import JSONResponse

from src.api.models.requests import IndexDocumentRequest
from src.api.models.responses import DocumentProcessingResult, ErrorResponse
from src.meilisearch_integration.document_processor import DocumentProcessor, ProcessingStatus
from src.meilisearch_integration.client import MeiliSearchClient
from src.tokenizer.thai_segmenter import ThaiSegmenter
from src.tokenizer.token_processor import TokenProcessor

logger = logging.getLogger(__name__)

router = APIRouter()

# Global instances (will be injected via dependency injection)
_document_processor: DocumentProcessor = None
_meilisearch_client: MeiliSearchClient = None


def get_document_processor() -> DocumentProcessor:
    """Dependency to get document processor instance."""
    global _document_processor, _meilisearch_client
    if _document_processor is None:
        if _meilisearch_client is None:
            _meilisearch_client = MeiliSearchClient()
        _document_processor = DocumentProcessor(meilisearch_client=_meilisearch_client)
    return _document_processor


def get_meilisearch_client() -> MeiliSearchClient:
    """Dependency to get MeiliSearch client instance."""
    global _meilisearch_client
    if _meilisearch_client is None:
        _meilisearch_client = MeiliSearchClient()
    return _meilisearch_client


@router.post("/index-document", response_model=DocumentProcessingResult)
async def index_document(
    request: IndexDocumentRequest,
    background_tasks: BackgroundTasks,
    document_processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    Process and index a single Thai document.
    
    This endpoint processes Thai text content, tokenizes it, and indexes it
    in MeiliSearch with proper Thai tokenization settings.
    """
    try:
        logger.info(f"Processing document: {request.id}")
        
        # Convert request to document format
        document = {
            "id": request.id,
            "title": request.title,
            "content": request.content,
            "metadata": request.metadata or {}
        }
        
        # Process the document
        processed_doc = await document_processor.process_document(document)
        
        # Prepare tokenized fields result
        tokenized_fields = {}
        
        if processed_doc.status == ProcessingStatus.COMPLETED:
            # Create tokenization results for title and content
            if processed_doc.thai_content:
                tokenized_fields["thai_content"] = {
                    "original_text": processed_doc.thai_content,
                    "tokens": processed_doc.tokenized_content.split() if processed_doc.tokenized_content else [],
                    "word_boundaries": [],  # Would need to be calculated from tokenization
                    "processing_time_ms": int(processed_doc.metadata.processing_time_ms)
                }
        
        # Index in MeiliSearch if processing was successful
        if processed_doc.status == ProcessingStatus.COMPLETED:
            # Add background task to index the document
            background_tasks.add_task(
                _index_document_background,
                document_processor,
                [processed_doc],
                "documents"  # Default index name
            )
        
        response = DocumentProcessingResult(
            document_id=processed_doc.id,
            status=processed_doc.status.value,
            tokenized_fields=tokenized_fields,
            indexed_at=processed_doc.metadata.processed_at or datetime.now()
        )
        
        logger.info(
            f"Document {request.id} processed: {processed_doc.status.value} "
            f"({processed_doc.metadata.token_count} tokens)"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Document processing failed for {request.id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="document_processing_error",
                message=f"Failed to process document: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/index-documents/batch")
async def index_documents_batch(
    documents: List[IndexDocumentRequest],
    background_tasks: BackgroundTasks,
    index_name: str = "documents",
    document_processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    Process and index multiple Thai documents in batch.
    
    This endpoint processes multiple documents concurrently and indexes them
    in MeiliSearch with proper Thai tokenization.
    """
    try:
        logger.info(f"Processing batch of {len(documents)} documents")
        
        if not documents:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No documents provided for processing"
            )
        
        # Convert requests to document format
        document_dicts = []
        for req in documents:
            document_dicts.append({
                "id": req.id,
                "title": req.title,
                "content": req.content,
                "metadata": req.metadata or {}
            })
        
        # Process documents in batch
        batch_result = await document_processor.process_batch(document_dicts)
        
        # Add background task to index successfully processed documents
        successful_docs = [
            doc for doc in batch_result.processed_documents
            if doc.status == ProcessingStatus.COMPLETED
        ]
        
        if successful_docs:
            background_tasks.add_task(
                _index_document_background,
                document_processor,
                successful_docs,
                index_name
            )
        
        # Prepare response
        response = {
            "batch_id": f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "total_documents": batch_result.total_documents,
            "processed_count": batch_result.processed_count,
            "failed_count": batch_result.failed_count,
            "skipped_count": batch_result.skipped_count,
            "processing_time_ms": int(batch_result.processing_time_ms),
            "index_name": index_name,
            "status": "completed",
            "errors": batch_result.errors
        }
        
        logger.info(
            f"Batch processing completed: {batch_result.processed_count} processed, "
            f"{batch_result.failed_count} failed, {batch_result.skipped_count} skipped"
        )
        
        return response
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="batch_processing_error",
                message=f"Failed to process document batch: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/processing/stats")
async def get_processing_stats(
    document_processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    Get document processing statistics and configuration.
    
    Returns information about the current processing configuration,
    performance statistics, and system status.
    """
    try:
        stats = document_processor.get_processing_stats()
        
        return {
            "processing": stats,
            "status": "healthy",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Failed to get processing stats: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="stats_error",
                message=f"Failed to retrieve processing statistics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/reprocess/{document_id}")
async def reprocess_document(
    document_id: str,
    background_tasks: BackgroundTasks,
    index_name: str = "documents",
    meilisearch_client: MeiliSearchClient = Depends(get_meilisearch_client),
    document_processor: DocumentProcessor = Depends(get_document_processor)
):
    """
    Reprocess an existing document with updated tokenization.
    
    This endpoint retrieves a document from MeiliSearch, reprocesses it
    with the current tokenization settings, and updates the index.
    """
    try:
        logger.info(f"Reprocessing document: {document_id}")
        
        # Retrieve document from MeiliSearch
        try:
            document = await meilisearch_client.get_document(index_name, document_id)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Document {document_id} not found in index {index_name}"
            )
        
        # Process the document
        processed_doc = await document_processor.process_document(document)
        
        # Add background task to update the document in MeiliSearch
        if processed_doc.status == ProcessingStatus.COMPLETED:
            background_tasks.add_task(
                _index_document_background,
                document_processor,
                [processed_doc],
                index_name
            )
        
        response = {
            "document_id": document_id,
            "status": processed_doc.status.value,
            "reprocessed_at": datetime.now().isoformat(),
            "token_count": processed_doc.metadata.token_count,
            "processing_time_ms": int(processed_doc.metadata.processing_time_ms)
        }
        
        logger.info(f"Document {document_id} reprocessed: {processed_doc.status.value}")
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Document reprocessing failed for {document_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="reprocessing_error",
                message=f"Failed to reprocess document: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


async def _index_document_background(
    document_processor: DocumentProcessor,
    processed_documents: List,
    index_name: str
):
    """Background task to index processed documents."""
    try:
        result = await document_processor.index_processed_documents(
            processed_documents,
            index_name
        )
        logger.info(f"Background indexing completed: {result.get('indexed_count', 0)} documents")
    except Exception as e:
        logger.error(f"Background indexing failed: {e}", exc_info=True)