# Docker Deployment Scripts and Utilities

This directory contains comprehensive Docker deployment scripts and utilities for the Thai Tokenizer service, designed to integrate with existing on-premise Meilisearch infrastructure.

## Overview

The Docker deployment system provides:

- **Comprehensive pre-deployment validation**
- **Resource-optimized container configuration**
- **Advanced health monitoring and alerting**
- **Automated backup and recovery procedures**
- **Performance monitoring and metrics collection**
- **Security-hardened deployment options**

## Requirements

- Docker 20.10+ with Docker Compose V2
- Python 3.8+ (for enhanced features)
- curl (for health checks)
- At least 512MB RAM and 2GB disk space
- Access to existing Meilisearch server

## Quick Start

1. **Copy and configure environment file:**
   ```bash
   cp .env.external-meilisearch.template .env.external-meilisearch
   # Edit .env.external-meilisearch with your Meilisearch configuration
   ```

2. **Validate configuration:**
   ```bash
   ./deploy-external-meilisearch.sh validate
   ```

3. **Deploy the service:**
   ```bash
   ./deploy-external-meilisearch.sh deploy
   ```

4. **Check service health:**
   ```bash
   ./deploy-external-meilisearch.sh health
   ```

## Core Components

### 1. Enhanced Deployment Script (`deploy-external-meilisearch.sh`)

Main deployment script with comprehensive features:

```bash
# Basic deployment
./deploy-external-meilisearch.sh deploy

# Deploy with Nginx proxy
./deploy-external-meilisearch.sh deploy --profile proxy

# Deploy without building images
./deploy-external-meilisearch.sh deploy --no-build

# Validate configuration
./deploy-external-meilisearch.sh validate

# Check service health
./deploy-external-meilisearch.sh health

# View service logs
./deploy-external-meilisearch.sh logs --follow

# Create backup
./deploy-external-meilisearch.sh backup

# Restore from backup
./deploy-external-meilisearch.sh restore --backup-id BACKUP_ID

# Start health monitoring
./deploy-external-meilisearch.sh monitor
```

### 2. Deployment Manager (`docker-deployment-manager.py`)

Python-based deployment manager with advanced validation:

```bash
# Comprehensive validation
python3 docker-deployment-manager.py validate

# Enhanced deployment
python3 docker-deployment-manager.py deploy --profile proxy

# Detailed health check
python3 docker-deployment-manager.py health

# Service management
python3 docker-deployment-manager.py stop
python3 docker-deployment-manager.py restart
```

**Features:**
- Pre-deployment system validation
- Docker daemon health checks
- Meilisearch connectivity testing
- Resource availability verification
- Network configuration validation
- Comprehensive error reporting

### 3. Health Monitor (`docker-health-monitor.py`)

Advanced health monitoring and metrics collection:

```bash
# Single health check
python3 docker-health-monitor.py health

# Collect performance metrics
python3 docker-health-monitor.py metrics

# Generate comprehensive report
python3 docker-health-monitor.py report --output health-report.json

# Export Prometheus metrics
python3 docker-health-monitor.py prometheus --output metrics.txt

# Continuous monitoring
python3 docker-health-monitor.py monitor --interval 30
```

**Monitored Components:**
- Docker daemon status
- Container health and resource usage
- Thai Tokenizer API functionality
- Meilisearch connectivity
- System resource utilization
- Network connectivity
- Storage and volume health

### 4. Backup and Recovery Manager (`docker-backup-recovery.py`)

Comprehensive backup and recovery system:

```bash
# Create full backup
python3 docker-backup-recovery.py backup --include-volumes --include-logs

# Create backup with images
python3 docker-backup-recovery.py backup --include-images

# List available backups
python3 docker-backup-recovery.py list

# Restore from backup
python3 docker-backup-recovery.py restore --backup-id BACKUP_ID

# Restore with specific components
python3 docker-backup-recovery.py restore --backup-id BACKUP_ID --restore-volumes --restore-configuration

# Delete old backup
python3 docker-backup-recovery.py delete --backup-id BACKUP_ID
```

**Backup Components:**
- Configuration files (.env, docker-compose.yml, nginx.conf)
- Docker volumes (logs, PyThaiNLP data)
- Docker images (optional)
- Service logs and container logs
- Service state and metadata

## Configuration Files

### Environment Configuration (`.env.external-meilisearch`)

Key configuration variables:

```bash
# Meilisearch connection
MEILISEARCH_HOST=http://your-meilisearch-server:7700
MEILISEARCH_API_KEY=your_api_key_here
MEILISEARCH_INDEX=documents

# Service configuration
THAI_TOKENIZER_PORT=8000
LOG_LEVEL=INFO
WORKER_PROCESSES=4

# Resource limits
CPU_LIMIT=2.0
MEMORY_LIMIT=1G
CPU_RESERVATION=0.5
MEMORY_RESERVATION=256M

# Security settings
CORS_ORIGINS=*
API_KEY_REQUIRED=false
```

### Resource Limits (`docker-resource-limits.yml`)

Predefined resource configurations for different scenarios:

- **Production**: Balanced performance and stability
- **Development**: Relaxed limits for development
- **High-Performance**: Maximum resources for heavy workloads
- **Low-Resource**: Minimal resources for constrained environments
- **Security-Hardened**: Enhanced security with resource constraints

### Docker Compose Configuration

Main deployment file: `docker-compose.external-meilisearch.yml`

Features:
- External Meilisearch integration
- Resource limits and health checks
- Volume management for persistence
- Network configuration for security
- Optional Nginx reverse proxy
- Comprehensive logging configuration

## Deployment Scenarios

### 1. Basic Production Deployment

```bash
# Configure environment
cp .env.external-meilisearch.template .env.external-meilisearch
# Edit MEILISEARCH_HOST and MEILISEARCH_API_KEY

# Validate and deploy
./deploy-external-meilisearch.sh validate
./deploy-external-meilisearch.sh deploy

# Verify deployment
./deploy-external-meilisearch.sh health
```

### 2. High-Availability Deployment with Proxy

```bash
# Deploy with Nginx proxy
./deploy-external-meilisearch.sh deploy --profile proxy

# Configure SSL certificates (optional)
# Place certificates in ../../ssl/

# Monitor continuously
./deploy-external-meilisearch.sh monitor --interval 30
```

### 3. Development Deployment

```bash
# Set development environment variables
export LOG_LEVEL=DEBUG
export DEBUG=true
export WORKER_PROCESSES=2

# Deploy without building (use existing images)
./deploy-external-meilisearch.sh deploy --no-build

# Follow logs for debugging
./deploy-external-meilisearch.sh logs --follow
```

### 4. Disaster Recovery

```bash
# Create backup before maintenance
./deploy-external-meilisearch.sh backup --include-images

# If recovery is needed
./deploy-external-meilisearch.sh restore --backup-id docker_backup_20240131_143022

# Verify restored service
./deploy-external-meilisearch.sh health
```

## Health Monitoring

### Health Check Endpoints

The service provides multiple health check endpoints:

- `GET /health` - Basic health status
- `GET /health/detailed` - Comprehensive health information
- `GET /metrics` - Prometheus-compatible metrics

### Monitoring Integration

#### Prometheus Integration

```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'thai-tokenizer'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
    scrape_interval: 30s
```

#### Grafana Dashboard

Key metrics to monitor:
- `thai_tokenizer_health_status` - Overall service health
- `thai_tokenizer_cpu_usage_percent` - CPU utilization
- `thai_tokenizer_memory_usage_mb` - Memory usage
- `thai_tokenizer_request_count` - Request throughput
- `thai_tokenizer_avg_response_time_ms` - Response times

### Alerting Rules

Example Prometheus alerting rules:

```yaml
groups:
  - name: thai-tokenizer
    rules:
      - alert: ThaiTokenizerDown
        expr: thai_tokenizer_health_status < 2
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "Thai Tokenizer service is unhealthy"
      
      - alert: HighMemoryUsage
        expr: thai_tokenizer_memory_usage_percent > 85
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "Thai Tokenizer memory usage is high"
```

## Security Considerations

### Container Security

- Non-root user execution
- Read-only root filesystem (security-hardened mode)
- Dropped capabilities
- Resource limits to prevent DoS
- Secure logging configuration

### Network Security

- Internal network isolation
- Configurable CORS origins
- Optional API key authentication
- SSL/TLS support for Meilisearch connections

### Data Protection

- Secure credential management via environment variables
- Encrypted backup storage (when configured)
- Log sanitization to prevent data leakage
- Configurable data retention policies

## Performance Optimization

### Resource Tuning

Adjust these environment variables based on your workload:

```bash
# CPU and memory
WORKER_PROCESSES=4          # Number of worker processes
CPU_LIMIT=2.0              # CPU limit
MEMORY_LIMIT=1G            # Memory limit

# Thai tokenization
TOKENIZER_CACHE_SIZE=1000  # Token cache size
BATCH_SIZE=50              # Processing batch size
MAX_WORKERS=4              # Concurrent workers

# Network and timeouts
REQUEST_TIMEOUT=30         # Request timeout seconds
MEILISEARCH_TIMEOUT_MS=10000  # Meilisearch timeout
```

### Performance Monitoring

Monitor these key metrics:
- Response time < 100ms for typical requests
- CPU usage < 80% under normal load
- Memory usage < 85% of allocated limit
- Error rate < 1% of total requests

## Troubleshooting

### Common Issues

1. **Service won't start**
   ```bash
   # Check logs
   ./deploy-external-meilisearch.sh logs
   
   # Validate configuration
   ./deploy-external-meilisearch.sh validate
   ```

2. **Meilisearch connectivity issues**
   ```bash
   # Test connectivity
   curl -f http://your-meilisearch-host:7700/health
   
   # Check API key
   curl -H "Authorization: Bearer YOUR_API_KEY" \
        http://your-meilisearch-host:7700/keys
   ```

3. **High resource usage**
   ```bash
   # Check resource usage
   python3 docker-health-monitor.py metrics
   
   # Adjust resource limits in .env file
   ```

4. **Health check failures**
   ```bash
   # Detailed health check
   python3 docker-health-monitor.py health
   
   # Check individual components
   curl http://localhost:8000/health/detailed
   ```

### Log Analysis

Logs are stored in:
- Application logs: `../../logs/thai-tokenizer/`
- Container logs: `docker compose logs`
- Nginx logs: `../../logs/nginx/` (if using proxy)

### Recovery Procedures

1. **Service recovery**
   ```bash
   ./deploy-external-meilisearch.sh restart
   ```

2. **Configuration recovery**
   ```bash
   ./deploy-external-meilisearch.sh restore --backup-id BACKUP_ID --restore-configuration
   ```

3. **Full system recovery**
   ```bash
   ./deploy-external-meilisearch.sh restore --backup-id BACKUP_ID --restore-volumes --restore-configuration
   ```

## Maintenance

### Regular Maintenance Tasks

1. **Weekly health checks**
   ```bash
   python3 docker-health-monitor.py report --output weekly-report.json
   ```

2. **Monthly backups**
   ```bash
   ./deploy-external-meilisearch.sh backup --include-images
   ```

3. **Quarterly updates**
   ```bash
   ./deploy-external-meilisearch.sh update
   ```

### Log Rotation

Logs are automatically rotated based on configuration:
- Max size: 100MB per file
- Max files: 5 files retained
- Compression: Enabled for older logs

### Backup Retention

Recommended backup retention policy:
- Daily backups: Keep for 7 days
- Weekly backups: Keep for 4 weeks
- Monthly backups: Keep for 12 months

## Support and Documentation

For additional support:
1. Check the main project README
2. Review the API documentation
3. Examine the health check endpoints
4. Analyze the monitoring metrics
5. Review the deployment logs

## Version History

- **v1.0.0**: Initial Docker deployment system
  - Basic deployment and health checking
  - External Meilisearch integration
  - Resource limits and monitoring

- **v1.1.0**: Enhanced deployment features
  - Comprehensive validation system
  - Advanced health monitoring
  - Backup and recovery procedures
  - Performance metrics collection

- **v1.2.0**: Security and reliability improvements
  - Security-hardened deployment options
  - Enhanced error handling and recovery
  - Prometheus metrics integration
  - Automated alerting capabilities