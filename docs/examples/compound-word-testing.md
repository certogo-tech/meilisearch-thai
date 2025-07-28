# Thai Compound Word Testing Guide

This guide demonstrates how to test complex Thai compound words, including Thai-Japanese terms like "สาหร่ายวากาเมะ" (wakame seaweed).

## 🎯 Understanding Complex Compound Words

### Thai-Japanese Food Terms

Thai cuisine incorporates many Japanese ingredients, creating compound words that combine Thai and Japanese elements:

- **สาหร่ายวากาเมะ** (sǎa-làai waa-gaa-mé) = "wakame seaweed"
  - **สาหร่าย** (sǎa-làai) = Thai word for "seaweed/algae"
  - **วากาเมะ** (waa-gaa-mé) = Japanese "wakame" written in Thai script

### Why This is Challenging

1. **Mixed Language Origins**: Thai + Japanese transliteration
2. **Compound Structure**: Two distinct concepts joined together
3. **Search Expectations**: Users might search for either part
4. **Contextual Usage**: Used in food, health, and cooking contexts

## 🧪 Testing "สาหร่ายวากาเมะ"

### Basic Tokenization Test

```bash
# Test basic tokenization
curl -X POST http://localhost:8001/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "สาหร่ายวากาเมะเป็นอาหารทะเลที่มีประโยชน์"}'

# Expected result: Should properly separate the compound word
# ["สาหร่ายวากาเมะ", "เป็น", "อาหารทะเล", "ที่", "มี", "ประโยชน์"]
```

### Search Query Processing Test

```bash
# Test query processing for compound word
curl -X POST http://localhost:8001/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{
    "query": "สาหร่ายวากาเมะ",
    "options": {
      "expand_compounds": true,
      "enable_partial_matching": true
    }
  }'

# Should generate search variants including:
# - "สาหร่ายวากาเมะ" (exact match)
# - "สาหร่าย" (Thai part)
# - "วากาเมะ" (Japanese part)
# - "*สาหร่าย*" (partial match)
# - "*วากาเมะ*" (partial match)
```

### Partial Search Tests

```bash
# Test searching for Thai part only
curl -X POST http://localhost:8001/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{"query": "สาหร่าย", "options": {"expand_compounds": true}}'

# Test searching for Japanese part only
curl -X POST http://localhost:8001/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{"query": "วากาเมะ", "options": {"expand_compounds": true}}'
```

## 📊 Sample Test Data

### Test Documents

```json
{
  "test_documents": [
    {
      "id": "food_001",
      "title": "สูตรสลัดสาหร่ายวากาเมะ",
      "content": "สาหร่ายวากาเมะเป็นสาหร่ายทะเลจากญี่ปุ่นที่มีรสชาติหวานเล็กน้อย เหมาะสำหรับทำสลัดหรือซุป มีประโยชน์ต่อสุขภาพสูง",
      "category": "recipes",
      "tags": ["สาหร่าย", "อาหารญี่ปุ่น", "อาหารทะเล", "สุขภาพ"]
    },
    {
      "id": "health_001", 
      "title": "ประโยชน์ของสาหร่ายวากาเมะต่อสุขภาพ",
      "content": "สาหร่ายวากาเมะอุดมไปด้วยไอโอดีน แคลเซียม และเส้นใยอาหาร ช่วยบำรุงต่อมไทรอยด์และระบบย่อยอาหาร",
      "category": "health",
      "tags": ["สาหร่าย", "สุขภาพ", "วิตามิน", "แร่ธาตุ"]
    },
    {
      "id": "cooking_001",
      "title": "วิธีเตรียมสาหร่ายวากาเมะแห้ง",
      "content": "การเตรียมสาหร่ายวากาเมะแห้งให้นุ่ม ต้องแช่น้ำอุ่นประมาณ 10-15 นาที จนสาหร่ายขยายตัวและนุ่ม",
      "category": "cooking",
      "tags": ["สาหร่าย", "การทำอาหาร", "เทคนิค"]
    },
    {
      "id": "nutrition_001",
      "title": "เปรียบเทียบคุณค่าทางโภชนาการของสาหร่ายชนิดต่างๆ",
      "content": "สาหร่ายวากาเมะมีไอโอดีนสูงกว่าสาหร่ายโนริ แต่สาหร่ายคอมบุมีโปรตีนมากกว่า แต่ละชนิดมีประโยชน์แตกต่างกัน",
      "category": "nutrition",
      "tags": ["สาหร่าย", "โภชนาการ", "เปรียบเทียบ"]
    }
  ]
}
```

### Expected Search Results

```json
{
  "search_test_cases": [
    {
      "query": "สาหร่ายวากาเมะ",
      "expected_documents": ["food_001", "health_001", "cooking_001", "nutrition_001"],
      "description": "Exact compound word should find all documents"
    },
    {
      "query": "สาหร่าย",
      "expected_documents": ["food_001", "health_001", "cooking_001", "nutrition_001"],
      "description": "Thai part should find all documents containing the compound"
    },
    {
      "query": "วากาเมะ",
      "expected_documents": ["food_001", "health_001", "cooking_001", "nutrition_001"],
      "description": "Japanese part should find all documents containing the compound"
    },
    {
      "query": "สลัดสาหร่าย",
      "expected_documents": ["food_001"],
      "description": "Context-specific search should find relevant documents"
    },
    {
      "query": "อาหารทะเล",
      "expected_documents": ["food_001"],
      "description": "Related terms should find contextually relevant documents"
    }
  ]
}
```

## 🔧 Advanced Testing Scenarios

### Mixed Content Testing

```bash
# Test document with mixed Thai-Japanese-English content
curl -X POST http://localhost:8001/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{
    "text": "Wakame สาหร่ายวากาเมะ is a type of seaweed ที่มีประโยชน์ต่อสุขภาพ"
  }'

# Should handle:
# - English: "Wakame", "is", "a", "type", "of", "seaweed"
# - Thai-Japanese compound: "สาหร่ายวากาเมะ"
# - Thai text: "ที่", "มี", "ประโยชน์", "ต่อ", "สุขภาพ"
```

### Context-Aware Search Testing

```bash
# Test context-aware search
curl -X POST http://localhost:8001/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{
    "query": "สาหร่ายวากาเมะ สูตรอาหาร",
    "options": {
      "expand_compounds": true,
      "context_aware": true
    }
  }'

# Should understand this is a food/recipe context
# and boost food-related documents
```

### Synonym and Related Terms Testing

```bash
# Test with synonyms and related terms
curl -X POST http://localhost:8001/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{
    "query": "สาหร่ายวากาเมะ",
    "options": {
      "expand_compounds": true,
      "include_synonyms": true,
      "related_terms": ["สาหร่ายทะเล", "อาหารญี่ปุ่น", "wakame"]
    }
  }'
```

## 📈 Performance Testing

### Tokenization Speed Test

```python
import time
import requests

def test_compound_word_performance():
    """Test tokenization performance with compound words"""
    
    test_texts = [
        "สาหร่ายวากาเมะ",  # Simple compound
        "สาหร่ายวากาเมะเป็นอาหารทะเลที่มีประโยชน์",  # Compound in sentence
        "สูตรสลัดสาหร่ายวากาเมะแบบญี่ปุ่นแท้",  # Multiple compounds
        "สาหร่ายวากาเมะ โนริ คอมบุ และสาหร่ายทะเลอื่นๆ"  # Multiple seaweed types
    ]
    
    results = []
    for text in test_texts:
        times = []
        for _ in range(10):  # Run 10 times for average
            start = time.time()
            response = requests.post(
                "http://localhost:8001/api/v1/tokenize",
                json={"text": text}
            )
            end = time.time()
            
            if response.status_code == 200:
                times.append(end - start)
        
        avg_time = sum(times) / len(times) * 1000  # Convert to ms
        results.append({
            "text": text,
            "length": len(text),
            "avg_time_ms": avg_time,
            "chars_per_second": len(text) / (avg_time / 1000)
        })
    
    return results

# Run the test
performance_results = test_compound_word_performance()
for result in performance_results:
    print(f"Text: {result['text'][:30]}...")
    print(f"Speed: {result['chars_per_second']:.0f} chars/sec")
    print(f"Time: {result['avg_time_ms']:.2f}ms")
    print()
```

## 🎯 Quality Validation

### Accuracy Testing Script

```python
def test_compound_word_accuracy():
    """Test accuracy of compound word tokenization"""
    
    test_cases = [
        {
            "input": "สาหร่ายวากาเมะเป็นอาหารทะเล",
            "expected_tokens": ["สาหร่ายวากาเมะ", "เป็น", "อาหารทะเล"],
            "description": "Basic compound word recognition"
        },
        {
            "input": "ซื้อสาหร่ายวากาเมะแห้งจากญี่ปุ่น",
            "expected_contains": ["สาหร่ายวากาเมะ", "แห้ง", "ญี่ปุ่น"],
            "description": "Compound word in shopping context"
        },
        {
            "input": "สาหร่ายวากาเมะและสาหร่ายโนริ",
            "expected_contains": ["สาหร่ายวากาเมะ", "และ", "สาหร่ายโนริ"],
            "description": "Multiple compound words"
        }
    ]
    
    results = []
    for case in test_cases:
        response = requests.post(
            "http://localhost:8001/api/v1/tokenize",
            json={"text": case["input"]}
        )
        
        if response.status_code == 200:
            tokens = response.json()["tokens"]
            
            if "expected_tokens" in case:
                accuracy = len(set(tokens) & set(case["expected_tokens"])) / len(case["expected_tokens"])
            else:
                accuracy = len(set(tokens) & set(case["expected_contains"])) / len(case["expected_contains"])
            
            results.append({
                "description": case["description"],
                "input": case["input"],
                "tokens": tokens,
                "accuracy": accuracy,
                "passed": accuracy >= 0.8
            })
    
    return results
```

## 🔍 Search Quality Testing

### Search Relevance Test

```python
def test_search_relevance():
    """Test search relevance for compound words"""
    
    # First, index test documents
    test_docs = [
        {
            "id": "1",
            "title": "สูตรสลัดสาหร่ายวากาเมะ",
            "content": "วิธีทำสลัดสาหร่ายวากาเมะแบบญี่ปุ่น"
        },
        {
            "id": "2", 
            "title": "ประโยชน์ของสาหร่าย",
            "content": "สาหร่ายวากาเมะมีไอโอดีนสูง"
        },
        {
            "id": "3",
            "title": "อาหารทะเลญี่ปุ่น",
            "content": "ซูชิ ซาชิมิ และสาหร่ายต่างๆ"
        }
    ]
    
    # Index documents (pseudo-code - actual implementation depends on your setup)
    # index_documents(test_docs)
    
    # Test search queries
    search_tests = [
        {
            "query": "สาหร่ายวากาเมะ",
            "expected_top_results": ["1", "2"],  # Should rank recipe and health docs higher
            "description": "Exact compound word search"
        },
        {
            "query": "สลัดสาหร่าย",
            "expected_top_results": ["1"],  # Recipe should be top result
            "description": "Context-specific search"
        },
        {
            "query": "วากาเมะ",
            "expected_top_results": ["1", "2"],  # Should find compound word documents
            "description": "Japanese part search"
        }
    ]
    
    return search_tests
```

## 📚 Integration with Demo Script

Let me update the demo script to include "สาหร่ายวากาเมะ" examples:

```python
# Add to demo_thai_tokenizer.py
def demo_compound_word_challenges():
    """Demo challenging compound words like Thai-Japanese terms"""
    print("🌊 DEMO: Thai-Japanese Compound Words")
    print("=" * 50)
    
    challenging_compounds = [
        {
            "word": "สาหร่ายวากาเมะ",
            "meaning": "wakame seaweed (Thai + Japanese)",
            "context": "อาหารทะเล"
        },
        {
            "word": "ราเมนต้นกำเนิด", 
            "meaning": "original ramen (Thai + Japanese + Thai)",
            "context": "อาหารญี่ปุ่น"
        },
        {
            "word": "ซาชิมิปลาแซลมอน",
            "meaning": "salmon sashimi (Japanese + Thai + English)",
            "context": "อาหารดิบ"
        }
    ]
    
    for item in challenging_compounds:
        print(f"Word: {item['word']}")
        print(f"Meaning: {item['meaning']}")
        print(f"Context: {item['context']}")
        
        # Test tokenization
        response = requests.post(
            f"{BASE_URL}/api/v1/tokenize",
            json={"text": f"{item['word']}เป็น{item['context']}ที่มีประโยชน์"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"Tokens: {' | '.join(data['tokens'])}")
            print(f"Processing time: {data['processing_time_ms']}ms")
        
        print()
```

## 🧪 Comprehensive Test Suite
