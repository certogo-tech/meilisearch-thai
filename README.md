# Thai Tokenizer for MeiliSearch

A high-performance Thai tokenization service that integrates with MeiliSearch to provide accurate search capabilities for Thai compound words and mixed Thai-English content.

## 🚀 Quick Start

```bash
# Clone and start services
git clone <repository-url>
cd thai-tokenizer-meilisearch
docker compose up -d

# Test the service
curl -X POST http://localhost:8000/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "ปัญญาประดิษฐ์และการเรียนรู้ของเครื่อง"}'
```

## 🎯 Problem & Solution

**Problem**: Thai language lacks spaces between words, making compound word segmentation critical for accurate search results. MeiliSearch's default tokenization cannot properly handle Thai compound words.

**Solution**: A containerized Thai tokenization service that pre-processes Thai text using advanced NLP techniques before indexing in MeiliSearch, dramatically improving search accuracy for Thai content.

## ✨ Key Features

- **Accurate Thai Tokenization**: Uses PyThaiNLP with attacut/deepcut fallbacks
- **Mixed Language Support**: Handles Thai-English mixed content intelligently
- **High Performance**: < 50ms tokenization for 1000 characters, > 500 docs/sec indexing
- **Production Ready**: Docker containerization with monitoring, health checks, and scaling
- **REST API**: FastAPI-based with automatic OpenAPI documentation
- **Configurable**: Multiple tokenization engines and customizable settings

## 📁 Project Structure

```
thai-tokenizer-meilisearch/
├── src/                    # Source code
│   ├── api/               # FastAPI application
│   ├── tokenizer/         # Thai tokenization logic
│   ├── meilisearch_integration/  # MeiliSearch integration
│   └── utils/             # Utility modules
├── tests/                 # Comprehensive test suite
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   ├── performance/      # Performance tests
│   └── production/       # Production validation
├── docs/                  # Documentation
│   ├── api/              # API documentation
│   ├── deployment/       # Deployment guides
│   ├── development/      # Development setup
│   └── architecture/     # System architecture
├── deployment/            # Deployment configurations
│   ├── docker/           # Docker configurations
│   ├── k8s/             # Kubernetes manifests
│   ├── environments/    # Environment configs
│   └── scripts/         # Deployment scripts
├── config/               # Configuration files
├── data/                 # Sample data and fixtures
├── monitoring/           # Monitoring and observability
└── reports/             # Generated reports
```

## 🛠️ Technology Stack

- **Python 3.12+** with FastAPI 0.116+
- **PyThaiNLP 5.1.2+** for Thai text processing
- **MeiliSearch 1.15.2+** for search engine
- **Docker & Docker Compose V2** for containerization
- **Pydantic V2.11+** for data validation
- **Modern tooling**: uv, ruff, mypy, pytest

## 📚 Documentation

### Getting Started
- **[Development Guide](docs/development/README.md)** - Complete development setup and API usage
- **[API Documentation](docs/api/index.md)** - REST API reference with examples

### Deployment & Operations
- **[Production Deployment](docs/deployment/PRODUCTION_DEPLOYMENT.md)** - Production deployment guide
- **[Performance Optimizations](docs/deployment/PERFORMANCE_OPTIMIZATIONS.md)** - Performance tuning guide
- **[Architecture Overview](docs/architecture/index.md)** - System design and architecture

### Additional Resources
- **[Troubleshooting Guide](docs/troubleshooting.md)** - Common issues and solutions
- **[Sample Data](data/samples/README.md)** - Thai text samples and test cases
- **[Examples](docs/examples.md)** - Usage examples and integration patterns

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