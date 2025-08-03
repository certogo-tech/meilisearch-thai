#!/bin/bash

# Test Wakame Tokenization
# Test the specific case: "ฉันกินสาหร่ายวากาเมะ" should become "ฉัน กิน สาหร่าย วากาเมะ"

echo "🧪 Testing Wakame Tokenization"
echo "=============================="

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

# Test text
TEST_TEXT="ฉันกินสาหร่ายวากาเมะ"
EXPECTED_TOKENS="ฉัน กิน สาหร่าย วากาเมะ"

print_info "Testing text: $TEST_TEXT"
print_info "Expected tokens: $EXPECTED_TOKENS"
echo ""

# Test using Docker container (internal network)
print_info "=== INTERNAL TESTING (from inside server) ==="
CONTAINER_ID=$(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)

if [ -n "$CONTAINER_ID" ]; then
    print_info "Found container: $CONTAINER_ID"
    
    # Test basic tokenization
    print_info "Testing basic tokenization (internal)..."
    CONTAINER_BASIC=$(docker exec "$CONTAINER_ID" curl -s -X POST "http://localhost:8000/api/v1/tokenize" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$TEST_TEXT\"}" 2>/dev/null || echo "ERROR")
    
    if echo "$CONTAINER_BASIC" | grep -q '"tokens"'; then
        print_success "✅ Internal basic tokenization working"
        
        # Extract tokens
        BASIC_TOKENS=$(echo "$CONTAINER_BASIC" | grep -o '"tokens":\[[^]]*\]' | sed 's/"tokens":\[//; s/\]//; s/"//g' | tr ',' ' ')
        print_info "Basic tokens: $BASIC_TOKENS"
        echo "$CONTAINER_BASIC"
    else
        print_error "❌ Internal basic tokenization failed"
        echo "$CONTAINER_BASIC"
    fi
    
    echo ""
    
    # Test compound tokenization
    print_info "Testing compound tokenization (internal)..."
    CONTAINER_COMPOUND=$(docker exec "$CONTAINER_ID" curl -s -X POST "http://localhost:8000/api/v1/tokenize/compound" \
        -H "Content-Type: application/json" \
        -d "{\"text\": \"$TEST_TEXT\"}" 2>/dev/null || echo "ERROR")
    
    if echo "$CONTAINER_COMPOUND" | grep -q '"tokens"'; then
        print_success "✅ Internal compound tokenization working"
        
        # Extract tokens
        COMPOUND_TOKENS=$(echo "$CONTAINER_COMPOUND" | grep -o '"tokens":\[[^]]*\]' | sed 's/"tokens":\[//; s/\]//; s/"//g' | tr ',' ' ')
        print_info "Compound tokens: $COMPOUND_TOKENS"
        echo "$CONTAINER_COMPOUND"
        
        # Check if tokenization is correct
        if [ "$COMPOUND_TOKENS" = "$EXPECTED_TOKENS" ]; then
            print_success "🎉 INTERNAL: Perfect tokenization! Matches expected result."
        else
            print_warning "⚠️ INTERNAL: Tokenization differs from expected result"
            print_info "Expected: $EXPECTED_TOKENS"
            print_info "Actual:   $COMPOUND_TOKENS"
        fi
    else
        print_error "❌ Internal compound tokenization failed"
        echo "$CONTAINER_COMPOUND"
    fi
else
    print_warning "⚠️ No Thai Tokenizer container found for internal testing"
fi

echo ""
print_info "=== EXTERNAL TESTING (from outside server) ==="

# Test using external API
print_info "Testing via external API (https://search.cads.arda.or.th)..."
EXTERNAL_RESPONSE=$(curl -s --connect-timeout 10 -X POST "https://search.cads.arda.or.th/api/v1/tokenize" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$TEST_TEXT\"}" 2>/dev/null || echo "ERROR")

if echo "$EXTERNAL_RESPONSE" | grep -q '"tokens"'; then
    print_success "✅ External API responded"
    
    # Extract tokens
    ACTUAL_TOKENS=$(echo "$EXTERNAL_RESPONSE" | grep -o '"tokens":\[[^]]*\]' | sed 's/"tokens":\[//; s/\]//; s/"//g' | tr ',' ' ')
    print_info "External basic tokens: $ACTUAL_TOKENS"
    echo "$EXTERNAL_RESPONSE"
elif echo "$EXTERNAL_RESPONSE" | grep -q "ERROR"; then
    print_warning "⚠️ External domain not accessible from this server (normal for internal server)"
    print_info "External users should be able to access https://search.cads.arda.or.th"
else
    print_error "❌ External API failed"
    echo "$EXTERNAL_RESPONSE"
fi

echo ""

# Test compound tokenization endpoint
print_info "Testing compound tokenization endpoint..."
COMPOUND_RESPONSE=$(curl -s -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$TEST_TEXT\"}" 2>/dev/null || echo "ERROR")

if echo "$COMPOUND_RESPONSE" | grep -q '"tokens"'; then
    print_success "✅ Compound tokenization responded"
    
    # Extract tokens
    COMPOUND_TOKENS=$(echo "$COMPOUND_RESPONSE" | grep -o '"tokens":\[[^]]*\]' | sed 's/"tokens":\[//; s/\]//; s/"//g' | tr ',' ' ')
    print_info "Compound tokens: $COMPOUND_TOKENS"
    
    # Show full response
    echo ""
    print_info "Compound response:"
    echo "$COMPOUND_RESPONSE"
    
    # Check if tokenization is correct
    if [ "$COMPOUND_TOKENS" = "$EXPECTED_TOKENS" ]; then
        print_success "🎉 Perfect compound tokenization! Matches expected result."
    else
        print_warning "⚠️ Compound tokenization differs from expected result"
        print_info "Expected: $EXPECTED_TOKENS"
        print_info "Actual:   $COMPOUND_TOKENS"
    fi
else
    print_error "❌ Compound tokenization failed"
    echo "$COMPOUND_RESPONSE"
fi

echo ""
print_info "Tokenization test completed!"
print_info "Test text: $TEST_TEXT"
print_info "Expected: $EXPECTED_TOKENS"