# Project Structure Documentation

This document provides a comprehensive overview of the Thai Tokenizer project structure after the 2025 restructuring migration, explaining the purpose and organization of each directory and key files.

## Overview

The project follows modern Python project organization standards with clear separation of concerns, making it easy for developers to navigate, understand, and contribute to the codebase. The structure was migrated from a flat directory layout to this organized hierarchy to improve maintainability, developer experience, and deployment management.

> **Migration Note**: This project was restructured in 2025 from a flat directory structure to the current organized layout. For detailed migration information, see the [Migration Guide](../development/migration-guide.md).

## Directory Structure

### 🔧 Source Code (`src/`)

The main application code organized by functional areas:

```
src/
├── api/                           # FastAPI web application
│   ├── main.py                   # Application entry point and configuration
│   ├── endpoints/                # API route handlers
│   │   ├── tokenize.py          # Tokenization endpoints
│   │   ├── documents.py         # Document processing endpoints
│   │   ├── config.py            # Configuration endpoints
│   │   └── monitoring.py        # Health and monitoring endpoints
│   └── models/                   # Pydantic data models
│       ├── requests.py          # Request schemas
│       └── responses.py         # Response schemas
├── tokenizer/                     # Core tokenization logic
│   ├── thai_segmenter.py        # Thai text segmentation
│   ├── token_processor.py       # Token processing utilities
│   ├── query_processor.py       # Query processing logic
│   ├── result_enhancer.py       # Search result enhancement
│   └── config_manager.py        # Tokenizer configuration
├── meilisearch_integration/       # MeiliSearch integration
│   ├── client.py                # MeiliSearch client wrapper
│   ├── document_processor.py    # Document indexing pipeline
│   └── settings_manager.py      # Search engine settings
└── utils/                         # Shared utilities
    ├── logging.py               # Logging configuration
    └── health.py                # Health check utilities
```

**Key Principles:**
- Each module has a single responsibility
- Clear separation between API, business logic, and integrations
- Shared utilities are centralized in `utils/`

### 🧪 Testing (`tests/`)

Comprehensive test suite organized by test type:

```
tests/
├── unit/                          # Unit tests for individual components
│   ├── test_thai_segmenter.py   # Tokenizer unit tests
│   ├── test_meilisearch_client.py # MeiliSearch client tests
│   ├── test_api_endpoints.py     # API endpoint tests
│   └── test_*.py                 # Additional unit tests
├── integration/                   # Integration tests
│   ├── test_end_to_end.py        # Complete workflow tests
│   ├── test_meilisearch_integration.py # MeiliSearch integration
│   └── test_full_system_integration.py # System integration
├── performance/                   # Performance and load tests
│   ├── load_test.py              # Load testing scenarios
│   ├── functional_test.py        # Functional performance tests
│   └── manual_performance_test.py # Manual performance validation
└── production/                    # Production validation tests
    └── production_test.py         # Production readiness tests
```

**Testing Strategy:**
- Unit tests focus on individual component behavior
- Integration tests verify component interactions
- Performance tests ensure system meets SLA requirements
- Production tests validate deployment readiness

### 📚 Documentation (`docs/`)

Comprehensive documentation organized by audience:

```
docs/
├── index.md                       # Documentation hub and navigation
├── api/                          # API documentation
│   └── index.md                  # API reference and examples
├── deployment/                    # Deployment and operations
│   ├── index.md                  # Deployment documentation hub
│   ├── PRODUCTION_DEPLOYMENT.md  # Production deployment guide
│   └── PERFORMANCE_OPTIMIZATIONS.md # Performance tuning
├── development/                   # Development resources
│   ├── index.md                  # Development documentation hub
│   └── README.md                 # Development setup guide
├── architecture/                  # System architecture
│   ├── index.md                  # Architecture documentation hub
│   └── project-structure.md      # This document
├── examples.md                    # Usage examples
└── troubleshooting.md            # Common issues and solutions
```

**Documentation Philosophy:**
- Audience-specific organization (developers, DevOps, architects)
- Progressive disclosure from overview to detailed implementation
- Practical examples and troubleshooting guides

### 🚀 Deployment (`deployment/`)

All deployment-related configurations and scripts:

```
deployment/
├── docker/                        # Docker configurations
│   ├── Dockerfile                # Main application container
│   ├── Dockerfile.prod           # Production-optimized container
│   ├── docker-compose.yml        # Development orchestration
│   ├── docker-compose.prod.yml   # Production orchestration
│   ├── docker-compose.optimized.yml # Performance-optimized setup
│   └── nginx.conf                # Reverse proxy configuration
├── k8s/                          # Kubernetes manifests
│   ├── README.md                 # Kubernetes deployment guide
│   └── k8s-deployment.yaml       # Kubernetes deployment config
├── environments/                  # Environment-specific configs
└── scripts/                      # Deployment automation
    ├── README.md                 # Script documentation
    ├── deploy_production.sh      # Production deployment
    ├── setup_demo.py             # Demo environment setup
    ├── benchmark.py              # Performance benchmarking
    └── run_*.py                  # Various automation scripts
```

**Deployment Strategy:**
- Multi-stage Docker builds for optimized production images
- Environment-specific configurations
- Automated deployment scripts
- Kubernetes support for scalable deployments

### ⚙️ Configuration (`config/`)

Environment-based configuration management:

```
config/
├── index.md                       # Configuration documentation
├── development/                   # Development environment
│   ├── .env.example              # Development environment template
│   └── .env.template             # Configuration template
├── production/                    # Production environment
│   ├── .env.prod                 # Production environment settings
│   ├── .env.prod.local           # Local production overrides
│   └── .env.template             # Production template
├── testing/                       # Testing environment
│   └── .env.template             # Testing configuration template
└── shared/                        # Shared configurations
    └── logging.yaml              # Logging configuration
```

**Configuration Principles:**
- Environment-specific settings isolation
- Template files for easy setup
- Secure handling of sensitive configuration
- Centralized logging configuration

### 📊 Data (`data/`)

Sample data, fixtures, and data management:

```
data/
├── index.md                       # Data documentation
├── samples/                       # Thai text samples
│   ├── README.md                 # Sample data documentation
│   ├── thai_documents.json       # Thai document samples
│   ├── test_queries.json         # Test search queries
│   ├── combined_dataset.json     # Combined test dataset
│   ├── formal_documents.json     # Formal Thai text samples
│   └── informal_documents.json   # Informal Thai text samples
├── fixtures/                      # Test fixtures
├── benchmarks/                    # Benchmark datasets
└── migrations/                    # Data migration scripts
```

**Data Management:**
- Comprehensive Thai text samples for testing
- Structured test fixtures for consistent testing
- Benchmark datasets for performance validation
- Migration scripts for data updates

### 📈 Monitoring (`monitoring/`)

Observability and monitoring infrastructure:

```
monitoring/
├── index.md                       # Monitoring documentation
├── grafana/                       # Grafana dashboards
│   └── dashboards/               # Dashboard configurations
├── prometheus/                    # Prometheus monitoring
│   └── prometheus.yml            # Prometheus configuration
├── logging/                       # Centralized logging
└── alerts/                        # Alerting rules
```

**Monitoring Strategy:**
- Comprehensive metrics collection with Prometheus
- Visual dashboards with Grafana
- Centralized logging for troubleshooting
- Proactive alerting for system health

### 📋 Reports (`reports/`)

Generated reports and analysis:

```
reports/
├── index.md                       # Reports documentation
├── performance/                   # Performance analysis
│   └── performance_optimization_report.json
├── testing/                       # Test execution reports
│   ├── comprehensive_test_report.md
│   └── integration_test_report.json
└── production/                    # Production readiness
    ├── PRODUCTION_READINESS_REPORT.md
    └── production_test_results.json
```

**Reporting Philosophy:**
- Automated report generation
- Performance tracking over time
- Test execution summaries
- Production readiness validation

## Key Design Decisions

### 1. Modular Architecture
- Clear separation between API, business logic, and integrations
- Each module has a single responsibility
- Easy to test and maintain individual components

### 2. Environment-Based Configuration
- Separate configuration for each environment
- Template files for easy setup
- Secure handling of sensitive data

### 3. Comprehensive Testing Strategy
- Multiple test types (unit, integration, performance, production)
- Test organization mirrors source code structure
- Automated test execution in CI/CD pipeline

### 4. Documentation-First Approach
- Documentation organized by user type and use case
- Progressive disclosure from overview to implementation details
- Practical examples and troubleshooting guides

### 5. Production-Ready Deployment
- Multi-stage Docker builds for optimization
- Kubernetes support for scalability
- Comprehensive monitoring and observability

## Navigation Guidelines

### For New Developers
1. Start with the [Development Guide](../development/README.md)
2. Review the [API Documentation](../api/index.md)
3. Explore the source code structure in `src/`
4. Run tests to understand system behavior: `pytest tests/`

### For Existing Team Members (Post-Migration)
1. Review the [Migration Guide](../development/migration-guide.md) for changes
2. Update local development commands (see migration guide)
3. Update any personal scripts or aliases for new paths
4. Review updated development setup instructions

### For DevOps Engineers
1. Review the [Deployment Documentation](../deployment/index.md)
2. Examine deployment configurations in `deployment/`
3. Update deployment scripts for new file paths
4. Set up monitoring using `monitoring/` configurations
5. Review production readiness reports in `reports/production/`

### For System Architects
1. Study this project structure documentation
2. Review the system architecture documentation
3. Examine the modular design in `src/`
4. Understand the testing strategy in `tests/`
5. Review the migration rationale and benefits

## Maintenance and Evolution

This project structure is designed to evolve with the project needs while maintaining clarity and organization. When adding new features:

1. Follow the established patterns for code organization
2. Add appropriate tests in the corresponding test directories
3. Update documentation to reflect changes
4. Ensure configuration management supports new features
5. Add monitoring for new components

The structure supports both small-scale development and large-scale production deployment while maintaining developer productivity and system reliability.