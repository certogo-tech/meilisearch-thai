# Thai Search Proxy Tokenization Examples

This document demonstrates how the Thai Search Proxy tokenizes queries before searching, showing the complete flow from query input to search execution.

## How Tokenization Works

The search proxy follows this process:

1. **Receive query** → 2. **Analyze content** → 3. **Tokenize with multiple engines** → 4. **Generate query variants** → 5. **Execute parallel searches** → 6. **Merge and rank results**

## Example 1: Thai Compound Word (สาหร่ายวากาเมะ)

### Input Query
```
"สาหร่ายวากาเมะ"
```

### Step 1: Query Analysis
```json
{
  "thai_content_detected": true,
  "mixed_content": false,
  "thai_percentage": 1.0,
  "has_english": false
}
```

### Step 2: Tokenization Process
The query processor uses multiple tokenization strategies:

```json
{
  "tokenization_results": [
    {
      "engine": "newmm",
      "tokens": ["สาหร่าย", "วากาเมะ"],
      "confidence": 0.95,
      "processing_time_ms": 2.3,
      "success": true
    },
    {
      "engine": "custom_dictionary",
      "tokens": ["สาหร่าย", "วากาเมะ"],
      "confidence": 1.0,
      "note": "วากาเมะ recognized as compound word from dictionary"
    }
  ]
}
```

### Step 3: Query Variants Generated
```json
{
  "query_variants": [
    {
      "variant_type": "original",
      "query_text": "สาหร่ายวากาเมะ",
      "weight": 1.0,
      "description": "Exact match search"
    },
    {
      "variant_type": "tokenized",
      "query_text": "สาหร่าย วากาเมะ",
      "weight": 0.9,
      "tokenization_engine": "newmm",
      "description": "Space-separated tokens"
    },
    {
      "variant_type": "compound_split",
      "query_text": "สาหร่าย",
      "weight": 0.7,
      "description": "First compound part only"
    }
  ]
}
```

### Step 4: Parallel Search Execution
The search proxy executes these searches in parallel:
```
1. Search for: "สาหร่ายวากาเมะ" (exact match)
2. Search for: "สาหร่าย วากาเมะ" (tokenized)
3. Search for: "สาหร่าย" (partial match)
```

### API Call Example
```bash
# Search request with tokenization info
curl -X POST https://search.cads.arda.or.th/api/v1/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "query": "สาหร่ายวากาเมะ",
    "index_name": "research",
    "include_tokenization_info": true
  }'
```

### Response with Tokenization Info
```json
{
  "hits": [
    {
      "id": "doc-123",
      "score": 0.95,
      "document": {
        "title": "ผลของสาหร่ายผักกาดทะเล",
        "abstract": "การศึกษาสาหร่าย..."
      },
      "ranking_info": {
        "variant_type": "tokenized",
        "matched_tokens": ["สาหร่าย"]
      }
    }
  ],
  "total_hits": 42,
  "query_info": {
    "original_query": "สาหร่ายวากาเมะ",
    "processed_query": "สาหร่าย วากาเมะ",
    "thai_content_detected": true,
    "query_variants_used": 3,
    "tokenization_info": {
      "primary_engine": "newmm",
      "tokens": ["สาหร่าย", "วากาเมะ"],
      "compound_words_detected": ["วากาเมะ"]
    }
  }
}
```

## Example 2: Mixed Thai-English Query

### Input Query
```
"Smart Farm เกษตรอัจฉริยะ"
```

### Tokenization Results
```json
{
  "tokenization_results": [
    {
      "engine": "mixed_language_handler",
      "tokens": ["Smart", "Farm", "เกษตร", "อัจฉริยะ"],
      "thai_tokens": ["เกษตร", "อัจฉริยะ"],
      "english_tokens": ["Smart", "Farm"],
      "confidence": 0.9
    }
  ]
}
```

### Query Variants
```json
{
  "query_variants": [
    {
      "variant_type": "original",
      "query_text": "Smart Farm เกษตรอัจฉริยะ",
      "weight": 1.0
    },
    {
      "variant_type": "tokenized",
      "query_text": "Smart Farm เกษตร อัจฉริยะ",
      "weight": 0.85
    },
    {
      "variant_type": "thai_only",
      "query_text": "เกษตร อัจฉริยะ",
      "weight": 0.7
    },
    {
      "variant_type": "english_only",
      "query_text": "Smart Farm",
      "weight": 0.7
    }
  ]
}
```

## Example 3: Long Thai Phrase

### Input Query
```
"การเพาะปลูกพืชอินทรีย์แบบยั่งยืน"
```

### Tokenization Results
```json
{
  "tokenization_results": [
    {
      "engine": "newmm",
      "tokens": ["การ", "เพาะปลูก", "พืช", "อินทรีย์", "แบบ", "ยั่งยืน"],
      "confidence": 0.92
    },
    {
      "engine": "attacut",
      "tokens": ["การเพาะปลูก", "พืชอินทรีย์", "แบบ", "ยั่งยืน"],
      "confidence": 0.88
    }
  ]
}
```

### Query Variants (Best Tokenization Selected)
```json
{
  "query_variants": [
    {
      "variant_type": "original",
      "query_text": "การเพาะปลูกพืชอินทรีย์แบบยั่งยืน",
      "weight": 1.0
    },
    {
      "variant_type": "tokenized",
      "query_text": "การ เพาะปลูก พืช อินทรีย์ แบบ ยั่งยืน",
      "weight": 0.9,
      "tokenization_engine": "newmm"
    },
    {
      "variant_type": "phrase",
      "query_text": "\"การเพาะปลูก\" \"พืชอินทรีย์\"",
      "weight": 0.75,
      "description": "Phrase search for compound terms"
    }
  ]
}
```

## Testing Tokenization Directly

You can test tokenization without searching:

```bash
# Test tokenization endpoint
curl -X POST https://search.cads.arda.or.th/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{
    "text": "สาหร่ายวากาเมะและคอมพิวเตอร์",
    "engine": "newmm"
  }'
```

Response:
```json
{
  "original_text": "สาหร่ายวากาเมะและคอมพิวเตอร์",
  "tokens": ["สาหร่าย", "วากาเมะ", "และ", "คอมพิวเตอร์"],
  "word_boundaries": [0, 7, 14, 17, 29],
  "processing_time_ms": 2.5
}
```

## How Results Are Ranked

After parallel searches with different variants:

1. **Exact matches** (original query) get highest boost (2.0x)
2. **Tokenized matches** get high boost (1.5x)
3. **Partial matches** (compound splits) get moderate boost (1.3x)
4. **Fuzzy matches** get lower boost (0.9x)

## API Integration Example

### JavaScript/TypeScript
```typescript
async function searchWithTokenization(query: string) {
  const response = await fetch('https://search.cads.arda.or.th/api/v1/search', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-API-Key': process.env.SEARCH_API_KEY
    },
    body: JSON.stringify({
      query: query,
      index_name: 'research',
      include_tokenization_info: true,  // Get tokenization details
      options: {
        limit: 20,
        highlight: true
      }
    })
  });
  
  const result = await response.json();
  
  // Check tokenization info
  console.log('Query tokenized as:', result.query_info.tokenization_info.tokens);
  console.log('Variants used:', result.query_info.query_variants_used);
  
  return result;
}

// Example usage
const results = await searchWithTokenization('สาหร่ายวากาเมะ');
```

### Python
```python
import requests

def search_with_tokenization(query):
    response = requests.post(
        'https://search.cads.arda.or.th/api/v1/search',
        headers={
            'Content-Type': 'application/json',
            'X-API-Key': 'your-api-key'
        },
        json={
            'query': query,
            'index_name': 'research',
            'include_tokenization_info': True
        }
    )
    
    result = response.json()
    
    # Display tokenization info
    token_info = result['query_info']['tokenization_info']
    print(f"Query tokenized as: {token_info['tokens']}")
    print(f"Engine used: {token_info['primary_engine']}")
    
    return result

# Example
results = search_with_tokenization('สาหร่ายวากาเมะ')
```

## Key Benefits of Tokenization Before Search

1. **Better Recall**: Finding documents that contain individual words even if not the exact phrase
2. **Compound Word Handling**: Properly splits Thai compound words like "วากาเมะ", "คอมพิวเตอร์"
3. **Mixed Language Support**: Handles Thai-English mixed queries intelligently
4. **Multiple Search Strategies**: Executes different search variants in parallel
5. **Optimized Ranking**: Results are ranked based on how well they match each variant

## Configuration Options

You can control tokenization behavior:

```env
# Primary tokenization engine
SEARCH_PROXY_PRIMARY_ENGINE=newmm

# Enable compound word splitting
SEARCH_PROXY_ENABLE_COMPOUND_SPLITTING=true

# Maximum query variants to generate
SEARCH_PROXY_MAX_QUERY_VARIANTS=5

# Custom dictionary path
CUSTOM_DICTIONARY_PATH=/app/data/dictionaries/thai_compounds.json
```

## Summary

The Thai Search Proxy automatically:
1. ✅ Detects Thai content in queries
2. ✅ Tokenizes using appropriate engines (newmm, attacut, deepcut)
3. ✅ Recognizes compound words from custom dictionary
4. ✅ Generates multiple query variants (exact, tokenized, compound splits)
5. ✅ Executes parallel searches with all variants
6. ✅ Merges and ranks results optimally

This ensures that searching for "สาหร่ายวากาเมะ" will find documents containing:
- The exact phrase "สาหร่ายวากาเมะ"
- The words "สาหร่าย" and "วากาเมะ" separately
- Just "สาหร่าย" (with lower ranking)