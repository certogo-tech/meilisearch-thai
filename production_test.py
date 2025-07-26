#!/usr/bin/env python3
"""
Production Setup Test Suite
Tests all aspects of the production deployment to ensure everything is working correctly.
"""

import requests
import json
import time
import sys
from typing import Dict, List, Any
from datetime import datetime

class ProductionTester:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.results = []
        self.failed_tests = []
        
    def log_test(self, test_name: str, success: bool, details: str = "", response_time: float = 0):
        """Log test result"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}")
        if details:
            print(f"    {details}")
        if response_time > 0:
            print(f"    Response time: {response_time:.2f}ms")
        
        self.results.append({
            "test": test_name,
            "success": success,
            "details": details,
            "response_time_ms": response_time,
            "timestamp": datetime.now().isoformat()
        })
        
        if not success:
            self.failed_tests.append(test_name)
    
    def test_basic_health(self):
        """Test basic health endpoint"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/health", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "healthy":
                    self.log_test("Basic Health Check", True, 
                                f"Status: {data.get('status')}, Uptime: {data.get('uptime_seconds')}s", 
                                response_time)
                else:
                    self.log_test("Basic Health Check", False, f"Unhealthy status: {data}")
            else:
                self.log_test("Basic Health Check", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Basic Health Check", False, f"Exception: {str(e)}")
    
    def test_detailed_health(self):
        """Test detailed health endpoint"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/v1/health/detailed", timeout=15)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                overall_status = data.get("overall_status")
                checks = data.get("checks", {})
                
                if overall_status == "healthy":
                    healthy_checks = sum(1 for check in checks.values() if check.get("status") == "healthy")
                    total_checks = len(checks)
                    self.log_test("Detailed Health Check", True, 
                                f"Overall: {overall_status}, Healthy checks: {healthy_checks}/{total_checks}", 
                                response_time)
                else:
                    self.log_test("Detailed Health Check", False, f"Overall status: {overall_status}")
            else:
                self.log_test("Detailed Health Check", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Detailed Health Check", False, f"Exception: {str(e)}")
    
    def test_tokenization(self):
        """Test basic tokenization"""
        try:
            test_text = "รถยนต์ไฟฟ้าเป็นเทคโนโลยีใหม่ที่น่าสนใจ"
            payload = {"text": test_text, "engine": "pythainlp"}
            
            start_time = time.time()
            response = requests.post(f"{self.base_url}/api/v1/tokenize", 
                                   json=payload, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                tokens = data.get("tokens", [])
                if len(tokens) > 0:
                    self.log_test("Basic Tokenization", True, 
                                f"Tokenized into {len(tokens)} tokens: {tokens[:3]}...", 
                                response_time)
                else:
                    self.log_test("Basic Tokenization", False, "No tokens returned")
            else:
                self.log_test("Basic Tokenization", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Basic Tokenization", False, f"Exception: {str(e)}")
    
    def test_compound_tokenization(self):
        """Test compound tokenization"""
        try:
            test_text = "รถยนต์ไฟฟ้า"
            payload = {"text": test_text, "engine": "pythainlp"}
            
            start_time = time.time()
            response = requests.post(f"{self.base_url}/api/v1/tokenize/compound", 
                                   json=payload, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                tokens = data.get("tokens", [])
                if len(tokens) >= 2:  # Should split compound word
                    self.log_test("Compound Tokenization", True, 
                                f"Split compound into {len(tokens)} tokens: {tokens}", 
                                response_time)
                else:
                    self.log_test("Compound Tokenization", False, f"Expected 2+ tokens, got {len(tokens)}")
            else:
                self.log_test("Compound Tokenization", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Compound Tokenization", False, f"Exception: {str(e)}")
    
    def test_query_processing(self):
        """Test query processing"""
        try:
            test_query = "รถยนต์ไฟฟ้า"
            payload = {"query": test_query, "engine": "pythainlp"}
            
            start_time = time.time()
            response = requests.post(f"{self.base_url}/api/v1/query/process", 
                                   json=payload, timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                query_tokens = data.get("query_tokens", [])
                search_variants = data.get("search_variants", [])
                
                if len(query_tokens) > 0 and len(search_variants) > 0:
                    self.log_test("Query Processing", True, 
                                f"Generated {len(query_tokens)} tokens, {len(search_variants)} variants", 
                                response_time)
                else:
                    self.log_test("Query Processing", False, "No query tokens or variants generated")
            else:
                self.log_test("Query Processing", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Query Processing", False, f"Exception: {str(e)}")
    
    def test_configuration(self):
        """Test configuration endpoint"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/v1/config", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                config = data.get("configuration", {})
                status = data.get("status")
                
                if status == "active" and config.get("tokenizer_engine"):
                    self.log_test("Configuration", True, 
                                f"Status: {status}, Engine: {config.get('tokenizer_engine')}", 
                                response_time)
                else:
                    self.log_test("Configuration", False, f"Invalid config status: {status}")
            else:
                self.log_test("Configuration", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("Configuration", False, f"Exception: {str(e)}")
    
    def test_metrics(self):
        """Test metrics endpoints"""
        try:
            # Test tokenizer metrics
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/v1/metrics/tokenizer", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                requests_data = data.get("requests", {})
                total_requests = requests_data.get("total", 0)
                
                if total_requests > 0:
                    self.log_test("Tokenizer Metrics", True, 
                                f"Total requests: {total_requests}, Success rate: {requests_data.get('success_rate', 0):.1f}%", 
                                response_time)
                else:
                    self.log_test("Tokenizer Metrics", True, "No requests yet (expected for fresh deployment)")
            else:
                self.log_test("Tokenizer Metrics", False, f"HTTP {response.status_code}")
                
            # Test system metrics
            start_time = time.time()
            response = requests.get(f"{self.base_url}/api/v1/metrics/system", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                cpu = data.get("cpu", {})
                memory = data.get("memory", {})
                
                self.log_test("System Metrics", True, 
                            f"CPU: {cpu.get('usage_percent', 0):.1f}%, Memory: {memory.get('usage_percent', 0):.1f}%", 
                            response_time)
            else:
                self.log_test("System Metrics", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_test("Metrics", False, f"Exception: {str(e)}")
    
    def test_api_documentation(self):
        """Test API documentation accessibility"""
        try:
            start_time = time.time()
            response = requests.get(f"{self.base_url}/docs", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200 and "swagger" in response.text.lower():
                self.log_test("API Documentation", True, "Swagger UI accessible", response_time)
            else:
                self.log_test("API Documentation", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("API Documentation", False, f"Exception: {str(e)}")
    
    def test_meilisearch_integration(self):
        """Test MeiliSearch integration"""
        try:
            # Test MeiliSearch health directly
            start_time = time.time()
            response = requests.get("http://localhost:7700/health", timeout=10)
            response_time = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "available":
                    self.log_test("MeiliSearch Health", True, "MeiliSearch is available", response_time)
                else:
                    self.log_test("MeiliSearch Health", False, f"Status: {data.get('status')}")
            else:
                self.log_test("MeiliSearch Health", False, f"HTTP {response.status_code}")
        except Exception as e:
            self.log_test("MeiliSearch Health", False, f"Exception: {str(e)}")
    
    def test_performance_benchmarks(self):
        """Test performance benchmarks"""
        try:
            # Test tokenization performance
            test_texts = [
                "รถยนต์ไฟฟ้า",
                "เทคโนโลยีใหม่ที่น่าสนใจมาก",
                "การพัฒนาระบบค้นหาภาษาไทยด้วย MeiliSearch และ PyThaiNLP"
            ]
            
            total_time = 0
            successful_requests = 0
            
            for text in test_texts:
                payload = {"text": text, "engine": "pythainlp"}
                start_time = time.time()
                response = requests.post(f"{self.base_url}/api/v1/tokenize", 
                                       json=payload, timeout=5)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    total_time += response_time
                    successful_requests += 1
            
            if successful_requests > 0:
                avg_time = total_time / successful_requests
                if avg_time < 100:  # Less than 100ms average
                    self.log_test("Performance Benchmark", True, 
                                f"Average response time: {avg_time:.2f}ms ({successful_requests} requests)")
                else:
                    self.log_test("Performance Benchmark", False, 
                                f"Average response time too high: {avg_time:.2f}ms")
            else:
                self.log_test("Performance Benchmark", False, "No successful requests")
                
        except Exception as e:
            self.log_test("Performance Benchmark", False, f"Exception: {str(e)}")
    
    def run_all_tests(self):
        """Run all production tests"""
        print("🚀 Starting Production Setup Tests")
        print("=" * 50)
        
        # Run all tests
        self.test_basic_health()
        self.test_detailed_health()
        self.test_meilisearch_integration()
        self.test_tokenization()
        self.test_compound_tokenization()
        self.test_query_processing()
        self.test_configuration()
        self.test_metrics()
        self.test_api_documentation()
        self.test_performance_benchmarks()
        
        # Summary
        print("\n" + "=" * 50)
        print("📊 Test Summary")
        print("=" * 50)
        
        total_tests = len(self.results)
        passed_tests = sum(1 for r in self.results if r["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests} ✅")
        print(f"Failed: {failed_tests} ❌")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if self.failed_tests:
            print(f"\n❌ Failed Tests:")
            for test in self.failed_tests:
                print(f"  - {test}")
        
        # Save detailed results
        with open("production_test_results.json", "w") as f:
            json.dump({
                "summary": {
                    "total_tests": total_tests,
                    "passed_tests": passed_tests,
                    "failed_tests": failed_tests,
                    "success_rate": (passed_tests/total_tests)*100,
                    "timestamp": datetime.now().isoformat()
                },
                "results": self.results
            }, f, indent=2)
        
        print(f"\n📄 Detailed results saved to: production_test_results.json")
        
        # Return success status
        return failed_tests == 0

if __name__ == "__main__":
    tester = ProductionTester()
    success = tester.run_all_tests()
    
    if success:
        print("\n🎉 All production tests passed! System is ready for deployment.")
        sys.exit(0)
    else:
        print("\n⚠️  Some tests failed. Please review and fix issues before deployment.")
        sys.exit(1)