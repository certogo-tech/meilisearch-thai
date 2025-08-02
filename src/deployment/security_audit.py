"""
Security audit and validation tools for on-premise deployment.

This module provides comprehensive security auditing capabilities including:
- System security assessment
- Configuration validation
- Vulnerability scanning
- Compliance checking
- Security reporting
"""

import os
import json
import subprocess
import socket
import ssl
import hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field

try:
    from src.deployment.config import OnPremiseConfig, SecurityLevel
    from src.deployment.security import SecureCredentialStore, SecurityValidationResult
    from src.deployment.network_security import NetworkSecurityManager, NetworkValidationResult
    from src.utils.logging import get_structured_logger
except ImportError:
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class AuditSeverity(str, Enum):
    """Audit finding severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AuditCategory(str, Enum):
    """Audit categories."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    ENCRYPTION = "encryption"
    NETWORK = "network"
    CONFIGURATION = "configuration"
    SYSTEM = "system"
    COMPLIANCE = "compliance"


class AuditFinding(BaseModel):
    """Individual audit finding."""
    category: AuditCategory
    severity: AuditSeverity
    title: str
    description: str
    recommendation: str
    affected_component: str
    evidence: Dict[str, Any] = Field(default_factory=dict)
    remediation_steps: List[str] = Field(default_factory=list)
    compliance_frameworks: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class SecurityAuditReport(BaseModel):
    """Comprehensive security audit report."""
    audit_id: str
    deployment_method: str
    security_level: str
    audit_timestamp: datetime = Field(default_factory=datetime.now)
    
    # Summary statistics
    total_findings: int = 0
    critical_findings: int = 0
    high_findings: int = 0
    medium_findings: int = 0
    low_findings: int = 0
    info_findings: int = 0
    
    # Overall security score (0-100)
    security_score: int = 0
    security_grade: str = "F"  # A, B, C, D, F
    
    # Detailed findings
    findings: List[AuditFinding] = Field(default_factory=list)
    
    # Recommendations summary
    priority_recommendations: List[str] = Field(default_factory=list)
    compliance_status: Dict[str, str] = Field(default_factory=dict)
    
    # System information
    system_info: Dict[str, Any] = Field(default_factory=dict)
    
    def add_finding(self, finding: AuditFinding):
        """Add a finding to the report."""
        self.findings.append(finding)
        self.total_findings += 1
        
        # Update severity counters
        if finding.severity == AuditSeverity.CRITICAL:
            self.critical_findings += 1
        elif finding.severity == AuditSeverity.HIGH:
            self.high_findings += 1
        elif finding.severity == AuditSeverity.MEDIUM:
            self.medium_findings += 1
        elif finding.severity == AuditSeverity.LOW:
            self.low_findings += 1
        else:
            self.info_findings += 1
    
    def calculate_security_score(self):
        """Calculate overall security score."""
        # Base score starts at 100
        score = 100
        
        # Deduct points based on findings
        score -= self.critical_findings * 25
        score -= self.high_findings * 15
        score -= self.medium_findings * 8
        score -= self.low_findings * 3
        
        # Ensure score doesn't go below 0
        self.security_score = max(0, score)
        
        # Assign grade
        if self.security_score >= 90:
            self.security_grade = "A"
        elif self.security_score >= 80:
            self.security_grade = "B"
        elif self.security_score >= 70:
            self.security_grade = "C"
        elif self.security_score >= 60:
            self.security_grade = "D"
        else:
            self.security_grade = "F"


class SecurityAuditor:
    """
    Comprehensive security auditor for on-premise deployment.
    
    Performs detailed security assessment across multiple categories:
    - System security configuration
    - Network security
    - Authentication and authorization
    - Encryption and data protection
    - Configuration security
    - Compliance validation
    """
    
    def __init__(self, config: OnPremiseConfig, credential_store: Optional[SecureCredentialStore] = None):
        """Initialize security auditor."""
        self.config = config
        self.credential_store = credential_store
        self.logger = get_structured_logger(f"{__name__}.SecurityAuditor")
        
        # Initialize network security manager for network audits
        self.network_manager = NetworkSecurityManager(config)
        
        self.logger.info(
            f"Initialized security auditor for {config.deployment_method.value} deployment",
            extra={"security_level": config.security_config.security_level.value}
        )
    
    def perform_comprehensive_audit(self) -> SecurityAuditReport:
        """
        Perform comprehensive security audit.
        
        Returns:
            Detailed security audit report
        """
        audit_id = hashlib.md5(f"{datetime.now().isoformat()}{self.config.service_config.service_name}".encode()).hexdigest()[:8]
        
        report = SecurityAuditReport(
            audit_id=audit_id,
            deployment_method=self.config.deployment_method.value,
            security_level=self.config.security_config.security_level.value
        )
        
        try:
            # Collect system information
            report.system_info = self._collect_system_info()
            
            # Perform individual audit categories
            self._audit_authentication(report)
            self._audit_authorization(report)
            self._audit_encryption(report)
            self._audit_network_security(report)
            self._audit_configuration_security(report)
            self._audit_system_security(report)
            self._audit_compliance(report)
            
            # Calculate overall security score
            report.calculate_security_score()
            
            # Generate priority recommendations
            report.priority_recommendations = self._generate_priority_recommendations(report)
            
            self.logger.info(
                f"Security audit completed",
                extra={
                    "audit_id": audit_id,
                    "total_findings": report.total_findings,
                    "security_score": report.security_score,
                    "security_grade": report.security_grade
                }
            )
            
        except Exception as e:
            self.logger.error(f"Security audit failed: {e}")
            report.add_finding(AuditFinding(
                category=AuditCategory.SYSTEM,
                severity=AuditSeverity.CRITICAL,
                title="Audit System Failure",
                description=f"Security audit system encountered a critical error: {e}",
                recommendation="Investigate audit system configuration and dependencies",
                affected_component="audit_system"
            ))
        
        return report
    
    def _collect_system_info(self) -> Dict[str, Any]:
        """Collect system information for audit context."""
        system_info = {
            "hostname": socket.gethostname(),
            "platform": os.name,
            "audit_timestamp": datetime.now().isoformat(),
            "deployment_config": {
                "method": self.config.deployment_method.value,
                "security_level": self.config.security_config.security_level.value,
                "service_port": self.config.service_config.service_port,
                "https_enabled": self.config.security_config.enable_https
            }
        }
        
        try:
            import platform
            system_info.update({
                "os_name": platform.system(),
                "os_version": platform.release(),
                "architecture": platform.machine(),
                "python_version": platform.python_version()
            })
        except ImportError:
            pass
        
        return system_info
    
    def _audit_authentication(self, report: SecurityAuditReport):
        """Audit authentication mechanisms."""
        try:
            # Check API key authentication
            if self.config.security_config.api_key_required:
                if self.config.security_config.api_key:
                    # API key is configured
                    api_key_value = self.config.security_config.api_key.get_secret_value()
                    
                    # Check API key strength
                    if len(api_key_value) < 32:
                        report.add_finding(AuditFinding(
                            category=AuditCategory.AUTHENTICATION,
                            severity=AuditSeverity.MEDIUM,
                            title="Weak API Key Length",
                            description=f"API key length is {len(api_key_value)} characters, which may be insufficient",
                            recommendation="Use API keys with at least 32 characters for better security",
                            affected_component="api_authentication",
                            remediation_steps=[
                                "Generate a new API key with at least 32 characters",
                                "Update configuration with the new API key",
                                "Test authentication with the new key"
                            ]
                        ))
                    
                    # Check for credential store integration
                    if self.credential_store:
                        stored_key = self.credential_store.retrieve_credential("api_key_service_auth")
                        if not stored_key:
                            report.add_finding(AuditFinding(
                                category=AuditCategory.AUTHENTICATION,
                                severity=AuditSeverity.LOW,
                                title="API Key Not in Secure Store",
                                description="API key is configured but not stored in the secure credential store",
                                recommendation="Store API key in the secure credential store for better protection",
                                affected_component="credential_management"
                            ))
                
                else:
                    report.add_finding(AuditFinding(
                        category=AuditCategory.AUTHENTICATION,
                        severity=AuditSeverity.HIGH,
                        title="API Key Authentication Enabled but No Key Configured",
                        description="API key authentication is required but no API key is configured",
                        recommendation="Configure a strong API key or disable API key authentication",
                        affected_component="api_authentication",
                        remediation_steps=[
                            "Generate a strong API key (32+ characters)",
                            "Configure the API key in the security settings",
                            "Test authentication functionality"
                        ]
                    ))
            
            else:
                # API key authentication is disabled
                if self.config.security_config.security_level == SecurityLevel.HIGH:
                    report.add_finding(AuditFinding(
                        category=AuditCategory.AUTHENTICATION,
                        severity=AuditSeverity.HIGH,
                        title="No Authentication with High Security Level",
                        description="High security level is configured but API key authentication is disabled",
                        recommendation="Enable API key authentication for high security deployments",
                        affected_component="security_configuration",
                        compliance_frameworks=["NIST", "ISO27001"]
                    ))
                elif self.config.security_config.security_level == SecurityLevel.STANDARD:
                    report.add_finding(AuditFinding(
                        category=AuditCategory.AUTHENTICATION,
                        severity=AuditSeverity.MEDIUM,
                        title="No Authentication Configured",
                        description="No authentication mechanism is configured for the service",
                        recommendation="Consider enabling API key authentication for better security",
                        affected_component="security_configuration"
                    ))
        
        except Exception as e:
            report.add_finding(AuditFinding(
                category=AuditCategory.AUTHENTICATION,
                severity=AuditSeverity.MEDIUM,
                title="Authentication Audit Failed",
                description=f"Unable to complete authentication audit: {e}",
                recommendation="Investigate authentication configuration",
                affected_component="audit_system"
            ))
    
    def _audit_authorization(self, report: SecurityAuditReport):
        """Audit authorization and access control."""
        try:
            # Check allowed hosts configuration
            allowed_hosts = self.config.security_config.allowed_hosts
            
            if "*" in allowed_hosts:
                severity = AuditSeverity.HIGH if self.config.security_config.security_level == SecurityLevel.HIGH else AuditSeverity.MEDIUM
                report.add_finding(AuditFinding(
                    category=AuditCategory.AUTHORIZATION,
                    severity=severity,
                    title="Unrestricted Host Access",
                    description="Service allows connections from any host (*)",
                    recommendation="Restrict allowed hosts to specific IP addresses or hostnames",
                    affected_component="host_authorization",
                    remediation_steps=[
                        "Identify legitimate client IP addresses",
                        "Update allowed_hosts configuration to specific IPs",
                        "Test connectivity from allowed hosts"
                    ],
                    compliance_frameworks=["NIST", "PCI-DSS"]
                ))
            
            # Check CORS configuration
            cors_origins = self.config.security_config.cors_origins
            
            if "*" in cors_origins:
                severity = AuditSeverity.HIGH if self.config.security_config.security_level == SecurityLevel.HIGH else AuditSeverity.MEDIUM
                report.add_finding(AuditFinding(
                    category=AuditCategory.AUTHORIZATION,
                    severity=severity,
                    title="Unrestricted CORS Origins",
                    description="CORS policy allows requests from any origin (*)",
                    recommendation="Restrict CORS origins to specific domains",
                    affected_component="cors_authorization",
                    remediation_steps=[
                        "Identify legitimate web application domains",
                        "Update CORS origins to specific domains",
                        "Test web application functionality"
                    ]
                ))
            
            # Check service user configuration
            if self.config.service_config.service_user == "root":
                report.add_finding(AuditFinding(
                    category=AuditCategory.AUTHORIZATION,
                    severity=AuditSeverity.HIGH,
                    title="Service Running as Root",
                    description="Service is configured to run as root user",
                    recommendation="Create a dedicated service user with minimal privileges",
                    affected_component="service_user",
                    remediation_steps=[
                        "Create a dedicated user account for the service",
                        "Update service configuration to use the new user",
                        "Ensure proper file permissions for the service user"
                    ],
                    compliance_frameworks=["NIST", "CIS"]
                ))
        
        except Exception as e:
            report.add_finding(AuditFinding(
                category=AuditCategory.AUTHORIZATION,
                severity=AuditSeverity.MEDIUM,
                title="Authorization Audit Failed",
                description=f"Unable to complete authorization audit: {e}",
                recommendation="Investigate authorization configuration",
                affected_component="audit_system"
            ))
    
    def _audit_encryption(self, report: SecurityAuditReport):
        """Audit encryption and data protection."""
        try:
            # Check HTTPS/TLS configuration
            if not self.config.security_config.enable_https:
                severity = AuditSeverity.HIGH if self.config.security_config.security_level == SecurityLevel.HIGH else AuditSeverity.MEDIUM
                report.add_finding(AuditFinding(
                    category=AuditCategory.ENCRYPTION,
                    severity=severity,
                    title="HTTPS/TLS Not Enabled",
                    description="Service is not configured to use HTTPS/TLS encryption",
                    recommendation="Enable HTTPS/TLS for secure communications",
                    affected_component="tls_configuration",
                    remediation_steps=[
                        "Obtain SSL/TLS certificates",
                        "Configure HTTPS in service settings",
                        "Update client configurations to use HTTPS"
                    ],
                    compliance_frameworks=["PCI-DSS", "HIPAA", "GDPR"]
                ))
            
            else:
                # HTTPS is enabled, check certificate configuration
                if self.config.security_config.ssl_cert_path:
                    cert_path = Path(self.config.security_config.ssl_cert_path)
                    
                    if not cert_path.exists():
                        report.add_finding(AuditFinding(
                            category=AuditCategory.ENCRYPTION,
                            severity=AuditSeverity.HIGH,
                            title="SSL Certificate File Not Found",
                            description=f"SSL certificate file not found: {cert_path}",
                            recommendation="Ensure SSL certificate file exists and is accessible",
                            affected_component="ssl_certificate"
                        ))
                    
                    else:
                        # Check certificate permissions
                        cert_stat = cert_path.stat()
                        if cert_stat.st_mode & 0o044:  # World readable
                            report.add_finding(AuditFinding(
                                category=AuditCategory.ENCRYPTION,
                                severity=AuditSeverity.LOW,
                                title="SSL Certificate World Readable",
                                description="SSL certificate file has world-readable permissions",
                                recommendation="Restrict certificate file permissions to owner only",
                                affected_component="ssl_certificate"
                            ))
                
                # Check private key configuration
                if self.config.security_config.ssl_key_path:
                    key_path = Path(self.config.security_config.ssl_key_path)
                    
                    if not key_path.exists():
                        report.add_finding(AuditFinding(
                            category=AuditCategory.ENCRYPTION,
                            severity=AuditSeverity.CRITICAL,
                            title="SSL Private Key File Not Found",
                            description=f"SSL private key file not found: {key_path}",
                            recommendation="Ensure SSL private key file exists and is accessible",
                            affected_component="ssl_private_key"
                        ))
                    
                    else:
                        # Check private key permissions
                        key_stat = key_path.stat()
                        if key_stat.st_mode & 0o077:  # Group or world accessible
                            report.add_finding(AuditFinding(
                                category=AuditCategory.ENCRYPTION,
                                severity=AuditSeverity.CRITICAL,
                                title="SSL Private Key Insecure Permissions",
                                description="SSL private key file has insecure permissions",
                                recommendation="Set private key permissions to 0600 (owner read/write only)",
                                affected_component="ssl_private_key",
                                remediation_steps=[
                                    f"chmod 600 {key_path}",
                                    "Verify key file is accessible to service user only"
                                ]
                            ))
            
            # Check Meilisearch connection encryption
            if not self.config.meilisearch_config.ssl_enabled:
                if self.config.meilisearch_config.host.startswith("https://"):
                    report.add_finding(AuditFinding(
                        category=AuditCategory.ENCRYPTION,
                        severity=AuditSeverity.MEDIUM,
                        title="Meilisearch SSL Configuration Mismatch",
                        description="Meilisearch URL uses HTTPS but SSL is not enabled in configuration",
                        recommendation="Enable SSL in Meilisearch configuration",
                        affected_component="meilisearch_ssl"
                    ))
                
                elif self.config.security_config.security_level == SecurityLevel.HIGH:
                    report.add_finding(AuditFinding(
                        category=AuditCategory.ENCRYPTION,
                        severity=AuditSeverity.MEDIUM,
                        title="Unencrypted Meilisearch Connection",
                        description="Connection to Meilisearch is not encrypted",
                        recommendation="Enable SSL/TLS for Meilisearch connections",
                        affected_component="meilisearch_connection"
                    ))
            
            # Check credential store encryption
            if self.credential_store:
                # Credential store uses encryption by default, but check if it's accessible
                try:
                    credentials = self.credential_store.list_credentials()
                    if not credentials:
                        report.add_finding(AuditFinding(
                            category=AuditCategory.ENCRYPTION,
                            severity=AuditSeverity.INFO,
                            title="No Credentials in Secure Store",
                            description="Secure credential store is empty",
                            recommendation="Consider storing sensitive credentials in the secure store",
                            affected_component="credential_store"
                        ))
                except Exception:
                    report.add_finding(AuditFinding(
                        category=AuditCategory.ENCRYPTION,
                        severity=AuditSeverity.MEDIUM,
                        title="Credential Store Access Issue",
                        description="Unable to access secure credential store",
                        recommendation="Verify credential store configuration and master password",
                        affected_component="credential_store"
                    ))
        
        except Exception as e:
            report.add_finding(AuditFinding(
                category=AuditCategory.ENCRYPTION,
                severity=AuditSeverity.MEDIUM,
                title="Encryption Audit Failed",
                description=f"Unable to complete encryption audit: {e}",
                recommendation="Investigate encryption configuration",
                affected_component="audit_system"
            ))
    
    def _audit_network_security(self, report: SecurityAuditReport):
        """Audit network security configuration."""
        try:
            # Perform network validation
            network_result = self.network_manager.validate_network_access()
            
            # Convert network issues to audit findings
            for issue in network_result.issues:
                report.add_finding(AuditFinding(
                    category=AuditCategory.NETWORK,
                    severity=AuditSeverity.MEDIUM,
                    title="Network Configuration Issue",
                    description=issue,
                    recommendation="Review and fix network configuration",
                    affected_component="network_configuration"
                ))
            
            # Convert network recommendations to audit findings
            for recommendation in network_result.recommendations:
                report.add_finding(AuditFinding(
                    category=AuditCategory.NETWORK,
                    severity=AuditSeverity.LOW,
                    title="Network Security Recommendation",
                    description=recommendation,
                    recommendation="Consider implementing this network security improvement",
                    affected_component="network_security"
                ))
            
            # Check firewall status
            if not network_result.network_info.get("firewall_available", False):
                report.add_finding(AuditFinding(
                    category=AuditCategory.NETWORK,
                    severity=AuditSeverity.HIGH,
                    title="No Firewall Detected",
                    description="No firewall system detected on the server",
                    recommendation="Install and configure a firewall (ufw recommended)",
                    affected_component="firewall",
                    remediation_steps=[
                        "Install ufw: sudo apt install ufw",
                        "Configure firewall rules for the service",
                        "Enable the firewall: sudo ufw enable"
                    ],
                    compliance_frameworks=["NIST", "CIS"]
                ))
            
            elif not network_result.network_info.get("firewall_active", False):
                report.add_finding(AuditFinding(
                    category=AuditCategory.NETWORK,
                    severity=AuditSeverity.HIGH,
                    title="Firewall Not Active",
                    description="Firewall is installed but not active",
                    recommendation="Enable and configure the firewall",
                    affected_component="firewall",
                    remediation_steps=[
                        "Configure necessary firewall rules",
                        "Enable the firewall",
                        "Test connectivity after enabling"
                    ]
                ))
        
        except Exception as e:
            report.add_finding(AuditFinding(
                category=AuditCategory.NETWORK,
                severity=AuditSeverity.MEDIUM,
                title="Network Security Audit Failed",
                description=f"Unable to complete network security audit: {e}",
                recommendation="Investigate network configuration",
                affected_component="audit_system"
            ))
    
    def _audit_configuration_security(self, report: SecurityAuditReport):
        """Audit configuration file security."""
        try:
            # Check configuration directory permissions
            config_dir = Path(self.config.config_path)
            
            if config_dir.exists():
                dir_stat = config_dir.stat()
                if dir_stat.st_mode & 0o077:
                    report.add_finding(AuditFinding(
                        category=AuditCategory.CONFIGURATION,
                        severity=AuditSeverity.HIGH,
                        title="Insecure Configuration Directory Permissions",
                        description=f"Configuration directory has insecure permissions: {oct(dir_stat.st_mode)}",
                        recommendation="Set configuration directory permissions to 0700",
                        affected_component="configuration_directory",
                        remediation_steps=[
                            f"chmod 700 {config_dir}",
                            "Verify only service user can access the directory"
                        ]
                    ))
            
            # Check for sensitive data in configuration files
            config_files = [
                config_dir / "config.json",
                config_dir / "environment.env",
                config_dir / ".env"
            ]
            
            for config_file in config_files:
                if config_file.exists():
                    # Check file permissions
                    file_stat = config_file.stat()
                    if file_stat.st_mode & 0o077:
                        report.add_finding(AuditFinding(
                            category=AuditCategory.CONFIGURATION,
                            severity=AuditSeverity.HIGH,
                            title=f"Insecure Configuration File Permissions: {config_file.name}",
                            description=f"Configuration file has insecure permissions: {oct(file_stat.st_mode)}",
                            recommendation="Set configuration file permissions to 0600",
                            affected_component="configuration_files",
                            remediation_steps=[
                                f"chmod 600 {config_file}",
                                "Verify only service user can read the file"
                            ]
                        ))
                    
                    # Check for plain text secrets
                    try:
                        content = config_file.read_text().lower()
                        sensitive_patterns = ["password", "api_key", "secret", "token", "private_key"]
                        
                        for pattern in sensitive_patterns:
                            if pattern in content and "=" in content:
                                report.add_finding(AuditFinding(
                                    category=AuditCategory.CONFIGURATION,
                                    severity=AuditSeverity.MEDIUM,
                                    title=f"Potential Plain Text Secrets in {config_file.name}",
                                    description=f"Configuration file may contain plain text secrets (found '{pattern}')",
                                    recommendation="Consider encrypting configuration file or using secure credential store",
                                    affected_component="configuration_security"
                                ))
                                break
                    
                    except UnicodeDecodeError:
                        # File might be encrypted or binary - this is good
                        pass
        
        except Exception as e:
            report.add_finding(AuditFinding(
                category=AuditCategory.CONFIGURATION,
                severity=AuditSeverity.MEDIUM,
                title="Configuration Security Audit Failed",
                description=f"Unable to complete configuration security audit: {e}",
                recommendation="Investigate configuration file security",
                affected_component="audit_system"
            ))
    
    def _audit_system_security(self, report: SecurityAuditReport):
        """Audit system-level security."""
        try:
            # Check if running as root
            if os.getuid() == 0:
                report.add_finding(AuditFinding(
                    category=AuditCategory.SYSTEM,
                    severity=AuditSeverity.HIGH,
                    title="Running as Root User",
                    description="Audit is running as root user, service may also run as root",
                    recommendation="Run service as a dedicated non-root user",
                    affected_component="system_user",
                    compliance_frameworks=["NIST", "CIS"]
                ))
            
            # Check system directories
            directories = [
                ("data", self.config.data_path),
                ("log", self.config.log_path),
                ("config", self.config.config_path)
            ]
            
            for dir_name, dir_path in directories:
                path_obj = Path(dir_path)
                
                if path_obj.exists():
                    dir_stat = path_obj.stat()
                    if dir_stat.st_mode & 0o077:
                        report.add_finding(AuditFinding(
                            category=AuditCategory.SYSTEM,
                            severity=AuditSeverity.MEDIUM,
                            title=f"Insecure {dir_name.title()} Directory Permissions",
                            description=f"{dir_name.title()} directory has insecure permissions: {oct(dir_stat.st_mode)}",
                            recommendation=f"Set {dir_name} directory permissions to 0700",
                            affected_component=f"{dir_name}_directory"
                        ))
                else:
                    report.add_finding(AuditFinding(
                        category=AuditCategory.SYSTEM,
                        severity=AuditSeverity.LOW,
                        title=f"{dir_name.title()} Directory Missing",
                        description=f"{dir_name.title()} directory does not exist: {dir_path}",
                        recommendation=f"Create {dir_name} directory with secure permissions",
                        affected_component=f"{dir_name}_directory"
                    ))
            
            # Check for security updates (if possible)
            try:
                # This is a basic check - in production, integrate with proper vulnerability scanning
                result = subprocess.run(
                    ["which", "apt"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                
                if result.returncode == 0:
                    # System uses apt - check for updates
                    update_result = subprocess.run(
                        ["apt", "list", "--upgradable"],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    if update_result.returncode == 0 and "upgradable" in update_result.stdout:
                        upgradable_count = update_result.stdout.count('\n') - 1
                        if upgradable_count > 0:
                            report.add_finding(AuditFinding(
                                category=AuditCategory.SYSTEM,
                                severity=AuditSeverity.MEDIUM,
                                title="System Updates Available",
                                description=f"System has {upgradable_count} upgradable packages",
                                recommendation="Apply system security updates regularly",
                                affected_component="system_updates",
                                compliance_frameworks=["NIST", "CIS"]
                            ))
            
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # Skip update check if not available or times out
                pass
        
        except Exception as e:
            report.add_finding(AuditFinding(
                category=AuditCategory.SYSTEM,
                severity=AuditSeverity.MEDIUM,
                title="System Security Audit Failed",
                description=f"Unable to complete system security audit: {e}",
                recommendation="Investigate system security configuration",
                affected_component="audit_system"
            ))
    
    def _audit_compliance(self, report: SecurityAuditReport):
        """Audit compliance with security frameworks."""
        try:
            # NIST Cybersecurity Framework compliance
            nist_score = 0
            nist_total = 5
            
            # Identify (ID)
            if self.config.monitoring_config.enable_logging:
                nist_score += 1
            
            # Protect (PR)
            if self.config.security_config.api_key_required:
                nist_score += 1
            
            # Detect (DE)
            if self.config.monitoring_config.enable_health_checks:
                nist_score += 1
            
            # Respond (RS)
            if self.config.monitoring_config.enable_prometheus:
                nist_score += 1
            
            # Recover (RC)
            if Path(self.config.data_path).exists():
                nist_score += 1
            
            nist_compliance = (nist_score / nist_total) * 100
            report.compliance_status["NIST"] = f"{nist_compliance:.0f}%"
            
            if nist_compliance < 60:
                report.add_finding(AuditFinding(
                    category=AuditCategory.COMPLIANCE,
                    severity=AuditSeverity.MEDIUM,
                    title="Low NIST Framework Compliance",
                    description=f"NIST Cybersecurity Framework compliance is {nist_compliance:.0f}%",
                    recommendation="Improve security controls to meet NIST framework requirements",
                    affected_component="compliance_framework",
                    compliance_frameworks=["NIST"]
                ))
            
            # CIS Controls compliance (basic check)
            cis_score = 0
            cis_total = 3
            
            # CIS Control 4: Controlled Use of Administrative Privileges
            if self.config.service_config.service_user != "root":
                cis_score += 1
            
            # CIS Control 11: Data Recovery
            if Path(self.config.data_path).exists():
                cis_score += 1
            
            # CIS Control 12: Boundary Defense
            firewall_available = report.system_info.get("firewall_available", False)
            if firewall_available:
                cis_score += 1
            
            cis_compliance = (cis_score / cis_total) * 100
            report.compliance_status["CIS"] = f"{cis_compliance:.0f}%"
            
            if cis_compliance < 70:
                report.add_finding(AuditFinding(
                    category=AuditCategory.COMPLIANCE,
                    severity=AuditSeverity.MEDIUM,
                    title="Low CIS Controls Compliance",
                    description=f"CIS Controls compliance is {cis_compliance:.0f}%",
                    recommendation="Implement additional CIS security controls",
                    affected_component="compliance_framework",
                    compliance_frameworks=["CIS"]
                ))
        
        except Exception as e:
            report.add_finding(AuditFinding(
                category=AuditCategory.COMPLIANCE,
                severity=AuditSeverity.LOW,
                title="Compliance Audit Failed",
                description=f"Unable to complete compliance audit: {e}",
                recommendation="Investigate compliance framework requirements",
                affected_component="audit_system"
            ))
    
    def _generate_priority_recommendations(self, report: SecurityAuditReport) -> List[str]:
        """Generate priority recommendations based on findings."""
        recommendations = []
        
        # Critical findings first
        critical_findings = [f for f in report.findings if f.severity == AuditSeverity.CRITICAL]
        for finding in critical_findings[:3]:  # Top 3 critical
            recommendations.append(f"CRITICAL: {finding.title} - {finding.recommendation}")
        
        # High severity findings
        high_findings = [f for f in report.findings if f.severity == AuditSeverity.HIGH]
        for finding in high_findings[:3]:  # Top 3 high
            recommendations.append(f"HIGH: {finding.title} - {finding.recommendation}")
        
        # Add general recommendations based on security level
        if self.config.security_config.security_level == SecurityLevel.HIGH:
            if not self.config.security_config.api_key_required:
                recommendations.append("Enable API key authentication for high security level")
            if not self.config.security_config.enable_https:
                recommendations.append("Enable HTTPS/TLS for high security level")
        
        return recommendations[:10]  # Limit to top 10 recommendations
    
    def save_audit_report(self, report: SecurityAuditReport, output_path: str) -> bool:
        """
        Save audit report to file.
        
        Args:
            report: Security audit report
            output_path: Path to save the report
        
        Returns:
            True if saved successfully
        """
        try:
            report_data = report.model_dump(mode='json')
            
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(report_data, f, indent=2, default=str)
            
            # Set secure permissions
            output_file.chmod(0o600)
            
            self.logger.info(f"Security audit report saved: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save audit report: {e}")
            return False