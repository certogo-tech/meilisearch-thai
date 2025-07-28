# Thai Tokenizer - Local Production Setup Guide

This guide will help you set up the Thai Tokenizer project from scratch for local production use with containers.

## Prerequisites

Before starting, ensure you have the following installed on your system:

- **Docker** (version 20.10+)
- **Docker Compose** (version 2.0+)
- **Git**
- **curl** (for testing)

### Verify Prerequisites

```bash
# Check Docker
docker --version
docker compose version

# Check Git
git --version

# Check curl
curl --version
```

## Step 1: Clone the Repository

```bash
# Clone the repository
git clone <your-repository-url>
cd thai-tokenizer-meilisearch

# Switch to the restructured branch (if needed)
git checkout feature/project-restructure
```

## Step 2: Set Up Production Environment Configuration

### Create Production Environment File

```bash
# Create production environment file
cp config/production/.env.template config/production/.env.prod

# Edit the production configuration
nano config/production/.env.prod
```

### Configure Environment Variables

Edit `config/production/.env.prod` with your production settings:

```bash
# MeiliSearch Configuration
MEILISEARCH_API_KEY=your-secure-api-key-here
MEILISEARCH_INDEX=documents
MEILI_LOG_LEVEL=WARN
MEILI_MAX_INDEXING_MEMORY=2Gb
MEILI_MAX_INDEXING_THREADS=4

# Thai Tokenizer Configuration
TOKENIZER_ENGINE=pythainlp
TOKENIZER_MODEL=attacut
BATCH_SIZE=50
MAX_RETRIES=5
TIMEOUT_MS=10000
LOG_LEVEL=INFO
VERSION=1.0.0

# Performance Settings
WORKER_PROCESSES=8
TOKENIZER_CACHE_SIZE=2000

# Security Settings
CORS_ORIGINS=http://localhost,https://yourdomain.com
DEBUG=false

# Monitoring (optional)
GRAFANA_PASSWORD=your-secure-grafana-password
```

### Generate Secure API Key

```bash
# Generate a secure MeiliSearch API key
openssl rand -base64 32
```

Copy this key and use it as your `MEILISEARCH_API_KEY` in the environment file.

## Step 3: Create Required Directories

```bash
# Create log directories
mkdir -p logs/thai-tokenizer
mkdir -p logs/meilisearch
mkdir -p logs/nginx

# Create SSL directory (for HTTPS if needed)
mkdir -p ssl

# Set proper permissions
chmod 755 logs/thai-tokenizer logs/meilisearch logs/nginx
```

## Step 4: Build and Start Production Services

### Option A: Basic Production Setup (Recommended for Local)

```bash
# Build and start core services
docker compose -f deployment/docker/docker-compose.prod.yml up -d thai-tokenizer meilisearch

# Check service status
docker compose -f deployment/docker/docker-compose.prod.yml ps

# View logs
docker compose -f deployment/docker/docker-compose.prod.yml logs -f
```

### Option B: Full Production Setup with Nginx and Monitoring

```bash
# Start all services including nginx proxy and monitoring
docker compose -f deployment/docker/docker-compose.prod.yml --profile monitoring up -d

# Check all services
docker compose -f deployment/docker/docker-compose.prod.yml ps
```

## Step 5: Verify Installation

### Check Service Health

```bash
# Check Thai Tokenizer health
curl http://localhost:8000/health

# Check MeiliSearch health  
curl http://localhost:7700/health

# If using nginx proxy
curl http://localhost/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "thai-tokenizer",
  "version": "1.0.0",
  "timestamp": "2025-01-28T10:00:00Z"
}
```

### Test Tokenization

```bash
# Test basic tokenization
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"}'
```

Expected response:
```json
{
  "tokens": ["ปัญญาประดิษฐ์", "และ", "การเรียนรู้", "ของ", "เครื่อง"],
  "token_count": 5,
  "processing_time_ms": 23
}
```

## Step 6: Load Sample Data (Optional)

```bash
# Run the demo setup script to load sample Thai documents
docker compose -f deployment/docker/docker-compose.prod.yml exec thai-tokenizer python deployment/scripts/setup_demo.py

# Or run it from your host machine if you have Python installed
python deployment/scripts/setup_demo.py
```

## Step 7: Access Services

### Core Services
- **Thai Tokenizer API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **MeiliSearch**: http://localhost:7700
- **Nginx Proxy** (if enabled): http://localhost

### Monitoring (if enabled)
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000 (admin/your-grafana-password)

## Step 8: Performance Testing

### Run Benchmarks

```bash
# Run performance benchmarks
python deployment/scripts/benchmark.py

# View benchmark results
cat reports/performance/benchmark_report.json
```

### Load Testing

```bash
# Run load tests
docker compose -f deployment/docker/docker-compose.prod.yml exec thai-tokenizer python tests/performance/load_test.py
```

## Management Commands

### Service Management

```bash
# Stop all services
docker compose -f deployment/docker/docker-compose.prod.yml down

# Restart specific service
docker compose -f deployment/docker/docker-compose.prod.yml restart thai-tokenizer

# View service logs
docker compose -f deployment/docker/docker-compose.prod.yml logs -f thai-tokenizer

# Scale services (if needed)
docker compose -f deployment/docker/docker-compose.prod.yml up -d --scale thai-tokenizer=3
```

### Data Management

```bash
# Backup MeiliSearch data
docker compose -f deployment/docker/docker-compose.prod.yml exec meilisearch curl -X POST http://localhost:7700/snapshots

# View MeiliSearch indexes
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:7700/indexes

# Reset MeiliSearch data (WARNING: deletes all data)
docker compose -f deployment/docker/docker-compose.prod.yml down -v
```

### Monitoring

```bash
# Check resource usage
docker stats

# View container health
docker compose -f deployment/docker/docker-compose.prod.yml ps

# Check logs for errors
docker compose -f deployment/docker/docker-compose.prod.yml logs thai-tokenizer | grep ERROR
```

## Troubleshooting

### Common Issues

1. **Services won't start**
   ```bash
   # Check Docker daemon
   sudo systemctl status docker
   
   # Check port conflicts
   sudo netstat -tulpn | grep :8000
   ```

2. **MeiliSearch connection errors**
   ```bash
   # Verify API key
   curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:7700/health
   
   # Check MeiliSearch logs
   docker compose -f deployment/docker/docker-compose.prod.yml logs meilisearch
   ```

3. **Thai tokenization not working**
   ```bash
   # Check PyThaiNLP installation
   docker compose -f deployment/docker/docker-compose.prod.yml exec thai-tokenizer python -c "import pythainlp; print('OK')"
   
   # Check tokenizer logs
   docker compose -f deployment/docker/docker-compose.prod.yml logs thai-tokenizer
   ```

4. **Performance issues**
   ```bash
   # Check resource limits
   docker stats
   
   # Increase memory limits in docker-compose.prod.yml
   # Adjust worker processes in environment variables
   ```

### Log Locations

- **Thai Tokenizer**: `logs/thai-tokenizer/`
- **MeiliSearch**: `logs/meilisearch/`
- **Nginx**: `logs/nginx/`
- **Container logs**: `docker compose logs <service-name>`

## Security Considerations

1. **Change default passwords**: Update `MEILISEARCH_API_KEY` and `GRAFANA_PASSWORD`
2. **Use HTTPS**: Configure SSL certificates in the `ssl/` directory
3. **Firewall**: Restrict access to necessary ports only
4. **Updates**: Regularly update Docker images and dependencies
5. **Monitoring**: Enable monitoring to detect issues early

## Performance Optimization

### For High Load

1. **Scale services**:
   ```bash
   docker compose -f deployment/docker/docker-compose.prod.yml up -d --scale thai-tokenizer=4
   ```

2. **Increase resources** in `docker-compose.prod.yml`:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '8.0'
         memory: 4G
   ```

3. **Tune MeiliSearch**:
   ```bash
   MEILI_MAX_INDEXING_MEMORY=4Gb
   MEILI_MAX_INDEXING_THREADS=8
   ```

## Next Steps

1. **Set up monitoring**: Enable Grafana dashboards for production monitoring
2. **Configure backups**: Set up automated MeiliSearch snapshots
3. **SSL/HTTPS**: Configure SSL certificates for secure access
4. **CI/CD**: Set up automated deployment pipeline
5. **Load balancing**: Configure load balancer for multiple instances

## Support

- **Documentation**: Check `docs/` directory for detailed guides
- **Issues**: Report problems on GitHub Issues
- **Performance**: Run benchmarks with `python deployment/scripts/benchmark.py`
- **Logs**: Check service logs for troubleshooting

Your Thai Tokenizer production environment is now ready! 🚀