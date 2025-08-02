"""
Unit tests for security implementation.

Tests the security and configuration management components.
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from src.deployment.config import OnPremiseConfig, SecurityConfig, SecurityLevel, DeploymentMethod
from src.deployment.security import (
    SecureCredentialStore,
    APIKeyManager,
    SSLConfigurationManager,
    ConfigurationProtectionManager,
    CredentialType
)
from src.deployment.security_manager import DeploymentSecurityManager
from src.deployment.network_security import NetworkSecurityManager, FirewallRule, AccessControlAction, NetworkProtocol
from src.deployment.security_audit import SecurityAuditor, AuditSeverity, AuditCategory


class TestSecureCredentialStore:
    """Test secure credential storage."""
    
    def test_credential_store_initialization(self):
        """Test credential store initialization."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = os.path.join(temp_dir, "credentials.json")
            
            # Set master password via environment
            os.environ['THAI_TOKENIZER_MASTER_PASSWORD'] = 'test_master_password_123'
            
            try:
                store = SecureCredentialStore(store_path)
                assert store.store_path == Path(store_path)
                assert store.master_password == 'test_master_password_123'
            finally:
                del os.environ['THAI_TOKENIZER_MASTER_PASSWORD']
    
    def test_store_and_retrieve_credential(self):
        """Test storing and retrieving credentials."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = os.path.join(temp_dir, "credentials.json")
            
            os.environ['THAI_TOKENIZER_MASTER_PASSWORD'] = 'test_master_password_123'
            
            try:
                store = SecureCredentialStore(store_path)
                
                # Store a credential
                success = store.store_credential(
                    key="test_api_key",
                    value="secret_api_key_value",
                    credential_type=CredentialType.API_KEY,
                    metadata={"purpose": "testing"}
                )
                
                assert success is True
                
                # Retrieve the credential
                retrieved_value = store.retrieve_credential("test_api_key")
                assert retrieved_value == "secret_api_key_value"
                
                # List credentials
                credentials = store.list_credentials()
                assert len(credentials) == 1
                assert credentials[0]["key"] == "test_api_key"
                assert credentials[0]["type"] == "api_key"
                
            finally:
                del os.environ['THAI_TOKENIZER_MASTER_PASSWORD']
    
    def test_credential_not_found(self):
        """Test retrieving non-existent credential."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = os.path.join(temp_dir, "credentials.json")
            
            os.environ['THAI_TOKENIZER_MASTER_PASSWORD'] = 'test_master_password_123'
            
            try:
                store = SecureCredentialStore(store_path)
                
                # Try to retrieve non-existent credential
                retrieved_value = store.retrieve_credential("non_existent_key")
                assert retrieved_value is None
                
            finally:
                del os.environ['THAI_TOKENIZER_MASTER_PASSWORD']


class TestAPIKeyManager:
    """Test API key management."""
    
    def test_api_key_generation(self):
        """Test API key generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            store_path = os.path.join(temp_dir, "credentials.json")
            
            os.environ['THAI_TOKENIZER_MASTER_PASSWORD'] = 'test_master_password_123'
            
            try:
                store = SecureCredentialStore(store_path)
                api_manager = APIKeyManager(store)
                
                # Generate API key
                api_key = api_manager.generate_api_key()
                assert len(api_key) >= 32  # Should be at least 32 characters
                assert isinstance(api_key, str)
                
                # Store API key
                stored_key = api_manager.store_api_key("test_service", api_key)
                assert stored_key == api_key
                
                # Validate API key
                is_valid = api_manager.validate_api_key("test_service", api_key)
                assert is_valid is True
                
                # Test invalid key
                is_valid = api_manager.validate_api_key("test_service", "invalid_key")
                assert is_valid is False
                
            finally:
                del os.environ['THAI_TOKENIZER_MASTER_PASSWORD']


class TestNetworkSecurityManager:
    """Test network security management."""
    
    def create_test_config(self):
        """Create test configuration."""
        from pydantic import SecretStr
        
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config={
                "host": "http://localhost:7700",
                "api_key": SecretStr("test_api_key")
            },
            security_config=SecurityConfig(
                security_level=SecurityLevel.STANDARD,
                allowed_hosts=["localhost", "127.0.0.1"],
                cors_origins=["http://localhost:3000"]
            )
        )
    
    def test_firewall_rule_creation(self):
        """Test firewall rule creation."""
        rule = FirewallRule(
            action=AccessControlAction.ALLOW,
            protocol=NetworkProtocol.TCP,
            port=8000,
            comment="Thai Tokenizer service"
        )
        
        assert rule.action == AccessControlAction.ALLOW
        assert rule.protocol == NetworkProtocol.TCP
        assert rule.port == 8000
        assert rule.comment == "Thai Tokenizer service"
        
        # Test UFW rule generation
        ufw_rule = rule.to_ufw_rule()
        assert "ufw allow" in ufw_rule
        assert "port 8000" in ufw_rule
        assert "Thai Tokenizer service" in ufw_rule
    
    def test_network_security_manager_initialization(self):
        """Test network security manager initialization."""
        config = self.create_test_config()
        
        with patch('subprocess.run') as mock_run:
            # Mock firewall detection
            mock_run.return_value.returncode = 0
            
            manager = NetworkSecurityManager(config)
            assert manager.config == config
    
    def test_firewall_rules_generation(self):
        """Test firewall rules generation."""
        config = self.create_test_config()
        
        with patch('subprocess.run') as mock_run:
            mock_run.return_value.returncode = 0
            
            manager = NetworkSecurityManager(config)
            rules = manager.generate_firewall_rules()
            
            assert len(rules) > 0
            
            # Should include SSH and service port rules
            service_rule = next((r for r in rules if r.port == 8000), None)
            assert service_rule is not None
            assert service_rule.action == AccessControlAction.ALLOW


class TestSecurityAuditor:
    """Test security auditing."""
    
    def create_test_config(self):
        """Create test configuration."""
        from pydantic import SecretStr
        
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config={
                "host": "http://localhost:7700",
                "api_key": SecretStr("test_api_key")
            },
            security_config=SecurityConfig(
                security_level=SecurityLevel.STANDARD,
                api_key_required=True,
                api_key=SecretStr("test_service_api_key"),
                enable_https=False
            )
        )
    
    @patch('socket.gethostname')
    @patch('os.name', 'posix')
    def test_security_audit_initialization(self, mock_hostname):
        """Test security auditor initialization."""
        mock_hostname.return_value = "test-host"
        
        config = self.create_test_config()
        auditor = SecurityAuditor(config)
        
        assert auditor.config == config
    
    @patch('socket.gethostname')
    @patch('os.name', 'posix')
    @patch('subprocess.run')
    def test_comprehensive_audit(self, mock_run, mock_hostname):
        """Test comprehensive security audit."""
        mock_hostname.return_value = "test-host"
        mock_run.return_value.returncode = 1  # No firewall
        
        config = self.create_test_config()
        auditor = SecurityAuditor(config)
        
        # Mock network manager to avoid actual network calls
        with patch.object(auditor.network_manager, 'validate_network_access') as mock_validate:
            mock_validate.return_value = Mock(
                valid=True,
                issues=[],
                recommendations=["Test recommendation"],
                network_info={"firewall_available": False}
            )
            
            report = auditor.perform_comprehensive_audit()
            
            assert report.audit_id is not None
            assert report.deployment_method == "docker"
            assert report.security_level == "standard"
            assert report.total_findings >= 0
            assert isinstance(report.security_score, int)
            assert report.security_grade in ["A", "B", "C", "D", "F"]


class TestDeploymentSecurityManager:
    """Test deployment security manager integration."""
    
    def create_test_config(self):
        """Create test configuration."""
        from pydantic import SecretStr
        
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config={
                "host": "http://localhost:7700",
                "api_key": SecretStr("test_api_key")
            },
            security_config=SecurityConfig(
                security_level=SecurityLevel.STANDARD,
                api_key_required=True
            ),
            config_path="/tmp/test_config"
        )
    
    def test_security_manager_initialization(self):
        """Test security manager initialization."""
        config = self.create_test_config()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config.config_path = temp_dir
            
            os.environ['THAI_TOKENIZER_MASTER_PASSWORD'] = 'test_master_password_123'
            
            try:
                manager = DeploymentSecurityManager(config)
                assert manager.config == config
                assert manager.credential_store is not None
                assert manager.api_key_manager is not None
                assert manager.ssl_manager is not None
                assert manager.config_protection_manager is not None
                
            finally:
                del os.environ['THAI_TOKENIZER_MASTER_PASSWORD']
    
    def test_security_status(self):
        """Test security status retrieval."""
        config = self.create_test_config()
        
        with tempfile.TemporaryDirectory() as temp_dir:
            config.config_path = temp_dir
            
            os.environ['THAI_TOKENIZER_MASTER_PASSWORD'] = 'test_master_password_123'
            
            try:
                manager = DeploymentSecurityManager(config)
                status = manager.get_security_status()
                
                assert "security_level" in status
                assert "credentials" in status
                assert "api_keys" in status
                assert "ssl_tls" in status
                assert "configuration" in status
                assert status["security_level"] == "standard"
                
            finally:
                del os.environ['THAI_TOKENIZER_MASTER_PASSWORD']


if __name__ == "__main__":
    pytest.main([__file__])