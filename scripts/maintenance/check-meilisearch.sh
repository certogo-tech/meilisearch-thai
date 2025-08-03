#!/bin/bash

# Script to check your existing Meilisearch setup
echo "🔍 Checking your existing Meilisearch setup..."
echo "=============================================="

# Check for running Meilisearch containers
echo "1. Looking for Meilisearch containers:"
docker ps --filter "name=meilisearch" --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"
docker ps --filter "ancestor=getmeili/meilisearch" --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}"

echo ""
echo "2. Checking Docker networks:"
docker network ls | grep -E "(meilisearch|meili)"

echo ""
echo "3. All running containers (to identify Meilisearch):"
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Ports}}"

echo ""
echo "4. If you found your Meilisearch container, test connectivity:"
echo "   Replace 'your-container-name' with actual container name:"
echo "   docker exec your-container-name curl http://localhost:7700/health"

echo ""
echo "5. To check which network your Meilisearch is on:"
echo "   docker inspect your-container-name | grep NetworkMode"
echo "   docker inspect your-container-name | grep -A 10 Networks"