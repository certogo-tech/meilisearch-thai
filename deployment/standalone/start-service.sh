#!/bin/bash
#
# Enhanced convenience script to start Thai Tokenizer service in standalone mode.
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"

# Default installation path
DEFAULT_INSTALL_PATH="/opt/thai-tokenizer"

# Parse arguments
INSTALL_PATH="${1:-$DEFAULT_INSTALL_PATH}"
VERBOSE=false
WAIT_FOR_HEALTH=false

# Parse additional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -w|--wait)
            WAIT_FOR_HEALTH=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [install-path] [options]"
            echo "Options:"
            echo "  -v, --verbose    Enable verbose output"
            echo "  -w, --wait       Wait for service to become healthy"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Example: $0 /opt/thai-tokenizer --verbose --wait"
            exit 0
            ;;
        *)
            if [ -z "$INSTALL_PATH" ] || [ "$INSTALL_PATH" = "$DEFAULT_INSTALL_PATH" ]; then
                INSTALL_PATH="$1"
            fi
            shift
            ;;
    esac
done

# Logging function
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

log_error() {
    echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
}

# Validation
if [ ! -d "$INSTALL_PATH" ]; then
    log_error "Installation path not found: $INSTALL_PATH"
    echo "Usage: $0 [install-path] [options]"
    echo "Example: $0 /opt/thai-tokenizer"
    exit 1
fi

log "Starting Thai Tokenizer service..."
log "Installation path: $INSTALL_PATH"

# Check if service is already running
if [ "$VERBOSE" = true ]; then
    log "Checking current service status..."
fi

STATUS_OUTPUT=$(python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status --json 2>/dev/null || echo '{"running": false}')
IS_RUNNING=$(echo "$STATUS_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('running', False))" 2>/dev/null || echo "false")

if [ "$IS_RUNNING" = "True" ]; then
    log_warning "Service is already running"
    
    if [ "$VERBOSE" = true ]; then
        python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status
    fi
    
    exit 0
fi

# Pre-start validation
if [ "$VERBOSE" = true ]; then
    log "Running pre-start validation..."
    
    # Check configuration
    if [ ! -f "$INSTALL_PATH/config/config.json" ]; then
        log_error "Configuration file not found: $INSTALL_PATH/config/config.json"
        exit 1
    fi
    
    # Check virtual environment
    if [ ! -f "$INSTALL_PATH/venv/bin/python" ]; then
        log_error "Virtual environment not found: $INSTALL_PATH/venv"
        exit 1
    fi
    
    log_success "Pre-start validation passed"
fi

# Start the service
log "Starting service..."

if [ "$VERBOSE" = true ]; then
    python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" start --verbose
else
    python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" start
fi

START_RESULT=$?

if [ $START_RESULT -eq 0 ]; then
    log_success "Service start command completed successfully"
    
    # Wait for service to become healthy if requested
    if [ "$WAIT_FOR_HEALTH" = true ]; then
        log "Waiting for service to become healthy..."
        
        MAX_WAIT=30
        WAIT_COUNT=0
        
        while [ $WAIT_COUNT -lt $MAX_WAIT ]; do
            sleep 2
            WAIT_COUNT=$((WAIT_COUNT + 2))
            
            STATUS_OUTPUT=$(python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status --json 2>/dev/null || echo '{"running": false}')
            IS_HEALTHY=$(echo "$STATUS_OUTPUT" | python3 -c "import sys, json; data=json.load(sys.stdin); print(data.get('health_check', {}).get('healthy', False))" 2>/dev/null || echo "false")
            
            if [ "$IS_HEALTHY" = "True" ]; then
                log_success "Service is healthy and ready"
                break
            fi
            
            if [ "$VERBOSE" = true ]; then
                log "Waiting for health check... ($WAIT_COUNT/${MAX_WAIT}s)"
            fi
        done
        
        if [ "$IS_HEALTHY" != "True" ]; then
            log_warning "Service started but health check is not passing after ${MAX_WAIT}s"
            log_warning "Check logs: tail -f $INSTALL_PATH/logs/thai-tokenizer.log"
        fi
    fi
    
    # Show status
    if [ "$VERBOSE" = true ]; then
        log "Current service status:"
        python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status
    fi
    
    log_success "Service management commands:"
    echo "  Status:  python3 $SCRIPT_DIR/manage-service.py --install-path $INSTALL_PATH status"
    echo "  Stop:    python3 $SCRIPT_DIR/manage-service.py --install-path $INSTALL_PATH stop"
    echo "  Logs:    python3 $SCRIPT_DIR/manage-service.py --install-path $INSTALL_PATH logs"
    echo "  Monitor: python3 $SCRIPT_DIR/manage-service.py --install-path $INSTALL_PATH monitor"
    
else
    log_error "Service start failed with exit code: $START_RESULT"
    log_error "Check logs for details: tail -f $INSTALL_PATH/logs/thai-tokenizer.log"
    exit $START_RESULT
fi