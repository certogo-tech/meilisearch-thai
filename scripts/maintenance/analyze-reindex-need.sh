#!/bin/bash

# Analyze Reindexing Need for MeiliSearch Indexes
# This script checks which indexes need reindexing for Thai tokenization

echo "🔍 Analyzing MeiliSearch Indexes for Reindexing Need"
echo "===================================================="

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

# Configuration - can be overridden by environment variables
MEILISEARCH_HOST="${MEILISEARCH_HOST:-http://10.0.2.105:7700}"
MEILISEARCH_API_KEY="${MEILISEARCH_API_KEY:-FKjPKTmFnCl7EPg6YLula1DC6n5mHqId}"

print_info "Connecting to MeiliSearch: $MEILISEARCH_HOST"

# Test basic connectivity and API key
print_info "Testing API connectivity..."
HEALTH_CHECK=$(curl -s "$MEILISEARCH_HOST/health" 2>/dev/null)
if echo "$HEALTH_CHECK" | grep -q "available"; then
    print_success "MeiliSearch is healthy"
else
    print_warning "MeiliSearch health check failed: $HEALTH_CHECK"
fi

echo ""

# Get all indexes
print_info "=== DISCOVERING INDEXES ==="
INDEXES_RESPONSE=$(curl -s -X GET "$MEILISEARCH_HOST/indexes" \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY" 2>/dev/null)

if [ $? -ne 0 ] || [ -z "$INDEXES_RESPONSE" ]; then
    print_error "Failed to fetch indexes from MeiliSearch"
    exit 1
fi

ALL_INDEXES=$(echo "$INDEXES_RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'error' in data:
        print(f'API_ERROR:{data.get(\"message\", \"Unknown error\")}', file=sys.stderr)
        sys.exit(1)
    for idx in data.get('results', []):
        print(f'{idx[\"uid\"]}:{idx.get(\"numberOfDocuments\", 0)}')
except Exception as e:
    print(f'PARSE_ERROR:{e}', file=sys.stderr)
    sys.exit(1)
")

if echo "$ALL_INDEXES" | grep -q "ERROR:"; then
    ERROR_MSG=$(echo "$ALL_INDEXES" | grep "ERROR:" | cut -d':' -f2-)
    print_error "Failed to fetch indexes: $ERROR_MSG"
    exit 1
fi

if [ -z "$ALL_INDEXES" ]; then
    print_warning "No indexes found"
    exit 0
fi

print_success "Found indexes:"
echo "$ALL_INDEXES" | while IFS=':' read -r index_name doc_count; do
    echo "  • $index_name ($doc_count documents)"
done

echo ""

# Analyze each index
print_info "=== ANALYZING TOKENIZATION STATUS ==="

# Create temporary file for analysis results
ANALYSIS_TEMP=$(mktemp "/tmp/analysis_results_XXXXXX.txt")
trap 'rm -f "$ANALYSIS_TEMP"' EXIT
> "$ANALYSIS_TEMP"

# Process each index (avoid subshell by using process substitution)
while IFS=':' read -r INDEX_NAME DOC_COUNT; do
    if [ -n "$INDEX_NAME" ] && [ "$DOC_COUNT" -gt 0 ]; then
        print_info "Analyzing index: $INDEX_NAME ($DOC_COUNT documents)"
        
        # Sample a few documents to check for tokenized_content field
        SAMPLE_DOCS=$(curl -s -X GET "$MEILISEARCH_HOST/indexes/$INDEX_NAME/documents" \
            -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
            -d '{"limit": 5}' 2>/dev/null)
        
        if [ $? -ne 0 ] || [ -z "$SAMPLE_DOCS" ]; then
            print_error "  ❌ Failed to fetch documents from index $INDEX_NAME"
            echo "ERROR:$INDEX_NAME" >> "$ANALYSIS_TEMP"
            continue
        fi
        
        # Check if documents have tokenized_content field
        HAS_TOKENIZED=$(echo "$SAMPLE_DOCS" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    docs = data.get('results', [])
    if not docs:
        print('NO_DOCS')
    else:
        has_tokenized = any('tokenized_content' in doc for doc in docs)
        has_thai = any(
            any('\\u0e00' <= c <= '\\u0e7f' for c in str(doc.get('content', '') + doc.get('title', '')))
            for doc in docs
        )
        print(f'TOKENIZED:{has_tokenized}:THAI:{has_thai}')
except Exception as e:
    print(f'ERROR:{e}')
")
        
        if echo "$HAS_TOKENIZED" | grep -q "ERROR:"; then
            print_error "  ❌ Failed to analyze documents"
            echo "ERROR:$INDEX_NAME" >> "$ANALYSIS_TEMP"
            continue
        fi
        
        if echo "$HAS_TOKENIZED" | grep -q "NO_DOCS"; then
            print_info "  ℹ️ No documents to analyze"
            echo "NO_DOCS:$INDEX_NAME" >> "$ANALYSIS_TEMP"
            continue
        fi
        
        # Parse results
        HAS_TOKENIZED_FIELD=$(echo "$HAS_TOKENIZED" | cut -d':' -f2 2>/dev/null || echo "False")
        HAS_THAI_CONTENT=$(echo "$HAS_TOKENIZED" | cut -d':' -f4 2>/dev/null || echo "False")
        
        if [ "$HAS_TOKENIZED_FIELD" = "True" ]; then
            print_success "  ✅ Already has tokenized_content field"
            echo "ALREADY_TOKENIZED:$INDEX_NAME" >> "$ANALYSIS_TEMP"
        elif [ "$HAS_THAI_CONTENT" = "True" ]; then
            print_warning "  ⚠️ Has Thai content but missing tokenized_content"
            print_info "     → NEEDS REINDEXING for compound word search"
            echo "NEEDS_REINDEXING:$INDEX_NAME" >> "$ANALYSIS_TEMP"
        else
            print_info "  ℹ️ No Thai content detected, tokenization not needed"
            echo "NO_THAI:$INDEX_NAME" >> "$ANALYSIS_TEMP"
        fi
        
        # Test a compound word search to see current quality
        COMPOUND_TEST=$(curl -s -X POST "$MEILISEARCH_HOST/indexes/$INDEX_NAME/search" \
            -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
            -d '{"q": "วากาเมะ", "limit": 3}' 2>/dev/null)
        
        COMPOUND_HITS=$(echo "$COMPOUND_TEST" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    print(len(data.get('hits', [])))
except:
    print(0)
")
        
        if [ "$COMPOUND_HITS" -gt 0 ]; then
            print_info "  🔍 Found $COMPOUND_HITS results for 'วากาเมะ'"
        else
            print_info "  🔍 No results for 'วากาเมะ' (may need reindexing)"
        fi
        
        echo ""
    fi
done < <(echo "$ALL_INDEXES")

# Read the summary (since variables don't persist from subshell)
SUMMARY_STATS=$(echo "$ALL_INDEXES" | python3 -c "
import sys
total_indexes = 0
total_docs = 0
for line in sys.stdin:
    if ':' in line:
        index_name, doc_count = line.strip().split(':', 1)
        if index_name and doc_count.isdigit():
            total_indexes += 1
            total_docs += int(doc_count)

print(f'{total_indexes}:{total_docs}')
")

TOTAL_INDEXES=$(echo "$SUMMARY_STATS" | cut -d':' -f1)
TOTAL_DOCS=$(echo "$SUMMARY_STATS" | cut -d':' -f2)

# Display summary
print_info "=== SUMMARY ==="
echo "📊 Analysis Results:"
echo "  • Total indexes: $TOTAL_INDEXES"
echo "  • Total documents: $TOTAL_DOCS"
echo ""

# Count indexes that need reindexing by checking the analysis output
if [ -f "$ANALYSIS_TEMP" ]; then
    NEEDS_REINDEXING=$(grep -c "NEEDS_REINDEXING:" "$ANALYSIS_TEMP" 2>/dev/null)
    ALREADY_TOKENIZED=$(grep -c "ALREADY_TOKENIZED:" "$ANALYSIS_TEMP" 2>/dev/null)
else
    NEEDS_REINDEXING=0
    ALREADY_TOKENIZED=0
fi

# Clean up any newlines and ensure variables are integers
NEEDS_REINDEXING=$(echo "$NEEDS_REINDEXING" | tr -d '\n\r' | sed 's/[^0-9]//g')
ALREADY_TOKENIZED=$(echo "$ALREADY_TOKENIZED" | tr -d '\n\r' | sed 's/[^0-9]//g')

# Set defaults if empty
NEEDS_REINDEXING=${NEEDS_REINDEXING:-0}
ALREADY_TOKENIZED=${ALREADY_TOKENIZED:-0}

echo "🔄 Reindexing Status:"
echo "  • Indexes needing reindexing: $NEEDS_REINDEXING"
echo "  • Indexes already tokenized: $ALREADY_TOKENIZED"
echo ""

# Recommendations
print_info "=== RECOMMENDATIONS ==="

if [ "${NEEDS_REINDEXING:-0}" -eq 0 ]; then
    print_success "✅ No reindexing needed!"
    echo "  All indexes either have tokenized_content or don't contain Thai text."
    echo ""
    print_info "Next steps:"
    echo "  1. Test search quality: ./scripts/testing/test-all-indexes.sh"
    echo "  2. Verify compound words work: search for วากาเมะ, รูเมน, ซูชิ"
    
elif [ "${NEEDS_REINDEXING:-0}" -eq "${TOTAL_INDEXES:-0}" ]; then
    print_warning "🔄 Full reindexing recommended!"
    echo "  All indexes need reindexing for proper Thai compound word search."
    echo ""
    print_info "Recommended commands:"
    echo "  1. Preview changes: ./scripts/maintenance/reindex-all-data.sh --dry-run --all"
    echo "  2. Reindex all: ./scripts/maintenance/reindex-all-data.sh --all"
    
else
    print_warning "⚠️ Partial reindexing needed!"
    echo "  Some indexes need reindexing for Thai compound word search."
    echo ""
    print_info "Recommended approach:"
    echo "  1. Preview: ./scripts/maintenance/reindex-all-data.sh --dry-run --all"
    echo "  2. Reindex specific indexes that need it"
    echo ""
    print_info "Indexes that likely need reindexing:"
    grep "NEEDS_REINDEXING:" "$ANALYSIS_TEMP" 2>/dev/null | cut -d':' -f2 | sed 's/^/  • /' || echo "  (Check analysis output above)"
fi

echo ""

# Performance estimates
if [ "${NEEDS_REINDEXING:-0}" -gt 0 ]; then
    print_info "=== PERFORMANCE ESTIMATES ==="
    
    # Estimate processing time (conservative: 100ms per document)
    ESTIMATED_SECONDS=$((TOTAL_DOCS / 10))
    ESTIMATED_MINUTES=$((ESTIMATED_SECONDS / 60))
    
    echo "⏱️ Estimated reindexing time:"
    echo "  • Processing rate: ~10 documents/second"
    echo "  • Total time: ~$ESTIMATED_MINUTES minutes"
    echo "  • Backup creation: +2-5 minutes per index"
    echo ""
    
    print_info "💡 Tips for faster reindexing:"
    echo "  • Use --no-backup to skip backup creation (faster but riskier)"
    echo "  • Reindex during low-traffic periods"
    echo "  • Monitor system resources during processing"
fi

# Cleanup handled by trap

print_success "🎉 Analysis completed!"
echo ""
print_info "Next steps:"
echo "  1. Review recommendations above"
echo "  2. Run dry-run to preview changes"
echo "  3. Perform reindexing if needed"
echo "  4. Test search quality after reindexing"