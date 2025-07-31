# 🚀 Quick Start Guide

## For New Users (Full Stack)

```bash
# Start both Thai Tokenizer + MeiliSearch
docker compose -f deployment/docker/docker-compose.yml up -d

# Test compound word tokenization
curl -X POST "http://localhost:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะมีประโยชน์ต่อสุขภาพ"}'
```

## For Existing MeiliSearch Users

If you already have MeiliSearch running on port 7700:

```bash
# Automated setup (recommended)
./setup_existing_meilisearch.sh

# Or manual setup
cp deployment/configs/.env.existing.example .env.existing
# Edit .env.existing with your MeiliSearch details
docker compose -f deployment/docker/docker-compose.tokenizer-only.yml --env-file .env.existing up -d
```

**📖 Detailed Guide**: [deployment/scripts/README_EXISTING_MEILISEARCH.md](deployment/scripts/README_EXISTING_MEILISEARCH.md)

## For Development

```bash
# Start API with compound support
python3 start_api_with_compounds.py

# Run integration tests
python3 tests/integration/test_api_integration.py
```

## 📚 Documentation

- **Full Production Guide**: [docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md](docs/deployment/PRODUCTION_DEPLOYMENT_GUIDE.md)
- **Compound Dictionary Guide**: [docs/deployment/COMPOUND_DICTIONARY_DEPLOYMENT.md](docs/deployment/COMPOUND_DICTIONARY_DEPLOYMENT.md)
- **API Documentation**: `http://localhost:8001/docs` (when running)

## 🎯 Expected Results

Input: `"วากาเมะมีประโยชน์ต่อสุขภาพ"`  
Output: `["วากาเมะ","มีประโยชน์","ต่อ","สุขภาพ"]` ✅

The compound word "วากาเมะ" stays as a single token!