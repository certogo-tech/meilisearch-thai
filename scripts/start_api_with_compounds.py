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
    # Get the project root directory (parent of scripts directory)
    project_root = Path(__file__).parent.parent
    script_path = project_root / "deployment/scripts/start_api_with_compounds.py"
    
    if not script_path.exists():
        print(f"❌ Start script not found: {script_path}")
        print("Please ensure the project structure is intact.")
        sys.exit(1)
    
    print("🚀 Starting Thai Tokenizer API with compound word support...")
    print("")
    
    # Change to project root and execute the actual script
    import os
    os.chdir(project_root)
    
    try:
        subprocess.run([sys.executable, str(script_path)] + sys.argv[1:], check=True)
    except subprocess.CalledProcessError as e:
        sys.exit(e.returncode)

if __name__ == "__main__":
    main()