# On-Premise Deployment Guide

This comprehensive guide provides step-by-step instructions for deploying the Thai Tokenizer service to integrate with existing on-premise Meilisearch infrastructure. The deployment supports three methods: Docker, systemd service, and standalone Python.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Deployment Methods Overview](#deployment-methods-overview)
3. [Docker Deployment](#docker-deployment)
4. [Systemd Service Deployment](#systemd-service-deployment)
5. [Standalone Python Deployment](#standalone-python-deployment)
6. [Configuration Examples](#configuration-examples)
7. [Performance Tuning](#performance-tuning)
8. [Troubleshooting](#troubleshooting)
9. [Security Best Practices](#security-best-practices)

## Prerequisites

### System Requirements

- **Operating System**: Linux (Ubuntu 20.04+, CentOS 8+, or equivalent)
- **Python**: 3.12 or higher
- **Memory**: Minimum 512MB RAM, recommended 1GB+
- **CPU**: Minimum 1 core, recommended 2+ cores
- **Disk Space**: Minimum 2GB free space
- **Network**: Access to existing Meilisearch server

### Required Software

```bash
# Install Python 3.12+
sudo apt update
sudo apt install python3.12 python3.12-venv python3.12-dev

# Install uv package manager
pip install uv

# For Docker deployment
sudo apt install docker.io docker-compose-plugin

# For systemd deployment
# systemd is included in most Linux distributions
```

### Existing Meilisearch Server

Ensure your existing Meilisearch server is:

- Running and accessible
- Has API key authentication configured (recommended)
- Supports the required API version (1.15.2+)

Test connectivity:

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" http://your-meilisearch-host:7700/health
```

## Deployment Methods Overview

| Method | Best For | Pros | Cons |
|--------|----------|------|------|
| **Docker** | Containerized environments, easy scaling | Isolated, consistent, easy management | Requires Docker knowledge |
| **Systemd** | Native Linux integration, production servers | Auto-start, resource control, logging | Linux-specific |
| **Standalone** | Development, custom environments | Direct control, easy debugging | Manual management |

## Docker Deployment

### Quick Start

1. **Clone the repository**:

   ```bash
   git clone <repository-url>
   cd thai-tokenizer
   ```

2. **Configure environment**:

   ```bash
   cp deployment/docker/.env.external-meilisearch.template .env
   nano .env
   ```

   Edit the following variables:

   ```env
   MEILISEARCH_HOST=http://your-meilisearch-host:7700
   MEILISEARCH_API_KEY=your-api-key
   THAI_TOKENIZER_PORT=8000
   ```

3. **Deploy with Docker Compose**:

   ```bash
   docker compose -f deployment/docker/docker-compose.external-meilisearch.yml up -d
   ```

4. **Verify deployment**:

   ```bash
   curl http://localhost:8000/health
   ```

### Detailed Docker Setup

#### Step 1: Prepare Configuration

Create a custom configuration file:

```bash
# Create configuration directory
mkdir -p config/production

# Copy template
cp deployment/docker/.env.external-meilisearch.template config/production/.env

# Edit configuration
nano config/production/.env
```

Required configuration:

```env
# Meilisearch Connection
MEILISEARCH_HOST=https://your-meilisearch.example.com
MEILISEARCH_API_KEY=your-secure-api-key
MEILISEARCH_SSL_VERIFY=true
MEILISEARCH_TIMEOUT=30

# Service Configuration
THAI_TOKENIZER_SERVICE_NAME=thai-tokenizer
THAI_TOKENIZER_SERVICE_PORT=8000
THAI_TOKENIZER_SERVICE_HOST=0.0.0.0
THAI_TOKENIZER_WORKER_PROCESSES=4

# Resource Limits
THAI_TOKENIZER_MEMORY_LIMIT_MB=512
THAI_TOKENIZER_CPU_LIMIT_CORES=1.0
THAI_TOKENIZER_MAX_CONCURRENT_REQUESTS=100

# Security
THAI_TOKENIZER_ALLOWED_HOSTS=localhost,your-domain.com
THAI_TOKENIZER_CORS_ORIGINS=https://your-frontend.com
THAI_TOKENIZER_API_KEY_REQUIRED=false
```

#### Step 2: Deploy Services

```bash
# Deploy with custom configuration
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml \
  --env-file config/production/.env up -d

# Check service status
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml ps

# View logs
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml logs -f thai-tokenizer
```

#### Step 3: Configure Reverse Proxy (Optional)

If using nginx as a reverse proxy:

```nginx
# /etc/nginx/sites-available/thai-tokenizer
server {
    listen 80;
    server_name tokenizer.your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeout settings
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    location /health {
        proxy_pass http://localhost:8000/health;
        access_log off;
    }
}
```

Enable the site:

```bash
sudo ln -s /etc/nginx/sites-available/thai-tokenizer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### Docker Management Commands

```bash
# Start services
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml up -d

# Stop services
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml down

# Restart services
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml restart

# View logs
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml logs -f

# Update services
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml pull
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml up -d

# Scale services
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml up -d --scale thai-tokenizer=3
```

## Systemd Service Deployment

### Quick Start

1. **Run deployment script**:

   ```bash
   sudo deployment/systemd/deploy-systemd.sh \
     --meilisearch-host http://your-meilisearch-host:7700 \
     --meilisearch-key your-api-key
   ```

2. **Start the service**:

   ```bash
   sudo systemctl start thai-tokenizer
   sudo systemctl enable thai-tokenizer
   ```

3. **Verify deployment**:

   ```bash
   systemctl status thai-tokenizer
   curl http://localhost:8000/health
   ```

### Detailed Systemd Setup

#### Step 1: Prepare System

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install python3.12 python3.12-venv python3.12-dev build-essential

# Install uv package manager
pip install uv
```

#### Step 2: Create Service User

```bash
# Create dedicated system user
sudo useradd --system --shell /bin/false --home /opt/thai-tokenizer thai-tokenizer

# Create necessary directories
sudo mkdir -p /opt/thai-tokenizer
sudo mkdir -p /var/lib/thai-tokenizer
sudo mkdir -p /var/log/thai-tokenizer
sudo mkdir -p /etc/thai-tokenizer

# Set ownership
sudo chown -R thai-tokenizer:thai-tokenizer /opt/thai-tokenizer
sudo chown -R thai-tokenizer:thai-tokenizer /var/lib/thai-tokenizer
sudo chown -R thai-tokenizer:thai-tokenizer /var/log/thai-tokenizer
```

#### Step 3: Install Service

```bash
# Run installation script with custom options
sudo deployment/systemd/deploy-systemd.sh \
  --meilisearch-host https://your-meilisearch.example.com \
  --meilisearch-key your-secure-api-key \
  --port 8000 \
  --install-path /opt/thai-tokenizer \
  --user thai-tokenizer \
  --group thai-tokenizer \
  --memory-limit 512M \
  --cpu-limit 1.0
```

#### Step 4: Configure Service

Edit the environment file:

```bash
sudo nano /etc/thai-tokenizer/environment
```

Key configuration options:

```env
# Service Configuration
THAI_TOKENIZER_SERVICE_PORT=8000
THAI_TOKENIZER_SERVICE_HOST=127.0.0.1
THAI_TOKENIZER_WORKER_PROCESSES=2

# Meilisearch Configuration
THAI_TOKENIZER_MEILISEARCH_HOST=https://your-meilisearch.example.com
THAI_TOKENIZER_MEILISEARCH_API_KEY=your-secure-api-key
THAI_TOKENIZER_MEILISEARCH_SSL_VERIFY=true
THAI_TOKENIZER_MEILISEARCH_TIMEOUT=30

# Resource Configuration
THAI_TOKENIZER_MEMORY_LIMIT_MB=512
THAI_TOKENIZER_CPU_LIMIT_CORES=1.0
THAI_TOKENIZER_MAX_CONCURRENT_REQUESTS=50

# Security Configuration
THAI_TOKENIZER_ALLOWED_HOSTS=localhost,127.0.0.1
THAI_TOKENIZER_API_KEY_REQUIRED=false

# Logging Configuration
THAI_TOKENIZER_LOG_LEVEL=INFO
THAI_TOKENIZER_LOG_FILE=/var/log/thai-tokenizer/thai-tokenizer.log
```

#### Step 5: Start and Enable Service

```bash
# Reload systemd configuration
sudo systemctl daemon-reload

# Start the service
sudo systemctl start thai-tokenizer

# Enable automatic startup
sudo systemctl enable thai-tokenizer

# Check service status
systemctl status thai-tokenizer
```

### Systemd Management Commands

```bash
# Service control
sudo systemctl start thai-tokenizer
sudo systemctl stop thai-tokenizer
sudo systemctl restart thai-tokenizer
sudo systemctl reload thai-tokenizer

# Service status
systemctl status thai-tokenizer
systemctl is-active thai-tokenizer
systemctl is-enabled thai-tokenizer

# View logs
journalctl -u thai-tokenizer -f
journalctl -u thai-tokenizer --since "1 hour ago"
journalctl -u thai-tokenizer -n 100

# Configuration management
sudo systemctl edit thai-tokenizer  # Create override
sudo systemctl daemon-reload       # Reload after changes
```

## Standalone Python Deployment

### Quick Start

1. **Run setup script**:

   ```bash
   python3 deployment/standalone/setup-standalone.py --install-path /opt/thai-tokenizer
   ```

2. **Configure Meilisearch connection**:

   ```bash
   nano /opt/thai-tokenizer/config/config.json
   ```

3. **Start the service**:

   ```bash
   /opt/thai-tokenizer/bin/start-service.sh
   ```

### Detailed Standalone Setup

#### Step 1: Prepare Installation Directory

```bash
# Create installation directory
sudo mkdir -p /opt/thai-tokenizer
sudo chown $USER:$USER /opt/thai-tokenizer

# Or use a user directory
mkdir -p ~/thai-tokenizer
cd ~/thai-tokenizer
```

#### Step 2: Set Up Virtual Environment

```bash
# Create virtual environment
python3 deployment/standalone/setup-venv.py \
  --install-path /opt/thai-tokenizer \
  --python /usr/bin/python3.12
```

#### Step 3: Install Dependencies

```bash
# Install with uv (recommended)
python3 deployment/standalone/install-dependencies.py \
  --venv-path /opt/thai-tokenizer/venv

# Or install with pip (fallback)
python3 deployment/standalone/install-dependencies.py \
  --venv-path /opt/thai-tokenizer/venv --no-uv
```

#### Step 4: Configure Service

```bash
# Generate configuration
python3 deployment/standalone/configure-service.py \
  --install-path /opt/thai-tokenizer

# Edit configuration
nano /opt/thai-tokenizer/config/config.json
```

Example configuration:

```json
{
  "meilisearch_config": {
    "host": "https://your-meilisearch.example.com",
    "port": 7700,
    "api_key": "your-secure-api-key",
    "ssl_enabled": true,
    "ssl_verify": true,
    "timeout_seconds": 30,
    "max_retries": 3
  },
  "service_config": {
    "service_name": "thai-tokenizer",
    "service_port": 8000,
    "service_host": "127.0.0.1",
    "worker_processes": 2
  },
  "resource_config": {
    "memory_limit_mb": 512,
    "cpu_limit_cores": 1.0,
    "max_concurrent_requests": 50,
    "request_timeout_seconds": 30
  },
  "security_config": {
    "allowed_hosts": ["localhost", "127.0.0.1"],
    "cors_origins": [],
    "api_key_required": false
  },
  "monitoring_config": {
    "log_level": "INFO",
    "log_file": "/opt/thai-tokenizer/logs/thai-tokenizer.log",
    "metrics_enabled": true,
    "health_check_enabled": true
  }
}
```

#### Step 5: Start Service

```bash
# Start service
/opt/thai-tokenizer/bin/start-service.sh

# Or use the management script
python3 deployment/standalone/manage-service.py \
  --install-path /opt/thai-tokenizer start
```

### Standalone Management Commands

```bash
# Service control
/opt/thai-tokenizer/bin/start-service.sh
/opt/thai-tokenizer/bin/stop-service.sh
/opt/thai-tokenizer/bin/restart-service.sh

# Check status
/opt/thai-tokenizer/bin/status-service.sh
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer status

# View logs
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer logs
tail -f /opt/thai-tokenizer/logs/thai-tokenizer.log

# Monitor service
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer monitor
```

## Configuration Examples

### Basic Configuration

For a simple deployment with minimal security:

```json
{
  "meilisearch_config": {
    "host": "http://localhost:7700",
    "api_key": "development-key"
  },
  "service_config": {
    "service_port": 8000,
    "worker_processes": 2
  }
}
```

### Production Configuration

For a production deployment with security and monitoring:

```json
{
  "meilisearch_config": {
    "host": "https://meilisearch.internal.company.com",
    "port": 7700,
    "api_key": "prod-secure-key-here",
    "ssl_enabled": true,
    "ssl_verify": true,
    "timeout_seconds": 30,
    "max_retries": 3
  },
  "service_config": {
    "service_name": "thai-tokenizer-prod",
    "service_port": 8000,
    "service_host": "0.0.0.0",
    "worker_processes": 4
  },
  "resource_config": {
    "memory_limit_mb": 1024,
    "cpu_limit_cores": 2.0,
    "max_concurrent_requests": 200,
    "request_timeout_seconds": 60
  },
  "security_config": {
    "allowed_hosts": [
      "tokenizer.company.com",
      "api.company.com",
      "10.0.0.0/8"
    ],
    "cors_origins": [
      "https://app.company.com",
      "https://admin.company.com"
    ],
    "api_key_required": true,
    "api_key": "tokenizer-api-key-here"
  },
  "monitoring_config": {
    "log_level": "INFO",
    "log_file": "/var/log/thai-tokenizer/thai-tokenizer.log",
    "metrics_enabled": true,
    "health_check_enabled": true,
    "prometheus_metrics": true
  }
}
```

### High-Performance Configuration

For high-throughput deployments:

```json
{
  "meilisearch_config": {
    "host": "http://meilisearch-cluster.internal:7700",
    "api_key": "cluster-api-key",
    "timeout_seconds": 10,
    "max_retries": 2,
    "connection_pool_size": 20
  },
  "service_config": {
    "service_port": 8000,
    "service_host": "0.0.0.0",
    "worker_processes": 8
  },
  "resource_config": {
    "memory_limit_mb": 2048,
    "cpu_limit_cores": 4.0,
    "max_concurrent_requests": 500,
    "request_timeout_seconds": 30
  },
  "performance_config": {
    "tokenization_cache_size": 10000,
    "connection_pool_size": 50,
    "async_workers": 16,
    "batch_processing_enabled": true,
    "batch_size": 100
  }
}
```

## Performance Tuning

### Resource Optimization

#### Memory Tuning

```bash
# Monitor memory usage
free -h
ps aux | grep thai-tokenizer

# For Docker deployment
docker stats thai-tokenizer

# For systemd deployment
systemctl show thai-tokenizer --property=MemoryCurrent
```

Recommended memory settings:

- **Light load**: 256-512MB
- **Medium load**: 512MB-1GB
- **Heavy load**: 1-2GB+

#### CPU Optimization

```bash
# Monitor CPU usage
top -p $(pgrep -f thai-tokenizer)
htop

# Check CPU cores
nproc
```

Worker process recommendations:

- **Single core**: 1-2 workers
- **Dual core**: 2-4 workers
- **Quad core**: 4-8 workers
- **8+ cores**: 8-16 workers

### Network Optimization

#### Connection Pooling

```json
{
  "meilisearch_config": {
    "connection_pool_size": 20,
    "max_connections_per_host": 10,
    "keep_alive_timeout": 30
  }
}
```

#### Request Handling

```json
{
  "service_config": {
    "max_concurrent_requests": 100,
    "request_timeout_seconds": 30,
    "keep_alive_timeout": 5
  }
}
```

### Thai Tokenization Performance

#### Caching Configuration

```json
{
  "tokenization_config": {
    "cache_enabled": true,
    "cache_size": 10000,
    "cache_ttl_seconds": 3600,
    "preload_common_words": true
  }
}
```

#### Batch Processing

```json
{
  "batch_config": {
    "batch_processing_enabled": true,
    "batch_size": 100,
    "batch_timeout_ms": 50,
    "parallel_processing": true
  }
}
```

### Monitoring Performance

#### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health with metrics
curl http://localhost:8000/health/detailed

# Performance metrics
curl http://localhost:8000/metrics
```

#### Performance Benchmarking

```bash
# Run performance tests
python3 deployment/scripts/benchmark.py \
  --host http://localhost:8000 \
  --concurrent-users 10 \
  --duration 60

# Thai-specific performance test
python3 deployment/scripts/demo_thai_tokenizer.py \
  --benchmark --iterations 1000
```

## Troubleshooting

### Common Issues

#### Service Won't Start

**Symptoms**: Service fails to start or exits immediately

**Diagnosis**:

```bash
# Check service status
systemctl status thai-tokenizer  # For systemd
docker logs thai-tokenizer       # For Docker
cat /opt/thai-tokenizer/logs/thai-tokenizer.log  # For standalone

# Check configuration
python3 -c "import json; print(json.load(open('/path/to/config.json')))"

# Test Python environment
/opt/thai-tokenizer/venv/bin/python -c "import pythainlp; print('OK')"
```

**Solutions**:

1. **Check Python version**: Ensure Python 3.12+ is installed
2. **Verify dependencies**: Reinstall dependencies with uv
3. **Check permissions**: Ensure service user has proper permissions
4. **Validate configuration**: Check JSON syntax and required fields

#### Meilisearch Connection Failed

**Symptoms**: Service starts but can't connect to Meilisearch

**Diagnosis**:

```bash
# Test Meilisearch connectivity
curl -H "Authorization: Bearer YOUR_API_KEY" http://your-meilisearch:7700/health

# Check network connectivity
ping your-meilisearch-host
telnet your-meilisearch-host 7700

# Check DNS resolution
nslookup your-meilisearch-host
```

**Solutions**:

1. **Verify Meilisearch URL**: Check host, port, and protocol (http/https)
2. **Check API key**: Ensure API key is correct and has proper permissions
3. **Network access**: Verify firewall rules and network connectivity
4. **SSL issues**: For HTTPS, check SSL certificate validity

#### Port Already in Use

**Symptoms**: Service fails to bind to port

**Diagnosis**:

```bash
# Check what's using the port
sudo ss -tulpn | grep :8000
sudo lsof -i :8000

# Check if service is already running
ps aux | grep thai-tokenizer
```

**Solutions**:

1. **Stop conflicting service**: Stop the service using the port
2. **Change port**: Configure service to use a different port
3. **Kill process**: Kill the process using the port (if safe)

#### High Memory Usage

**Symptoms**: Service consumes excessive memory

**Diagnosis**:

```bash
# Monitor memory usage
ps aux | grep thai-tokenizer
top -p $(pgrep -f thai-tokenizer)

# Check for memory leaks
valgrind --tool=memcheck python3 -m src.api.main
```

**Solutions**:

1. **Reduce cache size**: Lower tokenization cache settings
2. **Limit workers**: Reduce number of worker processes
3. **Memory limits**: Set resource limits in configuration
4. **Restart service**: Periodic restarts to clear memory

#### Slow Performance

**Symptoms**: Thai tokenization is slower than expected

**Diagnosis**:

```bash
# Run performance benchmark
python3 deployment/scripts/benchmark.py --host http://localhost:8000

# Check resource usage
htop
iotop

# Profile the application
python3 -m cProfile -o profile.stats -m src.api.main
```

**Solutions**:

1. **Enable caching**: Configure tokenization result caching
2. **Increase workers**: Add more worker processes
3. **Optimize resources**: Allocate more CPU/memory
4. **Batch processing**: Enable batch processing for multiple documents

### Debug Mode

Enable debug logging for detailed troubleshooting:

#### Docker Debug

```bash
# Set debug environment
echo "THAI_TOKENIZER_LOG_LEVEL=DEBUG" >> .env

# Restart with debug
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml up -d

# View debug logs
docker compose -f deployment/docker/docker-compose.external-meilisearch.yml logs -f
```

#### Systemd Debug

```bash
# Edit environment file
sudo nano /etc/thai-tokenizer/environment

# Add debug setting
THAI_TOKENIZER_LOG_LEVEL=DEBUG

# Restart service
sudo systemctl restart thai-tokenizer

# View debug logs
journalctl -u thai-tokenizer -f
```

#### Standalone Debug

```bash
# Edit configuration
nano /opt/thai-tokenizer/config/config.json

# Set debug level
{
  "monitoring_config": {
    "log_level": "DEBUG"
  }
}

# Restart service
/opt/thai-tokenizer/bin/restart-service.sh

# View debug logs
tail -f /opt/thai-tokenizer/logs/thai-tokenizer.log
```

### Log Analysis

#### Common Log Patterns

**Successful startup**:

```
INFO: Thai Tokenizer service starting on port 8000
INFO: Connected to Meilisearch at http://localhost:7700
INFO: Thai tokenization engine initialized
INFO: Service ready to accept requests
```

**Connection issues**:

```
ERROR: Failed to connect to Meilisearch: Connection refused
ERROR: Meilisearch authentication failed: Invalid API key
WARNING: Retrying Meilisearch connection in 5 seconds
```

**Performance issues**:

```
WARNING: Thai tokenization took 150ms (threshold: 50ms)
WARNING: High memory usage: 800MB (limit: 512MB)
ERROR: Request timeout after 30 seconds
```

#### Log Aggregation

For production deployments, consider log aggregation:

```bash
# Configure rsyslog for centralized logging
echo "*.* @@log-server:514" >> /etc/rsyslog.conf

# Use structured logging
{
  "monitoring_config": {
    "log_format": "json",
    "log_structured": true
  }
}
```

## Security Best Practices

### Network Security

1. **Firewall Configuration**:

   ```bash
   # Allow only necessary ports
   sudo ufw allow 8000/tcp
   sudo ufw enable
   
   # Restrict to specific IPs
   sudo ufw allow from 10.0.0.0/8 to any port 8000
   ```

2. **Reverse Proxy**: Use nginx or Apache as a reverse proxy
3. **SSL/TLS**: Enable HTTPS for external access
4. **Network Segmentation**: Deploy in isolated network segments

### Authentication and Authorization

1. **API Key Authentication**:

   ```json
   {
     "security_config": {
       "api_key_required": true,
       "api_key": "secure-random-key-here"
     }
   }
   ```

2. **IP Whitelisting**:

   ```json
   {
     "security_config": {
       "allowed_hosts": ["10.0.0.0/8", "192.168.1.0/24"]
     }
   }
   ```

### System Security

1. **Non-root User**: Always run as dedicated system user
2. **File Permissions**: Restrict access to configuration files
3. **Resource Limits**: Set memory and CPU limits
4. **Regular Updates**: Keep system and dependencies updated

### Data Protection

1. **Log Sanitization**: Ensure logs don't contain sensitive data
2. **Configuration Encryption**: Encrypt sensitive configuration files
3. **Secure Storage**: Use secure storage for API keys and certificates
4. **Backup Security**: Encrypt backups and restrict access

This completes the comprehensive deployment documentation for task 9.1. The guide provides detailed step-by-step instructions for all three deployment methods, configuration examples for various scenarios, performance tuning guidance, and extensive troubleshooting procedures.
