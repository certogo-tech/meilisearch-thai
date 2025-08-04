#!/bin/bash

# Thai Search Proxy Production Setup Script
# This script helps set up the Thai Search Proxy for production with NPM

set -e

echo "==================================="
echo "Thai Search Proxy Production Setup"
echo "==================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [[ $EUID -eq 0 ]]; then
   echo -e "${RED}This script should not be run as root!${NC}"
   exit 1
fi

# Check prerequisites
echo -e "\n${YELLOW}Checking prerequisites...${NC}"

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check Docker Compose
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${GREEN}Prerequisites check passed!${NC}"

# Navigate to deployment directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR/../docker"

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "\n${YELLOW}Creating .env file from template...${NC}"
    cp .env.example .env
    echo -e "${GREEN}.env file created!${NC}"
    echo -e "${YELLOW}Please edit .env file with your production values:${NC}"
    echo "  - MEILISEARCH_HOST"
    echo "  - MEILISEARCH_API_KEY"
    echo "  - THAI_TOKENIZER_API_KEY (if API_KEY_REQUIRED=true)"
    echo ""
    read -p "Press Enter after editing .env file..."
fi

# Generate API key if needed
echo -e "\n${YELLOW}Do you want to generate a secure API key? (y/n)${NC}"
read -r generate_key
if [[ $generate_key == "y" || $generate_key == "Y" ]]; then
    API_KEY=$(openssl rand -base64 32)
    echo -e "${GREEN}Generated API Key: ${API_KEY}${NC}"
    echo -e "${YELLOW}Add this to your .env file as THAI_TOKENIZER_API_KEY${NC}"
    read -p "Press Enter to continue..."
fi

# Check MeiliSearch connectivity
echo -e "\n${YELLOW}Checking MeiliSearch connectivity...${NC}"
source .env
if [ -z "$MEILISEARCH_HOST" ]; then
    echo -e "${RED}MEILISEARCH_HOST not set in .env file${NC}"
    exit 1
fi

# Test MeiliSearch connection
if curl -f -s "${MEILISEARCH_HOST}/health" > /dev/null; then
    echo -e "${GREEN}MeiliSearch is accessible!${NC}"
else
    echo -e "${RED}Cannot connect to MeiliSearch at ${MEILISEARCH_HOST}${NC}"
    echo "Please check your MEILISEARCH_HOST setting"
    exit 1
fi

# Pull latest images
echo -e "\n${YELLOW}Building Docker image...${NC}"
docker-compose -f docker-compose.npm-search-proxy.yml build

# Start services
echo -e "\n${YELLOW}Starting Thai Search Proxy service...${NC}"
docker-compose -f docker-compose.npm-search-proxy.yml up -d

# Wait for service to be ready
echo -e "\n${YELLOW}Waiting for service to be ready...${NC}"
sleep 10

# Check health
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo -e "${GREEN}Service is healthy!${NC}"
else
    echo -e "${RED}Service health check failed${NC}"
    echo "Checking logs..."
    docker-compose -f docker-compose.npm-search-proxy.yml logs --tail=50
    exit 1
fi

# Display NPM configuration instructions
echo -e "\n${GREEN}==================================="
echo "Service is running successfully!"
echo "===================================${NC}"
echo ""
echo "Next steps for Nginx Proxy Manager:"
echo ""
echo "1. Login to NPM admin panel"
echo "2. Add new Proxy Host:"
echo "   - Domain: search.cads.arda.or.th (or your domain)"
echo "   - Forward Host: localhost"
echo "   - Forward Port: 8000"
echo "   - Enable SSL with Let's Encrypt"
echo ""
echo "3. Test the setup:"
echo "   curl https://search.cads.arda.or.th/health"
echo ""
echo "Service endpoints:"
echo "  - Health: http://localhost:8000/health"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - Metrics: http://localhost:8000/metrics"
echo ""

# Optional monitoring setup
echo -e "${YELLOW}Do you want to enable Prometheus monitoring? (y/n)${NC}"
read -r enable_monitoring
if [[ $enable_monitoring == "y" || $enable_monitoring == "Y" ]]; then
    echo "COMPOSE_PROFILES=monitoring" >> .env
    docker-compose -f docker-compose.npm-search-proxy.yml up -d
    echo -e "${GREEN}Prometheus monitoring enabled at http://localhost:9090${NC}"
fi

echo -e "\n${GREEN}Setup complete!${NC}"