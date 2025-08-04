# Thai Search Proxy Deployment Troubleshooting Guide

This guide helps diagnose and resolve common deployment issues.

## Table of Contents
- [Common Issues](#common-issues)
- [Diagnostic Commands](#diagnostic-commands)
- [Service-Specific Issues](#service-specific-issues)
- [Performance Issues](#performance-issues)
- [Security Issues](#security-issues)
- [Recovery Procedures](#recovery-procedures)

## Common Issues

### 1. Service Won't Start

#### Symptom
```
thai_search_proxy exited with code 1
```

#### Diagnosis
```bash
# Check logs
docker logs thai_search_proxy

# Common errors:
# - "Address already in use"
# - "Permission denied"
# - "Module not found"
```

#### Solutions

**Port Already in Use:**
```bash
# Find process using port 8000
sudo lsof -i :8000

# Kill the process
sudo kill -9 <PID>

# Or change port in .env
SEARCH_PROXY_PORT=8001
```

**Permission Issues:**
```bash
# Fix directory permissions
sudo chown -R 1000:1000 ./data
sudo chmod -R 755 ./data

# Rebuild with correct permissions
docker-compose build --no-cache
```

**Module Not Found:**
```bash
# Rebuild image
docker-compose build --no-cache

# Verify requirements.txt
docker run --rm thai-search-proxy pip list
```

### 2. MeiliSearch Connection Failed

#### Symptom
```
Failed to connect to MeiliSearch at http://localhost:7700
```

#### Diagnosis
```bash
# Test MeiliSearch connectivity
curl http://localhost:7700/health

# From inside container
docker exec thai_search_proxy curl http://172.17.0.1:7700/health
```

#### Solutions

**Wrong Host Configuration:**
```bash
# Update .env
MEILISEARCH_HOST=http://172.17.0.1:7700  # Docker bridge IP

# Or use host networking
docker run --network host ...
```

**MeiliSearch Not Running:**
```bash
# Check MeiliSearch status
docker ps | grep meilisearch

# Start MeiliSearch
docker-compose -f docker-compose.meilisearch.yml up -d
```

**Firewall Blocking:**
```bash
# Allow MeiliSearch port
sudo ufw allow 7700/tcp

# Or for iptables
sudo iptables -A INPUT -p tcp --dport 7700 -j ACCEPT
```

### 3. API Key Authentication Failed

#### Symptom
```
401 Unauthorized: Invalid API key
```

#### Solutions

**Missing API Key Header:**
```bash
# Test with API key
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"query": "test", "index_name": "research"}'
```

**Wrong API Key:**
```bash
# Verify API key in .env
grep SEARCH_PROXY_API_KEY .env

# Restart service after changing
docker-compose restart thai-search-proxy
```

### 4. Custom Dictionary Not Loading

#### Symptom
```
Custom dictionary not found at /app/data/dictionaries/thai_compounds.json
```

#### Solutions

**Missing Volume Mount:**
```yaml
# docker-compose.yml
volumes:
  - ./data/dictionaries:/app/data/dictionaries:ro
```

**File Path Issues:**
```bash
# Verify file exists
ls -la data/dictionaries/thai_compounds.json

# Check inside container
docker exec thai_search_proxy ls -la /app/data/dictionaries/
```

**JSON Format Error:**
```bash
# Validate JSON
python -m json.tool data/dictionaries/thai_compounds.json

# Common issues:
# - Missing quotes
# - Trailing commas
# - Invalid UTF-8 encoding
```

## Diagnostic Commands

### Health Checks

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check
curl http://localhost:8000/api/v1/health/detailed | jq

# Component status
curl http://localhost:8000/api/v1/health/detailed | jq '.components'
```

### Log Analysis

```bash
# View all logs
docker logs thai_search_proxy

# Follow logs
docker logs -f thai_search_proxy

# Last 100 lines
docker logs --tail 100 thai_search_proxy

# Filter errors
docker logs thai_search_proxy 2>&1 | grep ERROR

# Save logs for analysis
docker logs thai_search_proxy > search_proxy_logs.txt 2>&1
```

### Container Inspection

```bash
# Inspect container
docker inspect thai_search_proxy

# Check environment variables
docker exec thai_search_proxy env | sort

# Check file system
docker exec thai_search_proxy ls -la /app/

# Check running processes
docker exec thai_search_proxy ps aux
```

### Network Diagnostics

```bash
# Check port bindings
docker port thai_search_proxy

# Test internal connectivity
docker exec thai_search_proxy ping -c 3 172.17.0.1

# Check DNS resolution
docker exec thai_search_proxy nslookup meilisearch

# List network interfaces
docker exec thai_search_proxy ip addr
```

## Service-Specific Issues

### 1. Tokenizer Errors

#### AttaCut/DeepCut Not Working
```bash
# Error: "Tokenizer 'attacut' failed"

# Solution 1: Reinstall dependencies
docker exec thai_search_proxy pip install --force-reinstall attacut

# Solution 2: Use fallback tokenizer
THAI_TOKENIZER_FALLBACK_ENGINE=newmm
```

#### Memory Issues with Large Models
```bash
# Increase container memory
docker update --memory="2g" thai_search_proxy

# Or in docker-compose.yml
deploy:
  resources:
    limits:
      memory: 2g
```

### 2. Search Performance Issues

#### Slow Response Times
```bash
# Check metrics
curl http://localhost:8000/api/v1/metrics/summary | jq '.search_metrics'

# Enable query caching
SEARCH_PROXY_ENABLE_CACHE=true
SEARCH_PROXY_CACHE_TTL=3600

# Increase MeiliSearch timeout
MEILISEARCH_TIMEOUT_MS=10000
```

#### High Memory Usage
```bash
# Monitor memory
docker stats thai_search_proxy

# Limit concurrent searches
SEARCH_PROXY_MAX_CONCURRENT_SEARCHES=10

# Reduce result limit
SEARCH_PROXY_MAX_RESULTS_LIMIT=50
```

### 3. Result Quality Issues

#### No Results Returned
```bash
# Check if index exists
curl http://localhost:7700/indexes | jq

# Verify tokenization
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "สาหร่ายวากาเมะ"}'

# Test with debug mode
SEARCH_PROXY_INCLUDE_DEBUG_INFO=true
```

#### Poor Ranking
```bash
# Adjust ranking parameters
SEARCH_PROXY_BOOST_EXACT_MATCHES=2.0
SEARCH_PROXY_BOOST_TOKENIZED_MATCHES=1.5

# Check ranking scores
curl -X POST http://localhost:8000/api/v1/search \
  -d '{"query": "test", "index_name": "research", "include_ranking_info": true}'
```

## Performance Issues

### 1. High CPU Usage

```bash
# Profile CPU usage
docker exec thai_search_proxy py-spy top --pid 1

# Common causes:
# - Too many concurrent requests
# - Inefficient tokenization
# - No caching enabled
```

**Solutions:**
```bash
# Enable caching
SEARCH_PROXY_ENABLE_CACHE=true

# Limit workers
GUNICORN_WORKERS=2

# Use lighter tokenizer
THAI_TOKENIZER_DEFAULT_ENGINE=newmm
```

### 2. Memory Leaks

```bash
# Monitor memory over time
while true; do
  docker stats --no-stream thai_search_proxy | grep thai_search_proxy
  sleep 60
done

# Force garbage collection
docker exec thai_search_proxy python -c "import gc; gc.collect()"
```

**Solutions:**
```bash
# Restart workers periodically
GUNICORN_MAX_REQUESTS=1000
GUNICORN_MAX_REQUESTS_JITTER=100

# Limit memory per worker
GUNICORN_WORKER_MEMORY_LIMIT=512
```

### 3. Slow Startup

```bash
# Time startup
time docker-compose up -d

# Check initialization logs
docker logs thai_search_proxy | grep -E "(Loading|Initializing|Ready)"
```

**Solutions:**
```bash
# Pre-download models
docker run --rm -v $(pwd)/models:/models thai-search-proxy \
  python -c "import pythainlp; pythainlp.download('newmm')"

# Use smaller dictionary
CUSTOM_DICTIONARY_PATH=/app/data/dictionaries/minimal.json
```

## Security Issues

### 1. Exposed Services

```bash
# Check exposed ports
netstat -tlnp | grep -E "(8000|7700)"

# Scan for vulnerabilities
nmap -sV localhost -p 8000,7700
```

**Solutions:**
```bash
# Bind to localhost only
SEARCH_PROXY_HOST=127.0.0.1

# Use firewall
sudo ufw deny 8000/tcp
sudo ufw allow from 10.0.0.0/8 to any port 8000
```

### 2. API Key Compromise

```bash
# Rotate API keys
# 1. Generate new key
openssl rand -hex 32

# 2. Update .env
SEARCH_PROXY_API_KEY=new_key_here

# 3. Restart service
docker-compose restart thai-search-proxy

# 4. Update all clients
```

### 3. Log Exposure

```bash
# Check for sensitive data in logs
docker logs thai_search_proxy | grep -E "(api_key|password|token)"

# Sanitize logs
LOG_LEVEL=INFO
SEARCH_PROXY_SANITIZE_LOGS=true
```

## Recovery Procedures

### 1. Service Recovery

```bash
#!/bin/bash
# recovery.sh

echo "Starting Thai Search Proxy recovery..."

# Stop all services
docker-compose down

# Clean up
docker system prune -f
rm -rf /tmp/thai-search-proxy*

# Verify MeiliSearch
if ! curl -s http://localhost:7700/health > /dev/null; then
    echo "ERROR: MeiliSearch is not responding"
    exit 1
fi

# Rebuild and start
docker-compose build --no-cache
docker-compose up -d

# Wait for health
for i in {1..30}; do
    if curl -s http://localhost:8000/health | grep -q "healthy"; then
        echo "Service recovered successfully!"
        exit 0
    fi
    echo "Waiting for service to start... ($i/30)"
    sleep 2
done

echo "ERROR: Service failed to start"
exit 1
```

### 2. Data Recovery

```bash
# Backup current state
docker exec thai_search_proxy tar -czf /tmp/backup.tar.gz \
  /app/data /var/log/search-proxy

# Copy backup out
docker cp thai_search_proxy:/tmp/backup.tar.gz ./backup-$(date +%Y%m%d).tar.gz

# Restore from backup
docker cp ./backup-20240101.tar.gz thai_search_proxy:/tmp/
docker exec thai_search_proxy tar -xzf /tmp/backup-20240101.tar.gz -C /
```

### 3. Emergency Rollback

```bash
#!/bin/bash
# rollback.sh

# Tag current version
docker tag thai-search-proxy:latest thai-search-proxy:rollback

# Pull previous version
docker pull ghcr.io/your-org/thai-search-proxy:v1.0.0

# Stop and replace
docker-compose stop thai-search-proxy
docker tag ghcr.io/your-org/thai-search-proxy:v1.0.0 thai-search-proxy:latest
docker-compose up -d thai-search-proxy

# Verify rollback
curl http://localhost:8000/health
```

## Monitoring Commands

### Real-time Monitoring

```bash
#!/bin/bash
# monitor.sh

while true; do
    clear
    echo "=== Thai Search Proxy Monitor ==="
    echo "Time: $(date)"
    echo ""
    
    # Health status
    echo "Health Check:"
    curl -s http://localhost:8000/health | jq -r '.status'
    echo ""
    
    # Container stats
    echo "Container Stats:"
    docker stats --no-stream thai_search_proxy | tail -n 1
    echo ""
    
    # Recent errors
    echo "Recent Errors:"
    docker logs --tail 5 thai_search_proxy 2>&1 | grep ERROR || echo "No errors"
    echo ""
    
    # Active connections
    echo "Active Connections:"
    docker exec thai_search_proxy netstat -an | grep :8000 | grep ESTABLISHED | wc -l
    
    sleep 5
done
```

### Performance Baseline

```bash
# Establish baseline performance
for i in {1..100}; do
    time curl -s -X POST http://localhost:8000/api/v1/search \
      -H "Content-Type: application/json" \
      -d '{"query": "ทดสอบ", "index_name": "research"}' > /dev/null
done 2>&1 | grep real | awk '{print $2}' | \
  awk -F'm|s' '{print ($1*60)+$2}' | \
  awk '{sum+=$1; count++} END {print "Average:", sum/count, "seconds"}'
```

## Quick Reference

### Essential Commands
```bash
# Restart service
docker-compose restart thai-search-proxy

# View logs
docker logs -f thai_search_proxy

# Check health
curl http://localhost:8000/health

# Test search
curl -X POST http://localhost:8000/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "test", "index_name": "research"}'

# Get metrics
curl http://localhost:8000/api/v1/metrics/summary | jq

# Rebuild service
docker-compose build --no-cache thai-search-proxy
docker-compose up -d thai-search-proxy
```

### Emergency Contacts

- **DevOps Team**: devops@cads.arda.or.th
- **On-call Engineer**: +66-XXX-XXXX
- **Escalation**: manager@cads.arda.or.th

### Useful Links

- [Service Documentation](./SEARCH-PROXY-API.md)
- [Deployment Guide](./deployment/nginx-proxy-manager/PRODUCTION-SETUP.md)
- [MeiliSearch Docs](https://docs.meilisearch.com)
- [Docker Troubleshooting](https://docs.docker.com/config/daemon/troubleshoot/)