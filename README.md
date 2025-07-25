# Thai Tokenizer for MeiliSearch

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
docker compose up -d

# Check service health
curl http://localhost:8000/health
curl http://localhost:7700/health

# View logs
docker compose logs -f thai-tokenizer
```

#### Production Mode (With Nginx Proxy)
```bash
# Start all services including nginx proxy
docker compose --profile production up -d

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
cp .env.example .env

# Edit configuration as needed
# Key variables:
# - MEILISEARCH_API_KEY: API key for MeiliSearch
# - TOKENIZER_ENGINE: pythainlp (default), attacut, or deepcut
# - LOG_LEVEL: INFO (default), DEBUG, WARNING, ERROR
```

#### Container Management
```bash
# Stop services
docker compose down

# Rebuild and restart
docker compose up --build -d

# View service status
docker compose ps

# Clean up volumes (WARNING: deletes data)
docker compose down -v
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
src/
├── tokenizer/          # Core Thai tokenization logic
├── meilisearch/        # MeiliSearch integration
├── api/               # FastAPI application
└── utils/             # Utility modules

docker/                # Container configuration
tests/                 # Test suite
```

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
python scripts/run_demo.py

# This will:
# 1. Set up sample Thai documents in MeiliSearch
# 2. Compare search results before/after tokenization  
# 3. Run performance benchmarks
# 4. Generate detailed reports
```

### Individual Demo Scripts
```bash
# Set up demo data
python scripts/setup_demo.py

# Compare search results
python scripts/compare_results.py

# Run performance benchmarks
python scripts/benchmark.py
```

## Performance Benchmarks

The system meets the following performance targets:

- **Tokenization Speed**: < 50ms for 1000 characters
- **Search Response**: < 100ms for typical queries  
- **Memory Usage**: < 256MB per container
- **Indexing Throughput**: > 500 documents/second

Run benchmarks to validate performance:
```bash
python scripts/benchmark.py
```

## Documentation

### Complete Documentation
- **[API Documentation](docs/api.md)** - Complete API reference with examples
- **[Deployment Guide](docs/deployment.md)** - Production deployment instructions
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions

### Sample Data
- **[Sample Documents](sample_data/)** - Thai text samples for testing
- **[Test Queries](sample_data/test_queries.json)** - Search test cases
- **[Dataset Documentation](sample_data/README.md)** - Sample data usage guide

### Scripts
- **[Demonstration Scripts](scripts/)** - Automated demo and benchmarking
- **[Script Documentation](scripts/README.md)** - Usage instructions for all scripts

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
# Unit tests
pytest tests/unit/ -v

# Integration tests
pytest tests/integration/ -v

# End-to-end tests
pytest tests/e2e/ -v

# Performance tests
python scripts/benchmark.py
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
- **Documentation**: Check the [docs/](docs/) directory for detailed guides
- **Examples**: See [sample_data/](sample_data/) and [scripts/](scripts/) for usage examples
- **Performance**: Run benchmarks with `python scripts/benchmark.py`

## License

MIT License - see [LICENSE](LICENSE) file for details