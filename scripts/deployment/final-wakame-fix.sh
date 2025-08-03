#!/bin/bash

# Final Wakame Tokenization Fix
# Remove "สาหร่ายวากาเมะ" from dictionary to allow proper splitting

echo "🎯 Final Wakame Tokenization Fix"
echo "==============================="

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

# Detect docker compose command
if command -v "docker compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v "docker-compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    print_error "Neither 'docker compose' nor 'docker-compose' command found!"
    exit 1
fi

print_info "Applied fix: Removed 'สาหร่ายวากาเมะ' from dictionary"
print_info "Now 'ฉันกินสาหร่ายวากาเมะ' should tokenize as:"
print_info "['ฉัน', 'กิน', 'สาหร่าย', 'วากาเมะ']"

print_info "Rebuilding service with updated dictionary..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production down
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production build --no-cache thai-tokenizer
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d

print_info "Waiting for service to start..."
sleep 15

# Test the tokenization
print_info "Testing the fix..."
CONTAINER_ID=$(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)

if [ -n "$CONTAINER_ID" ]; then
    COMPOUND_RESPONSE=$(docker exec "$CONTAINER_ID" curl -s -X POST "http://localhost:8000/api/v1/tokenize/compound" \
        -H "Content-Type: application/json" \
        -d '{"text": "ฉันกินสาหร่ายวากาเมะ"}' 2>/dev/null || echo "ERROR")
    
    if echo "$COMPOUND_RESPONSE" | grep -q '"tokens"'; then
        print_success "✅ Tokenization working!"
        echo "$COMPOUND_RESPONSE"
        
        # Check if we get the expected result
        if echo "$COMPOUND_RESPONSE" | grep -q '"วากาเมะ"' && echo "$COMPOUND_RESPONSE" | grep -q '"สาหร่าย"'; then
            print_success "🎉 Perfect! Got both 'สาหร่าย' and 'วากาเมะ' as separate tokens!"
        else
            print_warning "⚠️ Still not getting the expected tokenization"
        fi
    else
        print_error "❌ Tokenization failed"
        echo "$COMPOUND_RESPONSE"
    fi
else
    print_error "❌ No container found"
fi

print_success "✅ Final fix applied!"
print_info "Test with: ./test-wakame-tokenization.sh"