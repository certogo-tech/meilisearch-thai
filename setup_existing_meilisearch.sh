#!/bin/bash

# Wrapper script for setting up Thai Tokenizer with existing MeiliSearch
# This script calls the actual implementation in deployment/scripts/

set -e

SCRIPT_PATH="deployment/scripts/setup_existing_meilisearch.sh"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Setup script not found: $SCRIPT_PATH"
    echo "Please ensure you're running this from the project root directory."
    exit 1
fi

echo "🚀 Running Thai Tokenizer setup for existing MeiliSearch..."
echo "Calling: $SCRIPT_PATH"
echo ""

# Change to the script directory and run it
cd deployment/scripts
./setup_existing_meilisearch.sh