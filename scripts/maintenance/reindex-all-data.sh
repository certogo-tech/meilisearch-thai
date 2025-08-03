#!/bin/bash

# Reindex All MeiliSearch Data with Thai Tokenization
# This script extracts existing documents and re-processes them with Thai tokenizer

echo "🔄 MeiliSearch Thai Tokenization Reindexing Tool"
echo "================================================="

# Colors for output
RED='\\033[0;31m'
GREEN='\\033[0;32m'
YELLOW='\\033[1;33m'
BLUE='\\033[0;34m'
NC='\\033[0m' # No Color

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Configuration
MEILISEARCH_HOST="http://10.0.2.105:7700"
MEILISEARCH_API_KEY="FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/reindex-existing-data.py"

# Check if Python script exists
if [ ! -f "$PYTHON_SCRIPT" ]; then
    print_error "Python reindexing script not found: $PYTHON_SCRIPT"
    exit 1
fi

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --index INDEX_NAME    Reindex specific index (e.g., research, faq)"
    echo "  --all                 Reindex all indexes"
    echo "  --dry-run            Show what would be done without making changes"
    echo "  --force              Force reindexing even if not needed"
    echo "  --no-backup          Skip creating backup indexes"
    echo "  --exclude INDEX      Exclude specific indexes (can be used multiple times)"
    echo "  --help               Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 --index research                    # Reindex only research index"
    echo "  $0 --all                              # Reindex all indexes"
    echo "  $0 --all --exclude documents          # Reindex all except documents"
    echo "  $0 --dry-run --all                    # Preview what would be done"
    echo "  $0 --force --index research           # Force reindex research"
}

# Function to check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."
    
    # Check Python
    if ! command -v python3 &> /dev/null; then
        print_error "Python 3 is required but not installed"
        return 1
    fi
    
    # Check MeiliSearch connectivity
    print_info "Testing MeiliSearch connectivity..."
    if ! curl -s -f "$MEILISEARCH_HOST/health" > /dev/null; then
        print_error "Cannot connect to MeiliSearch at $MEILISEARCH_HOST"
        print_info "Please ensure MeiliSearch is running and accessible"
        return 1
    fi
    
    # Check API key
    INDEX_TEST=$(curl -s -X GET "$MEILISEARCH_HOST/indexes" \\
        -H "Authorization: Bearer $MEILISEARCH_API_KEY")
    
    if echo "$INDEX_TEST" | grep -q "error"; then
        print_error "MeiliSearch API key authentication failed"
        print_info "Please check your API key: $MEILISEARCH_API_KEY"
        return 1
    fi
    
    print_success "Prerequisites check passed"
    return 0
}

# Function to show available indexes
show_available_indexes() {
    print_info "Available indexes:"
    curl -s -X GET "$MEILISEARCH_HOST/indexes" \\
        -H "Authorization: Bearer $MEILISEARCH_API_KEY" | \\
        python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    for idx in data.get('results', []):
        print(f'  - {idx[\"uid\"]} ({idx.get(\"numberOfDocuments\", 0)} documents)')
except:
    print('  (Unable to parse index list)')
"
}

# Function to estimate reindexing time
estimate_time() {
    local total_docs=0
    
    print_info "Estimating reindexing time..."
    
    # Get document counts
    INDEXES_INFO=$(curl -s -X GET "$MEILISEARCH_HOST/indexes" \\
        -H "Authorization: Bearer $MEILISEARCH_API_KEY")
    
    total_docs=$(echo "$INDEXES_INFO" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    total = sum(idx.get('numberOfDocuments', 0) for idx in data.get('results', []))
    print(total)
except:
    print(0)
")
    
    if [ "$total_docs" -gt 0 ]; then
        # Estimate: ~100ms per document processing + indexing time
        estimated_seconds=$((total_docs / 10))  # Conservative estimate
        estimated_minutes=$((estimated_seconds / 60))
        
        print_info "Estimated processing time:"
        echo "  • Total documents: $total_docs"
        echo "  • Estimated time: ~${estimated_minutes} minutes"
        echo "  • Processing rate: ~10 documents/second"
    fi
}

# Function to run reindexing with progress
run_reindexing() {
    local python_args=("$@")
    
    print_info "Starting reindexing process..."
    print_warning "This may take several minutes depending on data size"
    
    # Run the Python script
    cd "$SCRIPT_DIR/../.." || exit 1
    
    if python3 "$PYTHON_SCRIPT" "${python_args[@]}"; then
        print_success "Reindexing completed successfully!"
        
        print_info "Next steps:"
        echo "  1. Test search quality: ./scripts/testing/test-all-indexes.sh"
        echo "  2. Test compound words: ./scripts/testing/test-wakame-tokenization.sh"
        echo "  3. Update your frontend to use the new tokenized_content field"
        
        return 0
    else
        print_error "Reindexing failed - check logs for details"
        return 1
    fi
}

# Parse command line arguments
PYTHON_ARGS=()
DRY_RUN=false
SHOW_HELP=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --index)
            PYTHON_ARGS+=("--index" "$2")
            shift 2
            ;;
        --all)
            PYTHON_ARGS+=("--all-indexes")
            shift
            ;;
        --dry-run)
            PYTHON_ARGS+=("--dry-run")
            DRY_RUN=true
            shift
            ;;
        --force)
            PYTHON_ARGS+=("--force")
            shift
            ;;
        --no-backup)
            PYTHON_ARGS+=("--no-backup")
            shift
            ;;
        --exclude)
            PYTHON_ARGS+=("--exclude" "$2")
            shift 2
            ;;
        --help)
            SHOW_HELP=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Show help if requested
if [ "$SHOW_HELP" = true ]; then
    show_usage
    exit 0
fi

# Validate arguments
if [ ${#PYTHON_ARGS[@]} -eq 0 ]; then
    print_error "No operation specified"
    show_usage
    exit 1
fi

# Main execution
print_info "MeiliSearch Thai Tokenization Reindexing"
print_info "Host: $MEILISEARCH_HOST"
print_info "Mode: $([ "$DRY_RUN" = true ] && echo "DRY RUN" || echo "LIVE RUN")"
echo ""

# Check prerequisites
if ! check_prerequisites; then
    exit 1
fi

echo ""

# Show available indexes
show_available_indexes
echo ""

# Estimate time if not dry run
if [ "$DRY_RUN" = false ]; then
    estimate_time
    echo ""
    
    # Confirmation prompt for live run
    read -p "Do you want to proceed with reindexing? (y/N): " confirm
    if [[ ! $confirm =~ ^[Yy]$ ]]; then
        print_info "Reindexing cancelled by user"
        exit 0
    fi
    echo ""
fi

# Run reindexing
if run_reindexing "${PYTHON_ARGS[@]}"; then
    print_success "🎉 Reindexing process completed!"
    
    if [ "$DRY_RUN" = false ]; then
        print_info "Your indexes now have proper Thai tokenization for compound words!"
        print_info "Test with: วากาเมะ, รูเมน, ซูชิ, เทมปุระ"
    fi
else
    print_error "Reindexing failed"
    exit 1
fi