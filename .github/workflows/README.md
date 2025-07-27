# GitHub Actions Workflows

This directory contains GitHub Actions workflows for the Thai Tokenizer MeiliSearch project. The workflows are organized to support the new project structure with separate test directories and deployment configurations.

## Workflows Overview

### 1. CI Workflow (`ci.yml`)
**Trigger:** Push to main/develop branches, Pull requests
**Purpose:** Continuous integration testing and code quality checks

**Jobs:**
- **test**: Runs unit and integration tests in parallel matrix
  - Linting with ruff
  - Type checking with mypy  
  - Test execution with pytest
  - Coverage reporting
- **performance-tests**: Runs performance benchmarks (main branch only)
- **security**: Security scanning with bandit

**Test Structure Support:**
- Uses new test directory structure: `tests/unit/`, `tests/integration/`
- Separate test jobs for different test types
- Coverage reporting for each test category

### 2. Deploy Workflow (`deploy.yml`)
**Trigger:** Push to main branch, version tags, manual dispatch
**Purpose:** Build and deploy Docker images to staging/production

**Jobs:**
- **build-and-push**: Build multi-arch Docker images
- **deploy-staging**: Deploy to staging environment (main branch)
- **deploy-production**: Deploy to production (version tags only)

**Directory Structure Support:**
- Uses `deployment/docker/Dockerfile.prod` for production builds
- References `deployment/k8s/` for Kubernetes deployments
- Runs `tests/production/` for validation

### 3. Release Workflow (`release.yml`)
**Trigger:** Version tags (v*)
**Purpose:** Create GitHub releases with documentation

**Jobs:**
- **create-release**: Generate changelog and create release
- **build-documentation**: Build and deploy documentation to GitHub Pages

**Documentation Support:**
- Uses `docs/` directory structure
- Builds documentation from organized docs folders
- Uploads test coverage and performance reports

### 4. Maintenance Workflow (`maintenance.yml`)
**Trigger:** Daily schedule, manual dispatch
**Purpose:** Automated maintenance tasks

**Jobs:**
- **dependency-check**: Check for outdated dependencies
- **cleanup-artifacts**: Remove old GitHub artifacts
- **performance-monitoring**: Nightly performance benchmarks

**Monitoring Support:**
- Uses `deployment/scripts/benchmark.py` for performance testing
- Stores results in `reports/performance/`
- Compares against baseline metrics

### 5. Docker Workflow (`docker.yml`)
**Trigger:** Changes to source code or Docker files
**Purpose:** Build, test, and scan Docker images

**Jobs:**
- **build-and-test**: Build images and run security scans
- **integration-test**: Test Docker containers with MeiliSearch

**Docker Structure Support:**
- Builds from `deployment/docker/Dockerfile` and `deployment/docker/Dockerfile.prod`
- Tests container integration with MeiliSearch service
- Vulnerability scanning with Trivy

## Environment Variables and Secrets

### Required Secrets
- `GITHUB_TOKEN`: Automatically provided by GitHub
- `STAGING_MEILI_HOST`: MeiliSearch host for staging
- `STAGING_MEILI_KEY`: MeiliSearch API key for staging  
- `PRODUCTION_API_URL`: Production API URL for health checks

### Environment Variables
- `PYTHON_VERSION`: Python version (default: "3.12")
- `REGISTRY`: Container registry (default: ghcr.io)
- `IMAGE_NAME`: Docker image name (default: repository name)

## Test Directory Integration

The workflows are designed to work with the new test directory structure:

```
tests/
├── unit/          # Unit tests (run in CI matrix)
├── integration/   # Integration tests (run in CI matrix)  
├── performance/   # Performance tests (run on main branch)
└── production/    # Production validation (run in deployment)
```

### Test Execution Strategy
- **Unit tests**: Run on every PR and push
- **Integration tests**: Run on every PR and push with MeiliSearch service
- **Performance tests**: Run only on main branch pushes
- **Production tests**: Run during staging/production deployments

## Deployment Structure Integration

The workflows reference the new deployment directory structure:

```
deployment/
├── docker/        # Docker configurations
├── k8s/          # Kubernetes manifests
├── environments/ # Environment-specific configs
└── scripts/      # Deployment scripts
```

## Configuration Files

### pytest Configuration
The workflows use the updated pytest configuration in `pyproject.toml`:
- Explicit test paths for each directory
- Coverage reporting with XML output
- Test markers for different test types

### Docker Configuration  
- Development builds use `deployment/docker/Dockerfile`
- Production builds use `deployment/docker/Dockerfile.prod`
- Multi-architecture builds (amd64, arm64)

## Monitoring and Reporting

### Coverage Reporting
- Unit test coverage uploaded to Codecov
- HTML coverage reports stored as artifacts
- XML coverage for external tools

### Performance Monitoring
- Nightly performance benchmarks
- Comparison with baseline metrics
- Performance regression detection

### Security Scanning
- Dependency vulnerability scanning with Safety
- Container vulnerability scanning with Trivy
- Security results uploaded to GitHub Security tab

## Usage Examples

### Running Specific Test Types
```bash
# Run only unit tests
pytest tests/unit/

# Run only integration tests  
pytest tests/integration/

# Run performance tests
pytest tests/performance/
```

### Manual Workflow Triggers
- Deploy workflow can be triggered manually via GitHub UI
- Maintenance workflow can be run on-demand
- All workflows support workflow_dispatch for manual execution

## Troubleshooting

### Common Issues
1. **Test failures**: Check test logs in the CI workflow
2. **Docker build failures**: Verify Dockerfile paths in `deployment/docker/`
3. **Deployment failures**: Check environment secrets and configurations
4. **Performance regressions**: Review performance comparison reports

### Debugging
- All workflows include verbose output (`-v` flag for pytest)
- Artifacts are uploaded for debugging (coverage, performance reports)
- Container logs are available in workflow outputs