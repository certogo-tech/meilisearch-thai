# Thai Tokenizer - Production Deployment Guide

This guide covers deploying the Thai Tokenizer system to production with proper security, monitoring, and performance optimizations.

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+ and Docker Compose V2
- At least 4GB RAM and 2 CPU cores
- 20GB+ available disk space
- Domain name (for HTTPS setup)

### 1. Clone and Configure

```bash
git clone <repository-url>
cd thai-tokenizer-meilisearch

# Copy and configure production environment
cp config/production/.env.template config/production/.env.prod.local
# Edit config/production/.env.prod.local with your production values
```

### 2. Deploy

```bash
# Deploy production services
./deployment/scripts/deploy_production.sh

# Check status
./deployment/scripts/deploy_production.sh status

# View logs
./deployment/scripts/deploy_production.sh logs
```

### 3. Verify Deployment

```bash
# Run health checks
./deployment/scripts/deploy_production.sh health

# Test tokenization
curl -X POST http://localhost/api/v1/tokenize \
  -H "Content-Type: application/json" \
  -d '{"text": "รถยนต์ไฟฟ้าเป็นเทคโนโลยีใหม่", "engine": "pythainlp"}'
```

## 📋 Production Configuration

### Environment Variables

Edit `config/production/.env.prod.local` with your production values:

```bash
# Security (REQUIRED - Change these!)
MEILISEARCH_API_KEY=your-secure-api-key-here
GRAFANA_PASSWORD=your-secure-password-here

# Domain configuration
CORS_ORIGINS=https://yourdomain.com,https://api.yourdomain.com

# Performance tuning
BATCH_SIZE=50
MAX_RETRIES=5
TIMEOUT_MS=10000
MEILI_MAX_INDEXING_MEMORY=2Gb
MEILI_MAX_INDEXING_THREADS=4
```

### SSL/HTTPS Setup

1. **Obtain SSL certificates** (Let's Encrypt recommended):
```bash
# Using certbot
sudo certbot certonly --standalone -d yourdomain.com
```

2. **Copy certificates**:
```bash
mkdir -p ssl/
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/cert.pem
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/key.pem
```

3. **Enable HTTPS** in `docker/nginx.prod.conf`:
   - Uncomment the HTTPS server block
   - Update server_name with your domain
   - Enable HTTP to HTTPS redirect

## 🏗️ Architecture

### Production Stack

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│     Nginx       │    │  Thai Tokenizer  │    │   MeiliSearch   │
│   (Reverse      │────│    (FastAPI +    │────│   (Search       │
│    Proxy)       │    │    Gunicorn)     │    │    Engine)      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │              ┌──────────────────┐              │
         └──────────────│   Monitoring     │──────────────┘
                        │ (Prometheus +    │
                        │   Grafana)       │
                        └──────────────────┘
```

### Service Configuration

- **Nginx**: Reverse proxy with SSL termination, rate limiting, and caching
- **Thai Tokenizer**: 4 Gunicorn workers with Uvicorn worker class
- **MeiliSearch**: Production-optimized with 2GB indexing memory
- **Monitoring**: Prometheus metrics collection and Grafana dashboards

## 📊 Monitoring

### Enable Monitoring Stack

```bash
# Enable monitoring in environment
echo "COMPOSE_PROFILES=monitoring" >> config/production/.env.prod.local

# Redeploy with monitoring
./deployment/scripts/deploy_production.sh
```

### Access Monitoring

- **Grafana**: http://localhost:3000 (admin/your-password)
- **Prometheus**: http://localhost:9090

### Key Metrics

- **Response Times**: API endpoint latency
- **Throughput**: Requests per second
- **Error Rates**: Failed requests percentage
- **Resource Usage**: CPU, memory, disk usage
- **MeiliSearch**: Index size, search performance

## 🔒 Security

### Network Security

- All services run in isolated Docker network
- Only Nginx exposes ports to host
- Internal service communication only

### API Security

- Rate limiting: 100 requests/minute per IP
- Tokenization endpoints: 200 requests/minute per IP
- Security headers enabled
- CORS properly configured

### Data Security

- MeiliSearch API key authentication
- No sensitive data in logs
- Secure token processing
- Regular security updates

## 🔧 Maintenance

### Backup

```bash
# Manual backup
./deployment/scripts/backup.sh

# Automated backups (add to crontab)
0 2 * * * /path/to/thai-tokenizer/deployment/scripts/backup.sh
```

### Updates

```bash
# Update to new version
git pull origin main
./deployment/scripts/deploy_production.sh

# Rollback if needed
docker compose -f docker-compose.prod.yml down
# Restore from backup
./scripts/restore.sh /path/to/backup
```

### Log Management

```bash
# View logs
./deployment/scripts/deploy_production.sh logs

# View specific service logs
./deployment/scripts/deploy_production.sh logs thai-tokenizer

# Log rotation (configure logrotate)
sudo logrotate -f /etc/logrotate.d/thai-tokenizer
```

## 🚨 Troubleshooting

### Common Issues

1. **Services not starting**:
```bash
# Check logs
./deployment/scripts/deploy_production.sh logs

# Check resource usage
docker stats
```

2. **High memory usage**:
```bash
# Reduce MeiliSearch memory limit
export MEILI_MAX_INDEXING_MEMORY=1Gb
./deployment/scripts/deploy_production.sh restart
```

3. **SSL certificate issues**:
```bash
# Verify certificate files
ls -la ssl/
openssl x509 -in ssl/cert.pem -text -noout
```

### Health Checks

```bash
# System health
./deployment/scripts/deploy_production.sh health

# Detailed health check
curl http://localhost/api/v1/health/detailed

# Service status
docker compose -f docker-compose.prod.yml ps
```

## 📈 Performance Tuning

### Scaling

```bash
# Scale Thai Tokenizer service
docker compose -f docker-compose.prod.yml up -d --scale thai-tokenizer=3

# Update Nginx upstream configuration
# Edit docker/nginx.prod.conf to add more upstream servers
```

### Optimization

1. **CPU Optimization**:
   - Adjust Gunicorn workers based on CPU cores
   - Tune MeiliSearch indexing threads

2. **Memory Optimization**:
   - Monitor memory usage with Grafana
   - Adjust MeiliSearch memory limits
   - Configure swap if needed

3. **Disk Optimization**:
   - Use SSD storage for better performance
   - Configure log rotation
   - Monitor disk usage

## 🔄 CI/CD Integration

### GitHub Actions Example

```yaml
name: Deploy to Production

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Deploy to production
        run: |
          ssh user@server 'cd /path/to/thai-tokenizer && git pull && ./deployment/scripts/deploy_production.sh'
```

## 📞 Support

### Monitoring Alerts

Set up alerts for:
- High error rates (>5%)
- High response times (>500ms)
- Low disk space (<10%)
- Service downtime

### Log Analysis

Key log patterns to monitor:
- Error patterns in application logs
- High response times in access logs
- Failed health checks
- Resource exhaustion warnings

---

## 🎯 Production Checklist

Before going live:

- [ ] SSL certificates configured
- [ ] Environment variables set
- [ ] Monitoring enabled
- [ ] Backups configured
- [ ] Security headers verified
- [ ] Rate limiting tested
- [ ] Health checks passing
- [ ] Performance benchmarks met
- [ ] Documentation updated
- [ ] Team trained on operations

**The Thai Tokenizer system is now ready for production deployment!** 🚀