#!/usr/bin/env python3

"""
Wrapper script for starting Thai Tokenizer API with compound word support.
This script calls the actual implementation.
"""

import sys
import subprocess
from pathlib import Path

def main():
    """Execute the actual start script."""
    script_path = Path("scripts/wrappers/start_api_with_compounds.py")
    
    if not script_path.exists():
        print(f"❌ Start script not found: {script_path}")
        print("Please ensure you're running this from the project root directory.")
        sys.exit(1)
    
    print("🚀 Starting Thai Tokenizer API with compound word support...")
    print(f"Calling: {script_path}")
    print("")
    
    # Execute the actual script
    try:
        subprocess.run([sys.executable, str(script_path)] + sys.argv[1:], check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()