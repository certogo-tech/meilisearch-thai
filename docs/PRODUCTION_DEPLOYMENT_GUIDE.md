# Thai Tokenizer Production Deployment Guide

This comprehensive guide covers production deployment of the Thai Tokenizer on-premise system, including installation procedures, configuration management, monitoring setup, and maintenance operations.

## Overview

The Thai Tokenizer deployment package provides a complete solution for deploying Thai text tokenization services in production environments. It supports multiple deployment methods and includes comprehensive tooling for configuration, monitoring, and maintenance.

### Supported Deployment Methods

1. **Docker** - Containerized deployment (recommended for most environments)
2. **systemd** - Native Linux service deployment
3. **Standalone** - Python virtual environment deployment

### System Requirements

#### Minimum Requirements

- **OS**: Linux (Ubuntu 20.04+, CentOS 8+, RHEL 8+) or macOS 12+
- **Python**: 3.12 or higher
- **Memory**: 512MB RAM
- **Storage**: 2GB free disk space
- **Network**: Access to existing Meilisearch server

#### Recommended Requirements

- **Memory**: 1GB+ RAM
- **CPU**: 2+ cores
- **Storage**: 5GB+ free disk space
- **Network**: Dedicated network interface for service

#### Dependencies

- **uv** package manager
- **Docker** (for Docker deployment)
- **systemd** (for systemd deployment)
- **curl** (for health checks)

## Installation

### Step 1: Download and Extract Package

```bash
# Download the latest release
wget https://github.com/your-org/thai-tokenizer/releases/latest/download/thai-tokenizer-deployment-latest.tar.gz

# Extract the package
tar -xzf thai-tokenizer-deployment-latest.tar.gz
cd thai-tokenizer-deployment-*
```

### Step 2: Run Installation Script

```bash
# Basic installation
./install.sh

# Install with CLI symlink (requires sudo)
./install.sh --install-cli
```

### Step 3: Verify Installation

```bash
# Check version
./scripts/thai-tokenizer-deploy version

# Validate system requirements
./scripts/thai-tokenizer-deploy validate-system
```

## Configuration

### Quick Start Configuration

Generate a configuration template for your deployment method:

```bash
# Docker deployment (recommended)
./scripts/thai-tokenizer-deploy generate-config \
  --method docker \
  --output production-config.json \
  --example

# systemd deployment
./scripts/thai-tokenizer-deploy generate-config \
  --method systemd \
  --output production-config.json \
  --example
```

### Environment Variables

Set these environment variables before deployment:

```bash
# Meilisearch Configuration
export MEILISEARCH_HOST="https://your-meilisearch-server.com"
export MEILISEARCH_API_KEY="your-secure-api-key"

# Service Configuration
export SERVICE_PORT="8000"
export WORKER_PROCESSES="4"

# Security Configuration
export ALLOWED_HOST="your-domain.com"
export CORS_ORIGIN="https://your-app.com"
export API_KEY_REQUIRED="true"
```

### Production Configuration Template

Create a production configuration file:

```json
{
  "deployment_method": "docker",
  "meilisearch_config": {
    "host": "https://your-meilisearch-server.com",
    "port": 443,
    "api_key": "your-secure-api-key",
    "ssl_enabled": true,
    "ssl_verify": true,
    "timeout_seconds": 30,
    "max_retries": 3
  },
  "service_config": {
    "service_name": "thai-tokenizer",
    "service_port": 8000,
    "service_host": "0.0.0.0",
    "worker_processes": 4,
    "service_user": "thai-tokenizer",
    "service_group": "thai-tokenizer"
  },
  "security_config": {
    "security_level": "strict",
    "allowed_hosts": ["your-domain.com"],
    "cors_origins": ["https://your-app.com"],
    "api_key_required": true,
    "enable_https": true
  },
  "resource_config": {
    "memory_limit_mb": 1024,
    "cpu_limit_cores": 2.0,
    "max_concurrent_requests": 100,
    "request_timeout_seconds": 30,
    "enable_metrics": true,
    "metrics_port": 9000
  },
  "monitoring_config": {
    "enable_health_checks": true,
    "health_check_interval_seconds": 15,
    "enable_logging": true,
    "log_level": "INFO",
    "enable_prometheus": true,
    "prometheus_port": 9000
  },
  "installation_path": "/opt/thai-tokenizer",
  "data_path": "/opt/thai-tokenizer/data",
  "log_path": "/var/log/thai-tokenizer",
  "config_path": "/etc/thai-tokenizer"
}
```

## Deployment

### Docker Deployment (Recommended)

1. **Validate Configuration**

   ```bash
   ./scripts/thai-tokenizer-deploy validate-config --config production-config.json
   ```

2. **Test Meilisearch Connectivity**

   ```bash
   ./scripts/thai-tokenizer-deploy validate-meilisearch \
     --host https://your-meilisearch-server.com \
     --api-key your-secure-api-key
   ```

3. **Deploy Service**

   ```bash
   ./scripts/thai-tokenizer-deploy deploy \
     --config production-config.json \
     --method docker \
     --progress-file deployment-progress.json
   ```

4. **Verify Deployment**

   ```bash
   ./scripts/thai-tokenizer-deploy test \
     --service-url http://localhost:8000 \
     --test-type all
   ```

### systemd Deployment

1. **Prepare System** (requires root)

   ```bash
   sudo ./scripts/thai-tokenizer-deploy deploy \
     --config production-config.json \
     --method systemd
   ```

2. **Check Service Status**

   ```bash
   sudo systemctl status thai-tokenizer
   ```

3. **View Service Logs**

   ```bash
   sudo journalctl -u thai-tokenizer -f
   ```

### Standalone Deployment

1. **Deploy Service**

   ```bash
   ./scripts/thai-tokenizer-deploy deploy \
     --config production-config.json \
     --method standalone
   ```

2. **Check Process Status**

   ```bash
   ./scripts/thai-tokenizer-deploy status --service-name thai-tokenizer
   ```

## Post-Deployment Configuration

### SSL/TLS Setup

For production deployments, configure SSL/TLS:

1. **Obtain SSL Certificate**

   ```bash
   # Using Let's Encrypt (example)
   sudo certbot certonly --standalone -d your-domain.com
   ```

2. **Configure Reverse Proxy** (nginx example)

   ```nginx
   server {
       listen 443 ssl;
       server_name your-domain.com;
       
       ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
       }
       
       location /health {
           proxy_pass http://localhost:8000/health;
           access_log off;
       }
   }
   ```

### Firewall Configuration

Configure firewall rules:

```bash
# Allow service port
sudo ufw allow 8000/tcp

# Allow metrics port (if enabled)
sudo ufw allow 9000/tcp

# Allow HTTPS (if using reverse proxy)
sudo ufw allow 443/tcp
```

### Log Rotation

Configure log rotation:

```bash
# Create logrotate configuration
sudo tee /etc/logrotate.d/thai-tokenizer << EOF
/var/log/thai-tokenizer/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 0644 thai-tokenizer thai-tokenizer
    postrotate
        systemctl reload thai-tokenizer
    endscript
}
EOF
```

## Monitoring and Alerting

### Health Checks

Set up automated health checks:

```bash
# Create health check script
cat > /usr/local/bin/thai-tokenizer-health-check.sh << 'EOF'
#!/bin/bash
if curl -f -s http://localhost:8000/health > /dev/null; then
    echo "Service healthy"
    exit 0
else
    echo "Service unhealthy"
    exit 1
fi
EOF

chmod +x /usr/local/bin/thai-tokenizer-health-check.sh

# Add to crontab for monitoring
echo "*/5 * * * * /usr/local/bin/thai-tokenizer-health-check.sh || logger 'Thai Tokenizer health check failed'" | crontab -
```

### Prometheus Monitoring

If Prometheus monitoring is enabled:

1. **Configure Prometheus** to scrape metrics:

   ```yaml
   scrape_configs:
     - job_name: 'thai-tokenizer'
       static_configs:
         - targets: ['localhost:9000']
       scrape_interval: 30s
   ```

2. **Set up Grafana Dashboard** with key metrics:
   - Request rate and response time
   - Error rate
   - Memory and CPU usage
   - Thai tokenization accuracy

### Log Monitoring

Configure log monitoring with your preferred solution:

```bash
# Example with rsyslog
echo "*.* @@your-log-server:514" >> /etc/rsyslog.conf
systemctl restart rsyslog
```

## Backup and Recovery

### Configuration Backup

```bash
# Backup configuration
./scripts/thai-tokenizer-deploy backup-config --output-dir /backup/thai-tokenizer

# Automated backup script
cat > /usr/local/bin/backup-thai-tokenizer.sh << 'EOF'
#!/bin/bash
BACKUP_DIR="/backup/thai-tokenizer/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# Backup configuration
cp -r /etc/thai-tokenizer "$BACKUP_DIR/"

# Backup logs (last 7 days)
find /var/log/thai-tokenizer -name "*.log" -mtime -7 -exec cp {} "$BACKUP_DIR/" \;

# Compress backup
tar -czf "$BACKUP_DIR.tar.gz" -C /backup/thai-tokenizer "$(basename $BACKUP_DIR)"
rm -rf "$BACKUP_DIR"

# Keep only last 30 days of backups
find /backup/thai-tokenizer -name "*.tar.gz" -mtime +30 -delete
EOF

chmod +x /usr/local/bin/backup-thai-tokenizer.sh

# Schedule daily backups
echo "0 2 * * * /usr/local/bin/backup-thai-tokenizer.sh" | crontab -
```

### Disaster Recovery

1. **Service Recovery**

   ```bash
   # Stop service
   ./scripts/thai-tokenizer-deploy stop --service-name thai-tokenizer
   
   # Restore configuration
   tar -xzf backup-YYYYMMDD.tar.gz -C /
   
   # Restart service
   ./scripts/thai-tokenizer-deploy restart --service-name thai-tokenizer
   ```

2. **Complete Reinstallation**

   ```bash
   # Clean installation
   ./uninstall.sh
   ./install.sh
   
   # Restore configuration
   cp backup-config.json production-config.json
   
   # Redeploy
   ./scripts/thai-tokenizer-deploy deploy --config production-config.json
   ```

## Maintenance

### Updates

1. **Check for Updates**

   ```bash
   ./scripts/package/version_manager.py current
   ```

2. **Update Process**

   ```bash
   # Download new version
   wget https://github.com/your-org/thai-tokenizer/releases/latest/download/thai-tokenizer-deployment-latest.tar.gz
   
   # Backup current installation
   ./scripts/thai-tokenizer-deploy backup --output-dir /backup/pre-update
   
   # Stop service
   ./scripts/thai-tokenizer-deploy stop
   
   # Extract new version
   tar -xzf thai-tokenizer-deployment-latest.tar.gz
   
   # Run update
   cd thai-tokenizer-deployment-*
   ./install.sh
   
   # Restore configuration
   cp /backup/pre-update/production-config.json .
   
   # Deploy updated version
   ./scripts/thai-tokenizer-deploy deploy --config production-config.json
   ```

### Performance Tuning

1. **Memory Optimization**

   ```json
   {
     "resource_config": {
       "memory_limit_mb": 2048,
       "worker_processes": 4
     }
   }
   ```

2. **Connection Tuning**

   ```json
   {
     "resource_config": {
       "max_concurrent_requests": 200,
       "request_timeout_seconds": 15
     }
   }
   ```

3. **Meilisearch Optimization**

   ```json
   {
     "meilisearch_config": {
       "timeout_seconds": 10,
       "max_retries": 5,
       "retry_delay_seconds": 0.5
     }
   }
   ```

### Log Management

1. **Log Level Adjustment**

   ```bash
   # Update configuration
   ./scripts/thai-tokenizer-deploy config-update \
     --key monitoring_config.log_level \
     --value WARNING
   ```

2. **Log Analysis**

   ```bash
   # View recent errors
   grep ERROR /var/log/thai-tokenizer/*.log | tail -20
   
   # Monitor real-time logs
   tail -f /var/log/thai-tokenizer/service.log
   ```

## Troubleshooting

### Common Issues

1. **Service Won't Start**

   ```bash
   # Check configuration
   ./scripts/thai-tokenizer-deploy validate-config --config production-config.json
   
   # Check system requirements
   ./scripts/thai-tokenizer-deploy validate-system
   
   # Check logs
   ./scripts/thai-tokenizer-deploy logs --service-name thai-tokenizer --lines 50
   ```

2. **Meilisearch Connection Issues**

   ```bash
   # Test connectivity
   ./scripts/thai-tokenizer-deploy validate-meilisearch \
     --host https://your-meilisearch-server.com \
     --api-key your-api-key
   
   # Check network connectivity
   curl -H "Authorization: Bearer your-api-key" https://your-meilisearch-server.com/health
   ```

3. **Performance Issues**

   ```bash
   # Run performance tests
   ./scripts/thai-tokenizer-deploy test --test-type performance
   
   # Check resource usage
   ./scripts/thai-tokenizer-deploy status --detailed
   ```

### Support and Documentation

- **Troubleshooting Guide**: See `docs/TROUBLESHOOTING.md`
- **CLI Reference**: See `docs/CLI_AND_AUTOMATION.md`
- **API Documentation**: Available at `/docs` endpoint when service is running
- **Configuration Reference**: See configuration templates in `config_templates/`

### Getting Help

1. **Check Logs**: Always start by checking service logs
2. **Validate Configuration**: Ensure configuration is valid and complete
3. **Test Connectivity**: Verify Meilisearch connectivity
4. **Review Documentation**: Check relevant documentation sections
5. **Create Issue**: If problems persist, create a detailed issue report

## Security Considerations

### Production Security Checklist

- [ ] Use HTTPS for all external communications
- [ ] Enable API key authentication
- [ ] Configure restrictive CORS origins
- [ ] Set up proper firewall rules
- [ ] Use dedicated service user account
- [ ] Enable audit logging
- [ ] Regular security updates
- [ ] Monitor for suspicious activity
- [ ] Backup encryption keys securely
- [ ] Implement rate limiting

### Security Best Practices

1. **Network Security**
   - Use private networks when possible
   - Implement network segmentation
   - Regular security audits

2. **Access Control**
   - Principle of least privilege
   - Regular access reviews
   - Strong authentication mechanisms

3. **Data Protection**
   - Encrypt sensitive data at rest
   - Secure API key management
   - Regular backup testing

This production deployment guide provides comprehensive coverage of all aspects needed for successful Thai Tokenizer deployment in production environments. Follow the guidelines carefully and adapt them to your specific infrastructure requirements.
