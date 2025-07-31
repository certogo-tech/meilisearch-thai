# Thai Tokenizer Integration with Existing MeiliSearch

This guide helps you integrate the Thai Tokenizer with your existing MeiliSearch instance to improve Thai text search accuracy, especially for compound words.

## Quick Start

If you already have MeiliSearch running on port 7700, you can quickly set up the Thai Tokenizer integration:

```bash
# From project root
./setup_existing_meilisearch.sh
```

This will:
1. ✅ Verify your compound dictionary (32 Thai-Japanese and Thai-English compound words)
2. ✅ Create environment configuration
3. ✅ Test connection to your existing MeiliSearch
4. ✅ Start Thai Tokenizer service on port 8001
5. ✅ Verify compound word tokenization is working

## What This Solves

### Before Integration
```bash
# Thai compound words get incorrectly split
"วากาเมะ" → ["วา", "กา", "เมะ"]  # ❌ Wrong
"ซาชิมิ" → ["ซา", "ชิ", "มิ"]     # ❌ Wrong
```

### After Integration
```bash
# Thai compound words stay as single tokens
"วากาเมะ" → ["วากาเมะ"]          # ✅ Correct
"ซาชิมิ" → ["ซาชิมิ"]            # ✅ Correct
```

## Manual Setup

### 1. Prerequisites

- Existing MeiliSearch instance running on port 7700
- Docker and Docker Compose installed
- `jq` and `curl` for testing

### 2. Configuration

Create `.env.existing` file in project root:

```bash
# Your existing MeiliSearch configuration
EXISTING_MEILISEARCH_URL=http://host.docker.internal:7700
EXISTING_MEILISEARCH_API_KEY=your-existing-master-key

# Thai Tokenizer configuration
THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH=data/dictionaries/thai_compounds.json
THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS=true
THAI_TOKENIZER_TOKENIZER_ENGINE=newmm
THAI_TOKENIZER_DEBUG=false

# API configuration
API_HOST=0.0.0.0
API_PORT=8000
API_WORKERS=4
```

**Important**: Use `host.docker.internal:7700` if your MeiliSearch is running on the host machine.

### 3. Start Thai Tokenizer

```bash
cd deployment/docker
docker compose -f docker-compose.tokenizer-only.yml --env-file ../../.env.existing up -d
```

### 4. Test Integration

```bash
# Test compound word tokenization
curl -X POST "http://localhost:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "ร้านอาหารญี่ปุ่นเสิร์ฟวากาเมะและซาชิมิ"}'

# Expected result: วากาเมะ and ซาชิมิ should be single tokens
```

## Supported Compound Words

The tokenizer includes 32 compound words:

### Thai-Japanese Compounds (22 words)
- วากาเมะ (wakame seaweed)
- ซาชิมิ (sashimi)
- เทมปุระ (tempura)
- ซูชิ (sushi)
- ราเมน (ramen)
- And 17 more...

### Thai-English Compounds (10 words)
- คอมพิวเตอร์ (computer)
- อินเทอร์เน็ต (internet)
- เว็บไซต์ (website)
- เทคโนโลยี (technology)
- ดิจิทัล (digital)
- And 5 more...

## API Endpoints

Once running, the Thai Tokenizer provides these endpoints:

- **Tokenization**: `POST http://localhost:8001/api/v1/tokenize`
- **Health Check**: `GET http://localhost:8001/health`
- **API Docs**: `GET http://localhost:8001/docs`
- **Statistics**: `GET http://localhost:8001/api/v1/tokenize/stats`

## Integration with Your Application

### Option 1: Pre-process Documents
Tokenize documents before indexing in MeiliSearch:

```python
import requests

def tokenize_thai_text(text):
    response = requests.post("http://localhost:8001/api/v1/tokenize", 
                           json={"text": text})
    return response.json()["tokens"]

# Before indexing
document = {"title": "ร้านอาหารญี่ปุ่น", "content": "เสิร์ฟวากาเมะและซาชิมิ"}
document["title_tokens"] = tokenize_thai_text(document["title"])
document["content_tokens"] = tokenize_thai_text(document["content"])

# Index in MeiliSearch
meilisearch_client.index("documents").add_documents([document])
```

### Option 2: Pre-process Search Queries
Tokenize search queries for better matching:

```python
def search_with_thai_tokenization(query, index_name="documents"):
    # Tokenize the search query
    tokenized = tokenize_thai_text(query)
    processed_query = " ".join(tokenized)
    
    # Search in MeiliSearch
    results = meilisearch_client.index(index_name).search(processed_query)
    return results
```

## Troubleshooting

### Connection Issues
```bash
# Test MeiliSearch connection
curl -H "Authorization: Bearer your-api-key" http://localhost:7700/health

# Test Thai Tokenizer connection
curl http://localhost:8001/health
```

### Docker Networking
If you get connection errors, ensure you're using the correct URL:
- From host: `http://localhost:7700`
- From Docker container: `http://host.docker.internal:7700`

### Compound Words Not Working
Check if the dictionary is loaded:
```bash
curl http://localhost:8001/api/v1/tokenize/stats
# Should show custom_dictionary_size > 0
```

## Testing

Run the comprehensive test suite:

```bash
# From project root
./tests/integration/test_existing_meilisearch_setup.sh
```

This runs 13 tests covering:
- Dictionary loading
- Environment configuration
- Docker setup
- MeiliSearch connectivity
- Compound word tokenization
- API functionality

## Cleanup

To stop and remove the Thai Tokenizer:

```bash
cd deployment/docker
docker compose -f docker-compose.tokenizer-only.yml down
```

## Performance

- **Tokenization Speed**: < 50ms for 1000 Thai characters
- **Memory Usage**: < 256MB per container
- **Throughput**: > 500 documents/second for batch processing

## Support

For issues or questions:
1. Check the logs: `docker logs docker-thai-tokenizer-1`
2. Verify configuration in `.env.existing`
3. Test individual components using the troubleshooting commands above