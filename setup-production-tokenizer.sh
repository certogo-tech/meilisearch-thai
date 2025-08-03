#!/bin/bash

# Setup Production Tokenizer with Custom Dictionary
# This script ensures the custom dictionary is properly loaded and the tokenizer works correctly

set -e

echo "🔧 Setting up Production Tokenizer with Custom Dictionary"
echo "========================================================"

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

# Check if custom dictionary exists
print_info "Checking custom dictionary..."
if [ -f "data/dictionaries/thai_compounds.json" ]; then
    print_success "✅ Custom dictionary found"
    
    # Show some entries
    print_info "Dictionary contains:"
    grep -o '"[^"]*"' data/dictionaries/thai_compounds.json | head -10 | sed 's/"//g' | while read word; do
        echo "  - $word"
    done
    
    # Check if วากาเมะ is in the dictionary
    if grep -q "วากาเมะ" data/dictionaries/thai_compounds.json; then
        print_success "✅ 'วากาเมะ' found in dictionary"
    else
        print_warning "⚠️ 'วากาเมะ' not found in dictionary, adding it..."
        
        # Add วากาเมะ to the dictionary
        python3 -c "
import json
with open('data/dictionaries/thai_compounds.json', 'r', encoding='utf-8') as f:
    data = json.load(f)
if 'วากาเมะ' not in data.get('thai_japanese_compounds', []):
    data.setdefault('thai_japanese_compounds', []).append('วากาเมะ')
    with open('data/dictionaries/thai_compounds.json', 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print('Added วากาเมะ to dictionary')
"
    fi
else
    print_warning "⚠️ Custom dictionary not found, creating it..."
    
    # Create directory if it doesn't exist
    mkdir -p data/dictionaries
    
    # Create basic dictionary with วากาเมะ
    cat > data/dictionaries/thai_compounds.json << 'EOF'
{
  "thai_japanese_compounds": [
    "วากาเมะ",
    "สาหร่ายวากาเมะ",
    "ซาชิมิ",
    "เทมปุระ",
    "ซูชิ",
    "ราเมน",
    "อุด้ง",
    "โซบะ",
    "มิโซะ",
    "โชยุ",
    "วาซาบิ"
  ],
  "thai_english_compounds": [
    "คอมพิวเตอร์",
    "อินเทอร์เน็ต",
    "เว็บไซต์",
    "อีเมล",
    "โซเชียล"
  ]
}
EOF
    print_success "✅ Created custom dictionary with วากาเมะ"
fi

# Update .env.production to include custom dictionary path
print_info "Updating .env.production with custom dictionary path..."
if ! grep -q "CUSTOM_DICTIONARY_PATH" .env.production; then
    echo "" >> .env.production
    echo "# Custom dictionary configuration" >> .env.production
    echo "CUSTOM_DICTIONARY_PATH=data/dictionaries/thai_compounds.json" >> .env.production
    print_success "✅ Added CUSTOM_DICTIONARY_PATH to .env.production"
else
    print_info "CUSTOM_DICTIONARY_PATH already exists in .env.production"
fi

# Update Docker Compose to mount the dictionary
print_info "Updating Docker Compose to mount custom dictionary..."
if ! grep -q "data/dictionaries" deployment/docker/docker-compose.npm.yml; then
    # Add volume mount for dictionary
    sed -i '/volumes:/a\      - ./data/dictionaries:/app/data/dictionaries:ro' deployment/docker/docker-compose.npm.yml
    print_success "✅ Added dictionary volume mount to Docker Compose"
else
    print_info "Dictionary volume mount already exists"
fi

# Add environment variable for custom dictionary
if ! grep -q "CUSTOM_DICTIONARY_PATH" deployment/docker/docker-compose.npm.yml; then
    sed -i '/THAI_TOKENIZER_API_KEY=/a\      - CUSTOM_DICTIONARY_PATH=${CUSTOM_DICTIONARY_PATH:-}' deployment/docker/docker-compose.npm.yml
    print_success "✅ Added CUSTOM_DICTIONARY_PATH environment variable"
else
    print_info "CUSTOM_DICTIONARY_PATH environment variable already exists"
fi

# Detect docker compose command
if command -v "docker compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v "docker-compose" &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    print_error "Neither 'docker compose' nor 'docker-compose' command found!"
    exit 1
fi

print_info "Using Docker Compose command: $DOCKER_COMPOSE_CMD"

# Rebuild and restart the service
print_info "Rebuilding and restarting service with custom dictionary..."
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production down
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production build --no-cache thai-tokenizer
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d

# Wait for service to start
print_info "Waiting for service to start..."
sleep 20

# Test the tokenization - Both internal and external
print_info "Testing วากาเมะ tokenization..."

# First, test from inside the container (internal network)
CONTAINER_ID=$(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)
if [ -n "$CONTAINER_ID" ]; then
    print_info "=== INTERNAL TESTING (from inside container) ==="
    
    # Test basic tokenization from container
    print_info "Testing basic tokenization (internal)..."
    CONTAINER_BASIC=$(docker exec "$CONTAINER_ID" curl -s -X POST "http://localhost:8000/api/v1/tokenize" \
        -H "Content-Type: application/json" \
        -d '{"text": "ฉันกินสาหร่ายวากาเมะ"}' 2>/dev/null || echo "ERROR")
    
    if echo "$CONTAINER_BASIC" | grep -q '"tokens"'; then
        print_success "✅ Internal basic tokenization working"
        echo "$CONTAINER_BASIC"
    else
        print_error "❌ Internal basic tokenization failed"
        echo "$CONTAINER_BASIC"
    fi
    
    echo ""
    
    # Test compound tokenization from container
    print_info "Testing compound tokenization (internal)..."
    CONTAINER_COMPOUND=$(docker exec "$CONTAINER_ID" curl -s -X POST "http://localhost:8000/api/v1/tokenize/compound" \
        -H "Content-Type: application/json" \
        -d '{"text": "ฉันกินสาหร่ายวากาเมะ"}' 2>/dev/null || echo "ERROR")
    
    if echo "$CONTAINER_COMPOUND" | grep -q '"tokens"'; then
        print_success "✅ Internal compound tokenization working"
        echo "$CONTAINER_COMPOUND"
        
        if echo "$CONTAINER_COMPOUND" | grep -q '"วากาเมะ"'; then
            print_success "🎉 INTERNAL: วากาเมะ is tokenized as one word!"
        else
            print_warning "⚠️ INTERNAL: วากาเมะ is still being split"
            # Show the actual tokens
            TOKENS=$(echo "$CONTAINER_COMPOUND" | grep -o '"tokens":\[[^]]*\]')
            print_info "Actual tokens: $TOKENS"
        fi
    else
        print_error "❌ Internal compound tokenization failed"
        echo "$CONTAINER_COMPOUND"
    fi
else
    print_error "❌ No Thai Tokenizer container found for internal testing"
fi

echo ""
print_info "=== EXTERNAL TESTING (from outside server) ==="

# Test external access (for users outside the server)
print_info "Testing external access (https://search.cads.arda.or.th)..."

# Test basic tokenization externally
print_info "Testing basic tokenization (external)..."
EXTERNAL_BASIC=$(curl -s --connect-timeout 10 -X POST "https://search.cads.arda.or.th/api/v1/tokenize" \
    -H "Content-Type: application/json" \
    -d '{"text": "ฉันกินสาหร่ายวากาเมะ"}' 2>/dev/null || echo "ERROR")

if echo "$EXTERNAL_BASIC" | grep -q '"tokens"'; then
    print_success "✅ External basic tokenization working"
    echo "$EXTERNAL_BASIC"
elif echo "$EXTERNAL_BASIC" | grep -q "ERROR"; then
    print_warning "⚠️ External domain not accessible from this server (normal for internal server)"
    print_info "External users should still be able to access https://search.cads.arda.or.th"
else
    print_error "❌ External basic tokenization failed"
    echo "$EXTERNAL_BASIC"
fi

echo ""

# Test compound tokenization externally
print_info "Testing compound tokenization (external)..."
EXTERNAL_COMPOUND=$(curl -s --connect-timeout 10 -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
    -H "Content-Type: application/json" \
    -d '{"text": "ฉันกินสาหร่ายวากาเมะ"}' 2>/dev/null || echo "ERROR")

if echo "$EXTERNAL_COMPOUND" | grep -q '"tokens"'; then
    print_success "✅ External compound tokenization working"
    echo "$EXTERNAL_COMPOUND"
    
    if echo "$EXTERNAL_COMPOUND" | grep -q '"วากาเมะ"'; then
        print_success "🎉 EXTERNAL: วากาเมะ is tokenized as one word!"
    else
        print_warning "⚠️ EXTERNAL: วากาเมะ is still being split"
        # Show the actual tokens
        TOKENS=$(echo "$EXTERNAL_COMPOUND" | grep -o '"tokens":\[[^]]*\]')
        print_info "Actual tokens: $TOKENS"
    fi
elif echo "$EXTERNAL_COMPOUND" | grep -q "ERROR"; then
    print_warning "⚠️ External domain not accessible from this server (normal for internal server)"
    print_info "External users should test with: curl -X POST 'https://search.cads.arda.or.th/api/v1/tokenize/compound' -H 'Content-Type: application/json' -d '{\"text\": \"ฉันกินสาหร่ายวากาเมะ\"}'"
else
    print_error "❌ External compound tokenization failed"
    echo "$EXTERNAL_COMPOUND"
fi

echo ""
print_success "✅ Production tokenizer setup completed!"
print_info "Custom dictionary: data/dictionaries/thai_compounds.json"
print_info "Test command: ./test-wakame-tokenization.sh"
print_info "Service URL: https://search.cads.arda.or.th"

# Show final status
print_info "Final service status:"
$DOCKER_COMPOSE_CMD -f deployment/docker/docker-compose.npm.yml --env-file .env.production ps