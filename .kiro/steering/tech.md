---
inclusion: always
---

# Technology Stack & Development Guidelines

## Required Technology Stack
- **Python 3.12+**: Use latest Python features, type hints, and async/await patterns
- **FastAPI 0.116+**: All API endpoints must use FastAPI with Pydantic V2 models
- **PyThaiNLP 5.1.2+**: Primary Thai tokenization engine - implement fallback to attacut/deepcut
- **Meilisearch 1.15.2+**: Configure with custom Thai tokenization settings
- **uv**: Use for all dependency management and script execution
- **ruff**: Use for linting and formatting (replaces black, flake8, isort)

## Development Commands (Use These Exactly)
When working with this project, use these specific commands:

### Setup & Dependencies
```bash
# Install dependencies (preferred method)
uv pip install -r requirements.txt

# Run the tokenizer service
uv run uvicorn src.api.main:app --reload --port 8000
```

### Code Quality (Run Before Commits)
```bash
# Format and lint code
uv run ruff format src/ tests/
uv run ruff check src/ tests/

# Type checking
uv run mypy src/

# Run tests with coverage
uv run pytest tests/ -v --cov=src --cov-report=html
```

### Docker Operations
```bash
# Start all services
docker compose up -d

# View service logs
docker compose logs -f thai-tokenizer

# Rebuild after code changes
docker compose up --build -d thai-tokenizer
```

## Code Standards (Enforce These)

### Import Organization
```python
# Standard library first
import asyncio
from typing import List, Optional, Dict

# Third-party libraries
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel, Field

# Local imports last
from src.tokenizer.thai_segmenter import ThaiSegmenter
from src.utils.logging import get_logger
```

### Async Patterns (Required)
- Use `async/await` for all I/O operations (Meilisearch, file operations)
- Implement proper connection pooling for external services
- Handle timeouts gracefully with `asyncio.timeout()`
- Use FastAPI dependency injection for shared resources

### Error Handling (Critical)
```python
# Always include context in exceptions
raise HTTPException(
    status_code=422,
    detail=f"Thai tokenization failed for text length {len(text)}: {str(e)}"
)

# Log errors with structured data
logger.error("Tokenization failed", extra={
    "text_length": len(text),
    "error": str(e),
    "tokenizer": "pythainlp"
})
```

### Thai Text Handling Rules
- Always use UTF-8 encoding
- Preserve original text alongside tokenized versions
- Test with both formal and informal Thai content
- Handle mixed Thai-English content appropriately
- Never log actual Thai text content (privacy)

## Meilisearch Integration Patterns

### Configuration (Use These Settings)
```python
# Configure Meilisearch with Thai tokenization
settings = {
    "searchableAttributes": ["content", "title"],
    "filterableAttributes": ["language", "type"],
    "sortableAttributes": ["created_at"],
    "stopWords": [],  # Don't use English stop words for Thai
    "synonyms": {},
    "distinctAttribute": None
}
```

### Health Checks (Implement These)
```bash
# Check Meilisearch connectivity
curl http://localhost:7700/health

# Verify index settings
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://localhost:7700/indexes/documents/settings
```

## Performance Requirements (Must Meet)
- **Tokenization**: < 50ms for 1000 Thai characters
- **API Response**: < 100ms for typical requests  
- **Memory Usage**: < 256MB per container
- **Throughput**: > 500 documents/second for batch processing
- **Cold Start**: < 2 seconds container startup

## Testing Requirements
- Use Thai fixtures from `data/samples/` for consistent testing
- Test both formal and informal Thai content
- Include performance benchmarks in tests
- Test graceful degradation when PyThaiNLP fails
- Validate mixed Thai-English content handling

## Fallback Strategy (Implement This Order)
1. **PyThaiNLP** (primary) - Most accurate for Thai
2. **attacut** (fallback) - Faster alternative
3. **deepcut** (fallback) - Basic segmentation
4. **Character splitting** (last resort) - Preserve functionality