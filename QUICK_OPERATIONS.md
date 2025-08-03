# Thai Tokenizer - Quick Operations Reference

## 🚀 Most Common Operations

### 1. Add New Compound Word

```bash
# 1. Edit dictionary
nano data/dictionaries/thai_compounds.json

# 2. Add your word to the appropriate category:
#    "thai_japanese_compounds": ["วากาเมะ", "YOUR_NEW_WORD"]
#    "thai_english_compounds": ["คอมพิวเตอร์", "YOUR_NEW_WORD"]

# 3. Rebuild service
./deploy.sh rebuild

# 4. Test the new word
curl -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "YOUR_TEST_SENTENCE_WITH_NEW_WORD"}'
```

### 2. Restart Service

```bash
# Quick restart
./deploy.sh rebuild

# Full rebuild (after code changes)
./scripts/deployment/simple-rebuild.sh

# With dictionary updates
./scripts/deployment/rebuild-with-dictionary.sh
```

### 3. Assess Existing Index Reindexing Need

```bash
# Check if you need to reindex existing documents
./scripts/maintenance/assess-reindexing-need.sh

# This will tell you:
# - Whether reindexing is needed (full/selective/none)
# - Current search quality assessment
# - Specific recommendations based on your index size and quality
```

### 4. Reindex Existing Data (CRITICAL!)

Your existing indexes need reindexing to add `tokenized_content` field:

```bash
# 1. Analyze what needs reindexing
./scripts/maintenance/analyze-reindex-need.sh

# 2. Preview changes (dry run)
./scripts/maintenance/reindex-all-data.sh --dry-run --all

# 3. Reindex all indexes
./scripts/maintenance/reindex-all-data.sh --all

# 4. Or reindex specific index
./scripts/maintenance/reindex-all-data.sh --index research
```

### 5. Test วากาเมะ Compound Search

```bash
# Test tokenization
./scripts/testing/test-wakame-tokenization.sh

# Expected result: ["ฉัน", "กิน", "สาหร่าย", "วากาเมะ"]

# Test in Meilisearch
curl -X POST "https://search.cads.arda.or.th/api/v1/index-document" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "wakame-test",
    "title": "ทดสอบวากาเมะ",
    "content": "ฉันกินสาหร่ายวากาเมะ"
  }'

# Search for it
curl -X POST "https://search.cads.arda.or.th/api/v1/search" \
  -H "Content-Type: application/json" \
  -d '{"query": "วากาเมะ"}'
```

### 6. Health Check

```bash
# Quick health
curl -s "https://search.cads.arda.or.th/health"

# Detailed health
curl -s "https://search.cads.arda.or.th/api/v1/health/detailed" | jq .

# Check specific components
curl -s "https://search.cads.arda.or.th/api/v1/health/check/configuration_validity"
curl -s "https://search.cads.arda.or.th/api/v1/health/check/meilisearch"
```

### 5. Debug Issues

```bash
# Debug dictionary loading
./scripts/maintenance/debug-dictionary.sh

# Validate configuration
./scripts/maintenance/validate-env-config.sh

# Check container logs
docker logs $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1) --tail 50
```

### 6. Performance Testing

```bash
# Test external API
./scripts/testing/test-external-api.sh

# Test from container
./scripts/testing/test-from-container.sh

# Benchmark tokenization
time curl -X POST "https://search.cads.arda.or.th/api/v1/tokenize/compound" \
  -H "Content-Type: application/json" \
  -d '{"text": "ฉันกินสาหร่ายวากาเมะที่ร้านซูชิ"}'
```

## 🆘 Emergency Commands

### Service Down

```bash
# Emergency restart
docker restart $(docker ps --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)

# Emergency rebuild
./scripts/deployment/simple-rebuild.sh

# Check what's wrong
docker logs $(docker ps -a --filter "name=thai-tokenizer" --format "{{.ID}}" | head -1)
```

### Configuration Issues

```bash
# Restore from backup
cp backups/env/.env.production.backup.* .env.production
./deploy.sh rebuild

# Use example config
cp .env.production.example .env.production
# Edit with correct values, then:
./deploy.sh production
```

## 📊 Key URLs

- **API**: <https://search.cads.arda.or.th>
- **Health**: <https://search.cads.arda.or.th/api/v1/health/detailed>
- **Docs**: <https://search.cads.arda.or.th/docs>
- **Meilisearch**: <http://10.0.2.105:7700>

## 📁 Key Files

- **Main config**: `.env.production`
- **Dictionary**: `data/dictionaries/thai_compounds.json`
- **Deploy script**: `deploy.sh`
- **Full guide**: `docs/OPERATIONAL_TROUBLESHOOTING.md`
