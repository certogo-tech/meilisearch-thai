"""
Comprehensive security manager for on-premise deployment.

This module integrates all security components and provides a unified interface
for managing security aspects of the Thai Tokenizer deployment.
"""

import os
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

from pydantic import BaseModel, Field

try:
    from src.deployment.security import (
        SecureCredentialStore,
        APIKeyManager,
        SSLConfigurationManager,
        ConfigurationProtectionManager,
        SecurityValidationResult,
        CredentialType
    )
    from src.deployment.config import OnPremiseConfig, SecurityConfig, SecurityLevel
    from src.utils.logging import get_structured_logger
except ImportError:
    # Fallback for when running outside the main application
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class SecuritySetupResult(BaseModel):
    """Result of security setup operations."""
    success: bool
    security_level: str
    components_configured: List[str] = Field(default_factory=list)
    credentials_stored: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class SecurityAuditResult(BaseModel):
    """Result of security audit."""
    overall_security_level: str
    passed_checks: int
    failed_checks: int
    warnings: int
    critical_issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    detailed_results: Dict[str, SecurityValidationResult] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class DeploymentSecurityManager:
    """
    Comprehensive security manager for on-premise deployment.
    
    This class provides a unified interface for all security operations including:
    - Credential management
    - API key management
    - SSL/TLS configuration
    - Configuration file protection
    - Security auditing and validation
    """
    
    def __init__(
        self,
        config: OnPremiseConfig,
        credential_store_path: Optional[str] = None,
        master_password: Optional[str] = None
    ):
        """
        Initialize security manager.
        
        Args:
            config: On-premise deployment configuration
            credential_store_path: Path to credential store (default: config_path/credentials.json)
            master_password: Master password for credential encryption
        """
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.DeploymentSecurityManager")
        
        # Initialize credential store
        if not credential_store_path:
            credential_store_path = os.path.join(config.config_path, "credentials.json")
        
        self.credential_store = SecureCredentialStore(
            store_path=credential_store_path,
            master_password=master_password
        )
        
        # Initialize security components
        self.api_key_manager = APIKeyManager(self.credential_store)
        self.ssl_manager = SSLConfigurationManager(self.credential_store)
        self.config_protection_manager = ConfigurationProtectionManager(self.credential_store)
        
        self.logger.info(
            f"Initialized security manager for {config.deployment_method.value} deployment",
            extra={
                "security_level": config.security_config.security_level.value,
                "credential_store_path": credential_store_path
            }
        )
    
    def setup_security(self) -> SecuritySetupResult:
        """
        Set up comprehensive security for the deployment.
        
        Returns:
            Security setup result with details of configured components
        """
        result = SecuritySetupResult(
            success=True,
            security_level=self.config.security_config.security_level.value
        )
        
        try:
            # 1. Store Meilisearch credentials
            self._setup_meilisearch_credentials(result)
            
            # 2. Set up API key authentication if required
            if self.config.security_config.api_key_required:
                self._setup_api_authentication(result)
            
            # 3. Set up SSL/TLS if enabled
            if self.config.security_config.enable_https:
                self._setup_ssl_configuration(result)
            
            # 4. Protect configuration files
            self._protect_configuration_files(result)
            
            # 5. Set up directory permissions
            self._setup_directory_permissions(result)
            
            # 6. Generate security documentation
            self._generate_security_documentation(result)
            
            self.logger.info(
                f"Security setup completed successfully",
                extra={
                    "components_configured": len(result.components_configured),
                    "credentials_stored": len(result.credentials_stored),
                    "security_level": result.security_level
                }
            )
            
        except Exception as e:
            result.success = False
            result.issues.append(f"Security setup failed: {e}")
            self.logger.error(f"Security setup failed: {e}")
        
        return result
    
    def _setup_meilisearch_credentials(self, result: SecuritySetupResult):
        """Set up secure storage for Meilisearch credentials."""
        try:
            # Store Meilisearch API key
            success = self.credential_store.store_credential(
                key="meilisearch_api_key",
                value=self.config.meilisearch_config.api_key.get_secret_value(),
                credential_type=CredentialType.API_KEY,
                metadata={
                    "host": self.config.meilisearch_config.host,
                    "purpose": "meilisearch_authentication"
                }
            )
            
            if success:
                result.components_configured.append("meilisearch_credentials")
                result.credentials_stored.append("meilisearch_api_key")
            else:
                result.issues.append("Failed to store Meilisearch API key")
            
        except Exception as e:
            result.issues.append(f"Meilisearch credential setup failed: {e}")
    
    def _setup_api_authentication(self, result: SecuritySetupResult):
        """Set up API key authentication for the service."""
        try:
            # Generate or use existing API key
            if self.config.security_config.api_key:
                api_key = self.config.security_config.api_key.get_secret_value()
            else:
                api_key = None  # Will be generated
            
            # Store service API key
            stored_key = self.api_key_manager.store_api_key(
                key_name="service_auth",
                api_key=api_key,
                expires_in_days=365,  # 1 year expiration
                metadata={
                    "purpose": "service_authentication",
                    "security_level": self.config.security_config.security_level.value
                }
            )
            
            # Update configuration with generated key if needed
            if not self.config.security_config.api_key:
                from pydantic import SecretStr
                self.config.security_config.api_key = SecretStr(stored_key)
            
            result.components_configured.append("api_authentication")
            result.credentials_stored.append("service_auth_api_key")
            
        except Exception as e:
            result.issues.append(f"API authentication setup failed: {e}")
    
    def _setup_ssl_configuration(self, result: SecuritySetupResult):
        """Set up SSL/TLS configuration."""
        try:
            # Check if SSL certificates are provided
            if (self.config.security_config.ssl_cert_path and 
                self.config.security_config.ssl_key_path):
                
                # Validate existing certificates
                cert_path = Path(self.config.security_config.ssl_cert_path)
                if cert_path.exists():
                    cert_content = cert_path.read_text()
                    validation = self.ssl_manager.validate_certificate_chain(cert_content)
                    
                    if validation.valid:
                        result.components_configured.append("ssl_certificates_validated")
                    else:
                        result.issues.extend(validation.issues)
                else:
                    result.issues.append(f"SSL certificate file not found: {cert_path}")
            
            else:
                # Generate self-signed certificate for development
                if self.config.security_config.security_level == SecurityLevel.BASIC:
                    cert_pem, key_pem = self.ssl_manager.generate_self_signed_certificate(
                        cert_name="service_ssl",
                        common_name="localhost",
                        validity_days=365
                    )
                    
                    # Save certificates to files
                    cert_path = Path(self.config.config_path) / "ssl_cert.pem"
                    key_path = Path(self.config.config_path) / "ssl_key.pem"
                    
                    cert_path.write_text(cert_pem)
                    key_path.write_text(key_pem)
                    
                    cert_path.chmod(0o644)
                    key_path.chmod(0o600)
                    
                    # Update configuration
                    self.config.security_config.ssl_cert_path = str(cert_path)
                    self.config.security_config.ssl_key_path = str(key_path)
                    
                    result.components_configured.append("ssl_self_signed_generated")
                    result.recommendations.append("Self-signed certificate generated - consider using CA-signed certificate for production")
                
                else:
                    result.issues.append("HTTPS enabled but no SSL certificates provided")
            
        except Exception as e:
            result.issues.append(f"SSL configuration setup failed: {e}")
    
    def _protect_configuration_files(self, result: SecuritySetupResult):
        """Protect configuration files with appropriate security measures."""
        try:
            config_files = [
                "config.json",
                "environment.env",
                ".env"
            ]
            
            config_dir = Path(self.config.config_path)
            
            for config_file in config_files:
                config_path = config_dir / config_file
                
                if config_path.exists():
                    # Apply file protection
                    success = self.config_protection_manager.protect_configuration_file(
                        str(config_path),
                        backup=True
                    )
                    
                    if success:
                        result.components_configured.append(f"protected_{config_file}")
                    
                    # For high security, encrypt sensitive files
                    if self.config.security_config.security_level == SecurityLevel.HIGH:
                        if config_file in ["environment.env", ".env"]:
                            encrypt_success = self.config_protection_manager.encrypt_configuration_file(
                                str(config_path)
                            )
                            
                            if encrypt_success:
                                result.components_configured.append(f"encrypted_{config_file}")
            
        except Exception as e:
            result.issues.append(f"Configuration file protection failed: {e}")
    
    def _setup_directory_permissions(self, result: SecuritySetupResult):
        """Set up secure directory permissions."""
        try:
            directories = [
                self.config.config_path,
                self.config.data_path,
                self.config.log_path
            ]
            
            for directory in directories:
                dir_path = Path(directory)
                
                # Create directory if it doesn't exist
                dir_path.mkdir(parents=True, exist_ok=True)
                
                # Set secure permissions
                dir_path.chmod(0o700)
                
                result.components_configured.append(f"secured_directory_{dir_path.name}")
            
        except Exception as e:
            result.issues.append(f"Directory permission setup failed: {e}")
    
    def _generate_security_documentation(self, result: SecuritySetupResult):
        """Generate security documentation and configuration summary."""
        try:
            security_doc = {
                "deployment_security_summary": {
                    "deployment_method": self.config.deployment_method.value,
                    "security_level": self.config.security_config.security_level.value,
                    "setup_timestamp": datetime.now().isoformat(),
                    "components_configured": result.components_configured,
                    "credentials_managed": len(result.credentials_stored)
                },
                "security_features": {
                    "credential_encryption": True,
                    "api_key_authentication": self.config.security_config.api_key_required,
                    "https_enabled": self.config.security_config.enable_https,
                    "file_protection": True,
                    "directory_permissions": True
                },
                "maintenance": {
                    "credential_rotation_recommended": "annually",
                    "certificate_expiration_monitoring": "enabled",
                    "security_audit_frequency": "quarterly"
                }
            }
            
            # Save security documentation
            doc_path = Path(self.config.config_path) / "security_summary.json"
            doc_path.write_text(json.dumps(security_doc, indent=2))
            doc_path.chmod(0o600)
            
            result.components_configured.append("security_documentation")
            
        except Exception as e:
            result.issues.append(f"Security documentation generation failed: {e}")
    
    def audit_security(self) -> SecurityAuditResult:
        """
        Perform comprehensive security audit.
        
        Returns:
            Detailed security audit result
        """
        audit_result = SecurityAuditResult(
            overall_security_level="unknown",
            passed_checks=0,
            failed_checks=0,
            warnings=0
        )
        
        try:
            # 1. Audit credential store
            self._audit_credential_store(audit_result)
            
            # 2. Audit configuration files
            self._audit_configuration_files(audit_result)
            
            # 3. Audit SSL/TLS configuration
            if self.config.security_config.enable_https:
                self._audit_ssl_configuration(audit_result)
            
            # 4. Audit directory permissions
            self._audit_directory_permissions(audit_result)
            
            # 5. Audit API key configuration
            if self.config.security_config.api_key_required:
                self._audit_api_keys(audit_result)
            
            # 6. Determine overall security level
            self._determine_overall_security_level(audit_result)
            
            self.logger.info(
                f"Security audit completed",
                extra={
                    "overall_security_level": audit_result.overall_security_level,
                    "passed_checks": audit_result.passed_checks,
                    "failed_checks": audit_result.failed_checks,
                    "warnings": audit_result.warnings
                }
            )
            
        except Exception as e:
            audit_result.critical_issues.append(f"Security audit failed: {e}")
            self.logger.error(f"Security audit failed: {e}")
        
        return audit_result
    
    def _audit_credential_store(self, audit_result: SecurityAuditResult):
        """Audit credential store security."""
        try:
            # Check credential store file permissions
            store_path = Path(self.credential_store.store_path)
            
            if store_path.exists():
                file_stat = store_path.stat()
                if file_stat.st_mode & 0o077:
                    audit_result.failed_checks += 1
                    audit_result.critical_issues.append("Credential store has insecure file permissions")
                else:
                    audit_result.passed_checks += 1
                
                # Check for expired credentials
                expired_count = self.credential_store.cleanup_expired()
                if expired_count > 0:
                    audit_result.warnings += 1
                    audit_result.recommendations.append(f"Cleaned up {expired_count} expired credentials")
            
            audit_result.detailed_results["credential_store"] = SecurityValidationResult(
                valid=True,
                security_level="high"
            )
            
        except Exception as e:
            audit_result.failed_checks += 1
            audit_result.critical_issues.append(f"Credential store audit failed: {e}")
    
    def _audit_configuration_files(self, audit_result: SecurityAuditResult):
        """Audit configuration file security."""
        config_files = [
            "config.json",
            "environment.env",
            ".env"
        ]
        
        config_dir = Path(self.config.config_path)
        
        for config_file in config_files:
            config_path = config_dir / config_file
            
            if config_path.exists():
                validation = self.config_protection_manager.verify_configuration_integrity(
                    str(config_path)
                )
                
                audit_result.detailed_results[f"config_{config_file}"] = validation
                
                if validation.valid:
                    audit_result.passed_checks += 1
                else:
                    audit_result.failed_checks += 1
                    audit_result.critical_issues.extend(validation.issues)
                
                if validation.recommendations:
                    audit_result.warnings += len(validation.recommendations)
                    audit_result.recommendations.extend(validation.recommendations)
    
    def _audit_ssl_configuration(self, audit_result: SecurityAuditResult):
        """Audit SSL/TLS configuration."""
        if self.config.security_config.ssl_cert_path:
            cert_path = Path(self.config.security_config.ssl_cert_path)
            
            if cert_path.exists():
                cert_content = cert_path.read_text()
                validation = self.ssl_manager.validate_certificate_chain(cert_content)
                
                audit_result.detailed_results["ssl_certificate"] = validation
                
                if validation.valid:
                    audit_result.passed_checks += 1
                else:
                    audit_result.failed_checks += 1
                    audit_result.critical_issues.extend(validation.issues)
                
                if validation.recommendations:
                    audit_result.warnings += len(validation.recommendations)
                    audit_result.recommendations.extend(validation.recommendations)
            else:
                audit_result.failed_checks += 1
                audit_result.critical_issues.append(f"SSL certificate file not found: {cert_path}")
    
    def _audit_directory_permissions(self, audit_result: SecurityAuditResult):
        """Audit directory permissions."""
        directories = [
            ("config", self.config.config_path),
            ("data", self.config.data_path),
            ("log", self.config.log_path)
        ]
        
        for dir_name, dir_path in directories:
            path_obj = Path(dir_path)
            
            if path_obj.exists():
                dir_stat = path_obj.stat()
                
                if dir_stat.st_mode & 0o077:
                    audit_result.failed_checks += 1
                    audit_result.critical_issues.append(f"Insecure permissions on {dir_name} directory: {dir_path}")
                else:
                    audit_result.passed_checks += 1
            else:
                audit_result.warnings += 1
                audit_result.recommendations.append(f"Directory does not exist: {dir_path}")
    
    def _audit_api_keys(self, audit_result: SecurityAuditResult):
        """Audit API key configuration."""
        try:
            api_keys = self.api_key_manager.list_api_keys()
            
            for key_info in api_keys:
                if key_info["expired"]:
                    audit_result.warnings += 1
                    audit_result.recommendations.append(f"API key '{key_info['name']}' has expired")
                else:
                    audit_result.passed_checks += 1
            
        except Exception as e:
            audit_result.failed_checks += 1
            audit_result.critical_issues.append(f"API key audit failed: {e}")
    
    def _determine_overall_security_level(self, audit_result: SecurityAuditResult):
        """Determine overall security level based on audit results."""
        total_checks = audit_result.passed_checks + audit_result.failed_checks
        
        if total_checks == 0:
            audit_result.overall_security_level = "unknown"
        elif audit_result.failed_checks == 0:
            if audit_result.warnings == 0:
                audit_result.overall_security_level = "high"
            elif audit_result.warnings <= 2:
                audit_result.overall_security_level = "medium"
            else:
                audit_result.overall_security_level = "medium-low"
        elif audit_result.failed_checks <= 1 and audit_result.warnings <= 3:
            audit_result.overall_security_level = "medium"
        elif audit_result.failed_checks <= 2:
            audit_result.overall_security_level = "low"
        else:
            audit_result.overall_security_level = "critical"
    
    def rotate_credentials(self, credential_types: Optional[List[str]] = None) -> Dict[str, bool]:
        """
        Rotate specified credentials or all credentials.
        
        Args:
            credential_types: List of credential types to rotate (if None, rotates all)
        
        Returns:
            Dictionary mapping credential names to rotation success status
        """
        results = {}
        
        try:
            if not credential_types:
                credential_types = ["api_keys", "meilisearch_key"]
            
            # Rotate API keys
            if "api_keys" in credential_types:
                try:
                    new_key = self.api_key_manager.rotate_api_key("service_auth")
                    results["service_auth_api_key"] = True
                    
                    # Update configuration with new key
                    from pydantic import SecretStr
                    self.config.security_config.api_key = SecretStr(new_key)
                    
                except Exception as e:
                    results["service_auth_api_key"] = False
                    self.logger.error(f"Failed to rotate service API key: {e}")
            
            # Rotate Meilisearch key (if needed)
            if "meilisearch_key" in credential_types:
                # Note: This would typically require coordination with Meilisearch admin
                results["meilisearch_api_key"] = False
                self.logger.info("Meilisearch API key rotation requires manual intervention")
            
            self.logger.info(
                f"Credential rotation completed",
                extra={
                    "rotated_credentials": [k for k, v in results.items() if v],
                    "failed_rotations": [k for k, v in results.items() if not v]
                }
            )
            
        except Exception as e:
            self.logger.error(f"Credential rotation failed: {e}")
        
        return results
    
    def get_security_status(self) -> Dict[str, Any]:
        """
        Get current security status summary.
        
        Returns:
            Dictionary with security status information
        """
        try:
            # Get credential information
            credentials = self.credential_store.list_credentials()
            api_keys = self.api_key_manager.list_api_keys()
            
            status = {
                "security_level": self.config.security_config.security_level.value,
                "credentials": {
                    "total_stored": len(credentials),
                    "expired": len([c for c in credentials if c["expired"]]),
                    "types": list(set(c["type"] for c in credentials))
                },
                "api_keys": {
                    "total": len(api_keys),
                    "expired": len([k for k in api_keys if k["expired"]]),
                    "authentication_required": self.config.security_config.api_key_required
                },
                "ssl_tls": {
                    "enabled": self.config.security_config.enable_https,
                    "certificate_path": self.config.security_config.ssl_cert_path,
                    "key_path": self.config.security_config.ssl_key_path
                },
                "configuration": {
                    "allowed_hosts": self.config.security_config.allowed_hosts,
                    "cors_origins": self.config.security_config.cors_origins,
                    "firewall_rules": len(self.config.security_config.firewall_rules)
                },
                "last_updated": datetime.now().isoformat()
            }
            
            return status
            
        except Exception as e:
            self.logger.error(f"Failed to get security status: {e}")
            return {"error": str(e)}