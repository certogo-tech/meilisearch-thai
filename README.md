# Thai Tokenizer for MeiliSearch

A high-performance Thai tokenization service that integrates with MeiliSearch to provide accurate search capabilities for Thai compound words and mixed Thai-English content.

## 🚀 Quick Start

### For New Users (Full Stack)

```bash
# Start both Thai Tokenizer + MeiliSearch
docker compose -f deployment/docker/docker-compose.yml up -d

# Test compound word tokenization
curl -X POST "http://localhost:8001/api/v1/tokenize" \
  -H "Content-Type: application/json" \
  -d '{"text": "วากาเมะมีประโยชน์ต่อสุขภาพ"}'
```

### For Existing MeiliSearch Users

```bash
# One-command setup for existing MeiliSearch on port 7700
./setup_existing_meilisearch.sh
```

### For Development

```bash
# Start API with compound support
python3 start_api_with_compounds.py

# Run integration tests
python3 tests/integration/test_api_integration.py
```

**📖 Complete Guide**: [QUICK_START.md](QUICK_START.md)

## 🎯 Problem & Solution

**Problem**: Thai language lacks spaces between words, making compound word segmentation critical for accurate search results. MeiliSearch's default tokenization cannot properly handle Thai compound words.

**Solution**: A containerized Thai tokenization service that pre-processes Thai text using advanced NLP techniques before indexing in MeiliSearch, dramatically improving search accuracy for Thai content.

## ✨ Key Features

- **🎯 Compound Word Tokenization**: Properly handles Thai compound words like "วากาเมะ" (wakame)
- **⚡ High Performance**: < 50ms tokenization for 1000 characters, > 500 docs/sec indexing
- **🔧 Easy Integration**: One-command setup for existing MeiliSearch instances
- **🐳 Production Ready**: Docker containerization with monitoring, health checks, and scaling
- **📚 Well Documented**: Comprehensive guides and examples for all use cases
- **🧪 Thoroughly Tested**: 13 automated tests ensure reliability
- **🏗️ Clean Architecture**: Ultra-organized codebase with clear separation of concerns

## 📁 Project Structure

Ultra-clean organization with everything in its proper place:

```
thai-tokenizer-meilisearch/
├── 📄 README.md                  # You are here
├── 📄 QUICK_START.md             # Quick setup guide  
├── 🔧 setup_existing_meilisearch.sh  # One-command setup
├── 🔧 start_api_with_compounds.py    # Development API
├── 📁 src/                       # Source code
├── 📁 deployment/                # Docker & deployment configs
├── 📁 docs/                      # All documentation
├── 📁 tests/                     # Comprehensive test suite
├── 📁 scripts/                   # Utility scripts
└── 📁 data/                      # Dictionaries & sample data
├── tests/                         # 🧪 Comprehensive test suite
│   ├── unit/                     # Unit tests for individual components
│   ├── integration/              # Integration tests for component interaction
│   ├── performance/              # Performance and load testing
│   └── production/               # Production validation tests
├── docs/                          # 📚 [Documentation hub](docs/index.md)
│   ├── api/                      # API reference and examples
│   ├── deployment/               # Deployment and operations guides
│   ├── development/              # Development setup and guidelines
│   └── architecture/             # System design and architecture
├── deployment/                    # 🚀 Deployment configurations
│   ├── docker/                   # Docker containers and compose files
│   ├── k8s/                      # Kubernetes manifests and configs
│   ├── environments/             # Environment-specific configurations
│   └── scripts/                  # Deployment automation scripts
├── config/                        # ⚙️ [Configuration management](config/index.md)
│   ├── development/              # Development environment settings
│   ├── production/               # Production environment settings
│   ├── testing/                  # Testing environment settings
│   └── shared/                   # Shared configuration files
├── data/                          # 📊 [Data and samples](data/index.md)
│   ├── samples/                  # Thai text samples and test data
│   ├── fixtures/                 # Test fixtures and mock data
│   ├── benchmarks/               # Benchmark datasets
│   └── migrations/               # Data migration scripts
├── monitoring/                    # 📈 [Observability stack](monitoring/index.md)
│   ├── grafana/                  # Grafana dashboards and configs
│   ├── prometheus/               # Prometheus monitoring setup
│   ├── logging/                  # Centralized logging configuration
│   └── alerts/                   # Alerting rules and notifications
├── reports/                       # 📋 [Generated reports](reports/index.md)
│   ├── performance/              # Performance analysis reports
│   ├── testing/                  # Test execution reports
│   └── production/               # Production readiness reports
├── build/                         # 🔨 Build and CI/CD artifacts
├── backups/                       # 💾 Project backups and snapshots
├── logs/                          # 📝 Application and service logs
└── ssl/                           # 🔒 SSL certificates and security
```

### 🗂️ Directory Navigation

Each major directory contains detailed documentation about its contents and usage:

- **[📚 Documentation](docs/index.md)** - Complete project documentation
- **[⚙️ Configuration](config/index.md)** - Environment and application settings
- **[📊 Data & Samples](data/index.md)** - Test data, fixtures, and samples
- **[📈 Monitoring](monitoring/index.md)** - Observability and monitoring setup
- **[📋 Reports](reports/index.md)** - Generated analysis and test reports

## 🛠️ Technology Stack

- **Python 3.12+** with FastAPI 0.116+
- **PyThaiNLP 5.1.2+** for Thai text processing
- **MeiliSearch 1.15.2+** for search engine
- **Docker & Docker Compose V2** for containerization
- **Pydantic V2.11+** for data validation
- **Modern tooling**: uv, ruff, mypy, pytest

## 📚 Documentation

Our documentation is organized by audience and use case. Start with the section most relevant to your needs:

### 🎯 Choose Your Path

- **New to Thai tokenization?** → [Complete Newcomer Guide (0 to 100)](docs/getting-started/newcomer-guide.md)
- **Have existing MeiliSearch?** → [Integration Guide](docs/integration/existing-meilisearch-integration.md)
- **Want to see it in action?** → Run `python3 deployment/scripts/demo_thai_tokenizer.py`

### 🚀 Getting Started

- **[Complete Newcomer Guide (0 to 100)](docs/getting-started/newcomer-guide.md)** - Start here if you're new to Thai tokenization
- **[Existing MeiliSearch Integration](docs/integration/existing-meilisearch-integration.md)** - Add Thai tokenization to your current setup
- **[Development Guide](docs/development/README.md)** - Complete development setup, API usage, and contribution guidelines
- **[Quick Start Examples](docs/examples.md)** - Ready-to-run code examples and integration patterns
- **[API Documentation](docs/api/index.md)** - Comprehensive REST API reference with interactive examples

### 🏗️ Architecture & Design

- **[System Architecture](docs/architecture/index.md)** - High-level system design, components, and data flow
- **[Project Structure Guide](docs/architecture/project-structure.md)** - Detailed explanation of directory organization

### 🚀 Deployment & Operations

- **[Production Deployment](docs/deployment/PRODUCTION_DEPLOYMENT.md)** - Complete production deployment guide
- **[Performance Optimizations](docs/deployment/PERFORMANCE_OPTIMIZATIONS.md)** - Performance tuning and scaling strategies
- **[Deployment Index](docs/deployment/index.md)** - All deployment-related documentation

### 🔧 Development Resources

- **[Development Setup](docs/development/index.md)** - Local development environment setup
- **[Testing Guide](docs/development/testing.md)** - Testing strategies and best practices
- **[Contributing Guidelines](docs/development/contributing.md)** - How to contribute to the project

### 📊 Data & Configuration

- **[Sample Data Guide](data/samples/README.md)** - Thai text samples, test cases, and usage examples
- **[Configuration Reference](config/index.md)** - Environment settings and configuration options
- **[Monitoring Setup](monitoring/index.md)** - Observability, logging, and alerting configuration

### 🆘 Support & Troubleshooting

- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues, solutions, and debugging tips
- **[Performance Reports](reports/index.md)** - System performance analysis and benchmarks

## 🚀 Deployment Options

### Development

```bash
docker compose up -d
```

### Production

```bash
# Quick production deployment
./deployment/scripts/deploy_production.sh

# Or with monitoring stack
COMPOSE_PROFILES=monitoring docker compose -f docker-compose.prod.yml up -d
```

### Kubernetes

```bash
kubectl apply -f deployment/k8s/
```

## 📊 Performance

- **Tokenization**: < 50ms for 1000 characters
- **Search Response**: < 100ms for typical queries
- **Memory Usage**: < 256MB per container
- **Throughput**: > 500 documents/second indexing
- **Availability**: 99.9% uptime with proper deployment

## 🤝 Contributing

We welcome contributions! Please see our [Development Guide](docs/development/README.md) for setup instructions and contribution guidelines.

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Run quality checks: `uv run ruff check && uv run mypy src/`
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Documentation**: Check the [docs/](docs/) directory
- **Issues**: Report bugs on GitHub Issues
- **Performance**: Run benchmarks with `python deployment/scripts/benchmark.py`
- **Examples**: See [data/samples/](data/samples/) for usage examples

---

**Ready to improve your Thai search experience?** Start with our [Development Guide](docs/development/README.md) or jump straight to [Production Deployment](docs/deployment/PRODUCTION_DEPLOYMENT.md)!
