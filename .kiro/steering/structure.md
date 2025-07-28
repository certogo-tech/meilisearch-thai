---
inclusion: always
---

# Project Structure & Conventions

## Core Architecture
This Thai tokenizer project follows a layered architecture with clear separation of concerns:

- **src/tokenizer/**: Core Thai NLP processing (PyThaiNLP integration)
- **src/meilisearch_integration/**: MeiliSearch client and document processing
- **src/api/**: FastAPI REST endpoints with Pydantic models
- **src/utils/**: Shared utilities (logging, health checks)

## File Organization Rules

### Source Code Structure
- Place all business logic in `src/` with functional modules
- Use `__init__.py` files to define public APIs for each module
- Keep API endpoints in `src/api/endpoints/` with one file per resource
- Store Pydantic models in `src/api/models/` (separate requests/responses)

### Configuration Hierarchy
1. **Environment files**: Use `.env` files in `config/` subdirectories
2. **Settings classes**: Pydantic Settings models with validation
3. **Runtime config**: Store in `config/` with environment-specific folders
4. **Secrets**: Environment variables only, never commit to code

### Testing Organization
- **Unit tests**: Mirror `src/` structure in `tests/unit/`
- **Integration tests**: Full component interactions in `tests/integration/`
- **Performance tests**: Benchmarking in `tests/performance/`
- **Thai fixtures**: Use `data/samples/` for consistent test data

## Naming Conventions (Strict)
- **Python files/modules**: `snake_case` (e.g., `thai_segmenter.py`)
- **Classes**: `PascalCase` (e.g., `ThaiTokenizer`, `DocumentProcessor`)
- **Functions/variables**: `snake_case` (e.g., `tokenize_text`, `process_document`)
- **Constants**: `UPPER_SNAKE_CASE` (e.g., `DEFAULT_TIMEOUT`, `MAX_RETRIES`)
- **API endpoints**: `kebab-case` (e.g., `/tokenize-document`, `/health-check`)
- **Environment variables**: `UPPER_SNAKE_CASE` with prefixes (e.g., `MEILISEARCH_URL`)

## Code Organization Patterns

### Import Structure
```python
# Standard library imports first
import asyncio
from typing import List, Optional

# Third-party imports
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Local imports last
from src.tokenizer.thai_segmenter import ThaiSegmenter
from src.utils.logging import get_logger
```

### Error Handling
- Use custom exception classes in each module
- Always include context in error messages
- Log errors with structured data (JSON format)
- Return consistent error responses from API endpoints

### Async Patterns
- Use `async/await` for all I/O operations
- Implement proper connection pooling for external services
- Use dependency injection for shared resources
- Handle timeouts and retries gracefully

## File Placement Rules

### New Features
- Core tokenization logic → `src/tokenizer/`
- MeiliSearch operations → `src/meilisearch_integration/`
- API endpoints → `src/api/endpoints/`
- Data models → `src/api/models/`
- Utilities → `src/utils/`

### Configuration Files
- Development config → `config/development/`
- Production config → `config/production/`
- Shared config → `config/shared/`
- Docker configs → `deployment/docker/`

### Documentation
- API docs → `docs/api/`
- Deployment guides → `docs/deployment/`
- Architecture docs → `docs/architecture/`

## Thai Language Handling
- Always use UTF-8 encoding for Thai text
- Include Thai text samples in all tokenization tests
- Test with both formal and informal Thai content
- Preserve original text alongside tokenized versions
- Handle mixed Thai-English content appropriately

## Performance Requirements
- Tokenization: < 50ms for 1000 characters
- API response: < 100ms for typical requests
- Memory usage: < 256MB per container
- Support concurrent requests with async processing