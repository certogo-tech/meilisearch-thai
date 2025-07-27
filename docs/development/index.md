# Development Documentation

This directory contains comprehensive guides for developing and contributing to the Thai Tokenizer MeiliSearch integration system.

## Available Guides

### [Development Setup Guide](README.md)
Complete guide for setting up the development environment and getting started with the codebase.

**Contents:**
- Quick start with Docker Compose
- Local development setup
- API usage examples and testing
- Code quality tools and testing procedures
- Contribution guidelines

**Target Audience:** Developers, contributors, and anyone wanting to understand the system

## Quick Navigation

### For New Developers
1. Start with [Development Setup Guide](README.md)
2. Follow the Quick Start section for basic setup
3. Review the API usage examples
4. Set up your development environment
5. Run the test suite to verify everything works

### For Contributors
1. Review the [Development Setup Guide](README.md) for contribution guidelines
2. Set up the development environment with quality tools
3. Follow the code quality procedures
4. Submit pull requests following the outlined process

### For API Integration
1. Check the API endpoints section in [Development Setup Guide](README.md)
2. Review the API usage examples
3. Consult the [API Documentation](../api/index.md) for detailed reference
4. Use the sample data for testing your integration

## Development Workflow

### Setup
```bash
# Clone and setup
git clone <repository-url>
cd thai-tokenizer-meilisearch

# Development with Docker
docker compose up -d

# Or local development
uv venv && uv pip install -r requirements.txt
uvicorn src.api.main:app --reload --port 8000
```

### Code Quality
```bash
# Run all quality checks
uv run ruff check && uv run ruff format --check && uv run mypy src/

# Run tests
pytest tests/ -v --cov=src
```

### Testing
```bash
# Unit tests
pytest tests/unit/ -v

# Integration tests  
pytest tests/integration/ -v

# Performance benchmarks
python deployment/scripts/benchmark.py
```

## Related Documentation

- [API Documentation](../api/index.md) - Complete API reference
- [Deployment Guide](../deployment/index.md) - Production deployment
- [Architecture Documentation](../architecture/index.md) - System design
- [Troubleshooting Guide](../troubleshooting.md) - Common issues

## Development Resources

### Sample Data
- [Thai Text Samples](../../data/samples/) - Test data for development
- [Test Queries](../../data/samples/test_queries.json) - Search test cases

### Scripts
- [Demo Scripts](../../deployment/scripts/) - Automated demos and benchmarks
- [Setup Scripts](../../deployment/scripts/setup_demo.py) - Development data setup

### Configuration
- [Environment Templates](../../config/) - Configuration examples
- [Docker Configurations](../../deployment/docker/) - Container setup

## Support

For development-related questions:
1. Check the [Development Setup Guide](README.md)
2. Review the troubleshooting sections
3. Consult the API documentation
4. Ask questions in GitHub Issues
5. Contribute improvements back to the documentation