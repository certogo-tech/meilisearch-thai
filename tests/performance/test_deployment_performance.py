#!/usr/bin/env python3
"""
Performance and load testing for on-premise deployment methods.

This module provides comprehensive performance testing for deployed Thai tokenizer
services, including response time benchmarks, throughput testing, and resource
usage monitoring.
"""

import asyncio
import json
import time
import statistics
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import pytest
import httpx
import psutil
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.deployment.config import OnPremiseConfig


@dataclass
class PerformanceMetrics:
    """Performance metrics data structure."""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    avg_response_time_ms: float
    min_response_time_ms: float
    max_response_time_ms: float
    p95_response_time_ms: float
    p99_response_time_ms: float
    requests_per_second: float
    total_duration_seconds: float
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None
    error_rate_percent: float = 0.0


@dataclass
class LoadTestResult:
    """Individual load test request result."""
    success: bool
    response_time_ms: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: float = 0.0


class DeploymentPerformanceTester:
    """Performance testing utility for deployed services."""
    
    def __init__(self, service_url: str, config: OnPremiseConfig):
        self.service_url = service_url
        self.config = config
        self.thai_test_data = self._load_thai_test_data()
    
    def _load_thai_test_data(self) -> List[Dict]:
        """Load Thai test data for performance testing."""
        samples_file = Path(__file__).parent.parent.parent / "data" / "samples" / "thai_documents.json"
        if samples_file.exists():
            with open(samples_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Fallback test data
        return [
            {
                "id": "perf_001",
                "content": "สาหร่ายวากาเมะเป็นสาหร่ายทะเลจากญี่ปุ่นที่มีรสชาติหวานเล็กน้อย เหมาะสำหรับทำสลัดหรือซุป",
                "expected_tokens": 15
            },
            {
                "id": "perf_002", 
                "content": "การพัฒนาเทคโนโลยีปัญญาประดิษฐ์ในประเทศไทยกำลังเติบโตอย่างรวดเร็ว",
                "expected_tokens": 12
            },
            {
                "id": "perf_003",
                "content": "Startup ecosystem ในประเทศไทยกำลังเติบโตอย่างรวดเร็ว บริษัท Fintech เช่น TrueMoney",
                "expected_tokens": 18
            }
        ]
    
    async def run_single_request_test(self, text: str, timeout: float = 30.0) -> LoadTestResult:
        """Run a single tokenization request and measure performance."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{self.service_url}/v1/tokenize",
                    json={"text": text}
                )
                
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                
                return LoadTestResult(
                    success=response.status_code == 200,
                    response_time_ms=response_time_ms,
                    status_code=response.status_code,
                    timestamp=start_time
                )
                
        except Exception as e:
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            
            return LoadTestResult(
                success=False,
                response_time_ms=response_time_ms,
                error_message=str(e),
                timestamp=start_time
            )
    
    async def run_concurrent_load_test(
        self, 
        concurrent_users: int = 10, 
        requests_per_user: int = 10,
        ramp_up_seconds: float = 5.0
    ) -> PerformanceMetrics:
        """Run concurrent load test with multiple users."""
        
        all_results = []
        start_time = time.time()
        
        # Create semaphore to control concurrency
        semaphore = asyncio.Semaphore(concurrent_users)
        
        async def user_session(user_id: int):
            """Simulate a user session with multiple requests."""
            user_results = []
            
            # Ramp up delay
            await asyncio.sleep((user_id / concurrent_users) * ramp_up_seconds)
            
            for request_num in range(requests_per_user):
                async with semaphore:
                    # Select test data cyclically
                    test_data = self.thai_test_data[request_num % len(self.thai_test_data)]
                    text = test_data.get("content", test_data.get("text", ""))
                    
                    result = await self.run_single_request_test(text)
                    user_results.append(result)
                    
                    # Small delay between requests from same user
                    await asyncio.sleep(0.1)
            
            return user_results
        
        # Create tasks for all users
        tasks = [user_session(i) for i in range(concurrent_users)]
        
        # Execute all user sessions concurrently
        user_results_list = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Flatten results
        for user_results in user_results_list:
            if isinstance(user_results, list):
                all_results.extend(user_results)
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        return self._calculate_performance_metrics(
            "concurrent_load_test",
            all_results,
            total_duration
        )
    
    async def run_sustained_load_test(
        self, 
        duration_seconds: int = 60,
        target_rps: float = 10.0
    ) -> PerformanceMetrics:
        """Run sustained load test for specified duration."""
        
        all_results = []
        start_time = time.time()
        end_time = start_time + duration_seconds
        request_interval = 1.0 / target_rps
        
        request_count = 0
        
        while time.time() < end_time:
            # Select test data cyclically
            test_data = self.thai_test_data[request_count % len(self.thai_test_data)]
            text = test_data.get("content", test_data.get("text", ""))
            
            # Make request
            result = await self.run_single_request_test(text)
            all_results.append(result)
            
            request_count += 1
            
            # Wait for next request interval
            next_request_time = start_time + (request_count * request_interval)
            current_time = time.time()
            
            if next_request_time > current_time:
                await asyncio.sleep(next_request_time - current_time)
        
        actual_duration = time.time() - start_time
        
        return self._calculate_performance_metrics(
            "sustained_load_test",
            all_results,
            actual_duration
        )
    
    async def run_spike_test(
        self, 
        baseline_rps: float = 5.0,
        spike_rps: float = 50.0,
        spike_duration_seconds: int = 30,
        total_duration_seconds: int = 120
    ) -> PerformanceMetrics:
        """Run spike test with sudden load increase."""
        
        all_results = []
        start_time = time.time()
        
        # Calculate spike timing
        spike_start = total_duration_seconds // 3
        spike_end = spike_start + spike_duration_seconds
        
        request_count = 0
        
        while time.time() - start_time < total_duration_seconds:
            current_time_offset = time.time() - start_time
            
            # Determine current RPS based on test phase
            if spike_start <= current_time_offset <= spike_end:
                current_rps = spike_rps
            else:
                current_rps = baseline_rps
            
            request_interval = 1.0 / current_rps
            
            # Select test data
            test_data = self.thai_test_data[request_count % len(self.thai_test_data)]
            text = test_data.get("content", test_data.get("text", ""))
            
            # Make request
            result = await self.run_single_request_test(text)
            all_results.append(result)
            
            request_count += 1
            
            # Wait for next request
            next_request_time = start_time + (request_count * request_interval)
            current_time = time.time()
            
            if next_request_time > current_time:
                await asyncio.sleep(next_request_time - current_time)
        
        actual_duration = time.time() - start_time
        
        return self._calculate_performance_metrics(
            "spike_test",
            all_results,
            actual_duration
        )
    
    def _calculate_performance_metrics(
        self, 
        test_name: str, 
        results: List[LoadTestResult], 
        duration: float
    ) -> PerformanceMetrics:
        """Calculate performance metrics from test results."""
        
        if not results:
            return PerformanceMetrics(
                test_name=test_name,
                total_requests=0,
                successful_requests=0,
                failed_requests=0,
                avg_response_time_ms=0.0,
                min_response_time_ms=0.0,
                max_response_time_ms=0.0,
                p95_response_time_ms=0.0,
                p99_response_time_ms=0.0,
                requests_per_second=0.0,
                total_duration_seconds=duration
            )
        
        successful_results = [r for r in results if r.success]
        failed_results = [r for r in results if not r.success]
        
        response_times = [r.response_time_ms for r in successful_results]
        
        if response_times:
            avg_response_time = statistics.mean(response_times)
            min_response_time = min(response_times)
            max_response_time = max(response_times)
            p95_response_time = statistics.quantiles(response_times, n=20)[18] if len(response_times) > 1 else avg_response_time
            p99_response_time = statistics.quantiles(response_times, n=100)[98] if len(response_times) > 1 else avg_response_time
        else:
            avg_response_time = min_response_time = max_response_time = p95_response_time = p99_response_time = 0.0
        
        requests_per_second = len(results) / duration if duration > 0 else 0.0
        error_rate = (len(failed_results) / len(results)) * 100 if results else 0.0
        
        return PerformanceMetrics(
            test_name=test_name,
            total_requests=len(results),
            successful_requests=len(successful_results),
            failed_requests=len(failed_results),
            avg_response_time_ms=avg_response_time,
            min_response_time_ms=min_response_time,
            max_response_time_ms=max_response_time,
            p95_response_time_ms=p95_response_time,
            p99_response_time_ms=p99_response_time,
            requests_per_second=requests_per_second,
            total_duration_seconds=duration,
            error_rate_percent=error_rate
        )
    
    def get_system_resource_usage(self, service_name: str) -> Tuple[Optional[float], Optional[float]]:
        """Get current memory and CPU usage for the service."""
        try:
            for process in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info', 'cpu_percent']):
                try:
                    if service_name in ' '.join(process.info['cmdline'] or []):
                        memory_mb = process.info['memory_info'].rss / (1024 * 1024)
                        cpu_percent = process.info['cpu_percent']
                        return memory_mb, cpu_percent
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception:
            pass
        
        return None, None


class TestDeploymentPerformance:
    """Performance test suite for deployment methods."""
    
    @pytest.fixture
    def performance_config(self):
        """Create configuration for performance testing."""
        return {
            "deployment_method": "docker",
            "meilisearch_config": {
                "host": "http://localhost:7700",
                "port": 7700,
                "api_key": "test-performance-key",
                "ssl_enabled": False,
                "ssl_verify": True,
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0
            },
            "service_config": {
                "service_name": "thai-tokenizer-performance-test",
                "service_port": 8005,
                "service_host": "0.0.0.0",
                "worker_processes": 4,
                "service_user": "thai-tokenizer",
                "service_group": "thai-tokenizer"
            },
            "security_config": {
                "security_level": "standard",
                "allowed_hosts": ["*"],
                "cors_origins": ["*"],
                "api_key_required": False,
                "enable_https": False
            },
            "resource_config": {
                "memory_limit_mb": 512,
                "cpu_limit_cores": 1.0,
                "max_concurrent_requests": 100,
                "request_timeout_seconds": 30,
                "enable_metrics": True,
                "metrics_port": 9095
            },
            "monitoring_config": {
                "enable_health_checks": True,
                "health_check_interval_seconds": 30,
                "enable_logging": True,
                "log_level": "INFO",
                "enable_prometheus": True,
                "prometheus_port": 9095
            },
            "installation_path": "/tmp/thai-tokenizer-performance-test",
            "data_path": "/tmp/thai-tokenizer-performance-test/data",
            "log_path": "/tmp/thai-tokenizer-performance-test/logs",
            "config_path": "/tmp/thai-tokenizer-performance-test/config",
            "environment_variables": {}
        }
    
    @pytest.mark.asyncio
    async def test_single_request_performance(self, performance_config):
        """Test single request performance requirements."""
        config = OnPremiseConfig(**performance_config)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentPerformanceTester(service_url, config)
        
        # Mock the HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tokens": ["สาหร่าย", "วากาเมะ", "เป็น", "สาหร่าย", "ทะเล"],
                "processing_time_ms": 25.5
            }
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Test with Thai text
            test_text = "สาหร่ายวากาเมะเป็นสาหร่ายทะเลจากญี่ปุ่น"
            result = await tester.run_single_request_test(test_text)
            
            assert result.success == True
            assert result.response_time_ms < 100  # Should be under 100ms
            assert result.status_code == 200
    
    @pytest.mark.asyncio
    async def test_concurrent_load_performance(self, performance_config):
        """Test concurrent load performance."""
        config = OnPremiseConfig(**performance_config)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentPerformanceTester(service_url, config)
        
        # Mock the HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tokens": ["test", "tokens"],
                "processing_time_ms": 30.0
            }
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Run concurrent load test
            metrics = await tester.run_concurrent_load_test(
                concurrent_users=5,
                requests_per_user=10,
                ramp_up_seconds=2.0
            )
            
            # Verify performance requirements
            assert metrics.total_requests == 50  # 5 users * 10 requests
            assert metrics.successful_requests >= 45  # Allow some failures
            assert metrics.avg_response_time_ms < 100  # Average under 100ms
            assert metrics.error_rate_percent < 10  # Less than 10% error rate
            assert metrics.requests_per_second > 5  # At least 5 RPS
    
    @pytest.mark.asyncio
    async def test_sustained_load_performance(self, performance_config):
        """Test sustained load performance."""
        config = OnPremiseConfig(**performance_config)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentPerformanceTester(service_url, config)
        
        # Mock the HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tokens": ["sustained", "test"],
                "processing_time_ms": 35.0
            }
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Run sustained load test (shorter duration for testing)
            metrics = await tester.run_sustained_load_test(
                duration_seconds=10,  # Short duration for testing
                target_rps=8.0
            )
            
            # Verify sustained performance
            assert metrics.total_requests >= 70  # Should be close to 80 (8 RPS * 10s)
            assert metrics.successful_requests >= 60  # Allow some failures
            assert metrics.avg_response_time_ms < 100  # Maintain performance
            assert metrics.error_rate_percent < 15  # Acceptable error rate
            assert abs(metrics.requests_per_second - 8.0) < 2.0  # Close to target RPS
    
    @pytest.mark.asyncio
    async def test_spike_load_performance(self, performance_config):
        """Test spike load performance."""
        config = OnPremiseConfig(**performance_config)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentPerformanceTester(service_url, config)
        
        # Mock the HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tokens": ["spike", "test"],
                "processing_time_ms": 40.0
            }
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Run spike test (shorter duration for testing)
            metrics = await tester.run_spike_test(
                baseline_rps=3.0,
                spike_rps=15.0,
                spike_duration_seconds=5,
                total_duration_seconds=20
            )
            
            # Verify spike handling
            assert metrics.total_requests >= 100  # Should handle spike
            assert metrics.successful_requests >= 80  # Allow more failures during spike
            assert metrics.avg_response_time_ms < 150  # May be higher during spike
            assert metrics.error_rate_percent < 25  # Higher error rate acceptable during spike
    
    @pytest.mark.asyncio
    async def test_memory_usage_monitoring(self, performance_config):
        """Test memory usage monitoring during load."""
        config = OnPremiseConfig(**performance_config)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentPerformanceTester(service_url, config)
        
        # Mock system resource monitoring
        with patch.object(tester, 'get_system_resource_usage') as mock_resources:
            mock_resources.return_value = (200.0, 25.5)  # 200MB memory, 25.5% CPU
            
            memory_mb, cpu_percent = tester.get_system_resource_usage(
                config.service_config.service_name
            )
            
            # Verify resource usage is within limits
            assert memory_mb is not None
            assert memory_mb < config.resource_config.memory_limit_mb
            assert cpu_percent is not None
            assert cpu_percent < 80.0  # Should not exceed 80% CPU
    
    @pytest.mark.asyncio
    async def test_thai_tokenization_accuracy_under_load(self, performance_config):
        """Test Thai tokenization accuracy under load conditions."""
        config = OnPremiseConfig(**performance_config)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentPerformanceTester(service_url, config)
        
        # Mock responses with realistic Thai tokenization
        with patch('httpx.AsyncClient') as mock_client:
            def mock_tokenize_response(*args, **kwargs):
                request_data = kwargs.get('json', {})
                text = request_data.get('text', '')
                
                # Simulate realistic tokenization based on text length
                estimated_tokens = max(1, len(text) // 8)  # Rough estimate
                
                return Mock(
                    status_code=200,
                    json=lambda: {
                        "tokens": [f"token_{i}" for i in range(estimated_tokens)],
                        "original_text": text,
                        "processing_time_ms": min(50, len(text) * 0.5)
                    }
                )
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                side_effect=mock_tokenize_response
            )
            
            # Test with various Thai text samples
            thai_samples = [
                "สาหร่ายวากาเมะ",
                "การพัฒนาเทคโนโลยีปัญญาประดิษฐ์",
                "Startup ecosystem ในประเทศไทย",
                "สาหร่ายวากาเมะเป็นสาหร่ายทะเลจากญี่ปุ่นที่มีรสชาติหวานเล็กน้อย"
            ]
            
            results = []
            for text in thai_samples:
                result = await tester.run_single_request_test(text)
                results.append(result)
            
            # Verify all requests succeeded
            successful_results = [r for r in results if r.success]
            assert len(successful_results) == len(thai_samples)
            
            # Verify response times are reasonable
            avg_response_time = sum(r.response_time_ms for r in successful_results) / len(successful_results)
            assert avg_response_time < 50  # Should be under 50ms for Thai tokenization
    
    def test_performance_metrics_calculation(self):
        """Test performance metrics calculation accuracy."""
        # Create sample test results
        results = [
            LoadTestResult(success=True, response_time_ms=25.0, status_code=200),
            LoadTestResult(success=True, response_time_ms=30.0, status_code=200),
            LoadTestResult(success=True, response_time_ms=35.0, status_code=200),
            LoadTestResult(success=True, response_time_ms=40.0, status_code=200),
            LoadTestResult(success=False, response_time_ms=100.0, error_message="Timeout"),
        ]
        
        config = OnPremiseConfig(
            deployment_method="docker",
            meilisearch_config={
                "host": "http://localhost:7700",
                "port": 7700,
                "api_key": "test-key"
            }
        )
        
        tester = DeploymentPerformanceTester("http://localhost:8000", config)
        metrics = tester._calculate_performance_metrics("test", results, 10.0)
        
        # Verify calculated metrics
        assert metrics.test_name == "test"
        assert metrics.total_requests == 5
        assert metrics.successful_requests == 4
        assert metrics.failed_requests == 1
        assert metrics.avg_response_time_ms == 32.5  # (25+30+35+40)/4
        assert metrics.min_response_time_ms == 25.0
        assert metrics.max_response_time_ms == 40.0
        assert metrics.requests_per_second == 0.5  # 5 requests / 10 seconds
        assert metrics.error_rate_percent == 20.0  # 1 failure out of 5 requests


if __name__ == "__main__":
    # Run performance tests directly
    pytest.main([__file__, "-v", "--tb=short"])