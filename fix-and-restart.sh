#!/bin/bash

# Fix Docker Compose and Restart Service
# This script fixes any YAML syntax issues and restarts the service

set -e

echo "🔧 Fixing Docker Compose and Restarting Service"
echo "==============================================="

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

print_info "Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Validate Docker Compose file syntax
print_info "Validating Docker Compose file syntax..."
if $DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml config > /dev/null 2>&1; then
    print_success "✅ Docker Compose file syntax is valid"
else
    print_error "❌ Docker Compose file has syntax errors"
    print_info "Showing validation errors:"
    $DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml config
    exit 1
fi

# Ensure custom dictionary directory exists
print_info "Ensuring custom dictionary directory exists..."
mkdir -p data/dictionaries
print_success "✅ Dictionary directory ready"

# Stop any running containers
print_info "Stopping any running containers..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production down || true

# Build the image
print_info "Building Docker image..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production build thai-tokenizer

# Start the service
print_info "Starting service..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d

# Wait for service to start
print_info "Waiting for service to start..."
sleep 15

# Check container status
print_info "Checking container status..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production ps

# Test the service from inside container
CONTAINER_ID=$(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)
if [ -n "$CONTAINER_ID" ]; then
    print_info "Testing service from inside container..."
    
    # Test basic health
    HEALTH_RESPONSE=$(docker exec "$CONTAINER_ID" curl -s "http://localhost:8000/health" 2>/dev/null || echo "ERROR")
    
    if echo "$HEALTH_RESPONSE" | grep -q "status"; then
        print_success "✅ Service is responding"
    else
        print_error "❌ Service is not responding"
        print_info "Container logs:"
        docker logs --tail 20 "$CONTAINER_ID"
        exit 1
    fi
    
    # Test tokenization
    print_info "Testing Thai tokenization..."
    TOKENIZE_RESPONSE=$(docker exec "$CONTAINER_ID" curl -s -X POST "http://localhost:8000/api/v1/tokenize/compound" \
        -H "Content-Type: application/json" \
        -d '{"text": "ฉันกินสาหร่ายวากาเมะ"}' 2>/dev/null || echo "ERROR")
    
    if echo "$TOKENIZE_RESPONSE" | grep -q '"tokens"'; then
        print_success "✅ Tokenization is working"
        echo "$TOKENIZE_RESPONSE"
        
        # Check if วากาเมะ is tokenized correctly
        if echo "$TOKENIZE_RESPONSE" | grep -q '"วากาเมะ"'; then
            print_success "🎉 วากาเมะ is tokenized as one word!"
        else
            print_warning "⚠️ วากาเมะ is still being split"
        fi
    else
        print_error "❌ Tokenization failed"
        echo "$TOKENIZE_RESPONSE"
    fi
else
    print_error "❌ No container found"
fi

print_success "✅ Service restart completed!"
print_info "Service should now be running with custom dictionary support"
print_info "Test externally: curl -X POST 'https://search.cads.arda.or.th/api/v1/tokenize/compound' -H 'Content-Type: application/json' -d '{\"text\": \"ฉันกินสาหร่ายวากาเมะ\"}'"