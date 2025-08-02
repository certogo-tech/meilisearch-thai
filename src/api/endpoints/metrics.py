"""Prometheus-compatible metrics endpoints for monitoring integration."""

import time
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, Response
from fastapi.responses import PlainTextResponse

from src.utils.health import health_checker, HealthStatus
from src.utils.logging import get_structured_logger

logger = get_structured_logger(__name__)

router = APIRouter()


class PrometheusMetrics:
    """Prometheus metrics formatter and collector."""
    
    def __init__(self):
        self.metrics_cache = {}
        self.cache_ttl = 30  # Cache metrics for 30 seconds
        self.last_cache_time = 0
    
    def format_metric(self, name: str, value: float, labels: Dict[str, str] = None, 
                     help_text: str = None, metric_type: str = "gauge") -> str:
        """Format a single metric in Prometheus format."""
        lines = []
        
        if help_text:
            lines.append(f"# HELP {name} {help_text}")
        
        lines.append(f"# TYPE {name} {metric_type}")
        
        if labels:
            label_str = ",".join([f'{k}="{v}"' for k, v in labels.items()])
            lines.append(f"{name}{{{label_str}}} {value}")
        else:
            lines.append(f"{name} {value}")
        
        return "\n".join(lines)
    
    def format_health_metrics(self, check_results: Dict[str, Any]) -> List[str]:
        """Format health check results as Prometheus metrics."""
        metrics = []
        
        # Overall health status (0=unhealthy, 1=degraded, 2=healthy)
        overall_status = health_checker.get_overall_status(check_results)
        status_value = {
            HealthStatus.UNHEALTHY: 0,
            HealthStatus.ERROR: 0,
            HealthStatus.TIMEOUT: 0,
            HealthStatus.DEGRADED: 1,
            HealthStatus.HEALTHY: 2,
            HealthStatus.UNKNOWN: 0
        }.get(overall_status, 0)
        
        metrics.append(self.format_metric(
            "thai_tokenizer_health_status",
            status_value,
            help_text="Overall health status (0=unhealthy, 1=degraded, 2=healthy)"
        ))
        
        # Individual health check metrics
        for name, result in check_results.items():
            check_status = 1 if result.status == HealthStatus.HEALTHY else 0
            metrics.append(self.format_metric(
                "thai_tokenizer_health_check",
                check_status,
                labels={"check": name, "critical": str(health_checker.checks.get(name, {}).get("critical", True)).lower()},
                help_text="Individual health check status (0=failed, 1=healthy)"
            ))
            
            # Response time for each check
            metrics.append(self.format_metric(
                "thai_tokenizer_health_check_duration_ms",
                result.response_time_ms,
                labels={"check": name},
                help_text="Health check response time in milliseconds"
            ))
        
        # Health score (percentage)
        healthy_checks = sum(1 for r in check_results.values() if r.status == HealthStatus.HEALTHY)
        health_score = (healthy_checks / len(check_results) * 100) if check_results else 0
        metrics.append(self.format_metric(
            "thai_tokenizer_health_score_percent",
            health_score,
            help_text="Overall health score as percentage"
        ))
        
        return metrics
    
    def format_system_metrics(self, system_metrics) -> List[str]:
        """Format system metrics as Prometheus metrics."""
        metrics = []
        
        # CPU metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_cpu_usage_percent",
            system_metrics.cpu_usage_percent,
            help_text="CPU usage percentage"
        ))
        
        # Memory metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_memory_usage_percent",
            system_metrics.memory_usage_percent,
            help_text="Memory usage percentage"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_memory_used_bytes",
            system_metrics.memory_used_mb * 1024 * 1024,
            help_text="Memory used in bytes"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_memory_available_bytes",
            system_metrics.memory_available_mb * 1024 * 1024,
            help_text="Memory available in bytes"
        ))
        
        # Disk metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_disk_usage_percent",
            system_metrics.disk_usage_percent,
            help_text="Disk usage percentage"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_disk_free_bytes",
            system_metrics.disk_free_gb * 1024 * 1024 * 1024,
            help_text="Disk free space in bytes"
        ))
        
        # System metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_uptime_seconds",
            system_metrics.uptime_seconds,
            help_text="Service uptime in seconds"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_process_count",
            system_metrics.process_count,
            help_text="Number of system processes"
        ))
        
        # Load average (if available)
        if system_metrics.load_average:
            for i, load in enumerate(system_metrics.load_average):
                period = ["1m", "5m", "15m"][i] if i < 3 else f"{i+1}m"
                metrics.append(self.format_metric(
                    "thai_tokenizer_load_average",
                    load,
                    labels={"period": period},
                    help_text="System load average"
                ))
        
        return metrics
    
    def format_tokenizer_metrics(self, tokenizer_metrics) -> List[str]:
        """Format tokenizer performance metrics as Prometheus metrics."""
        metrics = []
        
        # Request metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_requests_total",
            tokenizer_metrics.total_requests,
            help_text="Total number of tokenization requests",
            metric_type="counter"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_requests_successful_total",
            tokenizer_metrics.successful_requests,
            help_text="Total number of successful requests",
            metric_type="counter"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_requests_failed_total",
            tokenizer_metrics.failed_requests,
            help_text="Total number of failed requests",
            metric_type="counter"
        ))
        
        # Success rate
        success_rate = (tokenizer_metrics.successful_requests / tokenizer_metrics.total_requests * 100) if tokenizer_metrics.total_requests > 0 else 100
        metrics.append(self.format_metric(
            "thai_tokenizer_success_rate_percent",
            success_rate,
            help_text="Request success rate percentage"
        ))
        
        # Performance metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_response_time_ms",
            tokenizer_metrics.average_response_time_ms,
            help_text="Average response time in milliseconds"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_requests_per_second",
            tokenizer_metrics.requests_per_second,
            help_text="Requests processed per second"
        ))
        
        # Response time percentiles
        metrics.append(self.format_metric(
            "thai_tokenizer_response_time_p95_ms",
            health_checker.get_percentile_response_time(95),
            help_text="95th percentile response time in milliseconds"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_response_time_p99_ms",
            health_checker.get_percentile_response_time(99),
            help_text="99th percentile response time in milliseconds"
        ))
        
        # Quality metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_accuracy_percent",
            tokenizer_metrics.tokenization_accuracy * 100,
            help_text="Tokenization accuracy percentage"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_cache_hit_rate_percent",
            tokenizer_metrics.cache_hit_rate * 100,
            help_text="Cache hit rate percentage"
        ))
        
        # Active connections
        metrics.append(self.format_metric(
            "thai_tokenizer_active_connections",
            tokenizer_metrics.active_connections,
            help_text="Number of active connections"
        ))
        
        # Throughput metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_tokens_per_second",
            health_checker.get_token_throughput(),
            help_text="Tokens processed per second"
        ))
        
        return metrics
    
    def format_meilisearch_metrics(self) -> List[str]:
        """Format MeiliSearch-specific metrics."""
        metrics = []
        
        try:
            # Get MeiliSearch health check result
            meilisearch_result = health_checker.last_results.get("meilisearch")
            if meilisearch_result:
                # Connection status
                connection_status = 1 if meilisearch_result.status == HealthStatus.HEALTHY else 0
                metrics.append(self.format_metric(
                    "thai_tokenizer_meilisearch_connection_status",
                    connection_status,
                    help_text="MeiliSearch connection status (0=disconnected, 1=connected)"
                ))
                
                # Connection response time
                metrics.append(self.format_metric(
                    "thai_tokenizer_meilisearch_response_time_ms",
                    meilisearch_result.response_time_ms,
                    help_text="MeiliSearch connection response time in milliseconds"
                ))
                
                # Additional MeiliSearch metrics from details
                if meilisearch_result.details:
                    details = meilisearch_result.details
                    
                    # Index count
                    if "index_count" in details:
                        metrics.append(self.format_metric(
                            "thai_tokenizer_meilisearch_indexes_total",
                            details["index_count"],
                            help_text="Total number of MeiliSearch indexes"
                        ))
                    
                    # Document count
                    if "document_count" in details:
                        metrics.append(self.format_metric(
                            "thai_tokenizer_meilisearch_documents_total",
                            details["document_count"],
                            help_text="Total number of documents in MeiliSearch"
                        ))
                    
                    # Database size
                    if "database_size_bytes" in details:
                        metrics.append(self.format_metric(
                            "thai_tokenizer_meilisearch_database_size_bytes",
                            details["database_size_bytes"],
                            help_text="MeiliSearch database size in bytes"
                        ))
        
        except Exception as e:
            logger.warning("Failed to format MeiliSearch metrics", error=e)
        
        return metrics
    
    def format_error_metrics(self) -> List[str]:
        """Format error and reliability metrics."""
        metrics = []
        
        try:
            from src.utils.logging import error_tracker
            
            # Get error summary
            error_summary = error_tracker.get_error_summary()
            error_trends = error_tracker.get_error_trends(hours=1)
            
            # Total errors
            metrics.append(self.format_metric(
                "thai_tokenizer_errors_total",
                error_summary["total_errors"],
                help_text="Total number of errors",
                metric_type="counter"
            ))
            
            # Error rate
            metrics.append(self.format_metric(
                "thai_tokenizer_error_rate_per_hour",
                error_trends["error_rate_per_hour"],
                help_text="Error rate per hour"
            ))
            
            # Error types
            for error_type, count in error_summary["error_counts"].items():
                metrics.append(self.format_metric(
                    "thai_tokenizer_errors_by_type_total",
                    count,
                    labels={"error_type": error_type},
                    help_text="Total errors by type",
                    metric_type="counter"
                ))
            
            # Reliability metrics
            metrics.append(self.format_metric(
                "thai_tokenizer_uptime_percent",
                health_checker.get_uptime_percentage(),
                help_text="Service uptime percentage"
            ))
            
            metrics.append(self.format_metric(
                "thai_tokenizer_mttr_seconds",
                health_checker.get_mttr(),
                help_text="Mean Time To Recovery in seconds"
            ))
            
        except Exception as e:
            logger.warning("Failed to format error metrics", error=e)
        
        return metrics
    
    def format_custom_metrics(self) -> List[str]:
        """Format Thai tokenizer specific custom metrics."""
        metrics = []
        
        # Thai-specific quality metrics
        metrics.append(self.format_metric(
            "thai_tokenizer_compound_word_detection_rate_percent",
            health_checker.get_compound_word_detection_rate() * 100,
            help_text="Compound word detection accuracy percentage"
        ))
        
        metrics.append(self.format_metric(
            "thai_tokenizer_false_positive_rate_percent",
            health_checker.get_false_positive_rate() * 100,
            help_text="Tokenization false positive rate percentage"
        ))
        
        # Memory efficiency
        metrics.append(self.format_metric(
            "thai_tokenizer_memory_efficiency_percent",
            health_checker.get_memory_efficiency(),
            help_text="Memory usage efficiency percentage"
        ))
        
        # Garbage collection metrics
        gc_metrics = health_checker.get_gc_metrics()
        if gc_metrics:
            if "collections" in gc_metrics:
                for i, count in enumerate(gc_metrics["collections"]):
                    metrics.append(self.format_metric(
                        "thai_tokenizer_gc_collections_total",
                        count,
                        labels={"generation": str(i)},
                        help_text="Garbage collection count by generation",
                        metric_type="counter"
                    ))
        
        return metrics
    
    async def get_all_metrics(self) -> str:
        """Get all metrics in Prometheus format."""
        current_time = time.time()
        
        # Use cache if still valid
        if (current_time - self.last_cache_time) < self.cache_ttl and self.metrics_cache:
            return self.metrics_cache.get("all_metrics", "")
        
        try:
            all_metrics = []
            
            # Add metadata
            all_metrics.append("# Thai Tokenizer for MeiliSearch - Prometheus Metrics")
            all_metrics.append(f"# Generated at: {datetime.now().isoformat()}")
            all_metrics.append("")
            
            # Get current data
            check_results = await health_checker.run_all_checks()
            system_metrics = health_checker.get_system_metrics()
            tokenizer_metrics = health_checker.get_tokenizer_metrics()
            
            # Format all metric categories
            all_metrics.extend(self.format_health_metrics(check_results))
            all_metrics.append("")
            
            all_metrics.extend(self.format_system_metrics(system_metrics))
            all_metrics.append("")
            
            all_metrics.extend(self.format_tokenizer_metrics(tokenizer_metrics))
            all_metrics.append("")
            
            all_metrics.extend(self.format_meilisearch_metrics())
            all_metrics.append("")
            
            all_metrics.extend(self.format_error_metrics())
            all_metrics.append("")
            
            all_metrics.extend(self.format_custom_metrics())
            all_metrics.append("")
            
            # Add service info
            all_metrics.append(self.format_metric(
                "thai_tokenizer_info",
                1,
                labels={
                    "version": "1.0.0",
                    "service": "thai-tokenizer-meilisearch"
                },
                help_text="Service information"
            ))
            
            metrics_text = "\n".join(all_metrics)
            
            # Cache the result
            self.metrics_cache["all_metrics"] = metrics_text
            self.last_cache_time = current_time
            
            return metrics_text
            
        except Exception as e:
            logger.error("Failed to generate Prometheus metrics", error=e)
            return f"# Error generating metrics: {str(e)}\n"


# Global metrics instance
prometheus_metrics = PrometheusMetrics()


@router.get("/metrics", response_class=PlainTextResponse)
async def prometheus_metrics_endpoint():
    """
    Prometheus-compatible metrics endpoint.
    
    Returns all service metrics in Prometheus exposition format.
    """
    try:
        metrics_text = await prometheus_metrics.get_all_metrics()
        
        logger.debug("Prometheus metrics generated",
                    metrics_size=len(metrics_text),
                    cache_used=time.time() - prometheus_metrics.last_cache_time < prometheus_metrics.cache_ttl)
        
        return PlainTextResponse(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error("Prometheus metrics endpoint failed", error=e)
        return PlainTextResponse(
            content=f"# Error: Failed to generate metrics - {str(e)}\n",
            status_code=500,
            media_type="text/plain"
        )


@router.get("/metrics/health", response_class=PlainTextResponse)
async def health_metrics():
    """
    Health-specific metrics in Prometheus format.
    
    Returns only health check related metrics.
    """
    try:
        check_results = await health_checker.run_all_checks()
        health_metrics_list = prometheus_metrics.format_health_metrics(check_results)
        
        metrics_text = "\n".join([
            "# Thai Tokenizer Health Metrics",
            f"# Generated at: {datetime.now().isoformat()}",
            ""
        ] + health_metrics_list)
        
        return PlainTextResponse(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error("Health metrics endpoint failed", error=e)
        return PlainTextResponse(
            content=f"# Error: Failed to generate health metrics - {str(e)}\n",
            status_code=500,
            media_type="text/plain"
        )


@router.get("/metrics/system", response_class=PlainTextResponse)
async def system_metrics():
    """
    System resource metrics in Prometheus format.
    
    Returns only system resource related metrics.
    """
    try:
        system_metrics_data = health_checker.get_system_metrics()
        system_metrics_list = prometheus_metrics.format_system_metrics(system_metrics_data)
        
        metrics_text = "\n".join([
            "# Thai Tokenizer System Metrics",
            f"# Generated at: {datetime.now().isoformat()}",
            ""
        ] + system_metrics_list)
        
        return PlainTextResponse(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error("System metrics endpoint failed", error=e)
        return PlainTextResponse(
            content=f"# Error: Failed to generate system metrics - {str(e)}\n",
            status_code=500,
            media_type="text/plain"
        )


@router.get("/metrics/performance", response_class=PlainTextResponse)
async def performance_metrics():
    """
    Performance metrics in Prometheus format.
    
    Returns only performance and tokenizer related metrics.
    """
    try:
        tokenizer_metrics_data = health_checker.get_tokenizer_metrics()
        performance_metrics_list = prometheus_metrics.format_tokenizer_metrics(tokenizer_metrics_data)
        
        metrics_text = "\n".join([
            "# Thai Tokenizer Performance Metrics",
            f"# Generated at: {datetime.now().isoformat()}",
            ""
        ] + performance_metrics_list)
        
        return PlainTextResponse(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error("Performance metrics endpoint failed", error=e)
        return PlainTextResponse(
            content=f"# Error: Failed to generate performance metrics - {str(e)}\n",
            status_code=500,
            media_type="text/plain"
        )


@router.get("/metrics/custom", response_class=PlainTextResponse)
async def custom_metrics():
    """
    Thai tokenizer specific custom metrics in Prometheus format.
    
    Returns Thai language processing specific metrics.
    """
    try:
        custom_metrics_list = prometheus_metrics.format_custom_metrics()
        
        metrics_text = "\n".join([
            "# Thai Tokenizer Custom Metrics",
            f"# Generated at: {datetime.now().isoformat()}",
            ""
        ] + custom_metrics_list)
        
        return PlainTextResponse(
            content=metrics_text,
            media_type="text/plain; version=0.0.4; charset=utf-8"
        )
        
    except Exception as e:
        logger.error("Custom metrics endpoint failed", error=e)
        return PlainTextResponse(
            content=f"# Error: Failed to generate custom metrics - {str(e)}\n",
            status_code=500,
            media_type="text/plain"
        )