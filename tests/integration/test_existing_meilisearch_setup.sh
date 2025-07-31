#!/bin/bash

# Test script for Thai Tokenizer setup with existing MeiliSearch
# This script tests the setup process step by step

set -e

echo "🧪 Testing Thai Tokenizer Setup for Existing MeiliSearch"
echo "========================================================"

# Test 1: Check if compound dictionary exists
echo "Test 1: Checking compound dictionary..."
if [ ! -f "data/dictionaries/thai_compounds.json" ]; then
    echo "❌ FAIL: Compound dictionary not found"
    exit 1
fi

DICT_ENTRIES=$(jq -r '[.thai_japanese_compounds[], .thai_english_compounds[]] | length' data/dictionaries/thai_compounds.json)
echo "✅ PASS: Compound dictionary found with $DICT_ENTRIES entries"

# Test 2: Check if environment example exists
echo "Test 2: Checking environment example file..."
if [ ! -f "deployment/configs/.env.existing.example" ]; then
    echo "❌ FAIL: Environment example file not found"
    exit 1
fi
echo "✅ PASS: Environment example file exists"

# Test 3: Check if Docker compose file exists
echo "Test 3: Checking Docker compose file..."
if [ ! -f "deployment/docker/docker-compose.tokenizer-only.yml" ]; then
    echo "❌ FAIL: Docker compose file not found"
    exit 1
fi
echo "✅ PASS: Docker compose file exists"

# Test 4: Create test environment file
echo "Test 4: Creating test environment file..."
cp .env.existing.test .env.existing
echo "✅ PASS: Test environment file created"

# Test 5: Validate environment file format
echo "Test 5: Validating environment file format..."
source .env.existing
if [ -z "$EXISTING_MEILISEARCH_URL" ] || [ -z "$EXISTING_MEILISEARCH_API_KEY" ]; then
    echo "❌ FAIL: Required environment variables not set"
    exit 1
fi
echo "✅ PASS: Environment variables are properly set"
echo "   URL: $EXISTING_MEILISEARCH_URL"
echo "   API Key: ${EXISTING_MEILISEARCH_API_KEY:0:10}..."

# Test 6: Check if we can start a test MeiliSearch container
echo "Test 6: Starting test MeiliSearch container..."
docker run -d --name test-meilisearch \
    -p 7700:7700 \
    -e MEILI_MASTER_KEY=test-master-key \
    getmeili/meilisearch:v1.15.2 \
    meilisearch --master-key=test-master-key || echo "Container might already exist"

# Wait for MeiliSearch to start
echo "⏳ Waiting for MeiliSearch to start..."
sleep 15

# Test 7: Test connection to MeiliSearch
echo "Test 7: Testing connection to MeiliSearch..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f -H "Authorization: Bearer test-master-key" "http://localhost:7700/health" > /dev/null; then
        echo "✅ PASS: Successfully connected to MeiliSearch"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⏳ Retry $RETRY_COUNT/$MAX_RETRIES: Waiting for MeiliSearch..."
        sleep 5
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ FAIL: Could not connect to MeiliSearch after $MAX_RETRIES retries"
    docker logs test-meilisearch
    exit 1
fi

# Test 8: Test Docker compose configuration
echo "Test 8: Testing Docker compose configuration..."
cd deployment/docker
if docker compose -f docker-compose.tokenizer-only.yml --env-file ../../.env.existing config > /dev/null; then
    echo "✅ PASS: Docker compose configuration is valid"
else
    echo "❌ FAIL: Docker compose configuration is invalid"
    exit 1
fi
cd ../..

# Test 9: Start Thai Tokenizer
echo "Test 9: Starting Thai Tokenizer..."
cd deployment/docker
docker compose -f docker-compose.tokenizer-only.yml --env-file ../../.env.existing up -d
cd ../..

# Wait for Thai Tokenizer to start
echo "⏳ Waiting for Thai Tokenizer to start..."
sleep 20

# Test 10: Test Thai Tokenizer health
echo "Test 10: Testing Thai Tokenizer health..."
MAX_RETRIES=10
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s -f "http://localhost:8001/health" > /dev/null; then
        echo "✅ PASS: Thai Tokenizer is healthy"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        echo "⏳ Retry $RETRY_COUNT/$MAX_RETRIES: Waiting for Thai Tokenizer..."
        sleep 5
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    echo "❌ FAIL: Thai Tokenizer is not responding after $MAX_RETRIES retries"
    docker logs thai-tokenizer-thai-tokenizer-1 || docker logs deployment-docker-thai-tokenizer-1
    exit 1
fi

# Test 11: Test compound word tokenization
echo "Test 11: Testing compound word tokenization..."
RESPONSE=$(curl -s -X POST "http://localhost:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะมีประโยชน์ต่อสุขภาพ"}')

if echo "$RESPONSE" | grep -q '"วากาเมะ"'; then
    echo "✅ PASS: Compound word tokenization is working!"
    echo "   Input: วากาเมะมีประโยชน์ต่อสุขภาพ"
    echo "   Tokens: $(echo "$RESPONSE" | jq -r '.tokens | join(", ")')"
else
    echo "❌ FAIL: Compound word tokenization is not working properly"
    echo "Response: $RESPONSE"
fi

# Test 12: Test tokenizer statistics
echo "Test 12: Testing tokenizer statistics..."
STATS=$(curl -s "http://localhost:8001/api/v1/tokenize/stats")
DICT_SIZE=$(echo "$STATS" | jq -r '.custom_dictionary_size // 0')

if [ "$DICT_SIZE" -gt 0 ]; then
    echo "✅ PASS: Custom dictionary loaded with $DICT_SIZE compound words"
else
    echo "⚠️  WARNING: Custom dictionary size is $DICT_SIZE"
fi

# Test 13: Test API documentation
echo "Test 13: Testing API documentation..."
if curl -s -f "http://localhost:8001/docs" > /dev/null; then
    echo "✅ PASS: API documentation is accessible"
else
    echo "❌ FAIL: API documentation is not accessible"
fi

echo ""
echo "🎉 All Tests Completed!"
echo "======================="
echo "✅ Thai Tokenizer is running on: http://localhost:8001"
echo "✅ API Documentation: http://localhost:8001/docs"
echo "✅ Health Check: http://localhost:8001/health"
echo "✅ Connected to MeiliSearch: http://localhost:7700"
echo ""
echo "🧪 Manual test command:"
echo 'curl -X POST "http://localhost:8001/api/v1/tokenize" \'
echo '  -H "Content-Type: application/json" \'
echo '  -d '"'"'{"text": "ร้านอาหารญี่ปุ่นเสิร์ฟวากาเมะและซาชิมิ"}'"'"
echo ""
echo "Expected result: วากาเมะ and ซาชิมิ should be single tokens!"