# Project Structure

## Planned Directory Layout

```
thai-tokenizer-meilisearch/
├── src/
│   ├── tokenizer/
│   │   ├── __init__.py
│   │   ├── thai_segmenter.py      # Core Thai tokenization logic
│   │   ├── token_processor.py     # Token processing utilities
│   │   └── config_manager.py      # Configuration management
│   ├── meilisearch/
│   │   ├── __init__.py
│   │   ├── client.py              # MeiliSearch client wrapper
│   │   ├── settings_manager.py    # Custom tokenization settings
│   │   └── document_processor.py  # Document processing pipeline
│   ├── api/
│   │   ├── __init__.py
│   │   ├── main.py                # FastAPI application
│   │   ├── endpoints/
│   │   │   ├── tokenize.py        # Tokenization endpoints
│   │   │   ├── documents.py       # Document processing endpoints
│   │   │   └── config.py          # Configuration endpoints
│   │   └── models/
│   │       ├── requests.py        # Request models
│   │       └── responses.py       # Response models
│   └── utils/
│       ├── __init__.py
│       ├── logging.py             # Logging configuration
│       └── health.py              # Health check utilities
├── tests/
│   ├── unit/
│   │   ├── test_tokenizer.py      # Tokenization unit tests
│   │   ├── test_meilisearch.py    # MeiliSearch integration tests
│   │   └── test_api.py            # API endpoint tests
│   ├── integration/
│   │   └── test_end_to_end.py     # Full workflow tests
│   └── fixtures/
│       └── thai_samples.py        # Thai text test data
├── docker/
│   ├── Dockerfile                 # Thai tokenizer service
│   ├── docker-compose.yml         # Service orchestration
│   └── nginx.conf                 # Nginx proxy configuration
├── data/
│   ├── samples/
│   │   ├── thai_documents.json    # Sample Thai documents
│   │   └── test_queries.json      # Sample search queries
├── scripts/
│   ├── setup_demo.py              # Demo data setup
│   ├── benchmark.py               # Performance testing
│   └── compare_results.py         # Before/after comparison
├── docs/
│   ├── api.md                     # API documentation
│   ├── deployment.md              # Deployment guide
│   └── troubleshooting.md         # Common issues
├── pyproject.toml                 # Modern Python project config (uv/pip)
├── requirements.txt               # Fallback dependencies file
├── uv.lock                        # Lockfile for reproducible builds
├── docker-compose.yml             # Main orchestration file
├── .dockerignore                  # Docker build optimization
├── .gitignore                     # Git ignore patterns
├── ruff.toml                      # Linting and formatting config
├── mypy.ini                       # Type checking configuration
└── README.md                      # Project overview
```

## Key Conventions

### File Organization
- **src/**: All source code organized by functional area
- **tests/**: Comprehensive test suite with unit and integration tests
- **docker/**: Container configuration and orchestration
- **data/samples/**: Thai text samples for testing and demonstration
- **scripts/**: Utility scripts for setup, testing, and benchmarking

### Naming Conventions
- **Python files**: snake_case (e.g., `thai_segmenter.py`)
- **Classes**: PascalCase (e.g., `ThaiTokenizer`)
- **Functions/variables**: snake_case (e.g., `tokenize_text`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `DEFAULT_TIMEOUT`)
- **API endpoints**: kebab-case (e.g., `/tokenize-document`)

### Configuration Management
- **pyproject.toml**: Modern Python project configuration
- **Environment-specific settings**: `.env` files with Pydantic Settings
- **Configuration schema**: Pydantic V2 models with validation
- **Secrets management**: Environment variables and Docker secrets
- **Feature flags**: Runtime configuration for A/B testing

### Testing Structure
- Unit tests mirror source code structure
- Integration tests focus on component interactions
- End-to-end tests validate complete workflows
- Thai text fixtures for consistent testing

### Docker Organization
- **Multi-stage Dockerfiles**: Optimized production images
- **Docker Compose V2**: Modern orchestration with profiles
- **BuildKit optimization**: Faster builds with advanced caching
- **Distroless base images**: Security-focused minimal containers
- **Health checks**: Comprehensive monitoring for all services
- **Resource limits**: Proper CPU and memory constraints