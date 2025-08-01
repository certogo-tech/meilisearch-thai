"""
Unit tests for deployment configuration management system.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from pydantic import ValidationError

from src.deployment.config import (
    OnPremiseConfig,
    DeploymentMethod,
    MeilisearchConnectionConfig,
    ServiceConfig,
    SecurityConfig,
    ResourceConfig,
    MonitoringConfig,
    SecurityLevel,
    ConnectionStatus,
    MeilisearchConnectionTester,
    ConfigurationValidator
)
from src.deployment.templates import DeploymentTemplates, ConfigurationExporter


class TestMeilisearchConnectionConfig:
    """Test Meilisearch connection configuration."""
    
    def test_valid_config(self):
        """Test valid Meilisearch configuration."""
        config = MeilisearchConnectionConfig(
            host="http://localhost:7700",
            api_key="test-key"
        )
        assert config.host == "http://localhost:7700"
        assert config.api_key.get_secret_value() == "test-key"
        assert config.full_url == "http://localhost:7700"
    
    def test_host_validation(self):
        """Test host URL validation."""
        # Test automatic http:// prefix
        config = MeilisearchConnectionConfig(
            host="localhost:7700",
            api_key="test-key"
        )
        assert config.host == "http://localhost:7700"
        
        # Test trailing slash removal
        config = MeilisearchConnectionConfig(
            host="http://localhost:7700/",
            api_key="test-key"
        )
        assert config.host == "http://localhost:7700"
    
    def test_invalid_config(self):
        """Test invalid configuration validation."""
        with pytest.raises(ValidationError):
            MeilisearchConnectionConfig(
                host="",  # Empty host
                api_key="test-key"
            )
        
        with pytest.raises(ValidationError):
            MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key="test-key",
                timeout_seconds=0  # Invalid timeout
            )


class TestServiceConfig:
    """Test service configuration."""
    
    def test_valid_config(self):
        """Test valid service configuration."""
        config = ServiceConfig(
            service_name="thai-tokenizer",
            service_port=8000
        )
        assert config.service_name == "thai-tokenizer"
        assert config.service_port == 8000
    
    def test_service_name_validation(self):
        """Test service name validation."""
        # Valid names
        ServiceConfig(service_name="thai-tokenizer")
        ServiceConfig(service_name="thai_tokenizer")
        ServiceConfig(service_name="thaitokenizer123")
        
        # Invalid names
        with pytest.raises(ValidationError):
            ServiceConfig(service_name="")
        
        with pytest.raises(ValidationError):
            ServiceConfig(service_name="thai tokenizer")  # Space not allowed


class TestOnPremiseConfig:
    """Test comprehensive on-premise configuration."""
    
    def test_valid_config(self):
        """Test valid on-premise configuration."""
        config = OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key="test-key"
            )
        )
        assert config.deployment_method == DeploymentMethod.DOCKER
        assert config.meilisearch_config.host == "http://localhost:7700"
    
    def test_environment_variables(self):
        """Test environment variable generation."""
        config = OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key="test-key"
            )
        )
        
        env_vars = config.get_environment_dict()
        
        assert "THAI_TOKENIZER_SERVICE_NAME" in env_vars
        assert "THAI_TOKENIZER_MEILISEARCH_HOST" in env_vars
        assert "THAI_TOKENIZER_MEILISEARCH_API_KEY" in env_vars
        assert env_vars["THAI_TOKENIZER_SERVICE_PORT"] == "8000"
        assert env_vars["THAI_TOKENIZER_MEILISEARCH_HOST"] == "http://localhost:7700"
    
    def test_path_validation(self):
        """Test path validation."""
        config = OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key="test-key"
            ),
            installation_path="/tmp/test-install",
            data_path="/tmp/test-data"
        )
        
        result = config.validate_paths()
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)


class TestMeilisearchConnectionTester:
    """Test Meilisearch connection testing."""
    
    @pytest.fixture
    def config(self):
        """Create test configuration."""
        return MeilisearchConnectionConfig(
            host="http://localhost:7700",
            api_key="test-key",
            timeout_seconds=5
        )
    
    @pytest.fixture
    def tester(self, config):
        """Create connection tester."""
        return MeilisearchConnectionTester(config)
    
    @pytest.mark.asyncio
    async def test_successful_connection(self, tester):
        """Test successful connection."""
        with patch('httpx.AsyncClient') as mock_client:
            # Mock successful health check
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "available"}
            
            # Mock version endpoint
            mock_version_response = MagicMock()
            mock_version_response.status_code = 200
            mock_version_response.json.return_value = {"pkgVersion": "1.5.0"}
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = [mock_response, mock_version_response]
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await tester.test_connection()
            
            assert result.status == ConnectionStatus.CONNECTED
            assert result.meilisearch_version == "1.5.0"
            assert result.response_time_ms is not None
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, tester):
        """Test connection timeout."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = asyncio.TimeoutError()
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await tester.test_connection()
            
            assert result.status == ConnectionStatus.TIMEOUT
            assert "timeout" in result.error_message.lower()
    
    @pytest.mark.asyncio
    async def test_connection_error(self, tester):
        """Test connection error."""
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = MagicMock()
            mock_response.status_code = 500
            mock_response.text = "Internal Server Error"
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.return_value = mock_response
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await tester.test_connection()
            
            assert result.status == ConnectionStatus.ERROR
            assert "500" in result.error_message
    
    @pytest.mark.asyncio
    async def test_connection_with_retries(self, tester):
        """Test connection with retry logic."""
        with patch('httpx.AsyncClient') as mock_client:
            # First attempt fails, second succeeds
            mock_error_response = MagicMock()
            mock_error_response.status_code = 500
            mock_error_response.text = "Error"
            
            mock_success_response = MagicMock()
            mock_success_response.status_code = 200
            
            # Mock version response with proper JSON
            mock_version_response = MagicMock()
            mock_version_response.status_code = 200
            mock_version_response.json.return_value = {"pkgVersion": "1.5.0"}
            
            mock_client_instance = AsyncMock()
            mock_client_instance.get.side_effect = [
                mock_error_response,  # First attempt fails
                mock_success_response,  # Second attempt succeeds
                mock_version_response   # Version check
            ]
            mock_client.return_value.__aenter__.return_value = mock_client_instance
            
            result = await tester.test_connection_with_retries()
            
            assert result.status == ConnectionStatus.CONNECTED


class TestConfigurationValidator:
    """Test configuration validation."""
    
    @pytest.fixture
    def valid_config(self):
        """Create valid configuration for testing."""
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key="test-key"
            ),
            service_config=ServiceConfig(
                service_port=8000
            ),
            resource_config=ResourceConfig(
                metrics_port=9090
            )
        )
    
    @pytest.fixture
    def validator(self, valid_config):
        """Create configuration validator."""
        return ConfigurationValidator(valid_config)
    
    def test_port_validation(self, validator):
        """Test port validation."""
        result = validator._validate_ports()
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
    
    def test_security_validation(self, validator):
        """Test security validation."""
        result = validator._validate_security()
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
    
    def test_resource_validation(self, validator):
        """Test resource validation."""
        result = validator._validate_resources()
        assert isinstance(result.valid, bool)
        assert isinstance(result.errors, list)
        assert isinstance(result.warnings, list)
    
    def test_port_conflict_detection(self):
        """Test port conflict detection."""
        config = OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key="test-key"
            ),
            service_config=ServiceConfig(
                service_port=8000
            ),
            resource_config=ResourceConfig(
                metrics_port=8000  # Same as service port - conflict!
            )
        )
        
        validator = ConfigurationValidator(config)
        result = validator._validate_ports()
        
        assert not result.valid
        assert any("conflict" in error.lower() for error in result.errors)


class TestDeploymentTemplates:
    """Test deployment templates."""
    
    def test_docker_template(self):
        """Test Docker template creation."""
        config = DeploymentTemplates.create_docker_template(
            meilisearch_host="http://localhost:7700",
            meilisearch_api_key="test-key"
        )
        
        assert config.deployment_method == DeploymentMethod.DOCKER
        assert config.meilisearch_config.host == "http://localhost:7700"
        assert config.service_config.service_host == "0.0.0.0"
        assert config.installation_path == "/app"
    
    def test_systemd_template(self):
        """Test systemd template creation."""
        config = DeploymentTemplates.create_systemd_template(
            meilisearch_host="http://localhost:7700",
            meilisearch_api_key="test-key"
        )
        
        assert config.deployment_method == DeploymentMethod.SYSTEMD
        assert config.service_config.service_host == "127.0.0.1"
        assert config.installation_path == "/opt/thai-tokenizer"
        assert config.monitoring_config.log_file_path is not None
    
    def test_standalone_template(self):
        """Test standalone template creation."""
        config = DeploymentTemplates.create_standalone_template(
            meilisearch_host="http://localhost:7700",
            meilisearch_api_key="test-key"
        )
        
        assert config.deployment_method == DeploymentMethod.STANDALONE
        assert config.service_config.worker_processes == 1
        assert config.resource_config.enable_metrics is False
    
    def test_template_recommendations(self):
        """Test template recommendations."""
        recommendations = DeploymentTemplates.get_template_recommendations()
        
        assert "docker" in recommendations
        assert "systemd" in recommendations
        assert "standalone" in recommendations
        
        for method, info in recommendations.items():
            assert "name" in info
            assert "description" in info
            assert "best_for" in info
            assert "requirements" in info
            assert "pros" in info
            assert "cons" in info


class TestConfigurationExporter:
    """Test configuration export functionality."""
    
    @pytest.fixture
    def docker_config(self):
        """Create Docker configuration for testing."""
        return DeploymentTemplates.create_docker_template(
            meilisearch_host="http://localhost:7700",
            meilisearch_api_key="test-key"
        )
    
    @pytest.fixture
    def systemd_config(self):
        """Create systemd configuration for testing."""
        return DeploymentTemplates.create_systemd_template(
            meilisearch_host="http://localhost:7700",
            meilisearch_api_key="test-key"
        )
    
    def test_env_file_export(self, docker_config):
        """Test environment file export."""
        content = ConfigurationExporter.to_env_file(docker_config)
        
        assert "THAI_TOKENIZER_SERVICE_NAME=" in content
        assert "THAI_TOKENIZER_MEILISEARCH_HOST=" in content
        assert "# Service Configuration" in content
        assert "# Meilisearch Configuration" in content
    
    def test_docker_compose_export(self, docker_config):
        """Test Docker Compose export."""
        content = ConfigurationExporter.to_docker_compose(docker_config)
        
        assert "version: '3.8'" in content
        assert "thai-tokenizer:" in content
        assert "environment:" in content
        assert "healthcheck:" in content
        assert "deploy:" in content
    
    def test_systemd_unit_export(self, systemd_config):
        """Test systemd unit file export."""
        content = ConfigurationExporter.to_systemd_unit(systemd_config)
        
        assert "[Unit]" in content
        assert "[Service]" in content
        assert "[Install]" in content
        assert "Description=Thai Tokenizer Service" in content
        assert "ExecStart=" in content
    
    def test_invalid_export_method(self, systemd_config):
        """Test invalid export method."""
        with pytest.raises(ValueError):
            ConfigurationExporter.to_docker_compose(systemd_config)
        
        docker_config = DeploymentTemplates.create_docker_template(
            meilisearch_host="http://localhost:7700",
            meilisearch_api_key="test-key"
        )
        
        with pytest.raises(ValueError):
            ConfigurationExporter.to_systemd_unit(docker_config)


if __name__ == "__main__":
    pytest.main([__file__])