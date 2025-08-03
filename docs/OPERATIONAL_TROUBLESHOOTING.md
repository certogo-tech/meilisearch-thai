# Thai Tokenizer - Operational Troubleshooting Guide

This guide provides step-by-step instructions for common operational tasks and troubleshooting scenarios for the Thai Tokenizer service.

## 🚀 Quick Reference

### Main Commands

```bash
# Deploy to production
./deploy.sh production

# Test the service
./deploy.sh test

# Debug issues
./deploy.sh debug

# Validate configuration
./deploy.sh validate
```

### Service URLs

- **Production API**: <https://search.cads.arda.or.th>
- **Health Check**: <https://search.cads.arda.or.th/api/v1/health/detailed>
- **API Documentation**: <https://search.cads.arda.or.th/docs>
- **Meilisearch**: <http://10.0.2.105:7700>

---

## 📚 Table of Contents

1. [Adding New Custom Dictionary Compounds](#1-adding-new-custom-dictionary-compounds)
2. [Rebuild, Restart & Maintain Service](#2-rebuild-restart--maintain-service)
3. [Testing Compound Word Search in Meilisearch](#3-testing-compound-word-search-in-meilisearch)
4. [Health Monitoring & Diagnostics](#4-health-monitoring--diagnostics)
5. [Configuration Management](#5-configuration-management)
6. [Performance Optimization](#6-performance-optimization)
7. [Backup & Recovery](#7-backup--recovery)
8. [Common Issues & Solutions](#8-common-issues--solutions)

---

## 1. Adding New Custom Dictionary Compounds

### 1.1 Add New Compound Words

**Step 1: Edit the dictionary file**

```bash
# Edit the custom dictionary
nano data/dictionaries/thai_compounds.json
```

**Step 2: Add your compound words**

```json
{
  "thai_japanese_compounds": [
    "วากาเมะ",
    "ซาชิมิ",
    "เทมปุระ",
    "ซูชิ",
    "ราเมน",
    "YOUR_NEW_COMPOUND_WORD_HERE"
  ],
  "thai_english_compounds": [
    "คอมพิวเตอร์",
    "อินเทอร์เน็ต",
    "YOUR_NEW_ENGLISH_COMPOUND_HERE"
  ]
}
```

**Step 3: Rebuild the service**

```bash
./deploy.sh rebuild
```

**Step 4: Test the new compound**

```bash
# Test your new compound word
curl -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "YOUR_TEST_TEXT_WITH_NEW_COMPOUND"}'
```

### 1.2 Validate Dictionary Loading

**Check if dictionary is loaded:**

```bash
./scripts/maintenance/debug-dictionary.sh
```

**Expected output:**

```
✅ Custom dictionary is loaded with X words
✅ 'YOUR_NEW_WORD' found in dictionary file
```

---

## 2. Rebuild, Restart & Maintain Service

### 2.1 Service Management Commands

**Quick Restart:**

```bash
./deploy.sh rebuild
```

**Full Rebuild (recommended after code changes):**

```bash
./scripts/deployment/simple-rebuild.sh
```

**Restart with Dictionary Updates:**

```bash
./scripts/deployment/rebuild-with-dictionary.sh
```

**Production Deployment (full setup):**

```bash
./scripts/deployment/deploy-production.sh
```

### 2.2 Check Service Status

**Container Status:**

```bash
docker ps --filter "name=thai-tokenizer"
```

**Service Logs:**

```bash
docker logs $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1) --tail 50
```

**Health Check:**

```bash
curl -s "https://search.cads.arda.or.th/api/v1/health/detailed" | jq .
```

### 2.3 Maintenance Tasks

**Clean Up Old Containers:**

```bash
docker system prune -f
docker volume prune -f
```

**Update Environment Configuration:**

```bash
# Backup current config
cp .env.production backups/env/.env.production.backup.$(date +%Y%m%d_%H%M%S)

# Edit configuration
nano .env.production

# Apply changes
./deploy.sh rebuild
```

---

## 3. Testing Compound Word Search in Meilisearch

### 3.1 Test Wakame Tokenization

**Test the specific wakame case:**

```bash
./scripts/testing/test-wakame-tokenization.sh
```

**Expected result:**

```json
{
  "original_text": "ฉันกินสาหร่ายวากาเมะ",
  "tokens": ["ฉัน", "กิน", "สาหร่าย", "วากาเมะ"],
  "word_boundaries": [0, 3, 6, 13, 20]
}
```

### 3.2 Test Document Indexing with Compounds

**Index a document with compound words:**

```bash
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "test-compound-$(date +%s)",
    "title": "ทดสอบคำประสม",
    "content": "ฉันกินสาหร่ายวากาเมะที่ร้านซูชิ"
  }'
```

**Expected response:**

```json
{
  "document_id": "test-compound-xxx",
  "status": "completed",
  "tokenized_fields": {
    "thai_content": {
      "tokens": ["ฉัน", "กิน", "สาหร่าย", "วากาเมะ", "ที่", "ร้าน", "ซูชิ"]
    }
  }
}
```

### 3.3 Search for Compound Words in Meilisearch

**Direct Meilisearch search:**

```bash
# Search for วากาเมะ
curl -X POST "http://10.0.2.105:7700/indexes/thai_documents/search" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  -d '{"q": "วากาเมะ", "limit": 10}'
```

**Search through Thai Tokenizer:**

```bash
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "วากาเมะ", "limit": 10}'
```

---

## 4. Health Monitoring & Diagnostics

### 4.1 Comprehensive Health Check

**Run full health diagnostics:**

```bash
./scripts/testing/test-service-health.sh
```

**Check specific health components:**

```bash
# Configuration health
curl -s "https://search.cads.arda.or.th/api/v1/health/check/configuration_validity"

# Meilisearch health
curl -s "https://search.cads.arda.or.th/api/v1/health/check/meilisearch"

# Tokenizer health
curl -s "https://search.cads.arda.or.th/api/v1/health/check/tokenizer"

# Thai models health
curl -s "https://search.cads.arda.or.th/api/v1/health/check/thai_models"
```

### 4.2 Performance Monitoring

**Check performance metrics:**

```bash
curl -s "https://search.cads.arda.or.th/api/v1/health/summary" | jq '.key_metrics'
```

**Monitor processing times:**

```bash
# Test tokenization performance
time curl -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "ฉันกินสาหร่ายวากาเมะที่ร้านซูชิญี่ปุ่นในกรุงเทพมหานคร"}'
```

### 4.3 Resource Usage

**Check container resource usage:**

```bash
docker stats $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)
```

**Check disk usage:**

```bash
df -h
docker system df
```

---

## 5. Configuration Management

### 5.1 Environment Variables

**Key configuration variables:**

```bash
# Meilisearch connection
MEILISEARCH_HOST=http://10.0.2.105:7700
MEILISEARCH_API_KEY=FKjPKTmFnCl7EPg6YLula1DC6n5mHqId
MEILISEARCH_INDEX=thai_documents

# Custom dictionary
CUSTOM_DICTIONARY_PATH=data/dictionaries/thai_compounds.json

# Performance settings
WORKER_PROCESSES=4
BATCH_SIZE=50
TOKENIZER_CACHE_SIZE=1000
```

**Validate configuration:**

```bash
./scripts/maintenance/validate-env-config.sh
```

### 5.2 Dictionary Management

**Check dictionary status:**

```bash
./scripts/maintenance/debug-dictionary.sh
```

**Update dictionary and reload:**

```bash
# Edit dictionary
nano data/dictionaries/thai_compounds.json

# Reload service
./scripts/deployment/rebuild-with-dictionary.sh
```

---

## 6. Performance Optimization

### 6.1 Tokenization Performance

**Benchmark tokenization speed:**

```bash
# Test with various text lengths
for text in "สวัสดี" "ฉันกินสาหร่ายวากาเมะ" "ฉันกินสาหร่ายวากาเมะที่ร้านซูชิญี่ปุ่นในกรุงเทพมหานคร"; do
  echo "Testing: $text"
  time curl -s -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
    -H "Content-Type: application/json" \
    -d "{\"text\": \"$text\"}" | jq '.processing_time_ms'
done
```

### 6.2 Resource Optimization

**Adjust worker processes:**

```bash
# Edit .env.production
WORKER_PROCESSES=8  # Increase for more CPU cores
MAX_WORKERS=8
BATCH_SIZE=100      # Increase for better throughput
```

**Monitor memory usage:**

```bash
docker exec $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1) \
  cat /proc/meminfo | grep -E "MemTotal|MemAvailable|MemFree"
```

---

## 7. Backup & Recovery

### 7.1 Configuration Backup

**Automatic backup (done by scripts):**

```bash
# Backups are created automatically in backups/env/
ls -la backups/env/
```

**Manual backup:**

```bash
cp .env.production backups/env/.env.production.backup.$(date +%Y%m%d_%H%M%S)
```

### 7.2 Dictionary Backup

**Backup custom dictionary:**

```bash
cp data/dictionaries/thai_compounds.json backups/thai_compounds.backup.$(date +%Y%m%d_%H%M%S).json
```

### 7.3 Recovery Procedures

**Restore from backup:**

```bash
# List available backups
ls -la backups/env/

# Restore configuration
cp backups/env/.env.production.backup.YYYYMMDD_HHMMSS .env.production

# Restart service
./deploy.sh rebuild
```

**Emergency recovery:**

```bash
# If service is completely broken, use the example config
cp .env.production.example .env.production

# Edit with correct values
nano .env.production

# Deploy
./deploy.sh production
```

---

## 8. Common Issues & Solutions

### 8.1 Service Won't Start

**Symptoms:**

- Container exits immediately
- Health checks fail
- API not accessible

**Diagnosis:**

```bash
# Check container logs
docker logs $(docker ps -a --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)

# Check configuration
./scripts/maintenance/validate-env-config.sh
```

**Solutions:**

```bash
# Fix 1: Rebuild with clean slate
docker system prune -f
./deploy.sh production

# Fix 2: Check environment variables
grep -E "MEILISEARCH|CUSTOM_DICTIONARY" .env.production

# Fix 3: Verify Meilisearch connectivity
curl -s http://10.0.2.105:7700/health
```

### 8.2 Compound Words Not Working

**Symptoms:**

- วากาเมะ splits into วา, กา, เมะ
- Custom dictionary not loading

**Diagnosis:**

```bash
./scripts/maintenance/debug-dictionary.sh
```

**Solutions:**

```bash
# Fix 1: Rebuild with dictionary fix
./scripts/deployment/rebuild-with-dictionary.sh

# Fix 2: Check dictionary file
cat data/dictionaries/thai_compounds.json | jq .

# Fix 3: Verify environment variable
docker exec $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1) \
  env | grep CUSTOM_DICTIONARY
```

### 8.3 Meilisearch Connection Issues

**Symptoms:**

- Meilisearch health check fails
- Document indexing fails

**Diagnosis:**

```bash
# Test direct connection
curl -s http://10.0.2.105:7700/health

# Check API key
curl -s -H "Authorization: Bearer FKjPKTmFnCl7EPg6YLula1DC6n5mHqId" \
  http://10.0.2.105:7700/indexes
```

**Solutions:**

```bash
# Fix 1: Update Meilisearch host
sed -i 's|MEILISEARCH_HOST=.*|MEILISEARCH_HOST=http://10.0.2.105:7700|' .env.production
./deploy.sh rebuild

# Fix 2: Check network connectivity
ping 10.0.2.105

# Fix 3: Verify API key
grep MEILISEARCH_API_KEY .env.production
```

### 8.4 Performance Issues

**Symptoms:**

- Slow tokenization (>100ms)
- High memory usage
- Timeouts

**Diagnosis:**

```bash
# Check performance metrics
curl -s "https://search.cads.arda.or.th/api/v1/health/summary" | jq '.key_metrics'

# Monitor resources
docker stats $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)
```

**Solutions:**

```bash
# Fix 1: Increase worker processes
sed -i 's|WORKER_PROCESSES=.*|WORKER_PROCESSES=8|' .env.production
./deploy.sh rebuild

# Fix 2: Optimize batch size
sed -i 's|BATCH_SIZE=.*|BATCH_SIZE=100|' .env.production
./deploy.sh rebuild

# Fix 3: Increase memory limit
sed -i 's|MEMORY_LIMIT=.*|MEMORY_LIMIT=2G|' .env.production
./deploy.sh rebuild
```

---

## 🆘 Emergency Contacts & Resources

### Quick Recovery Commands

```bash
# Emergency restart
docker restart $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)

# Emergency rebuild
./scripts/deployment/simple-rebuild.sh

# Emergency health check
curl -s "https://search.cads.arda.or.th/health"
```

### Log Locations

- **Container logs**: `docker logs <container_id>`
- **Application logs**: `/var/log/thai-tokenizer/` (inside container)
- **Backup files**: `backups/env/`

### Key Files

- **Main config**: `.env.production`
- **Dictionary**: `data/dictionaries/thai_compounds.json`
- **Docker config**: `deployment/docker/docker-compose.npm.yml`
- **Main deployment**: `deploy.sh`

---

*Last updated: $(date)*
*Service URL: <https://search.cads.arda.or.th>*
*Meilisearch: <http://10.0.2.105:7700>*
