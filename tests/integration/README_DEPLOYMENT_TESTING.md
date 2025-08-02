# Deployment Integration Testing

This directory contains comprehensive integration tests for the Thai Tokenizer on-premise deployment system. The tests cover all deployment methods (Docker, systemd, standalone) and validate functionality, performance, and security.

## Test Structure

### Integration Tests
- `test_on_premise_deployment_integration.py` - End-to-end deployment testing for all methods
- `test_deployment_orchestration.py` - Deployment manager and orchestration testing
- `test_deployment_security.py` - Security and authentication testing
- `test_deployment_validation_reporting.py` - Validation framework and reporting

### Performance Tests
- `../performance/test_deployment_performance.py` - Performance and load testing

## Running Tests

### Quick Test Execution

Use the test runner script for convenient test execution:

```bash
# Run all deployment tests
python scripts/run_deployment_tests.py --test-type all --verbose

# Run only integration tests
python scripts/run_deployment_tests.py --test-type integration

# Run only performance tests
python scripts/run_deployment_tests.py --test-type performance

# Run only security tests
python scripts/run_deployment_tests.py --test-type security

# Run validation and reporting tests
python scripts/run_deployment_tests.py --test-type validation
```

### Direct pytest Execution

You can also run tests directly with pytest:

```bash
# Run specific test file
pytest tests/integration/test_on_premise_deployment_integration.py -v

# Run all integration tests
pytest tests/integration/ -v

# Run with coverage
pytest tests/integration/ --cov=src --cov-report=html

# Run with JSON report
pytest tests/integration/ --json-report --json-report-file=test_results.json
```

### CI Pipeline Testing

For continuous integration environments, use the CI testing script:

```bash
# Create a deployment configuration file
cat > deployment_config.json << EOF
{
  "deployment_method": "docker",
  "meilisearch_config": {
    "host": "http://localhost:7700",
    "port": 7700,
    "api_key": "test-key"
  },
  "service_config": {
    "service_name": "thai-tokenizer-ci",
    "service_port": 8000
  }
}
EOF

# Run CI pipeline
python scripts/ci_deployment_testing.py --config deployment_config.json --output-dir ci_results
```

## Test Categories

### 1. End-to-End Integration Tests

**File**: `test_on_premise_deployment_integration.py`

Tests complete deployment workflows for each deployment method:
- Docker deployment with external Meilisearch
- systemd service deployment
- Standalone Python deployment
- Thai tokenization workflow validation
- Performance benchmarking
- Security feature testing

**Key Test Cases**:
- `test_docker_deployment_integration()` - Complete Docker deployment flow
- `test_systemd_deployment_integration()` - Complete systemd deployment flow
- `test_standalone_deployment_integration()` - Complete standalone deployment flow
- `test_load_testing_simulation()` - Concurrent request testing
- `test_deployment_method_factory_comprehensive()` - Factory pattern validation

### 2. Performance Testing

**File**: `../performance/test_deployment_performance.py`

Validates performance requirements and load handling:
- Single request response time (< 50ms target)
- Concurrent load testing
- Sustained load testing
- Spike load testing
- Memory usage monitoring
- Thai tokenization accuracy under load

**Key Test Cases**:
- `test_single_request_performance()` - Response time validation
- `test_concurrent_load_performance()` - Concurrent user simulation
- `test_sustained_load_performance()` - Extended load testing
- `test_spike_load_performance()` - Sudden load increase testing
- `test_thai_tokenization_accuracy_under_load()` - Accuracy validation

### 3. Security Testing

**File**: `test_deployment_security.py`

Validates security configurations and measures:
- CORS configuration testing
- API key authentication
- Rate limiting validation
- HTTPS/TLS configuration
- Input validation and sanitization
- Security headers verification

**Key Test Cases**:
- `test_cors_security_basic()` - CORS policy validation
- `test_api_key_authentication_strict()` - Authentication testing
- `test_rate_limiting_security()` - Rate limiting validation
- `test_input_validation_security()` - Input sanitization testing
- `test_comprehensive_security_audit()` - Complete security audit

### 4. Validation and Reporting

**File**: `test_deployment_validation_reporting.py`

Tests the validation framework and report generation:
- System requirements validation
- Deployment method validation
- Meilisearch connectivity testing
- Thai tokenization validation
- Performance benchmarking
- Report generation (JSON, HTML, Markdown)

**Key Test Cases**:
- `test_validation_runner_execution()` - Validation framework testing
- `test_report_generation_json()` - JSON report generation
- `test_report_generation_html()` - HTML report generation
- `test_report_generation_markdown()` - Markdown report generation

## Test Configuration

### Environment Variables

Set these environment variables to customize test behavior:

```bash
# Meilisearch configuration
export MEILISEARCH_HOST="http://localhost:7700"
export MEILISEARCH_API_KEY="your-api-key"

# Service configuration
export THAI_TOKENIZER_SERVICE_PORT="8000"
export THAI_TOKENIZER_MEMORY_LIMIT="256"

# Test configuration
export CI_CLEANUP_DEPLOYMENT="true"  # Cleanup after CI tests
export TEST_TIMEOUT_SECONDS="300"    # Test timeout
```

### Configuration Files

Create deployment configuration files for different scenarios:

**Docker Configuration** (`config/test_docker.json`):
```json
{
  "deployment_method": "docker",
  "meilisearch_config": {
    "host": "http://localhost:7700",
    "port": 7700,
    "api_key": "test-docker-key"
  },
  "service_config": {
    "service_name": "thai-tokenizer-docker-test",
    "service_port": 8002
  },
  "security_config": {
    "security_level": "standard",
    "cors_origins": ["http://localhost:3000"]
  }
}
```

**Systemd Configuration** (`config/test_systemd.json`):
```json
{
  "deployment_method": "systemd",
  "meilisearch_config": {
    "host": "http://localhost:7700",
    "port": 7700,
    "api_key": "test-systemd-key"
  },
  "service_config": {
    "service_name": "thai-tokenizer-systemd-test",
    "service_port": 8003
  },
  "security_config": {
    "security_level": "strict",
    "api_key_required": true
  }
}
```

## Test Data

### Thai Test Samples

Tests use Thai text samples from `data/samples/thai_documents.json`:
- Basic Thai text
- Compound words (สาหร่ายวากาเมะ)
- Mixed Thai-English content
- Technical terminology
- Various difficulty levels

### Performance Test Data

Performance tests use realistic Thai text samples:
- Short phrases (< 50 characters)
- Medium sentences (50-200 characters)
- Long paragraphs (200+ characters)
- Mixed content with English terms

## Expected Results

### Performance Targets
- **Response Time**: < 50ms for 1000 Thai characters
- **Memory Usage**: < 256MB per service instance
- **Throughput**: > 500 documents/second for batch processing
- **Concurrent Requests**: Handle 50+ concurrent requests

### Security Requirements
- **Input Validation**: Reject malformed inputs
- **Authentication**: Support API key authentication
- **CORS**: Configurable CORS policies
- **Rate Limiting**: Prevent abuse with rate limiting

### Deployment Success Criteria
- **Service Health**: All health endpoints respond correctly
- **Thai Tokenization**: Accurate tokenization of Thai text
- **Meilisearch Integration**: Successful connection and operations
- **Resource Usage**: Within configured limits

## Troubleshooting

### Common Issues

1. **Meilisearch Connection Failures**
   ```bash
   # Check Meilisearch is running
   curl http://localhost:7700/health
   
   # Verify API key
   curl -H "Authorization: Bearer your-api-key" http://localhost:7700/version
   ```

2. **Port Conflicts**
   ```bash
   # Check port availability
   netstat -tlnp | grep :8000
   
   # Use different port in configuration
   ```

3. **Permission Issues (systemd tests)**
   ```bash
   # Run with sudo for systemd tests
   sudo python -m pytest tests/integration/test_deployment_security.py
   ```

4. **Docker Issues**
   ```bash
   # Check Docker daemon
   docker info
   
   # Check Docker Compose
   docker compose version
   ```

### Test Debugging

Enable verbose logging for debugging:

```bash
# Enable debug logging
export PYTHONPATH=src
export LOG_LEVEL=DEBUG

# Run specific test with verbose output
pytest tests/integration/test_on_premise_deployment_integration.py::TestOnPremiseDeploymentIntegration::test_docker_deployment_integration -v -s
```

### Mock Testing

Tests use extensive mocking to avoid external dependencies:
- HTTP clients are mocked for API calls
- System commands are mocked for deployment operations
- File operations are mocked for configuration management

To run tests without mocking (integration mode):
```bash
export INTEGRATION_TEST_MODE=true
pytest tests/integration/ -v
```

## Contributing

When adding new deployment tests:

1. **Follow Test Structure**: Use the existing test class patterns
2. **Add Mocking**: Mock external dependencies appropriately
3. **Include Documentation**: Document test purpose and expected behavior
4. **Test All Methods**: Ensure tests work for Docker, systemd, and standalone
5. **Performance Validation**: Include performance assertions where relevant
6. **Security Checks**: Validate security configurations and measures

### Test Naming Convention

- `test_<deployment_method>_<functionality>()` - Method-specific tests
- `test_<functionality>_<scenario>()` - General functionality tests
- `test_<component>_validation()` - Validation tests
- `test_<feature>_security()` - Security tests

### Assertion Guidelines

- Use descriptive assertion messages
- Validate both success and failure scenarios
- Check performance metrics against requirements
- Verify security configurations
- Test error handling and recovery