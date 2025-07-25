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

## Development

```bash
# Run tests
pytest tests/ -v

# Lint and format
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/
```

## License

MIT License