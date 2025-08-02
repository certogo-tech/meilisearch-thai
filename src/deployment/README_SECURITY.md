# Security Implementation for On-Premise Deployment

This document describes the comprehensive security features implemented for the Thai Tokenizer on-premise deployment.

## Overview

The security implementation provides multiple layers of protection:

- **Credential Management**: Secure storage and encryption of sensitive credentials
- **API Key Authentication**: Optional API key-based authentication
- **Network Security**: Firewall configuration and access control
- **SSL/TLS Support**: Certificate management and HTTPS configuration
- **Configuration Protection**: File encryption and secure permissions
- **Security Auditing**: Comprehensive security assessment and compliance checking

## Components

### 1. Secure Credential Store (`security.py`)

The `SecureCredentialStore` class provides encrypted storage for sensitive credentials:

```python
from src.deployment.security import SecureCredentialStore, CredentialType

# Initialize with master password
store = SecureCredentialStore(
    store_path="/etc/thai-tokenizer/credentials.json",
    master_password="your_master_password"
)

# Store a credential
store.store_credential(
    key="meilisearch_api_key",
    value="your_api_key_here",
    credential_type=CredentialType.API_KEY,
    expires_in_days=365
)

# Retrieve a credential
api_key = store.retrieve_credential("meilisearch_api_key")
```

**Features:**
- AES-256 encryption using Fernet
- PBKDF2 key derivation with 100,000 iterations
- Secure file permissions (0600)
- Credential expiration support
- Audit logging

### 2. API Key Management (`security.py`)

The `APIKeyManager` class handles API key generation and validation:

```python
from src.deployment.security import APIKeyManager

api_manager = APIKeyManager(credential_store)

# Generate and store API key
api_key = api_manager.store_api_key(
    key_name="service_auth",
    expires_in_days=365
)

# Validate API key
is_valid = api_manager.validate_api_key("service_auth", provided_key)

# Rotate API key
new_key = api_manager.rotate_api_key("service_auth")
```

**Features:**
- Cryptographically secure key generation
- Constant-time comparison to prevent timing attacks
- Key rotation and expiration
- Usage tracking and audit logging

### 3. SSL/TLS Configuration (`security.py`)

The `SSLConfigurationManager` class manages SSL certificates:

```python
from src.deployment.security import SSLConfigurationManager

ssl_manager = SSLConfigurationManager(credential_store)

# Generate self-signed certificate for development
cert_pem, key_pem = ssl_manager.generate_self_signed_certificate(
    cert_name="service_ssl",
    common_name="localhost",
    validity_days=365
)

# Validate certificate
validation = ssl_manager.validate_certificate_chain(cert_pem)
```

**Features:**
- Self-signed certificate generation
- Certificate chain validation
- Certificate expiration monitoring
- Secure certificate storage

### 4. Network Security (`network_security.py`)

The `NetworkSecurityManager` class handles network-level security:

```python
from src.deployment.network_security import NetworkSecurityManager

network_manager = NetworkSecurityManager(config)

# Generate firewall rules
rules = network_manager.generate_firewall_rules()

# Apply firewall rules
result = network_manager.apply_firewall_rules(rules, dry_run=False)

# Validate network configuration
validation = network_manager.validate_network_access()
```

**Features:**
- Automatic firewall detection (UFW, iptables, firewalld)
- Firewall rule generation and application
- CORS configuration management
- Network access validation
- Port availability checking

### 5. Security Auditing (`security_audit.py`)

The `SecurityAuditor` class performs comprehensive security assessments:

```python
from src.deployment.security_audit import SecurityAuditor

auditor = SecurityAuditor(config, credential_store)

# Perform comprehensive audit
report = auditor.perform_comprehensive_audit()

# Save audit report
auditor.save_audit_report(report, "/var/log/security_audit.json")
```

**Audit Categories:**
- Authentication mechanisms
- Authorization and access control
- Encryption and data protection
- Network security configuration
- Configuration file security
- System-level security
- Compliance framework alignment (NIST, CIS, PCI-DSS)

### 6. Security Manager (`security_manager.py`)

The `DeploymentSecurityManager` class provides a unified interface:

```python
from src.deployment.security_manager import DeploymentSecurityManager

security_manager = DeploymentSecurityManager(
    config=deployment_config,
    master_password="your_master_password"
)

# Set up comprehensive security
setup_result = security_manager.setup_security()

# Perform security audit
audit_result = security_manager.audit_security()

# Rotate credentials
rotation_result = security_manager.rotate_credentials()

# Get security status
status = security_manager.get_security_status()
```

## Security Levels

The implementation supports three security levels:

### Basic Security
- Minimal authentication requirements
- Basic firewall configuration
- Standard logging
- Self-signed certificates allowed

### Standard Security (Default)
- API key authentication recommended
- Comprehensive firewall rules
- Enhanced logging and monitoring
- Certificate validation

### High Security
- API key authentication required
- Strict firewall rules and host restrictions
- Comprehensive audit logging
- CA-signed certificates required
- Configuration file encryption
- Regular security audits

## Configuration

### Environment Variables

The security system uses these environment variables:

```bash
# Master password for credential encryption
THAI_TOKENIZER_MASTER_PASSWORD=your_secure_master_password

# Security level
THAI_TOKENIZER_SECURITY_LEVEL=standard

# API key authentication
THAI_TOKENIZER_API_KEY_REQUIRED=true
THAI_TOKENIZER_API_KEY=your_api_key_here

# SSL/TLS configuration
THAI_TOKENIZER_ENABLE_HTTPS=true
THAI_TOKENIZER_SSL_CERT_PATH=/etc/ssl/certs/thai-tokenizer.crt
THAI_TOKENIZER_SSL_KEY_PATH=/etc/ssl/private/thai-tokenizer.key

# Network security
THAI_TOKENIZER_ALLOWED_HOSTS=localhost,127.0.0.1,your-server.com
THAI_TOKENIZER_CORS_ORIGINS=https://your-app.com
```

### Configuration File

Security settings in the deployment configuration:

```python
security_config = SecurityConfig(
    security_level=SecurityLevel.STANDARD,
    allowed_hosts=["localhost", "127.0.0.1"],
    cors_origins=["https://your-app.com"],
    api_key_required=True,
    api_key=SecretStr("your_api_key"),
    enable_https=True,
    ssl_cert_path="/etc/ssl/certs/thai-tokenizer.crt",
    ssl_key_path="/etc/ssl/private/thai-tokenizer.key",
    firewall_rules=[
        "allow tcp 8000 from 192.168.1.0/24 comment 'Thai Tokenizer'"
    ]
)
```

## Deployment Integration

### Docker Deployment

```dockerfile
# Set security environment variables
ENV THAI_TOKENIZER_SECURITY_LEVEL=standard
ENV THAI_TOKENIZER_API_KEY_REQUIRED=true

# Copy certificates
COPY ssl/cert.pem /etc/ssl/certs/thai-tokenizer.crt
COPY ssl/key.pem /etc/ssl/private/thai-tokenizer.key

# Set secure permissions
RUN chmod 644 /etc/ssl/certs/thai-tokenizer.crt && \
    chmod 600 /etc/ssl/private/thai-tokenizer.key
```

### Systemd Deployment

```ini
[Service]
Environment=THAI_TOKENIZER_SECURITY_LEVEL=standard
Environment=THAI_TOKENIZER_API_KEY_REQUIRED=true
EnvironmentFile=/etc/thai-tokenizer/environment

# Security settings
PrivateDevices=true
ProtectClock=true
ProtectKernelTunables=true
RestrictRealtime=true
```

### Standalone Deployment

```bash
#!/bin/bash
# Set security environment
export THAI_TOKENIZER_SECURITY_LEVEL=standard
export THAI_TOKENIZER_API_KEY_REQUIRED=true

# Configure firewall
ufw allow 8000/tcp comment 'Thai Tokenizer'
ufw enable

# Start service with security
python -m src.api.main
```

## Security Best Practices

### 1. Credential Management
- Use strong master passwords (32+ characters)
- Rotate credentials regularly (annually recommended)
- Store credentials in the secure credential store
- Never log credential values

### 2. Network Security
- Enable firewall and configure specific rules
- Restrict allowed hosts to known IP addresses
- Use HTTPS/TLS for all communications
- Regularly update SSL certificates

### 3. Access Control
- Enable API key authentication for production
- Use strong API keys (32+ characters)
- Implement proper CORS policies
- Run service as non-root user

### 4. Monitoring and Auditing
- Enable comprehensive logging
- Perform regular security audits
- Monitor for security events
- Set up alerting for security issues

### 5. System Security
- Keep system packages updated
- Use secure file permissions
- Encrypt sensitive configuration files
- Regular security assessments

## Compliance

The security implementation supports compliance with:

- **NIST Cybersecurity Framework**: Identify, Protect, Detect, Respond, Recover
- **CIS Controls**: Critical Security Controls for Effective Cyber Defense
- **PCI-DSS**: Payment Card Industry Data Security Standard (relevant controls)
- **ISO 27001**: Information Security Management Systems
- **GDPR**: General Data Protection Regulation (data protection aspects)

## Troubleshooting

### Common Issues

1. **Credential Store Access Denied**
   ```bash
   # Check file permissions
   ls -la /etc/thai-tokenizer/credentials.json
   # Should be 600 (rw-------)
   
   # Fix permissions
   chmod 600 /etc/thai-tokenizer/credentials.json
   ```

2. **SSL Certificate Issues**
   ```bash
   # Validate certificate
   openssl x509 -in /etc/ssl/certs/thai-tokenizer.crt -text -noout
   
   # Check certificate expiration
   openssl x509 -in /etc/ssl/certs/thai-tokenizer.crt -enddate -noout
   ```

3. **Firewall Configuration**
   ```bash
   # Check UFW status
   ufw status verbose
   
   # Check iptables rules
   iptables -L -n
   ```

4. **API Key Validation Failures**
   ```bash
   # Check API key in logs (masked)
   grep "API key" /var/log/thai-tokenizer/service.log
   
   # Validate API key format
   echo -n "your_api_key" | wc -c  # Should be 32+ characters
   ```

### Security Audit

Run regular security audits:

```python
from src.deployment.security_audit import SecurityAuditor

auditor = SecurityAuditor(config)
report = auditor.perform_comprehensive_audit()

print(f"Security Score: {report.security_score}/100")
print(f"Security Grade: {report.security_grade}")
print(f"Critical Issues: {report.critical_findings}")
```

## Dependencies

The security implementation requires:

```bash
pip install cryptography>=3.4.8  # For encryption
pip install psutil>=5.8.0        # For system information
pip install httpx>=0.24.0        # For HTTP connections
```

## Support

For security-related issues:

1. Check the security audit report for specific recommendations
2. Review the troubleshooting section above
3. Ensure all dependencies are installed and up to date
4. Verify environment variables and configuration
5. Check system logs for security-related errors

Remember: Security is an ongoing process. Regularly review and update your security configuration based on audit findings and changing requirements.