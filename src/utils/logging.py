"""Comprehensive logging configuration utilities for Thai tokenizer service."""

import asyncio
import logging
import sys
import os
import time
import uuid
from typing import Dict, Any, Optional, Union
import json
from datetime import datetime, timedelta
from contextvars import ContextVar
from functools import wraps
from dataclasses import dataclass, asdict


# Context variables for request tracking
correlation_id_var: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar('request_id', default=None)


@dataclass
class PerformanceMetrics:
    """Performance metrics for operations."""
    operation: str
    duration_ms: float
    input_size: int = 0
    output_size: int = 0
    tokens_processed: int = 0
    success: bool = True
    error_type: Optional[str] = None
    memory_usage_mb: Optional[float] = None


@dataclass
class TokenizationMetrics:
    """Specific metrics for tokenization operations."""
    text_length: int
    token_count: int
    processing_time_ms: float
    engine: str
    compound_words_detected: int = 0
    thai_content_ratio: float = 0.0
    mixed_content: bool = False
    fallback_used: bool = False


@dataclass
class SearchMetrics:
    """Metrics for search operations."""
    query: str
    query_length: int
    results_count: int
    processing_time_ms: float
    index_name: str
    thai_query_detected: bool = False
    query_tokens: int = 0


class StructuredLogger:
    """Enhanced logger with structured logging and metrics."""
    
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name
    
    def _get_base_context(self) -> Dict[str, Any]:
        """Get base context for all log entries."""
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "service": "thai-tokenizer",
            "logger": self.name,
            "correlation_id": correlation_id_var.get(),
            "request_id": request_id_var.get(),
            "process_id": os.getpid(),
        }
    
    def info(self, message: str, **kwargs):
        """Log info message with structured data."""
        self._log(logging.INFO, message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """Log debug message with structured data."""
        self._log(logging.DEBUG, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message with structured data."""
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log error message with structured data."""
        if error:
            kwargs.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_traceback": self._format_exception(error) if error.__traceback__ else None
            })
        self._log(logging.ERROR, message, **kwargs)
    
    def _format_exception(self, error: Exception) -> Optional[str]:
        """Format exception traceback safely."""
        try:
            import traceback
            return ''.join(traceback.format_exception(type(error), error, error.__traceback__))
        except:
            return None
    
    def performance(self, metrics: PerformanceMetrics):
        """Log performance metrics."""
        self._log(
            logging.INFO,
            f"Performance: {metrics.operation}",
            event_type="performance",
            metrics=asdict(metrics)
        )
    
    def tokenization(self, metrics: TokenizationMetrics):
        """Log tokenization-specific metrics."""
        self._log(
            logging.INFO,
            f"Tokenization: {metrics.text_length} chars -> {metrics.token_count} tokens",
            event_type="tokenization",
            metrics=asdict(metrics)
        )
    
    def search(self, metrics: SearchMetrics):
        """Log search-specific metrics."""
        self._log(
            logging.INFO,
            f"Search: '{metrics.query}' -> {metrics.results_count} results",
            event_type="search",
            metrics=asdict(metrics)
        )
    
    def indexing(self, document_count: int, processing_time_ms: float, 
                index_name: str, success: bool = True, **kwargs):
        """Log indexing operations."""
        self._log(
            logging.INFO,
            f"Indexing: {document_count} documents in {index_name}",
            event_type="indexing",
            document_count=document_count,
            processing_time_ms=processing_time_ms,
            index_name=index_name,
            success=success,
            **kwargs
        )
    
    def critical(self, message: str, error: Optional[Exception] = None, **kwargs):
        """Log critical message with structured data."""
        if error:
            kwargs.update({
                "error_type": type(error).__name__,
                "error_message": str(error),
                "error_traceback": self._format_exception(error) if error.__traceback__ else None
            })
        self._log(logging.CRITICAL, message, **kwargs)
    
    def metrics(self, metric_name: str, value: float, unit: str = "", **kwargs):
        """Log metrics data for monitoring systems."""
        self._log(
            logging.INFO,
            f"Metric: {metric_name}",
            event_type="metric",
            metric_name=metric_name,
            metric_value=value,
            metric_unit=unit,
            **kwargs
        )
    
    def audit(self, action: str, resource: str, user_id: Optional[str] = None, **kwargs):
        """Log audit events for security and compliance."""
        self._log(
            logging.INFO,
            f"Audit: {action} on {resource}",
            event_type="audit",
            action=action,
            resource=resource,
            user_id=user_id,
            **kwargs
        )
    
    def business_event(self, event_name: str, **kwargs):
        """Log business events for analytics."""
        self._log(
            logging.INFO,
            f"Business Event: {event_name}",
            event_type="business",
            event_name=event_name,
            **kwargs
        )
    
    def security_event(self, event_type: str, severity: str = "medium", **kwargs):
        """Log security events for monitoring."""
        self._log(
            logging.WARNING if severity == "medium" else logging.ERROR,
            f"Security Event: {event_type}",
            event_type="security",
            security_event_type=event_type,
            severity=severity,
            **kwargs
        )
    
    def _log(self, log_level: int, message: str, **kwargs):
        """Internal logging method with context."""
        context = self._get_base_context()
        context.update({
            "level": logging.getLevelName(log_level),
            "message": message,
            **kwargs
        })
        
        # Use the original logger to emit the structured record
        record = logging.LogRecord(
            name=self.name,
            level=log_level,
            pathname="",
            lineno=0,
            msg=json.dumps(context),
            args=(),
            exc_info=None
        )
        self.logger.handle(record)


class JSONFormatter(logging.Formatter):
    """Enhanced JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        # If the message is already JSON (from StructuredLogger), return it
        try:
            json.loads(record.getMessage())
            return record.getMessage()
        except (json.JSONDecodeError, ValueError):
            pass
        
        # Otherwise, format as structured log entry
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "service": "thai-tokenizer",
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
            "process_id": os.getpid(),
            "correlation_id": correlation_id_var.get(),
            "request_id": request_id_var.get(),
        }
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
            
        # Add extra fields if present
        for attr in ['correlation_id', 'request_id', 'user_id', 'operation']:
            if hasattr(record, attr):
                log_entry[attr] = getattr(record, attr)
            
        return json.dumps(log_entry, ensure_ascii=False)


def performance_monitor(operation_name: str):
    """Decorator to monitor performance of functions."""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__)
            start_time = time.time()
            start_memory = _get_memory_usage()
            
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                end_memory = _get_memory_usage()
                
                # Calculate sizes if possible
                input_size = _estimate_size(args, kwargs)
                output_size = _estimate_size(result)
                
                metrics = PerformanceMetrics(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    input_size=input_size,
                    output_size=output_size,
                    success=True,
                    memory_usage_mb=end_memory - start_memory if start_memory and end_memory else None
                )
                
                logger.performance(metrics)
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                metrics = PerformanceMetrics(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    input_size=_estimate_size(args, kwargs),
                    success=False,
                    error_type=type(e).__name__
                )
                
                logger.performance(metrics)
                logger.error(f"Operation {operation_name} failed", error=e)
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            logger = StructuredLogger(func.__module__)
            start_time = time.time()
            start_memory = _get_memory_usage()
            
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                end_memory = _get_memory_usage()
                
                # Calculate sizes if possible
                input_size = _estimate_size(args, kwargs)
                output_size = _estimate_size(result)
                
                metrics = PerformanceMetrics(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    input_size=input_size,
                    output_size=output_size,
                    success=True,
                    memory_usage_mb=end_memory - start_memory if start_memory and end_memory else None
                )
                
                logger.performance(metrics)
                return result
                
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                
                metrics = PerformanceMetrics(
                    operation=operation_name,
                    duration_ms=duration_ms,
                    input_size=_estimate_size(args, kwargs),
                    success=False,
                    error_type=type(e).__name__
                )
                
                logger.performance(metrics)
                logger.error(f"Operation {operation_name} failed", error=e)
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


def set_correlation_id(correlation_id: str):
    """Set correlation ID for request tracking."""
    correlation_id_var.set(correlation_id)


def set_request_id(request_id: str):
    """Set request ID for request tracking."""
    request_id_var.set(request_id)


def generate_correlation_id() -> str:
    """Generate a new correlation ID."""
    return str(uuid.uuid4())


class ErrorTracker:
    """Enhanced error tracking and debugging utilities."""
    
    def __init__(self):
        self.error_counts = {}
        self.error_history = []
        self.max_history = 1000
    
    def track_error(self, error: Exception, context: Dict[str, Any] = None):
        """Track error occurrence with context."""
        error_type = type(error).__name__
        error_message = str(error)
        
        # Update error counts
        if error_type not in self.error_counts:
            self.error_counts[error_type] = 0
        self.error_counts[error_type] += 1
        
        # Add to error history
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "error_type": error_type,
            "error_message": error_message,
            "context": context or {},
            "correlation_id": correlation_id_var.get(),
            "request_id": request_id_var.get()
        }
        
        self.error_history.append(error_entry)
        
        # Keep history size manageable
        if len(self.error_history) > self.max_history:
            self.error_history = self.error_history[-self.max_history:]
        
        # Log the error
        logger = get_structured_logger("error_tracker")
        logger.error("Error tracked", 
                    error=error,
                    error_count=self.error_counts[error_type],
                    context=context)
    
    def get_error_summary(self) -> Dict[str, Any]:
        """Get summary of tracked errors."""
        return {
            "total_errors": len(self.error_history),
            "error_counts": self.error_counts.copy(),
            "recent_errors": self.error_history[-10:] if self.error_history else []
        }
    
    def get_error_trends(self, hours: int = 24) -> Dict[str, Any]:
        """Get error trends for the specified time period."""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        cutoff_str = cutoff_time.isoformat()
        
        recent_errors = [
            error for error in self.error_history
            if error["timestamp"] >= cutoff_str
        ]
        
        # Count errors by type in the time period
        error_counts = {}
        for error in recent_errors:
            error_type = error["error_type"]
            if error_type not in error_counts:
                error_counts[error_type] = 0
            error_counts[error_type] += 1
        
        return {
            "time_period_hours": hours,
            "total_errors": len(recent_errors),
            "error_counts": error_counts,
            "error_rate_per_hour": len(recent_errors) / hours if hours > 0 else 0
        }


class DebugContext:
    """Context manager for enhanced debugging information."""
    
    def __init__(self, operation: str, **context):
        self.operation = operation
        self.context = context
        self.start_time = None
        self.logger = get_structured_logger("debug")
    
    def __enter__(self):
        self.start_time = time.time()
        self.logger.debug(f"Starting operation: {self.operation}", 
                         operation=self.operation,
                         context=self.context)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration_ms = (time.time() - self.start_time) * 1000
        
        if exc_type is not None:
            self.logger.error(f"Operation failed: {self.operation}",
                            operation=self.operation,
                            duration_ms=duration_ms,
                            error_type=exc_type.__name__,
                            error_message=str(exc_val),
                            context=self.context)
            
            # Track the error
            error_tracker.track_error(exc_val, {
                "operation": self.operation,
                "duration_ms": duration_ms,
                **self.context
            })
        else:
            self.logger.debug(f"Operation completed: {self.operation}",
                            operation=self.operation,
                            duration_ms=duration_ms,
                            context=self.context)
    
    def add_context(self, **additional_context):
        """Add additional context during operation."""
        self.context.update(additional_context)
        self.logger.debug(f"Context updated for {self.operation}",
                         operation=self.operation,
                         additional_context=additional_context)


# Global error tracker instance
error_tracker = ErrorTracker()


def get_structured_logger(name: str) -> StructuredLogger:
    """Get a structured logger instance."""
    return StructuredLogger(name)


def debug_context(operation: str, **context) -> DebugContext:
    """Create a debug context for enhanced debugging."""
    return DebugContext(operation, **context)


def _get_memory_usage() -> Optional[float]:
    """Get current memory usage in MB."""
    try:
        import psutil
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # Convert to MB
    except ImportError:
        return None


def _estimate_size(obj: Any) -> int:
    """Estimate size of object for logging."""
    try:
        if isinstance(obj, str):
            return len(obj)
        elif isinstance(obj, (list, tuple)):
            return len(obj)
        elif isinstance(obj, dict):
            return len(obj)
        else:
            return sys.getsizeof(obj)
    except:
        return 0


def setup_logging(level: str = "INFO", enable_performance_logging: bool = True) -> None:
    """Set up comprehensive structured logging configuration."""
    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=[logging.StreamHandler(sys.stdout)],
        format="%(message)s"
    )
    
    # Set JSON formatter for all handlers
    formatter = JSONFormatter()
    for handler in logging.root.handlers:
        handler.setFormatter(formatter)
    
    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("meilisearch").setLevel(logging.INFO)
    logging.getLogger("pythainlp").setLevel(logging.WARNING)
    
    # Performance logging configuration
    if enable_performance_logging:
        perf_logger = logging.getLogger("performance")
        perf_logger.setLevel(logging.INFO)
        
        # Add metrics logger for detailed performance tracking
        metrics_logger = logging.getLogger("metrics")
        metrics_logger.setLevel(logging.INFO)
        
        # Add error tracking logger
        error_logger = logging.getLogger("errors")
        error_logger.setLevel(logging.ERROR)
    
    # Add file handlers for persistent logging
    log_dir = os.getenv("LOG_DIR", "/var/log/thai-tokenizer")
    if os.getenv("ENVIRONMENT") == "production" or os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true":
        try:
            os.makedirs(log_dir, exist_ok=True)
            
            # Main application log
            app_handler = logging.FileHandler(f"{log_dir}/app.log")
            app_handler.setFormatter(formatter)
            logging.root.addHandler(app_handler)
            
            # Performance metrics log
            perf_handler = logging.FileHandler(f"{log_dir}/performance.log")
            perf_handler.setFormatter(formatter)
            logging.getLogger("performance").addHandler(perf_handler)
            
            # Error tracking log
            error_handler = logging.FileHandler(f"{log_dir}/errors.log")
            error_handler.setFormatter(formatter)
            logging.getLogger("errors").addHandler(error_handler)
            
            # Metrics log for monitoring systems
            metrics_handler = logging.FileHandler(f"{log_dir}/metrics.log")
            metrics_handler.setFormatter(formatter)
            logging.getLogger("metrics").addHandler(metrics_handler)
            
        except Exception as e:
            # Fallback to stdout if file logging fails
            print(f"Warning: Failed to set up file logging: {e}")
    
    logger = get_structured_logger(__name__)
    logger.info("Logging system initialized", 
                level=level, 
                performance_logging=enable_performance_logging,
                log_directory=log_dir,
                file_logging_enabled=os.getenv("ENABLE_FILE_LOGGING", "false").lower() == "true")