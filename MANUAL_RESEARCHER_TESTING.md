# Manual Testing Guide for Researcher Index with วากาเมะ

This guide provides step-by-step manual commands to test วากาเมะ tokenization in your existing "researcher" index.

## 🔬 **Quick Test Commands**

### **1. Check Your Researcher Index**
```bash
# Check if researcher index exists and get document count
curl -X GET "http://10.0.2.105:7700/indexes/researcher" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
```

### **2. Search for วากาเมะ in Existing Data**
```bash
# Search for documents containing วากาเมะ in your researcher index
curl -X POST "http://10.0.2.105:7700/indexes/researcher/search" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "วากาเมะ",
    "limit": 10,
    "attributesToHighlight": ["*"]
  }'
```

**What to look for:**
- ✅ `"hits": [...]` with results = วากาเมะ is searchable
- ❌ `"hits": []` empty = วากาเมะ not found or poorly tokenized

### **3. Test Current Tokenization Quality**
```bash
# Test how the current tokenizer handles วากาเมะ
curl -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "นักวิจัยศึกษาสาหร่ายวากาเมะ"}'
```

**Expected good result:**
```json
{
  "tokens": ["นักวิจัย", "ศึกษา", "สาหร่าย", "วากาเมะ"],
  "processing_time_ms": 0
}
```

**Bad result (if วากาเมะ splits):**
```json
{
  "tokens": ["นักวิจัย", "ศึกษา", "สาหร่าย", "วา", "กา", "เมะ"]
}
```

### **4. Test New Document Indexing**
```bash
# Index a new test document with วากาเมะ
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "wakame-researcher-test",
    "title": "การวิจัยวากาเมะ",
    "content": "นักวิจัยพบว่าสาหร่ายวากาเมะมีประโยชน์ต่อสุขภาพ"
  }'
```

**Expected result:**
```json
{
  "document_id": "wakame-researcher-test",
  "status": "completed",
  "tokenized_fields": {
    "thai_content": {
      "tokens": ["นักวิจัย", "พบ", "ว่า", "สาหร่าย", "วากาเมะ", "มี", "ประโยชน์", "ต่อ", "สุขภาพ"]
    }
  }
}
```

### **5. Search for Your New Document**
```bash
# Wait 2 seconds for indexing, then search
sleep 2

curl -X POST "http://10.0.2.105:7700/indexes/researcher/search" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -H "Content-Type: application/json" \
  -d '{
    "q": "วากาเมะ",
    "limit": 10,
    "attributesToHighlight": ["title", "content"]
  }'
```

**What to look for:**
- Your new document should appear in results
- วากาเมะ should be highlighted in the content
- Should show improved tokenization

## 🧪 **Automated Testing Script**

Run the comprehensive test:
```bash
./scripts/testing/test-researcher-index.sh
```

This script will:
- ✅ Check your researcher index
- ✅ Search for existing วากาเมะ documents
- ✅ Test current tokenization quality
- ✅ Index a new test document
- ✅ Verify the new document is searchable
- ✅ Compare old vs new tokenization

## 🔍 **Manual Verification Steps**

### **Step 1: Check Current Search Quality**
```bash
# Test various compound word searches in your researcher index
for term in "วากาเมะ" "ซูชิ" "เทมปุระ" "ราเมน"; do
  echo "Testing: $term"
  curl -s -X POST "http://10.0.2.105:7700/indexes/researcher/search" \
    -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
    -d "{\"q\": \"$term\", \"limit\": 5}" | \
    grep -o '"hits":\[[^]]*\]' | grep -o '{"' | wc -l
done
```

### **Step 2: Test Specific Research Content**
```bash
# Test with research-specific content containing วากาเมะ
curl -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{
    "text": "การศึกษาวิจัยเกี่ยวกับสาหร่ายวากาเมะในด้านโภชนาการ"
  }'
```

### **Step 3: Compare Before/After**
```bash
# Before: Search existing documents
echo "=== EXISTING DOCUMENTS ==="
curl -s -X POST "http://10.0.2.105:7700/indexes/researcher/search" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -d '{"q": "วากาเมะ", "limit": 5}' | \
  jq '.hits | length'

# After: Index new document and search
echo "=== AFTER NEW INDEXING ==="
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "comparison-test",
    "content": "วิจัยใหม่เกี่ยวกับวากาเมะและประโยชน์ทางการแพทย์"
  }' > /dev/null

sleep 2

curl -s -X POST "http://10.0.2.105:7700/indexes/researcher/search" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -d '{"q": "วากาเมะ", "limit": 10}' | \
  jq '.hits | length'
```

## 📊 **Success Criteria**

### **✅ Good Tokenization:**
- วากาเมะ appears as single token: `["วากาเมะ"]`
- Search finds documents containing วากาเมะ
- New documents are properly indexed and searchable
- Processing time < 10ms

### **❌ Poor Tokenization:**
- วากาเมะ splits into: `["วา", "กา", "เมะ"]`
- Search doesn't find วากาเมะ documents
- Inconsistent search results

## 🔧 **If Tokenization is Poor**

If your tests show poor tokenization:

1. **Check dictionary loading:**
   ```bash
   ./scripts/maintenance/debug-dictionary.sh
   ```

2. **Rebuild with dictionary fix:**
   ```bash
   ./scripts/deployment/rebuild-with-dictionary.sh
   ```

3. **Consider selective reindexing:**
   ```bash
   ./scripts/maintenance/assess-reindexing-need.sh
   ```

## 🎯 **Quick Quality Check**

**One-liner to test everything:**
```bash
echo "Testing วากาเมะ tokenization..." && \
curl -s -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะ"}' | \
grep -q '"วากาเมะ"' && \
echo "✅ วากาเมะ preserved as compound" || \
echo "❌ วากาเมะ not preserved"
```

This will quickly tell you if your compound word tokenization is working correctly!