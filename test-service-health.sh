#!/bin/bash

# Test Service Health Script
# This script tests both internal and external access to the Thai Tokenizer service

echo "🔍 Testing Thai Tokenizer Service Health"
echo "========================================"

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

# Test internal access (localhost:8000)
print_info "Testing internal access (localhost:8000)..."

if curl -s --connect-timeout 5 'http://localhost:8000/health' > /dev/null; then
    print_success "✅ Internal service is accessible"
    
    # Test configuration validity
    print_info "Checking configuration validity..."
    CONFIG_HEALTH=$(curl -s 'http://localhost:8000/api/v1/health/check/configuration_validity')
    
    if echo "$CONFIG_HEALTH" | grep -q '"status":"healthy"'; then
        print_success "✅ Configuration validation: HEALTHY"
    elif echo "$CONFIG_HEALTH" | grep -q '"status":"unhealthy"'; then
        print_warning "⚠️ Configuration validation: UNHEALTHY"
        echo "$CONFIG_HEALTH" | jq -r '.message // "No message"' 2>/dev/null || echo "Details not available"
    else
        print_error "❌ Could not get configuration status"
    fi
    
    # Test overall health
    print_info "Checking overall health..."
    OVERALL_HEALTH=$(curl -s 'http://localhost:8000/api/v1/health/summary')
    
    if echo "$OVERALL_HEALTH" | grep -q '"overall_status":"healthy"'; then
        print_success "🎉 Overall status: HEALTHY"
    elif echo "$OVERALL_HEALTH" | grep -q '"overall_status":"degraded"'; then
        print_warning "⚠️ Overall status: DEGRADED"
    else
        print_warning "⚠️ Overall status: UNHEALTHY"
    fi
    
    # Show health score
    HEALTH_SCORE=$(echo "$OVERALL_HEALTH" | jq -r '.health_score // "unknown"' 2>/dev/null || echo "unknown")
    print_info "Health score: $HEALTH_SCORE%"
    
else
    print_error "❌ Internal service is not accessible"
fi

echo ""

# Test external access (https://search.cads.arda.or.th)
print_info "Testing external access (https://search.cads.arda.or.th)..."

if curl -s --connect-timeout 5 'https://search.cads.arda.or.th/health' > /dev/null; then
    print_success "✅ External domain is accessible"
    
    # Test tokenization
    print_info "Testing Thai tokenization..."
    TOKENIZE_RESPONSE=$(curl -s -X POST "https://search.cads.arda.or.th/api/v1/tokenize" \
        -H "Content-Type: application/json" \
        -d '{"text": "สวัสดีครับ"}')
    
    if echo "$TOKENIZE_RESPONSE" | grep -q '"tokens"'; then
        print_success "✅ Thai tokenization is working"
        TOKENS=$(echo "$TOKENIZE_RESPONSE" | jq -r '.tokens[]' 2>/dev/null | tr '\n' ' ')
        print_info "Sample tokens: $TOKENS"
    else
        print_error "❌ Thai tokenization failed"
        echo "$TOKENIZE_RESPONSE"
    fi
    
else
    print_warning "⚠️ External domain not accessible from this server"
    print_info "This may be normal if testing from inside the server network"
fi

echo ""

# Test Meilisearch connectivity
print_info "Testing Meilisearch connectivity..."
source .env.production 2>/dev/null || true

if [ -n "$MEILISEARCH_HOST" ]; then
    print_info "Testing Meilisearch at: $MEILISEARCH_HOST"
    
    if curl -s --connect-timeout 5 "$MEILISEARCH_HOST/health" > /dev/null; then
        MEILISEARCH_STATUS=$(curl -s "$MEILISEARCH_HOST/health" | jq -r '.status // "unknown"' 2>/dev/null || echo "unknown")
        print_success "✅ Meilisearch is accessible - Status: $MEILISEARCH_STATUS"
    else
        print_error "❌ Cannot connect to Meilisearch at $MEILISEARCH_HOST"
    fi
else
    print_warning "⚠️ MEILISEARCH_HOST not found in .env.production"
fi

echo ""
print_info "Health check completed!"
print_info "For detailed health information, visit:"
print_info "- Internal: http://localhost:8000/api/v1/health/detailed"
print_info "- External: https://search.cads.arda.or.th/api/v1/health/detailed"