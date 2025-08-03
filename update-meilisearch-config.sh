#!/bin/bash

# Update Meilisearch Configuration Script
# This script updates the Thai Tokenizer service to use the discovered Meilisearch endpoint

set -e

echo "🔧 Updating Thai Tokenizer Meilisearch Configuration..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    print_error ".env.production file not found!"
    exit 1
fi

print_status "Configuration file found: .env.production"

# Test Meilisearch connectivity
print_status "Testing Meilisearch connectivity at http://10.0.2.105:7700..."

if curl -s --connect-timeout 5 http://10.0.2.105:7700/health > /dev/null; then
    print_success "Meilisearch server is accessible"
    
    # Get Meilisearch status
    MEILISEARCH_STATUS=$(curl -s http://10.0.2.105:7700/health | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    print_status "Meilisearch status: $MEILISEARCH_STATUS"
else
    print_error "Cannot connect to Meilisearch at http://10.0.2.105:7700"
    print_error "Please verify the IP address and ensure Meilisearch is running"
    exit 1
fi

# Backup current configuration
BACKUP_FILE=".env.production.backup.$(date +%Y%m%d_%H%M%S)"
print_status "Creating backup: $BACKUP_FILE"
cp .env.production "$BACKUP_FILE"
print_success "Configuration backed up to $BACKUP_FILE"

# Check if Docker Compose is running
print_status "Checking current deployment status..."

# Detect docker compose command
if command -v "docker compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v "docker-compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    print_error "Neither 'docker compose' nor 'docker-compose' command found!"
    exit 1
fi

print_status "Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Check if service is running
if $DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml ps | grep -q "thai-tokenizer"; then
    print_status "Thai Tokenizer service is currently running"
    
    # Restart the service with new configuration
    print_status "Restarting Thai Tokenizer service with updated configuration..."
    
    $DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production down
    print_status "Service stopped"
    
    $DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d
    print_status "Service starting with new configuration..."
    
else
    print_status "Thai Tokenizer service is not running, starting with new configuration..."
    $DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d
fi

# Wait for service to start
print_status "Waiting for service to start..."
sleep 10

# Test service health
print_status "Testing service health..."

MAX_RETRIES=12
RETRY_COUNT=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if curl -s --connect-timeout 5 https://search.cads.arda.or.th/health > /dev/null; then
        print_success "Service is responding!"
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        print_status "Waiting for service... (attempt $RETRY_COUNT/$MAX_RETRIES)"
        sleep 5
    fi
done

if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
    print_error "Service failed to start properly"
    print_error "Check logs with: $DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml logs thai-tokenizer"
    exit 1
fi

# Test detailed health
print_status "Checking detailed health status..."
HEALTH_RESPONSE=$(curl -s https://search.cads.arda.or.th/api/v1/health/detailed)

if echo "$HEALTH_RESPONSE" | grep -q '"overall_status":"healthy"'; then
    print_success "Service is healthy!"
elif echo "$HEALTH_RESPONSE" | grep -q '"overall_status":"degraded"'; then
    print_warning "Service is running but degraded"
    print_status "Check detailed status at: https://search.cads.arda.or.th/api/v1/health/detailed"
else
    print_warning "Service is running but may have issues"
    print_status "Check detailed status at: https://search.cads.arda.or.th/api/v1/health/detailed"
fi

# Test tokenization
print_status "Testing Thai tokenization..."
TOKENIZE_RESPONSE=$(curl -s -X POST "https://search.cads.arda.or.th/api/v1/tokenize" \
    -H "Content-Type: application/json" \
    -d '{"text": "สวัสดีครับ นี่คือการทดสอบ"}')

if echo "$TOKENIZE_RESPONSE" | grep -q '"tokens"'; then
    print_success "Thai tokenization is working!"
    echo "Sample response: $TOKENIZE_RESPONSE"
else
    print_warning "Thai tokenization may have issues"
    echo "Response: $TOKENIZE_RESPONSE"
fi

# Test Meilisearch integration
print_status "Testing Meilisearch integration..."
MEILISEARCH_HEALTH=$(curl -s https://search.cads.arda.or.th/api/v1/health/check/meilisearch)

if echo "$MEILISEARCH_HEALTH" | grep -q '"status":"healthy"'; then
    print_success "Meilisearch integration is working!"
else
    print_warning "Meilisearch integration may have issues"
    echo "Response: $MEILISEARCH_HEALTH"
fi

print_success "Configuration update completed!"
print_status "Updated Meilisearch endpoint to: http://10.0.2.105:7700"
print_status "Service URL: https://search.cads.arda.or.th"
print_status "Health check: https://search.cads.arda.or.th/api/v1/health/detailed"
print_status "API documentation: https://search.cads.arda.or.th/docs"

echo ""
print_status "If you need to rollback, use: cp $BACKUP_FILE .env.production"
print_status "Then restart with: $DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production restart"