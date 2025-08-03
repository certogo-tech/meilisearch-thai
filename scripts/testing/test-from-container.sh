#!/bin/bash

# Test Service from Inside Container
# This script tests the service by executing commands inside the Docker container

echo "🔍 Testing Service from Inside Container"
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

# Find the Thai Tokenizer container
CONTAINER_ID=$(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)

if [ -z "$CONTAINER_ID" ]; then
    print_error "❌ Thai Tokenizer container not found!"
    print_info "Available containers:"
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    exit 1
fi

print_success "✅ Found Thai Tokenizer container: $CONTAINER_ID"

# Test basic health
print_info "Testing basic health..."
BASIC_HEALTH=$(docker exec "$CONTAINER_ID" curl -s "http://localhost:8000/health" 2>/dev/null || echo "ERROR")

if echo "$BASIC_HEALTH" | grep -q "status"; then
    print_success "✅ Basic health check passed"
else
    print_error "❌ Basic health check failed"
    echo "$BASIC_HEALTH"
fi

# Test configuration validity
print_info "Testing configuration validity..."
CONFIG_HEALTH=$(docker exec "$CONTAINER_ID" curl -s "http://localhost:8000/api/v1/health/check/configuration_validity" 2>/dev/null || echo "ERROR")

if echo "$CONFIG_HEALTH" | grep -q '"status":"healthy"'; then
    print_success "✅ Configuration validation: HEALTHY"
elif echo "$CONFIG_HEALTH" | grep -q '"status":"unhealthy"'; then
    print_warning "⚠️ Configuration validation: UNHEALTHY"
    echo "$CONFIG_HEALTH"
else
    print_error "❌ Could not get configuration status"
    echo "$CONFIG_HEALTH"
fi

# Test overall health summary
print_info "Testing overall health summary..."
OVERALL_HEALTH=$(docker exec "$CONTAINER_ID" curl -s "http://localhost:8000/api/v1/health/summary" 2>/dev/null || echo "ERROR")

if echo "$OVERALL_HEALTH" | grep -q '"overall_status":"healthy"'; then
    print_success "🎉 Overall status: HEALTHY"
elif echo "$OVERALL_HEALTH" | grep -q '"overall_status":"degraded"'; then
    print_warning "⚠️ Overall status: DEGRADED"
else
    print_warning "⚠️ Overall status: UNHEALTHY or ERROR"
fi

# Show health score
if echo "$OVERALL_HEALTH" | grep -q "health_score"; then
    HEALTH_SCORE=$(echo "$OVERALL_HEALTH" | grep -o '"health_score":[0-9.]*' | cut -d':' -f2)
    print_info "Health score: $HEALTH_SCORE%"
fi

# Test tokenization
print_info "Testing Thai tokenization..."
TOKENIZE_RESPONSE=$(docker exec "$CONTAINER_ID" curl -s -X POST "http://localhost:8000/api/v1/tokenize" \
    -H "Content-Type: application/json" \
    -d '{"text": "สวัสดีครับ"}' 2>/dev/null || echo "ERROR")

if echo "$TOKENIZE_RESPONSE" | grep -q '"tokens"'; then
    print_success "✅ Thai tokenization is working"
    echo "$TOKENIZE_RESPONSE"
else
    print_error "❌ Thai tokenization failed"
    echo "$TOKENIZE_RESPONSE"
fi

# Show container logs (last 10 lines)
print_info "Recent container logs:"
docker logs --tail 10 "$CONTAINER_ID"

print_info "Test completed!"
print_info "Container ID: $CONTAINER_ID"
print_info "To view full logs: docker logs $CONTAINER_ID"