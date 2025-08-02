# Configuration Examples

This document provides comprehensive configuration examples for different deployment scenarios of the Thai Tokenizer service.

## Table of Contents

1. [Basic Configurations](#basic-configurations)
2. [Production Configurations](#production-configurations)
3. [High-Performance Configurations](#high-performance-configurations)
4. [Security-Focused Configurations](#security-focused-configurations)
5. [Development Configurations](#development-configurations)
6. [Environment-Specific Examples](#environment-specific-examples)
7. [Integration Scenarios](#integration-scenarios)

## Basic Configurations

### Minimal Configuration

For simple development or testing environments:

```json
{
  "meilisearch_config": {
    "host": "http://localhost:7700",
    "api_key": "development-key"
  },
  "service_config": {
    "service_port": 8000
  }
}
```

**Environment Variables (Docker/Systemd)**:
```env
MEILISEARCH_HOST=http://localhost:7700
MEILISEARCH_API_KEY=development-key
THAI_TOKENIZER_SERVICE_PORT=8000
```

### Standard Configuration

For typical production deployments:

```json
{
  "meilisearch_config": {
    "host": "http://meilisearch.internal:7700",
    "api_key": "your-production-api-key",
    "timeout_seconds": 30,
    "max_retries": 3
  },
  "service_config": {
    "service_name": "thai-tokenizer",
    "service_port": 8000,
    "service_host": "0.0.0.0",
    "worker_processes": 2
  },
  "resource_config": {
    "memory_limit_mb": 512,
    "cpu_limit_cores": 1.0,
    "max_concurrent_requests": 50
  },
  "monitoring_config": {
    "log_level": "INFO",
    "metrics_enabled": true,
    "health_check_enabled": true
  }
}
```

## Production Configurations

### Enterprise Production

For large-scale enterprise deployments:

```json
{
  "meilisearch_config": {
    "host": "https://meilisearch-cluster.company.com",
    "port": 7700,
    "api_key": "enterprise-secure-api-key",
    "ssl_enabled": true,
    "ssl_verify": true,
    "timeout_seconds": 30,
    "max_retries": 3,
    "connection_pool_size": 20,
    "max_connections_per_host": 10
  },
  "service_config": {
    "service_name": "thai-tokenizer-prod",
    "service_port": 8000,
    "service_host": "0.0.0.0",
    "worker_processes": 4,
    "max_worker_connections": 1000
  },
  "resource_config": {
    "memory_limit_mb": 1024,
    "cpu_limit_cores": 2.0,
    "max_concurrent_requests": 200,
    "request_timeout_seconds": 60,
    "connection_timeout_seconds": 30
  },
  "security_config": {
    "allowed_hosts": [
      "tokenizer.company.com",
      "api.company.com",
      "10.0.0.0/8",
      "172.16.0.0/12"
    ],
    "cors_origins": [
      "https://app.company.com",
      "https://admin.company.com",
      "https://dashboard.company.com"
    ],
    "api_key_required": true,
    "api_key": "tokenizer-production-api-key",
    "rate_limiting_enabled": true,
    "rate_limit_requests_per_minute": 1000
  },
  "monitoring_config": {
    "log_level": "INFO",
    "log_file": "/var/log/thai-tokenizer/thai-tokenizer.log",
    "log_format": "json",
    "log_structured": true,
    "metrics_enabled": true,
    "health_check_enabled": true,
    "prometheus_metrics": true,
    "prometheus_port": 9090
  },
  "tokenization_config": {
    "cache_enabled": true,
    "cache_size": 10000,
    "cache_ttl_seconds": 3600,
    "preload_common_words": true,
    "fallback_enabled": true,
    "fallback_engines": ["attacut", "deepcut"]
  }
}
```

### Multi-Region Production

For geographically distributed deployments:

```json
{
  "meilisearch_config": {
    "host": "https://meilisearch-asia.company.com",
    "api_key": "region-asia-api-key",
    "ssl_enabled": true,
    "timeout_seconds": 45,
    "max_retries": 5,
    "retry_backoff_factor": 2.0,
    "connection_pool_size": 30
  },
  "service_config": {
    "service_name": "thai-tokenizer-asia",
    "service_port": 8000,
    "worker_processes": 6,
    "region": "asia-southeast",
    "datacenter": "singapore"
  },
  "resource_config": {
    "memory_limit_mb": 2048,
    "cpu_limit_cores": 4.0,
    "max_concurrent_requests": 500
  },
  "monitoring_config": {
    "log_level": "INFO",
    "metrics_enabled": true,
    "region_tag": "asia-southeast",
    "datacenter_tag": "singapore",
    "custom_metrics": {
      "region_latency": true,
      "cross_region_requests": true
    }
  },
  "performance_config": {
    "regional_optimization": true,
    "thai_language_priority": true,
    "local_cache_size": 20000
  }
}
```

## High-Performance Configurations

### High-Throughput Configuration

For maximum performance and throughput:

```json
{
  "meilisearch_config": {
    "host": "http://meilisearch-cluster.internal:7700",
    "api_key": "high-performance-key",
    "timeout_seconds": 10,
    "max_retries": 2,
    "connection_pool_size": 50,
    "max_connections_per_host": 25,
    "keep_alive_timeout": 60
  },
  "service_config": {
    "service_port": 8000,
    "service_host": "0.0.0.0",
    "worker_processes": 8,
    "max_worker_connections": 2000,
    "worker_class": "uvicorn.workers.UvicornWorker",
    "preload_app": true
  },
  "resource_config": {
    "memory_limit_mb": 4096,
    "cpu_limit_cores": 8.0,
    "max_concurrent_requests": 1000,
    "request_timeout_seconds": 30,
    "keepalive_timeout": 5
  },
  "performance_config": {
    "tokenization_cache_size": 50000,
    "connection_pool_size": 100,
    "async_workers": 32,
    "batch_processing_enabled": true,
    "batch_size": 200,
    "batch_timeout_ms": 25,
    "parallel_processing": true,
    "cpu_optimization": true,
    "memory_optimization": true
  },
  "tokenization_config": {
    "cache_enabled": true,
    "cache_size": 50000,
    "cache_ttl_seconds": 7200,
    "preload_common_words": true,
    "preload_dictionary_size": 100000,
    "fast_mode": true,
    "parallel_tokenization": true,
    "chunk_size": 1000
  },
  "monitoring_config": {
    "log_level": "WARNING",
    "metrics_enabled": true,
    "detailed_metrics": true,
    "performance_tracking": true,
    "latency_percentiles": [50, 90, 95, 99]
  }
}
```

### Memory-Optimized Configuration

For environments with limited memory:

```json
{
  "meilisearch_config": {
    "host": "http://localhost:7700",
    "api_key": "memory-optimized-key",
    "connection_pool_size": 5,
    "max_connections_per_host": 3
  },
  "service_config": {
    "service_port": 8000,
    "worker_processes": 1,
    "max_worker_connections": 100
  },
  "resource_config": {
    "memory_limit_mb": 128,
    "cpu_limit_cores": 0.5,
    "max_concurrent_requests": 10,
    "request_timeout_seconds": 60
  },
  "performance_config": {
    "tokenization_cache_size": 1000,
    "memory_efficient_mode": true,
    "lazy_loading": true,
    "garbage_collection_aggressive": true
  },
  "tokenization_config": {
    "cache_enabled": true,
    "cache_size": 1000,
    "cache_ttl_seconds": 1800,
    "preload_common_words": false,
    "memory_efficient_tokenization": true,
    "streaming_mode": true
  }
}
```

## Security-Focused Configurations

### High-Security Configuration

For security-critical environments:

```json
{
  "meilisearch_config": {
    "host": "https://secure-meilisearch.internal:7700",
    "api_key": "ultra-secure-api-key-with-rotation",
    "ssl_enabled": true,
    "ssl_verify": true,
    "ssl_cert_path": "/etc/ssl/certs/meilisearch-client.crt",
    "ssl_key_path": "/etc/ssl/private/meilisearch-client.key",
    "ssl_ca_path": "/etc/ssl/certs/company-ca.crt",
    "timeout_seconds": 30
  },
  "service_config": {
    "service_name": "thai-tokenizer-secure",
    "service_port": 8000,
    "service_host": "127.0.0.1",
    "worker_processes": 2
  },
  "security_config": {
    "allowed_hosts": [
      "127.0.0.1",
      "10.0.1.0/24"
    ],
    "cors_origins": [],
    "api_key_required": true,
    "api_key": "tokenizer-ultra-secure-key",
    "api_key_rotation_enabled": true,
    "api_key_rotation_interval_hours": 24,
    "rate_limiting_enabled": true,
    "rate_limit_requests_per_minute": 100,
    "rate_limit_burst": 20,
    "request_signing_enabled": true,
    "request_encryption_enabled": true,
    "audit_logging_enabled": true,
    "security_headers": {
      "X-Content-Type-Options": "nosniff",
      "X-Frame-Options": "DENY",
      "X-XSS-Protection": "1; mode=block",
      "Strict-Transport-Security": "max-age=31536000; includeSubDomains"
    }
  },
  "monitoring_config": {
    "log_level": "INFO",
    "security_logging": true,
    "audit_trail": true,
    "failed_auth_logging": true,
    "suspicious_activity_detection": true
  },
  "compliance_config": {
    "data_retention_days": 90,
    "log_encryption": true,
    "pii_detection": true,
    "gdpr_compliance": true
  }
}
```

### Network-Isolated Configuration

For air-gapped or highly isolated environments:

```json
{
  "meilisearch_config": {
    "host": "http://192.168.100.10:7700",
    "api_key": "isolated-network-key",
    "timeout_seconds": 60,
    "max_retries": 5,
    "connection_pool_size": 3
  },
  "service_config": {
    "service_port": 8000,
    "service_host": "192.168.100.20",
    "worker_processes": 2
  },
  "security_config": {
    "allowed_hosts": [
      "192.168.100.0/24"
    ],
    "cors_origins": [],
    "api_key_required": true,
    "network_isolation": true,
    "external_connections_blocked": true
  },
  "monitoring_config": {
    "log_level": "INFO",
    "external_logging_disabled": true,
    "local_metrics_only": true,
    "network_monitoring": true
  },
  "offline_config": {
    "offline_mode_enabled": true,
    "local_dictionary_path": "/opt/thai-tokenizer/data/dictionaries",
    "fallback_tokenization": true,
    "cache_persistence": true
  }
}
```

## Development Configurations

### Local Development

For local development environments:

```json
{
  "meilisearch_config": {
    "host": "http://localhost:7700",
    "api_key": "dev-key-123",
    "timeout_seconds": 10
  },
  "service_config": {
    "service_port": 8000,
    "service_host": "127.0.0.1",
    "worker_processes": 1,
    "reload": true,
    "debug": true
  },
  "resource_config": {
    "memory_limit_mb": 256,
    "max_concurrent_requests": 10
  },
  "monitoring_config": {
    "log_level": "DEBUG",
    "log_format": "text",
    "console_logging": true,
    "file_logging": false,
    "metrics_enabled": false
  },
  "development_config": {
    "hot_reload": true,
    "debug_mode": true,
    "profiling_enabled": true,
    "test_data_enabled": true,
    "mock_meilisearch": false
  }
}
```

### Testing Configuration

For automated testing environments:

```json
{
  "meilisearch_config": {
    "host": "http://test-meilisearch:7700",
    "api_key": "test-api-key",
    "timeout_seconds": 5
  },
  "service_config": {
    "service_port": 8001,
    "worker_processes": 1
  },
  "testing_config": {
    "test_mode": true,
    "mock_external_services": true,
    "deterministic_responses": true,
    "test_data_preload": true,
    "performance_testing": false
  },
  "monitoring_config": {
    "log_level": "ERROR",
    "console_logging": false,
    "file_logging": true,
    "test_logging": true
  }
}
```

## Environment-Specific Examples

### Docker Compose Environment Variables

```env
# .env file for Docker Compose
COMPOSE_PROJECT_NAME=thai-tokenizer

# Meilisearch Configuration
MEILISEARCH_HOST=http://meilisearch:7700
MEILISEARCH_API_KEY=docker-compose-key
MEILISEARCH_SSL_ENABLED=false
MEILISEARCH_TIMEOUT=30

# Service Configuration
THAI_TOKENIZER_SERVICE_NAME=thai-tokenizer
THAI_TOKENIZER_SERVICE_PORT=8000
THAI_TOKENIZER_SERVICE_HOST=0.0.0.0
THAI_TOKENIZER_WORKER_PROCESSES=2

# Resource Configuration
THAI_TOKENIZER_MEMORY_LIMIT_MB=512
THAI_TOKENIZER_CPU_LIMIT_CORES=1.0
THAI_TOKENIZER_MAX_CONCURRENT_REQUESTS=50

# Security Configuration
THAI_TOKENIZER_ALLOWED_HOSTS=localhost,127.0.0.1,thai-tokenizer
THAI_TOKENIZER_CORS_ORIGINS=
THAI_TOKENIZER_API_KEY_REQUIRED=false

# Monitoring Configuration
THAI_TOKENIZER_LOG_LEVEL=INFO
THAI_TOKENIZER_METRICS_ENABLED=true
THAI_TOKENIZER_HEALTH_CHECK_ENABLED=true

# Docker-specific
DOCKER_RESTART_POLICY=unless-stopped
DOCKER_NETWORK=thai-tokenizer-network
```

### Systemd Environment File

```env
# /etc/thai-tokenizer/environment
THAI_TOKENIZER_SERVICE_NAME=thai-tokenizer
THAI_TOKENIZER_SERVICE_PORT=8000
THAI_TOKENIZER_SERVICE_HOST=127.0.0.1
THAI_TOKENIZER_WORKER_PROCESSES=2

THAI_TOKENIZER_MEILISEARCH_HOST=http://localhost:7700
THAI_TOKENIZER_MEILISEARCH_API_KEY=systemd-production-key
THAI_TOKENIZER_MEILISEARCH_SSL_ENABLED=false
THAI_TOKENIZER_MEILISEARCH_TIMEOUT=30

THAI_TOKENIZER_MEMORY_LIMIT_MB=512
THAI_TOKENIZER_CPU_LIMIT_CORES=1.0
THAI_TOKENIZER_MAX_CONCURRENT_REQUESTS=50

THAI_TOKENIZER_ALLOWED_HOSTS=localhost,127.0.0.1
THAI_TOKENIZER_CORS_ORIGINS=
THAI_TOKENIZER_API_KEY_REQUIRED=false

THAI_TOKENIZER_LOG_LEVEL=INFO
THAI_TOKENIZER_LOG_FILE=/var/log/thai-tokenizer/thai-tokenizer.log
THAI_TOKENIZER_METRICS_ENABLED=true
THAI_TOKENIZER_HEALTH_CHECK_ENABLED=true

# Systemd-specific
PYTHONPATH=/opt/thai-tokenizer/src
PYTHONUNBUFFERED=1
```

### Kubernetes ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: thai-tokenizer-config
  namespace: thai-tokenizer
data:
  config.json: |
    {
      "meilisearch_config": {
        "host": "http://meilisearch-service:7700",
        "api_key": "k8s-cluster-key",
        "timeout_seconds": 30,
        "max_retries": 3
      },
      "service_config": {
        "service_name": "thai-tokenizer-k8s",
        "service_port": 8000,
        "service_host": "0.0.0.0",
        "worker_processes": 2
      },
      "resource_config": {
        "memory_limit_mb": 512,
        "cpu_limit_cores": 1.0,
        "max_concurrent_requests": 100
      },
      "monitoring_config": {
        "log_level": "INFO",
        "log_format": "json",
        "metrics_enabled": true,
        "prometheus_metrics": true,
        "kubernetes_integration": true
      }
    }
```

## Integration Scenarios

### Load Balancer Integration

Configuration for use behind a load balancer:

```json
{
  "service_config": {
    "service_port": 8000,
    "service_host": "0.0.0.0",
    "worker_processes": 4,
    "behind_proxy": true,
    "proxy_headers": true
  },
  "security_config": {
    "allowed_hosts": [
      "tokenizer.company.com",
      "10.0.0.0/8"
    ],
    "trust_proxy_headers": true,
    "proxy_ip_whitelist": [
      "10.0.1.100",
      "10.0.1.101"
    ]
  },
  "monitoring_config": {
    "real_ip_header": "X-Forwarded-For",
    "health_check_path": "/health",
    "metrics_path": "/metrics"
  }
}
```

### API Gateway Integration

Configuration for use with API gateways:

```json
{
  "service_config": {
    "service_port": 8000,
    "api_prefix": "/api/v1/tokenizer",
    "worker_processes": 3
  },
  "security_config": {
    "api_key_required": true,
    "api_key_header": "X-API-Key",
    "cors_origins": ["*"],
    "cors_methods": ["GET", "POST"],
    "cors_headers": ["Content-Type", "Authorization", "X-API-Key"]
  },
  "integration_config": {
    "api_gateway": true,
    "request_id_header": "X-Request-ID",
    "correlation_id_header": "X-Correlation-ID",
    "timeout_header": "X-Timeout"
  }
}
```

### Microservices Architecture

Configuration for microservices deployment:

```json
{
  "meilisearch_config": {
    "host": "http://meilisearch-service.search.svc.cluster.local:7700",
    "api_key": "microservice-key",
    "service_discovery": true
  },
  "service_config": {
    "service_name": "thai-tokenizer-service",
    "service_port": 8000,
    "service_host": "0.0.0.0",
    "worker_processes": 2
  },
  "microservices_config": {
    "service_mesh": true,
    "circuit_breaker": true,
    "retry_policy": {
      "max_retries": 3,
      "backoff_factor": 2.0,
      "max_backoff": 30
    },
    "health_check": {
      "interval": 30,
      "timeout": 5,
      "retries": 3
    }
  },
  "monitoring_config": {
    "distributed_tracing": true,
    "jaeger_endpoint": "http://jaeger-collector:14268/api/traces",
    "metrics_enabled": true,
    "service_metrics": true
  }
}
```

### Multi-Tenant Configuration

Configuration for multi-tenant deployments:

```json
{
  "meilisearch_config": {
    "host": "http://meilisearch-cluster:7700",
    "api_key": "multi-tenant-master-key",
    "tenant_isolation": true
  },
  "service_config": {
    "service_port": 8000,
    "worker_processes": 4,
    "multi_tenant": true
  },
  "tenant_config": {
    "tenant_header": "X-Tenant-ID",
    "tenant_isolation": true,
    "per_tenant_limits": {
      "requests_per_minute": 100,
      "memory_limit_mb": 128,
      "cache_size": 1000
    },
    "tenant_specific_config": {
      "tenant-a": {
        "meilisearch_index": "tenant-a-documents",
        "api_key": "tenant-a-key"
      },
      "tenant-b": {
        "meilisearch_index": "tenant-b-documents",
        "api_key": "tenant-b-key"
      }
    }
  }
}
```

This comprehensive configuration examples document covers various deployment scenarios and provides ready-to-use configurations for different environments and use cases.