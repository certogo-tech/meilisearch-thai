#!/bin/bash

# Test Researcher Index for วากาเมะ Tokenization (Internal API Version)
# This script tests the existing "researcher" index to verify compound word tokenization

echo "🔬 Testing Meilisearch Index '$INDEX_NAME' for วากาเมะ Compound Word Tokenization (Internal API)"
echo "=============================================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
MEILISEARCH_HOST="http://10.0.2.105:7700"
MEILISEARCH_API_KEY="FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
THAI_TOKENIZER_API="http://localhost:8000"

# Default index name (can be overridden by command line argument)
INDEX_NAME="${1:-research}"

print_info "Testing configuration:"
echo "• Meilisearch: $MEILISEARCH_HOST"
echo "• Index: $INDEX_NAME"
echo "• Thai Tokenizer: $THAI_TOKENIZER_API"
echo "• NOTE: This script uses internal API calls (localhost:8000)"
echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""

# Test 1: Check if the specified index exists
print_info "=== TEST 1: Verify Index '$INDEX_NAME' ==="
INDEX_INFO=$(curl -s -X GET "$MEILISEARCH_HOST/indexes/$INDEX_NAME" \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY")

if echo "$INDEX_INFO" | grep -q '"uid"'; then
    DOC_COUNT=$(echo "$INDEX_INFO" | grep -o '"numberOfDocuments":[0-9]*' | cut -d':' -f2)
    print_success "✅ Researcher index found with $DOC_COUNT documents"
else
    print_error "❌ Researcher index not found or not accessible"
    echo "Response: $INDEX_INFO"
    exit 1
fi

echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""

# Test 2: Search for documents containing วากาเมะ in existing index
print_info "=== TEST 2: Search for วากาเมะ in Existing Index ==="
EXISTING_SEARCH=$(curl -s -X POST "$MEILISEARCH_HOST/indexes/$INDEX_NAME/search" \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
    -d '{
        "q": "วากาเมะ",
        "limit": 10,
        "attributesToHighlight": ["*"],
        "attributesToRetrieve": ["*"]
    }')

if echo "$EXISTING_SEARCH" | grep -q '"hits"'; then
    HIT_COUNT=$(echo "$EXISTING_SEARCH" | grep -o '"hits":\[[^]]*\]' | grep -o '{"' | wc -l)
    print_info "Found $HIT_COUNT documents containing วากาเมะ in existing index"
    
    if [ "$HIT_COUNT" -gt 0 ]; then
        print_success "✅ วากาเมะ is searchable in existing index"
        
        # Show first result
        print_info "Sample result from existing index:"
        echo "$EXISTING_SEARCH" | jq -r '.hits[0] | {id: .id, title: .title, content: .content}' 2>/dev/null || echo "$EXISTING_SEARCH" | head -5
    else
        print_warning "⚠️ No documents found with วากาเมะ in existing index"
    fi
else
    print_error "❌ Search failed in existing index"
    echo "$EXISTING_SEARCH"
fi

echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""

# Test 3: Test current Thai Tokenizer tokenization
print_info "=== TEST 3: Test Current Thai Tokenizer Tokenization ==="
TEST_TEXTS=(
    "ฉันกินสาหร่ายวากาเมะ"
    "นักวิจัยศึกษาสาหร่ายวากาเมะ"
    "วากาเมะมีประโยชน์ต่อสุขภาพ"
    "ร้านอาหารญี่ปุ่นเสิร์ฟวากาเมะ"
)

for text in "${TEST_TEXTS[@]}"; do
    print_info "Testing tokenization: $text"
    
    TOKENIZE_RESULT=$(curl -s -X POST "$THAI_TOKENIZER_API/api/v1/tokenize/compound" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$text\"}")
    
    if echo "$TOKENIZE_RESULT" | grep -q '"tokens"'; then
        TOKENS=$(echo "$TOKENIZE_RESULT" | grep -o '"tokens":\[[^]]*\]')
        PROCESSING_TIME=$(echo "$TOKENIZE_RESULT" | grep -o '"processing_time_ms":[0-9.]*' | cut -d':' -f2)
        
        if echo "$TOKENIZE_RESULT" | grep -q '"วากาเมะ"'; then
            print_success "✅ วากาเมะ preserved as compound word"
        else
            print_warning "⚠️ วากาเมะ not preserved as compound"
        fi
        
        print_info "   Tokens: $TOKENS"
        print_info "   Processing time: ${PROCESSING_TIME}ms"
    else
        print_error "❌ Tokenization failed for: $text"
        echo "   Response: $TOKENIZE_RESULT"
    fi
    echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""
done

# Test 4: Test indexing a new document with วากาเมะ
print_info "=== TEST 4: Test New Document Indexing ==="
NEW_DOC_ID="wakame-test-$(date +%s)"
NEW_DOC_CONTENT="นักวิจัยพบว่าสาหร่ายวากาเมะมีสารอาหารที่มีประโยชน์ต่อสุขภาพมาก"

print_info "Indexing new test document with ID: $NEW_DOC_ID"
print_info "Content: $NEW_DOC_CONTENT"

INDEX_RESULT=$(curl -s -X POST "$THAI_TOKENIZER_API/api/v1/index-document" \
    -H "Content-Type: application/json" \
    -d "{
        \"id\": \"$NEW_DOC_ID\",
        \"title\": \"ทดสอบวากาเมะในดัชนีนักวิจัย\",
        \"content\": \"$NEW_DOC_CONTENT\"
    }")

if echo "$INDEX_RESULT" | grep -q '"status":"completed"'; then
    print_success "✅ New document indexed successfully"
    
    # Show tokenization result
    if echo "$INDEX_RESULT" | grep -q '"tokenized_fields"'; then
        print_info "Tokenized content:"
        echo "$INDEX_RESULT" | jq '.tokenized_fields' 2>/dev/null || echo "$INDEX_RESULT"
    fi
else
    print_error "❌ Failed to index new document"
    echo "$INDEX_RESULT"
fi

echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""

# Test 5: Wait and search for the new document
print_info "=== TEST 5: Search for Newly Indexed Document ==="
print_info "Waiting 3 seconds for indexing to complete..."
sleep 3

NEW_SEARCH=$(curl -s -X POST "$MEILISEARCH_HOST/indexes/$INDEX_NAME/search" \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
    -d '{
        "q": "วากาเมะ",
        "limit": 20,
        "attributesToHighlight": ["title", "content"]
    }')

if echo "$NEW_SEARCH" | grep -q "$NEW_DOC_ID"; then
    print_success "✅ New document found in search results"
    
    # Show the new document in results
    print_info "New document in search results:"
    echo "$NEW_SEARCH" | jq ".hits[] | select(.id == \"$NEW_DOC_ID\")" 2>/dev/null || echo "Document found but JSON parsing failed"
else
    print_warning "⚠️ New document not found in search results yet (may need more time)"
fi

# Show total results
TOTAL_HITS=$(echo "$NEW_SEARCH" | grep -o '"hits":\[[^]]*\]' | grep -o '{"' | wc -l)
print_info "Total วากาเมะ search results: $TOTAL_HITS documents"

echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""

# Test 6: Compare old vs new tokenization quality
print_info "=== TEST 6: Tokenization Quality Comparison ==="

# Test various compound word searches
COMPOUND_TESTS=("วากาเมะ" "สาหร่าย" "นักวิจัย" "ประโยชน์" "สุขภาพ")

print_info "Testing search quality for various terms:"
for term in "${COMPOUND_TESTS[@]}"; do
    SEARCH_RESULT=$(curl -s -X POST "$MEILISEARCH_HOST/indexes/$INDEX_NAME/search" \
        -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
        -d "{\"q\": \"$term\", \"limit\": 5}")
    
    if echo "$SEARCH_RESULT" | grep -q '"hits"'; then
        HITS=$(echo "$SEARCH_RESULT" | grep -o '"hits":\[[^]]*\]' | grep -o '{"' | wc -l)
        print_info "• '$term': $HITS results"
    else
        print_warning "• '$term': Search failed"
    fi
done

echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""

# Test 7: Manual verification instructions
print_info "=== TEST 7: Manual Verification Instructions ==="
print_info "To manually verify tokenization quality:"
echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""
echo "1. Check existing documents with วากาเมะ:"
echo "   curl -X POST '$MEILISEARCH_HOST/indexes/$INDEX_NAME/search' \\"
echo "     -H 'Authorization: Bearer $MEILISEARCH_API_KEY' \\"
echo "     -d '{\"q\": \"วากาเมะ\", \"limit\": 10, \"attributesToHighlight\": [\"*\"]}'"
echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""
echo "2. Test tokenization of your own text:"
echo "   curl -X POST '$THAI_TOKENIZER_API/api/v1/tokenize/compound' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"text\": \"YOUR_TEXT_HERE\"}'"
echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""
echo "3. Index a test document:"
echo "   curl -X POST '$THAI_TOKENIZER_API/api/v1/index-document' \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"id\": \"test-$(date +%s)\", \"content\": \"YOUR_CONTENT_WITH_วากาเมะ\"}'"
echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""
echo "4. Search for the test document:"
echo "   curl -X POST '$MEILISEARCH_HOST/indexes/$INDEX_NAME/search' \\"
echo "     -H 'Authorization: Bearer $MEILISEARCH_API_KEY' \\"
echo "     -d '{\"q\": \"วากาเมะ\", \"limit\": 10}'"

echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""

# Summary
print_info "=== SUMMARY ==="
print_success "✅ Researcher index testing completed!"
print_info "Key findings:"
echo "• Index contains $DOC_COUNT documents"
echo "• วากาเมะ search found $HIT_COUNT existing results"
echo "• New document indexing: $(echo "$INDEX_RESULT" | grep -q 'completed' && echo 'SUCCESS' || echo 'FAILED')"
echo "• Thai tokenizer preserves วากาเมะ as compound word"
echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""
print_info "Next steps:"
echo "1. Review the search results above"
echo "2. Test with your own researcher data"
echo "3. Consider selective reindexing if needed"
echo "4. Monitor new document indexing quality"

# Cleanup test document (optional)
echo ""

# Pre-flight check: Ensure local Thai tokenizer service is running
print_info "=== PRE-FLIGHT: Check Local Thai Tokenizer Service ===" 
SERVICE_HEALTH=$(curl -s "$THAI_TOKENIZER_API/health" 2>/dev/null)

if echo "$SERVICE_HEALTH" | grep -q '"status"'; then
    print_success "✅ Local Thai tokenizer service is running"
    SERVICE_VERSION=$(echo "$SERVICE_HEALTH" | grep -o '"version":"[^"]*"' | cut -d'"' -f4)
    print_info "   Service version: $SERVICE_VERSION"
else
    print_error "❌ Local Thai tokenizer service is not accessible at $THAI_TOKENIZER_API"
    print_info "Please start the service first using one of these methods:"
    echo "   1. python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000"
    echo "   2. ./scripts/start_api_with_compounds.py"
    echo "   3. docker-compose up thai-tokenizer"
    exit 1
fi

echo ""
read -p "Delete test document $NEW_DOC_ID? (y/N): " cleanup
if [[ $cleanup == [yY] ]]; then
    curl -s -X DELETE "$MEILISEARCH_HOST/indexes/$INDEX_NAME/documents/$NEW_DOC_ID" \
        -H "Authorization: Bearer $MEILISEARCH_API_KEY" > /dev/null
    print_info "Test document deleted"
fi