# Backups Directory

This directory contains project backups, snapshots, and recovery files for the Thai Tokenizer project. Regular backups ensure data protection and enable quick recovery from issues.

## 📁 Directory Purpose

### Backup Types
- **Project Snapshots**: Complete project state backups
- **Configuration Backups**: Environment and application settings
- **Data Backups**: Sample data, fixtures, and user data
- **Database Backups**: MeiliSearch index and configuration backups
- **SSL Certificate Backups**: Security certificates and keys

## 🗂️ Backup Organization

### File Naming Convention
```
backup-type-YYYYMMDD-HHMMSS.extension

Examples:
- project-backup-20240115-143022.tar.gz
- config-backup-20240115-090000.tar.gz
- meilisearch-backup-20240115-120000.tar.gz
- ssl-backup-20240115-060000.tar.gz
```

### Backup Categories

#### Project Backups
**Purpose**: Complete project state snapshots
- Full source code backup
- Configuration files
- Documentation
- Build artifacts

#### Configuration Backups
**Purpose**: Environment and application settings
- Environment configuration files
- Docker compose configurations
- Nginx configurations
- Application settings

#### Data Backups
**Purpose**: Application data and samples
- Thai text samples
- Test fixtures
- Benchmark data
- User-generated content

#### Service Backups
**Purpose**: External service data
- MeiliSearch indexes
- Database dumps
- Cache snapshots
- Log archives

## 🔄 Backup Schedule

### Automated Backups
```bash
# Daily project backup (automated via cron)
0 2 * * * /path/to/project/deployment/scripts/backup_project.sh

# Weekly configuration backup
0 3 * * 0 /path/to/project/deployment/scripts/backup_config.sh

# Monthly full system backup
0 1 1 * * /path/to/project/deployment/scripts/backup_full.sh
```

### Manual Backup Commands
```bash
# Create project backup
./deployment/scripts/backup_project.sh

# Create configuration backup
tar -czf backups/config-backup-$(date +%Y%m%d-%H%M%S).tar.gz config/

# Create data backup
tar -czf backups/data-backup-$(date +%Y%m%d-%H%M%S).tar.gz data/

# Create MeiliSearch backup
curl -X POST "http://localhost:7700/dumps" -H "Authorization: Bearer YOUR_API_KEY"
```

## 💾 Backup Creation

### Project Backup Script
```bash
#!/bin/bash
# backup_project.sh

BACKUP_DATE=$(date +%Y%m%d-%H%M%S)
BACKUP_NAME="project-backup-${BACKUP_DATE}.tar.gz"
BACKUP_PATH="backups/${BACKUP_NAME}"

# Create backup excluding unnecessary files
tar -czf "${BACKUP_PATH}" \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  --exclude='.git' \
  --exclude='logs/*' \
  --exclude='backups/*' \
  --exclude='htmlcov' \
  --exclude='.pytest_cache' \
  .

echo "Backup created: ${BACKUP_PATH}"
echo "Backup size: $(du -h ${BACKUP_PATH} | cut -f1)"
```

### Service-Specific Backups
```bash
# MeiliSearch backup
#!/bin/bash
MEILISEARCH_URL="http://localhost:7700"
API_KEY="YOUR_API_KEY"
BACKUP_DATE=$(date +%Y%m%d-%H%M%S)

# Create dump
DUMP_UID=$(curl -s -X POST "${MEILISEARCH_URL}/dumps" \
  -H "Authorization: Bearer ${API_KEY}" | jq -r '.taskUid')

# Wait for dump completion
while true; do
  STATUS=$(curl -s "${MEILISEARCH_URL}/tasks/${DUMP_UID}" \
    -H "Authorization: Bearer ${API_KEY}" | jq -r '.status')
  
  if [ "$STATUS" = "succeeded" ]; then
    break
  elif [ "$STATUS" = "failed" ]; then
    echo "Backup failed"
    exit 1
  fi
  
  sleep 5
done

# Move dump to backups directory
mv dumps/*.dump "backups/meilisearch-backup-${BACKUP_DATE}.dump"
```

## 🔄 Backup Restoration

### Project Restoration
```bash
# Extract project backup
tar -xzf backups/project-backup-20240115-143022.tar.gz

# Restore specific directory
tar -xzf backups/project-backup-20240115-143022.tar.gz config/

# Restore with verification
tar -tzf backups/project-backup-20240115-143022.tar.gz | head -20
```

### Configuration Restoration
```bash
# Restore configuration files
tar -xzf backups/config-backup-20240115-090000.tar.gz

# Restore specific environment config
tar -xzf backups/config-backup-20240115-090000.tar.gz config/production/

# Verify configuration after restore
./deployment/scripts/validate_config.sh
```

### Service Data Restoration
```bash
# Restore MeiliSearch from dump
curl -X POST "http://localhost:7700/dumps/import" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/octet-stream" \
  --data-binary @backups/meilisearch-backup-20240115-120000.dump

# Restore data directory
tar -xzf backups/data-backup-20240115-100000.tar.gz
```

## 🔒 Backup Security

### Encryption
```bash
# Encrypt backup with GPG
gpg --cipher-algo AES256 --compress-algo 1 --s2k-cipher-algo AES256 \
    --s2k-digest-algo SHA512 --s2k-mode 3 --s2k-count 65536 \
    --force-mdc --encrypt -r backup@company.com \
    backups/project-backup-20240115-143022.tar.gz

# Decrypt backup
gpg --decrypt backups/project-backup-20240115-143022.tar.gz.gpg > \
    backups/project-backup-20240115-143022.tar.gz
```

### Access Control
```bash
# Set proper permissions for backup directory
chmod 700 backups/
chmod 600 backups/*.tar.gz

# Restrict access to backup user only
chown -R backup:backup backups/
```

### Integrity Verification
```bash
# Create checksums for backups
sha256sum backups/*.tar.gz > backups/checksums.sha256

# Verify backup integrity
sha256sum -c backups/checksums.sha256

# Create backup manifest
#!/bin/bash
BACKUP_FILE="$1"
echo "Backup: ${BACKUP_FILE}" > "${BACKUP_FILE}.manifest"
echo "Created: $(date)" >> "${BACKUP_FILE}.manifest"
echo "Size: $(du -h ${BACKUP_FILE} | cut -f1)" >> "${BACKUP_FILE}.manifest"
echo "SHA256: $(sha256sum ${BACKUP_FILE} | cut -d' ' -f1)" >> "${BACKUP_FILE}.manifest"
```

## ☁️ Remote Backup Storage

### Cloud Storage Integration
```bash
# AWS S3 backup
aws s3 cp backups/project-backup-20240115-143022.tar.gz \
    s3://your-backup-bucket/thai-tokenizer/

# Google Cloud Storage backup
gsutil cp backups/project-backup-20240115-143022.tar.gz \
    gs://your-backup-bucket/thai-tokenizer/

# Azure Blob Storage backup
az storage blob upload \
    --account-name yourstorageaccount \
    --container-name backups \
    --name thai-tokenizer/project-backup-20240115-143022.tar.gz \
    --file backups/project-backup-20240115-143022.tar.gz
```

### Backup Synchronization
```bash
# Rsync to remote server
rsync -avz --delete backups/ backup-server:/backups/thai-tokenizer/

# Automated remote backup
#!/bin/bash
BACKUP_FILE="$1"
REMOTE_HOST="backup-server"
REMOTE_PATH="/backups/thai-tokenizer/"

# Upload backup
scp "${BACKUP_FILE}" "${REMOTE_HOST}:${REMOTE_PATH}"

# Verify upload
ssh "${REMOTE_HOST}" "sha256sum ${REMOTE_PATH}$(basename ${BACKUP_FILE})"
```

## 🧹 Backup Maintenance

### Cleanup and Retention
```bash
# Keep only last 30 days of daily backups
find backups/ -name "project-backup-*.tar.gz" -mtime +30 -delete

# Keep only last 12 weekly backups
find backups/ -name "*-backup-*" -mtime +84 -delete

# Automated cleanup script
#!/bin/bash
# cleanup_backups.sh

# Daily backups: keep 30 days
find backups/ -name "*backup-*" -mtime +30 -type f -delete

# Weekly backups: keep 12 weeks
find backups/ -name "*weekly-*" -mtime +84 -type f -delete

# Monthly backups: keep 12 months
find backups/ -name "*monthly-*" -mtime +365 -type f -delete

echo "Backup cleanup completed: $(date)"
```

### Backup Monitoring
```bash
# Check backup health
#!/bin/bash
BACKUP_DIR="backups"
LATEST_BACKUP=$(ls -t ${BACKUP_DIR}/project-backup-*.tar.gz | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No backups found"
    exit 1
fi

# Check if backup is recent (within 24 hours)
BACKUP_AGE=$(stat -c %Y "$LATEST_BACKUP")
CURRENT_TIME=$(date +%s)
AGE_HOURS=$(( (CURRENT_TIME - BACKUP_AGE) / 3600 ))

if [ $AGE_HOURS -gt 24 ]; then
    echo "WARNING: Latest backup is ${AGE_HOURS} hours old"
fi

# Verify backup integrity
if tar -tzf "$LATEST_BACKUP" > /dev/null 2>&1; then
    echo "OK: Latest backup is valid"
else
    echo "ERROR: Latest backup is corrupted"
    exit 1
fi
```

## 🚨 Disaster Recovery

### Recovery Procedures
```bash
# Emergency project restoration
#!/bin/bash
# emergency_restore.sh

BACKUP_FILE="$1"
RESTORE_DIR="/tmp/emergency-restore"

if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file>"
    exit 1
fi

# Create restore directory
mkdir -p "$RESTORE_DIR"
cd "$RESTORE_DIR"

# Extract backup
tar -xzf "$BACKUP_FILE"

# Restore services
docker compose down
docker compose up -d

echo "Emergency restoration completed"
```

### Recovery Testing
```bash
# Test backup restoration (monthly)
#!/bin/bash
TEST_DIR="/tmp/backup-test-$(date +%Y%m%d)"
LATEST_BACKUP=$(ls -t backups/project-backup-*.tar.gz | head -1)

mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

# Extract and test backup
tar -xzf "$LATEST_BACKUP"
docker compose -f docker-compose.yml config --quiet

if [ $? -eq 0 ]; then
    echo "Backup restoration test: PASSED"
else
    echo "Backup restoration test: FAILED"
fi

# Cleanup test directory
rm -rf "$TEST_DIR"
```

## 📋 Backup Checklist

### Daily Tasks
- [ ] Verify automated backup completion
- [ ] Check backup file integrity
- [ ] Monitor backup storage space
- [ ] Review backup logs for errors

### Weekly Tasks
- [ ] Test backup restoration procedure
- [ ] Clean up old backup files
- [ ] Verify remote backup synchronization
- [ ] Update backup documentation

### Monthly Tasks
- [ ] Full disaster recovery test
- [ ] Review backup retention policies
- [ ] Audit backup security measures
- [ ] Update backup procedures

## 🔗 Related Documentation

- **[Deployment Scripts](../deployment/scripts/README.md)** - Automated backup scripts
- **[Production Deployment](../docs/deployment/PRODUCTION_DEPLOYMENT.md)** - Production backup setup
- **[Monitoring Setup](../monitoring/index.md)** - Backup monitoring configuration
- **[Security Guide](../docs/security.md)** - Backup security best practices

---

**Need to restore from backup?** Follow the restoration procedures above or check the [Disaster Recovery Guide](../docs/disaster-recovery.md) for detailed instructions.