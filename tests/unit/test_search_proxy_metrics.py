"""
Unit tests for the search proxy metrics collection.

Tests metrics recording, aggregation, and Prometheus format export.
"""

import pytest
import time
from datetime import datetime, timedelta

from src.search_proxy.metrics import (
    SearchProxyMetricsCollector,
    SearchMetrics,
    QueryMetrics,
    PerformanceMetrics
)


class TestSearchProxyMetricsCollector:
    """Test cases for the SearchProxyMetricsCollector."""
    
    @pytest.fixture
    def metrics_collector(self):
        """Create a metrics collector instance for testing."""
        return SearchProxyMetricsCollector(window_size_minutes=5)
    
    def test_initialization(self, metrics_collector):
        """Test metrics collector initialization."""
        assert isinstance(metrics_collector.search_metrics, SearchMetrics)
        assert isinstance(metrics_collector.query_metrics, QueryMetrics)
        assert isinstance(metrics_collector.performance_metrics, PerformanceMetrics)
        assert metrics_collector._start_time > 0
    
    def test_record_successful_search(self, metrics_collector):
        """Test recording metrics for a successful search."""
        metrics_collector.record_search_request(
            query="ค้นหาเอกสาร",
            success=True,
            processing_time_ms=50.0,
            query_variants_count=3,
            results_count=10,
            unique_results_count=8,
            tokenization_time_ms=10.0,
            search_time_ms=30.0,
            ranking_time_ms=10.0,
            cache_hit=False
        )
        
        assert metrics_collector.search_metrics.total_searches == 1
        assert metrics_collector.search_metrics.successful_searches == 1
        assert metrics_collector.search_metrics.failed_searches == 0
        assert metrics_collector.search_metrics.total_query_variants == 3
        assert metrics_collector.search_metrics.total_results_returned == 10
        assert metrics_collector.search_metrics.total_unique_results == 8
        assert metrics_collector.search_metrics.total_processing_time_ms == 50.0
        assert metrics_collector.search_metrics.tokenization_time_ms == 10.0
        assert metrics_collector.search_metrics.search_execution_time_ms == 30.0
        assert metrics_collector.search_metrics.ranking_time_ms == 10.0
        assert metrics_collector.search_metrics.cache_misses == 1
        assert metrics_collector.search_metrics.cache_hits == 0
    
    def test_record_failed_search(self, metrics_collector):
        """Test recording metrics for a failed search."""
        metrics_collector.record_search_request(
            query="test query",
            success=False,
            processing_time_ms=100.0,
            query_variants_count=0,
            results_count=0,
            unique_results_count=0,
            tokenization_time_ms=20.0,
            search_time_ms=0.0,
            ranking_time_ms=0.0,
            cache_hit=False,
            error_type="TokenizationError"
        )
        
        assert metrics_collector.search_metrics.total_searches == 1
        assert metrics_collector.search_metrics.successful_searches == 0
        assert metrics_collector.search_metrics.failed_searches == 1
        assert metrics_collector._error_counts["TokenizationError"] == 1
    
    def test_record_cache_hit(self, metrics_collector):
        """Test recording cache hit metrics."""
        metrics_collector.record_search_request(
            query="cached query",
            success=True,
            processing_time_ms=5.0,
            query_variants_count=2,
            results_count=5,
            unique_results_count=5,
            tokenization_time_ms=0.0,
            search_time_ms=0.0,
            ranking_time_ms=0.0,
            cache_hit=True
        )
        
        assert metrics_collector.search_metrics.cache_hits == 1
        assert metrics_collector.search_metrics.cache_misses == 0
    
    def test_record_query_processing(self, metrics_collector):
        """Test recording query processing metrics."""
        # Thai query
        metrics_collector.record_query_processing(
            query="ค้นหาเอกสาร",
            language_detected="thai",
            tokenization_success=True,
            variants_generated=3,
            fallback_used=False,
            compound_words_found=2
        )
        
        assert metrics_collector.query_metrics.total_queries_processed == 1
        assert metrics_collector.query_metrics.thai_queries == 1
        assert metrics_collector.query_metrics.english_queries == 0
        assert metrics_collector.query_metrics.mixed_queries == 0
        assert metrics_collector.query_metrics.tokenization_successes == 1
        assert metrics_collector.query_metrics.tokenization_failures == 0
        assert metrics_collector.query_metrics.fallback_used == 0
        assert metrics_collector.query_metrics.total_variants_generated == 3
        assert metrics_collector.query_metrics.avg_variants_per_query == 3.0
        assert metrics_collector.query_metrics.compound_words_detected == 1
        assert metrics_collector.query_metrics.compound_word_splits == 2
        
        # English query
        metrics_collector.record_query_processing(
            query="search documents",
            language_detected="english",
            tokenization_success=True,
            variants_generated=2,
            fallback_used=False
        )
        
        assert metrics_collector.query_metrics.total_queries_processed == 2
        assert metrics_collector.query_metrics.english_queries == 1
        assert metrics_collector.query_metrics.avg_variants_per_query == 2.5
        
        # Mixed language query with fallback
        metrics_collector.record_query_processing(
            query="ค้นหา documents",
            language_detected="mixed",
            tokenization_success=False,
            variants_generated=1,
            fallback_used=True
        )
        
        assert metrics_collector.query_metrics.total_queries_processed == 3
        assert metrics_collector.query_metrics.mixed_queries == 1
        assert metrics_collector.query_metrics.tokenization_failures == 1
        assert metrics_collector.query_metrics.fallback_used == 1
    
    def test_record_batch_search(self, metrics_collector):
        """Test recording batch search metrics."""
        metrics_collector.record_batch_search(
            batch_size=5,
            successful_queries=4,
            failed_queries=1,
            total_processing_time_ms=250.0
        )
        
        assert metrics_collector.search_metrics.total_searches == 5
        assert metrics_collector.search_metrics.successful_searches == 4
        assert metrics_collector.search_metrics.failed_searches == 1
    
    def test_update_active_searches(self, metrics_collector):
        """Test updating active search counter."""
        # Start searches
        metrics_collector.update_active_searches(1)
        assert metrics_collector.performance_metrics.active_searches == 1
        
        metrics_collector.update_active_searches(1)
        assert metrics_collector.performance_metrics.active_searches == 2
        assert metrics_collector.performance_metrics.peak_concurrent_searches == 2
        
        # End searches
        metrics_collector.update_active_searches(-1)
        assert metrics_collector.performance_metrics.active_searches == 1
        
        metrics_collector.update_active_searches(-1)
        assert metrics_collector.performance_metrics.active_searches == 0
        
        # Peak should remain at 2
        assert metrics_collector.performance_metrics.peak_concurrent_searches == 2
    
    def test_response_time_percentiles(self, metrics_collector):
        """Test response time percentile calculations."""
        # Record various response times
        response_times = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        
        for rt in response_times:
            metrics_collector.record_search_request(
                query="test",
                success=True,
                processing_time_ms=rt,
                query_variants_count=1,
                results_count=1,
                unique_results_count=1,
                tokenization_time_ms=5.0,
                search_time_ms=rt-10,
                ranking_time_ms=5.0,
                cache_hit=False
            )
        
        summary = metrics_collector.get_metrics_summary()
        percentiles = summary["performance_metrics"]["response_time_percentiles_ms"]
        
        assert percentiles[50] == 50  # Median
        assert percentiles[90] == 90  # 90th percentile
        assert percentiles[99] == 100  # 99th percentile
    
    def test_metrics_summary(self, metrics_collector):
        """Test comprehensive metrics summary generation."""
        # Record some searches
        for i in range(10):
            metrics_collector.record_search_request(
                query=f"query {i}",
                success=i < 8,  # 80% success rate
                processing_time_ms=50.0 + i * 10,
                query_variants_count=2,
                results_count=5,
                unique_results_count=4,
                tokenization_time_ms=10.0,
                search_time_ms=30.0,
                ranking_time_ms=10.0,
                cache_hit=i % 3 == 0  # 30% cache hit
            )
        
        summary = metrics_collector.get_metrics_summary()
        
        assert summary["uptime_seconds"] > 0
        assert summary["search_metrics"]["total_searches"] == 10
        assert summary["search_metrics"]["successful_searches"] == 8
        assert summary["search_metrics"]["failed_searches"] == 2
        assert summary["search_metrics"]["success_rate_percent"] == 80.0
        assert summary["search_metrics"]["avg_response_time_ms"] == 95.0  # Average of 50-140
        assert summary["search_metrics"]["cache_hit_rate_percent"] > 0
    
    def test_prometheus_metrics_format(self, metrics_collector):
        """Test Prometheus metrics format generation."""
        # Record some metrics
        metrics_collector.record_search_request(
            query="test query",
            success=True,
            processing_time_ms=50.0,
            query_variants_count=2,
            results_count=10,
            unique_results_count=8,
            tokenization_time_ms=10.0,
            search_time_ms=30.0,
            ranking_time_ms=10.0,
            cache_hit=False
        )
        
        prometheus_metrics = metrics_collector.get_prometheus_metrics()
        
        # Check format
        assert isinstance(prometheus_metrics, list)
        assert any("# HELP search_proxy_total_searches" in line for line in prometheus_metrics)
        assert any("# TYPE search_proxy_total_searches counter" in line for line in prometheus_metrics)
        assert any("search_proxy_total_searches 1" in line for line in prometheus_metrics)
        
        # Check various metric types
        assert any("search_proxy_successful_searches" in line for line in prometheus_metrics)
        assert any("search_proxy_success_rate_percent" in line for line in prometheus_metrics)
        assert any("search_proxy_avg_response_time_ms" in line for line in prometheus_metrics)
    
    def test_error_tracking(self, metrics_collector):
        """Test error type tracking and reporting."""
        error_types = ["TokenizationError", "SearchExecutionError", "TimeoutError", "TokenizationError"]
        
        for error_type in error_types:
            metrics_collector.record_search_request(
                query="failing query",
                success=False,
                processing_time_ms=100.0,
                query_variants_count=0,
                results_count=0,
                unique_results_count=0,
                tokenization_time_ms=0.0,
                search_time_ms=0.0,
                ranking_time_ms=0.0,
                cache_hit=False,
                error_type=error_type
            )
        
        summary = metrics_collector.get_metrics_summary()
        error_counts = summary["error_metrics"]["error_counts"]
        
        assert error_counts["TokenizationError"] == 2
        assert error_counts["SearchExecutionError"] == 1
        assert error_counts["TimeoutError"] == 1
        
        # Check last error times are recorded
        assert len(summary["error_metrics"]["last_error_times"]) == 3
    
    def test_reset_metrics(self, metrics_collector):
        """Test metrics reset functionality."""
        # Record some metrics
        metrics_collector.record_search_request(
            query="test",
            success=True,
            processing_time_ms=50.0,
            query_variants_count=2,
            results_count=5,
            unique_results_count=5,
            tokenization_time_ms=10.0,
            search_time_ms=30.0,
            ranking_time_ms=10.0,
            cache_hit=False
        )
        
        # Reset
        metrics_collector.reset_metrics()
        
        # Verify all metrics are reset
        assert metrics_collector.search_metrics.total_searches == 0
        assert metrics_collector.search_metrics.successful_searches == 0
        assert metrics_collector.query_metrics.total_queries_processed == 0
        assert metrics_collector.performance_metrics.active_searches == 0
        assert len(metrics_collector.performance_metrics.response_times) == 0
        assert len(metrics_collector._error_counts) == 0
    
    def test_throughput_calculation(self, metrics_collector):
        """Test throughput metrics calculation."""
        # Simulate searches over time
        current_time = time.time()
        
        # Mock time series data
        for i in range(60):  # 60 searches in last minute
            metrics_collector._time_series_data['searches_per_second'].append(
                (current_time - i, 1)
            )
        
        summary = metrics_collector.get_metrics_summary()
        
        # Should calculate ~1 request per second
        assert summary["performance_metrics"]["requests_per_second"] == pytest.approx(1.0, rel=0.1)
    
    def test_histogram_buckets(self, metrics_collector):
        """Test response time histogram buckets."""
        # Record searches with various response times
        response_times = [5, 15, 35, 75, 150, 350, 750, 1500, 3500, 7500, 15000]
        
        for rt in response_times:
            metrics_collector.record_search_request(
                query="test",
                success=True,
                processing_time_ms=rt,
                query_variants_count=1,
                results_count=1,
                unique_results_count=1,
                tokenization_time_ms=1.0,
                search_time_ms=rt-2,
                ranking_time_ms=1.0,
                cache_hit=False
            )
        
        # Check histogram buckets
        assert metrics_collector._response_time_histogram[10] == 1  # 5ms
        assert metrics_collector._response_time_histogram[25] == 1  # 15ms
        assert metrics_collector._response_time_histogram[50] == 1  # 35ms
        assert metrics_collector._response_time_histogram[100] == 1  # 75ms
        assert metrics_collector._response_time_histogram['inf'] == 1  # 15000ms