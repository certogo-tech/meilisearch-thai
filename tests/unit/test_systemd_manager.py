"""
Unit tests for systemd deployment manager.

Tests the systemd service configuration, user management, and deployment
functionality for the Thai Tokenizer service.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from pydantic import SecretStr

from src.deployment.config import (
    OnPremiseConfig,
    DeploymentMethod,
    MeilisearchConnectionConfig,
    ServiceConfig,
    SecurityConfig,
    ResourceConfig,
    MonitoringConfig
)
from src.deployment.systemd_manager import (
    SystemdUserManager,
    SystemdServiceGenerator,
    SystemdServiceManager,
    SystemdDeploymentValidator
)


@pytest.fixture
def sample_config():
    """Create a sample systemd configuration for testing."""
    return OnPremiseConfig(
        deployment_method=DeploymentMethod.SYSTEMD,
        meilisearch_config=MeilisearchConnectionConfig(
            host="http://localhost:7700",
            api_key=SecretStr("test-api-key")
        ),
        service_config=ServiceConfig(
            service_name="thai-tokenizer-test",
            service_port=8001,
            service_user="thai-tokenizer-test",
            service_group="thai-tokenizer-test"
        ),
        security_config=SecurityConfig(),
        resource_config=ResourceConfig(
            memory_limit_mb=256,
            cpu_limit_cores=0.5
        ),
        monitoring_config=MonitoringConfig(),
        installation_path="/opt/thai-tokenizer-test",
        data_path="/var/lib/thai-tokenizer-test",
        log_path="/var/log/thai-tokenizer-test",
        config_path="/etc/thai-tokenizer-test"
    )


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


class TestSystemdUserManager:
    """Test systemd user management functionality."""
    
    def test_user_manager_initialization(self, sample_config):
        """Test SystemdUserManager initialization."""
        manager = SystemdUserManager(sample_config)
        assert manager.config == sample_config
        assert manager.logger is not None
    
    @patch('pwd.getpwnam')
    def test_user_exists_true(self, mock_getpwnam, sample_config):
        """Test user_exists returns True when user exists."""
        mock_getpwnam.return_value = Mock()
        manager = SystemdUserManager(sample_config)
        
        assert manager.user_exists("existing-user") is True
        mock_getpwnam.assert_called_once_with("existing-user")
    
    @patch('pwd.getpwnam')
    def test_user_exists_false(self, mock_getpwnam, sample_config):
        """Test user_exists returns False when user doesn't exist."""
        mock_getpwnam.side_effect = KeyError("User not found")
        manager = SystemdUserManager(sample_config)
        
        assert manager.user_exists("nonexistent-user") is False
        mock_getpwnam.assert_called_once_with("nonexistent-user")
    
    @patch('grp.getgrnam')
    def test_group_exists_true(self, mock_getgrnam, sample_config):
        """Test group_exists returns True when group exists."""
        mock_getgrnam.return_value = Mock()
        manager = SystemdUserManager(sample_config)
        
        assert manager.group_exists("existing-group") is True
        mock_getgrnam.assert_called_once_with("existing-group")
    
    @patch('grp.getgrnam')
    def test_group_exists_false(self, mock_getgrnam, sample_config):
        """Test group_exists returns False when group doesn't exist."""
        mock_getgrnam.side_effect = KeyError("Group not found")
        manager = SystemdUserManager(sample_config)
        
        assert manager.group_exists("nonexistent-group") is False
        mock_getgrnam.assert_called_once_with("nonexistent-group")
    
    @patch('subprocess.run')
    @patch('src.deployment.systemd_manager.SystemdUserManager.group_exists')
    @patch('src.deployment.systemd_manager.SystemdUserManager.user_exists')
    def test_create_user_success(self, mock_user_exists, mock_group_exists, mock_subprocess, sample_config):
        """Test successful user creation."""
        mock_user_exists.return_value = False
        mock_group_exists.return_value = False
        mock_subprocess.return_value = Mock(returncode=0, stderr="")
        
        manager = SystemdUserManager(sample_config)
        result = manager.create_user("test-user", "test-group", "/home/test-user")
        
        assert result.valid is True
        assert len(result.warnings) >= 2  # Group and user creation warnings
        assert len(result.errors) == 0
        
        # Verify subprocess calls
        assert mock_subprocess.call_count == 2  # groupadd and useradd
    
    @patch('subprocess.run')
    @patch('src.deployment.systemd_manager.SystemdUserManager.group_exists')
    @patch('src.deployment.systemd_manager.SystemdUserManager.user_exists')
    def test_create_user_already_exists(self, mock_user_exists, mock_group_exists, mock_subprocess, sample_config):
        """Test user creation when user already exists."""
        mock_user_exists.return_value = True
        mock_group_exists.return_value = True
        
        manager = SystemdUserManager(sample_config)
        result = manager.create_user("existing-user", "existing-group", "/home/existing-user")
        
        assert result.valid is True
        assert "already exists" in " ".join(result.warnings)
        mock_subprocess.assert_not_called()
    
    @patch('subprocess.run')
    @patch('src.deployment.systemd_manager.SystemdUserManager.group_exists')
    @patch('src.deployment.systemd_manager.SystemdUserManager.user_exists')
    def test_create_user_failure(self, mock_user_exists, mock_group_exists, mock_subprocess, sample_config):
        """Test user creation failure."""
        mock_user_exists.return_value = False
        mock_group_exists.return_value = False
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "useradd", stderr="Permission denied")
        
        manager = SystemdUserManager(sample_config)
        result = manager.create_user("test-user", "test-group", "/home/test-user")
        
        assert result.valid is False
        assert len(result.errors) > 0
        assert "Permission denied" in result.errors[0]


class TestSystemdServiceGenerator:
    """Test systemd service file generation."""
    
    def test_service_generator_initialization(self, sample_config):
        """Test SystemdServiceGenerator initialization."""
        generator = SystemdServiceGenerator(sample_config)
        assert generator.config == sample_config
        assert generator.logger is not None
    
    def test_get_template_substitutions(self, sample_config):
        """Test template substitution variable generation."""
        generator = SystemdServiceGenerator(sample_config)
        substitutions = generator._get_template_substitutions()
        
        # Check required substitutions
        assert substitutions["SERVICE_NAME"] == "thai-tokenizer-test"
        assert substitutions["SERVICE_USER"] == "thai-tokenizer-test"
        assert substitutions["SERVICE_GROUP"] == "thai-tokenizer-test"
        assert substitutions["SERVICE_PORT"] == "8001"
        assert substitutions["INSTALLATION_PATH"] == "/opt/thai-tokenizer-test"
        assert substitutions["MEMORY_LIMIT_MB"] == "256"
        assert substitutions["CPU_QUOTA"] == "50"  # 0.5 * 100
    
    def test_generate_service_file(self, sample_config, temp_dir):
        """Test systemd service file generation."""
        generator = SystemdServiceGenerator(sample_config)
        
        # Create a simple template
        template_path = Path(temp_dir) / "test.service.template"
        template_content = """[Unit]
Description=Test Service
[Service]
User={{SERVICE_USER}}
ExecStart={{INSTALLATION_PATH}}/bin/service
[Install]
WantedBy=multi-user.target"""
        
        template_path.write_text(template_content)
        
        # Generate service file
        output_path = Path(temp_dir) / "test.service"
        result = generator.generate_service_file(str(template_path), str(output_path))
        
        assert result.valid is True
        assert output_path.exists()
        
        # Check content
        generated_content = output_path.read_text()
        assert "User=thai-tokenizer-test" in generated_content
        assert "ExecStart=/opt/thai-tokenizer-test/bin/service" in generated_content
    
    def test_generate_service_file_missing_template(self, sample_config, temp_dir):
        """Test service file generation with missing template."""
        generator = SystemdServiceGenerator(sample_config)
        
        template_path = Path(temp_dir) / "nonexistent.template"
        output_path = Path(temp_dir) / "test.service"
        
        result = generator.generate_service_file(str(template_path), str(output_path))
        
        assert result.valid is False
        assert "Template file not found" in result.errors[0]
    
    def test_generate_environment_file(self, sample_config, temp_dir):
        """Test environment file generation."""
        generator = SystemdServiceGenerator(sample_config)
        
        output_path = Path(temp_dir) / "environment"
        result = generator.generate_environment_file(str(output_path))
        
        assert result.valid is True
        assert output_path.exists()
        
        # Check content
        env_content = output_path.read_text()
        assert "THAI_TOKENIZER_SERVICE_NAME" in env_content
        assert "THAI_TOKENIZER_MEILISEARCH_HOST" in env_content
        assert "test-api-key" in env_content  # API key should be present


class TestSystemdServiceManager:
    """Test systemd service management operations."""
    
    def test_service_manager_initialization(self):
        """Test SystemdServiceManager initialization."""
        manager = SystemdServiceManager("test-service")
        assert manager.service_name == "test-service"
        assert manager.logger is not None
    
    @patch('subprocess.run')
    @patch('shutil.copy2')
    def test_install_service_success(self, mock_copy, mock_subprocess, temp_dir):
        """Test successful service installation."""
        manager = SystemdServiceManager("test-service")
        
        # Create a test service file
        service_file = Path(temp_dir) / "test.service"
        service_file.write_text("[Unit]\nDescription=Test\n")
        
        mock_subprocess.return_value = Mock(returncode=0)
        
        result = manager.install_service(str(service_file))
        
        assert result.valid is True
        mock_copy.assert_called_once()
        mock_subprocess.assert_called_once_with(
            ["systemctl", "daemon-reload"],
            check=True,
            capture_output=True
        )
    
    @patch('subprocess.run')
    def test_install_service_missing_file(self, mock_subprocess, temp_dir):
        """Test service installation with missing file."""
        manager = SystemdServiceManager("test-service")
        
        nonexistent_file = Path(temp_dir) / "nonexistent.service"
        result = manager.install_service(str(nonexistent_file))
        
        assert result.valid is False
        assert "Service file not found" in result.errors[0]
        mock_subprocess.assert_not_called()
    
    @patch('subprocess.run')
    def test_enable_service_success(self, mock_subprocess):
        """Test successful service enabling."""
        manager = SystemdServiceManager("test-service")
        mock_subprocess.return_value = Mock(returncode=0, stderr="")
        
        result = manager.enable_service()
        
        assert result.valid is True
        mock_subprocess.assert_called_once_with(
            ["systemctl", "enable", "test-service"],
            check=True,
            capture_output=True,
            text=True
        )
    
    @patch('subprocess.run')
    def test_enable_service_failure(self, mock_subprocess):
        """Test service enabling failure."""
        manager = SystemdServiceManager("test-service")
        mock_subprocess.side_effect = subprocess.CalledProcessError(
            1, "systemctl", stderr="Service not found"
        )
        
        result = manager.enable_service()
        
        assert result.valid is False
        assert "Service not found" in result.errors[0]
    
    @patch('subprocess.run')
    def test_start_service_success(self, mock_subprocess):
        """Test successful service start."""
        manager = SystemdServiceManager("test-service")
        mock_subprocess.return_value = Mock(returncode=0, stderr="")
        
        result = manager.start_service()
        
        assert result.valid is True
        mock_subprocess.assert_called_once_with(
            ["systemctl", "start", "test-service"],
            check=True,
            capture_output=True,
            text=True
        )
    
    @patch('subprocess.run')
    def test_get_service_status_active(self, mock_subprocess):
        """Test getting active service status."""
        manager = SystemdServiceManager("test-service")
        mock_subprocess.return_value = Mock(returncode=0, stdout="active\n")
        
        is_active, status = manager.get_service_status()
        
        assert is_active is True
        assert status == "active"
    
    @patch('subprocess.run')
    def test_get_service_status_inactive(self, mock_subprocess):
        """Test getting inactive service status."""
        manager = SystemdServiceManager("test-service")
        
        # Mock the is-active call (returns non-zero for inactive)
        mock_subprocess.side_effect = [
            Mock(returncode=1, stdout="inactive\n"),  # is-active call
            Mock(returncode=0, stdout="● test-service - Test Service\n   Loaded: loaded\n   Active: inactive")  # status call
        ]
        
        is_active, status = manager.get_service_status()
        
        assert is_active is False
        assert "Test Service" in status


class TestSystemdDeploymentValidator:
    """Test systemd deployment validation."""
    
    def test_validator_initialization(self, sample_config):
        """Test SystemdDeploymentValidator initialization."""
        validator = SystemdDeploymentValidator(sample_config)
        assert validator.config == sample_config
        assert validator.logger is not None
    
    @patch('subprocess.run')
    @patch('os.geteuid')
    @patch('socket.socket')
    def test_validate_system_requirements_success(self, mock_socket, mock_geteuid, mock_subprocess, sample_config):
        """Test successful system requirements validation."""
        validator = SystemdDeploymentValidator(sample_config)
        
        # Mock successful conditions
        mock_geteuid.return_value = 0  # Running as root
        mock_subprocess.return_value = Mock(returncode=0)  # systemctl and uv available
        
        # Mock socket for port availability
        mock_socket_instance = Mock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.bind.return_value = None  # Port available
        
        result = validator.validate_system_requirements()
        
        assert result.valid is True
        assert any("systemd is available" in warning for warning in result.warnings)
        assert any("Python" in warning for warning in result.warnings)
    
    @patch('subprocess.run')
    @patch('os.geteuid')
    def test_validate_system_requirements_no_root(self, mock_geteuid, mock_subprocess, sample_config):
        """Test system requirements validation without root privileges."""
        validator = SystemdDeploymentValidator(sample_config)
        
        mock_geteuid.return_value = 1000  # Not running as root
        mock_subprocess.return_value = Mock(returncode=0)
        
        result = validator.validate_system_requirements()
        
        assert result.valid is False
        assert any("root privileges" in error for error in result.errors)
    
    @patch('subprocess.run')
    @patch('os.geteuid')
    def test_validate_system_requirements_no_systemd(self, mock_geteuid, mock_subprocess, sample_config):
        """Test system requirements validation without systemd."""
        validator = SystemdDeploymentValidator(sample_config)
        
        mock_geteuid.return_value = 0
        mock_subprocess.side_effect = FileNotFoundError("systemctl not found")
        
        result = validator.validate_system_requirements()
        
        assert result.valid is False
        assert any("systemd is not available" in error for error in result.errors)
    
    @patch('socket.socket')
    def test_validate_system_requirements_port_conflict(self, mock_socket, sample_config):
        """Test system requirements validation with port conflict."""
        validator = SystemdDeploymentValidator(sample_config)
        
        # Mock port conflict
        mock_socket_instance = Mock()
        mock_socket.return_value.__enter__.return_value = mock_socket_instance
        mock_socket_instance.bind.side_effect = OSError("Address already in use")
        
        with patch('subprocess.run') as mock_subprocess, \
             patch('os.geteuid', return_value=0):
            mock_subprocess.return_value = Mock(returncode=0)
            
            result = validator.validate_system_requirements()
            
            assert result.valid is False
            assert any("already in use" in error for error in result.errors)
    
    @patch('subprocess.run')
    def test_validate_service_dependencies(self, mock_subprocess, sample_config):
        """Test service dependencies validation."""
        validator = SystemdDeploymentValidator(sample_config)
        
        mock_subprocess.return_value = Mock(returncode=0)  # network.target is active
        
        result = validator.validate_service_dependencies()
        
        assert result.valid is True
        assert any("network.target is active" in warning for warning in result.warnings)


# Import subprocess for the tests that need it
import subprocess