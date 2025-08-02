# Thai Tokenizer with External Meilisearch Deployment

This directory contains Docker Compose configuration and deployment scripts for running the Thai Tokenizer service with an existing external Meilisearch instance.

## Overview

The external Meilisearch deployment is designed for scenarios where:
- You already have a running Meilisearch instance
- You want to add Thai tokenization capabilities without modifying your existing setup
- You need to integrate with enterprise Meilisearch deployments
- You want to minimize resource usage by not running a separate Meilisearch instance

## Quick Start

### 1. Configuration Setup

Copy the environment template and customize it for your setup:

```bash
cp .env.external-meilisearch.template .env.external-meilisearch
```

Edit `.env.external-meilisearch` with your Meilisearch configuration:

```bash
# Essential configuration
MEILISEARCH_HOST=http://your-meilisearch-server:7700
MEILISEARCH_API_KEY=your_api_key_here
MEILISEARCH_INDEX=documents
```

### 2. Validate Configuration

Test connectivity to your external Meilisearch:

```bash
./deploy-external-meilisearch.sh validate
```

### 3. Deploy the Service

Deploy the Thai Tokenizer service:

```bash
./deploy-external-meilisearch.sh deploy
```

### 4. Verify Deployment

Check service health and connectivity:

```bash
./deploy-external-meilisearch.sh health
```

## Configuration Options

### Core Meilisearch Settings

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `MEILISEARCH_HOST` | External Meilisearch URL | `http://host.docker.internal:7700` | Yes |
| `MEILISEARCH_API_KEY` | Meilisearch API key | - | Yes |
| `MEILISEARCH_INDEX` | Target index name | `documents` | No |
| `MEILISEARCH_SSL_VERIFY` | Verify SSL certificates | `true` | No |
| `MEILISEARCH_TIMEOUT_MS` | Connection timeout | `10000` | No |
| `MEILISEARCH_MAX_RETRIES` | Max retry attempts | `3` | No |

### Service Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `THAI_TOKENIZER_PORT` | Service port | `8000` |
| `SERVICE_NAME` | Service name | `thai-tokenizer-external` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `DEBUG` | Enable debug mode | `false` |

### Performance Tuning

| Variable | Description | Default |
|----------|-------------|---------|
| `BATCH_SIZE` | Processing batch size | `50` |
| `MAX_WORKERS` | Max worker threads | `4` |
| `WORKER_PROCESSES` | Worker processes | `4` |
| `TOKENIZER_CACHE_SIZE` | Cache size | `1000` |
| `CPU_LIMIT` | Docker CPU limit | `2.0` |
| `MEMORY_LIMIT` | Docker memory limit | `1G` |

### Security Settings

| Variable | Description | Default |
|----------|-------------|---------|
| `CORS_ORIGINS` | Allowed CORS origins | `*` |
| `ALLOWED_HOSTS` | Allowed host headers | `*` |
| `API_KEY_REQUIRED` | Require API key auth | `false` |
| `THAI_TOKENIZER_API_KEY` | Service API key | - |

## Deployment Methods

### Standard Deployment

Deploy only the Thai Tokenizer service:

```bash
./deploy-external-meilisearch.sh deploy
```

### With Nginx Proxy

Deploy with Nginx reverse proxy for production:

```bash
./deploy-external-meilisearch.sh deploy --profile proxy
```

### Development Mode

Deploy with debug settings:

```bash
# Edit .env.external-meilisearch
DEBUG=true
LOG_LEVEL=DEBUG

./deploy-external-meilisearch.sh deploy
```

## Network Configuration

### Docker Host Network Access

For Meilisearch running on the Docker host:

```bash
MEILISEARCH_HOST=http://host.docker.internal:7700
EXTERNAL_MEILISEARCH_NETWORK=bridge
```

### External Network Access

For Meilisearch on a different server:

```bash
MEILISEARCH_HOST=https://meilisearch.example.com
MEILISEARCH_SSL_VERIFY=true
```

### Custom Docker Network

To use a custom Docker network:

```bash
# Create the network first
docker network create meilisearch-network

# Configure the service
EXTERNAL_MEILISEARCH_NETWORK=meilisearch-network
```

## Health Checks and Monitoring

### Health Check Endpoints

The service provides comprehensive health checking:

- **Basic Health**: `GET /health`
  - Returns 200 if service is running
  
- **Detailed Health**: `GET /health/detailed`
  - Includes Meilisearch connectivity status
  - Thai tokenizer functionality status
  - Resource usage information

- **Metrics**: `GET /metrics`
  - Prometheus-compatible metrics
  - Performance statistics

### Health Check Configuration

Health checks validate:
1. Service responsiveness
2. External Meilisearch connectivity
3. Thai tokenization functionality
4. Resource availability

```yaml
healthcheck:
  test: |
    curl -f http://localhost:8000/health && \
    curl -f http://localhost:8000/health/detailed | grep -q '"meilisearch_status":"healthy"'
  interval: 30s
  timeout: 15s
  retries: 5
  start_period: 60s
```

## Management Commands

### Service Management

```bash
# Deploy the service
./deploy-external-meilisearch.sh deploy

# Start stopped service
./deploy-external-meilisearch.sh start

# Stop running service
./deploy-external-meilisearch.sh stop

# Restart service
./deploy-external-meilisearch.sh restart

# Check service status
./deploy-external-meilisearch.sh status
```

### Monitoring and Debugging

```bash
# View service logs
./deploy-external-meilisearch.sh logs

# Follow logs in real-time
./deploy-external-meilisearch.sh logs --follow

# Check service health
./deploy-external-meilisearch.sh health

# Validate configuration
./deploy-external-meilisearch.sh validate
```

### Maintenance

```bash
# Update to latest version
./deploy-external-meilisearch.sh update

# Clean up deployment
./deploy-external-meilisearch.sh cleanup

# Force cleanup without confirmation
./deploy-external-meilisearch.sh cleanup --force
```

## API Usage Examples

### Basic Tokenization

```bash
# Tokenize Thai text
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "สวัสดีครับ นี่คือการทดสอบ"}'
```

### Document Processing

```bash
# Process document for Meilisearch
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "1",
        "title": "ทดสอบเอกสาร",
        "content": "เนื้อหาเอกสารภาษาไทย"
      }
    ]
  }'
```

### Health Check

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health information
curl http://localhost:8000/health/detailed
```

## Troubleshooting

### Common Issues

#### 1. Cannot Connect to External Meilisearch

**Symptoms:**
- Health check fails with Meilisearch connectivity error
- Service logs show connection timeouts

**Solutions:**
```bash
# Verify Meilisearch is accessible
curl -f http://your-meilisearch-host:7700/health

# Check network connectivity from container
docker exec -it thai-tokenizer-container curl -f http://your-meilisearch-host:7700/health

# Verify API key
curl -H "Authorization: Bearer YOUR_API_KEY" http://your-meilisearch-host:7700/keys
```

#### 2. Service Fails to Start

**Symptoms:**
- Container exits immediately
- Health check never passes

**Solutions:**
```bash
# Check container logs
./deploy-external-meilisearch.sh logs

# Verify environment configuration
./deploy-external-meilisearch.sh validate

# Check resource limits
docker stats
```

#### 3. Slow Thai Tokenization

**Symptoms:**
- High response times
- Timeout errors

**Solutions:**
```bash
# Increase resource limits
CPU_LIMIT=4.0
MEMORY_LIMIT=2G

# Optimize batch processing
BATCH_SIZE=25
MAX_WORKERS=8

# Enable caching
TOKENIZER_CACHE_SIZE=2000
```

#### 4. Network Connectivity Issues

**Symptoms:**
- Cannot reach external Meilisearch
- DNS resolution failures

**Solutions:**
```bash
# Use IP address instead of hostname
MEILISEARCH_HOST=http://192.168.1.100:7700

# Use host network mode
docker run --network host ...

# Check Docker network configuration
docker network ls
docker network inspect bridge
```

### Debug Mode

Enable debug mode for detailed logging:

```bash
# Edit .env.external-meilisearch
DEBUG=true
LOG_LEVEL=DEBUG

# Redeploy with debug settings
./deploy-external-meilisearch.sh deploy
```

### Log Analysis

```bash
# View recent logs
./deploy-external-meilisearch.sh logs --tail 100

# Search for specific errors
./deploy-external-meilisearch.sh logs | grep -i error

# Monitor logs in real-time
./deploy-external-meilisearch.sh logs --follow
```

## Security Considerations

### Network Security

- Use HTTPS for external Meilisearch connections
- Configure firewall rules to restrict access
- Use VPN for remote Meilisearch access

### Authentication

- Always use strong API keys for Meilisearch
- Enable API key authentication for the Thai Tokenizer service
- Rotate API keys regularly

### Data Privacy

- Thai text content is not logged by default
- Use SSL/TLS for all external communications
- Consider data encryption at rest

## Performance Optimization

### Resource Allocation

```bash
# For high-throughput scenarios
CPU_LIMIT=4.0
MEMORY_LIMIT=2G
WORKER_PROCESSES=8
BATCH_SIZE=100

# For memory-constrained environments
CPU_LIMIT=1.0
MEMORY_LIMIT=512M
WORKER_PROCESSES=2
BATCH_SIZE=25
```

### Caching Configuration

```bash
# Enable aggressive caching
TOKENIZER_CACHE_SIZE=5000

# Disable caching for memory-constrained environments
TOKENIZER_CACHE_SIZE=0
```

### Network Optimization

```bash
# Reduce connection timeout for fast networks
MEILISEARCH_TIMEOUT_MS=5000

# Increase timeout for slow networks
MEILISEARCH_TIMEOUT_MS=30000

# Adjust retry settings
MEILISEARCH_MAX_RETRIES=5
```

## Integration Examples

### Docker Swarm

```yaml
version: '3.8'
services:
  thai-tokenizer:
    image: thai-tokenizer:latest
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
    environment:
      - MEILISEARCH_HOST=http://meilisearch.example.com:7700
      - MEILISEARCH_API_KEY=${MEILISEARCH_API_KEY}
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: thai-tokenizer
spec:
  replicas: 3
  selector:
    matchLabels:
      app: thai-tokenizer
  template:
    metadata:
      labels:
        app: thai-tokenizer
    spec:
      containers:
      - name: thai-tokenizer
        image: thai-tokenizer:latest
        env:
        - name: MEILISEARCH_HOST
          value: "http://meilisearch-service:7700"
        - name: MEILISEARCH_API_KEY
          valueFrom:
            secretKeyRef:
              name: meilisearch-secret
              key: api-key
```

### CI/CD Integration

```yaml
# GitHub Actions example
- name: Deploy Thai Tokenizer
  run: |
    cd deployment/docker
    ./deploy-external-meilisearch.sh validate
    ./deploy-external-meilisearch.sh deploy --detach
    ./deploy-external-meilisearch.sh health
```

## Support and Documentation

- **API Documentation**: Available at `/docs` when service is running
- **Health Monitoring**: Use `/health/detailed` for comprehensive status
- **Metrics**: Prometheus metrics available at `/metrics`
- **Logs**: Structured JSON logging for easy parsing

For additional support, check the main project documentation or create an issue in the project repository.