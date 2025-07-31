#!/bin/bash

# Setup script for connecting Thai Tokenizer to existing MeiliSearch
# Usage: ./setup_existing_meilisearch.sh

set -e

echo "🚀 Thai Tokenizer Setup for Existing MeiliSearch"
echo "================================================="

# Check if compound dictionary exists
if [ ! -f "../../data/dictionaries/thai_compounds.json" ]; then
    echo "❌ Compound dictionary not found: ../../data/dictionaries/thai_compounds.json"
    echo "Please ensure the dictionary file exists before running this script."
    exit 1
fi

echo "✅ Compound dictionary found with $(jq -r '[.thai_japanese_compounds[], .thai_english_compounds[]] | length' ../../data/dictionaries/thai_compounds.json) entries"

# Create environment file if it doesn't exist
if [ ! -f "../../.env.existing" ]; then
    echo "📝 Creating .env.existing file..."
    cp ../configs/.env.existing.example ../../.env.existing
    echo "⚠️  Please edit .env.existing with your MeiliSearch details:"
    echo "   - EXISTING_MEILISEARCH_URL"
    echo "   - EXISTING_MEILISEARCH_API_KEY"
    echo ""
    read -p "Press Enter after updating .env.existing file..."
fi

# Load environment variables
source ../../.env.existing

# Test connection to existing MeiliSearch
echo "🔍 Testing connection to existing MeiliSearch..."

# Convert Docker internal URL to host URL for testing from host
TEST_URL="$EXISTING_MEILISEARCH_URL"
if [[ "$EXISTING_MEILISEARCH_URL" == *"host.docker.internal"* ]]; then
    TEST_URL="${EXISTING_MEILISEARCH_URL//host.docker.internal/localhost}"
fi

if curl -s -f -H "Authorization: Bearer $EXISTING_MEILISEARCH_API_KEY" "$TEST_URL/health" > /dev/null; then
    echo "✅ Successfully connected to MeiliSearch at $TEST_URL"
else
    echo "❌ Failed to connect to MeiliSearch at $TEST_URL"
    echo "Please check your EXISTING_MEILISEARCH_URL and EXISTING_MEILISEARCH_API_KEY in .env.existing"
    echo "Note: Use 'http://host.docker.internal:7700' for Docker containers to connect to host MeiliSearch"
    exit 1
fi

# Start Thai Tokenizer
echo "🚀 Starting Thai Tokenizer..."
docker compose -f ../docker/docker-compose.tokenizer-only.yml --env-file ../../.env.existing up -d

# Wait for service to be ready
echo "⏳ Waiting for Thai Tokenizer to be ready..."
sleep 10

# Test Thai Tokenizer
echo "🧪 Testing Thai Tokenizer with compound words..."
RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะมีประโยชน์ต่อสุขภาพ"}')

if echo "$RESPONSE" | grep -q '"วากาเมะ"'; then
    echo "✅ SUCCESS: Compound word tokenization is working!"
    echo "   Input: วากาเมะมีประโยชน์ต่อสุขภาพ"
    echo "   Tokens: $(echo "$RESPONSE" | jq -r '.tokens | join(", ")')"
else
    echo "❌ FAILED: Compound word tokenization is not working properly"
    echo "Response: $RESPONSE"
    exit 1
fi

# Check tokenizer stats
echo "📊 Checking tokenizer statistics..."
STATS=$(curl -s "http://localhost:8001/api/v1/tokenize/stats")
DICT_SIZE=$(echo "$STATS" | jq -r '.custom_dictionary_size // 0')

if [ "$DICT_SIZE" -gt 0 ]; then
    echo "✅ Custom dictionary loaded with $DICT_SIZE compound words"
else
    echo "⚠️  Warning: Custom dictionary size is $DICT_SIZE"
fi

echo ""
echo "🎉 Setup Complete!"
echo "=================================="
echo "✅ Thai Tokenizer is running on: http://localhost:8001"
echo "✅ API Documentation: http://localhost:8001/docs"
echo "✅ Health Check: http://localhost:8001/health"
echo "✅ Connected to MeiliSearch: $EXISTING_MEILISEARCH_URL"
echo ""
echo "🧪 Test the integration:"
echo 'curl -X POST "http://localhost:8001/api/v1/tokenize" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"text": "ร้านอาหารญี่ปุ่นเสิร์ฟวากาเมะและซาชิมิ"}'"'"
echo ""
echo "Expected result: วากาเมะ and ซาชิมิ should be single tokens!"