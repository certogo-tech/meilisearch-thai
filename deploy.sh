#!/bin/bash

# Main Deployment Script
# This is the primary script for deploying the Thai Tokenizer service

echo "🚀 Thai Tokenizer Deployment"
echo "============================"

# Show available deployment options
echo "Available deployment scripts:"
echo "1. scripts/deployment/deploy-production.sh - Full production deployment"
echo "2. scripts/deployment/setup-production-tokenizer.sh - Setup with custom dictionary"
echo "3. scripts/deployment/simple-rebuild.sh - Simple rebuild and restart"
echo "4. scripts/deployment/final-wakame-fix.sh - Apply wakame tokenization fix"
echo ""
echo "Available testing scripts:"
echo "1. scripts/testing/test-external-api.sh - Test from external server"
echo "2. scripts/testing/test-wakame-tokenization.sh - Test wakame tokenization"
echo "3. scripts/testing/test-service-health.sh - Test service health"
echo ""
echo "Available maintenance scripts:"
echo "1. scripts/maintenance/debug-dictionary.sh - Debug custom dictionary"
echo "2. scripts/maintenance/validate-env-config.sh - Validate configuration"
echo ""

# Check if user wants to run a specific script
if [ $# -eq 0 ]; then
    echo "Usage: $0 [script-name]"
    echo "Example: $0 production  # Runs full production deployment"
    echo "Example: $0 test        # Runs external API test"
    echo "Example: $0 health      # Runs health check"
    exit 0
fi

case "$1" in
    "production"|"prod")
        echo "Running production deployment..."
        ./scripts/deployment/deploy-production.sh
        ;;
    "setup")
        echo "Running production setup with custom dictionary..."
        ./scripts/deployment/setup-production-tokenizer.sh
        ;;
    "rebuild")
        echo "Running simple rebuild..."
        ./scripts/deployment/simple-rebuild.sh
        ;;
    "test")
        echo "Running external API test..."
        ./scripts/testing/test-external-api.sh
        ;;
    "wakame")
        echo "Testing wakame tokenization..."
        ./scripts/testing/test-wakame-tokenization.sh
        ;;
    "health")
        echo "Testing service health..."
        ./scripts/testing/test-service-health.sh
        ;;
    "debug")
        echo "Running debug tools..."
        ./scripts/maintenance/debug-dictionary.sh
        ;;
    "validate")
        echo "Validating configuration..."
        ./scripts/maintenance/validate-env-config.sh
        ;;
    *)
        echo "Unknown option: $1"
        echo "Run '$0' without arguments to see available options"
        exit 1
        ;;
esac
