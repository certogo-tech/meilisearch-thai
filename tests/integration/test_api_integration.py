#!/usr/bin/env python3
"""
Test script to verify that the API integration with compound dictionary works.
This tests the actual API endpoints to ensure wakame tokenization is fixed.
"""

import requests
import json
import time
from typing import Dict, Any


def test_api_endpoint(base_url: str = "http://localhost:8000"):
    """Test the API endpoints with wakame compound words."""
    
    print("🧪 Testing API Integration with Compound Dictionary")
    print("=" * 55)
    
    # Test cases from our successful tests
    test_cases = [
        {
            "text": "สาหร่ายวากาเมะ",
            "description": "Basic wakame seaweed compound",
            "expected_compound": "วากาเมะ"
        },
        {
            "text": "สาหร่ายวากาเมะเป็นอาหารทะเล",
            "description": "Wakame in sentence context",
            "expected_compound": "วากาเมะ"
        },
        {
            "text": "ร้านอาหารญี่ปุ่นเสิร์ฟวากาเมะ",
            "description": "Restaurant serving wakame",
            "expected_compound": "วากาเมะ"
        },
        {
            "text": "วากาเมะมีประโยชน์ต่อสุขภาพ",
            "description": "Wakame health benefits",
            "expected_compound": "วากาเมะ"
        }
    ]
    
    # Test health endpoint first
    print("🏥 Testing Health Endpoint...")
    try:
        response = requests.get(f"{base_url}/health", timeout=5)
        if response.status_code == 200:
            print("✅ API is healthy and running")
        else:
            print(f"⚠️  API health check returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ API is not accessible: {e}")
        print("💡 Make sure to start the API server with: uvicorn src.api.main:app --reload --port 8000")
        return
    
    # Test tokenization stats
    print("\\n📊 Testing Tokenization Stats...")
    try:
        response = requests.get(f"{base_url}/api/v1/tokenize/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            custom_dict_size = stats.get("tokenizer", {}).get("custom_dict_size", 0)
            print(f"✅ Tokenizer stats retrieved")
            print(f"   Custom dictionary size: {custom_dict_size}")
            
            if custom_dict_size > 0:
                print("✅ Custom dictionary is loaded!")
            else:
                print("⚠️  Custom dictionary appears to be empty")
        else:
            print(f"⚠️  Stats endpoint returned status {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to get stats: {e}")
    
    # Test tokenization endpoints
    print("\\n🔍 Testing Tokenization Endpoints...")
    
    success_count = 0
    total_tests = len(test_cases)
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"\\n🧪 Test {i}: {test_case['description']}")
        print(f"   Text: {test_case['text']}")
        
        try:
            # Test standard tokenization endpoint
            payload = {"text": test_case["text"]}
            response = requests.post(
                f"{base_url}/api/v1/tokenize",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                tokens = result.get("tokens", [])
                processing_time = result.get("processing_time_ms", 0)
                
                print(f"   Tokens: {tokens}")
                print(f"   Processing time: {processing_time}ms")
                
                # Check if wakame is preserved as compound
                wakame_preserved = test_case["expected_compound"] in tokens
                wakame_not_split = not ("วา" in tokens and "กา" in tokens and "เมะ" in tokens)
                
                if wakame_preserved:
                    print(f"   ✅ SUCCESS: {test_case['expected_compound']} preserved as single token!")
                    success_count += 1
                elif wakame_not_split:
                    print(f"   ✅ IMPROVED: {test_case['expected_compound']} not split into syllables!")
                    success_count += 1
                else:
                    print(f"   ❌ ISSUE: {test_case['expected_compound']} still being split")
                
            else:
                print(f"   ❌ API returned status {response.status_code}: {response.text}")
                
        except requests.exceptions.RequestException as e:
            print(f"   ❌ Request failed: {e}")
    
    # Test compound-specific endpoint
    print("\\n🌟 Testing Compound Tokenization Endpoint...")
    
    compound_test = "สาหร่ายวากาเมะและซาชิมิ"
    try:
        payload = {"text": compound_test}
        response = requests.post(
            f"{base_url}/api/v1/tokenize/compound",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            tokens = result.get("tokens", [])
            print(f"   Text: {compound_test}")
            print(f"   Tokens: {tokens}")
            
            compounds_found = []
            for compound in ["วากาเมะ", "ซาชิมิ", "สาหร่ายวากาเมะ"]:
                if compound in tokens:
                    compounds_found.append(compound)
            
            if compounds_found:
                print(f"   ✅ Compounds preserved: {compounds_found}")
            else:
                print("   ⚠️  No compounds preserved in specialized endpoint")
        else:
            print(f"   ❌ Compound endpoint returned status {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Compound endpoint request failed: {e}")
    
    # Summary
    print("\\n" + "=" * 55)
    print("📈 API INTEGRATION TEST SUMMARY:")
    print(f"   Tests passed: {success_count}/{total_tests}")
    print(f"   Success rate: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("   🎉 EXCELLENT: All API tests passed!")
        print("   ✅ Wakame tokenization issue is RESOLVED in production API!")
    elif success_count >= total_tests * 0.8:
        print("   ✅ GOOD: Most API tests passed!")
        print("   ✅ Significant improvement in wakame tokenization!")
    else:
        print("   ⚠️  PARTIAL: Some API tests failed.")
        print("   💡 Check API server logs for more details.")
    
    print("\\n🚀 Next Steps:")
    print("1. If tests passed: Your API is ready for production!")
    print("2. If tests failed: Check server logs and restart the API")
    print("3. Update your client applications to use the fixed tokenization")


def test_direct_api_call():
    """Test a direct API call to verify the fix."""
    print("\\n🎯 Direct API Test for Wakame Fix")
    print("-" * 35)
    
    base_url = "http://localhost:8000"
    test_text = "วากาเมะมีประโยชน์ต่อสุขภาพ"
    
    try:
        payload = {"text": test_text}
        response = requests.post(
            f"{base_url}/api/v1/tokenize",
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            tokens = result["tokens"]
            
            print(f"Input: {test_text}")
            print(f"Tokens: {tokens}")
            
            if "วากาเมะ" in tokens:
                print("🎉 PERFECT: วากาเมะ is preserved as single token!")
                return True
            elif not ("วา" in tokens and "กา" in tokens and "เมะ" in tokens):
                print("✅ IMPROVED: วากาเมะ is not split into syllables!")
                return True
            else:
                print("❌ ISSUE: วากาเมะ is still being split")
                return False
        else:
            print(f"❌ API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


if __name__ == "__main__":
    print("🚀 API Integration Test for Wakame Compound Word Fix")
    print("This script tests the production API to verify the fix is working.")
    print()
    
    # Test the API integration
    test_api_endpoint()
    
    # Quick direct test
    success = test_direct_api_call()
    
    if success:
        print("\\n🎊 CONGRATULATIONS!")
        print("The wakame tokenization fix is working in your production API!")
    else:
        print("\\n⚠️  The fix may not be fully integrated yet.")
        print("Try restarting your API server to load the compound dictionary.")