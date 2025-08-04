"""
Main search proxy service orchestrator.

This service coordinates the complete search pipeline from query processing
to ranked results, integrating tokenization, search execution, and ranking.
"""

import asyncio
import time
from typing import List, Optional

from ...meilisearch_integration.client import MeiliSearchClient, MeiliSearchConfig
from ...utils.logging import get_structured_logger
from ..config.settings import SearchProxySettings
from ..models.requests import SearchRequest, BatchSearchRequest
from ..models.responses import SearchResponse, SearchErrorResponse
from ..models.query import ProcessedQuery
from ..metrics import metrics_collector
from ..analytics import analytics_collector
from .query_processor import QueryProcessor
from .search_executor import SearchExecutor, SearchExecutorConfig
from .result_ranker import ResultRanker
from ..config.hot_reload import HotReloadConfigManager


logger = get_structured_logger(__name__)


class SearchProxyService:
    """
    Main orchestrator for the Thai search proxy service.
    
    Coordinates the complete search pipeline:
    1. Query processing and tokenization
    2. Parallel search execution with multiple variants
    3. Result ranking and merging
    4. Response formatting
    """
    
    def __init__(
        self, 
        settings: SearchProxySettings,
        meilisearch_client: Optional[MeiliSearchClient] = None
    ):
        """
        Initialize the search proxy service.
        
        Args:
            settings: Configuration settings for the service
            meilisearch_client: Optional MeiliSearch client instance
        """
        self.settings = settings
        self._initialized = False
        
        # Store MeiliSearch client
        self._meilisearch_client = meilisearch_client
        
        # Initialize components
        self._query_processor: Optional[QueryProcessor] = None
        self._search_executor: Optional[SearchExecutor] = None
        self._result_ranker: Optional[ResultRanker] = None
        
        # Hot reload configuration manager
        self._hot_reload_manager: Optional[HotReloadConfigManager] = None
        self._enable_hot_reload = getattr(settings.performance, 'enable_hot_reload', False)
        
    async def initialize(self) -> None:
        """
        Initialize the search proxy service and its components.
        
        This method sets up all required components and verifies
        connectivity to external dependencies.
        """
        if self._initialized:
            return
            
        start_time = time.time()
        
        try:
            # Initialize components
            await self._initialize_components()
            
            # Verify external dependencies
            await self._verify_dependencies()
            
            # Initialize hot reload if enabled
            if self._enable_hot_reload:
                await self._initialize_hot_reload()
            
            self._initialized = True
            
            initialization_time = (time.time() - start_time) * 1000
            
            logger.info(
                "Search proxy service initialized successfully",
                extra={
                    "initialization_time_ms": initialization_time,
                    "components_initialized": {
                        "query_processor": self._query_processor is not None,
                        "search_executor": self._search_executor is not None,
                        "result_ranker": self._result_ranker is not None
                    },
                    "settings": {
                        "environment": self.settings.environment,
                        "service_version": self.settings.service_version,
                        "max_concurrent_searches": self.settings.search.max_concurrent_searches,
                        "tokenization_engine": self.settings.tokenization.primary_engine
                    }
                }
            )
            
        except Exception as e:
            logger.error(
                "Failed to initialize search proxy service",
                extra={"error": str(e), "initialization_time_ms": (time.time() - start_time) * 1000}
            )
            raise RuntimeError(f"Failed to initialize search proxy service: {str(e)}")
    
    async def search(
        self, 
        request: SearchRequest
    ) -> SearchResponse:
        """
        Execute a single search request.
        
        Args:
            request: Search request with query and options
            
        Returns:
            SearchResponse with ranked results and metadata
            
        Raises:
            RuntimeError: If service is not initialized
            ValueError: If request validation fails
        """
        if not self._initialized:
            raise RuntimeError("Search proxy service not initialized")
        
        start_time = time.time()
        tokenization_start = 0.0
        search_start = 0.0
        ranking_start = 0.0
        
        # Update active searches counter
        metrics_collector.update_active_searches(1)
        
        try:
            # Validate request
            self._validate_search_request(request)
            
            # Process query with timing
            tokenization_start = time.time()
            processed_query = await self._process_query(request.query)
            tokenization_time = (time.time() - tokenization_start) * 1000
            
            # Record query processing metrics
            language_detected = "thai" if processed_query.thai_content_detected else "english"
            if processed_query.mixed_content:
                language_detected = "mixed"
            
            metrics_collector.record_query_processing(
                query=request.query,
                language_detected=language_detected,
                tokenization_success=not processed_query.fallback_used,
                variants_generated=len(processed_query.query_variants),
                fallback_used=processed_query.fallback_used,
                compound_words_found=0  # TODO: Extract from processed_query when available
            )
            
            # Execute searches with timing
            search_start = time.time()
            search_results = await self._execute_searches(
                processed_query, 
                request.index_name,
                request.options
            )
            search_time = (time.time() - search_start) * 1000
            
            # Rank and merge results with timing
            ranking_start = time.time()
            ranked_results = await self._rank_results(search_results, processed_query)
            ranking_time = (time.time() - ranking_start) * 1000
            
            # Build response
            processing_time = (time.time() - start_time) * 1000
            response = self._build_search_response(
                ranked_results,
                processed_query,
                request,
                processing_time
            )
            
            # Record successful search metrics
            metrics_collector.record_search_request(
                query=request.query,
                success=True,
                processing_time_ms=processing_time,
                query_variants_count=len(processed_query.query_variants),
                results_count=len(ranked_results["hits"]),
                unique_results_count=ranked_results["total_hits"],
                tokenization_time_ms=tokenization_time,
                search_time_ms=search_time,
                ranking_time_ms=ranking_time,
                cache_hit=False  # TODO: Implement caching
            )
            
            # Record analytics
            analytics_collector.record_search(
                query=request.query,
                session_id=getattr(request, 'session_id', None),
                success=True,
                response_time_ms=processing_time,
                results_count=len(ranked_results["hits"]),
                language=processed_query.primary_language or ("thai" if processed_query.thai_content_detected else "english")
            )
            
            return response
            
        except Exception as e:
            # Record failed search metrics
            processing_time = (time.time() - start_time) * 1000
            error_type = type(e).__name__
            
            # Log the error with traceback for debugging
            logger.error(
                "Search processing failed",
                extra={
                    "error_type": error_type,
                    "error_message": str(e),
                    "query": request.query,
                    "index_name": request.index_name
                },
                exc_info=True
            )
            
            metrics_collector.record_search_request(
                query=request.query,
                success=False,
                processing_time_ms=processing_time,
                query_variants_count=0,
                results_count=0,
                unique_results_count=0,
                tokenization_time_ms=(time.time() - tokenization_start) * 1000 if tokenization_start else 0,
                search_time_ms=(time.time() - search_start) * 1000 if search_start else 0,
                ranking_time_ms=(time.time() - ranking_start) * 1000 if ranking_start else 0,
                cache_hit=False,
                error_type=error_type
            )
            
            # Record analytics for failed search
            analytics_collector.record_search(
                query=request.query,
                session_id=getattr(request, 'session_id', None),
                success=False,
                response_time_ms=processing_time,
                results_count=0,
                language="unknown",
                error_type=error_type
            )
            
            # Handle errors gracefully
            return await self._handle_search_error(e, request, start_time)
        finally:
            # Always update active searches counter
            metrics_collector.update_active_searches(-1)
    
    async def batch_search(
        self, 
        request: BatchSearchRequest
    ) -> List[SearchResponse]:
        """
        Execute multiple search requests concurrently.
        
        Args:
            request: Batch search request with multiple queries
            
        Returns:
            List of SearchResponse objects for each query
            
        Raises:
            RuntimeError: If service is not initialized
            ValueError: If request validation fails
        """
        if not self._initialized:
            raise RuntimeError("Search proxy service not initialized")
        
        start_time = time.time()
        
        # Validate batch request
        self._validate_batch_request(request)
        
        logger.info(
            "Starting batch search processing",
            extra={
                "query_count": len(request.queries),
                "index_name": request.index_name,
                "max_concurrent": self.settings.search.max_concurrent_searches,
                "include_tokenization_info": request.include_tokenization_info
            }
        )
        
        # Create individual search requests
        search_requests = [
            SearchRequest(
                query=query,
                index_name=request.index_name,
                options=request.options,
                include_tokenization_info=request.include_tokenization_info
            )
            for query in request.queries
        ]
        
        # Execute searches concurrently with semaphore for resource management
        semaphore = asyncio.Semaphore(self.settings.search.max_concurrent_searches)
        
        async def execute_single_search_with_error_handling(
            search_request: SearchRequest, 
            query_index: int
        ) -> SearchResponse:
            async with semaphore:
                try:
                    return await self.search(search_request)
                except Exception as e:
                    logger.error(
                        f"Batch search failed for query {query_index + 1}",
                        extra={
                            "query": search_request.query[:100],  # Truncate for logging
                            "error": str(e),
                            "query_index": query_index
                        }
                    )
                    # Return error response in SearchResponse format
                    return await self._handle_search_error(e, search_request, time.time())
        
        # Execute all searches concurrently
        results = await asyncio.gather(
            *[
                execute_single_search_with_error_handling(req, i) 
                for i, req in enumerate(search_requests)
            ],
            return_exceptions=False  # Errors are handled in the wrapper function
        )
        
        batch_processing_time = (time.time() - start_time) * 1000
        successful_searches = sum(1 for r in results if r.total_hits >= 0)  # Basic success check
        failed_searches = len(results) - successful_searches
        
        # Record batch search metrics
        metrics_collector.record_batch_search(
            batch_size=len(request.queries),
            successful_queries=successful_searches,
            failed_queries=failed_searches,
            total_processing_time_ms=batch_processing_time
        )
        
        logger.info(
            "Batch search processing completed",
            extra={
                "total_queries": len(request.queries),
                "successful_searches": successful_searches,
                "failed_searches": failed_searches,
                "batch_processing_time_ms": batch_processing_time,
                "average_time_per_query": batch_processing_time / len(request.queries) if request.queries else 0
            }
        )
        
        return results
    
    async def health_check(self) -> dict:
        """
        Perform health check for the search proxy service.
        
        Returns:
            Dictionary with health status information
        """
        health_status = {
            "service": "thai-search-proxy",
            "status": "healthy" if self._initialized else "unhealthy",
            "version": self.settings.service_version,
            "environment": self.settings.environment,
            "components": {},
            "dependencies": {},
            "metrics": {}
        }
        
        if self._initialized:
            # Check component health (placeholders)
            health_status["components"] = {
                "query_processor": "healthy",
                "search_executor": "healthy", 
                "result_ranker": "healthy"
            }
            
            # Check dependency health
            health_status["dependencies"] = await self._check_dependencies()
            
            # Add performance metrics summary
            metrics_summary = metrics_collector.get_metrics_summary()
            health_status["metrics"] = {
                "uptime_seconds": metrics_summary["uptime_seconds"],
                "total_searches": metrics_summary["search_metrics"]["total_searches"],
                "success_rate_percent": metrics_summary["search_metrics"]["success_rate_percent"],
                "avg_response_time_ms": metrics_summary["search_metrics"]["avg_response_time_ms"],
                "active_searches": metrics_summary["performance_metrics"]["active_searches"],
                "cache_hit_rate_percent": metrics_summary["search_metrics"]["cache_hit_rate_percent"]
            }
        
        return health_status
    
    async def _initialize_hot_reload(self) -> None:
        """Initialize hot reload configuration manager."""
        logger.info("Initializing hot reload configuration manager")
        
        try:
            self._hot_reload_manager = HotReloadConfigManager(self.settings)
            
            # Register reload callbacks
            self._hot_reload_manager.register_reload_callback(self._on_config_reload)
            
            # Start watching config files
            self._hot_reload_manager.start()
            
            logger.info("Hot reload configuration manager initialized")
            
        except Exception as e:
            logger.error(f"Failed to initialize hot reload: {e}")
            # Don't fail service initialization if hot reload fails
    
    async def _on_config_reload(self, config_type: str) -> None:
        """Handle configuration reload events."""
        logger.info(f"Reloading configuration: {config_type}")
        
        try:
            if config_type == "dictionary":
                # Reload dictionary in query processor
                if self._query_processor:
                    await self._query_processor.reload_dictionary(
                        self._hot_reload_manager.get_cached_config("dictionary")
                    )
                    
            elif config_type == "tokenization":
                # Update tokenization settings
                if self._query_processor:
                    self._query_processor.settings = self.settings
                    
            elif config_type == "ranking":
                # Update ranking settings
                if self._result_ranker:
                    self._result_ranker.config = self.settings.ranking
                    
            logger.info(f"Successfully reloaded {config_type} configuration")
            
        except Exception as e:
            logger.error(f"Failed to reload {config_type} configuration: {e}")
    
    async def shutdown(self) -> None:
        """Shutdown the search proxy service and cleanup resources."""
        logger.info("Shutting down search proxy service")
        
        # Stop hot reload if enabled
        if self._hot_reload_manager:
            self._hot_reload_manager.stop()
        
        # Cleanup other resources
        self._initialized = False
        
        logger.info("Search proxy service shutdown complete")
    
    # Private helper methods
    
    async def _initialize_components(self) -> None:
        """Initialize search proxy components."""
        logger.info("Initializing search proxy components")
        
        # Initialize query processor
        self._query_processor = QueryProcessor(self.settings)
        await self._query_processor.initialize()
        
        # Initialize search executor
        if self._meilisearch_client is None:
            # Create default MeiliSearch client if not provided
            config = MeiliSearchConfig(
                host=self.settings.meilisearch_url,
                api_key=self.settings.meilisearch_api_key,
                timeout=int(self.settings.meilisearch_timeout_ms / 1000)
            )
            self._meilisearch_client = MeiliSearchClient(config)
        
        # Configure search executor
        executor_config = SearchExecutorConfig(
            max_concurrent_searches=self.settings.search.max_concurrent_searches,
            search_timeout_ms=self.settings.search.timeout_ms,
            enable_parallel_execution=self.settings.search.parallel_searches,
            retry_failed_searches=self.settings.search.retry_attempts > 0,
            max_retries=self.settings.search.retry_attempts,
            retry_delay_ms=self.settings.search.retry_delay_ms
        )
        
        self._search_executor = SearchExecutor(
            meilisearch_client=self._meilisearch_client,
            config=executor_config
        )
        
        # Initialize result ranker
        self._result_ranker = ResultRanker(self.settings.ranking)
        
        logger.info(
            "Search proxy components initialized successfully",
            extra={
                "query_processor": "initialized",
                "search_executor": "initialized", 
                "result_ranker": "initialized",
                "meilisearch_client": "ready"
            }
        )
    
    async def _verify_dependencies(self) -> None:
        """Verify connectivity to external dependencies."""
        logger.info("Verifying external dependencies")
        
        try:
            # Verify MeiliSearch connectivity
            if self._meilisearch_client:
                health_status = await self._meilisearch_client.health_check()
                if health_status.get("status") != "healthy":
                    raise RuntimeError(f"MeiliSearch health check failed: {health_status}")
                
                logger.info(
                    "MeiliSearch connectivity verified",
                    extra={"health_status": health_status}
                )
            
            # Verify tokenization engines are available
            if self._query_processor:
                # This will be verified during query processor initialization
                logger.info("Tokenization engines verified during query processor initialization")
            
        except Exception as e:
            logger.error(
                "Dependency verification failed",
                extra={"error": str(e)}
            )
            raise
    
    async def _process_query(self, query: str) -> ProcessedQuery:
        """Process query through tokenization pipeline."""
        if not self._query_processor:
            raise RuntimeError("Query processor not initialized")
        
        return await self._query_processor.process_query(query)
    
    async def _execute_searches(self, processed_query: ProcessedQuery, index_name: str, options) -> list:
        """Execute searches with query variants."""
        if not self._search_executor:
            raise RuntimeError("Search executor not initialized")
        
        return await self._search_executor.execute_parallel_searches(
            query_variants=processed_query.query_variants,
            index_name=index_name,
            search_options=options
        )
    
    async def _rank_results(self, search_results: list, processed_query: ProcessedQuery) -> dict:
        """Rank and merge search results."""
        if not self._result_ranker:
            raise RuntimeError("Result ranker not initialized")
        
        # Create query context for ranking
        from ..models.search import QueryContext
        
        query_context = QueryContext(
            original_query=processed_query.original_query,
            processed_query=" ".join([
                variant.query_text for variant in processed_query.query_variants[:1]
            ]),
            thai_content_ratio=1.0 if processed_query.thai_content_detected else 0.0,
            mixed_content=processed_query.mixed_content,
            primary_language=processed_query.primary_language,
            query_length=len(processed_query.original_query),
            tokenization_confidence=processed_query.average_tokenization_confidence,
            variant_count=len(processed_query.query_variants),
            processing_time_ms=processed_query.processing_time_ms
        )
        
        # Rank results
        ranked_results = self._result_ranker.rank_results(
            search_results=search_results,
            original_query=processed_query.original_query,
            query_context=query_context
        )
        
        return {
            "hits": ranked_results.hits,
            "total_hits": ranked_results.total_unique_hits,
            "ranking_metadata": {
                "deduplication_count": ranked_results.deduplication_count,
                "ranking_time_ms": ranked_results.ranking_time_ms,
                "ranking_algorithm": ranked_results.ranking_algorithm
            }
        }
    
    def _build_search_response(
        self, 
        ranked_results: dict, 
        processed_query: ProcessedQuery,
        request: SearchRequest,
        processing_time: float
    ) -> SearchResponse:
        """Build final search response."""
        from ..models.responses import QueryInfo, PaginationInfo
        
        query_info = QueryInfo(
            original_query=processed_query.original_query,
            processed_query=processed_query.original_query,
            thai_content_detected=processed_query.thai_content_detected,
            mixed_content=processed_query.mixed_content,
            query_variants_used=len(processed_query.query_variants),
            fallback_used=processed_query.fallback_used
        )
        
        pagination = PaginationInfo(
            offset=request.options.offset,
            limit=request.options.limit,
            total_hits=ranked_results["total_hits"],
            has_next_page=request.options.offset + request.options.limit < ranked_results["total_hits"],
            has_previous_page=request.options.offset > 0
        )
        
        return SearchResponse(
            hits=ranked_results["hits"],
            total_hits=ranked_results["total_hits"],
            processing_time_ms=processing_time,
            query_info=query_info,
            pagination=pagination
        )
    
    async def _handle_search_error(
        self, 
        error: Exception, 
        request: SearchRequest, 
        start_time: float
    ) -> SearchResponse:
        """Handle search errors gracefully."""
        processing_time = (time.time() - start_time) * 1000
        
        # Create minimal response for error case
        from ..models.responses import QueryInfo, PaginationInfo
        
        query_info = QueryInfo(
            original_query=request.query,
            processed_query=request.query,
            thai_content_detected=False,
            mixed_content=False,
            query_variants_used=0,
            fallback_used=True
        )
        
        pagination = PaginationInfo(
            offset=request.options.offset,
            limit=request.options.limit,
            total_hits=0,
            has_next_page=False,
            has_previous_page=False
        )
        
        return SearchResponse(
            hits=[],
            total_hits=0,
            processing_time_ms=processing_time,
            query_info=query_info,
            pagination=pagination
        )
    
    def _error_to_search_response(self, error_response: SearchErrorResponse) -> SearchResponse:
        """Convert error response to search response format."""
        from ..models.responses import QueryInfo, PaginationInfo
        
        query_info = QueryInfo(
            original_query="",
            processed_query="",
            thai_content_detected=False,
            mixed_content=False,
            query_variants_used=0,
            fallback_used=error_response.fallback_used
        )
        
        pagination = PaginationInfo(
            offset=0,
            limit=0,
            total_hits=0,
            has_next_page=False,
            has_previous_page=False
        )
        
        return SearchResponse(
            hits=error_response.partial_results or [],
            total_hits=0,
            processing_time_ms=0.0,
            query_info=query_info,
            pagination=pagination
        )
    
    def _validate_search_request(self, request: SearchRequest) -> None:
        """Validate search request parameters."""
        if len(request.query.strip()) == 0:
            raise ValueError("Query cannot be empty")
        
        if len(request.query) > self.settings.performance.max_query_length:
            raise ValueError(f"Query too long: {len(request.query)} > {self.settings.performance.max_query_length}")
    
    def _validate_batch_request(self, request: BatchSearchRequest) -> None:
        """Validate batch search request parameters."""
        if len(request.queries) > self.settings.performance.max_batch_size:
            raise ValueError(f"Batch size too large: {len(request.queries)} > {self.settings.performance.max_batch_size}")
        
        for i, query in enumerate(request.queries):
            if len(query.strip()) == 0:
                raise ValueError(f"Query {i+1} cannot be empty")
            
            if len(query) > self.settings.performance.max_query_length:
                raise ValueError(f"Query {i+1} too long: {len(query)} > {self.settings.performance.max_query_length}")
    
    async def _check_dependencies(self) -> dict:
        """Check health of external dependencies."""
        dependencies = {}
        
        try:
            # Check MeiliSearch health
            if self._meilisearch_client:
                meilisearch_health = await self._meilisearch_client.health_check()
                dependencies["meilisearch"] = meilisearch_health
            else:
                dependencies["meilisearch"] = {"status": "not_configured"}
            
            # Check search executor health
            if self._search_executor:
                executor_health = await self._search_executor.health_check()
                dependencies["search_executor"] = executor_health
            else:
                dependencies["search_executor"] = {"status": "not_initialized"}
            
            # Check tokenization engines (via query processor)
            if self._query_processor:
                # Query processor doesn't have explicit health check, so we'll assume healthy if initialized
                dependencies["tokenization_engines"] = {"status": "healthy"}
            else:
                dependencies["tokenization_engines"] = {"status": "not_initialized"}
            
        except Exception as e:
            logger.error(
                "Error checking dependencies",
                extra={"error": str(e)}
            )
            dependencies["error"] = str(e)
        
        return dependencies