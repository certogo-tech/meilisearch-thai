# Backup and Recovery Operations Guide

This comprehensive guide provides detailed procedures for backing up and recovering the Thai Tokenizer service, including configuration, data, and service state management.

## Table of Contents

1. [Backup Strategy Overview](#backup-strategy-overview)
2. [Configuration Backup](#configuration-backup)
3. [Service State Backup](#service-state-backup)
4. [Custom Dictionary Backup](#custom-dictionary-backup)
5. [Automated Backup Procedures](#automated-backup-procedures)
6. [Recovery Procedures](#recovery-procedures)
7. [Disaster Recovery](#disaster-recovery)
8. [Backup Validation and Testing](#backup-validation-and-testing)
9. [Backup Storage and Retention](#backup-storage-and-retention)
10. [Monitoring and Alerting](#monitoring-and-alerting)

## Backup Strategy Overview

### Backup Components

1. **Configuration Files**: Service configuration, environment variables, certificates
2. **Service State**: Process state, runtime data, temporary files
3. **Custom Dictionaries**: User-defined Thai word dictionaries and tokenization rules
4. **Logs**: Historical log files for troubleshooting and audit purposes
5. **Dependencies**: Virtual environment, installed packages, system dependencies

### Backup Types

- **Full Backup**: Complete system backup including all components
- **Incremental Backup**: Only changed files since last backup
- **Configuration Backup**: Configuration files and settings only
- **Hot Backup**: Backup while service is running
- **Cold Backup**: Backup while service is stopped

### Backup Schedule

```bash
# Recommended backup schedule
# Daily: Configuration and logs
# Weekly: Full service backup
# Monthly: Complete system backup with dependencies
```

## Configuration Backup

### Manual Configuration Backup

```bash
#!/bin/bash
# manual-config-backup.sh

BACKUP_DIR="/opt/thai-tokenizer/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
CONFIG_BACKUP_FILE="$BACKUP_DIR/config-backup-$TIMESTAMP.tar.gz"

echo "=== Configuration Backup - $(date) ==="

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create temporary directory for backup
TEMP_DIR=$(mktemp -d)
BACKUP_TEMP="$TEMP_DIR/config-backup"
mkdir -p "$BACKUP_TEMP"

# Copy configuration files
echo "Backing up configuration files..."
cp -r /opt/thai-tokenizer/config "$BACKUP_TEMP/"
cp -r /etc/thai-tokenizer "$BACKUP_TEMP/" 2>/dev/null || true

# Copy SSL certificates if they exist
if [ -d "/etc/ssl/thai-tokenizer" ]; then
    cp -r /etc/ssl/thai-tokenizer "$BACKUP_TEMP/"
fi

# Copy systemd service files
if [ -f "/etc/systemd/system/thai-tokenizer.service" ]; then
    mkdir -p "$BACKUP_TEMP/systemd"
    cp /etc/systemd/system/thai-tokenizer.service* "$BACKUP_TEMP/systemd/"
fi

# Copy Docker configuration
if [ -f "docker-compose.yml" ]; then
    cp docker-compose.yml "$BACKUP_TEMP/"
    cp .env "$BACKUP_TEMP/" 2>/dev/null || true
fi

# Create backup metadata
cat > "$BACKUP_TEMP/backup-metadata.json" << EOF
{
  "backup_type": "configuration",
  "timestamp": "$TIMESTAMP",
  "hostname": "$(hostname)",
  "service_version": "$(cat /opt/thai-tokenizer/VERSION 2>/dev/null || echo 'unknown')",
  "backup_size": "$(du -sh $BACKUP_TEMP | cut -f1)",
  "files_included": [
    "config/",
    "systemd/",
    "ssl/",
    "docker-compose.yml",
    ".env"
  ]
}
EOF

# Create compressed backup
echo "Creating compressed backup..."
tar -czf "$CONFIG_BACKUP_FILE" -C "$TEMP_DIR" config-backup

# Cleanup temporary directory
rm -rf "$TEMP_DIR"

# Verify backup
if [ -f "$CONFIG_BACKUP_FILE" ]; then
    echo "✓ Configuration backup created: $CONFIG_BACKUP_FILE"
    echo "  Size: $(du -sh $CONFIG_BACKUP_FILE | cut -f1)"
    echo "  Files: $(tar -tzf $CONFIG_BACKUP_FILE | wc -l)"
else
    echo "✗ Configuration backup failed"
    exit 1
fi
```

### Automated Configuration Backup

```python
#!/usr/bin/env python3
# config-backup.py

import os
import json
import tarfile
import shutil
import hashlib
from datetime import datetime
from pathlib import Path

class ConfigurationBackup:
    def __init__(self, install_path="/opt/thai-tokenizer"):
        self.install_path = Path(install_path)
        self.backup_dir = self.install_path / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_backup(self, backup_name=None):
        """Create configuration backup"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = backup_name or f"config-backup-{timestamp}"
        backup_file = self.backup_dir / f"{backup_name}.tar.gz"
        
        print(f"Creating configuration backup: {backup_file}")
        
        # Files and directories to backup
        backup_items = [
            self.install_path / "config",
            Path("/etc/thai-tokenizer"),
            Path("/etc/ssl/thai-tokenizer"),
            Path("/etc/systemd/system/thai-tokenizer.service"),
            Path("/etc/systemd/system/thai-tokenizer.service.d"),
            self.install_path / "docker-compose.yml",
            self.install_path / ".env"
        ]
        
        # Create backup metadata
        metadata = {
            "backup_type": "configuration",
            "timestamp": timestamp,
            "hostname": os.uname().nodename,
            "service_version": self._get_service_version(),
            "files_included": [],
            "checksums": {}
        }
        
        # Create tar archive
        with tarfile.open(backup_file, "w:gz") as tar:
            for item in backup_items:
                if item.exists():
                    arcname = item.name
                    tar.add(item, arcname=arcname)
                    metadata["files_included"].append(str(item))
                    
                    # Calculate checksum for files
                    if item.is_file():
                        metadata["checksums"][str(item)] = self._calculate_checksum(item)
            
            # Add metadata
            metadata_json = json.dumps(metadata, indent=2)
            metadata_info = tarfile.TarInfo(name="backup-metadata.json")
            metadata_info.size = len(metadata_json.encode())
            tar.addfile(metadata_info, fileobj=io.BytesIO(metadata_json.encode()))
        
        # Verify backup
        if backup_file.exists():
            size = backup_file.stat().st_size
            print(f"✓ Configuration backup created successfully")
            print(f"  File: {backup_file}")
            print(f"  Size: {size / 1024 / 1024:.2f} MB")
            return str(backup_file)
        else:
            raise Exception("Backup creation failed")
    
    def list_backups(self):
        """List available configuration backups"""
        backups = []
        for backup_file in self.backup_dir.glob("config-backup-*.tar.gz"):
            stat = backup_file.stat()
            backups.append({
                "name": backup_file.name,
                "path": str(backup_file),
                "size": stat.st_size,
                "created": datetime.fromtimestamp(stat.st_mtime).isoformat()
            })
        
        return sorted(backups, key=lambda x: x["created"], reverse=True)
    
    def restore_backup(self, backup_file):
        """Restore configuration from backup"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        print(f"Restoring configuration from: {backup_file}")
        
        # Create temporary extraction directory
        temp_dir = Path("/tmp/config-restore")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Extract backup
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)
            
            # Read metadata
            metadata_file = temp_dir / "backup-metadata.json"
            if metadata_file.exists():
                with open(metadata_file) as f:
                    metadata = json.load(f)
                print(f"Restoring backup from {metadata['timestamp']}")
            
            # Restore files
            restored_files = []
            for item in temp_dir.iterdir():
                if item.name == "backup-metadata.json":
                    continue
                
                if item.name == "config":
                    target = self.install_path / "config"
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(item, target)
                    restored_files.append(str(target))
                
                elif item.name == "thai-tokenizer":
                    target = Path("/etc/thai-tokenizer")
                    if target.exists():
                        shutil.rmtree(target)
                    shutil.copytree(item, target)
                    restored_files.append(str(target))
                
                # Handle other restoration logic...
            
            print(f"✓ Configuration restored successfully")
            print(f"  Restored files: {len(restored_files)}")
            return restored_files
            
        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _get_service_version(self):
        """Get service version"""
        version_file = self.install_path / "VERSION"
        if version_file.exists():
            return version_file.read_text().strip()
        return "unknown"
    
    def _calculate_checksum(self, file_path):
        """Calculate SHA256 checksum of file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

if __name__ == "__main__":
    import sys
    
    backup = ConfigurationBackup()
    
    if len(sys.argv) < 2:
        print("Usage: python3 config-backup.py <create|list|restore> [backup_file]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        backup_name = sys.argv[2] if len(sys.argv) > 2 else None
        backup_file = backup.create_backup(backup_name)
        print(f"Backup created: {backup_file}")
    
    elif command == "list":
        backups = backup.list_backups()
        print("Available configuration backups:")
        for b in backups:
            print(f"  {b['name']} - {b['created']} ({b['size'] / 1024 / 1024:.2f} MB)")
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Please specify backup file to restore")
            sys.exit(1)
        backup.restore_backup(sys.argv[2])
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
```

## Service State Backup

### Service State Backup Script

```bash
#!/bin/bash
# service-state-backup.sh

INSTALL_PATH="/opt/thai-tokenizer"
BACKUP_DIR="$INSTALL_PATH/backups"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
STATE_BACKUP_FILE="$BACKUP_DIR/state-backup-$TIMESTAMP.tar.gz"

echo "=== Service State Backup - $(date) ==="

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create temporary directory for backup
TEMP_DIR=$(mktemp -d)
BACKUP_TEMP="$TEMP_DIR/state-backup"
mkdir -p "$BACKUP_TEMP"

# Backup service state
echo "Backing up service state..."

# Process information
if pgrep -f thai-tokenizer > /dev/null; then
    echo "Service is running - capturing process state"
    ps aux | grep thai-tokenizer | grep -v grep > "$BACKUP_TEMP/process-info.txt"
    
    # Get process ID
    PID=$(pgrep -f thai-tokenizer | head -1)
    if [ -n "$PID" ]; then
        # Process memory maps
        cat /proc/$PID/maps > "$BACKUP_TEMP/process-maps.txt" 2>/dev/null || true
        
        # Process status
        cat /proc/$PID/status > "$BACKUP_TEMP/process-status.txt" 2>/dev/null || true
        
        # Open files
        lsof -p $PID > "$BACKUP_TEMP/open-files.txt" 2>/dev/null || true
    fi
else
    echo "Service is not running"
    echo "stopped" > "$BACKUP_TEMP/service-status.txt"
fi

# Runtime data
if [ -d "$INSTALL_PATH/run" ]; then
    cp -r "$INSTALL_PATH/run" "$BACKUP_TEMP/"
fi

# Temporary data
if [ -d "$INSTALL_PATH/tmp" ]; then
    cp -r "$INSTALL_PATH/tmp" "$BACKUP_TEMP/"
fi

# Cache data
if [ -d "$INSTALL_PATH/cache" ]; then
    cp -r "$INSTALL_PATH/cache" "$BACKUP_TEMP/"
fi

# Recent logs (last 1000 lines)
if [ -f "$INSTALL_PATH/logs/thai-tokenizer.log" ]; then
    tail -1000 "$INSTALL_PATH/logs/thai-tokenizer.log" > "$BACKUP_TEMP/recent-logs.txt"
fi

# System information
echo "Capturing system information..."
uname -a > "$BACKUP_TEMP/system-info.txt"
df -h >> "$BACKUP_TEMP/system-info.txt"
free -h >> "$BACKUP_TEMP/system-info.txt"
uptime >> "$BACKUP_TEMP/system-info.txt"

# Network connections
netstat -tulpn | grep :8000 > "$BACKUP_TEMP/network-connections.txt" 2>/dev/null || true

# Create backup metadata
cat > "$BACKUP_TEMP/backup-metadata.json" << EOF
{
  "backup_type": "service_state",
  "timestamp": "$TIMESTAMP",
  "hostname": "$(hostname)",
  "service_running": $(pgrep -f thai-tokenizer > /dev/null && echo "true" || echo "false"),
  "backup_size": "$(du -sh $BACKUP_TEMP | cut -f1)"
}
EOF

# Create compressed backup
echo "Creating compressed backup..."
tar -czf "$STATE_BACKUP_FILE" -C "$TEMP_DIR" state-backup

# Cleanup temporary directory
rm -rf "$TEMP_DIR"

# Verify backup
if [ -f "$STATE_BACKUP_FILE" ]; then
    echo "✓ Service state backup created: $STATE_BACKUP_FILE"
    echo "  Size: $(du -sh $STATE_BACKUP_FILE | cut -f1)"
else
    echo "✗ Service state backup failed"
    exit 1
fi
```

## Custom Dictionary Backup

### Dictionary Backup Implementation

```python
#!/usr/bin/env python3
# dictionary-backup.py

import os
import json
import shutil
import tarfile
from datetime import datetime
from pathlib import Path

class DictionaryBackup:
    def __init__(self, install_path="/opt/thai-tokenizer"):
        self.install_path = Path(install_path)
        self.data_dir = self.install_path / "data"
        self.backup_dir = self.install_path / "backups"
        self.backup_dir.mkdir(exist_ok=True)
    
    def create_dictionary_backup(self, backup_name=None):
        """Create backup of custom dictionaries"""
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_name = backup_name or f"dictionary-backup-{timestamp}"
        backup_file = self.backup_dir / f"{backup_name}.tar.gz"
        
        print(f"Creating dictionary backup: {backup_file}")
        
        # Dictionary directories to backup
        dict_dirs = [
            self.data_dir / "dictionaries",
            self.data_dir / "custom_words",
            self.data_dir / "compound_words",
            self.data_dir / "user_dictionaries"
        ]
        
        # Create backup metadata
        metadata = {
            "backup_type": "dictionaries",
            "timestamp": timestamp,
            "hostname": os.uname().nodename,
            "dictionaries": []
        }
        
        # Create tar archive
        with tarfile.open(backup_file, "w:gz") as tar:
            for dict_dir in dict_dirs:
                if dict_dir.exists():
                    # Add directory to archive
                    tar.add(dict_dir, arcname=dict_dir.name)
                    
                    # Collect dictionary information
                    dict_info = {
                        "name": dict_dir.name,
                        "path": str(dict_dir),
                        "files": [],
                        "total_words": 0
                    }
                    
                    # Process dictionary files
                    for dict_file in dict_dir.glob("*.txt"):
                        try:
                            with open(dict_file, 'r', encoding='utf-8') as f:
                                word_count = sum(1 for line in f if line.strip())
                            
                            dict_info["files"].append({
                                "name": dict_file.name,
                                "size": dict_file.stat().st_size,
                                "word_count": word_count,
                                "modified": datetime.fromtimestamp(dict_file.stat().st_mtime).isoformat()
                            })
                            dict_info["total_words"] += word_count
                        except Exception as e:
                            print(f"Warning: Could not process {dict_file}: {e}")
                    
                    metadata["dictionaries"].append(dict_info)
            
            # Add metadata to archive
            metadata_json = json.dumps(metadata, indent=2, ensure_ascii=False)
            metadata_info = tarfile.TarInfo(name="dictionary-metadata.json")
            metadata_info.size = len(metadata_json.encode('utf-8'))
            tar.addfile(metadata_info, fileobj=io.BytesIO(metadata_json.encode('utf-8')))
        
        if backup_file.exists():
            size = backup_file.stat().st_size
            total_words = sum(d["total_words"] for d in metadata["dictionaries"])
            print(f"✓ Dictionary backup created successfully")
            print(f"  File: {backup_file}")
            print(f"  Size: {size / 1024 / 1024:.2f} MB")
            print(f"  Total words: {total_words:,}")
            return str(backup_file)
        else:
            raise Exception("Dictionary backup creation failed")
    
    def restore_dictionary_backup(self, backup_file):
        """Restore dictionaries from backup"""
        backup_path = Path(backup_file)
        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_file}")
        
        print(f"Restoring dictionaries from: {backup_file}")
        
        # Create temporary extraction directory
        temp_dir = Path("/tmp/dictionary-restore")
        temp_dir.mkdir(exist_ok=True)
        
        try:
            # Extract backup
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(temp_dir)
            
            # Read metadata
            metadata_file = temp_dir / "dictionary-metadata.json"
            if metadata_file.exists():
                with open(metadata_file, encoding='utf-8') as f:
                    metadata = json.load(f)
                print(f"Restoring dictionary backup from {metadata['timestamp']}")
            
            # Restore dictionary directories
            restored_dirs = []
            for item in temp_dir.iterdir():
                if item.name == "dictionary-metadata.json":
                    continue
                
                if item.is_dir():
                    target_dir = self.data_dir / item.name
                    
                    # Backup existing directory if it exists
                    if target_dir.exists():
                        backup_existing = target_dir.with_suffix(f".backup.{datetime.now().strftime('%Y%m%d-%H%M%S')}")
                        shutil.move(target_dir, backup_existing)
                        print(f"Existing directory backed up to: {backup_existing}")
                    
                    # Restore directory
                    shutil.copytree(item, target_dir)
                    restored_dirs.append(str(target_dir))
                    print(f"Restored: {target_dir}")
            
            print(f"✓ Dictionary restoration completed")
            print(f"  Restored directories: {len(restored_dirs)}")
            return restored_dirs
            
        finally:
            # Cleanup temporary directory
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def validate_dictionaries(self):
        """Validate dictionary files"""
        validation_results = []
        
        dict_dirs = [
            self.data_dir / "dictionaries",
            self.data_dir / "custom_words",
            self.data_dir / "compound_words"
        ]
        
        for dict_dir in dict_dirs:
            if not dict_dir.exists():
                continue
            
            for dict_file in dict_dir.glob("*.txt"):
                result = {
                    "file": str(dict_file),
                    "valid": True,
                    "errors": [],
                    "word_count": 0,
                    "encoding": "utf-8"
                }
                
                try:
                    with open(dict_file, 'r', encoding='utf-8') as f:
                        for line_num, line in enumerate(f, 1):
                            line = line.strip()
                            if not line:
                                continue
                            
                            result["word_count"] += 1
                            
                            # Validate Thai characters
                            if not any('\u0e00' <= char <= '\u0e7f' for char in line):
                                result["errors"].append(f"Line {line_num}: No Thai characters found")
                                result["valid"] = False
                            
                            # Check for invalid characters
                            if any(ord(char) < 32 and char not in '\t\n\r' for char in line):
                                result["errors"].append(f"Line {line_num}: Invalid control characters")
                                result["valid"] = False
                
                except UnicodeDecodeError as e:
                    result["valid"] = False
                    result["errors"].append(f"Encoding error: {e}")
                    result["encoding"] = "unknown"
                
                except Exception as e:
                    result["valid"] = False
                    result["errors"].append(f"File error: {e}")
                
                validation_results.append(result)
        
        return validation_results

if __name__ == "__main__":
    import sys
    import io
    
    backup = DictionaryBackup()
    
    if len(sys.argv) < 2:
        print("Usage: python3 dictionary-backup.py <create|restore|validate> [backup_file]")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "create":
        backup_name = sys.argv[2] if len(sys.argv) > 2 else None
        backup_file = backup.create_dictionary_backup(backup_name)
        print(f"Dictionary backup created: {backup_file}")
    
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Please specify backup file to restore")
            sys.exit(1)
        backup.restore_dictionary_backup(sys.argv[2])
    
    elif command == "validate":
        results = backup.validate_dictionaries()
        print("Dictionary validation results:")
        for result in results:
            status = "✓" if result["valid"] else "✗"
            print(f"{status} {result['file']} - {result['word_count']} words")
            for error in result["errors"]:
                print(f"    Error: {error}")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
```

## Automated Backup Procedures

### Comprehensive Backup Script

```bash
#!/bin/bash
# automated-backup.sh

set -e

# Configuration
INSTALL_PATH="/opt/thai-tokenizer"
BACKUP_DIR="$INSTALL_PATH/backups"
REMOTE_BACKUP_DIR="/mnt/backup/thai-tokenizer"
RETENTION_DAYS=30
LOG_FILE="$INSTALL_PATH/logs/backup.log"

# Backup types
BACKUP_TYPE="${1:-full}"  # full, config, state, dictionary
BACKUP_NAME="${2:-auto-backup-$(date +%Y%m%d-%H%M%S)}"

# Logging function
log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') - $1" | tee -a "$LOG_FILE"
}

# Error handling
handle_error() {
    log "ERROR: Backup failed at line $1"
    exit 1
}
trap 'handle_error $LINENO' ERR

log "=== Starting Automated Backup ==="
log "Backup type: $BACKUP_TYPE"
log "Backup name: $BACKUP_NAME"

# Create backup directories
mkdir -p "$BACKUP_DIR"
mkdir -p "$REMOTE_BACKUP_DIR" 2>/dev/null || true

# Pre-backup health check
log "Performing pre-backup health check..."
if ! curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log "WARNING: Service health check failed"
fi

case "$BACKUP_TYPE" in
    "full")
        log "Creating full backup..."
        
        # Configuration backup
        log "Backing up configuration..."
        python3 "$INSTALL_PATH/scripts/config-backup.py" create "config-$BACKUP_NAME"
        
        # Service state backup
        log "Backing up service state..."
        bash "$INSTALL_PATH/scripts/service-state-backup.sh"
        
        # Dictionary backup
        log "Backing up dictionaries..."
        python3 "$INSTALL_PATH/scripts/dictionary-backup.py" create "dictionary-$BACKUP_NAME"
        
        # Combine all backups
        log "Creating combined full backup..."
        FULL_BACKUP_FILE="$BACKUP_DIR/full-backup-$BACKUP_NAME.tar.gz"
        tar -czf "$FULL_BACKUP_FILE" -C "$BACKUP_DIR" \
            config-$BACKUP_NAME.tar.gz \
            state-backup-*.tar.gz \
            dictionary-$BACKUP_NAME.tar.gz
        
        BACKUP_FILE="$FULL_BACKUP_FILE"
        ;;
        
    "config")
        log "Creating configuration backup..."
        python3 "$INSTALL_PATH/scripts/config-backup.py" create "$BACKUP_NAME"
        BACKUP_FILE="$BACKUP_DIR/config-$BACKUP_NAME.tar.gz"
        ;;
        
    "state")
        log "Creating service state backup..."
        bash "$INSTALL_PATH/scripts/service-state-backup.sh"
        BACKUP_FILE=$(ls -t "$BACKUP_DIR"/state-backup-*.tar.gz | head -1)
        ;;
        
    "dictionary")
        log "Creating dictionary backup..."
        python3 "$INSTALL_PATH/scripts/dictionary-backup.py" create "$BACKUP_NAME"
        BACKUP_FILE="$BACKUP_DIR/dictionary-$BACKUP_NAME.tar.gz"
        ;;
        
    *)
        log "ERROR: Unknown backup type: $BACKUP_TYPE"
        exit 1
        ;;
esac

# Verify backup
if [ -f "$BACKUP_FILE" ]; then
    BACKUP_SIZE=$(du -sh "$BACKUP_FILE" | cut -f1)
    log "✓ Backup created successfully: $BACKUP_FILE ($BACKUP_SIZE)"
    
    # Test backup integrity
    if tar -tzf "$BACKUP_FILE" > /dev/null 2>&1; then
        log "✓ Backup integrity verified"
    else
        log "✗ Backup integrity check failed"
        exit 1
    fi
else
    log "✗ Backup file not found: $BACKUP_FILE"
    exit 1
fi

# Copy to remote backup location
if [ -d "$REMOTE_BACKUP_DIR" ]; then
    log "Copying backup to remote location..."
    cp "$BACKUP_FILE" "$REMOTE_BACKUP_DIR/"
    if [ $? -eq 0 ]; then
        log "✓ Backup copied to remote location"
    else
        log "✗ Failed to copy backup to remote location"
    fi
fi

# Cleanup old backups
log "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
find "$REMOTE_BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>/dev/null || true

# Generate backup report
BACKUP_COUNT=$(ls -1 "$BACKUP_DIR"/*.tar.gz 2>/dev/null | wc -l)
TOTAL_BACKUP_SIZE=$(du -sh "$BACKUP_DIR" | cut -f1)

cat > "$BACKUP_DIR/backup-report-$(date +%Y%m%d).txt" << EOF
Backup Report - $(date)
======================
Backup Type: $BACKUP_TYPE
Backup File: $BACKUP_FILE
Backup Size: $BACKUP_SIZE
Total Backups: $BACKUP_COUNT
Total Backup Size: $TOTAL_BACKUP_SIZE
Retention Policy: $RETENTION_DAYS days
Remote Backup: $([ -d "$REMOTE_BACKUP_DIR" ] && echo "Enabled" || echo "Disabled")
EOF

log "=== Backup Completed Successfully ==="
log "Backup file: $BACKUP_FILE"
log "Backup size: $BACKUP_SIZE"
```

### Cron Job Setup

```bash
#!/bin/bash
# setup-backup-cron.sh

# Create cron jobs for automated backups
cat > /tmp/thai-tokenizer-backup-cron << 'EOF'
# Thai Tokenizer Automated Backups

# Daily configuration backup at 2 AM
0 2 * * * /opt/thai-tokenizer/scripts/automated-backup.sh config

# Weekly full backup on Sundays at 3 AM
0 3 * * 0 /opt/thai-tokenizer/scripts/automated-backup.sh full

# Daily dictionary backup at 1 AM
0 1 * * * /opt/thai-tokenizer/scripts/automated-backup.sh dictionary

# Hourly service state backup during business hours
0 9-17 * * 1-5 /opt/thai-tokenizer/scripts/automated-backup.sh state
EOF

# Install cron jobs
crontab -l > /tmp/current-cron 2>/dev/null || true
cat /tmp/current-cron /tmp/thai-tokenizer-backup-cron | crontab -

echo "Backup cron jobs installed successfully"
echo "Current cron jobs:"
crontab -l | grep thai-tokenizer
```

This comprehensive backup and recovery guide provides detailed procedures for protecting and restoring the Thai Tokenizer service, ensuring business continuity and data protection across different deployment scenarios.