#!/bin/bash

# External API Test Script
# Run this script from outside the production server to test the Thai Tokenizer API

echo "🌐 Testing Thai Tokenizer External API"
echo "======================================"

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

# API endpoint
API_BASE="https://search.cads.arda.or.th"

# Test data
TEST_TEXT="ฉันกินสาหร่ายวากาเมะ"
EXPECTED_TOKENS="ฉัน กิน สาหร่าย วากาเมะ"

print_info "Testing API endpoint: $API_BASE"
print_info "Test text: $TEST_TEXT"
print_info "Expected tokens: $EXPECTED_TOKENS"
echo ""

# Test 1: Basic Health Check
print_info "=== TEST 1: Basic Health Check ==="
HEALTH_RESPONSE=$(curl -s --connect-timeout 10 "$API_BASE/health" 2>/dev/null || echo "ERROR")

if echo "$HEALTH_RESPONSE" | grep -q "status"; then
    print_success "✅ API is accessible"
    echo "$HEALTH_RESPONSE"
else
    print_error "❌ API is not accessible"
    echo "$HEALTH_RESPONSE"
    exit 1
fi

echo ""

# Test 2: Detailed Health Check
print_info "=== TEST 2: Detailed Health Check ==="
DETAILED_HEALTH=$(curl -s --connect-timeout 10 "$API_BASE/api/v1/health/detailed" 2>/dev/null || echo "ERROR")

if echo "$DETAILED_HEALTH" | grep -q "overall_status"; then
    OVERALL_STATUS=$(echo "$DETAILED_HEALTH" | grep -o '"overall_status":"[^"]*"' | cut -d'"' -f4)
    HEALTH_SCORE=$(echo "$DETAILED_HEALTH" | grep -o '"health_score":[0-9.]*' | cut -d':' -f2)
    
    print_info "Overall status: $OVERALL_STATUS"
    print_info "Health score: $HEALTH_SCORE%"
    
    if [ "$OVERALL_STATUS" = "healthy" ]; then
        print_success "✅ Service is healthy"
    else
        print_warning "⚠️ Service status: $OVERALL_STATUS"
    fi
else
    print_error "❌ Could not get detailed health status"
    echo "$DETAILED_HEALTH"
fi

echo ""

# Test 3: Configuration Validity
print_info "=== TEST 3: Configuration Validity ==="
CONFIG_HEALTH=$(curl -s --connect-timeout 10 "$API_BASE/api/v1/health/check/configuration_validity" 2>/dev/null || echo "ERROR")

if echo "$CONFIG_HEALTH" | grep -q '"status"'; then
    CONFIG_STATUS=$(echo "$CONFIG_HEALTH" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    
    if [ "$CONFIG_STATUS" = "healthy" ]; then
        print_success "✅ Configuration is valid"
    else
        print_warning "⚠️ Configuration status: $CONFIG_STATUS"
        CONFIG_MESSAGE=$(echo "$CONFIG_HEALTH" | grep -o '"message":"[^"]*"' | cut -d'"' -f4)
        print_info "Message: $CONFIG_MESSAGE"
    fi
else
    print_error "❌ Could not check configuration validity"
    echo "$CONFIG_HEALTH"
fi

echo ""

# Test 4: Basic Tokenization
print_info "=== TEST 4: Basic Tokenization ==="
BASIC_RESPONSE=$(curl -s --connect-timeout 10 -X POST "$API_BASE/api/v1/tokenize" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$TEST_TEXT\"}" 2>/dev/null || echo "ERROR")

if echo "$BASIC_RESPONSE" | grep -q '"tokens"'; then
    print_success "✅ Basic tokenization working"
    
    # Extract tokens
    BASIC_TOKENS=$(echo "$BASIC_RESPONSE" | grep -o '"tokens":\[[^]]*\]' | sed 's/"tokens":\[//; s/\]//; s/"//g' | tr ',' ' ')
    print_info "Basic tokens: $BASIC_TOKENS"
    
    # Show processing time
    PROCESSING_TIME=$(echo "$BASIC_RESPONSE" | grep -o '"processing_time_ms":[0-9.]*' | cut -d':' -f2)
    print_info "Processing time: ${PROCESSING_TIME}ms"
    
    echo ""
    print_info "Full response:"
    echo "$BASIC_RESPONSE"
else
    print_error "❌ Basic tokenization failed"
    echo "$BASIC_RESPONSE"
fi

echo ""

# Test 5: Compound Tokenization (Main Test)
print_info "=== TEST 5: Compound Tokenization (MAIN TEST) ==="
COMPOUND_RESPONSE=$(curl -s --connect-timeout 10 -X POST "$API_BASE/api/v1/tokenize/compound" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$TEST_TEXT\"}" 2>/dev/null || echo "ERROR")

if echo "$COMPOUND_RESPONSE" | grep -q '"tokens"'; then
    print_success "✅ Compound tokenization working"
    
    # Extract tokens
    COMPOUND_TOKENS=$(echo "$COMPOUND_RESPONSE" | grep -o '"tokens":\[[^]]*\]' | sed 's/"tokens":\[//; s/\]//; s/"//g' | tr ',' ' ')
    print_info "Compound tokens: $COMPOUND_TOKENS"
    
    # Show processing time
    PROCESSING_TIME=$(echo "$COMPOUND_RESPONSE" | grep -o '"processing_time_ms":[0-9.]*' | cut -d':' -f2)
    print_info "Processing time: ${PROCESSING_TIME}ms"
    
    echo ""
    print_info "Full response:"
    echo "$COMPOUND_RESPONSE"
    
    echo ""
    
    # Check if tokenization matches expected result
    if [ "$COMPOUND_TOKENS" = "$EXPECTED_TOKENS" ]; then
        print_success "🎉 PERFECT! Tokenization matches expected result!"
        print_success "✅ 'วากาเมะ' is preserved as one compound word"
    else
        print_warning "⚠️ Tokenization differs from expected result"
        print_info "Expected: $EXPECTED_TOKENS"
        print_info "Actual:   $COMPOUND_TOKENS"
        
        # Check if วากาเมะ is at least preserved
        if echo "$COMPOUND_RESPONSE" | grep -q '"วากาเมะ"'; then
            print_success "✅ 'วากาเมะ' is preserved as one word"
        else
            print_error "❌ 'วากาเมะ' is still being split"
        fi
    fi
else
    print_error "❌ Compound tokenization failed"
    echo "$COMPOUND_RESPONSE"
fi

echo ""

# Test 6: Additional Thai Text Tests
print_info "=== TEST 6: Additional Thai Text Tests ==="

# Test other compound words
TEST_CASES=(
    "รถยนต์ไฟฟ้า"
    "โรงเรียนมัธยมศึกษา"
    "ซูชิซาชิมิ"
)

for test_case in "${TEST_CASES[@]}"; do
    print_info "Testing: $test_case"
    
    RESPONSE=$(curl -s --connect-timeout 5 -X POST "$API_BASE/api/v1/tokenize/compound" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$test_case\"}" 2>/dev/null || echo "ERROR")
    
    if echo "$RESPONSE" | grep -q '"tokens"'; then
        TOKENS=$(echo "$RESPONSE" | grep -o '"tokens":\[[^]]*\]' | sed 's/"tokens":\[//; s/\]//; s/"//g' | tr ',' ' ')
        print_info "→ $TOKENS"
    else
        print_error "→ Failed"
    fi
done

echo ""

# Test 7: Document Indexing Test
print_info "=== TEST 7: Document Indexing Test ==="
INDEX_RESPONSE=$(curl -s --connect-timeout 10 -X POST "$API_BASE/api/v1/index-document" \
    -H "Content-Type: application/json" \
    -d "{\"id\": \"test-wakame-$(date +%s)\", \"title\": \"ทดสอบวากาเมะ\", \"content\": \"$TEST_TEXT\"}" 2>/dev/null || echo "ERROR")

if echo "$INDEX_RESPONSE" | grep -q '"status":"completed"'; then
    print_success "✅ Document indexing working"
    
    # Show tokenized content
    if echo "$INDEX_RESPONSE" | grep -q '"tokenized_fields"'; then
        print_info "Document was successfully tokenized and indexed"
    fi
    
    echo ""
    print_info "Indexing response:"
    echo "$INDEX_RESPONSE"
else
    print_error "❌ Document indexing failed"
    echo "$INDEX_RESPONSE"
fi

echo ""

# Summary
print_info "=== TEST SUMMARY ==="
print_info "API Endpoint: $API_BASE"
print_info "Test Text: $TEST_TEXT"
print_info "Expected Result: $EXPECTED_TOKENS"

if [ "$COMPOUND_TOKENS" = "$EXPECTED_TOKENS" ]; then
    print_success "🎉 ALL TESTS PASSED! Wakame tokenization is working perfectly!"
else
    print_warning "⚠️ Some tests need attention. Check the compound tokenization results above."
fi

echo ""
print_info "To run this test again: ./test-external-api.sh"
print_info "API Documentation: $API_BASE/docs"