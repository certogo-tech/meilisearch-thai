# Technology Stack

## Core Technologies
- **Python 3.12+**: Latest Python with improved performance and type hints
- **FastAPI 0.116+**: Modern async REST API framework with automatic OpenAPI docs
- **PyThaiNLP 5.1.2+**: Latest Thai NLP library with improved tokenization models
- **Meilisearch 1.15.2+**: Latest search engine with enhanced tokenization features
- **Docker & Docker Compose V2**: Modern containerization with BuildKit support
- **Pydantic V2.11+**: Fast data validation with improved performance

## Alternative Libraries
- **attacut 1.1+** or **deepcut 0.7+**: Alternative Thai tokenization engines
- **Traefik 3.0+**: Modern reverse proxy with automatic service discovery (alternative to Nginx)
- **spaCy 3.7+**: Advanced NLP pipeline for mixed-language processing

## Development Tools
- **Python**: Primary development language with modern tooling
- **uv**: Ultra-fast Python package manager and project manager
- **ruff**: Extremely fast Python linter and formatter (replaces flake8, black, isort)
- **mypy 1.7+**: Static type checker with latest improvements
- **pytest 7.4+**: Modern testing framework with async support
- **pytest-asyncio**: Async testing support for FastAPI endpoints

## Common Commands

### Development Setup
```bash
# Install uv (modern Python package manager)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment and install dependencies
uv venv
uv pip install -r requirements.txt

# Alternative: Use uv to manage project entirely
uv init --python 3.12
uv add fastapi uvicorn pythainlp meilisearch pydantic
```

### Development
```bash
# Run tokenizer service with hot reload
uv run uvicorn src.api.main:app --reload --port 8000

# Run tests with coverage
uv run pytest tests/ -v --cov=src --cov-report=html

# Lint and format code (extremely fast)
uv run ruff check src/ tests/
uv run ruff format src/ tests/

# Type checking
uv run mypy src/

# Run all quality checks
uv run ruff check && uv run ruff format --check && uv run mypy src/
```

### Docker Operations (Compose V2)
```bash
# Build containers with BuildKit
DOCKER_BUILDKIT=1 docker compose build

# Start all services
docker compose up -d

# View logs with follow
docker compose logs -f thai-tokenizer

# Stop services
docker compose down

# Rebuild and restart specific service
docker compose up --build -d thai-tokenizer

# Scale services
docker compose up -d --scale thai-tokenizer=3
```

### Meilisearch Management
```bash
# Check Meilisearch health (latest API)
curl http://localhost:7700/health

# View index settings with API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:7700/indexes/documents/settings

# Create index with custom settings
curl -X POST http://localhost:7700/indexes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{"uid": "documents", "primaryKey": "id"}'

# Reset index
curl -X DELETE http://localhost:7700/indexes/documents \
  -H "Authorization: Bearer YOUR_API_KEY"
```

## Modern Development Practices
- **Async/await**: Full async support throughout the application
- **Type hints**: Complete type coverage with Pydantic V2 models
- **Dependency injection**: FastAPI's modern DI system for testability
- **Structured logging**: JSON logging with correlation IDs
- **Health checks**: Comprehensive health endpoints for all services
- **Observability**: Metrics and tracing with OpenTelemetry support

## Container Optimization
- **Multi-stage builds**: Minimal production images
- **Distroless images**: Security-focused base images
- **BuildKit**: Faster builds with advanced caching
- **Health checks**: Proper container health monitoring

## Performance Targets
- Tokenization: < 50ms for 1000 characters (improved with latest PyThaiNLP)
- Search response: < 100ms for typical queries (Meilisearch 1.5+ optimizations)
- Memory usage: < 256MB per container (optimized with Python 3.12)
- Throughput: > 500 documents/second indexing (async processing)
- Cold start: < 2 seconds container startup time