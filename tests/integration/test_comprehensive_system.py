#!/usr/bin/env python3
"""
Comprehensive System Integration Tests for Thai Tokenizer

This module provides comprehensive integration testing for the Thai Tokenizer system,
testing all endpoints, functionality, and performance characteristics.

Usage:
    python3 tests/integration/test_comprehensive_system.py

Requirements:
    - Thai Tokenizer service running on localhost:8001
    - MeiliSearch service running on localhost:7700
    - requests library installed
"""

import requests
import json
import time
from typing import Dict, Any

BASE_URL = "http://localhost:8001"

def test_health_check():
    """Test service health"""
    print("🏥 Testing Health Check...")
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Service Status: {data['status']}")
        print(f"✅ Version: {data['version']}")
        print(f"✅ Uptime: {data['uptime_seconds']} seconds")
        print(f"✅ Dependencies: {data['dependencies']}")
        return True
    else:
        print(f"❌ Health check failed: {response.status_code}")
        return False

def test_tokenization():
    """Test Thai tokenization with various text types"""
    print("\n🔤 Testing Thai Tokenization...")
    
    test_cases = [
        {
            "name": "Simple compound words",
            "text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"
        },
        {
            "name": "Mixed Thai-English",
            "text": "การพัฒนา AI และ Machine Learning ในประเทศไทย"
        },
        {
            "name": "Technical terms",
            "text": "เทคโนโลยีสารสนเทศและการสื่อสารดิจิทัล"
        },
        {
            "name": "Formal language",
            "text": "การประชุมคณะกรรมการบริหารจัดการองค์กร"
        },
        {
            "name": "Numbers and punctuation",
            "text": "ราคา 1,500 บาท (รวม VAT 7%)"
        }
    ]
    
    results = []
    for test_case in test_cases:
        print(f"\n📝 Testing: {test_case['name']}")
        print(f"Input: {test_case['text']}")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/tokenize",
            json={"text": test_case['text']},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            tokens = data['tokens']
            processing_time = data['processing_time_ms']
            
            print(f"✅ Tokens ({len(tokens)}): {tokens}")
            print(f"✅ Processing time: {processing_time}ms")
            
            results.append({
                "test": test_case['name'],
                "success": True,
                "token_count": len(tokens),
                "processing_time": processing_time
            })
        else:
            print(f"❌ Tokenization failed: {response.status_code}")
            results.append({
                "test": test_case['name'],
                "success": False,
                "error": response.status_code
            })
    
    return results

def test_query_processing():
    """Test query processing functionality"""
    print("\n🔍 Testing Query Processing...")
    
    queries = [
        "ปัญญาประดิษฐ์",
        "การเรียนรู้",
        "AI และ ML",
        "เทคโนโลยี"
    ]
    
    results = []
    for query in queries:
        print(f"\n🔎 Processing query: {query}")
        
        response = requests.post(
            f"{BASE_URL}/api/v1/query/process",
            json={
                "query": query,
                "options": {
                    "expand_compounds": True,
                    "enable_partial_matching": True
                }
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            tokens = data['query_tokens']
            variants = data['search_variants']
            
            print(f"✅ Query tokens: {len(tokens)}")
            print(f"✅ Search variants: {len(variants)}")
            print(f"✅ Processing time: {data['processing_metadata']['processing_time_ms']:.2f}ms")
            
            results.append({
                "query": query,
                "success": True,
                "token_count": len(tokens),
                "variant_count": len(variants)
            })
        else:
            print(f"❌ Query processing failed: {response.status_code}")
            results.append({
                "query": query,
                "success": False,
                "error": response.status_code
            })
    
    return results

def test_configuration():
    """Test configuration endpoints"""
    print("\n⚙️ Testing Configuration...")
    
    response = requests.get(f"{BASE_URL}/api/v1/config")
    if response.status_code == 200:
        data = response.json()
        config = data['configuration']
        
        print(f"✅ Service: {config['service_name']} v{config['version']}")
        print(f"✅ Tokenizer Engine: {config['tokenizer_engine']}")
        print(f"✅ MeiliSearch Host: {config['meilisearch_host']}")
        print(f"✅ Batch Size: {config['processing_batch_size']}")
        print(f"✅ Configuration Valid: {config['validation_report']['valid']}")
        
        return True
    else:
        print(f"❌ Configuration test failed: {response.status_code}")
        return False

def test_meilisearch_connection():
    """Test MeiliSearch connection"""
    print("\n🔗 Testing MeiliSearch Connection...")
    
    try:
        response = requests.get("http://localhost:7700/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MeiliSearch Status: {data['status']}")
            return True
        else:
            print(f"❌ MeiliSearch connection failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ MeiliSearch connection error: {e}")
        return False

def performance_benchmark():
    """Run performance benchmarks"""
    print("\n⚡ Running Performance Benchmarks...")
    
    # Test with increasing text lengths
    test_texts = [
        "ปัญญาประดิษฐ์",  # Short
        "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่องในยุคดิจิทัล",  # Medium
        "การพัฒนาเทคโนโลยีปัญญาประดิษฐ์และการเรียนรู้ของเครื่องในประเทศไทยเป็นสิ่งสำคัญสำหรับการเติบโตทางเศรษฐกิจและสังคมในอนาคต เทคโนโลยีเหล่านี้จะช่วยเพิ่มประสิทธิภาพในการทำงานและสร้างนวัตกรรมใหม่ๆ"  # Long
    ]
    
    results = []
    for i, text in enumerate(test_texts):
        text_length = len(text)
        print(f"\n📊 Benchmark {i+1}: {text_length} characters")
        
        # Run multiple times for average
        times = []
        for _ in range(5):
            start_time = time.time()
            response = requests.post(
                f"{BASE_URL}/api/v1/tokenize",
                json={"text": text},
                headers={"Content-Type": "application/json"}
            )
            end_time = time.time()
            
            if response.status_code == 200:
                data = response.json()
                api_time = data['processing_time_ms']
                total_time = (end_time - start_time) * 1000
                times.append({"api": api_time, "total": total_time})
        
        if times:
            avg_api_time = sum(t["api"] for t in times) / len(times)
            avg_total_time = sum(t["total"] for t in times) / len(times)
            
            print(f"✅ Average API processing: {avg_api_time:.2f}ms")
            print(f"✅ Average total time: {avg_total_time:.2f}ms")
            print(f"✅ Characters per second: {text_length / (avg_api_time / 1000):.0f}")
            
            results.append({
                "text_length": text_length,
                "avg_api_time": avg_api_time,
                "avg_total_time": avg_total_time,
                "chars_per_second": text_length / (avg_api_time / 1000)
            })
    
    return results

def main():
    """Run all tests"""
    print("🚀 Thai Tokenizer Comprehensive Testing")
    print("=" * 50)
    
    # Test results summary
    test_results = {
        "health_check": False,
        "meilisearch_connection": False,
        "tokenization_tests": [],
        "query_processing_tests": [],
        "configuration_test": False,
        "performance_benchmarks": []
    }
    
    # Run tests
    test_results["health_check"] = test_health_check()
    test_results["meilisearch_connection"] = test_meilisearch_connection()
    test_results["tokenization_tests"] = test_tokenization()
    test_results["query_processing_tests"] = test_query_processing()
    test_results["configuration_test"] = test_configuration()
    test_results["performance_benchmarks"] = performance_benchmark()
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 TEST SUMMARY")
    print("=" * 50)
    
    print(f"Health Check: {'✅ PASS' if test_results['health_check'] else '❌ FAIL'}")
    print(f"MeiliSearch Connection: {'✅ PASS' if test_results['meilisearch_connection'] else '❌ FAIL'}")
    print(f"Configuration: {'✅ PASS' if test_results['configuration_test'] else '❌ FAIL'}")
    
    # Tokenization summary
    tokenization_success = sum(1 for t in test_results['tokenization_tests'] if t['success'])
    tokenization_total = len(test_results['tokenization_tests'])
    print(f"Tokenization Tests: ✅ {tokenization_success}/{tokenization_total} PASS")
    
    # Query processing summary
    query_success = sum(1 for t in test_results['query_processing_tests'] if t['success'])
    query_total = len(test_results['query_processing_tests'])
    print(f"Query Processing Tests: ✅ {query_success}/{query_total} PASS")
    
    # Performance summary
    if test_results['performance_benchmarks']:
        avg_speed = sum(b['chars_per_second'] for b in test_results['performance_benchmarks']) / len(test_results['performance_benchmarks'])
        print(f"Average Processing Speed: ⚡ {avg_speed:.0f} chars/second")
    
    print("\n🎉 Testing Complete!")
    
    # Save results to file
    with open('test_results.json', 'w', encoding='utf-8') as f:
        json.dump(test_results, f, indent=2, ensure_ascii=False)
    print("📄 Detailed results saved to test_results.json")

if __name__ == "__main__":
    main()