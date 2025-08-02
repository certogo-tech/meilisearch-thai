#!/bin/bash
#
# Convenience script to check Thai Tokenizer service status in standalone mode.
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
JSON_OUTPUT=false
DETAILED=false
CONTINUOUS=false
INTERVAL=5

# Parse additional arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -j|--json)
            JSON_OUTPUT=true
            shift
            ;;
        -d|--detailed)
            DETAILED=true
            shift
            ;;
        -c|--continuous)
            CONTINUOUS=true
            shift
            ;;
        -i|--interval)
            INTERVAL="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [install-path] [options]"
            echo "Options:"
            echo "  -j, --json       Output status as JSON"
            echo "  -d, --detailed   Show detailed status information"
            echo "  -c, --continuous Monitor status continuously"
            echo "  -i, --interval   Interval for continuous monitoring (default: 5s)"
            echo "  -h, --help       Show this help message"
            echo ""
            echo "Example: $0 /opt/thai-tokenizer --detailed"
            echo "Example: $0 /opt/thai-tokenizer --continuous --interval 10"
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
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
    fi
}

log_success() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "${GREEN}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
    fi
}

log_warning() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "${YELLOW}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
    fi
}

log_error() {
    if [ "$JSON_OUTPUT" != true ]; then
        echo -e "${RED}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1"
    fi
}

# Validation
if [ ! -d "$INSTALL_PATH" ]; then
    log_error "Installation path not found: $INSTALL_PATH"
    echo "Usage: $0 [install-path] [options]"
    echo "Example: $0 /opt/thai-tokenizer"
    exit 1
fi

# Function to get and display status
show_status() {
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    if [ "$JSON_OUTPUT" = true ]; then
        python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status --json
    else
        if [ "$CONTINUOUS" = true ]; then
            echo -e "\n${BLUE}=== Status Check at $timestamp ===${NC}"
        fi
        
        if [ "$DETAILED" = true ]; then
            # Show detailed status
            python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status
            
            # Show performance metrics
            echo -e "\n${BLUE}Performance Metrics:${NC}"
            python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" metrics
            
        else
            # Show basic status
            python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status
        fi
    fi
}

# Handle continuous monitoring
if [ "$CONTINUOUS" = true ]; then
    if [ "$JSON_OUTPUT" = true ]; then
        log_error "Continuous monitoring is not compatible with JSON output"
        exit 1
    fi
    
    log "Starting continuous status monitoring..."
    log "Installation path: $INSTALL_PATH"
    log "Interval: ${INTERVAL}s"
    log "Press Ctrl+C to stop"
    echo ""
    
    # Trap Ctrl+C
    trap 'echo -e "\n${YELLOW}Monitoring stopped${NC}"; exit 0' INT
    
    while true; do
        show_status
        sleep "$INTERVAL"
    done
else
    # Single status check
    if [ "$JSON_OUTPUT" != true ]; then
        log "Checking Thai Tokenizer service status..."
        log "Installation path: $INSTALL_PATH"
        echo ""
    fi
    
    show_status
    
    # Set exit code based on service status
    if [ "$JSON_OUTPUT" != true ]; then
        STATUS_OUTPUT=$(python3 "$SCRIPT_DIR/manage-service.py" --install-path "$INSTALL_PATH" status --json 2>/dev/null || echo '{"running": false}')
        IS_RUNNING=$(echo "$STATUS_OUTPUT" | python3 -c "import sys, json; print(json.load(sys.stdin).get('running', False))" 2>/dev/null || echo "false")
        
        if [ "$IS_RUNNING" = "True" ]; then
            exit 0
        else
            exit 1
        fi
    fi
fi