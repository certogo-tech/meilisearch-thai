"""
Unit tests for search proxy API endpoints.

Tests the FastAPI endpoints for proper request handling, validation,
and error responses.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from fastapi import FastAPI

from src.api.endpoints.search_proxy import router
from src.search_proxy.models.requests import SearchRequest, BatchSearchRequest, SearchOptions
from src.search_proxy.models.responses import SearchResponse, QueryInfo, PaginationInfo
from src.search_proxy.exceptions import ValidationError, SearchExecutionError, ServiceUnavailableError


# Create test app
app = FastAPI()
app.include_router(router, prefix="/api/v1")

client = TestClient(app)


class TestSearchEndpoint:
    """Test cases for the /search endpoint."""
    
    def test_search_request_validation_empty_query(self):
        """Test validation of empty query."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "",
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "empty" in data["message"].lower()
    
    def test_search_request_validation_long_query(self):
        """Test validation of overly long query."""
        long_query = "a" * 1001  # Exceeds 1000 character limit
        
        response = client.post(
            "/api/v1/search",
            json={
                "query": long_query,
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "too long" in data["message"].lower()
    
    def test_search_request_validation_invalid_index_name(self):
        """Test validation of invalid index name."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "test query",
                "index_name": "invalid@index!"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_search_request_validation_invalid_options(self):
        """Test validation of invalid search options."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "test query",
                "index_name": "test_index",
                "options": {
                    "limit": 101,  # Exceeds maximum
                    "offset": -1   # Negative offset
                }
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_search_request_valid_thai_query(self):
        """Test valid Thai search request."""
        # This test would need proper service mocking
        # For now, just test that the request structure is accepted
        response = client.post(
            "/api/v1/search",
            json={
                "query": "ค้นหาเอกสารภาษาไทย",
                "index_name": "documents",
                "options": {
                    "limit": 10,
                    "highlight": True,
                    "tokenization_engine": "newmm"
                },
                "include_tokenization_info": True
            }
        )
        
        # Without proper service mocking, this will fail with service unavailable
        # But the request structure should be valid
        assert response.status_code in [503, 500]  # Service not available in test


class TestBatchSearchEndpoint:
    """Test cases for the /batch-search endpoint."""
    
    def test_batch_search_validation_empty_queries(self):
        """Test validation of empty queries list."""
        response = client.post(
            "/api/v1/batch-search",
            json={
                "queries": [],
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
    
    def test_batch_search_validation_too_many_queries(self):
        """Test validation of too many queries."""
        queries = ["query"] * 51  # Exceeds 50 query limit
        
        response = client.post(
            "/api/v1/batch-search",
            json={
                "queries": queries,
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "too many" in data["message"].lower()
    
    def test_batch_search_validation_empty_query_in_batch(self):
        """Test validation of empty query within batch."""
        response = client.post(
            "/api/v1/batch-search",
            json={
                "queries": ["valid query", "", "another valid query"],
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "query 2" in data["message"].lower()
    
    def test_batch_search_validation_long_query_in_batch(self):
        """Test validation of overly long query within batch."""
        long_query = "a" * 1001
        
        response = client.post(
            "/api/v1/batch-search",
            json={
                "queries": ["valid query", long_query],
                "index_name": "test_index"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        assert data["error"] == "VALIDATION_ERROR"
        assert "query 2" in data["message"].lower()
    
    def test_batch_search_valid_thai_queries(self):
        """Test valid Thai batch search request."""
        response = client.post(
            "/api/v1/batch-search",
            json={
                "queries": [
                    "ค้นหาเอกสาร",
                    "Thai document search",
                    "การค้นหาข้อมูล"
                ],
                "index_name": "documents",
                "options": {
                    "limit": 5,
                    "highlight": True,
                    "enable_compound_search": True
                },
                "include_tokenization_info": True
            }
        )
        
        # Without proper service mocking, this will fail with service unavailable
        # But the request structure should be valid
        assert response.status_code in [503, 500]  # Service not available in test


class TestHealthCheckEndpoint:
    """Test cases for the /health endpoint."""
    
    def test_health_check_endpoint_exists(self):
        """Test that health check endpoint exists."""
        response = client.get("/api/v1/health")
        
        # Without proper service mocking, this will fail
        # But the endpoint should exist
        assert response.status_code in [200, 503, 500]
        
        # Response should be JSON
        data = response.json()
        assert isinstance(data, dict)


class TestErrorResponseFormat:
    """Test cases for error response formatting."""
    
    def test_validation_error_response_format(self):
        """Test that validation errors have consistent format."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "",
                "index_name": "test"
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Check required error response fields
        assert "error" in data
        assert "message" in data
        assert "timestamp" in data
        assert "fallback_used" in data
        
        # Check error type
        assert data["error"] == "VALIDATION_ERROR"
        assert isinstance(data["fallback_used"], bool)
    
    def test_pydantic_validation_error_response_format(self):
        """Test that Pydantic validation errors are properly formatted."""
        response = client.post(
            "/api/v1/search",
            json={
                "query": "valid query",
                "index_name": "test",
                "options": {
                    "limit": "invalid_number"  # Should be integer
                }
            }
        )
        
        assert response.status_code == 422
        data = response.json()
        
        # Check error response format
        assert data["error"] == "VALIDATION_ERROR"
        assert "validation" in data["message"].lower()
        assert "details" in data
        assert "validation_errors" in data["details"]


if __name__ == "__main__":
    pytest.main([__file__])