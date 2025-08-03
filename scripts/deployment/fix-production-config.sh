#!/bin/bash

# Fix Production Configuration Script
# This script updates the Meilisearch host to use the correct IP address

set -e

echo "🔧 Fixing Production Configuration"
echo "=================================="

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

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    print_error ".env.production file not found!"
    exit 1
fi

print_info "Found .env.production file"

# Create backup
BACKUP_FILE=".env.production.backup.$(date +%Y%m%d_%H%M%S)"
cp .env.production "$BACKUP_FILE"
print_success "Created backup: $BACKUP_FILE"

# Show current Meilisearch host
CURRENT_HOST=$(grep "^MEILISEARCH_HOST=" .env.production | cut -d'=' -f2)
print_info "Current Meilisearch host: $CURRENT_HOST"

# Update the Meilisearch host to use the correct IP
print_info "Updating Meilisearch host to use IP address 10.0.2.105:7700..."

# Use sed to replace the Meilisearch host
sed -i.bak 's|^MEILISEARCH_HOST=.*|MEILISEARCH_HOST=http://10.0.2.105:7700|' .env.production

# Verify the change
NEW_HOST=$(grep "^MEILISEARCH_HOST=" .env.production | cut -d'=' -f2)
print_success "Updated Meilisearch host to: $NEW_HOST"

# Test connectivity to the new host
print_info "Testing connectivity to $NEW_HOST..."
if curl -s --connect-timeout 5 "$NEW_HOST/health" > /dev/null; then
    MEILISEARCH_STATUS=$(curl -s "$NEW_HOST/health" | grep -o '"status":"[^"]*"' | cut -d'"' -f4)
    print_success "Meilisearch is accessible - Status: $MEILISEARCH_STATUS"
else
    print_error "Cannot connect to Meilisearch at $NEW_HOST"
    print_error "Restoring backup..."
    cp "$BACKUP_FILE" .env.production
    exit 1
fi

print_success "✅ Configuration updated successfully!"
print_info "Backup saved as: $BACKUP_FILE"
print_info "Next steps:"
echo "1. Restart the service: ./restart-service.sh"
echo "2. Or redeploy: ./deploy-production.sh"
echo "3. Test health: curl -s 'https://search.cads.arda.or.th/api/v1/health/check/configuration_validity'"