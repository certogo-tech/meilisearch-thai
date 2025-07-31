#!/usr/bin/env python3
"""
Simple wrapper script to start the Thai tokenizer API with compound dictionary support.
This script calls the actual implementation in deployment/scripts/
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    """Run the compound API startup script from its proper location."""
    script_path = Path("deployment/scripts/start_api_with_compounds.py")
    
    if not script_path.exists():
        print(f"❌ Startup script not found: {script_path}")
        print("Please ensure you're running this from the project root directory.")
        sys.exit(1)
    
    # Change to the script directory and run it
    original_cwd = os.getcwd()
    try:
        os.chdir("deployment/scripts")
        subprocess.run([sys.executable, "start_api_with_compounds.py"], check=True)
    finally:
        os.chdir(original_cwd)

if __name__ == "__main__":
    main()