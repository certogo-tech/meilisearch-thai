"""
Unit tests for SearchExecutor class.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any, List

from src.search_proxy.services.search_executor import SearchExecutor, SearchExecutorConfig
from src.search_proxy.models.query import QueryVariant, QueryVariantType
from src.search_proxy.models.requests import SearchOptions
from src.search_proxy.models.search import SearchResult
from src.search_proxy.models.responses import SearchHit


class TestSearchExecutor:
    """Test cases for SearchExecutor class."""
    
    @pytest.fixture
    def mock_meilisearch_client(self):
        """Create a mock MeiliSearch client."""
        client = MagicMock()
        client.search = AsyncMock()
        client.health_check = AsyncMock(return_value={"status": "healthy"})
        return client
    
    @pytest.fixture
    def search_executor_config(self):
        """Create SearchExecutor configuration."""
        return SearchExecutorConfig(
            max_concurrent_searches=3,
            search_timeout_ms=5000,
            enable_parallel_execution=True,
            retry_failed_searches=True,
            max_retries=2
        )
    
    @pytest.fixture
    def search_executor(self, mock_meilisearch_client, search_executor_config):
        """Create SearchExecutor instance."""
        return SearchExecutor(mock_meilisearch_client, search_executor_config)
    
    @pytest.fixture
    def sample_query_variants(self):
        """Create sample query variants for testing."""
        return [
            QueryVariant(
                query_text="ค้นหาเอกสาร",
                variant_type=QueryVariantType.ORIGINAL,
                tokenization_engine="none",
                weight=0.8,
                search_options={}
            ),
            QueryVariant(
                query_text="ค้นหา เอกสาร",
                variant_type=QueryVariantType.TOKENIZED,
                tokenization_engine="newmm",
                weight=1.0,
                search_options={"matching_strategy": "last"}
            ),
            QueryVariant(
                query_text="ค้นหา เอกสาร ภาษาไทย",
                variant_type=QueryVariantType.COMPOUND_SPLIT,
                tokenization_engine="newmm",
                weight=0.9,
                search_options={}
            )
        ]
    
    @pytest.fixture
    def sample_search_options(self):
        """Create sample search options."""
        return SearchOptions(
            limit=10,
            offset=0,
            highlight=True,
            filters={"language": "thai"},
            sort=["created_at:desc"],
            matching_strategy="last"
        )
    
    @pytest.fixture
    def mock_meilisearch_response(self):
        """Create mock Meilisearch response."""
        return {
            "hits": [
                {
                    "id": "doc_1",
                    "_rankingScore": 0.95,
                    "title": "Thai Document 1",
                    "content": "เอกสารภาษาไทย",
                    "_formatted": {
                        "title": "<em>Thai</em> Document 1",
                        "content": "<em>เอกสาร</em>ภาษาไทย"
                    }
                },
                {
                    "id": "doc_2",
                    "_rankingScore": 0.87,
                    "title": "Thai Document 2",
                    "content": "เอกสารอื่น",
                    "_formatted": {
                        "title": "Thai Document 2",
                        "content": "<em>เอกสาร</em>อื่น"
                    }
                }
            ],
            "query": "ค้นหา เอกสาร",
            "processingTimeMs": 15,
            "limit": 10,
            "offset": 0,
            "estimatedTotalHits": 42
        }
    
    @pytest.mark.asyncio
    async def test_execute_single_search_success(
        self, 
        search_executor, 
        sample_query_variants, 
        sample_search_options,
        mock_meilisearch_response
    ):
        """Test successful single search execution."""
        # Setup
        variant = sample_query_variants[0]
        search_executor.client.search.return_value = mock_meilisearch_response
        
        # Execute
        result = await search_executor.execute_single_search(
            variant, "test_index", sample_search_options
        )
        
        # Verify
        assert isinstance(result, SearchResult)
        assert result.success is True
        assert result.error_message is None
        assert len(result.hits) == 2
        assert result.total_hits == 42
        assert result.query_variant == variant
        
        # Verify hits are properly converted
        first_hit = result.hits[0]
        assert first_hit.id == "doc_1"
        assert first_hit.score == 0.95
        assert first_hit.document["title"] == "Thai Document 1"
        assert first_hit.ranking_info["variant_weight"] == variant.weight
    
    @pytest.mark.asyncio
    async def test_execute_single_search_failure(
        self, 
        search_executor, 
        sample_query_variants, 
        sample_search_options
    ):
        """Test single search execution with failure."""
        # Setup
        variant = sample_query_variants[0]
        search_executor.client.search.side_effect = Exception("Meilisearch error")
        
        # Execute
        result = await search_executor.execute_single_search(
            variant, "test_index", sample_search_options
        )
        
        # Verify
        assert isinstance(result, SearchResult)
        assert result.success is False
        assert "Search failed: Meilisearch error" in result.error_message
        assert len(result.hits) == 0
        assert result.total_hits == 0
        assert result.query_variant == variant
    
    @pytest.mark.asyncio
    async def test_execute_parallel_searches_success(
        self, 
        search_executor, 
        sample_query_variants, 
        sample_search_options,
        mock_meilisearch_response
    ):
        """Test successful parallel search execution."""
        # Setup
        search_executor.client.search.return_value = mock_meilisearch_response
        
        # Execute
        results = await search_executor.execute_parallel_searches(
            sample_query_variants, "test_index", sample_search_options
        )
        
        # Verify
        assert len(results) == len(sample_query_variants)
        assert all(isinstance(r, SearchResult) for r in results)
        assert all(r.success for r in results)
        
        # Verify client was called for each variant
        assert search_executor.client.search.call_count == len(sample_query_variants)
    
    @pytest.mark.asyncio
    async def test_execute_parallel_searches_with_failures(
        self, 
        search_executor, 
        sample_query_variants, 
        sample_search_options,
        mock_meilisearch_response
    ):
        """Test parallel search execution with some failures."""
        # Setup - first call succeeds, second fails, third succeeds
        search_executor.client.search.side_effect = [
            mock_meilisearch_response,
            Exception("Search failed"),
            mock_meilisearch_response
        ]
        
        # Execute
        results = await search_executor.execute_parallel_searches(
            sample_query_variants, "test_index", sample_search_options
        )
        
        # Verify
        assert len(results) == len(sample_query_variants)
        assert results[0].success is True
        assert results[1].success is False
        assert results[2].success is True
        assert "Search failed" in results[1].error_message
    
    def test_translate_search_options_to_meilisearch(
        self, 
        search_executor, 
        sample_search_options,
        sample_query_variants
    ):
        """Test translation of SearchOptions to Meilisearch parameters."""
        variant = sample_query_variants[1]  # tokenized variant
        
        # Execute
        params = search_executor.translate_search_options_to_meilisearch(
            sample_search_options, variant
        )
        
        # Verify basic parameters
        assert params["limit"] == sample_search_options.limit
        assert params["offset"] == sample_search_options.offset
        assert params["sort"] == sample_search_options.sort
        assert params["matchingStrategy"] == "last"  # Should be adjusted for tokenized variant
        
        # Verify filter formatting
        assert "filter" in params
        assert 'language = "thai"' in params["filter"]
    
    def test_format_filters_for_meilisearch(self, search_executor):
        """Test filter formatting for Meilisearch."""
        # Test simple equality filter
        filters = {"language": "thai", "status": "published"}
        result = search_executor._format_filters_for_meilisearch(filters)
        assert 'language = "thai"' in result
        assert 'status = "published"' in result
        assert " AND " in result
        
        # Test complex filters with operators
        filters = {
            "score": {"$gte": 0.8, "$lte": 1.0},
            "category": {"$in": ["news", "article"]},
            "published": {"$exists": True}
        }
        result = search_executor._format_filters_for_meilisearch(filters)
        assert "score >= 0.8" in result
        assert "score <= 1.0" in result
        assert "category = " in result  # Should handle $in operator
        assert "published EXISTS" in result
    
    def test_collect_and_deduplicate_results_id_based(
        self, 
        search_executor,
        sample_query_variants
    ):
        """Test result collection and deduplication by ID."""
        # Create mock search results with duplicate IDs
        search_results = [
            SearchResult(
                query_variant=sample_query_variants[0],
                hits=[
                    SearchHit(id="doc_1", score=0.9, document={"title": "Doc 1"}, highlight=None, ranking_info=None),
                    SearchHit(id="doc_2", score=0.8, document={"title": "Doc 2"}, highlight=None, ranking_info=None)
                ],
                total_hits=2,
                processing_time_ms=10.0,
                success=True,
                error_message=None,
                meilisearch_metadata={}
            ),
            SearchResult(
                query_variant=sample_query_variants[1],
                hits=[
                    SearchHit(id="doc_1", score=0.95, document={"title": "Doc 1 Better"}, highlight=None, ranking_info=None),  # Higher score
                    SearchHit(id="doc_3", score=0.7, document={"title": "Doc 3"}, highlight=None, ranking_info=None)
                ],
                total_hits=2,
                processing_time_ms=12.0,
                success=True,
                error_message=None,
                meilisearch_metadata={}
            )
        ]
        
        # Execute
        deduplicated_hits, metadata = search_executor.collect_and_deduplicate_results(
            search_results, "id_based"
        )
        
        # Verify
        assert len(deduplicated_hits) == 3  # doc_1, doc_2, doc_3
        assert metadata["deduplication_count"] == 1  # One duplicate removed
        assert metadata["total_raw_hits"] == 4
        assert metadata["successful_searches"] == 2
        
        # Verify the higher scoring doc_1 was kept
        doc_1_hit = next(hit for hit in deduplicated_hits if hit.id == "doc_1")
        assert doc_1_hit.score == 0.95
        assert doc_1_hit.document["title"] == "Doc 1 Better"
    
    def test_validate_search_options_valid(self, search_executor, sample_search_options):
        """Test validation of valid search options."""
        errors = search_executor.validate_search_options(sample_search_options)
        assert len(errors) == 0
    
    def test_validate_search_options_invalid(self, search_executor):
        """Test validation of invalid search options."""
        invalid_options = SearchOptions(
            limit=150,  # Too high
            offset=-1,  # Negative
            crop_length=5,  # Too low
            matching_strategy="invalid",  # Invalid strategy
            sort=["field:invalid_direction"]  # Invalid sort direction
        )
        
        errors = search_executor.validate_search_options(invalid_options)
        assert len(errors) > 0
        assert any("Limit must be between 1 and 100" in error for error in errors)
        assert any("Offset must be non-negative" in error for error in errors)
        assert any("Crop length must be between 10 and 1000" in error for error in errors)
        assert any("Matching strategy must be one of" in error for error in errors)
        assert any("Invalid sort direction" in error for error in errors)
    
    @pytest.mark.asyncio
    async def test_health_check(self, search_executor):
        """Test health check functionality."""
        # Execute
        health = await search_executor.health_check()
        
        # Verify
        assert health["status"] == "healthy"
        assert "meilisearch_client" in health
        assert "config" in health
        assert health["config"]["max_concurrent_searches"] == 3
    
    def test_get_metrics(self, search_executor):
        """Test metrics collection."""
        metrics = search_executor.get_metrics()
        
        # Verify
        assert "config" in metrics
        assert "runtime" in metrics
        assert metrics["config"]["max_concurrent_searches"] == 3
        assert "semaphore_available" in metrics["runtime"]


if __name__ == "__main__":
    pytest.main([__file__])