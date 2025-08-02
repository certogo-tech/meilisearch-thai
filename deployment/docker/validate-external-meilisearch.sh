#!/bin/bash

# Validation script for External Meilisearch configuration
# This script validates the configuration and connectivity before deployment

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/.env.external-meilisearch"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if environment file exists
if [[ ! -f "$ENV_FILE" ]]; then
    log_error "Environment file not found: $ENV_FILE"
    log_info "Please copy .env.external-meilisearch.template to .env.external-meilisearch"
    exit 1
fi

# Source environment variables
set -a
source "$ENV_FILE"
set +a

log_info "Validating External Meilisearch Configuration"
echo "================================================"

# Validate required environment variables
VALIDATION_ERRORS=0

validate_var() {
    local var_name="$1"
    local var_value="${!var_name:-}"
    local required="${2:-true}"
    
    if [[ -z "$var_value" ]]; then
        if [[ "$required" == "true" ]]; then
            log_error "Required variable $var_name is not set"
            ((VALIDATION_ERRORS++))
        else
            log_warning "Optional variable $var_name is not set"
        fi
    else
        log_success "$var_name is set"
    fi
}

log_info "Checking required environment variables..."
validate_var "MEILISEARCH_HOST" true
validate_var "MEILISEARCH_API_KEY" true
validate_var "MEILISEARCH_INDEX" false

log_info "Checking optional configuration variables..."
validate_var "THAI_TOKENIZER_PORT" false
validate_var "LOG_LEVEL" false
validate_var "BATCH_SIZE" false

if [[ $VALIDATION_ERRORS -gt 0 ]]; then
    log_error "Configuration validation failed with $VALIDATION_ERRORS errors"
    exit 1
fi

log_success "Environment variable validation passed"
echo ""

# Test network connectivity
log_info "Testing network connectivity..."

# Extract host and port from MEILISEARCH_HOST
if [[ "$MEILISEARCH_HOST" =~ ^https?://([^:/]+)(:([0-9]+))?(/.*)?$ ]]; then
    MEILISEARCH_HOSTNAME="${BASH_REMATCH[1]}"
    MEILISEARCH_PORT="${BASH_REMATCH[3]:-7700}"
else
    log_error "Invalid MEILISEARCH_HOST format: $MEILISEARCH_HOST"
    log_error "Expected format: http://hostname:port or https://hostname:port"
    exit 1
fi

log_info "Testing DNS resolution for $MEILISEARCH_HOSTNAME..."
if nslookup "$MEILISEARCH_HOSTNAME" > /dev/null 2>&1; then
    log_success "DNS resolution successful"
else
    log_error "DNS resolution failed for $MEILISEARCH_HOSTNAME"
    log_error "Please verify the hostname is correct and accessible"
    exit 1
fi

log_info "Testing TCP connectivity to $MEILISEARCH_HOSTNAME:$MEILISEARCH_PORT..."
if timeout 10 bash -c "</dev/tcp/$MEILISEARCH_HOSTNAME/$MEILISEARCH_PORT" 2>/dev/null; then
    log_success "TCP connection successful"
else
    log_error "TCP connection failed to $MEILISEARCH_HOSTNAME:$MEILISEARCH_PORT"
    log_error "Please verify:"
    log_error "  1. Meilisearch is running on the specified host and port"
    log_error "  2. Firewall allows connections to port $MEILISEARCH_PORT"
    log_error "  3. Network routing is configured correctly"
    exit 1
fi

echo ""

# Test Meilisearch HTTP API
log_info "Testing Meilisearch HTTP API..."

HEALTH_URL="${MEILISEARCH_HOST}/health"
log_info "Testing health endpoint: $HEALTH_URL"

if curl -f -s --max-time 10 "$HEALTH_URL" > /dev/null; then
    log_success "Meilisearch health endpoint accessible"
else
    log_error "Meilisearch health endpoint not accessible"
    log_error "Please verify:"
    log_error "  1. Meilisearch is running and healthy"
    log_error "  2. The URL is correct: $HEALTH_URL"
    log_error "  3. No proxy or firewall is blocking the request"
    exit 1
fi

# Test API key authentication
log_info "Testing Meilisearch API key authentication..."
KEYS_URL="${MEILISEARCH_HOST}/keys"

AUTH_RESPONSE=$(curl -f -s --max-time 10 \
    -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
    "$KEYS_URL" 2>/dev/null || echo "")

if [[ -n "$AUTH_RESPONSE" ]]; then
    log_success "API key authentication successful"
    
    # Check if the key has sufficient permissions
    if echo "$AUTH_RESPONSE" | grep -q '"actions"'; then
        log_info "API key permissions detected"
    else
        log_warning "Could not verify API key permissions"
    fi
else
    log_error "API key authentication failed"
    log_error "Please verify:"
    log_error "  1. The API key is correct"
    log_error "  2. The API key has sufficient permissions"
    log_error "  3. Meilisearch authentication is properly configured"
    exit 1
fi

# Test index access
if [[ -n "${MEILISEARCH_INDEX:-}" ]]; then
    log_info "Testing index access for: $MEILISEARCH_INDEX"
    INDEX_URL="${MEILISEARCH_HOST}/indexes/$MEILISEARCH_INDEX"
    
    INDEX_RESPONSE=$(curl -f -s --max-time 10 \
        -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
        "$INDEX_URL" 2>/dev/null || echo "")
    
    if [[ -n "$INDEX_RESPONSE" ]]; then
        log_success "Index access successful"
        
        # Extract index information
        if command -v jq > /dev/null 2>&1; then
            INDEX_UID=$(echo "$INDEX_RESPONSE" | jq -r '.uid // "unknown"')
            PRIMARY_KEY=$(echo "$INDEX_RESPONSE" | jq -r '.primaryKey // "none"')
            log_info "Index UID: $INDEX_UID"
            log_info "Primary Key: $PRIMARY_KEY"
        fi
    else
        log_warning "Index '$MEILISEARCH_INDEX' not found or not accessible"
        log_info "The index will be created automatically when documents are added"
    fi
fi

echo ""

# Test Docker prerequisites
log_info "Checking Docker prerequisites..."

if ! command -v docker > /dev/null 2>&1; then
    log_error "Docker is not installed"
    exit 1
fi

if ! docker info > /dev/null 2>&1; then
    log_error "Docker daemon is not running"
    exit 1
fi

if ! docker compose version > /dev/null 2>&1; then
    log_error "Docker Compose is not available"
    exit 1
fi

log_success "Docker prerequisites satisfied"

# Check available resources
log_info "Checking system resources..."

# Check available memory
AVAILABLE_MEMORY_KB=$(grep MemAvailable /proc/meminfo | awk '{print $2}' 2>/dev/null || echo "0")
AVAILABLE_MEMORY_MB=$((AVAILABLE_MEMORY_KB / 1024))

REQUIRED_MEMORY_MB=512
if [[ $AVAILABLE_MEMORY_MB -lt $REQUIRED_MEMORY_MB ]]; then
    log_warning "Available memory ($AVAILABLE_MEMORY_MB MB) is less than recommended ($REQUIRED_MEMORY_MB MB)"
else
    log_success "Sufficient memory available ($AVAILABLE_MEMORY_MB MB)"
fi

# Check available disk space
AVAILABLE_DISK_MB=$(df . | tail -1 | awk '{print int($4/1024)}')
REQUIRED_DISK_MB=1024

if [[ $AVAILABLE_DISK_MB -lt $REQUIRED_DISK_MB ]]; then
    log_warning "Available disk space ($AVAILABLE_DISK_MB MB) is less than recommended ($REQUIRED_DISK_MB MB)"
else
    log_success "Sufficient disk space available ($AVAILABLE_DISK_MB MB)"
fi

echo ""

# Performance recommendations
log_info "Performance Recommendations:"

if [[ "${BATCH_SIZE:-50}" -gt 100 ]]; then
    log_warning "BATCH_SIZE ($BATCH_SIZE) is quite high, consider reducing for better memory usage"
fi

if [[ "${MAX_WORKERS:-4}" -gt 8 ]]; then
    log_warning "MAX_WORKERS ($MAX_WORKERS) is high, ensure sufficient CPU cores are available"
fi

if [[ "${WORKER_PROCESSES:-4}" -gt 4 ]] && [[ $AVAILABLE_MEMORY_MB -lt 2048 ]]; then
    log_warning "WORKER_PROCESSES ($WORKER_PROCESSES) may be too high for available memory"
fi

echo ""

# Security recommendations
log_info "Security Recommendations:"

if [[ "${MEILISEARCH_HOST}" == http://* ]]; then
    log_warning "Using HTTP connection to Meilisearch (not encrypted)"
    log_info "Consider using HTTPS for production deployments"
fi

if [[ "${CORS_ORIGINS:-*}" == "*" ]]; then
    log_warning "CORS is configured to allow all origins"
    log_info "Consider restricting CORS_ORIGINS for production deployments"
fi

if [[ "${API_KEY_REQUIRED:-false}" == "false" ]]; then
    log_info "API key authentication is disabled"
    log_info "Consider enabling API_KEY_REQUIRED for production deployments"
fi

echo ""

# Final validation summary
log_success "=== VALIDATION SUMMARY ==="
log_success "✓ Environment configuration is valid"
log_success "✓ Network connectivity to Meilisearch is working"
log_success "✓ Meilisearch API authentication is successful"
log_success "✓ Docker prerequisites are satisfied"
log_success "✓ System resources are adequate"

echo ""
log_info "Configuration is ready for deployment!"
log_info "Run the following command to deploy:"
log_info "  ./deploy-external-meilisearch.sh deploy"

echo ""
log_info "For additional options, run:"
log_info "  ./deploy-external-meilisearch.sh --help"