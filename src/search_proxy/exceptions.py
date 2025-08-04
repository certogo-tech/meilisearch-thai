"""
Custom exceptions for the search proxy service.

Provides structured error handling with consistent error responses
and appropriate HTTP status codes.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime


class SearchProxyException(Exception):
    """Base exception for search proxy errors."""
    
    def __init__(
        self,
        message: str,
        error_code: str = "SEARCH_PROXY_ERROR",
        details: Optional[Dict[str, Any]] = None,
        fallback_used: bool = False,
        partial_results: Optional[List[Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.fallback_used = fallback_used
        self.partial_results = partial_results or []
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary format."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
            "fallback_used": self.fallback_used,
            "partial_results": self.partial_results,
            "timestamp": self.timestamp
        }


class ValidationError(SearchProxyException):
    """Exception for request validation errors."""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        validation_details = details or {}
        if field:
            validation_details["field"] = field
        if value is not None:
            validation_details["invalid_value"] = str(value)
        
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            details=validation_details
        )


class TokenizationError(SearchProxyException):
    """Exception for tokenization failures."""
    
    def __init__(
        self,
        message: str,
        engine: Optional[str] = None,
        text_length: Optional[int] = None,
        fallback_used: bool = True,
        details: Optional[Dict[str, Any]] = None
    ):
        tokenization_details = details or {}
        if engine:
            tokenization_details["failed_engine"] = engine
        if text_length is not None:
            tokenization_details["text_length"] = text_length
        
        super().__init__(
            message=message,
            error_code="TOKENIZATION_ERROR",
            details=tokenization_details,
            fallback_used=fallback_used
        )


class SearchExecutionError(SearchProxyException):
    """Exception for search execution failures."""
    
    def __init__(
        self,
        message: str,
        index_name: Optional[str] = None,
        query_variants: Optional[int] = None,
        partial_results: Optional[List[Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        search_details = details or {}
        if index_name:
            search_details["index_name"] = index_name
        if query_variants is not None:
            search_details["query_variants_attempted"] = query_variants
        
        super().__init__(
            message=message,
            error_code="SEARCH_EXECUTION_ERROR",
            details=search_details,
            fallback_used=bool(partial_results),
            partial_results=partial_results or []
        )


class MeilisearchConnectionError(SearchProxyException):
    """Exception for Meilisearch connectivity issues."""
    
    def __init__(
        self,
        message: str,
        host: Optional[str] = None,
        timeout: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        connection_details = details or {}
        if host:
            connection_details["meilisearch_host"] = host
        if timeout is not None:
            connection_details["timeout_ms"] = timeout
        
        super().__init__(
            message=message,
            error_code="MEILISEARCH_CONNECTION_ERROR",
            details=connection_details,
            fallback_used=True
        )


class RankingError(SearchProxyException):
    """Exception for result ranking failures."""
    
    def __init__(
        self,
        message: str,
        results_count: Optional[int] = None,
        ranking_algorithm: Optional[str] = None,
        partial_results: Optional[List[Any]] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        ranking_details = details or {}
        if results_count is not None:
            ranking_details["results_count"] = results_count
        if ranking_algorithm:
            ranking_details["ranking_algorithm"] = ranking_algorithm
        
        super().__init__(
            message=message,
            error_code="RANKING_ERROR",
            details=ranking_details,
            fallback_used=bool(partial_results),
            partial_results=partial_results or []
        )


class ServiceUnavailableError(SearchProxyException):
    """Exception for service unavailability."""
    
    def __init__(
        self,
        message: str,
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        service_details = details or {}
        if service_name:
            service_details["service"] = service_name
        
        super().__init__(
            message=message,
            error_code="SERVICE_UNAVAILABLE",
            details=service_details
        )


class TimeoutError(SearchProxyException):
    """Exception for operation timeouts."""
    
    def __init__(
        self,
        message: str,
        operation: Optional[str] = None,
        timeout_ms: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        timeout_details = details or {}
        if operation:
            timeout_details["operation"] = operation
        if timeout_ms is not None:
            timeout_details["timeout_ms"] = timeout_ms
        
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            details=timeout_details,
            fallback_used=True
        )


class ConfigurationError(SearchProxyException):
    """Exception for configuration issues."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        config_details = details or {}
        if config_key:
            config_details["config_key"] = config_key
        if config_value is not None:
            config_details["config_value"] = str(config_value)
        
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            details=config_details
        )


# HTTP status code mapping for exceptions
EXCEPTION_STATUS_CODES = {
    ValidationError: 400,
    TokenizationError: 422,
    SearchExecutionError: 500,
    MeilisearchConnectionError: 503,
    RankingError: 500,
    ServiceUnavailableError: 503,
    TimeoutError: 504,
    ConfigurationError: 500,
    SearchProxyException: 500,  # Default for base exception
}


def get_http_status_code(exception: SearchProxyException) -> int:
    """
    Get appropriate HTTP status code for an exception.
    
    Args:
        exception: Search proxy exception
        
    Returns:
        int: HTTP status code
    """
    return EXCEPTION_STATUS_CODES.get(type(exception), 500)