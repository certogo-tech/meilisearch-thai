# Thai Search Proxy Docker Deployment

This directory contains Docker configurations for deploying the Thai Search Proxy service, which provides intelligent Thai language search capabilities through advanced tokenization, parallel search execution, and result ranking.

## Quick Start

### Basic Deployment

```bash
# Start the search proxy with MeiliSearch
docker-compose -f docker-compose.yml -f docker-compose.search-proxy.yml up -d

# Check service health
docker-compose ps
curl http://localhost:8001/api/v1/health
```

### With Monitoring Stack

```bash
# Start with Prometheus and Grafana monitoring
docker-compose -f docker-compose.yml -f docker-compose.search-proxy.yml --profile monitoring up -d

# Access services:
# - Search Proxy API: http://localhost:8001
# - MeiliSearch: http://localhost:7700
# - Prometheus: http://localhost:9090
# - Grafana: http://localhost:3000 (admin/admin)
```

## Configuration

### Environment Variables

Create a `.env` file to customize the deployment:

```env
# MeiliSearch Configuration
MEILISEARCH_API_KEY=your-secure-api-key
MEILI_ENV=production

# Search Proxy Configuration
SEARCH_PROXY_ENABLED=true
ENVIRONMENT=production
SEARCH_PROXY_PRIMARY_ENGINE=newmm
SEARCH_PROXY_MAX_CONCURRENT=10
SEARCH_PROXY_TIMEOUT_MS=5000
SEARCH_PROXY_RANKING_ALGORITHM=optimized_score

# Performance Tuning
SEARCH_PROXY_CACHE=true
SEARCH_PROXY_METRICS=true
DETAILED_LOGGING=false

# Monitoring
GRAFANA_ADMIN_PASSWORD=secure-password
```

### Search Proxy Features

The deployment includes:

1. **Thai Tokenization**
   - Primary engine: NewMM
   - Fallback engines: AttaCut, DeepCut
   - Mixed Thai-English support
   - Compound word handling

2. **Search Optimization**
   - Parallel query variant execution
   - Result deduplication
   - Intelligent ranking with Thai-specific boosting
   - Response caching

3. **Monitoring & Analytics**
   - Prometheus metrics collection
   - Search analytics tracking
   - Performance monitoring
   - Query pattern analysis

## API Endpoints

### Search Endpoints

```bash
# Single search
curl -X POST http://localhost:8001/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ค้นหาเอกสารภาษาไทย",
    "index_name": "documents",
    "options": {
      "limit": 20,
      "offset": 0
    }
  }'

# Batch search
curl -X POST http://localhost:8001/api/v1/batch-search \
  -H "Content-Type: application/json" \
  -d '{
    "queries": ["คำค้นหา1", "คำค้นหา2", "คำค้นหา3"],
    "index_name": "documents"
  }'
```

### Analytics Endpoints

```bash
# Query analytics
curl http://localhost:8001/api/v1/analytics/queries

# Performance trends
curl http://localhost:8001/api/v1/analytics/performance-trends?hours=24

# Search quality report
curl http://localhost:8001/api/v1/analytics/quality-report

# Popular searches
curl http://localhost:8001/api/v1/analytics/popular-searches?limit=50
```

### Monitoring Endpoints

```bash
# Health check
curl http://localhost:8001/api/v1/health

# Prometheus metrics
curl http://localhost:8001/metrics

# Search proxy specific metrics
curl http://localhost:8001/metrics/search-proxy
```

## Performance Tuning

### Resource Allocation

The default configuration allocates:
- CPU: 2.5 cores limit, 1.0 core reserved
- Memory: 1.5GB limit, 512MB reserved

Adjust in `docker-compose.search-proxy.yml`:

```yaml
deploy:
  resources:
    limits:
      cpus: '4.0'    # Increase for higher throughput
      memory: 2G     # Increase for larger caches
```

### Caching Configuration

```env
SEARCH_PROXY_PERFORMANCE__CACHE_ENABLED=true
SEARCH_PROXY_PERFORMANCE__CACHE_TTL_SECONDS=600  # 10 minutes
SEARCH_PROXY_PERFORMANCE__MEMORY_LIMIT_MB=512    # Increase cache size
```

### Concurrent Search Tuning

```env
SEARCH_PROXY_SEARCH__MAX_CONCURRENT_SEARCHES=20   # Increase parallelism
SEARCH_PROXY_SEARCH__TIMEOUT_MS=3000             # Reduce for faster responses
SEARCH_PROXY_SEARCH__MAX_QUERY_VARIANTS=3        # Reduce for performance
```

## Monitoring Setup

### Prometheus Queries

Useful queries for monitoring:

```promql
# Request rate
rate(search_proxy_total_searches[5m])

# Success rate
search_proxy_success_rate_percent

# Response time percentiles
search_proxy_response_time_p95_ms
search_proxy_response_time_p99_ms

# Active searches
search_proxy_active_searches

# Cache hit rate
search_proxy_cache_hit_rate_percent
```

### Grafana Dashboard

Import the provided dashboard for comprehensive monitoring:
1. Navigate to Grafana (http://localhost:3000)
2. Go to Dashboards → Import
3. Upload `grafana/dashboards/search-proxy-dashboard.json`

## Troubleshooting

### Common Issues

1. **Service fails to start**
   ```bash
   # Check logs
   docker-compose logs thai-tokenizer-search-proxy
   
   # Verify MeiliSearch is healthy
   docker-compose ps meilisearch
   ```

2. **Slow search responses**
   - Check metrics: `curl http://localhost:8001/metrics/search-proxy`
   - Increase concurrent searches limit
   - Enable caching if disabled
   - Check MeiliSearch performance

3. **High memory usage**
   - Reduce cache TTL
   - Lower max results per variant
   - Decrease batch size limits

### Debug Mode

Enable detailed logging:
```env
DETAILED_LOGGING=true
THAI_TOKENIZER_LOG_LEVEL=DEBUG
```

## Production Deployment

### Security Considerations

1. **API Keys**: Always use strong API keys in production
   ```env
   MEILISEARCH_API_KEY=<generate-secure-key>
   ```

2. **Network Security**: Use reverse proxy with SSL
   ```yaml
   # nginx.conf example
   location /api/v1/search {
       proxy_pass http://thai-tokenizer-search-proxy:8000;
       proxy_set_header X-Real-IP $remote_addr;
   }
   ```

3. **Resource Limits**: Set appropriate limits to prevent DoS
   ```env
   SEARCH_PROXY_PERFORMANCE__MAX_QUERY_LENGTH=200
   SEARCH_PROXY_PERFORMANCE__MAX_BATCH_SIZE=25
   ```

### Backup and Recovery

```bash
# Backup MeiliSearch data
docker-compose exec meilisearch meilisearch --dump

# Backup analytics data
docker run --rm -v search_analytics:/data -v $(pwd):/backup alpine tar czf /backup/analytics-backup.tar.gz -C /data .
```

## Scaling

### Horizontal Scaling

For high-traffic deployments:

1. Use Docker Swarm or Kubernetes
2. Deploy multiple search proxy instances
3. Use load balancer for distribution
4. Share MeiliSearch instance or use cluster

### Vertical Scaling

Increase resources for single instance:
```yaml
deploy:
  resources:
    limits:
      cpus: '8.0'
      memory: 4G
```

## Support

For issues or questions:
1. Check logs: `docker-compose logs -f thai-tokenizer-search-proxy`
2. Review metrics: http://localhost:8001/metrics
3. Consult health status: http://localhost:8001/api/v1/health