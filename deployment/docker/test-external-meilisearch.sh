#!/bin/bash

# Integration test script for External Meilisearch deployment
# This script performs end-to-end testing of the deployment

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

# Test configuration
TEST_TIMEOUT=60
TEST_RETRIES=5
CLEANUP_ON_EXIT=true

cleanup() {
    if [[ "$CLEANUP_ON_EXIT" == "true" ]]; then
        log_info "Cleaning up test deployment..."
        ./deploy-external-meilisearch.sh stop > /dev/null 2>&1 || true
    fi
}

trap cleanup EXIT

# Function to wait for service to be ready
wait_for_service() {
    local service_url="$1"
    local timeout="$2"
    local retries="$3"
    
    log_info "Waiting for service to be ready at $service_url..."
    
    for ((i=1; i<=retries; i++)); do
        if curl -f -s --max-time 5 "$service_url" > /dev/null; then
            log_success "Service is ready"
            return 0
        fi
        
        log_info "Attempt $i/$retries failed, waiting..."
        sleep $((timeout / retries))
    done
    
    log_error "Service failed to become ready within $timeout seconds"
    return 1
}

# Function to test API endpoint
test_api_endpoint() {
    local endpoint="$1"
    local expected_status="${2:-200}"
    local description="$3"
    
    log_info "Testing $description: $endpoint"
    
    local response
    local status_code
    
    response=$(curl -s -w "\n%{http_code}" "$endpoint" 2>/dev/null || echo -e "\n000")
    status_code=$(echo "$response" | tail -n1)
    
    if [[ "$status_code" == "$expected_status" ]]; then
        log_success "$description test passed (HTTP $status_code)"
        return 0
    else
        log_error "$description test failed (HTTP $status_code)"
        echo "Response: $(echo "$response" | head -n -1)"
        return 1
    fi
}

# Function to test Thai tokenization
test_thai_tokenization() {
    local service_url="$1"
    local tokenize_endpoint="${service_url}/api/v1/tokenize"
    
    log_info "Testing Thai tokenization functionality..."
    
    local test_text="สวัสดีครับ นี่คือการทดสอบระบบโทเค็นไนเซอร์ภาษาไทย"
    local payload=$(cat << EOF
{
    "text": "$test_text",
    "engine": "pythainlp"
}
EOF
)
    
    local response
    response=$(curl -s -X POST \
        -H "Content-Type: application/json" \
        -d "$payload" \
        "$tokenize_endpoint" 2>/dev/null || echo "")
    
    if [[ -n "$response" ]] && echo "$response" | grep -q "tokens"; then
        log_success "Thai tokenization test passed"
        
        # Extract token count for validation
        if command -v jq > /dev/null 2>&1; then
            local token_count
            token_count=$(echo "$response" | jq '.tokens | length' 2>/dev/null || echo "0")
            log_info "Generated $token_count tokens"
        fi
        
        return 0
    else
        log_error "Thai tokenization test failed"
        log_error "Response: $response"
        return 1
    fi
}

# Function to test Meilisearch integration
test_meilisearch_integration() {
    local service_url="$1"
    local health_endpoint="${service_url}/health/detailed"
    
    log_info "Testing Meilisearch integration..."
    
    local response
    response=$(curl -s "$health_endpoint" 2>/dev/null || echo "")
    
    if [[ -n "$response" ]]; then
        # Check if Meilisearch status is healthy
        if echo "$response" | grep -q '"meilisearch_status":"healthy"'; then
            log_success "Meilisearch integration test passed"
            return 0
        else
            log_error "Meilisearch integration test failed"
            log_error "Meilisearch status is not healthy"
            log_error "Response: $response"
            return 1
        fi
    else
        log_error "Could not retrieve health information"
        return 1
    fi
}

# Function to test performance
test_performance() {
    local service_url="$1"
    local tokenize_endpoint="${service_url}/api/v1/tokenize"
    
    log_info "Testing performance with multiple requests..."
    
    local test_text="การทดสอบประสิทธิภาพของระบบโทเค็นไนเซอร์ภาษาไทยด้วยข้อความที่ยาวขึ้น เพื่อให้เห็นถึงความสามารถในการประมวลผลข้อความภาษาไทยที่มีความซับซ้อน"
    local payload=$(cat << EOF
{
    "text": "$test_text",
    "engine": "pythainlp"
}
EOF
)
    
    local total_requests=10
    local successful_requests=0
    local total_time=0
    
    for ((i=1; i<=total_requests; i++)); do
        local start_time=$(date +%s%N)
        
        local response
        response=$(curl -s -X POST \
            -H "Content-Type: application/json" \
            -d "$payload" \
            "$tokenize_endpoint" 2>/dev/null || echo "")
        
        local end_time=$(date +%s%N)
        local request_time=$(( (end_time - start_time) / 1000000 )) # Convert to milliseconds
        
        if [[ -n "$response" ]] && echo "$response" | grep -q "tokens"; then
            ((successful_requests++))
            total_time=$((total_time + request_time))
            log_info "Request $i: ${request_time}ms"
        else
            log_warning "Request $i failed"
        fi
    done
    
    if [[ $successful_requests -gt 0 ]]; then
        local avg_time=$((total_time / successful_requests))
        log_success "Performance test completed: $successful_requests/$total_requests successful"
        log_info "Average response time: ${avg_time}ms"
        
        # Check if performance meets requirements (< 100ms for typical requests)
        if [[ $avg_time -lt 100 ]]; then
            log_success "Performance meets requirements (< 100ms)"
        else
            log_warning "Performance is slower than recommended (${avg_time}ms > 100ms)"
        fi
        
        return 0
    else
        log_error "Performance test failed: no successful requests"
        return 1
    fi
}

# Main test function
run_tests() {
    local test_failures=0
    
    log_info "Starting External Meilisearch Integration Tests"
    echo "=================================================="
    
    # Check if environment file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        log_error "Environment file not found: $ENV_FILE"
        log_info "Please run the validation script first: ./validate-external-meilisearch.sh"
        exit 1
    fi
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    local service_port="${THAI_TOKENIZER_PORT:-8000}"
    local service_url="http://localhost:${service_port}"
    
    # Validate configuration first
    log_info "Validating configuration..."
    if ! ./validate-external-meilisearch.sh > /dev/null 2>&1; then
        log_error "Configuration validation failed"
        log_info "Please run: ./validate-external-meilisearch.sh"
        exit 1
    fi
    log_success "Configuration validation passed"
    
    # Deploy the service
    log_info "Deploying service for testing..."
    if ! ./deploy-external-meilisearch.sh deploy --detach > /dev/null 2>&1; then
        log_error "Service deployment failed"
        exit 1
    fi
    log_success "Service deployed successfully"
    
    # Wait for service to be ready
    if ! wait_for_service "${service_url}/health" $TEST_TIMEOUT $TEST_RETRIES; then
        log_error "Service failed to start within timeout"
        ((test_failures++))
    fi
    
    # Test basic health endpoint
    if ! test_api_endpoint "${service_url}/health" 200 "Basic health check"; then
        ((test_failures++))
    fi
    
    # Test detailed health endpoint
    if ! test_api_endpoint "${service_url}/health/detailed" 200 "Detailed health check"; then
        ((test_failures++))
    fi
    
    # Test metrics endpoint
    if ! test_api_endpoint "${service_url}/metrics" 200 "Metrics endpoint"; then
        ((test_failures++))
    fi
    
    # Test Meilisearch integration
    if ! test_meilisearch_integration "$service_url"; then
        ((test_failures++))
    fi
    
    # Test Thai tokenization
    if ! test_thai_tokenization "$service_url"; then
        ((test_failures++))
    fi
    
    # Test performance
    if ! test_performance "$service_url"; then
        ((test_failures++))
    fi
    
    # Test error handling
    log_info "Testing error handling..."
    if ! test_api_endpoint "${service_url}/nonexistent" 404 "404 error handling"; then
        ((test_failures++))
    fi
    
    echo ""
    echo "=================================================="
    
    if [[ $test_failures -eq 0 ]]; then
        log_success "All tests passed! ✓"
        log_success "External Meilisearch integration is working correctly"
        return 0
    else
        log_error "$test_failures test(s) failed ✗"
        log_error "Please check the logs and configuration"
        return 1
    fi
}

# Parse command line arguments
CLEANUP_ON_EXIT=true

while [[ $# -gt 0 ]]; do
    case $1 in
        --no-cleanup)
            CLEANUP_ON_EXIT=false
            shift
            ;;
        --timeout)
            TEST_TIMEOUT="$2"
            shift 2
            ;;
        --retries)
            TEST_RETRIES="$2"
            shift 2
            ;;
        -h|--help)
            cat << EOF
Usage: $0 [OPTIONS]

Integration test script for External Meilisearch deployment

OPTIONS:
    --no-cleanup    Don't stop the service after testing
    --timeout SEC   Service startup timeout (default: $TEST_TIMEOUT)
    --retries NUM   Number of startup retries (default: $TEST_RETRIES)
    -h, --help      Show this help message

EXAMPLES:
    $0                      # Run all tests with cleanup
    $0 --no-cleanup         # Run tests but leave service running
    $0 --timeout 120        # Use longer startup timeout

EOF
            exit 0
            ;;
        *)
            log_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Run the tests
run_tests