#!/usr/bin/env python3
"""
Startup script for the Thai tokenizer API with compound dictionary support.
This script ensures the compound dictionary is loaded and starts the API server.
"""

import os
import sys
import json
import subprocess
from pathlib import Path


def check_compound_dictionary():
    """Check if the compound dictionary exists and is valid."""
    dict_path = Path("data/dictionaries/thai_compounds.json")
    
    if not dict_path.exists():
        print(f"❌ Compound dictionary not found: {dict_path}")
        return False
    
    try:
        with open(dict_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Count compound words
        compound_count = 0
        if isinstance(data, list):
            compound_count = len(data)
        elif isinstance(data, dict):
            for category, words in data.items():
                if isinstance(words, list):
                    compound_count += len(words)
        
        print(f"✅ Compound dictionary found with {compound_count} entries")
        
        # Check for wakame specifically
        compounds = []
        if isinstance(data, list):
            compounds = data
        elif isinstance(data, dict):
            for words in data.values():
                if isinstance(words, list):
                    compounds.extend(words)
        
        if "วากาเมะ" in compounds:
            print("✅ วากาเมะ found in dictionary - tokenization fix is ready!")
        else:
            print("⚠️  วากาเมะ not found in dictionary")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to load compound dictionary: {e}")
        return False


def set_environment_variables():
    """Set environment variables for compound dictionary support."""
    env_vars = {
        "THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH": "data/dictionaries/thai_compounds.json",
        "THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS": "true",
        "THAI_TOKENIZER_TOKENIZER_ENGINE": "newmm",
        "THAI_TOKENIZER_DEBUG": "false"
    }
    
    print("🔧 Setting environment variables...")
    for key, value in env_vars.items():
        os.environ[key] = value
        print(f"   {key}={value}")
    
    print("✅ Environment variables set")


def check_dependencies():
    """Check if required dependencies are installed."""
    try:
        import pythainlp
        print("✅ PyThaiNLP is available")
        
        # Test basic tokenization
        from pythainlp import word_tokenize
        test_tokens = word_tokenize("ทดสอบ", engine="newmm")
        print("✅ PyThaiNLP tokenization works")
        
        return True
        
    except ImportError as e:
        print(f"❌ PyThaiNLP not available: {e}")
        print("💡 Install with: pip install pythainlp")
        return False


def start_api_server(port: int = 8000, reload: bool = True):
    """Start the API server with uvicorn."""
    print(f"🚀 Starting API server on port {port}...")
    
    cmd = [
        "uvicorn",
        "src.api.main:app",
        "--host", "0.0.0.0",
        "--port", str(port)
    ]
    
    if reload:
        cmd.append("--reload")
    
    try:
        print(f"Command: {' '.join(cmd)}")
        print("✅ API server starting...")
        print("📖 API documentation will be available at:")
        print(f"   - Swagger UI: http://localhost:{port}/docs")
        print(f"   - ReDoc: http://localhost:{port}/redoc")
        print()
        print("🧪 Test the wakame fix with:")
        print(f"   python3 test_api_integration.py")
        print()
        print("Press Ctrl+C to stop the server")
        print("-" * 50)
        
        subprocess.run(cmd, check=True)
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to start API server: {e}")
        return False
    except KeyboardInterrupt:
        print("\\n🛑 API server stopped by user")
        return True
    except FileNotFoundError:
        print("❌ uvicorn not found. Install with: pip install uvicorn")
        return False


def main():
    """Main startup function."""
    print("🚀 Thai Tokenizer API with Compound Dictionary Support")
    print("=" * 55)
    print("This script starts the API server with wakame tokenization fix.")
    print()
    
    # Check compound dictionary
    if not check_compound_dictionary():
        print("❌ Cannot start without compound dictionary")
        sys.exit(1)
    
    # Check dependencies
    if not check_dependencies():
        print("❌ Cannot start without required dependencies")
        sys.exit(1)
    
    # Set environment variables
    set_environment_variables()
    
    print()
    print("🎯 Ready to start API server with compound dictionary support!")
    print("The wakame tokenization issue should be resolved.")
    print()
    
    # Start the server
    success = start_api_server()
    
    if success:
        print("✅ API server stopped successfully")
    else:
        print("❌ API server encountered an error")
        sys.exit(1)


if __name__ == "__main__":
    main()