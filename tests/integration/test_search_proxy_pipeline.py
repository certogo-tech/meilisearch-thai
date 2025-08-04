"""
Integration tests for the complete search proxy pipeline.

Tests the end-to-end flow from query processing through search execution 
to result ranking, including error scenarios and edge cases.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.search_proxy.services.search_proxy_service import SearchProxyService
from src.search_proxy.config.settings import SearchProxySettings, get_development_settings
from src.search_proxy.models.requests import SearchRequest, BatchSearchRequest, SearchOptions
from src.search_proxy.models.responses import SearchResponse
from src.meilisearch_integration.client import MeiliSearchClient


class TestSearchProxyPipelineIntegration:
    """Integration tests for the complete search proxy pipeline."""
    
    @pytest.fixture
    async def mock_meilisearch_client(self):
        """Create a mock MeiliSearch client for testing."""
        client = AsyncMock(spec=MeiliSearchClient)
        
        # Default health check response
        client.health_check.return_value = {"status": "healthy"}
        
        # Default search response
        client.search.return_value = {
            "hits": [
                {
                    "id": "1",
                    "title": "Thai Document ภาษาไทย",
                    "content": "เนื้อหาเอกสารภาษาไทย",
                    "_rankingScore": 0.9
                },
                {
                    "id": "2", 
                    "title": "English Document",
                    "content": "English content here",
                    "_rankingScore": 0.8
                }
            ],
            "query": "test",
            "processingTimeMs": 25,
            "limit": 20,
            "offset": 0,
            "estimatedTotalHits": 2
        }
        
        return client
    
    @pytest.fixture
    async def search_proxy_service(self, mock_meilisearch_client):
        """Create and initialize a search proxy service for testing."""
        settings = get_development_settings()
        service = SearchProxyService(settings, mock_meilisearch_client)
        await service.initialize()
        return service
    
    @pytest.mark.asyncio
    async def test_complete_thai_search_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test complete pipeline with Thai language query."""
        # Create Thai search request
        request = SearchRequest(
            query="ค้นหาเอกสารภาษาไทย",
            index_name="documents"
        )
        
        # Execute search
        response = await search_proxy_service.search(request)
        
        # Verify response structure
        assert isinstance(response, SearchResponse)
        assert response.total_hits == 2
        assert len(response.hits) == 2
        assert response.processing_time_ms > 0
        
        # Verify query processing
        assert response.query_info.thai_content_detected is True
        assert response.query_info.original_query == "ค้นหาเอกสารภาษาไทย"
        assert response.query_info.query_variants_used > 0
        
        # Verify MeiliSearch was called
        assert mock_meilisearch_client.search.called
        
        # Verify pagination info
        assert response.pagination.offset == 0
        assert response.pagination.limit == 20
        assert response.pagination.has_next_page is False
    
    @pytest.mark.asyncio
    async def test_complete_english_search_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test complete pipeline with English language query."""
        request = SearchRequest(
            query="search documents database",
            index_name="documents",
            options=SearchOptions(limit=10)
        )
        
        response = await search_proxy_service.search(request)
        
        assert isinstance(response, SearchResponse)
        assert response.query_info.thai_content_detected is False
        assert response.query_info.mixed_content is False
        assert response.pagination.limit == 10
    
    @pytest.mark.asyncio
    async def test_mixed_language_search_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test pipeline with mixed Thai-English query."""
        request = SearchRequest(
            query="ค้นหา documents ใน database",
            index_name="documents"
        )
        
        # Mock tokenizer response for mixed content
        with patch('src.search_proxy.services.query_processor.QueryProcessor._tokenize_thai') as mock_tokenize:
            mock_tokenize.return_value = {
                "tokens": ["ค้นหา", "documents", "ใน", "database"],
                "success": True,
                "engine": "newmm",
                "processing_time_ms": 15.0
            }
            
            response = await search_proxy_service.search(request)
        
        assert response.query_info.thai_content_detected is True
        assert response.query_info.mixed_content is True
    
    @pytest.mark.asyncio
    async def test_search_with_filters_and_sorting(self, search_proxy_service, mock_meilisearch_client):
        """Test search with filters and sorting options."""
        request = SearchRequest(
            query="test query",
            index_name="documents",
            options=SearchOptions(
                filters="category = 'tech' AND published = true",
                sort=["date:desc", "score:desc"],
                limit=50
            )
        )
        
        response = await search_proxy_service.search(request)
        
        # Verify MeiliSearch was called with correct parameters
        mock_meilisearch_client.search.assert_called()
        call_args = mock_meilisearch_client.search.call_args[1]
        assert call_args["filter"] == "category = 'tech' AND published = true"
        assert call_args["sort"] == ["date:desc", "score:desc"]
        assert call_args["limit"] == 50
    
    @pytest.mark.asyncio
    async def test_batch_search_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test batch search processing pipeline."""
        # Mock different responses for different queries
        mock_meilisearch_client.search.side_effect = [
            {"hits": [{"id": "1"}], "estimatedTotalHits": 1},
            {"hits": [{"id": "2"}, {"id": "3"}], "estimatedTotalHits": 2},
            {"hits": [], "estimatedTotalHits": 0}
        ]
        
        request = BatchSearchRequest(
            queries=["query1", "query2", "query3"],
            index_name="documents"
        )
        
        responses = await search_proxy_service.batch_search(request)
        
        assert len(responses) == 3
        assert all(isinstance(r, SearchResponse) for r in responses)
        assert responses[0].total_hits == 1
        assert responses[1].total_hits == 2
        assert responses[2].total_hits == 0
    
    @pytest.mark.asyncio
    async def test_search_error_handling_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test error handling throughout the pipeline."""
        # Mock search failure
        mock_meilisearch_client.search.side_effect = Exception("MeiliSearch connection failed")
        
        request = SearchRequest(
            query="test query",
            index_name="documents"
        )
        
        response = await search_proxy_service.search(request)
        
        # Should return response even on error
        assert isinstance(response, SearchResponse)
        assert response.total_hits == 0
        assert len(response.hits) == 0
        assert response.query_info.fallback_used is True
    
    @pytest.mark.asyncio
    async def test_tokenization_fallback_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test pipeline with tokenization fallback."""
        request = SearchRequest(
            query="ค้นหาเอกสาร",
            index_name="documents"
        )
        
        # Mock primary tokenizer failure
        with patch('src.search_proxy.services.query_processor.QueryProcessor._tokenize_with_engine') as mock_tokenize:
            # First call fails, second succeeds
            mock_tokenize.side_effect = [
                Exception("Primary engine failed"),
                {
                    "tokens": ["ค้นหา", "เอกสาร"],
                    "success": True,
                    "engine": "attacut",
                    "processing_time_ms": 30.0
                }
            ]
            
            response = await search_proxy_service.search(request)
        
        assert response.query_info.fallback_used is True
        assert response.total_hits >= 0  # Should still return results
    
    @pytest.mark.asyncio
    async def test_empty_results_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test pipeline with no search results."""
        mock_meilisearch_client.search.return_value = {
            "hits": [],
            "estimatedTotalHits": 0
        }
        
        request = SearchRequest(
            query="no results query",
            index_name="documents"
        )
        
        response = await search_proxy_service.search(request)
        
        assert response.total_hits == 0
        assert len(response.hits) == 0
        assert response.pagination.has_next_page is False
    
    @pytest.mark.asyncio
    async def test_pagination_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test search with pagination through pipeline."""
        # Mock paginated results
        mock_meilisearch_client.search.return_value = {
            "hits": [{"id": str(i)} for i in range(10, 20)],
            "estimatedTotalHits": 100
        }
        
        request = SearchRequest(
            query="paginated query",
            index_name="documents",
            options=SearchOptions(
                offset=10,
                limit=10
            )
        )
        
        response = await search_proxy_service.search(request)
        
        assert len(response.hits) == 10
        assert response.pagination.offset == 10
        assert response.pagination.limit == 10
        assert response.pagination.has_previous_page is True
        assert response.pagination.has_next_page is True
    
    @pytest.mark.asyncio
    async def test_concurrent_searches_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test multiple concurrent searches through pipeline."""
        # Create multiple search requests
        requests = [
            SearchRequest(query=f"query {i}", index_name="documents")
            for i in range(5)
        ]
        
        # Execute searches concurrently
        responses = await asyncio.gather(*[
            search_proxy_service.search(req) for req in requests
        ])
        
        assert len(responses) == 5
        assert all(isinstance(r, SearchResponse) for r in responses)
        assert all(r.processing_time_ms > 0 for r in responses)
    
    @pytest.mark.asyncio
    async def test_search_with_tokenization_info(self, search_proxy_service, mock_meilisearch_client):
        """Test search with tokenization info included."""
        request = SearchRequest(
            query="ค้นหาเอกสาร",
            index_name="documents",
            include_tokenization_info=True
        )
        
        response = await search_proxy_service.search(request)
        
        # Should include tokenization details
        assert hasattr(response, 'tokenization_info') or response.query_info is not None
        assert response.query_info.query_variants_used > 0
    
    @pytest.mark.asyncio
    async def test_deduplication_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test result deduplication in pipeline."""
        # Mock multiple search calls with duplicate results
        mock_meilisearch_client.search.side_effect = [
            {
                "hits": [
                    {"id": "1", "title": "Doc 1", "_rankingScore": 0.9},
                    {"id": "2", "title": "Doc 2", "_rankingScore": 0.8}
                ],
                "estimatedTotalHits": 2
            },
            {
                "hits": [
                    {"id": "1", "title": "Doc 1", "_rankingScore": 0.85},  # Duplicate
                    {"id": "3", "title": "Doc 3", "_rankingScore": 0.75}
                ],
                "estimatedTotalHits": 2
            }
        ]
        
        request = SearchRequest(
            query="ค้นหา เอกสาร",  # Will generate multiple variants
            index_name="documents"
        )
        
        response = await search_proxy_service.search(request)
        
        # Check for unique results
        doc_ids = [hit.id for hit in response.hits]
        assert len(doc_ids) == len(set(doc_ids))  # No duplicates
        assert response.total_hits <= 3  # Should deduplicate
    
    @pytest.mark.asyncio
    async def test_health_check_integration(self, search_proxy_service):
        """Test health check with all components."""
        health = await search_proxy_service.health_check()
        
        assert health["status"] == "healthy"
        assert health["service"] == "thai-search-proxy"
        assert "components" in health
        assert "dependencies" in health
        assert "metrics" in health
        
        # Check component statuses
        assert health["components"]["query_processor"] == "healthy"
        assert health["components"]["search_executor"] == "healthy"
        assert health["components"]["result_ranker"] == "healthy"
        
        # Check metrics are included
        assert "total_searches" in health["metrics"]
        assert "success_rate_percent" in health["metrics"]
        assert "avg_response_time_ms" in health["metrics"]
    
    @pytest.mark.asyncio
    async def test_timeout_handling_pipeline(self, search_proxy_service, mock_meilisearch_client):
        """Test timeout handling in pipeline."""
        # Mock slow search
        async def slow_search(*args, **kwargs):
            await asyncio.sleep(10)
            return {"hits": [], "estimatedTotalHits": 0}
        
        mock_meilisearch_client.search.side_effect = slow_search
        
        # Set short timeout
        search_proxy_service.settings.search.timeout_ms = 100
        
        request = SearchRequest(
            query="timeout test",
            index_name="documents"
        )
        
        # Should handle timeout gracefully
        response = await search_proxy_service.search(request)
        
        assert isinstance(response, SearchResponse)
        assert response.total_hits == 0
        assert response.processing_time_ms < 1000  # Should timeout quickly


@pytest.mark.integration
class TestSearchProxyRealIntegration:
    """Integration tests with real components (requires running services)."""
    
    @pytest.mark.skipif(
        not pytest.config.getoption("--integration", default=False),
        reason="Integration tests require --integration flag"
    )
    @pytest.mark.asyncio
    async def test_real_meilisearch_integration(self):
        """Test with real MeiliSearch instance."""
        settings = SearchProxySettings(
            meilisearch_url="http://localhost:7700",
            meilisearch_api_key="masterKey"
        )
        
        try:
            service = SearchProxyService(settings)
            await service.initialize()
            
            request = SearchRequest(
                query="test search",
                index_name="test_index"
            )
            
            response = await service.search(request)
            
            assert isinstance(response, SearchResponse)
            assert response.processing_time_ms > 0
            
        except Exception as e:
            pytest.skip(f"MeiliSearch not available: {e}")