#!/bin/bash

# Cleanup script for test environment

echo "🧹 Cleaning up test environment..."

# Stop and remove Thai Tokenizer
echo "Stopping Thai Tokenizer..."
cd deployment/docker
docker compose -f docker-compose.tokenizer-only.yml down --remove-orphans || true
cd ../..

# Stop and remove test MeiliSearch
echo "Stopping test MeiliSearch..."
docker stop test-meilisearch || true
docker rm test-meilisearch || true

# Remove test environment file
echo "Removing test files..."
rm -f .env.existing
rm -f .env.existing.test

echo "✅ Cleanup completed!"