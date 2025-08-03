#!/bin/bash

# Organize Root Folder Script
# This script cleans and organizes the root directory files into proper folders

echo "🧹 Organizing Root Folder Files"
echo "==============================="

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

# Create organization directories
print_info "Creating organization directories..."

# Scripts directory for deployment and maintenance scripts
mkdir -p scripts/deployment
mkdir -p scripts/testing
mkdir -p scripts/maintenance
mkdir -p scripts/development

# Documentation directory
mkdir -p docs/production
mkdir -p docs/deployment

# Backup directory for environment files
mkdir -p backups/env

print_success "✅ Directories created"

# Move deployment scripts
print_info "Moving deployment scripts..."
mv deploy-production.sh scripts/deployment/ 2>/dev/null || true
mv setup-production-tokenizer.sh scripts/deployment/ 2>/dev/null || true
mv final-wakame-fix.sh scripts/deployment/ 2>/dev/null || true
mv fix-and-restart.sh scripts/deployment/ 2>/dev/null || true
mv rebuild-and-restart.sh scripts/deployment/ 2>/dev/null || true
mv rebuild-compound-fix.sh scripts/deployment/ 2>/dev/null || true
mv rebuild-with-dictionary.sh scripts/deployment/ 2>/dev/null || true
mv simple-rebuild.sh scripts/deployment/ 2>/dev/null || true
mv restart-service.sh scripts/deployment/ 2>/dev/null || true
mv setup-ssl.sh scripts/deployment/ 2>/dev/null || true
mv update-meilisearch-config.sh scripts/deployment/ 2>/dev/null || true
mv fix-production-config.sh scripts/deployment/ 2>/dev/null || true

print_success "✅ Deployment scripts moved to scripts/deployment/"

# Move testing scripts
print_info "Moving testing scripts..."
mv test-external-api.sh scripts/testing/ 2>/dev/null || true
mv test-from-container.sh scripts/testing/ 2>/dev/null || true
mv test-service-health.sh scripts/testing/ 2>/dev/null || true
mv test-wakame-tokenization.sh scripts/testing/ 2>/dev/null || true

print_success "✅ Testing scripts moved to scripts/testing/"

# Move maintenance scripts
print_info "Moving maintenance scripts..."
mv debug-dictionary.sh scripts/maintenance/ 2>/dev/null || true
mv validate-env-config.sh scripts/maintenance/ 2>/dev/null || true
mv check-meilisearch.sh scripts/maintenance/ 2>/dev/null || true

print_success "✅ Maintenance scripts moved to scripts/maintenance/"

# Move documentation files
print_info "Moving documentation files..."
mv PRODUCTION_CONTAINER_SETUP.md docs/production/ 2>/dev/null || true
mv PRODUCTION_DEPLOYMENT_TEST_RESULTS.md docs/production/ 2>/dev/null || true
mv PRODUCTION_DOMAIN_SETUP.md docs/production/ 2>/dev/null || true
mv PRODUCTION_FIX_COMMANDS.md docs/production/ 2>/dev/null || true
mv SECURITY_IMPLEMENTATION_SUMMARY.md docs/production/ 2>/dev/null || true

print_success "✅ Documentation moved to docs/production/"

# Move environment backup files
print_info "Moving environment backup files..."
mv .env.production.backup.* backups/env/ 2>/dev/null || true

print_success "✅ Environment backups moved to backups/env/"

# Create a main deployment script in root
print_info "Creating main deployment script..."
cat > deploy.sh << 'EOF'
#!/bin/bash

# Main Deployment Script
# This is the primary script for deploying the Thai Tokenizer service

echo "🚀 Thai Tokenizer Deployment"
echo "============================"

# Show available deployment options
echo "Available deployment scripts:"
echo "1. scripts/deployment/deploy-production.sh - Full production deployment"
echo "2. scripts/deployment/setup-production-tokenizer.sh - Setup with custom dictionary"
echo "3. scripts/deployment/simple-rebuild.sh - Simple rebuild and restart"
echo "4. scripts/deployment/final-wakame-fix.sh - Apply wakame tokenization fix"
echo ""
echo "Available testing scripts:"
echo "1. scripts/testing/test-external-api.sh - Test from external server"
echo "2. scripts/testing/test-wakame-tokenization.sh - Test wakame tokenization"
echo "3. scripts/testing/test-service-health.sh - Test service health"
echo ""
echo "Available maintenance scripts:"
echo "1. scripts/maintenance/debug-dictionary.sh - Debug custom dictionary"
echo "2. scripts/maintenance/validate-env-config.sh - Validate configuration"
echo ""

# Check if user wants to run a specific script
if [ $# -eq 0 ]; then
    echo "Usage: $0 [script-name]"
    echo "Example: $0 production  # Runs full production deployment"
    echo "Example: $0 test        # Runs external API test"
    echo "Example: $0 health      # Runs health check"
    exit 0
fi

case "$1" in
    "production"|"prod")
        echo "Running production deployment..."
        ./scripts/deployment/deploy-production.sh
        ;;
    "setup")
        echo "Running production setup with custom dictionary..."
        ./scripts/deployment/setup-production-tokenizer.sh
        ;;
    "rebuild")
        echo "Running simple rebuild..."
        ./scripts/deployment/simple-rebuild.sh
        ;;
    "test")
        echo "Running external API test..."
        ./scripts/testing/test-external-api.sh
        ;;
    "wakame")
        echo "Testing wakame tokenization..."
        ./scripts/testing/test-wakame-tokenization.sh
        ;;
    "health")
        echo "Testing service health..."
        ./scripts/testing/test-service-health.sh
        ;;
    "debug")
        echo "Running debug tools..."
        ./scripts/maintenance/debug-dictionary.sh
        ;;
    "validate")
        echo "Validating configuration..."
        ./scripts/maintenance/validate-env-config.sh
        ;;
    *)
        echo "Unknown option: $1"
        echo "Run '$0' without arguments to see available options"
        exit 1
        ;;
esac
EOF

chmod +x deploy.sh
print_success "✅ Main deployment script created: deploy.sh"

# Create a README for the scripts directory
print_info "Creating scripts README..."
cat > scripts/README.md << 'EOF'
# Scripts Directory

This directory contains all the operational scripts for the Thai Tokenizer service.

## Directory Structure

### `deployment/`
Scripts for deploying and managing the production service:
- `deploy-production.sh` - Full production deployment with health checks
- `setup-production-tokenizer.sh` - Setup service with custom dictionary
- `final-wakame-fix.sh` - Apply the wakame tokenization fix
- `simple-rebuild.sh` - Simple rebuild and restart
- `rebuild-*.sh` - Various rebuild scripts for specific fixes
- `setup-ssl.sh` - SSL certificate setup
- `restart-service.sh` - Restart the service

### `testing/`
Scripts for testing the service functionality:
- `test-external-api.sh` - Comprehensive external API testing
- `test-wakame-tokenization.sh` - Test wakame tokenization specifically
- `test-service-health.sh` - Test service health and status
- `test-from-container.sh` - Test from inside Docker container

### `maintenance/`
Scripts for maintenance and debugging:
- `debug-dictionary.sh` - Debug custom dictionary loading
- `validate-env-config.sh` - Validate environment configuration
- `check-meilisearch.sh` - Check Meilisearch connectivity

## Usage

### Quick Deployment
```bash
# From project root
./deploy.sh production
```

### Quick Testing
```bash
# From project root
./deploy.sh test
```

### Direct Script Usage
```bash
# Run specific deployment script
./scripts/deployment/deploy-production.sh

# Run specific test
./scripts/testing/test-external-api.sh

# Run maintenance task
./scripts/maintenance/debug-dictionary.sh
```

## Script Dependencies

Most scripts require:
- Docker and Docker Compose
- curl for API testing
- Access to `.env.production` file
- Proper network connectivity to the service

## Environment

Scripts are designed to work with:
- Production environment at `https://search.cads.arda.or.th`
- Meilisearch at `http://10.0.2.105:7700`
- Docker containers for the Thai Tokenizer service
EOF

print_success "✅ Scripts README created"

# Update .gitignore to ignore backup files in their new location
print_info "Updating .gitignore..."
if ! grep -q "backups/env/" .gitignore; then
    echo "" >> .gitignore
    echo "# Environment backups" >> .gitignore
    echo "backups/env/.env.production.backup.*" >> .gitignore
fi

print_success "✅ .gitignore updated"

# Create a summary of the organization
print_info "Creating organization summary..."
cat > ORGANIZATION_SUMMARY.md << 'EOF'
# Root Folder Organization Summary

This document describes the organization of the Thai Tokenizer project root folder.

## Directory Structure

```
thai-tokenizer/
├── src/                          # Source code
├── tests/                        # Test files
├── deployment/                   # Docker and deployment configs
├── docs/                         # Documentation
│   └── production/              # Production-specific docs
├── scripts/                      # Operational scripts
│   ├── deployment/              # Deployment scripts
│   ├── testing/                 # Testing scripts
│   └── maintenance/             # Maintenance scripts
├── data/                         # Data files (dictionaries, etc.)
├── backups/                      # Backup files
│   └── env/                     # Environment file backups
├── config/                       # Configuration files
├── logs/                         # Log files
└── ssl/                          # SSL certificates
```

## Key Files in Root

### Essential Files
- `README.md` - Main project documentation
- `pyproject.toml` - Python project configuration
- `requirements.txt` - Python dependencies
- `.env.production` - Production environment configuration
- `.gitignore` - Git ignore patterns
- `Makefile` - Build and development commands

### Main Scripts
- `deploy.sh` - Main deployment script (entry point)

### Development Files
- `.dockerignore` - Docker ignore patterns
- `QUICK_START.md` - Quick start guide

## Usage

### Deploy to Production
```bash
./deploy.sh production
```

### Test the Service
```bash
./deploy.sh test
```

### Debug Issues
```bash
./deploy.sh debug
```

### Validate Configuration
```bash
./deploy.sh validate
```

## Backup Policy

- Environment file backups are stored in `backups/env/`
- Backups are automatically created before configuration changes
- Backup files follow the pattern: `.env.production.backup.YYYYMMDD_HHMMSS`

## Script Organization

All operational scripts have been moved to the `scripts/` directory:
- **Deployment scripts**: For deploying and managing the service
- **Testing scripts**: For testing functionality and health
- **Maintenance scripts**: For debugging and maintenance tasks

This organization makes it easier to:
1. Find the right script for the task
2. Maintain and update scripts
3. Understand the project structure
4. Onboard new team members
EOF

print_success "✅ Organization summary created"

# Show final directory structure
print_info "Final root directory structure:"
ls -la | grep -E "^d|^-" | head -20

echo ""
print_success "🎉 Root folder organization completed!"
echo ""
print_info "Summary of changes:"
echo "✅ Moved deployment scripts to scripts/deployment/"
echo "✅ Moved testing scripts to scripts/testing/"
echo "✅ Moved maintenance scripts to scripts/maintenance/"
echo "✅ Moved documentation to docs/production/"
echo "✅ Moved environment backups to backups/env/"
echo "✅ Created main deploy.sh script"
echo "✅ Created scripts/README.md"
echo "✅ Created ORGANIZATION_SUMMARY.md"
echo "✅ Updated .gitignore"
echo ""
print_info "Usage:"
echo "• Deploy to production: ./deploy.sh production"
echo "• Test the service: ./deploy.sh test"
echo "• Debug issues: ./deploy.sh debug"
echo "• See all options: ./deploy.sh"