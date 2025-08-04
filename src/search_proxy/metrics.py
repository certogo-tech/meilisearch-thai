"""
Performance metrics collection for the Thai search proxy service.

This module provides metrics collection and monitoring for search proxy operations,
including query processing, search execution, result ranking, and overall performance.
"""

import time
import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict, deque
import threading

from ..utils.logging import get_structured_logger


logger = get_structured_logger(__name__)


@dataclass
class SearchMetrics:
    """Container for search operation metrics."""
    total_searches: int = 0
    successful_searches: int = 0
    failed_searches: int = 0
    total_query_variants: int = 0
    total_results_returned: int = 0
    total_unique_results: int = 0
    total_processing_time_ms: float = 0.0
    
    # Component timing breakdowns
    tokenization_time_ms: float = 0.0
    search_execution_time_ms: float = 0.0
    ranking_time_ms: float = 0.0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    
    # Error breakdown
    tokenization_errors: int = 0
    search_errors: int = 0
    ranking_errors: int = 0
    timeout_errors: int = 0


@dataclass
class QueryMetrics:
    """Container for query processing metrics."""
    total_queries_processed: int = 0
    thai_queries: int = 0
    english_queries: int = 0
    mixed_queries: int = 0
    
    # Tokenization metrics
    tokenization_successes: int = 0
    tokenization_failures: int = 0
    fallback_used: int = 0
    
    # Query variant generation
    total_variants_generated: int = 0
    avg_variants_per_query: float = 0.0
    
    # Compound word detection
    compound_words_detected: int = 0
    compound_word_splits: int = 0


@dataclass
class PerformanceMetrics:
    """Container for performance and throughput metrics."""
    # Response time percentiles (in ms)
    response_times: deque = field(default_factory=lambda: deque(maxlen=10000))
    
    # Throughput
    requests_per_second: float = 0.0
    queries_per_second: float = 0.0
    
    # Concurrency
    active_searches: int = 0
    peak_concurrent_searches: int = 0
    
    # Resource usage
    memory_usage_mb: float = 0.0
    cpu_usage_percent: float = 0.0


class SearchProxyMetricsCollector:
    """
    Collects and manages metrics for the search proxy service.
    
    Provides thread-safe metrics collection with time-based aggregation
    and Prometheus-compatible metric exposure.
    """
    
    def __init__(self, window_size_minutes: int = 5):
        """
        Initialize the metrics collector.
        
        Args:
            window_size_minutes: Time window for rolling metrics
        """
        self.window_size = timedelta(minutes=window_size_minutes)
        self._lock = threading.Lock()
        
        # Current metrics
        self.search_metrics = SearchMetrics()
        self.query_metrics = QueryMetrics()
        self.performance_metrics = PerformanceMetrics()
        
        # Time-based metrics storage
        self._time_series_data: Dict[str, deque] = defaultdict(
            lambda: deque(maxlen=300)  # 5 minutes of per-second data
        )
        
        # Histogram buckets for response time distribution
        self._response_time_buckets = [10, 25, 50, 100, 250, 500, 1000, 2500, 5000, 10000]
        self._response_time_histogram = defaultdict(int)
        
        # Start time for uptime calculation
        self._start_time = time.time()
        
        # Error tracking
        self._error_counts: Dict[str, int] = defaultdict(int)
        self._last_error_time: Dict[str, float] = {}
        
    def record_search_request(
        self,
        query: str,
        success: bool,
        processing_time_ms: float,
        query_variants_count: int,
        results_count: int,
        unique_results_count: int,
        tokenization_time_ms: float,
        search_time_ms: float,
        ranking_time_ms: float,
        cache_hit: bool = False,
        error_type: Optional[str] = None
    ) -> None:
        """
        Record metrics for a single search request.
        
        Args:
            query: Original search query
            success: Whether the search succeeded
            processing_time_ms: Total processing time
            query_variants_count: Number of query variants generated
            results_count: Total results returned
            unique_results_count: Unique results after deduplication
            tokenization_time_ms: Time spent on tokenization
            search_time_ms: Time spent on search execution
            ranking_time_ms: Time spent on ranking
            cache_hit: Whether results were served from cache
            error_type: Type of error if search failed
        """
        with self._lock:
            timestamp = time.time()
            
            # Update search metrics
            self.search_metrics.total_searches += 1
            if success:
                self.search_metrics.successful_searches += 1
            else:
                self.search_metrics.failed_searches += 1
                if error_type:
                    self._error_counts[error_type] += 1
                    self._last_error_time[error_type] = timestamp
            
            self.search_metrics.total_query_variants += query_variants_count
            self.search_metrics.total_results_returned += results_count
            self.search_metrics.total_unique_results += unique_results_count
            self.search_metrics.total_processing_time_ms += processing_time_ms
            
            # Component timing
            self.search_metrics.tokenization_time_ms += tokenization_time_ms
            self.search_metrics.search_execution_time_ms += search_time_ms
            self.search_metrics.ranking_time_ms += ranking_time_ms
            
            # Cache metrics
            if cache_hit:
                self.search_metrics.cache_hits += 1
            else:
                self.search_metrics.cache_misses += 1
            
            # Update performance metrics
            self.performance_metrics.response_times.append(processing_time_ms)
            
            # Update histogram
            for bucket in self._response_time_buckets:
                if processing_time_ms <= bucket:
                    self._response_time_histogram[bucket] += 1
                    break
            else:
                self._response_time_histogram['inf'] += 1
            
            # Record time series data
            self._time_series_data['searches_per_second'].append((timestamp, 1))
            self._time_series_data['response_time_ms'].append((timestamp, processing_time_ms))
            
            # Log detailed metrics for monitoring
            logger.debug(
                "Search request metrics recorded",
                extra={
                    "query_length": len(query),
                    "success": success,
                    "processing_time_ms": processing_time_ms,
                    "query_variants": query_variants_count,
                    "results_count": results_count,
                    "unique_results": unique_results_count,
                    "cache_hit": cache_hit,
                    "error_type": error_type
                }
            )
    
    def record_query_processing(
        self,
        query: str,
        language_detected: str,
        tokenization_success: bool,
        variants_generated: int,
        fallback_used: bool,
        compound_words_found: int = 0
    ) -> None:
        """
        Record metrics for query processing operations.
        
        Args:
            query: Original query text
            language_detected: Detected language (thai/english/mixed)
            tokenization_success: Whether tokenization succeeded
            variants_generated: Number of query variants generated
            fallback_used: Whether fallback tokenization was used
            compound_words_found: Number of compound words detected
        """
        with self._lock:
            self.query_metrics.total_queries_processed += 1
            
            # Language detection
            if language_detected == "thai":
                self.query_metrics.thai_queries += 1
            elif language_detected == "english":
                self.query_metrics.english_queries += 1
            elif language_detected == "mixed":
                self.query_metrics.mixed_queries += 1
            
            # Tokenization metrics
            if tokenization_success:
                self.query_metrics.tokenization_successes += 1
            else:
                self.query_metrics.tokenization_failures += 1
            
            if fallback_used:
                self.query_metrics.fallback_used += 1
            
            # Query variants
            self.query_metrics.total_variants_generated += variants_generated
            if self.query_metrics.total_queries_processed > 0:
                self.query_metrics.avg_variants_per_query = (
                    self.query_metrics.total_variants_generated / 
                    self.query_metrics.total_queries_processed
                )
            
            # Compound word detection
            if compound_words_found > 0:
                self.query_metrics.compound_words_detected += 1
                self.query_metrics.compound_word_splits += compound_words_found
    
    def record_batch_search(
        self,
        batch_size: int,
        successful_queries: int,
        failed_queries: int,
        total_processing_time_ms: float
    ) -> None:
        """
        Record metrics for batch search operations.
        
        Args:
            batch_size: Number of queries in batch
            successful_queries: Number of successful queries
            failed_queries: Number of failed queries
            total_processing_time_ms: Total batch processing time
        """
        with self._lock:
            # Record as individual searches
            self.search_metrics.total_searches += batch_size
            self.search_metrics.successful_searches += successful_queries
            self.search_metrics.failed_searches += failed_queries
            
            # Record batch-specific metrics
            self._time_series_data['batch_searches'].append((time.time(), 1))
            self._time_series_data['batch_size'].append((time.time(), batch_size))
            self._time_series_data['batch_processing_time_ms'].append(
                (time.time(), total_processing_time_ms)
            )
    
    def update_active_searches(self, delta: int) -> None:
        """
        Update the count of active concurrent searches.
        
        Args:
            delta: Change in active searches (+1 for start, -1 for end)
        """
        with self._lock:
            self.performance_metrics.active_searches += delta
            if self.performance_metrics.active_searches > self.performance_metrics.peak_concurrent_searches:
                self.performance_metrics.peak_concurrent_searches = self.performance_metrics.active_searches
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """
        Get a summary of all collected metrics.
        
        Returns:
            Dictionary containing metrics summary
        """
        with self._lock:
            # Calculate derived metrics
            success_rate = (
                self.search_metrics.successful_searches / self.search_metrics.total_searches * 100
                if self.search_metrics.total_searches > 0 else 100.0
            )
            
            avg_response_time = (
                self.search_metrics.total_processing_time_ms / self.search_metrics.total_searches
                if self.search_metrics.total_searches > 0 else 0.0
            )
            
            cache_hit_rate = (
                self.search_metrics.cache_hits / 
                (self.search_metrics.cache_hits + self.search_metrics.cache_misses) * 100
                if (self.search_metrics.cache_hits + self.search_metrics.cache_misses) > 0 else 0.0
            )
            
            # Calculate percentiles
            response_times = list(self.performance_metrics.response_times)
            percentiles = self._calculate_percentiles(response_times, [50, 75, 90, 95, 99])
            
            # Calculate throughput
            throughput = self._calculate_throughput()
            
            return {
                "uptime_seconds": time.time() - self._start_time,
                "search_metrics": {
                    "total_searches": self.search_metrics.total_searches,
                    "successful_searches": self.search_metrics.successful_searches,
                    "failed_searches": self.search_metrics.failed_searches,
                    "success_rate_percent": success_rate,
                    "total_query_variants": self.search_metrics.total_query_variants,
                    "total_results_returned": self.search_metrics.total_results_returned,
                    "total_unique_results": self.search_metrics.total_unique_results,
                    "avg_response_time_ms": avg_response_time,
                    "cache_hit_rate_percent": cache_hit_rate
                },
                "query_metrics": {
                    "total_queries_processed": self.query_metrics.total_queries_processed,
                    "thai_queries": self.query_metrics.thai_queries,
                    "english_queries": self.query_metrics.english_queries,
                    "mixed_queries": self.query_metrics.mixed_queries,
                    "tokenization_success_rate": (
                        self.query_metrics.tokenization_successes / 
                        self.query_metrics.total_queries_processed * 100
                        if self.query_metrics.total_queries_processed > 0 else 100.0
                    ),
                    "avg_variants_per_query": self.query_metrics.avg_variants_per_query,
                    "fallback_usage_percent": (
                        self.query_metrics.fallback_used / 
                        self.query_metrics.total_queries_processed * 100
                        if self.query_metrics.total_queries_processed > 0 else 0.0
                    )
                },
                "performance_metrics": {
                    "response_time_percentiles_ms": percentiles,
                    "requests_per_second": throughput['requests_per_second'],
                    "active_searches": self.performance_metrics.active_searches,
                    "peak_concurrent_searches": self.performance_metrics.peak_concurrent_searches
                },
                "component_timing": {
                    "avg_tokenization_time_ms": (
                        self.search_metrics.tokenization_time_ms / self.search_metrics.total_searches
                        if self.search_metrics.total_searches > 0 else 0.0
                    ),
                    "avg_search_execution_time_ms": (
                        self.search_metrics.search_execution_time_ms / self.search_metrics.total_searches
                        if self.search_metrics.total_searches > 0 else 0.0
                    ),
                    "avg_ranking_time_ms": (
                        self.search_metrics.ranking_time_ms / self.search_metrics.total_searches
                        if self.search_metrics.total_searches > 0 else 0.0
                    )
                },
                "error_metrics": {
                    "error_counts": dict(self._error_counts),
                    "last_error_times": {
                        error_type: datetime.fromtimestamp(timestamp).isoformat()
                        for error_type, timestamp in self._last_error_time.items()
                    }
                }
            }
    
    def get_prometheus_metrics(self) -> List[str]:
        """
        Get metrics in Prometheus exposition format.
        
        Returns:
            List of metric lines in Prometheus format
        """
        metrics = []
        summary = self.get_metrics_summary()
        
        # Search metrics
        metrics.extend([
            f'# HELP search_proxy_total_searches Total number of search requests',
            f'# TYPE search_proxy_total_searches counter',
            f'search_proxy_total_searches {summary["search_metrics"]["total_searches"]}',
            '',
            f'# HELP search_proxy_successful_searches Total number of successful searches',
            f'# TYPE search_proxy_successful_searches counter',
            f'search_proxy_successful_searches {summary["search_metrics"]["successful_searches"]}',
            '',
            f'# HELP search_proxy_failed_searches Total number of failed searches',
            f'# TYPE search_proxy_failed_searches counter',
            f'search_proxy_failed_searches {summary["search_metrics"]["failed_searches"]}',
            '',
            f'# HELP search_proxy_success_rate_percent Search success rate percentage',
            f'# TYPE search_proxy_success_rate_percent gauge',
            f'search_proxy_success_rate_percent {summary["search_metrics"]["success_rate_percent"]:.2f}',
            '',
            f'# HELP search_proxy_avg_response_time_ms Average response time in milliseconds',
            f'# TYPE search_proxy_avg_response_time_ms gauge',
            f'search_proxy_avg_response_time_ms {summary["search_metrics"]["avg_response_time_ms"]:.2f}',
            '',
            f'# HELP search_proxy_cache_hit_rate_percent Cache hit rate percentage',
            f'# TYPE search_proxy_cache_hit_rate_percent gauge',
            f'search_proxy_cache_hit_rate_percent {summary["search_metrics"]["cache_hit_rate_percent"]:.2f}',
            ''
        ])
        
        # Query processing metrics
        metrics.extend([
            f'# HELP search_proxy_queries_by_language Queries processed by language',
            f'# TYPE search_proxy_queries_by_language counter',
            f'search_proxy_queries_by_language{{language="thai"}} {summary["query_metrics"]["thai_queries"]}',
            f'search_proxy_queries_by_language{{language="english"}} {summary["query_metrics"]["english_queries"]}',
            f'search_proxy_queries_by_language{{language="mixed"}} {summary["query_metrics"]["mixed_queries"]}',
            '',
            f'# HELP search_proxy_tokenization_success_rate Tokenization success rate percentage',
            f'# TYPE search_proxy_tokenization_success_rate gauge',
            f'search_proxy_tokenization_success_rate {summary["query_metrics"]["tokenization_success_rate"]:.2f}',
            ''
        ])
        
        # Performance metrics
        percentiles = summary["performance_metrics"]["response_time_percentiles_ms"]
        for p, value in percentiles.items():
            metrics.extend([
                f'# HELP search_proxy_response_time_p{p}_ms {p}th percentile response time',
                f'# TYPE search_proxy_response_time_p{p}_ms gauge',
                f'search_proxy_response_time_p{p}_ms {value:.2f}',
                ''
            ])
        
        metrics.extend([
            f'# HELP search_proxy_requests_per_second Current requests per second',
            f'# TYPE search_proxy_requests_per_second gauge',
            f'search_proxy_requests_per_second {summary["performance_metrics"]["requests_per_second"]:.2f}',
            '',
            f'# HELP search_proxy_active_searches Currently active searches',
            f'# TYPE search_proxy_active_searches gauge',
            f'search_proxy_active_searches {summary["performance_metrics"]["active_searches"]}',
            ''
        ])
        
        # Component timing
        timing = summary["component_timing"]
        metrics.extend([
            f'# HELP search_proxy_avg_tokenization_time_ms Average tokenization time',
            f'# TYPE search_proxy_avg_tokenization_time_ms gauge',
            f'search_proxy_avg_tokenization_time_ms {timing["avg_tokenization_time_ms"]:.2f}',
            '',
            f'# HELP search_proxy_avg_search_execution_time_ms Average search execution time',
            f'# TYPE search_proxy_avg_search_execution_time_ms gauge',
            f'search_proxy_avg_search_execution_time_ms {timing["avg_search_execution_time_ms"]:.2f}',
            '',
            f'# HELP search_proxy_avg_ranking_time_ms Average ranking time',
            f'# TYPE search_proxy_avg_ranking_time_ms gauge',
            f'search_proxy_avg_ranking_time_ms {timing["avg_ranking_time_ms"]:.2f}',
            ''
        ])
        
        # Error metrics
        error_counts = summary["error_metrics"]["error_counts"]
        if error_counts:
            metrics.extend([
                f'# HELP search_proxy_errors_by_type Total errors by type',
                f'# TYPE search_proxy_errors_by_type counter'
            ])
            for error_type, count in error_counts.items():
                metrics.append(f'search_proxy_errors_by_type{{type="{error_type}"}} {count}')
            metrics.append('')
        
        return metrics
    
    def _calculate_percentiles(self, data: List[float], percentiles: List[int]) -> Dict[int, float]:
        """Calculate percentiles from a list of values."""
        if not data:
            return {p: 0.0 for p in percentiles}
        
        sorted_data = sorted(data)
        result = {}
        
        for p in percentiles:
            index = int(len(sorted_data) * p / 100)
            if index >= len(sorted_data):
                index = len(sorted_data) - 1
            result[p] = sorted_data[index]
        
        return result
    
    def _calculate_throughput(self) -> Dict[str, float]:
        """Calculate current throughput metrics."""
        current_time = time.time()
        window_start = current_time - 60  # 1 minute window
        
        # Count requests in the last minute
        recent_searches = sum(
            1 for timestamp, _ in self._time_series_data['searches_per_second']
            if timestamp >= window_start
        )
        
        requests_per_second = recent_searches / 60.0 if recent_searches > 0 else 0.0
        
        return {
            'requests_per_second': requests_per_second
        }
    
    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        with self._lock:
            self.search_metrics = SearchMetrics()
            self.query_metrics = QueryMetrics()
            self.performance_metrics = PerformanceMetrics()
            self._time_series_data.clear()
            self._response_time_histogram.clear()
            self._error_counts.clear()
            self._last_error_time.clear()
            logger.info("Search proxy metrics reset")


# Global metrics collector instance
metrics_collector = SearchProxyMetricsCollector()