# Production Setup for search.cads.arda.or.th

This guide walks you through setting up the Thai Tokenizer service to be accessible at `search.cads.arda.or.th` with proper SSL/HTTPS configuration.

## Overview

The setup includes:
- Thai Tokenizer service running in Docker
- Nginx reverse proxy with SSL termination
- Connection to your existing Meilisearch container
- Production-grade security and monitoring

## Prerequisites

1. **Server Requirements:**
   - Linux server with Docker and Docker Compose
   - At least 2GB RAM and 2 CPU cores
   - Ports 80 and 443 available

2. **DNS Configuration:**
   - `search.cads.arda.or.th` must point to your server's IP address
   - DNS propagation completed (check with `nslookup search.cads.arda.or.th`)

3. **Existing Meilisearch:**
   - Meilisearch container running and accessible
   - API key available
   - Network connectivity between containers

## Step-by-Step Setup

### Step 1: DNS Configuration

Ensure your DNS is configured:

```bash
# Check DNS resolution
nslookup search.cads.arda.or.th

# Should return your server's IP address
```

### Step 2: SSL Certificate Setup

Run the SSL setup script:

```bash
./setup-ssl.sh
```

Choose option 3 for Let's Encrypt (recommended for production) or option 2 for testing.

### Step 3: Configure Environment

Edit the production environment file:

```bash
nano .env.production
```

**Key configurations to update:**

```bash
# Meilisearch connection (update with your actual values)
MEILISEARCH_HOST=http://your-meilisearch-container:7700
MEILISEARCH_API_KEY=your-actual-meilisearch-api-key
MEILISEARCH_INDEX=your-index-name

# Your Meilisearch network name
EXTERNAL_MEILISEARCH_NETWORK=your-meilisearch-network

# Security (generate a strong API key)
THAI_TOKENIZER_API_KEY=your-very-secure-random-api-key

# Domain is already configured for search.cads.arda.or.th
```

### Step 4: Check Meilisearch Connection

First, identify your Meilisearch setup:

```bash
./check-meilisearch.sh
```

Update your `.env.production` based on the output.

### Step 5: Deploy the Service

Deploy the Thai Tokenizer:

```bash
./deploy-production.sh
```

This will:
- Build the Thai Tokenizer Docker image
- Start the service with Nginx reverse proxy
- Configure SSL termination
- Set up health checks and monitoring

### Step 6: Verify Deployment

Check that everything is working:

```bash
# Check service status
./deploy-production.sh status

# Test HTTPS endpoint
curl https://search.cads.arda.or.th/health

# Check detailed health (including Meilisearch connection)
curl https://search.cads.arda.or.th/health/detailed
```

## Service URLs

Once deployed, your service will be available at:

- **Main Service**: `https://search.cads.arda.or.th`
- **Health Check**: `https://search.cads.arda.or.th/health`
- **API Documentation**: `https://search.cads.arda.or.th/docs`
- **Detailed Health**: `https://search.cads.arda.or.th/health/detailed`

## API Usage Examples

### Basic Health Check

```bash
curl https://search.cads.arda.or.th/health
```

### Tokenize Thai Text

```bash
curl -X POST "https://search.cads.arda.or.th/tokenize" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "text": "สวัสดีครับ นี่คือการทดสอบระบบโทเค็นไนเซอร์ภาษาไทย"
  }'
```

### Process Document for Meilisearch

```bash
curl -X POST "https://search.cads.arda.or.th/process-document" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "content": "เนื้อหาเอกสารภาษาไทยที่ต้องการประมวลผลและจัดเก็บใน Meilisearch",
    "title": "หัวข้อเอกสาร",
    "metadata": {
      "category": "research",
      "author": "ARDA"
    }
  }'
```

## Security Configuration

### API Key Authentication

The service is configured with API key authentication. Include the API key in requests:

```bash
# In headers
-H "X-API-Key: your-api-key"

# Or as query parameter
?api_key=your-api-key
```

### CORS Configuration

CORS is configured to allow requests from:
- `https://cads.arda.or.th`
- `https://arda.or.th`

### Rate Limiting

Nginx is configured with rate limiting:
- API endpoints: 10 requests/second per IP
- Health checks: 30 requests/second per IP

## Monitoring and Logs

### View Logs

```bash
# Service logs
./deploy-production.sh logs

# Nginx access logs
tail -f logs/nginx/thai-tokenizer-access.log

# Nginx error logs
tail -f logs/nginx/thai-tokenizer-error.log
```

### Health Monitoring

```bash
# Basic health check
curl https://search.cads.arda.or.th/health

# Detailed health (includes Meilisearch status)
curl https://search.cads.arda.or.th/health/detailed

# Service metrics (restricted to internal networks)
curl https://search.cads.arda.or.th/metrics
```

## Service Management

### Common Commands

```bash
# Deploy/Update service
./deploy-production.sh deploy

# Stop service
./deploy-production.sh stop

# Restart service
./deploy-production.sh restart

# View service status
./deploy-production.sh status

# View logs
./deploy-production.sh logs

# Health check
./deploy-production.sh health
```

### Manual Docker Commands

```bash
# View containers
docker ps | grep thai

# Service logs
docker logs thai_tokenizer_prod-thai-tokenizer-1 -f

# Nginx logs
docker logs thai_tokenizer_prod-nginx-1 -f

# Execute commands in container
docker exec -it thai_tokenizer_prod-thai-tokenizer-1 bash
```

## SSL Certificate Management

### Let's Encrypt Renewal

Set up automatic renewal:

```bash
# Add to crontab
0 12 * * * /usr/bin/docker run --rm -v /path/to/ssl/certbot:/etc/letsencrypt -v /path/to/ssl/certbot:/var/www/certbot certbot/certbot renew --quiet
```

### Manual Certificate Renewal

```bash
# Renew certificate
docker run --rm \
  -v "$PWD/ssl/certbot:/etc/letsencrypt" \
  -v "$PWD/ssl/certbot:/var/www/certbot" \
  certbot/certbot renew

# Copy renewed certificates
cp ssl/certbot/live/search.cads.arda.or.th/fullchain.pem ssl/search.cads.arda.or.th.crt
cp ssl/certbot/live/search.cads.arda.or.th/privkey.pem ssl/search.cads.arda.or.th.key

# Restart nginx
docker-compose -f deployment/docker/docker-compose.production.yml restart nginx
```

## Troubleshooting

### Common Issues

1. **SSL Certificate Issues**
   ```bash
   # Check certificate validity
   openssl x509 -in ssl/search.cads.arda.or.th.crt -noout -dates
   
   # Test SSL connection
   openssl s_client -connect search.cads.arda.or.th:443
   ```

2. **Cannot Connect to Meilisearch**
   ```bash
   # Test from Thai Tokenizer container
   docker exec thai_tokenizer_prod-thai-tokenizer-1 curl http://your-meilisearch:7700/health
   
   # Check network connectivity
   docker network ls
   docker network inspect your-meilisearch-network
   ```

3. **Service Not Accessible**
   ```bash
   # Check if ports are open
   netstat -tlnp | grep :80
   netstat -tlnp | grep :443
   
   # Check DNS resolution
   nslookup search.cads.arda.or.th
   
   # Check firewall
   ufw status
   ```

### Log Analysis

```bash
# Check for errors in service logs
docker logs thai_tokenizer_prod-thai-tokenizer-1 | grep ERROR

# Check nginx access patterns
tail -f logs/nginx/thai-tokenizer-access.log | grep -v "GET /health"

# Monitor real-time requests
tail -f logs/nginx/thai-tokenizer-access.log
```

## Performance Optimization

### Resource Tuning

Edit `.env.production`:

```bash
# Increase for high-traffic sites
WORKER_PROCESSES=8
CPU_LIMIT=4.0
MEMORY_LIMIT=2G

# Adjust batch size for performance
BATCH_SIZE=100
```

### Nginx Optimization

The Nginx configuration includes:
- Gzip compression
- HTTP/2 support
- Connection keep-alive
- Proxy buffering
- Rate limiting

## Backup and Recovery

### Configuration Backup

```bash
# Backup configuration
tar -czf backup-$(date +%Y%m%d).tar.gz .env.production ssl/ logs/
```

### Service Recovery

```bash
# Quick recovery
git pull
./deploy-production.sh deploy

# Full recovery from backup
tar -xzf backup-YYYYMMDD.tar.gz
./deploy-production.sh deploy
```

## Integration with Your Applications

### Frontend Integration

```javascript
// Example JavaScript integration
const API_BASE = 'https://search.cads.arda.or.th';
const API_KEY = 'your-api-key';

async function tokenizeText(text) {
  const response = await fetch(`${API_BASE}/tokenize`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': API_KEY
    },
    body: JSON.stringify({ text })
  });
  
  return await response.json();
}
```

### Backend Integration

```python
# Example Python integration
import requests

API_BASE = 'https://search.cads.arda.or.th'
API_KEY = 'your-api-key'

def process_document(content, title, metadata=None):
    response = requests.post(
        f'{API_BASE}/process-document',
        json={
            'content': content,
            'title': title,
            'metadata': metadata or {}
        },
        headers={'X-API-Key': API_KEY}
    )
    return response.json()
```

This setup provides a production-ready Thai Tokenizer service accessible at `search.cads.arda.or.th` with enterprise-grade security, monitoring, and performance.