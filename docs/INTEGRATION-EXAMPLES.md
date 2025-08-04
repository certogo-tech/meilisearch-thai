# Thai Search Proxy Integration Examples

This guide provides integration examples for various programming languages and frameworks.

## Table of Contents
- [Python](#python)
- [JavaScript/Node.js](#javascriptnode.js)
- [Go](#go)
- [Java](#java)
- [PHP](#php)
- [cURL](#curl)

## Python

### Basic Search

```python
import requests
import json

# Configuration
API_URL = "https://search.cads.arda.or.th/api/v1/search"
API_KEY = "your-api-key-here"  # Optional if API key is required

# Headers
headers = {
    "Content-Type": "application/json",
    "X-API-Key": API_KEY  # Remove if not using API keys
}

# Search request
def search(query, index_name="research", limit=20):
    payload = {
        "query": query,
        "index_name": index_name,
        "options": {
            "limit": limit,
            "offset": 0,
            "highlight": True
        }
    }
    
    response = requests.post(API_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Search failed: {response.status_code} - {response.text}")

# Example usage
try:
    results = search("สาหร่ายวากาเมะ")
    print(f"Found {results['total_hits']} results")
    
    for hit in results['hits'][:5]:
        print(f"- {hit['document']['title']} (Score: {hit['score']:.2f})")
        
except Exception as e:
    print(f"Error: {e}")
```

### Advanced Search with Filters

```python
def advanced_search(query, filters=None, sort=None, attributes=None):
    payload = {
        "query": query,
        "index_name": "research",
        "options": {
            "limit": 50,
            "offset": 0,
            "highlight": True,
            "crop_length": 200
        }
    }
    
    if filters:
        payload["options"]["filters"] = filters
    
    if sort:
        payload["options"]["sort"] = sort
    
    if attributes:
        payload["options"]["attributes_to_retrieve"] = attributes
    
    response = requests.post(API_URL, json=payload, headers=headers)
    return response.json()

# Example: Search for recent agriculture papers
results = advanced_search(
    query="การเกษตรอินทรีย์",
    filters="category = 'agriculture' AND publishing_date >= 2020",
    sort=["publishing_date:desc"],
    attributes=["title", "abstract", "authors", "publishing_date"]
)
```

### Batch Search

```python
def batch_search(queries, index_name="research"):
    url = "https://search.cads.arda.or.th/api/v1/batch-search"
    
    payload = {
        "queries": queries,
        "index_name": index_name,
        "options": {
            "limit": 10
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    return response.json()

# Example
queries = ["มะพร้าว", "สาหร่าย", "ข้าวอินทรีย์"]
batch_results = batch_search(queries)

for i, result in enumerate(batch_results):
    print(f"Query '{queries[i]}': {result['total_hits']} hits")
```

## JavaScript/Node.js

### Using Axios

```javascript
const axios = require('axios');

const API_URL = 'https://search.cads.arda.or.th/api/v1/search';
const API_KEY = 'your-api-key-here'; // Optional

// Search function
async function search(query, options = {}) {
    const payload = {
        query: query,
        index_name: 'research',
        options: {
            limit: 20,
            offset: 0,
            highlight: true,
            ...options
        }
    };
    
    try {
        const response = await axios.post(API_URL, payload, {
            headers: {
                'Content-Type': 'application/json',
                'X-API-Key': API_KEY
            }
        });
        
        return response.data;
    } catch (error) {
        console.error('Search error:', error.response?.data || error.message);
        throw error;
    }
}

// Example usage
(async () => {
    try {
        const results = await search('สาหร่ายวากาเมะ');
        console.log(`Found ${results.total_hits} results`);
        
        results.hits.slice(0, 5).forEach(hit => {
            console.log(`- ${hit.document.title} (Score: ${hit.score.toFixed(2)})`);
        });
    } catch (error) {
        console.error('Error:', error.message);
    }
})();
```

### Using Fetch (Browser/Modern Node.js)

```javascript
async function searchAPI(query, filters = null) {
    const url = 'https://search.cads.arda.or.th/api/v1/search';
    
    const payload = {
        query: query,
        index_name: 'research',
        options: {
            limit: 20,
            offset: 0,
            highlight: true
        }
    };
    
    if (filters) {
        payload.options.filters = filters;
    }
    
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-API-Key': 'your-api-key-here'
        },
        body: JSON.stringify(payload)
    });
    
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }
    
    return await response.json();
}

// React component example
function SearchComponent() {
    const [results, setResults] = useState([]);
    const [loading, setLoading] = useState(false);
    
    const handleSearch = async (query) => {
        setLoading(true);
        try {
            const data = await searchAPI(query);
            setResults(data.hits);
        } catch (error) {
            console.error('Search failed:', error);
        } finally {
            setLoading(false);
        }
    };
    
    return (
        <div>
            <input 
                type="text" 
                onKeyPress={(e) => {
                    if (e.key === 'Enter') {
                        handleSearch(e.target.value);
                    }
                }}
            />
            {loading && <p>Searching...</p>}
            {results.map(hit => (
                <div key={hit.id}>
                    <h3>{hit.document.title}</h3>
                    <p>Score: {hit.score.toFixed(2)}</p>
                </div>
            ))}
        </div>
    );
}
```

## Go

```go
package main

import (
    "bytes"
    "encoding/json"
    "fmt"
    "io/ioutil"
    "net/http"
)

const (
    API_URL = "https://search.cads.arda.or.th/api/v1/search"
    API_KEY = "your-api-key-here"
)

type SearchRequest struct {
    Query     string         `json:"query"`
    IndexName string         `json:"index_name"`
    Options   SearchOptions  `json:"options"`
}

type SearchOptions struct {
    Limit     int      `json:"limit"`
    Offset    int      `json:"offset"`
    Highlight bool     `json:"highlight"`
    Filters   string   `json:"filters,omitempty"`
    Sort      []string `json:"sort,omitempty"`
}

type SearchResponse struct {
    Hits       []Hit       `json:"hits"`
    TotalHits  int         `json:"total_hits"`
    QueryInfo  QueryInfo   `json:"query_info"`
}

type Hit struct {
    ID       string                 `json:"id"`
    Score    float64               `json:"score"`
    Document map[string]interface{} `json:"document"`
}

type QueryInfo struct {
    OriginalQuery string `json:"original_query"`
    ProcessedQuery string `json:"processed_query"`
}

func search(query string) (*SearchResponse, error) {
    request := SearchRequest{
        Query:     query,
        IndexName: "research",
        Options: SearchOptions{
            Limit:     20,
            Offset:    0,
            Highlight: true,
        },
    }
    
    jsonData, err := json.Marshal(request)
    if err != nil {
        return nil, err
    }
    
    req, err := http.NewRequest("POST", API_URL, bytes.NewBuffer(jsonData))
    if err != nil {
        return nil, err
    }
    
    req.Header.Set("Content-Type", "application/json")
    req.Header.Set("X-API-Key", API_KEY)
    
    client := &http.Client{}
    resp, err := client.Do(req)
    if err != nil {
        return nil, err
    }
    defer resp.Body.Close()
    
    body, err := ioutil.ReadAll(resp.Body)
    if err != nil {
        return nil, err
    }
    
    if resp.StatusCode != http.StatusOK {
        return nil, fmt.Errorf("search failed: %s", string(body))
    }
    
    var searchResp SearchResponse
    err = json.Unmarshal(body, &searchResp)
    if err != nil {
        return nil, err
    }
    
    return &searchResp, nil
}

func main() {
    results, err := search("สาหร่ายวากาเมะ")
    if err != nil {
        fmt.Printf("Error: %v\n", err)
        return
    }
    
    fmt.Printf("Found %d results\n", results.TotalHits)
    
    for i, hit := range results.Hits {
        if i >= 5 {
            break
        }
        title := hit.Document["title"].(string)
        fmt.Printf("- %s (Score: %.2f)\n", title, hit.Score)
    }
}
```

## Java

```java
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.net.URI;
import java.time.Duration;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.JsonNode;

public class ThaiSearchClient {
    private static final String API_URL = "https://search.cads.arda.or.th/api/v1/search";
    private static final String API_KEY = "your-api-key-here";
    private final HttpClient httpClient;
    private final ObjectMapper objectMapper;
    
    public ThaiSearchClient() {
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
        this.objectMapper = new ObjectMapper();
    }
    
    public SearchResult search(String query) throws Exception {
        return search(query, 20, 0, null);
    }
    
    public SearchResult search(String query, int limit, int offset, String filters) 
            throws Exception {
        
        // Build request body
        var requestBody = objectMapper.createObjectNode();
        requestBody.put("query", query);
        requestBody.put("index_name", "research");
        
        var options = requestBody.putObject("options");
        options.put("limit", limit);
        options.put("offset", offset);
        options.put("highlight", true);
        
        if (filters != null) {
            options.put("filters", filters);
        }
        
        String jsonBody = objectMapper.writeValueAsString(requestBody);
        
        // Create HTTP request
        HttpRequest request = HttpRequest.newBuilder()
            .uri(URI.create(API_URL))
            .header("Content-Type", "application/json")
            .header("X-API-Key", API_KEY)
            .POST(HttpRequest.BodyPublishers.ofString(jsonBody))
            .build();
        
        // Send request
        HttpResponse<String> response = httpClient.send(
            request, 
            HttpResponse.BodyHandlers.ofString()
        );
        
        if (response.statusCode() != 200) {
            throw new Exception("Search failed: " + response.body());
        }
        
        // Parse response
        JsonNode jsonResponse = objectMapper.readTree(response.body());
        return new SearchResult(jsonResponse);
    }
    
    public static class SearchResult {
        private final JsonNode data;
        
        public SearchResult(JsonNode data) {
            this.data = data;
        }
        
        public int getTotalHits() {
            return data.get("total_hits").asInt();
        }
        
        public JsonNode getHits() {
            return data.get("hits");
        }
        
        public void printResults(int maxResults) {
            System.out.println("Found " + getTotalHits() + " results");
            
            JsonNode hits = getHits();
            int count = Math.min(maxResults, hits.size());
            
            for (int i = 0; i < count; i++) {
                JsonNode hit = hits.get(i);
                String title = hit.get("document").get("title").asText();
                double score = hit.get("score").asDouble();
                
                System.out.printf("- %s (Score: %.2f)%n", title, score);
            }
        }
    }
    
    public static void main(String[] args) {
        try {
            ThaiSearchClient client = new ThaiSearchClient();
            
            // Simple search
            SearchResult results = client.search("สาหร่ายวากาเมะ");
            results.printResults(5);
            
            // Advanced search with filters
            SearchResult filteredResults = client.search(
                "การเกษตร",
                50,
                0,
                "category = 'agriculture' AND publishing_date >= 2020"
            );
            
            System.out.println("\nFiltered search:");
            filteredResults.printResults(5);
            
        } catch (Exception e) {
            e.printStackTrace();
        }
    }
}
```

## PHP

```php
<?php

class ThaiSearchClient {
    private $apiUrl = 'https://search.cads.arda.or.th/api/v1/search';
    private $apiKey = 'your-api-key-here';
    
    public function search($query, $options = []) {
        $defaultOptions = [
            'limit' => 20,
            'offset' => 0,
            'highlight' => true
        ];
        
        $payload = [
            'query' => $query,
            'index_name' => 'research',
            'options' => array_merge($defaultOptions, $options)
        ];
        
        $ch = curl_init($this->apiUrl);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
            'X-API-Key: ' . $this->apiKey
        ]);
        
        $response = curl_exec($ch);
        $statusCode = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        curl_close($ch);
        
        if ($statusCode !== 200) {
            throw new Exception('Search failed: ' . $response);
        }
        
        return json_decode($response, true);
    }
    
    public function advancedSearch($query, $filters = null, $sort = null) {
        $options = [];
        
        if ($filters) {
            $options['filters'] = $filters;
        }
        
        if ($sort) {
            $options['sort'] = $sort;
        }
        
        return $this->search($query, $options);
    }
    
    public function batchSearch($queries) {
        $batchUrl = str_replace('/search', '/batch-search', $this->apiUrl);
        
        $payload = [
            'queries' => $queries,
            'index_name' => 'research',
            'options' => [
                'limit' => 10
            ]
        ];
        
        $ch = curl_init($batchUrl);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($payload));
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            'Content-Type: application/json',
            'X-API-Key: ' . $this->apiKey
        ]);
        
        $response = curl_exec($ch);
        curl_close($ch);
        
        return json_decode($response, true);
    }
}

// Example usage
try {
    $client = new ThaiSearchClient();
    
    // Simple search
    $results = $client->search('สาหร่ายวากาเมะ');
    echo "Found {$results['total_hits']} results\n";
    
    foreach (array_slice($results['hits'], 0, 5) as $hit) {
        $title = $hit['document']['title'];
        $score = round($hit['score'], 2);
        echo "- {$title} (Score: {$score})\n";
    }
    
    // Advanced search
    $advancedResults = $client->advancedSearch(
        'การเกษตร',
        "category = 'agriculture'",
        ['publishing_date:desc']
    );
    
    echo "\nAdvanced search results: {$advancedResults['total_hits']}\n";
    
} catch (Exception $e) {
    echo "Error: " . $e->getMessage() . "\n";
}
```

## cURL

### Basic Search

```bash
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "query": "สาหร่ายวากาเมะ",
    "index_name": "research",
    "options": {
      "limit": 20,
      "offset": 0,
      "highlight": true
    }
  }'
```

### Search with Filters

```bash
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "query": "การเกษตรอินทรีย์",
    "index_name": "research",
    "options": {
      "limit": 50,
      "filters": "category = \"agriculture\" AND publishing_date >= 2020",
      "sort": ["relevance", "publishing_date:desc"],
      "attributes_to_retrieve": ["title", "abstract", "authors", "publishing_date"]
    }
  }'
```

### Batch Search

```bash
curl -X POST https://search.cads.arda.or.th/api/v1/batch-search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key-here" \
  -d '{
    "queries": ["มะพร้าว", "สาหร่าย", "ข้าวอินทรีย์"],
    "index_name": "research",
    "options": {
      "limit": 10
    }
  }'
```

### Health Check

```bash
# Simple health check
curl https://search.cads.arda.or.th/health

# Detailed health check
curl https://search.cads.arda.or.th/api/v1/health/detailed
```

### Get Metrics

```bash
# Metrics summary
curl https://search.cads.arda.or.th/api/v1/metrics/summary

# Analytics for last 24 hours
curl "https://search.cads.arda.or.th/api/v1/analytics/summary?hours=24"
```

## Best Practices

### 1. Error Handling

Always implement proper error handling:

```python
try:
    results = search("query")
except requests.exceptions.Timeout:
    # Handle timeout
    pass
except requests.exceptions.ConnectionError:
    # Handle connection error
    pass
except Exception as e:
    # Handle other errors
    logging.error(f"Search failed: {e}")
```

### 2. Rate Limiting

Respect rate limits to avoid 429 errors:

```javascript
// Simple rate limiter
class RateLimiter {
    constructor(maxRequests, timeWindow) {
        this.maxRequests = maxRequests;
        this.timeWindow = timeWindow;
        this.requests = [];
    }
    
    async waitIfNeeded() {
        const now = Date.now();
        this.requests = this.requests.filter(time => now - time < this.timeWindow);
        
        if (this.requests.length >= this.maxRequests) {
            const oldestRequest = this.requests[0];
            const waitTime = this.timeWindow - (now - oldestRequest) + 100;
            await new Promise(resolve => setTimeout(resolve, waitTime));
        }
        
        this.requests.push(now);
    }
}

const limiter = new RateLimiter(30, 1000); // 30 requests per second

async function searchWithRateLimit(query) {
    await limiter.waitIfNeeded();
    return search(query);
}
```

### 3. Caching

Implement caching for frequently searched queries:

```python
from functools import lru_cache
import hashlib

@lru_cache(maxsize=100)
def cached_search(query_hash):
    # Actual search implementation
    pass

def search_with_cache(query, options=None):
    # Create hash of query + options
    cache_key = hashlib.md5(
        f"{query}:{json.dumps(options or {})}".encode()
    ).hexdigest()
    
    return cached_search(cache_key)
```

### 4. Retry Logic

Implement exponential backoff for retries:

```go
func searchWithRetry(query string, maxRetries int) (*SearchResponse, error) {
    var lastErr error
    
    for i := 0; i < maxRetries; i++ {
        response, err := search(query)
        if err == nil {
            return response, nil
        }
        
        lastErr = err
        
        // Exponential backoff
        waitTime := time.Duration(math.Pow(2, float64(i))) * time.Second
        time.Sleep(waitTime)
    }
    
    return nil, fmt.Errorf("search failed after %d retries: %v", maxRetries, lastErr)
}
```

## Testing Your Integration

### 1. Unit Tests

```python
import unittest
from unittest.mock import patch, Mock

class TestSearchIntegration(unittest.TestCase):
    @patch('requests.post')
    def test_successful_search(self, mock_post):
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'hits': [{'id': '1', 'score': 0.95}],
            'total_hits': 1
        }
        mock_post.return_value = mock_response
        
        # Test
        results = search("test query")
        self.assertEqual(results['total_hits'], 1)
        self.assertEqual(len(results['hits']), 1)
```

### 2. Integration Tests

```javascript
describe('Thai Search Integration', () => {
    it('should return search results', async () => {
        const results = await search('มะพร้าว');
        
        expect(results).toHaveProperty('hits');
        expect(results).toHaveProperty('total_hits');
        expect(results.hits).toBeInstanceOf(Array);
    });
    
    it('should handle errors gracefully', async () => {
        // Test with invalid index
        await expect(search('test', { index_name: 'invalid' }))
            .rejects
            .toThrow();
    });
});
```

## Troubleshooting

### Common Issues

1. **401 Unauthorized**
   - Check API key is correct
   - Ensure API key header is included

2. **429 Too Many Requests**
   - Implement rate limiting
   - Use exponential backoff

3. **500 Internal Server Error**
   - Check service status
   - Verify request format

4. **Empty Results**
   - Verify index name
   - Check query syntax
   - Ensure Thai text encoding is correct

### Debug Tips

1. Log full request/response:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

2. Check service health:
```bash
curl https://search.cads.arda.or.th/health
```

3. Test with simple query first:
```bash
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -d '{"query": "ข้าว", "index_name": "research"}'
```