# 🚀 Production Deployment Guide: Thai Tokenizer with Compound Words + MeiliSearch

## 📋 **Quick Production Setup**

### **Option 1: Docker Deployment (Recommended for Production)**

```bash
# 1. Clone and navigate to your repository
git clone <your-repo-url>
cd meilisearch-thai

# 2. Start both Thai Tokenizer + MeiliSearch with Docker
docker compose -f deployment/docker/docker-compose.yml up -d

# 3. Verify services are running
docker compose -f deployment/docker/docker-compose.yml ps

# 4. Test the compound word tokenization
curl -X POST "http://localhost:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะมีประโยชน์ต่อสุขภาพ"}'

# Expected: ["วากาเมะ","มีประโยชน์","ต่อ","สุขภาพ"]
```

### **Option 2: Python + MeiliSearch Separate (Development/Testing)**

```bash
# 1. Start MeiliSearch
docker run -it --rm \
  -p 7700:7700 \
  -v $(pwd)/meili_data:/meili_data \
  getmeili/meilisearch:v1.15.2

# 2. In another terminal, start Thai Tokenizer with compounds
python3 start_api_with_compounds.py

# 3. Test integration
python3 tests/integration/test_api_integration.py
```

### **Option 3: Thai Tokenizer Only (Connect to Existing MeiliSearch)**

If you already have MeiliSearch running in your infrastructure:

```bash
# 1. Configure environment to point to your existing MeiliSearch
export MEILISEARCH_URL=http://your-meilisearch-server:7700
export MEILISEARCH_API_KEY=your-existing-master-key

# 2. Start only the Thai Tokenizer with compound support
python3 start_api_with_compounds.py

# 3. Test connection to your existing MeiliSearch
curl -X GET "http://your-meilisearch-server:7700/health" \
  -H "Authorization: Bearer your-existing-master-key"
```

## 🏗️ **Production Architecture**

```ascii
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Your App     │───▶│ Thai Tokenizer  │───▶│   MeiliSearch   │
│                │    │ (Port 8001)     │    │   (Port 7700)   │
│ - Search UI    │    │ - Compound Dict │    │ - Search Index  │
│ - Document Mgmt│    │ - 32+ Words     │    │ - Fast Queries  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔧 **Production Configuration**

### **1. Environment Variables**

Create `.env.production`:

```bash
# Thai Tokenizer Configuration
THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH=data/dictionaries/thai_compounds.json
THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS=true
THAI_TOKENIZER_TOKENIZER_ENGINE=newmm
THAI_TOKENIZER_DEBUG=false

# MeiliSearch Configuration (for new MeiliSearch)
MEILI_MASTER_KEY=your-secure-master-key-here
MEILI_ENV=production
MEILI_HTTP_ADDR=0.0.0.0:7700

# Existing MeiliSearch Configuration (if using existing)
EXISTING_MEILISEARCH_URL=http://your-meilisearch-server:7700
EXISTING_MEILISEARCH_API_KEY=your-existing-master-key

# API Configuration
API_HOST=0.0.0.0
API_PORT=8001
API_WORKERS=4
```

### **2. Docker Compose Configurations**

#### **Option A: Full Stack (New MeiliSearch)**

```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  meilisearch:
    image: getmeili/meilisearch:v1.15.2
    ports:
      - "7700:7700"
    environment:
      - MEILI_MASTER_KEY=${MEILI_MASTER_KEY}
      - MEILI_ENV=production
    volumes:
      - meili_data:/meili_data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:7700/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  thai-tokenizer:
    build: .
    ports:
      - "8001:8000"
    environment:
      - THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH=data/dictionaries/thai_compounds.json
      - THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS=true
      - MEILISEARCH_URL=http://meilisearch:7700
      - MEILISEARCH_API_KEY=${MEILI_MASTER_KEY}
    volumes:
      - ./data:/app/data
    depends_on:
      - meilisearch
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

volumes:
  meili_data:
```

#### **Option B: Thai Tokenizer Only (Existing MeiliSearch)**

```yaml
# docker-compose.tokenizer-only.yml
version: '3.8'
services:
  thai-tokenizer:
    build: .
    ports:
      - "8001:8000"
    environment:
      - THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH=data/dictionaries/thai_compounds.json
      - THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS=true
      - MEILISEARCH_URL=${EXISTING_MEILISEARCH_URL}
      - MEILISEARCH_API_KEY=${EXISTING_MEILISEARCH_API_KEY}
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## 📊 **Integration Workflow**

### **1. Document Indexing with Compound Words**

```python
import requests

# 1. Tokenize Thai text with compound words
def tokenize_thai_text(text):
    response = requests.post(
        "http://localhost:8001/api/v1/tokenize",
        json={"text": text}
    )
    return response.json()["tokens"]

# 2. Index documents in MeiliSearch
def index_document(document):
    # Tokenize Thai content
    thai_tokens = tokenize_thai_text(document["content"])
    
    # Add tokenized content to document
    document["thai_tokens"] = " ".join(thai_tokens)
    
    # Index in MeiliSearch
    response = requests.post(
        "http://localhost:7700/indexes/documents/documents",
        headers={"Authorization": f"Bearer {MEILI_MASTER_KEY}"},
        json=[document]
    )
    return response.json()

# Example usage
document = {
    "id": 1,
    "title": "สาหร่ายวากาเมะ",
    "content": "สาหร่ายวากาเมะเป็นอาหารทะเลที่มีประโยชน์ต่อสุขภาพ"
}

result = index_document(document)
```

### **2. Search with Compound Word Support**

#### **For New MeiliSearch Setup**

```python
def search_documents(query, meilisearch_url="http://localhost:7700", api_key=None):
    # 1. Tokenize search query
    tokenized_query = tokenize_thai_text(query)
    search_terms = " ".join(tokenized_query)
    
    # 2. Search in MeiliSearch
    headers = {}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    response = requests.post(
        f"{meilisearch_url}/indexes/documents/search",
        headers=headers,
        json={
            "q": search_terms,
            "attributesToHighlight": ["content", "thai_tokens"],
            "limit": 20
        }
    )
    return response.json()

# Example: Search for wakame
results = search_documents("วากาเมะ")
# Will find documents containing "สาหร่ายวากาเมะ" correctly!
```

#### **For Existing MeiliSearch Setup**

```python
def search_existing_meilisearch(query, meilisearch_url, api_key, index_name):
    # 1. Tokenize search query with Thai Tokenizer
    tokenized_query = tokenize_thai_text(query)
    search_terms = " ".join(tokenized_query)
    
    # 2. Search in your existing MeiliSearch
    response = requests.post(
        f"{meilisearch_url}/indexes/{index_name}/search",
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "q": search_terms,
            "attributesToHighlight": ["content", "thai_tokens"],
            "limit": 20
        }
    )
    return response.json()

# Example: Search in existing MeiliSearch
results = search_existing_meilisearch(
    query="วากาเมะ",
    meilisearch_url="http://your-meilisearch-server:7700",
    api_key="your-existing-master-key",
    index_name="your_existing_index"
)
```

## 🚀 **Production Deployment Steps**

### **Step 1: Prepare Production Environment**

```bash
# 1. Clone repository on production server
git clone <your-repo-url>
cd meilisearch-thai

# 2. Set up environment variables
cp .env.example .env.production
# Edit .env.production with your production values

# 3. Ensure compound dictionary exists
ls -la data/dictionaries/thai_compounds.json
# Should show 32+ compound words including วากาเมะ
```

### **Step 2: Deploy with Docker**

#### **Option A: Full Stack Deployment (New MeiliSearch)**

```bash
# 1. Build and start both services
docker compose -f deployment/docker/docker-compose.yml up -d

# 2. Verify services are healthy
docker compose -f deployment/docker/docker-compose.yml ps
docker compose -f deployment/docker/docker-compose.yml logs -f

# 3. Test compound word tokenization
curl -X POST "http://your-server:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะมีประโยชน์ต่อสุขภาพ"}'
```

#### **Option B: Thai Tokenizer Only (Existing MeiliSearch)**

```bash
# 1. Set environment variables for your existing MeiliSearch
export EXISTING_MEILISEARCH_URL=http://your-meilisearch-server:7700
export EXISTING_MEILISEARCH_API_KEY=your-existing-master-key

# 2. Build and start only the Thai Tokenizer
docker compose -f deployment/docker/docker-compose.tokenizer-only.yml up -d

# 3. Verify tokenizer is healthy and connected to your MeiliSearch
docker compose -f deployment/docker/docker-compose.tokenizer-only.yml ps
docker compose -f deployment/docker/docker-compose.tokenizer-only.yml logs -f

# 4. Test connection to your existing MeiliSearch
curl -X GET "http://your-meilisearch-server:7700/health" \
  -H "Authorization: Bearer your-existing-master-key"

# 5. Test compound word tokenization
curl -X POST "http://your-server:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะมีประโยชน์ต่อสุขภาพ"}'
```

### **Step 3: Configure MeiliSearch Index**

#### **For New MeiliSearch (Option A)**

```bash
# 1. Create index with proper settings
curl -X POST "http://your-server:7700/indexes" \
  -H "Authorization: Bearer YOUR_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "documents",
    "primaryKey": "id"
  }'

# 2. Configure searchable attributes
curl -X PATCH "http://your-server:7700/indexes/documents/settings" \
  -H "Authorization: Bearer YOUR_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "searchableAttributes": ["title", "content", "thai_tokens"],
    "filterableAttributes": ["category", "language"],
    "sortableAttributes": ["created_at", "updated_at"]
  }'
```

#### **For Existing MeiliSearch (Option B)**

```bash
# 1. Check existing indexes
curl -X GET "http://your-meilisearch-server:7700/indexes" \
  -H "Authorization: Bearer YOUR_EXISTING_MASTER_KEY"

# 2. Create new index for Thai content (if needed)
curl -X POST "http://your-meilisearch-server:7700/indexes" \
  -H "Authorization: Bearer YOUR_EXISTING_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "uid": "thai_documents",
    "primaryKey": "id"
  }'

# 3. Configure Thai-specific searchable attributes
curl -X PATCH "http://your-meilisearch-server:7700/indexes/thai_documents/settings" \
  -H "Authorization: Bearer YOUR_EXISTING_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "searchableAttributes": ["title", "content", "thai_tokens"],
    "filterableAttributes": ["category", "language"],
    "sortableAttributes": ["created_at", "updated_at"]
  }'

# 4. Or update existing index to include Thai tokens
curl -X PATCH "http://your-meilisearch-server:7700/indexes/YOUR_EXISTING_INDEX/settings" \
  -H "Authorization: Bearer YOUR_EXISTING_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "searchableAttributes": ["title", "content", "thai_tokens", "your_existing_fields"],
    "filterableAttributes": ["category", "language", "your_existing_filters"],
    "sortableAttributes": ["created_at", "updated_at", "your_existing_sorts"]
  }'
```

## 📈 **Production Monitoring**

### **Health Checks**

#### **For Full Stack Deployment**

```bash
# Thai Tokenizer health
curl http://your-server:8001/health

# MeiliSearch health  
curl http://your-server:7700/health

# Compound dictionary status
curl http://your-server:8001/api/v1/tokenize/stats
```

#### **For Thai Tokenizer Only (Existing MeiliSearch)**

```bash
# Thai Tokenizer health
curl http://your-server:8001/health

# Your existing MeiliSearch health
curl http://your-meilisearch-server:7700/health \
  -H "Authorization: Bearer your-existing-master-key"

# Compound dictionary status
curl http://your-server:8001/api/v1/tokenize/stats

# Test connection between Thai Tokenizer and your MeiliSearch
curl http://your-server:8001/api/v1/tokenize/stats | grep -i meilisearch
```

### **Performance Monitoring**

```bash
# Monitor tokenization performance
curl http://your-server:8001/api/v1/tokenize/stats

# Expected metrics:
# - custom_dict_size: 32
# - has_custom_tokenizer: true
# - processing_time: <50ms
```

## 🎯 **Production Checklist**

### ✅ **Pre-Deployment**

- [ ] Compound dictionary file exists (`data/dictionaries/thai_compounds.json`)
- [ ] Environment variables configured
- [ ] Docker images built and tested
- [ ] SSL certificates configured (if needed)
- [ ] Firewall rules set up

### ✅ **Post-Deployment**

- [ ] Services are running and healthy
- [ ] Compound word tokenization working (`วากาเมะ` → single token)
- [ ] MeiliSearch index created and configured
- [ ] Search functionality tested with Thai compound words
- [ ] Performance metrics within acceptable ranges
- [ ] Monitoring and alerting configured

## 🔒 **Security Considerations**

```bash
# 1. Set strong MeiliSearch master key
MEILI_MASTER_KEY=$(openssl rand -base64 32)

# 2. Configure firewall (example for Ubuntu)
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw allow 7700  # MeiliSearch (or restrict to internal network)
sudo ufw allow 8001  # Thai Tokenizer (or restrict to internal network)
sudo ufw enable

# 3. Use reverse proxy (nginx example)
# Proxy external requests through nginx with SSL
```

## 🎉 **Success Verification**

After deployment, verify everything works:

```bash
# 1. Test compound word tokenization
curl -X POST "http://your-server:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "ร้านอาหารญี่ปุ่นเสิร์ฟวากาเมะและซาชิมิ"}'

# Expected: ["ร้านอาหาร","ญี่ปุ่น","เสิร์ฟ","วากาเมะ","และ","ซาชิมิ"]

# 2. Test MeiliSearch integration
# Index a document and search for compound words
# Verify that searching for "วากาเมะ" finds documents with "สาหร่ายวากาเมะ"
```

## 🔧 **Troubleshooting**

### **Common Issues**

1. **Compound dictionary not loading**

   ```bash
   # Check if dictionary file exists
   ls -la data/dictionaries/thai_compounds.json
   
   # Check environment variables
   echo $THAI_TOKENIZER_CUSTOM_DICTIONARY_PATH
   echo $THAI_TOKENIZER_TOKENIZER_HANDLE_COMPOUNDS
   ```

2. **Services not starting**

   ```bash
   # Check Docker logs
   docker compose -f deployment/docker/docker-compose.yml logs thai-tokenizer
   docker compose -f deployment/docker/docker-compose.yml logs meilisearch
   ```

3. **Network connectivity issues**

   ```bash
   # Test internal network connectivity
   docker exec -it docker-thai-tokenizer-1 curl http://meilisearch:7700/health
   ```

### **Performance Optimization**

```bash
# 1. Monitor resource usage
docker stats

# 2. Scale services if needed
docker compose -f deployment/docker/docker-compose.yml up -d --scale thai-tokenizer=3

# 3. Configure load balancer (nginx example)
upstream thai_tokenizer {
    server localhost:8001;
    server localhost:8002;
    server localhost:8003;
}
```

## 🔄 **Existing MeiliSearch Integration Guide**

If you already have MeiliSearch running in your infrastructure, you can easily add Thai compound word support:

### **Step 1: Deploy Thai Tokenizer Only**

```bash
# 1. Create environment file for existing MeiliSearch
cp deployment/configs/.env.existing.example .env.existing
# Edit .env.existing with your MeiliSearch details

# 2. Deploy only Thai Tokenizer
docker compose -f deployment/docker/docker-compose.tokenizer-only.yml --env-file .env.existing up -d
```

### **Step 2: Update Your Application Code**

```python
# Before: Direct MeiliSearch indexing
def old_index_document(document):
    response = requests.post(
        f"{MEILISEARCH_URL}/indexes/documents/documents",
        headers={"Authorization": f"Bearer {MEILISEARCH_API_KEY}"},
        json=[document]
    )
    return response.json()

# After: With Thai compound word tokenization
def new_index_document(document):
    # 1. Tokenize Thai content
    if 'content' in document:
        thai_tokens = tokenize_thai_text(document['content'])
        document['thai_tokens'] = ' '.join(thai_tokens)
    
    # 2. Index in your existing MeiliSearch
    response = requests.post(
        f"{MEILISEARCH_URL}/indexes/documents/documents",
        headers={"Authorization": f"Bearer {MEILISEARCH_API_KEY}"},
        json=[document]
    )
    return response.json()
```

### **Step 3: Update Search Functionality**

```python
# Enhanced search with compound word support
def enhanced_search(query):
    # 1. Tokenize query with Thai Tokenizer
    tokenized_query = tokenize_thai_text(query)
    search_terms = ' '.join(tokenized_query)
    
    # 2. Search in your existing MeiliSearch
    response = requests.post(
        f"{MEILISEARCH_URL}/indexes/documents/search",
        headers={"Authorization": f"Bearer {MEILISEARCH_API_KEY}"},
        json={
            "q": search_terms,
            "attributesToHighlight": ["content", "thai_tokens"],
            "limit": 20
        }
    )
    return response.json()
```

## 📚 **Additional Resources**

### **For New MeiliSearch Setup**

- **API Documentation**: `http://your-server:8001/docs`
- **MeiliSearch Dashboard**: `http://your-server:7700`
- **Health Monitoring**: `http://your-server:8001/health`
- **Tokenizer Stats**: `http://your-server:8001/api/v1/tokenize/stats`

### **For Existing MeiliSearch Setup**

- **Thai Tokenizer API**: `http://your-server:8001/docs`
- **Your MeiliSearch Dashboard**: `http://your-meilisearch-server:7700`
- **Thai Tokenizer Health**: `http://your-server:8001/health`
- **Integration Stats**: `http://your-server:8001/api/v1/tokenize/stats`

## 🎊 **Conclusion**

Your production setup is now ready with **Thai compound word support** that dramatically improves search accuracy for Thai content!

**Key Benefits:**

- ✅ **Accurate Tokenization**: "วากาเมะ" stays as single token
- ✅ **Better Search Results**: Find "สาหร่ายวากาเมะ" when searching "วากาเมะ"
- ✅ **Production Ready**: Docker deployment with health checks
- ✅ **Scalable**: Can handle high-volume requests
- ✅ **Monitored**: Built-in health checks and performance metrics

The wakame tokenization issue is now **completely resolved** in production! 🚀
