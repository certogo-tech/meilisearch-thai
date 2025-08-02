# Disaster Recovery Guide

This guide provides comprehensive procedures for recovering from catastrophic failures of the Thai Tokenizer on-premise deployment.

## Overview

Disaster recovery procedures are designed to restore service functionality in the event of:

- Complete system failure
- Data corruption
- Hardware failure
- Network infrastructure failure
- Security breaches
- Natural disasters

## Recovery Time Objectives (RTO)

| Scenario | Target RTO | Maximum RTO |
|----------|------------|-------------|
| Service crash | 5 minutes | 15 minutes |
| Configuration corruption | 10 minutes | 30 minutes |
| Data corruption | 30 minutes | 2 hours |
| Complete system failure | 2 hours | 8 hours |
| Hardware failure | 4 hours | 24 hours |

## Recovery Point Objectives (RPO)

| Data Type | Target RPO | Maximum RPO |
|-----------|------------|-------------|
| Configuration | 0 minutes | 1 hour |
| Custom dictionaries | 1 hour | 24 hours |
| Service logs | 24 hours | 7 days |
| System state | 1 hour | 24 hours |

## Prerequisites

### Required Information

- Deployment method (Docker, systemd, standalone)
- Installation paths and configuration
- Meilisearch server details
- Network configuration
- Backup locations and credentials

### Required Tools

- Backup and recovery CLI tool
- System administration access
- Network connectivity to backup storage
- Meilisearch access credentials

### Required Backups

- Recent full system backup
- Configuration backup
- Custom dictionary backup
- Rollback points (if available)

## Disaster Recovery Procedures

### 1. Initial Assessment

#### 1.1 Assess the Scope of Failure

```bash
# Check service status
python3 src/deployment/backup_cli.py recovery diagnose

# Check system resources
df -h
free -h
ps aux | grep thai-tokenizer

# Check network connectivity
ping <meilisearch-host>
curl -I <meilisearch-host>:7700/health
```

#### 1.2 Determine Recovery Strategy

Based on the assessment, choose the appropriate recovery strategy:

- **Service Recovery**: Service is down but system is intact
- **Configuration Recovery**: Configuration is corrupted but data is intact
- **Data Recovery**: Data is corrupted but system is functional
- **Full System Recovery**: Complete system rebuild required

### 2. Service Recovery

For service crashes or process failures:

```bash
# Diagnose the failure
python3 src/deployment/backup_cli.py recovery diagnose

# Execute automatic recovery
python3 src/deployment/backup_cli.py recovery recover service_crash

# Verify recovery
curl http://localhost:8000/health
```

### 3. Configuration Recovery

For configuration corruption or invalid settings:

```bash
# Restore configuration from backup
python3 src/deployment/backup_cli.py backup restore <backup-id> --components configuration

# Restart service
# For Docker:
docker compose restart

# For systemd:
sudo systemctl restart thai-tokenizer.service

# For standalone:
python3 deployment/standalone/restart-service.sh
```

### 4. Data Recovery

For corrupted custom dictionaries or data files:

```bash
# List available backups
python3 src/deployment/backup_cli.py backup list

# Restore data components
python3 src/deployment/backup_cli.py backup restore <backup-id> --components dictionaries

# Verify data integrity
python3 -c "
import json
with open('/var/lib/thai-tokenizer/dictionaries/thai_compounds.json', 'r') as f:
    data = json.load(f)
    print(f'Loaded {len(data)} dictionary entries')
"
```

### 5. Full System Recovery

For complete system failure requiring rebuild:

#### 5.1 Prepare New System

```bash
# Install required dependencies
# For Ubuntu/Debian:
sudo apt update
sudo apt install python3 python3-pip python3-venv docker.io docker-compose

# For CentOS/RHEL:
sudo yum update
sudo yum install python3 python3-pip docker docker-compose
```

#### 5.2 Restore from Backup

```bash
# Create installation directory
sudo mkdir -p /opt/thai-tokenizer
sudo chown $USER:$USER /opt/thai-tokenizer

# Extract backup
cd /opt/thai-tokenizer
tar -xzf <backup-file>.tar.gz

# Restore configuration
python3 src/deployment/backup_cli.py backup restore <backup-id>
```

#### 5.3 Reconfigure System

```bash
# Update configuration for new system
# Edit configuration files to match new environment
nano /etc/thai-tokenizer/config.json

# Update Meilisearch connection settings
# Update file paths if different
# Update network settings if changed
```

#### 5.4 Deploy Service

```bash
# For Docker deployment:
cd deployment/docker
docker compose up -d

# For systemd deployment:
cd deployment/systemd
sudo ./deploy-systemd.sh

# For standalone deployment:
cd deployment/standalone
./setup-standalone.py --install-path /opt/thai-tokenizer
```

### 6. Rollback Procedures

If recovery attempts fail or cause additional issues:

#### 6.1 List Available Rollback Points

```bash
python3 src/deployment/backup_cli.py rollback list
```

#### 6.2 Execute Rollback

```bash
# Rollback to previous working state
python3 src/deployment/backup_cli.py rollback execute <rollback-id>

# Verify rollback success
curl http://localhost:8000/health
```

### 7. Network Recovery

For network-related failures:

#### 7.1 Check Network Connectivity

```bash
# Test basic connectivity
ping 8.8.8.8

# Test DNS resolution
nslookup <meilisearch-host>

# Test port connectivity
telnet <meilisearch-host> 7700
```

#### 7.2 Reconfigure Network Settings

```bash
# Update firewall rules
sudo ufw allow 8000/tcp
sudo ufw allow from <meilisearch-ip> to any port 7700

# Update hosts file if needed
echo "<meilisearch-ip> <meilisearch-host>" | sudo tee -a /etc/hosts

# Restart networking
sudo systemctl restart networking
```

### 8. Security Incident Recovery

For security breaches or compromised systems:

#### 8.1 Immediate Response

```bash
# Stop all services immediately
python3 src/deployment/backup_cli.py recovery recover service_crash

# Change all credentials
# Update Meilisearch API keys
# Update service authentication tokens
# Update SSL certificates if compromised
```

#### 8.2 System Hardening

```bash
# Update all packages
sudo apt update && sudo apt upgrade -y

# Review and update firewall rules
sudo ufw --force reset
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 8000/tcp
sudo ufw enable

# Review file permissions
find /opt/thai-tokenizer -type f -exec chmod 644 {} \;
find /opt/thai-tokenizer -type d -exec chmod 755 {} \;
```

#### 8.3 Restore from Clean Backup

```bash
# Use backup from before security incident
python3 src/deployment/backup_cli.py backup list
python3 src/deployment/backup_cli.py backup restore <clean-backup-id>
```

## Validation Procedures

After any recovery operation, perform these validation steps:

### 1. Service Health Check

```bash
# Check service status
curl http://localhost:8000/health

# Expected response:
# {"status": "healthy", "timestamp": "...", "version": "..."}
```

### 2. Thai Tokenization Test

```bash
# Test Thai tokenization functionality
curl -X POST http://localhost:8000/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "สวัสดีครับ", "language": "th"}'

# Expected response with tokenized text
```

### 3. Meilisearch Connectivity Test

```bash
# Test Meilisearch connection
curl http://localhost:8000/v1/health/detailed

# Check for Meilisearch connectivity in response
```

### 4. Performance Test

```bash
# Run basic performance test
time curl -X POST http://localhost:8000/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "'"$(head -c 1000 /dev/urandom | base64)"'", "language": "th"}'

# Should complete within reasonable time (<1 second)
```

### 5. Log Verification

```bash
# Check service logs for errors
tail -f /var/log/thai-tokenizer/service.log

# Look for:
# - No error messages
# - Successful startup messages
# - Meilisearch connection success
```

## Monitoring and Alerting

### Post-Recovery Monitoring

After recovery, implement enhanced monitoring:

```bash
# Enable detailed logging
export THAI_TOKENIZER_LOG_LEVEL=DEBUG

# Monitor resource usage
watch -n 5 'ps aux | grep thai-tokenizer; free -h; df -h'

# Monitor service health
watch -n 30 'curl -s http://localhost:8000/health'
```

### Set Up Alerting

Configure alerts for:

- Service downtime
- High error rates
- Resource exhaustion
- Meilisearch connectivity issues

## Backup Strategy Post-Recovery

### Immediate Actions

```bash
# Create recovery checkpoint
python3 src/deployment/backup_cli.py rollback create "post-recovery-$(date +%Y%m%d)"

# Create full backup
python3 src/deployment/backup_cli.py backup create --type full

# Enable automated backups
python3 src/deployment/backup_cli.py backup schedule --enable --frequency 6
```

### Long-term Strategy

- Increase backup frequency temporarily
- Implement off-site backup storage
- Test backup restoration procedures
- Document lessons learned

## Troubleshooting Common Issues

### Issue: Service Won't Start After Recovery

```bash
# Check configuration validity
python3 -c "
import json
with open('/etc/thai-tokenizer/config.json', 'r') as f:
    config = json.load(f)
    print('Configuration loaded successfully')
"

# Check file permissions
ls -la /opt/thai-tokenizer/
ls -la /etc/thai-tokenizer/
ls -la /var/log/thai-tokenizer/

# Check dependencies
python3 -c "import pythainlp; print('PyThaiNLP available')"
```

### Issue: Meilisearch Connection Fails

```bash
# Test direct connection
curl -H "Authorization: Bearer <api-key>" \
  http://<meilisearch-host>:7700/health

# Check network routing
traceroute <meilisearch-host>

# Verify API key
echo "<api-key>" | base64 -d
```

### Issue: Performance Degradation

```bash
# Check resource usage
top -p $(pgrep -f thai-tokenizer)

# Check disk space
df -h /var/lib/thai-tokenizer/

# Check memory usage
free -h

# Clear caches
python3 src/deployment/backup_cli.py recovery recover resource_exhaustion
```

## Emergency Contacts

### Internal Contacts

- System Administrator: [contact-info]
- Development Team: [contact-info]
- Network Administrator: [contact-info]

### External Contacts

- Hosting Provider: [contact-info]
- Meilisearch Support: [contact-info]
- Security Team: [contact-info]

## Recovery Documentation

### Post-Recovery Report Template

```
Disaster Recovery Report
Date: [date]
Incident ID: [id]
Recovery Time: [duration]

Incident Summary:
- Failure type: [type]
- Root cause: [cause]
- Impact: [impact]

Recovery Actions:
- [action 1]
- [action 2]
- [action 3]

Lessons Learned:
- [lesson 1]
- [lesson 2]

Preventive Measures:
- [measure 1]
- [measure 2]
```

### Update Procedures

After each recovery:

1. Update this documentation with new procedures
2. Update backup and recovery scripts
3. Test new procedures in staging environment
4. Train team members on new procedures

## Testing Recovery Procedures

### Regular Testing Schedule

- Monthly: Service recovery procedures
- Quarterly: Configuration recovery procedures
- Semi-annually: Full system recovery procedures
- Annually: Disaster recovery simulation

### Testing Checklist

- [ ] All backup files are accessible
- [ ] Recovery procedures complete within RTO
- [ ] Service functionality is fully restored
- [ ] Performance meets baseline requirements
- [ ] All integrations work correctly
- [ ] Monitoring and alerting are functional

## Appendix

### A. Configuration File Templates

See `deployment/configs/` directory for template files.

### B. Network Configuration Examples

See `deployment/configs/network/` directory for examples.

### C. Monitoring Setup Scripts

See `monitoring/` directory for setup scripts.

### D. Security Hardening Checklist

See `SECURITY_IMPLEMENTATION_SUMMARY.md` for security procedures.
