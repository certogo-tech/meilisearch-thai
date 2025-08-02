# Standalone Python Deployment

This directory contains scripts and utilities for deploying the Thai Tokenizer service as a standalone Python application using virtual environments.

## Overview

The standalone deployment method provides:
- Direct Python environment control
- Minimal overhead
- Easy debugging and development
- Custom Python version support
- Manual service management

## Files

### Core Scripts
- `setup-venv.py` - Virtual environment creation and management
- `install-dependencies.py` - Dependency installation with uv package manager
- `configure-service.py` - Python-specific configuration management
- `manage-service.py` - Process management scripts for standalone deployment

### Convenience Scripts
- `setup-standalone.py` - Complete setup orchestrator (runs all setup steps)
- `start-service.sh` - Service startup convenience script
- `test-setup.py` - Test script for validating setup components

### Utility Scripts
- `backup-service.py` - Backup and recovery utilities
- `debug-utilities.py` - Development and debugging tools
- `start-service.sh` - Enhanced service startup script
- `stop-service.sh` - Service shutdown script  
- `restart-service.sh` - Service restart script
- `status-service.sh` - Service status check script

### Generated Files (after setup)
- `{install-path}/bin/start-service.sh` - Service startup script
- `{install-path}/bin/stop-service.sh` - Service shutdown script  
- `{install-path}/bin/restart-service.sh` - Service restart script
- `{install-path}/bin/status-service.sh` - Service status check script

## Requirements

- Python 3.12+
- uv package manager
- Sufficient permissions for installation directory
- Access to existing Meilisearch server

## Quick Start

### Option 1: Complete Setup (Recommended)
```bash
# Run complete setup in one command
python3 deployment/standalone/setup-standalone.py --install-path /opt/thai-tokenizer

# Configure Meilisearch connection (edit the generated config file)
nano /opt/thai-tokenizer/config/config.json

# Start the service
/opt/thai-tokenizer/bin/start-service.sh
```

### Option 2: Step-by-Step Setup
1. Set up virtual environment:
   ```bash
   python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer
   ```

2. Install dependencies:
   ```bash
   python3 deployment/standalone/install-dependencies.py --venv-path /opt/thai-tokenizer/venv
   ```

3. Configure service:
   ```bash
   python3 deployment/standalone/configure-service.py --install-path /opt/thai-tokenizer
   ```

4. Start service:
   ```bash
   python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer start
   ```

## Configuration

The standalone deployment uses the same configuration model as other deployment methods, with additional Python-specific settings for virtual environment management and process control.
##
 Detailed Usage

### Virtual Environment Setup

```bash
# Basic setup
python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer

# Use specific Python version
python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer --python /usr/bin/python3.12

# Remove existing environment
python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer --remove

# Verbose output
python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer --verbose
```

### Dependency Installation

```bash
# Install with uv (recommended)
python3 deployment/standalone/install-dependencies.py --venv-path /opt/thai-tokenizer/venv

# Install with pip (fallback)
python3 deployment/standalone/install-dependencies.py --venv-path /opt/thai-tokenizer/venv --no-uv

# Specify project root
python3 deployment/standalone/install-dependencies.py --venv-path /opt/thai-tokenizer/venv --project-root /path/to/project
```

### Service Configuration

```bash
# Use default configuration
python3 deployment/standalone/configure-service.py --install-path /opt/thai-tokenizer

# Use existing configuration file
python3 deployment/standalone/configure-service.py --install-path /opt/thai-tokenizer --config-file my-config.json
```

### Process Management

```bash
# Start service
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer start

# Stop service
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer stop

# Force stop service
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer stop --force

# Restart service
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer restart

# Check status
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer status

# Check status (JSON output)
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer status --json

# View logs
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer logs

# View more log lines
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer logs --lines 100

# Monitor service
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer monitor

# Monitor for specific duration
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer monitor --duration 300 --interval 10
```

## Configuration Details

### Main Configuration File
Location: `{install-path}/config/config.json`

Key sections:
- `meilisearch_config`: Connection details for existing Meilisearch server
- `service_config`: Thai Tokenizer service settings (port, workers, etc.)
- `security_config`: Security settings (API keys, CORS, etc.)
- `resource_config`: Resource limits and performance settings
- `monitoring_config`: Logging and monitoring configuration

### Environment Variables
Location: `{install-path}/config/.env`

Automatically generated from the main configuration file. Contains all environment variables needed by the service.

### Logging Configuration
Location: `{install-path}/config/logging.json`

Configures structured logging with both console and file output, including log rotation.

## Directory Structure

After setup, the installation directory will contain:

```
/opt/thai-tokenizer/
├── venv/                    # Python virtual environment
├── config/                  # Configuration files
│   ├── config.json         # Main configuration
│   ├── .env               # Environment variables
│   └── logging.json       # Logging configuration
├── bin/                    # Service management scripts
│   ├── activate-thai-tokenizer  # Environment activation
│   ├── start-service.sh    # Start service
│   ├── stop-service.sh     # Stop service
│   ├── restart-service.sh  # Restart service
│   └── status-service.sh   # Check status
├── logs/                   # Log files
│   └── thai-tokenizer.log  # Main log file
├── data/                   # Data directory
├── run/                    # Runtime files
│   └── thai-tokenizer.pid  # Process ID file
├── venv-info.json          # Virtual environment info
├── installation-report.json # Dependency installation report
└── SETUP_SUMMARY.md        # Setup summary and instructions
```

## Troubleshooting

### Common Issues

1. **Permission Denied**
   ```bash
   # Ensure proper permissions for installation directory
   sudo chown -R $USER:$USER /opt/thai-tokenizer
   chmod -R 755 /opt/thai-tokenizer
   ```

2. **Python Version Issues**
   ```bash
   # Check Python version
   python3 --version
   
   # Use specific Python version
   python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer --python /usr/bin/python3.12
   ```

3. **uv Not Found**
   ```bash
   # Install uv
   pip install uv
   
   # Or use pip instead
   python3 deployment/standalone/install-dependencies.py --venv-path /opt/thai-tokenizer/venv --no-uv
   ```

4. **Service Won't Start**
   ```bash
   # Check logs
   python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer logs
   
   # Check configuration
   cat /opt/thai-tokenizer/config/config.json
   
   # Test Meilisearch connection
   curl http://your-meilisearch-host:7700/health
   ```

5. **Port Already in Use**
   ```bash
   # Check what's using the port
   lsof -i :8000
   
   # Edit configuration to use different port
   nano /opt/thai-tokenizer/config/config.json
   ```

### Testing Setup

```bash
# Run setup validation tests
python3 deployment/standalone/test-setup.py

# Run comprehensive diagnostics
python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer diagnostics

# Test individual components
python3 deployment/standalone/setup-venv.py --help
python3 deployment/standalone/install-dependencies.py --help
python3 deployment/standalone/configure-service.py --help
python3 deployment/standalone/manage-service.py --help
```

### Advanced Troubleshooting

#### Service Won't Start
1. **Run diagnostics**:
   ```bash
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer diagnostics
   ```

2. **Check installation**:
   ```bash
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test installation
   ```

3. **Test dependencies**:
   ```bash
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test dependencies
   ```

4. **Check logs**:
   ```bash
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer logs
   ```

#### Meilisearch Connection Issues
1. **Test connection**:
   ```bash
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test meilisearch
   ```

2. **Check configuration**:
   ```bash
   cat /opt/thai-tokenizer/config/config.json
   ```

3. **Manual connection test**:
   ```bash
   curl http://your-meilisearch-host:7700/health
   ```

#### Thai Tokenization Problems
1. **Test tokenization**:
   ```bash
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test tokenization
   ```

2. **Interactive debugging**:
   ```bash
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer interactive
   ```

#### Performance Issues
1. **Monitor service**:
   ```bash
   python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer monitor --detailed --duration 300
   ```

2. **Get performance metrics**:
   ```bash
   python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer metrics
   ```

3. **Continuous monitoring**:
   ```bash
   ./deployment/standalone/status-service.sh /opt/thai-tokenizer --continuous --detailed
   ```

#### Backup and Recovery
1. **Create backup before changes**:
   ```bash
   python3 deployment/standalone/backup-service.py --install-path /opt/thai-tokenizer create --name pre-update-backup
   ```

2. **Restore if issues occur**:
   ```bash
   python3 deployment/standalone/backup-service.py --install-path /opt/thai-tokenizer restore /path/to/backup.tar.gz
   ```

## Performance Tuning

### Resource Configuration
Edit `/opt/thai-tokenizer/config/config.json`:

```json
{
  "resource_config": {
    "memory_limit_mb": 1024,
    "cpu_limit_cores": 2.0,
    "max_concurrent_requests": 200,
    "request_timeout_seconds": 60
  },
  "service_config": {
    "worker_processes": 4
  }
}
```

### Monitoring
```bash
# Monitor resource usage with alerts
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer monitor --duration 600 --detailed

# Monitor with custom thresholds
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer monitor --cpu-threshold 70 --memory-threshold 256

# Get performance metrics
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer metrics

# Check service health
curl http://localhost:8000/health

# View detailed status
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer status --json

# Continuous status monitoring
./deployment/standalone/status-service.sh /opt/thai-tokenizer --continuous --interval 10
```

### Backup and Recovery
```bash
# Create full backup
python3 deployment/standalone/backup-service.py --install-path /opt/thai-tokenizer create

# Create backup with custom name
python3 deployment/standalone/backup-service.py --install-path /opt/thai-tokenizer create --name my-backup

# List available backups
python3 deployment/standalone/backup-service.py --install-path /opt/thai-tokenizer list

# Restore from backup
python3 deployment/standalone/backup-service.py --install-path /opt/thai-tokenizer restore /path/to/backup.tar.gz

# Restore specific components only
python3 deployment/standalone/backup-service.py --install-path /opt/thai-tokenizer restore /path/to/backup.tar.gz --components configuration service_state

# Clean up old backups (keep last 5)
python3 deployment/standalone/backup-service.py --install-path /opt/thai-tokenizer cleanup --keep 5
```

### Development and Debugging
```bash
# Run comprehensive diagnostics
python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer diagnostics

# Test specific components
python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test installation
python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test dependencies
python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test meilisearch
python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test tokenization

# Analyze logs
python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer logs --lines 200

# Interactive debugging session
python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer interactive
```

## Security Considerations

1. **File Permissions**: Configuration files are created with restricted permissions (600)
2. **API Keys**: Stored securely in environment variables
3. **Network Access**: Configure firewall rules as needed
4. **User Isolation**: Run service as non-root user
5. **Log Security**: Ensure log files don't contain sensitive data

## Integration with Existing Systems

### Systemd Integration
To integrate with systemd, you can create a service file that calls the standalone scripts:

```ini
[Unit]
Description=Thai Tokenizer Service
After=network.target

[Service]
Type=forking
User=thai-tokenizer
Group=thai-tokenizer
ExecStart=/opt/thai-tokenizer/bin/start-service.sh
ExecStop=/usr/bin/python3 /path/to/deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer stop
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Monitoring Integration
The service provides Prometheus-compatible metrics and structured logging for integration with monitoring systems.

### Load Balancer Integration
Configure your load balancer to use the health check endpoint: `http://service-host:8000/health`