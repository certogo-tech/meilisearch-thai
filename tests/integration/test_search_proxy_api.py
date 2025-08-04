"""
Integration tests for search proxy API endpoints.

Tests the complete API flow including request validation, processing,
and response formatting.
"""

import pytest
import json
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from src.api.main import app
from src.search_proxy.services.search_proxy_service import SearchProxyService
from src.search_proxy.config.settings import SearchProxySettings


class TestSearchProxyAPIIntegration:
    """Integration tests for search proxy API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_search_service(self):
        """Create mock search proxy service."""
        service = AsyncMock(spec=SearchProxyService)
        
        # Mock health check
        service.health_check.return_value = {
            "service": "thai-search-proxy",
            "status": "healthy",
            "version": "1.0.0",
            "environment": "test",
            "components": {
                "query_processor": "healthy",
                "search_executor": "healthy",
                "result_ranker": "healthy"
            },
            "dependencies": {
                "meilisearch": {"status": "healthy"}
            },
            "metrics": {
                "total_searches": 100,
                "success_rate_percent": 95.0,
                "avg_response_time_ms": 50.0
            }
        }
        
        return service
    
    def test_search_endpoint_success(self, client, mock_search_service):
        """Test successful search request."""
        # Mock search response
        from src.search_proxy.models.responses import (
            SearchResponse, SearchHit, QueryInfo, PaginationInfo
        )
        
        mock_response = SearchResponse(
            hits=[
                SearchHit(
                    id="1",
                    score=0.9,
                    document={"title": "Test Document", "content": "Test content"}
                )
            ],
            total_hits=1,
            processing_time_ms=50.0,
            query_info=QueryInfo(
                original_query="test query",
                processed_query="test query",
                thai_content_detected=False,
                mixed_content=False,
                query_variants_used=1
            ),
            pagination=PaginationInfo(
                offset=0,
                limit=20,
                total_hits=1,
                has_next_page=False,
                has_previous_page=False
            )
        )
        
        mock_search_service.search.return_value = mock_response
        
        with patch('src.api.endpoints.search_proxy.get_search_proxy_service', return_value=mock_search_service):
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "test query",
                    "index_name": "test_index"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["total_hits"] == 1
        assert len(data["hits"]) == 1
        assert data["query_info"]["original_query"] == "test query"
    
    def test_search_endpoint_validation_error(self, client):
        """Test search request validation."""
        # Empty query
        response = client.post(
            "/api/v1/search",
            json={
                "query": "",
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert "error" in data
        assert "empty" in data["message"].lower()
    
    def test_search_endpoint_with_options(self, client, mock_search_service):
        """Test search with advanced options."""
        from src.search_proxy.models.responses import SearchResponse, QueryInfo, PaginationInfo
        
        mock_search_service.search.return_value = SearchResponse(
            hits=[],
            total_hits=0,
            processing_time_ms=30.0,
            query_info=QueryInfo(
                original_query="filtered query",
                processed_query="filtered query",
                thai_content_detected=False,
                mixed_content=False,
                query_variants_used=1
            ),
            pagination=PaginationInfo(
                offset=10,
                limit=50,
                total_hits=0,
                has_next_page=False,
                has_previous_page=True
            )
        )
        
        with patch('src.api.endpoints.search_proxy.get_search_proxy_service', return_value=mock_search_service):
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "filtered query",
                    "index_name": "test_index",
                    "options": {
                        "limit": 50,
                        "offset": 10,
                        "filters": "category = 'tech'",
                        "sort": ["date:desc"]
                    }
                }
            )
        
        assert response.status_code == 200
        
        # Verify service was called with correct options
        call_args = mock_search_service.search.call_args[0][0]
        assert call_args.options.limit == 50
        assert call_args.options.offset == 10
        assert call_args.options.filters == "category = 'tech'"
    
    def test_batch_search_endpoint(self, client, mock_search_service):
        """Test batch search endpoint."""
        from src.search_proxy.models.responses import SearchResponse, QueryInfo, PaginationInfo
        
        # Mock batch responses
        mock_responses = [
            SearchResponse(
                hits=[],
                total_hits=i,
                processing_time_ms=25.0,
                query_info=QueryInfo(
                    original_query=f"query{i}",
                    processed_query=f"query{i}",
                    thai_content_detected=False,
                    mixed_content=False,
                    query_variants_used=1
                ),
                pagination=PaginationInfo(
                    offset=0,
                    limit=20,
                    total_hits=i,
                    has_next_page=False,
                    has_previous_page=False
                )
            )
            for i in range(3)
        ]
        
        mock_search_service.batch_search.return_value = mock_responses
        
        with patch('src.api.endpoints.search_proxy.get_search_proxy_service', return_value=mock_search_service):
            response = client.post(
                "/api/v1/batch-search",
                json={
                    "queries": ["query0", "query1", "query2"],
                    "index_name": "test_index"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 3
        assert all("total_hits" in item for item in data)
    
    def test_batch_search_validation(self, client):
        """Test batch search validation."""
        # Empty queries list
        response = client.post(
            "/api/v1/batch-search",
            json={
                "queries": [],
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        assert "empty" in response.json()["message"].lower()
        
        # Too many queries
        response = client.post(
            "/api/v1/batch-search",
            json={
                "queries": ["q"] * 51,
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        assert "too many" in response.json()["message"].lower()
    
    def test_health_endpoint(self, client, mock_search_service):
        """Test health check endpoint."""
        with patch('src.api.endpoints.search_proxy.get_search_proxy_service', return_value=mock_search_service):
            response = client.get("/api/v1/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "components" in data
        assert "dependencies" in data
        assert "metrics" in data
    
    def test_analytics_endpoints(self, client):
        """Test analytics API endpoints."""
        # Query analytics
        response = client.get("/api/v1/analytics/queries")
        assert response.status_code == 200
        data = response.json()
        assert "total_unique_queries" in data
        assert "top_queries" in data
        
        # Session analytics
        response = client.get("/api/v1/analytics/sessions")
        assert response.status_code == 200
        data = response.json()
        assert "active_sessions" in data
        assert "avg_session_duration_seconds" in data
        
        # Performance trends
        response = client.get("/api/v1/analytics/performance-trends?hours=24")
        assert response.status_code == 200
        data = response.json()
        assert "period_hours" in data
        assert "trends" in data
        
        # Quality report
        response = client.get("/api/v1/analytics/quality-report")
        assert response.status_code == 200
        data = response.json()
        assert "zero_result_queries" in data
        assert "slow_queries" in data
        assert "recommendations" in data
    
    def test_metrics_endpoints(self, client):
        """Test metrics endpoints."""
        # Main metrics endpoint
        response = client.get("/metrics")
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/plain")
        content = response.text
        assert "# Thai Tokenizer" in content
        
        # Search proxy specific metrics
        response = client.get("/metrics/search-proxy")
        assert response.status_code == 200
        content = response.text
        assert "# Thai Search Proxy Metrics" in content
        assert "search_proxy_total_searches" in content
    
    def test_search_with_thai_content(self, client, mock_search_service):
        """Test search with Thai language content."""
        from src.search_proxy.models.responses import (
            SearchResponse, SearchHit, QueryInfo, PaginationInfo
        )
        
        mock_response = SearchResponse(
            hits=[
                SearchHit(
                    id="1",
                    score=0.95,
                    document={
                        "title": "เอกสารภาษาไทย",
                        "content": "เนื้อหาของเอกสารภาษาไทย"
                    }
                )
            ],
            total_hits=1,
            processing_time_ms=60.0,
            query_info=QueryInfo(
                original_query="ค้นหาเอกสาร",
                processed_query="ค้นหา เอกสาร",
                thai_content_detected=True,
                mixed_content=False,
                query_variants_used=3
            ),
            pagination=PaginationInfo(
                offset=0,
                limit=20,
                total_hits=1,
                has_next_page=False,
                has_previous_page=False
            )
        )
        
        mock_search_service.search.return_value = mock_response
        
        with patch('src.api.endpoints.search_proxy.get_search_proxy_service', return_value=mock_search_service):
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "ค้นหาเอกสาร",
                    "index_name": "thai_documents"
                }
            )
        
        assert response.status_code == 200
        data = response.json()
        assert data["query_info"]["thai_content_detected"] is True
        assert data["query_info"]["query_variants_used"] == 3
    
    def test_error_response_format(self, client, mock_search_service):
        """Test error response formatting."""
        # Mock service error
        mock_search_service.search.side_effect = RuntimeError("Service unavailable")
        
        with patch('src.api.endpoints.search_proxy.get_search_proxy_service', return_value=mock_search_service):
            response = client.post(
                "/api/v1/search",
                json={
                    "query": "test query",
                    "index_name": "test_index"
                }
            )
        
        # Should handle error gracefully
        assert response.status_code in [200, 503]  # Depends on error handling
        data = response.json()
        
        # Should still have valid response structure
        if response.status_code == 200:
            assert "hits" in data
            assert "total_hits" in data
            assert data["total_hits"] == 0
    
    def test_concurrent_api_requests(self, client, mock_search_service):
        """Test handling of concurrent API requests."""
        from src.search_proxy.models.responses import SearchResponse, QueryInfo, PaginationInfo
        import threading
        
        mock_search_service.search.return_value = SearchResponse(
            hits=[],
            total_hits=0,
            processing_time_ms=25.0,
            query_info=QueryInfo(
                original_query="concurrent test",
                processed_query="concurrent test",
                thai_content_detected=False,
                mixed_content=False,
                query_variants_used=1
            ),
            pagination=PaginationInfo(
                offset=0,
                limit=20,
                total_hits=0,
                has_next_page=False,
                has_previous_page=False
            )
        )
        
        results = []
        
        def make_request():
            with patch('src.api.endpoints.search_proxy.get_search_proxy_service', return_value=mock_search_service):
                response = client.post(
                    "/api/v1/search",
                    json={
                        "query": "concurrent test",
                        "index_name": "test_index"
                    }
                )
                results.append(response.status_code)
        
        # Create multiple concurrent requests
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads
        for thread in threads:
            thread.join()
        
        # All requests should succeed
        assert all(status == 200 for status in results)