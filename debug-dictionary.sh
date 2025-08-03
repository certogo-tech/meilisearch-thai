#!/bin/bash

# Debug Custom Dictionary Loading
# This script checks if the custom dictionary is being loaded correctly

echo "🔍 Debugging Custom Dictionary Loading"
echo "====================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
print_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
print_warning() { echo -e "${YELLOW}[WARNING]${NC} $1"; }
print_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if dictionary file exists
print_info "Checking dictionary file..."
if [ -f "data/dictionaries/thai_compounds.json" ]; then
    print_success "✅ Dictionary file exists"
    
    # Show dictionary content
    print_info "Dictionary content:"
    cat data/dictionaries/thai_compounds.json | jq . 2>/dev/null || cat data/dictionaries/thai_compounds.json
    
    # Check if วากาเมะ is in the file
    if grep -q "วากาเมะ" data/dictionaries/thai_compounds.json; then
        print_success "✅ 'วากาเมะ' found in dictionary file"
    else
        print_error "❌ 'วากาเมะ' not found in dictionary file"
    fi
else
    print_error "❌ Dictionary file not found"
fi

echo ""

# Check environment variables
print_info "Checking environment variables..."
source .env.production
print_info "CUSTOM_DICTIONARY_PATH: ${CUSTOM_DICTIONARY_PATH:-'not set'}"

echo ""

# Check if container can see the dictionary file
CONTAINER_ID=$(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)
if [ -n "$CONTAINER_ID" ]; then
    print_info "Checking dictionary file inside container..."
    
    # Check if file exists in container
    if docker exec "$CONTAINER_ID" test -f "/app/data/dictionaries/thai_compounds.json"; then
        print_success "✅ Dictionary file exists in container"
        
        # Show file content in container
        print_info "Dictionary content in container:"
        docker exec "$CONTAINER_ID" cat "/app/data/dictionaries/thai_compounds.json" 2>/dev/null || print_error "Could not read file"
    else
        print_error "❌ Dictionary file not found in container"
        print_info "Container file system:"
        docker exec "$CONTAINER_ID" ls -la /app/data/ 2>/dev/null || print_error "Could not list directory"
    fi
    
    echo ""
    
    # Check environment variables in container
    print_info "Checking environment variables in container..."
    docker exec "$CONTAINER_ID" env | grep -i dictionary || print_warning "No dictionary-related environment variables found"
    
    echo ""
    
    # Check container logs for dictionary loading
    print_info "Checking container logs for dictionary loading..."
    docker logs "$CONTAINER_ID" 2>&1 | grep -i dictionary || print_warning "No dictionary-related log messages found"
    
    echo ""
    
    # Test configuration endpoint
    print_info "Testing configuration endpoint..."
    CONFIG_RESPONSE=$(docker exec "$CONTAINER_ID" curl -s "http://localhost:8000/api/v1/config" 2>/dev/null || echo "ERROR")
    
    if echo "$CONFIG_RESPONSE" | grep -q "custom_dictionary"; then
        print_success "✅ Configuration endpoint accessible"
        
        # Extract custom dictionary info
        DICT_SIZE=$(echo "$CONFIG_RESPONSE" | grep -o '"custom_dictionary_size":[0-9]*' | cut -d':' -f2)
        print_info "Custom dictionary size: ${DICT_SIZE:-'unknown'}"
        
        if [ "$DICT_SIZE" -gt 0 ] 2>/dev/null; then
            print_success "✅ Custom dictionary is loaded with $DICT_SIZE words"
        else
            print_warning "⚠️ Custom dictionary appears to be empty"
        fi
    else
        print_error "❌ Could not access configuration endpoint"
        echo "$CONFIG_RESPONSE"
    fi
else
    print_error "❌ No Thai Tokenizer container found"
fi

echo ""
print_info "Debug completed!"
print_info "If dictionary is not loading, try rebuilding with: ./fix-and-restart.sh"