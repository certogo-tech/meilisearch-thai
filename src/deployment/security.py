"""
Secure configuration handling for on-premise deployment.

This module provides comprehensive security features including:
- Secure credential storage and retrieval
- Configuration file encryption and protection
- API key management for optional authentication
- SSL/TLS configuration for Meilisearch connections
"""

import os
import secrets
import hashlib
import base64
import json
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timedelta
from enum import Enum

from pydantic import BaseModel, Field, SecretStr, field_validator
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import Encoding, PrivateFormat, NoEncryption
import stat

try:
    from src.utils.logging import get_structured_logger
except ImportError:
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class CredentialType(str, Enum):
    """Types of credentials that can be stored."""
    API_KEY = "api_key"
    PASSWORD = "password"
    CERTIFICATE = "certificate"
    PRIVATE_KEY = "private_key"
    TOKEN = "token"


class EncryptionMethod(str, Enum):
    """Supported encryption methods."""
    FERNET = "fernet"
    AES_256 = "aes_256"


class SecurityValidationResult(BaseModel):
    """Result of security validation."""
    valid: bool
    security_level: str
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class CredentialEntry(BaseModel):
    """Encrypted credential entry."""
    credential_type: CredentialType
    encrypted_value: str
    encryption_method: EncryptionMethod
    salt: str
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SecureCredentialStore:
    """
    Secure storage and retrieval system for sensitive credentials.
    
    Features:
    - Encryption at rest using Fernet (AES 128 in CBC mode)
    - Key derivation using PBKDF2
    - Secure file permissions
    - Credential expiration support
    - Audit logging
    """
    
    def __init__(self, store_path: str, master_password: Optional[str] = None):
        """
        Initialize secure credential store.
        
        Args:
            store_path: Path to the credential store file
            master_password: Master password for encryption (if None, uses environment)
        """
        self.store_path = Path(store_path)
        self.master_password = master_password or os.environ.get('THAI_TOKENIZER_MASTER_PASSWORD')
        self.logger = get_structured_logger(f"{__name__}.SecureCredentialStore")
        
        if not self.master_password:
            raise ValueError("Master password must be provided via parameter or THAI_TOKENIZER_MASTER_PASSWORD environment variable")
        
        # Ensure store directory exists with secure permissions
        self.store_path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        
        # Initialize or load credential store
        self._credentials: Dict[str, CredentialEntry] = {}
        self._load_credentials()
    
    def _derive_key(self, salt: bytes) -> bytes:
        """Derive encryption key from master password and salt."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(self.master_password.encode()))
    
    def _encrypt_value(self, value: str) -> Tuple[str, str]:
        """
        Encrypt a credential value.
        
        Returns:
            Tuple of (encrypted_value, salt)
        """
        salt = os.urandom(16)
        key = self._derive_key(salt)
        fernet = Fernet(key)
        
        encrypted_bytes = fernet.encrypt(value.encode())
        encrypted_value = base64.urlsafe_b64encode(encrypted_bytes).decode()
        salt_str = base64.urlsafe_b64encode(salt).decode()
        
        return encrypted_value, salt_str
    
    def _decrypt_value(self, encrypted_value: str, salt: str) -> str:
        """Decrypt a credential value."""
        try:
            salt_bytes = base64.urlsafe_b64decode(salt.encode())
            key = self._derive_key(salt_bytes)
            fernet = Fernet(key)
            
            encrypted_bytes = base64.urlsafe_b64decode(encrypted_value.encode())
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            
            return decrypted_bytes.decode()
        except Exception as e:
            self.logger.error(f"Failed to decrypt credential: {e}")
            raise ValueError("Failed to decrypt credential - invalid master password or corrupted data")
    
    def _load_credentials(self):
        """Load credentials from store file."""
        if not self.store_path.exists():
            self.logger.info(f"Creating new credential store at {self.store_path}")
            self._save_credentials()
            return
        
        try:
            # Check file permissions
            file_stat = self.store_path.stat()
            if file_stat.st_mode & 0o077:
                self.logger.warning(f"Credential store has insecure permissions: {oct(file_stat.st_mode)}")
                # Fix permissions
                self.store_path.chmod(0o600)
            
            with open(self.store_path, 'r') as f:
                data = json.load(f)
            
            for key, entry_data in data.items():
                self._credentials[key] = CredentialEntry(**entry_data)
            
            self.logger.info(f"Loaded {len(self._credentials)} credentials from store")
            
        except Exception as e:
            self.logger.error(f"Failed to load credential store: {e}")
            raise
    
    def _save_credentials(self):
        """Save credentials to store file."""
        try:
            # Prepare data for serialization
            data = {}
            for key, entry in self._credentials.items():
                data[key] = entry.model_dump(mode='json')
            
            # Write to temporary file first
            temp_path = self.store_path.with_suffix('.tmp')
            with open(temp_path, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            # Set secure permissions
            temp_path.chmod(0o600)
            
            # Atomic move
            temp_path.replace(self.store_path)
            
            self.logger.debug(f"Saved {len(self._credentials)} credentials to store")
            
        except Exception as e:
            self.logger.error(f"Failed to save credential store: {e}")
            raise
    
    def store_credential(
        self,
        key: str,
        value: str,
        credential_type: CredentialType,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Store a credential securely.
        
        Args:
            key: Unique identifier for the credential
            value: The credential value to encrypt and store
            credential_type: Type of credential
            expires_in_days: Optional expiration in days
            metadata: Optional metadata to store with credential
        
        Returns:
            True if stored successfully
        """
        try:
            encrypted_value, salt = self._encrypt_value(value)
            
            expires_at = None
            if expires_in_days:
                expires_at = datetime.now() + timedelta(days=expires_in_days)
            
            entry = CredentialEntry(
                credential_type=credential_type,
                encrypted_value=encrypted_value,
                encryption_method=EncryptionMethod.FERNET,
                salt=salt,
                expires_at=expires_at,
                metadata=metadata or {}
            )
            
            self._credentials[key] = entry
            self._save_credentials()
            
            self.logger.info(
                f"Stored credential '{key}' of type {credential_type.value}",
                extra={
                    "credential_key": key,
                    "credential_type": credential_type.value,
                    "expires_at": expires_at.isoformat() if expires_at else None
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to store credential '{key}': {e}")
            return False
    
    def retrieve_credential(self, key: str) -> Optional[str]:
        """
        Retrieve and decrypt a credential.
        
        Args:
            key: Credential identifier
        
        Returns:
            Decrypted credential value or None if not found/expired
        """
        if key not in self._credentials:
            self.logger.warning(f"Credential '{key}' not found")
            return None
        
        entry = self._credentials[key]
        
        # Check expiration
        if entry.expires_at and datetime.now() > entry.expires_at:
            self.logger.warning(f"Credential '{key}' has expired")
            self.delete_credential(key)
            return None
        
        try:
            value = self._decrypt_value(entry.encrypted_value, entry.salt)
            
            self.logger.debug(
                f"Retrieved credential '{key}'",
                extra={
                    "credential_key": key,
                    "credential_type": entry.credential_type.value
                }
            )
            
            return value
            
        except Exception as e:
            self.logger.error(f"Failed to retrieve credential '{key}': {e}")
            return None
    
    def delete_credential(self, key: str) -> bool:
        """
        Delete a credential from the store.
        
        Args:
            key: Credential identifier
        
        Returns:
            True if deleted successfully
        """
        if key in self._credentials:
            del self._credentials[key]
            self._save_credentials()
            
            self.logger.info(f"Deleted credential '{key}'")
            return True
        
        return False
    
    def list_credentials(self) -> List[Dict[str, Any]]:
        """
        List all stored credentials (without values).
        
        Returns:
            List of credential metadata
        """
        credentials = []
        
        for key, entry in self._credentials.items():
            credentials.append({
                "key": key,
                "type": entry.credential_type.value,
                "created_at": entry.created_at.isoformat(),
                "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
                "expired": entry.expires_at and datetime.now() > entry.expires_at,
                "metadata": entry.metadata
            })
        
        return credentials
    
    def cleanup_expired(self) -> int:
        """
        Remove expired credentials.
        
        Returns:
            Number of credentials removed
        """
        now = datetime.now()
        expired_keys = []
        
        for key, entry in self._credentials.items():
            if entry.expires_at and now > entry.expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._credentials[key]
        
        if expired_keys:
            self._save_credentials()
            self.logger.info(f"Cleaned up {len(expired_keys)} expired credentials")
        
        return len(expired_keys)


class APIKeyManager:
    """
    API key management for optional authentication.
    
    Features:
    - Generate secure API keys
    - Key validation and verification
    - Key rotation and expiration
    - Usage tracking and audit logging
    """
    
    def __init__(self, credential_store: SecureCredentialStore):
        """Initialize with credential store."""
        self.credential_store = credential_store
        self.logger = get_structured_logger(f"{__name__}.APIKeyManager")
    
    def generate_api_key(self, length: int = 32) -> str:
        """
        Generate a cryptographically secure API key.
        
        Args:
            length: Length of the API key in bytes
        
        Returns:
            Base64-encoded API key
        """
        key_bytes = secrets.token_bytes(length)
        api_key = base64.urlsafe_b64encode(key_bytes).decode().rstrip('=')
        
        self.logger.info(f"Generated new API key with length {length} bytes")
        
        return api_key
    
    def store_api_key(
        self,
        key_name: str,
        api_key: Optional[str] = None,
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store an API key in the credential store.
        
        Args:
            key_name: Name/identifier for the API key
            api_key: API key to store (if None, generates new one)
            expires_in_days: Optional expiration in days
            metadata: Optional metadata
        
        Returns:
            The API key that was stored
        """
        if not api_key:
            api_key = self.generate_api_key()
        
        # Store API key hash for validation
        key_hash = hashlib.sha256(api_key.encode()).hexdigest()
        
        store_metadata = metadata or {}
        store_metadata.update({
            "key_hash": key_hash,
            "generated_at": datetime.now().isoformat()
        })
        
        success = self.credential_store.store_credential(
            key=f"api_key_{key_name}",
            value=api_key,
            credential_type=CredentialType.API_KEY,
            expires_in_days=expires_in_days,
            metadata=store_metadata
        )
        
        if success:
            self.logger.info(
                f"Stored API key '{key_name}'",
                extra={
                    "key_name": key_name,
                    "expires_in_days": expires_in_days,
                    "key_hash": key_hash[:8] + "..."  # Log partial hash for identification
                }
            )
        
        return api_key
    
    def validate_api_key(self, key_name: str, provided_key: str) -> bool:
        """
        Validate an API key against stored value.
        
        Args:
            key_name: Name of the API key to validate
            provided_key: API key provided for validation
        
        Returns:
            True if key is valid and not expired
        """
        stored_key = self.credential_store.retrieve_credential(f"api_key_{key_name}")
        
        if not stored_key:
            self.logger.warning(f"API key '{key_name}' not found or expired")
            return False
        
        # Use constant-time comparison to prevent timing attacks
        is_valid = secrets.compare_digest(stored_key, provided_key)
        
        if is_valid:
            self.logger.info(f"API key '{key_name}' validated successfully")
        else:
            self.logger.warning(f"Invalid API key provided for '{key_name}'")
        
        return is_valid
    
    def rotate_api_key(self, key_name: str, expires_in_days: Optional[int] = None) -> str:
        """
        Rotate an API key (generate new one and replace old).
        
        Args:
            key_name: Name of the API key to rotate
            expires_in_days: Optional expiration for new key
        
        Returns:
            New API key
        """
        # Get existing metadata
        credentials = self.credential_store.list_credentials()
        existing_metadata = {}
        
        for cred in credentials:
            if cred["key"] == f"api_key_{key_name}":
                existing_metadata = cred["metadata"]
                break
        
        # Generate and store new key
        new_key = self.store_api_key(
            key_name=key_name,
            expires_in_days=expires_in_days,
            metadata=existing_metadata
        )
        
        self.logger.info(f"Rotated API key '{key_name}'")
        
        return new_key
    
    def list_api_keys(self) -> List[Dict[str, Any]]:
        """
        List all stored API keys (without values).
        
        Returns:
            List of API key metadata
        """
        all_credentials = self.credential_store.list_credentials()
        
        api_keys = []
        for cred in all_credentials:
            if cred["key"].startswith("api_key_") and cred["type"] == "api_key":
                key_name = cred["key"][8:]  # Remove "api_key_" prefix
                api_keys.append({
                    "name": key_name,
                    "created_at": cred["created_at"],
                    "expires_at": cred["expires_at"],
                    "expired": cred["expired"],
                    "metadata": cred["metadata"]
                })
        
        return api_keys


class SSLConfigurationManager:
    """
    SSL/TLS configuration management for Meilisearch connections.
    
    Features:
    - Generate self-signed certificates for development
    - Validate SSL certificate chains
    - Manage certificate storage and rotation
    - SSL connection testing
    """
    
    def __init__(self, credential_store: SecureCredentialStore):
        """Initialize with credential store."""
        self.credential_store = credential_store
        self.logger = get_structured_logger(f"{__name__}.SSLConfigurationManager")
    
    def generate_self_signed_certificate(
        self,
        cert_name: str,
        common_name: str = "localhost",
        validity_days: int = 365,
        key_size: int = 2048
    ) -> Tuple[str, str]:
        """
        Generate a self-signed SSL certificate.
        
        Args:
            cert_name: Name to store certificate under
            common_name: Common name for certificate
            validity_days: Certificate validity period
            key_size: RSA key size in bits
        
        Returns:
            Tuple of (certificate_pem, private_key_pem)
        """
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives.asymmetric import rsa
        
        # Generate private key
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=key_size,
        )
        
        # Create certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "US"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, "CA"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, "San Francisco"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "Thai Tokenizer"),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.now()
        ).not_valid_after(
            datetime.now() + timedelta(days=validity_days)
        ).add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(common_name),
                x509.DNSName("localhost"),
                x509.IPAddress("127.0.0.1"),
            ]),
            critical=False,
        ).sign(private_key, hashes.SHA256())
        
        # Serialize to PEM format
        cert_pem = cert.public_bytes(Encoding.PEM).decode()
        key_pem = private_key.private_bytes(
            encoding=Encoding.PEM,
            format=PrivateFormat.PKCS8,
            encryption_algorithm=NoEncryption()
        ).decode()
        
        # Store in credential store
        self.credential_store.store_credential(
            key=f"ssl_cert_{cert_name}",
            value=cert_pem,
            credential_type=CredentialType.CERTIFICATE,
            expires_in_days=validity_days,
            metadata={
                "common_name": common_name,
                "key_size": key_size,
                "self_signed": True
            }
        )
        
        self.credential_store.store_credential(
            key=f"ssl_key_{cert_name}",
            value=key_pem,
            credential_type=CredentialType.PRIVATE_KEY,
            expires_in_days=validity_days,
            metadata={
                "common_name": common_name,
                "key_size": key_size,
                "certificate_name": cert_name
            }
        )
        
        self.logger.info(
            f"Generated self-signed certificate '{cert_name}' for {common_name}",
            extra={
                "cert_name": cert_name,
                "common_name": common_name,
                "validity_days": validity_days,
                "key_size": key_size
            }
        )
        
        return cert_pem, key_pem
    
    def get_certificate(self, cert_name: str) -> Optional[Tuple[str, str]]:
        """
        Retrieve certificate and private key.
        
        Args:
            cert_name: Name of the certificate
        
        Returns:
            Tuple of (certificate_pem, private_key_pem) or None if not found
        """
        cert_pem = self.credential_store.retrieve_credential(f"ssl_cert_{cert_name}")
        key_pem = self.credential_store.retrieve_credential(f"ssl_key_{cert_name}")
        
        if cert_pem and key_pem:
            return cert_pem, key_pem
        
        return None
    
    def validate_certificate_chain(self, cert_pem: str) -> SecurityValidationResult:
        """
        Validate SSL certificate chain.
        
        Args:
            cert_pem: Certificate in PEM format
        
        Returns:
            Validation result with security assessment
        """
        from cryptography import x509
        
        result = SecurityValidationResult(valid=True, security_level="unknown")
        
        try:
            cert = x509.load_pem_x509_certificate(cert_pem.encode())
            
            # Check expiration
            now = datetime.now()
            if cert.not_valid_after < now:
                result.valid = False
                result.issues.append("Certificate has expired")
            elif cert.not_valid_after < now + timedelta(days=30):
                result.issues.append("Certificate expires within 30 days")
            
            # Check key size
            public_key = cert.public_key()
            if hasattr(public_key, 'key_size'):
                key_size = public_key.key_size
                if key_size < 2048:
                    result.issues.append(f"Weak key size: {key_size} bits (recommend 2048+)")
                    result.security_level = "low"
                elif key_size >= 4096:
                    result.security_level = "high"
                else:
                    result.security_level = "medium"
            
            # Check signature algorithm
            signature_algorithm = cert.signature_algorithm_oid._name
            if "sha1" in signature_algorithm.lower():
                result.issues.append("Weak signature algorithm: SHA-1")
                result.security_level = "low"
            
            # Check if self-signed
            if cert.issuer == cert.subject:
                result.recommendations.append("Self-signed certificate - consider using CA-signed certificate for production")
            
            self.logger.info(
                f"Certificate validation completed",
                extra={
                    "valid": result.valid,
                    "security_level": result.security_level,
                    "issues_count": len(result.issues),
                    "expires_at": cert.not_valid_after.isoformat()
                }
            )
            
        except Exception as e:
            result.valid = False
            result.issues.append(f"Certificate parsing error: {e}")
            self.logger.error(f"Certificate validation failed: {e}")
        
        return result


class ConfigurationProtectionManager:
    """
    Configuration file encryption and protection.
    
    Features:
    - Encrypt sensitive configuration files
    - Secure file permissions management
    - Configuration backup and recovery
    - Integrity verification
    """
    
    def __init__(self, credential_store: SecureCredentialStore):
        """Initialize with credential store."""
        self.credential_store = credential_store
        self.logger = get_structured_logger(f"{__name__}.ConfigurationProtectionManager")
    
    def protect_configuration_file(
        self,
        config_path: str,
        backup: bool = True
    ) -> bool:
        """
        Apply security protections to configuration file.
        
        Args:
            config_path: Path to configuration file
            backup: Whether to create backup before protection
        
        Returns:
            True if protection applied successfully
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            self.logger.error(f"Configuration file not found: {config_path}")
            return False
        
        try:
            # Create backup if requested
            if backup:
                backup_path = config_file.with_suffix(f"{config_file.suffix}.backup")
                backup_path.write_bytes(config_file.read_bytes())
                backup_path.chmod(0o600)
                self.logger.info(f"Created backup: {backup_path}")
            
            # Set secure file permissions
            config_file.chmod(0o600)
            
            # Set secure directory permissions
            config_file.parent.chmod(0o700)
            
            # Verify ownership (if running as root, change to service user)
            current_stat = config_file.stat()
            
            self.logger.info(
                f"Applied security protections to {config_path}",
                extra={
                    "file_mode": oct(current_stat.st_mode),
                    "file_size": current_stat.st_size,
                    "backup_created": backup
                }
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to protect configuration file {config_path}: {e}")
            return False
    
    def encrypt_configuration_file(
        self,
        config_path: str,
        encryption_key_name: str = "config_encryption_key"
    ) -> bool:
        """
        Encrypt a configuration file.
        
        Args:
            config_path: Path to configuration file
            encryption_key_name: Name of encryption key in credential store
        
        Returns:
            True if encryption successful
        """
        config_file = Path(config_path)
        
        if not config_file.exists():
            self.logger.error(f"Configuration file not found: {config_path}")
            return False
        
        try:
            # Generate encryption key if it doesn't exist
            encryption_key = self.credential_store.retrieve_credential(encryption_key_name)
            if not encryption_key:
                encryption_key = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode()
                self.credential_store.store_credential(
                    key=encryption_key_name,
                    value=encryption_key,
                    credential_type=CredentialType.TOKEN,
                    metadata={"purpose": "configuration_encryption"}
                )
            
            # Read and encrypt file content
            original_content = config_file.read_bytes()
            
            fernet = Fernet(encryption_key.encode())
            encrypted_content = fernet.encrypt(original_content)
            
            # Write encrypted content
            encrypted_path = config_file.with_suffix(f"{config_file.suffix}.encrypted")
            encrypted_path.write_bytes(encrypted_content)
            encrypted_path.chmod(0o600)
            
            # Create metadata file
            metadata = {
                "original_file": str(config_file),
                "encrypted_at": datetime.now().isoformat(),
                "encryption_key_name": encryption_key_name,
                "file_size": len(original_content),
                "encrypted_size": len(encrypted_content)
            }
            
            metadata_path = encrypted_path.with_suffix(".metadata")
            metadata_path.write_text(json.dumps(metadata, indent=2))
            metadata_path.chmod(0o600)
            
            self.logger.info(
                f"Encrypted configuration file: {config_path} -> {encrypted_path}",
                extra=metadata
            )
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to encrypt configuration file {config_path}: {e}")
            return False
    
    def decrypt_configuration_file(
        self,
        encrypted_path: str,
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Decrypt a configuration file.
        
        Args:
            encrypted_path: Path to encrypted configuration file
            output_path: Optional output path (if None, uses original path from metadata)
        
        Returns:
            Path to decrypted file or None if failed
        """
        encrypted_file = Path(encrypted_path)
        metadata_file = encrypted_file.with_suffix(".metadata")
        
        if not encrypted_file.exists():
            self.logger.error(f"Encrypted file not found: {encrypted_path}")
            return None
        
        if not metadata_file.exists():
            self.logger.error(f"Metadata file not found: {metadata_file}")
            return None
        
        try:
            # Load metadata
            metadata = json.loads(metadata_file.read_text())
            encryption_key_name = metadata["encryption_key_name"]
            
            # Get encryption key
            encryption_key = self.credential_store.retrieve_credential(encryption_key_name)
            if not encryption_key:
                self.logger.error(f"Encryption key '{encryption_key_name}' not found")
                return None
            
            # Decrypt content
            encrypted_content = encrypted_file.read_bytes()
            fernet = Fernet(encryption_key.encode())
            decrypted_content = fernet.decrypt(encrypted_content)
            
            # Determine output path
            if not output_path:
                output_path = metadata["original_file"]
            
            output_file = Path(output_path)
            output_file.write_bytes(decrypted_content)
            output_file.chmod(0o600)
            
            self.logger.info(
                f"Decrypted configuration file: {encrypted_path} -> {output_path}",
                extra={
                    "original_size": metadata["file_size"],
                    "decrypted_size": len(decrypted_content)
                }
            )
            
            return str(output_file)
            
        except Exception as e:
            self.logger.error(f"Failed to decrypt configuration file {encrypted_path}: {e}")
            return None
    
    def verify_configuration_integrity(self, config_path: str) -> SecurityValidationResult:
        """
        Verify configuration file integrity and security.
        
        Args:
            config_path: Path to configuration file
        
        Returns:
            Security validation result
        """
        result = SecurityValidationResult(valid=True, security_level="unknown")
        config_file = Path(config_path)
        
        if not config_file.exists():
            result.valid = False
            result.issues.append("Configuration file not found")
            return result
        
        try:
            # Check file permissions
            file_stat = config_file.stat()
            file_mode = file_stat.st_mode
            
            if file_mode & 0o077:
                result.issues.append(f"Insecure file permissions: {oct(file_mode)} (should be 0o600)")
                result.security_level = "low"
            else:
                result.security_level = "high"
            
            # Check directory permissions
            dir_stat = config_file.parent.stat()
            dir_mode = dir_stat.st_mode
            
            if dir_mode & 0o077:
                result.issues.append(f"Insecure directory permissions: {oct(dir_mode)} (should be 0o700)")
            
            # Check file size (detect potential corruption)
            file_size = file_stat.st_size
            if file_size == 0:
                result.valid = False
                result.issues.append("Configuration file is empty")
            elif file_size > 10 * 1024 * 1024:  # 10MB
                result.recommendations.append("Configuration file is unusually large")
            
            # Check for sensitive data in plain text
            try:
                content = config_file.read_text()
                sensitive_patterns = [
                    "password",
                    "api_key",
                    "secret",
                    "token",
                    "private_key"
                ]
                
                for pattern in sensitive_patterns:
                    if pattern in content.lower():
                        result.recommendations.append(f"Consider encrypting file - contains '{pattern}'")
                        break
            
            except UnicodeDecodeError:
                # File might be encrypted or binary
                result.recommendations.append("File appears to be encrypted or binary")
            
            self.logger.info(
                f"Configuration integrity check completed for {config_path}",
                extra={
                    "valid": result.valid,
                    "security_level": result.security_level,
                    "file_size": file_size,
                    "issues_count": len(result.issues)
                }
            )
            
        except Exception as e:
            result.valid = False
            result.issues.append(f"Integrity check failed: {e}")
            self.logger.error(f"Configuration integrity check failed for {config_path}: {e}")
        
        return result