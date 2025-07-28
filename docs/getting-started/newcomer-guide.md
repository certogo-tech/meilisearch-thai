# Complete Newcomer Guide: Thai Tokenizer for MeiliSearch (0 to 100)

Welcome! This guide will take you from zero knowledge to running a production-ready Thai search system.

## 🎯 What You'll Learn

By the end of this guide, you'll have:

- ✅ A running Thai tokenization service
- ✅ MeiliSearch configured for Thai text
- ✅ Understanding of how Thai tokenization works
- ✅ Ability to search Thai compound words accurately
- ✅ Production deployment knowledge

## 📋 Prerequisites

### System Requirements

- **Operating System**: macOS, Linux, or Windows with WSL2
- **Memory**: At least 4GB RAM (8GB recommended)
- **Storage**: 2GB free space
- **Network**: Internet connection for downloading dependencies

### Required Software

1. **Docker & Docker Compose** (we'll install this)
2. **Git** (we'll install this)
3. **Python 3.9+** (optional, for development)
4. **curl** (for testing APIs)

## 🚀 Step-by-Step Setup

### Step 1: Install Required Software

#### On macOS:

```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Docker Desktop
brew install --cask docker

# Install Git
brew install git

# Install curl (usually pre-installed)
brew install curl
```

#### On Ubuntu/Debian Linux:

```bash
# Update package list
sudo apt update

# Install Docker
sudo apt install -y docker.io docker-compose-plugin

# Install Git
sudo apt install -y git curl

# Add your user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

#### On Windows:

1. Install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
2. Install [Git for Windows](https://git-scm.com/download/win)
3. Use PowerShell or Command Prompt for commands

### Step 2: Clone the Project

```bash
# Clone the repository
git clone https://github.com/your-username/thai-tokenizer-meilisearch.git
cd thai-tokenizer-meilisearch

# Verify you're in the right directory
ls -la
# You should see: src/, docs/, deployment/, tests/, etc.
```

### Step 3: Start the Services

```bash
# Start all services with Docker Compose
docker compose -f deployment/docker/docker-compose.yml up -d

# Wait for services to start (about 30-60 seconds)
# Check if services are running
docker compose -f deployment/docker/docker-compose.yml ps
```

**Expected Output:**

```
NAME                      IMAGE                          STATUS
docker-meilisearch-1      getmeili/meilisearch:v1.15.2   Up (healthy)
docker-thai-tokenizer-1   docker-thai-tokenizer          Up (healthy)
```

### Step 4: Verify Everything Works

#### Test 1: Health Check

```bash
# Test Thai Tokenizer health
curl http://localhost:8001/health

# Expected response:
# {"status":"healthy","version":"1.0.0",...}
```

#### Test 2: Basic Thai Tokenization

```bash
# Test Thai text tokenization
curl -X POST http://localhost:8001/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"}'

# Expected response:
# {"tokens": ["ปัญญาประดิษฐ์", "และ", "การเรียนรู้", "ของ", "เครื่อง"], ...}
```

#### Test 3: MeiliSearch Connection

```bash
# Test MeiliSearch
curl http://localhost:7700/health

# Expected response:
# {"status": "available"}
```

🎉 **Congratulations!** If all tests pass, your Thai tokenizer is working!

## 🧪 Interactive Learning

### Run the Demo Script

```bash
# Run interactive demonstrations
python3 deployment/scripts/demo_thai_tokenizer.py
```

This will show you:

- Basic Thai tokenization examples
- Compound word handling
- Mixed Thai-English content
- Search query processing
- Performance comparisons
- Real-world examples

### Run Comprehensive Tests

```bash
# Run full system tests
python3 tests/integration/test_comprehensive_system.py
```

This validates:

- All API endpoints
- Performance benchmarks
- Error handling
- Configuration management

## 📖 Understanding Thai Tokenization

### The Problem

Thai language doesn't use spaces between words:

- **Thai text**: `ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง`
- **Meaning**: "Artificial Intelligence and Machine Learning"
- **Without tokenization**: Search engines can't find compound words properly

### The Solution

Our tokenizer breaks Thai text into meaningful words:

- **Input**: `ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง`
- **Output**: `["ปัญญาประดิษฐ์", "และ", "การเรียนรู้", "ของ", "เครื่อง"]`
- **Result**: Users can search for "ปัญญาประดิษฐ์" and find documents containing this compound word

### Real-World Example

```bash
# Without tokenization: Searching "ปัญญา" might not find "ปัญญาประดิษฐ์"
# With tokenization: Searching "ปัญญา" will find "ปัญญาประดิษฐ์" correctly

# Test this yourself:
curl -X POST http://localhost:8001/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{"query": "ปัญญา", "options": {"expand_compounds": true}}'
```

### Advanced Example: Thai-Japanese Compound Words

Thai cuisine uses many Japanese ingredients, creating complex compound words:

```bash
# Test Thai-Japanese compound word
curl -X POST http://localhost:8001/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "สาหร่ายวากาเมะเป็นอาหารทะเลที่มีประโยชน์"}'

# Expected result: ["สาหร่ายวากาเมะ", "เป็น", "อาหารทะเล", "ที่", "มี", "ประโยชน์"]
# "สาหร่ายวากาเมะ" = wakame seaweed (Thai + Japanese)

# Test partial searches:
curl -X POST http://localhost:8001/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{"query": "สาหร่าย", "options": {"expand_compounds": true}}'

curl -X POST http://localhost:8001/api/v1/query/process \
  -H "Content-Type: application/json" \
  -d '{"query": "วากาเมะ", "options": {"expand_compounds": true}}'
```

## 🌐 API Documentation

### Access Interactive API Docs

Open your browser and go to: **<http://localhost:8001/docs>**

This provides:

- Complete API reference
- Interactive testing interface
- Request/response examples
- Authentication details

### Key Endpoints

#### 1. Tokenize Thai Text

```bash
POST /api/v1/tokenize
{
  "text": "Your Thai text here"
}
```

#### 2. Process Search Queries

```bash
POST /api/v1/query/process
{
  "query": "Your search query",
  "options": {"expand_compounds": true}
}
```

#### 3. Get Configuration

```bash
GET /api/v1/config
```

## 🏗️ Building Your First Thai Search Application

### Step 1: Index Thai Documents

```bash
# Example: Index a Thai document
curl -X POST http://localhost:7700/indexes/documents/documents \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer masterKey" \
  -d '[{
    "id": 1,
    "title": "การพัฒนา AI ในประเทศไทย",
    "content": "ปัญญาประดิษฐ์กำลังเปลี่ยนแปลงอุตสาหกรรมต่างๆ ในประเทศไทย"
  }]'
```

### Step 2: Configure Thai Tokenization Settings

```bash
# Configure MeiliSearch for Thai text
curl -X PATCH http://localhost:7700/indexes/documents/settings \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer masterKey" \
  -d '{
    "searchableAttributes": ["title", "content"],
    "stopWords": ["และ", "ของ", "ใน", "ที่", "เป็น"],
    "synonyms": {
      "AI": ["ปัญญาประดิษฐ์", "เอไอ"],
      "ML": ["การเรียนรู้ของเครื่อง"]
    }
  }'
```

### Step 3: Search Thai Content

```bash
# Search for Thai compound words
curl -X POST http://localhost:7700/indexes/documents/search \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer masterKey" \
  -d '{
    "q": "ปัญญาประดิษฐ์",
    "limit": 10
  }'
```

## 🚀 Production Deployment

### Option 1: Docker Compose (Recommended for beginners)

```bash
# Production deployment with monitoring
COMPOSE_PROFILES=monitoring docker compose -f deployment/docker/docker-compose.yml up -d
```

### Option 2: Using Production Script

```bash
# Automated production setup
./deployment/scripts/setup_production_local.sh
```

### Option 3: Cloud Deployment

See [Production Deployment Guide](../deployment/production-setup-guide.md) for:

- AWS deployment
- Google Cloud deployment
- Azure deployment
- Kubernetes deployment

## 📊 Monitoring and Maintenance

### Check Service Status

```bash
# View service status
docker compose -f deployment/docker/docker-compose.yml ps

# View logs
docker compose -f deployment/docker/docker-compose.yml logs thai-tokenizer
docker compose -f deployment/docker/docker-compose.yml logs meilisearch
```

### Performance Monitoring

```bash
# Check health endpoints
curl http://localhost:8001/health
curl http://localhost:7700/health

# Run performance tests
python3 tests/integration/test_comprehensive_system.py
```

### Backup and Recovery

```bash
# Backup MeiliSearch data
docker compose -f deployment/docker/docker-compose.yml exec meilisearch \
  curl -X POST http://localhost:7700/dumps -H "Authorization: Bearer masterKey"

# Backup configuration
cp -r config/ backups/config-$(date +%Y%m%d)
```

## 🆘 Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check Docker is running
docker --version

# Check ports are available
lsof -i :8001  # Thai tokenizer port
lsof -i :7700  # MeiliSearch port

# Restart services
docker compose -f deployment/docker/docker-compose.yml restart
```

#### Tokenization Not Working

```bash
# Check service logs
docker compose -f deployment/docker/docker-compose.yml logs thai-tokenizer

# Test with simple text
curl -X POST http://localhost:8001/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "สวัสดี"}'
```

#### Search Results Poor

1. Verify Thai tokenization is working
2. Check MeiliSearch index settings
3. Review stop words and synonyms configuration
4. Test with the demo script

### Getting Help

- **Documentation**: Check `docs/` directory
- **Examples**: Run `python3 deployment/scripts/demo_thai_tokenizer.py`
- **Issues**: Create GitHub issue with error logs
- **Community**: Join Thai NLP communities

## 🎓 Next Steps

### Learn More

1. **[Development Guide](../development/README.md)** - Contribute to the project
2. **[API Documentation](../api/index.md)** - Advanced API usage
3. **[Performance Optimization](../deployment/PERFORMANCE_OPTIMIZATIONS.md)** - Tune for your needs
4. **[Architecture Guide](../architecture/index.md)** - Understand the system design

### Advanced Topics

1. **Custom Dictionary**: Add domain-specific Thai terms
2. **Multi-language Support**: Handle Thai-English mixed content
3. **Scaling**: Deploy across multiple servers
4. **Integration**: Connect with your existing applications

### Build Something Cool

Ideas for your first Thai search project:

- **Thai News Search**: Search Thai news articles
- **E-commerce Search**: Thai product search
- **Document Management**: Thai document search system
- **Academic Search**: Thai research paper search

## 🎉 Congratulations!

You've successfully:

- ✅ Set up a complete Thai tokenization system
- ✅ Learned how Thai tokenization works
- ✅ Built your first Thai search application
- ✅ Deployed a production-ready system
- ✅ Gained troubleshooting skills

**You're now ready to build amazing Thai search applications!**

---

**Need help?** Check our [troubleshooting guide](../troubleshooting.md) or run the demo script for examples.

**Ready for production?** See our [production deployment guide](../deployment/production-setup-guide.md).

**Want to contribute?** Check our [development guide](../development/README.md).