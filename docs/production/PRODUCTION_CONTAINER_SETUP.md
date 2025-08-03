# Thai Tokenizer Production Container Setup

This guide walks you through deploying the Thai Tokenizer as a container in your production environment with an existing Meilisearch container.

## Prerequisites

- Docker and Docker Compose installed
- Existing Meilisearch container running
- Network access between Thai Tokenizer and Meilisearch containers

## Quick Start

### Step 1: Configure Environment

1. **Edit the production environment file:**
   ```bash
   nano .env.production
   ```

2. **Update these key settings:**
   ```bash
   # Your Meilisearch container connection
   MEILISEARCH_HOST=http://meilisearch:7700  # Use your container name/network
   MEILISEARCH_API_KEY=your-actual-api-key
   MEILISEARCH_INDEX=your-index-name
   
   # Security settings
   CORS_ORIGINS=https://your-domain.com
   ALLOWED_HOSTS=your-domain.com
   API_KEY_REQUIRED=true
   THAI_TOKENIZER_API_KEY=your-secure-api-key
   
   # Network (your Meilisearch network name)
   EXTERNAL_MEILISEARCH_NETWORK=your-meilisearch-network
   ```

### Step 2: Deploy

```bash
# Deploy Thai Tokenizer
./deploy-production.sh

# Or deploy step by step:
./deploy-production.sh deploy
```

### Step 3: Verify

```bash
# Check service status
./deploy-production.sh status

# Check health
./deploy-production.sh health

# View logs
./deploy-production.sh logs
```

## Configuration Details

### Meilisearch Connection Options

**Option 1: Same Docker Network**
```bash
MEILISEARCH_HOST=http://meilisearch:7700
EXTERNAL_MEILISEARCH_NETWORK=your-meilisearch-network
```

**Option 2: Different Host/Network**
```bash
MEILISEARCH_HOST=http://your-meilisearch-host:7700
EXTERNAL_MEILISEARCH_NETWORK=bridge
```

**Option 3: Host Network**
```bash
MEILISEARCH_HOST=http://host.docker.internal:7700
EXTERNAL_MEILISEARCH_NETWORK=bridge
```

### Security Configuration

For production, always configure:

```bash
# Restrict CORS origins
CORS_ORIGINS=https://your-app.com,https://your-admin.com

# Restrict allowed hosts
ALLOWED_HOSTS=thai-tokenizer.your-domain.com

# Enable API key authentication
API_KEY_REQUIRED=true
THAI_TOKENIZER_API_KEY=your-very-secure-random-key
```

### Performance Tuning

Adjust based on your server resources:

```bash
# CPU and memory limits
CPU_LIMIT=2.0
MEMORY_LIMIT=1G

# Worker processes (typically = CPU cores)
WORKER_PROCESSES=4

# Batch processing size
BATCH_SIZE=50
```

## Service Management

### Common Commands

```bash
# Deploy/Update
./deploy-production.sh deploy

# Stop service
./deploy-production.sh stop

# Restart service
./deploy-production.sh restart

# View logs
./deploy-production.sh logs

# Check status
./deploy-production.sh status

# Health check
./deploy-production.sh health
```

### Manual Docker Commands

```bash
# View running containers
docker ps | grep thai-tokenizer

# View logs
docker logs thai_tokenizer_prod-thai-tokenizer-1 -f

# Execute commands in container
docker exec -it thai_tokenizer_prod-thai-tokenizer-1 bash

# Stop and remove
docker-compose -f deployment/docker/docker-compose.external-meilisearch.yml --env-file .env.production down
```

## API Usage

Once deployed, the Thai Tokenizer will be available at:

- **Service URL**: `http://localhost:8000` (or your configured port)
- **Health Check**: `http://localhost:8000/health`
- **API Documentation**: `http://localhost:8000/docs`
- **Detailed Health**: `http://localhost:8000/health/detailed`

### Example API Calls

```bash
# Health check
curl http://localhost:8000/health

# Tokenize Thai text
curl -X POST "http://localhost:8000/tokenize" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"text": "สวัสดีครับ นี่คือการทดสอบ"}'

# Process document for Meilisearch
curl -X POST "http://localhost:8000/process-document" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"content": "เนื้อหาภาษาไทยที่ต้องการประมวลผล", "title": "หัวข้อเอกสาร"}'
```

## Monitoring and Logs

### Log Locations

- **Application logs**: `./logs/thai-tokenizer/`
- **Container logs**: `docker logs thai_tokenizer_prod-thai-tokenizer-1`
- **Nginx logs** (if using proxy): `./logs/nginx/`

### Health Monitoring

The service includes comprehensive health checks:

```bash
# Basic health
curl http://localhost:8000/health

# Detailed health (includes Meilisearch status)
curl http://localhost:8000/health/detailed
```

### Metrics

If Prometheus monitoring is enabled:

- **Metrics endpoint**: `http://localhost:8000/metrics`
- **Grafana dashboards**: Available in `monitoring/grafana/`

## Troubleshooting

### Common Issues

1. **Cannot connect to Meilisearch**
   - Check network configuration
   - Verify Meilisearch container is running
   - Test connectivity: `docker exec thai_tokenizer_prod-thai-tokenizer-1 curl http://meilisearch:7700/health`

2. **Service won't start**
   - Check logs: `./deploy-production.sh logs`
   - Verify environment configuration
   - Check resource limits

3. **Performance issues**
   - Adjust `WORKER_PROCESSES` and `BATCH_SIZE`
   - Increase memory limits
   - Monitor resource usage

### Getting Help

1. **Check service logs**:
   ```bash
   ./deploy-production.sh logs
   ```

2. **Check detailed health**:
   ```bash
   curl http://localhost:8000/health/detailed
   ```

3. **Verify configuration**:
   ```bash
   docker exec thai_tokenizer_prod-thai-tokenizer-1 env | grep THAI_TOKENIZER
   ```

## Security Best Practices

1. **Use strong API keys**
2. **Restrict CORS origins and allowed hosts**
3. **Use HTTPS in production (configure reverse proxy)**
4. **Regularly update container images**
5. **Monitor access logs**
6. **Use Docker secrets for sensitive data**

## Updates and Maintenance

### Updating the Service

```bash
# Pull latest changes
git pull

# Rebuild and redeploy
./deploy-production.sh deploy
```

### Backup and Recovery

```bash
# Backup configuration
cp .env.production .env.production.backup

# Backup logs
tar -czf logs-backup-$(date +%Y%m%d).tar.gz logs/
```

This setup provides a production-ready Thai Tokenizer that integrates seamlessly with your existing Meilisearch container infrastructure.