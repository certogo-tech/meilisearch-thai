#!/bin/bash
# Production deployment script for Thai Tokenizer

set -e

echo "🚀 Starting Thai Tokenizer Production Deployment"
echo "================================================"

# Configuration
COMPOSE_FILE="docker-compose.prod.yml"
ENV_FILE=".env.prod"
BACKUP_DIR="./backups/$(date +%Y%m%d_%H%M%S)"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not installed"
        exit 1
    fi
    
    if [ ! -f "$ENV_FILE" ]; then
        log_error "Environment file $ENV_FILE not found"
        log_info "Please copy .env.prod.example to .env.prod and configure it"
        exit 1
    fi
    
    log_success "Prerequisites check passed"
}

# Create backup
create_backup() {
    log_info "Creating backup..."
    
    mkdir -p "$BACKUP_DIR"
    
    # Backup MeiliSearch data if exists
    if docker volume ls | grep -q meilisearch_data; then
        log_info "Backing up MeiliSearch data..."
        docker run --rm -v meilisearch_data:/data -v "$(pwd)/$BACKUP_DIR":/backup alpine tar czf /backup/meilisearch_data.tar.gz -C /data .
    fi
    
    # Backup configuration
    cp -r docker/ "$BACKUP_DIR/"
    cp "$ENV_FILE" "$BACKUP_DIR/"
    
    log_success "Backup created at $BACKUP_DIR"
}

# Build and deploy
deploy() {
    log_info "Building production images..."
    
    # Load environment variables
    export $(cat "$ENV_FILE" | grep -v '^#' | xargs)
    
    # Build images
    docker compose -f "$COMPOSE_FILE" build --no-cache
    
    log_info "Starting production services..."
    
    # Start services
    docker compose -f "$COMPOSE_FILE" up -d
    
    log_info "Waiting for services to be healthy..."
    
    # Wait for services to be healthy
    timeout=300
    elapsed=0
    while [ $elapsed -lt $timeout ]; do
        if docker compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
            log_success "Services are healthy"
            break
        fi
        sleep 5
        elapsed=$((elapsed + 5))
        echo -n "."
    done
    
    if [ $elapsed -ge $timeout ]; then
        log_error "Services failed to become healthy within $timeout seconds"
        docker compose -f "$COMPOSE_FILE" logs
        exit 1
    fi
}

# Run health checks
health_check() {
    log_info "Running health checks..."
    
    # Check main health endpoint
    if curl -f http://localhost/health > /dev/null 2>&1; then
        log_success "Main health check passed"
    else
        log_error "Main health check failed"
        return 1
    fi
    
    # Check API endpoints
    if curl -f http://localhost/docs > /dev/null 2>&1; then
        log_success "API documentation accessible"
    else
        log_warning "API documentation not accessible"
    fi
    
    # Check tokenization endpoint
    if curl -X POST http://localhost/api/v1/tokenize \
        -H "Content-Type: application/json" \
        -d '{"text": "ทดสอบระบบ", "engine": "pythainlp"}' > /dev/null 2>&1; then
        log_success "Tokenization endpoint working"
    else
        log_error "Tokenization endpoint failed"
        return 1
    fi
    
    log_success "All health checks passed"
}

# Show deployment status
show_status() {
    log_info "Deployment Status:"
    echo "=================="
    
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    log_info "Service URLs:"
    echo "- Main API: http://localhost/"
    echo "- Health Check: http://localhost/health"
    echo "- API Documentation: http://localhost/docs"
    echo "- Monitoring (if enabled): http://localhost:3000"
    
    echo ""
    log_info "Logs:"
    echo "- View all logs: docker compose -f $COMPOSE_FILE logs -f"
    echo "- View specific service: docker compose -f $COMPOSE_FILE logs -f <service>"
}

# Main deployment process
main() {
    echo "Starting deployment process..."
    
    check_prerequisites
    create_backup
    deploy
    
    # Wait a bit for services to fully start
    sleep 10
    
    health_check
    show_status
    
    log_success "🎉 Production deployment completed successfully!"
    log_info "Monitor the logs and ensure everything is working correctly."
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "status")
        docker compose -f "$COMPOSE_FILE" ps
        ;;
    "logs")
        docker compose -f "$COMPOSE_FILE" logs -f "${2:-}"
        ;;
    "stop")
        log_info "Stopping production services..."
        docker compose -f "$COMPOSE_FILE" down
        log_success "Services stopped"
        ;;
    "restart")
        log_info "Restarting production services..."
        docker compose -f "$COMPOSE_FILE" restart
        log_success "Services restarted"
        ;;
    "health")
        health_check
        ;;
    *)
        echo "Usage: $0 {deploy|status|logs|stop|restart|health}"
        echo ""
        echo "Commands:"
        echo "  deploy  - Deploy production services (default)"
        echo "  status  - Show service status"
        echo "  logs    - Show service logs (optionally specify service name)"
        echo "  stop    - Stop all services"
        echo "  restart - Restart all services"
        echo "  health  - Run health checks"
        exit 1
        ;;
esac