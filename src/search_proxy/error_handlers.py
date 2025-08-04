"""
Error handling utilities for the search proxy service.

Provides consistent error response formatting and graceful fallback mechanisms.
"""

import time
from typing import Any, Dict, List, Optional, Union
from fastapi import Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError as PydanticValidationError

from src.utils.logging import get_structured_logger
from .exceptions import (
    SearchProxyException,
    ValidationError,
    TokenizationError,
    SearchExecutionError,
    MeilisearchConnectionError,
    RankingError,
    ServiceUnavailableError,
    TimeoutError,
    ConfigurationError,
    get_http_status_code
)
from .models.responses import SearchErrorResponse, SearchResponse, QueryInfo, PaginationInfo

logger = get_structured_logger(__name__)


class SearchProxyErrorHandler:
    """Centralized error handling for search proxy operations."""
    
    @staticmethod
    def handle_validation_error(
        error: Union[PydanticValidationError, ValidationError],
        request_data: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Handle validation errors with detailed field information.
        
        Args:
            error: Validation error (Pydantic or custom)
            request_data: Original request data for context
            
        Returns:
            JSONResponse: Formatted error response
        """
        if isinstance(error, PydanticValidationError):
            # Handle Pydantic validation errors
            error_details = {
                "validation_errors": [],
                "error_count": len(error.errors())
            }
            
            for err in error.errors():
                field_path = " -> ".join(str(loc) for loc in err["loc"])
                error_details["validation_errors"].append({
                    "field": field_path,
                    "message": err["msg"],
                    "type": err["type"],
                    "input": err.get("input")
                })
            
            error_response = SearchErrorResponse(
                error="VALIDATION_ERROR",
                message="Request validation failed",
                details=error_details,
                fallback_used=False
            )
            
            logger.warning(
                "Request validation failed",
                error_count=len(error.errors()),
                validation_errors=error_details["validation_errors"]
            )
            
            return JSONResponse(
                status_code=422,
                content=error_response.model_dump()
            )
        
        elif isinstance(error, ValidationError):
            # Handle custom validation errors
            error_response = SearchErrorResponse(
                error=error.error_code,
                message=error.message,
                details=error.details,
                fallback_used=error.fallback_used
            )
            
            logger.warning(
                "Custom validation error",
                error_code=error.error_code,
                message=error.message,
                details=error.details
            )
            
            return JSONResponse(
                status_code=get_http_status_code(error),
                content=error_response.model_dump()
            )
        
        else:
            # Fallback for unknown validation errors
            error_response = SearchErrorResponse(
                error="UNKNOWN_VALIDATION_ERROR",
                message=str(error),
                fallback_used=False
            )
            
            return JSONResponse(
                status_code=400,
                content=error_response.model_dump()
            )
    
    @staticmethod
    def handle_search_proxy_error(
        error: SearchProxyException,
        original_query: Optional[str] = None,
        request_options: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Handle search proxy specific errors with fallback responses.
        
        Args:
            error: Search proxy exception
            original_query: Original search query for context
            request_options: Original request options
            
        Returns:
            JSONResponse: Formatted error response
        """
        # Log the error with context
        logger.error(
            "Search proxy error occurred",
            error_code=error.error_code,
            message=error.message,
            details=error.details,
            fallback_used=error.fallback_used,
            partial_results_count=len(error.partial_results),
            original_query_length=len(original_query) if original_query else 0
        )
        
        # Create error response
        error_response = SearchErrorResponse(
            error=error.error_code,
            message=error.message,
            details=error.details,
            fallback_used=error.fallback_used,
            partial_results=error.partial_results
        )
        
        return JSONResponse(
            status_code=get_http_status_code(error),
            content=error_response.model_dump()
        )
    
    @staticmethod
    def handle_unexpected_error(
        error: Exception,
        operation: str,
        start_time: float,
        original_query: Optional[str] = None,
        request_options: Optional[Dict[str, Any]] = None
    ) -> JSONResponse:
        """
        Handle unexpected errors with graceful fallback.
        
        Args:
            error: Unexpected exception
            operation: Operation being performed when error occurred
            start_time: Operation start time for duration calculation
            original_query: Original search query
            request_options: Original request options
            
        Returns:
            JSONResponse: Formatted error response
        """
        processing_time = (time.time() - start_time) * 1000
        
        # Log the unexpected error
        logger.error(
            "Unexpected error occurred",
            operation=operation,
            error_type=type(error).__name__,
            error_message=str(error),
            processing_time_ms=processing_time,
            original_query_length=len(original_query) if original_query else 0
        )
        
        # Create fallback error response
        error_response = SearchErrorResponse(
            error="INTERNAL_ERROR",
            message=f"An unexpected error occurred during {operation}",
            details={
                "error_type": type(error).__name__,
                "operation": operation,
                "processing_time_ms": processing_time
            },
            fallback_used=True
        )
        
        return JSONResponse(
            status_code=500,
            content=error_response.model_dump()
        )
    
    @staticmethod
    def create_fallback_search_response(
        original_query: str,
        error: Exception,
        request_options: Optional[Dict[str, Any]] = None,
        processing_time: float = 0.0
    ) -> SearchResponse:
        """
        Create a fallback search response when errors occur.
        
        Args:
            original_query: Original search query
            error: Error that occurred
            request_options: Original request options
            processing_time: Processing time before error
            
        Returns:
            SearchResponse: Fallback response with empty results
        """
        options = request_options or {}
        
        query_info = QueryInfo(
            original_query=original_query,
            processed_query=original_query,
            thai_content_detected=False,
            mixed_content=False,
            query_variants_used=0,
            fallback_used=True
        )
        
        pagination = PaginationInfo(
            offset=options.get("offset", 0),
            limit=options.get("limit", 20),
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
    
    @staticmethod
    def log_error_context(
        error: Exception,
        request: Request,
        operation: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Log error with full request context.
        
        Args:
            error: Exception that occurred
            request: FastAPI request object
            operation: Operation being performed
            additional_context: Additional context information
        """
        context = {
            "operation": operation,
            "error_type": type(error).__name__,
            "error_message": str(error),
            "method": request.method,
            "path": request.url.path,
            "query_params": dict(request.query_params),
            "client_ip": request.client.host if request.client else None,
            "user_agent": request.headers.get("user-agent"),
        }
        
        if additional_context:
            context.update(additional_context)
        
        logger.error("Request processing error", **context)


def create_error_handler_middleware():
    """
    Create middleware for handling search proxy errors.
    
    Returns:
        Callable: Middleware function
    """
    async def error_handler_middleware(request: Request, call_next):
        """Middleware to catch and handle search proxy errors."""
        start_time = time.time()
        
        try:
            response = await call_next(request)
            return response
            
        except SearchProxyException as e:
            # Handle known search proxy errors
            SearchProxyErrorHandler.log_error_context(
                e, request, "middleware_error_handling"
            )
            return SearchProxyErrorHandler.handle_search_proxy_error(e)
            
        except PydanticValidationError as e:
            # Handle Pydantic validation errors
            SearchProxyErrorHandler.log_error_context(
                e, request, "validation_error_handling"
            )
            return SearchProxyErrorHandler.handle_validation_error(e)
            
        except Exception as e:
            # Handle unexpected errors
            SearchProxyErrorHandler.log_error_context(
                e, request, "unexpected_error_handling"
            )
            return SearchProxyErrorHandler.handle_unexpected_error(
                e, "request_processing", start_time
            )
    
    return error_handler_middleware