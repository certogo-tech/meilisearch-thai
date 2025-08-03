#!/bin/bash

# Rebuild Service with Custom Dictionary Fix
# This script rebuilds the service with the corrected environment variable mapping

echo "🔧 Rebuilding Service with Custom Dictionary Fix"
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

# Show the fix that was applied
print_info "Applied fix: Environment variable mapping"
print_info "- Changed: CUSTOM_DICTIONARY_PATH"
print_info "- To: THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH"

# Stop and rebuild
print_info "Stopping service..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production down

print_info "Rebuilding with dictionary fix..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production build --no-cache thai-tokenizer

print_info "Starting service..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d

print_success "✅ Service rebuilt with dictionary fix!"
print_info "Wait 15 seconds, then run: ./debug-dictionary.sh"
print_info "Then test with: ./test-wakame-tokenization.sh"