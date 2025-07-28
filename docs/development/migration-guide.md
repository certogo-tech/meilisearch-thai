# Project Structure Migration Guide

## Overview

This document describes the migration from the original flat project structure to the new organized directory layout that follows modern Python project conventions. The migration was completed to improve maintainability, developer experience, and deployment management.

## Migration Summary

### What Changed

The project has been restructured from a flat directory layout to an organized structure with clear separation of concerns:

- **Tests**: All test files moved to `tests/` with subdirectories by type
- **Documentation**: All documentation consolidated in `docs/` with logical grouping
- **Deployment**: All deployment-related files moved to `deployment/` with tool-specific subdirectories
- **Configuration**: Environment-specific configs organized in `config/` subdirectories
- **Data**: Sample data and fixtures organized in `data/` subdirectories
- **Monitoring**: Observability files organized in `monitoring/` subdirectories
- **Reports**: Generated reports organized in `reports/` subdirectories

### Directory Structure Before vs After

#### Before (Flat Structure)
```
thai-tokenizer-meilisearch/
├── src/                           # Source code
├── test_*.py                      # Unit tests scattered in root
├── load_test.py                   # Performance tests in root
├── production_test.py             # Production tests in root
├── docker/                        # Docker files
├── scripts/                       # Deployment scripts
├── sample_data/                   # Sample data
├── *.md                          # Documentation files scattered
├── .env.prod                     # Config files in root
├── docker-compose*.yml           # Compose files in root
└── [various other files]
```

#### After (Organized Structure)
```
thai-tokenizer-meilisearch/
├── src/                           # Source code (unchanged)
├── tests/                         # All test files organized by type
│   ├── unit/                      # Unit tests
│   ├── integration/               # Integration tests
│   ├── performance/               # Performance and load tests
│   └── production/                # Production validation tests
├── docs/                          # All documentation
│   ├── api/                       # API documentation
│   ├── deployment/                # Deployment guides
│   ├── development/               # Development guides
│   └── architecture/              # Architecture documentation
├── deployment/                    # All deployment-related files
│   ├── docker/                    # Docker configurations
│   ├── k8s/                       # Kubernetes configurations
│   ├── environments/              # Environment-specific configs
│   └── scripts/                   # Deployment scripts
├── config/                        # Configuration files by environment
│   ├── development/               # Development configuration
│   ├── production/                # Production configuration
│   ├── testing/                   # Testing configuration
│   └── shared/                    # Shared configuration
├── data/                          # Data files and samples
│   ├── samples/                   # Thai text samples
│   ├── fixtures/                  # Test fixtures
│   ├── benchmarks/                # Benchmark data
│   └── migrations/                # Data migration scripts
├── monitoring/                    # Monitoring and observability
│   ├── grafana/                   # Grafana dashboards
│   ├── prometheus/                # Prometheus configuration
│   ├── logging/                   # Logging configuration
│   └── alerts/                    # Alerting rules
├── reports/                       # Generated reports and analysis
│   ├── performance/               # Performance reports
│   ├── testing/                   # Test reports
│   └── production/                # Production readiness reports
└── [root files]                   # Essential project files only
```

## File Movement Details

### Test Files Migration
- `test_*.py` → `tests/unit/`
- `load_test.py`, `manual_performance_test.py`, `functional_test.py` → `tests/performance/`
- `production_test.py` → `tests/production/`
- Integration tests remained in `tests/integration/`

### Documentation Migration
- `PRODUCTION_DEPLOYMENT.md`, `PERFORMANCE_OPTIMIZATIONS.md` → `docs/deployment/`
- Development README → `docs/development/README.md`
- New root README created with project overview
- Report files → `reports/` subdirectories by type

### Deployment Files Migration
- `docker/` contents → `deployment/docker/`
- `docker-compose*.yml` → `deployment/docker/`
- `scripts/` → `deployment/scripts/`
- `k8s-deployment.yaml` → `deployment/k8s/`

### Configuration Files Migration
- `.env.prod`, `.env.prod.local` → `config/production/`
- `.env.example` → `config/development/`
- Environment-specific templates created

### Data Files Migration
- `sample_data/` → `data/samples/`
- Test fixtures organized in `data/fixtures/`
- Benchmark data in `data/benchmarks/`

## Impact on Development Workflow

### Testing
- **Before**: `pytest test_*.py`
- **After**: `pytest tests/` or `pytest tests/unit/` for specific test types

### Running Services
- **Before**: `docker-compose up`
- **After**: `docker compose -f deployment/docker/docker-compose.yml up`

### Configuration
- **Before**: `.env.prod` in root
- **After**: `config/production/.env.prod`

### Documentation
- **Before**: Various `.md` files in root
- **After**: Organized in `docs/` with clear navigation

## Updated Commands

### Development Setup
```bash
# Clone and setup (unchanged)
git clone <repository>
cd thai-tokenizer-meilisearch

# Install dependencies (unchanged)
uv venv
uv pip install -r requirements.txt

# Run tests (updated paths)
uv run pytest tests/                    # All tests
uv run pytest tests/unit/              # Unit tests only
uv run pytest tests/integration/       # Integration tests only
uv run pytest tests/performance/       # Performance tests only
```

### Docker Operations
```bash
# Start services (updated compose file location)
docker compose -f deployment/docker/docker-compose.yml up -d

# Production deployment (updated script location)
./deployment/scripts/deploy_production.sh

# View logs (unchanged service names)
docker compose -f deployment/docker/docker-compose.yml logs -f thai-tokenizer
```

### Configuration Management
```bash
# Development environment
cp config/development/.env.template config/development/.env

# Production environment
cp config/production/.env.template config/production/.env.prod
```

## Breaking Changes

### Import Paths
- No Python import paths changed (all source code in `src/` unchanged)
- Test discovery patterns updated in `pyproject.toml`

### Docker Compose
- Compose files moved to `deployment/docker/`
- File paths in compose files updated for new structure
- Build contexts updated for new directory layout

### Scripts and Automation
- Deployment scripts moved to `deployment/scripts/`
- Script paths updated in documentation
- CI/CD pipelines updated for new test paths

### Configuration Files
- Environment files moved to `config/` subdirectories
- Docker compose files reference new config locations
- Deployment scripts updated for new config paths

## Validation Steps

After migration, the following validation was performed:

1. **Test Suite Execution**: All tests run successfully with new structure
2. **Docker Build**: All containers build and run correctly
3. **Documentation Links**: All internal documentation links verified
4. **Deployment Process**: End-to-end deployment tested
5. **Configuration Loading**: All environment configs load correctly

## Rollback Plan

If rollback is needed:

1. **Git Revert**: Use git to revert to pre-migration commit
2. **File Restoration**: Restore files to original locations
3. **Config Updates**: Revert configuration file references
4. **Documentation**: Restore original documentation structure

## Team Onboarding

### For New Team Members
1. Clone the repository
2. Follow the updated setup instructions in `docs/development/README.md`
3. Review the project structure in `docs/architecture/project-structure.md`
4. Run tests to verify setup: `pytest tests/`

### For Existing Team Members
1. Pull the latest changes
2. Update local development environment
3. Update any local scripts or aliases
4. Review this migration guide
5. Update IDE/editor configurations for new test paths

## Benefits Achieved

1. **Improved Organization**: Clear separation of concerns
2. **Better Navigation**: Logical grouping of related files
3. **Enhanced Maintainability**: Easier to find and modify files
4. **Professional Structure**: Follows Python project best practices
5. **Scalability**: Structure supports project growth
6. **Developer Experience**: Faster onboarding and development

## Support

For questions about the migration or new structure:
- Review this guide and the project structure documentation
- Check the updated development setup instructions
- Refer to the architecture documentation in `docs/architecture/`
- Contact the development team for specific issues

## Next Steps

1. Update any external documentation or wikis
2. Update CI/CD pipeline configurations if needed
3. Train team members on new structure
4. Monitor for any issues in the first few weeks
5. Gather feedback and make adjustments if necessary