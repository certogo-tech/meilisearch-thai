# Usage Examples

This document provides comprehensive examples of using the Thai Tokenizer for MeiliSearch integration in various scenarios.

## Table of Contents

- [Basic Usage](#basic-usage)
- [Document Processing](#document-processing)
- [Search Enhancement](#search-enhancement)
- [Batch Operations](#batch-operations)
- [Configuration Management](#configuration-management)
- [Integration Examples](#integration-examples)
- [Advanced Use Cases](#advanced-use-cases)

## Basic Usage

### Simple Text Tokenization

```bash
# Basic tokenization
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"
  }'
```

**Response:**
```json
{
  "tokens": ["ปัญญาประดิษฐ์", "และ", "การเรียนรู้", "ของ", "เครื่อง"],
  "original_text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง",
  "token_count": 5,
  "processing_time_ms": 23,
  "engine_used": "pythainlp"
}
```

### Tokenization with Options

```bash
# Tokenization with custom options
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "AI และ Machine Learning เป็นเทคโนโลยีอนาคต",
    "options": {
      "engine": "pythainlp",
      "keep_whitespace": true,
      "handle_compounds": true
    }
  }'
```

### Different Tokenization Engines

```bash
# Using attacut engine
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "การประมวลผลภาษาธรรมชาติ",
    "options": {"engine": "attacut"}
  }'

# Using deepcut engine
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "การประมวลผลภาษาธรรมชาติ",
    "options": {"engine": "deepcut"}
  }'
```

## Document Processing

### Single Document Processing

```bash
# Process a technology document
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "id": "tech_001",
      "title": "การพัฒนาปัญญาประดิษฐ์ในประเทศไทย",
      "content": "ปัญญาประดิษฐ์หรือ AI เป็นเทคโนโลยีที่กำลังเปลี่ยนแปลงโลก การเรียนรู้ของเครื่องและการประมวลผลภาษาธรรมชาติเป็นส่วนสำคัญของระบบ AI ในปัจจุบัน",
      "metadata": {
        "category": "technology",
        "tags": ["AI", "machine learning", "NLP"],
        "author": "Thai Tech Team",
        "published_date": "2024-07-24"
      }
    },
    "options": {
      "index_name": "thai_documents",
      "auto_index": true
    }
  }'
```

**Response:**
```json
{
  "document_id": "tech_001",
  "processed_document": {
    "id": "tech_001",
    "title": "การพัฒนาปัญญาประดิษฐ์ในประเทศไทย",
    "content": "ปัญญาประดิษฐ์หรือ AI เป็นเทคโนโลยีที่กำลังเปลี่ยนแปลงโลก...",
    "title_tokenized": "การพัฒนา ปัญญาประดิษฐ์ ใน ประเทศไทย",
    "content_tokenized": "ปัญญาประดิษฐ์ หรือ AI เป็น เทคโนโลยี ที่ กำลัง เปลี่ยนแปลง โลก การเรียนรู้ ของ เครื่อง และ การประมวลผล ภาษาธรรมชาติ เป็น ส่วน สำคัญ ของ ระบบ AI ใน ปัจจุบัน",
    "searchable_text": "การพัฒนา ปัญญาประดิษฐ์ ใน ประเทศไทย ปัญญาประดิษฐ์ หรือ AI เป็น เทคโนโลยี ที่ กำลัง เปลี่ยนแปลง โลก การเรียนรู้ ของ เครื่อง และ การประมวลผล ภาษาธรรมชาติ เป็น ส่วน สำคัญ ของ ระบบ AI ใน ปัจจุบัน",
    "metadata": {
      "category": "technology",
      "tags": ["AI", "machine learning", "NLP"],
      "author": "Thai Tech Team",
      "published_date": "2024-07-24",
      "token_count": 28,
      "processed_at": "2024-07-24T10:30:00Z"
    }
  },
  "indexing_status": "completed",
  "processing_time_ms": 156
}
```

### Food and Culture Document

```bash
# Process a food/culture document
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "id": "food_001",
      "title": "อาหารไทยและวัฒนธรรมการกิน",
      "content": "อาหารไทยมีความหลากหลายและรสชาติที่เป็นเอกลักษณ์ ต้มยำกุ้ง แกงเขียวหวาน ผัดไทย และส้มตำ เป็นอาหารที่มีชื่อเสียงระดับโลก การปรุงอาหารไทยใช้เครื่องเทศและสมุนไพรมากมาย",
      "metadata": {
        "category": "culture",
        "tags": ["อาหารไทย", "วัฒนธรรม", "ต้มยำกุ้ง"],
        "region": "Thailand"
      }
    }
  }'
```

## Search Enhancement

### Query Processing

```bash
# Process search query with expansion
curl -X POST http://localhost:8000/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "ปัญญาประดิษฐ์",
    "options": {
      "expand_compounds": true,
      "include_synonyms": true,
      "boost_exact_matches": true
    }
  }'
```

**Response:**
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

### Search Result Enhancement

```bash
# Enhance search results with Thai-specific processing
curl -X POST http://localhost:8000/api/v1/search/enhance \
  -H "Content-Type: application/json" \
  -d '{
    "query": "การเรียนรู้ของเครื่อง",
    "results": [
      {
        "id": "tech_001",
        "title": "การพัฒนาปัญญาประดิษฐ์ในประเทศไทย",
        "content": "ปัญญาประดิษฐ์หรือ AI เป็นเทคโนโลยีที่กำลังเปลี่ยนแปลงโลก การเรียนรู้ของเครื่องและการประมวลผลภาษาธรรมชาติเป็นส่วนสำคัญ",
        "score": 0.85
      }
    ],
    "options": {
      "highlight_compounds": true,
      "adjust_relevance": true
    }
  }'
```

## Batch Operations

### Batch Tokenization

```bash
# Tokenize multiple texts at once
curl -X POST http://localhost:8000/api/v1/tokenize/batch \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "ปัญญาประดิษฐ์และการเรียนรู้",
      "อาหารไทยมีรสชาติเป็นเอกลักษณ์",
      "เทคโนโลยีดิจิทัลเปลี่ยนโลก",
      "การพัฒนาซอฟต์แวร์ในยุคใหม่"
    ],
    "options": {
      "engine": "pythainlp",
      "keep_whitespace": false
    }
  }'
```

**Response:**
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
    },
    {
      "text": "เทคโนโลยีดิจิทัลเปลี่ยนโลก",
      "tokens": ["เทคโนโลยี", "ดิจิทัล", "เปลี่ยน", "โลก"],
      "token_count": 4
    },
    {
      "text": "การพัฒนาซอฟต์แวร์ในยุคใหม่",
      "tokens": ["การพัฒนา", "ซอฟต์แวร์", "ใน", "ยุค", "ใหม่"],
      "token_count": 5
    }
  ],
  "total_texts": 4,
  "total_tokens": 17,
  "processing_time_ms": 45
}
```

### Batch Document Processing

```bash
# Process multiple documents
curl -X POST http://localhost:8000/api/v1/documents/batch \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [
      {
        "id": "news_001",
        "title": "ข่าวเทคโนโลยีวันนี้",
        "content": "ปัญญาประดิษฐ์กำลังพัฒนาอย่างรวดเร็ว...",
        "category": "news"
      },
      {
        "id": "edu_001", 
        "title": "การศึกษาออนไลน์ในยุคดิจิทัล",
        "content": "การเรียนรู้ผ่านแพลตฟอร์มออนไลน์...",
        "category": "education"
      }
    ],
    "options": {
      "index_name": "mixed_content",
      "batch_size": 10
    }
  }'
```

## Configuration Management

### Get Current Configuration

```bash
# Get all configuration
curl http://localhost:8000/api/v1/config
```

**Response:**
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

### Update Tokenizer Configuration

```bash
# Add custom dictionary
curl -X PUT http://localhost:8000/api/v1/config/tokenizer \
  -H "Content-Type: application/json" \
  -d '{
    "engine": "pythainlp",
    "keep_whitespace": true,
    "handle_compounds": true,
    "custom_dictionary": [
      "ปัญญาประดิษฐ์",
      "การเรียนรู้ของเครื่อง",
      "เทคโนโลยีบล็อกเชน",
      "คลาวด์คอมพิวติ้ง",
      "บิ๊กดาต้า",
      "อินเทอร์เน็ตของสิ่งของ"
    ]
  }'
```

### Update MeiliSearch Configuration

```bash
# Update MeiliSearch settings
curl -X PUT http://localhost:8000/api/v1/config/meilisearch \
  -H "Content-Type: application/json" \
  -d '{
    "host": "http://meilisearch:7700",
    "api_key": "your-api-key",
    "index_name": "thai_documents",
    "timeout_ms": 10000,
    "max_retries": 5
  }'
```

## Integration Examples

### Python Integration

```python
import httpx
import asyncio
from typing import List, Dict, Any

class ThaiTokenizerClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.client = httpx.AsyncClient()
    
    async def tokenize(self, text: str, **options) -> Dict[str, Any]:
        """Tokenize Thai text."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/tokenize",
            json={"text": text, "options": options}
        )
        response.raise_for_status()
        return response.json()
    
    async def tokenize_batch(self, texts: List[str], **options) -> Dict[str, Any]:
        """Tokenize multiple texts."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/tokenize/batch",
            json={"texts": texts, "options": options}
        )
        response.raise_for_status()
        return response.json()
    
    async def process_document(self, document: Dict[str, Any], **options) -> Dict[str, Any]:
        """Process document for indexing."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/documents/process",
            json={"document": document, "options": options}
        )
        response.raise_for_status()
        return response.json()
    
    async def enhance_search_query(self, query: str, **options) -> Dict[str, Any]:
        """Enhance search query with Thai processing."""
        response = await self.client.post(
            f"{self.base_url}/api/v1/search/query",
            json={"query": query, "options": options}
        )
        response.raise_for_status()
        return response.json()

# Usage example
async def main():
    client = ThaiTokenizerClient()
    
    # Tokenize text
    result = await client.tokenize("ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง")
    print("Tokens:", result["tokens"])
    
    # Process document
    document = {
        "id": "example_001",
        "title": "ตัวอย่างเอกสาร",
        "content": "นี่คือเนื้อหาตัวอย่างสำหรับการทดสอบระบบ",
        "category": "example"
    }
    
    processed = await client.process_document(document, auto_index=True)
    print("Processed document ID:", processed["document_id"])
    
    # Enhance search query
    enhanced = await client.enhance_search_query(
        "ปัญญาประดิษฐ์",
        expand_compounds=True,
        include_synonyms=True
    )
    print("Enhanced query:", enhanced["processed_query"])

# Run the example
asyncio.run(main())
```

### JavaScript/Node.js Integration

```javascript
const axios = require('axios');

class ThaiTokenizerClient {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.client = axios.create({
            baseURL: baseUrl,
            headers: {
                'Content-Type': 'application/json'
            }
        });
    }
    
    async tokenize(text, options = {}) {
        const response = await this.client.post('/api/v1/tokenize', {
            text,
            options
        });
        return response.data;
    }
    
    async tokenizeBatch(texts, options = {}) {
        const response = await this.client.post('/api/v1/tokenize/batch', {
            texts,
            options
        });
        return response.data;
    }
    
    async processDocument(document, options = {}) {
        const response = await this.client.post('/api/v1/documents/process', {
            document,
            options
        });
        return response.data;
    }
    
    async enhanceSearchQuery(query, options = {}) {
        const response = await this.client.post('/api/v1/search/query', {
            query,
            options
        });
        return response.data;
    }
}

// Usage example
async function main() {
    const client = new ThaiTokenizerClient();
    
    try {
        // Tokenize text
        const result = await client.tokenize('ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง');
        console.log('Tokens:', result.tokens);
        
        // Process multiple texts
        const batchResult = await client.tokenizeBatch([
            'ปัญญาประดิษฐ์',
            'การเรียนรู้ของเครื่อง',
            'เทคโนโลยีบล็อกเชน'
        ]);
        console.log('Batch results:', batchResult.results);
        
        // Process document
        const document = {
            id: 'js_example_001',
            title: 'JavaScript Integration Example',
            content: 'ตัวอย่างการใช้งาน API ผ่าน JavaScript',
            metadata: {
                language: 'th',
                framework: 'nodejs'
            }
        };
        
        const processed = await client.processDocument(document, {
            auto_index: true
        });
        console.log('Processed document:', processed.document_id);
        
    } catch (error) {
        console.error('Error:', error.response?.data || error.message);
    }
}

main();
```

### PHP Integration

```php
<?php

class ThaiTokenizerClient {
    private $baseUrl;
    private $httpClient;
    
    public function __construct($baseUrl = 'http://localhost:8000') {
        $this->baseUrl = $baseUrl;
        $this->httpClient = new \GuzzleHttp\Client([
            'base_uri' => $baseUrl,
            'headers' => [
                'Content-Type' => 'application/json'
            ]
        ]);
    }
    
    public function tokenize($text, $options = []) {
        $response = $this->httpClient->post('/api/v1/tokenize', [
            'json' => [
                'text' => $text,
                'options' => $options
            ]
        ]);
        
        return json_decode($response->getBody(), true);
    }
    
    public function processDocument($document, $options = []) {
        $response = $this->httpClient->post('/api/v1/documents/process', [
            'json' => [
                'document' => $document,
                'options' => $options
            ]
        ]);
        
        return json_decode($response->getBody(), true);
    }
    
    public function enhanceSearchQuery($query, $options = []) {
        $response = $this->httpClient->post('/api/v1/search/query', [
            'json' => [
                'query' => $query,
                'options' => $options
            ]
        ]);
        
        return json_decode($response->getBody(), true);
    }
}

// Usage example
$client = new ThaiTokenizerClient();

// Tokenize text
$result = $client->tokenize('ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง');
echo "Tokens: " . implode(', ', $result['tokens']) . "\n";

// Process document
$document = [
    'id' => 'php_example_001',
    'title' => 'PHP Integration Example',
    'content' => 'ตัวอย่างการใช้งาน API ผ่าน PHP',
    'metadata' => [
        'language' => 'th',
        'framework' => 'php'
    ]
];

$processed = $client->processDocument($document, ['auto_index' => true]);
echo "Processed document ID: " . $processed['document_id'] . "\n";
?>
```

## Advanced Use Cases

### Custom Dictionary Management

```bash
# Add domain-specific terms
curl -X PUT http://localhost:8000/api/v1/config/tokenizer \
  -H "Content-Type: application/json" \
  -d '{
    "custom_dictionary": [
      "ฟินเทค",
      "อีคอมเมิร์ซ",
      "สตาร์ทอัพ",
      "ยูนิคอร์น",
      "ดิสรัปชัน",
      "เอไอ",
      "บิ๊กดาต้า",
      "คลาวด์",
      "บล็อกเชน",
      "ไซเบอร์เซกิวริตี้"
    ]
  }'

# Test with custom dictionary
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "บริษัทฟินเทคสตาร์ทอัพใช้เทคโนโลยีบล็อกเชนและเอไอ"
  }'
```

### Mixed Language Content

```bash
# Process mixed Thai-English content
curl -X POST http://localhost:8000/api/v1/documents/process \
  -H "Content-Type: application/json" \
  -d '{
    "document": {
      "id": "mixed_001",
      "title": "Startup ไทยในยุค Digital Transformation",
      "content": "Startup ecosystem ในประเทศไทยกำลังเติบโตอย่างรวดเร็ว บริษัท Fintech เช่น TrueMoney และ Omise กำลังปฏิวัติระบบการเงิน E-commerce platforms อย่าง Shopee และ Lazada ช่วยเปลี่ยนพฤติกรรมการซื้อของผู้บริโภค",
      "metadata": {
        "category": "business",
        "mixed_content": true,
        "languages": ["th", "en"]
      }
    }
  }'
```

### Performance Optimization

```bash
# Configure for high-performance processing
curl -X PUT http://localhost:8000/api/v1/config/processing \
  -H "Content-Type: application/json" \
  -d '{
    "batch_size": 50,
    "max_concurrent": 20,
    "enable_caching": true,
    "cache_ttl_seconds": 7200
  }'

# Process large batch with optimized settings
curl -X POST http://localhost:8000/api/v1/documents/batch \
  -H "Content-Type: application/json" \
  -d '{
    "documents": [/* large array of documents */],
    "options": {
      "batch_size": 50,
      "parallel_processing": true
    }
  }'
```

### Search Query Expansion

```bash
# Advanced query processing with expansion
curl -X POST http://localhost:8000/api/v1/search/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "AI",
    "options": {
      "expand_compounds": true,
      "include_synonyms": true,
      "boost_exact_matches": true,
      "add_related_terms": true,
      "language_detection": true
    }
  }'
```

**Response:**
```json
{
  "original_query": "AI",
  "processed_query": "(AI OR ปัญญาประดิษฐ์ OR เอไอ) AND (การเรียนรู้ OR machine learning OR deep learning)",
  "query_tokens": ["AI"],
  "expanded_terms": ["ปัญญาประดิษฐ์", "เอไอ"],
  "related_terms": ["การเรียนรู้", "machine learning", "deep learning"],
  "language_detected": "mixed",
  "suggestions": [
    "ปัญญาประดิษฐ์ในประเทศไทย",
    "การพัฒนา AI",
    "เทคโนโลยี AI"
  ],
  "processing_time_ms": 18
}
```

### Real-time Processing Pipeline

```python
# Example: Real-time document processing pipeline
import asyncio
import aiohttp
from typing import AsyncGenerator

async def process_document_stream(documents: AsyncGenerator[dict, None]):
    """Process documents in real-time stream."""
    async with aiohttp.ClientSession() as session:
        async for document in documents:
            try:
                async with session.post(
                    'http://localhost:8000/api/v1/documents/process',
                    json={
                        'document': document,
                        'options': {'auto_index': True}
                    }
                ) as response:
                    result = await response.json()
                    print(f"Processed: {result['document_id']}")
                    
            except Exception as e:
                print(f"Error processing document {document.get('id')}: {e}")

# Usage with document stream
async def document_generator():
    """Generate documents from various sources."""
    documents = [
        {
            'id': f'stream_{i}',
            'title': f'เอกสารที่ {i}',
            'content': f'เนื้อหาเอกสารตัวอย่างที่ {i} เกี่ยวกับปัญญาประดิษฐ์'
        }
        for i in range(100)
    ]
    
    for doc in documents:
        yield doc
        await asyncio.sleep(0.1)  # Simulate real-time arrival

# Run the pipeline
asyncio.run(process_document_stream(document_generator()))
```

These examples demonstrate the flexibility and power of the Thai Tokenizer API for various use cases, from simple tokenization to complex document processing pipelines.