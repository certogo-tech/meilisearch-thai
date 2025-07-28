# Thai Tokenizer for MeiliSearch - Development Guide

A custom Thai tokenization service that integrates with MeiliSearch to improve search accuracy for Thai compound words.

## Overview

Thai language lacks spaces between words, making compound word segmentation critical for accurate search results. This project provides a containerized solution that pre-processes Thai text using advanced tokenization before indexing in MeiliSearch.

## Features

- Accurate Thai compound word segmentation using PyThaiNLP
- Docker containerization for easy deployment
- REST API for tokenization and document processing
- Support for mixed Thai-English content
- Performance monitoring and health checks

## Quick Start

### Using Docker Compose

#### Development Mode (Default)
```bash
# Start services for development (no nginx proxy)
docker compose -f deployment/docker/docker-compose.yml up -d

# Check service health
curl http://localhost:8000/health
curl http://localhost:7700/health

# View logs
docker compose -f deployment/docker/docker-compose.yml logs -f thai-tokenizer
```

#### Production Mode (With Nginx Proxy)
```bash
# Start all services including nginx proxy
docker compose -f deployment/docker/docker-compose.yml --profile production up -d

# Access through nginx proxy
curl http://localhost/health
curl http://localhost/api/docs

# Direct service access still available
curl http://localhost:8000/health
curl http://localhost:7700/health
```

#### Environment Configuration
```bash
# Copy example environment file
cp config/development/.env.example .env

# Edit configuration as needed
# Key variables:
# - MEILISEARCH_API_KEY: API key for MeiliSearch
# - TOKENIZER_ENGINE: pythainlp (default), attacut, or deepcut
# - LOG_LEVEL: INFO (default), DEBUG, WARNING, ERROR
```

#### Container Management
```bash
# Stop services
docker compose -f deployment/docker/docker-compose.yml down

# Rebuild and restart
docker compose -f deployment/docker/docker-compose.yml up --build -d

# View service status
docker compose -f deployment/docker/docker-compose.yml ps

# Clean up volumes (WARNING: deletes data)
docker compose -f deployment/docker/docker-compose.yml down -v
```

### Development Setup

```bash
# Install dependencies with uv (recommended)
uv venv
uv pip install -r requirements.txt

# Or with pip
pip install -r requirements.txt

# Run the service
uvicorn src.api.main:app --reload --port 8000
```

## API Endpoints

- `POST /tokenize` - Tokenize Thai text
- `POST /index-document` - Process and index documents
- `GET /health` - Service health check
- `PUT /config/meilisearch` - Update MeiliSearch configuration

## Project Structure

```
thai-tokenizer-meilisearch/
├── src/                           # Source code
│   ├── tokenizer/                 # Core Thai tokenization logic
│   ├── meilisearch_integration/   # MeiliSearch integration
│   ├── api/                       # FastAPI application
│   └── utils/                     # Utility modules
├── tests/                         # Test suite organized by type
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   ├── performance/               # Performance tests
│   └── production/                # Production validation tests
├── docs/                          # Documentation
│   ├── api/                       # API documentation
│   ├── deployment/                # Deployment guides
│   ├── development/               # Development guides (this file)
│   └── architecture/              # Architecture documentation
├── deployment/                    # Deployment configuration
│   ├── docker/                    # Docker configurations
│   ├── k8s/                       # Kubernetes configurations
│   ├── environments/              # Environment-specific configs
│   └── scripts/                   # Deployment scripts
├── config/                        # Configuration by environment
│   ├── development/               # Development configuration
│   ├── production/                # Production configuration
│   ├── testing/                   # Testing configuration
│   └── shared/                    # Shared configuration
├── data/                          # Data files and samples
│   ├── samples/                   # Thai text samples
│   ├── fixtures/                  # Test fixtures
│   ├── benchmarks/                # Benchmark data
│   └── migrations/                # Data migration scripts
├── monitoring/                    # Monitoring and observability
├── reports/                       # Generated reports
└── [root files]                   # Essential project files
```

For detailed information about the project structure and recent migration, see the [Migration Guide](migration-guide.md).

## API Usage Examples

### Basic Tokenization
```bash
# Tokenize Thai text
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"}'

# Response
{
  "tokens": ["ปัญญาประดิษฐ์", "และ", "การเรียนรู้", "ของ", "เครื่อง"],
  "token_count": 5,
  "processing_time_ms": 23
}
```

### Document Processing
```bash
# Process document for indexing
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "id": "tech_001",
      "title": "การพัฒนา AI ในประเทศไทย",
      "content": "ปัญญาประดิษฐ์กำลังเปลี่ยนแปลงอุตสาหกรรมต่างๆ ในประเทศไทย...",
      "category": "technology"
    },
    "options": {
      "auto_index": true
    }
  }'
```

### Search Enhancement
```bash
# Process search query with Thai tokenization
curl -X POST http://localhost:8000/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ปัญญาประดิษฐ์",
    "options": {
      "expand_compounds": true,
      "include_synonyms": true
    }
  }'
```

### Configuration Management
```bash
# Get current configuration
curl http://localhost:8000/api/v1/config

# Update tokenizer settings
curl -X PUT http://localhost:8000/api/v1/config/tokenizer \
  -H "Content-Type: application/json" \
  -d '{
    "engine": "pythainlp",
    "custom_dictionary": ["AI", "บิ๊กดาต้า", "คลาวด์คอมพิวติ้ง"]
  }'
```

## Demonstration

### Run Complete Demo
```bash
# Run full demonstration suite
python deployment/scripts/run_demo.py

# This will:
# 1. Set up sample Thai documents in MeiliSearch
# 2. Compare search results before/after tokenization  
# 3. Run performance benchmarks
# 4. Generate detailed reports
```

### Individual Demo Scripts
```bash
# Set up demo data
python deployment/scripts/setup_demo.py

# Compare search results
python deployment/scripts/compare_results.py

# Run performance benchmarks
python deployment/scripts/benchmark.py
```

## Performance Benchmarks

The system meets the following performance targets:

- **Tokenization Speed**: < 50ms for 1000 characters
- **Search Response**: < 100ms for typical queries  
- **Memory Usage**: < 256MB per container
- **Indexing Throughput**: > 500 documents/second

Run benchmarks to validate performance:
```bash
python deployment/scripts/benchmark.py
```

## Documentation

### Complete Documentation
- **[API Documentation](../api/index.md)** - Complete API reference with examples
- **[Deployment Guide](../deployment/index.md)** - Production deployment instructions
- **[Production Setup Guide](../deployment/production-setup-guide.md)** - Production deployment setup
- **[Testing Summary](testing-summary.md)** - Comprehensive testing results and validation
- **[Migration Guide](migration-guide.md)** - Project structure migration information
- **[Troubleshooting Guide](../troubleshooting.md)** - Common issues and solutions

### Sample Data
- **[Sample Documents](../../data/samples/)** - Thai text samples for testing
- **[Test Queries](../../data/samples/test_queries.json)** - Search test cases
- **[Dataset Documentation](../../data/samples/README.md)** - Sample data usage guide

### Scripts and Testing
- **[Demonstration Scripts](../../deployment/scripts/)** - Automated demo and benchmarking
- **[Demo Script](../../deployment/scripts/demo_thai_tokenizer.py)** - Interactive Thai tokenizer demonstrations
- **[Comprehensive Tests](../../tests/integration/test_comprehensive_system.py)** - Full system integration tests
- **[Script Documentation](../../deployment/scripts/README.md)** - Usage instructions for all scripts

## Development

### Setup Development Environment
```bash
# Install dependencies
pip install -r requirements.txt

# Install development dependencies  
pip install -r requirements.txt[dev]

# Or use uv (recommended)
uv sync --dev
```

### Code Quality
```bash
# Run tests
pytest tests/ -v --cov=src

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/

# Run all quality checks
uv run ruff check && uv run ruff format --check && uv run mypy src/
```

### Testing
```bash
# All tests
pytest tests/ -v

# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# Performance tests
pytest tests/performance/ -v

# Production validation tests
pytest tests/production/ -v

# Run benchmarks
python deployment/scripts/benchmark.py
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass (`pytest tests/ -v`)
6. Run code quality checks (`ruff check && mypy src/`)
7. Commit your changes (`git commit -m 'Add amazing feature'`)
8. Push to the branch (`git push origin feature/amazing-feature`)
9. Open a Pull Request

## Support

- **Issues**: Report bugs and request features on GitHub Issues
- **Documentation**: Check the [docs/](../) directory for detailed guides
- **Examples**: See [data/samples/](../../data/samples/) and [deployment/scripts/](../../deployment/scripts/) for usage examples
- **Performance**: Run benchmarks with `python scripts/benchmark.py`

## License

MIT License - see [LICENSE](../../LICENSE) file for details