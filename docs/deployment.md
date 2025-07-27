# Deployment Guide

This guide covers deployment options for the Thai Tokenizer for MeiliSearch integration, from development setup to production deployment.

## Table of Contents

- [Quick Start](#quick-start)
- [Development Deployment](#development-deployment)
- [Production Deployment](#production-deployment)
- [Configuration](#configuration)
- [Monitoring](#monitoring)
- [Troubleshooting](#troubleshooting)

## Quick Start

### Prerequisites

- Docker and Docker Compose V2
- Python 3.12+ (for local development)
- 4GB RAM minimum, 8GB recommended
- 2 CPU cores minimum

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd thai-tokenizer-meilisearch

# Copy environment configuration
cp config/development/.env.example .env

# Edit configuration as needed
nano .env
```

### 2. Start Services

```bash
# Development mode (no nginx proxy)
docker compose up -d

# Production mode (with nginx proxy)
docker compose --profile production up -d
```

### 3. Verify Deployment

```bash
# Check service health
curl http://localhost:8000/health  # Thai tokenizer
curl http://localhost:7700/health  # MeiliSearch
curl http://localhost/health       # Nginx proxy (production only)

# Run demonstration
python deployment/scripts/run_demo.py
```

## Development Deployment

### Local Development Setup

#### Option 1: Docker Development (Recommended)

```bash
# Start development services
docker compose up -d

# Services available at:
# - Thai Tokenizer: http://localhost:8000
# - MeiliSearch: http://localhost:7700
# - API Documentation: http://localhost:8000/docs
```

**Features**:
- Hot reload enabled for code changes
- Debug logging
- Volume mounting for live code updates
- Direct service access (no proxy)

#### Option 2: Native Python Development

```bash
# Install dependencies
pip install -r requirements.txt

# Start MeiliSearch
docker run -d --name meilisearch \
  -p 7700:7700 \
  -e MEILI_MASTER_KEY=masterKey \
  getmeili/meilisearch:v1.15.2

# Start Thai tokenizer service
uvicorn src.api.main:app --reload --port 8000
```

### Development Configuration

```bash
# .env file for development
MEILISEARCH_HOST=http://localhost:7700
MEILISEARCH_API_KEY=masterKey
LOG_LEVEL=DEBUG
TOKENIZER_ENGINE=pythainlp
```

### Development Workflow

```bash
# 1. Make code changes
# 2. Services auto-reload (Docker) or restart manually
# 3. Test changes
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"}'

# 4. Run tests
pytest tests/ -v

# 5. Check code quality
ruff check src/ tests/
mypy src/
```

## Production Deployment

### Docker Compose Production

#### 1. Production Configuration

```bash
# config/production/.env.prod
MEILISEARCH_HOST=http://meilisearch:7700
MEILISEARCH_API_KEY=your-secure-api-key
MEILI_ENV=production
LOG_LEVEL=INFO
TOKENIZER_ENGINE=pythainlp
```

#### 2. Deploy with Nginx Proxy

```bash
# Start production services
docker compose --profile production up -d

# Services:
# - Nginx Proxy: http://localhost (port 80)
# - Thai Tokenizer: http://localhost:8000 (direct access)
# - MeiliSearch: http://localhost:7700 (direct access)
```

#### 3. Production Features

- **Nginx reverse proxy** with rate limiting
- **SSL termination** (configure certificates)
- **Load balancing** for multiple tokenizer instances
- **Health checks** and automatic restarts
- **Resource limits** and monitoring
- **Persistent data** with named volumes

### Kubernetes Deployment

#### 1. Create Namespace

```yaml
# namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: thai-tokenizer
```

#### 2. ConfigMap and Secrets

```yaml
# configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: thai-tokenizer-config
  namespace: thai-tokenizer
data:
  MEILISEARCH_HOST: "http://meilisearch:7700"
  LOG_LEVEL: "INFO"
  TOKENIZER_ENGINE: "pythainlp"

---
apiVersion: v1
kind: Secret
metadata:
  name: thai-tokenizer-secrets
  namespace: thai-tokenizer
type: Opaque
stringData:
  MEILISEARCH_API_KEY: "your-secure-api-key"
```

#### 3. MeiliSearch Deployment

```yaml
# meilisearch.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: meilisearch
  namespace: thai-tokenizer
spec:
  replicas: 1
  selector:
    matchLabels:
      app: meilisearch
  template:
    metadata:
      labels:
        app: meilisearch
    spec:
      containers:
      - name: meilisearch
        image: getmeili/meilisearch:v1.15.2
        ports:
        - containerPort: 7700
        env:
        - name: MEILI_MASTER_KEY
          valueFrom:
            secretKeyRef:
              name: thai-tokenizer-secrets
              key: MEILISEARCH_API_KEY
        - name: MEILI_ENV
          value: "production"
        volumeMounts:
        - name: data
          mountPath: /meili_data
        resources:
          requests:
            memory: "512Mi"
            cpu: "250m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
      volumes:
      - name: data
        persistentVolumeClaim:
          claimName: meilisearch-pvc

---
apiVersion: v1
kind: Service
metadata:
  name: meilisearch
  namespace: thai-tokenizer
spec:
  selector:
    app: meilisearch
  ports:
  - port: 7700
    targetPort: 7700

---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: meilisearch-pvc
  namespace: thai-tokenizer
spec:
  accessModes:
  - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
```

#### 4. Thai Tokenizer Deployment

```yaml
# thai-tokenizer.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: thai-tokenizer
  namespace: thai-tokenizer
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
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: thai-tokenizer-config
        - secretRef:
            name: thai-tokenizer-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"

---
apiVersion: v1
kind: Service
metadata:
  name: thai-tokenizer
  namespace: thai-tokenizer
spec:
  selector:
    app: thai-tokenizer
  ports:
  - port: 8000
    targetPort: 8000
```

#### 5. Ingress Configuration

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: thai-tokenizer-ingress
  namespace: thai-tokenizer
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
spec:
  rules:
  - host: thai-tokenizer.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: thai-tokenizer
            port:
              number: 8000
```

#### 6. Deploy to Kubernetes

```bash
# Apply configurations
kubectl apply -f namespace.yaml
kubectl apply -f configmap.yaml
kubectl apply -f meilisearch.yaml
kubectl apply -f thai-tokenizer.yaml
kubectl apply -f ingress.yaml

# Check deployment status
kubectl get pods -n thai-tokenizer
kubectl get services -n thai-tokenizer
```

### Cloud Deployment

#### AWS ECS Deployment

```json
{
  "family": "thai-tokenizer",
  "networkMode": "awsvpc",
  "requiresCompatibilities": ["FARGATE"],
  "cpu": "512",
  "memory": "1024",
  "executionRoleArn": "arn:aws:iam::account:role/ecsTaskExecutionRole",
  "containerDefinitions": [
    {
      "name": "thai-tokenizer",
      "image": "your-registry/thai-tokenizer:latest",
      "portMappings": [
        {
          "containerPort": 8000,
          "protocol": "tcp"
        }
      ],
      "environment": [
        {
          "name": "MEILISEARCH_HOST",
          "value": "http://meilisearch:7700"
        }
      ],
      "secrets": [
        {
          "name": "MEILISEARCH_API_KEY",
          "valueFrom": "arn:aws:secretsmanager:region:account:secret:thai-tokenizer/api-key"
        }
      ],
      "healthCheck": {
        "command": ["CMD-SHELL", "curl -f http://localhost:8000/health || exit 1"],
        "interval": 30,
        "timeout": 5,
        "retries": 3
      },
      "logConfiguration": {
        "logDriver": "awslogs",
        "options": {
          "awslogs-group": "/ecs/thai-tokenizer",
          "awslogs-region": "us-west-2",
          "awslogs-stream-prefix": "ecs"
        }
      }
    }
  ]
}
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MEILISEARCH_HOST` | `http://localhost:7700` | MeiliSearch server URL |
| `MEILISEARCH_API_KEY` | `masterKey` | MeiliSearch API key |
| `MEILISEARCH_INDEX` | `documents` | Default index name |
| `TOKENIZER_ENGINE` | `pythainlp` | Thai tokenization engine |
| `LOG_LEVEL` | `INFO` | Logging level |
| `BATCH_SIZE` | `100` | Document processing batch size |
| `MAX_RETRIES` | `3` | Maximum retry attempts |
| `TIMEOUT_MS` | `5000` | Request timeout in milliseconds |

### MeiliSearch Configuration

```bash
# Production MeiliSearch settings
MEILI_MASTER_KEY=your-secure-key
MEILI_ENV=production
MEILI_LOG_LEVEL=INFO
MEILI_MAX_INDEXING_MEMORY=2Gb
MEILI_MAX_INDEXING_THREADS=4
```

### Nginx Configuration

For custom nginx configuration, modify `docker/nginx.conf`:

```nginx
# Rate limiting
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=100r/s;

# SSL configuration (add your certificates)
server {
    listen 443 ssl http2;
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Your existing configuration
}
```

## Monitoring

### Health Checks

```bash
# Service health endpoints
curl http://localhost:8000/health
curl http://localhost:7700/health

# Detailed health information
curl http://localhost:8000/api/v1/config
```

### Metrics Collection

#### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'thai-tokenizer'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 15s
```

#### Grafana Dashboard

Key metrics to monitor:
- Request rate and response times
- Tokenization performance
- Memory and CPU usage
- Error rates
- MeiliSearch index statistics

### Logging

#### Structured Logging

```python
# Example log output
{
  "timestamp": "2024-07-24T10:30:00Z",
  "level": "INFO",
  "service": "thai-tokenizer",
  "message": "Document processed successfully",
  "document_id": "doc_123",
  "processing_time_ms": 45,
  "tokens_count": 156
}
```

#### Log Aggregation

```yaml
# docker-compose.yml logging configuration
services:
  thai-tokenizer:
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

## Troubleshooting

### Common Issues

#### Service Startup Problems

```bash
# Check container logs
docker compose logs thai-tokenizer
docker compose logs meilisearch

# Check service status
docker compose ps

# Restart services
docker compose restart thai-tokenizer
```

#### Connection Issues

```bash
# Test network connectivity
docker compose exec thai-tokenizer curl http://meilisearch:7700/health

# Check port bindings
netstat -tlnp | grep :8000
netstat -tlnp | grep :7700
```

#### Performance Issues

```bash
# Monitor resource usage
docker stats

# Check MeiliSearch index status
curl http://localhost:7700/indexes/documents/stats

# Run performance benchmark
python deployment/scripts/benchmark.py
```

#### Memory Issues

```bash
# Check memory usage
docker compose exec thai-tokenizer free -h

# Adjust memory limits in docker-compose.yml
services:
  thai-tokenizer:
    deploy:
      resources:
        limits:
          memory: 512M
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with debug output
docker compose up --no-daemon

# Access container for debugging
docker compose exec thai-tokenizer bash
```

### Recovery Procedures

#### Data Recovery

```bash
# Backup MeiliSearch data
docker compose exec meilisearch tar -czf /tmp/backup.tar.gz /meili_data

# Restore from backup
docker compose exec meilisearch tar -xzf /tmp/backup.tar.gz -C /
```

#### Service Recovery

```bash
# Full service restart
docker compose down
docker compose up -d

# Reset MeiliSearch index
curl -X DELETE http://localhost:7700/indexes/documents
python deployment/scripts/setup_demo.py
```

## Security Considerations

### API Security

- Change default API keys in production
- Use HTTPS in production environments
- Implement rate limiting
- Validate all input data
- Use secure headers

### Network Security

- Use private networks for service communication
- Implement firewall rules
- Use VPN for remote access
- Monitor network traffic

### Data Security

- Encrypt data at rest
- Use secure backup procedures
- Implement access controls
- Regular security updates

## Performance Optimization

### Scaling

```bash
# Scale tokenizer service
docker compose up -d --scale thai-tokenizer=3

# Use load balancer
# Configure nginx upstream with multiple backends
```

### Caching

- Enable result caching for frequent queries
- Use Redis for distributed caching
- Implement CDN for static content

### Database Optimization

- Tune MeiliSearch settings for your data
- Optimize index configuration
- Monitor and adjust resource allocation

## Backup and Disaster Recovery

### Backup Strategy

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
docker compose exec meilisearch tar -czf /tmp/backup_$DATE.tar.gz /meili_data
docker cp $(docker compose ps -q meilisearch):/tmp/backup_$DATE.tar.gz ./backups/
```

### Disaster Recovery

1. **Service Failure**: Automatic restart with health checks
2. **Data Corruption**: Restore from latest backup
3. **Complete System Failure**: Redeploy from infrastructure as code
4. **Regional Failure**: Failover to secondary region

This deployment guide provides comprehensive coverage for various deployment scenarios. Choose the approach that best fits your infrastructure and requirements.