# Testing Compound Word Search in Meilisearch

This guide specifically covers how to test that compound words like "วากาเมะ" are properly tokenized and searchable in Meilisearch.

## 🎯 Testing วากาเมะ Compound Search

### Step 1: Verify Tokenization

**Test the tokenization first:**
```bash
curl -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "ฉันกินสาหร่ายวากาเมะ"}'
```

**Expected result:**
```json
{
  "original_text": "ฉันกินสาหร่ายวากาเมะ",
  "tokens": ["ฉัน", "กิน", "สาหร่าย", "วากาเมะ"],
  "word_boundaries": [0, 3, 6, 13, 20],
  "processing_time_ms": 0
}
```

✅ **Success criteria**: "วากาเมะ" appears as a single token, not split into "วา", "กา", "เมะ"

### Step 2: Index Test Documents

**Index documents containing วากาเมะ:**
```bash
# Document 1: Simple wakame
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "wakame-simple",
    "title": "สาหร่ายวากาเมะ",
    "content": "ฉันกินสาหร่ายวากาเมะ"
  }'

# Document 2: Wakame in context
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "wakame-context",
    "title": "อาหารญี่ปุ่น",
    "content": "ร้านซูชิเสิร์ฟสาหร่ายวากาเมะสดใหม่ทุกวัน"
  }'

# Document 3: Multiple compounds
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "wakame-multiple",
    "title": "เมนูญี่ปุ่น",
    "content": "เมนูแนะนำ: ซูชิ เทมปุระ สาหร่ายวากาเมะ และราเมน"
  }'
```

**Verify indexing success:**
Each request should return:
```json
{
  "document_id": "wakame-xxx",
  "status": "completed",
  "tokenized_fields": {
    "thai_content": {
      "tokens": ["...", "วากาเมะ", "..."]
    }
  }
}
```

### Step 3: Test Search Functionality

**Search for วากาเมะ through Thai Tokenizer:**
```bash
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "วากาเมะ",
    "limit": 10
  }'
```

**Search directly in Meilisearch:**
```bash
curl -X POST "http://10.0.2.105:7700/indexes/thai_documents/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -d '{
    "q": "วากาเมะ",
    "limit": 10,
    "attributesToHighlight": ["*"]
  }'
```

**Expected search results:**
```json
{
  "hits": [
    {
      "id": "wakame-simple",
      "title": "สาหร่ายวากาเมะ",
      "content": "ฉันกินสาหร่ายวากาเมะ",
      "_formatted": {
        "content": "ฉันกินสาหร่าย<em>วากาเมะ</em>"
      }
    },
    {
      "id": "wakame-context",
      "title": "อาหารญี่ปุ่น",
      "content": "ร้านซูชิเสิร์ฟสาหร่ายวากาเมะสดใหม่ทุกวัน"
    }
  ],
  "query": "วากาเมะ",
  "processingTimeMs": 1
}
```

### Step 4: Test Partial Searches

**Test that partial searches work correctly:**
```bash
# Should find วากาเมะ documents
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "วากา"}'

# Should find วากาเมะ documents  
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "เมะ"}'

# Should find documents with both
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "สาหร่าย วากาเมะ"}'
```

### Step 5: Verify Search Quality

**Test search ranking and relevance:**
```bash
# Search for "สาหร่าย" should rank documents with "สาหร่ายวากาเมะ" highly
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "สาหร่าย",
    "limit": 10,
    "attributesToHighlight": ["title", "content"]
  }'
```

## 🧪 Comprehensive Test Script

**Run all tests at once:**
```bash
#!/bin/bash
echo "🧪 Testing Wakame Compound Search in Meilisearch"

# Test 1: Tokenization
echo "1. Testing tokenization..."
TOKENIZE_RESULT=$(curl -s -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "ฉันกินสาหร่ายวากาเมะ"}')

if echo "$TOKENIZE_RESULT" | grep -q '"วากาเมะ"'; then
  echo "✅ Tokenization: วากาเมะ preserved as compound"
else
  echo "❌ Tokenization: วากาเมะ not preserved"
  echo "$TOKENIZE_RESULT"
fi

# Test 2: Document indexing
echo "2. Testing document indexing..."
INDEX_RESULT=$(curl -s -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-wakame-'$(date +%s)'",
    "title": "ทดสอบวากาเมะ",
    "content": "ฉันกินสาหร่ายวากาเมะที่ร้านซูชิ"
  }')

if echo "$INDEX_RESULT" | grep -q '"status":"completed"'; then
  echo "✅ Indexing: Document indexed successfully"
else
  echo "❌ Indexing: Failed to index document"
  echo "$INDEX_RESULT"
fi

# Test 3: Search functionality
echo "3. Testing search..."
sleep 2  # Wait for indexing to complete

SEARCH_RESULT=$(curl -s -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "วากาเมะ", "limit": 5}')

if echo "$SEARCH_RESULT" | grep -q '"hits"'; then
  HIT_COUNT=$(echo "$SEARCH_RESULT" | grep -o '"hits":\[' | wc -l)
  echo "✅ Search: Found results for วากาเมะ"
  echo "   Results: $SEARCH_RESULT"
else
  echo "❌ Search: No results found for วากาเมะ"
  echo "$SEARCH_RESULT"
fi

echo "🎯 Wakame compound search test completed!"
```

## 🔍 Troubleshooting Search Issues

### Issue: วากาเมะ splits into multiple tokens

**Diagnosis:**
```bash
# Check tokenization
curl -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะ"}'

# Should return: {"tokens": ["วากาเมะ"]}
# If it returns: {"tokens": ["วา", "กา", "เมะ"]} - dictionary not working
```

**Solution:**
```bash
# Check dictionary loading
./scripts/maintenance/debug-dictionary.sh

# Rebuild with dictionary fix
./scripts/deployment/rebuild-with-dictionary.sh
```

### Issue: Search doesn't find วากาเมะ documents

**Diagnosis:**
```bash
# Check if documents are indexed
curl -X GET "http://10.0.2.105:7700/indexes/thai_documents/documents" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"

# Check Meilisearch settings
curl -X GET "http://10.0.2.105:7700/indexes/thai_documents/settings" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
```

**Solution:**
```bash
# Re-index documents
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{"id": "wakame-test", "content": "ฉันกินสาหร่ายวากาเมะ"}'

# Wait and search again
sleep 3
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "วากาเมะ"}'
```

### Issue: Partial searches don't work

**Diagnosis:**
```bash
# Test different search terms
for term in "วา" "กา" "เมะ" "วากา" "กาเมะ" "วากาเมะ"; do
  echo "Searching for: $term"
  curl -s -X POST "https://search.cads.arda.or.th/api/v1/search" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"$term\"}" | jq '.hits | length'
done
```

**Solution:**
Check Meilisearch tokenization settings and ensure proper prefix search configuration.

## 📊 Success Metrics

### Tokenization Success
- ✅ "ฉันกินสาหร่ายวากาเมะ" → `["ฉัน", "กิน", "สาหร่าย", "วากาเมะ"]`
- ✅ Processing time < 10ms
- ✅ No errors in tokenization

### Indexing Success  
- ✅ Documents with วากาเมะ index successfully
- ✅ Tokenized fields contain "วากาเมะ" as single token
- ✅ Index completion status: "completed"

### Search Success
- ✅ Search for "วากาเมะ" returns relevant documents
- ✅ Search results highlight the compound word correctly
- ✅ Partial searches ("วากา", "เมะ") work appropriately
- ✅ Search response time < 50ms

This comprehensive testing ensures that the compound word tokenization and search functionality works correctly end-to-end.