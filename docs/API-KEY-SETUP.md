# Thai Search Proxy API Key Setup Guide

This guide explains how to set up and use API key authentication for the Thai Search Proxy service.

## Overview

API key authentication provides a simple yet effective way to secure your Thai Search Proxy endpoints. When enabled, all API requests must include a valid API key.

## Quick Start

### 1. Generate an API Key

```bash
# Using the provided script
./scripts/generate-api-key.sh

# Or manually with OpenSSL
openssl rand -hex 32
```

Example output:
```
a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd
```

### 2. Configure the Service

Update your `.env` file:

```env
# Enable API key authentication
API_KEY_REQUIRED=true

# Set your generated API key
SEARCH_PROXY_API_KEY=a1b2c3d4e5f6789012345678901234567890123456789012345678901234abcd
```

### 3. Restart the Service

```bash
# Docker Compose
docker-compose restart thai-search-proxy

# Or full restart
docker-compose down
docker-compose up -d
```

### 4. Test Authentication

```bash
# Test without API key (should fail)
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "index_name": "research"}'

# Response: 401 Unauthorized

# Test with API key (should succeed)
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{"query": "test", "index_name": "research"}'
```

## Authentication Methods

The service supports two methods for providing the API key:

### Method 1: X-API-Key Header (Recommended)

```bash
curl -H "X-API-Key: your-api-key-here" https://search.cads.arda.or.th/api/v1/search
```

### Method 2: Authorization Bearer Token

```bash
curl -H "Authorization: Bearer your-api-key-here" https://search.cads.arda.or.th/api/v1/search
```

## Integration Examples

### JavaScript/Axios

```javascript
const apiClient = axios.create({
  baseURL: 'https://search.cads.arda.or.th',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.SEARCH_API_KEY
  }
});

// Use the client
const response = await apiClient.post('/api/v1/search', {
  query: 'สาหร่าย',
  index_name: 'research'
});
```

### Python/Requests

```python
import requests
import os

API_KEY = os.getenv('SEARCH_API_KEY')
headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
}

response = requests.post(
    'https://search.cads.arda.or.th/api/v1/search',
    json={'query': 'สาหร่าย', 'index_name': 'research'},
    headers=headers
)
```

### NextJS Integration

```typescript
// lib/searchClient.ts
import axios from 'axios';

const searchClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_SEARCH_API_URL || 'https://search.cads.arda.or.th',
  headers: {
    'Content-Type': 'application/json',
    'X-API-Key': process.env.SEARCH_API_KEY || ''
  },
  timeout: 10000
});

export const searchAPI = {
  async search(query: string, indexName: string = 'research', options?: any) {
    const response = await searchClient.post('/api/v1/search', {
      query,
      index_name: indexName,
      options: options || { limit: 20 }
    });
    return response.data;
  },
  
  async batchSearch(queries: string[], indexName: string = 'research') {
    const response = await searchClient.post('/api/v1/batch-search', {
      queries,
      index_name: indexName,
      options: { limit: 10 }
    });
    return response.data;
  }
};

// pages/api/search.ts (NextJS API Route)
import { NextApiRequest, NextApiResponse } from 'next';
import { searchAPI } from '../../lib/searchClient';

export default async function handler(
  req: NextApiRequest,
  res: NextApiResponse
) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Method not allowed' });
  }
  
  try {
    const { query, index } = req.body;
    const results = await searchAPI.search(query, index);
    res.status(200).json(results);
  } catch (error) {
    console.error('Search error:', error);
    res.status(500).json({ error: 'Search failed' });
  }
}
```

## Environment Configuration

### Development (.env.development)

```env
API_KEY_REQUIRED=false  # Optional for development
SEARCH_PROXY_API_KEY=dev-key-for-testing
```

### Production (.env.production)

```env
API_KEY_REQUIRED=true
SEARCH_PROXY_API_KEY=your-secure-production-key
```

## Security Best Practices

### 1. Key Generation

Always use cryptographically secure methods:

```bash
# Good - 256-bit key
openssl rand -hex 32

# Good - Base64 encoded
openssl rand -base64 32

# Bad - Weak key
echo "myapikey123"
```

### 2. Key Storage

**DO:**
- Store in environment variables
- Use secret management services (AWS Secrets Manager, Vault)
- Restrict file permissions (chmod 600)
- Use .env files (add to .gitignore)

**DON'T:**
- Commit keys to version control
- Hardcode in source code
- Share keys in plain text
- Use the same key across environments

### 3. Key Rotation

Implement regular key rotation:

```bash
# 1. Generate new key
NEW_KEY=$(openssl rand -hex 32)

# 2. Update configuration
echo "SEARCH_PROXY_API_KEY=$NEW_KEY" >> .env.new

# 3. Deploy with both keys temporarily
# 4. Update all clients
# 5. Remove old key
```

### 4. Access Logging

Monitor API key usage:

```bash
# Check access logs
docker logs thai-search-proxy | grep "API key"

# Monitor failed attempts
docker logs thai-search-proxy | grep "Invalid API key"
```

## Troubleshooting

### Issue: 401 Unauthorized

**Symptom:**
```json
{
  "detail": "API key required. Please provide X-API-Key header or Authorization Bearer token."
}
```

**Solution:**
- Verify API_KEY_REQUIRED is set to true
- Check if API key is included in request
- Ensure header name is correct (X-API-Key)

### Issue: 403 Forbidden

**Symptom:**
```json
{
  "detail": "Invalid API key."
}
```

**Solution:**
- Verify API key matches configured value
- Check for extra spaces or newlines
- Ensure environment variable is loaded

### Issue: API Key Not Loading

**Debug Steps:**

```bash
# Check environment variables
docker exec thai-search-proxy env | grep API_KEY

# Verify configuration
docker exec thai-search-proxy cat .env | grep API_KEY

# Test directly
curl -H "X-API-Key: $SEARCH_PROXY_API_KEY" http://localhost:8000/health
```

## Disabling Authentication

To disable API key authentication (not recommended for production):

```env
API_KEY_REQUIRED=false
# SEARCH_PROXY_API_KEY can be omitted or empty
```

## Multiple API Keys (Advanced)

For supporting multiple API keys, you can extend the authentication:

```python
# Custom implementation in auth.py
VALID_API_KEYS = os.getenv("SEARCH_PROXY_API_KEYS", "").split(",")

def validate_api_key(api_key: str) -> bool:
    return api_key in VALID_API_KEYS
```

Environment configuration:
```env
SEARCH_PROXY_API_KEYS=key1,key2,key3
```

## Monitoring and Alerts

### Prometheus Metrics

Monitor authentication metrics:

```promql
# Failed authentication rate
rate(api_auth_failures_total[5m])

# Successful requests by API key
api_requests_total{status="success"}
```

### Alert Configuration

```yaml
# alerts.yml
groups:
  - name: api_auth
    rules:
      - alert: HighAuthFailureRate
        expr: rate(api_auth_failures_total[5m]) > 10
        annotations:
          summary: High API authentication failure rate
```

## API Key Management Script

Create a management script for operations:

```bash
#!/bin/bash
# api-key-manager.sh

case "$1" in
  generate)
    openssl rand -hex 32
    ;;
  rotate)
    echo "Current key: $(grep SEARCH_PROXY_API_KEY .env | cut -d= -f2)"
    NEW_KEY=$(openssl rand -hex 32)
    echo "New key: $NEW_KEY"
    sed -i "s/SEARCH_PROXY_API_KEY=.*/SEARCH_PROXY_API_KEY=$NEW_KEY/" .env
    ;;
  validate)
    curl -s -H "X-API-Key: $2" http://localhost:8000/health
    ;;
  *)
    echo "Usage: $0 {generate|rotate|validate <key>}"
    ;;
esac
```

## Summary

API key authentication provides:
- ✅ Simple implementation
- ✅ Easy integration
- ✅ Suitable for service-to-service communication
- ✅ Low overhead

For more advanced authentication needs (OAuth2, JWT), consider extending the authentication middleware.