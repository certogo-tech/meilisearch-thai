#!/bin/bash

# Wrapper script for setting up Thai Tokenizer with existing MeiliSearch
# This script calls the actual implementation

set -e

SCRIPT_PATH="deployment/scripts/setup_existing_meilisearch.sh"

if [ ! -f "$SCRIPT_PATH" ]; then
    echo "❌ Setup script not found: $SCRIPT_PATH"
    echo "Please ensure you're running this from the project root directory."
    exit 1
fi

echo "🚀 Running Thai Tokenizer setup for existing MeiliSearch..."
echo ""

# Change to the project root, then to the script directory and execute
cd "$(dirname "$0")/.."
cd deployment/scripts
exec ./setup_existing_meilisearch.sh