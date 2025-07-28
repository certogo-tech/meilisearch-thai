# Integrating Thai Tokenization with Existing MeiliSearch

If you already have MeiliSearch running and want to add Thai tokenization capabilities, this guide will help you integrate our Thai tokenizer without disrupting your existing setup.

## 🎯 Integration Overview

### What This Guide Covers
- ✅ Adding Thai tokenization to existing MeiliSearch
- ✅ Migrating existing Thai content to use tokenization
- ✅ Preserving existing non-Thai indexes
- ✅ Gradual rollout strategies
- ✅ Performance optimization
- ✅ Backup and rollback procedures

### Integration Approaches
1. **Side-by-side**: Run Thai tokenizer alongside existing MeiliSearch
2. **Preprocessing**: Use tokenizer to preprocess documents before indexing
3. **Hybrid**: Tokenize only Thai content, leave other content unchanged
4. **Full migration**: Gradually migrate all content to use tokenization

## 🏗️ Architecture Options

### Option 1: Side-by-Side Deployment (Recommended)

```
Your Application
       ↓
   Load Balancer
    ↙        ↘
Existing      Thai Tokenizer
MeiliSearch   + MeiliSearch
(Port 7700)   (Port 8001 + 7701)
```

**Benefits:**
- Zero downtime migration
- Easy rollback
- Test thoroughly before switching
- Preserve existing functionality

### Option 2: Preprocessing Pipeline

```
Your Application
       ↓
Thai Tokenizer API (Port 8001)
       ↓
Document Processing
       ↓
Existing MeiliSearch (Port 7700)
```

**Benefits:**
- Use existing MeiliSearch instance
- Minimal infrastructure changes
- Gradual content migration

### Option 3: Hybrid Integration

```
Your Application
       ↓
Smart Router
    ↙        ↘
Thai Content    Non-Thai Content
    ↓               ↓
Thai Tokenizer   Existing MeiliSearch
+ MeiliSearch    (Port 7700)
(Port 8001)
```

**Benefits:**
- Language-specific optimization
- Preserve existing performance
- Targeted improvements

## 🚀 Step-by-Step Integration

### Step 1: Assessment and Planning

#### Analyze Your Current Setup
```bash
# Check your current MeiliSearch version
curl http://your-meilisearch:7700/version

# List existing indexes
curl http://your-meilisearch:7700/indexes \
  -H "Authorization: Bearer YOUR_API_KEY"

# Check index settings
curl http://your-meilisearch:7700/indexes/YOUR_INDEX/settings \
  -H "Authorization: Bearer YOUR_API_KEY"
```

#### Identify Thai Content
```bash
# Sample script to identify Thai content in your data
python3 << 'EOF'
import re

def contains_thai(text):
    thai_pattern = re.compile(r'[\u0E00-\u0E7F]')
    return bool(thai_pattern.search(text))

# Test with your data
sample_texts = [
    "Your existing content",
    "ข้อความภาษาไทย",
    "Mixed content with Thai ภาษาไทย"
]

for text in sample_texts:
    print(f"'{text}' contains Thai: {contains_thai(text)}")
EOF
```

### Step 2: Deploy Thai Tokenizer (Side-by-Side)

#### Option A: Docker Compose Integration
```yaml
# Add to your existing docker-compose.yml
version: '3.8'
services:
  # Your existing services...
  
  thai-tokenizer:
    image: thai-tokenizer:latest
    ports:
      - "8001:8000"
    environment:
      - MEILISEARCH_HOST=http://thai-meilisearch:7700
      - MEILISEARCH_API_KEY=${THAI_MEILI_API_KEY}
    depends_on:
      - thai-meilisearch
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  thai-meilisearch:
    image: getmeili/meilisearch:v1.15.2
    ports:
      - "7701:7700"  # Different port to avoid conflict
    environment:
      - MEILI_MASTER_KEY=${THAI_MEILI_API_KEY}
      - MEILI_ENV=production
    volumes:
      - thai_meili_data:/meili_data

volumes:
  thai_meili_data:
```

#### Option B: Standalone Deployment
```bash
# Clone the Thai tokenizer
git clone https://github.com/your-repo/thai-tokenizer-meilisearch.git
cd thai-tokenizer-meilisearch

# Configure for your environment
cp config/production/.env.template config/production/.env.prod
# Edit config/production/.env.prod with your settings

# Start Thai tokenizer services
docker compose -f deployment/docker/docker-compose.yml up -d
```

### Step 3: Create Integration Layer

#### Smart Router Implementation
```python
# smart_router.py - Route requests based on content language
import re
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Configuration
EXISTING_MEILISEARCH = "http://localhost:7700"
THAI_TOKENIZER = "http://localhost:8001"
EXISTING_API_KEY = "your-existing-api-key"
THAI_API_KEY = "your-thai-api-key"

def contains_thai(text):
    """Check if text contains Thai characters"""
    thai_pattern = re.compile(r'[\u0E00-\u0E7F]')
    return bool(thai_pattern.search(text))

@app.route('/search', methods=['POST'])
def smart_search():
    data = request.json
    query = data.get('q', '')
    
    if contains_thai(query):
        # Route to Thai tokenizer
        response = requests.post(
            f"{THAI_TOKENIZER}/api/v1/search",
            json=data,
            headers={"Authorization": f"Bearer {THAI_API_KEY}"}
        )
    else:
        # Route to existing MeiliSearch
        response = requests.post(
            f"{EXISTING_MEILISEARCH}/indexes/your-index/search",
            json=data,
            headers={"Authorization": f"Bearer {EXISTING_API_KEY}"}
        )
    
    return jsonify(response.json())

@app.route('/documents', methods=['POST'])
def smart_index():
    documents = request.json
    
    # Separate Thai and non-Thai documents
    thai_docs = []
    regular_docs = []
    
    for doc in documents:
        content = doc.get('content', '') + ' ' + doc.get('title', '')
        if contains_thai(content):
            thai_docs.append(doc)
        else:
            regular_docs.append(doc)
    
    results = []
    
    # Index Thai documents with tokenization
    if thai_docs:
        thai_response = requests.post(
            f"{THAI_TOKENIZER}/api/v1/documents/process",
            json={"documents": thai_docs, "options": {"auto_index": True}},
            headers={"Authorization": f"Bearer {THAI_API_KEY}"}
        )
        results.append(thai_response.json())
    
    # Index regular documents normally
    if regular_docs:
        regular_response = requests.post(
            f"{EXISTING_MEILISEARCH}/indexes/your-index/documents",
            json=regular_docs,
            headers={"Authorization": f"Bearer {EXISTING_API_KEY}"}
        )
        results.append(regular_response.json())
    
    return jsonify({"results": results})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

### Step 4: Data Migration Strategy

#### Gradual Migration Approach
```python
# migrate_thai_content.py
import requests
import json
import time
from typing import List, Dict

class ThaiContentMigrator:
    def __init__(self, existing_meili_url, thai_tokenizer_url, api_keys):
        self.existing_meili = existing_meili_url
        self.thai_tokenizer = thai_tokenizer_url
        self.existing_key = api_keys['existing']
        self.thai_key = api_keys['thai']
    
    def identify_thai_documents(self, index_name: str) -> List[Dict]:
        """Identify documents containing Thai text"""
        # Get all documents from existing index
        response = requests.get(
            f"{self.existing_meili}/indexes/{index_name}/documents",
            headers={"Authorization": f"Bearer {self.existing_key}"},
            params={"limit": 1000}
        )
        
        documents = response.json().get('results', [])
        thai_docs = []
        
        for doc in documents:
            content = str(doc.get('content', '')) + ' ' + str(doc.get('title', ''))
            if self.contains_thai(content):
                thai_docs.append(doc)
        
        return thai_docs
    
    def contains_thai(self, text: str) -> bool:
        """Check if text contains Thai characters"""
        import re
        thai_pattern = re.compile(r'[\u0E00-\u0E7F]')
        return bool(thai_pattern.search(text))
    
    def migrate_documents(self, documents: List[Dict], batch_size: int = 50):
        """Migrate documents to Thai tokenizer with batching"""
        total = len(documents)
        migrated = 0
        
        for i in range(0, total, batch_size):
            batch = documents[i:i + batch_size]
            
            try:
                # Process with Thai tokenizer
                response = requests.post(
                    f"{self.thai_tokenizer}/api/v1/documents/process",
                    json={
                        "documents": batch,
                        "options": {
                            "auto_index": True,
                            "preserve_original": True
                        }
                    },
                    headers={"Authorization": f"Bearer {self.thai_key}"}
                )
                
                if response.status_code == 200:
                    migrated += len(batch)
                    print(f"Migrated {migrated}/{total} documents")
                else:
                    print(f"Error migrating batch: {response.text}")
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                print(f"Error processing batch: {e}")
        
        return migrated

# Usage example
if __name__ == "__main__":
    migrator = ThaiContentMigrator(
        existing_meili_url="http://localhost:7700",
        thai_tokenizer_url="http://localhost:8001",
        api_keys={
            "existing": "your-existing-key",
            "thai": "your-thai-key"
        }
    )
    
    # Identify Thai documents
    thai_docs = migrator.identify_thai_documents("your-index")
    print(f"Found {len(thai_docs)} Thai documents")
    
    # Migrate in batches
    migrated_count = migrator.migrate_documents(thai_docs)
    print(f"Successfully migrated {migrated_count} documents")
```

### Step 5: Update Your Application

#### Minimal Changes Approach
```python
# Update your existing search function
def search_documents(query, filters=None):
    # Detect if query contains Thai
    if contains_thai(query):
        # Use Thai tokenizer endpoint
        response = requests.post(
            "http://localhost:8001/api/v1/search",
            json={
                "query": query,
                "filters": filters,
                "options": {"expand_compounds": True}
            }
        )
    else:
        # Use existing MeiliSearch
        response = requests.post(
            f"{EXISTING_MEILISEARCH}/indexes/your-index/search",
            json={"q": query, "filter": filters}
        )
    
    return response.json()
```

#### Full Integration Approach
```python
# search_service.py - Unified search service
class UnifiedSearchService:
    def __init__(self):
        self.thai_tokenizer = "http://localhost:8001"
        self.existing_meili = "http://localhost:7700"
        self.router_endpoint = "http://localhost:8080"  # Smart router
    
    def search(self, query, index=None, filters=None, options=None):
        """Unified search interface"""
        search_request = {
            "q": query,
            "index": index,
            "filters": filters,
            "options": options or {}
        }
        
        # Use smart router for automatic routing
        response = requests.post(
            f"{self.router_endpoint}/search",
            json=search_request
        )
        
        return response.json()
    
    def index_document(self, document, index=None):
        """Unified indexing interface"""
        index_request = {
            "documents": [document] if isinstance(document, dict) else document,
            "index": index
        }
        
        response = requests.post(
            f"{self.router_endpoint}/documents",
            json=index_request
        )
        
        return response.json()
```

## 🔄 Migration Strategies

### Strategy 1: Blue-Green Deployment

```bash
# 1. Set up Thai tokenizer (Green)
docker compose -f deployment/docker/docker-compose.yml up -d

# 2. Migrate data to green environment
python3 migrate_thai_content.py

# 3. Test green environment thoroughly
python3 tests/integration/test_comprehensive_system.py

# 4. Switch traffic gradually
# Update load balancer to route 10% traffic to green
# Monitor performance and accuracy
# Gradually increase to 100%

# 5. Decommission blue environment
```

### Strategy 2: Canary Release

```python
# canary_router.py - Gradual traffic shifting
import random

def route_search_request(query):
    # Start with 5% of Thai queries to new tokenizer
    if contains_thai(query) and random.random() < 0.05:
        return route_to_thai_tokenizer(query)
    else:
        return route_to_existing_meili(query)

# Gradually increase percentage:
# Week 1: 5%
# Week 2: 20%
# Week 3: 50%
# Week 4: 100%
```

### Strategy 3: Feature Flag Approach

```python
# feature_flags.py
class FeatureFlags:
    def __init__(self):
        self.flags = {
            "thai_tokenization_enabled": False,
            "thai_tokenization_percentage": 0,
            "thai_tokenization_users": []  # Specific users for testing
        }
    
    def should_use_thai_tokenizer(self, user_id=None, query=None):
        if not self.flags["thai_tokenization_enabled"]:
            return False
        
        if user_id in self.flags["thai_tokenization_users"]:
            return True
        
        if contains_thai(query):
            return random.random() < (self.flags["thai_tokenization_percentage"] / 100)
        
        return False
```

## 📊 Monitoring and Validation

### Performance Comparison
```python
# performance_monitor.py
import time
import requests

def compare_search_performance(query, iterations=100):
    """Compare search performance between old and new systems"""
    
    # Test existing MeiliSearch
    existing_times = []
    for _ in range(iterations):
        start = time.time()
        response = requests.post(f"{EXISTING_MEILI}/indexes/your-index/search", 
                               json={"q": query})
        existing_times.append(time.time() - start)
    
    # Test Thai tokenizer
    thai_times = []
    for _ in range(iterations):
        start = time.time()
        response = requests.post(f"{THAI_TOKENIZER}/api/v1/search", 
                               json={"query": query})
        thai_times.append(time.time() - start)
    
    return {
        "existing_avg": sum(existing_times) / len(existing_times),
        "thai_avg": sum(thai_times) / len(thai_times),
        "improvement": (sum(existing_times) - sum(thai_times)) / sum(existing_times) * 100
    }

# Test with Thai queries
thai_queries = ["ปัญญาประดิษฐ์", "การเรียนรู้", "เทคโนโลยี"]
for query in thai_queries:
    results = compare_search_performance(query)
    print(f"Query: {query}")
    print(f"Performance improvement: {results['improvement']:.2f}%")
```

### Search Quality Validation
```python
# quality_validator.py
def validate_search_quality(test_queries):
    """Compare search result quality"""
    
    results = []
    for query_data in test_queries:
        query = query_data["query"]
        expected_docs = query_data["expected_document_ids"]
        
        # Search with existing system
        existing_results = search_existing(query)
        existing_found = set(doc["id"] for doc in existing_results["hits"])
        
        # Search with Thai tokenizer
        thai_results = search_thai_tokenizer(query)
        thai_found = set(doc["id"] for doc in thai_results["hits"])
        
        # Calculate metrics
        expected_set = set(expected_docs)
        existing_precision = len(existing_found & expected_set) / len(existing_found) if existing_found else 0
        thai_precision = len(thai_found & expected_set) / len(thai_found) if thai_found else 0
        
        results.append({
            "query": query,
            "existing_precision": existing_precision,
            "thai_precision": thai_precision,
            "improvement": thai_precision - existing_precision
        })
    
    return results
```

## 🔧 Configuration Management

### Environment-Specific Settings
```yaml
# config/integration/existing-meili.yml
existing_meilisearch:
  host: "http://localhost:7700"
  api_key: "${EXISTING_MEILI_API_KEY}"
  indexes:
    - name: "products"
      migrate_thai: true
    - name: "users"
      migrate_thai: false
    - name: "content"
      migrate_thai: true

thai_tokenizer:
  host: "http://localhost:8001"
  api_key: "${THAI_TOKENIZER_API_KEY}"
  
migration:
  batch_size: 50
  rate_limit_ms: 100
  backup_before_migration: true
  rollback_enabled: true
```

### Index Mapping Configuration
```json
{
  "index_mappings": {
    "products": {
      "thai_fields": ["name", "description"],
      "preserve_fields": ["id", "price", "category"],
      "tokenization_options": {
        "expand_compounds": true,
        "handle_mixed_content": true
      }
    },
    "content": {
      "thai_fields": ["title", "content", "tags"],
      "preserve_fields": ["id", "author", "created_at"],
      "tokenization_options": {
        "expand_compounds": true,
        "enable_synonyms": true
      }
    }
  }
}
```

## 🚨 Rollback Procedures

### Automated Rollback Script
```bash
#!/bin/bash
# rollback_integration.sh

echo "🔄 Starting rollback procedure..."

# 1. Stop Thai tokenizer services
echo "Stopping Thai tokenizer services..."
docker compose -f deployment/docker/docker-compose.yml down

# 2. Restore original MeiliSearch configuration
echo "Restoring original configuration..."
curl -X PATCH http://localhost:7700/indexes/your-index/settings \
  -H "Authorization: Bearer $EXISTING_API_KEY" \
  -d @backups/original-settings.json

# 3. Update application routing
echo "Reverting application routing..."
# Update your load balancer or application config

# 4. Verify rollback
echo "Verifying rollback..."
curl http://localhost:7700/health

echo "✅ Rollback completed successfully"
```

### Data Backup Strategy
```python
# backup_manager.py
class BackupManager:
    def backup_index_settings(self, index_name):
        """Backup current index settings"""
        response = requests.get(
            f"{self.meili_url}/indexes/{index_name}/settings",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        
        with open(f"backups/{index_name}-settings-{datetime.now().isoformat()}.json", "w") as f:
            json.dump(response.json(), f, indent=2)
    
    def backup_documents(self, index_name, batch_size=1000):
        """Backup all documents from an index"""
        offset = 0
        all_docs = []
        
        while True:
            response = requests.get(
                f"{self.meili_url}/indexes/{index_name}/documents",
                headers={"Authorization": f"Bearer {self.api_key}"},
                params={"limit": batch_size, "offset": offset}
            )
            
            docs = response.json().get("results", [])
            if not docs:
                break
                
            all_docs.extend(docs)
            offset += batch_size
        
        with open(f"backups/{index_name}-documents-{datetime.now().isoformat()}.json", "w") as f:
            json.dump(all_docs, f, indent=2, ensure_ascii=False)
        
        return len(all_docs)
```

## 🎯 Best Practices

### 1. Testing Strategy
- **Unit Tests**: Test individual components
- **Integration Tests**: Test system interactions
- **Performance Tests**: Compare before/after performance
- **User Acceptance Tests**: Validate search quality improvements

### 2. Monitoring
- **Response Times**: Monitor API response times
- **Error Rates**: Track error rates and types
- **Search Quality**: Monitor search result relevance
- **Resource Usage**: Monitor CPU, memory, and disk usage

### 3. Gradual Rollout
- **Start Small**: Begin with 5-10% of traffic
- **Monitor Closely**: Watch metrics and user feedback
- **Increase Gradually**: Slowly increase traffic percentage
- **Have Rollback Ready**: Always be prepared to rollback

### 4. Documentation
- **Document Changes**: Keep detailed records of all changes
- **Update Runbooks**: Update operational procedures
- **Train Team**: Ensure team understands new system
- **Create Troubleshooting Guides**: Document common issues and solutions

## 🎉 Success Metrics

### Technical Metrics
- **Search Accuracy**: Improved compound word matching
- **Response Time**: Maintained or improved response times
- **Availability**: 99.9%+ uptime during migration
- **Error Rate**: <0.1% error rate

### Business Metrics
- **User Satisfaction**: Improved search experience
- **Search Success Rate**: Higher percentage of successful searches
- **User Engagement**: Increased time spent on search results
- **Conversion Rate**: Better search leading to more conversions

## 📞 Support and Next Steps

### Getting Help
- **Documentation**: Check `docs/` directory for detailed guides
- **Community**: Join Thai NLP and MeiliSearch communities
- **Issues**: Create GitHub issues for bugs or feature requests
- **Professional Support**: Contact for enterprise support options

### Advanced Integration Topics
1. **Multi-language Support**: Handle Thai, English, and other languages
2. **Custom Dictionaries**: Add domain-specific terms
3. **Machine Learning**: Improve tokenization with ML models
4. **Analytics**: Advanced search analytics and insights

---

**Ready to integrate?** Start with the side-by-side deployment approach for the safest migration path.

**Need help?** Check our [troubleshooting guide](../troubleshooting.md) or contact our support team.