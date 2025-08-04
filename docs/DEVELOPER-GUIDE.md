# Thai Search Proxy Developer Guide

This guide explains how to extend and customize the Thai Search Proxy for your specific needs.

## Table of Contents
- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
- [Adding Custom Tokenizers](#adding-custom-tokenizers)
- [Customizing Result Ranking](#customizing-result-ranking)
- [Adding New Endpoints](#adding-new-endpoints)
- [Performance Optimization](#performance-optimization)
- [Testing Guidelines](#testing-guidelines)
- [Contributing](#contributing)

## Architecture Overview

The Thai Search Proxy follows a modular architecture:

```
┌─────────────────┐
│   FastAPI App   │
└────────┬────────┘
         │
┌────────▼────────┐
│  Search Proxy   │
│    Service      │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
┌───▼───┐ ┌──▼────┐
│ Query  │ │Result │
│Process │ │Ranker │
└───┬───┘ └───────┘
    │
┌───▼───┐
│Search │
│Execute│
└───┬───┘
    │
┌───▼───────┐
│MeiliSearch│
└───────────┘
```

## Core Components

### 1. Query Processor

The Query Processor handles Thai text tokenization and query variant generation.

```python
# src/search_proxy/services/query_processor.py

class QueryProcessor:
    def process_query(self, query: str) -> ProcessedQuery:
        # 1. Detect language content
        # 2. Tokenize Thai text
        # 3. Generate query variants
        # 4. Handle compound words
        pass
```

#### Extending Query Processing

To add custom query processing logic:

```python
from src.search_proxy.services.query_processor import QueryProcessor

class CustomQueryProcessor(QueryProcessor):
    def process_query(self, query: str) -> ProcessedQuery:
        # Call parent processing
        result = super().process_query(query)
        
        # Add custom logic
        if self._contains_special_terms(query):
            result.variants.append(self._process_special_terms(query))
        
        return result
    
    def _contains_special_terms(self, query: str) -> bool:
        # Your custom logic
        pass
    
    def _process_special_terms(self, query: str) -> QueryVariant:
        # Your custom processing
        pass
```

### 2. Search Executor

The Search Executor manages the actual search requests to MeiliSearch.

```python
# src/search_proxy/services/search_executor.py

class SearchExecutor:
    async def execute_search(
        self,
        processed_query: ProcessedQuery,
        search_request: SearchRequest
    ) -> List[SearchResult]:
        # 1. Execute multiple search variants
        # 2. Merge results
        # 3. Apply score adjustments
        pass
```

#### Custom Search Strategies

```python
from src.search_proxy.services.search_executor import SearchExecutor

class CustomSearchExecutor(SearchExecutor):
    async def execute_search(
        self,
        processed_query: ProcessedQuery,
        search_request: SearchRequest
    ) -> List[SearchResult]:
        # Add pre-processing
        if self._should_use_custom_strategy(search_request):
            return await self._custom_search_strategy(
                processed_query, 
                search_request
            )
        
        # Fall back to default
        return await super().execute_search(processed_query, search_request)
```

### 3. Result Ranker

The Result Ranker applies Thai-specific ranking algorithms.

```python
# src/search_proxy/services/result_ranker.py

class ResultRanker:
    def rank_results(
        self,
        results: List[SearchResult],
        query_info: QueryInfo
    ) -> List[RankedResult]:
        # 1. Apply content type boosts
        # 2. Boost exact matches
        # 3. Apply Thai-specific ranking
        pass
```

#### Custom Ranking Algorithms

```python
from src.search_proxy.services.result_ranker import ResultRanker

class CustomResultRanker(ResultRanker):
    def calculate_final_score(
        self,
        base_score: float,
        result: SearchResult,
        query_info: QueryInfo
    ) -> float:
        score = super().calculate_final_score(base_score, result, query_info)
        
        # Add custom scoring factors
        if self._is_premium_content(result):
            score *= 1.2
        
        if self._matches_user_preferences(result):
            score *= 1.1
        
        return min(score, 1.0)  # Cap at 1.0
```

## Adding Custom Tokenizers

### Step 1: Create Tokenizer Class

```python
# src/tokenizer/engines/custom_tokenizer.py

from typing import List, Optional
from src.tokenizer.base import TokenizerEngine, TokenizationResult

class CustomTokenizer(TokenizerEngine):
    def __init__(self):
        super().__init__()
        # Initialize your tokenizer
        self.model = self._load_model()
    
    def tokenize(
        self, 
        text: str, 
        return_confidence: bool = False
    ) -> TokenizationResult:
        # Your tokenization logic
        tokens = self._tokenize_text(text)
        
        return TokenizationResult(
            original_text=text,
            tokens=tokens,
            word_boundaries=self._get_boundaries(tokens),
            confidence_scores=self._get_confidence(tokens) if return_confidence else None
        )
    
    def _load_model(self):
        # Load your model
        pass
    
    def _tokenize_text(self, text: str) -> List[str]:
        # Implement tokenization
        pass
```

### Step 2: Register Tokenizer

```python
# src/tokenizer/factory.py

from src.tokenizer.engines.custom_tokenizer import CustomTokenizer

TOKENIZER_REGISTRY = {
    "newmm": NewMMTokenizer,
    "attacut": AttaCutTokenizer,
    "deepcut": DeepCutTokenizer,
    "custom": CustomTokenizer,  # Add your tokenizer
}
```

### Step 3: Configure Usage

```yaml
# config/tokenizer.yaml
engines:
  custom:
    enabled: true
    priority: 4
    fallback_to: newmm
    
default_engine: custom
```

## Customizing Result Ranking

### 1. Content Type Boosts

```python
# src/search_proxy/models/config.py

class ContentTypeBoosts(BaseModel):
    exact: float = 1.5
    tokenized: float = 1.2
    compound_split: float = 1.1
    fuzzy: float = 0.9
    custom_type: float = 1.3  # Add custom types
```

### 2. Field-Specific Boosts

```python
# src/search_proxy/services/result_ranker.py

class CustomResultRanker(ResultRanker):
    def apply_field_boosts(self, result: SearchResult) -> float:
        boost = 1.0
        
        # Title matches are more important
        if self._matches_in_field(result, "title"):
            boost *= 1.5
        
        # Recent content boost
        if self._is_recent(result):
            boost *= 1.2
        
        # Author reputation boost
        if self._has_reputable_author(result):
            boost *= 1.1
        
        return boost
```

### 3. Query-Specific Ranking

```python
def rank_by_query_intent(
    self,
    results: List[SearchResult],
    query_info: QueryInfo
) -> List[SearchResult]:
    # Detect query intent
    intent = self._detect_intent(query_info.original_query)
    
    if intent == "research":
        # Boost academic papers
        return self._boost_academic_content(results)
    elif intent == "practical":
        # Boost how-to guides
        return self._boost_practical_content(results)
    else:
        # Default ranking
        return results
```

## Adding New Endpoints

### 1. Create Endpoint Handler

```python
# src/api/endpoints/custom_search.py

from fastapi import APIRouter, Depends
from src.search_proxy.models import SearchRequest, SearchResponse
from src.search_proxy.services import SearchProxyService

router = APIRouter()

@router.post("/api/v1/custom-search", response_model=SearchResponse)
async def custom_search(
    request: CustomSearchRequest,
    search_service: SearchProxyService = Depends(get_search_service)
):
    """Custom search endpoint with additional features."""
    
    # Pre-process request
    processed_request = preprocess_custom_request(request)
    
    # Execute search
    results = await search_service.search(
        processed_request.query,
        processed_request.index_name,
        processed_request.options
    )
    
    # Post-process results
    enhanced_results = enhance_results(results, request.enhancements)
    
    return enhanced_results
```

### 2. Register Endpoint

```python
# src/api/main.py

from src.api.endpoints import custom_search

app.include_router(custom_search.router, tags=["custom"])
```

### 3. Add Request Models

```python
# src/search_proxy/models/requests.py

class CustomSearchRequest(SearchRequest):
    enhancements: Dict[str, Any] = Field(default_factory=dict)
    user_context: Optional[UserContext] = None
    
    class Config:
        schema_extra = {
            "example": {
                "query": "สาหร่าย",
                "index_name": "research",
                "enhancements": {
                    "expand_synonyms": True,
                    "include_related": True
                }
            }
        }
```

## Performance Optimization

### 1. Caching Strategy

```python
# src/search_proxy/cache/redis_cache.py

from redis import Redis
import json
import hashlib

class SearchCache:
    def __init__(self, redis_client: Redis):
        self.redis = redis_client
        self.ttl = 3600  # 1 hour
    
    def get_cache_key(self, request: SearchRequest) -> str:
        # Create deterministic cache key
        key_data = {
            "query": request.query,
            "index": request.index_name,
            "options": request.options.dict()
        }
        key_string = json.dumps(key_data, sort_keys=True)
        return f"search:{hashlib.md5(key_string.encode()).hexdigest()}"
    
    async def get(self, request: SearchRequest) -> Optional[SearchResponse]:
        key = self.get_cache_key(request)
        cached = await self.redis.get(key)
        
        if cached:
            return SearchResponse.parse_raw(cached)
        return None
    
    async def set(self, request: SearchRequest, response: SearchResponse):
        key = self.get_cache_key(request)
        await self.redis.setex(
            key, 
            self.ttl, 
            response.json()
        )
```

### 2. Connection Pooling

```python
# src/search_proxy/clients/meilisearch_pool.py

from contextlib import asynccontextmanager
import asyncio

class MeiliSearchPool:
    def __init__(self, config: MeiliSearchConfig, pool_size: int = 10):
        self.config = config
        self.pool_size = pool_size
        self._pool = asyncio.Queue(maxsize=pool_size)
        self._initialized = False
    
    async def initialize(self):
        for _ in range(self.pool_size):
            client = MeiliSearchClient(self.config)
            await self._pool.put(client)
        self._initialized = True
    
    @asynccontextmanager
    async def get_client(self):
        if not self._initialized:
            await self.initialize()
        
        client = await self._pool.get()
        try:
            yield client
        finally:
            await self._pool.put(client)
```

### 3. Batch Processing

```python
# src/search_proxy/services/batch_processor.py

class BatchProcessor:
    def __init__(self, search_service: SearchProxyService):
        self.search_service = search_service
        self.max_concurrent = 10
    
    async def process_batch(
        self,
        queries: List[str],
        index_name: str,
        options: SearchOptions
    ) -> List[SearchResponse]:
        # Create semaphore for concurrency control
        semaphore = asyncio.Semaphore(self.max_concurrent)
        
        async def search_with_limit(query: str):
            async with semaphore:
                return await self.search_service.search(
                    query, 
                    index_name, 
                    options
                )
        
        # Execute searches concurrently
        tasks = [search_with_limit(query) for query in queries]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Handle errors
        processed_results = []
        for result in results:
            if isinstance(result, Exception):
                # Log error and return empty result
                processed_results.append(SearchResponse(hits=[], total_hits=0))
            else:
                processed_results.append(result)
        
        return processed_results
```

## Testing Guidelines

### 1. Unit Tests

```python
# tests/unit/test_custom_tokenizer.py

import pytest
from src.tokenizer.engines.custom_tokenizer import CustomTokenizer

class TestCustomTokenizer:
    @pytest.fixture
    def tokenizer(self):
        return CustomTokenizer()
    
    def test_basic_tokenization(self, tokenizer):
        text = "ทดสอบการตัดคำ"
        result = tokenizer.tokenize(text)
        
        assert len(result.tokens) > 0
        assert "".join(result.tokens) == text
    
    def test_compound_words(self, tokenizer):
        text = "คอมพิวเตอร์"
        result = tokenizer.tokenize(text)
        
        # Should keep as single token
        assert len(result.tokens) == 1
        assert result.tokens[0] == "คอมพิวเตอร์"
    
    @pytest.mark.parametrize("text,expected_tokens", [
        ("สวัสดีครับ", ["สวัสดี", "ครับ"]),
        ("น้ำมันมะพร้าว", ["น้ำมัน", "มะพร้าว"]),
    ])
    def test_various_inputs(self, tokenizer, text, expected_tokens):
        result = tokenizer.tokenize(text)
        assert result.tokens == expected_tokens
```

### 2. Integration Tests

```python
# tests/integration/test_search_pipeline.py

import pytest
from httpx import AsyncClient
from src.api.main import app

@pytest.mark.asyncio
class TestSearchPipeline:
    async def test_end_to_end_search(self):
        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/v1/search",
                json={
                    "query": "สาหร่ายวากาเมะ",
                    "index_name": "test_index",
                    "options": {"limit": 10}
                }
            )
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert "hits" in data
            assert "total_hits" in data
            assert "query_info" in data
            
            # Verify Thai processing
            query_info = data["query_info"]
            assert query_info["thai_content_detected"] is True
            assert len(query_info["processed_query"].split()) >= 2
```

### 3. Performance Tests

```python
# tests/performance/test_load.py

import asyncio
import time
from statistics import mean, stdev

async def measure_response_time(client, query):
    start = time.time()
    response = await client.search(query)
    end = time.time()
    
    return {
        "duration": (end - start) * 1000,
        "success": response is not None,
        "hits": len(response.hits) if response else 0
    }

async def load_test(num_requests=100, concurrency=10):
    # Setup
    client = SearchClient()
    queries = ["ข้าว", "มะพร้าว", "สาหร่าย"] * (num_requests // 3)
    
    # Run concurrent requests
    semaphore = asyncio.Semaphore(concurrency)
    
    async def limited_search(query):
        async with semaphore:
            return await measure_response_time(client, query)
    
    # Execute
    results = await asyncio.gather(
        *[limited_search(q) for q in queries]
    )
    
    # Analyze
    durations = [r["duration"] for r in results if r["success"]]
    
    print(f"Total requests: {num_requests}")
    print(f"Successful: {len(durations)}")
    print(f"Average response time: {mean(durations):.2f}ms")
    print(f"Std deviation: {stdev(durations):.2f}ms")
    print(f"Min: {min(durations):.2f}ms")
    print(f"Max: {max(durations):.2f}ms")
```

## Contributing

### Code Style

Follow PEP 8 and use type hints:

```python
from typing import List, Optional, Dict, Any

def process_query(
    query: str,
    options: Optional[Dict[str, Any]] = None
) -> List[str]:
    """Process search query with options.
    
    Args:
        query: The search query text
        options: Optional processing options
        
    Returns:
        List of processed query tokens
    """
    # Implementation
    pass
```

### Documentation

All new features must include:

1. Docstrings for all public methods
2. Type hints for parameters and returns
3. Usage examples in documentation
4. Unit tests with >80% coverage

### Pull Request Process

1. Fork the repository
2. Create feature branch: `git checkout -b feature/your-feature`
3. Write tests first (TDD approach)
4. Implement feature
5. Ensure all tests pass: `pytest`
6. Update documentation
7. Submit PR with detailed description

### Performance Requirements

New features should maintain:

- Response time p95 < 200ms
- Memory usage < 512MB under normal load
- CPU usage < 80% at peak load
- Zero memory leaks over 24h operation

## Advanced Topics

### 1. Custom Dictionary Management

```python
# src/tokenizer/dictionary/manager.py

class DictionaryManager:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.dictionaries = {}
    
    def load_domain_dictionary(self, domain: str):
        """Load domain-specific dictionary."""
        path = f"{self.base_path}/{domain}_dictionary.json"
        
        with open(path, 'r', encoding='utf-8') as f:
            self.dictionaries[domain] = json.load(f)
    
    def add_term(self, term: str, domain: str = "general"):
        """Add new term to dictionary."""
        if domain not in self.dictionaries:
            self.dictionaries[domain] = []
        
        self.dictionaries[domain].append(term)
        self._save_dictionary(domain)
    
    def get_terms(self, domain: str = None) -> List[str]:
        """Get all terms, optionally filtered by domain."""
        if domain:
            return self.dictionaries.get(domain, [])
        
        # Return all terms
        all_terms = []
        for terms in self.dictionaries.values():
            all_terms.extend(terms)
        
        return list(set(all_terms))
```

### 2. Query Understanding

```python
# src/search_proxy/nlp/query_understanding.py

class QueryUnderstanding:
    def analyze_query(self, query: str) -> QueryAnalysis:
        return QueryAnalysis(
            intent=self._detect_intent(query),
            entities=self._extract_entities(query),
            language=self._detect_language(query),
            complexity=self._assess_complexity(query),
            domain=self._detect_domain(query)
        )
    
    def _detect_intent(self, query: str) -> str:
        # Implement intent detection
        # e.g., "research", "navigation", "factual"
        pass
    
    def _extract_entities(self, query: str) -> List[Entity]:
        # Extract named entities, dates, numbers
        pass
```

### 3. Result Post-Processing

```python
# src/search_proxy/postprocessing/enhancer.py

class ResultEnhancer:
    def enhance_results(
        self,
        results: List[SearchResult],
        enhancements: Dict[str, Any]
    ) -> List[EnhancedResult]:
        enhanced = []
        
        for result in results:
            enhanced_result = EnhancedResult.from_search_result(result)
            
            if enhancements.get("extract_keywords"):
                enhanced_result.keywords = self._extract_keywords(result)
            
            if enhancements.get("generate_summary"):
                enhanced_result.summary = self._generate_summary(result)
            
            if enhancements.get("find_similar"):
                enhanced_result.similar_docs = self._find_similar(result)
            
            enhanced.append(enhanced_result)
        
        return enhanced
```

## Resources

- [Thai NLP Resources](https://github.com/PyThaiNLP/pythainlp)
- [MeiliSearch Documentation](https://docs.meilisearch.com)
- [FastAPI Best Practices](https://fastapi.tiangolo.com/tutorial/)
- [Performance Testing Guide](https://locust.io/)