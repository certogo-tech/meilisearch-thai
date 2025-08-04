# Thai Search Proxy: Auto-Tokenization & Multi-Search Pipeline

## Overview

The Thai Search Proxy implements a sophisticated **auto-tokenize → multi-search → merge → re-ranking** pipeline that automatically optimizes Thai language searches for better recall and precision.

## Complete Search Pipeline Flow

### 1. Auto-Tokenization

When a query is received, the system automatically:
- Detects language content (Thai, English, or mixed)
- Selects appropriate tokenization engine
- Applies custom dictionary for compound words
- Generates tokenized versions

**Example:**
```
Input: "สาหร่ายวากาเมะ"
     ↓
Auto-detect: Thai content (100%)
     ↓
Tokenize: ["สาหร่าย", "วากาเมะ"]
```

### 2. Query Variant Generation

The system creates multiple search variants to maximize recall:

```
Original Query: "สาหร่ายวากาเมะ"
     ↓
Generated Variants:
- Variant 1: "สาหร่ายวากาเมะ" (original - exact match)
- Variant 2: "สาหร่าย วากาเมะ" (tokenized - space separated)
- Variant 3: "สาหร่าย" (compound split - partial match)
```

### 3. Parallel Multi-Search Execution

All variants are searched simultaneously for optimal performance:

```
┌─────────────────┐
│ Search Executor │
└────────┬────────┘
         │
    ┌────┴────┬──────────┬───────────┐
    ↓         ↓          ↓           ↓
Search 1   Search 2   Search 3   (up to 5 parallel)
"สาหร่าย   "สาหร่าย   "สาหร่าย"
วากาเมะ"   วากาเมะ"
```

### 4. Result Merging & Deduplication

Results from all searches are intelligently merged:

```
Results from Search 1: [Doc A, Doc B, Doc C]
Results from Search 2: [Doc B, Doc D, Doc E]  
Results from Search 3: [Doc F, Doc G, Doc H]
                ↓
Merged (deduplicated): [A, B, C, D, E, F, G, H]
```

### 5. Thai-Aware Re-Ranking

Final ranking applies language-specific scoring:

```
Scoring Factors:
- Exact match boost: 2.0x
- Tokenized match boost: 1.5x  
- Thai content boost: 1.4x
- Compound match boost: 1.3x
                ↓
Final ranked results: [B(1.0), D(0.95), A(0.92), ...]
```

## Pipeline Components

### Query Processor (`query_processor.py`)
- Analyzes query language content
- Performs tokenization with multiple engines
- Generates optimized query variants

```python
# Automatic processing
processed_query = await query_processor.process_query("สาหร่ายวากาเมะ")
# Returns: variants, tokenization results, language detection
```

### Search Executor (`search_executor.py`)
- Executes parallel searches for all variants
- Manages concurrent connections
- Handles timeouts and retries

```python
# Parallel execution
results = await search_executor.execute_parallel_searches(
    query_variants, 
    index_name="research"
)
```

### Result Ranker (`result_ranker.py`)
- Merges results from multiple searches
- Removes duplicates
- Applies Thai-specific ranking algorithm

```python
# Intelligent ranking
ranked_results = result_ranker.rank_results(
    merged_results,
    query_info
)
```

## Real-World Example

### Search: "สาหร่ายวากาเมะ"

**Step 1: Tokenization**
```
Input: "สาหร่ายวากาเมะ"
Tokens: ["สาหร่าย", "วากาเมะ"]
Engine: newmm with custom dictionary
```

**Step 2: Query Variants**
```json
[
  {
    "variant_type": "original",
    "query": "สาหร่ายวากาเมะ",
    "weight": 1.0
  },
  {
    "variant_type": "tokenized",
    "query": "สาหร่าย วากาเมะ",
    "weight": 0.9
  },
  {
    "variant_type": "compound_split",
    "query": "สาหร่าย",
    "weight": 0.7
  }
]
```

**Step 3: Parallel Search**
- 3 searches executed simultaneously
- Total time: ~50ms (vs ~150ms sequential)

**Step 4: Results**
- Found: 10 documents containing "สาหร่าย"
- Including documents without "วากาเมะ"
- Best matches (with both terms) ranked highest

## Benefits

### 1. **Improved Recall**
- Finds related documents even with partial matches
- Handles compound words intelligently
- Supports word variations

### 2. **Better Precision**
- Exact matches get highest scores
- Thai-specific ranking factors
- Context-aware scoring

### 3. **Optimal Performance**
- Parallel execution reduces latency
- Efficient deduplication
- Smart caching strategies

### 4. **Language Intelligence**
- Automatic language detection
- Mixed Thai-English support
- Custom dictionary integration

## Configuration

### Tokenization Settings
```env
# Primary engine
SEARCH_PROXY_PRIMARY_ENGINE=newmm

# Enable compound splitting
SEARCH_PROXY_ENABLE_COMPOUND_SPLITTING=true

# Max variants to generate
SEARCH_PROXY_MAX_QUERY_VARIANTS=5

# Custom dictionary
CUSTOM_DICTIONARY_PATH=/app/data/dictionaries/thai_compounds.json
```

### Search Execution
```env
# Parallel search settings
SEARCH_PROXY_MAX_CONCURRENT_SEARCHES=5
SEARCH_PROXY_PARALLEL_EXECUTION=true

# Timeout settings
SEARCH_PROXY_SEARCH_TIMEOUT_MS=5000
```

### Ranking Algorithm
```env
# Ranking weights
SEARCH_PROXY_BOOST_EXACT_MATCHES=2.0
SEARCH_PROXY_BOOST_TOKENIZED_MATCHES=1.5
SEARCH_PROXY_BOOST_THAI_MATCHES=1.4
SEARCH_PROXY_BOOST_COMPOUND_MATCHES=1.3
```

## API Usage

### Basic Search (Auto-Pipeline)
```bash
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "สาหร่ายวากาเมะ",
    "index_name": "research"
  }'
```

### With Pipeline Details
```bash
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "สาหร่ายวากาเมะ",
    "index_name": "research",
    "include_tokenization_info": true
  }'
```

Response includes:
```json
{
  "query_info": {
    "original_query": "สาหร่ายวากาเมะ",
    "processed_query": "สาหร่าย วากาเมะ",
    "thai_content_detected": true,
    "query_variants_used": 3,
    "tokenization_info": {
      "tokens": ["สาหร่าย", "วากาเมะ"],
      "engine": "newmm"
    }
  }
}
```

## Performance Metrics

### Typical Pipeline Timings
- Tokenization: ~2-5ms
- Query variant generation: ~1ms
- Parallel search execution: ~40-60ms
- Result merging: ~2-3ms
- Re-ranking: ~3-5ms
- **Total: ~50-75ms**

### Throughput
- Single query: ~50ms average
- Batch (10 queries): ~200ms average
- Concurrent capacity: 50+ req/sec

## Integration Example

### JavaScript/TypeScript
```typescript
class ThaiSearchClient {
  async search(query: string) {
    const response = await fetch('/api/v1/search', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': process.env.SEARCH_API_KEY
      },
      body: JSON.stringify({
        query: query,  // Auto-tokenization happens here
        index_name: 'research',
        options: {
          limit: 20,
          highlight: true
        }
      })
    });
    
    const result = await response.json();
    
    // Pipeline automatically:
    // 1. Tokenized the query
    // 2. Generated variants
    // 3. Executed parallel searches
    // 4. Merged results
    // 5. Re-ranked by relevance
    
    return result;
  }
}

// Usage
const client = new ThaiSearchClient();
const results = await client.search('สาหร่ายวากาเมะ');
// Returns optimally ranked results
```

## Monitoring Pipeline Performance

### Metrics Endpoint
```bash
curl https://search.cads.arda.or.th/api/v1/metrics/summary
```

Returns:
```json
{
  "search_metrics": {
    "avg_tokenization_time_ms": 3.2,
    "avg_variant_generation_time_ms": 1.1,
    "avg_search_execution_time_ms": 45.3,
    "avg_ranking_time_ms": 4.2,
    "avg_total_pipeline_time_ms": 53.8
  }
}
```

## Troubleshooting

### Issue: Slow Searches
- Check parallel execution is enabled
- Verify MeiliSearch connection latency
- Review number of query variants

### Issue: Poor Recall
- Verify custom dictionary is loaded
- Check tokenization engine selection
- Review minimum score threshold

### Issue: Irrelevant Results
- Adjust ranking boost factors
- Review variant weights
- Check index configuration

## Summary

The Thai Search Proxy's auto-tokenization and multi-search pipeline provides:

1. **Automatic optimization** - No manual query processing needed
2. **Language intelligence** - Thai-aware tokenization and ranking
3. **High performance** - Parallel execution and smart caching
4. **Better results** - Improved recall without sacrificing precision

This pipeline ensures that Thai language searches work as well as (or better than) English searches in terms of finding relevant content and ranking it appropriately.