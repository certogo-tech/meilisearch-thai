#!/usr/bin/env python3
"""Test script for query processing API endpoints."""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from src.api.main import app

def test_query_processing_endpoints():
    """Test the query processing endpoints."""
    client = TestClient(app)
    
    print("Testing query processing endpoints...")
    
    # Test simple query processing
    print("\n1. Testing simple query processing:")
    response = client.post("/api/v1/query/process", json={
        "query": "สวัสดี",
        "enable_partial_matching": True,
        "enable_query_expansion": True,
        "include_suggestions": True,
        "max_suggestions": 5
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Original query: {result['original_query']}")
        print(f"Processed query: {result['processed_query']}")
        print(f"Number of tokens: {len(result['query_tokens'])}")
        print(f"Number of variants: {len(result['search_variants'])}")
        print(f"Number of suggestions: {len(result['suggested_completions'])}")
        
        if result['query_tokens']:
            token = result['query_tokens'][0]
            print(f"First token: {token['original']} -> {token['processed']}")
            print(f"Query type: {token['query_type']}")
            print(f"Is partial: {token['is_partial']}")
    else:
        print(f"Error: {response.text}")
    
    # Test compound query processing
    print("\n2. Testing compound query processing:")
    response = client.post("/api/v1/query/compound", json={
        "query": "การศึกษา",
        "enable_partial_matching": True,
        "enable_query_expansion": True,
        "include_suggestions": True,
        "max_suggestions": 5
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Original query: {result['original_query']}")
        print(f"Processed query: {result['processed_query']}")
        print(f"Number of tokens: {len(result['query_tokens'])}")
        print(f"Number of variants: {len(result['search_variants'])}")
        
        if result['query_tokens']:
            token = result['query_tokens'][0]
            print(f"First token: {token['original']} -> {token['processed']}")
            print(f"Query type: {token['query_type']}")
            print(f"Is partial: {token['is_partial']}")
            print(f"Boost score: {token['boost_score']}")
            if token['compound_parts']:
                print(f"Compound parts: {token['compound_parts']}")
    else:
        print(f"Error: {response.text}")
    
    # Test mixed content query
    print("\n3. Testing mixed content query:")
    response = client.post("/api/v1/query/process", json={
        "query": "API การใช้งาน",
        "enable_partial_matching": True,
        "enable_query_expansion": True,
        "include_suggestions": False
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Original query: {result['original_query']}")
        print(f"Processed query: {result['processed_query']}")
        print(f"Number of tokens: {len(result['query_tokens'])}")
        
        for i, token in enumerate(result['query_tokens']):
            print(f"Token {i+1}: {token['original']} -> {token['processed']}")
            print(f"  Type: {token['query_type']}")
    else:
        print(f"Error: {response.text}")
    
    # Test empty query
    print("\n4. Testing empty query:")
    response = client.post("/api/v1/query/process", json={
        "query": "",
        "enable_partial_matching": True,
        "enable_query_expansion": True
    })
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Empty query handled correctly: {result['processing_metadata'].get('empty_query', False)}")
    else:
        print(f"Error: {response.text}")
    
    # Test stats endpoint
    print("\n5. Testing stats endpoint:")
    response = client.get("/api/v1/tokenize/stats")
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Status: {result['status']}")
        print(f"Query processor enabled: {result.get('query_processor', {}).get('query_expansion_enabled', 'N/A')}")
        print(f"Compound patterns: {result.get('query_processor', {}).get('compound_patterns_count', 'N/A')}")
    else:
        print(f"Error: {response.text}")

if __name__ == "__main__":
    test_query_processing_endpoints()