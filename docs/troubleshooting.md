# Troubleshooting Guide

This guide helps diagnose and resolve common issues with the Thai Tokenizer for MeiliSearch integration.

## Table of Contents

- [Quick Diagnostics](#quick-diagnostics)
- [Service Issues](#service-issues)
- [Tokenization Problems](#tokenization-problems)
- [Search Issues](#search-issues)
- [Performance Problems](#performance-problems)
- [Configuration Issues](#configuration-issues)
- [Docker Issues](#docker-issues)
- [Network Problems](#network-problems)
- [Data Issues](#data-issues)
- [Monitoring and Debugging](#monitoring-and-debugging)

## Quick Diagnostics

### Health Check Commands

```bash
# Check all services
curl http://localhost:8000/health
curl http://localhost:7700/health
curl http://localhost/health  # If using nginx proxy

# Check Docker services
docker compose ps
docker compose logs --tail=50 thai-tokenizer
docker compose logs --tail=50 meilisearch

# Check system resources
docker stats
df -h  # Disk space
free -h  # Memory usage
```

### Common Status Indicators

| Service | Healthy Response | Unhealthy Indicators |
|---------|------------------|---------------------|
| Thai Tokenizer | `{"status": "healthy"}` | Connection refused, 500 errors |
| MeiliSearch | `{"status": "available"}` | Connection timeout, index errors |
| Nginx | `200 OK` | 502/503 errors, connection refused |

## Service Issues

### Thai Tokenizer Service Won't Start

#### Symptoms
- Container exits immediately
- Connection refused on port 8000
- Import errors in logs

#### Diagnosis
```bash
# Check container logs
docker compose logs thai-tokenizer

# Check if port is in use
netstat -tlnp | grep :8000
lsof -i :8000

# Test direct Python execution
python -c "from src.api.main import app; print('Import successful')"
```

#### Solutions

**Missing Dependencies**
```bash
# Rebuild container with latest dependencies
docker compose build --no-cache thai-tokenizer
docker compose up -d thai-tokenizer
```

**Port Conflicts**
```bash
# Change port in docker-compose.yml
services:
  thai-tokenizer:
    ports:
      - "8001:8000"  # Use different external port
```

**PyThaiNLP Data Issues**
```bash
# Clear PyThaiNLP cache and rebuild
docker compose exec thai-tokenizer rm -rf /home/appuser/.pythainlp
docker compose restart thai-tokenizer
```

**Memory Issues**
```bash
# Increase memory limit
services:
  thai-tokenizer:
    deploy:
      resources:
        limits:
          memory: 1G
```

### MeiliSearch Service Issues

#### Symptoms
- MeiliSearch not responding
- Index creation failures
- Search timeouts

#### Diagnosis
```bash
# Check MeiliSearch logs
docker compose logs meilisearch

# Test MeiliSearch directly
curl http://localhost:7700/health
curl http://localhost:7700/version

# Check data volume
docker volume inspect meilisearch-thai_meilisearch_data
```

#### Solutions

**Data Corruption**
```bash
# Reset MeiliSearch data (WARNING: deletes all data)
docker compose down
docker volume rm meilisearch-thai_meilisearch_data
docker compose up -d

# Restore from backup if available
python scripts/setup_demo.py
```

**Memory Issues**
```bash
# Increase MeiliSearch memory
services:
  meilisearch:
    environment:
      - MEILI_MAX_INDEXING_MEMORY=4Gb
```

**Permission Issues**
```bash
# Fix volume permissions
docker compose exec meilisearch chown -R meili:meili /meili_data
```

## Tokenization Problems

### Poor Tokenization Quality

#### Symptoms
- Incorrect word boundaries
- Missing compound words
- Unexpected token splits

#### Diagnosis
```bash
# Test tokenization directly
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"}'

# Check tokenizer configuration
curl http://localhost:8000/api/v1/config
```

#### Solutions

**Update Custom Dictionary**
```bash
curl -X PUT http://localhost:8000/api/v1/config/tokenizer \
  -H "Content-Type: application/json" \
  -d '{
    "custom_dictionary": [
      "ปัญญาประดิษฐ์",
      "การเรียนรู้ของเครื่อง",
      "เทคโนโลยีบล็อกเชน"
    ]
  }'
```

**Try Different Engine**
```bash
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ปัญญาประดิษฐ์",
    "options": {"engine": "attacut"}
  }'
```

**Check PyThaiNLP Version**
```bash
docker compose exec thai-tokenizer python -c "import pythainlp; print(pythainlp.__version__)"
```

### Tokenization Errors

#### Symptoms
- 500 errors on tokenization requests
- Timeout errors
- Memory errors

#### Diagnosis
```bash
# Check error logs
docker compose logs thai-tokenizer | grep ERROR

# Test with simple text
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "ทดสอบ"}'

# Monitor memory usage
docker stats thai-tokenizer
```

#### Solutions

**Memory Issues**
```bash
# Increase container memory
services:
  thai-tokenizer:
    deploy:
      resources:
        limits:
          memory: 2G
```

**Text Length Issues**
```bash
# Process in smaller chunks
curl -X POST http://localhost:8000/api/v1/tokenize/batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["chunk1", "chunk2", "chunk3"]
  }'
```

## Search Issues

### Poor Search Results

#### Symptoms
- Relevant documents not found
- Incorrect ranking
- Missing compound word matches

#### Diagnosis
```bash
# Test search directly in MeiliSearch
curl "http://localhost:7700/indexes/documents/search?q=ปัญญาประดิษฐ์"

# Check index configuration
curl http://localhost:7700/indexes/documents/settings

# Test with tokenized query
curl -X POST http://localhost:8000/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{"query": "ปัญญาประดิษฐ์"}'
```

#### Solutions

**Reconfigure Index**
```bash
# Update searchable attributes
curl -X PUT http://localhost:7700/indexes/documents/settings/searchable-attributes \
  -H "Content-Type: application/json" \
  -d '[
    "title",
    "content", 
    "title_tokenized",
    "content_tokenized",
    "searchable_text_tokenized"
  ]'
```

**Add Synonyms**
```bash
curl -X PUT http://localhost:7700/indexes/documents/settings/synonyms \
  -H "Content-Type: application/json" \
  -d '{
    "AI": ["ปัญญาประดิษฐ์", "เอไอ"],
    "ปัญญาประดิษฐ์": ["AI", "เอไอ"]
  }'
```

**Reindex Documents**
```bash
python scripts/setup_demo.py
```

### Search Timeouts

#### Symptoms
- Search requests timeout
- 503 service unavailable
- Slow response times

#### Diagnosis
```bash
# Check MeiliSearch performance
curl "http://localhost:7700/indexes/documents/stats"

# Monitor resource usage
docker stats meilisearch

# Test simple queries
curl "http://localhost:7700/indexes/documents/search?q=test&limit=1"
```

#### Solutions

**Optimize Index Settings**
```bash
# Reduce searchable attributes
curl -X PUT http://localhost:7700/indexes/documents/settings/searchable-attributes \
  -H "Content-Type: application/json" \
  -d '["title", "content_tokenized"]'

# Adjust ranking rules
curl -X PUT http://localhost:7700/indexes/documents/settings/ranking-rules \
  -H "Content-Type: application/json" \
  -d '["words", "typo", "proximity", "attribute", "exactness"]'
```

**Increase Resources**
```bash
services:
  meilisearch:
    environment:
      - MEILI_MAX_INDEXING_THREADS=8
    deploy:
      resources:
        limits:
          memory: 4G
          cpus: '2.0'
```

## Performance Problems

### Slow Tokenization

#### Symptoms
- High response times (>100ms)
- CPU usage spikes
- Request timeouts

#### Diagnosis
```bash
# Run performance benchmark
python scripts/benchmark.py

# Monitor during tokenization
docker stats thai-tokenizer

# Test with different text sizes
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "short text"}'
```

#### Solutions

**Optimize Container Resources**
```bash
services:
  thai-tokenizer:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
```

**Enable Caching**
```bash
curl -X PUT http://localhost:8000/api/v1/config/processing \
  -H "Content-Type: application/json" \
  -d '{
    "enable_caching": true,
    "cache_ttl_seconds": 3600
  }'
```

**Use Batch Processing**
```bash
# Process multiple texts together
curl -X POST http://localhost:8000/api/v1/tokenize/batch \
  -H "Content-Type: application/json" \
  -d '{"texts": ["text1", "text2", "text3"]}'
```

### High Memory Usage

#### Symptoms
- Out of memory errors
- Container restarts
- System slowdown

#### Diagnosis
```bash
# Monitor memory usage
docker stats --no-stream
free -h

# Check for memory leaks
docker compose exec thai-tokenizer ps aux
```

#### Solutions

**Increase Memory Limits**
```bash
services:
  thai-tokenizer:
    deploy:
      resources:
        limits:
          memory: 2G
  meilisearch:
    deploy:
      resources:
        limits:
          memory: 4G
```

**Optimize Processing**
```bash
# Reduce batch sizes
curl -X PUT http://localhost:8000/api/v1/config/processing \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 50,
    "max_concurrent": 5
  }'
```

## Configuration Issues

### Invalid Configuration

#### Symptoms
- Service startup failures
- Configuration validation errors
- Feature not working as expected

#### Diagnosis
```bash
# Check current configuration
curl http://localhost:8000/api/v1/config

# Validate configuration
docker compose config

# Check environment variables
docker compose exec thai-tokenizer env | grep THAI_TOKENIZER
```

#### Solutions

**Reset to Defaults**
```bash
# Reset tokenizer configuration
curl -X PUT http://localhost:8000/api/v1/config/tokenizer \
  -H "Content-Type: application/json" \
  -d '{
    "engine": "pythainlp",
    "keep_whitespace": true,
    "handle_compounds": true
  }'
```

**Fix Environment Variables**
```bash
# Update .env file
MEILISEARCH_HOST=http://meilisearch:7700
MEILISEARCH_API_KEY=masterKey
LOG_LEVEL=INFO

# Restart services
docker compose down
docker compose up -d
```

### Connection Issues

#### Symptoms
- Cannot connect to MeiliSearch
- Network timeouts
- Service discovery failures

#### Diagnosis
```bash
# Test network connectivity
docker compose exec thai-tokenizer curl http://meilisearch:7700/health

# Check network configuration
docker network ls
docker network inspect meilisearch-thai_thai-tokenizer-network
```

#### Solutions

**Fix Network Configuration**
```bash
# Ensure services are on same network
services:
  thai-tokenizer:
    networks:
      - thai-tokenizer-network
  meilisearch:
    networks:
      - thai-tokenizer-network

networks:
  thai-tokenizer-network:
    driver: bridge
```

**Update Connection Settings**
```bash
curl -X PUT http://localhost:8000/api/v1/config/meilisearch \
  -H "Content-Type: application/json" \
  -d '{
    "host": "http://meilisearch:7700",
    "timeout_ms": 10000,
    "max_retries": 5
  }'
```

## Docker Issues

### Container Build Failures

#### Symptoms
- Docker build errors
- Missing dependencies
- Permission denied errors

#### Diagnosis
```bash
# Check build logs
docker compose build --no-cache thai-tokenizer

# Test base image
docker run --rm python:3.12-slim python --version

# Check Dockerfile syntax
docker build -f deployment/docker/Dockerfile .
```

#### Solutions

**Clear Build Cache**
```bash
docker system prune -a
docker compose build --no-cache
```

**Fix Dockerfile Issues**
```dockerfile
# Ensure proper permissions
RUN mkdir -p /home/appuser/.pythainlp && \
    chown -R appuser:appuser /home/appuser
```

**Update Dependencies**
```bash
# Update requirements.txt
pip-compile requirements.in
docker compose build --no-cache
```

### Volume Issues

#### Symptoms
- Data not persisting
- Permission errors
- Volume mount failures

#### Diagnosis
```bash
# Check volumes
docker volume ls
docker volume inspect meilisearch-thai_meilisearch_data

# Check permissions
docker compose exec meilisearch ls -la /meili_data
```

#### Solutions

**Fix Volume Permissions**
```bash
# Reset volume permissions
docker compose exec meilisearch chown -R meili:meili /meili_data
```

**Recreate Volumes**
```bash
# WARNING: This deletes data
docker compose down -v
docker compose up -d
```

## Network Problems

### Port Conflicts

#### Symptoms
- Port already in use errors
- Cannot bind to port
- Connection refused

#### Diagnosis
```bash
# Check port usage
netstat -tlnp | grep :8000
lsof -i :8000

# Check Docker port mappings
docker compose ps
```

#### Solutions

**Change Ports**
```yaml
# docker-compose.yml
services:
  thai-tokenizer:
    ports:
      - "8001:8000"  # Use different external port
  meilisearch:
    ports:
      - "7701:7700"
```

**Stop Conflicting Services**
```bash
# Find and stop conflicting process
sudo kill $(lsof -t -i:8000)
```

### DNS Resolution Issues

#### Symptoms
- Cannot resolve service names
- Connection timeouts between services
- Network unreachable errors

#### Diagnosis
```bash
# Test DNS resolution
docker compose exec thai-tokenizer nslookup meilisearch
docker compose exec thai-tokenizer ping meilisearch
```

#### Solutions

**Use IP Addresses**
```bash
# Get container IP
docker inspect meilisearch | grep IPAddress

# Update configuration with IP
MEILISEARCH_HOST=http://172.18.0.2:7700
```

**Recreate Network**
```bash
docker compose down
docker network prune
docker compose up -d
```

## Data Issues

### Index Corruption

#### Symptoms
- Search returns no results
- Index statistics show 0 documents
- Indexing errors

#### Diagnosis
```bash
# Check index status
curl http://localhost:7700/indexes/documents/stats

# List all indexes
curl http://localhost:7700/indexes

# Check index settings
curl http://localhost:7700/indexes/documents/settings
```

#### Solutions

**Recreate Index**
```bash
# Delete corrupted index
curl -X DELETE http://localhost:7700/indexes/documents

# Recreate with demo script
python scripts/setup_demo.py
```

**Restore from Backup**
```bash
# If you have backups
curl -X POST http://localhost:7700/snapshots/import \
  -H "Content-Type: application/json" \
  -d '{"snapshot_path": "/path/to/backup.snapshot"}'
```

### Document Processing Failures

#### Symptoms
- Documents not appearing in search
- Processing errors in logs
- Partial document indexing

#### Diagnosis
```bash
# Check processing logs
docker compose logs thai-tokenizer | grep "process"

# Test document processing
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "id": "test",
      "title": "ทดสอบ",
      "content": "เนื้อหาทดสอบ"
    }
  }'
```

#### Solutions

**Process Documents in Smaller Batches**
```bash
curl -X PUT http://localhost:8000/api/v1/config/processing \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 10,
    "max_concurrent": 2
  }'
```

**Validate Document Format**
```bash
# Ensure documents have required fields
{
  "id": "unique_id",
  "title": "Document Title",
  "content": "Document content..."
}
```

## Monitoring and Debugging

### Enable Debug Logging

```bash
# Set debug level
export LOG_LEVEL=DEBUG

# Restart with debug logging
docker compose down
docker compose up -d

# View debug logs
docker compose logs -f thai-tokenizer
```

### Performance Monitoring

```bash
# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}"

# Run performance benchmark
python scripts/benchmark.py

# Monitor MeiliSearch performance
curl http://localhost:7700/stats
```

### Health Monitoring

```bash
# Set up health check monitoring
#!/bin/bash
while true; do
  if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    echo "$(date): Thai tokenizer unhealthy"
    docker compose restart thai-tokenizer
  fi
  sleep 30
done
```

### Log Analysis

```bash
# Search for errors
docker compose logs thai-tokenizer | grep -i error

# Monitor request patterns
docker compose logs thai-tokenizer | grep "POST /api"

# Check response times
docker compose logs thai-tokenizer | grep "processing_time"
```

## Getting Help

### Collect Diagnostic Information

```bash
#!/bin/bash
# diagnostic_info.sh
echo "=== System Information ==="
uname -a
docker --version
docker compose version

echo "=== Service Status ==="
docker compose ps

echo "=== Service Health ==="
curl -s http://localhost:8000/health || echo "Thai tokenizer unhealthy"
curl -s http://localhost:7700/health || echo "MeiliSearch unhealthy"

echo "=== Resource Usage ==="
docker stats --no-stream

echo "=== Recent Logs ==="
docker compose logs --tail=50 thai-tokenizer
docker compose logs --tail=50 meilisearch

echo "=== Configuration ==="
curl -s http://localhost:8000/api/v1/config
```

### Common Support Information

When reporting issues, include:
1. System information (OS, Docker version)
2. Service logs (last 50 lines)
3. Configuration details
4. Steps to reproduce
5. Expected vs actual behavior
6. Error messages

### Community Resources

- GitHub Issues: Report bugs and feature requests
- Documentation: Check latest documentation
- Examples: Review sample implementations
- Performance: Run benchmark comparisons

This troubleshooting guide covers the most common issues. For complex problems, enable debug logging and collect diagnostic information before seeking support.