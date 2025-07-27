# Configuration Directory

This directory contains environment-specific configuration files and templates for the Thai Tokenizer MeiliSearch integration system.

## 📁 Directory Structure

```
config/
├── development/       # Development environment configuration
│   ├── .env.template # Development environment template
│   └── README.md     # Development configuration guide
├── production/        # Production environment configuration
│   ├── .env.template # Production environment template
│   ├── .env.prod     # Production environment file (not in git)
│   └── README.md     # Production configuration guide
├── testing/          # Testing environment configuration
│   ├── .env.test     # Testing environment file
│   └── README.md     # Testing configuration guide
└── staging/          # Staging environment configuration
    ├── .env.staging  # Staging environment file
    └── README.md     # Staging configuration guide
```

## 🔧 Environment Configuration

### Development Environment
**File**: `development/.env.template`

Contains configuration for local development:
- Local service URLs (localhost)
- Development-friendly settings
- Debug mode enabled
- Relaxed security settings
- Sample API keys

### Production Environment
**File**: `production/.env.template`

Contains configuration for production deployment:
- Production service URLs
- Security-hardened settings
- Performance optimizations
- Monitoring and logging configuration
- Placeholder values for secrets

### Testing Environment
**File**: `testing/.env.test`

Contains configuration for automated testing:
- Test database connections
- Mock service configurations
- Test-specific timeouts
- Isolated test environment settings

### Staging Environment
**File**: `staging/.env.staging`

Contains configuration for staging/pre-production:
- Production-like settings
- Staging service URLs
- Performance testing configuration
- Integration testing setup

## 🚀 Quick Setup

### Development Setup
```bash
# Copy development template
cp config/development/.env.template .env

# Edit configuration as needed
nano .env

# Start development services
docker compose up -d
```

### Production Setup
```bash
# Copy production template
cp config/production/.env.template config/production/.env.prod

# Configure production values
nano config/production/.env.prod

# Deploy to production
./deployment/scripts/deploy_production.sh
```

## ⚙️ Configuration Categories

### Core Service Configuration
- **Service Names**: Unique identifiers for services
- **Ports**: Service port assignments
- **Hosts**: Service host configurations
- **API Keys**: Authentication and authorization

### MeiliSearch Configuration
- **Host URL**: MeiliSearch server location
- **API Key**: Master key for MeiliSearch access
- **Index Names**: Default index configurations
- **Performance Settings**: Memory, threads, timeouts

### Tokenizer Configuration
- **Engine Selection**: PyThaiNLP, attacut, deepcut
- **Model Versions**: Specific model versions to use
- **Processing Settings**: Batch sizes, timeouts, retries
- **Custom Dictionaries**: Additional vocabulary

### Performance Configuration
- **Worker Processes**: Number of worker processes
- **Memory Limits**: Container memory constraints
- **Cache Settings**: Caching configuration
- **Optimization Flags**: Performance tuning options

### Security Configuration
- **CORS Origins**: Allowed cross-origin requests
- **SSL/TLS**: Certificate and encryption settings
- **Authentication**: API authentication methods
- **Rate Limiting**: Request rate limiting

### Monitoring Configuration
- **Log Levels**: Logging verbosity
- **Metrics Collection**: Performance metrics
- **Health Checks**: Service health monitoring
- **Alerting**: Alert configuration

## 🔐 Security Best Practices

### Environment Files
- **Never commit** `.env.prod` or other environment files with secrets
- **Use templates** for sharing configuration structure
- **Rotate secrets** regularly in production
- **Use strong passwords** and API keys

### Access Control
- **Limit permissions** to configuration files
- **Use service accounts** for automated deployments
- **Implement least privilege** access
- **Audit configuration** changes

### Secret Management
- **Use external secret stores** for production (AWS Secrets Manager, HashiCorp Vault)
- **Encrypt sensitive data** at rest
- **Use environment variables** for runtime secrets
- **Implement secret rotation** procedures

## 📝 Configuration Reference

### Required Variables
```bash
# Service Configuration
THAI_TOKENIZER_SERVICE_NAME=thai-tokenizer
THAI_TOKENIZER_VERSION=1.0.0
THAI_TOKENIZER_LOG_LEVEL=INFO

# MeiliSearch Configuration
MEILISEARCH_HOST=http://localhost:7700
MEILISEARCH_API_KEY=masterKey
MEILISEARCH_INDEX=documents

# Tokenizer Configuration
TOKENIZER_ENGINE=pythainlp
TOKENIZER_MODEL=latest
BATCH_SIZE=100
```

### Optional Variables
```bash
# Performance Tuning
WORKER_PROCESSES=4
MAX_RETRIES=3
TIMEOUT_MS=5000
CACHE_SIZE=1000

# Security
CORS_ORIGINS=*
DEBUG_MODE=false
SSL_ENABLED=false

# Monitoring
METRICS_ENABLED=true
HEALTH_CHECK_INTERVAL=30
LOG_FORMAT=json
```

## 🔄 Environment Management

### Development to Production
1. **Start with development** template
2. **Test thoroughly** in development
3. **Copy to staging** for integration testing
4. **Adapt for production** with security hardening
5. **Deploy with monitoring** and rollback capability

### Configuration Validation
```bash
# Validate configuration syntax
python -c "import os; from dotenv import load_dotenv; load_dotenv('.env')"

# Test configuration with services
docker compose config

# Validate production deployment
./deployment/scripts/deploy_production.sh health
```

## 📚 Related Documentation

- **[Development Guide](../docs/development/README.md)** - Development environment setup
- **[Production Deployment](../docs/deployment/PRODUCTION_DEPLOYMENT.md)** - Production configuration
- **[Performance Optimizations](../docs/deployment/PERFORMANCE_OPTIMIZATIONS.md)** - Performance tuning
- **[Troubleshooting Guide](../docs/troubleshooting.md)** - Configuration issues

## 🤝 Contributing Configuration

To contribute configuration improvements:

1. **Test thoroughly** in your environment
2. **Update templates** with new options
3. **Document changes** in environment README files
4. **Provide examples** of usage
5. **Submit pull request** with clear description

### Configuration Guidelines
- Use clear, descriptive variable names
- Include comments explaining complex settings
- Provide sensible defaults
- Document security implications
- Test across environments

---

**Need help with configuration?** Check the environment-specific README files or the [Development Guide](../docs/development/README.md) for detailed setup instructions!