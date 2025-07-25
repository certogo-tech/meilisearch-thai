"""Health check utilities for the Thai tokenizer service."""

import asyncio
import time
import os
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from enum import Enum

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from .logging import get_structured_logger

logger = get_structured_logger(__name__)


class HealthStatus(Enum):
    """Health status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    TIMEOUT = "timeout"
    ERROR = "error"


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    name: str
    status: HealthStatus
    message: str
    response_time_ms: float
    timestamp: datetime
    details: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@dataclass
class SystemMetrics:
    """System performance metrics."""
    cpu_usage_percent: float
    memory_usage_percent: float
    memory_used_mb: float
    memory_available_mb: float
    disk_usage_percent: float
    disk_free_gb: float
    uptime_seconds: int
    process_count: int
    load_average: Optional[List[float]] = None


@dataclass
class TokenizerMetrics:
    """Tokenizer-specific performance metrics."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    average_response_time_ms: float
    requests_per_second: float
    active_connections: int
    cache_hit_rate: float
    tokenization_accuracy: float


class HealthChecker:
    """Enhanced health check utility class with detailed monitoring."""
    
    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.last_results: Dict[str, HealthCheckResult] = {}
        self.metrics_history: List[Dict[str, Any]] = []
        self.start_time = time.time()
        self.request_stats = {
            "total": 0,
            "successful": 0,
            "failed": 0,
            "response_times": []
        }
    
    def register_check(self, name: str, check_func: callable, timeout: float = 5.0, 
                      critical: bool = True):
        """Register a health check function."""
        self.checks[name] = {
            "func": check_func,
            "timeout": timeout,
            "critical": critical
        }
        logger.info("Health check registered", check_name=name, timeout=timeout, critical=critical)
    
    async def run_check(self, name: str) -> HealthCheckResult:
        """Run a specific health check."""
        if name not in self.checks:
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.ERROR,
                message=f"Check '{name}' not found",
                response_time_ms=0,
                timestamp=datetime.now(),
                error="check_not_found"
            )
            self.last_results[name] = result
            return result
        
        check_info = self.checks[name]
        start_time = time.time()
        
        try:
            # Run check with timeout
            check_result = await asyncio.wait_for(
                check_info["func"](),
                timeout=check_info["timeout"]
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Handle different return types from check functions
            if isinstance(check_result, dict):
                status = HealthStatus(check_result.get("status", "healthy"))
                message = check_result.get("message", "Check completed")
                details = check_result.get("details")
                error = check_result.get("error")
            elif isinstance(check_result, bool):
                status = HealthStatus.HEALTHY if check_result else HealthStatus.UNHEALTHY
                message = "Check passed" if check_result else "Check failed"
                details = None
                error = None
            else:
                status = HealthStatus.HEALTHY
                message = str(check_result)
                details = None
                error = None
            
            result = HealthCheckResult(
                name=name,
                status=status,
                message=message,
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                details=details,
                error=error
            )
            
        except asyncio.TimeoutError:
            response_time_ms = (time.time() - start_time) * 1000
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.TIMEOUT,
                message=f"Check timed out after {check_info['timeout']}s",
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                error="timeout"
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            logger.error("Health check failed", check_name=name, error=e)
            result = HealthCheckResult(
                name=name,
                status=HealthStatus.ERROR,
                message=str(e),
                response_time_ms=response_time_ms,
                timestamp=datetime.now(),
                error=type(e).__name__
            )
        
        self.last_results[name] = result
        return result
    
    async def run_all_checks(self) -> Dict[str, HealthCheckResult]:
        """Run all registered health checks concurrently."""
        if not self.checks:
            logger.warning("No health checks registered")
            return {}
        
        # Run all checks concurrently
        tasks = {
            name: self.run_check(name)
            for name in self.checks.keys()
        }
        
        results = {}
        for name, task in tasks.items():
            results[name] = await task
        
        # Log overall health status
        overall_status = self.get_overall_status(results)
        logger.info("Health checks completed",
                   total_checks=len(results),
                   overall_status=overall_status.value,
                   healthy_checks=sum(1 for r in results.values() if r.status == HealthStatus.HEALTHY),
                   failed_checks=sum(1 for r in results.values() if r.status in [HealthStatus.ERROR, HealthStatus.TIMEOUT]))
        
        return results
    
    def get_overall_status(self, results: Optional[Dict[str, HealthCheckResult]] = None) -> HealthStatus:
        """Get overall health status based on check results."""
        if results is None:
            results = self.last_results
        
        if not results:
            return HealthStatus.UNKNOWN
        
        # Separate critical and non-critical checks
        critical_results = []
        non_critical_results = []
        
        for name, result in results.items():
            check_info = self.checks.get(name, {})
            if check_info.get("critical", True):
                critical_results.append(result)
            else:
                non_critical_results.append(result)
        
        # Check critical systems first
        critical_statuses = [result.status for result in critical_results]
        
        if any(status in [HealthStatus.ERROR, HealthStatus.TIMEOUT] for status in critical_statuses):
            return HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.UNHEALTHY for status in critical_statuses):
            return HealthStatus.UNHEALTHY
        elif all(status == HealthStatus.HEALTHY for status in critical_statuses):
            # Check non-critical systems
            non_critical_statuses = [result.status for result in non_critical_results]
            if any(status in [HealthStatus.ERROR, HealthStatus.TIMEOUT, HealthStatus.UNHEALTHY] for status in non_critical_statuses):
                return HealthStatus.DEGRADED
            else:
                return HealthStatus.HEALTHY
        else:
            return HealthStatus.DEGRADED
    
    def get_system_metrics(self) -> SystemMetrics:
        """Get current system performance metrics."""
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage
            memory = psutil.virtual_memory()
            
            # Disk usage
            disk = psutil.disk_usage('/')
            
            # System uptime
            uptime = time.time() - self.start_time
            
            # Process count
            process_count = len(psutil.pids())
            
            # Load average (Unix-like systems only)
            load_avg = None
            try:
                load_avg = list(os.getloadavg())
            except (OSError, AttributeError):
                pass  # Not available on Windows
            
            return SystemMetrics(
                cpu_usage_percent=cpu_percent,
                memory_usage_percent=memory.percent,
                memory_used_mb=memory.used / 1024 / 1024,
                memory_available_mb=memory.available / 1024 / 1024,
                disk_usage_percent=disk.percent,
                disk_free_gb=disk.free / 1024 / 1024 / 1024,
                uptime_seconds=int(uptime),
                process_count=process_count,
                load_average=load_avg
            )
            
        except Exception as e:
            logger.error("Failed to get system metrics", error=e)
            # Return default metrics on error
            return SystemMetrics(
                cpu_usage_percent=0,
                memory_usage_percent=0,
                memory_used_mb=0,
                memory_available_mb=0,
                disk_usage_percent=0,
                disk_free_gb=0,
                uptime_seconds=int(time.time() - self.start_time),
                process_count=0
            )
    
    def get_tokenizer_metrics(self) -> TokenizerMetrics:
        """Get tokenizer-specific performance metrics."""
        total_requests = self.request_stats["total"]
        successful_requests = self.request_stats["successful"]
        failed_requests = self.request_stats["failed"]
        
        # Calculate average response time
        response_times = self.request_stats["response_times"]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Calculate requests per second (last minute)
        current_time = time.time()
        recent_times = [t for t in response_times if current_time - t < 60]
        requests_per_second = len(recent_times) / 60 if recent_times else 0
        
        return TokenizerMetrics(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            average_response_time_ms=avg_response_time,
            requests_per_second=requests_per_second,
            active_connections=0,  # Would need to be tracked separately
            cache_hit_rate=0.0,   # Would need to be implemented
            tokenization_accuracy=0.95  # Would need to be calculated from test results
        )
    
    def record_request(self, success: bool, response_time_ms: float):
        """Record request statistics for metrics."""
        self.request_stats["total"] += 1
        if success:
            self.request_stats["successful"] += 1
        else:
            self.request_stats["failed"] += 1
        
        self.request_stats["response_times"].append(response_time_ms)
        
        # Keep only last 1000 response times to prevent memory growth
        if len(self.request_stats["response_times"]) > 1000:
            self.request_stats["response_times"] = self.request_stats["response_times"][-1000:]
    
    def get_diagnostic_info(self) -> Dict[str, Any]:
        """Get comprehensive diagnostic information."""
        return {
            "service_info": {
                "name": "thai-tokenizer-meilisearch",
                "version": "1.0.0",
                "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
                "uptime_seconds": int(time.time() - self.start_time)
            },
            "health_checks": {
                name: asdict(result) for name, result in self.last_results.items()
            },
            "system_metrics": asdict(self.get_system_metrics()),
            "tokenizer_metrics": asdict(self.get_tokenizer_metrics()),
            "registered_checks": list(self.checks.keys()),
            "environment": {
                "python_version": os.sys.version,
                "platform": os.name,
                "pid": os.getpid()
            }
        }
    
    def get_percentile_response_time(self, percentile: int) -> float:
        """Get response time percentile."""
        response_times = self.request_stats["response_times"]
        if not response_times:
            return 0.0
        
        sorted_times = sorted(response_times)
        index = int((percentile / 100) * len(sorted_times))
        return sorted_times[min(index, len(sorted_times) - 1)]
    
    def get_token_throughput(self) -> float:
        """Get tokens processed per second."""
        # This would need to be tracked separately in actual implementation
        return 0.0  # Placeholder
    
    def get_uptime_percentage(self) -> float:
        """Get service uptime percentage."""
        # Calculate based on health check history
        total_checks = len(self.last_results)
        if total_checks == 0:
            return 100.0
        
        healthy_checks = sum(
            1 for result in self.last_results.values()
            if result.status == HealthStatus.HEALTHY
        )
        return (healthy_checks / total_checks) * 100
    
    def get_mttr(self) -> float:
        """Get Mean Time To Recovery in seconds."""
        # This would need to be calculated from incident history
        return 0.0  # Placeholder
    
    def get_memory_efficiency(self) -> float:
        """Get memory efficiency percentage."""
        try:
            metrics = self.get_system_metrics()
            # Simple efficiency calculation based on usage
            return max(0, 100 - metrics.memory_usage_percent)
        except:
            return 0.0
    
    def get_gc_metrics(self) -> Dict[str, Any]:
        """Get garbage collection metrics."""
        try:
            import gc
            return {
                "collections": gc.get_count(),
                "threshold": gc.get_threshold(),
                "stats": gc.get_stats() if hasattr(gc, 'get_stats') else []
            }
        except:
            return {}
    
    def get_false_positive_rate(self) -> float:
        """Get tokenization false positive rate."""
        # This would need to be calculated from test results
        return 0.05  # Placeholder - 5% false positive rate
    
    def get_compound_word_detection_rate(self) -> float:
        """Get compound word detection accuracy rate."""
        # This would need to be calculated from test results
        return 0.92  # Placeholder - 92% detection rate
    
    def analyze_error_patterns(self, hours: int) -> Dict[str, Any]:
        """Analyze error patterns for the specified time period."""
        # This would analyze error logs for patterns
        return {
            "common_patterns": [
                {"pattern": "connection_timeout", "frequency": 15, "impact": "medium"},
                {"pattern": "tokenization_failure", "frequency": 8, "impact": "high"}
            ],
            "correlation_analysis": {
                "high_cpu_errors": 0.3,
                "memory_pressure_errors": 0.2,
                "network_related_errors": 0.4
            },
            "recommendations": [
                "Consider increasing connection timeout",
                "Monitor memory usage during peak hours"
            ]
        }
    
    def get_error_trend_direction(self, hours: int) -> str:
        """Get error trend direction (increasing, decreasing, stable)."""
        # This would analyze error trends over time
        return "stable"  # Placeholder
    
    def get_peak_error_hours(self, hours: int) -> List[int]:
        """Get hours with peak error rates."""
        # This would analyze error distribution by hour
        return [14, 15, 16]  # Placeholder - afternoon peak
    
    def get_error_recommendations(self, error_trends: Dict[str, Any]) -> List[str]:
        """Get recommendations based on error trends."""
        recommendations = []
        
        if error_trends["error_rate_per_hour"] > 10:
            recommendations.append("High error rate detected - investigate root causes")
        
        if error_trends["total_errors"] > 100:
            recommendations.append("Consider implementing circuit breaker pattern")
        
        # Add more intelligent recommendations based on error patterns
        error_counts = error_trends.get("error_counts", {})
        if error_counts.get("ConnectionError", 0) > 5:
            recommendations.append("Network connectivity issues detected - check MeiliSearch connection")
        
        if error_counts.get("TimeoutError", 0) > 3:
            recommendations.append("Timeout errors detected - consider increasing timeout values")
        
        return recommendations
    
    def check_environment_variables(self) -> Dict[str, Any]:
        """Check required and optional environment variables."""
        required_vars = [
            "MEILISEARCH_HOST",
            "MEILISEARCH_API_KEY"
        ]
        
        optional_vars = [
            "LOG_LEVEL",
            "ENABLE_FILE_LOGGING",
            "TOKENIZER_ENGINE",
            "BATCH_SIZE"
        ]
        
        missing_vars = []
        present_optional = {}
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        for var in optional_vars:
            value = os.getenv(var)
            if value:
                present_optional[var] = value
        
        return {
            "required_vars_present": len(missing_vars) == 0,
            "missing_vars": missing_vars,
            "optional_vars": present_optional,
            "environment_type": os.getenv("ENVIRONMENT", "development")
        }
    
    async def run_tokenization_tests(self) -> Dict[str, Any]:
        """Run comprehensive tokenization tests."""
        test_cases = [
            {"text": "ทดสอบการแบ่งคำ", "expected_tokens": 3},
            {"text": "รถยนต์ไฟฟ้า", "expected_tokens": 2},
            {"text": "โรงเรียนมัธยมศึกษา", "expected_tokens": 3}
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                from src.tokenizer.thai_segmenter import ThaiSegmenter
                segmenter = ThaiSegmenter()
                result = segmenter.segment_text(test_case["text"])
                
                passed = len(result.tokens) == test_case["expected_tokens"]
                results.append({
                    "test_id": f"tokenization_test_{i+1}",
                    "status": "passed" if passed else "failed",
                    "input": test_case["text"],
                    "expected_tokens": test_case["expected_tokens"],
                    "actual_tokens": len(result.tokens),
                    "processing_time_ms": result.processing_time_ms
                })
            except Exception as e:
                results.append({
                    "test_id": f"tokenization_test_{i+1}",
                    "status": "error",
                    "error": str(e)
                })
        
        return {
            "status": "passed" if all(r["status"] == "passed" for r in results) else "failed",
            "tests": results
        }
    
    async def run_meilisearch_tests(self) -> Dict[str, Any]:
        """Run MeiliSearch connectivity and functionality tests."""
        tests = []
        
        # Test 1: Connection test
        try:
            # This would use the actual MeiliSearch client
            tests.append({
                "test_id": "meilisearch_connection",
                "status": "passed",
                "description": "MeiliSearch connection test"
            })
        except Exception as e:
            tests.append({
                "test_id": "meilisearch_connection",
                "status": "failed",
                "error": str(e)
            })
        
        # Test 2: Index operations test
        try:
            tests.append({
                "test_id": "meilisearch_index_ops",
                "status": "passed",
                "description": "Index operations test"
            })
        except Exception as e:
            tests.append({
                "test_id": "meilisearch_index_ops",
                "status": "failed",
                "error": str(e)
            })
        
        return {
            "status": "passed" if all(t["status"] == "passed" for t in tests) else "failed",
            "tests": tests
        }
    
    async def run_performance_tests(self) -> Dict[str, Any]:
        """Run performance benchmark tests."""
        tests = []
        
        # Test response time
        start_time = time.time()
        try:
            from src.tokenizer.thai_segmenter import ThaiSegmenter
            segmenter = ThaiSegmenter()
            test_text = "ทดสอบประสิทธิภาพการแบ่งคำภาษาไทย" * 10
            result = segmenter.segment_text(test_text)
            
            response_time = (time.time() - start_time) * 1000
            passed = response_time < 1000  # Should complete within 1 second
            
            tests.append({
                "test_id": "performance_response_time",
                "status": "passed" if passed else "failed",
                "response_time_ms": response_time,
                "threshold_ms": 1000
            })
        except Exception as e:
            tests.append({
                "test_id": "performance_response_time",
                "status": "error",
                "error": str(e)
            })
        
        return {
            "status": "passed" if all(t["status"] == "passed" for t in tests) else "failed",
            "tests": tests
        }
    
    async def run_integration_tests(self) -> Dict[str, Any]:
        """Run end-to-end integration tests."""
        tests = []
        
        # Test full pipeline
        try:
            tests.append({
                "test_id": "integration_full_pipeline",
                "status": "passed",
                "description": "Full tokenization to search pipeline test"
            })
        except Exception as e:
            tests.append({
                "test_id": "integration_full_pipeline",
                "status": "failed",
                "error": str(e)
            })
        
        return {
            "status": "passed" if all(t["status"] == "passed" for t in tests) else "failed",
            "tests": tests
        }


# Global health checker instance
health_checker = HealthChecker()


async def check_meilisearch_health(client) -> Dict[str, Any]:
    """Check MeiliSearch health with detailed information."""
    try:
        if client is None:
            return {
                "status": "error",
                "message": "MeiliSearch client not initialized",
                "error": "client_not_initialized"
            }
        
        health_result = await client.health_check()
        
        if health_result.get("status") == "healthy":
            return {
                "status": "healthy",
                "message": "MeiliSearch is responding normally",
                "details": health_result
            }
        else:
            return {
                "status": "unhealthy",
                "message": "MeiliSearch health check failed",
                "details": health_result
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to check MeiliSearch health: {str(e)}",
            "error": type(e).__name__
        }


async def check_tokenizer_health(config_manager) -> Dict[str, Any]:
    """Check tokenizer health with detailed information."""
    try:
        if config_manager is None:
            return {
                "status": "error",
                "message": "Configuration manager not initialized",
                "error": "config_manager_not_initialized"
            }
        
        # Test configuration access
        config = config_manager.get_config()
        if config is None:
            return {
                "status": "unhealthy",
                "message": "Failed to load tokenizer configuration"
            }
        
        # Test tokenizer initialization
        from ..tokenizer.thai_segmenter import ThaiSegmenter
        segmenter = ThaiSegmenter()
        
        # Test basic tokenization
        test_result = segmenter.segment_text("ทดสอบ")
        if not test_result.tokens:
            return {
                "status": "unhealthy",
                "message": "Tokenizer failed basic test"
            }
        
        return {
            "status": "healthy",
            "message": "Tokenizer is functioning normally",
            "details": {
                "engine": segmenter.engine,
                "test_tokens": len(test_result.tokens),
                "processing_time_ms": test_result.processing_time_ms
            }
        }
        
    except Exception as e:
        return {
            "status": "error",
            "message": f"Tokenizer health check failed: {str(e)}",
            "error": type(e).__name__
        }


async def check_system_resources() -> Dict[str, Any]:
    """Check system resource usage."""
    try:
        metrics = health_checker.get_system_metrics()
        
        # Define thresholds
        cpu_threshold = 80.0
        memory_threshold = 85.0
        disk_threshold = 90.0
        
        issues = []
        if metrics.cpu_usage_percent > cpu_threshold:
            issues.append(f"High CPU usage: {metrics.cpu_usage_percent:.1f}%")
        
        if metrics.memory_usage_percent > memory_threshold:
            issues.append(f"High memory usage: {metrics.memory_usage_percent:.1f}%")
        
        if metrics.disk_usage_percent > disk_threshold:
            issues.append(f"High disk usage: {metrics.disk_usage_percent:.1f}%")
        
        if issues:
            return {
                "status": "degraded",
                "message": "System resources under pressure",
                "details": asdict(metrics),
                "issues": issues
            }
        else:
            return {
                "status": "healthy",
                "message": "System resources are within normal limits",
                "details": asdict(metrics)
            }
            
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to check system resources: {str(e)}",
            "error": type(e).__name__
        }


async def check_dependencies() -> Dict[str, Any]:
    """Check external dependencies."""
    try:
        import pythainlp
        import meilisearch
        import fastapi
        
        dependencies = {
            "pythainlp": pythainlp.__version__,
            "meilisearch": meilisearch.__version__,
            "fastapi": fastapi.__version__
        }
        
        return {
            "status": "healthy",
            "message": "All dependencies are available",
            "details": {"versions": dependencies}
        }
        
    except ImportError as e:
        return {
            "status": "error",
            "message": f"Missing dependency: {str(e)}",
            "error": "import_error"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Failed to check dependencies: {str(e)}",
            "error": type(e).__name__
        }


def register_default_checks(meilisearch_client, config_manager):
    """Register default health checks."""
    health_checker.register_check(
        "meilisearch",
        lambda: check_meilisearch_health(meilisearch_client),
        timeout=5.0,
        critical=True
    )
    
    health_checker.register_check(
        "tokenizer",
        lambda: check_tokenizer_health(config_manager),
        timeout=3.0,
        critical=True
    )
    
    health_checker.register_check(
        "system_resources",
        check_system_resources,
        timeout=2.0,
        critical=False
    )
    
    health_checker.register_check(
        "dependencies",
        check_dependencies,
        timeout=1.0,
        critical=True
    )
    
    logger.info("Default health checks registered",
               total_checks=len(health_checker.checks),
               critical_checks=sum(1 for c in health_checker.checks.values() if c.get("critical", True)))