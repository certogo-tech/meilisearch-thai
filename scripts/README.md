# Scripts Directory

This directory contains all the operational scripts for the Thai Tokenizer service.

## Directory Structure

### `deployment/`
Scripts for deploying and managing the production service:
- `deploy-production.sh` - Full production deployment with health checks
- `setup-production-tokenizer.sh` - Setup service with custom dictionary
- `final-wakame-fix.sh` - Apply the wakame tokenization fix
- `simple-rebuild.sh` - Simple rebuild and restart
- `rebuild-*.sh` - Various rebuild scripts for specific fixes
- `setup-ssl.sh` - SSL certificate setup
- `restart-service.sh` - Restart the service

### `testing/`
Scripts for testing the service functionality:
- `test-external-api.sh` - Comprehensive external API testing
- `test-wakame-tokenization.sh` - Test wakame tokenization specifically
- `test-service-health.sh` - Test service health and status
- `test-from-container.sh` - Test from inside Docker container

### `maintenance/`
Scripts for maintenance and debugging:
- `debug-dictionary.sh` - Debug custom dictionary loading
- `validate-env-config.sh` - Validate environment configuration
- `check-meilisearch.sh` - Check Meilisearch connectivity

## Usage

### Quick Deployment
```bash
# From project root
./deploy.sh production
```

### Quick Testing
```bash
# From project root
./deploy.sh test
```

### Direct Script Usage
```bash
# Run specific deployment script
./scripts/deployment/deploy-production.sh

# Run specific test
./scripts/testing/test-external-api.sh

# Run maintenance task
./scripts/maintenance/debug-dictionary.sh
```

## Script Dependencies

Most scripts require:
- Docker and Docker Compose
- curl for API testing
- Access to `.env.production` file
- Proper network connectivity to the service

## Environment

Scripts are designed to work with:
- Production environment at `https://search.cads.arda.or.th`
- Meilisearch at `http://10.0.2.105:7700`
- Docker containers for the Thai Tokenizer service
