# Thai Tokenizer CLI and Automation Tools

This document provides comprehensive documentation for the Thai Tokenizer deployment CLI and automation tools, including command-line interface usage, automation scripts, and pipeline integration utilities.

## Overview

The Thai Tokenizer deployment system includes:

1. **Command-Line Interface (CLI)** - Interactive deployment tool
2. **Deployment Automation** - Automated deployment scripts
3. **Pipeline Integration** - CI/CD pipeline templates and utilities
4. **Configuration Management** - Automated configuration management tools

## Command-Line Interface (CLI)

### Installation and Setup

The CLI tool is available as `scripts/thai-tokenizer-deploy`:

```bash
# Make the CLI executable
chmod +x scripts/thai-tokenizer-deploy

# Add to PATH (optional)
export PATH=$PATH:$(pwd)/scripts

# Verify installation
thai-tokenizer-deploy --help
```

### Basic Usage

```bash
# Interactive deployment setup
thai-tokenizer-deploy deploy --interactive

# Deploy with configuration file
thai-tokenizer-deploy deploy --config config.json --method docker

# Validate system requirements
thai-tokenizer-deploy validate-system --config config.json

# Generate configuration template
thai-tokenizer-deploy generate-config --method docker --output config.json
```

### Available Commands

#### Deployment Commands

**`deploy`** - Deploy Thai Tokenizer service
```bash
thai-tokenizer-deploy deploy [OPTIONS]

Options:
  -m, --method {docker,systemd,standalone}  Deployment method
  -i, --interactive                         Interactive setup
  --dry-run                                 Validate without deploying
  --force                                   Force deployment despite warnings
  --progress-file FILE                      Progress updates file
  --output-dir DIR                          Artifacts output directory
```

Examples:
```bash
# Interactive deployment
thai-tokenizer-deploy deploy --interactive

# Docker deployment with config
thai-tokenizer-deploy deploy --config docker-config.json --method docker

# Dry run validation
thai-tokenizer-deploy deploy --config config.json --dry-run

# Force deployment with progress tracking
thai-tokenizer-deploy deploy --config config.json --force --progress-file progress.json
```

#### Validation Commands

**`validate-system`** - Validate system requirements
```bash
thai-tokenizer-deploy validate-system [OPTIONS]

Options:
  -m, --method {docker,systemd,standalone}  Deployment method to validate
  --report-file FILE                        Save validation report
  --format {json,html,markdown}             Report format
```

**`validate-config`** - Validate deployment configuration
```bash
thai-tokenizer-deploy validate-config [OPTIONS]

Options:
  --fix                                     Attempt to fix issues
```

**`validate-meilisearch`** - Validate Meilisearch connectivity
```bash
thai-tokenizer-deploy validate-meilisearch [OPTIONS]

Options:
  --host URL                                Meilisearch host URL
  --api-key KEY                             Meilisearch API key
```

Examples:
```bash
# System validation with report
thai-tokenizer-deploy validate-system --config config.json --report-file validation.html --format html

# Configuration validation with auto-fix
thai-tokenizer-deploy validate-config --config config.json --fix

# Meilisearch connectivity test
thai-tokenizer-deploy validate-meilisearch --host http://localhost:7700 --api-key your-key
```

#### Management Commands

**`status`** - Check deployment status
```bash
thai-tokenizer-deploy status [OPTIONS]

Options:
  --deployment-id ID                        Deployment ID to check
  --service-name NAME                       Service name to check
  --detailed                                Show detailed information
```

**`stop`** - Stop deployed service
```bash
thai-tokenizer-deploy stop [OPTIONS]

Options:
  --deployment-id ID                        Deployment ID to stop
  --service-name NAME                       Service name to stop
  --force                                   Force stop
```

**`restart`** - Restart deployed service
```bash
thai-tokenizer-deploy restart [OPTIONS]

Options:
  --deployment-id ID                        Deployment ID to restart
  --service-name NAME                       Service name to restart
```

**`cleanup`** - Clean up deployment resources
```bash
thai-tokenizer-deploy cleanup [OPTIONS]

Options:
  --deployment-id ID                        Deployment ID to clean up
  --all                                     Clean up all deployments
  --force                                   Force cleanup without confirmation
```

#### Configuration Commands

**`generate-config`** - Generate configuration template
```bash
thai-tokenizer-deploy generate-config [OPTIONS]

Options:
  -m, --method {docker,systemd,standalone}  Deployment method (required)
  -o, --output FILE                         Output file (required)
  -i, --interactive                         Interactive generation
  --example                                 Generate with sample values
```

**`show-config`** - Display configuration
```bash
thai-tokenizer-deploy show-config [OPTIONS]

Options:
  --format {json,yaml,table}                Output format
  --mask-secrets                            Mask sensitive information
```

**`edit-config`** - Edit deployment configuration
```bash
thai-tokenizer-deploy edit-config [OPTIONS]

Options:
  --editor EDITOR                           Text editor to use
```

Examples:
```bash
# Generate Docker configuration template
thai-tokenizer-deploy generate-config --method docker --output docker-config.json --example

# Show configuration in table format
thai-tokenizer-deploy show-config --config config.json --format table --mask-secrets

# Interactive configuration generation
thai-tokenizer-deploy generate-config --method systemd --output systemd-config.json --interactive
```

#### Utility Commands

**`test`** - Test deployed service
```bash
thai-tokenizer-deploy test [OPTIONS]

Options:
  --service-url URL                         Service URL to test
  --test-type {health,tokenization,performance,security,all}  Test type
  --report-file FILE                        Save test report
```

**`logs`** - View service logs
```bash
thai-tokenizer-deploy logs [OPTIONS]

Options:
  --deployment-id ID                        Deployment ID
  --service-name NAME                       Service name
  -f, --follow                              Follow log output
  -n, --lines N                             Number of lines to show
```

**`version`** - Show version information
```bash
thai-tokenizer-deploy version [OPTIONS]

Options:
  --detailed                                Show detailed version info
```

Examples:
```bash
# Test all functionality
thai-tokenizer-deploy test --service-url http://localhost:8000 --test-type all

# Follow service logs
thai-tokenizer-deploy logs --service-name thai-tokenizer --follow

# Show detailed version
thai-tokenizer-deploy version --detailed
```

### Interactive Configuration Setup

The CLI provides an interactive configuration wizard:

```bash
thai-tokenizer-deploy deploy --interactive
```

The wizard will guide you through:
1. Deployment method selection
2. Meilisearch configuration
3. Service configuration
4. Security settings
5. Resource limits
6. Installation paths

### Global Options

All commands support these global options:

```bash
Options:
  -c, --config FILE                         Configuration file path
  -v, --verbose                             Enable verbose logging
  -q, --quiet                               Suppress non-essential output
  --log-file FILE                           Log file path
```

## Deployment Automation

### Automated Deployment Script

The deployment automation script provides hands-free deployment:

```bash
python scripts/automation/deploy_automation.py [OPTIONS]
```

#### Options

```bash
--config FILE                               Configuration file
--environment {development,staging,production}  Target environment
--output-dir DIR                            Output directory
--skip-validation                           Skip pre-deployment validation
--batch ENV1 ENV2 ...                       Deploy to multiple environments
--parallel                                  Run batch deployments in parallel
```

#### Examples

```bash
# Single environment deployment
python scripts/automation/deploy_automation.py --environment production

# Batch deployment to multiple environments
python scripts/automation/deploy_automation.py --batch development staging production

# Parallel batch deployment
python scripts/automation/deploy_automation.py --batch development staging --parallel

# Custom configuration with validation skip
python scripts/automation/deploy_automation.py --config custom-config.json --environment staging --skip-validation
```

#### Environment-Specific Settings

The automation script automatically configures settings based on environment:

**Development Environment:**
- Security level: Basic
- Memory limit: 128MB
- Debug logging enabled
- CORS origins: `["*"]`
- API key authentication: Disabled

**Staging Environment:**
- Security level: Standard
- Memory limit: 256MB
- Info logging
- Restricted CORS origins
- API key authentication: Enabled

**Production Environment:**
- Security level: Strict
- Memory limit: 512MB
- Warning-level logging
- Strict CORS policy
- API key authentication: Required
- HTTPS enabled

#### Automation Features

1. **Pre-deployment Validation**
   - System requirements check
   - Meilisearch connectivity test
   - Configuration validation

2. **Deployment Execution**
   - Progress tracking
   - Error handling
   - Rollback on failure

3. **Post-deployment Verification**
   - Health checks
   - Performance testing
   - Security validation

4. **Reporting**
   - JSON and HTML reports
   - Deployment artifacts
   - Recommendations

## Pipeline Integration

### Generate Pipeline Templates

```bash
python scripts/automation/pipeline_integration.py [OPTIONS]
```

#### Options

```bash
--pipeline {github,gitlab,jenkins,azure,all}  Pipeline type
--environments ENV1 ENV2 ...                  Target environments
--deployment-method METHOD                     Deployment method
--no-tests                                     Exclude test stages
--output-dir DIR                               Output directory
```

#### Examples

```bash
# Generate all pipeline templates
python scripts/automation/pipeline_integration.py --pipeline all

# Generate GitHub Actions workflow
python scripts/automation/pipeline_integration.py --pipeline github --environments dev staging prod

# Generate GitLab CI without tests
python scripts/automation/pipeline_integration.py --pipeline gitlab --no-tests

# Generate Jenkins pipeline for Docker deployment
python scripts/automation/pipeline_integration.py --pipeline jenkins --deployment-method docker
```

### Generated Pipeline Files

The pipeline integration tool generates:

1. **GitHub Actions** (`.github/workflows/deploy.yml`)
2. **GitLab CI** (`.gitlab-ci.yml`)
3. **Jenkins Pipeline** (`Jenkinsfile`)
4. **Azure DevOps** (`azure-pipelines.yml`)
5. **Docker Compose Overrides** (`docker-compose.{env}.yml`)
6. **Deployment Scripts** (`quick_deploy.sh`, `rollback.sh`, `health_check.sh`)

### Pipeline Features

- **Multi-environment support** with environment-specific configurations
- **Automated testing** integration with deployment tests
- **Artifact management** for deployment results and reports
- **Security scanning** and validation
- **Rollback capabilities** for failed deployments
- **Notification integration** for deployment status

### Environment Variables for Pipelines

Configure these secrets/variables in your CI/CD platform:

```bash
# Meilisearch Configuration
MEILISEARCH_HOST_DEV=http://dev-meilisearch:7700
MEILISEARCH_HOST_STAGING=https://staging-meilisearch.example.com
MEILISEARCH_HOST_PRODUCTION=https://meilisearch.example.com

MEILISEARCH_API_KEY_DEV=dev-api-key
MEILISEARCH_API_KEY_STAGING=staging-api-key
MEILISEARCH_API_KEY_PRODUCTION=production-api-key

# Service Configuration
SERVICE_PORT_DEV=8000
SERVICE_PORT_STAGING=8000
SERVICE_PORT_PRODUCTION=8000

# Security Configuration
ALLOWED_HOST_STAGING=staging.example.com
ALLOWED_HOST_PRODUCTION=production.example.com

CORS_ORIGIN_STAGING=https://staging-app.example.com
CORS_ORIGIN_PRODUCTION=https://app.example.com
```

## Configuration Management

### Configuration Management Tool

```bash
python scripts/automation/config_management.py COMMAND [OPTIONS]
```

#### Commands

**`generate`** - Generate configuration from template
```bash
python scripts/automation/config_management.py generate --template TEMPLATE --output FILE
```

**`validate`** - Validate all configurations
```bash
python scripts/automation/config_management.py validate --config-dir DIR
```

**`drift-check`** - Check for configuration drift
```bash
python scripts/automation/config_management.py drift-check --output CONFIG_FILE
```

**`backup`** - Backup configurations
```bash
python scripts/automation/config_management.py backup
```

**`list-templates`** - List available templates
```bash
python scripts/automation/config_management.py list-templates
```

#### Examples

```bash
# Generate production configuration
python scripts/automation/config_management.py generate \
  --template docker-production \
  --output prod-config.json \
  --env-vars env-vars.json

# Validate all configurations
python scripts/automation/config_management.py validate --config-dir configs/

# Check for configuration drift
python scripts/automation/config_management.py drift-check --output configs/production.json

# Backup all configurations
python scripts/automation/config_management.py backup

# List available templates
python scripts/automation/config_management.py list-templates
```

### Configuration Templates

Available built-in templates:

1. **`docker-development`** - Docker deployment for development
2. **`docker-production`** - Docker deployment for production
3. **`systemd-production`** - Systemd deployment for production

### Secret Management

The configuration management tool includes secure secret handling:

- **Encryption**: Secrets are encrypted using Fernet symmetric encryption
- **Key Management**: Encryption keys are stored securely in `~/.thai-tokenizer/secret.key`
- **Automatic Detection**: API keys and passwords are automatically encrypted
- **Environment Variables**: Supports environment variable substitution

### Configuration Validation

Built-in validation rules:
- **Type checking**: Ensures correct data types
- **Range validation**: Validates numeric ranges
- **Choice validation**: Validates enum values
- **Required fields**: Ensures required fields are present

### Configuration Drift Detection

Monitor configuration changes:
- **Hash-based detection**: Uses SHA-256 hashes to detect changes
- **Baseline management**: Maintains configuration baselines
- **Change tracking**: Identifies specific changed fields
- **Automated alerts**: Can be integrated with monitoring systems

## Best Practices

### CLI Usage

1. **Use Interactive Mode** for initial setup and learning
2. **Save Configurations** for reproducible deployments
3. **Validate Before Deploy** using `--dry-run` option
4. **Monitor Progress** with `--progress-file` option
5. **Test After Deployment** using the `test` command

### Automation

1. **Environment-Specific Configs** for different deployment targets
2. **Pre-deployment Validation** to catch issues early
3. **Progress Monitoring** for long-running deployments
4. **Artifact Collection** for troubleshooting and auditing
5. **Rollback Planning** for failed deployments

### Pipeline Integration

1. **Environment Promotion** from development to production
2. **Automated Testing** at each stage
3. **Security Scanning** before production deployment
4. **Artifact Management** for deployment packages
5. **Notification Setup** for deployment status

### Configuration Management

1. **Template Usage** for consistent configurations
2. **Secret Encryption** for sensitive data
3. **Version Control** for configuration files
4. **Drift Monitoring** for configuration compliance
5. **Regular Backups** for disaster recovery

## Troubleshooting

### Common Issues

1. **Permission Errors**
   ```bash
   # Fix script permissions
   chmod +x scripts/thai-tokenizer-deploy
   chmod +x scripts/automation/*.py
   ```

2. **Missing Dependencies**
   ```bash
   # Install required packages
   pip install uv
   uv pip install -r requirements.txt
   ```

3. **Configuration Validation Errors**
   ```bash
   # Validate configuration
   thai-tokenizer-deploy validate-config --config config.json --fix
   ```

4. **Meilisearch Connection Issues**
   ```bash
   # Test connectivity
   thai-tokenizer-deploy validate-meilisearch --host http://localhost:7700
   ```

5. **Service Health Check Failures**
   ```bash
   # Test service health
   thai-tokenizer-deploy test --service-url http://localhost:8000 --test-type health
   ```

### Debug Mode

Enable verbose logging for troubleshooting:

```bash
# CLI debug mode
thai-tokenizer-deploy --verbose deploy --config config.json

# Automation debug mode
python scripts/automation/deploy_automation.py --environment dev 2>&1 | tee debug.log

# Set log level
export LOG_LEVEL=DEBUG
```

### Log Files

Default log file locations:
- CLI logs: `deployment.log`
- Automation logs: `automation_output/automation.log`
- Service logs: Check deployment-specific log paths

## Integration Examples

### GitHub Actions Integration

```yaml
name: Deploy Thai Tokenizer
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      - name: Install dependencies
        run: |
          pip install uv
          uv pip install -r requirements.txt
      - name: Deploy to production
        run: |
          python scripts/automation/deploy_automation.py --environment production
        env:
          MEILISEARCH_HOST: ${{ secrets.MEILISEARCH_HOST }}
          MEILISEARCH_API_KEY: ${{ secrets.MEILISEARCH_API_KEY }}
```

### Docker Compose Integration

```yaml
version: '3.8'
services:
  thai-tokenizer:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MEILISEARCH_HOST=http://meilisearch:7700
      - MEILISEARCH_API_KEY=${MEILISEARCH_API_KEY}
    depends_on:
      - meilisearch
    healthcheck:
      test: ["CMD", "python", "scripts/thai-tokenizer-deploy", "test", "--test-type", "health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### Monitoring Integration

```bash
#!/bin/bash
# Health check script for monitoring systems

# Check service health
if thai-tokenizer-deploy test --service-url http://localhost:8000 --test-type health; then
    echo "Service healthy"
    exit 0
else
    echo "Service unhealthy"
    exit 1
fi
```

This comprehensive CLI and automation system provides everything needed for professional Thai Tokenizer deployment management, from interactive setup to fully automated CI/CD pipeline integration.