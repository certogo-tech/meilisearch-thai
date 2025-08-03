# Managing Existing Meilisearch Indexes

This guide covers how to handle existing Meilisearch indexes when updating the Thai Tokenizer service, especially after custom dictionary changes.

## 🎯 **Do You Need to Reindex?**

### **Quick Assessment**

**Check your current tokenization quality:**
```bash
# 1. Check a sample document from your existing index
curl -X GET "http://10.0.2.105:7700/indexes/YOUR_INDEX_NAME/documents/SAMPLE_DOC_ID" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"

# 2. Test search for compound words
curl -X POST "http://10.0.2.105:7700/indexes/YOUR_INDEX_NAME/search" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -d '{"q": "วากาเมะ", "limit": 5}'

# 3. Check if compound words are properly searchable
curl -X POST "http://10.0.2.105:7700/indexes/YOUR_INDEX_NAME/search" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -d '{"q": "ซูชิ", "limit": 5}'
```

### **Decision Matrix**

| Scenario | Action Required | Reason |
|----------|----------------|---------|
| **Search works well for compound words** | ✅ No reindexing needed | Existing tokenization is sufficient |
| **Some compound words don't search properly** | 🔄 Selective reindexing | Only problematic documents need updating |
| **Poor search quality overall** | 🔄 Full reindexing | Complete tokenization improvement needed |
| **New compound words added to dictionary** | 🔄 Future documents only | Existing docs can stay as-is |

---

## 🔍 **Option 1: No Reindexing (Recommended)**

### **When to Use:**
- Existing search quality is acceptable
- You only want improved tokenization for new documents
- You want to minimize system disruption

### **Implementation:**
```bash
# Simply deploy the updated tokenizer
./deploy.sh production

# Test with new documents
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "new-doc-test",
    "title": "ทดสอบใหม่",
    "content": "ฉันกินสาหร่ายวากาเมะที่ร้านซูชิ"
  }'

# Verify improved tokenization
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "วากาเมะ"}'
```

### **Pros:**
- ✅ No downtime
- ✅ No system load from reindexing
- ✅ Immediate benefits for new content
- ✅ Existing search continues to work

### **Cons:**
- ❌ Inconsistent tokenization between old and new documents
- ❌ Some compound words in old documents may not be searchable

---

## 🎯 **Option 2: Selective Reindexing**

### **When to Use:**
- You have specific documents with compound words that need better tokenization
- You want to improve search for specific content types
- You have a manageable number of documents to update

### **Implementation:**

**Step 1: Identify documents to reindex**
```bash
# Search for documents containing compound words that might be poorly tokenized
curl -X POST "http://10.0.2.105:7700/indexes/thai_documents/search" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -d '{
    "q": "วากาเมะ OR ซูชิ OR เทมปุระ OR ราเมน",
    "limit": 100,
    "attributesToRetrieve": ["id", "title"]
  }' > documents_to_reindex.json
```

**Step 2: Create selective reindexing script**
```bash
#!/bin/bash
# selective-reindex.sh

echo "🔄 Selective Reindexing for Compound Words"

# List of compound words to check
COMPOUND_WORDS=("วากาเมะ" "ซูชิ" "เทมปุระ" "ราเมน" "อุด้ง" "โซบะ")

for word in "${COMPOUND_WORDS[@]}"; do
    echo "Processing documents with: $word"
    
    # Search for documents containing this compound word
    DOCS=$(curl -s -X POST "http://10.0.2.105:7700/indexes/thai_documents/search" \
        -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
        -d "{\"q\": \"$word\", \"limit\": 50}" | jq -r '.hits[].id')
    
    # Reindex each document through Thai Tokenizer
    for doc_id in $DOCS; do
        if [ "$doc_id" != "null" ] && [ -n "$doc_id" ]; then
            echo "Reindexing document: $doc_id"
            
            # Get original document
            ORIGINAL=$(curl -s -X GET "http://10.0.2.105:7700/indexes/thai_documents/documents/$doc_id" \
                -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId")
            
            # Extract content and reindex through Thai Tokenizer
            TITLE=$(echo "$ORIGINAL" | jq -r '.title // ""')
            CONTENT=$(echo "$ORIGINAL" | jq -r '.content // ""')
            
            if [ "$CONTENT" != "" ]; then
                curl -s -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
                    -H "Content-Type: application/json" \
                    -d "{
                        \"id\": \"$doc_id\",
                        \"title\": \"$TITLE\",
                        \"content\": \"$CONTENT\"
                    }" > /dev/null
                
                echo "✅ Reindexed: $doc_id"
                sleep 0.1  # Rate limiting
            fi
        fi
    done
done

echo "🎉 Selective reindexing completed!"
```

**Step 3: Run selective reindexing**
```bash
chmod +x selective-reindex.sh
./selective-reindex.sh
```

### **Pros:**
- ✅ Improves search for specific compound words
- ✅ Lower system load than full reindexing
- ✅ Targeted improvement where needed

### **Cons:**
- ❌ More complex to implement
- ❌ May miss some documents
- ❌ Still creates inconsistency

---

## 🔄 **Option 3: Full Reindexing**

### **When to Use:**
- You want consistent tokenization across all documents
- Search quality improvement is critical
- You have the system resources and time for full reindexing

### **Implementation:**

**Step 1: Create full reindexing script**
```bash
#!/bin/bash
# full-reindex.sh

echo "🔄 Full Reindexing of Meilisearch Documents"
echo "⚠️  This will reindex ALL documents with improved tokenization"

read -p "Are you sure you want to proceed? (y/N): " confirm
if [[ $confirm != [yY] ]]; then
    echo "Reindexing cancelled"
    exit 0
fi

# Get all document IDs
echo "📋 Getting list of all documents..."
ALL_DOCS=$(curl -s -X GET "http://10.0.2.105:7700/indexes/thai_documents/documents?limit=10000" \
    -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" | jq -r '.results[].id')

TOTAL_DOCS=$(echo "$ALL_DOCS" | wc -l)
echo "📊 Found $TOTAL_DOCS documents to reindex"

COUNTER=0
for doc_id in $ALL_DOCS; do
    if [ "$doc_id" != "null" ] && [ -n "$doc_id" ]; then
        COUNTER=$((COUNTER + 1))
        echo "[$COUNTER/$TOTAL_DOCS] Reindexing: $doc_id"
        
        # Get original document
        ORIGINAL=$(curl -s -X GET "http://10.0.2.105:7700/indexes/thai_documents/documents/$doc_id" \
            -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId")
        
        # Extract all fields
        TITLE=$(echo "$ORIGINAL" | jq -r '.title // ""')
        CONTENT=$(echo "$ORIGINAL" | jq -r '.content // ""')
        
        # Reindex through Thai Tokenizer
        if [ "$CONTENT" != "" ]; then
            RESPONSE=$(curl -s -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
                -H "Content-Type: application/json" \
                -d "{
                    \"id\": \"$doc_id\",
                    \"title\": \"$TITLE\",
                    \"content\": \"$CONTENT\"
                }")
            
            if echo "$RESPONSE" | grep -q '"status":"completed"'; then
                echo "✅ Success: $doc_id"
            else
                echo "❌ Failed: $doc_id"
                echo "   Response: $RESPONSE"
            fi
        fi
        
        # Rate limiting to avoid overwhelming the system
        sleep 0.1
        
        # Progress update every 100 documents
        if [ $((COUNTER % 100)) -eq 0 ]; then
            echo "📊 Progress: $COUNTER/$TOTAL_DOCS documents processed"
        fi
    fi
done

echo "🎉 Full reindexing completed!"
echo "📊 Total documents processed: $COUNTER"
```

**Step 2: Run full reindexing (with caution)**
```bash
chmod +x full-reindex.sh
./full-reindex.sh
```

**Step 3: Verify reindexing results**
```bash
# Test compound word searches
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "วากาเมะ", "limit": 10}'

# Check index statistics
curl -X GET "http://10.0.2.105:7700/indexes/thai_documents/stats" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
```

### **Pros:**
- ✅ Consistent tokenization across all documents
- ✅ Maximum search quality improvement
- ✅ All compound words properly searchable

### **Cons:**
- ❌ High system load during reindexing
- ❌ Time-consuming for large datasets
- ❌ Potential service disruption

---

## 🛡️ **Safe Reindexing Practices**

### **Before Reindexing:**

1. **Backup your index:**
```bash
# Export all documents
curl -X GET "http://10.0.2.105:7700/indexes/thai_documents/documents?limit=100000" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  > backup_documents_$(date +%Y%m%d_%H%M%S).json
```

2. **Test with a small subset:**
```bash
# Test reindexing with just 10 documents first
curl -X GET "http://10.0.2.105:7700/indexes/thai_documents/documents?limit=10" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
```

3. **Monitor system resources:**
```bash
# Monitor during reindexing
watch -n 5 'docker stats $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)'
```

### **During Reindexing:**

1. **Rate limiting:** Add delays between requests
2. **Progress monitoring:** Log progress regularly
3. **Error handling:** Capture and log failures
4. **Health checks:** Monitor service health

### **After Reindexing:**

1. **Verify search quality:**
```bash
# Test various compound word searches
./scripts/testing/test-external-api.sh
```

2. **Check index health:**
```bash
curl -X GET "http://10.0.2.105:7700/indexes/thai_documents/stats" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
```

---

## 📊 **Recommendation Matrix**

| Index Size | Current Quality | Recommendation |
|------------|----------------|----------------|
| **< 1,000 docs** | Any | 🔄 Full reindexing |
| **1,000 - 10,000 docs** | Good | ✅ No reindexing |
| **1,000 - 10,000 docs** | Poor | 🎯 Selective reindexing |
| **> 10,000 docs** | Good | ✅ No reindexing |
| **> 10,000 docs** | Poor | 🎯 Selective reindexing |
| **> 100,000 docs** | Any | ✅ No reindexing (new docs only) |

## 🎯 **My Recommendation**

For most production scenarios, I recommend **Option 1 (No Reindexing)** because:

1. ✅ **Zero downtime** - Service continues normally
2. ✅ **Immediate benefits** - New documents get improved tokenization
3. ✅ **Low risk** - No chance of breaking existing search
4. ✅ **Resource efficient** - No system load from reindexing

The improved tokenization will naturally improve your search quality over time as you add new content and update existing documents.

**Only consider reindexing if:**
- Your current search quality is significantly poor
- You have specific business requirements for consistent tokenization
- You have the resources and time for a full reindexing operation

Would you like me to help you assess your current index quality to make the best decision?