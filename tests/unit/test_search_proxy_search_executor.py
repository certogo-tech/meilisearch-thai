"""
Unit tests for the search proxy SearchExecutor component.

Tests parallel search execution, error handling, and retry logic.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.search_proxy.services.search_executor import (
    SearchExecutor, SearchExecutorConfig, SearchResult, SearchError
)
from src.search_proxy.models.query import QueryVariant, QueryVariantType
from src.search_proxy.models.search import SearchOptions
from src.meilisearch_integration.client import MeiliSearchClient


class TestSearchExecutor:
    """Test cases for the SearchExecutor component."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return SearchExecutorConfig(
            max_concurrent_searches=3,
            search_timeout_ms=5000,
            enable_parallel_execution=True,
            retry_failed_searches=True,
            max_retries=2,
            retry_delay_ms=100
        )
    
    @pytest.fixture
    def mock_meilisearch_client(self):
        """Create a mock MeiliSearch client."""
        client = AsyncMock(spec=MeiliSearchClient)
        client.health_check.return_value = {"status": "healthy"}
        return client
    
    @pytest.fixture
    def search_executor(self, mock_meilisearch_client, config):
        """Create a SearchExecutor instance for testing."""
        return SearchExecutor(
            meilisearch_client=mock_meilisearch_client,
            config=config
        )
    
    @pytest.mark.asyncio
    async def test_single_variant_search(self, search_executor, mock_meilisearch_client):
        """Test searching with a single query variant."""
        # Setup mock response
        mock_response = {
            "hits": [
                {"id": "1", "title": "Document 1"},
                {"id": "2", "title": "Document 2"}
            ],
            "query": "test query",
            "processingTimeMs": 25,
            "limit": 20,
            "offset": 0,
            "estimatedTotalHits": 2
        }
        mock_meilisearch_client.search.return_value = mock_response
        
        # Create query variant
        variant = QueryVariant(
            query_text="test query",
            variant_type=QueryVariantType.ORIGINAL,
            weight=1.0
        )
        
        # Execute search
        results = await search_executor.execute_parallel_searches(
            query_variants=[variant],
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)
        assert results[0].success is True
        assert len(results[0].hits) == 2
        assert results[0].query_variant == variant
        assert results[0].search_time_ms > 0
    
    @pytest.mark.asyncio
    async def test_parallel_variant_search(self, search_executor, mock_meilisearch_client):
        """Test parallel searching with multiple query variants."""
        # Setup mock responses
        mock_meilisearch_client.search.side_effect = [
            {
                "hits": [{"id": "1", "title": "Document 1"}],
                "estimatedTotalHits": 1
            },
            {
                "hits": [{"id": "2", "title": "Document 2"}],
                "estimatedTotalHits": 1
            },
            {
                "hits": [{"id": "3", "title": "Document 3"}],
                "estimatedTotalHits": 1
            }
        ]
        
        # Create multiple query variants
        variants = [
            QueryVariant(query_text="query1", variant_type=QueryVariantType.ORIGINAL, weight=1.0),
            QueryVariant(query_text="query2", variant_type=QueryVariantType.TOKENIZED, weight=0.8),
            QueryVariant(query_text="query3", variant_type=QueryVariantType.FUZZY, weight=0.6)
        ]
        
        # Execute parallel search
        results = await search_executor.execute_parallel_searches(
            query_variants=variants,
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        assert len(results) == 3
        assert all(r.success for r in results)
        assert mock_meilisearch_client.search.call_count == 3
        
        # Verify each result corresponds to correct variant
        for i, result in enumerate(results):
            assert result.query_variant == variants[i]
            assert len(result.hits) == 1
    
    @pytest.mark.asyncio
    async def test_search_with_filters(self, search_executor, mock_meilisearch_client):
        """Test search with filters applied."""
        mock_meilisearch_client.search.return_value = {
            "hits": [{"id": "1", "category": "tech"}],
            "estimatedTotalHits": 1
        }
        
        variant = QueryVariant(
            query_text="test query",
            variant_type=QueryVariantType.ORIGINAL,
            weight=1.0
        )
        
        search_options = SearchOptions(
            filters="category = 'tech'",
            limit=10,
            offset=0
        )
        
        results = await search_executor.execute_parallel_searches(
            query_variants=[variant],
            index_name="test_index",
            search_options=search_options
        )
        
        # Verify filter was passed to MeiliSearch
        mock_meilisearch_client.search.assert_called_with(
            index_name="test_index",
            query="test query",
            filter="category = 'tech'",
            limit=10,
            offset=0,
            show_matches_position=True,
            attributes_to_highlight=["*"],
            highlight_pre_tag="<mark>",
            highlight_post_tag="</mark>"
        )
    
    @pytest.mark.asyncio
    async def test_search_error_handling(self, search_executor, mock_meilisearch_client):
        """Test error handling during search execution."""
        # Mock search failure
        mock_meilisearch_client.search.side_effect = Exception("Search failed")
        
        variant = QueryVariant(
            query_text="test query",
            variant_type=QueryVariantType.ORIGINAL,
            weight=1.0
        )
        
        results = await search_executor.execute_parallel_searches(
            query_variants=[variant],
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        assert len(results) == 1
        assert results[0].success is False
        assert isinstance(results[0].error, SearchError)
        assert "Search failed" in results[0].error.message
    
    @pytest.mark.asyncio
    async def test_search_retry_logic(self, search_executor, mock_meilisearch_client):
        """Test retry logic on search failure."""
        # Mock failure then success
        mock_meilisearch_client.search.side_effect = [
            Exception("Temporary failure"),
            {"hits": [{"id": "1"}], "estimatedTotalHits": 1}
        ]
        
        variant = QueryVariant(
            query_text="test query",
            variant_type=QueryVariantType.ORIGINAL,
            weight=1.0
        )
        
        results = await search_executor.execute_parallel_searches(
            query_variants=[variant],
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        assert len(results) == 1
        assert results[0].success is True
        assert mock_meilisearch_client.search.call_count == 2  # Initial + 1 retry
    
    @pytest.mark.asyncio
    async def test_search_timeout(self, search_executor, mock_meilisearch_client):
        """Test search timeout handling."""
        # Mock slow search
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(10)  # Longer than timeout
            return {"hits": [], "estimatedTotalHits": 0}
        
        mock_meilisearch_client.search.side_effect = slow_search
        
        # Set short timeout
        search_executor.config.search_timeout_ms = 100
        
        variant = QueryVariant(
            query_text="test query",
            variant_type=QueryVariantType.ORIGINAL,
            weight=1.0
        )
        
        results = await search_executor.execute_parallel_searches(
            query_variants=[variant],
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        assert len(results) == 1
        assert results[0].success is False
        assert results[0].error.error_type == "timeout"
    
    @pytest.mark.asyncio
    async def test_concurrent_search_limit(self, search_executor, mock_meilisearch_client):
        """Test concurrent search limit enforcement."""
        search_count = 0
        concurrent_searches = []
        
        async def track_concurrent_search(*args, **kwargs):
            nonlocal search_count
            search_count += 1
            concurrent_searches.append(search_count)
            await asyncio.sleep(0.1)  # Simulate search time
            search_count -= 1
            return {"hits": [], "estimatedTotalHits": 0}
        
        mock_meilisearch_client.search.side_effect = track_concurrent_search
        
        # Create more variants than concurrent limit
        variants = [
            QueryVariant(query_text=f"query{i}", variant_type=QueryVariantType.ORIGINAL, weight=1.0)
            for i in range(10)
        ]
        
        # Execute with concurrent limit of 3
        search_executor.config.max_concurrent_searches = 3
        
        results = await search_executor.execute_parallel_searches(
            query_variants=variants,
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        assert len(results) == 10
        assert max(concurrent_searches) <= 3  # Never exceed concurrent limit
    
    @pytest.mark.asyncio
    async def test_search_result_deduplication(self, search_executor, mock_meilisearch_client):
        """Test deduplication of search results."""
        # Mock responses with duplicate documents
        mock_meilisearch_client.search.side_effect = [
            {
                "hits": [
                    {"id": "1", "title": "Document 1"},
                    {"id": "2", "title": "Document 2"}
                ],
                "estimatedTotalHits": 2
            },
            {
                "hits": [
                    {"id": "2", "title": "Document 2"},  # Duplicate
                    {"id": "3", "title": "Document 3"}
                ],
                "estimatedTotalHits": 2
            }
        ]
        
        variants = [
            QueryVariant(query_text="query1", variant_type=QueryVariantType.ORIGINAL, weight=1.0),
            QueryVariant(query_text="query2", variant_type=QueryVariantType.TOKENIZED, weight=0.8)
        ]
        
        results = await search_executor.execute_parallel_searches(
            query_variants=variants,
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        # Collect all unique document IDs
        all_doc_ids = set()
        for result in results:
            if result.success:
                for hit in result.hits:
                    all_doc_ids.add(hit["id"])
        
        assert len(all_doc_ids) == 3  # Should have 3 unique documents
    
    @pytest.mark.asyncio
    async def test_search_with_pagination(self, search_executor, mock_meilisearch_client):
        """Test search with pagination parameters."""
        mock_meilisearch_client.search.return_value = {
            "hits": [{"id": f"{i}"} for i in range(10, 20)],
            "estimatedTotalHits": 100
        }
        
        variant = QueryVariant(
            query_text="test query",
            variant_type=QueryVariantType.ORIGINAL,
            weight=1.0
        )
        
        search_options = SearchOptions(
            limit=10,
            offset=10  # Second page
        )
        
        results = await search_executor.execute_parallel_searches(
            query_variants=[variant],
            index_name="test_index",
            search_options=search_options
        )
        
        # Verify pagination parameters were passed
        mock_meilisearch_client.search.assert_called_with(
            index_name="test_index",
            query="test query",
            filter=None,
            limit=10,
            offset=10,
            show_matches_position=True,
            attributes_to_highlight=["*"],
            highlight_pre_tag="<mark>",
            highlight_post_tag="</mark>"
        )
    
    @pytest.mark.asyncio
    async def test_search_with_disabled_parallel_execution(self, search_executor, mock_meilisearch_client):
        """Test sequential search when parallel execution is disabled."""
        search_executor.config.enable_parallel_execution = False
        
        call_times = []
        
        async def track_call_time(*args, **kwargs):
            call_times.append(asyncio.get_event_loop().time())
            await asyncio.sleep(0.1)
            return {"hits": [], "estimatedTotalHits": 0}
        
        mock_meilisearch_client.search.side_effect = track_call_time
        
        variants = [
            QueryVariant(query_text=f"query{i}", variant_type=QueryVariantType.ORIGINAL, weight=1.0)
            for i in range(3)
        ]
        
        await search_executor.execute_parallel_searches(
            query_variants=variants,
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        # Verify searches were executed sequentially
        for i in range(1, len(call_times)):
            time_diff = call_times[i] - call_times[i-1]
            assert time_diff >= 0.09  # Should be at least 0.1s apart (with small tolerance)
    
    @pytest.mark.asyncio
    async def test_health_check(self, search_executor, mock_meilisearch_client):
        """Test health check functionality."""
        health_status = await search_executor.health_check()
        
        assert health_status["status"] == "healthy"
        assert health_status["meilisearch_connected"] is True
        assert "config" in health_status
        assert health_status["config"]["max_concurrent_searches"] == 3
    
    @pytest.mark.asyncio
    async def test_empty_query_variants(self, search_executor):
        """Test handling of empty query variants list."""
        results = await search_executor.execute_parallel_searches(
            query_variants=[],
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        assert results == []
    
    @pytest.mark.asyncio
    async def test_search_result_metadata(self, search_executor, mock_meilisearch_client):
        """Test that search results include proper metadata."""
        mock_meilisearch_client.search.return_value = {
            "hits": [{"id": "1", "_matchesPosition": {"title": [{"start": 0, "length": 4}]}}],
            "query": "test",
            "processingTimeMs": 15,
            "estimatedTotalHits": 1
        }
        
        variant = QueryVariant(
            query_text="test",
            variant_type=QueryVariantType.ORIGINAL,
            weight=1.0
        )
        
        results = await search_executor.execute_parallel_searches(
            query_variants=[variant],
            index_name="test_index",
            search_options=SearchOptions()
        )
        
        assert len(results) == 1
        result = results[0]
        
        assert result.total_hits == 1
        assert result.search_time_ms > 0
        assert result.index_name == "test_index"
        assert "_matchesPosition" in result.hits[0]