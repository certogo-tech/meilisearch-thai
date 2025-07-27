"""
Unit tests for MeiliSearch client wrapper.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.meilisearch_integration.client import (
    MeiliSearchClient,
    MeiliSearchConfig,
    DocumentModel,
    IndexStats
)


@pytest.fixture
def config():
    """Test configuration."""
    return MeiliSearchConfig(
        host="http://localhost:7700",
        api_key="test_key",
        timeout=10,
        max_retries=2,
        retry_delay=0.1
    )


@pytest.fixture
def mock_meilisearch_client():
    """Mock MeiliSearch client."""
    with patch('src.meilisearch_integration.client.ms_client.Client') as mock_client_class:
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        yield mock_client


@pytest.fixture
def client(config, mock_meilisearch_client):
    """MeiliSearch client instance."""
    return MeiliSearchClient(config)


class TestMeiliSearchClient:
    """Test cases for MeiliSearch client wrapper."""
    
    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_meilisearch_client):
        """Test successful health check."""
        mock_meilisearch_client.health.return_value = {"status": "available"}
        
        result = await client.health_check()
        
        assert result["status"] == "healthy"
        assert result["details"]["status"] == "available"
        mock_meilisearch_client.health.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check_failure(self, client, mock_meilisearch_client):
        """Test health check failure."""
        mock_meilisearch_client.health.side_effect = Exception("Connection failed")
        
        result = await client.health_check()
        
        assert result["status"] == "unhealthy"
        assert "Connection failed" in result["error"]
    
    @pytest.mark.asyncio
    async def test_create_index_success(self, client, mock_meilisearch_client):
        """Test successful index creation."""
        mock_task = {"taskUid": 123}
        mock_meilisearch_client.create_index.return_value = mock_task
        mock_meilisearch_client.get_task.return_value = {"status": "succeeded", "uid": 123}
        mock_index = Mock()
        mock_meilisearch_client.index.return_value = mock_index
        
        result = await client.create_index("test_index", "id")
        
        assert result["status"] == "created"
        assert result["index"] == "test_index"
        assert result["task_uid"] == 123
        mock_meilisearch_client.create_index.assert_called_once_with(
            "test_index", {"primaryKey": "id"}
        )
    
    @pytest.mark.asyncio
    async def test_add_documents_with_models(self, client, mock_meilisearch_client):
        """Test adding documents using DocumentModel."""
        mock_index = Mock()
        mock_meilisearch_client.index.return_value = mock_index
        mock_meilisearch_client.get_index.return_value = mock_index
        mock_index.add_documents.return_value = {"taskUid": 456}
        
        # Create test documents
        doc1 = DocumentModel(
            id="1",
            title="Test Document",
            content="Test content",
            thai_content="เนื้อหาทดสอบ",
            created_at=datetime(2024, 1, 1, 12, 0, 0)
        )
        doc2 = DocumentModel(
            id="2",
            title="Another Document",
            content="More content"
        )
        
        # Mock get_index to avoid index creation
        client._indexes["test_index"] = mock_index
        
        result = await client.add_documents("test_index", [doc1, doc2])
        
        assert result["status"] == "added"
        assert result["count"] == 2
        assert result["task_uid"] == 456
        
        # Verify the documents were converted properly
        call_args = mock_index.add_documents.call_args
        documents = call_args[0][0]
        
        assert len(documents) == 2
        assert documents[0]["id"] == "1"
        assert documents[0]["thai_content"] == "เนื้อหาทดสอบ"
        assert documents[0]["created_at"] == "2024-01-01T12:00:00"
        assert documents[1]["id"] == "2"
        assert "created_at" not in documents[1]  # Should be excluded if None
    
    @pytest.mark.asyncio
    async def test_search_with_options(self, client, mock_meilisearch_client):
        """Test search with options."""
        mock_index = Mock()
        mock_meilisearch_client.index.return_value = mock_index
        mock_index.search.return_value = {
            "hits": [{"id": "1", "title": "Test"}],
            "query": "test",
            "processingTimeMs": 10
        }
        
        client._indexes["test_index"] = mock_index
        
        search_options = {"limit": 10, "attributesToHighlight": ["title"]}
        result = await client.search("test_index", "test query", search_options)
        
        assert len(result["hits"]) == 1
        assert result["query"] == "test"
        mock_index.search.assert_called_once_with("test query", search_options)
    
    @pytest.mark.asyncio
    async def test_retry_logic_success_after_failures(self, client, mock_meilisearch_client):
        """Test retry logic succeeds after initial failures."""
        from meilisearch.errors import MeilisearchError
        
        # Mock to fail once then succeed
        mock_meilisearch_client.create_index.side_effect = [
            MeilisearchError("Temporary error"),
            {"taskUid": 123}
        ]
        mock_meilisearch_client.get_task.return_value = {"status": "succeeded", "uid": 123}
        mock_index = Mock()
        mock_meilisearch_client.index.return_value = mock_index
        
        result = await client.create_index("test_index")
        
        assert result["status"] == "created"
        assert mock_meilisearch_client.create_index.call_count == 2
    
    @pytest.mark.asyncio
    async def test_retry_exhaustion(self, client, mock_meilisearch_client):
        """Test retry logic when all attempts fail."""
        from meilisearch.errors import MeilisearchError
        
        error = MeilisearchError("Persistent error")
        mock_meilisearch_client.health.side_effect = error
        
        result = await client.health_check()
        
        assert result["status"] == "unhealthy"
        assert "Persistent error" in result["error"]
        assert mock_meilisearch_client.health.call_count == 2  # max_retries
    
    @pytest.mark.asyncio
    async def test_update_index_settings(self, client, mock_meilisearch_client):
        """Test updating index settings."""
        mock_index = Mock()
        mock_meilisearch_client.index.return_value = mock_index
        mock_index.update_settings.return_value = {"taskUid": 789}
        mock_meilisearch_client.get_task.return_value = {"status": "succeeded", "uid": 789}
        
        client._indexes["test_index"] = mock_index
        
        settings = {
            "separatorTokens": ["​", "​​"],
            "nonSeparatorTokens": ["ๆ", "ฯ"]
        }
        
        result = await client.update_index_settings("test_index", settings)
        
        assert result["status"] == "updated"
        assert result["task_uid"] == 789
        mock_index.update_settings.assert_called_once_with(settings)
    
    @pytest.mark.asyncio
    async def test_get_index_stats(self, client, mock_meilisearch_client):
        """Test getting index statistics."""
        mock_index = Mock()
        mock_meilisearch_client.index.return_value = mock_index
        mock_index.get_stats.return_value = {
            "numberOfDocuments": 100,
            "isIndexing": False,
            "fieldDistribution": {"title": 100, "content": 95}
        }
        
        client._indexes["test_index"] = mock_index
        
        stats = await client.get_index_stats("test_index")
        
        assert isinstance(stats, IndexStats)
        assert stats.number_of_documents == 100
        assert stats.is_indexing is False
        assert stats.field_distribution["title"] == 100
    
    @pytest.mark.asyncio
    async def test_delete_documents(self, client, mock_meilisearch_client):
        """Test deleting multiple documents."""
        mock_index = Mock()
        mock_meilisearch_client.index.return_value = mock_index
        mock_index.delete_documents.return_value = {"taskUid": 999}
        
        client._indexes["test_index"] = mock_index
        
        document_ids = ["1", "2", "3"]
        result = await client.delete_documents("test_index", document_ids)
        
        assert result["status"] == "deleted"
        assert result["count"] == 3
        assert result["task_uid"] == 999
        mock_index.delete_documents.assert_called_once_with(document_ids)
    
    @pytest.mark.asyncio
    async def test_wait_for_task_success(self, client, mock_meilisearch_client):
        """Test waiting for task completion."""
        mock_meilisearch_client.get_task.side_effect = [
            {"status": "enqueued", "uid": 123},
            {"status": "processing", "uid": 123},
            {"status": "succeeded", "uid": 123}
        ]
        
        result = await client._wait_for_task(123, timeout=5)
        
        assert result["status"] == "succeeded"
        assert result["uid"] == 123
        assert mock_meilisearch_client.get_task.call_count == 3
    
    @pytest.mark.asyncio
    async def test_wait_for_task_failure(self, client, mock_meilisearch_client):
        """Test waiting for failed task."""
        from meilisearch.errors import MeilisearchError
        
        mock_meilisearch_client.get_task.return_value = {
            "status": "failed",
            "uid": 123,
            "error": {"message": "Task failed"}
        }
        
        with pytest.raises(MeilisearchError, match="Task 123 failed: Task failed"):
            await client._wait_for_task(123)
    
    @pytest.mark.asyncio
    async def test_get_task_status(self, client, mock_meilisearch_client):
        """Test getting task status."""
        mock_task = {
            "uid": 123,
            "status": "succeeded",
            "type": "documentAdditionOrUpdate",
            "startedAt": "2024-01-01T12:00:00Z",
            "finishedAt": "2024-01-01T12:00:01Z",
            "error": None
        }
        mock_meilisearch_client.get_task.return_value = mock_task
        
        result = await client.get_task_status(123)
        
        assert result["uid"] == 123
        assert result["status"] == "succeeded"
        assert result["type"] == "documentAdditionOrUpdate"
        assert result["started_at"] == "2024-01-01T12:00:00Z"
        assert result["finished_at"] == "2024-01-01T12:00:01Z"
        assert result["error"] is None


class TestDocumentModel:
    """Test cases for DocumentModel."""
    
    def test_document_model_creation(self):
        """Test creating a DocumentModel."""
        doc = DocumentModel(
            id="test-1",
            title="Test Document",
            content="This is test content",
            thai_content="เนื้อหาทดสอบ",
            metadata={"category": "test", "priority": 1}
        )
        
        assert doc.id == "test-1"
        assert doc.title == "Test Document"
        assert doc.thai_content == "เนื้อหาทดสอบ"
        assert doc.metadata["category"] == "test"
        assert doc.tokenized_content is None
    
    def test_document_model_defaults(self):
        """Test DocumentModel with default values."""
        doc = DocumentModel(id="test-2")
        
        assert doc.id == "test-2"
        assert doc.title == ""
        assert doc.content == ""
        assert doc.thai_content is None
        assert doc.metadata == {}
        assert doc.created_at is None


class TestMeiliSearchConfig:
    """Test cases for MeiliSearchConfig."""
    
    def test_config_creation(self):
        """Test creating MeiliSearchConfig."""
        config = MeiliSearchConfig(
            host="http://localhost:7700",
            api_key="test_key",
            timeout=60,
            max_retries=5,
            retry_delay=2.0
        )
        
        assert config.host == "http://localhost:7700"
        assert config.api_key == "test_key"
        assert config.timeout == 60
        assert config.max_retries == 5
        assert config.retry_delay == 2.0
    
    def test_config_defaults(self):
        """Test MeiliSearchConfig with default values."""
        config = MeiliSearchConfig(host="http://localhost:7700")
        
        assert config.host == "http://localhost:7700"
        assert config.api_key is None
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.retry_delay == 1.0