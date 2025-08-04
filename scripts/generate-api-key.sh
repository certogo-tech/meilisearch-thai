#!/bin/bash

# Thai Search Proxy API Key Generator
# Generates secure API keys for authentication

echo "Thai Search Proxy API Key Generator"
echo "==================================="
echo ""

# Generate a secure API key
API_KEY=$(openssl rand -hex 32)

echo "Generated API Key:"
echo "$API_KEY"
echo ""

echo "To use this API key:"
echo ""
echo "1. Update your .env file:"
echo "   SEARCH_PROXY_API_KEY=$API_KEY"
echo ""
echo "2. Restart the service:"
echo "   docker-compose restart thai-search-proxy"
echo ""
echo "3. Use in API requests:"
echo "   curl -H \"X-API-Key: $API_KEY\" https://search.cads.arda.or.th/api/v1/search"
echo ""
echo "Security Tips:"
echo "- Store this key securely (e.g., in a password manager)"
echo "- Never commit API keys to version control"
echo "- Rotate keys regularly (e.g., every 90 days)"
echo "- Use different keys for different environments"
echo ""

# Optional: Save to a secure file
read -p "Save to secure file? (y/n): " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    TIMESTAMP=$(date +%Y%m%d_%H%M%S)
    FILENAME="api_key_${TIMESTAMP}.txt"
    
    echo "API Key generated on $(date)" > "$FILENAME"
    echo "Environment: Production" >> "$FILENAME"
    echo "Service: Thai Search Proxy" >> "$FILENAME"
    echo "----------------------------------------" >> "$FILENAME"
    echo "API_KEY=$API_KEY" >> "$FILENAME"
    echo "----------------------------------------" >> "$FILENAME"
    echo "Usage: SEARCH_PROXY_API_KEY=$API_KEY" >> "$FILENAME"
    
    # Secure the file
    chmod 600 "$FILENAME"
    
    echo "API key saved to: $FILENAME"
    echo "File permissions set to 600 (owner read/write only)"
fi