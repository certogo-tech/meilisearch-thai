#!/usr/bin/env python3
"""
Comprehensive functional testing for Thai tokenizer system.
"""

import requests
import json
from typing import Dict, Any, List

BASE_URL = "http://localhost:8001"
MEILISEARCH_URL = "http://localhost:7700"
API_KEY = "masterKey"

def test_endpoint(name: str, method: str, url: str, data: Dict = None, headers: Dict = None) -> bool:
    """Test an API endpoint and return success status."""
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers)
        elif method.upper() == "POST":
            response = requests.post(url, json=data, headers=headers)
        else:
            print(f"  ❌ {name}: Unsupported method {method}")
            return False
        
        if response.status_code == 200:
            result = response.json()
            print(f"  ✅ {name}: SUCCESS (Status: {response.status_code})")
            return True
        else:
            print(f"  ❌ {name}: FAILED (Status: {response.status_code})")
            return False
    except Exception as e:
        print(f"  ❌ {name}: ERROR - {str(e)}")
        return False

def run_functional_tests():
    """Run comprehensive functional tests."""
    print("🧪 Starting Thai Tokenizer Functional Tests")
    print("=" * 60)
    
    passed_tests = 0
    total_tests = 0
    
    # Test 1: Health Check
    print("\n🏥 Health Check Tests")
    total_tests += 1
    if test_endpoint("Basic Health Check", "GET", f"{BASE_URL}/health"):
        passed_tests += 1
    
    total_tests += 1
    if test_endpoint("Detailed Health Check", "GET", f"{BASE_URL}/api/v1/health/detailed"):
        passed_tests += 1
    
    # Test 2: Tokenization Tests
    print("\n📝 Tokenization Tests")
    
    # Basic tokenization
    total_tests += 1
    if test_endpoint(
        "Basic Thai Tokenization",
        "POST",
        f"{BASE_URL}/api/v1/tokenize",
        {"text": "รถยนต์ไฟฟ้าเป็นเทคโนโลยีใหม่", "engine": "pythainlp"}
    ):
        passed_tests += 1
    
    # Compound word tokenization
    total_tests += 1
    if test_endpoint(
        "Compound Word Tokenization",
        "POST",
        f"{BASE_URL}/api/v1/tokenize/compound",
        {"text": "โรงเรียนมัธยมศึกษา", "engine": "pythainlp"}
    ):
        passed_tests += 1
    
    # Mixed content tokenization
    total_tests += 1
    if test_endpoint(
        "Mixed Content Tokenization",
        "POST",
        f"{BASE_URL}/api/v1/tokenize",
        {"text": "AI และ Machine Learning เป็นเทคโนโลยีใหม่", "engine": "pythainlp"}
    ):
        passed_tests += 1
    
    # Test 3: Query Processing Tests
    print("\n🔍 Query Processing Tests")
    
    total_tests += 1
    if test_endpoint(
        "Basic Query Processing",
        "POST",
        f"{BASE_URL}/api/v1/query/process",
        {"query": "รถยนต์ไฟฟ้า", "index_name": "documents"}
    ):
        passed_tests += 1
    
    total_tests += 1
    if test_endpoint(
        "Compound Query Processing",
        "POST",
        f"{BASE_URL}/api/v1/query/compound",
        {"query": "โรงเรียนมัธยมศึกษา", "index_name": "documents"}
    ):
        passed_tests += 1
    
    # Test 4: Document Processing Tests
    print("\n📚 Document Processing Tests")
    
    total_tests += 1
    if test_endpoint(
        "Single Document Indexing",
        "POST",
        f"{BASE_URL}/api/v1/index-document",
        {
            "id": "func-test-1",
            "title": "การทดสอบระบบ",
            "content": "การทดสอบระบบโทเคนไนเซอร์ภาษาไทย",
            "metadata": {"category": "test"}
        }
    ):
        passed_tests += 1
    
    # Test 5: Search Enhancement Tests
    print("\n✨ Search Enhancement Tests")
    
    total_tests += 1
    if test_endpoint(
        "Search Result Enhancement",
        "POST",
        f"{BASE_URL}/api/v1/search/enhance",
        {
            "original_query": "รถยนต์",
            "search_results": {
                "hits": [
                    {
                        "id": "test-1",
                        "title": "รถยนต์ไฟฟ้า",
                        "content": "รถยนต์ไฟฟ้าเป็นเทคโนโลยีใหม่"
                    }
                ]
            },
            "highlight_fields": ["title", "content"]
        }
    ):
        passed_tests += 1
    
    # Test 6: Configuration Tests
    print("\n⚙️ Configuration Tests")
    
    total_tests += 1
    if test_endpoint("Get Configuration", "GET", f"{BASE_URL}/api/v1/config"):
        passed_tests += 1
    
    total_tests += 1
    if test_endpoint("Validate Configuration", "POST", f"{BASE_URL}/api/v1/config/validate", {}):
        passed_tests += 1
    
    # Test 7: Monitoring Tests
    print("\n📊 Monitoring Tests")
    
    total_tests += 1
    if test_endpoint("System Metrics", "GET", f"{BASE_URL}/api/v1/metrics/system"):
        passed_tests += 1
    
    total_tests += 1
    if test_endpoint("Tokenizer Metrics", "GET", f"{BASE_URL}/api/v1/metrics/tokenizer"):
        passed_tests += 1
    
    total_tests += 1
    if test_endpoint("Performance Metrics", "GET", f"{BASE_URL}/api/v1/metrics/performance"):
        passed_tests += 1
    
    # Test 8: Diagnostics Tests
    print("\n🔧 Diagnostics Tests")
    
    total_tests += 1
    if test_endpoint("System Diagnostics", "GET", f"{BASE_URL}/api/v1/diagnostics"):
        passed_tests += 1
    
    total_tests += 1
    if test_endpoint("Tokenization Diagnostics", "GET", f"{BASE_URL}/api/v1/diagnostics/tokenization"):
        passed_tests += 1
    
    # Test 9: MeiliSearch Integration Tests
    print("\n🔍 MeiliSearch Integration Tests")
    
    # Test direct MeiliSearch health
    total_tests += 1
    if test_endpoint(
        "MeiliSearch Health",
        "GET",
        f"{MEILISEARCH_URL}/health",
        headers={"Authorization": f"Bearer {API_KEY}"}
    ):
        passed_tests += 1
    
    # Test search functionality
    total_tests += 1
    if test_endpoint(
        "MeiliSearch Search",
        "POST",
        f"{MEILISEARCH_URL}/indexes/documents/search",
        {"q": "รถยนต์"},
        headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    ):
        passed_tests += 1
    
    # Test 10: Edge Cases and Error Handling
    print("\n🚨 Edge Cases and Error Handling Tests")
    
    # Empty text tokenization
    total_tests += 1
    if test_endpoint(
        "Empty Text Tokenization",
        "POST",
        f"{BASE_URL}/api/v1/tokenize",
        {"text": "", "engine": "pythainlp"}
    ):
        passed_tests += 1
    
    # Very long text tokenization
    long_text = "รถยนต์ไฟฟ้า" * 100  # 1000+ characters
    total_tests += 1
    if test_endpoint(
        "Long Text Tokenization",
        "POST",
        f"{BASE_URL}/api/v1/tokenize",
        {"text": long_text, "engine": "pythainlp"}
    ):
        passed_tests += 1
    
    # Special characters
    total_tests += 1
    if test_endpoint(
        "Special Characters Tokenization",
        "POST",
        f"{BASE_URL}/api/v1/tokenize",
        {"text": "รถยนต์@#$%^&*()ไฟฟ้า", "engine": "pythainlp"}
    ):
        passed_tests += 1
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 FUNCTIONAL TEST SUMMARY")
    print("=" * 60)
    
    success_rate = (passed_tests / total_tests) * 100
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if success_rate >= 90:
        print("\n🎉 EXCELLENT: System is highly functional!")
    elif success_rate >= 80:
        print("\n✅ GOOD: System is mostly functional with minor issues")
    elif success_rate >= 70:
        print("\n⚠️  FAIR: System has some functional issues")
    else:
        print("\n❌ POOR: System has significant functional issues")
    
    print("=" * 60)
    
    return success_rate >= 80

if __name__ == "__main__":
    run_functional_tests()