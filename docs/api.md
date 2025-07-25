# API Documentation

This document provides comprehensive documentation for the Thai Tokenizer for MeiliSearch API endpoints.

## Table of Contents

- [Overview](#overview)
- [Authentication](#authentication)
- [Base URL](#base-url)
- [Endpoints](#endpoints)
- [Request/Response Format](#requestresponse-format)
- [Error Handling](#error-handling)
- [Examples](#examples)
- [SDKs and Libraries](#sdks-and-libraries)

## Overview

The Thai Tokenizer API provides endpoints for:
- Thai text tokenization and segmentation
- Document processing and indexing
- Search query processing
- Configuration management
- Health monitoring

All endpoints return JSON responses and support standard HTTP methods.

## Authentication

Currently, the API does not require authentication for tokenization endpoints. However, configuration endpoints may require API keys in production deployments.

```bash
# No authentication required for basic endpoints
curl http://localhost:8000/api/v1/tokenize

# API key authentication (if configured)
curl -H "Authorization: Bearer YOUR_API_KEY" http://localhost:8000/api/v1/config
```

## Base URL

- **Development**: `http://localhost:8000`
- **Production**: `https://your-domain.com`
- **Docker**: `http://thai-tokenizer:8000` (internal network)

## Endpoints

### Health and Status

#### GET /health
Check service health and status.

**Response**:
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "uptime_seconds": 3600,
  "dependencies": {
    "meilisearch": "healthy",
    "tokenizer": "healthy"
  }
}
```

#### GET /
Get service information and links.

**Response**:
```json
{
  "service": "Thai Tokenizer for MeiliSearch",
  "version": "1.0.0",
  "status": "running",
  "docs": "/docs"
}
```

### Tokenization Endpoints

#### POST /api/v1/tokenize
Tokenize Thai text into individual words.

**Request Body**:
```json
{
  "text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง",
  "options": {
    "engine": "pythainlp",
    "keep_whitespace": true,
    "handle_compounds": true
  }
}
```

**Response**:
```json
{
  "tokens": ["ปัญญาประดิษฐ์", "และ", "การเรียนรู้", "ของ", "เครื่อง"],
  "original_text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง",
  "token_count": 5,
  "processing_time_ms": 23,
  "engine_used": "pythainlp"
}
```

**Parameters**:
- `text` (required): Thai text to tokenize
- `options` (optional): Tokenization options
  - `engine`: Tokenization engine (`pythainlp`, `attacut`, `deepcut`)
  - `keep_whitespace`: Preserve whitespace tokens
  - `handle_compounds`: Apply compound word processing

#### POST /api/v1/tokenize/batch
Tokenize multiple texts in a single request.

**Request Body**:
```json
{
  "texts": [
    "ปัญญาประดิษฐ์และการเรียนรู้",
    "อาหารไทยมีรสชาติเป็นเอกลักษณ์",
    "เทคโนโลยีดิจิทัลเปลี่ยนโลก"
  ],
  "options": {
    "engine": "pythainlp"
  }
}
```

**Response**:
```json
{
  "results": [
    {
      "text": "ปัญญาประดิษฐ์และการเรียนรู้",
      "tokens": ["ปัญญาประดิษฐ์", "และ", "การเรียนรู้"],
      "token_count": 3
    },
    {
      "text": "อาหารไทยมีรสชาติเป็นเอกลักษณ์",
      "tokens": ["อาหารไทย", "มี", "รสชาติ", "เป็น", "เอกลักษณ์"],
      "token_count": 5
    }
  ],
  "total_texts": 3,
  "total_tokens": 13,
  "processing_time_ms": 45
}
```

### Document Processing Endpoints

#### POST /api/v1/documents/process
Process a document with Thai tokenization for indexing.

**Request Body**:
```json
{
  "document": {
    "id": "doc_001",
    "title": "การพัฒนาปัญญาประดิษฐ์",
    "content": "ปัญญาประดิษฐ์เป็นเทคโนโลยีที่สำคัญในอนาคต...",
    "metadata": {
      "category": "technology",
      "tags": ["AI", "technology"]
    }
  },
  "options": {
    "index_name": "documents",
    "auto_index": true
  }
}
```

**Response**:
```json
{
  "document_id": "doc_001",
  "processed_document": {
    "id": "doc_001",
    "title": "การพัฒนาปัญญาประดิษฐ์",
    "content": "ปัญญาประดิษฐ์เป็นเทคโนโลยีที่สำคัญในอนาคต...",
    "title_tokenized": "การพัฒนา ปัญญาประดิษฐ์",
    "content_tokenized": "ปัญญาประดิษฐ์ เป็น เทคโนโลยี ที่ สำคัญ ใน อนาคต",
    "searchable_text": "การพัฒนา ปัญญาประดิษฐ์ เป็น เทคโนโลยี ที่ สำคัญ ใน อนาคต",
    "metadata": {
      "category": "technology",
      "tags": ["AI", "technology"],
      "token_count": 8,
      "processed_at": "2024-07-24T10:30:00Z"
    }
  },
  "indexing_status": "completed",
  "processing_time_ms": 156
}
```

#### POST /api/v1/documents/batch
Process multiple documents in batch.

**Request Body**:
```json
{
  "documents": [
    {
      "id": "doc_001",
      "title": "การพัฒนาปัญญาประดิษฐ์",
      "content": "..."
    },
    {
      "id": "doc_002", 
      "title": "อาหารไทยและวัฒนธรรม",
      "content": "..."
    }
  ],
  "options": {
    "index_name": "documents",
    "batch_size": 10
  }
}
```

**Response**:
```json
{
  "processed_count": 2,
  "failed_count": 0,
  "results": [
    {
      "document_id": "doc_001",
      "status": "success",
      "token_count": 45
    },
    {
      "document_id": "doc_002",
      "status": "success", 
      "token_count": 67
    }
  ],
  "total_processing_time_ms": 234
}
```

### Search Enhancement Endpoints

#### POST /api/v1/search/query
Process search query with Thai tokenization.

**Request Body**:
```json
{
  "query": "ปัญญาประดิษฐ์",
  "options": {
    "expand_compounds": true,
    "include_synonyms": true,
    "boost_exact_matches": true
  }
}
```

**Response**:
```json
{
  "original_query": "ปัญญาประดิษฐ์",
  "processed_query": "ปัญญาประดิษฐ์ OR AI OR เอไอ",
  "query_tokens": ["ปัญญาประดิษฐ์"],
  "expanded_terms": ["AI", "เอไอ"],
  "suggestions": ["การเรียนรู้ของเครื่อง", "เทคโนโลยี AI"],
  "processing_time_ms": 12
}
```

#### POST /api/v1/search/enhance
Enhance search results with Thai-specific processing.

**Request Body**:
```json
{
  "query": "ปัญญาประดิษฐ์",
  "results": [
    {
      "id": "doc_001",
      "title": "การพัฒนาปัญญาประดิษฐ์",
      "content": "...",
      "score": 0.95
    }
  ],
  "options": {
    "highlight_compounds": true,
    "adjust_relevance": true
  }
}
```

**Response**:
```json
{
  "enhanced_results": [
    {
      "id": "doc_001",
      "title": "การพัฒนา<mark>ปัญญาประดิษฐ์</mark>",
      "content": "...",
      "original_score": 0.95,
      "adjusted_score": 0.98,
      "compound_matches": ["ปัญญาประดิษฐ์"],
      "relevance_factors": {
        "exact_compound_match": 0.3,
        "title_match": 0.2
      }
    }
  ],
  "total_results": 1,
  "processing_time_ms": 8
}
```

### Configuration Endpoints

#### GET /api/v1/config
Get current configuration.

**Response**:
```json
{
  "service": {
    "name": "thai-tokenizer",
    "version": "1.0.0",
    "debug": false
  },
  "tokenizer": {
    "engine": "pythainlp",
    "model_version": null,
    "keep_whitespace": true,
    "handle_compounds": true,
    "custom_dictionary_size": 0
  },
  "meilisearch": {
    "host": "http://meilisearch:7700",
    "index_name": "documents",
    "timeout_ms": 5000,
    "max_retries": 3
  },
  "processing": {
    "batch_size": 100,
    "max_concurrent": 10,
    "enable_caching": true,
    "cache_ttl_seconds": 3600
  }
}
```

#### PUT /api/v1/config/tokenizer
Update tokenizer configuration.

**Request Body**:
```json
{
  "engine": "pythainlp",
  "keep_whitespace": true,
  "handle_compounds": true,
  "custom_dictionary": ["คำศัพท์เฉพาะ", "บริษัทเทคโนโลยี"]
}
```

**Response**:
```json
{
  "status": "updated",
  "previous_config": {
    "engine": "pythainlp",
    "custom_dictionary_size": 0
  },
  "new_config": {
    "engine": "pythainlp", 
    "custom_dictionary_size": 2
  },
  "restart_required": false
}
```

#### PUT /api/v1/config/meilisearch
Update MeiliSearch configuration.

**Request Body**:
```json
{
  "host": "http://meilisearch:7700",
  "api_key": "new-api-key",
  "index_name": "thai_documents",
  "timeout_ms": 10000
}
```

**Response**:
```json
{
  "status": "updated",
  "connection_test": "success",
  "index_status": "exists",
  "updated_fields": ["api_key", "timeout_ms"]
}
```

## Request/Response Format

### Content Type
All requests must use `Content-Type: application/json`.

### Response Structure
All responses follow a consistent structure:

```json
{
  "data": {}, // Main response data
  "meta": {   // Metadata about the response
    "timestamp": "2024-07-24T10:30:00Z",
    "processing_time_ms": 23,
    "version": "1.0.0"
  }
}
```

### Pagination
For endpoints that return lists:

```json
{
  "data": [...],
  "pagination": {
    "page": 1,
    "per_page": 20,
    "total": 100,
    "total_pages": 5
  }
}
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input data",
    "details": {
      "field": "text",
      "issue": "Text cannot be empty"
    },
    "timestamp": "2024-07-24T10:30:00Z",
    "request_id": "req_123456"
  }
}
```

### HTTP Status Codes

| Code | Description | Example |
|------|-------------|---------|
| 200 | Success | Request completed successfully |
| 201 | Created | Document created/indexed |
| 400 | Bad Request | Invalid input data |
| 401 | Unauthorized | Missing or invalid API key |
| 404 | Not Found | Endpoint or resource not found |
| 422 | Validation Error | Input validation failed |
| 429 | Rate Limited | Too many requests |
| 500 | Internal Error | Server error |
| 503 | Service Unavailable | Service temporarily unavailable |

### Common Error Codes

| Code | Description |
|------|-------------|
| `VALIDATION_ERROR` | Input validation failed |
| `TOKENIZATION_ERROR` | Text tokenization failed |
| `MEILISEARCH_ERROR` | MeiliSearch operation failed |
| `CONFIGURATION_ERROR` | Invalid configuration |
| `RATE_LIMIT_EXCEEDED` | Request rate limit exceeded |
| `SERVICE_UNAVAILABLE` | External service unavailable |

## Examples

### Basic Tokenization

```bash
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"
  }'
```

### Document Processing

```bash
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "id": "tech_001",
      "title": "การพัฒนา AI ในประเทศไทย",
      "content": "ปัญญาประดิษฐ์กำลังเปลี่ยนแปลงอุตสาหกรรมต่างๆ...",
      "metadata": {
        "category": "technology",
        "language": "th"
      }
    },
    "options": {
      "auto_index": true
    }
  }'
```

### Batch Processing

```bash
curl -X POST http://localhost:8000/api/v1/tokenize/batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "ปัญญาประดิษฐ์",
      "การเรียนรู้ของเครื่อง",
      "เทคโนโลยีบล็อกเชน"
    ]
  }'
```

### Configuration Update

```bash
curl -X PUT http://localhost:8000/api/v1/config/tokenizer \
  -H "Content-Type: application/json" \
  -d '{
    "engine": "pythainlp",
    "custom_dictionary": ["AI", "บิ๊กดาต้า", "คลาวด์คอมพิวติ้ง"]
  }'
```

## SDKs and Libraries

### Python SDK

```python
import httpx

class ThaiTokenizerClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.Client()
    
    def tokenize(self, text, **options):
        response = self.client.post(
            f"{self.base_url}/api/v1/tokenize",
            json={"text": text, "options": options}
        )
        return response.json()
    
    def process_document(self, document, **options):
        response = self.client.post(
            f"{self.base_url}/api/v1/documents/process",
            json={"document": document, "options": options}
        )
        return response.json()

# Usage
client = ThaiTokenizerClient()
result = client.tokenize("ปัญญาประดิษฐ์และการเรียนรู้")
print(result["tokens"])
```

### JavaScript SDK

```javascript
class ThaiTokenizerClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async tokenize(text, options = {}) {
        const response = await fetch(`${this.baseUrl}/api/v1/tokenize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ text, options })
        });
        return response.json();
    }
    
    async processDocument(document, options = {}) {
        const response = await fetch(`${this.baseUrl}/api/v1/documents/process`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ document, options })
        });
        return response.json();
    }
}

// Usage
const client = new ThaiTokenizerClient();
const result = await client.tokenize('ปัญญาประดิษฐ์และการเรียนรู้');
console.log(result.tokens);
```

### cURL Examples

```bash
# Health check
curl http://localhost:8000/health

# Simple tokenization
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "ปัญญาประดิษฐ์"}'

# Get configuration
curl http://localhost:8000/api/v1/config

# Process document
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "id": "test_001",
      "title": "ทดสอบระบบ",
      "content": "นี่คือการทดสอบระบบโทเค็นไนเซอร์ภาษาไทย"
    }
  }'
```

## Rate Limiting

The API implements rate limiting to ensure fair usage:

- **Tokenization endpoints**: 100 requests/minute per IP
- **Document processing**: 50 requests/minute per IP  
- **Configuration endpoints**: 10 requests/minute per IP

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1627123456
```

## Webhooks

For real-time notifications of processing events:

```bash
# Register webhook
curl -X POST http://localhost:8000/api/v1/webhooks \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://your-app.com/webhook",
    "events": ["document.processed", "batch.completed"],
    "secret": "your-webhook-secret"
  }'
```

Webhook payload example:
```json
{
  "event": "document.processed",
  "timestamp": "2024-07-24T10:30:00Z",
  "data": {
    "document_id": "doc_001",
    "status": "success",
    "token_count": 45
  }
}
```

This API documentation provides comprehensive coverage of all available endpoints and their usage patterns.