#!/bin/bash

# Thai Search Proxy Deployment Script for NPM
# This script helps deploy the search proxy with Nginx Proxy Manager

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
COMPOSE_FILE="docker-compose.npm-search-proxy.yml"
ENV_FILE=".env"
ENV_TEMPLATE=".env.npm-search-proxy"

echo -e "${GREEN}Thai Search Proxy NPM Deployment Script${NC}"
echo "========================================"

# Function to check prerequisites
check_prerequisites() {
    echo -e "\n${YELLOW}Checking prerequisites...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed${NC}"
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed${NC}"
        exit 1
    fi
    
    # Check if we're in the correct directory
    if [ ! -f "$COMPOSE_FILE" ]; then
        echo -e "${RED}Error: $COMPOSE_FILE not found. Please run from deployment/docker directory${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}Prerequisites checked successfully${NC}"
}

# Function to setup environment
setup_environment() {
    echo -e "\n${YELLOW}Setting up environment...${NC}"
    
    if [ ! -f "$ENV_FILE" ]; then
        if [ -f "$ENV_TEMPLATE" ]; then
            cp "$ENV_TEMPLATE" "$ENV_FILE"
            echo -e "${GREEN}Created $ENV_FILE from template${NC}"
            echo -e "${YELLOW}Please edit $ENV_FILE to configure your deployment${NC}"
            echo "Important settings to configure:"
            echo "  - MEILISEARCH_HOST"
            echo "  - MEILISEARCH_API_KEY"
            echo "  - THAI_TOKENIZER_PORT (if not using 8000)"
            read -p "Press Enter after configuring $ENV_FILE..."
        else
            echo -e "${RED}Error: No environment file found${NC}"
            exit 1
        fi
    else
        echo -e "${GREEN}Using existing $ENV_FILE${NC}"
    fi
}

# Function to deploy service
deploy_service() {
    echo -e "\n${YELLOW}Deploying Thai Search Proxy...${NC}"
    
    # Pull latest images
    echo "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull
    
    # Build the service
    echo "Building service..."
    docker-compose -f "$COMPOSE_FILE" build
    
    # Start the service
    echo "Starting service..."
    docker-compose -f "$COMPOSE_FILE" up -d
    
    echo -e "${GREEN}Service deployed successfully${NC}"
}

# Function to check health
check_health() {
    echo -e "\n${YELLOW}Checking service health...${NC}"
    
    # Wait for service to start
    echo "Waiting for service to initialize..."
    sleep 10
    
    # Get the port from env file
    PORT=$(grep -E "^THAI_TOKENIZER_PORT=" "$ENV_FILE" | cut -d'=' -f2 || echo "8000")
    
    # Check health endpoint
    if curl -f -s "http://localhost:${PORT}/health" > /dev/null; then
        echo -e "${GREEN}Health check passed${NC}"
        
        # Show detailed health
        echo -e "\nDetailed health status:"
        curl -s "http://localhost:${PORT}/api/v1/health" | python3 -m json.tool 2>/dev/null || \
        curl -s "http://localhost:${PORT}/api/v1/health"
    else
        echo -e "${RED}Health check failed${NC}"
        echo "Checking logs..."
        docker-compose -f "$COMPOSE_FILE" logs --tail=50
    fi
}

# Function to show NPM configuration
show_npm_config() {
    echo -e "\n${YELLOW}Nginx Proxy Manager Configuration${NC}"
    echo "=================================="
    echo "Add the following proxy host in NPM:"
    echo ""
    echo "Domain Names: search.cads.arda.or.th (or your domain)"
    echo "Scheme: http"
    echo "Forward Hostname/IP: localhost"
    echo "Forward Port: ${PORT:-8000}"
    echo ""
    echo "Recommended settings:"
    echo "- Enable 'Block Common Exploits'"
    echo "- Enable 'Websockets Support'"
    echo "- Request Let's Encrypt SSL certificate"
    echo "- Enable Force SSL"
    echo "- Enable HTTP/2 Support"
    echo ""
    echo "Custom Nginx Configuration (optional):"
    echo "proxy_connect_timeout 60s;"
    echo "proxy_read_timeout 60s;"
    echo "proxy_buffer_size 16k;"
}

# Function to show useful commands
show_commands() {
    echo -e "\n${YELLOW}Useful Commands${NC}"
    echo "==============="
    echo "View logs:        docker-compose -f $COMPOSE_FILE logs -f"
    echo "Stop service:     docker-compose -f $COMPOSE_FILE down"
    echo "Restart service:  docker-compose -f $COMPOSE_FILE restart"
    echo "View metrics:     curl http://localhost:${PORT:-8000}/metrics/search-proxy"
    echo "Test search:      curl -X POST http://localhost:${PORT:-8000}/api/v1/search -H 'Content-Type: application/json' -d '{\"query\":\"ทดสอบ\",\"index_name\":\"documents\"}'"
}

# Main deployment flow
main() {
    check_prerequisites
    setup_environment
    
    # Ask for deployment confirmation
    echo -e "\n${YELLOW}Ready to deploy Thai Search Proxy${NC}"
    read -p "Continue with deployment? (y/n) " -n 1 -r
    echo
    
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        deploy_service
        check_health
        show_npm_config
        show_commands
        
        echo -e "\n${GREEN}Deployment completed!${NC}"
        echo "Next steps:"
        echo "1. Configure proxy host in Nginx Proxy Manager"
        echo "2. Test the service through your domain"
        echo "3. Monitor logs and metrics"
    else
        echo -e "${YELLOW}Deployment cancelled${NC}"
    fi
}

# Run main function
main