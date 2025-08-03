#!/bin/bash

# Assess Reindexing Need Script
# This script helps determine if you need to reindex existing Meilisearch documents

echo "🔍 Assessing Reindexing Need for Existing Meilisearch Indexes"
echo "============================================================"

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
INDEX_NAME="thai_documents"

# Test compound words
COMPOUND_WORDS=("วากาเมะ" "ซูชิ" "เทมปุระ" "ราเมน" "อุด้ง" "โซบะ" "มิโซะ" "โชยุ")

print_info "Checking Meilisearch connection..."

# Test Meilisearch connectivity
if ! curl -s --connect-timeout 5 "$MEILISEARCH_HOST/health" > /dev/null; then
    print_error "Cannot connect to Meilisearch at $MEILISEARCH_HOST"
    exit 1
fi

print_success "✅ Connected to Meilisearch"

# Get index statistics
print_info "Getting index statistics..."
INDEX_STATS=$(curl -s -X GET "$MEILISEARCH_HOST/indexes/$INDEX_NAME/stats" \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY")

if echo "$INDEX_STATS" | grep -q "numberOfDocuments"; then
    DOC_COUNT=$(echo "$INDEX_STATS" | grep -o '"numberOfDocuments":[0-9]*' | cut -d':' -f2)
    print_info "Index contains $DOC_COUNT documents"
else
    print_error "Could not get index statistics"
    echo "$INDEX_STATS"
    exit 1
fi

echo ""
print_info "=== ASSESSMENT RESULTS ==="

# Assessment 1: Index size
print_info "1. Index Size Assessment"
if [ "$DOC_COUNT" -lt 1000 ]; then
    print_success "✅ Small index ($DOC_COUNT docs) - Full reindexing is feasible"
    SIZE_RECOMMENDATION="FULL_REINDEX"
elif [ "$DOC_COUNT" -lt 10000 ]; then
    print_warning "⚠️ Medium index ($DOC_COUNT docs) - Selective reindexing recommended"
    SIZE_RECOMMENDATION="SELECTIVE_REINDEX"
else
    print_warning "⚠️ Large index ($DOC_COUNT docs) - Consider no reindexing"
    SIZE_RECOMMENDATION="NO_REINDEX"
fi

echo ""

# Assessment 2: Compound word search quality
print_info "2. Compound Word Search Quality Assessment"
SEARCH_QUALITY_SCORE=0
TOTAL_TESTS=0

for word in "${COMPOUND_WORDS[@]}"; do
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
    
    # Search for the compound word
    SEARCH_RESULT=$(curl -s -X POST "$MEILISEARCH_HOST/indexes/$INDEX_NAME/search" \
        -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
        -d "{\"q\": \"$word\", \"limit\": 5}")
    
    if echo "$SEARCH_RESULT" | grep -q '"hits"'; then
        HIT_COUNT=$(echo "$SEARCH_RESULT" | grep -o '"hits":\[[^]]*\]' | grep -o '{"' | wc -l)
        if [ "$HIT_COUNT" -gt 0 ]; then
            print_success "✅ '$word' found $HIT_COUNT results"
            SEARCH_QUALITY_SCORE=$((SEARCH_QUALITY_SCORE + 1))
        else
            print_warning "⚠️ '$word' found 0 results"
        fi
    else
        print_error "❌ Search failed for '$word'"
    fi
done

SEARCH_QUALITY_PERCENT=$((SEARCH_QUALITY_SCORE * 100 / TOTAL_TESTS))
print_info "Search quality score: $SEARCH_QUALITY_SCORE/$TOTAL_TESTS ($SEARCH_QUALITY_PERCENT%)"

if [ "$SEARCH_QUALITY_PERCENT" -ge 80 ]; then
    print_success "✅ Good search quality - No reindexing needed"
    QUALITY_RECOMMENDATION="NO_REINDEX"
elif [ "$SEARCH_QUALITY_PERCENT" -ge 50 ]; then
    print_warning "⚠️ Moderate search quality - Selective reindexing recommended"
    QUALITY_RECOMMENDATION="SELECTIVE_REINDEX"
else
    print_error "❌ Poor search quality - Full reindexing recommended"
    QUALITY_RECOMMENDATION="FULL_REINDEX"
fi

echo ""

# Assessment 3: Test new tokenization vs existing
print_info "3. Tokenization Quality Comparison"

# Test current tokenization
TEST_TEXT="ฉันกินสาหร่ายวากาเมะที่ร้านซูชิ"
print_info "Testing tokenization of: $TEST_TEXT"

NEW_TOKENIZATION=$(curl -s -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$TEST_TEXT\"}")

if echo "$NEW_TOKENIZATION" | grep -q '"tokens"'; then
    NEW_TOKENS=$(echo "$NEW_TOKENIZATION" | grep -o '"tokens":\[[^]]*\]')
    print_success "✅ New tokenization: $NEW_TOKENS"
    
    # Check if วากาเมะ is preserved as compound
    if echo "$NEW_TOKENIZATION" | grep -q '"วากาเมะ"'; then
        print_success "✅ Compound words properly preserved"
        TOKENIZATION_QUALITY="GOOD"
    else
        print_warning "⚠️ Compound words not properly preserved"
        TOKENIZATION_QUALITY="POOR"
    fi
else
    print_error "❌ Could not test new tokenization"
    TOKENIZATION_QUALITY="UNKNOWN"
fi

echo ""

# Final recommendation
print_info "=== FINAL RECOMMENDATION ==="

# Decision matrix
if [ "$SIZE_RECOMMENDATION" = "NO_REINDEX" ] || [ "$QUALITY_RECOMMENDATION" = "NO_REINDEX" ]; then
    FINAL_RECOMMENDATION="NO_REINDEX"
elif [ "$SIZE_RECOMMENDATION" = "FULL_REINDEX" ] && [ "$QUALITY_RECOMMENDATION" = "FULL_REINDEX" ]; then
    FINAL_RECOMMENDATION="FULL_REINDEX"
else
    FINAL_RECOMMENDATION="SELECTIVE_REINDEX"
fi

case "$FINAL_RECOMMENDATION" in
    "NO_REINDEX")
        print_success "🎯 RECOMMENDATION: No reindexing needed"
        echo ""
        print_info "Reasons:"
        echo "• Your index size is manageable and search quality is acceptable"
        echo "• New documents will automatically use improved tokenization"
        echo "• Existing search functionality will continue to work"
        echo ""
        print_info "Next steps:"
        echo "1. Deploy the updated tokenizer: ./deploy.sh production"
        echo "2. Test with new documents to verify improved tokenization"
        echo "3. Monitor search quality over time"
        ;;
    "SELECTIVE_REINDEX")
        print_warning "🎯 RECOMMENDATION: Selective reindexing"
        echo ""
        print_info "Reasons:"
        echo "• Some compound words are not searching properly"
        echo "• Index size makes selective reindexing feasible"
        echo "• Targeted improvement will provide better search quality"
        echo ""
        print_info "Next steps:"
        echo "1. Deploy the updated tokenizer: ./deploy.sh production"
        echo "2. Run selective reindexing script for compound words"
        echo "3. Test search quality for improved compound words"
        ;;
    "FULL_REINDEX")
        print_error "🎯 RECOMMENDATION: Full reindexing"
        echo ""
        print_info "Reasons:"
        echo "• Search quality is poor for compound words"
        echo "• Index size is small enough for full reindexing"
        echo "• Consistent tokenization across all documents is needed"
        echo ""
        print_info "Next steps:"
        echo "1. Backup your current index"
        echo "2. Deploy the updated tokenizer: ./deploy.sh production"
        echo "3. Run full reindexing script"
        echo "4. Verify search quality improvement"
        ;;
esac

echo ""
print_info "=== DETAILED ASSESSMENT SUMMARY ==="
echo "Index size: $DOC_COUNT documents"
echo "Search quality: $SEARCH_QUALITY_PERCENT% ($SEARCH_QUALITY_SCORE/$TOTAL_TESTS compound words found)"
echo "Tokenization quality: $TOKENIZATION_QUALITY"
echo "Size recommendation: $SIZE_RECOMMENDATION"
echo "Quality recommendation: $QUALITY_RECOMMENDATION"
echo "Final recommendation: $FINAL_RECOMMENDATION"

echo ""
print_info "For detailed reindexing instructions, see: docs/EXISTING_INDEX_MANAGEMENT.md"

# Create a summary file
SUMMARY_FILE="reindexing_assessment_$(date +%Y%m%d_%H%M%S).txt"
cat > "$SUMMARY_FILE" << EOF
Reindexing Assessment Summary
Generated: $(date)

Index Statistics:
- Document count: $DOC_COUNT
- Search quality: $SEARCH_QUALITY_PERCENT% ($SEARCH_QUALITY_SCORE/$TOTAL_TESTS)
- Tokenization quality: $TOKENIZATION_QUALITY

Recommendations:
- Size-based: $SIZE_RECOMMENDATION
- Quality-based: $QUALITY_RECOMMENDATION
- Final: $FINAL_RECOMMENDATION

Next Steps:
$(case "$FINAL_RECOMMENDATION" in
    "NO_REINDEX") echo "1. Deploy updated tokenizer
2. Test with new documents
3. Monitor search quality" ;;
    "SELECTIVE_REINDEX") echo "1. Deploy updated tokenizer
2. Run selective reindexing
3. Test compound word searches" ;;
    "FULL_REINDEX") echo "1. Backup current index
2. Deploy updated tokenizer
3. Run full reindexing
4. Verify improvements" ;;
esac)
EOF

print_info "Assessment summary saved to: $SUMMARY_FILE"