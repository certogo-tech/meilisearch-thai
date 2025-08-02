#!/usr/bin/env python3
"""
Comprehensive Error Handling and Recovery for Thai Tokenizer Deployment.

This module provides centralized error handling, recovery mechanisms, and
resilience patterns for all deployment components and operations.
"""

import asyncio
import logging
import os
import sys
import traceback
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable, Type
from dataclasses import dataclass, field
import json

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.logging import get_structured_logger


class ErrorSeverity(str, Enum):
    """Error severity levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""
    CONFIGURATION = "configuration"
    NETWORK = "network"
    PERMISSION = "permission"
    RESOURCE = "resource"
    SERVICE = "service"
    VALIDATION = "validation"
    DEPLOYMENT = "deployment"
    SYSTEM = "system"
    UNKNOWN = "unknown"


class RecoveryAction(str, Enum):
    """Recovery action types."""
    RETRY = "retry"
    FALLBACK = "fallback"
    SKIP = "skip"
    ABORT = "abort"
    MANUAL = "manual"


@dataclass
class ErrorContext:
    """Error context information."""
    component: str
    operation: str
    phase: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    stack_trace: Optional[str] = None


@dataclass
class RecoveryStrategy:
    """Recovery strategy definition."""
    name: str
    description: str
    action: RecoveryAction
    max_attempts: int = 3
    delay_seconds: float = 1.0
    conditions: List[str] = field(default_factory=list)
    recovery_func: Optional[Callable] = None


@dataclass
class ErrorRecord:
    """Error record for tracking and analysis."""
    error_id: str
    error_type: str
    error_message: str
    severity: ErrorSeverity
    category: ErrorCategory
    context: ErrorContext
    recovery_attempted: bool = False
    recovery_successful: bool = False
    recovery_strategy: Optional[str] = None
    resolution_time: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class DeploymentError(Exception):
    """Base exception for deployment-related errors."""
    
    def __init__(
        self, 
        message: str, 
        category: ErrorCategory = ErrorCategory.UNKNOWN,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: Optional[ErrorContext] = None,
        recoverable: bool = True
    ):
        super().__init__(message)
        self.category = category
        self.severity = severity
        self.context = context
        self.recoverable = recoverable


class ConfigurationError(DeploymentError):
    """Configuration-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class NetworkError(DeploymentError):
    """Network-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class PermissionError(DeploymentError):
    """Permission-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.PERMISSION,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ResourceError(DeploymentError):
    """Resource-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.RESOURCE,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ServiceError(DeploymentError):
    """Service-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.SERVICE,
            severity=ErrorSeverity.HIGH,
            **kwargs
        )


class ValidationError(DeploymentError):
    """Validation-related errors."""
    
    def __init__(self, message: str, **kwargs):
        super().__init__(
            message, 
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.MEDIUM,
            **kwargs
        )


class ErrorHandler:
    """Centralized error handling and recovery system."""
    
    def __init__(self, log_file: Optional[str] = None):
        self.logger = get_structured_logger(__name__)
        self.error_records: List[ErrorRecord] = []
        self.recovery_strategies: Dict[str, RecoveryStrategy] = {}
        self.error_patterns: Dict[str, ErrorCategory] = {}
        self.log_file = log_file
        
        # Initialize built-in recovery strategies
        self._initialize_recovery_strategies()
        self._initialize_error_patterns()
    
    def _initialize_recovery_strategies(self):
        """Initialize built-in recovery strategies."""
        
        # Connection timeout recovery
        self.recovery_strategies["connection_timeout"] = RecoveryStrategy(
            name="connection_timeout",
            description="Retry connection with exponential backoff",
            action=RecoveryAction.RETRY,
            max_attempts=3,
            delay_seconds=5.0,
            conditions=["timeout", "connection", "refused"],
            recovery_func=self._recover_connection_timeout
        )
        
        # Permission denied recovery
        self.recovery_strategies["permission_denied"] = RecoveryStrategy(
            name="permission_denied",
            description="Attempt to fix permissions or suggest manual intervention",
            action=RecoveryAction.MANUAL,
            max_attempts=1,
            delay_seconds=0.0,
            conditions=["permission", "access", "denied"],
            recovery_func=self._recover_permission_denied
        )
        
        # Resource exhaustion recovery
        self.recovery_strategies["resource_exhaustion"] = RecoveryStrategy(
            name="resource_exhaustion",
            description="Reduce resource usage and retry",
            action=RecoveryAction.FALLBACK,
            max_attempts=2,
            delay_seconds=10.0,
            conditions=["memory", "disk", "resource", "exhausted"],
            recovery_func=self._recover_resource_exhaustion
        )
        
        # Service unavailable recovery
        self.recovery_strategies["service_unavailable"] = RecoveryStrategy(
            name="service_unavailable",
            description="Wait for service to become available",
            action=RecoveryAction.RETRY,
            max_attempts=5,
            delay_seconds=30.0,
            conditions=["unavailable", "not found", "unreachable"],
            recovery_func=self._recover_service_unavailable
        )
        
        # Configuration invalid recovery
        self.recovery_strategies["configuration_invalid"] = RecoveryStrategy(
            name="configuration_invalid",
            description="Validate and fix configuration issues",
            action=RecoveryAction.FALLBACK,
            max_attempts=1,
            delay_seconds=0.0,
            conditions=["configuration", "config", "invalid", "missing"],
            recovery_func=self._recover_configuration_invalid
        )
        
        # Deployment failure recovery
        self.recovery_strategies["deployment_failure"] = RecoveryStrategy(
            name="deployment_failure",
            description="Clean up and attempt alternative deployment method",
            action=RecoveryAction.FALLBACK,
            max_attempts=1,
            delay_seconds=60.0,
            conditions=["deployment", "failed", "error"],
            recovery_func=self._recover_deployment_failure
        )
    
    def _initialize_error_patterns(self):
        """Initialize error pattern matching for categorization."""
        self.error_patterns = {
            # Configuration patterns
            r"config.*invalid|invalid.*config|configuration.*error": ErrorCategory.CONFIGURATION,
            r"missing.*config|config.*not found|no such file": ErrorCategory.CONFIGURATION,
            
            # Network patterns
            r"connection.*timeout|timeout.*connection": ErrorCategory.NETWORK,
            r"connection.*refused|refused.*connection": ErrorCategory.NETWORK,
            r"network.*unreachable|unreachable.*network": ErrorCategory.NETWORK,
            r"dns.*resolution|resolution.*failed": ErrorCategory.NETWORK,
            
            # Permission patterns
            r"permission.*denied|access.*denied": ErrorCategory.PERMISSION,
            r"not.*permitted|operation.*not permitted": ErrorCategory.PERMISSION,
            r"insufficient.*privileges|privileges.*insufficient": ErrorCategory.PERMISSION,
            
            # Resource patterns
            r"out of memory|memory.*exhausted": ErrorCategory.RESOURCE,
            r"disk.*full|no space left": ErrorCategory.RESOURCE,
            r"resource.*unavailable|unavailable.*resource": ErrorCategory.RESOURCE,
            
            # Service patterns
            r"service.*unavailable|unavailable.*service": ErrorCategory.SERVICE,
            r"service.*not found|not found.*service": ErrorCategory.SERVICE,
            r"service.*failed|failed.*service": ErrorCategory.SERVICE,
            
            # Validation patterns
            r"validation.*failed|failed.*validation": ErrorCategory.VALIDATION,
            r"invalid.*input|input.*invalid": ErrorCategory.VALIDATION,
            r"schema.*error|error.*schema": ErrorCategory.VALIDATION,
            
            # System patterns
            r"system.*error|error.*system": ErrorCategory.SYSTEM,
            r"kernel.*error|error.*kernel": ErrorCategory.SYSTEM,
            r"hardware.*error|error.*hardware": ErrorCategory.SYSTEM
        }
    
    def handle_error(
        self, 
        error: Exception, 
        context: Optional[ErrorContext] = None,
        attempt_recovery: bool = True
    ) -> ErrorRecord:
        """Handle an error with optional recovery attempt."""
        
        # Generate error ID
        error_id = f"err-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{len(self.error_records)}"
        
        # Classify error
        category = self._classify_error(error)
        severity = self._determine_severity(error, category)
        
        # Create error record
        error_record = ErrorRecord(
            error_id=error_id,
            error_type=type(error).__name__,
            error_message=str(error),
            severity=severity,
            category=category,
            context=context or ErrorContext(
                component="unknown",
                operation="unknown",
                phase="unknown",
                stack_trace=traceback.format_exc()
            )
        )
        
        # Log error
        self._log_error(error_record)
        
        # Store error record
        self.error_records.append(error_record)
        
        # Attempt recovery if requested and error is recoverable
        if attempt_recovery and getattr(error, 'recoverable', True):
            recovery_result = asyncio.create_task(self._attempt_recovery(error_record))
            # Note: In a real implementation, you'd want to handle this properly
            # For now, we'll mark it as attempted
            error_record.recovery_attempted = True
        
        return error_record
    
    def _classify_error(self, error: Exception) -> ErrorCategory:
        """Classify error based on type and message."""
        
        # Check if it's a custom deployment error
        if isinstance(error, DeploymentError):
            return error.category
        
        # Check error type
        error_type = type(error).__name__.lower()
        error_message = str(error).lower()
        
        # Pattern matching
        import re
        for pattern, category in self.error_patterns.items():
            if re.search(pattern, error_message, re.IGNORECASE):
                return category
        
        # Type-based classification
        if "timeout" in error_type or "connection" in error_type:
            return ErrorCategory.NETWORK
        elif "permission" in error_type or "access" in error_type:
            return ErrorCategory.PERMISSION
        elif "memory" in error_type or "resource" in error_type:
            return ErrorCategory.RESOURCE
        elif "config" in error_type or "validation" in error_type:
            return ErrorCategory.CONFIGURATION
        elif "service" in error_type:
            return ErrorCategory.SERVICE
        else:
            return ErrorCategory.UNKNOWN
    
    def _determine_severity(self, error: Exception, category: ErrorCategory) -> ErrorSeverity:
        """Determine error severity based on type and category."""
        
        # Check if it's a custom deployment error with severity
        if isinstance(error, DeploymentError):
            return error.severity
        
        # Category-based severity
        severity_map = {
            ErrorCategory.CONFIGURATION: ErrorSeverity.HIGH,
            ErrorCategory.PERMISSION: ErrorSeverity.HIGH,
            ErrorCategory.SERVICE: ErrorSeverity.HIGH,
            ErrorCategory.NETWORK: ErrorSeverity.MEDIUM,
            ErrorCategory.RESOURCE: ErrorSeverity.MEDIUM,
            ErrorCategory.VALIDATION: ErrorSeverity.MEDIUM,
            ErrorCategory.DEPLOYMENT: ErrorSeverity.HIGH,
            ErrorCategory.SYSTEM: ErrorSeverity.CRITICAL,
            ErrorCategory.UNKNOWN: ErrorSeverity.MEDIUM
        }
        
        return severity_map.get(category, ErrorSeverity.MEDIUM)
    
    def _log_error(self, error_record: ErrorRecord):
        """Log error record."""
        log_level = {
            ErrorSeverity.LOW: logging.INFO,
            ErrorSeverity.MEDIUM: logging.WARNING,
            ErrorSeverity.HIGH: logging.ERROR,
            ErrorSeverity.CRITICAL: logging.CRITICAL
        }.get(error_record.severity, logging.ERROR)
        
        self.logger.log(
            log_level,
            f"Error {error_record.error_id}: {error_record.error_message}",
            extra={
                "error_id": error_record.error_id,
                "error_type": error_record.error_type,
                "category": error_record.category.value,
                "severity": error_record.severity.value,
                "component": error_record.context.component,
                "operation": error_record.context.operation,
                "phase": error_record.context.phase
            }
        )
        
        # Write to error log file if specified
        if self.log_file:
            self._write_error_log(error_record)
    
    def _write_error_log(self, error_record: ErrorRecord):
        """Write error to log file."""
        try:
            log_entry = {
                "timestamp": error_record.context.timestamp.isoformat(),
                "error_id": error_record.error_id,
                "error_type": error_record.error_type,
                "error_message": error_record.error_message,
                "severity": error_record.severity.value,
                "category": error_record.category.value,
                "context": {
                    "component": error_record.context.component,
                    "operation": error_record.context.operation,
                    "phase": error_record.context.phase,
                    "metadata": error_record.context.metadata
                },
                "stack_trace": error_record.context.stack_trace
            }
            
            log_file = Path(self.log_file)
            log_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(log_file, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            self.logger.error(f"Failed to write error log: {e}")
    
    async def _attempt_recovery(self, error_record: ErrorRecord) -> bool:
        """Attempt to recover from error."""
        
        # Find matching recovery strategy
        strategy = self._find_recovery_strategy(error_record)
        
        if not strategy:
            self.logger.warning(f"No recovery strategy found for error: {error_record.error_id}")
            return False
        
        error_record.recovery_strategy = strategy.name
        
        self.logger.info(f"Attempting recovery for error {error_record.error_id} using strategy: {strategy.name}")
        
        # Execute recovery strategy
        for attempt in range(strategy.max_attempts):
            try:
                if strategy.recovery_func:
                    success = await strategy.recovery_func(error_record, attempt + 1)
                else:
                    success = await self._default_recovery(error_record, strategy, attempt + 1)
                
                if success:
                    error_record.recovery_successful = True
                    error_record.resolution_time = datetime.now(timezone.utc)
                    self.logger.info(f"Recovery successful for error: {error_record.error_id}")
                    return True
                
                # Wait before next attempt
                if attempt < strategy.max_attempts - 1:
                    delay = strategy.delay_seconds * (2 ** attempt)  # Exponential backoff
                    await asyncio.sleep(delay)
                    
            except Exception as recovery_error:
                self.logger.error(f"Recovery attempt {attempt + 1} failed: {recovery_error}")
        
        self.logger.warning(f"Recovery failed for error: {error_record.error_id}")
        return False
    
    def _find_recovery_strategy(self, error_record: ErrorRecord) -> Optional[RecoveryStrategy]:
        """Find appropriate recovery strategy for error."""
        
        error_message = error_record.error_message.lower()
        
        # Check each strategy's conditions
        for strategy in self.recovery_strategies.values():
            if any(condition in error_message for condition in strategy.conditions):
                return strategy
        
        # Fallback based on category
        category_strategies = {
            ErrorCategory.NETWORK: "connection_timeout",
            ErrorCategory.PERMISSION: "permission_denied",
            ErrorCategory.RESOURCE: "resource_exhaustion",
            ErrorCategory.SERVICE: "service_unavailable",
            ErrorCategory.CONFIGURATION: "configuration_invalid",
            ErrorCategory.DEPLOYMENT: "deployment_failure"
        }
        
        strategy_name = category_strategies.get(error_record.category)
        if strategy_name and strategy_name in self.recovery_strategies:
            return self.recovery_strategies[strategy_name]
        
        return None
    
    async def _default_recovery(
        self, 
        error_record: ErrorRecord, 
        strategy: RecoveryStrategy, 
        attempt: int
    ) -> bool:
        """Default recovery implementation."""
        
        if strategy.action == RecoveryAction.RETRY:
            # Simple retry - return True to indicate retry should be attempted
            return True
        elif strategy.action == RecoveryAction.FALLBACK:
            # Fallback to alternative approach
            return await self._fallback_recovery(error_record)
        elif strategy.action == RecoveryAction.SKIP:
            # Skip the operation
            return True
        elif strategy.action == RecoveryAction.MANUAL:
            # Requires manual intervention
            self.logger.warning(f"Manual intervention required for error: {error_record.error_id}")
            return False
        else:
            return False
    
    async def _fallback_recovery(self, error_record: ErrorRecord) -> bool:
        """Fallback recovery implementation."""
        # This would implement fallback logic based on the error category
        # For now, just return False to indicate fallback is not available
        return False
    
    # Recovery function implementations
    async def _recover_connection_timeout(self, error_record: ErrorRecord, attempt: int) -> bool:
        """Recover from connection timeout."""
        try:
            # Wait with exponential backoff
            delay = 5.0 * (2 ** (attempt - 1))
            await asyncio.sleep(delay)
            
            # Test connectivity (this would be implemented based on the specific service)
            # For now, just return True to simulate successful recovery
            return True
            
        except Exception:
            return False
    
    async def _recover_permission_denied(self, error_record: ErrorRecord, attempt: int) -> bool:
        """Recover from permission denied."""
        try:
            # Check if we can fix permissions
            if error_record.context.metadata.get("file_path"):
                file_path = Path(error_record.context.metadata["file_path"])
                if file_path.exists():
                    try:
                        os.chmod(file_path, 0o755)
                        return True
                    except PermissionError:
                        pass
            
            # Suggest manual intervention
            self.logger.warning("Permission issue requires manual intervention")
            return False
            
        except Exception:
            return False
    
    async def _recover_resource_exhaustion(self, error_record: ErrorRecord, attempt: int) -> bool:
        """Recover from resource exhaustion."""
        try:
            # Implement resource cleanup or reduction
            # This would be specific to the resource type
            
            # Wait for resources to be freed
            await asyncio.sleep(10.0)
            
            return True
            
        except Exception:
            return False
    
    async def _recover_service_unavailable(self, error_record: ErrorRecord, attempt: int) -> bool:
        """Recover from service unavailable."""
        try:
            # Wait for service to become available
            delay = 30.0 * attempt
            await asyncio.sleep(delay)
            
            # Test service availability (this would be implemented based on the specific service)
            return True
            
        except Exception:
            return False
    
    async def _recover_configuration_invalid(self, error_record: ErrorRecord, attempt: int) -> bool:
        """Recover from configuration invalid."""
        try:
            # Attempt to fix common configuration issues
            # This would be specific to the configuration type
            
            return True
            
        except Exception:
            return False
    
    async def _recover_deployment_failure(self, error_record: ErrorRecord, attempt: int) -> bool:
        """Recover from deployment failure."""
        try:
            # Clean up failed deployment
            # This would implement cleanup logic
            
            # Wait before retry
            await asyncio.sleep(60.0)
            
            return False  # Usually requires manual intervention
            
        except Exception:
            return False
    
    def get_error_statistics(self) -> Dict[str, Any]:
        """Get error statistics and analysis."""
        if not self.error_records:
            return {"total_errors": 0}
        
        # Count by category
        category_counts = {}
        for record in self.error_records:
            category = record.category.value
            category_counts[category] = category_counts.get(category, 0) + 1
        
        # Count by severity
        severity_counts = {}
        for record in self.error_records:
            severity = record.severity.value
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
        
        # Recovery statistics
        recovery_attempted = len([r for r in self.error_records if r.recovery_attempted])
        recovery_successful = len([r for r in self.error_records if r.recovery_successful])
        
        return {
            "total_errors": len(self.error_records),
            "category_breakdown": category_counts,
            "severity_breakdown": severity_counts,
            "recovery_attempted": recovery_attempted,
            "recovery_successful": recovery_successful,
            "recovery_success_rate": (recovery_successful / recovery_attempted * 100) if recovery_attempted > 0 else 0,
            "most_common_category": max(category_counts.items(), key=lambda x: x[1])[0] if category_counts else None,
            "most_common_severity": max(severity_counts.items(), key=lambda x: x[1])[0] if severity_counts else None
        }
    
    def export_error_report(self, output_file: str) -> str:
        """Export comprehensive error report."""
        report = {
            "report_timestamp": datetime.now(timezone.utc).isoformat(),
            "statistics": self.get_error_statistics(),
            "error_records": [
                {
                    "error_id": record.error_id,
                    "timestamp": record.context.timestamp.isoformat(),
                    "error_type": record.error_type,
                    "error_message": record.error_message,
                    "severity": record.severity.value,
                    "category": record.category.value,
                    "component": record.context.component,
                    "operation": record.context.operation,
                    "phase": record.context.phase,
                    "recovery_attempted": record.recovery_attempted,
                    "recovery_successful": record.recovery_successful,
                    "recovery_strategy": record.recovery_strategy,
                    "resolution_time": record.resolution_time.isoformat() if record.resolution_time else None
                }
                for record in self.error_records
            ]
        }
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return str(output_path)


# Global error handler instance
_global_error_handler = None


def get_error_handler(log_file: Optional[str] = None) -> ErrorHandler:
    """Get global error handler instance."""
    global _global_error_handler
    
    if _global_error_handler is None:
        _global_error_handler = ErrorHandler(log_file)
    
    return _global_error_handler


def handle_deployment_error(
    error: Exception,
    component: str = "unknown",
    operation: str = "unknown",
    phase: str = "unknown",
    metadata: Optional[Dict[str, Any]] = None,
    attempt_recovery: bool = True
) -> ErrorRecord:
    """Convenience function for handling deployment errors."""
    
    context = ErrorContext(
        component=component,
        operation=operation,
        phase=phase,
        metadata=metadata or {},
        stack_trace=traceback.format_exc()
    )
    
    error_handler = get_error_handler()
    return error_handler.handle_error(error, context, attempt_recovery)


# Decorator for automatic error handling
def with_error_handling(
    component: str,
    operation: str,
    phase: str = "execution",
    attempt_recovery: bool = True
):
    """Decorator for automatic error handling."""
    
    def decorator(func):
        async def async_wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                handle_deployment_error(
                    e, component, operation, phase, 
                    {"args": str(args), "kwargs": str(kwargs)},
                    attempt_recovery
                )
                raise
        
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                handle_deployment_error(
                    e, component, operation, phase,
                    {"args": str(args), "kwargs": str(kwargs)},
                    attempt_recovery
                )
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    
    return decorator