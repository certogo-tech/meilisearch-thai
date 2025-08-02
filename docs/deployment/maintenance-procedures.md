# Maintenance Procedures and Update Guide

This document provides comprehensive procedures for maintaining, updating, and managing the Thai Tokenizer service in production environments.

## Table of Contents

1. [Routine Maintenance](#routine-maintenance)
2. [Update Procedures](#update-procedures)
3. [Health Monitoring](#health-monitoring)
4. [Log Management](#log-management)
5. [Database and Index Maintenance](#database-and-index-maintenance)
6. [Performance Monitoring](#performance-monitoring)
7. [Security Maintenance](#security-maintenance)
8. [Capacity Planning](#capacity-planning)
9. [Incident Response](#incident-response)
10. [Documentation Maintenance](#documentation-maintenance)

## Routine Maintenance

### Daily Maintenance Tasks

#### Health Check Verification

```bash
#!/bin/bash
# daily-health-check.sh

echo "=== Daily Health Check - $(date) ==="

# Service health
curl -s http://localhost:8000/health | jq '.'
if [ $? -eq 0 ]; then
    echo "✓ Service health check passed"
else
    echo "✗ Service health check failed"
    exit 1
fi

# Meilisearch connectivity
curl -s -H "Authorization: Bearer $MEILISEARCH_API_KEY" \
    http://your-meilisearch:7700/health | jq '.'
if [ $? -eq 0 ]; then
    echo "✓ Meilisearch connectivity check passed"
else
    echo "✗ Meilisearch connectivity check failed"
fi

# Thai tokenization test
response=$(curl -s -X POST http://localhost:8000/tokenize \
    -H "Content-Type: application/json" \
    -d '{"text": "สวัสดีครับ"}')
if echo "$response" | jq -e '.tokens' > /dev/null; then
    echo "✓ Thai tokenization test passed"
else
    echo "✗ Thai tokenization test failed"
fi

# Resource usage
echo "=== Resource Usage ==="
ps aux | grep thai-tokenizer | grep -v grep
free -h
df -h /opt/thai-tokenizer

echo "=== Health Check Complete ==="
```

#### Log Review

```bash
#!/bin/bash
# daily-log-review.sh

LOG_FILE="/opt/thai-tokenizer/logs/thai-tokenizer.log"
YESTERDAY=$(date -d "yesterday" +%Y-%m-%d)

echo "=== Daily Log Review - $(date) ==="

# Check for errors
echo "Errors in the last 24 hours:"
grep -i error "$LOG_FILE" | grep "$YESTERDAY" | wc -l

# Check for warnings
echo "Warnings in the last 24 hours:"
grep -i warning "$LOG_FILE" | grep "$YESTERDAY" | wc -l

# Check for performance issues
echo "Slow requests (>100ms) in the last 24 hours:"
grep "slow request" "$LOG_FILE" | grep "$YESTERDAY" | wc -l

# Check memory usage patterns
echo "Memory usage alerts:"
grep "memory" "$LOG_FILE" | grep "$YESTERDAY" | tail -5

# Generate summary report
cat > /tmp/daily-log-summary.txt << EOF
Daily Log Summary - $YESTERDAY
================================
Total log entries: $(wc -l < "$LOG_FILE")
Errors: $(grep -i error "$LOG_FILE" | grep "$YESTERDAY" | wc -l)
Warnings: $(grep -i warning "$LOG_FILE" | grep "$YESTERDAY" | wc -l)
Performance issues: $(grep "slow request" "$LOG_FILE" | grep "$YESTERDAY" | wc -l)
EOF

echo "Log summary saved to /tmp/daily-log-summary.txt"
```

### Weekly Maintenance Tasks

#### Performance Review

```bash
#!/bin/bash
# weekly-performance-review.sh

echo "=== Weekly Performance Review - $(date) ==="

# Run performance benchmark
python3 deployment/scripts/benchmark.py \
    --host http://localhost:8000 \
    --concurrent-users 10 \
    --duration 300 \
    --output-file /tmp/weekly-benchmark.json

# Analyze results
python3 << 'EOF'
import json
import statistics

with open('/tmp/weekly-benchmark.json') as f:
    data = json.load(f)

response_times = data.get('response_times', [])
if response_times:
    print(f"Average response time: {statistics.mean(response_times):.2f}ms")
    print(f"95th percentile: {statistics.quantiles(response_times, n=20)[18]:.2f}ms")
    print(f"Max response time: {max(response_times):.2f}ms")
    
    # Check if performance targets are met
    avg_time = statistics.mean(response_times)
    if avg_time > 100:
        print("⚠️  WARNING: Average response time exceeds 100ms target")
    else:
        print("✓ Performance targets met")
EOF

# Check resource trends
echo "=== Resource Usage Trends ==="
# Memory usage over the week
grep "memory_usage" /opt/thai-tokenizer/logs/thai-tokenizer.log | \
    tail -168 | awk '{print $3}' | \
    python3 -c "
import sys
values = [float(line.strip()) for line in sys.stdin]
if values:
    print(f'Memory usage trend: {values[-1] - values[0]:.2f}MB change')
    print(f'Average: {sum(values)/len(values):.2f}MB')
    print(f'Peak: {max(values):.2f}MB')
"
```

#### Security Audit

```bash
#!/bin/bash
# weekly-security-audit.sh

echo "=== Weekly Security Audit - $(date) ==="

# Check file permissions
echo "Checking file permissions..."
find /opt/thai-tokenizer -type f -perm /o+w -ls
find /etc/thai-tokenizer -type f -perm /o+r -ls

# Check for failed authentication attempts
echo "Failed authentication attempts:"
grep -i "authentication failed" /opt/thai-tokenizer/logs/thai-tokenizer.log | \
    grep "$(date -d '7 days ago' +%Y-%m-%d)" | wc -l

# Check SSL certificate expiry
if [ -f "/etc/ssl/certs/thai-tokenizer.crt" ]; then
    echo "SSL certificate expiry:"
    openssl x509 -in /etc/ssl/certs/thai-tokenizer.crt -noout -dates
fi

# Check for suspicious activity
echo "Suspicious activity patterns:"
grep -E "(unusual|suspicious|attack)" /opt/thai-tokenizer/logs/thai-tokenizer.log | \
    grep "$(date -d '7 days ago' +%Y-%m-%d)" | wc -l

# Generate security report
cat > /tmp/weekly-security-report.txt << EOF
Weekly Security Audit - $(date +%Y-%m-%d)
=========================================
File permission issues: $(find /opt/thai-tokenizer -type f -perm /o+w | wc -l)
Failed auth attempts: $(grep -i "authentication failed" /opt/thai-tokenizer/logs/thai-tokenizer.log | grep "$(date -d '7 days ago' +%Y-%m-%d)" | wc -l)
Suspicious activities: $(grep -E "(unusual|suspicious|attack)" /opt/thai-tokenizer/logs/thai-tokenizer.log | grep "$(date -d '7 days ago' +%Y-%m-%d)" | wc -l)
EOF
```

### Monthly Maintenance Tasks

#### Comprehensive System Review

```bash
#!/bin/bash
# monthly-system-review.sh

echo "=== Monthly System Review - $(date) ==="

# Disk usage analysis
echo "Disk usage analysis:"
du -sh /opt/thai-tokenizer/*
du -sh /var/log/thai-tokenizer/*

# Log rotation verification
echo "Log rotation status:"
ls -la /var/log/thai-tokenizer/
logrotate -d /etc/logrotate.d/thai-tokenizer

# Dependency updates check
echo "Checking for dependency updates:"
/opt/thai-tokenizer/venv/bin/pip list --outdated

# Configuration drift detection
echo "Configuration drift check:"
diff -u /opt/thai-tokenizer/config/config.json.backup \
    /opt/thai-tokenizer/config/config.json || echo "No configuration backup found"

# Performance trend analysis
python3 << 'EOF'
import json
import glob
from datetime import datetime, timedelta

# Analyze monthly performance trends
benchmark_files = glob.glob('/tmp/weekly-benchmark-*.json')
if benchmark_files:
    print("Monthly performance trends:")
    for file in sorted(benchmark_files)[-4:]:  # Last 4 weeks
        with open(file) as f:
            data = json.load(f)
        avg_time = sum(data.get('response_times', [])) / len(data.get('response_times', [1]))
        print(f"{file}: {avg_time:.2f}ms average")
EOF
```

## Update Procedures

### Service Updates

#### Minor Updates (Patch Versions)

```bash
#!/bin/bash
# minor-update.sh

set -e

echo "=== Minor Update Procedure ==="

# Pre-update backup
echo "Creating pre-update backup..."
python3 deployment/standalone/backup-service.py \
    --install-path /opt/thai-tokenizer \
    create --name "pre-update-$(date +%Y%m%d-%H%M%S)"

# Health check before update
echo "Pre-update health check..."
curl -f http://localhost:8000/health || {
    echo "Service unhealthy before update. Aborting."
    exit 1
}

# Update dependencies
echo "Updating dependencies..."
/opt/thai-tokenizer/venv/bin/pip install --upgrade -r requirements.txt

# Restart service
echo "Restarting service..."
case "$DEPLOYMENT_METHOD" in
    "docker")
        docker compose -f deployment/docker/docker-compose.external-meilisearch.yml restart thai-tokenizer
        ;;
    "systemd")
        sudo systemctl restart thai-tokenizer
        ;;
    "standalone")
        /opt/thai-tokenizer/bin/restart-service.sh
        ;;
esac

# Post-update verification
echo "Post-update verification..."
sleep 10
curl -f http://localhost:8000/health || {
    echo "Service unhealthy after update. Rolling back..."
    # Rollback procedure would go here
    exit 1
}

# Run smoke tests
python3 deployment/scripts/demo_thai_tokenizer.py --test-mode

echo "Minor update completed successfully"
```

#### Major Updates (Version Upgrades)

```bash
#!/bin/bash
# major-update.sh

set -e

echo "=== Major Update Procedure ==="

# Pre-update checklist
echo "Pre-update checklist:"
echo "1. Backup created: $(ls -la /opt/thai-tokenizer/backups/ | tail -1)"
echo "2. Maintenance window scheduled: $(date)"
echo "3. Rollback plan prepared: Yes"

# Stop service
echo "Stopping service for major update..."
case "$DEPLOYMENT_METHOD" in
    "docker")
        docker compose -f deployment/docker/docker-compose.external-meilisearch.yml down
        ;;
    "systemd")
        sudo systemctl stop thai-tokenizer
        ;;
    "standalone")
        /opt/thai-tokenizer/bin/stop-service.sh
        ;;
esac

# Update application code
echo "Updating application code..."
git fetch origin
git checkout v2.0.0  # Example version

# Update configuration if needed
echo "Updating configuration..."
if [ -f "config/migration/v2.0.0-migration.py" ]; then
    python3 config/migration/v2.0.0-migration.py \
        --config-file /opt/thai-tokenizer/config/config.json
fi

# Update dependencies
echo "Updating dependencies..."
/opt/thai-tokenizer/venv/bin/pip install --upgrade -r requirements.txt

# Run database migrations if needed
echo "Running migrations..."
if [ -f "migrations/v2.0.0.py" ]; then
    python3 migrations/v2.0.0.py
fi

# Start service
echo "Starting updated service..."
case "$DEPLOYMENT_METHOD" in
    "docker")
        docker compose -f deployment/docker/docker-compose.external-meilisearch.yml up -d
        ;;
    "systemd")
        sudo systemctl start thai-tokenizer
        ;;
    "standalone")
        /opt/thai-tokenizer/bin/start-service.sh
        ;;
esac

# Extended verification
echo "Extended post-update verification..."
sleep 30

# Health check
curl -f http://localhost:8000/health || {
    echo "Health check failed. Initiating rollback..."
    exit 1
}

# Functional tests
python3 deployment/scripts/run_full_system_integration_tests.py

echo "Major update completed successfully"
```

### Rollback Procedures

```bash
#!/bin/bash
# rollback.sh

set -e

BACKUP_FILE="$1"
if [ -z "$BACKUP_FILE" ]; then
    echo "Usage: $0 <backup-file>"
    echo "Available backups:"
    ls -la /opt/thai-tokenizer/backups/
    exit 1
fi

echo "=== Rollback Procedure ==="

# Stop current service
echo "Stopping current service..."
case "$DEPLOYMENT_METHOD" in
    "docker")
        docker compose -f deployment/docker/docker-compose.external-meilisearch.yml down
        ;;
    "systemd")
        sudo systemctl stop thai-tokenizer
        ;;
    "standalone")
        /opt/thai-tokenizer/bin/stop-service.sh
        ;;
esac

# Restore from backup
echo "Restoring from backup: $BACKUP_FILE"
python3 deployment/standalone/backup-service.py \
    --install-path /opt/thai-tokenizer \
    restore "$BACKUP_FILE"

# Start service
echo "Starting restored service..."
case "$DEPLOYMENT_METHOD" in
    "docker")
        docker compose -f deployment/docker/docker-compose.external-meilisearch.yml up -d
        ;;
    "systemd")
        sudo systemctl start thai-tokenizer
        ;;
    "standalone")
        /opt/thai-tokenizer/bin/start-service.sh
        ;;
esac

# Verify rollback
echo "Verifying rollback..."
sleep 15
curl -f http://localhost:8000/health || {
    echo "Rollback verification failed"
    exit 1
}

echo "Rollback completed successfully"
```

## Health Monitoring

### Automated Health Monitoring

```bash
#!/bin/bash
# health-monitor.sh

HEALTH_CHECK_INTERVAL=60
ALERT_THRESHOLD=3
FAILURE_COUNT=0

while true; do
    # Perform health check
    if curl -s -f http://localhost:8000/health > /dev/null; then
        FAILURE_COUNT=0
        echo "$(date): Health check passed"
    else
        FAILURE_COUNT=$((FAILURE_COUNT + 1))
        echo "$(date): Health check failed (attempt $FAILURE_COUNT)"
        
        if [ $FAILURE_COUNT -ge $ALERT_THRESHOLD ]; then
            # Send alert
            echo "$(date): ALERT - Service health check failed $FAILURE_COUNT times" | \
                mail -s "Thai Tokenizer Health Alert" admin@company.com
            
            # Attempt automatic recovery
            echo "$(date): Attempting automatic recovery..."
            /opt/thai-tokenizer/bin/restart-service.sh
            
            # Reset counter after recovery attempt
            FAILURE_COUNT=0
        fi
    fi
    
    sleep $HEALTH_CHECK_INTERVAL
done
```

### Health Check Dashboard

```python
#!/usr/bin/env python3
# health-dashboard.py

import requests
import json
import time
from datetime import datetime

def check_service_health():
    """Check Thai Tokenizer service health"""
    try:
        response = requests.get('http://localhost:8000/health/detailed', timeout=10)
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {'error': str(e)}

def check_meilisearch_health():
    """Check Meilisearch connectivity"""
    try:
        response = requests.get(
            'http://your-meilisearch:7700/health',
            headers={'Authorization': 'Bearer YOUR_API_KEY'},
            timeout=10
        )
        return response.status_code == 200, response.json()
    except Exception as e:
        return False, {'error': str(e)}

def generate_health_report():
    """Generate comprehensive health report"""
    report = {
        'timestamp': datetime.now().isoformat(),
        'service_health': {},
        'meilisearch_health': {},
        'overall_status': 'unknown'
    }
    
    # Check service health
    service_ok, service_data = check_service_health()
    report['service_health'] = {
        'status': 'healthy' if service_ok else 'unhealthy',
        'data': service_data
    }
    
    # Check Meilisearch health
    meilisearch_ok, meilisearch_data = check_meilisearch_health()
    report['meilisearch_health'] = {
        'status': 'healthy' if meilisearch_ok else 'unhealthy',
        'data': meilisearch_data
    }
    
    # Overall status
    if service_ok and meilisearch_ok:
        report['overall_status'] = 'healthy'
    elif service_ok or meilisearch_ok:
        report['overall_status'] = 'degraded'
    else:
        report['overall_status'] = 'unhealthy'
    
    return report

if __name__ == '__main__':
    report = generate_health_report()
    print(json.dumps(report, indent=2))
    
    # Save to file
    with open('/tmp/health-report.json', 'w') as f:
        json.dump(report, f, indent=2)
```

## Log Management

### Log Rotation Configuration

```bash
# /etc/logrotate.d/thai-tokenizer
/opt/thai-tokenizer/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 thai-tokenizer thai-tokenizer
    postrotate
        /opt/thai-tokenizer/bin/restart-service.sh > /dev/null 2>&1 || true
    endscript
}

/var/log/thai-tokenizer/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 thai-tokenizer thai-tokenizer
    postrotate
        systemctl reload thai-tokenizer > /dev/null 2>&1 || true
    endscript
}
```

### Log Analysis Scripts

```bash
#!/bin/bash
# log-analysis.sh

LOG_FILE="/opt/thai-tokenizer/logs/thai-tokenizer.log"
ANALYSIS_DATE="${1:-$(date +%Y-%m-%d)}"

echo "=== Log Analysis for $ANALYSIS_DATE ==="

# Error analysis
echo "Top 10 errors:"
grep "$ANALYSIS_DATE" "$LOG_FILE" | grep -i error | \
    awk '{print $5}' | sort | uniq -c | sort -nr | head -10

# Performance analysis
echo "Slow requests (>100ms):"
grep "$ANALYSIS_DATE" "$LOG_FILE" | grep "slow request" | \
    awk '{print $6}' | sort -n | tail -10

# Request volume analysis
echo "Hourly request volume:"
grep "$ANALYSIS_DATE" "$LOG_FILE" | grep "request completed" | \
    awk '{print $2}' | cut -d: -f1 | sort | uniq -c

# Memory usage patterns
echo "Memory usage peaks:"
grep "$ANALYSIS_DATE" "$LOG_FILE" | grep "memory_usage" | \
    awk '{print $2, $4}' | sort -k2 -n | tail -5

# Generate summary
TOTAL_REQUESTS=$(grep "$ANALYSIS_DATE" "$LOG_FILE" | grep "request completed" | wc -l)
ERROR_COUNT=$(grep "$ANALYSIS_DATE" "$LOG_FILE" | grep -i error | wc -l)
WARNING_COUNT=$(grep "$ANALYSIS_DATE" "$LOG_FILE" | grep -i warning | wc -l)

cat > "/tmp/log-analysis-$ANALYSIS_DATE.txt" << EOF
Log Analysis Summary - $ANALYSIS_DATE
====================================
Total requests: $TOTAL_REQUESTS
Errors: $ERROR_COUNT
Warnings: $WARNING_COUNT
Error rate: $(echo "scale=2; $ERROR_COUNT * 100 / $TOTAL_REQUESTS" | bc)%
EOF

echo "Analysis saved to /tmp/log-analysis-$ANALYSIS_DATE.txt"
```

### Centralized Logging Setup

```bash
#!/bin/bash
# setup-centralized-logging.sh

# Install rsyslog if not present
sudo apt install rsyslog

# Configure rsyslog for Thai Tokenizer
cat > /etc/rsyslog.d/30-thai-tokenizer.conf << 'EOF'
# Thai Tokenizer logging
$template ThaiTokenizerFormat,"%timestamp% %hostname% thai-tokenizer: %msg%\n"

# Local logging
if $programname == 'thai-tokenizer' then {
    /var/log/thai-tokenizer/thai-tokenizer.log;ThaiTokenizerFormat
    stop
}

# Remote logging (optional)
if $programname == 'thai-tokenizer' then {
    @@log-server.company.com:514;ThaiTokenizerFormat
}
EOF

# Restart rsyslog
sudo systemctl restart rsyslog

# Configure logrotate for centralized logs
cat > /etc/logrotate.d/thai-tokenizer-centralized << 'EOF'
/var/log/thai-tokenizer/*.log {
    daily
    missingok
    rotate 90
    compress
    delaycompress
    notifempty
    create 644 syslog adm
    postrotate
        systemctl reload rsyslog > /dev/null 2>&1 || true
    endscript
}
EOF

echo "Centralized logging configured"
```

## Database and Index Maintenance

### Meilisearch Index Maintenance

```python
#!/usr/bin/env python3
# meilisearch-maintenance.py

import requests
import json
import time
from datetime import datetime

class MeilisearchMaintenance:
    def __init__(self, host, api_key):
        self.host = host
        self.api_key = api_key
        self.headers = {'Authorization': f'Bearer {api_key}'}
    
    def get_indexes(self):
        """Get all indexes"""
        response = requests.get(f'{self.host}/indexes', headers=self.headers)
        return response.json()
    
    def get_index_stats(self, index_uid):
        """Get index statistics"""
        response = requests.get(f'{self.host}/indexes/{index_uid}/stats', headers=self.headers)
        return response.json()
    
    def optimize_index(self, index_uid):
        """Optimize index performance"""
        # Update settings for better Thai tokenization
        settings = {
            'searchableAttributes': ['content', 'title'],
            'filterableAttributes': ['language', 'type', 'created_at'],
            'sortableAttributes': ['created_at', 'updated_at'],
            'stopWords': [],  # Don't use English stop words for Thai
            'synonyms': {},
            'distinctAttribute': None
        }
        
        response = requests.patch(
            f'{self.host}/indexes/{index_uid}/settings',
            headers=self.headers,
            json=settings
        )
        return response.json()
    
    def cleanup_old_documents(self, index_uid, days_old=90):
        """Remove documents older than specified days"""
        cutoff_date = datetime.now().timestamp() - (days_old * 24 * 3600)
        
        # This would depend on your document structure
        filter_query = f'created_at < {cutoff_date}'
        
        response = requests.delete(
            f'{self.host}/indexes/{index_uid}/documents',
            headers=self.headers,
            params={'filter': filter_query}
        )
        return response.json()
    
    def generate_maintenance_report(self):
        """Generate comprehensive maintenance report"""
        report = {
            'timestamp': datetime.now().isoformat(),
            'indexes': []
        }
        
        indexes = self.get_indexes()
        for index in indexes.get('results', []):
            index_uid = index['uid']
            stats = self.get_index_stats(index_uid)
            
            index_report = {
                'uid': index_uid,
                'document_count': stats.get('numberOfDocuments', 0),
                'index_size': stats.get('isIndexing', False),
                'last_update': stats.get('lastUpdate'),
                'field_distribution': stats.get('fieldDistribution', {})
            }
            report['indexes'].append(index_report)
        
        return report

if __name__ == '__main__':
    maintenance = MeilisearchMaintenance(
        'http://your-meilisearch:7700',
        'YOUR_API_KEY'
    )
    
    report = maintenance.generate_maintenance_report()
    print(json.dumps(report, indent=2))
    
    # Save report
    with open(f'/tmp/meilisearch-maintenance-{datetime.now().strftime("%Y%m%d")}.json', 'w') as f:
        json.dump(report, f, indent=2)
```

### Index Optimization Schedule

```bash
#!/bin/bash
# index-optimization.sh

echo "=== Meilisearch Index Optimization ==="

# Run optimization during low-traffic hours
CURRENT_HOUR=$(date +%H)
if [ "$CURRENT_HOUR" -ge 2 ] && [ "$CURRENT_HOUR" -le 4 ]; then
    echo "Running index optimization during maintenance window..."
    
    # Generate maintenance report
    python3 /opt/thai-tokenizer/scripts/meilisearch-maintenance.py
    
    # Optimize each index
    curl -X PATCH "http://your-meilisearch:7700/indexes/documents/settings" \
        -H "Authorization: Bearer YOUR_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{
            "searchableAttributes": ["content", "title"],
            "filterableAttributes": ["language", "type"],
            "sortableAttributes": ["created_at"]
        }'
    
    echo "Index optimization completed"
else
    echo "Skipping optimization - outside maintenance window"
fi
```

## Performance Monitoring

### Performance Metrics Collection

```python
#!/usr/bin/env python3
# performance-metrics.py

import psutil
import requests
import json
import time
from datetime import datetime

class PerformanceMonitor:
    def __init__(self, service_url='http://localhost:8000'):
        self.service_url = service_url
        self.process_name = 'thai-tokenizer'
    
    def get_system_metrics(self):
        """Collect system-level metrics"""
        return {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_usage': psutil.disk_usage('/').percent,
            'load_average': psutil.getloadavg(),
            'network_io': psutil.net_io_counters()._asdict()
        }
    
    def get_process_metrics(self):
        """Collect process-specific metrics"""
        metrics = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            if self.process_name in proc.info['name']:
                metrics.append(proc.info)
        return metrics
    
    def get_service_metrics(self):
        """Collect service-specific metrics"""
        try:
            response = requests.get(f'{self.service_url}/metrics', timeout=10)
            if response.status_code == 200:
                return response.text
        except Exception as e:
            return {'error': str(e)}
        return None
    
    def test_performance(self):
        """Run performance test"""
        test_data = {'text': 'สวัสดีครับผมชื่อจอห์นมาจากประเทศไทย'}
        
        start_time = time.time()
        try:
            response = requests.post(
                f'{self.service_url}/tokenize',
                json=test_data,
                timeout=10
            )
            end_time = time.time()
            
            return {
                'response_time': (end_time - start_time) * 1000,  # ms
                'status_code': response.status_code,
                'success': response.status_code == 200
            }
        except Exception as e:
            return {
                'response_time': None,
                'status_code': None,
                'success': False,
                'error': str(e)
            }
    
    def collect_all_metrics(self):
        """Collect comprehensive metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'system': self.get_system_metrics(),
            'processes': self.get_process_metrics(),
            'service': self.get_service_metrics(),
            'performance_test': self.test_performance()
        }

if __name__ == '__main__':
    monitor = PerformanceMonitor()
    metrics = monitor.collect_all_metrics()
    
    # Print summary
    print(f"CPU: {metrics['system']['cpu_percent']}%")
    print(f"Memory: {metrics['system']['memory_percent']}%")
    print(f"Response time: {metrics['performance_test']['response_time']}ms")
    
    # Save detailed metrics
    with open(f'/tmp/performance-metrics-{datetime.now().strftime("%Y%m%d-%H%M%S")}.json', 'w') as f:
        json.dump(metrics, f, indent=2)
```

### Automated Performance Alerts

```bash
#!/bin/bash
# performance-alerts.sh

# Thresholds
CPU_THRESHOLD=80
MEMORY_THRESHOLD=85
RESPONSE_TIME_THRESHOLD=100

# Get current metrics
METRICS=$(python3 /opt/thai-tokenizer/scripts/performance-metrics.py)
CPU_USAGE=$(echo "$METRICS" | grep "CPU:" | awk '{print $2}' | sed 's/%//')
MEMORY_USAGE=$(echo "$METRICS" | grep "Memory:" | awk '{print $2}' | sed 's/%//')
RESPONSE_TIME=$(echo "$METRICS" | grep "Response time:" | awk '{print $3}' | sed 's/ms//')

# Check thresholds and send alerts
if (( $(echo "$CPU_USAGE > $CPU_THRESHOLD" | bc -l) )); then
    echo "ALERT: High CPU usage: ${CPU_USAGE}%" | \
        mail -s "Thai Tokenizer CPU Alert" admin@company.com
fi

if (( $(echo "$MEMORY_USAGE > $MEMORY_THRESHOLD" | bc -l) )); then
    echo "ALERT: High memory usage: ${MEMORY_USAGE}%" | \
        mail -s "Thai Tokenizer Memory Alert" admin@company.com
fi

if (( $(echo "$RESPONSE_TIME > $RESPONSE_TIME_THRESHOLD" | bc -l) )); then
    echo "ALERT: Slow response time: ${RESPONSE_TIME}ms" | \
        mail -s "Thai Tokenizer Performance Alert" admin@company.com
fi
```

## Security Maintenance

### Security Audit Procedures

```bash
#!/bin/bash
# security-audit.sh

echo "=== Security Audit - $(date) ==="

# Check file permissions
echo "Checking file permissions..."
find /opt/thai-tokenizer -type f -perm /o+w -exec ls -la {} \;
find /etc/thai-tokenizer -type f -perm /o+r -exec ls -la {} \;

# Check for unauthorized access attempts
echo "Checking for unauthorized access attempts..."
grep -i "unauthorized\|forbidden\|denied" /opt/thai-tokenizer/logs/thai-tokenizer.log | \
    tail -10

# Check SSL certificate status
if [ -f "/etc/ssl/certs/thai-tokenizer.crt" ]; then
    echo "SSL certificate status:"
    openssl x509 -in /etc/ssl/certs/thai-tokenizer.crt -noout -dates
    
    # Check if certificate expires within 30 days
    EXPIRY_DATE=$(openssl x509 -in /etc/ssl/certs/thai-tokenizer.crt -noout -enddate | cut -d= -f2)
    EXPIRY_TIMESTAMP=$(date -d "$EXPIRY_DATE" +%s)
    CURRENT_TIMESTAMP=$(date +%s)
    DAYS_UNTIL_EXPIRY=$(( (EXPIRY_TIMESTAMP - CURRENT_TIMESTAMP) / 86400 ))
    
    if [ $DAYS_UNTIL_EXPIRY -lt 30 ]; then
        echo "WARNING: SSL certificate expires in $DAYS_UNTIL_EXPIRY days"
    fi
fi

# Check for security updates
echo "Checking for security updates..."
/opt/thai-tokenizer/venv/bin/pip list --outdated | grep -E "(security|vulnerability)"

# Audit API key usage
echo "API key usage audit:"
grep "api_key" /opt/thai-tokenizer/logs/thai-tokenizer.log | \
    awk '{print $1, $2}' | sort | uniq -c | sort -nr | head -10

# Generate security report
cat > /tmp/security-audit-$(date +%Y%m%d).txt << EOF
Security Audit Report - $(date)
===============================
File permission issues: $(find /opt/thai-tokenizer -type f -perm /o+w | wc -l)
Unauthorized access attempts: $(grep -i "unauthorized\|forbidden\|denied" /opt/thai-tokenizer/logs/thai-tokenizer.log | wc -l)
SSL certificate days until expiry: ${DAYS_UNTIL_EXPIRY:-"N/A"}
Security updates available: $(pip list --outdated | grep -E "(security|vulnerability)" | wc -l)
EOF

echo "Security audit completed. Report saved to /tmp/security-audit-$(date +%Y%m%d).txt"
```

### API Key Rotation

```bash
#!/bin/bash
# rotate-api-keys.sh

echo "=== API Key Rotation Procedure ==="

# Generate new API key
NEW_API_KEY=$(openssl rand -hex 32)

# Update configuration with new key
CONFIG_FILE="/opt/thai-tokenizer/config/config.json"
BACKUP_FILE="/opt/thai-tokenizer/config/config.json.backup.$(date +%Y%m%d)"

# Backup current configuration
cp "$CONFIG_FILE" "$BACKUP_FILE"

# Update API key in configuration
python3 << EOF
import json

with open('$CONFIG_FILE', 'r') as f:
    config = json.load(f)

# Update Meilisearch API key
config['meilisearch_config']['api_key'] = '$NEW_API_KEY'

# Update service API key if enabled
if config.get('security_config', {}).get('api_key_required'):
    config['security_config']['api_key'] = '$(openssl rand -hex 16)'

with open('$CONFIG_FILE', 'w') as f:
    json.dump(config, f, indent=2)
EOF

# Restart service to apply new configuration
echo "Restarting service with new API keys..."
/opt/thai-tokenizer/bin/restart-service.sh

# Verify service is working with new keys
sleep 10
if curl -f http://localhost:8000/health; then
    echo "API key rotation successful"
    
    # Clean up old backup (keep last 5)
    ls -t /opt/thai-tokenizer/config/config.json.backup.* | tail -n +6 | xargs rm -f
else
    echo "API key rotation failed. Restoring backup..."
    cp "$BACKUP_FILE" "$CONFIG_FILE"
    /opt/thai-tokenizer/bin/restart-service.sh
    exit 1
fi
```

## Capacity Planning

### Capacity Monitoring

```python
#!/usr/bin/env python3
# capacity-monitor.py

import psutil
import json
import time
from datetime import datetime, timedelta

class CapacityMonitor:
    def __init__(self):
        self.metrics_history = []
    
    def collect_metrics(self):
        """Collect current capacity metrics"""
        return {
            'timestamp': datetime.now().isoformat(),
            'cpu': {
                'usage_percent': psutil.cpu_percent(interval=1),
                'load_average': psutil.getloadavg(),
                'core_count': psutil.cpu_count()
            },
            'memory': {
                'total_gb': psutil.virtual_memory().total / (1024**3),
                'used_gb': psutil.virtual_memory().used / (1024**3),
                'usage_percent': psutil.virtual_memory().percent,
                'available_gb': psutil.virtual_memory().available / (1024**3)
            },
            'disk': {
                'total_gb': psutil.disk_usage('/').total / (1024**3),
                'used_gb': psutil.disk_usage('/').used / (1024**3),
                'usage_percent': psutil.disk_usage('/').percent,
                'free_gb': psutil.disk_usage('/').free / (1024**3)
            },
            'network': {
                'bytes_sent': psutil.net_io_counters().bytes_sent,
                'bytes_recv': psutil.net_io_counters().bytes_recv,
                'packets_sent': psutil.net_io_counters().packets_sent,
                'packets_recv': psutil.net_io_counters().packets_recv
            }
        }
    
    def analyze_trends(self, days=7):
        """Analyze capacity trends over specified days"""
        # Load historical data
        try:
            with open('/tmp/capacity-history.json', 'r') as f:
                history = json.load(f)
        except FileNotFoundError:
            history = []
        
        # Filter data for specified period
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_data = [
            entry for entry in history
            if datetime.fromisoformat(entry['timestamp']) > cutoff_date
        ]
        
        if not recent_data:
            return {'error': 'Insufficient historical data'}
        
        # Calculate trends
        cpu_values = [entry['cpu']['usage_percent'] for entry in recent_data]
        memory_values = [entry['memory']['usage_percent'] for entry in recent_data]
        disk_values = [entry['disk']['usage_percent'] for entry in recent_data]
        
        return {
            'period_days': days,
            'data_points': len(recent_data),
            'cpu': {
                'average': sum(cpu_values) / len(cpu_values),
                'peak': max(cpu_values),
                'trend': 'increasing' if cpu_values[-1] > cpu_values[0] else 'decreasing'
            },
            'memory': {
                'average': sum(memory_values) / len(memory_values),
                'peak': max(memory_values),
                'trend': 'increasing' if memory_values[-1] > memory_values[0] else 'decreasing'
            },
            'disk': {
                'average': sum(disk_values) / len(disk_values),
                'peak': max(disk_values),
                'trend': 'increasing' if disk_values[-1] > disk_values[0] else 'decreasing'
            }
        }
    
    def predict_capacity_needs(self):
        """Predict future capacity needs based on trends"""
        trends = self.analyze_trends(30)  # 30-day trend
        
        if 'error' in trends:
            return trends
        
        predictions = {}
        
        # CPU prediction
        if trends['cpu']['trend'] == 'increasing' and trends['cpu']['peak'] > 70:
            predictions['cpu'] = 'Consider adding CPU cores or optimizing workload'
        
        # Memory prediction
        if trends['memory']['trend'] == 'increasing' and trends['memory']['peak'] > 80:
            predictions['memory'] = 'Consider adding RAM or optimizing memory usage'
        
        # Disk prediction
        if trends['disk']['trend'] == 'increasing' and trends['disk']['peak'] > 85:
            predictions['disk'] = 'Consider adding storage or implementing cleanup policies'
        
        return predictions

if __name__ == '__main__':
    monitor = CapacityMonitor()
    
    # Collect current metrics
    current_metrics = monitor.collect_metrics()
    
    # Load and update history
    try:
        with open('/tmp/capacity-history.json', 'r') as f:
            history = json.load(f)
    except FileNotFoundError:
        history = []
    
    history.append(current_metrics)
    
    # Keep only last 90 days of data
    cutoff_date = datetime.now() - timedelta(days=90)
    history = [
        entry for entry in history
        if datetime.fromisoformat(entry['timestamp']) > cutoff_date
    ]
    
    # Save updated history
    with open('/tmp/capacity-history.json', 'w') as f:
        json.dump(history, f, indent=2)
    
    # Generate capacity report
    trends = monitor.analyze_trends(7)
    predictions = monitor.predict_capacity_needs()
    
    report = {
        'current_metrics': current_metrics,
        'trends': trends,
        'predictions': predictions,
        'recommendations': []
    }
    
    # Add recommendations based on current usage
    if current_metrics['cpu']['usage_percent'] > 80:
        report['recommendations'].append('High CPU usage detected - consider scaling')
    
    if current_metrics['memory']['usage_percent'] > 85:
        report['recommendations'].append('High memory usage detected - consider adding RAM')
    
    if current_metrics['disk']['usage_percent'] > 90:
        report['recommendations'].append('Low disk space - implement cleanup or add storage')
    
    print(json.dumps(report, indent=2))
```

This comprehensive maintenance procedures document provides detailed guidance for maintaining, updating, and managing the Thai Tokenizer service in production environments. The procedures cover routine maintenance, updates, health monitoring, log management, performance monitoring, security maintenance, and capacity planning.