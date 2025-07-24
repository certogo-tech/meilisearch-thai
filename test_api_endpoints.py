#!/usr/bin/env python3
"""
Test script to verify API endpoints work correctly.
"""

import asyncio
import json
import sys
import os
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from src.api.main import app

def test_config_endpoints():
    """Test the configuration API endpoints."""
    print("Testing configuration API endpoints...")
    
    client = TestClient(app)
    
    try:
        # Test GET /api/v1/config
        print("\n1. Testing GET /api/v1/config...")
        response = client.get("/api/v1/config")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            config_data = response.json()
            print(f"✓ Configuration retrieved: {config_data.get('status', 'unknown')}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        # Test PUT /api/v1/config/meilisearch
        print("\n2. Testing PUT /api/v1/config/meilisearch...")
        meilisearch_config = {
            "host": "http://localhost:7700",
            "api_key": "test_key_123",
            "index_name": "test_documents"
        }
        response = client.put("/api/v1/config/meilisearch", json=meilisearch_config)
        print(f"Status: {response.status_code}")
        if response.status_code in [200, 400]:  # 400 is expected if MeiliSearch is not running
            if response.status_code == 200:
                result = response.json()
                print(f"✓ MeiliSearch configuration updated: {result.get('status', 'unknown')}")
            else:
                print("⚠️ MeiliSearch not available (expected in test environment)")
        else:
            print(f"❌ Unexpected error: {response.text}")
            return False
        
        # Test PUT /api/v1/config/tokenizer
        print("\n3. Testing PUT /api/v1/config/tokenizer...")
        tokenizer_config = {
            "engine": "newmm",
            "model_version": "latest",
            "custom_dictionary": ["คำทดสอบ1", "คำทดสอบ2"],
            "keep_whitespace": True,
            "handle_compounds": True,
            "fallback_engine": "pythainlp",
            "batch_size": 50,
            "max_retries": 2,
            "timeout_ms": 3000
        }
        response = client.put("/api/v1/config/tokenizer", json=tokenizer_config)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Tokenizer configuration updated: {result.get('status', 'unknown')}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        # Test POST /api/v1/config/dictionary/add
        print("\n4. Testing POST /api/v1/config/dictionary/add...")
        words_to_add = ["คำใหม่1", "คำใหม่2", "คำใหม่3"]
        response = client.post("/api/v1/config/dictionary/add", json=words_to_add)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Dictionary words added: {result.get('status', 'unknown')}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        # Test GET /api/v1/config/dictionary
        print("\n5. Testing GET /api/v1/config/dictionary...")
        response = client.get("/api/v1/config/dictionary")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            dictionary_size = result.get('size', 0)
            print(f"✓ Dictionary retrieved with {dictionary_size} words")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        # Test POST /api/v1/config/dictionary/remove
        print("\n6. Testing POST /api/v1/config/dictionary/remove...")
        words_to_remove = ["คำใหม่1"]
        response = client.post("/api/v1/config/dictionary/remove", json=words_to_remove)
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Dictionary words removed: {result.get('status', 'unknown')}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        # Test GET /api/v1/config/validation
        print("\n7. Testing GET /api/v1/config/validation...")
        response = client.get("/api/v1/config/validation")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            is_valid = result.get('valid', False)
            print(f"✓ Configuration validation: {'valid' if is_valid else 'invalid'}")
            if result.get('errors'):
                print(f"  Errors: {result['errors']}")
            if result.get('warnings'):
                print(f"  Warnings: {result['warnings']}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        # Test POST /api/v1/config/validate
        print("\n8. Testing POST /api/v1/config/validate...")
        response = client.post("/api/v1/config/validate")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            overall_status = result.get('overall_status', 'unknown')
            print(f"✓ Configuration validation: {overall_status}")
            checks = result.get('checks', {})
            for check_name, check_result in checks.items():
                status = check_result.get('status', 'unknown')
                message = check_result.get('message', '')
                print(f"  {check_name}: {status} - {message}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        # Test POST /api/v1/config/reset
        print("\n9. Testing POST /api/v1/config/reset...")
        response = client.post("/api/v1/config/reset")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            result = response.json()
            print(f"✓ Configuration reset: {result.get('status', 'unknown')}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        # Test final configuration state
        print("\n10. Testing final configuration state...")
        response = client.get("/api/v1/config")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            config_data = response.json()
            print(f"✓ Final configuration status: {config_data.get('status', 'unknown')}")
        else:
            print(f"❌ Failed: {response.text}")
            return False
        
        print("\n✅ All configuration API endpoint tests passed!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_config_endpoints()
    sys.exit(0 if success else 1)