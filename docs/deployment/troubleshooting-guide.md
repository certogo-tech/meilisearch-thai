# Troubleshooting Guide

This comprehensive troubleshooting guide helps diagnose and resolve common issues with the Thai Tokenizer service deployment and operation.

## Table of Contents

1. [Quick Diagnosis](#quick-diagnosis)
2. [Service Startup Issues](#service-startup-issues)
3. [Meilisearch Connection Issues](#meilisearch-connection-issues)
4. [Performance Issues](#performance-issues)
5. [Thai Tokenization Issues](#thai-tokenization-issues)
6. [Network and Security Issues](#network-and-security-issues)
7. [Resource and Memory Issues](#resource-and-memory-issues)
8. [Configuration Issues](#configuration-issues)
9. [Deployment-Specific Issues](#deployment-specific-issues)
10. [Monitoring and Logging Issues](#monitoring-and-logging-issues)

## Quick Diagnosis

### Health Check Commands

```bash
# Basic service health
curl http://localhost:8000/health

# Detailed health information
curl http://localhost:8000/health/detailed

# Service metrics
curl http://localhost:8000/metrics

# Test Thai tokenization
curl -X POST http://localhost:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "สวัสดีครับ"}'
```

### Service Status Commands

**Docker Deployment**:
```bash
docker ps | grep thai-tokenizer
docker logs thai-tokenizer
docker stats thai-tokenizer
```

**Systemd Deployment**:
```bash
systemctl status thai-tokenizer
journalctl -u thai-tokenizer -f
systemctl show thai-tokenizer --property=MemoryCurrent,CPUUsageNSec
```

**Standalone Deployment**:
```bash
/opt/thai-tokenizer/bin/status-service.sh
python3 deployment/standalone/manage-service.py --install-path /opt/thai-tokenizer status
tail -f /opt/thai-tokenizer/logs/thai-tokenizer.log
```

### Common Log Locations

- **Docker**: `docker logs thai-tokenizer`
- **Systemd**: `journalctl -u thai-tokenizer` or `/var/log/thai-tokenizer/`
- **Standalone**: `/opt/thai-tokenizer/logs/thai-tokenizer.log`

## Service Startup Issues

### Issue: Service Won't Start

**Symptoms**:
- Service exits immediately after startup
- "Failed to start" error messages
- Process not found in process list

**Diagnosis Steps**:

1. **Check service status**:
   ```bash
   # Docker
   docker ps -a | grep thai-tokenizer
   docker logs thai-tokenizer
   
   # Systemd
   systemctl status thai-tokenizer
   journalctl -u thai-tokenizer -n 50
   
   # Standalone
   /opt/thai-tokenizer/bin/status-service.sh
   cat /opt/thai-tokenizer/logs/thai-tokenizer.log
   ```

2. **Verify Python environment**:
   ```bash
   # Check Python version
   python3 --version
   
   # Test virtual environment (standalone)
   /opt/thai-tokenizer/venv/bin/python --version
   /opt/thai-tokenizer/venv/bin/python -c "import pythainlp; print('OK')"
   
   # Test dependencies
   /opt/thai-tokenizer/venv/bin/python -c "import fastapi, uvicorn; print('OK')"
   ```

3. **Check configuration syntax**:
   ```bash
   # Validate JSON configuration
   python3 -c "import json; print(json.load(open('/path/to/config.json')))"
   
   # Check environment variables
   env | grep THAI_TOKENIZER
   ```

**Common Solutions**:

1. **Python Version Issues**:
   ```bash
   # Install correct Python version
   sudo apt install python3.12 python3.12-venv python3.12-dev
   
   # Recreate virtual environment
   python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer --remove
   python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer
   ```

2. **Missing Dependencies**:
   ```bash
   # Reinstall dependencies
   python3 deployment/standalone/install-dependencies.py --venv-path /opt/thai-tokenizer/venv
   
   # Or with pip fallback
   python3 deployment/standalone/install-dependencies.py --venv-path /opt/thai-tokenizer/venv --no-uv
   ```

3. **Permission Issues**:
   ```bash
   # Fix ownership
   sudo chown -R thai-tokenizer:thai-tokenizer /opt/thai-tokenizer
   sudo chown -R thai-tokenizer:thai-tokenizer /var/lib/thai-tokenizer
   sudo chown -R thai-tokenizer:thai-tokenizer /var/log/thai-tokenizer
   
   # Fix permissions
   chmod -R 755 /opt/thai-tokenizer
   chmod 600 /opt/thai-tokenizer/config/config.json
   ```

4. **Configuration Issues**:
   ```bash
   # Validate configuration
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test configuration
   
   # Reset to default configuration
   python3 deployment/standalone/configure-service.py --install-path /opt/thai-tokenizer --reset
   ```

### Issue: Service Starts But Exits Immediately

**Symptoms**:
- Service appears to start successfully
- Process exits within seconds
- No obvious error messages

**Diagnosis Steps**:

1. **Enable debug logging**:
   ```bash
   # Edit configuration to enable debug
   nano /opt/thai-tokenizer/config/config.json
   # Set "log_level": "DEBUG"
   
   # Or set environment variable
   export THAI_TOKENIZER_LOG_LEVEL=DEBUG
   ```

2. **Run service in foreground**:
   ```bash
   # Standalone
   /opt/thai-tokenizer/venv/bin/python -m src.api.main
   
   # Docker
   docker run -it --rm thai-tokenizer python -m src.api.main
   ```

3. **Check for port conflicts**:
   ```bash
   sudo ss -tulpn | grep :8000
   sudo lsof -i :8000
   ```

**Solutions**:

1. **Port Already in Use**:
   ```bash
   # Find and stop conflicting service
   sudo lsof -i :8000
   sudo kill -9 <PID>
   
   # Or change service port
   nano /opt/thai-tokenizer/config/config.json
   # Change "service_port": 8001
   ```

2. **Resource Limits**:
   ```bash
   # Check system resources
   free -h
   df -h
   
   # Reduce resource requirements
   nano /opt/thai-tokenizer/config/config.json
   # Reduce "memory_limit_mb" and "worker_processes"
   ```

## Meilisearch Connection Issues

### Issue: Cannot Connect to Meilisearch

**Symptoms**:
- "Connection refused" errors
- "Timeout" errors
- Service starts but health check fails

**Diagnosis Steps**:

1. **Test Meilisearch connectivity**:
   ```bash
   # Basic connectivity
   curl http://your-meilisearch-host:7700/health
   
   # With authentication
   curl -H "Authorization: Bearer YOUR_API_KEY" http://your-meilisearch-host:7700/health
   
   # Test from service host
   telnet your-meilisearch-host 7700
   ping your-meilisearch-host
   ```

2. **Check DNS resolution**:
   ```bash
   nslookup your-meilisearch-host
   dig your-meilisearch-host
   ```

3. **Verify network connectivity**:
   ```bash
   # Check routing
   traceroute your-meilisearch-host
   
   # Check firewall rules
   sudo iptables -L
   sudo ufw status
   ```

**Solutions**:

1. **Incorrect Meilisearch URL**:
   ```bash
   # Update configuration
   nano /opt/thai-tokenizer/config/config.json
   # Correct "host" field: "http://correct-host:7700"
   ```

2. **Authentication Issues**:
   ```bash
   # Verify API key
   curl -H "Authorization: Bearer YOUR_API_KEY" http://your-meilisearch-host:7700/keys
   
   # Update API key in configuration
   nano /opt/thai-tokenizer/config/config.json
   # Update "api_key" field
   ```

3. **Network/Firewall Issues**:
   ```bash
   # Allow outbound connections
   sudo ufw allow out 7700
   
   # Check corporate firewall/proxy settings
   export HTTP_PROXY=http://proxy.company.com:8080
   export HTTPS_PROXY=http://proxy.company.com:8080
   ```

4. **SSL/TLS Issues**:
   ```bash
   # For HTTPS Meilisearch, verify SSL
   openssl s_client -connect your-meilisearch-host:7700
   
   # Disable SSL verification (not recommended for production)
   nano /opt/thai-tokenizer/config/config.json
   # Set "ssl_verify": false
   ```

### Issue: Meilisearch Authentication Failed

**Symptoms**:
- "Invalid API key" errors
- "Unauthorized" responses
- 401/403 HTTP status codes

**Diagnosis Steps**:

1. **Verify API key format**:
   ```bash
   # Check key length and format
   echo "YOUR_API_KEY" | wc -c
   echo "YOUR_API_KEY" | grep -E '^[a-zA-Z0-9_-]+$'
   ```

2. **Test API key directly**:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" http://your-meilisearch-host:7700/keys
   ```

3. **Check Meilisearch logs**:
   ```bash
   # Check Meilisearch server logs for authentication attempts
   docker logs meilisearch  # If Meilisearch is in Docker
   journalctl -u meilisearch  # If Meilisearch is systemd service
   ```

**Solutions**:

1. **Generate New API Key**:
   ```bash
   # Connect to Meilisearch and create new key
   curl -X POST 'http://your-meilisearch-host:7700/keys' \
     -H 'Authorization: Bearer MASTER_KEY' \
     -H 'Content-Type: application/json' \
     --data-binary '{
       "description": "Thai Tokenizer Service Key",
       "actions": ["search", "documents.add", "documents.get", "documents.delete", "indexes.create", "indexes.get", "indexes.update", "indexes.delete", "settings.get", "settings.update"],
       "indexes": ["*"],
       "expiresAt": null
     }'
   ```

2. **Update Configuration**:
   ```bash
   # Update API key in configuration
   nano /opt/thai-tokenizer/config/config.json
   # Update "api_key" field with new key
   
   # Restart service
   /opt/thai-tokenizer/bin/restart-service.sh
   ```

## Performance Issues

### Issue: Slow Thai Tokenization

**Symptoms**:
- Tokenization takes longer than 50ms for 1000 characters
- High response times
- Timeout errors

**Diagnosis Steps**:

1. **Run performance benchmark**:
   ```bash
   python3 deployment/scripts/benchmark.py --host http://localhost:8000
   python3 deployment/scripts/demo_thai_tokenizer.py --benchmark --iterations 1000
   ```

2. **Check resource usage**:
   ```bash
   # CPU and memory usage
   top -p $(pgrep -f thai-tokenizer)
   htop
   
   # System load
   uptime
   iostat 1 5
   ```

3. **Profile the application**:
   ```bash
   # Enable profiling
   python3 -m cProfile -o profile.stats -m src.api.main
   
   # Analyze profile
   python3 -c "import pstats; p = pstats.Stats('profile.stats'); p.sort_stats('cumulative').print_stats(20)"
   ```

**Solutions**:

1. **Enable Caching**:
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

2. **Increase Resources**:
   ```json
   {
     "resource_config": {
       "memory_limit_mb": 1024,
       "cpu_limit_cores": 2.0,
       "max_concurrent_requests": 100
     },
     "service_config": {
       "worker_processes": 4
     }
   }
   ```

3. **Optimize Tokenization**:
   ```json
   {
     "tokenization_config": {
       "fast_mode": true,
       "parallel_tokenization": true,
       "chunk_size": 1000,
       "batch_processing_enabled": true
     }
   }
   ```

### Issue: High Memory Usage

**Symptoms**:
- Memory usage exceeds configured limits
- Out of memory errors
- System becomes unresponsive

**Diagnosis Steps**:

1. **Monitor memory usage**:
   ```bash
   # Process memory usage
   ps aux | grep thai-tokenizer
   pmap $(pgrep -f thai-tokenizer)
   
   # System memory
   free -h
   cat /proc/meminfo
   ```

2. **Check for memory leaks**:
   ```bash
   # Monitor over time
   while true; do
     ps aux | grep thai-tokenizer | grep -v grep
     sleep 60
   done
   
   # Use valgrind (if available)
   valgrind --tool=memcheck --leak-check=full python3 -m src.api.main
   ```

**Solutions**:

1. **Reduce Cache Size**:
   ```json
   {
     "tokenization_config": {
       "cache_size": 1000,
       "cache_ttl_seconds": 1800
     },
     "performance_config": {
       "memory_efficient_mode": true,
       "garbage_collection_aggressive": true
     }
   }
   ```

2. **Limit Worker Processes**:
   ```json
   {
     "service_config": {
       "worker_processes": 1
     },
     "resource_config": {
       "memory_limit_mb": 256,
       "max_concurrent_requests": 10
     }
   }
   ```

3. **Enable Memory Monitoring**:
   ```json
   {
     "monitoring_config": {
       "memory_monitoring": true,
       "memory_threshold_mb": 400,
       "memory_alerts": true
     }
   }
   ```

## Thai Tokenization Issues

### Issue: Incorrect Thai Tokenization Results

**Symptoms**:
- Thai text not properly segmented
- Missing or incorrect word boundaries
- Mixed Thai-English text issues

**Diagnosis Steps**:

1. **Test tokenization directly**:
   ```bash
   # Test with sample Thai text
   curl -X POST http://localhost:8000/tokenize \
     -H "Content-Type: application/json" \
     -d '{"text": "สวัสดีครับผมชื่อจอห์น"}'
   
   # Test with mixed Thai-English
   curl -X POST http://localhost:8000/tokenize \
     -H "Content-Type: application/json" \
     -d '{"text": "Hello สวัสดี World โลก"}'
   ```

2. **Check PyThaiNLP installation**:
   ```bash
   /opt/thai-tokenizer/venv/bin/python -c "
   import pythainlp
   print('PyThaiNLP version:', pythainlp.__version__)
   from pythainlp import word_tokenize
   print('Test:', word_tokenize('สวัสดีครับ'))
   "
   ```

3. **Test fallback engines**:
   ```bash
   /opt/thai-tokenizer/venv/bin/python -c "
   from pythainlp import word_tokenize
   print('newmm:', word_tokenize('สวัสดีครับ', engine='newmm'))
   print('attacut:', word_tokenize('สวัสดีครับ', engine='attacut'))
   print('deepcut:', word_tokenize('สวัสดีครับ', engine='deepcut'))
   "
   ```

**Solutions**:

1. **Update PyThaiNLP**:
   ```bash
   /opt/thai-tokenizer/venv/bin/pip install --upgrade pythainlp
   
   # Download latest models
   /opt/thai-tokenizer/venv/bin/python -c "
   import pythainlp.corpus
   pythainlp.corpus.download('thai2fit_wv')
   pythainlp.corpus.download('thaisum')
   "
   ```

2. **Configure Fallback Engines**:
   ```json
   {
     "tokenization_config": {
       "primary_engine": "newmm",
       "fallback_enabled": true,
       "fallback_engines": ["attacut", "deepcut"],
       "mixed_language_support": true
     }
   }
   ```

3. **Add Custom Dictionary**:
   ```bash
   # Add custom words to dictionary
   mkdir -p /opt/thai-tokenizer/data/dictionaries
   echo "คำศัพท์เฉพาะ" >> /opt/thai-tokenizer/data/dictionaries/custom_words.txt
   ```

### Issue: Thai Text Encoding Problems

**Symptoms**:
- Garbled Thai characters
- Question marks or boxes instead of Thai text
- Encoding errors in logs

**Diagnosis Steps**:

1. **Check system locale**:
   ```bash
   locale
   echo $LANG
   echo $LC_ALL
   ```

2. **Test character encoding**:
   ```bash
   # Test UTF-8 support
   echo "สวัสดี" | hexdump -C
   python3 -c "print('สวัสดี'.encode('utf-8'))"
   ```

3. **Check file encoding**:
   ```bash
   file -i /opt/thai-tokenizer/config/config.json
   ```

**Solutions**:

1. **Set Correct Locale**:
   ```bash
   # Install Thai locale
   sudo locale-gen th_TH.UTF-8
   
   # Set environment variables
   export LANG=en_US.UTF-8
   export LC_ALL=en_US.UTF-8
   export PYTHONIOENCODING=utf-8
   ```

2. **Fix Configuration Files**:
   ```bash
   # Ensure config files are UTF-8
   iconv -f ISO-8859-1 -t UTF-8 config.json > config_utf8.json
   mv config_utf8.json config.json
   ```

3. **Update Service Configuration**:
   ```json
   {
     "service_config": {
       "encoding": "utf-8",
       "locale": "en_US.UTF-8"
     }
   }
   ```

## Network and Security Issues

### Issue: CORS Errors

**Symptoms**:
- Browser console shows CORS errors
- "Access-Control-Allow-Origin" errors
- Cross-origin requests blocked

**Diagnosis Steps**:

1. **Test CORS headers**:
   ```bash
   curl -H "Origin: https://your-frontend.com" \
        -H "Access-Control-Request-Method: POST" \
        -H "Access-Control-Request-Headers: Content-Type" \
        -X OPTIONS http://localhost:8000/tokenize
   ```

2. **Check current CORS configuration**:
   ```bash
   curl -I http://localhost:8000/health | grep -i cors
   ```

**Solutions**:

1. **Configure CORS Origins**:
   ```json
   {
     "security_config": {
       "cors_origins": [
         "https://your-frontend.com",
         "https://admin.company.com",
         "http://localhost:3000"
       ],
       "cors_methods": ["GET", "POST", "OPTIONS"],
       "cors_headers": ["Content-Type", "Authorization"]
     }
   }
   ```

2. **Allow All Origins (Development Only)**:
   ```json
   {
     "security_config": {
       "cors_origins": ["*"]
     }
   }
   ```

### Issue: SSL/TLS Certificate Problems

**Symptoms**:
- SSL certificate verification errors
- "Certificate verify failed" errors
- HTTPS connection issues

**Diagnosis Steps**:

1. **Test SSL certificate**:
   ```bash
   openssl s_client -connect your-meilisearch-host:7700 -servername your-meilisearch-host
   curl -v https://your-meilisearch-host:7700/health
   ```

2. **Check certificate details**:
   ```bash
   echo | openssl s_client -connect your-meilisearch-host:7700 2>/dev/null | openssl x509 -noout -dates
   ```

**Solutions**:

1. **Update CA Certificates**:
   ```bash
   sudo apt update && sudo apt install ca-certificates
   sudo update-ca-certificates
   ```

2. **Add Custom CA Certificate**:
   ```bash
   # Copy custom CA certificate
   sudo cp your-ca.crt /usr/local/share/ca-certificates/
   sudo update-ca-certificates
   ```

3. **Disable SSL Verification (Not Recommended)**:
   ```json
   {
     "meilisearch_config": {
       "ssl_verify": false
     }
   }
   ```

## Resource and Memory Issues

### Issue: Service Killed by OOM Killer

**Symptoms**:
- Service suddenly stops
- "Killed" messages in logs
- System logs show OOM killer activity

**Diagnosis Steps**:

1. **Check system logs**:
   ```bash
   dmesg | grep -i "killed process"
   journalctl -k | grep -i "out of memory"
   grep -i "out of memory" /var/log/syslog
   ```

2. **Monitor memory usage**:
   ```bash
   # System memory
   free -h
   cat /proc/meminfo
   
   # Process memory
   ps aux --sort=-%mem | head -10
   ```

**Solutions**:

1. **Increase System Memory**:
   - Add more RAM to the system
   - Configure swap space

2. **Reduce Service Memory Usage**:
   ```json
   {
     "resource_config": {
       "memory_limit_mb": 256,
       "max_concurrent_requests": 10
     },
     "service_config": {
       "worker_processes": 1
     },
     "tokenization_config": {
       "cache_size": 1000,
       "memory_efficient_mode": true
     }
   }
   ```

3. **Configure Memory Limits**:
   ```bash
   # For systemd
   sudo systemctl edit thai-tokenizer
   # Add:
   # [Service]
   # MemoryLimit=512M
   
   # For Docker
   docker run --memory=512m thai-tokenizer
   ```

### Issue: High CPU Usage

**Symptoms**:
- CPU usage consistently high
- System becomes slow
- High load average

**Diagnosis Steps**:

1. **Monitor CPU usage**:
   ```bash
   top -p $(pgrep -f thai-tokenizer)
   htop
   iostat 1 5
   ```

2. **Profile CPU usage**:
   ```bash
   # Use perf (if available)
   sudo perf top -p $(pgrep -f thai-tokenizer)
   
   # Python profiling
   python3 -m cProfile -o cpu_profile.stats -m src.api.main
   ```

**Solutions**:

1. **Optimize Worker Configuration**:
   ```json
   {
     "service_config": {
       "worker_processes": 2,
       "max_worker_connections": 100
     },
     "resource_config": {
       "cpu_limit_cores": 1.0,
       "max_concurrent_requests": 20
     }
   }
   ```

2. **Enable CPU Optimization**:
   ```json
   {
     "performance_config": {
       "cpu_optimization": true,
       "parallel_processing": false,
       "batch_processing_enabled": true
     }
   }
   ```

## Configuration Issues

### Issue: Invalid Configuration Format

**Symptoms**:
- JSON parsing errors
- "Invalid configuration" errors
- Service fails to start with config errors

**Diagnosis Steps**:

1. **Validate JSON syntax**:
   ```bash
   python3 -m json.tool /opt/thai-tokenizer/config/config.json
   jq . /opt/thai-tokenizer/config/config.json
   ```

2. **Check configuration schema**:
   ```bash
   python3 deployment/standalone/debug-utilities.py --install-path /opt/thai-tokenizer test configuration
   ```

**Solutions**:

1. **Fix JSON Syntax**:
   ```bash
   # Use a JSON validator
   python3 -c "
   import json
   try:
       with open('/opt/thai-tokenizer/config/config.json') as f:
           json.load(f)
       print('JSON is valid')
   except json.JSONDecodeError as e:
       print(f'JSON error: {e}')
   "
   ```

2. **Reset to Default Configuration**:
   ```bash
   python3 deployment/standalone/configure-service.py --install-path /opt/thai-tokenizer --reset
   ```

### Issue: Environment Variable Conflicts

**Symptoms**:
- Configuration values not applied
- Unexpected behavior
- Environment variables not recognized

**Diagnosis Steps**:

1. **Check environment variables**:
   ```bash
   env | grep THAI_TOKENIZER | sort
   printenv | grep THAI_TOKENIZER
   ```

2. **Test variable precedence**:
   ```bash
   # Check which config source is used
   python3 -c "
   import os
   print('Config file:', os.path.exists('/opt/thai-tokenizer/config/config.json'))
   print('Env vars:', [k for k in os.environ if k.startswith('THAI_TOKENIZER')])
   "
   ```

**Solutions**:

1. **Clear Conflicting Variables**:
   ```bash
   # Unset conflicting environment variables
   unset $(env | grep THAI_TOKENIZER | cut -d= -f1)
   
   # Or set them explicitly
   export THAI_TOKENIZER_SERVICE_PORT=8000
   ```

2. **Use Configuration File Priority**:
   ```bash
   # Remove environment variables and use config file only
   unset $(env | grep THAI_TOKENIZER | cut -d= -f1)
   /opt/thai-tokenizer/bin/restart-service.sh
   ```

## Deployment-Specific Issues

### Docker Issues

**Issue: Container Won't Start**

```bash
# Check container status
docker ps -a | grep thai-tokenizer

# Check container logs
docker logs thai-tokenizer

# Inspect container
docker inspect thai-tokenizer

# Run container interactively
docker run -it --rm thai-tokenizer /bin/bash
```

**Issue: Volume Mount Problems**

```bash
# Check volume mounts
docker inspect thai-tokenizer | grep -A 10 "Mounts"

# Fix permissions
sudo chown -R 1000:1000 /host/path/to/data
```

### Systemd Issues

**Issue: Service Won't Enable**

```bash
# Check service file syntax
systemd-analyze verify /etc/systemd/system/thai-tokenizer.service

# Reload systemd
sudo systemctl daemon-reload

# Check service dependencies
systemctl list-dependencies thai-tokenizer
```

**Issue: Service Fails to Start**

```bash
# Check service status
systemctl status thai-tokenizer -l

# Check service logs
journalctl -u thai-tokenizer -f

# Check service file
cat /etc/systemd/system/thai-tokenizer.service
```

### Standalone Issues

**Issue: Virtual Environment Problems**

```bash
# Check virtual environment
/opt/thai-tokenizer/venv/bin/python --version
/opt/thai-tokenizer/venv/bin/pip list

# Recreate virtual environment
python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer --remove
python3 deployment/standalone/setup-venv.py --install-path /opt/thai-tokenizer
```

**Issue: Process Management Problems**

```bash
# Check process status
ps aux | grep thai-tokenizer

# Check PID file
cat /opt/thai-tokenizer/run/thai-tokenizer.pid

# Manual process cleanup
pkill -f thai-tokenizer
rm -f /opt/thai-tokenizer/run/thai-tokenizer.pid
```

## Monitoring and Logging Issues

### Issue: Logs Not Generated

**Symptoms**:
- No log files created
- Empty log files
- Missing log entries

**Diagnosis Steps**:

1. **Check log configuration**:
   ```bash
   # Check log file path
   ls -la /opt/thai-tokenizer/logs/
   ls -la /var/log/thai-tokenizer/
   
   # Check permissions
   ls -la /opt/thai-tokenizer/logs/thai-tokenizer.log
   ```

2. **Test logging**:
   ```bash
   # Test log writing
   echo "Test log entry" >> /opt/thai-tokenizer/logs/thai-tokenizer.log
   ```

**Solutions**:

1. **Fix Log Directory Permissions**:
   ```bash
   sudo mkdir -p /opt/thai-tokenizer/logs
   sudo chown -R thai-tokenizer:thai-tokenizer /opt/thai-tokenizer/logs
   sudo chmod 755 /opt/thai-tokenizer/logs
   ```

2. **Configure Logging**:
   ```json
   {
     "monitoring_config": {
       "log_level": "INFO",
       "log_file": "/opt/thai-tokenizer/logs/thai-tokenizer.log",
       "console_logging": true,
       "file_logging": true
     }
   }
   ```

### Issue: Metrics Not Available

**Symptoms**:
- `/metrics` endpoint returns 404
- No Prometheus metrics
- Monitoring dashboard shows no data

**Diagnosis Steps**:

1. **Test metrics endpoint**:
   ```bash
   curl http://localhost:8000/metrics
   curl http://localhost:8000/health/detailed
   ```

2. **Check metrics configuration**:
   ```bash
   grep -i metrics /opt/thai-tokenizer/config/config.json
   ```

**Solutions**:

1. **Enable Metrics**:
   ```json
   {
     "monitoring_config": {
       "metrics_enabled": true,
       "prometheus_metrics": true,
       "detailed_metrics": true
     }
   }
   ```

2. **Configure Metrics Port**:
   ```json
   {
     "monitoring_config": {
       "prometheus_port": 9090,
       "metrics_path": "/metrics"
     }
   }
   ```

This comprehensive troubleshooting guide covers the most common issues encountered when deploying and operating the Thai Tokenizer service. For issues not covered here, enable debug logging and examine the detailed error messages for specific guidance.