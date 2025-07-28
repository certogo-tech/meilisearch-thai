#!/bin/bash

# Thai Tokenizer - Local Production Setup Script
# This script automates the initial setup for local production deployment

set -e  # Exit on any error

echo "🚀 Thai Tokenizer - Local Production Setup"
echo "=========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed or not version 2.0+. Please install Docker Compose v2."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker."
        exit 1
    fi
    
    print_success "Prerequisites check passed"
}

# Generate secure API key
generate_api_key() {
    if command -v openssl &> /dev/null; then
        openssl rand -base64 32
    else
        # Fallback method
        date +%s | sha256sum | base64 | head -c 32
    fi
}

# Setup environment configuration
setup_environment() {
    print_status "Setting up production environment configuration..."
    
    # Create production environment file
    if [ ! -f "config/production/.env.prod" ]; then
        cp config/production/.env.template config/production/.env.prod
        
        # Generate secure API key
        API_KEY=$(generate_api_key)
        GRAFANA_PASSWORD=$(generate_api_key | head -c 16)
        
        # Update environment file with generated values
        sed -i.bak "s/\${MEILISEARCH_API_KEY}/$API_KEY/g" config/production/.env.prod
        sed -i.bak "s/your-secure-api-key-here/$API_KEY/g" config/production/.env.prod
        sed -i.bak "s/your-secure-grafana-password/$GRAFANA_PASSWORD/g" config/production/.env.prod
        
        # Remove backup file
        rm -f config/production/.env.prod.bak
        
        print_success "Environment configuration created"
        print_warning "Generated MeiliSearch API Key: $API_KEY"
        print_warning "Generated Grafana Password: $GRAFANA_PASSWORD"
        print_warning "Please save these credentials securely!"
    else
        print_warning "Environment file already exists, skipping..."
    fi
}

# Create required directories
setup_directories() {
    print_status "Creating required directories..."
    
    # Create log directories
    mkdir -p logs/thai-tokenizer
    mkdir -p logs/meilisearch  
    mkdir -p logs/nginx
    
    # Create SSL directory
    mkdir -p ssl
    
    # Set proper permissions
    chmod 755 logs/thai-tokenizer logs/meilisearch logs/nginx
    
    print_success "Directories created successfully"
}

# Build and start services
start_services() {
    print_status "Building and starting production services..."
    
    # Load environment variables safely
    if [ -f config/production/.env.prod ]; then
        print_status "Loading production environment variables..."
        set -a  # automatically export all variables
        source config/production/.env.prod
        set +a  # stop automatically exporting
        print_success "Environment variables loaded successfully"
    else
        print_error "Production environment file not found: config/production/.env.prod"
        exit 1
    fi
    
    # Build and start core services
    docker compose -f deployment/docker/docker-compose.prod.yml up -d thai-tokenizer meilisearch
    
    print_status "Waiting for services to be healthy..."
    
    # Wait for services to be healthy
    local max_attempts=30
    local attempt=1
    
    while [ $attempt -le $max_attempts ]; do
        if docker compose -f deployment/docker/docker-compose.prod.yml ps | grep -q "healthy"; then
            print_success "Services are healthy!"
            break
        fi
        
        if [ $attempt -eq $max_attempts ]; then
            print_error "Services failed to become healthy within timeout"
            docker compose -f deployment/docker/docker-compose.prod.yml logs
            exit 1
        fi
        
        print_status "Attempt $attempt/$max_attempts - waiting for services..."
        sleep 10
        ((attempt++))
    done
}

# Test the installation
test_installation() {
    print_status "Testing installation..."
    
    # Test Thai Tokenizer health
    if curl -f -s http://localhost:8000/health > /dev/null; then
        print_success "Thai Tokenizer is responding"
    else
        print_error "Thai Tokenizer health check failed"
        return 1
    fi
    
    # Test MeiliSearch health
    if curl -f -s http://localhost:7700/health > /dev/null; then
        print_success "MeiliSearch is responding"
    else
        print_error "MeiliSearch health check failed"
        return 1
    fi
    
    # Test tokenization
    print_status "Testing Thai tokenization..."
    local response=$(curl -s -X POST http://localhost:8000/api/v1/tokenize \
        -H "Content-Type: application/json" \
        -d '{"text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"}')
    
    if echo "$response" | grep -q "tokens"; then
        print_success "Thai tokenization is working"
        echo "Sample response: $response"
    else
        print_error "Thai tokenization test failed"
        echo "Response: $response"
        return 1
    fi
}

# Load sample data
load_sample_data() {
    print_status "Loading sample data..."
    
    if [ -f "deployment/scripts/setup_demo.py" ]; then
        docker compose -f deployment/docker/docker-compose.prod.yml exec -T thai-tokenizer python deployment/scripts/setup_demo.py
        print_success "Sample data loaded successfully"
    else
        print_warning "Demo setup script not found, skipping sample data loading"
    fi
}

# Display access information
show_access_info() {
    echo ""
    echo "🎉 Setup completed successfully!"
    echo "================================"
    echo ""
    echo "Service Access URLs:"
    echo "  • Thai Tokenizer API: http://localhost:8000"
    echo "  • API Documentation: http://localhost:8000/docs"
    echo "  • MeiliSearch: http://localhost:7700"
    echo ""
    echo "Useful Commands:"
    echo "  • View logs: docker compose -f deployment/docker/docker-compose.prod.yml logs -f"
    echo "  • Stop services: docker compose -f deployment/docker/docker-compose.prod.yml down"
    echo "  • Restart services: docker compose -f deployment/docker/docker-compose.prod.yml restart"
    echo ""
    echo "Configuration Files:"
    echo "  • Environment: config/production/.env.prod"
    echo "  • Logs: logs/ directory"
    echo ""
    echo "Next Steps:"
    echo "  1. Test the API at http://localhost:8000/docs"
    echo "  2. Review the production setup guide: PRODUCTION_SETUP_GUIDE.md"
    echo "  3. Configure monitoring (optional): docker compose --profile monitoring up -d"
    echo ""
}

# Main execution
main() {
    echo "Starting setup process..."
    echo ""
    
    check_prerequisites
    setup_environment
    setup_directories
    start_services
    
    # Wait a bit for services to fully start
    sleep 5
    
    test_installation
    load_sample_data
    show_access_info
}

# Handle script interruption
trap 'print_error "Setup interrupted"; exit 1' INT TERM

# Run main function
main "$@"