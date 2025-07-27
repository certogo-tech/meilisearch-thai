# SSL/TLS Certificates Directory

This directory contains SSL/TLS certificates and related security files for the Thai Tokenizer project. This directory is used for HTTPS configuration and secure communication between services.

## 🔒 Directory Purpose

### SSL Certificate Management
- **Development Certificates**: Self-signed certificates for local development
- **Production Certificates**: CA-signed certificates for production deployment
- **Certificate Authority Files**: Root and intermediate CA certificates
- **Private Keys**: Encrypted private keys for certificate authentication

## 📁 Expected File Structure

```
ssl/
├── certs/                     # Certificate files
│   ├── server.crt            # Server certificate
│   ├── server.key            # Server private key
│   ├── ca.crt                # Certificate Authority certificate
│   └── intermediate.crt      # Intermediate CA certificate (if applicable)
├── development/               # Development certificates
│   ├── localhost.crt         # Local development certificate
│   ├── localhost.key         # Local development private key
│   └── ca-dev.crt            # Development CA certificate
├── production/                # Production certificates
│   ├── domain.crt            # Production domain certificate
│   ├── domain.key            # Production private key
│   └── chain.crt             # Certificate chain
└── scripts/                   # Certificate management scripts
    ├── generate_dev_certs.sh  # Generate development certificates
    ├── renew_certs.sh         # Certificate renewal script
    └── validate_certs.sh      # Certificate validation script
```

## 🛡️ Security Best Practices

### Certificate Security
1. **Private Key Protection**: Never commit private keys to version control
2. **File Permissions**: Restrict access to certificate files (600 for keys, 644 for certificates)
3. **Encryption**: Use encrypted private keys with strong passphrases
4. **Regular Rotation**: Rotate certificates before expiration
5. **Backup**: Securely backup certificates and keys

### File Permissions
```bash
# Set proper permissions for certificate files
chmod 644 ssl/certs/*.crt
chmod 600 ssl/certs/*.key
chmod 700 ssl/

# Ensure only root/service user can access private keys
chown root:ssl-cert ssl/certs/*.key
```

## 🔧 Development Setup

### Generate Development Certificates
```bash
# Generate self-signed certificate for localhost
openssl req -x509 -newkey rsa:4096 -keyout ssl/development/localhost.key \
  -out ssl/development/localhost.crt -days 365 -nodes \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Generate certificate with SAN for multiple domains
openssl req -x509 -newkey rsa:4096 -keyout ssl/development/localhost.key \
  -out ssl/development/localhost.crt -days 365 -nodes \
  -config <(
    echo '[dn]'
    echo 'CN=localhost'
    echo '[req]'
    echo 'distinguished_name = dn'
    echo '[SAN]'
    echo 'subjectAltName=DNS:localhost,DNS:*.localhost,IP:127.0.0.1'
  ) -extensions SAN
```

### Docker Configuration
```yaml
# docker-compose.yml
services:
  nginx:
    volumes:
      - ./ssl/development:/etc/nginx/ssl:ro
    ports:
      - "443:443"
  
  thai-tokenizer:
    environment:
      - SSL_CERT_PATH=/app/ssl/certs/server.crt
      - SSL_KEY_PATH=/app/ssl/certs/server.key
    volumes:
      - ./ssl/certs:/app/ssl/certs:ro
```

### Nginx SSL Configuration
```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name localhost;
    
    ssl_certificate /etc/nginx/ssl/localhost.crt;
    ssl_certificate_key /etc/nginx/ssl/localhost.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;
    ssl_prefer_server_ciphers off;
    
    location / {
        proxy_pass http://thai-tokenizer:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 🚀 Production Deployment

### Certificate Acquisition
```bash
# Using Let's Encrypt with Certbot
certbot certonly --webroot -w /var/www/html \
  -d yourdomain.com -d www.yourdomain.com

# Copy certificates to ssl directory
cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem ssl/production/domain.crt
cp /etc/letsencrypt/live/yourdomain.com/privkey.pem ssl/production/domain.key
```

### Certificate Renewal
```bash
# Automated renewal with cron
0 12 * * * /usr/bin/certbot renew --quiet --post-hook "docker compose restart nginx"

# Manual renewal
certbot renew --dry-run
```

### Production Security Configuration
```bash
# Strong SSL configuration for production
ssl_protocols TLSv1.2 TLSv1.3;
ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384;
ssl_prefer_server_ciphers off;

# HSTS (HTTP Strict Transport Security)
add_header Strict-Transport-Security "max-age=63072000" always;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
```

## 🔍 Certificate Management

### Certificate Validation
```bash
# Check certificate expiration
openssl x509 -in ssl/certs/server.crt -text -noout | grep "Not After"

# Verify certificate chain
openssl verify -CAfile ssl/certs/ca.crt ssl/certs/server.crt

# Test SSL connection
openssl s_client -connect localhost:443 -servername localhost
```

### Certificate Information
```bash
# View certificate details
openssl x509 -in ssl/certs/server.crt -text -noout

# Check private key
openssl rsa -in ssl/certs/server.key -check

# Verify certificate and key match
openssl x509 -noout -modulus -in ssl/certs/server.crt | openssl md5
openssl rsa -noout -modulus -in ssl/certs/server.key | openssl md5
```

### Monitoring and Alerts
```bash
# Certificate expiration monitoring
#!/bin/bash
CERT_FILE="ssl/certs/server.crt"
DAYS_UNTIL_EXPIRY=$(openssl x509 -in $CERT_FILE -noout -dates | grep notAfter | cut -d= -f2 | xargs -I {} date -d {} +%s)
CURRENT_DATE=$(date +%s)
DAYS_LEFT=$(( ($DAYS_UNTIL_EXPIRY - $CURRENT_DATE) / 86400 ))

if [ $DAYS_LEFT -lt 30 ]; then
    echo "WARNING: Certificate expires in $DAYS_LEFT days"
fi
```

## 🚨 Troubleshooting

### Common SSL Issues

#### Certificate Not Trusted
```bash
# Add CA certificate to system trust store
sudo cp ssl/certs/ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

#### Permission Denied
```bash
# Fix certificate file permissions
sudo chown -R www-data:www-data ssl/
chmod 644 ssl/certs/*.crt
chmod 600 ssl/certs/*.key
```

#### Certificate Mismatch
```bash
# Verify certificate matches domain
openssl x509 -in ssl/certs/server.crt -text -noout | grep -A1 "Subject Alternative Name"
```

### SSL Testing Tools
```bash
# Test SSL configuration
nmap --script ssl-enum-ciphers -p 443 localhost

# SSL Labs test (for public domains)
curl -s "https://api.ssllabs.com/api/v3/analyze?host=yourdomain.com"

# Local SSL testing
testssl.sh https://localhost:443
```

## 📋 Maintenance Tasks

### Regular Maintenance
```bash
# Weekly certificate check
./ssl/scripts/validate_certs.sh

# Monthly certificate renewal check
certbot certificates

# Quarterly security audit
nmap --script ssl-cert,ssl-enum-ciphers -p 443 yourdomain.com
```

### Backup and Recovery
```bash
# Backup certificates
tar -czf backups/ssl-backup-$(date +%Y%m%d).tar.gz ssl/

# Restore certificates
tar -xzf backups/ssl-backup-20240115.tar.gz

# Secure backup to remote location
gpg --cipher-algo AES256 --compress-algo 1 --s2k-cipher-algo AES256 \
    --s2k-digest-algo SHA512 --s2k-mode 3 --s2k-count 65536 \
    --force-mdc --encrypt -r backup@company.com ssl-backup.tar.gz
```

## 🔗 Related Documentation

- **[Deployment Guide](../docs/deployment/PRODUCTION_DEPLOYMENT.md)** - Production SSL setup
- **[Security Guide](../docs/security.md)** - Complete security configuration
- **[Nginx Configuration](../deployment/docker/nginx.conf)** - Web server SSL setup
- **[Monitoring Setup](../monitoring/index.md)** - SSL certificate monitoring

## ⚠️ Important Notes

1. **Never commit private keys** to version control
2. **Use environment variables** for certificate passphrases
3. **Regularly update** SSL/TLS configurations
4. **Monitor certificate expiration** with automated alerts
5. **Test SSL configuration** after any changes
6. **Keep backups** of certificates and keys in secure locations

---

**Need help with SSL setup?** Check the [Deployment Guide](../docs/deployment/PRODUCTION_DEPLOYMENT.md) for complete SSL configuration instructions.