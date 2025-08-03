# Production Server Fix Commands

## Quick Fix (One-liner)

Run this command on the production server to fix the Meilisearch host configuration:

```bash
# Backup and update the Meilisearch host
cp .env.production .env.production.backup.$(date +%Y%m%d_%H%M%S) && \
sed -i 's|^MEILISEARCH_HOST=.*|MEILISEARCH_HOST=http://10.0.2.105:7700|' .env.production && \
echo "✅ Updated MEILISEARCH_HOST to http://10.0.2.105:7700"
```

## Verify the Change

```bash
# Check the updated configuration
grep "^MEILISEARCH_HOST=" .env.production
```

## Test Connectivity

```bash
# Test if Meilisearch is accessible
curl -s http://10.0.2.105:7700/health
```

## Restart the Service

```bash
# Option 1: Use the restart script (if available)
./restart-service.sh

# Option 2: Manual restart
docker-compose -f deployment/docker/docker-compose.npm.yml --env-file .env.production down && \
docker-compose -f deployment/docker/docker-compose.npm.yml --env-file .env.production up -d
```

## Verify the Fix

```bash
# Wait 30 seconds for startup, then check configuration health
sleep 30 && curl -s 'https://search.cads.arda.or.th/api/v1/health/check/configuration_validity'
```

## Expected Result

After the fix, you should see:
- `"status": "healthy"` in the configuration validity check
- The overall health status should change from "unhealthy" to "healthy"
- Meilisearch connection should show the correct IP address

## Rollback (if needed)

```bash
# If something goes wrong, restore from backup
cp .env.production.backup.* .env.production
docker-compose -f deployment/docker/docker-compose.npm.yml --env-file .env.production restart
```