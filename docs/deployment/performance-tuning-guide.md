# Performance Tuning and Optimization Guide

This guide provides comprehensive instructions for optimizing the Thai Tokenizer service performance across different deployment scenarios and workload patterns.

## Table of Contents

1. [Performance Targets](#performance-targets)
2. [System-Level Optimizations](#system-level-optimizations)
3. [Service Configuration Tuning](#service-configuration-tuning)
4. [Thai Tokenization Optimizations](#thai-tokenization-optimizations)
5. [Memory Management](#memory-management)
6. [Network and I/O Optimizations](#network-and-io-optimizations)
7. [Caching Strategies](#caching-strategies)
8. [Monitoring and Benchmarking](#monitoring-and-benchmarking)
9. [Deployment-Specific Optimizations](#deployment-specific-optimizations)
10. [Troubleshooting Performance Issues](#troubleshooting-performance-issues)

## Performance Targets

### Baseline Performance Requirements

- **Thai Tokenization**: < 50ms for 1000 Thai characters
- **API Response Time**: < 100ms for typical requests
- **Memory Usage**: < 256MB per container/process
- **Throughput**: > 500 documents/second for batch processing
- **Cold Start**: < 2 seconds container/service startup
- **Concurrent Requests**: Support 50+ concurrent requests

### Performance Measurement

```bash
# Basic performance test
curl -w "@curl-format.txt" -X POST http://localhost:8000/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "สวัสดีครับผมชื่อจอห์นมาจากประเทศไทย"}'

# Create curl-format.txt
cat > curl-format.txt << 'EOF'
     time_namelookup:  %{time_namelookup}\n
        time_connect:  %{time_connect}\n
     time_appconnect:  %{time_appconnect}\n
    time_pretransfer:  %{time_pretransfer}\n
       time_redirect:  %{time_redirect}\n
  time_starttransfer:  %{time_starttransfer}\n
                     ----------\n
          time_total:  %{time_total}\n
EOF

# Comprehensive benchmark
python3 deployment/scripts/benchmark.py \
  --host http://localhost:8000 \
  --concurrent-users 10 \
  --duration 60 \
  --thai-text-samples
```

## System-Level Optimizations

### Operating System Tuning

#### Kernel Parameters

```bash
# Optimize network performance
echo 'net.core.somaxconn = 65535' >> /etc/sysctl.conf
echo 'net.core.netdev_max_backlog = 5000' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 65535' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_fin_timeout = 30' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_keepalive_time = 1200' >> /etc/sysctl.conf

# Memory management
echo 'vm.swappiness = 10' >> /etc/sysctl.conf
echo 'vm.dirty_ratio = 15' >> /etc/sysctl.conf
echo 'vm.dirty_background_ratio = 5' >> /etc/sysctl.conf

# Apply changes
sudo sysctl -p
```

#### File Descriptor Limits

```bash
# Increase file descriptor limits
echo '* soft nofile 65535' >> /etc/security/limits.conf
echo '* hard nofile 65535' >> /etc/security/limits.conf
echo 'root soft nofile 65535' >> /etc/security/limits.conf
echo 'root hard nofile 65535' >> /etc/security/limits.conf

# For systemd services
mkdir -p /etc/systemd/system/thai-tokenizer.service.d
cat > /etc/systemd/system/thai-tokenizer.service.d/limits.conf << 'EOF'
[Service]
LimitNOFILE=65535
EOF

sudo systemctl daemon-reload
```

#### CPU Governor

```bash
# Set CPU governor to performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Make permanent
sudo apt install cpufrequtils
echo 'GOVERNOR="performance"' >> /etc/default/cpufrequtils
```

### Hardware Recommendations

#### CPU Optimization

- **Minimum**: 2 CPU cores
- **Recommended**: 4+ CPU cores for high-throughput deployments
- **Architecture**: x86_64 with AVX2 support for optimal PyThaiNLP performance

#### Memory Optimization

- **Minimum**: 1GB RAM
- **Recommended**: 2-4GB RAM for production workloads
- **Swap**: Configure 1-2GB swap for memory overflow protection

#### Storage Optimization

- **SSD Storage**: Use SSD for better I/O performance
- **Separate Volumes**: Separate volumes for logs, data, and application files
- **File System**: Use ext4 or xfs for optimal performance

## Service Configuration Tuning

### Worker Process Optimization

```json
{
  "service_config": {
    "worker_processes": "auto",
    "max_worker_connections": 1000,
    "worker_class": "uvicorn.workers.UvicornWorker",
    "preload_app": true,
    "max_requests": 1000,
    "max_requests_jitter": 100
  }
}
```

**Worker Process Guidelines**:
- **Single Core**: 1-2 workers
- **Dual Core**: 2-4 workers  
- **Quad Core**: 4-8 workers
- **8+ Cores**: 8-16 workers

### Resource Limits Configuration

```json
{
  "resource_config": {
    "memory_limit_mb": 1024,
    "cpu_limit_cores": 2.0,
    "max_concurrent_requests": 200,
    "request_timeout_seconds": 30,
    "connection_timeout_seconds": 10,
    "keepalive_timeout": 5
  }
}
```

### Connection Pool Optimization

```json
{
  "meilisearch_config": {
    "connection_pool_size": 20,
    "max_connections_per_host": 10,
    "keep_alive_timeout": 60,
    "connection_timeout": 10,
    "read_timeout": 30,
    "pool_recycle": 3600
  }
}
```

## Thai Tokenization Optimizations

### Engine Selection and Configuration

```json
{
  "tokenization_config": {
    "primary_engine": "newmm",
    "fallback_enabled": true,
    "fallback_engines": ["attacut", "deepcut"],
    "engine_timeout_ms": 100,
    "parallel_tokenization": true,
    "chunk_size": 1000,
    "max_text_length": 10000
  }
}
```

### Caching Configuration

```json
{
  "tokenization_config": {
    "cache_enabled": true,
    "cache_size": 50000,
    "cache_ttl_seconds": 7200,
    "cache_strategy": "lru",
    "preload_common_words": true,
    "preload_dictionary_size": 100000,
    "cache_compression": true
  }
}
```

### Batch Processing

```json
{
  "performance_config": {
    "batch_processing_enabled": true,
    "batch_size": 100,
    "batch_timeout_ms": 50,
    "parallel_batch_processing": true,
    "batch_queue_size": 1000
  }
}
```

### Dictionary Optimization

```bash
# Preload common Thai words
mkdir -p /opt/thai-tokenizer/data/dictionaries

# Create optimized word list
cat > /opt/thai-tokenizer/data/dictionaries/common_words.txt << 'EOF'
สวัสดี
ครับ
ค่ะ
ขอบคุณ
โรงเรียน
มหาวิทยาลัย
ประเทศไทย
กรุงเทพมหานคร
EOF

# Configure dictionary preloading
{
  "tokenization_config": {
    "custom_dictionary_path": "/opt/thai-tokenizer/data/dictionaries/common_words.txt",
    "dictionary_preload": true,
    "dictionary_cache_size": 10000
  }
}
```

## Memory Management

### Memory Pool Configuration

```json
{
  "memory_config": {
    "memory_pool_enabled": true,
    "memory_pool_size_mb": 256,
    "garbage_collection_threshold": 0.8,
    "memory_monitoring": true,
    "memory_alerts": true,
    "memory_cleanup_interval": 300
  }
}
```

### Garbage Collection Tuning

```bash
# Python garbage collection optimization
export PYTHONHASHSEED=0
export PYTHONOPTIMIZE=1
export PYTHONDONTWRITEBYTECODE=1

# Configure in service
{
  "python_config": {
    "gc_threshold": [700, 10, 10],
    "gc_debug": false,
    "memory_profiling": false
  }
}
```

### Memory Monitoring

```json
{
  "monitoring_config": {
    "memory_monitoring": true,
    "memory_threshold_mb": 800,
    "memory_alert_threshold": 0.9,
    "memory_cleanup_enabled": true,
    "oom_prevention": true
  }
}
```

## Network and I/O Optimizations

### HTTP Server Optimization

```json
{
  "server_config": {
    "keepalive_timeout": 5,
    "client_max_body_size": "10M",
    "client_body_timeout": 30,
    "client_header_timeout": 30,
    "send_timeout": 30,
    "tcp_nodelay": true,
    "tcp_nopush": true
  }
}
```

### Async I/O Configuration

```json
{
  "async_config": {
    "async_workers": 16,
    "event_loop": "uvloop",
    "async_timeout": 30,
    "connection_pool_size": 50,
    "max_keepalive_connections": 100
  }
}
```

### Compression

```json
{
  "compression_config": {
    "gzip_enabled": true,
    "gzip_level": 6,
    "gzip_min_length": 1000,
    "brotli_enabled": true,
    "response_compression": true
  }
}
```

## Caching Strategies

### Multi-Level Caching

```json
{
  "caching_config": {
    "l1_cache": {
      "type": "memory",
      "size": 10000,
      "ttl": 3600
    },
    "l2_cache": {
      "type": "redis",
      "host": "redis.internal",
      "size": 100000,
      "ttl": 86400
    },
    "cache_warming": true,
    "cache_prefetch": true
  }
}
```

### Result Caching

```json
{
  "result_caching": {
    "tokenization_cache": {
      "enabled": true,
      "size": 50000,
      "ttl": 7200,
      "key_strategy": "hash"
    },
    "response_cache": {
      "enabled": true,
      "size": 10000,
      "ttl": 1800,
      "vary_headers": ["Accept-Language"]
    }
  }
}
```

### Cache Warming

```bash
# Create cache warming script
cat > /opt/thai-tokenizer/scripts/warm_cache.py << 'EOF'
#!/usr/bin/env python3
import requests
import json

# Common Thai phrases for cache warming
phrases = [
    "สวัสดีครับ",
    "ขอบคุณมากครับ",
    "ยินดีที่ได้รู้จัก",
    "โรงเรียนมหาวิทยาลัย",
    "ประเทศไทยสวยงาม"
]

for phrase in phrases:
    response = requests.post(
        'http://localhost:8000/tokenize',
        json={'text': phrase}
    )
    print(f"Warmed cache for: {phrase}")
EOF

# Run cache warming on startup
chmod +x /opt/thai-tokenizer/scripts/warm_cache.py
```

## Monitoring and Benchmarking

### Performance Metrics

```json
{
  "metrics_config": {
    "detailed_metrics": true,
    "performance_tracking": true,
    "latency_percentiles": [50, 90, 95, 99],
    "throughput_tracking": true,
    "error_rate_tracking": true,
    "resource_usage_tracking": true
  }
}
```

### Benchmarking Tools

```bash
# Install benchmarking tools
pip install locust wrk

# Simple load test with curl
for i in {1..100}; do
  curl -s -w "%{time_total}\n" -X POST http://localhost:8000/tokenize \
    -H "Content-Type: application/json" \
    -d '{"text": "สวัสดีครับผมชื่อจอห์น"}' > /dev/null
done

# Advanced load testing with locust
cat > locustfile.py << 'EOF'
from locust import HttpUser, task, between

class ThaiTokenizerUser(HttpUser):
    wait_time = between(1, 3)
    
    @task
    def tokenize_thai(self):
        self.client.post("/tokenize", json={
            "text": "สวัสดีครับผมชื่อจอห์นมาจากประเทศไทย"
        })
    
    @task
    def health_check(self):
        self.client.get("/health")
EOF

# Run load test
locust -f locustfile.py --host=http://localhost:8000
```

### Continuous Performance Monitoring

```bash
# Create monitoring script
cat > /opt/thai-tokenizer/scripts/monitor_performance.sh << 'EOF'
#!/bin/bash

while true; do
    # CPU and Memory usage
    ps aux | grep thai-tokenizer | grep -v grep
    
    # Response time test
    curl -w "Response time: %{time_total}s\n" -s -X POST http://localhost:8000/tokenize \
      -H "Content-Type: application/json" \
      -d '{"text": "สวัสดีครับ"}' > /dev/null
    
    # Memory usage
    free -h
    
    echo "---"
    sleep 60
done
EOF

chmod +x /opt/thai-tokenizer/scripts/monitor_performance.sh
```

## Deployment-Specific Optimizations

### Docker Optimizations

```dockerfile
# Multi-stage build for smaller image
FROM python:3.12-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY . .

# Optimize Python
ENV PYTHONOPTIMIZE=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Performance settings
ENV UVICORN_WORKERS=4
ENV UVICORN_WORKER_CONNECTIONS=1000
```

```yaml
# docker-compose.yml optimizations
version: '3.8'
services:
  thai-tokenizer:
    image: thai-tokenizer:latest
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 1G
        reservations:
          cpus: '1.0'
          memory: 512M
    environment:
      - UVICORN_WORKERS=4
      - UVICORN_WORKER_CONNECTIONS=1000
    ulimits:
      nofile:
        soft: 65535
        hard: 65535
```

### Systemd Optimizations

```ini
# /etc/systemd/system/thai-tokenizer.service
[Unit]
Description=Thai Tokenizer Service
After=network.target

[Service]
Type=notify
User=thai-tokenizer
Group=thai-tokenizer
WorkingDirectory=/opt/thai-tokenizer
ExecStart=/opt/thai-tokenizer/venv/bin/uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always
RestartSec=5

# Performance optimizations
LimitNOFILE=65535
LimitNPROC=4096
MemoryLimit=1G
CPUQuota=200%

# Security optimizations
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/thai-tokenizer/logs /opt/thai-tokenizer/data

[Install]
WantedBy=multi-user.target
```

### Kubernetes Optimizations

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
        ports:
        - containerPort: 8000
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
        env:
        - name: UVICORN_WORKERS
          value: "4"
        - name: UVICORN_WORKER_CONNECTIONS
          value: "1000"
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
---
apiVersion: v1
kind: Service
metadata:
  name: thai-tokenizer-service
spec:
  selector:
    app: thai-tokenizer
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: thai-tokenizer-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: thai-tokenizer
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

## Troubleshooting Performance Issues

### Performance Diagnosis

```bash
# CPU profiling
python3 -m cProfile -o cpu_profile.stats -m src.api.main
python3 -c "
import pstats
p = pstats.Stats('cpu_profile.stats')
p.sort_stats('cumulative').print_stats(20)
"

# Memory profiling
pip install memory-profiler
python3 -m memory_profiler -m src.api.main

# I/O profiling
sudo iotop -p $(pgrep -f thai-tokenizer)
```

### Common Performance Issues

#### Slow Tokenization

**Symptoms**: Tokenization takes > 50ms for 1000 characters

**Solutions**:
1. Enable caching
2. Use faster tokenization engine
3. Implement batch processing
4. Optimize dictionary loading

#### High Memory Usage

**Symptoms**: Memory usage > 1GB per worker

**Solutions**:
1. Reduce cache sizes
2. Enable garbage collection
3. Limit concurrent requests
4. Use memory-efficient tokenization

#### High CPU Usage

**Symptoms**: CPU usage > 80% consistently

**Solutions**:
1. Reduce worker processes
2. Enable async processing
3. Implement request queuing
4. Optimize tokenization algorithms

### Performance Monitoring Dashboard

```bash
# Create Grafana dashboard configuration
cat > thai-tokenizer-dashboard.json << 'EOF'
{
  "dashboard": {
    "title": "Thai Tokenizer Performance",
    "panels": [
      {
        "title": "Response Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      },
      {
        "title": "Throughput",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "Requests/sec"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "graph",
        "targets": [
          {
            "expr": "process_resident_memory_bytes",
            "legendFormat": "Memory Usage"
          }
        ]
      }
    ]
  }
}
EOF
```

This comprehensive performance tuning guide provides detailed optimization strategies for maximizing the Thai Tokenizer service performance across different deployment scenarios and workload patterns.