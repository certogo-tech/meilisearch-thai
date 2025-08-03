#!/bin/bash

# Simple Rebuild Script - Just rebuild and restart without network testing
# Use this when network testing is problematic

set -e

echo "🔧 Simple Rebuild and Restart"
echo "============================="

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
sleep 20

# Show container status
print_info "Container status:"
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production ps

print_success "✅ Rebuild and restart completed!"
print_info "The service should now be running with the code fixes applied."
print_info ""
print_info "To test the service:"
print_info "1. From external: curl -s 'https://search.cads.arda.or.th/api/v1/health/check/configuration_validity'"
print_info "2. Run test script: ./test-service-health.sh"
print_info "3. Check logs: docker logs \$(docker ps --filter 'name=thai-tokenizer' --format '{{.ID}}' | head -1)"