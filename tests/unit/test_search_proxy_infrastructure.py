"""
Unit tests for search proxy core infrastructure.
"""

import pytest
from pydantic import ValidationError

from src.search_proxy.config.settings import (
    SearchProxySettings,
    TokenizationConfig,
    SearchConfig,
    RankingConfig,
    get_development_settings,
    get_production_settings
)
from src.search_proxy.models.requests import SearchRequest, BatchSearchRequest, SearchOptions
from src.search_proxy.models.responses import SearchResponse, SearchHit, QueryInfo, PaginationInfo
from src.search_proxy.models.query import ProcessedQuery, QueryVariant, QueryVariantType, TokenizationResult
from src.search_proxy.services.search_proxy_service import SearchProxyService


class TestSearchProxyConfiguration:
    """Test search proxy configuration management."""
    
    def test_default_settings_creation(self):
        """Test that default settings can be created successfully."""
        settings = SearchProxySettings()
        
        assert settings.service_name == "thai-search-proxy"
        assert settings.environment == "development"
        assert isinstance(settings.tokenization, TokenizationConfig)
        assert isinstance(settings.search, SearchConfig)
        assert isinstance(settings.ranking, RankingConfig)
    
    def test_development_settings_preset(self):
        """Test development settings preset."""
        settings = get_development_settings()
        
        assert settings.environment == "development"
        assert settings.log_level == "DEBUG"
        assert settings.performance.enable_detailed_logging is True
        assert settings.search.max_concurrent_searches == 3
        assert settings.tokenization.timeout_ms == 5000
    
    def test_production_settings_preset(self):
        """Test production settings preset."""
        settings = get_production_settings()
        
        assert settings.environment == "production"
        assert settings.log_level == "INFO"
        assert settings.performance.enable_detailed_logging is False
        assert settings.search.max_concurrent_searches == 10
        assert settings.tokenization.timeout_ms == 3000
    
    def test_tokenization_config_validation(self):
        """Test tokenization configuration validation."""
        # Valid configuration
        config = TokenizationConfig(
            primary_engine="newmm",
            fallback_engines=["attacut"],
            timeout_ms=3000,
            confidence_threshold=0.8
        )
        assert config.primary_engine == "newmm"
        assert config.confidence_threshold == 0.8
        
        # Invalid confidence threshold
        with pytest.raises(ValidationError):
            TokenizationConfig(confidence_threshold=1.5)  # > 1.0
    
    def test_search_config_validation(self):
        """Test search configuration validation."""
        # Valid configuration
        config = SearchConfig(
            max_concurrent_searches=5,
            timeout_ms=10000,
            retry_attempts=2
        )
        assert config.max_concurrent_searches == 5
        
        # Invalid concurrent searches
        with pytest.raises(ValidationError):
            SearchConfig(max_concurrent_searches=0)  # < 1


class TestSearchProxyModels:
    """Test search proxy data models."""
    
    def test_search_request_creation(self):
        """Test search request model creation."""
        request = SearchRequest(
            query="ค้นหาเอกสารภาษาไทย",
            index_name="documents"
        )
        
        assert request.query == "ค้นหาเอกสารภาษาไทย"
        assert request.index_name == "documents"
        assert isinstance(request.options, SearchOptions)
        assert request.include_tokenization_info is False
    
    def test_search_request_validation(self):
        """Test search request validation."""
        # Valid request
        request = SearchRequest(
            query="test query",
            index_name="test_index"
        )
        assert request.query == "test query"
        
        # Invalid empty query
        with pytest.raises(ValidationError):
            SearchRequest(query="", index_name="test")
        
        # Invalid long query
        with pytest.raises(ValidationError):
            SearchRequest(query="x" * 1001, index_name="test")
    
    def test_batch_search_request_creation(self):
        """Test batch search request model creation."""
        request = BatchSearchRequest(
            queries=["query1", "query2", "query3"],
            index_name="documents"
        )
        
        assert len(request.queries) == 3
        assert request.queries[0] == "query1"
        assert request.index_name == "documents"
    
    def test_batch_search_request_validation(self):
        """Test batch search request validation."""
        # Valid request
        request = BatchSearchRequest(
            queries=["query1", "query2"],
            index_name="test"
        )
        assert len(request.queries) == 2
        
        # Invalid empty queries list
        with pytest.raises(ValidationError):
            BatchSearchRequest(queries=[], index_name="test")
        
        # Invalid too many queries
        with pytest.raises(ValidationError):
            BatchSearchRequest(queries=["q"] * 51, index_name="test")
    
    def test_search_options_defaults(self):
        """Test search options default values."""
        options = SearchOptions()
        
        assert options.limit == 20
        assert options.offset == 0
        assert options.highlight is True
        assert options.filters is None
        assert options.sort is None
    
    def test_processed_query_creation(self):
        """Test processed query model creation."""
        tokenization_result = TokenizationResult(
            engine="newmm",
            tokens=["ค้นหา", "เอกสาร"],
            processing_time_ms=15.5,
            confidence=0.95,
            success=True
        )
        
        query_variant = QueryVariant(
            query_text="ค้นหา เอกสาร",
            variant_type=QueryVariantType.TOKENIZED,
            tokenization_engine="newmm",
            weight=1.0
        )
        
        processed_query = ProcessedQuery(
            original_query="ค้นหาเอกสาร",
            tokenization_results=[tokenization_result],
            query_variants=[query_variant],
            processing_time_ms=20.0,
            thai_content_detected=True,
            mixed_content=False,
            primary_language="thai"
        )
        
        assert processed_query.original_query == "ค้นหาเอกสาร"
        assert len(processed_query.tokenization_results) == 1
        assert len(processed_query.query_variants) == 1
        assert processed_query.thai_content_detected is True
    
    def test_search_response_creation(self):
        """Test search response model creation."""
        hit = SearchHit(
            id="doc_1",
            score=0.95,
            document={"title": "Test Document", "content": "Test content"}
        )
        
        query_info = QueryInfo(
            original_query="test query",
            processed_query="test query",
            thai_content_detected=False,
            mixed_content=False,
            query_variants_used=1
        )
        
        pagination = PaginationInfo(
            offset=0,
            limit=20,
            total_hits=1,
            has_next_page=False,
            has_previous_page=False
        )
        
        response = SearchResponse(
            hits=[hit],
            total_hits=1,
            processing_time_ms=50.0,
            query_info=query_info,
            pagination=pagination
        )
        
        assert len(response.hits) == 1
        assert response.total_hits == 1
        assert response.processing_time_ms == 50.0
        assert isinstance(response.timestamp, type(response.timestamp))


class TestSearchProxyService:
    """Test search proxy service functionality."""
    
    @pytest.fixture
    def service(self):
        """Create a search proxy service instance for testing."""
        settings = get_development_settings()
        return SearchProxyService(settings)
    
    def test_service_creation(self, service):
        """Test search proxy service creation."""
        assert service.settings.environment == "development"
        assert service._initialized is False
    
    @pytest.mark.asyncio
    async def test_service_initialization(self, service):
        """Test search proxy service initialization."""
        await service.initialize()
        assert service._initialized is True
    
    @pytest.mark.asyncio
    async def test_health_check_uninitialized(self, service):
        """Test health check on uninitialized service."""
        health = await service.health_check()
        
        assert health["service"] == "thai-search-proxy"
        assert health["status"] == "unhealthy"
        assert health["environment"] == "development"
    
    @pytest.mark.asyncio
    async def test_health_check_initialized(self, service):
        """Test health check on initialized service."""
        await service.initialize()
        health = await service.health_check()
        
        assert health["service"] == "thai-search-proxy"
        assert health["status"] == "healthy"
        assert "components" in health
        assert "dependencies" in health
    
    @pytest.mark.asyncio
    async def test_search_request_validation(self, service):
        """Test search request validation."""
        await service.initialize()
        
        # Valid request should not raise exception
        request = SearchRequest(query="test query", index_name="test")
        service._validate_search_request(request)
        
        # Empty query should raise exception
        with pytest.raises(ValueError, match="Query cannot be empty"):
            empty_request = SearchRequest(query="   ", index_name="test")
            service._validate_search_request(empty_request)
        
        # Long query should raise exception
        with pytest.raises(ValueError, match="Query too long"):
            long_request = SearchRequest(query="x" * 2000, index_name="test")
            service._validate_search_request(long_request)
    
    @pytest.mark.asyncio
    async def test_batch_request_validation(self, service):
        """Test batch search request validation."""
        await service.initialize()
        
        # Valid request should not raise exception
        request = BatchSearchRequest(queries=["query1", "query2"], index_name="test")
        service._validate_batch_request(request)
        
        # Too many queries should raise exception
        with pytest.raises(ValueError, match="Batch size too large"):
            large_request = BatchSearchRequest(queries=["q"] * 100, index_name="test")
            service._validate_batch_request(large_request)
        
        # Empty query in batch should raise exception
        with pytest.raises(ValueError, match="Query 2 cannot be empty"):
            empty_query_request = BatchSearchRequest(queries=["query1", "   "], index_name="test")
            service._validate_batch_request(empty_query_request)