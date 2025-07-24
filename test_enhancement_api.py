#!/usr/bin/env python3
"""
Test script to verify search result enhancement API endpoint.
"""

import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from src.api.main import app

def test_search_result_enhancement():
    """Test the search result enhancement API endpoint."""
    print("Testing search result enhancement API endpoint...")
    
    client = TestClient(app)
    
    try:
        # Test POST /api/v1/search/enhance
        print("\n1. Testing POST /api/v1/search/enhance...")
        
        # Mock search results from MeiliSearch
        mock_search_results = {
            "hits": [
                {
                    "_score": 1.0,
                    "id": "doc1",
                    "title": "การศึกษาไทย",
                    "content": "เกี่ยวกับการศึกษาในประเทศไทย มีความสำคัญมาก",
                    "_formatted": {
                        "title": "<em>การศึกษา</em>ไทย",
                        "content": "เกี่ยวกับ<em>การศึกษา</em>ในประเทศไทย มีความสำคัญมาก"
                    }
                },
                {
                    "_score": 0.8,
                    "id": "doc2", 
                    "title": "ระบบการศึกษา",
                    "content": "ระบบการศึกษาของไทยต้องพัฒนา",
                    "_formatted": {
                        "title": "ระบบ<em>การศึกษา</em>",
                        "content": "ระบบ<em>การศึกษา</em>ของไทยต้องพัฒนา"
                    }
                }
            ],
            "query": "การศึกษา",
            "processingTimeMs": 10,
            "hitsPerPage": 20,
            "page": 1,
            "totalPages": 1,
            "totalHits": 2
        }
        
        enhancement_request = {
            "search_results": mock_search_results,
            "original_query": "การศึกษา",
            "highlight_fields": ["title", "content"],
            "enable_compound_highlighting": True,
            "enable_relevance_boosting": True
        }
        
        response = client.post("/api/v1/search/enhance", json=enhancement_request)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Enhancement successful!")
            print(f"  - Enhanced hits: {len(result['enhanced_hits'])}")
            print(f"  - Query analysis: {result['query_analysis'].get('has_compound_words', False)}")
            print(f"  - Compound matches: {result['enhancement_metadata'].get('compound_matches', 0)}")
            
            # Check first enhanced hit
            if result['enhanced_hits']:
                first_hit = result['enhanced_hits'][0]
                print(f"  - First hit enhanced score: {first_hit['enhanced_score']}")
                print(f"  - Highlight spans: {len(first_hit['highlight_spans'])}")
                print(f"  - Compound matches: {first_hit['compound_matches']}")
                
                # Show some highlight spans
                for i, span in enumerate(first_hit['highlight_spans'][:3]):
                    print(f"    Span {i+1}: '{span['text']}' ({span['highlight_type']}, confidence: {span['confidence']})")
            
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

def test_enhancement_with_mixed_content():
    """Test enhancement with mixed Thai-English content."""
    print("\n2. Testing enhancement with mixed content...")
    
    client = TestClient(app)
    
    try:
        mock_search_results = {
            "hits": [
                {
                    "_score": 1.0,
                    "id": "doc1",
                    "title": "API การใช้งาน",
                    "content": "วิธีการใช้ API สำหรับการพัฒนาแอปพลิเคชัน",
                    "_formatted": {
                        "title": "<em>API</em> การใช้งาน",
                        "content": "วิธีการใช้ <em>API</em> สำหรับการพัฒนาแอปพลิเคชัน"
                    }
                }
            ],
            "query": "API การใช้งาน",
            "processingTimeMs": 8,
            "hitsPerPage": 20,
            "page": 1,
            "totalPages": 1,
            "totalHits": 1
        }
        
        enhancement_request = {
            "search_results": mock_search_results,
            "original_query": "API การใช้งาน",
            "highlight_fields": ["title", "content"],
            "enable_compound_highlighting": True,
            "enable_relevance_boosting": True
        }
        
        response = client.post("/api/v1/search/enhance", json=enhancement_request)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Mixed content enhancement successful!")
            print(f"  - Mixed language detected: {result['query_analysis'].get('is_mixed_language', False)}")
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

def test_enhancement_disabled_features():
    """Test enhancement with disabled features."""
    print("\n3. Testing enhancement with disabled features...")
    
    client = TestClient(app)
    
    try:
        mock_search_results = {
            "hits": [
                {
                    "_score": 1.0,
                    "id": "doc1",
                    "title": "การศึกษาไทย",
                    "content": "เกี่ยวกับการศึกษา"
                }
            ],
            "query": "การศึกษา",
            "processingTimeMs": 5
        }
        
        enhancement_request = {
            "search_results": mock_search_results,
            "original_query": "การศึกษา",
            "highlight_fields": ["title", "content"],
            "enable_compound_highlighting": False,
            "enable_relevance_boosting": False
        }
        
        response = client.post("/api/v1/search/enhance", json=enhancement_request)
        
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Enhancement with disabled features successful!")
            
            # Score should not be boosted
            if result['enhanced_hits']:
                first_hit = result['enhanced_hits'][0]
                original_score = first_hit['original_hit']['_score']
                enhanced_score = first_hit['enhanced_score']
                print(f"  - Original score: {original_score}, Enhanced score: {enhanced_score}")
                print(f"  - Score unchanged: {original_score == enhanced_score}")
            
            return True
        else:
            print(f"❌ Failed: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Exception occurred: {e}")
        return False

if __name__ == "__main__":
    print("=== Thai Tokenizer Search Result Enhancement API Tests ===")
    
    success_count = 0
    total_tests = 3
    
    if test_search_result_enhancement():
        success_count += 1
    
    if test_enhancement_with_mixed_content():
        success_count += 1
        
    if test_enhancement_disabled_features():
        success_count += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {success_count}/{total_tests}")
    
    if success_count == total_tests:
        print("✓ All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)