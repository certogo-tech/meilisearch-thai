#!/bin/bash

echo "🔄 Restarting Thai Tokenizer service with updated configuration..."

# Stop the service
echo "Stopping service..."
docker-compose -f deployment/docker/docker-compose.npm.yml --env-file .env.production down

# Start the service
echo "Starting service with updated environment variables..."
docker-compose -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d

echo "✅ Service restarted!"
echo "Wait 10 seconds for startup, then test with:"
echo "curl -s 'https://search.cads.arda.or.th/api/v1/health/check/configuration_validity'"