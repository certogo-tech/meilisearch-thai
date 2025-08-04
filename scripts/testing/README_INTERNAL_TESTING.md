# Internal API Testing Scripts

This directory contains testing scripts for the Thai tokenizer service with two variants:

## Scripts

### `test-researcher-index.sh` (Original)
- Uses external API calls to `search.cads.arda.or.th`
- Tests the production/staging environment
- Requires direct network access to the external service

### `test-researcher-index-internal.sh` (Internal Version) 
- Uses internal API calls to `localhost:8000`
- Tests the local development environment
- Requires the Thai tokenizer service to be running locally

## Usage

### Running the Internal Version

1. **Start the local Thai tokenizer service first:**
   ```bash
   # Option 1: Direct Python execution
   python -m uvicorn src.api.main:app --host 0.0.0.0 --port 8000
   
   # Option 2: Using startup script
   ./scripts/start_api_with_compounds.py
   
   # Option 3: Using Docker Compose
   docker-compose up thai-tokenizer
   ```

2. **Run the test script:**
   ```bash
   ./scripts/testing/test-researcher-index-internal.sh [index_name]
   ```

### Key Differences

| Feature | Original Script | Internal Script |
|---------|----------------|-----------------|
| API Endpoint | `https://search.cads.arda.or.th` | `http://localhost:8000` |
| Environment | Production/Staging | Local Development |
| Pre-requisites | Network access to external service | Local service running |
| Use Case | Production testing | Development & debugging |

### Pre-flight Checks

The internal script includes automatic checks to ensure:
- Local Thai tokenizer service is accessible
- Service health endpoint responds correctly
- Proper error messages if service is not running

### Configuration

Both scripts use the same MeiliSearch configuration:
- Host: `http://10.0.2.105:7700`
- API Key: From environment configuration
- Default index: `research` (can be overridden)

## Troubleshooting

If the internal script fails with connection errors:

1. Verify the local service is running on port 8000
2. Check firewall settings for localhost access
3. Ensure all dependencies are installed
4. Check service logs for startup errors

