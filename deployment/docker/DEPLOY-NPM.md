# Deploying Thai Search Proxy with Nginx Proxy Manager

This guide explains how to deploy the Thai Search Proxy service with Nginx Proxy Manager (NPM) for production use.

## Prerequisites

1. **Nginx Proxy Manager** already installed and configured
2. **MeiliSearch** instance running (can be external)
3. **Docker** and **Docker Compose** installed
4. Domain name configured (e.g., `search.cads.arda.or.th`)

## Quick Start Deployment

### Step 1: Configure Environment

```bash
# Copy the NPM-specific environment template
cp .env.npm-search-proxy .env

# Edit the configuration
nano .env
```

**Important settings to update:**
```env
# Your MeiliSearch connection
MEILISEARCH_HOST=http://your-meilisearch-host:7700
MEILISEARCH_API_KEY=your-secure-api-key

# Service configuration
THAI_TOKENIZER_PORT=8000  # Port NPM will proxy to
ENVIRONMENT=production
```

### Step 2: Deploy the Service

```bash
# Deploy Thai Search Proxy with NPM configuration
docker-compose -f docker-compose.npm-search-proxy.yml up -d

# Check if service is running
docker-compose -f docker-compose.npm-search-proxy.yml ps

# View logs
docker-compose -f docker-compose.npm-search-proxy.yml logs -f
```

### Step 3: Configure Nginx Proxy Manager

1. **Access NPM Admin Panel** (usually http://your-server:81)

2. **Add Proxy Host:**
   - Domain Names: `search.cads.arda.or.th`
   - Scheme: `http`
   - Forward Hostname/IP: `localhost` or Docker host IP
   - Forward Port: `8000`
   - Enable "Block Common Exploits"
   - Enable "Websockets Support"

3. **SSL Configuration:**
   - SSL Certificate: Request Let's Encrypt certificate
   - Force SSL: Enable
   - HTTP/2 Support: Enable
   - HSTS Enabled: Enable
   - HSTS Subdomains: Enable

4. **Advanced Configuration** (Custom Nginx Configuration):
   ```nginx
   # Add to Custom Nginx Configuration in NPM
   
   # Increase timeouts for search operations
   proxy_connect_timeout 60s;
   proxy_send_timeout 60s;
   proxy_read_timeout 60s;
   
   # Increase buffer sizes for large responses
   proxy_buffer_size 16k;
   proxy_buffers 8 16k;
   proxy_busy_buffers_size 32k;
   
   # Add security headers
   add_header X-Content-Type-Options "nosniff" always;
   add_header X-Frame-Options "SAMEORIGIN" always;
   add_header X-XSS-Protection "1; mode=block" always;
   
   # Enable CORS if needed
   add_header Access-Control-Allow-Origin "$http_origin" always;
   add_header Access-Control-Allow-Methods "GET, POST, OPTIONS" always;
   add_header Access-Control-Allow-Headers "Authorization, Content-Type" always;
   
   # Cache static responses
   location ~* \.(css|js|jpg|jpeg|png|gif|ico|svg)$ {
       expires 1y;
       add_header Cache-Control "public, immutable";
   }
   
   # Health check endpoint caching
   location = /health {
       proxy_pass http://localhost:8000;
       proxy_cache_valid 200 5s;
   }
   
   # Metrics endpoint (restrict access)
   location /metrics {
       proxy_pass http://localhost:8000;
       allow 10.0.0.0/8;  # Internal network only
       deny all;
   }
   ```

## Verify Deployment

### Step 1: Check Service Health

```bash
# Local health check
curl http://localhost:8000/health

# Via NPM domain
curl https://search.cads.arda.or.th/health

# Detailed health check
curl https://search.cads.arda.or.th/api/v1/health
```

### Step 2: Test Search Functionality

```bash
# Test Thai search
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ค้นหาเอกสาร",
    "index_name": "documents"
  }'

# Test batch search
curl -X POST https://search.cads.arda.or.th/api/v1/batch-search \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["คำค้นหา1", "คำค้นหา2"],
    "index_name": "documents"
  }'
```

### Step 3: Check Analytics

```bash
# View search analytics
curl https://search.cads.arda.or.th/api/v1/analytics/queries

# Popular searches
curl https://search.cads.arda.or.th/api/v1/analytics/popular-searches
```

## Enable Monitoring (Optional)

### Deploy with Prometheus

```bash
# Deploy with monitoring profile
docker-compose -f docker-compose.npm-search-proxy.yml --profile monitoring up -d

# Access Prometheus at http://localhost:9090
```

### Configure NPM for Prometheus

Add another proxy host in NPM:
- Domain: `metrics.cads.arda.or.th`
- Forward to: `localhost:9090`
- Enable SSL and security settings

### Import Grafana Dashboards

If using Grafana:
1. Access Grafana (deploy separately)
2. Add Prometheus data source: `http://prometheus:9090`
3. Import search proxy dashboards from `grafana/dashboards/`

## Performance Tuning

### Optimize for High Traffic

Update `.env` for production load:

```env
# Increase concurrent searches
SEARCH_PROXY_MAX_CONCURRENT=20

# Increase worker processes
WORKER_PROCESSES=8

# Increase cache size
TOKENIZER_CACHE_SIZE=5000

# Increase resource limits
CPU_LIMIT=4.0
MEMORY_LIMIT=2G
```

### Enable Caching in NPM

Add to NPM Custom Nginx Configuration:

```nginx
# Cache search results
location /api/v1/search {
    proxy_pass http://localhost:8000;
    proxy_cache search_cache;
    proxy_cache_valid 200 5m;
    proxy_cache_key "$request_method$request_uri$request_body";
    proxy_cache_methods POST;
    proxy_cache_bypass $http_cache_control;
    add_header X-Cache-Status $upstream_cache_status;
}

# Define cache zone (add to http context)
proxy_cache_path /var/cache/nginx/search levels=1:2 keys_zone=search_cache:10m max_size=100m inactive=60m;
```

## Maintenance

### View Logs

```bash
# All logs
docker-compose -f docker-compose.npm-search-proxy.yml logs

# Follow logs
docker-compose -f docker-compose.npm-search-proxy.yml logs -f

# Search proxy specific logs
docker exec thai-tokenizer-search-proxy tail -f /home/appuser/search-proxy/logs/search.log
```

### Update Service

```bash
# Pull latest changes
git pull

# Rebuild and restart
docker-compose -f docker-compose.npm-search-proxy.yml build
docker-compose -f docker-compose.npm-search-proxy.yml up -d
```

### Backup Analytics Data

```bash
# Backup analytics volume
docker run --rm -v search_analytics:/data -v $(pwd):/backup alpine \
  tar czf /backup/analytics-backup-$(date +%Y%m%d).tar.gz -C /data .
```

## Troubleshooting

### Service Won't Start

```bash
# Check logs
docker-compose -f docker-compose.npm-search-proxy.yml logs thai-tokenizer-search-proxy

# Check MeiliSearch connectivity
curl http://your-meilisearch-host:7700/health
```

### NPM Returns 502 Bad Gateway

1. Check if service is running: `docker ps`
2. Check health: `curl http://localhost:8000/health`
3. Check NPM error log in NPM admin panel
4. Verify port configuration matches

### Slow Response Times

1. Check metrics: `curl http://localhost:8000/metrics/search-proxy`
2. Increase concurrent searches in `.env`
3. Enable caching if disabled
4. Check MeiliSearch performance

### High Memory Usage

1. Reduce cache TTL: `SEARCH_PROXY_PERFORMANCE__CACHE_TTL_SECONDS=180`
2. Lower max results: `SEARCH_PROXY_RANKING__MAX_RESULTS_PER_VARIANT=50`
3. Decrease batch size: `BATCH_SIZE=10`

## Security Checklist

- [ ] Strong MeiliSearch API key configured
- [ ] NPM SSL certificate active
- [ ] Metrics endpoint restricted (see NPM config)
- [ ] CORS properly configured
- [ ] Rate limiting enabled in NPM
- [ ] Regular security updates applied

## Support

For issues:
1. Check service logs
2. Review health status
3. Consult metrics dashboard
4. Check NPM error logs

For detailed API documentation, visit:
- Health: `https://search.cads.arda.or.th/docs`
- OpenAPI: `https://search.cads.arda.or.th/openapi.json`