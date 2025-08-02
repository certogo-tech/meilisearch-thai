#!/bin/bash
#
# Convenience script to stop Thai Tokenizer service in standalone mode.
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
FORCE=false
VERBOSE=false

# Parse additional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -f|--force)
            FORCE=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [install-path] [options]"
            echo "Options:"
            echo "  -f, --force      Force stop the service"
            echo "  -v, --verbose    Enable verbose output"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Example: $0 /opt/thai-tokenizer --force"
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

log "Stopping Thai Tokenizer service..."
log "Installation path: $INSTALL_PATH"

# Check if service is running
if [ "$VERBOSE" = true ]; then
    log "Checking current service status..."
fi

STATUS_OUTPUT=$(python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status --json 2>/dev/null || echo '{"running": false}')
IS_RUNNING=$(echo "$STATUS_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('running', False))" 2>/dev/null || echo "false")

if [ "$IS_RUNNING" != "True" ]; then
    log_warning "Service is not running"
    exit 0
fi

# Stop the service
log "Stopping service..."

STOP_ARGS="--install-path $INSTALL_PATH stop"
if [ "$FORCE" = true ]; then
    STOP_ARGS="$STOP_ARGS --force"
    log "Using force stop..."
fi

if [ "$VERBOSE" = true ]; then
    STOP_ARGS="$STOP_ARGS --verbose"
fi

python3 "$SCRIPT_DIR/manage-service.py" $STOP_ARGS

STOP_RESULT=$?

if [ $STOP_RESULT -eq 0 ]; then
    log_success "Service stopped successfully"
    
    # Verify service is stopped
    if [ "$VERBOSE" = true ]; then
        log "Verifying service is stopped..."
        sleep 2
        
        STATUS_OUTPUT=$(python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status --json 2>/dev/null || echo '{"running": false}')
        IS_RUNNING=$(echo "$STATUS_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('running', False))" 2>/dev/null || echo "false")
        
        if [ "$IS_RUNNING" != "True" ]; then
            log_success "Service is confirmed stopped"
        else
            log_warning "Service may still be running"
        fi
    fi
    
else
    log_error "Service stop failed with exit code: $STOP_RESULT"
    exit $STOP_RESULT
fi