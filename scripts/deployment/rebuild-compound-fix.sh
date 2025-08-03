#!/bin/bash

# Rebuild with Compound Word Fix
# This script rebuilds the service with the fixed compound word logic

echo "🔧 Rebuilding with Compound Word Fix"
echo "===================================="

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

print_info "Applied fix: Compound word logic now preserves custom dictionary words"
print_info "- วากาเมะ should now be preserved as one token"
print_info "- Other unknown compound words will still be split"

print_info "Rebuilding service..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production down
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production build --no-cache thai-tokenizer
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d

print_info "Waiting for service to start..."
sleep 15

print_success "✅ Service rebuilt with compound word fix!"
print_info "Test with: ./test-wakame-tokenization.sh"
print_info "Expected result: ['ฉัน', 'กิน', 'สาหร่าย', 'วากาเมะ']"