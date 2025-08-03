#!/bin/bash

# Rebuild and Restart Service Script
# This script rebuilds the Docker image and restarts the service with the fixes

set -e

echo "🔧 Rebuilding and Restarting Thai Tokenizer Service"
echo "=================================================="

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

# Stop the current service
print_info "Stopping current service..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production down

# Rebuild the image
print_info "Rebuilding Docker image with fixes..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production build --no-cache thai-tokenizer

# Start the service
print_info "Starting service with updated code..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d

# Wait for service to start
print_info "Waiting for service to start..."
sleep 15

# Test the fixes
print_info "Testing configuration validity..."
HEALTH_RESPONSE=$(curl -s 'https://search.cads.arda.or.th/api/v1/health/check/configuration_validity')

if echo "$HEALTH_RESPONSE" | grep -q '"status":"healthy"'; then
    print_success "✅ Configuration validation is now healthy!"
    echo "$HEALTH_RESPONSE" | jq .
elif echo "$HEALTH_RESPONSE" | grep -q '"status":"unhealthy"'; then
    print_warning "⚠️ Configuration validation still has issues:"
    echo "$HEALTH_RESPONSE" | jq .
else
    print_error "❌ Could not get health status"
    echo "$HEALTH_RESPONSE"
fi

# Test overall health
print_info "Checking overall health status..."
OVERALL_HEALTH=$(curl -s 'https://search.cads.arda.or.th/api/v1/health/summary')

if echo "$OVERALL_HEALTH" | grep -q '"overall_status":"healthy"'; then
    print_success "🎉 Service is now fully healthy!"
elif echo "$OVERALL_HEALTH" | grep -q '"overall_status":"degraded"'; then
    print_warning "Service is running but degraded"
else
    print_warning "Service may still have issues"
fi

# Show health score
HEALTH_SCORE=$(echo "$OVERALL_HEALTH" | jq -r '.health_score // "unknown"')
print_info "Current health score: $HEALTH_SCORE%"

print_success "✅ Rebuild and restart completed!"
print_info "Service URL: https://search.cads.arda.or.th"
print_info "Health check: https://search.cads.arda.or.th/api/v1/health/detailed"