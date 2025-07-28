#!/usr/bin/env python3
"""
Comprehensive Test Suite for Thai-Japanese Compound Words
Specifically testing "สาหร่ายวากาเมะ" (wakame seaweed) and similar terms

This test suite validates the tokenization and search capabilities
for complex Thai-Japanese compound words that are common in Thai cuisine.
"""

import requests
import json
import time
from typing import Dict, List, Any

BASE_URL = "http://localhost:8001"

class WakameCompoundWordTester:
    """Test suite for Thai-Japanese compound words like wakame seaweed"""
    
    def __init__(self):
        self.base_url = BASE_URL
        self.test_results = []
    
    def test_basic_wakame_tokenization(self):
        """Test basic tokenization of wakame seaweed compound word"""
        print("🧪 Testing Basic Wakame Tokenization")
        print("-" * 40)
        
        test_cases = [
            {
                "text": "สาหร่ายวากาเมะ",
                "description": "Simple wakame compound word",
                "expected_contains": ["สาหร่ายวากาเมะ"]
            },
            {
                "text": "สาหร่ายวากาเมะเป็นอาหารทะเล",
                "description": "Wakame in sentence context",
                "expected_contains": ["สาหร่ายวากาเมะ", "เป็น", "อาหารทะเล"]
            },
            {
                "text": "สลัดสาหร่ายวากาเมะแบบญี่ปุ่น",
                "description": "Wakame salad with context",
                "expected_contains": ["สลัด", "สาหร่ายวากาเมะ", "แบบ", "ญี่ปุ่น"]
            },
            {
                "text": "สาหร่ายวากาเมะและสาหร่ายโนริ",
                "description": "Multiple seaweed types",
                "expected_contains": ["สาหร่ายวากาเมะ", "และ", "สาหร่ายโนริ"]
            }
        ]
        
        results = []
        for case in test_cases:
            response = requests.post(
                f"{self.base_url}/api/v1/tokenize",
                json={"text": case["text"]}
            )
            
            if response.status_code == 200:
                data = response.json()
                tokens = data["tokens"]
                processing_time = data["processing_time_ms"]
                
                # Check if expected tokens are present
                contains_expected = all(
                    any(expected in token for token in tokens) 
                    for expected in case["expected_contains"]
                )
                
                result = {
                    "description": case["description"],
                    "text": case["text"],
                    "tokens": tokens,
                    "processing_time_ms": processing_time,
                    "contains_expected": contains_expected,
                    "success": contains_expected
                }
                
                print(f"✅ {case['description']}")
                print(f"   Input: {case['text']}")
                print(f"   Tokens: {' | '.join(tokens)}")
                print(f"   Time: {processing_time}ms")
                print(f"   Expected found: {contains_expected}")
                print()
                
                results.append(result)
            else:
                print(f"❌ Failed to tokenize: {case['text']}")
                results.append({
                    "description": case["description"],
                    "text": case["text"],
                    "success": False,
                    "error": response.status_code
                })
        
        return results
    
    def test_wakame_query_processing(self):
        """Test query processing for wakame-related searches"""
        print("🔍 Testing Wakame Query Processing")
        print("-" * 40)
        
        query_tests = [
            {
                "query": "สาหร่ายวากาเมะ",
                "description": "Exact compound word query",
                "options": {"expand_compounds": True}
            },
            {
                "query": "สาหร่าย",
                "description": "Thai part only",
                "options": {"expand_compounds": True}
            },
            {
                "query": "วากาเมะ",
                "description": "Japanese part only", 
                "options": {"expand_compounds": True}
            },
            {
                "query": "สลัดสาหร่าย",
                "description": "Contextual search",
                "options": {"expand_compounds": True, "context_aware": True}
            }
        ]
        
        results = []
        for test in query_tests:
            response = requests.post(
                f"{self.base_url}/api/v1/query/process",
                json={
                    "query": test["query"],
                    "options": test["options"]
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                result = {
                    "description": test["description"],
                    "query": test["query"],
                    "processed_query": data["processed_query"],
                    "query_tokens": len(data["query_tokens"]),
                    "search_variants": len(data["search_variants"]),
                    "processing_time": data["processing_metadata"]["processing_time_ms"],
                    "success": True
                }
                
                print(f"✅ {test['description']}")
                print(f"   Query: {test['query']}")
                print(f"   Processed: {data['processed_query']}")
                print(f"   Tokens: {result['query_tokens']}")
                print(f"   Variants: {result['search_variants']}")
                print(f"   Time: {result['processing_time']:.2f}ms")
                print()
                
                results.append(result)
            else:
                print(f"❌ Failed to process query: {test['query']}")
                results.append({
                    "description": test["description"],
                    "query": test["query"],
                    "success": False,
                    "error": response.status_code
                })
        
        return results
    
    def test_wakame_performance(self):
        """Test performance with wakame compound words"""
        print("⚡ Testing Wakame Performance")
        print("-" * 40)
        
        performance_texts = [
            "สาหร่ายวากาเมะ",
            "สาหร่ายวากาเมะเป็นอาหารทะเลที่มีประโยชน์ต่อสุขภาพ",
            "ร้านอาหารญี่ปุ่นเสิร์ฟสลัดสาหร่ายวากาเมะแบบดั้งเดิม",
            "สาหร่ายวากาเมะ โนริ คอมบุ และสาหร่ายทะเลชนิดอื่นๆ จากญี่ปุ่น"
        ]
        
        results = []
        for text in performance_texts:
            times = []
            
            # Run multiple times for average
            for _ in range(10):
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/api/v1/tokenize",
                    json={"text": text}
                )
                end_time = time.time()
                
                if response.status_code == 200:
                    times.append(end_time - start_time)
            
            if times:
                avg_time = sum(times) / len(times) * 1000  # Convert to ms
                chars_per_sec = len(text) / (avg_time / 1000)
                
                result = {
                    "text": text[:50] + "..." if len(text) > 50 else text,
                    "length": len(text),
                    "avg_time_ms": avg_time,
                    "chars_per_second": chars_per_sec,
                    "success": True
                }
                
                print(f"✅ Text length: {len(text)} chars")
                print(f"   Average time: {avg_time:.2f}ms")
                print(f"   Speed: {chars_per_sec:.0f} chars/sec")
                print()
                
                results.append(result)
        
        return results
    
    def test_wakame_accuracy(self):
        """Test accuracy of wakame compound word recognition"""
        print("🎯 Testing Wakame Accuracy")
        print("-" * 40)
        
        accuracy_tests = [
            {
                "input": "สาหร่ายวากาเมะมีประโยชน์",
                "expected_compound": "สาหร่ายวากาเมะ",
                "description": "Should recognize wakame as single compound"
            },
            {
                "input": "สาหร่าย วากาเมะ แยกกัน",
                "expected_separate": ["สาหร่าย", "วากาเมะ"],
                "description": "Should recognize separated parts"
            },
            {
                "input": "ซื้อสาหร่ายวากาเมะแห้งจากญี่ปุ่น",
                "expected_compound": "สาหร่ายวากาเมะ",
                "description": "Should recognize compound in shopping context"
            }
        ]
        
        results = []
        for test in accuracy_tests:
            response = requests.post(
                f"{self.base_url}/api/v1/tokenize",
                json={"text": test["input"]}
            )
            
            if response.status_code == 200:
                tokens = response.json()["tokens"]
                
                if "expected_compound" in test:
                    accuracy = 1.0 if test["expected_compound"] in tokens else 0.0
                    expected_found = test["expected_compound"] in tokens
                else:
                    expected_found = all(term in tokens for term in test["expected_separate"])
                    accuracy = 1.0 if expected_found else 0.0
                
                result = {
                    "description": test["description"],
                    "input": test["input"],
                    "tokens": tokens,
                    "accuracy": accuracy,
                    "expected_found": expected_found,
                    "success": accuracy >= 0.8
                }
                
                print(f"{'✅' if result['success'] else '❌'} {test['description']}")
                print(f"   Input: {test['input']}")
                print(f"   Tokens: {' | '.join(tokens)}")
                print(f"   Expected found: {expected_found}")
                print()
                
                results.append(result)
        
        return results
    
    def run_comprehensive_test(self):
        """Run all wakame compound word tests"""
        print("🌊 Comprehensive Wakame Compound Word Testing")
        print("=" * 60)
        
        # Check if service is available
        try:
            response = requests.get(f"{self.base_url}/health")
            if response.status_code != 200:
                print("❌ Thai Tokenizer service not available")
                return False
        except requests.exceptions.ConnectionError:
            print("❌ Cannot connect to Thai Tokenizer service")
            return False
        
        print("✅ Service is available. Starting tests...\n")
        
        # Run all test suites
        tokenization_results = self.test_basic_wakame_tokenization()
        query_results = self.test_wakame_query_processing()
        performance_results = self.test_wakame_performance()
        accuracy_results = self.test_wakame_accuracy()
        
        # Summary
        print("=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(tokenization_results) + len(query_results) + len(accuracy_results)
        successful_tests = (
            sum(1 for r in tokenization_results if r.get("success", False)) +
            sum(1 for r in query_results if r.get("success", False)) +
            sum(1 for r in accuracy_results if r.get("success", False))
        )
        
        print(f"Tokenization Tests: {sum(1 for r in tokenization_results if r.get('success', False))}/{len(tokenization_results)} passed")
        print(f"Query Processing Tests: {sum(1 for r in query_results if r.get('success', False))}/{len(query_results)} passed")
        print(f"Accuracy Tests: {sum(1 for r in accuracy_results if r.get('success', False))}/{len(accuracy_results)} passed")
        print(f"Performance Tests: {len(performance_results)} completed")
        print(f"\nOverall Success Rate: {successful_tests}/{total_tests} ({successful_tests/total_tests*100:.1f}%)")
        
        if performance_results:
            avg_speed = sum(r["chars_per_second"] for r in performance_results) / len(performance_results)
            print(f"Average Processing Speed: {avg_speed:.0f} chars/second")
        
        print("\n🎉 Wakame compound word testing completed!")
        
        # Save detailed results
        detailed_results = {
            "tokenization_results": tokenization_results,
            "query_results": query_results,
            "performance_results": performance_results,
            "accuracy_results": accuracy_results,
            "summary": {
                "total_tests": total_tests,
                "successful_tests": successful_tests,
                "success_rate": successful_tests/total_tests if total_tests > 0 else 0,
                "average_speed": avg_speed if performance_results else 0
            }
        }
        
        with open("wakame_test_results.json", "w", encoding="utf-8") as f:
            json.dump(detailed_results, f, indent=2, ensure_ascii=False)
        
        print("📄 Detailed results saved to wakame_test_results.json")
        
        return successful_tests == total_tests

def main():
    """Run the wakame compound word test suite"""
    tester = WakameCompoundWordTester()
    success = tester.run_comprehensive_test()
    
    if success:
        print("\n🎊 All wakame compound word tests passed!")
        return 0
    else:
        print("\n⚠️  Some tests failed. Check the results above.")
        return 1

if __name__ == "__main__":
    exit(main())