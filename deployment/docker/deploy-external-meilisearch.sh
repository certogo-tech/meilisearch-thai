#!/bin/bash

# Thai Tokenizer Deployment Script for External Meilisearch
# Enhanced deployment script with comprehensive validation, monitoring, and recovery
# Requirements: 2.1, 2.2, 5.1, 5.2, 6.1

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.external-meilisearch.yml"
ENV_FILE="${SCRIPT_DIR}/.env.external-meilisearch"
ENV_TEMPLATE="${SCRIPT_DIR}/.env.external-meilisearch.template"

# Enhanced deployment tools
DEPLOYMENT_MANAGER="${SCRIPT_DIR}/docker-deployment-manager.py"
HEALTH_MONITOR="${SCRIPT_DIR}/docker-health-monitor.py"
BACKUP_RECOVERY="${SCRIPT_DIR}/docker-backup-recovery.py"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging functions
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

# Function to display usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS] COMMAND

Thai Tokenizer Deployment Script for External Meilisearch

COMMANDS:
    deploy      Deploy the Thai Tokenizer service
    start       Start the deployed service
    stop        Stop the running service
    restart     Restart the service
    status      Show service status
    logs        Show service logs
    health      Check service health
    validate    Validate configuration and connectivity
    cleanup     Remove all containers and volumes
    update      Update the service to latest version
    backup      Create backup of deployment
    restore     Restore from backup
    monitor     Start continuous health monitoring

OPTIONS:
    -h, --help              Show this help message
    -e, --env-file FILE     Use custom environment file (default: .env.external-meilisearch)
    -p, --profile PROFILE   Use Docker Compose profile (proxy, monitoring)
    -d, --detach           Run in detached mode
    -v, --verbose          Enable verbose output
    --no-build             Skip building Docker images
    --force                Force operation without confirmation
    --backup-id ID         Backup ID for restore operations
    --include-volumes      Include volumes in backup (default: true)
    --include-images       Include images in backup
    --monitor-interval N   Monitoring interval in seconds (default: 30)

EXAMPLES:
    $0 deploy                           # Deploy with default settings
    $0 deploy --profile proxy           # Deploy with Nginx proxy
    $0 validate                         # Validate Meilisearch connectivity
    $0 logs --follow                    # Follow service logs
    $0 health                          # Check service health
    $0 backup                          # Create deployment backup
    $0 restore --backup-id BACKUP_ID   # Restore from backup
    $0 monitor                         # Start health monitoring

ENVIRONMENT:
    Copy ${ENV_TEMPLATE} to ${ENV_FILE}
    and customize the configuration for your external Meilisearch setup.

EOF
}

# Function to check prerequisites
check_prerequisites() {
    log_info "Checking prerequisites..."
    
    # Check if Docker is installed and running
    if ! command -v docker &> /dev/null; then
        log_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    if ! docker info &> /dev/null; then
        log_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    # Check if Docker Compose is available
    if ! docker compose version &> /dev/null; then
        log_error "Docker Compose is not available. Please install Docker Compose."
        exit 1
    fi
    
    # Check if environment file exists
    if [[ ! -f "$ENV_FILE" ]]; then
        log_warning "Environment file not found: $ENV_FILE"
        log_info "Creating environment file from template..."
        cp "$ENV_TEMPLATE" "$ENV_FILE"
        log_warning "Please edit $ENV_FILE with your Meilisearch configuration before proceeding."
        return 1
    fi
    
    log_success "Prerequisites check passed"
    return 0
}

# Function to validate Meilisearch connectivity
validate_meilisearch() {
    log_info "Validating Meilisearch connectivity..."
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    # Check if required variables are set
    if [[ -z "${MEILISEARCH_HOST:-}" ]]; then
        log_error "MEILISEARCH_HOST is not set in environment file"
        return 1
    fi
    
    if [[ -z "${MEILISEARCH_API_KEY:-}" ]]; then
        log_error "MEILISEARCH_API_KEY is not set in environment file"
        return 1
    fi
    
    # Test Meilisearch connectivity
    log_info "Testing connection to Meilisearch at: $MEILISEARCH_HOST"
    
    # Extract host and port from MEILISEARCH_HOST
    MEILISEARCH_URL="${MEILISEARCH_HOST}/health"
    
    if curl -f -s --max-time 10 "$MEILISEARCH_URL" > /dev/null; then
        log_success "Meilisearch is accessible at $MEILISEARCH_HOST"
    else
        log_error "Cannot connect to Meilisearch at $MEILISEARCH_HOST"
        log_error "Please verify that:"
        log_error "  1. Meilisearch is running and accessible"
        log_error "  2. The host and port are correct"
        log_error "  3. Network connectivity is available"
        return 1
    fi
    
    # Test API key authentication
    log_info "Testing Meilisearch API key authentication..."
    AUTH_URL="${MEILISEARCH_HOST}/keys"
    
    if curl -f -s --max-time 10 -H "Authorization: Bearer $MEILISEARCH_API_KEY" "$AUTH_URL" > /dev/null; then
        log_success "Meilisearch API key authentication successful"
    else
        log_error "Meilisearch API key authentication failed"
        log_error "Please verify that the API key is correct and has sufficient permissions"
        return 1
    fi
    
    return 0
}

# Function to deploy the service
deploy_service() {
    local profiles=()
    local build_flag="--build"
    local detach_flag=""
    
    # Parse deployment options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --profile)
                profiles+=("--profile" "$2")
                shift 2
                ;;
            --no-build)
                build_flag=""
                shift
                ;;
            -d|--detach)
                detach_flag="-d"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "Deploying Thai Tokenizer service with external Meilisearch..."
    
    # Validate configuration first
    if ! validate_meilisearch; then
        log_error "Meilisearch validation failed. Please fix the configuration before deploying."
        return 1
    fi
    
    # Create necessary directories
    log_info "Creating necessary directories..."
    mkdir -p "${PROJECT_ROOT}/logs/thai-tokenizer"
    mkdir -p "${PROJECT_ROOT}/logs/nginx"
    
    # Deploy the service
    log_info "Starting Docker Compose deployment..."
    
    cd "$SCRIPT_DIR"
    
    if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" \
        "${profiles[@]}" up $build_flag $detach_flag; then
        log_success "Thai Tokenizer service deployed successfully"
        
        # Wait for service to be healthy
        log_info "Waiting for service to become healthy..."
        sleep 10
        
        if check_service_health; then
            log_success "Service is healthy and ready to use"
            show_service_info
        else
            log_warning "Service deployed but health check failed"
            log_info "Check logs with: $0 logs"
        fi
    else
        log_error "Deployment failed"
        return 1
    fi
}

# Function to check service health
check_service_health() {
    log_info "Checking service health..."
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    local service_port="${THAI_TOKENIZER_PORT:-8000}"
    local health_url="http://localhost:${service_port}/health"
    local detailed_health_url="http://localhost:${service_port}/health/detailed"
    
    # Basic health check
    if curl -f -s --max-time 10 "$health_url" > /dev/null; then
        log_success "Basic health check passed"
    else
        log_error "Basic health check failed"
        return 1
    fi
    
    # Detailed health check
    log_info "Performing detailed health check..."
    local health_response
    health_response=$(curl -f -s --max-time 15 "$detailed_health_url" 2>/dev/null || echo "")
    
    if [[ -n "$health_response" ]]; then
        # Check if Meilisearch status is healthy
        if echo "$health_response" | grep -q '"meilisearch_status":"healthy"'; then
            log_success "Meilisearch connectivity check passed"
        else
            log_error "Meilisearch connectivity check failed"
            log_error "Health response: $health_response"
            return 1
        fi
        
        # Check if Thai tokenizer is working
        if echo "$health_response" | grep -q '"tokenizer_status":"healthy"'; then
            log_success "Thai tokenizer check passed"
        else
            log_warning "Thai tokenizer check failed or not available"
        fi
    else
        log_error "Could not retrieve detailed health information"
        return 1
    fi
    
    return 0
}

# Function to show service information
show_service_info() {
    log_info "Service Information:"
    
    # Source environment variables
    set -a
    source "$ENV_FILE"
    set +a
    
    local service_port="${THAI_TOKENIZER_PORT:-8000}"
    local nginx_port="${NGINX_HTTP_PORT:-80}"
    
    echo "  Thai Tokenizer API: http://localhost:${service_port}"
    echo "  Health Check: http://localhost:${service_port}/health"
    echo "  Detailed Health: http://localhost:${service_port}/health/detailed"
    echo "  Metrics: http://localhost:${service_port}/metrics"
    
    if docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps --services | grep -q nginx; then
        echo "  Nginx Proxy: http://localhost:${nginx_port}"
    fi
    
    echo "  External Meilisearch: ${MEILISEARCH_HOST:-Not configured}"
}

# Function to show service logs
show_logs() {
    local follow_flag=""
    local service=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -f|--follow)
                follow_flag="-f"
                shift
                ;;
            --service)
                service="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    cd "$SCRIPT_DIR"
    
    if [[ -n "$service" ]]; then
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs $follow_flag "$service"
    else
        docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" logs $follow_flag
    fi
}

# Function to show service status
show_status() {
    cd "$SCRIPT_DIR"
    
    log_info "Service Status:"
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps
    
    echo ""
    log_info "Container Resource Usage:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}" \
        $(docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" ps -q) 2>/dev/null || true
}

# Function to cleanup deployment
cleanup_deployment() {
    local force_flag=""
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            --force)
                force_flag="true"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    if [[ "$force_flag" != "true" ]]; then
        log_warning "This will remove all containers, networks, and volumes."
        read -p "Are you sure you want to continue? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Cleanup cancelled"
            return 0
        fi
    fi
    
    log_info "Cleaning up deployment..."
    
    cd "$SCRIPT_DIR"
    
    # Stop and remove containers
    docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" down --volumes --remove-orphans
    
    # Remove unused networks
    docker network prune -f
    
    # Remove unused volumes (be careful with this)
    log_warning "Removing unused Docker volumes..."
    docker volume prune -f
    
    log_success "Cleanup completed"
}

# Enhanced deployment with comprehensive validation
deploy_with_validation() {
    local profiles=()
    local build_flag="--build"
    local detach_flag="-d"
    
    # Parse deployment options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --profile)
                profiles+=("$2")
                shift 2
                ;;
            --no-build)
                build_flag=""
                shift
                ;;
            --no-detach)
                detach_flag=""
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "Starting enhanced deployment with comprehensive validation..."
    
    # Use Python deployment manager for enhanced validation
    if command -v python3 &> /dev/null && [[ -f "$DEPLOYMENT_MANAGER" ]]; then
        log_info "Using enhanced deployment manager..."
        
        # Build Python command
        local python_cmd="python3 $DEPLOYMENT_MANAGER deploy"
        
        if [[ ${#profiles[@]} -gt 0 ]]; then
            for profile in "${profiles[@]}"; do
                python_cmd+=" --profile $profile"
            done
        fi
        
        if [[ -z "$build_flag" ]]; then
            python_cmd+=" --no-build"
        fi
        
        if [[ -z "$detach_flag" ]]; then
            python_cmd+=" --no-detach"
        fi
        
        # Execute enhanced deployment
        if eval "$python_cmd"; then
            log_success "Enhanced deployment completed successfully"
            
            # Start health monitoring if available
            if [[ -f "$HEALTH_MONITOR" ]]; then
                log_info "Health monitoring available. Run '$0 monitor' to start continuous monitoring."
            fi
            
            return 0
        else
            log_error "Enhanced deployment failed"
            return 1
        fi
    else
        log_warning "Enhanced deployment manager not available, falling back to basic deployment"
        deploy_service "$@"
    fi
}

# Enhanced health check with detailed reporting
check_enhanced_health() {
    log_info "Performing enhanced health check..."
    
    if command -v python3 &> /dev/null && [[ -f "$HEALTH_MONITOR" ]]; then
        log_info "Using enhanced health monitor..."
        
        if python3 "$HEALTH_MONITOR" health; then
            log_success "Enhanced health check completed"
            return 0
        else
            log_error "Enhanced health check failed"
            return 1
        fi
    else
        log_warning "Enhanced health monitor not available, falling back to basic health check"
        check_service_health
    fi
}

# Create deployment backup
create_backup() {
    local include_volumes="true"
    local include_images="false"
    local include_logs="true"
    
    # Parse backup options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --include-images)
                include_images="true"
                shift
                ;;
            --no-volumes)
                include_volumes="false"
                shift
                ;;
            --no-logs)
                include_logs="false"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "Creating deployment backup..."
    
    if command -v python3 &> /dev/null && [[ -f "$BACKUP_RECOVERY" ]]; then
        local backup_cmd="python3 $BACKUP_RECOVERY backup"
        
        if [[ "$include_volumes" == "true" ]]; then
            backup_cmd+=" --include-volumes"
        fi
        
        if [[ "$include_images" == "true" ]]; then
            backup_cmd+=" --include-images"
        fi
        
        if [[ "$include_logs" == "true" ]]; then
            backup_cmd+=" --include-logs"
        fi
        
        if eval "$backup_cmd"; then
            log_success "Backup created successfully"
            return 0
        else
            log_error "Backup creation failed"
            return 1
        fi
    else
        log_error "Backup manager not available"
        return 1
    fi
}

# Restore from backup
restore_backup() {
    local backup_id=""
    local restore_volumes="true"
    local restore_images="false"
    local restore_configuration="true"
    
    # Parse restore options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --backup-id)
                backup_id="$2"
                shift 2
                ;;
            --restore-images)
                restore_images="true"
                shift
                ;;
            --no-volumes)
                restore_volumes="false"
                shift
                ;;
            --no-configuration)
                restore_configuration="false"
                shift
                ;;
            *)
                shift
                ;;
        esac
    done
    
    if [[ -z "$backup_id" ]]; then
        log_error "Backup ID is required for restore operation"
        log_info "Available backups:"
        if command -v python3 &> /dev/null && [[ -f "$BACKUP_RECOVERY" ]]; then
            python3 "$BACKUP_RECOVERY" list
        fi
        return 1
    fi
    
    log_info "Restoring from backup: $backup_id"
    
    if command -v python3 &> /dev/null && [[ -f "$BACKUP_RECOVERY" ]]; then
        local restore_cmd="python3 $BACKUP_RECOVERY restore --backup-id $backup_id"
        
        if [[ "$restore_volumes" == "true" ]]; then
            restore_cmd+=" --restore-volumes"
        fi
        
        if [[ "$restore_images" == "true" ]]; then
            restore_cmd+=" --restore-images"
        fi
        
        if [[ "$restore_configuration" == "true" ]]; then
            restore_cmd+=" --restore-configuration"
        fi
        
        if eval "$restore_cmd"; then
            log_success "Restore completed successfully"
            return 0
        else
            log_error "Restore failed"
            return 1
        fi
    else
        log_error "Backup recovery manager not available"
        return 1
    fi
}

# Start continuous health monitoring
start_monitoring() {
    local interval="30"
    
    # Parse monitoring options
    while [[ $# -gt 0 ]]; do
        case $1 in
            --interval)
                interval="$2"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done
    
    log_info "Starting continuous health monitoring (interval: ${interval}s)"
    
    if command -v python3 &> /dev/null && [[ -f "$HEALTH_MONITOR" ]]; then
        python3 "$HEALTH_MONITOR" monitor --interval "$interval"
    else
        log_error "Health monitor not available"
        return 1
    fi
}

# Enhanced validation with comprehensive checks
validate_comprehensive() {
    log_info "Performing comprehensive validation..."
    
    if command -v python3 &> /dev/null && [[ -f "$DEPLOYMENT_MANAGER" ]]; then
        if python3 "$DEPLOYMENT_MANAGER" validate; then
            log_success "Comprehensive validation passed"
            return 0
        else
            log_error "Comprehensive validation failed"
            return 1
        fi
    else
        log_warning "Enhanced validation not available, falling back to basic validation"
        check_prerequisites || return 1
        validate_meilisearch
    fi
}

# Main script logic
main() {
    local command=""
    local env_file_override=""
    local verbose=false
    
    # Parse global options
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -e|--env-file)
                env_file_override="$2"
                shift 2
                ;;
            -v|--verbose)
                verbose=true
                set -x
                shift
                ;;
            deploy|start|stop|restart|status|logs|health|validate|cleanup|update|backup|restore|monitor)
                command="$1"
                shift
                break
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done
    
    # Override environment file if specified
    if [[ -n "$env_file_override" ]]; then
        ENV_FILE="$env_file_override"
    fi
    
    # Check if command was provided
    if [[ -z "$command" ]]; then
        log_error "No command specified"
        usage
        exit 1
    fi
    
    # Execute command
    case "$command" in
        deploy)
            check_prerequisites || exit 1
            deploy_with_validation "$@"
            ;;
        start)
            cd "$SCRIPT_DIR"
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" start
            ;;
        stop)
            cd "$SCRIPT_DIR"
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" stop
            ;;
        restart)
            cd "$SCRIPT_DIR"
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" restart
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$@"
            ;;
        health)
            check_enhanced_health
            ;;
        validate)
            validate_comprehensive
            ;;
        cleanup)
            cleanup_deployment "$@"
            ;;
        update)
            log_info "Updating service..."
            cd "$SCRIPT_DIR"
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
            docker compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d --build
            ;;
        backup)
            create_backup "$@"
            ;;
        restore)
            restore_backup "$@"
            ;;
        monitor)
            start_monitoring "$@"
            ;;
        *)
            log_error "Unknown command: $command"
            usage
            exit 1
            ;;
    esac
}

# Run main function with all arguments
main "$@"