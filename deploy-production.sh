#!/bin/bash

# Production Deployment Script for Thai Tokenizer
# This script deploys Thai Tokenizer to connect with existing Meilisearch

set -e

echo "🚀 Thai Tokenizer Production Deployment"
echo "========================================"

# Configuration
ENV_FILE=".env.production"
COMPOSE_FILE="deployment/docker/docker-compose.npm.yml"
DOCKERFILE="deployment/docker/Dockerfile.prod"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

log_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed or not in PATH"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    # Check environment file
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found"
        log_info "Please copy and configure .env.production with your settings"
        exit 1
    fi
    
    # Check compose file
    if [ ! -f "$COMPOSE_FILE" ]; then
        log_error "Docker Compose file $COMPOSE_FILE not found"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Validate configuration
validate_config() {
    log_info "Validating configuration..."
    
    # Source environment file
    source "$ENV_FILE"
    
    # Check required variables
    required_vars=(
        "MEILISEARCH_HOST"
        "MEILISEARCH_API_KEY"
        "MEILISEARCH_INDEX"
    )
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            log_error "Required environment variable $var is not set"
            exit 1
        fi
    done
    
    log_success "Configuration validation passed"
}

# Test Meilisearch connectivity
test_meilisearch() {
    log_info "Testing Meilisearch connectivity..."
    
    source "$ENV_FILE"
    
    # Extract host and port from MEILISEARCH_HOST
    MEILISEARCH_URL="$MEILISEARCH_HOST"
    
    # Test basic connectivity
    if curl -s -f "$MEILISEARCH_URL/health" > /dev/null; then
        log_success "Meilisearch is accessible at $MEILISEARCH_URL"
    else
        log_warning "Cannot reach Meilisearch at $MEILISEARCH_URL"
        log_info "This might be normal if Meilisearch is only accessible from within Docker network"
    fi
}

# Create necessary directories
create_directories() {
    log_info "Creating necessary directories..."
    
    source "$ENV_FILE"
    
    # Create log directory
    LOG_DIR_PATH="${LOG_DIR:-./logs/thai-tokenizer}"
    mkdir -p "$LOG_DIR_PATH"
    
    # Create SSL directory if needed
    mkdir -p ssl
    
    log_success "Directories created"
}

# Build and deploy
deploy() {
    log_info "Building and deploying Thai Tokenizer..."
    
    # Use docker compose (newer) or docker-compose (legacy) based on availability
    # Prefer docker compose over docker-compose to avoid permission issues
    if docker compose version &> /dev/null; then
        COMPOSE_CMD="docker compose"
    elif command -v docker-compose &> /dev/null && [ -x "$(command -v docker-compose)" ]; then
        COMPOSE_CMD="docker-compose"
    else
        log_error "Neither 'docker compose' nor 'docker-compose' is available or executable"
        exit 1
    fi
    
    # Build the image
    log_info "Using Docker Compose command: $COMPOSE_CMD"
    log_info "Building Thai Tokenizer image..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build thai-tokenizer
    
    # Deploy the service
    log_info "Deploying Thai Tokenizer service..."
    $COMPOSE_CMD -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d thai-tokenizer
    
    log_success "Thai Tokenizer deployed successfully"
}

# Health check
health_check() {
    log_info "Performing health check..."
    
    source "$ENV_FILE"
    PORT="${THAI_TOKENIZER_PORT:-8000}"
    
    # Wait for service to start
    log_info "Waiting for service to start..."
    sleep 30
    
    # Check service health
    if curl -s -f "http://localhost:$PORT/health" > /dev/null; then
        log_success "Thai Tokenizer is healthy and responding"
        
        # Check detailed health including Meilisearch connection
        log_info "Checking Meilisearch integration..."
        if curl -s "http://localhost:$PORT/health/detailed" | grep -q '"meilisearch_status":"healthy"'; then
            log_success "Meilisearch integration is working"
        else
            log_warning "Meilisearch integration may have issues - check logs"
        fi
    else
        log_error "Thai Tokenizer health check failed"
        log_info "Check logs with: docker logs thai_tokenizer_prod-thai-tokenizer-1"
        exit 1
    fi
}

# Show deployment info
show_info() {
    log_info "Deployment Information"
    echo "======================"
    
    source "$ENV_FILE"
    
    echo "Service URL: http://localhost:${THAI_TOKENIZER_PORT:-8000}"
    echo "Health Check: http://localhost:${THAI_TOKENIZER_PORT:-8000}/health"
    echo "API Documentation: http://localhost:${THAI_TOKENIZER_PORT:-8000}/docs"
    echo "Meilisearch Host: $MEILISEARCH_HOST"
    echo "Meilisearch Index: $MEILISEARCH_INDEX"
    echo ""
    echo "Useful Commands:"
    echo "- View logs: docker logs thai_tokenizer_prod-thai-tokenizer-1 -f"
    echo "- Stop service: docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE down"
    echo "- Restart service: docker-compose -f $COMPOSE_FILE --env-file $ENV_FILE restart"
    echo "- Update service: ./deploy-production.sh"
}

# Main deployment flow
main() {
    echo ""
    check_prerequisites
    echo ""
    validate_config
    echo ""
    test_meilisearch
    echo ""
    create_directories
    echo ""
    deploy
    echo ""
    health_check
    echo ""
    show_info
    echo ""
    log_success "🎉 Thai Tokenizer production deployment completed successfully!"
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "stop")
        log_info "Stopping Thai Tokenizer..."
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down
        log_success "Thai Tokenizer stopped"
        ;;
    "restart")
        log_info "Restarting Thai Tokenizer..."
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
        log_success "Thai Tokenizer restarted"
        ;;
    "logs")
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs -f thai-tokenizer
        ;;
    "status")
        docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
        ;;
    "health")
        source "$ENV_FILE"
        curl -s "http://localhost:${THAI_TOKENIZER_PORT:-8000}/health" | jq .
        ;;
    *)
        echo "Usage: $0 [deploy|stop|restart|logs|status|health]"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy Thai Tokenizer (default)"
        echo "  stop    - Stop Thai Tokenizer service"
        echo "  restart - Restart Thai Tokenizer service"
        echo "  logs    - View service logs"
        echo "  status  - Show service status"
        echo "  health  - Check service health"
        exit 1
        ;;
esac