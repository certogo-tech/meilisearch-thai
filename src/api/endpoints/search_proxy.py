"""
Search proxy API endpoints.

Provides intelligent Thai search capabilities through tokenization and ranking.
"""

import time
from typing import List

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from src.utils.logging import get_structured_logger
from src.api.middleware.auth import api_key_auth
from src.search_proxy.models.requests import SearchRequest, BatchSearchRequest
from src.search_proxy.models.responses import SearchResponse, SearchErrorResponse
from src.search_proxy.services.search_proxy_service import SearchProxyService
from src.search_proxy.config.settings import SearchProxySettings
from src.search_proxy.exceptions import (
    SearchProxyException,
    ValidationError,
    TokenizationError,
    SearchExecutionError,
    ServiceUnavailableError,
    TimeoutError
)
from src.search_proxy.error_handlers import SearchProxyErrorHandler

logger = get_structured_logger(__name__)

# Create router
router = APIRouter()

# Global service instance (will be initialized on startup)
_search_proxy_service: SearchProxyService = None


async def get_search_proxy_service() -> SearchProxyService:
    """
    Dependency to get the search proxy service instance.
    
    Returns:
        SearchProxyService: Initialized search proxy service
        
    Raises:
        HTTPException: If service is not initialized
    """
    global _search_proxy_service
    
    if _search_proxy_service is None:
        # Initialize service with default settings
        settings = SearchProxySettings()
        _search_proxy_service = SearchProxyService(settings)
        await _search_proxy_service.initialize()
    
    return _search_proxy_service


@router.post(
    "/search",
    response_model=SearchResponse,
    summary="Execute Thai-aware search",
    description="""
    Execute a single search request with intelligent Thai tokenization and ranking.
    
    This endpoint processes Thai text through advanced NLP tokenization, performs
    parallel searches with multiple query variants, and returns optimally ranked results.
    
    Features:
    - Automatic Thai text detection and tokenization
    - Mixed Thai-English content support
    - Fallback tokenization strategies
    - Intelligent result ranking and deduplication
    - Optional tokenization debugging information
    """,
    responses={
        200: {"description": "Search completed successfully"},
        400: {"description": "Invalid request parameters"},
        422: {"description": "Request validation failed"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)
async def search(
    request: SearchRequest,
    http_request: Request,
    service: SearchProxyService = Depends(get_search_proxy_service),
    api_key: str = Depends(api_key_auth)
) -> SearchResponse:
    """
    Execute a single search request with Thai tokenization.
    
    Args:
        request: Search request with query and options
        http_request: FastAPI request object for logging
        service: Search proxy service dependency
        
    Returns:
        SearchResponse: Search results with ranking and metadata
        
    Raises:
        HTTPException: For various error conditions
    """
    start_time = time.time()
    
    # Log request
    logger.info(
        "Search request received",
        query_length=len(request.query),
        index_name=request.index_name,
        limit=request.options.limit,
        offset=request.options.offset,
        include_tokenization_info=request.include_tokenization_info,
        client_ip=http_request.client.host if http_request.client else None
    )
    
    try:
        # Validate request manually for better error messages
        if not request.query or not request.query.strip():
            raise ValidationError(
                "Query cannot be empty or whitespace only",
                field="query",
                value=request.query
            )
        
        if len(request.query) > 1000:
            raise ValidationError(
                f"Query too long: {len(request.query)} characters (max 1000)",
                field="query",
                value=len(request.query)
            )
        
        # Execute search
        response = await service.search(request)
        
        # Log successful response
        processing_time = (time.time() - start_time) * 1000
        logger.info(
            "Search completed successfully",
            total_hits=response.total_hits,
            returned_hits=len(response.hits),
            processing_time_ms=processing_time,
            thai_content_detected=response.query_info.thai_content_detected,
            query_variants_used=response.query_info.query_variants_used,
            fallback_used=response.query_info.fallback_used
        )
        
        return response
        
    except ValidationError as e:
        # Handle custom validation errors
        return SearchProxyErrorHandler.handle_validation_error(e)
        
    except PydanticValidationError as e:
        # Handle Pydantic validation errors
        return SearchProxyErrorHandler.handle_validation_error(e)
        
    except SearchProxyException as e:
        # Handle search proxy specific errors
        return SearchProxyErrorHandler.handle_search_proxy_error(
            e, 
            original_query=request.query,
            request_options=request.options.model_dump()
        )
        
    except RuntimeError as e:
        # Convert runtime errors to service unavailable
        service_error = ServiceUnavailableError(
            f"Search service unavailable: {str(e)}",
            service_name="search_proxy"
        )
        return SearchProxyErrorHandler.handle_search_proxy_error(
            service_error,
            original_query=request.query
        )
        
    except Exception as e:
        # Handle unexpected errors with detailed logging
        SearchProxyErrorHandler.log_error_context(
            e, http_request, "search_execution",
            additional_context={
                "query_length": len(request.query),
                "index_name": request.index_name,
                "include_tokenization_info": request.include_tokenization_info
            }
        )
        
        return SearchProxyErrorHandler.handle_unexpected_error(
            e, "search", start_time, request.query, request.options.model_dump()
        )


@router.post(
    "/batch-search",
    response_model=List[SearchResponse],
    summary="Execute multiple Thai-aware searches",
    description="""
    Execute multiple search requests concurrently with intelligent Thai tokenization.
    
    This endpoint processes multiple queries in parallel, applying the same advanced
    tokenization and ranking algorithms to each query. Results are returned in the
    same order as the input queries.
    
    Features:
    - Concurrent processing of multiple queries
    - Resource management with configurable concurrency limits
    - Individual error handling per query
    - Partial results support when some queries fail
    - Batch-optimized performance
    """,
    responses={
        200: {"description": "Batch search completed (may include partial failures)"},
        400: {"description": "Invalid batch request parameters"},
        422: {"description": "Request validation failed"},
        500: {"description": "Internal server error"},
        503: {"description": "Service unavailable"}
    }
)
async def batch_search(
    request: BatchSearchRequest,
    http_request: Request,
    service: SearchProxyService = Depends(get_search_proxy_service),
    api_key: str = Depends(api_key_auth)
) -> List[SearchResponse]:
    """
    Execute multiple search requests concurrently.
    
    Args:
        request: Batch search request with multiple queries
        http_request: FastAPI request object for logging
        service: Search proxy service dependency
        
    Returns:
        List[SearchResponse]: Search results for each query
        
    Raises:
        HTTPException: For various error conditions
    """
    start_time = time.time()
    
    # Log batch request
    logger.info(
        "Batch search request received",
        query_count=len(request.queries),
        index_name=request.index_name,
        limit=request.options.limit,
        offset=request.options.offset,
        include_tokenization_info=request.include_tokenization_info,
        client_ip=http_request.client.host if http_request.client else None
    )
    
    try:
        # Validate batch request manually for better error messages
        if not request.queries:
            raise ValidationError(
                "Queries list cannot be empty",
                field="queries",
                value=len(request.queries)
            )
        
        if len(request.queries) > 50:
            raise ValidationError(
                f"Too many queries in batch: {len(request.queries)} (max 50)",
                field="queries",
                value=len(request.queries)
            )
        
        # Validate individual queries
        for i, query in enumerate(request.queries):
            if not query or not query.strip():
                raise ValidationError(
                    f"Query {i+1} cannot be empty or whitespace only",
                    field=f"queries[{i}]",
                    value=query
                )
            
            if len(query) > 1000:
                raise ValidationError(
                    f"Query {i+1} too long: {len(query)} characters (max 1000)",
                    field=f"queries[{i}]",
                    value=len(query)
                )
        
        # Execute batch search
        responses = await service.batch_search(request)
        
        # Calculate batch statistics
        processing_time = (time.time() - start_time) * 1000
        total_hits = sum(response.total_hits for response in responses)
        successful_queries = sum(1 for response in responses if response.total_hits >= 0)
        failed_queries = len(responses) - successful_queries
        
        # Log batch completion
        logger.info(
            "Batch search completed",
            query_count=len(request.queries),
            successful_queries=successful_queries,
            failed_queries=failed_queries,
            total_hits=total_hits,
            processing_time_ms=processing_time
        )
        
        return responses
        
    except ValidationError as e:
        # Handle custom validation errors
        return SearchProxyErrorHandler.handle_validation_error(e)
        
    except PydanticValidationError as e:
        # Handle Pydantic validation errors
        return SearchProxyErrorHandler.handle_validation_error(e)
        
    except SearchProxyException as e:
        # Handle search proxy specific errors
        return SearchProxyErrorHandler.handle_search_proxy_error(
            e,
            original_query=f"batch({len(request.queries)} queries)",
            request_options=request.options.model_dump()
        )
        
    except RuntimeError as e:
        # Convert runtime errors to service unavailable
        service_error = ServiceUnavailableError(
            f"Batch search service unavailable: {str(e)}",
            service_name="search_proxy"
        )
        return SearchProxyErrorHandler.handle_search_proxy_error(
            service_error,
            original_query=f"batch({len(request.queries)} queries)"
        )
        
    except Exception as e:
        # Handle unexpected errors with detailed logging
        SearchProxyErrorHandler.log_error_context(
            e, http_request, "batch_search_execution",
            additional_context={
                "query_count": len(request.queries),
                "index_name": request.index_name,
                "include_tokenization_info": request.include_tokenization_info
            }
        )
        
        return SearchProxyErrorHandler.handle_unexpected_error(
            e, "batch_search", start_time, 
            f"batch({len(request.queries)} queries)", 
            request.options.model_dump()
        )


@router.get(
    "/health",
    summary="Search proxy health check",
    description="""
    Check the health status of the search proxy service and its dependencies.
    
    Returns detailed information about:
    - Service initialization status
    - Component health (query processor, search executor, result ranker)
    - External dependency status (Meilisearch, tokenization engines)
    - Performance metrics and version information
    """,
    responses={
        200: {"description": "Service is healthy"},
        503: {"description": "Service is unhealthy"}
    }
)
async def health_check(
    service: SearchProxyService = Depends(get_search_proxy_service)
) -> dict:
    """
    Perform health check for the search proxy service.
    
    Args:
        service: Search proxy service dependency
        
    Returns:
        dict: Health status information
    """
    try:
        health_status = await service.health_check()
        
        # Determine HTTP status code based on health
        status_code = 200 if health_status["status"] == "healthy" else 503
        
        logger.info(
            "Health check performed",
            status=health_status["status"],
            components_healthy=all(
                status == "healthy" 
                for status in health_status.get("components", {}).values()
            ),
            dependencies_healthy=all(
                status == "healthy" 
                for status in health_status.get("dependencies", {}).values()
            )
        )
        
        return JSONResponse(
            status_code=status_code,
            content=health_status
        )
        
    except SearchProxyException as e:
        # Handle search proxy specific errors
        logger.error(
            "Health check failed with search proxy error",
            error_code=e.error_code,
            message=e.message,
            details=e.details
        )
        
        return JSONResponse(
            status_code=503,
            content={
                "service": "thai-search-proxy",
                "status": "unhealthy",
                "error": e.error_code,
                "message": e.message,
                "details": e.details,
                "components": {},
                "dependencies": {}
            }
        )
        
    except Exception as e:
        # Handle unexpected errors
        logger.error(
            "Health check failed with unexpected error",
            error=str(e),
            error_type=type(e).__name__
        )
        
        return JSONResponse(
            status_code=503,
            content={
                "service": "thai-search-proxy",
                "status": "unhealthy",
                "error": "HEALTH_CHECK_FAILED",
                "message": f"Health check failed: {str(e)}",
                "details": {"error_type": type(e).__name__},
                "components": {},
                "dependencies": {}
            }
        )