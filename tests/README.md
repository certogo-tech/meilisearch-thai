# Testing Documentation

This directory contains the comprehensive test suite for the Thai Tokenizer project, organized by test type and purpose.

## 🧪 Test Organization

### 📋 Test Categories

#### `unit/` - Unit Tests
**Purpose**: Test individual components in isolation
- **Focus**: Single functions, classes, or modules
- **Dependencies**: Mocked or stubbed external dependencies
- **Speed**: Fast execution (< 1 second per test)
- **Coverage**: High code coverage for business logic

**Key Test Files:**
- `test_thai_segmenter.py` - Thai tokenization logic tests
- `test_meilisearch_client.py` - MeiliSearch client tests
- `test_api_endpoints.py` - API endpoint unit tests
- `test_config_manager.py` - Configuration management tests
- `test_token_processor.py` - Token processing utilities tests

#### `integration/` - Integration Tests
**Purpose**: Test component interactions and workflows
- **Focus**: Multiple components working together
- **Dependencies**: Real or containerized external services
- **Speed**: Moderate execution (1-10 seconds per test)
- **Coverage**: Critical integration points and data flows

**Key Test Files:**
- `test_end_to_end.py` - Complete workflow validation
- `test_meilisearch_integration.py` - MeiliSearch integration tests
- `test_full_system_integration.py` - System-wide integration tests

#### `performance/` - Performance Tests
**Purpose**: Validate system performance and scalability
- **Focus**: Response times, throughput, and resource usage
- **Dependencies**: Production-like environment setup
- **Speed**: Longer execution (10+ seconds per test)
- **Coverage**: Performance SLA validation

**Key Test Files:**
- `load_test.py` - Load testing scenarios
- `functional_test.py` - Functional performance validation
- `manual_performance_test.py` - Manual performance testing tools

#### `production/` - Production Validation Tests
**Purpose**: Validate production readiness and deployment
- **Focus**: Production environment validation
- **Dependencies**: Production or production-like environment
- **Speed**: Variable execution time
- **Coverage**: Deployment validation and health checks

**Key Test Files:**
- `production_test.py` - Production readiness validation

## 🚀 Running Tests

### Prerequisites
```bash
# Install dependencies
uv pip install -r requirements.txt

# Ensure services are running (for integration tests)
docker compose up -d
```

### Running Test Suites

#### All Tests
```bash
# Run complete test suite
uv run pytest tests/ -v

# Run with coverage report
uv run pytest tests/ -v --cov=src --cov-report=html
```

#### By Test Type
```bash
# Unit tests only (fast)
uv run pytest tests/unit/ -v

# Integration tests only
uv run pytest tests/integration/ -v

# Performance tests only
uv run pytest tests/performance/ -v

# Production validation tests
uv run pytest tests/production/ -v
```

#### Specific Test Categories
```bash
# Thai tokenization tests
uv run pytest tests/unit/test_thai_segmenter.py -v

# API endpoint tests
uv run pytest tests/unit/test_api_endpoints.py -v

# MeiliSearch integration tests
uv run pytest tests/integration/test_meilisearch_integration.py -v
```

### Test Configuration

#### Pytest Configuration
Test configuration is managed in `pyproject.toml`:
- Test discovery patterns
- Coverage settings
- Test markers and categories
- Async test support

#### Environment Setup
- **Development**: Uses local configuration from `config/development/`
- **Testing**: Uses testing configuration from `config/testing/`
- **CI/CD**: Uses containerized services for consistent testing

## 📊 Test Data and Fixtures

### Thai Text Samples
Located in `../data/samples/`:
- `thai_documents.json` - Comprehensive Thai document samples
- `test_queries.json` - Thai search query test cases
- `formal_documents.json` - Formal Thai text samples
- `informal_documents.json` - Informal Thai text samples

### Test Fixtures
- Shared test fixtures are defined in `conftest.py` files
- Thai text fixtures for consistent tokenization testing
- Mock MeiliSearch responses for unit testing
- Performance test data sets

## 🎯 Testing Best Practices

### Writing Tests
1. **Follow AAA Pattern**: Arrange, Act, Assert
2. **Use Descriptive Names**: Test names should describe the scenario
3. **Test One Thing**: Each test should validate a single behavior
4. **Use Fixtures**: Leverage pytest fixtures for setup and teardown
5. **Mock External Dependencies**: Use mocks for external services in unit tests

### Thai Text Testing
1. **Use Real Thai Text**: Test with actual Thai language samples
2. **Test Edge Cases**: Include complex Thai characters and compound words
3. **Validate Encoding**: Ensure proper UTF-8 handling
4. **Test Mixed Content**: Include Thai-English mixed text scenarios

### Performance Testing
1. **Set Clear SLAs**: Define performance expectations
2. **Use Realistic Data**: Test with production-like data volumes
3. **Monitor Resources**: Track CPU, memory, and network usage
4. **Test Scalability**: Validate performance under load

## 📈 Test Reporting

### Coverage Reports
```bash
# Generate HTML coverage report
uv run pytest tests/ --cov=src --cov-report=html

# View coverage report
open htmlcov/index.html
```

### Performance Reports
Performance test results are saved to `../reports/performance/`:
- Execution time metrics
- Resource usage statistics
- Throughput measurements
- Performance trend analysis

### Test Execution Reports
Test execution reports are saved to `../reports/testing/`:
- Test execution summaries
- Integration test results
- Failure analysis and debugging information

## 🔧 Continuous Integration

### GitHub Actions
Tests are automatically executed in CI/CD pipeline:
- **Unit Tests**: Run on every pull request
- **Integration Tests**: Run on main branch commits
- **Performance Tests**: Run on release candidates
- **Production Tests**: Run during deployment validation

### Test Environment
- **Containerized Services**: MeiliSearch and dependencies run in containers
- **Isolated Testing**: Each test run uses fresh environment
- **Parallel Execution**: Tests run in parallel for faster feedback

## 🆘 Troubleshooting

### Common Issues

#### Test Failures
1. **Service Dependencies**: Ensure MeiliSearch is running for integration tests
2. **Thai Text Encoding**: Verify UTF-8 encoding in test files
3. **Async Tests**: Use proper async test decorators and fixtures

#### Performance Test Issues
1. **Resource Constraints**: Ensure adequate system resources
2. **Network Latency**: Account for network delays in timing assertions
3. **Data Consistency**: Use consistent test data for reliable results

#### Environment Issues
1. **Configuration**: Verify test environment configuration
2. **Dependencies**: Ensure all test dependencies are installed
3. **Permissions**: Check file and directory permissions

### Getting Help
- **Test Documentation**: Review test-specific documentation in each directory
- **Development Guide**: Check `../docs/development/README.md` for setup help
- **Troubleshooting Guide**: See `../docs/troubleshooting.md` for common issues

---

**Ready to run tests?** Start with `uv run pytest tests/unit/ -v` for a quick validation, then explore integration and performance tests as needed.