# Thai Search Proxy API Documentation

## Overview

The Thai Search Proxy enhances MeiliSearch with Thai language-specific tokenization and intelligent result ranking. It provides a unified search interface that automatically handles Thai text segmentation, compound word detection, and multi-variant queries for improved search accuracy.

## Base URL

```
https://search.cads.arda.or.th
```

For local development:
```
http://localhost:8000
```

## Authentication

If API key authentication is enabled, include the API key in the request header:

```
X-API-Key: your-api-key-here
```

## API Endpoints

### 1. Search

Perform a search with Thai language optimization.

**Endpoint:** `POST /api/v1/search`

**Request Body:**
```json
{
  "query": "สาหร่ายวากาเมะ",
  "index_name": "research",
  "options": {
    "limit": 20,
    "offset": 0,
    "filters": "category = 'agriculture'",
    "sort": ["created_date:desc"],
    "highlight": true,
    "attributes_to_retrieve": ["title", "abstract", "authors"],
    "attributes_to_highlight": ["title", "abstract"],
    "crop_length": 200,
    "crop_marker": "...",
    "matching_strategy": "last"
  },
  "include_tokenization_info": false
}
```

**Parameters:**
- `query` (required): Search query text
- `index_name` (required): MeiliSearch index to search
- `options` (optional): Search options
  - `limit`: Number of results to return (default: 20, max: 100)
  - `offset`: Pagination offset (default: 0)
  - `filters`: MeiliSearch filter syntax
  - `sort`: Array of sort criteria
  - `highlight`: Enable highlighting (default: true)
  - `attributes_to_retrieve`: Specific fields to return
  - `attributes_to_highlight`: Fields to highlight
  - `crop_length`: Length of cropped text (default: 200)
  - `crop_marker`: Marker for cropped text (default: "...")
  - `matching_strategy`: Matching strategy ("all", "last", "frequency")
- `include_tokenization_info`: Include tokenization details in response

**Response:**
```json
{
  "hits": [
    {
      "id": "document-id",
      "score": 0.95,
      "document": {
        "title": "ผลของการเสริมสาหร่ายผักกาดทะเล...",
        "abstract": "การศึกษาผลของสาหร่าย...",
        "authors": ["ดวงใจ พิสุทธิ์ธาราชัย"]
      },
      "highlight": {
        "title": "ผลของการเสริม<em>สาหร่าย</em>ผักกาดทะเล..."
      },
      "ranking_info": {
        "variant_type": "tokenized",
        "tokenization_engine": "newmm"
      }
    }
  ],
  "total_hits": 42,
  "processing_time_ms": 123.45,
  "query_info": {
    "original_query": "สาหร่ายวากาเมะ",
    "processed_query": "สาหร่าย วากาเมะ",
    "thai_content_detected": true,
    "mixed_content": false,
    "query_variants_used": 3,
    "fallback_used": false
  },
  "pagination": {
    "offset": 0,
    "limit": 20,
    "total_hits": 42,
    "has_next_page": true,
    "has_previous_page": false
  }
}
```

### 2. Batch Search

Perform multiple searches in a single request.

**Endpoint:** `POST /api/v1/batch-search`

**Request Body:**
```json
{
  "queries": [
    "มะพร้าว",
    "สาหร่ายวากาเมะ",
    "การเกษตรอินทรีย์"
  ],
  "index_name": "research",
  "options": {
    "limit": 10
  }
}
```

**Response:**
```json
[
  {
    "hits": [...],
    "total_hits": 25,
    "processing_time_ms": 45.2,
    "query_info": {...}
  },
  {
    "hits": [...],
    "total_hits": 10,
    "processing_time_ms": 38.7,
    "query_info": {...}
  },
  {
    "hits": [...],
    "total_hits": 156,
    "processing_time_ms": 52.1,
    "query_info": {...}
  }
]
```

### 3. Tokenize

Test Thai text tokenization.

**Endpoint:** `POST /api/v1/tokenize`

**Request Body:**
```json
{
  "text": "สาหร่ายวากาเมะ",
  "engine": "newmm"
}
```

**Response:**
```json
{
  "original_text": "สาหร่ายวากาเมะ",
  "tokens": ["สาหร่าย", "วากาเมะ"],
  "word_boundaries": [0, 7, 14],
  "confidence_scores": null,
  "processing_time_ms": 2.3
}
```

### 4. Health Check

Check service health status.

**Endpoint:** `GET /health`

**Response:**
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

### 5. Detailed Health Check

Get detailed health information including search proxy status.

**Endpoint:** `GET /api/v1/health/detailed`

**Response:**
```json
{
  "service": "thai-search-proxy",
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production",
  "components": {
    "query_processor": "healthy",
    "search_executor": "healthy",
    "result_ranker": "healthy"
  },
  "dependencies": {
    "meilisearch": {
      "status": "healthy",
      "version": "1.0.0",
      "response_time_ms": 5.2
    }
  },
  "metrics": {
    "uptime_seconds": 3600,
    "total_searches": 1523,
    "success_rate_percent": 99.8,
    "avg_response_time_ms": 45.3,
    "active_searches": 2,
    "cache_hit_rate_percent": 65.4
  }
}
```

### 6. Metrics

Get performance metrics (Prometheus format).

**Endpoint:** `GET /metrics`

**Response:** Prometheus-formatted metrics
```
# HELP search_requests_total Total number of search requests
# TYPE search_requests_total counter
search_requests_total{status="success"} 1520.0
search_requests_total{status="error"} 3.0

# HELP search_response_time_seconds Search response time in seconds
# TYPE search_response_time_seconds histogram
search_response_time_seconds_bucket{le="0.01"} 245.0
search_response_time_seconds_bucket{le="0.025"} 892.0
search_response_time_seconds_bucket{le="0.05"} 1420.0
...
```

### 7. Metrics Summary

Get human-readable metrics summary.

**Endpoint:** `GET /api/v1/metrics/summary`

**Response:**
```json
{
  "search_metrics": {
    "total_searches": 1523,
    "successful_searches": 1520,
    "failed_searches": 3,
    "success_rate_percent": 99.8,
    "avg_response_time_ms": 45.3,
    "p95_response_time_ms": 125.7,
    "p99_response_time_ms": 234.2,
    "cache_hit_rate_percent": 65.4
  },
  "tokenization_metrics": {
    "total_tokenizations": 4569,
    "avg_tokenization_time_ms": 3.2,
    "fallback_usage_percent": 2.1,
    "mixed_language_percent": 15.3
  },
  "performance_metrics": {
    "uptime_seconds": 3600,
    "active_searches": 2,
    "memory_usage_mb": 256.3,
    "error_rate_percent": 0.2
  }
}
```

### 8. Analytics Summary

Get search analytics data.

**Endpoint:** `GET /api/v1/analytics/summary`

**Query Parameters:**
- `hours`: Number of hours to look back (default: 24, max: 168)

**Response:**
```json
{
  "period_hours": 24,
  "total_searches": 892,
  "unique_users": 156,
  "popular_queries": [
    {"query": "มะพร้าว", "count": 45, "avg_results": 23},
    {"query": "สาหร่าย", "count": 38, "avg_results": 15},
    {"query": "การเกษตร", "count": 32, "avg_results": 189}
  ],
  "no_result_queries": [
    {"query": "ไม่มีผลลัพธ์", "count": 3}
  ],
  "language_distribution": {
    "thai": 0.75,
    "english": 0.15,
    "mixed": 0.10
  },
  "hourly_distribution": [
    {"hour": 0, "searches": 12},
    {"hour": 1, "searches": 8},
    ...
  ]
}
```

## Error Responses

All endpoints return standard error responses:

```json
{
  "error": "error_type",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional error context"
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

**Common Error Codes:**
- `400`: Bad Request - Invalid parameters
- `401`: Unauthorized - Missing or invalid API key
- `404`: Not Found - Endpoint or resource not found
- `422`: Unprocessable Entity - Validation error
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - Server error
- `503`: Service Unavailable - Service temporarily unavailable

## Rate Limiting

Default rate limits (configurable):
- 30 requests per second per IP
- Burst of 50 requests allowed
- Returns `429` status code when exceeded

## Best Practices

1. **Query Construction**
   - Use natural Thai language queries
   - Include context when possible
   - The system handles tokenization automatically

2. **Performance**
   - Use `attributes_to_retrieve` to limit response size
   - Enable caching for repeated queries
   - Use batch search for multiple queries

3. **Pagination**
   - Use `offset` and `limit` for large result sets
   - Maximum `limit` is 100 per request

4. **Error Handling**
   - Implement exponential backoff for retries
   - Handle rate limiting gracefully
   - Log error details for debugging

## Query Examples

### Simple Search
```bash
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "มะพร้าว",
    "index_name": "research"
  }'
```

### Advanced Search with Filters
```bash
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "สาหร่ายวากาเมะ",
    "index_name": "research",
    "options": {
      "filters": "publishing_date >= 2020 AND category = \"agriculture\"",
      "sort": ["relevance", "publishing_date:desc"],
      "limit": 50
    }
  }'
```

### Compound Word Search
```bash
# The system automatically handles compound words like "คอมพิวเตอร์"
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "คอมพิวเตอร์การเกษตร",
    "index_name": "research"
  }'
```

## SDK Support

While no official SDK exists yet, the API is compatible with any HTTP client. See the examples directory for implementation samples in various languages.