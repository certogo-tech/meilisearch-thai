---
inclusion: always
---

# Thai Tokenizer Product Guidelines

## Core Mission
Build a production-ready Thai tokenization service that solves MeiliSearch's inability to properly segment Thai compound words, enabling accurate search for Thai content.

## Critical Requirements

### Performance Constraints
- **Tokenization Speed**: < 50ms for 1000 Thai characters
- **API Response Time**: < 100ms for typical requests
- **Memory Usage**: < 256MB per container
- **Throughput**: > 500 documents/second for batch processing

### Thai Language Handling Rules
- **Always preserve original text** alongside tokenized versions for debugging
- **Use UTF-8 encoding** exclusively for all Thai text processing
- **Test with complex Thai characters** including tone marks and special characters
- **Support mixed Thai-English content** with automatic language detection
- **Handle both formal and informal Thai text** with appropriate tokenization strategies

### Data Privacy & Security
- **Never log user document content** - only log metadata and processing statistics
- **Sanitize Thai text in logs** to prevent encoding issues
- **Use environment variables for secrets** - never hardcode API keys or credentials

## Architecture Patterns

### Service Integration
- **MeiliSearch Integration**: Configure custom tokenizer settings, avoid document preprocessing
- **Fallback Strategy**: PyThaiNLP primary → attacut → deepcut → basic segmentation
- **Async Processing**: Use async/await throughout for I/O operations
- **Circuit Breakers**: Implement retry logic for external service failures

### API Design Standards
- **RESTful Endpoints**: Follow `/v1/tokenize`, `/v1/documents` patterns
- **Pydantic V2 Models**: Strict input/output validation with type hints
- **Error Responses**: Consistent JSON error format with Thai-safe encoding
- **Batch Operations**: Support bulk document processing for efficiency

### Code Organization Rules
- **Core tokenization logic** → `src/tokenizer/`
- **MeiliSearch operations** → `src/meilisearch_integration/`
- **API endpoints** → `src/api/endpoints/`
- **Thai test fixtures** → `data/samples/` with both formal and informal content

## Development Guidelines

### When Adding Features
1. **Include Thai text examples** in all API documentation
2. **Add corresponding test cases** with Thai fixtures from `data/samples/`
3. **Benchmark performance** against the 50ms tokenization target
4. **Test graceful degradation** when advanced tokenization fails
5. **Validate mixed-language handling** for Thai-English content

### Error Handling Strategy
- **Graceful degradation**: Fall back to simpler tokenization if advanced methods fail
- **Structured logging**: Use JSON format with correlation IDs
- **Health checks**: Monitor all dependencies (MeiliSearch, PyThaiNLP models)
- **Timeout handling**: Set reasonable timeouts for all external calls

### Testing Requirements
- **Unit tests**: Mirror `src/` structure in `tests/unit/`
- **Thai fixtures**: Use consistent test data from `data/samples/`
- **Performance tests**: Benchmark both formal and informal Thai content
- **Integration tests**: Test full MeiliSearch integration pipeline

## Configuration Management
- **Environment-based config** with Pydantic Settings validation
- **Hot-reload capability** for tokenization strategy changes
- **Separate configs** for development/production in `config/` subdirectories
- **Docker health checks** for container orchestration