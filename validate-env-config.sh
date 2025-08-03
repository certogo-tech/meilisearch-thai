#!/bin/bash

# Environment Variable Configuration Validator
# This script validates that all environment variables are correctly configured

set -e

echo "🔍 Validating Environment Variable Configuration"
echo "=============================================="

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

# Check if files exist
print_info "Checking configuration files..."

if [ ! -f ".env.production" ]; then
    print_error ".env.production file not found!"
    exit 1
fi

if [ ! -f "deployment/docker/docker-compose.npm.yml" ]; then
    print_error "docker-compose.npm.yml file not found!"
    exit 1
fi

if [ ! -f "deploy-production.sh" ]; then
    print_error "deploy-production.sh file not found!"
    exit 1
fi

print_success "All configuration files found"

# Load environment variables
print_info "Loading environment variables from .env.production..."
source .env.production

# Validate critical environment variables
print_info "Validating critical environment variables..."

ERRORS=0

# Check Meilisearch configuration
if [ -z "$MEILISEARCH_HOST" ]; then
    print_error "MEILISEARCH_HOST is not set"
    ERRORS=$((ERRORS + 1))
else
    print_success "MEILISEARCH_HOST: $MEILISEARCH_HOST"
    
    # Check if it's the correct IP
    if [[ "$MEILISEARCH_HOST" == *"10.0.2.105:7700"* ]]; then
        print_success "Meilisearch host uses correct IP address"
    else
        print_warning "Meilisearch host may not be using the discovered IP (10.0.2.105:7700)"
    fi
fi

if [ -z "$MEILISEARCH_API_KEY" ]; then
    print_error "MEILISEARCH_API_KEY is not set"
    ERRORS=$((ERRORS + 1))
else
    print_success "MEILISEARCH_API_KEY: [SET - ${#MEILISEARCH_API_KEY} characters]"
fi

if [ -z "$MEILISEARCH_INDEX" ]; then
    print_error "MEILISEARCH_INDEX is not set"
    ERRORS=$((ERRORS + 1))
else
    print_success "MEILISEARCH_INDEX: $MEILISEARCH_INDEX"
fi

# Check Thai Tokenizer configuration
if [ -z "$THAI_TOKENIZER_API_KEY" ]; then
    print_error "THAI_TOKENIZER_API_KEY is not set"
    ERRORS=$((ERRORS + 1))
else
    print_success "THAI_TOKENIZER_API_KEY: [SET - ${#THAI_TOKENIZER_API_KEY} characters]"
fi

if [ -z "$THAI_TOKENIZER_PORT" ]; then
    print_warning "THAI_TOKENIZER_PORT not set, will default to 8000"
else
    print_success "THAI_TOKENIZER_PORT: $THAI_TOKENIZER_PORT"
fi

# Check Docker Compose environment mapping
print_info "Checking Docker Compose environment variable mapping..."

# Extract environment variables from docker-compose.yml
COMPOSE_VARS=$(grep -E "^\s*-\s+[A-Z_]+" deployment/docker/docker-compose.npm.yml | sed 's/^\s*-\s*//' | cut -d'=' -f1)

print_info "Environment variables mapped in Docker Compose:"
echo "$COMPOSE_VARS" | while read -r var; do
    if [ -n "$var" ]; then
        echo "  - $var"
    fi
done

# Check if both standard and prefixed variables are mapped
REQUIRED_MAPPINGS=(
    "MEILISEARCH_HOST"
    "MEILISEARCH_API_KEY"
    "THAI_TOKENIZER_MEILISEARCH_HOST"
    "THAI_TOKENIZER_MEILISEARCH_API_KEY"
)

print_info "Checking required environment variable mappings..."
for mapping in "${REQUIRED_MAPPINGS[@]}"; do
    if grep -q "- $mapping=" deployment/docker/docker-compose.npm.yml; then
        print_success "$mapping is mapped in Docker Compose"
    else
        print_error "$mapping is NOT mapped in Docker Compose"
        ERRORS=$((ERRORS + 1))
    fi
done

# Test Meilisearch connectivity
print_info "Testing Meilisearch connectivity..."
if curl -s --connect-timeout 5 "$MEILISEARCH_HOST/health" > /dev/null; then
    MEILISEARCH_STATUS=$(curl -s "$MEILISEARCH_HOST/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    print_success "Meilisearch is accessible - Status: $MEILISEARCH_STATUS"
else
    print_error "Cannot connect to Meilisearch at $MEILISEARCH_HOST"
    ERRORS=$((ERRORS + 1))
fi

# Test Meilisearch with API key
print_info "Testing Meilisearch with API key..."
if curl -s --connect-timeout 5 -H "Authorization: Bearer $MEILISEARCH_API_KEY" "$MEILISEARCH_HOST/indexes" > /dev/null; then
    print_success "Meilisearch API key authentication works"
else
    print_warning "Meilisearch API key authentication failed (may be normal if no auth required)"
fi

# Check deployment script
print_info "Validating deployment script..."
if [ -x "deploy-production.sh" ]; then
    print_success "deploy-production.sh is executable"
else
    print_warning "deploy-production.sh is not executable - run: chmod +x deploy-production.sh"
fi

# Summary
echo ""
print_info "Validation Summary"
echo "=================="

if [ $ERRORS -eq 0 ]; then
    print_success "✅ All validations passed! Configuration looks good."
    echo ""
    print_info "Next steps:"
    echo "1. Run: ./deploy-production.sh"
    echo "2. Test: curl -s 'https://search.cads.arda.or.th/api/v1/health/detailed'"
    echo "3. Test tokenization: curl -X POST 'https://search.cads.arda.or.th/api/v1/tokenize' -H 'Content-Type: application/json' -d '{\"text\": \"สวัสดีครับ\"}'"
else
    print_error "❌ Found $ERRORS configuration issues that need to be fixed."
    exit 1
fi

# Show current configuration summary
echo ""
print_info "Current Configuration Summary:"
echo "=============================="
echo "Meilisearch Host: $MEILISEARCH_HOST"
echo "Meilisearch Index: $MEILISEARCH_INDEX"
echo "Thai Tokenizer Port: ${THAI_TOKENIZER_PORT:-8000}"
echo "API Key Required: ${API_KEY_REQUIRED:-false}"
echo "Worker Processes: ${WORKER_PROCESSES:-4}"
echo "Log Level: ${LOG_LEVEL:-INFO}"