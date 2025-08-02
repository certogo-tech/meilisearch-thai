#!/bin/bash
#
# Convenience script to restart Thai Tokenizer service in standalone mode.
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
            echo "  -w, --wait       Wait for service to become healthy after restart"
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

# Logging functions
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

log "Restarting Thai Tokenizer service..."
log "Installation path: $INSTALL_PATH"

# Use the process manager to restart the service
RESTART_ARGS="--install-path $INSTALL_PATH restart"

if [ "$VERBOSE" = true ]; then
    RESTART_ARGS="$RESTART_ARGS --verbose"
fi

python3 "$SCRIPT_DIR/manage-service.py" $RESTART_ARGS

RESTART_RESULT=$?

if [ $RESTART_RESULT -eq 0 ]; then
    log_success "Service restart command completed successfully"
    
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
            log_warning "Service restarted but health check is not passing after ${MAX_WAIT}s"
            log_warning "Check logs: tail -f $INSTALL_PATH/logs/thai-tokenizer.log"
        fi
    fi
    
    # Show status
    if [ "$VERBOSE" = true ]; then
        log "Current service status:"
        python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status
    fi
    
else
    log_error "Service restart failed with exit code: $RESTART_RESULT"
    log_error "Check logs for details: tail -f $INSTALL_PATH/logs/thai-tokenizer.log"
    exit $RESTART_RESULT
fi