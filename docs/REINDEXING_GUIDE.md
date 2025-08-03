# MeiliSearch Thai Tokenization Reindexing Guide

This guide explains how to reindex your existing MeiliSearch data to add proper Thai compound word tokenization support.

## 🎯 **Why Reindex?**

Your existing indexes (research, research_entity, scholar, faq, training) contain documents **without** the `tokenized_content` field that enables proper Thai compound word search. 

**Before reindexing:**
- Search for "วากาเมะ" may not find documents containing this compound word
- Thai text is not properly segmented for search

**After reindexing:**
- Documents have `tokenized_content` field with proper Thai segmentation
- Compound words like วากาเมะ, รูเมน, ซูชิ are preserved and searchable
- Improved search quality for Thai content

## 🔍 **Step 1: Analyze What Needs Reindexing**

First, check which indexes need reindexing:

```bash
./scripts/maintenance/analyze-reindex-need.sh
```

This will show you:
- Which indexes have Thai content
- Which indexes already have `tokenized_content` 
- Which indexes need reindexing
- Estimated processing time

**Example output:**
```
📊 Analysis Results:
  • Total indexes: 7
  • Total documents: 15,432

🔄 Reindexing Status:
  • Indexes needing reindexing: 5
  • Indexes already tokenized: 2

⚠️ Partial reindexing needed!
```

## 🧪 **Step 2: Preview Changes (Dry Run)**

Before making any changes, preview what would happen:

```bash
# Preview all indexes
./scripts/maintenance/reindex-all-data.sh --dry-run --all

# Preview specific index
./scripts/maintenance/reindex-all-data.sh --dry-run --index research
```

**Dry run shows:**
- Which documents would be processed
- How many documents need tokenization
- Processing time estimates
- No actual changes are made

## 🔄 **Step 3: Perform Reindexing**

### **Option A: Reindex All Indexes (Recommended)**

```bash
# Reindex all indexes with backup
./scripts/maintenance/reindex-all-data.sh --all

# Reindex all without backup (faster, but riskier)
./scripts/maintenance/reindex-all-data.sh --all --no-backup
```

### **Option B: Reindex Specific Indexes**

```bash
# Reindex research index
./scripts/maintenance/reindex-all-data.sh --index research

# Reindex multiple specific indexes
./scripts/maintenance/reindex-all-data.sh --index research
./scripts/maintenance/reindex-all-data.sh --index faq
./scripts/maintenance/reindex-all-data.sh --index training
```

### **Option C: Advanced Options**

```bash
# Force reindexing even if not needed
./scripts/maintenance/reindex-all-data.sh --all --force

# Exclude certain indexes
./scripts/maintenance/reindex-all-data.sh --all --exclude documents --exclude temp

# Reindex without creating backups
./scripts/maintenance/reindex-all-data.sh --all --no-backup
```

## 📊 **Understanding the Process**

### **What Happens During Reindexing:**

1. **Document Extraction**: All documents are extracted from the index
2. **Backup Creation**: A backup index is created (unless `--no-backup`)
3. **Thai Content Detection**: Documents are analyzed for Thai content
4. **Tokenization**: Thai text is processed through your tokenizer
5. **Field Addition**: `tokenized_content` field is added to documents
6. **Re-indexing**: Processed documents are indexed back to MeiliSearch

### **Document Structure Before/After:**

**Before reindexing:**
```json
{
  "id": "doc123",
  "title": "การวิจัยวากาเมะ",
  "content": "นักวิจัยพบว่าสาหร่ายวากาเมะมีประโยชน์...",
  "authors": ["นักวิจัย"]
}
```

**After reindexing:**
```json
{
  "id": "doc123",
  "title": "การวิจัยวากาเมะ",
  "content": "นักวิจัยพบว่าสาหร่ายวากาเมะมีประโยชน์...",
  "thai_content": "การวิจัยวากาเมะ นักวิจัยพบว่าสาหร่ายวากาเมะมีประโยชน์",
  "tokenized_content": "การวิจัย วากาเมะ นักวิจัย พบ ว่า สาหร่าย วากาเมะ มี ประโยชน์",
  "authors": ["นักวิจัย"],
  "metadata": {
    "tokenization_version": "1.0",
    "processed_at": "2025-01-31T10:30:00Z",
    "token_count": 9,
    "thai_content_detected": true
  }
}
```

## ⏱️ **Performance and Timing**

### **Processing Speed:**
- **Rate**: ~10 documents per second
- **Small indexes** (<1,000 docs): 2-5 minutes
- **Medium indexes** (1,000-10,000 docs): 10-30 minutes  
- **Large indexes** (>10,000 docs): 30+ minutes

### **Resource Usage:**
- **CPU**: Moderate usage during tokenization
- **Memory**: ~256MB per processing batch
- **Disk**: Temporary space for backups
- **Network**: Continuous MeiliSearch API calls

### **Optimization Tips:**
- Run during low-traffic periods
- Use `--no-backup` for faster processing (if you have other backups)
- Monitor system resources
- Process smaller indexes first to test

## 🔒 **Safety and Backups**

### **Automatic Backups:**
By default, the script creates backup indexes:
- **Backup name**: `{index_name}_backup_{timestamp}`
- **Example**: `research_backup_20250131_103000`
- **Contents**: Original documents before reindexing

### **Manual Backup (Recommended):**
```bash
# Create manual backup before reindexing
curl -X POST "http://10.0.2.105:7700/dumps" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
```

### **Recovery Options:**
If something goes wrong:
1. **Use backup index**: Copy data from `{index}_backup_{timestamp}`
2. **Restore from dump**: Use MeiliSearch dump file
3. **Re-run reindexing**: Fix issues and run again

## 🧪 **Step 4: Test Results**

After reindexing, test the improved search quality:

### **Test Compound Words:**
```bash
# Test all indexes
./scripts/testing/test-all-indexes.sh

# Test specific compound words
curl -X POST "http://10.0.2.105:7700/indexes/research/search" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -d '{"q": "วากาเมะ", "limit": 10}'
```

### **Expected Improvements:**
- ✅ **วากาเมะ** found as complete compound word
- ✅ **รูเมน** preserved in veterinary documents  
- ✅ **ซูชิ, เทมปุระ** found in food-related content
- ✅ Better highlighting in search results
- ✅ More relevant search results

## 🚨 **Troubleshooting**

### **Common Issues:**

**1. Connection Errors:**
```bash
# Check MeiliSearch is running
curl http://10.0.2.105:7700/health

# Check API key
curl -H "Authorization: Bearer YOUR_API_KEY" \
  http://10.0.2.105:7700/indexes
```

**2. Processing Failures:**
- Check logs in `reindex_YYYYMMDD_HHMMSS.log`
- Look for specific error messages
- Try reindexing smaller batches

**3. Out of Memory:**
- Reduce batch size in the script
- Close other applications
- Process indexes one at a time

**4. Slow Performance:**
- Check system resources
- Reduce concurrent processing
- Use `--no-backup` for faster processing

### **Recovery Commands:**

**Restore from backup:**
```bash
# List backup indexes
curl -X GET "http://10.0.2.105:7700/indexes" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" | \
  grep backup

# Copy backup to main index (manual process)
# This requires custom script - contact support if needed
```

## 📈 **Monitoring Progress**

### **Real-time Monitoring:**
```bash
# Watch reindexing logs
tail -f reindex_*.log

# Monitor MeiliSearch tasks
curl -X GET "http://10.0.2.105:7700/tasks" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"

# Check index document counts
curl -X GET "http://10.0.2.105:7700/indexes/research" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId"
```

### **Progress Indicators:**
- **Log messages**: Show processing status
- **Document counts**: Should remain the same
- **Processing time**: Logged per batch
- **Error counts**: Any failed documents

## 🎯 **Best Practices**

### **Before Reindexing:**
1. ✅ **Analyze first**: Run analysis script
2. ✅ **Test with dry-run**: Preview changes
3. ✅ **Create backups**: Manual dump + automatic backups
4. ✅ **Schedule downtime**: During low-traffic periods
5. ✅ **Monitor resources**: Ensure sufficient CPU/memory

### **During Reindexing:**
1. ✅ **Monitor logs**: Watch for errors
2. ✅ **Check progress**: Verify document counts
3. ✅ **Don't interrupt**: Let process complete
4. ✅ **Monitor system**: Watch CPU/memory usage

### **After Reindexing:**
1. ✅ **Test search quality**: Use test scripts
2. ✅ **Verify compound words**: Test วากาเมะ, รูเมน, etc.
3. ✅ **Update frontend**: Use new tokenized_content field
4. ✅ **Clean up backups**: Remove old backup indexes
5. ✅ **Document changes**: Update team on improvements

## 🔧 **Advanced Usage**

### **Python Script Direct Usage:**
```bash
# Use Python script directly for more control
cd /path/to/meilisearch-thai

# Reindex with custom settings
python3 scripts/maintenance/reindex-existing-data.py \
  --index research \
  --force \
  --no-backup

# Reindex all with exclusions
python3 scripts/maintenance/reindex-existing-data.py \
  --all-indexes \
  --exclude documents temp \
  --config custom_config.json
```

### **Custom Configuration:**
Create `custom_config.json`:
```json
{
  "meilisearch": {
    "host": "http://10.0.2.105:7700",
    "api_key": "your_api_key",
    "timeout_ms": 60000,
    "max_retries": 5
  },
  "processing": {
    "batch_size": 25,
    "max_concurrent": 3
  }
}
```

## 📋 **Checklist**

### **Pre-Reindexing Checklist:**
- [ ] Run analysis script
- [ ] Review which indexes need reindexing
- [ ] Test with dry-run
- [ ] Create manual backup
- [ ] Schedule appropriate time
- [ ] Ensure system resources available

### **Reindexing Checklist:**
- [ ] Run reindexing command
- [ ] Monitor progress logs
- [ ] Check for errors
- [ ] Verify document counts remain same
- [ ] Wait for completion

### **Post-Reindexing Checklist:**
- [ ] Test compound word search
- [ ] Run test scripts
- [ ] Verify search quality improvements
- [ ] Update frontend integration
- [ ] Clean up backup indexes
- [ ] Document completion

## 🎉 **Success Indicators**

You'll know reindexing was successful when:

1. ✅ **Search works**: วากาเมะ, รูเมน, ซูชิ return relevant results
2. ✅ **Highlighting**: Compound words are highlighted properly
3. ✅ **Document counts**: Same number of documents as before
4. ✅ **New fields**: Documents have `tokenized_content` and `thai_content`
5. ✅ **Performance**: Search is fast and accurate
6. ✅ **No errors**: Reindexing completed without failures

## 🆘 **Getting Help**

If you encounter issues:

1. **Check logs**: Look at `reindex_*.log` files
2. **Run analysis**: Use analysis script to diagnose
3. **Test connectivity**: Verify MeiliSearch connection
4. **Review documentation**: Check this guide
5. **Contact support**: Provide logs and error messages

---

**Remember**: Reindexing is a one-time process that significantly improves Thai compound word search quality. Take your time, test thoroughly, and enjoy better search results! 🚀