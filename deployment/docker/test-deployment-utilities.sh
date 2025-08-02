#!/bin/bash

# Test script for Docker deployment utilities
# This script tests the deployment utilities without actually deploying services

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

run_test() {
    local test_name="$1"
    local test_command="$2"
    
    log_info "Running test: $test_name"
    
    if eval "$test_command" > /dev/null 2>&1; then
        log_success "✓ $test_name"
        ((TESTS_PASSED++))
    else
        log_error "✗ $test_name"
        ((TESTS_FAILED++))
    fi
}

log_info "Testing Docker deployment utilities..."
echo "================================================"

# Test 1: Check if Python scripts exist and are executable
run_test "Python scripts exist" "test -x '$SCRIPT_DIR/docker-deployment-manager.py' && test -x '$SCRIPT_DIR/docker-backup-recovery.py' && test -x '$SCRIPT_DIR/docker-health-monitor.py'"

# Test 2: Check if main deployment script exists and is executable
run_test "Main deployment script exists" "test -x '$SCRIPT_DIR/deploy-external-meilisearch.sh'"

# Test 3: Check if configuration files exist
run_test "Configuration files exist" "test -f '$SCRIPT_DIR/docker-compose.external-meilisearch.yml' && test -f '$SCRIPT_DIR/.env.external-meilisearch.template'"

# Test 4: Check if Python is available
run_test "Python 3 available" "command -v python3"

# Test 5: Check if Docker is available
run_test "Docker available" "command -v docker"

# Test 6: Check if Docker Compose is available
run_test "Docker Compose available" "docker compose version"

# Test 7: Test Python script syntax
if command -v python3 > /dev/null 2>&1; then
    run_test "Deployment manager syntax" "python3 -m py_compile '$SCRIPT_DIR/docker-deployment-manager.py'"
    run_test "Health monitor syntax" "python3 -m py_compile '$SCRIPT_DIR/docker-health-monitor.py'"
    run_test "Backup recovery syntax" "python3 -m py_compile '$SCRIPT_DIR/docker-backup-recovery.py'"
else
    log_warning "Skipping Python syntax tests (Python not available)"
fi

# Test 8: Test deployment script help
run_test "Deployment script help" "'$SCRIPT_DIR/deploy-external-meilisearch.sh' --help"

# Test 9: Test Python scripts help (if Python is available)
if command -v python3 > /dev/null 2>&1; then
    run_test "Deployment manager help" "python3 '$SCRIPT_DIR/docker-deployment-manager.py' --help"
    run_test "Health monitor help" "python3 '$SCRIPT_DIR/docker-health-monitor.py' --help"
    run_test "Backup recovery help" "python3 '$SCRIPT_DIR/docker-backup-recovery.py' --help"
else
    log_warning "Skipping Python help tests (Python not available)"
fi

# Test 10: Test Docker Compose file syntax
run_test "Docker Compose syntax" "docker compose -f '$SCRIPT_DIR/docker-compose.external-meilisearch.yml' config --quiet"

# Test 11: Check if required Python packages are available (if Python is available)
if command -v python3 > /dev/null 2>&1; then
    run_test "Python requests module" "python3 -c 'import requests'"
    run_test "Python psutil module" "python3 -c 'import psutil'"
    run_test "Python yaml module" "python3 -c 'import yaml'"
else
    log_warning "Skipping Python package tests (Python not available)"
fi

# Test 12: Test environment template validity
run_test "Environment template valid" "grep -q 'MEILISEARCH_HOST' '$SCRIPT_DIR/.env.external-meilisearch.template'"

# Test 13: Test resource limits file exists
run_test "Resource limits file exists" "test -f '$SCRIPT_DIR/docker-resource-limits.yml'"

# Test 14: Test documentation exists
run_test "Documentation exists" "test -f '$SCRIPT_DIR/README_DOCKER_DEPLOYMENT.md'"

echo ""
echo "================================================"
log_info "Test Summary:"
log_success "Tests passed: $TESTS_PASSED"
if [[ $TESTS_FAILED -gt 0 ]]; then
    log_error "Tests failed: $TESTS_FAILED"
else
    log_success "Tests failed: $TESTS_FAILED"
fi

echo ""
if [[ $TESTS_FAILED -eq 0 ]]; then
    log_success "All tests passed! Docker deployment utilities are ready to use."
    echo ""
    log_info "Next steps:"
    echo "1. Copy .env.external-meilisearch.template to .env.external-meilisearch"
    echo "2. Configure your Meilisearch connection details"
    echo "3. Run: ./deploy-external-meilisearch.sh validate"
    echo "4. Run: ./deploy-external-meilisearch.sh deploy"
    exit 0
else
    log_error "Some tests failed. Please check the requirements and fix any issues."
    echo ""
    log_info "Common issues:"
    echo "- Docker not installed or not running"
    echo "- Python 3 not available"
    echo "- Missing Python packages (requests, psutil, pyyaml)"
    echo "- File permissions not set correctly"
    exit 1
fi