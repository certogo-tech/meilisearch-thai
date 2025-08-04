#!/usr/bin/env python3
"""
Load testing for Thai Search Proxy system.
"""

import asyncio
import aiohttp
import time
import statistics
from typing import List, Dict, Any
import json
import argparse

BASE_URL = "http://localhost:8000"

# Test queries for search
THAI_QUERIES = [
    # Simple words
    "ข้าว",
    "มะพร้าว",
    "สาหร่าย",
    
    # Compound words
    "สาหร่ายวากาเมะ",
    "คอมพิวเตอร์",
    "อินเทอร์เน็ต",
    
    # Phrases
    "การเกษตรแบบยั่งยืน",
    "เทคโนโลยีการเพาะปลูก",
    "น้ำมันมะพร้าวบริสุทธิ์",
    "พลังงานทดแทน",
    
    # Mixed language
    "Smart Farm",
    "IoT เกษตร",
    "Precision Agriculture"
]

async def search_request(session: aiohttp.ClientSession, query: str, request_id: int, api_key: str = None) -> Dict[str, Any]:
    """Make a single search request."""
    start_time = time.time()
    
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    
    try:
        async with session.post(
            f"{BASE_URL}/api/v1/search",
            json={
                "query": query,
                "index_name": "research",
                "options": {
                    "limit": 10,
                    "offset": 0
                }
            },
            headers=headers
        ) as response:
            result = await response.json()
            end_time = time.time()
            
            return {
                "request_id": request_id,
                "status": "success",
                "response_time": (end_time - start_time) * 1000,
                "status_code": response.status,
                "total_hits": result.get("total_hits", 0),
                "processing_time_ms": result.get("processing_time_ms", 0),
                "query_length": len(query)
            }
    except Exception as e:
        end_time = time.time()
        return {
            "request_id": request_id,
            "status": "error",
            "response_time": (end_time - start_time) * 1000,
            "error": str(e),
            "query_length": len(query)
        }

async def run_concurrent_requests(num_requests: int, concurrency: int, api_key: str = None) -> List[Dict[str, Any]]:
    """Run concurrent search requests."""
    print(f"🚀 Running {num_requests} requests with {concurrency} concurrent connections...")
    
    connector = aiohttp.TCPConnector(limit=concurrency)
    timeout = aiohttp.ClientTimeout(total=30)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        tasks = []
        
        for i in range(num_requests):
            query = THAI_QUERIES[i % len(THAI_QUERIES)]
            task = search_request(session, query, i, api_key)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter out exceptions and convert to proper results
        valid_results = []
        for result in results:
            if isinstance(result, dict):
                valid_results.append(result)
            else:
                valid_results.append({
                    "request_id": len(valid_results),
                    "status": "exception",
                    "response_time": 0,
                    "error": str(result)
                })
        
        return valid_results

def analyze_results(results: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze load test results."""
    successful_requests = [r for r in results if r["status"] == "success"]
    failed_requests = [r for r in results if r["status"] != "success"]
    
    if not successful_requests:
        return {
            "total_requests": len(results),
            "successful_requests": 0,
            "failed_requests": len(failed_requests),
            "success_rate": 0.0,
            "error": "No successful requests"
        }
    
    response_times = [r["response_time"] for r in successful_requests]
    
    return {
        "total_requests": len(results),
        "successful_requests": len(successful_requests),
        "failed_requests": len(failed_requests),
        "success_rate": (len(successful_requests) / len(results)) * 100,
        "response_times": {
            "mean": statistics.mean(response_times),
            "median": statistics.median(response_times),
            "min": min(response_times),
            "max": max(response_times),
            "p95": sorted(response_times)[int(len(response_times) * 0.95)] if len(response_times) > 20 else max(response_times),
            "p99": sorted(response_times)[int(len(response_times) * 0.99)] if len(response_times) > 100 else max(response_times)
        },
        "throughput": {
            "requests_per_second": len(successful_requests) / (max(response_times) / 1000) if response_times else 0,
            "total_hits": sum(r.get("total_hits", 0) for r in successful_requests),
            "avg_processing_time": statistics.mean([r.get("processing_time_ms", 0) for r in successful_requests]) if successful_requests else 0
        }
    }

async def run_load_tests(api_key: str = None):
    """Run comprehensive load tests."""
    print("⚡ Starting Thai Search Proxy Load Tests")
    print("=" * 60)
    
    test_scenarios = [
        {"name": "Light Load", "requests": 10, "concurrency": 2},
        {"name": "Medium Load", "requests": 50, "concurrency": 5},
        {"name": "Heavy Load", "requests": 100, "concurrency": 10},
        {"name": "Stress Test", "requests": 200, "concurrency": 20}
    ]
    
    all_results = {}
    
    for scenario in test_scenarios:
        print(f"\n📊 {scenario['name']} Test")
        print("-" * 40)
        
        start_time = time.time()
        results = await run_concurrent_requests(scenario["requests"], scenario["concurrency"], api_key)
        end_time = time.time()
        
        analysis = analyze_results(results)
        analysis["total_duration"] = end_time - start_time
        all_results[scenario["name"]] = analysis
        
        print(f"  Total Requests: {analysis['total_requests']}")
        print(f"  Successful: {analysis['successful_requests']}")
        print(f"  Failed: {analysis['failed_requests']}")
        print(f"  Success Rate: {analysis['success_rate']:.1f}%")
        print(f"  Total Duration: {analysis['total_duration']:.2f}s")
        
        if analysis['successful_requests'] > 0:
            rt = analysis['response_times']
            print(f"  Response Times:")
            print(f"    Mean: {rt['mean']:.2f}ms")
            print(f"    Median: {rt['median']:.2f}ms")
            print(f"    95th percentile: {rt['p95']:.2f}ms")
            print(f"    Max: {rt['max']:.2f}ms")
            
            tp = analysis['throughput']
            print(f"  Throughput:")
            print(f"    Requests/sec: {tp['requests_per_second']:.2f}")
            print(f"    Avg Processing Time: {tp['avg_processing_time']:.2f}ms")
    
    # Overall Assessment
    print("\n" + "=" * 60)
    print("📋 LOAD TEST SUMMARY")
    print("=" * 60)
    
    # Check if system meets performance requirements
    stress_test = all_results.get("Stress Test", {})
    
    requirements_met = True
    
    if stress_test.get("success_rate", 0) < 95:
        print("❌ Success Rate: FAIL (< 95% under stress)")
        requirements_met = False
    else:
        print("✅ Success Rate: PASS (≥ 95% under stress)")
    
    if stress_test.get("response_times", {}).get("p95", float('inf')) > 200:
        print("❌ Response Time: FAIL (95th percentile > 200ms)")
        requirements_met = False
    else:
        print("✅ Response Time: PASS (95th percentile ≤ 200ms)")
    
    if stress_test.get("throughput", {}).get("requests_per_second", 0) < 50:
        print("❌ Throughput: FAIL (< 50 requests/sec)")
        requirements_met = False
    else:
        print("✅ Throughput: PASS (≥ 50 requests/sec)")
    
    print("\n" + ("🎉 LOAD TESTS PASSED!" if requirements_met else "⚠️  LOAD TESTS FAILED"))
    print("=" * 60)
    
    return requirements_met

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load test Thai Search Proxy")
    parser.add_argument("--api-key", help="API key if required")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of the service")
    
    args = parser.parse_args()
    BASE_URL = args.url
    
    asyncio.run(run_load_tests(args.api_key))