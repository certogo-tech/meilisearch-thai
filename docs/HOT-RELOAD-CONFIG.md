# Thai Search Proxy: Hot-Reload Configuration Guide

This guide explains how to use the hot-reload configuration feature and configuration management API endpoints.

## Overview

The Thai Search Proxy supports hot-reloading of configuration files, allowing you to update settings without restarting the service. This is particularly useful for:

- Adjusting search parameters in production
- Updating custom dictionaries
- Fine-tuning ranking algorithms
- Modifying performance settings

## Enabling Hot-Reload

### Environment Configuration

Enable hot-reload in your `.env` file:

```env
# Enable hot-reload configuration
SEARCH_PROXY_ENABLE_HOT_RELOAD=true

# Optional: Custom config paths
SEARCH_PROXY_CONFIG_PATH=config/search_proxy.json
TOKENIZATION_CONFIG_PATH=config/tokenization.yaml
RANKING_CONFIG_PATH=config/ranking.yaml
CUSTOM_DICTIONARY_PATH=data/dictionaries/thai_compounds.json
```

### Programmatic Configuration

```python
from src.search_proxy.config.settings import PerformanceConfig, SearchProxySettings

# Enable in performance config
performance_config = PerformanceConfig(
    enable_hot_reload=True,
    enable_metrics=True
)

settings = SearchProxySettings(
    performance=performance_config
)
```

## Watched Configuration Files

The hot-reload manager automatically watches these files:

### 1. Custom Dictionary (`data/dictionaries/thai_compounds.json`)
```json
{
  "version": "1.0",
  "compounds": [
    "สาหร่ายวากาเมะ",
    "คอมพิวเตอร์",
    "อินเทอร์เน็ต"
  ]
}
```

### 2. Tokenization Config (`config/tokenization.yaml`)
```yaml
primary_engine: "newmm"
fallback_engines:
  - "attacut"
  - "deepcut"
timeout_ms: 5000
confidence_threshold: 0.8
enable_compound_splitting: true
```

### 3. Ranking Config (`config/ranking.yaml`)
```yaml
algorithm: "optimized_score"
boost_exact_matches: 2.0
boost_thai_matches: 1.5
boost_compound_matches: 1.3
min_score_threshold: 0.1
```

### 4. Environment Variables (`.env`)
```env
SEARCH_PROXY_MAX_CONCURRENT_SEARCHES=10
SEARCH_PROXY_TIMEOUT_MS=5000
MEILISEARCH_HOST=http://localhost:7700
```

## Configuration Management API

### Get All Configuration

```bash
curl -X GET https://search.cads.arda.or.th/api/v1/admin/config \
  -H "X-API-Key: your-api-key" | jq
```

Response:
```json
{
  "tokenization": {
    "config_type": "tokenization",
    "config_data": {
      "primary_engine": "newmm",
      "fallback_engines": ["attacut", "deepcut"],
      "timeout_ms": 5000
    },
    "version": "1.0.0"
  },
  "ranking": {
    "config_type": "ranking",
    "config_data": {
      "boost_exact_matches": 2.0,
      "boost_thai_matches": 1.5
    },
    "version": "1.0.0"
  }
}
```

### Get Specific Configuration

```bash
curl -X GET https://search.cads.arda.or.th/api/v1/admin/config/ranking \
  -H "X-API-Key: your-api-key" | jq
```

### Update Configuration

```bash
curl -X PUT https://search.cads.arda.or.th/api/v1/admin/config/ranking \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "config_type": "ranking",
    "config_data": {
      "boost_exact_matches": 2.5,
      "boost_thai_matches": 1.8,
      "boost_compound_matches": 1.4
    }
  }'
```

### Check Hot-Reload Status

```bash
curl -X GET https://search.cads.arda.or.th/api/v1/admin/config/hot-reload/status \
  -H "X-API-Key: your-api-key" | jq
```

Response:
```json
{
  "enabled": true,
  "running": true,
  "watched_paths": {
    "dictionary": "data/dictionaries/thai_compounds.json",
    "tokenization": "config/tokenization.yaml",
    "ranking": "config/ranking.yaml",
    "env": ".env"
  },
  "reload_count": 3
}
```

### Manually Trigger Reload

```bash
curl -X POST https://search.cads.arda.or.th/api/v1/admin/config/hot-reload/trigger?config_type=dictionary \
  -H "X-API-Key: your-api-key"
```

### Validate Configuration

```bash
curl -X POST https://search.cads.arda.or.th/api/v1/admin/config/validate \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "config_type": "ranking",
    "config_data": {
      "boost_exact_matches": 3.0,
      "boost_thai_matches": 2.0
    }
  }'
```

## Configuration Types

### 1. Tokenization Configuration

**Updatable Settings:**
- `primary_engine`: Primary tokenization engine
- `fallback_engines`: List of fallback engines
- `timeout_ms`: Tokenization timeout
- `confidence_threshold`: Minimum confidence for results
- `enable_compound_splitting`: Enable compound word splitting

**Example Update:**
```bash
curl -X PUT https://search.cads.arda.or.th/api/v1/admin/config/tokenization \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "config_type": "tokenization",
    "config_data": {
      "primary_engine": "attacut",
      "timeout_ms": 3000,
      "confidence_threshold": 0.9
    }
  }'
```

### 2. Search Configuration

**Updatable Settings:**
- `max_concurrent_searches`: Maximum concurrent searches
- `timeout_ms`: Search timeout
- `retry_attempts`: Number of retry attempts
- `max_query_variants`: Maximum query variants to generate

### 3. Ranking Configuration

**Updatable Settings:**
- `boost_exact_matches`: Boost factor for exact matches
- `boost_thai_matches`: Boost factor for Thai content
- `boost_compound_matches`: Boost factor for compound words
- `min_score_threshold`: Minimum score threshold

### 4. Performance Configuration

**Updatable Settings:**
- `enable_metrics`: Enable/disable metrics collection
- `cache_enabled`: Enable/disable result caching
- `cache_ttl_seconds`: Cache TTL in seconds
- `max_batch_size`: Maximum batch search size

## Use Cases

### 1. A/B Testing Search Parameters

```bash
# Test different ranking boosts
curl -X PUT .../config/ranking -d '{
  "config_type": "ranking", 
  "config_data": {"boost_exact_matches": 3.0}
}'

# Monitor results, then revert if needed
curl -X PUT .../config/ranking -d '{
  "config_type": "ranking",
  "config_data": {"boost_exact_matches": 2.0}
}'
```

### 2. Adding New Compound Words

Edit `data/dictionaries/thai_compounds.json`:
```json
{
  "compounds": [
    "สาหร่ายวากาเมะ",
    "คอมพิวเตอร์",
    "ใหม่_เพิ่มเติม_ศัพท์"
  ]
}
```

The system will automatically reload the dictionary within seconds.

### 3. Performance Tuning

```bash
# Adjust concurrent searches based on load
curl -X PUT .../config/search -d '{
  "config_type": "search",
  "config_data": {"max_concurrent_searches": 15}
}'

# Adjust cache settings
curl -X PUT .../config/performance -d '{
  "config_type": "performance", 
  "config_data": {"cache_ttl_seconds": 600}
}'
```

## Integration Examples

### JavaScript/Node.js

```javascript
class ConfigManager {
  constructor(apiKey, baseUrl) {
    this.apiKey = apiKey;
    this.baseUrl = baseUrl;
  }
  
  async updateRanking(boosts) {
    const response = await fetch(`${this.baseUrl}/api/v1/admin/config/ranking`, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': this.apiKey
      },
      body: JSON.stringify({
        config_type: 'ranking',
        config_data: boosts
      })
    });
    
    return response.json();
  }
  
  async getHotReloadStatus() {
    const response = await fetch(`${this.baseUrl}/api/v1/admin/config/hot-reload/status`, {
      headers: { 'X-API-Key': this.apiKey }
    });
    
    return response.json();
  }
}

// Usage
const config = new ConfigManager('your-api-key', 'https://search.cads.arda.or.th');

// Update ranking
await config.updateRanking({
  boost_exact_matches: 2.5,
  boost_thai_matches: 1.7
});

// Check status
const status = await config.getHotReloadStatus();
console.log('Hot reload enabled:', status.enabled);
```

### Python

```python
import requests

class SearchProxyConfig:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'Content-Type': 'application/json',
            'X-API-Key': api_key
        }
    
    def update_config(self, config_type, config_data):
        response = requests.put(
            f"{self.base_url}/api/v1/admin/config/{config_type}",
            headers=self.headers,
            json={
                'config_type': config_type,
                'config_data': config_data
            }
        )
        return response.json()
    
    def get_config(self, config_type=None):
        endpoint = f"{self.base_url}/api/v1/admin/config"
        if config_type:
            endpoint += f"/{config_type}"
        
        response = requests.get(endpoint, headers=self.headers)
        return response.json()
    
    def validate_config(self, config_type, config_data):
        response = requests.post(
            f"{self.base_url}/api/v1/admin/config/validate",
            headers=self.headers,
            json={
                'config_type': config_type,
                'config_data': config_data
            }
        )
        return response.json()

# Usage
config = SearchProxyConfig('your-api-key', 'https://search.cads.arda.or.th')

# Update tokenization settings
config.update_config('tokenization', {
    'primary_engine': 'attacut',
    'timeout_ms': 4000
})

# Validate before applying
validation = config.validate_config('ranking', {
    'boost_exact_matches': 2.8
})

if validation['valid']:
    config.update_config('ranking', {
        'boost_exact_matches': 2.8
    })
```

## Monitoring and Logging

### Configuration Change Logs

Hot-reload activities are logged with structured logging:

```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "message": "Configuration file changed: data/dictionaries/thai_compounds.json",
  "config_type": "dictionary",
  "reload_time_ms": 45.2
}
```

### Metrics

Hot-reload metrics are included in the service metrics:

```bash
curl https://search.cads.arda.or.th/api/v1/metrics/summary | jq '.config_metrics'
```

```json
{
  "config_metrics": {
    "hot_reload_enabled": true,
    "config_reloads_total": 15,
    "last_reload_time": "2024-01-01T12:00:00Z",
    "avg_reload_time_ms": 42.3
  }
}
```

## Security Considerations

### 1. API Key Protection

Configuration management endpoints require API key authentication:

```bash
# This will fail
curl -X PUT .../config/ranking -d '{...}'
# Response: 401 Unauthorized

# This will succeed
curl -X PUT .../config/ranking \
  -H "X-API-Key: your-api-key" \
  -d '{...}'
```

### 2. Admin Endpoint Separation

Configuration endpoints are under `/api/v1/admin/` prefix to clearly separate administrative functions.

### 3. Validation

All configuration updates are validated before applying:

```bash
# Invalid config will be rejected
curl -X PUT .../config/ranking -d '{
  "config_type": "ranking",
  "config_data": {"boost_exact_matches": "invalid"}
}'
# Response: 400 Bad Request with validation errors
```

## Troubleshooting

### Issue: Hot-Reload Not Working

**Check Status:**
```bash
curl -X GET .../config/hot-reload/status
```

**Common Causes:**
- Hot-reload not enabled in configuration
- File permissions preventing file watching
- Configuration file format errors

**Solutions:**
```bash
# Enable hot-reload
export SEARCH_PROXY_ENABLE_HOT_RELOAD=true

# Fix file permissions
chmod 644 data/dictionaries/thai_compounds.json

# Validate configuration format
curl -X POST .../config/validate -d '{...}'
```

### Issue: Configuration Update Rejected

**Check Validation:**
```bash
curl -X POST .../config/validate -d '{
  "config_type": "ranking",
  "config_data": {"invalid_field": "value"}
}'
```

**Get Default Values:**
```bash
curl -X GET .../config/defaults/ranking
```

### Issue: Service Performance After Config Change

**Monitor Metrics:**
```bash
curl .../metrics/summary | jq '.search_metrics.avg_response_time_ms'
```

**Revert Configuration:**
```bash
curl -X PUT .../config/ranking -d '{
  "config_type": "ranking",
  "config_data": {...previous_working_config...}
}'
```

## Best Practices

1. **Test in Development**: Always test configuration changes in development first
2. **Validate Before Apply**: Use the validation endpoint before updating
3. **Monitor Performance**: Watch metrics after configuration changes  
4. **Backup Configurations**: Keep copies of working configurations
5. **Gradual Changes**: Make small incremental changes rather than large ones
6. **Document Changes**: Keep track of what changes were made and why

## Summary

Hot-reload configuration provides:

- **Zero-downtime updates** - Change settings without service restart
- **Real-time validation** - Validate configurations before applying
- **Complete API control** - Full CRUD operations via REST API
- **Automatic file watching** - Changes detected and applied automatically
- **Security** - API key protected administrative endpoints

This enables dynamic optimization of search quality and performance in production environments.