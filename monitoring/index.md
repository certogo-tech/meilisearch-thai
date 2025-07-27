# Monitoring Directory

This directory contains monitoring, observability, and alerting configurations for the Thai Tokenizer MeiliSearch integration system.

## 📁 Directory Structure

```
monitoring/
├── grafana/           # Grafana dashboards and configuration
│   ├── dashboards/   # Dashboard JSON files
│   ├── datasources/  # Data source configurations
│   └── README.md     # Grafana setup guide
├── prometheus/        # Prometheus monitoring configuration
│   ├── prometheus.yml # Main Prometheus configuration
│   ├── rules/        # Alerting rules
│   └── README.md     # Prometheus setup guide
├── logging/          # Centralized logging configuration
│   ├── logstash/     # Logstash configuration
│   ├── elasticsearch/ # Elasticsearch setup
│   └── README.md     # Logging setup guide
├── alerts/           # Alerting rules and configurations
│   ├── rules.yml     # Alert rule definitions
│   ├── channels.yml  # Notification channels
│   └── README.md     # Alerting setup guide
└── docker-compose.monitoring.yml # Monitoring stack deployment
```

## 📊 Monitoring Components

### [Grafana Dashboards](grafana/)
**Purpose**: Visual monitoring and analytics dashboards

**Features**:
- **System Overview**: High-level system health and performance
- **Thai Tokenizer Metrics**: Tokenization performance and accuracy
- **MeiliSearch Metrics**: Search performance and indexing stats
- **Infrastructure Metrics**: CPU, memory, disk, and network usage
- **Application Metrics**: API response times, error rates, throughput

**Key Dashboards**:
- `thai-tokenizer-overview.json` - Main system dashboard
- `performance-metrics.json` - Performance monitoring
- `error-tracking.json` - Error analysis and debugging
- `capacity-planning.json` - Resource usage and scaling

### [Prometheus Monitoring](prometheus/)
**Purpose**: Metrics collection and time-series database

**Metrics Collected**:
- **Application Metrics**: Request rates, response times, error counts
- **Business Metrics**: Tokenization accuracy, search quality
- **Infrastructure Metrics**: System resources, container health
- **Custom Metrics**: Thai-specific performance indicators

**Configuration**:
- `prometheus.yml` - Main configuration with scrape targets
- `rules/` - Alerting rules and recording rules
- Service discovery for dynamic environments

### [Centralized Logging](logging/)
**Purpose**: Collect, process, and analyze system logs

**Components**:
- **Log Collection**: Structured JSON logging from all services
- **Log Processing**: Parse and enrich log data
- **Log Storage**: Searchable log storage and retention
- **Log Analysis**: Search, filter, and analyze log patterns

**Log Sources**:
- Thai Tokenizer API logs
- MeiliSearch operation logs
- Container and infrastructure logs
- Application performance logs

### [Alerting System](alerts/)
**Purpose**: Proactive monitoring and incident response

**Alert Categories**:
- **Critical**: Service down, data loss, security breaches
- **Warning**: Performance degradation, resource constraints
- **Info**: Deployment events, configuration changes

**Notification Channels**:
- Email notifications for critical alerts
- Slack integration for team notifications
- PagerDuty for on-call escalation
- Webhook integrations for custom workflows

## 🚀 Quick Setup

### Start Monitoring Stack
```bash
# Start monitoring services
docker compose -f monitoring/docker-compose.monitoring.yml up -d

# Access dashboards
open http://localhost:3000  # Grafana
open http://localhost:9090  # Prometheus
```

### Configure Alerts
```bash
# Edit alert rules
nano monitoring/alerts/rules.yml

# Reload Prometheus configuration
curl -X POST http://localhost:9090/-/reload

# Test alert rules
promtool check rules monitoring/alerts/rules.yml
```

### View Logs
```bash
# View application logs
docker compose logs -f thai-tokenizer

# Search logs with specific filters
curl "http://localhost:9200/_search" -H 'Content-Type: application/json' -d'
{
  "query": {
    "match": {
      "service": "thai-tokenizer"
    }
  }
}'
```

## 📈 Key Metrics

### Performance Metrics
- **Tokenization Latency**: Time to tokenize Thai text
- **Search Response Time**: MeiliSearch query response time
- **Throughput**: Requests per second, documents per second
- **Error Rate**: Failed requests as percentage of total

### Business Metrics
- **Tokenization Accuracy**: Quality of Thai word segmentation
- **Search Relevance**: Quality of search results
- **User Satisfaction**: API usage patterns and success rates
- **System Utilization**: Resource efficiency metrics

### Infrastructure Metrics
- **CPU Usage**: Processor utilization across services
- **Memory Usage**: RAM consumption and garbage collection
- **Disk I/O**: Storage performance and capacity
- **Network**: Bandwidth usage and connection metrics

### Application Metrics
- **API Endpoints**: Response times and error rates per endpoint
- **Database Performance**: Query times and connection pools
- **Cache Performance**: Hit rates and cache efficiency
- **Queue Metrics**: Message processing and backlog

## 🔔 Alerting Rules

### Critical Alerts
```yaml
# Service Down
- alert: ServiceDown
  expr: up == 0
  for: 1m
  labels:
    severity: critical
  annotations:
    summary: "Service {{ $labels.instance }} is down"

# High Error Rate
- alert: HighErrorRate
  expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
  for: 2m
  labels:
    severity: critical
```

### Warning Alerts
```yaml
# High Response Time
- alert: HighResponseTime
  expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
  for: 5m
  labels:
    severity: warning

# High Memory Usage
- alert: HighMemoryUsage
  expr: (node_memory_MemTotal_bytes - node_memory_MemAvailable_bytes) / node_memory_MemTotal_bytes > 0.8
  for: 5m
  labels:
    severity: warning
```

## 📊 Dashboard Configuration

### Grafana Setup
1. **Install Grafana**: Use Docker Compose or direct installation
2. **Configure Data Sources**: Add Prometheus and Elasticsearch
3. **Import Dashboards**: Load pre-built dashboard JSON files
4. **Customize Views**: Adapt dashboards to your needs
5. **Set Up Alerts**: Configure Grafana alerting rules

### Dashboard Categories
- **Executive Dashboard**: High-level KPIs and business metrics
- **Operations Dashboard**: System health and performance
- **Development Dashboard**: Code quality and deployment metrics
- **Troubleshooting Dashboard**: Error analysis and debugging

## 🔍 Log Analysis

### Structured Logging
All services use structured JSON logging:
```json
{
  "timestamp": "2024-01-01T12:00:00Z",
  "level": "INFO",
  "service": "thai-tokenizer",
  "message": "Tokenization completed",
  "duration_ms": 45,
  "text_length": 150,
  "token_count": 23
}
```

### Log Queries
```bash
# Find errors in the last hour
GET /logs/_search
{
  "query": {
    "bool": {
      "must": [
        {"match": {"level": "ERROR"}},
        {"range": {"timestamp": {"gte": "now-1h"}}}
      ]
    }
  }
}

# Analyze tokenization performance
GET /logs/_search
{
  "query": {"match": {"message": "Tokenization completed"}},
  "aggs": {
    "avg_duration": {"avg": {"field": "duration_ms"}}
  }
}
```

## 🔧 Configuration Management

### Environment-Specific Monitoring
- **Development**: Basic monitoring with local storage
- **Staging**: Full monitoring stack for testing
- **Production**: High-availability monitoring with redundancy

### Monitoring as Code
- **Version Control**: All configurations in Git
- **Automated Deployment**: Deploy monitoring with infrastructure
- **Configuration Validation**: Test configurations before deployment
- **Rollback Capability**: Quick rollback for configuration issues

## 📚 Related Documentation

- **[Production Deployment](../docs/deployment/PRODUCTION_DEPLOYMENT.md)** - Production monitoring setup
- **[Performance Optimizations](../docs/deployment/PERFORMANCE_OPTIMIZATIONS.md)** - Performance monitoring
- **[Troubleshooting Guide](../docs/troubleshooting.md)** - Using monitoring for debugging
- **[Development Guide](../docs/development/README.md)** - Development monitoring setup

## 🤝 Contributing Monitoring

To contribute monitoring improvements:

1. **Test thoroughly** in development environment
2. **Follow naming conventions** for metrics and dashboards
3. **Document new metrics** and their purpose
4. **Provide dashboard examples** for new metrics
5. **Update alerting rules** as needed

### Monitoring Guidelines
- Use consistent metric naming conventions
- Include helpful annotations in alerts
- Design dashboards for specific audiences
- Test alert rules before deploying
- Document monitoring procedures

---

**Ready to monitor your system?** Start with the [Grafana setup guide](grafana/README.md) or deploy the full monitoring stack with Docker Compose!