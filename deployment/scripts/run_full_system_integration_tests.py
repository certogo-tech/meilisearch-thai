#!/usr/bin/env python3
"""
Full system integration test runner for Thai tokenizer MeiliSearch integration.

This script runs comprehensive integration tests covering:
- Complete workflow from document ingestion to search results
- Error handling and recovery procedures
- Performance benchmark validation
- System reliability and resilience testing

Requirements covered: 3.1, 3.2, 3.3, 3.5
"""

import asyncio
import json
import logging
import sys
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import subprocess
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Test result data structure."""
    test_name: str
    status: str  # "PASS", "FAIL", "SKIP"
    duration_seconds: float
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class IntegrationTestReport:
    """Integration test report data structure."""
    timestamp: int
    total_tests: int
    passed_tests: int
    failed_tests: int
    skipped_tests: int
    total_duration_seconds: float
    success_rate: float
    test_results: List[TestResult]
    system_info: Dict[str, Any]
    performance_summary: Dict[str, Any]


class FullSystemIntegrationTestRunner:
    """Runner for full system integration tests."""
    
    def __init__(self):
        """Initialize test runner."""
        self.project_root = Path(__file__).parent.parent
        self.test_results: List[TestResult] = []
        self.start_time = time.time()
        
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information for the test report."""
        try:
            import psutil
            import platform
            
            return {
                "platform": platform.platform(),
                "python_version": sys.version,
                "cpu_count": psutil.cpu_count(),
                "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
                "disk_free_gb": round(psutil.disk_usage('/').free / (1024**3), 2)
            }
        except ImportError:
            return {
                "platform": "unknown",
                "python_version": sys.version,
                "note": "psutil not available for detailed system info"
            }
    
    def run_pytest_tests(self, test_file: str, test_class: str = None, 
                        test_method: str = None) -> TestResult:
        """Run specific pytest tests and capture results."""
        test_path = self.project_root / test_file
        
        # Build pytest command
        cmd = ["python", "-m", "pytest", str(test_path), "-v", "--tb=short"]
        
        if test_class:
            if test_method:
                cmd.append(f"-k {test_class} and {test_method}")
            else:
                cmd.append(f"-k {test_class}")
        
        test_name = f"{test_file}"
        if test_class:
            test_name += f"::{test_class}"
        if test_method:
            test_name += f"::{test_method}"
        
        logger.info(f"Running test: {test_name}")
        
        start_time = time.time()
        
        try:
            # Run pytest and capture output
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                return TestResult(
                    test_name=test_name,
                    status="PASS",
                    duration_seconds=duration,
                    details={"stdout": result.stdout}
                )
            else:
                return TestResult(
                    test_name=test_name,
                    status="FAIL",
                    duration_seconds=duration,
                    error_message=result.stderr,
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status="FAIL",
                duration_seconds=duration,
                error_message="Test timed out after 5 minutes"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name=test_name,
                status="FAIL",
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def run_benchmark_tests(self) -> TestResult:
        """Run performance benchmark tests."""
        logger.info("Running performance benchmark tests")
        
        benchmark_script = self.project_root / "scripts" / "benchmark.py"
        
        start_time = time.time()
        
        try:
            # Run benchmark script
            result = subprocess.run(
                ["python", str(benchmark_script)],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout for benchmarks
            )
            
            duration = time.time() - start_time
            
            if result.returncode == 0:
                return TestResult(
                    test_name="Performance Benchmarks",
                    status="PASS",
                    duration_seconds=duration,
                    details={"stdout": result.stdout}
                )
            else:
                return TestResult(
                    test_name="Performance Benchmarks",
                    status="FAIL",
                    duration_seconds=duration,
                    error_message=result.stderr,
                    details={"stdout": result.stdout, "stderr": result.stderr}
                )
                
        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            return TestResult(
                test_name="Performance Benchmarks",
                status="FAIL",
                duration_seconds=duration,
                error_message="Benchmark tests timed out after 10 minutes"
            )
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name="Performance Benchmarks",
                status="FAIL",
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def run_api_integration_tests(self) -> TestResult:
        """Run API integration tests."""
        logger.info("Running API integration tests")
        
        # Test API endpoints if service is running
        import httpx
        
        start_time = time.time()
        
        try:
            # Test health endpoint
            with httpx.Client(timeout=10.0) as client:
                health_response = client.get("http://localhost:8000/health")
                
                if health_response.status_code == 200:
                    # Test tokenization endpoint
                    tokenize_response = client.post(
                        "http://localhost:8000/api/v1/tokenize",
                        json={"text": "เทคโนโลยีสารสนเทศ", "engine": "newmm"}
                    )
                    
                    duration = time.time() - start_time
                    
                    if tokenize_response.status_code == 200:
                        return TestResult(
                            test_name="API Integration Tests",
                            status="PASS",
                            duration_seconds=duration,
                            details={
                                "health_status": health_response.json(),
                                "tokenize_result": tokenize_response.json()
                            }
                        )
                    else:
                        return TestResult(
                            test_name="API Integration Tests",
                            status="FAIL",
                            duration_seconds=duration,
                            error_message=f"Tokenization API failed: {tokenize_response.status_code}"
                        )
                else:
                    duration = time.time() - start_time
                    return TestResult(
                        test_name="API Integration Tests",
                        status="FAIL",
                        duration_seconds=duration,
                        error_message=f"Health check failed: {health_response.status_code}"
                    )
                    
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name="API Integration Tests",
                status="SKIP",
                duration_seconds=duration,
                error_message=f"API service not available: {str(e)}"
            )
    
    def run_docker_integration_tests(self) -> TestResult:
        """Run Docker container integration tests."""
        logger.info("Running Docker integration tests")
        
        start_time = time.time()
        
        try:
            # Check if Docker is available
            docker_check = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if docker_check.returncode != 0:
                duration = time.time() - start_time
                return TestResult(
                    test_name="Docker Integration Tests",
                    status="SKIP",
                    duration_seconds=duration,
                    error_message="Docker not available"
                )
            
            # Check if docker-compose is available
            compose_check = subprocess.run(
                ["docker", "compose", "version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if compose_check.returncode != 0:
                duration = time.time() - start_time
                return TestResult(
                    test_name="Docker Integration Tests",
                    status="SKIP",
                    duration_seconds=duration,
                    error_message="Docker Compose not available"
                )
            
            # Test docker-compose configuration
            compose_config = subprocess.run(
                ["docker", "compose", "config"],
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            duration = time.time() - start_time
            
            if compose_config.returncode == 0:
                return TestResult(
                    test_name="Docker Integration Tests",
                    status="PASS",
                    duration_seconds=duration,
                    details={"compose_config": "Valid"}
                )
            else:
                return TestResult(
                    test_name="Docker Integration Tests",
                    status="FAIL",
                    duration_seconds=duration,
                    error_message=compose_config.stderr
                )
                
        except Exception as e:
            duration = time.time() - start_time
            return TestResult(
                test_name="Docker Integration Tests",
                status="FAIL",
                duration_seconds=duration,
                error_message=str(e)
            )
    
    def extract_performance_summary(self) -> Dict[str, Any]:
        """Extract performance summary from test results."""
        performance_summary = {
            "tokenization_performance": "unknown",
            "search_performance": "unknown",
            "indexing_performance": "unknown",
            "memory_usage": "unknown",
            "overall_performance": "unknown"
        }
        
        # Look for performance test results
        for result in self.test_results:
            if "Performance" in result.test_name and result.status == "PASS":
                performance_summary["overall_performance"] = "meets_requirements"
            elif "Benchmark" in result.test_name and result.status == "PASS":
                performance_summary["overall_performance"] = "meets_requirements"
        
        return performance_summary
    
    def generate_report(self) -> IntegrationTestReport:
        """Generate comprehensive test report."""
        total_duration = time.time() - self.start_time
        
        passed_tests = sum(1 for r in self.test_results if r.status == "PASS")
        failed_tests = sum(1 for r in self.test_results if r.status == "FAIL")
        skipped_tests = sum(1 for r in self.test_results if r.status == "SKIP")
        total_tests = len(self.test_results)
        
        success_rate = passed_tests / total_tests if total_tests > 0 else 0
        
        return IntegrationTestReport(
            timestamp=int(time.time()),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            total_duration_seconds=total_duration,
            success_rate=success_rate,
            test_results=self.test_results,
            system_info=self.get_system_info(),
            performance_summary=self.extract_performance_summary()
        )
    
    def print_report(self, report: IntegrationTestReport) -> None:
        """Print detailed test report."""
        print("\n" + "=" * 80)
        print("FULL SYSTEM INTEGRATION TEST REPORT")
        print("=" * 80)
        print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(report.timestamp))}")
        print(f"Total Duration: {report.total_duration_seconds:.2f} seconds")
        print(f"Success Rate: {report.success_rate:.1%}")
        print()
        
        print("TEST SUMMARY")
        print("-" * 40)
        print(f"Total Tests: {report.total_tests}")
        print(f"Passed: {report.passed_tests}")
        print(f"Failed: {report.failed_tests}")
        print(f"Skipped: {report.skipped_tests}")
        print()
        
        print("SYSTEM INFORMATION")
        print("-" * 40)
        for key, value in report.system_info.items():
            print(f"{key.replace('_', ' ').title()}: {value}")
        print()
        
        print("PERFORMANCE SUMMARY")
        print("-" * 40)
        for key, value in report.performance_summary.items():
            status = "✓" if value == "meets_requirements" else "?" if value == "unknown" else "✗"
            print(f"{status} {key.replace('_', ' ').title()}: {value}")
        print()
        
        print("DETAILED TEST RESULTS")
        print("-" * 40)
        for result in report.test_results:
            status_symbol = "✓" if result.status == "PASS" else "✗" if result.status == "FAIL" else "⚠"
            print(f"{status_symbol} {result.test_name} ({result.duration_seconds:.2f}s) - {result.status}")
            
            if result.error_message:
                print(f"    Error: {result.error_message}")
        
        print("\n" + "=" * 80)
        
        # Overall assessment
        if report.success_rate >= 0.9:
            print("🎉 EXCELLENT: System integration tests passed with high success rate!")
        elif report.success_rate >= 0.7:
            print("✅ GOOD: System integration tests mostly passed, minor issues detected.")
        elif report.success_rate >= 0.5:
            print("⚠️  WARNING: System integration tests show significant issues.")
        else:
            print("❌ CRITICAL: System integration tests failed, major issues detected.")
        
        print("=" * 80)
    
    def save_report(self, report: IntegrationTestReport, filename: str = "integration_test_report.json") -> None:
        """Save test report to JSON file."""
        report_path = self.project_root / filename
        
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(report), f, indent=2, default=str)
        
        logger.info(f"Integration test report saved to {report_path}")
    
    async def run_all_tests(self) -> IntegrationTestReport:
        """Run all full system integration tests."""
        logger.info("Starting full system integration test suite")
        logger.info("=" * 60)
        
        # Test categories to run
        test_categories = [
            {
                "name": "Full System Workflow Tests",
                "test_file": "tests/integration/test_full_system_integration.py",
                "test_class": "TestFullSystemWorkflow"
            },
            {
                "name": "Error Handling and Recovery Tests",
                "test_file": "tests/integration/test_full_system_integration.py",
                "test_class": "TestErrorHandlingAndRecovery"
            },
            {
                "name": "Performance Benchmark Tests",
                "test_file": "tests/integration/test_full_system_integration.py",
                "test_class": "TestPerformanceBenchmarks"
            },
            {
                "name": "System Integration Validation Tests",
                "test_file": "tests/integration/test_full_system_integration.py",
                "test_class": "TestSystemIntegrationValidation"
            },
            {
                "name": "End-to-End Document Processing Tests",
                "test_file": "tests/integration/test_end_to_end.py",
                "test_class": "TestEndToEndDocumentProcessing"
            },
            {
                "name": "End-to-End Search Scenario Tests",
                "test_file": "tests/integration/test_end_to_end.py",
                "test_class": "TestEndToEndSearchScenarios"
            },
            {
                "name": "End-to-End Performance Tests",
                "test_file": "tests/integration/test_end_to_end.py",
                "test_class": "TestEndToEndPerformance"
            },
            {
                "name": "MeiliSearch Integration Tests",
                "test_file": "tests/integration/test_meilisearch_integration.py"
            }
        ]
        
        # Run each test category
        for category in test_categories:
            try:
                result = self.run_pytest_tests(
                    category["test_file"],
                    category.get("test_class")
                )
                result.test_name = category["name"]
                self.test_results.append(result)
                
            except Exception as e:
                logger.error(f"Failed to run {category['name']}: {e}")
                self.test_results.append(TestResult(
                    test_name=category["name"],
                    status="FAIL",
                    duration_seconds=0,
                    error_message=str(e)
                ))
        
        # Run additional integration tests
        additional_tests = [
            self.run_benchmark_tests,
            self.run_api_integration_tests,
            self.run_docker_integration_tests
        ]
        
        for test_func in additional_tests:
            try:
                result = test_func()
                self.test_results.append(result)
            except Exception as e:
                logger.error(f"Failed to run {test_func.__name__}: {e}")
                self.test_results.append(TestResult(
                    test_name=test_func.__name__.replace('run_', '').replace('_', ' ').title(),
                    status="FAIL",
                    duration_seconds=0,
                    error_message=str(e)
                ))
        
        # Generate and return report
        report = self.generate_report()
        
        logger.info("Full system integration test suite completed")
        logger.info(f"Results: {report.passed_tests}/{report.total_tests} tests passed ({report.success_rate:.1%})")
        
        return report


async def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Run full system integration tests")
    parser.add_argument("--output", "-o", default="integration_test_report.json",
                       help="Output file for test report")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Enable verbose output")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run integration tests
    runner = FullSystemIntegrationTestRunner()
    report = await runner.run_all_tests()
    
    # Print and save report
    runner.print_report(report)
    runner.save_report(report, args.output)
    
    # Exit with appropriate code
    if report.success_rate >= 0.8:
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure


if __name__ == "__main__":
    asyncio.run(main())