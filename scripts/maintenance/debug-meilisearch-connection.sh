#!/bin/bash

# Debug MeiliSearch Connection and Index Status
# This script helps diagnose why indexes might appear empty

echo "🔍 MeiliSearch Connection Diagnostic"
echo "===================================="

# Configuration
MEILISEARCH_HOST="http://10.0.2.105:7700"
MEILISEARCH_API_KEY="FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Test 1: Basic connectivity
print_info "=== TEST 1: Basic Connectivity ==="
echo "Testing: $MEILISEARCH_HOST"

if curl -s --connect-timeout 5 "$MEILISEARCH_HOST/health" > /dev/null; then
    HEALTH=$(curl -s "$MEILISEARCH_HOST/health")
    print_success "✅ MeiliSearch is reachable"
    echo "Health status: $HEALTH"
else
    print_error "❌ Cannot connect to MeiliSearch"
    echo "Please check:"
    echo "  1. Is MeiliSearch running?"
    echo "  2. Is the host correct: $MEILISEARCH_HOST"
    echo "  3. Are there firewall issues?"
    exit 1
fi

echo ""

# Test 2: API Key authentication
print_info "=== TEST 2: API Key Authentication ==="

AUTH_TEST=$(curl -s -w "%{http_code}" -o /tmp/auth_test.json \
    -X GET "$MEILISEARCH_HOST/indexes" \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY")

if [ "$AUTH_TEST" = "200" ]; then
    print_success "✅ API key authentication successful"
else
    print_error "❌ API key authentication failed (HTTP $AUTH_TEST)"
    echo "Response:"
    cat /tmp/auth_test.json 2>/dev/null || echo "(no response body)"
    echo ""
    echo "Please check your API key: $MEILISEARCH_API_KEY"
    exit 1
fi

echo ""

# Test 3: Raw index data
print_info "=== TEST 3: Raw Index Information ==="

RAW_INDEXES=$(curl -s -X GET "$MEILISEARCH_HOST/indexes" \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY")

echo "Raw response:"
echo "$RAW_INDEXES" | jq . 2>/dev/null || echo "$RAW_INDEXES"

echo ""

# Test 4: Parse and analyze each index
print_info "=== TEST 4: Detailed Index Analysis ==="

echo "$RAW_INDEXES" | jq -r '.results[]? | "\(.uid):\(.numberOfDocuments // 0)"' 2>/dev/null | while IFS=':' read -r index_name doc_count; do
    if [ -n "$index_name" ]; then
        print_info "Index: $index_name"
        echo "  Document count: $doc_count"
        
        # Get detailed index info
        INDEX_DETAILS=$(curl -s -X GET "$MEILISEARCH_HOST/indexes/$index_name" \
            -H "Authorization: Bearer $MEILISEARCH_API_KEY")
        
        echo "  Created: $(echo "$INDEX_DETAILS" | jq -r '.createdAt // "unknown"' 2>/dev/null)"
        echo "  Updated: $(echo "$INDEX_DETAILS" | jq -r '.updatedAt // "unknown"' 2>/dev/null)"
        echo "  Primary key: $(echo "$INDEX_DETAILS" | jq -r '.primaryKey // "none"' 2>/dev/null)"
        
        # Try to get a sample document
        if [ "$doc_count" -gt 0 ]; then
            SAMPLE_DOC=$(curl -s -X GET "$MEILISEARCH_HOST/indexes/$index_name/documents?limit=1" \
                -H "Authorization: Bearer $MEILISEARCH_API_KEY")
            
            if echo "$SAMPLE_DOC" | jq -e '.results[0]' > /dev/null 2>&1; then
                echo "  Sample document fields: $(echo "$SAMPLE_DOC" | jq -r '.results[0] | keys | join(", ")' 2>/dev/null)"
                
                # Check for Thai content
                CONTENT=$(echo "$SAMPLE_DOC" | jq -r '.results[0] | .content // .title // ""' 2>/dev/null)
                if echo "$CONTENT" | grep -q '[ก-๙]'; then
                    echo "  ✅ Contains Thai content"
                else
                    echo "  ❌ No Thai content detected"
                fi
                
                # Check for tokenized_content field
                if echo "$SAMPLE_DOC" | jq -e '.results[0].tokenized_content' > /dev/null 2>&1; then
                    echo "  ✅ Has tokenized_content field"
                else
                    echo "  ❌ Missing tokenized_content field"
                fi
            else
                echo "  ⚠️ Could not retrieve sample document"
            fi
        else
            echo "  ℹ️ Index is empty"
        fi
        
        echo ""
    fi
done

# Test 5: Search test
print_info "=== TEST 5: Search Functionality Test ==="

# Try searching in the research index
SEARCH_TEST=$(curl -s -X POST "$MEILISEARCH_HOST/indexes/research/search" \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
    -H "Content-Type: application/json" \
    -d '{"q": "", "limit": 5}')

if echo "$SEARCH_TEST" | jq -e '.hits' > /dev/null 2>&1; then
    HIT_COUNT=$(echo "$SEARCH_TEST" | jq -r '.hits | length' 2>/dev/null)
    print_success "✅ Search endpoint working"
    echo "  Empty search returned $HIT_COUNT results"
    
    if [ "$HIT_COUNT" -gt 0 ]; then
        echo "  Sample result fields: $(echo "$SEARCH_TEST" | jq -r '.hits[0] | keys | join(", ")' 2>/dev/null)"
    fi
else
    print_warning "⚠️ Search test failed or returned unexpected format"
    echo "Response: $SEARCH_TEST"
fi

echo ""

# Test 6: Specific compound word search
print_info "=== TEST 6: Compound Word Search Test ==="

for index in "research" "faq" "training"; do
    print_info "Testing วากาเมะ search in $index..."
    
    COMPOUND_SEARCH=$(curl -s -X POST "$MEILISEARCH_HOST/indexes/$index/search" \
        -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"q": "วากาเมะ", "limit": 3}')
    
    if echo "$COMPOUND_SEARCH" | jq -e '.hits' > /dev/null 2>&1; then
        HIT_COUNT=$(echo "$COMPOUND_SEARCH" | jq -r '.hits | length' 2>/dev/null)
        if [ "$HIT_COUNT" -gt 0 ]; then
            print_success "  ✅ Found $HIT_COUNT results for วากาเมะ"
        else
            print_info "  ℹ️ No results for วากาเมะ (expected if no Thai content)"
        fi
    else
        print_warning "  ⚠️ Search failed: $COMPOUND_SEARCH"
    fi
done

echo ""

# Summary and recommendations
print_info "=== SUMMARY & RECOMMENDATIONS ==="

# Count total documents across all indexes
TOTAL_DOCS=$(echo "$RAW_INDEXES" | jq -r '[.results[]?.numberOfDocuments // 0] | add' 2>/dev/null || echo "0")

echo "📊 Summary:"
echo "  • Total indexes: $(echo "$RAW_INDEXES" | jq -r '.results | length' 2>/dev/null || echo "unknown")"
echo "  • Total documents: $TOTAL_DOCS"

if [ "$TOTAL_DOCS" -eq 0 ]; then
    print_warning "🤔 All indexes appear empty!"
    echo ""
    echo "Possible reasons:"
    echo "  1. Indexes were recently created but not populated"
    echo "  2. Documents were deleted or cleared"
    echo "  3. There's an indexing issue preventing document storage"
    echo "  4. Documents exist but numberOfDocuments is not updated"
    echo ""
    echo "Next steps:"
    echo "  1. Check if you have source data to index"
    echo "  2. Try indexing a test document"
    echo "  3. Check MeiliSearch logs for indexing errors"
    echo "  4. Verify your data import process"
else
    print_success "✅ Found $TOTAL_DOCS documents total"
    echo ""
    echo "Next steps:"
    echo "  1. Run reindexing analysis: ./scripts/maintenance/analyze-reindex-need.sh"
    echo "  2. Test compound word search quality"
    echo "  3. Consider reindexing if tokenized_content is missing"
fi

# Cleanup
rm -f /tmp/auth_test.json

print_success "🎉 Diagnostic completed!"