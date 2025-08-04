# Production Setup Guide for Thai Search Proxy with Nginx Proxy Manager

This guide provides step-by-step instructions for deploying the Thai Search Proxy service in production using Nginx Proxy Manager (NPM).

## Prerequisites

1. **Nginx Proxy Manager** installed and running
2. **Domain name** configured (e.g., `search.cads.arda.or.th`)
3. **SSL certificate** (Let's Encrypt or custom)
4. **Docker** and **Docker Compose** installed
5. **MeiliSearch** instance running and accessible

## Step 1: Prepare the Environment

1. **Clone the repository** (if not already done):
```bash
git clone https://github.com/your-org/meilisearch-thai.git
cd meilisearch-thai/deployment/docker
```

2. **Create environment file**:
```bash
cp .env.example .env
```

3. **Edit `.env`** with your production values:
```bash
# IMPORTANT: Replace with your actual values
MEILISEARCH_HOST=http://your-meilisearch-host:7700
MEILISEARCH_API_KEY=your-secure-api-key-here
LOG_LEVEL=INFO
DEBUG=false
```

## Step 2: Deploy the Service

1. **Start the Thai Search Proxy**:
```bash
docker-compose -f docker-compose.npm-search-proxy.yml up -d
```

2. **Verify the service is running**:
```bash
# Check container status
docker ps | grep thai-tokenizer-search-proxy

# Check health endpoint
curl http://localhost:8000/health
```

## Step 3: Configure Nginx Proxy Manager

### 3.1 Add Proxy Host

1. **Login to NPM** admin interface (usually `http://your-server:81`)

2. **Go to "Proxy Hosts"** → **"Add Proxy Host"**

3. **Configure the Details tab**:
   - **Domain Names**: `search.cads.arda.or.th`
   - **Scheme**: `http`
   - **Forward Hostname/IP**: `localhost` (or Docker host IP)
   - **Forward Port**: `8000`
   - **Cache Assets**: ✓ (optional)
   - **Block Common Exploits**: ✓
   - **Websockets Support**: ✗ (not needed)

### 3.2 Configure SSL

1. **Go to SSL tab**:
   - **SSL Certificate**: Select "Request a new SSL Certificate"
   - **Force SSL**: ✓
   - **HTTP/2 Support**: ✓
   - **HSTS Enabled**: ✓
   - **HSTS Subdomains**: ✓ (if applicable)
   - **Email Address**: Your email for Let's Encrypt

2. **Click "Save"**

### 3.3 Advanced Configuration

1. **Go to Advanced tab** and add custom Nginx configuration:

```nginx
# Security headers
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;

# API-specific settings
proxy_buffering off;
proxy_request_buffering off;

# Timeouts for long-running searches
proxy_connect_timeout 60s;
proxy_send_timeout 60s;
proxy_read_timeout 60s;

# Rate limiting (adjust as needed)
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
limit_req zone=api_limit burst=50 nodelay;

# CORS headers (if needed)
if ($request_method = 'OPTIONS') {
    add_header 'Access-Control-Allow-Origin' '*' always;
    add_header 'Access-Control-Allow-Methods' 'GET, POST, OPTIONS' always;
    add_header 'Access-Control-Allow-Headers' 'DNT,User-Agent,X-Requested-With,If-Modified-Since,Cache-Control,Content-Type,Range,Authorization' always;
    add_header 'Access-Control-Max-Age' 1728000;
    add_header 'Content-Type' 'text/plain; charset=utf-8';
    add_header 'Content-Length' 0;
    return 204;
}
```

## Step 4: Production Configuration

### 4.1 Update Environment for Production

Edit `.env` file with production-ready settings:

```bash
# Performance tuning
WORKER_PROCESSES=8
MAX_WORKERS=8
BATCH_SIZE=50
TOKENIZER_CACHE_SIZE=5000

# Resource limits
CPU_LIMIT=4.0
MEMORY_LIMIT=2G

# Security
API_KEY_REQUIRED=true
THAI_TOKENIZER_API_KEY=generate-secure-key-here
CORS_ORIGINS=https://your-frontend-domain.com
ALLOWED_HOSTS=search.cads.arda.or.th

# Monitoring
COMPOSE_PROFILES=monitoring
PROMETHEUS_PORT=9090
```

### 4.2 Generate Secure API Key

```bash
# Generate a secure API key
openssl rand -base64 32
```

### 4.3 Restart with Production Settings

```bash
docker-compose -f docker-compose.npm-search-proxy.yml down
docker-compose -f docker-compose.npm-search-proxy.yml up -d
```

## Step 5: Monitoring Setup

### 5.1 Enable Prometheus Monitoring

The service includes Prometheus metrics at `/metrics` endpoint.

1. **Configure Prometheus** to scrape metrics:

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'thai-search-proxy'
    static_configs:
      - targets: ['search.cads.arda.or.th']
    metrics_path: '/metrics'
    scheme: 'https'
```

### 5.2 Setup Grafana Dashboard

Import the provided Grafana dashboard for monitoring:
- Search performance metrics
- API request rates
- Error rates
- Response times
- Resource usage

## Step 6: Security Hardening

### 6.1 API Key Authentication

If `API_KEY_REQUIRED=true`, clients must include the API key:

```bash
curl -H "X-API-Key: your-api-key" https://search.cads.arda.or.th/api/v1/search
```

### 6.2 IP Whitelisting (Optional)

In NPM Advanced configuration, add:

```nginx
# Allow specific IPs only
allow 192.168.1.0/24;
allow 10.0.0.0/8;
deny all;
```

### 6.3 Request Size Limits

```nginx
# Limit request body size
client_max_body_size 10M;

# Limit header size
large_client_header_buffers 4 16k;
```

## Step 7: Backup and Recovery

### 7.1 Backup Configuration

```bash
# Backup docker volumes
docker run --rm -v thai_search_proxy_npm_pythainlp_data:/data -v $(pwd):/backup alpine tar czf /backup/pythainlp_data_backup.tar.gz -C /data .

# Backup environment configuration
cp .env .env.backup.$(date +%Y%m%d)
```

### 7.2 Restore Procedure

```bash
# Restore volumes
docker run --rm -v thai_search_proxy_npm_pythainlp_data:/data -v $(pwd):/backup alpine tar xzf /backup/pythainlp_data_backup.tar.gz -C /data

# Restore configuration
cp .env.backup.20240101 .env
```

## Step 8: Testing Production Setup

### 8.1 Basic Health Check

```bash
curl https://search.cads.arda.or.th/health
```

### 8.2 Search Test

```bash
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "สาหร่ายวากาเมะ",
    "index_name": "research",
    "options": {
      "limit": 10
    }
  }'
```

### 8.3 Performance Test

```bash
# Install Apache Bench if not available
apt-get install apache2-utils

# Run performance test
ab -n 1000 -c 10 -H "X-API-Key: your-api-key" https://search.cads.arda.or.th/health
```

## Step 9: Maintenance

### 9.1 View Logs

```bash
# Application logs
docker logs -f thai_search_proxy_npm-thai-tokenizer-search-proxy-1

# Access logs in NPM
docker logs -f nginx-proxy-manager
```

### 9.2 Update Service

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose -f docker-compose.npm-search-proxy.yml build
docker-compose -f docker-compose.npm-search-proxy.yml up -d
```

### 9.3 Scale Service

For high traffic, run multiple instances behind NPM:

```bash
docker-compose -f docker-compose.npm-search-proxy.yml up -d --scale thai-tokenizer-search-proxy=3
```

## Troubleshooting

### Service Not Accessible

1. Check container is running: `docker ps`
2. Check logs: `docker logs thai_search_proxy_npm-thai-tokenizer-search-proxy-1`
3. Test locally: `curl http://localhost:8000/health`
4. Check NPM proxy configuration

### SSL Certificate Issues

1. Ensure domain DNS points to your server
2. Check NPM SSL settings
3. Try regenerating certificate in NPM

### Performance Issues

1. Check resource usage: `docker stats`
2. Review metrics at `/metrics` endpoint
3. Adjust worker processes and resource limits
4. Enable caching if not already enabled

### Search Not Working

1. Verify MeiliSearch connectivity
2. Check API key is correct
3. Review tokenizer logs for errors
4. Test with simple query first

## Support

For issues or questions:
1. Check application logs
2. Review NPM access logs
3. Monitor Prometheus metrics
4. Contact system administrator

---

**Note**: Always test configuration changes in a staging environment before applying to production.