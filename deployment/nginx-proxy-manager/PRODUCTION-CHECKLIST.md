# Production Deployment Checklist

Use this checklist to ensure all steps are completed for production deployment.

## Pre-Deployment

- [ ] **Environment Setup**
  - [ ] Docker and Docker Compose installed
  - [ ] Nginx Proxy Manager running
  - [ ] Domain name configured in DNS
  - [ ] MeiliSearch instance accessible

- [ ] **Security Configuration**
  - [ ] Generated secure API key
  - [ ] Updated `.env` with production values
  - [ ] Set `API_KEY_REQUIRED=true`
  - [ ] Configured `CORS_ORIGINS` appropriately
  - [ ] Set `LOG_LEVEL=INFO` and `DEBUG=false`

- [ ] **Resource Planning**
  - [ ] Determined CPU and memory requirements
  - [ ] Updated resource limits in `.env`
  - [ ] Planned for scaling if needed

## Deployment Steps

- [ ] **Service Deployment**
  - [ ] Copied `.env.example` to `.env`
  - [ ] Updated all environment variables
  - [ ] Built Docker image
  - [ ] Started service with `docker-compose`
  - [ ] Verified health endpoint responds

- [ ] **NPM Configuration**
  - [ ] Added proxy host in NPM
  - [ ] Configured domain name
  - [ ] Set up SSL certificate
  - [ ] Added security headers
  - [ ] Configured rate limiting
  - [ ] Added custom Nginx configuration

- [ ] **Testing**
  - [ ] Health check passes: `https://search.cads.arda.or.th/health`
  - [ ] Search API works with test query
  - [ ] API key authentication works (if enabled)
  - [ ] SSL certificate is valid
  - [ ] Response times are acceptable

## Post-Deployment

- [ ] **Monitoring Setup**
  - [ ] Prometheus scraping `/metrics` endpoint
  - [ ] Grafana dashboard configured
  - [ ] Alerts configured for downtime
  - [ ] Log aggregation setup

- [ ] **Backup Configuration**
  - [ ] Backup script scheduled
  - [ ] Backup location configured
  - [ ] Restore procedure tested

- [ ] **Documentation**
  - [ ] API endpoints documented
  - [ ] API key shared with authorized users
  - [ ] Support procedures documented
  - [ ] Runbook created for common issues

## Performance Validation

- [ ] **Load Testing**
  - [ ] Baseline performance established
  - [ ] Peak load capacity determined
  - [ ] Response time SLA met
  - [ ] Resource usage acceptable

- [ ] **Search Quality**
  - [ ] Thai tokenization working correctly
  - [ ] Custom dictionary loaded
  - [ ] Search results relevant
  - [ ] Ranking algorithm appropriate

## Security Validation

- [ ] **Access Control**
  - [ ] API key required for access
  - [ ] HTTPS enforced
  - [ ] Security headers present
  - [ ] Rate limiting active

- [ ] **Network Security**
  - [ ] Firewall rules configured
  - [ ] Only necessary ports exposed
  - [ ] MeiliSearch not publicly accessible
  - [ ] Internal services isolated

## Final Checks

- [ ] **Operational Readiness**
  - [ ] Systemd service configured (if applicable)
  - [ ] Auto-restart on failure enabled
  - [ ] Log rotation configured
  - [ ] Monitoring alerts tested

- [ ] **Team Readiness**
  - [ ] Operations team trained
  - [ ] Support procedures documented
  - [ ] Escalation path defined
  - [ ] Maintenance windows scheduled

## Sign-off

| Role | Name | Date | Signature |
|------|------|------|-----------|
| DevOps Engineer | | | |
| Security Review | | | |
| Operations Manager | | | |
| Project Manager | | | |

---

**Notes**: Document any deviations from standard procedure or special configurations below.
