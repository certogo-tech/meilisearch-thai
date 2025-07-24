"""
MeiliSearch client wrapper for Thai tokenizer integration.

This module provides a wrapper around the MeiliSearch client with:
- Index configuration and document management
- Error handling and retry logic for API calls
- Thai-specific tokenization settings management
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime

import meilisearch as ms_client
from meilisearch.errors import MeilisearchError, MeilisearchApiError
from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


@dataclass
class MeiliSearchConfig:
    """Configuration for MeiliSearch connection."""
    host: str
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0


class DocumentModel(BaseModel):
    """Base model for documents to be indexed."""
    id: str
    title: str = ""
    content: str = ""
    thai_content: Optional[str] = None
    tokenized_content: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IndexStats(BaseModel):
    """Statistics for a MeiliSearch index."""
    number_of_documents: int
    is_indexing: bool
    field_distribution: Dict[str, int]


class MeiliSearchClient:
    """
    Wrapper for MeiliSearch client with Thai tokenization support.
    
    Provides methods for index configuration, document management,
    and error handling with retry logic.
    """
    
    def __init__(self, config: MeiliSearchConfig):
        """Initialize MeiliSearch client with configuration."""
        self.config = config
        self.client = ms_client.Client(
            url=config.host,
            api_key=config.api_key,
            timeout=config.timeout
        )
        self._indexes: Dict[str, Any] = {}
        
    async def _retry_operation(self, operation, *args, **kwargs):
        """Execute operation with retry logic."""
        last_exception = None
        
        for attempt in range(self.config.max_retries):
            try:
                return await asyncio.to_thread(operation, *args, **kwargs)
            except (MeilisearchError, MeilisearchApiError) as e:
                last_exception = e
                if attempt < self.config.max_retries - 1:
                    wait_time = self.config.retry_delay * (2 ** attempt)
                    logger.warning(
                        f"MeiliSearch operation failed (attempt {attempt + 1}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"MeiliSearch operation failed after {self.config.max_retries} attempts: {e}")
                    
        raise last_exception
    
    async def health_check(self) -> Dict[str, Any]:
        """Check MeiliSearch server health."""
        try:
            health = await self._retry_operation(self.client.health)
            return {"status": "healthy", "details": health}
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {"status": "unhealthy", "error": str(e)}
    
    async def create_index(self, index_name: str, primary_key: Optional[str] = None) -> Dict[str, Any]:
        """Create a new index with optional primary key."""
        try:
            task = await self._retry_operation(
                self.client.create_index,
                index_name,
                {"primaryKey": primary_key} if primary_key else None
            )
            
            # Wait for index creation to complete
            await self._wait_for_task(task["taskUid"])
            
            self._indexes[index_name] = self.client.index(index_name)
            logger.info(f"Created index: {index_name}")
            
            return {"status": "created", "index": index_name, "task_uid": task["taskUid"]}
            
        except Exception as e:
            logger.error(f"Failed to create index {index_name}: {e}")
            raise
    
    async def index_exists(self, index_name: str) -> bool:
        """Check if an index exists."""
        try:
            await self._retry_operation(self.client.get_index, index_name)
            return True
        except MeilisearchApiError as e:
            if "index_not_found" in str(e):
                return False
            raise
    
    async def get_index(self, index_name: str):
        """Get or create index reference."""
        if index_name not in self._indexes:
            try:
                # Check if index exists
                await self._retry_operation(self.client.get_index, index_name)
                self._indexes[index_name] = self.client.index(index_name)
            except MeilisearchApiError as e:
                if "index_not_found" in str(e):
                    logger.info(f"Index {index_name} not found, creating it...")
                    await self.create_index(index_name)
                else:
                    raise
                    
        return self._indexes[index_name]
    
    async def update_index_settings(self, index_name: str, settings: Dict[str, Any]) -> Dict[str, Any]:
        """Update index settings including tokenization configuration."""
        try:
            index = await self.get_index(index_name)
            task = await self._retry_operation(index.update_settings, settings)
            
            # Wait for settings update to complete
            await self._wait_for_task(task["taskUid"])
            
            logger.info(f"Updated settings for index: {index_name}")
            return {"status": "updated", "task_uid": task["taskUid"]}
            
        except Exception as e:
            logger.error(f"Failed to update settings for index {index_name}: {e}")
            raise
    
    async def get_index_settings(self, index_name: str) -> Dict[str, Any]:
        """Get current index settings."""
        try:
            index = await self.get_index(index_name)
            settings = await self._retry_operation(index.get_settings)
            return settings
        except Exception as e:
            logger.error(f"Failed to get settings for index {index_name}: {e}")
            raise
    
    async def add_documents(
        self, 
        index_name: str, 
        documents: List[Union[Dict[str, Any], DocumentModel]],
        primary_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add documents to index with batch processing."""
        try:
            index = await self.get_index(index_name)
            
            # Convert DocumentModel instances to dictionaries
            doc_dicts = []
            for doc in documents:
                if isinstance(doc, DocumentModel):
                    doc_dict = doc.model_dump(exclude_none=True)
                    # Convert datetime objects to ISO strings
                    if doc_dict.get("created_at"):
                        doc_dict["created_at"] = doc_dict["created_at"].isoformat()
                    if doc_dict.get("updated_at"):
                        doc_dict["updated_at"] = doc_dict["updated_at"].isoformat()
                    doc_dicts.append(doc_dict)
                else:
                    doc_dicts.append(doc)
            
            task = await self._retry_operation(
                index.add_documents,
                doc_dicts,
                primary_key
            )
            
            logger.info(f"Added {len(documents)} documents to index: {index_name}")
            return {"status": "added", "count": len(documents), "task_uid": task["taskUid"]}
            
        except Exception as e:
            logger.error(f"Failed to add documents to index {index_name}: {e}")
            raise
    
    async def update_documents(
        self, 
        index_name: str, 
        documents: List[Union[Dict[str, Any], DocumentModel]],
        primary_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update documents in index."""
        try:
            index = await self.get_index(index_name)
            
            # Convert DocumentModel instances to dictionaries
            doc_dicts = []
            for doc in documents:
                if isinstance(doc, DocumentModel):
                    doc_dict = doc.model_dump(exclude_none=True)
                    # Convert datetime objects to ISO strings
                    if doc_dict.get("created_at"):
                        doc_dict["created_at"] = doc_dict["created_at"].isoformat()
                    if doc_dict.get("updated_at"):
                        doc_dict["updated_at"] = doc_dict["updated_at"].isoformat()
                    doc_dicts.append(doc_dict)
                else:
                    doc_dicts.append(doc)
            
            task = await self._retry_operation(
                index.update_documents,
                doc_dicts,
                primary_key
            )
            
            logger.info(f"Updated {len(documents)} documents in index: {index_name}")
            return {"status": "updated", "count": len(documents), "task_uid": task["taskUid"]}
            
        except Exception as e:
            logger.error(f"Failed to update documents in index {index_name}: {e}")
            raise
    
    async def delete_document(self, index_name: str, document_id: str) -> Dict[str, Any]:
        """Delete a document by ID."""
        try:
            index = await self.get_index(index_name)
            task = await self._retry_operation(index.delete_document, document_id)
            
            logger.info(f"Deleted document {document_id} from index: {index_name}")
            return {"status": "deleted", "document_id": document_id, "task_uid": task["taskUid"]}
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id} from index {index_name}: {e}")
            raise
    
    async def delete_documents(self, index_name: str, document_ids: List[str]) -> Dict[str, Any]:
        """Delete multiple documents by IDs."""
        try:
            index = await self.get_index(index_name)
            task = await self._retry_operation(index.delete_documents, document_ids)
            
            logger.info(f"Deleted {len(document_ids)} documents from index: {index_name}")
            return {"status": "deleted", "count": len(document_ids), "task_uid": task["taskUid"]}
            
        except Exception as e:
            logger.error(f"Failed to delete documents from index {index_name}: {e}")
            raise
    
    async def search(
        self, 
        index_name: str, 
        query: str, 
        options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Search documents in index."""
        try:
            index = await self.get_index(index_name)
            search_options = options or {}
            
            results = await self._retry_operation(index.search, query, search_options)
            
            logger.debug(f"Search query '{query}' returned {len(results.get('hits', []))} results")
            return results
            
        except Exception as e:
            logger.error(f"Search failed for query '{query}' in index {index_name}: {e}")
            raise
    
    async def get_index_stats(self, index_name: str) -> IndexStats:
        """Get index statistics."""
        try:
            index = await self.get_index(index_name)
            stats = await self._retry_operation(index.get_stats)
            
            return IndexStats(
                number_of_documents=stats.get("numberOfDocuments", 0),
                is_indexing=stats.get("isIndexing", False),
                field_distribution=stats.get("fieldDistribution", {})
            )
            
        except Exception as e:
            logger.error(f"Failed to get stats for index {index_name}: {e}")
            raise
    
    async def delete_index(self, index_name: str) -> Dict[str, Any]:
        """Delete an index."""
        try:
            task = await self._retry_operation(self.client.delete_index, index_name)
            
            # Remove from local cache
            if index_name in self._indexes:
                del self._indexes[index_name]
            
            logger.info(f"Deleted index: {index_name}")
            return {"status": "deleted", "index": index_name, "task_uid": task["taskUid"]}
            
        except Exception as e:
            logger.error(f"Failed to delete index {index_name}: {e}")
            raise
    
    async def _wait_for_task(self, task_uid: int, timeout: int = 30) -> Dict[str, Any]:
        """Wait for a MeiliSearch task to complete."""
        start_time = asyncio.get_event_loop().time()
        
        while True:
            try:
                task = await self._retry_operation(self.client.get_task, task_uid)
                
                if task["status"] in ["succeeded", "failed"]:
                    if task["status"] == "failed":
                        error_msg = task.get("error", {}).get("message", "Unknown error")
                        raise MeilisearchError(f"Task {task_uid} failed: {error_msg}")
                    return task
                
                # Check timeout
                if asyncio.get_event_loop().time() - start_time > timeout:
                    raise TimeoutError(f"Task {task_uid} did not complete within {timeout} seconds")
                
                await asyncio.sleep(0.5)  # Wait before checking again
                
            except Exception as e:
                logger.error(f"Error waiting for task {task_uid}: {e}")
                raise
    
    async def get_task_status(self, task_uid: int) -> Dict[str, Any]:
        """Get the status of a specific task."""
        try:
            task = await self._retry_operation(self.client.get_task, task_uid)
            return {
                "uid": task["uid"],
                "status": task["status"],
                "type": task["type"],
                "started_at": task.get("startedAt"),
                "finished_at": task.get("finishedAt"),
                "error": task.get("error")
            }
        except Exception as e:
            logger.error(f"Failed to get task status for {task_uid}: {e}")
            raise
    
    async def close(self):
        """Clean up resources."""
        self._indexes.clear()
        logger.info("MeiliSearch client closed")