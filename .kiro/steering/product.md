---
inclusion: always
---

# Product Overview

This project implements a custom Thai tokenizer for MeiliSearch to address the challenge of searching Thai compound words. Thai language lacks spaces between words, making compound word segmentation critical for accurate search results.

## Core Problem
MeiliSearch's default tokenization cannot properly handle Thai compound words, leading to poor search accuracy when users search for partial compound terms.

## Solution Architecture
A containerized Thai tokenization service that integrates with MeiliSearch through:
- Pre-processing pipeline for Thai text segmentation using PyThaiNLP
- Custom MeiliSearch configuration for Thai word boundaries
- REST API for tokenization and document processing
- Async processing pipeline for high-throughput document indexing

## Key Features
- Accurate Thai compound word segmentation using PyThaiNLP with attacut/deepcut fallbacks
- Docker containerization with multi-stage builds for production deployment
- FastAPI-based REST API with automatic OpenAPI documentation
- Support for mixed Thai-English content with language detection
- Performance monitoring, health checks, and structured logging
- Configurable tokenization strategies (formal/informal text handling)

## Business Rules
- **Text Processing**: Always preserve original text alongside tokenized versions for debugging
- **Language Detection**: Automatically detect Thai vs mixed content and apply appropriate tokenization
- **Performance SLA**: Tokenization must complete within 50ms for 1000 characters
- **Error Handling**: Graceful degradation to basic tokenization if advanced methods fail
- **Data Privacy**: Never log or persist user document content, only metadata

## API Design Principles
- **Consistency**: All endpoints follow RESTful conventions with consistent error responses
- **Async-First**: Use async/await throughout for better concurrency
- **Validation**: Strict input validation using Pydantic V2 models
- **Versioning**: API versioning through URL paths (`/v1/tokenize`)
- **Documentation**: Auto-generated OpenAPI docs with comprehensive examples

## Integration Patterns
- **MeiliSearch Integration**: Use custom tokenizer settings, not document preprocessing
- **Batch Processing**: Support bulk document operations for efficient indexing
- **Health Monitoring**: Implement comprehensive health checks for all dependencies
- **Configuration Management**: Environment-based config with validation and hot-reload
- **Error Recovery**: Implement circuit breakers and retry logic for external services

## Development Conventions
- **Thai Text Handling**: Always use UTF-8 encoding and test with complex Thai characters
- **Testing Strategy**: Include Thai text fixtures in all tokenization tests
- **Performance Testing**: Benchmark against both formal and informal Thai text samples
- **Documentation**: Include Thai language examples in API documentation
- **Logging**: Use structured logging with Thai text safely encoded

## Target Users
- **Developers**: Integrating Thai search capabilities into applications
- **System Administrators**: Deploying and monitoring search infrastructure
- **Content Managers**: Processing Thai documents for search indexing
- **DevOps Engineers**: Managing containerized deployment and scaling