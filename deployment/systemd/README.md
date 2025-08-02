# Systemd Deployment for Thai Tokenizer

This directory contains comprehensive systemd deployment tools for the Thai Tokenizer service, providing native Linux service integration with automatic startup, restart policies, and system resource management.

## Overview

The systemd deployment method provides:

- **Native Linux Integration**: Full systemd service with proper dependencies and startup order
- **Automatic Management**: Service starts automatically on boot and restarts on failure
- **Resource Control**: Memory and CPU limits with systemd cgroups
- **Security Hardening**: Restricted file system access and security policies
- **Logging Integration**: Structured logging with journald and optional file logging
- **User Management**: Dedicated system user and group for security isolation

## Quick Start

### Prerequisites

- Linux system with systemd
- Python 3.12+
- uv package manager
- Root privileges (sudo access)
- Existing Meilisearch server

### Basic Installation

```bash
# Clone the repository
git clone <repository-url>
cd thai-tokenizer

# Run the deployment script
sudo deployment/systemd/deploy-systemd.sh \
  --meilisearch-host http://localhost:7700 \
  --meilisearch-key your-api-key
```

### Custom Installation

```bash
# Custom port and installation path
sudo deployment/systemd/deploy-systemd.sh \
  --meilisearch-host https://meilisearch.example.com \
  --meilisearch-key your-api-key \
  --port 8080 \
  --install-path /opt/custom/thai-tokenizer \
  --user custom-user \
  --group custom-group
```

## Files and Components

### Core Files

- **`thai-tokenizer.service.template`**: Systemd service unit file template
- **`deploy-systemd.sh`**: Main deployment script with system preparation
- **`install-systemd-service.py`**: Python-based service installer
- **`manage-service.py`**: Service management utility
- **`logrotate.conf.template`**: Log rotation configuration template

### Python Modules

- **`systemd_manager.py`**: Core systemd service management classes
- **`systemd_config_manager.py`**: Configuration file management

### Generated Files (after installation)

- **`/etc/systemd/system/thai-tokenizer.service`**: Systemd service file
- **`/etc/thai-tokenizer/environment`**: Environment variables file
- **`/etc/logrotate.d/thai-tokenizer`**: Log rotation configuration
- **`/etc/systemd/system/thai-tokenizer.service.d/`**: Override directory

## Service Management

### Using systemctl (Standard)

```bash
# Start the service
sudo systemctl start thai-tokenizer

# Stop the service
sudo systemctl stop thai-tokenizer

# Restart the service
sudo systemctl restart thai-tokenizer

# Check service status
systemctl status thai-tokenizer

# View service logs
journalctl -u thai-tokenizer -f

# Enable automatic startup
sudo systemctl enable thai-tokenizer

# Disable automatic startup
sudo systemctl disable thai-tokenizer
```

### Using Management Script (Enhanced)

```bash
# Start service with validation
sudo deployment/systemd/manage-service.py start

# Get comprehensive status
deployment/systemd/manage-service.py status

# Show health information
deployment/systemd/manage-service.py health

# View logs
deployment/systemd/manage-service.py logs --lines 100

# Follow logs in real-time
deployment/systemd/manage-service.py logs --follow

# Reload configuration
sudo deployment/systemd/manage-service.py reload

# Validate configuration
deployment/systemd/manage-service.py validate
```

## Configuration

### Environment Variables

The service configuration is managed through environment variables in `/etc/thai-tokenizer/environment`:

```bash
# Service Configuration
THAI_TOKENIZER_SERVICE_NAME="thai-tokenizer"
THAI_TOKENIZER_SERVICE_PORT="8000"
THAI_TOKENIZER_SERVICE_HOST="127.0.0.1"
THAI_TOKENIZER_WORKER_PROCESSES="2"

# Meilisearch Configuration
THAI_TOKENIZER_MEILISEARCH_HOST="http://localhost:7700"
THAI_TOKENIZER_MEILISEARCH_API_KEY="your-api-key"
THAI_TOKENIZER_MEILISEARCH_TIMEOUT="30"

# Resource Configuration
THAI_TOKENIZER_MEMORY_LIMIT_MB="256"
THAI_TOKENIZER_CPU_LIMIT_CORES="0.5"
THAI_TOKENIZER_MAX_CONCURRENT_REQUESTS="50"

# Security Configuration
THAI_TOKENIZER_ALLOWED_HOSTS="localhost,127.0.0.1"
THAI_TOKENIZER_CORS_ORIGINS=""
THAI_TOKENIZER_API_KEY_REQUIRED="false"
```

### Systemd Overrides

Create custom overrides in `/etc/systemd/system/thai-tokenizer.service.d/`:

```ini
# /etc/systemd/system/thai-tokenizer.service.d/custom.conf
[Service]
# Custom resource limits
MemoryLimit=512M
CPUQuota=100%

# Custom environment variables
Environment=CUSTOM_SETTING=value

# Custom restart policy
RestartSec=10
```

After creating overrides:

```bash
sudo systemctl daemon-reload
sudo systemctl restart thai-tokenizer
```

## Security Features

### File System Security

- **Read-only installation directory**: Service cannot modify its own code
- **Restricted write access**: Only data, log, and config directories are writable
- **Private temporary directory**: Isolated /tmp for the service
- **Protected system directories**: Cannot access /home, /root, etc.

### Network Security

- **Address family restrictions**: Only IPv4, IPv6, and Unix sockets allowed
- **IP address filtering**: Configurable allowed networks
- **Localhost binding**: Default configuration binds to localhost only

### Process Security

- **Non-root execution**: Runs as dedicated system user
- **No new privileges**: Cannot escalate privileges
- **Memory protection**: Write-execute memory protection enabled
- **Kernel protection**: Cannot modify kernel parameters

### Resource Limits

- **Memory limits**: Configurable memory usage limits
- **CPU quotas**: Configurable CPU usage limits
- **Process limits**: Limited number of processes and file descriptors
- **Task limits**: Limited number of tasks per service

## Monitoring and Logging

### Systemd Journal Integration

```bash
# View all service logs
journalctl -u thai-tokenizer

# Follow logs in real-time
journalctl -u thai-tokenizer -f

# View logs since boot
journalctl -u thai-tokenizer -b

# View logs for specific time period
journalctl -u thai-tokenizer --since "2024-01-01" --until "2024-01-02"

# View logs with specific priority
journalctl -u thai-tokenizer -p err
```

### Log Rotation

Automatic log rotation is configured via logrotate:

- **Daily rotation**: Logs are rotated daily
- **30-day retention**: Keeps 30 days of compressed logs
- **Automatic compression**: Old logs are compressed to save space
- **Service reload**: Service is reloaded after rotation

### Health Monitoring

```bash
# Check application health
curl http://localhost:8000/health

# Get detailed health information
deployment/systemd/manage-service.py health --json
```

## Troubleshooting

### Common Issues

#### Service Won't Start

```bash
# Check service status
systemctl status thai-tokenizer

# Check detailed logs
journalctl -u thai-tokenizer -n 50

# Validate configuration
deployment/systemd/manage-service.py validate
```

#### Port Already in Use

```bash
# Check what's using the port
sudo ss -tulpn | grep :8000

# Change service port
sudo nano /etc/thai-tokenizer/environment
# Edit THAI_TOKENIZER_SERVICE_PORT="8001"

# Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart thai-tokenizer
```

#### Permission Errors

```bash
# Check directory ownership
ls -la /opt/thai-tokenizer /var/lib/thai-tokenizer /var/log/thai-tokenizer

# Fix ownership if needed
sudo chown -R thai-tokenizer:thai-tokenizer /opt/thai-tokenizer
sudo chown -R thai-tokenizer:thai-tokenizer /var/lib/thai-tokenizer
sudo chown -R thai-tokenizer:thai-tokenizer /var/log/thai-tokenizer
```

#### Meilisearch Connection Issues

```bash
# Test Meilisearch connectivity
curl -H "Authorization: Bearer your-api-key" http://localhost:7700/health

# Check environment configuration
sudo cat /etc/thai-tokenizer/environment | grep MEILISEARCH

# Update Meilisearch settings
sudo deployment/systemd/manage-service.py validate --config /path/to/config.json
```

### Debug Mode

Enable debug logging:

```bash
# Edit environment file
sudo nano /etc/thai-tokenizer/environment

# Change log level
THAI_TOKENIZER_LOG_LEVEL="DEBUG"

# Restart service
sudo systemctl restart thai-tokenizer

# View debug logs
journalctl -u thai-tokenizer -f
```

### Performance Monitoring

```bash
# Check resource usage
systemctl show thai-tokenizer --property=MemoryCurrent,CPUUsageNSec

# Monitor in real-time
watch -n 1 'systemctl show thai-tokenizer --property=MemoryCurrent,CPUUsageNSec'

# Check process details
ps aux | grep thai-tokenizer
```

## Uninstallation

### Complete Removal

```bash
# Stop and disable service
sudo systemctl stop thai-tokenizer
sudo systemctl disable thai-tokenizer

# Remove service files
sudo rm -f /etc/systemd/system/thai-tokenizer.service
sudo rm -rf /etc/systemd/system/thai-tokenizer.service.d
sudo rm -f /etc/logrotate.d/thai-tokenizer

# Reload systemd
sudo systemctl daemon-reload

# Remove user and group (optional)
sudo userdel thai-tokenizer
sudo groupdel thai-tokenizer

# Remove directories (optional)
sudo rm -rf /opt/thai-tokenizer
sudo rm -rf /var/lib/thai-tokenizer
sudo rm -rf /var/log/thai-tokenizer
sudo rm -rf /etc/thai-tokenizer
```

### Using Uninstall Script

```bash
# Automated uninstallation
sudo deployment/systemd/deploy-systemd.sh --uninstall
```

## Advanced Configuration

### Custom Service User

```bash
# Create custom user
sudo useradd --system --shell /bin/false custom-tokenizer

# Deploy with custom user
sudo deployment/systemd/deploy-systemd.sh \
  --meilisearch-host http://localhost:7700 \
  --meilisearch-key your-api-key \
  --user custom-tokenizer \
  --group custom-tokenizer
```

### Multiple Instances

```bash
# Deploy second instance on different port
sudo deployment/systemd/deploy-systemd.sh \
  --meilisearch-host http://localhost:7700 \
  --meilisearch-key your-api-key \
  --port 8001 \
  --install-path /opt/thai-tokenizer-2 \
  --user thai-tokenizer-2 \
  --group thai-tokenizer-2
```

### Integration with Reverse Proxy

Example nginx configuration:

```nginx
upstream thai_tokenizer {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name tokenizer.example.com;

    location / {
        proxy_pass http://thai_tokenizer;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /health {
        proxy_pass http://thai_tokenizer/health;
        access_log off;
    }
}
```

## Best Practices

### Security

1. **Use dedicated user**: Always run the service as a dedicated system user
2. **Restrict network access**: Bind to localhost unless external access is needed
3. **Enable API authentication**: Use API keys for production deployments
4. **Regular updates**: Keep the service and dependencies updated
5. **Monitor logs**: Regularly review service logs for security issues

### Performance

1. **Resource limits**: Set appropriate memory and CPU limits
2. **Worker processes**: Adjust worker count based on available CPU cores
3. **Connection pooling**: Configure appropriate connection limits
4. **Log rotation**: Ensure logs don't consume excessive disk space

### Reliability

1. **Health checks**: Implement comprehensive health monitoring
2. **Backup configuration**: Regularly backup configuration files
3. **Test deployments**: Test configuration changes in staging first
4. **Monitor dependencies**: Ensure Meilisearch availability

### Maintenance

1. **Automated deployment**: Use configuration management tools
2. **Version control**: Track configuration changes
3. **Documentation**: Document custom configurations and procedures
4. **Monitoring**: Set up alerting for service failures

## Support

For issues and questions:

1. Check the troubleshooting section above
2. Review service logs: `journalctl -u thai-tokenizer -f`
3. Validate configuration: `deployment/systemd/manage-service.py validate`
4. Check system resources: `systemctl show thai-tokenizer`
5. Test Meilisearch connectivity independently

## References

- [systemd Service Unit Configuration](https://www.freedesktop.org/software/systemd/man/systemd.service.html)
- [systemd Resource Control](https://www.freedesktop.org/software/systemd/man/systemd.resource-control.html)
- [journalctl Manual](https://www.freedesktop.org/software/systemd/man/journalctl.html)
- [logrotate Configuration](https://linux.die.net/man/8/logrotate)