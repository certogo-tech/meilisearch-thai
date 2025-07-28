# Demonstration Scripts

This directory contains scripts to demonstrate and benchmark the Thai Tokenizer for MeiliSearch integration.

## Scripts Overview

### 1. `run_demo.py` - Main Demo Runner
**Purpose**: Orchestrates the complete demonstration suite  
**Usage**: `python deployment/scripts/run_demo.py`

**Features**:
- Checks service availability
- Runs all demonstration scripts in sequence
- Provides comprehensive error handling and logging
- Supports selective execution of demo components

**Options**:
```bash
python deployment/scripts/run_demo.py --help
python deployment/scripts/run_demo.py --skip-setup          # Skip data setup
python deployment/scripts/run_demo.py --skip-comparison     # Skip search comparison
python deployment/scripts/run_demo.py --skip-benchmark      # Skip performance tests
```

### 2. `setup_demo.py` - Demo Data Setup
**Purpose**: Populates MeiliSearch with sample Thai documents  
**Usage**: `python deployment/scripts/setup_demo.py`

**Features**:
- Loads sample documents from `data/samples/` directory
- Preprocesses documents with Thai tokenization
- Configures MeiliSearch index for optimal Thai search
- Runs sample searches to verify functionality

**What it does**:
1. Loads Thai documents from JSON files
2. Tokenizes Thai text using PyThaiNLP
3. Creates optimized MeiliSearch index configuration
4. Populates index with processed documents
5. Runs sample searches to demonstrate functionality

### 3. `compare_results.py` - Search Comparison
**Purpose**: Compares search results before/after Thai tokenization  
**Usage**: `python deployment/scripts/compare_results.py`

**Features**:
- Creates two indexes: original and tokenized
- Runs identical queries against both indexes
- Calculates improvement scores and relevance metrics
- Generates detailed comparison report

**Comparison Metrics**:
- Number of search results
- Search relevance accuracy
- Processing time performance
- Result highlighting quality

**Output**: `comparison_report.json` with detailed analysis

### 4. `benchmark.py` - Performance Benchmarking
**Purpose**: Measures system performance against requirements  
**Usage**: `python deployment/scripts/benchmark.py`

**Benchmarks**:
- **Tokenization Speed**: Direct PyThaiNLP performance
- **API Performance**: HTTP API response times with concurrency
- **Indexing Throughput**: Document processing and indexing speed
- **Search Performance**: Query response times and throughput

**Performance Targets**:
- Tokenization: < 50ms for 1000 characters
- Search response: < 100ms for typical queries
- Memory usage: < 256MB per container
- Indexing throughput: > 500 documents/second

**Output**: `benchmark_report.json` with detailed metrics

### 5. `demo_thai_tokenizer.py` - Interactive Demonstrations
**Purpose**: Interactive demonstrations of Thai tokenizer capabilities  
**Usage**: `python deployment/scripts/demo_thai_tokenizer.py`

**Features**:
- Basic Thai tokenization examples
- Compound word handling demonstrations
- Mixed Thai-English content processing
- Search query processing examples
- Performance comparisons
- Real-world usage scenarios

**Demonstrations**:
- Simple Thai text tokenization
- Complex compound word segmentation
- Mixed language content handling
- Search query enhancement
- Performance benchmarking
- Real-world text examples (news, academic, business, government)

## Prerequisites

### Required Services
```bash
# Start services with Docker Compose
docker-compose up -d

# Verify services are running
curl http://localhost:7700/health  # MeiliSearch
curl http://localhost:8000/health  # Thai Tokenizer (optional)
```

### Python Dependencies
```bash
# Install script dependencies
pip install -r deployment/scripts/requirements.txt

# Or install main project dependencies
pip install -r requirements.txt
```

### Sample Data
Ensure sample data files exist in `data/samples/`:
- `thai_documents.json`
- `formal_documents.json`
- `informal_documents.json`
- `test_queries.json`

## Quick Start

### Complete Demo (Recommended)
```bash
# Run full demonstration suite
python deployment/scripts/run_demo.py
```

### Individual Scripts
```bash
# 1. Set up demo data
python deployment/scripts/setup_demo.py

# 2. Run interactive demonstrations
python deployment/scripts/demo_thai_tokenizer.py

# 3. Compare search results
python deployment/scripts/compare_results.py

# 4. Run performance benchmarks
python deployment/scripts/benchmark.py

# 5. Run comprehensive system tests
python tests/integration/test_comprehensive_system.py
```

### Custom Configuration
```bash
# Use different MeiliSearch instance
python deployment/scripts/run_demo.py --meilisearch-host http://remote:7700 --api-key mykey

# Skip certain components
python deployment/scripts/run_demo.py --skip-benchmark
```

## Expected Output

### Demo Setup
- Loads and processes 20+ Thai documents
- Creates optimized MeiliSearch index
- Runs sample searches with results

### Search Comparison
- Compares original vs tokenized search results
- Shows improvement in compound word matching
- Generates detailed analysis report

### Performance Benchmark
- Measures tokenization speed (target: <50ms)
- Tests search performance (target: <100ms)
- Validates memory usage (target: <256MB)
- Assesses indexing throughput (target: >500/s)

## Troubleshooting

### Common Issues

**Services Not Available**
```bash
# Check service status
docker-compose ps

# View service logs
docker-compose logs meilisearch
docker-compose logs thai-tokenizer
```

**Missing Sample Data**
```bash
# Verify sample data files exist
ls -la data/samples/
```

**Permission Errors**
```bash
# Make scripts executable
chmod +x deployment/scripts/*.py
```

**Import Errors**
```bash
# Ensure src/ is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Performance Issues

**Slow Tokenization**
- Check PyThaiNLP model loading
- Verify system resources (CPU, memory)
- Consider using smaller document samples

**Search Timeouts**
- Increase timeout values in scripts
- Check MeiliSearch index status
- Verify network connectivity

**Memory Issues**
- Reduce batch sizes in scripts
- Monitor system memory usage
- Consider running scripts individually

## Customization

### Adding New Test Cases
1. Add documents to `data/samples/` JSON files
2. Add queries to `test_queries.json`
3. Update expected results in query metadata

### Modifying Benchmarks
1. Edit benchmark parameters in `benchmark.py`
2. Adjust performance targets as needed
3. Add new benchmark categories

### Custom Index Configuration
1. Modify index settings in `setup_demo.py`
2. Add custom synonyms or stop words
3. Adjust ranking rules for specific use cases

## Integration with CI/CD

### Automated Testing
```bash
# Run in CI environment
python deployment/scripts/run_demo.py --skip-benchmark

# Generate reports for analysis
python deployment/scripts/compare_results.py
python deployment/scripts/benchmark.py
```

### Performance Monitoring
- Use benchmark results for performance regression testing
- Set up alerts for performance threshold violations
- Track improvement metrics over time

## Contributing

When adding new demonstration scripts:
1. Follow the existing error handling patterns
2. Include comprehensive logging
3. Add command-line argument support
4. Update this README with usage instructions
5. Test with various Thai text samples