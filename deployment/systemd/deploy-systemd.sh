#!/bin/bash
"""
Comprehensive systemd deployment script for Thai Tokenizer.

This script provides a complete deployment solution including system preparation,
service installation, configuration management, and post-deployment validation.
"""

set -euo pipefail

# Script configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SERVICE_NAME="thai-tokenizer"
DEFAULT_INSTALLATION_PATH="/opt/thai-tokenizer"
DEFAULT_SERVICE_PORT="8000"

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

# Check if running as root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Display usage information
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy Thai Tokenizer as a systemd service.

OPTIONS:
    -h, --help                  Show this help message
    -m, --meilisearch-host     Meilisearch server host URL (required)
    -k, --meilisearch-key      Meilisearch API key (required)
    -p, --port                 Service port (default: 8000)
    -i, --install-path         Installation directory (default: /opt/thai-tokenizer)
    -u, --user                 Service user name (default: thai-tokenizer)
    -g, --group                Service group name (default: thai-tokenizer)
    --skip-validation          Skip pre-deployment validation
    --dry-run                  Show what would be done without making changes
    --uninstall                Uninstall the service
    --config-file              Use configuration from JSON file

EXAMPLES:
    # Basic deployment
    sudo $0 -m http://localhost:7700 -k your-api-key

    # Custom port and installation path
    sudo $0 -m https://meilisearch.example.com -k your-api-key -p 8080 -i /opt/custom/thai-tokenizer

    # Uninstall service
    sudo $0 --uninstall

    # Dry run to see what would be done
    sudo $0 -m http://localhost:7700 -k your-api-key --dry-run

EOF
}

# Parse command line arguments
parse_arguments() {
    MEILISEARCH_HOST=""
    MEILISEARCH_API_KEY=""
    SERVICE_PORT="$DEFAULT_SERVICE_PORT"
    INSTALLATION_PATH="$DEFAULT_INSTALLATION_PATH"
    SERVICE_USER="$SERVICE_NAME"
    SERVICE_GROUP="$SERVICE_NAME"
    SKIP_VALIDATION=false
    DRY_RUN=false
    UNINSTALL=false
    CONFIG_FILE=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                usage
                exit 0
                ;;
            -m|--meilisearch-host)
                MEILISEARCH_HOST="$2"
                shift 2
                ;;
            -k|--meilisearch-key)
                MEILISEARCH_API_KEY="$2"
                shift 2
                ;;
            -p|--port)
                SERVICE_PORT="$2"
                shift 2
                ;;
            -i|--install-path)
                INSTALLATION_PATH="$2"
                shift 2
                ;;
            -u|--user)
                SERVICE_USER="$2"
                shift 2
                ;;
            -g|--group)
                SERVICE_GROUP="$2"
                shift 2
                ;;
            --skip-validation)
                SKIP_VALIDATION=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --uninstall)
                UNINSTALL=true
                shift
                ;;
            --config-file)
                CONFIG_FILE="$2"
                shift 2
                ;;
            *)
                log_error "Unknown option: $1"
                usage
                exit 1
                ;;
        esac
    done

    # Validate required arguments for installation
    if [[ "$UNINSTALL" == false && -z "$CONFIG_FILE" ]]; then
        if [[ -z "$MEILISEARCH_HOST" || -z "$MEILISEARCH_API_KEY" ]]; then
            log_error "Meilisearch host and API key are required for installation"
            usage
            exit 1
        fi
    fi
}

# Validate system requirements
validate_system() {
    log_info "Validating system requirements..."

    # Check systemd
    if ! command -v systemctl &> /dev/null; then
        log_error "systemd is not available on this system"
        return 1
    fi
    log_success "systemd is available"

    # Check Python version
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)" 2>/dev/null; then
        log_error "Python 3.12+ is required"
        return 1
    fi
    log_success "Python version is compatible"

    # Check uv package manager
    if ! command -v uv &> /dev/null; then
        log_error "uv package manager is required but not found"
        log_info "Install uv from: https://docs.astral.sh/uv/getting-started/installation/"
        return 1
    fi
    log_success "uv package manager is available"

    # Check disk space
    local available_space
    available_space=$(df "$INSTALLATION_PATH" 2>/dev/null | awk 'NR==2 {print $4}' || echo "0")
    local available_gb=$((available_space / 1024 / 1024))
    
    if [[ $available_gb -lt 1 ]]; then
        log_error "Insufficient disk space: ${available_gb}GB available, need at least 1GB"
        return 1
    fi
    log_success "Disk space available: ${available_gb}GB"

    # Check port availability
    if ss -tuln | grep -q ":$SERVICE_PORT "; then
        log_error "Port $SERVICE_PORT is already in use"
        return 1
    fi
    log_success "Port $SERVICE_PORT is available"

    return 0
}

# Create system user and group
create_user() {
    log_info "Creating system user and group..."

    # Create group if it doesn't exist
    if ! getent group "$SERVICE_GROUP" &>/dev/null; then
        groupadd --system "$SERVICE_GROUP"
        log_success "Created system group: $SERVICE_GROUP"
    else
        log_info "System group already exists: $SERVICE_GROUP"
    fi

    # Create user if it doesn't exist
    if ! getent passwd "$SERVICE_USER" &>/dev/null; then
        useradd --system \
                --gid "$SERVICE_GROUP" \
                --home-dir "$INSTALLATION_PATH" \
                --create-home \
                --shell /bin/false \
                --comment "Thai Tokenizer Service User" \
                "$SERVICE_USER"
        log_success "Created system user: $SERVICE_USER"
    else
        log_info "System user already exists: $SERVICE_USER"
    fi
}

# Set up directories
setup_directories() {
    log_info "Setting up directories..."

    local directories=(
        "$INSTALLATION_PATH"
        "/var/lib/$SERVICE_NAME"
        "/var/log/$SERVICE_NAME"
        "/etc/$SERVICE_NAME"
    )

    for dir in "${directories[@]}"; do
        mkdir -p "$dir"
        chown "$SERVICE_USER:$SERVICE_GROUP" "$dir"
        
        # Set appropriate permissions
        if [[ "$dir" == "/etc/$SERVICE_NAME" ]]; then
            chmod 750 "$dir"  # More restrictive for config
        else
            chmod 755 "$dir"
        fi
        
        log_success "Created directory: $dir"
    done
}

# Install Python dependencies
install_dependencies() {
    log_info "Installing Python dependencies..."

    # Create virtual environment
    local venv_path="$INSTALLATION_PATH/venv"
    
    if [[ ! -d "$venv_path" ]]; then
        python3 -m venv "$venv_path"
        log_success "Created virtual environment: $venv_path"
    fi

    # Install dependencies using uv
    cd "$PROJECT_ROOT"
    "$venv_path/bin/python" -m pip install uv
    "$venv_path/bin/uv" pip install -r requirements.txt
    
    log_success "Installed Python dependencies"

    # Copy source code
    rsync -av --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
          "$PROJECT_ROOT/src/" "$INSTALLATION_PATH/src/"
    
    # Set ownership
    chown -R "$SERVICE_USER:$SERVICE_GROUP" "$INSTALLATION_PATH"
    
    log_success "Copied source code to $INSTALLATION_PATH"
}

# Generate configuration files
generate_config() {
    log_info "Generating configuration files..."

    # Use Python script to generate configuration
    local python_args=(
        "--meilisearch-host" "$MEILISEARCH_HOST"
        "--meilisearch-api-key" "$MEILISEARCH_API_KEY"
        "--port" "$SERVICE_PORT"
        "--installation-path" "$INSTALLATION_PATH"
    )

    if [[ "$SKIP_VALIDATION" == true ]]; then
        python_args+=("--skip-validation")
    fi

    if [[ "$DRY_RUN" == true ]]; then
        python_args+=("--dry-run")
    fi

    if [[ -n "$CONFIG_FILE" ]]; then
        python_args+=("--config-file" "$CONFIG_FILE")
    fi

    python3 "$SCRIPT_DIR/install-systemd-service.py" "${python_args[@]}"
}

# Install and enable service
install_service() {
    log_info "Installing and enabling systemd service..."

    # Enable and start service
    systemctl daemon-reload
    systemctl enable "$SERVICE_NAME"
    
    log_success "Service enabled for automatic startup"

    # Start service
    if systemctl start "$SERVICE_NAME"; then
        log_success "Service started successfully"
    else
        log_error "Failed to start service"
        log_info "Check service status with: systemctl status $SERVICE_NAME"
        log_info "Check service logs with: journalctl -u $SERVICE_NAME -f"
        return 1
    fi
}

# Validate deployment
validate_deployment() {
    log_info "Validating deployment..."

    # Check service status
    if systemctl is-active --quiet "$SERVICE_NAME"; then
        log_success "Service is running"
    else
        log_error "Service is not running"
        return 1
    fi

    # Check application health
    local max_attempts=30
    local attempt=1
    
    while [[ $attempt -le $max_attempts ]]; do
        if curl -f -s "http://localhost:$SERVICE_PORT/health" >/dev/null 2>&1; then
            log_success "Application health check passed"
            break
        fi
        
        if [[ $attempt -eq $max_attempts ]]; then
            log_error "Application health check failed after $max_attempts attempts"
            return 1
        fi
        
        log_info "Waiting for application to start... (attempt $attempt/$max_attempts)"
        sleep 2
        ((attempt++))
    done

    # Test Thai tokenization
    local test_response
    test_response=$(curl -s -X POST "http://localhost:$SERVICE_PORT/tokenize" \
                         -H "Content-Type: application/json" \
                         -d '{"text": "สวัสดีครับ"}' || echo "")
    
    if [[ -n "$test_response" ]] && echo "$test_response" | grep -q "tokens"; then
        log_success "Thai tokenization test passed"
    else
        log_warning "Thai tokenization test failed or returned unexpected response"
    fi

    return 0
}

# Uninstall service
uninstall_service() {
    log_info "Uninstalling Thai Tokenizer systemd service..."

    # Stop service if running
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl stop "$SERVICE_NAME"
        log_success "Stopped service"
    fi

    # Disable service
    if systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        systemctl disable "$SERVICE_NAME"
        log_success "Disabled service"
    fi

    # Remove service file
    local service_file="/etc/systemd/system/$SERVICE_NAME.service"
    if [[ -f "$service_file" ]]; then
        rm -f "$service_file"
        log_success "Removed service file: $service_file"
    fi

    # Remove override directory
    local override_dir="/etc/systemd/system/$SERVICE_NAME.service.d"
    if [[ -d "$override_dir" ]]; then
        rm -rf "$override_dir"
        log_success "Removed override directory: $override_dir"
    fi

    # Remove logrotate configuration
    local logrotate_file="/etc/logrotate.d/$SERVICE_NAME"
    if [[ -f "$logrotate_file" ]]; then
        rm -f "$logrotate_file"
        log_success "Removed logrotate configuration: $logrotate_file"
    fi

    # Reload systemd daemon
    systemctl daemon-reload
    log_success "Reloaded systemd daemon"

    log_success "Uninstallation completed"
    log_info "Note: User, group, and data directories were not removed"
    log_info "To remove user: userdel $SERVICE_USER"
    log_info "To remove group: groupdel $SERVICE_GROUP"
    log_info "To remove directories: rm -rf $INSTALLATION_PATH /var/lib/$SERVICE_NAME /var/log/$SERVICE_NAME /etc/$SERVICE_NAME"
}

# Display deployment summary
show_summary() {
    log_success "Deployment completed successfully!"
    echo
    echo "Service Information:"
    echo "  Name: $SERVICE_NAME"
    echo "  Port: $SERVICE_PORT"
    echo "  User: $SERVICE_USER"
    echo "  Group: $SERVICE_GROUP"
    echo "  Installation: $INSTALLATION_PATH"
    echo
    echo "Useful Commands:"
    echo "  Start service:    systemctl start $SERVICE_NAME"
    echo "  Stop service:     systemctl stop $SERVICE_NAME"
    echo "  Restart service:  systemctl restart $SERVICE_NAME"
    echo "  Service status:   systemctl status $SERVICE_NAME"
    echo "  Service logs:     journalctl -u $SERVICE_NAME -f"
    echo "  Health check:     curl http://localhost:$SERVICE_PORT/health"
    echo
    echo "Management Script:"
    echo "  $SCRIPT_DIR/manage-service.py --help"
}

# Main deployment function
main() {
    log_info "Starting Thai Tokenizer systemd deployment..."

    # Check if running as root
    check_root

    # Parse command line arguments
    parse_arguments "$@"

    # Handle dry run
    if [[ "$DRY_RUN" == true ]]; then
        log_info "DRY RUN MODE - No changes will be made"
        echo "Configuration:"
        echo "  Service name: $SERVICE_NAME"
        echo "  Service port: $SERVICE_PORT"
        echo "  Installation path: $INSTALLATION_PATH"
        echo "  Service user: $SERVICE_USER"
        echo "  Service group: $SERVICE_GROUP"
        echo "  Meilisearch host: $MEILISEARCH_HOST"
        exit 0
    fi

    # Handle uninstall
    if [[ "$UNINSTALL" == true ]]; then
        uninstall_service
        exit 0
    fi

    # Validate system requirements
    if [[ "$SKIP_VALIDATION" == false ]]; then
        if ! validate_system; then
            log_error "System validation failed"
            exit 1
        fi
    fi

    # Create user and directories
    create_user
    setup_directories

    # Install dependencies
    install_dependencies

    # Generate configuration and install service
    generate_config

    # Install and start service
    if ! install_service; then
        log_error "Service installation failed"
        exit 1
    fi

    # Validate deployment
    if ! validate_deployment; then
        log_error "Deployment validation failed"
        exit 1
    fi

    # Show summary
    show_summary
}

# Run main function with all arguments
main "$@"