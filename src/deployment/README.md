# Thai Tokenizer Deployment Configuration System

This module provides comprehensive configuration management for deploying the Thai Tokenizer service to integrate with existing Meilisearch infrastructure.

## Features

- **OnPremiseConfig Model**: Comprehensive configuration with validation for existing Meilisearch integration
- **Configuration Templates**: Pre-configured templates for Docker, systemd, and standalone deployment methods
- **Secure Credential Management**: Environment variable support with proper secret handling
- **Meilisearch Connection Testing**: Utilities to validate connections and API access
- **Configuration Export**: Generate deployment files (Docker Compose, systemd units, environment files)

## Quick Start

### 1. Create a Configuration

```python
from deployment.templates import DeploymentTemplates
from deployment.config import SecurityLevel

# Create Docker deployment configuration
config = DeploymentTemplates.create_docker_template(
    meilisearch_host="http://localhost:7700",
    meilisearch_api_key="your-api-key",
    service_port=8000,
    security_level=SecurityLevel.STANDARD
)
```

### 2. Test Meilisearch Connection

```python
from deployment.config import MeilisearchConnectionTester

tester = MeilisearchConnectionTester(config.meilisearch_config)
result = await tester.test_connection()

if result.status == ConnectionStatus.CONNECTED:
    print(f"Connected! Version: {result.meilisearch_version}")
else:
    print(f"Connection failed: {result.error_message}")
```

### 3. Validate Configuration

```python
from deployment.config import ConfigurationValidator

validator = ConfigurationValidator(config)
result = await validator.validate_full_configuration()

if result.valid:
    print("Configuration is valid!")
else:
    print("Validation errors:", result.errors)
```

### 4. Export Configuration

```python
from deployment.templates import ConfigurationExporter

# Export as Docker Compose
compose_content = ConfigurationExporter.to_docker_compose(config)
with open("docker-compose.yml", "w") as f:
    f.write(compose_content)

# Export as environment file
env_content = ConfigurationExporter.to_env_file(config)
with open(".env", "w") as f:
    f.write(env_content)
```

## Deployment Methods

### Docker Deployment
- **Best for**: Production environments with container orchestration
- **Features**: Complete isolation, easy scaling, built-in health checks
- **Requirements**: Docker Engine 20.10+

### Systemd Service
- **Best for**: Traditional Linux server environments
- **Features**: Native system integration, automatic startup/restart
- **Requirements**: Linux with systemd, Python 3.12+

### Standalone Python
- **Best for**: Development, testing, simple deployments
- **Features**: Simple setup, direct Python access, cross-platform
- **Requirements**: Python 3.12+, virtual environment

## Configuration Components

### MeilisearchConnectionConfig
- Host URL and port configuration
- API key authentication
- SSL/TLS settings
- Timeout and retry configuration

### ServiceConfig
- Service name and port
- Worker process configuration
- System user/group settings

### SecurityConfig
- Security level (basic, standard, high)
- CORS and host restrictions
- API key authentication
- SSL certificate configuration

### ResourceConfig
- Memory and CPU limits
- Concurrent request limits
- Metrics configuration

### MonitoringConfig
- Health check settings
- Logging configuration
- Prometheus metrics

## Environment Variables

The system generates comprehensive environment variables for deployment:

```bash
# Service Configuration
THAI_TOKENIZER_SERVICE_NAME=thai-tokenizer
THAI_TOKENIZER_SERVICE_PORT=8000

# Meilisearch Configuration
THAI_TOKENIZER_MEILISEARCH_HOST=http://localhost:7700
THAI_TOKENIZER_MEILISEARCH_API_KEY=your-api-key

# Security Configuration
THAI_TOKENIZER_ALLOWED_HOSTS=localhost,127.0.0.1
THAI_TOKENIZER_API_KEY_REQUIRED=false

# Resource Configuration
THAI_TOKENIZER_MEMORY_LIMIT_MB=512
THAI_TOKENIZER_CPU_LIMIT_CORES=1.0
```

## Security Levels

### Basic
- Minimal security restrictions
- Suitable for development environments
- All hosts and CORS origins allowed

### Standard (Recommended)
- Balanced security and usability
- Restricted hosts and CORS origins
- Optional API key authentication

### High
- Maximum security restrictions
- API key authentication required
- HTTPS enforcement
- Strict host and CORS policies

## Examples

See `examples/deployment_config_demo.py` for comprehensive usage examples.

## Testing

Run the test suite:

```bash
python3 -m pytest tests/unit/test_deployment_config.py -v
```

## Integration with Existing Meilisearch

This system is designed to integrate with existing Meilisearch installations:

1. **Connection Testing**: Validates connectivity and API permissions
2. **Configuration Validation**: Ensures compatibility with existing setup
3. **Secure Credential Management**: Protects API keys and sensitive data
4. **Flexible Deployment**: Supports various deployment scenarios

The configuration system respects existing Meilisearch settings and provides the Thai Tokenizer service as an additional layer for enhanced Thai text processing.