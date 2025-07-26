#!/usr/bin/env python3
"""
Manual performance testing for Thai tokenizer system.
"""

import time
import requests
import json
import statistics
from typing import List, Dict, Any

# Test configuration
BASE_URL = "http://localhost:8001"
MEILISEARCH_URL = "http://localhost:7700"
API_KEY = "masterKey"

# Test data
THAI_TEST_TEXTS = [
    "รถยนต์ไฟฟ้าเป็นเทคโนโลยีใหม่",
    "โรงเรียนมัธยมศึกษาเป็นสถาบันการศึกษา",
    "ปัญญาประดิษฐ์เป็นเทคโนโลยีที่สำคัญ",
    "ความรับผิดชอบเป็นคุณธรรมที่สำคัญ",
    "การศึกษาเป็นรากฐานของการพัฒนา",
    "เทคโนโลยีสารสนเทศเป็นเครื่องมือสำคัญ",
    "การแพทย์แผนไทยเป็นภูมิปัญญาท้องถิน",
    "อุตสาหกรรมการท่องเที่ยวเป็นรายได้สำคัญ",
    "การเกษตรอินทรีย์เป็นเทรนด์ใหม่",
    "พลังงานทดแทนเป็นทางเลือกที่ยั่งยืน"
]

def measure_time(func):
    """Decorator to measure execution time."""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        return result, (end_time - start_time) * 1000  # Return result and time in ms
    return wrapper

@measure_time
def test_tokenization(text: str) -> Dict[str, Any]:
    """Test tokenization performance."""
    response = requests.post(
        f"{BASE_URL}/api/v1/tokenize",
        json={"text": text, "engine": "pythainlp"},
        headers={"Content-Type": "application/json"}
    )
    return response.json()

@measure_time
def test_query_processing(query: str) -> Dict[str, Any]:
    """Test query processing performance."""
    response = requests.post(
        f"{BASE_URL}/api/v1/query/process",
        json={"query": query, "index_name": "documents"},
        headers={"Content-Type": "application/json"}
    )
    return response.json()

@measure_time
def test_document_indexing(doc_id: str, title: str, content: str) -> Dict[str, Any]:
    """Test document indexing performance."""
    response = requests.post(
        f"{BASE_URL}/api/v1/index-document",
        json={
            "id": doc_id,
            "title": title,
            "content": content,
            "metadata": {"category": "test"}
        },
        headers={"Content-Type": "application/json"}
    )
    return response.json()

@measure_time
def test_search(query: str) -> Dict[str, Any]:
    """Test search performance."""
    response = requests.post(
        f"{MEILISEARCH_URL}/indexes/documents/search",
        json={"q": query},
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
    )
    return response.json()

def run_performance_tests():
    """Run comprehensive performance tests."""
    print("🚀 Starting Thai Tokenizer Performance Tests")
    print("=" * 60)
    
    # Test 1: Tokenization Performance
    print("\n📝 Testing Tokenization Performance...")
    tokenization_times = []
    
    for i, text in enumerate(THAI_TEST_TEXTS):
        try:
            result, duration = test_tokenization(text)
            tokenization_times.append(duration)
            print(f"  Text {i+1}: {duration:.2f}ms - {len(result.get('tokens', []))} tokens")
        except Exception as e:
            print(f"  Text {i+1}: ERROR - {e}")
    
    if tokenization_times:
        print(f"\n  📊 Tokenization Stats:")
        print(f"    Average: {statistics.mean(tokenization_times):.2f}ms")
        print(f"    Median:  {statistics.median(tokenization_times):.2f}ms")
        print(f"    Min:     {min(tokenization_times):.2f}ms")
        print(f"    Max:     {max(tokenization_times):.2f}ms")
        print(f"    Target:  < 50ms ({'✅ PASS' if max(tokenization_times) < 50 else '❌ FAIL'})")
    
    # Test 2: Query Processing Performance
    print("\n🔍 Testing Query Processing Performance...")
    query_times = []
    
    for i, query in enumerate(THAI_TEST_TEXTS[:5]):  # Test first 5 as queries
        try:
            result, duration = test_query_processing(query)
            query_times.append(duration)
            print(f"  Query {i+1}: {duration:.2f}ms - {len(result.get('query_tokens', []))} tokens")
        except Exception as e:
            print(f"  Query {i+1}: ERROR - {e}")
    
    if query_times:
        print(f"\n  📊 Query Processing Stats:")
        print(f"    Average: {statistics.mean(query_times):.2f}ms")
        print(f"    Median:  {statistics.median(query_times):.2f}ms")
        print(f"    Target:  < 100ms ({'✅ PASS' if max(query_times) < 100 else '❌ FAIL'})")
    
    # Test 3: Document Indexing Performance
    print("\n📚 Testing Document Indexing Performance...")
    indexing_times = []
    
    for i, text in enumerate(THAI_TEST_TEXTS[:5]):  # Test first 5 for indexing
        try:
            result, duration = test_document_indexing(f"perf-test-{i}", f"Test {i+1}", text)
            indexing_times.append(duration)
            print(f"  Doc {i+1}: {duration:.2f}ms - Status: {result.get('status', 'unknown')}")
        except Exception as e:
            print(f"  Doc {i+1}: ERROR - {e}")
    
    if indexing_times:
        print(f"\n  📊 Document Indexing Stats:")
        print(f"    Average: {statistics.mean(indexing_times):.2f}ms")
        print(f"    Median:  {statistics.median(indexing_times):.2f}ms")
        print(f"    Target:  < 200ms ({'✅ PASS' if max(indexing_times) < 200 else '❌ FAIL'})")
    
    # Test 4: Search Performance
    print("\n🔎 Testing Search Performance...")
    search_times = []
    search_queries = ["รถยนต์", "ไฟฟ้า", "โรงเรียน", "ปัญญาประดิษฐ์", "เทคโนโลยี"]
    
    for i, query in enumerate(search_queries):
        try:
            result, duration = test_search(query)
            search_times.append(duration)
            hits = len(result.get('hits', []))
            print(f"  Search {i+1} ('{query}'): {duration:.2f}ms - {hits} hits")
        except Exception as e:
            print(f"  Search {i+1}: ERROR - {e}")
    
    if search_times:
        print(f"\n  📊 Search Performance Stats:")
        print(f"    Average: {statistics.mean(search_times):.2f}ms")
        print(f"    Median:  {statistics.median(search_times):.2f}ms")
        print(f"    Target:  < 100ms ({'✅ PASS' if max(search_times) < 100 else '❌ FAIL'})")
    
    # Test 5: System Health Check
    print("\n🏥 Testing System Health...")
    try:
        health_result, health_time = test_health()
        print(f"  Health Check: {health_time:.2f}ms - Status: {health_result.get('status', 'unknown')}")
        
        if health_result.get('status') == 'healthy':
            deps = health_result.get('dependencies', {})
            print(f"    MeiliSearch: {deps.get('meilisearch', 'unknown')}")
            print(f"    Tokenizer: {deps.get('tokenizer', 'unknown')}")
            print(f"    System Resources: {deps.get('system_resources', 'unknown')}")
            print(f"    Dependencies: {deps.get('dependencies', 'unknown')}")
    except Exception as e:
        print(f"  Health Check: ERROR - {e}")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 PERFORMANCE TEST SUMMARY")
    print("=" * 60)
    
    all_tests_passed = True
    
    if tokenization_times and max(tokenization_times) < 50:
        print("✅ Tokenization Performance: PASS")
    else:
        print("❌ Tokenization Performance: FAIL")
        all_tests_passed = False
    
    if query_times and max(query_times) < 100:
        print("✅ Query Processing Performance: PASS")
    else:
        print("❌ Query Processing Performance: FAIL")
        all_tests_passed = False
    
    if indexing_times and max(indexing_times) < 200:
        print("✅ Document Indexing Performance: PASS")
    else:
        print("❌ Document Indexing Performance: FAIL")
        all_tests_passed = False
    
    if search_times and max(search_times) < 100:
        print("✅ Search Performance: PASS")
    else:
        print("❌ Search Performance: FAIL")
        all_tests_passed = False
    
    print("\n" + ("🎉 ALL TESTS PASSED!" if all_tests_passed else "⚠️  SOME TESTS FAILED"))
    print("=" * 60)

@measure_time
def test_health() -> Dict[str, Any]:
    """Test system health."""
    response = requests.get(f"{BASE_URL}/health")
    return response.json()

if __name__ == "__main__":
    run_performance_tests()