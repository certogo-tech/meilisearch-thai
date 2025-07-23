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

```bash
# Start all services
docker compose up -d

# Check service health
curl http://localhost:8000/health
curl http://localhost:7700/health
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