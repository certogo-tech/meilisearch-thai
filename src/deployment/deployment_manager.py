"""
Deployment orchestration system for Thai Tokenizer on-premise deployment.

This module provides the main DeploymentManager class that orchestrates
deployment across different methods (Docker, systemd, standalone) with
comprehensive validation, progress tracking, and reporting.
"""

import asyncio
import logging
import os
import sys
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
import json

from pydantic import BaseModel, Field

try:
    from src.deployment.config import (
        OnPremiseConfig, DeploymentMethod, ValidationResult, 
        ConfigurationValidator, MeilisearchConnectionTester
    )
    from src.deployment.systemd_manager import SystemdServiceManager, SystemdUserManager, SystemdServiceGenerator
    from src.utils.logging import get_structured_logger
except ImportError:
    # Fallback for when running outside the main application
    try:
        from deployment.config import (
            OnPremiseConfig, DeploymentMethod, ValidationResult, 
            ConfigurationValidator, MeilisearchConnectionTester
        )
        from deployment.systemd_manager import SystemdServiceManager, SystemdUserManager, SystemdServiceGenerator
        from utils.logging import get_structured_logger
    except ImportError:
        # Define minimal fallbacks
        from enum import Enum
        class DeploymentMethod(Enum):
            DOCKER = "docker"
            SYSTEMD = "systemd"
            STANDALONE = "standalone"
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class DeploymentStatus(str, Enum):
    """Deployment status enumeration."""
    NOT_STARTED = "not_started"
    VALIDATING = "validating"
    PREPARING = "preparing"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    STARTING = "starting"
    VERIFYING = "verifying"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLED_BACK = "rolled_back"


class DeploymentStep(BaseModel):
    """Individual deployment step information."""
    name: str = Field(description="Step name")
    description: str = Field(description="Step description")
    status: DeploymentStatus = Field(default=DeploymentStatus.NOT_STARTED)
    start_time: Optional[datetime] = Field(default=None)
    end_time: Optional[datetime] = Field(default=None)
    error_message: Optional[str] = Field(default=None)
    warnings: List[str] = Field(default_factory=list)
    details: Dict[str, Any] = Field(default_factory=dict)
    
    @property
    def duration_seconds(self) -> Optional[float]:
        """Get step duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None


class DeploymentProgress(BaseModel):
    """Deployment progress tracking."""
    deployment_id: str = Field(description="Unique deployment identifier")
    deployment_method: DeploymentMethod = Field(description="Deployment method")
    overall_status: DeploymentStatus = Field(default=DeploymentStatus.NOT_STARTED)
    start_time: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = Field(default=None)
    steps: List[DeploymentStep] = Field(default_factory=list)
    current_step_index: int = Field(default=0)
    progress_percentage: float = Field(default=0.0)
    
    @property
    def current_step(self) -> Optional[DeploymentStep]:
        """Get current deployment step."""
        if 0 <= self.current_step_index < len(self.steps):
            return self.steps[self.current_step_index]
        return None
    
    @property
    def total_duration_seconds(self) -> Optional[float]:
        """Get total deployment duration in seconds."""
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    def update_progress(self):
        """Update progress percentage based on completed steps."""
        if not self.steps:
            self.progress_percentage = 0.0
            return
        
        completed_steps = sum(
            1 for step in self.steps 
            if step.status in [DeploymentStatus.COMPLETED, DeploymentStatus.FAILED]
        )
        self.progress_percentage = (completed_steps / len(self.steps)) * 100.0


class DeploymentResult(BaseModel):
    """Final deployment result."""
    success: bool = Field(description="Whether deployment was successful")
    deployment_id: str = Field(description="Unique deployment identifier")
    deployment_method: DeploymentMethod = Field(description="Deployment method used")
    progress: DeploymentProgress = Field(description="Deployment progress information")
    service_info: Dict[str, Any] = Field(default_factory=dict, description="Service information")
    endpoints: Dict[str, str] = Field(default_factory=dict, description="Service endpoints")
    configuration_path: Optional[str] = Field(default=None, description="Configuration file path")
    log_file_path: Optional[str] = Field(default=None, description="Log file path")
    rollback_available: bool = Field(default=False, description="Whether rollback is available")
    
    @property
    def summary(self) -> str:
        """Get deployment summary."""
        status = "SUCCESS" if self.success else "FAILED"
        duration = self.progress.total_duration_seconds
        duration_str = f" in {duration:.1f}s" if duration else ""
        return f"Deployment {status}: {self.deployment_method.value}{duration_str}"


class DeploymentInterface(ABC):
    """Abstract interface for deployment methods."""
    
    @abstractmethod
    async def validate_requirements(self) -> ValidationResult:
        """Validate system requirements for this deployment method."""
        pass
    
    @abstractmethod
    async def install_dependencies(self) -> ValidationResult:
        """Install required dependencies."""
        pass
    
    @abstractmethod
    async def configure_service(self, config: OnPremiseConfig) -> ValidationResult:
        """Configure the service for deployment."""
        pass
    
    @abstractmethod
    async def start_service(self) -> ValidationResult:
        """Start the deployed service."""
        pass
    
    @abstractmethod
    async def verify_deployment(self) -> ValidationResult:
        """Verify the deployment is working correctly."""
        pass
    
    @abstractmethod
    async def stop_service(self) -> ValidationResult:
        """Stop the deployed service."""
        pass
    
    @abstractmethod
    async def cleanup(self) -> ValidationResult:
        """Clean up deployment resources."""
        pass


class DockerDeployment(DeploymentInterface):
    """Docker deployment implementation."""
    
    def __init__(self, config: OnPremiseConfig):
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.DockerDeployment")
        self.project_root = Path(__file__).parent.parent.parent
        self.docker_dir = self.project_root / "deployment" / "docker"
    
    async def validate_requirements(self) -> ValidationResult:
        """Validate Docker deployment requirements."""
        result = ValidationResult(valid=True)
        
        try:
            # Check Docker availability
            import subprocess
            docker_check = subprocess.run(
                ["docker", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if docker_check.returncode != 0:
                result.valid = False
                result.errors.append("Docker is not installed or not accessible")
                return result
            
            # Check Docker Compose
            compose_check = subprocess.run(
                ["docker", "compose", "version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if compose_check.returncode != 0:
                result.valid = False
                result.errors.append("Docker Compose is not available")
                return result
            
            # Check Docker daemon
            daemon_check = subprocess.run(
                ["docker", "info"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if daemon_check.returncode != 0:
                result.valid = False
                result.errors.append("Docker daemon is not running")
                return result
            
            result.warnings.append("Docker environment validated successfully")
            
        except subprocess.TimeoutExpired:
            result.valid = False
            result.errors.append("Docker command timeout")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Docker validation error: {e}")
        
        return result
    
    async def install_dependencies(self) -> ValidationResult:
        """Install Docker deployment dependencies."""
        result = ValidationResult(valid=True)
        
        try:
            # Check if Docker Compose file exists
            compose_file = self.docker_dir / "docker-compose.external-meilisearch.yml"
            if not compose_file.exists():
                result.valid = False
                result.errors.append(f"Docker Compose file not found: {compose_file}")
                return result
            
            # Create necessary directories
            log_dir = self.project_root / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            
            result.warnings.append("Docker deployment dependencies prepared")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to prepare Docker dependencies: {e}")
        
        return result
    
    async def configure_service(self, config: OnPremiseConfig) -> ValidationResult:
        """Configure Docker service."""
        result = ValidationResult(valid=True)
        
        try:
            # Create environment file
            env_file = self.docker_dir / ".env.external-meilisearch"
            env_vars = config.get_environment_dict()
            
            env_lines = [
                "# Thai Tokenizer Docker Environment Configuration",
                "# Generated for external Meilisearch deployment",
                "",
            ]
            
            for key, value in sorted(env_vars.items()):
                env_lines.append(f"{key}={value}")
            
            env_content = "\n".join(env_lines)
            env_file.write_text(env_content, encoding="utf-8")
            
            result.warnings.append(f"Docker environment configured: {env_file}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to configure Docker service: {e}")
        
        return result
    
    async def start_service(self) -> ValidationResult:
        """Start Docker service."""
        result = ValidationResult(valid=True)
        
        try:
            import subprocess
            
            compose_file = self.docker_dir / "docker-compose.external-meilisearch.yml"
            env_file = self.docker_dir / ".env.external-meilisearch"
            
            cmd = [
                "docker", "compose", 
                "-f", str(compose_file),
                "--env-file", str(env_file),
                "up", "-d", "--build"
            ]
            
            process = subprocess.run(
                cmd,
                cwd=self.docker_dir,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if process.returncode != 0:
                result.valid = False
                result.errors.append(f"Docker service start failed: {process.stderr}")
                return result
            
            result.warnings.append("Docker service started successfully")
            
        except subprocess.TimeoutExpired:
            result.valid = False
            result.errors.append("Docker service start timeout")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to start Docker service: {e}")
        
        return result
    
    async def verify_deployment(self) -> ValidationResult:
        """Verify Docker deployment."""
        result = ValidationResult(valid=True)
        
        try:
            # Wait for service to be ready
            await asyncio.sleep(10)
            
            # Check service health
            import requests
            service_port = self.config.service_config.service_port
            health_url = f"http://localhost:{service_port}/health"
            
            response = requests.get(health_url, timeout=10)
            if response.status_code != 200:
                result.valid = False
                result.errors.append(f"Service health check failed: {response.status_code}")
                return result
            
            result.warnings.append("Docker deployment verified successfully")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Docker deployment verification failed: {e}")
        
        return result
    
    async def stop_service(self) -> ValidationResult:
        """Stop Docker service."""
        result = ValidationResult(valid=True)
        
        try:
            import subprocess
            
            compose_file = self.docker_dir / "docker-compose.external-meilisearch.yml"
            env_file = self.docker_dir / ".env.external-meilisearch"
            
            cmd = [
                "docker", "compose", 
                "-f", str(compose_file),
                "--env-file", str(env_file),
                "stop"
            ]
            
            process = subprocess.run(
                cmd,
                cwd=self.docker_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if process.returncode != 0:
                result.warnings.append(f"Docker service stop warning: {process.stderr}")
            else:
                result.warnings.append("Docker service stopped successfully")
            
        except Exception as e:
            result.warnings.append(f"Docker service stop error: {e}")
        
        return result
    
    async def cleanup(self) -> ValidationResult:
        """Clean up Docker deployment."""
        result = ValidationResult(valid=True)
        
        try:
            import subprocess
            
            compose_file = self.docker_dir / "docker-compose.external-meilisearch.yml"
            env_file = self.docker_dir / ".env.external-meilisearch"
            
            cmd = [
                "docker", "compose", 
                "-f", str(compose_file),
                "--env-file", str(env_file),
                "down", "--remove-orphans"
            ]
            
            process = subprocess.run(
                cmd,
                cwd=self.docker_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if process.returncode != 0:
                result.warnings.append(f"Docker cleanup warning: {process.stderr}")
            else:
                result.warnings.append("Docker cleanup completed successfully")
            
        except Exception as e:
            result.warnings.append(f"Docker cleanup error: {e}")
        
        return result


class SystemdDeployment(DeploymentInterface):
    """Systemd deployment implementation."""
    
    def __init__(self, config: OnPremiseConfig):
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.SystemdDeployment")
        self.service_manager = SystemdServiceManager(config.service_config.service_name)
        self.user_manager = SystemdUserManager(config)
        self.service_generator = SystemdServiceGenerator(config)
    
    async def validate_requirements(self) -> ValidationResult:
        """Validate systemd deployment requirements."""
        result = ValidationResult(valid=True)
        
        try:
            # Check if systemd is available
            import subprocess
            systemd_check = subprocess.run(
                ["systemctl", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if systemd_check.returncode != 0:
                result.valid = False
                result.errors.append("systemd is not available")
                return result
            
            # Check if running as root
            if os.geteuid() != 0:
                result.valid = False
                result.errors.append("systemd deployment requires root privileges")
                return result
            
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 12):
                result.valid = False
                result.errors.append(f"Python 3.12+ required, found {python_version.major}.{python_version.minor}")
            
            result.warnings.append("systemd environment validated successfully")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"systemd validation error: {e}")
        
        return result
    
    async def install_dependencies(self) -> ValidationResult:
        """Install systemd deployment dependencies."""
        result = ValidationResult(valid=True)
        
        try:
            # Create system user and directories
            user_result = self.user_manager.create_user(
                self.config.service_config.service_user,
                self.config.service_config.service_group,
                self.config.installation_path
            )
            
            if not user_result.valid:
                result.valid = False
                result.errors.extend(user_result.errors)
                return result
            
            result.warnings.extend(user_result.warnings)
            
            # Setup directories
            dir_result = self.user_manager.setup_directories(
                self.config.service_config.service_user,
                self.config.service_config.service_group
            )
            
            if not dir_result.valid:
                result.valid = False
                result.errors.extend(dir_result.errors)
                return result
            
            result.warnings.extend(dir_result.warnings)
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to install systemd dependencies: {e}")
        
        return result
    
    async def configure_service(self, config: OnPremiseConfig) -> ValidationResult:
        """Configure systemd service."""
        result = ValidationResult(valid=True)
        
        try:
            # Generate service file
            template_path = Path(__file__).parent.parent.parent / "deployment" / "systemd" / "thai-tokenizer.service.template"
            service_file_path = f"/tmp/{config.service_config.service_name}.service"
            
            service_result = self.service_generator.generate_service_file(
                str(template_path), service_file_path
            )
            
            if not service_result.valid:
                result.valid = False
                result.errors.extend(service_result.errors)
                return result
            
            result.warnings.extend(service_result.warnings)
            
            # Generate environment file
            env_file_path = f"{config.config_path}/{config.service_config.service_name}.env"
            env_result = self.service_generator.generate_environment_file(env_file_path)
            
            if not env_result.valid:
                result.valid = False
                result.errors.extend(env_result.errors)
                return result
            
            result.warnings.extend(env_result.warnings)
            
            # Install service
            install_result = self.service_manager.install_service(service_file_path)
            
            if not install_result.valid:
                result.valid = False
                result.errors.extend(install_result.errors)
                return result
            
            result.warnings.extend(install_result.warnings)
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to configure systemd service: {e}")
        
        return result
    
    async def start_service(self) -> ValidationResult:
        """Start systemd service."""
        result = ValidationResult(valid=True)
        
        try:
            # Enable service
            enable_result = self.service_manager.enable_service()
            if not enable_result.valid:
                result.warnings.extend(enable_result.errors)
            else:
                result.warnings.extend(enable_result.warnings)
            
            # Start service
            start_result = self.service_manager.start_service()
            if not start_result.valid:
                result.valid = False
                result.errors.extend(start_result.errors)
                return result
            
            result.warnings.extend(start_result.warnings)
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to start systemd service: {e}")
        
        return result
    
    async def verify_deployment(self) -> ValidationResult:
        """Verify systemd deployment."""
        result = ValidationResult(valid=True)
        
        try:
            # Wait for service to be ready
            await asyncio.sleep(10)
            
            # Check service status
            is_active, status_output = self.service_manager.get_service_status()
            if not is_active:
                result.valid = False
                result.errors.append(f"Service is not active: {status_output}")
                return result
            
            # Check service health
            import requests
            service_port = self.config.service_config.service_port
            health_url = f"http://localhost:{service_port}/health"
            
            response = requests.get(health_url, timeout=10)
            if response.status_code != 200:
                result.valid = False
                result.errors.append(f"Service health check failed: {response.status_code}")
                return result
            
            result.warnings.append("systemd deployment verified successfully")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"systemd deployment verification failed: {e}")
        
        return result
    
    async def stop_service(self) -> ValidationResult:
        """Stop systemd service."""
        result = ValidationResult(valid=True)
        
        try:
            stop_result = self.service_manager.stop_service()
            if not stop_result.valid:
                result.warnings.extend(stop_result.errors)
            else:
                result.warnings.extend(stop_result.warnings)
            
        except Exception as e:
            result.warnings.append(f"systemd service stop error: {e}")
        
        return result
    
    async def cleanup(self) -> ValidationResult:
        """Clean up systemd deployment."""
        result = ValidationResult(valid=True)
        
        try:
            # Stop service first
            await self.stop_service()
            
            # Remove service file
            import subprocess
            service_file = f"/etc/systemd/system/{self.config.service_config.service_name}.service"
            if Path(service_file).exists():
                Path(service_file).unlink()
                subprocess.run(["systemctl", "daemon-reload"], check=True)
                result.warnings.append("systemd service file removed")
            
        except Exception as e:
            result.warnings.append(f"systemd cleanup error: {e}")
        
        return result


class StandaloneDeployment(DeploymentInterface):
    """Standalone Python deployment implementation."""
    
    def __init__(self, config: OnPremiseConfig):
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.StandaloneDeployment")
        self.project_root = Path(__file__).parent.parent.parent
        self.standalone_dir = self.project_root / "deployment" / "standalone"
    
    async def validate_requirements(self) -> ValidationResult:
        """Validate standalone deployment requirements."""
        result = ValidationResult(valid=True)
        
        try:
            # Check Python version
            python_version = sys.version_info
            if python_version < (3, 12):
                result.valid = False
                result.errors.append(f"Python 3.12+ required, found {python_version.major}.{python_version.minor}")
            
            # Check uv availability
            import subprocess
            uv_check = subprocess.run(
                ["uv", "--version"], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if uv_check.returncode != 0:
                result.valid = False
                result.errors.append("uv package manager is required but not found")
                return result
            
            result.warnings.append("Standalone environment validated successfully")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Standalone validation error: {e}")
        
        return result
    
    async def install_dependencies(self) -> ValidationResult:
        """Install standalone deployment dependencies."""
        result = ValidationResult(valid=True)
        
        try:
            import subprocess
            
            # Create virtual environment
            venv_path = Path(self.config.installation_path) / "venv"
            setup_script = self.standalone_dir / "setup-venv.py"
            
            cmd = [
                sys.executable, str(setup_script),
                "--install-path", self.config.installation_path
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if process.returncode != 0:
                result.valid = False
                result.errors.append(f"Virtual environment setup failed: {process.stderr}")
                return result
            
            result.warnings.append("Standalone dependencies installed successfully")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to install standalone dependencies: {e}")
        
        return result
    
    async def configure_service(self, config: OnPremiseConfig) -> ValidationResult:
        """Configure standalone service."""
        result = ValidationResult(valid=True)
        
        try:
            # Create configuration directory
            config_dir = Path(config.installation_path) / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            
            # Write configuration file
            config_file = config_dir / "config.json"
            config_data = {
                "deployment_method": config.deployment_method.value,
                "service_config": {
                    "service_name": config.service_config.service_name,
                    "service_host": config.service_config.service_host,
                    "service_port": config.service_config.service_port,
                    "worker_processes": config.service_config.worker_processes,
                },
                "meilisearch_config": {
                    "host": config.meilisearch_config.full_url,
                    "timeout_seconds": config.meilisearch_config.timeout_seconds,
                    "max_retries": config.meilisearch_config.max_retries,
                }
            }
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            # Write environment file
            env_file = config_dir / ".env"
            env_vars = config.get_environment_dict()
            
            env_lines = [
                "# Thai Tokenizer Standalone Environment Configuration",
                "",
            ]
            
            for key, value in sorted(env_vars.items()):
                env_lines.append(f"{key}={value}")
            
            env_content = "\n".join(env_lines)
            env_file.write_text(env_content, encoding="utf-8")
            
            result.warnings.append("Standalone service configured successfully")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to configure standalone service: {e}")
        
        return result
    
    async def start_service(self) -> ValidationResult:
        """Start standalone service."""
        result = ValidationResult(valid=True)
        
        try:
            import subprocess
            
            manage_script = self.standalone_dir / "manage-service.py"
            
            cmd = [
                sys.executable, str(manage_script),
                "--install-path", self.config.installation_path,
                "start"
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if process.returncode != 0:
                result.valid = False
                result.errors.append(f"Standalone service start failed: {process.stderr}")
                return result
            
            result.warnings.append("Standalone service started successfully")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to start standalone service: {e}")
        
        return result
    
    async def verify_deployment(self) -> ValidationResult:
        """Verify standalone deployment."""
        result = ValidationResult(valid=True)
        
        try:
            # Wait for service to be ready
            await asyncio.sleep(10)
            
            # Check service health
            import requests
            service_port = self.config.service_config.service_port
            health_url = f"http://localhost:{service_port}/health"
            
            response = requests.get(health_url, timeout=10)
            if response.status_code != 200:
                result.valid = False
                result.errors.append(f"Service health check failed: {response.status_code}")
                return result
            
            result.warnings.append("Standalone deployment verified successfully")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Standalone deployment verification failed: {e}")
        
        return result
    
    async def stop_service(self) -> ValidationResult:
        """Stop standalone service."""
        result = ValidationResult(valid=True)
        
        try:
            import subprocess
            
            manage_script = self.standalone_dir / "manage-service.py"
            
            cmd = [
                sys.executable, str(manage_script),
                "--install-path", self.config.installation_path,
                "stop"
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if process.returncode != 0:
                result.warnings.append(f"Standalone service stop warning: {process.stderr}")
            else:
                result.warnings.append("Standalone service stopped successfully")
            
        except Exception as e:
            result.warnings.append(f"Standalone service stop error: {e}")
        
        return result
    
    async def cleanup(self) -> ValidationResult:
        """Clean up standalone deployment."""
        result = ValidationResult(valid=True)
        
        try:
            # Stop service first
            await self.stop_service()
            
            # Remove installation directory if requested
            # (This is typically not done automatically for safety)
            result.warnings.append("Standalone cleanup completed (installation preserved)")
            
        except Exception as e:
            result.warnings.append(f"Standalone cleanup error: {e}")
        
        return result


class DeploymentMethodFactory:
    """Factory for creating deployment method instances."""
    
    @staticmethod
    def create_deployment(method: DeploymentMethod, config: OnPremiseConfig) -> DeploymentInterface:
        """
        Create deployment instance for the specified method.
        
        Args:
            method: Deployment method
            config: Deployment configuration
            
        Returns:
            Deployment interface implementation
        """
        if method == DeploymentMethod.DOCKER:
            return DockerDeployment(config)
        elif method == DeploymentMethod.SYSTEMD:
            return SystemdDeployment(config)
        elif method == DeploymentMethod.STANDALONE:
            return StandaloneDeployment(config)
        else:
            raise ValueError(f"Unsupported deployment method: {method}")


class DeploymentManager:
    """
    Main deployment orchestration manager.
    
    Provides comprehensive deployment orchestration with method selection,
    pre-deployment validation, progress tracking, and reporting.
    """
    
    def __init__(self, config: OnPremiseConfig, progress_callback: Optional[Callable[[DeploymentProgress], None]] = None):
        """
        Initialize deployment manager.
        
        Args:
            config: Deployment configuration
            progress_callback: Optional callback for progress updates
        """
        self.config = config
        self.progress_callback = progress_callback
        self.logger = get_structured_logger(f"{__name__}.DeploymentManager")
        
        # Create deployment instance
        self.deployment = DeploymentMethodFactory.create_deployment(
            config.deployment_method, config
        )
        
        # Initialize progress tracking
        self.progress = DeploymentProgress(
            deployment_id=f"deploy_{int(datetime.now().timestamp())}",
            deployment_method=config.deployment_method
        )
        
        # Define deployment steps
        self._initialize_deployment_steps()
    
    def _initialize_deployment_steps(self):
        """Initialize deployment steps based on method."""
        base_steps = [
            DeploymentStep(
                name="validate_requirements",
                description="Validate system requirements and prerequisites"
            ),
            DeploymentStep(
                name="validate_configuration",
                description="Validate deployment configuration"
            ),
            DeploymentStep(
                name="install_dependencies",
                description="Install required dependencies and components"
            ),
            DeploymentStep(
                name="configure_service",
                description="Configure service for deployment"
            ),
            DeploymentStep(
                name="start_service",
                description="Start the deployed service"
            ),
            DeploymentStep(
                name="verify_deployment",
                description="Verify deployment is working correctly"
            ),
        ]
        
        self.progress.steps = base_steps
        self.progress.update_progress()
    
    def _update_progress(self):
        """Update progress and notify callback if provided."""
        self.progress.update_progress()
        if self.progress_callback:
            self.progress_callback(self.progress)
    
    async def _execute_step(self, step_name: str, step_func: Callable) -> bool:
        """
        Execute a deployment step with progress tracking.
        
        Args:
            step_name: Name of the step
            step_func: Function to execute
            
        Returns:
            True if step succeeded
        """
        # Find step
        step = None
        for s in self.progress.steps:
            if s.name == step_name:
                step = s
                break
        
        if not step:
            self.logger.error(f"Step not found: {step_name}")
            return False
        
        # Update step status
        step.status = DeploymentStatus.PREPARING
        step.start_time = datetime.now()
        self._update_progress()
        
        try:
            self.logger.info(f"Executing step: {step.description}")
            
            # Execute step function
            if asyncio.iscoroutinefunction(step_func):
                result = await step_func()
            else:
                result = step_func()
            
            # Process result
            if isinstance(result, ValidationResult):
                if result.valid:
                    step.status = DeploymentStatus.COMPLETED
                    step.warnings.extend(result.warnings)
                    self.logger.info(f"Step completed: {step_name}")
                else:
                    step.status = DeploymentStatus.FAILED
                    step.error_message = "; ".join(result.errors)
                    self.logger.error(f"Step failed: {step_name} - {step.error_message}")
                    return False
            else:
                step.status = DeploymentStatus.COMPLETED
                self.logger.info(f"Step completed: {step_name}")
            
        except Exception as e:
            step.status = DeploymentStatus.FAILED
            step.error_message = str(e)
            self.logger.error(f"Step failed with exception: {step_name} - {e}")
            return False
        
        finally:
            step.end_time = datetime.now()
            self._update_progress()
        
        return True
    
    async def deploy(self) -> DeploymentResult:
        """
        Execute complete deployment process.
        
        Returns:
            Deployment result with comprehensive information
        """
        self.logger.info(f"Starting deployment: {self.progress.deployment_id}")
        self.progress.overall_status = DeploymentStatus.VALIDATING
        self._update_progress()
        
        try:
            # Execute deployment steps
            steps_to_execute = [
                ("validate_requirements", self.deployment.validate_requirements),
                ("validate_configuration", self._validate_configuration),
                ("install_dependencies", self.deployment.install_dependencies),
                ("configure_service", lambda: self.deployment.configure_service(self.config)),
                ("start_service", self.deployment.start_service),
                ("verify_deployment", self.deployment.verify_deployment),
            ]
            
            for step_name, step_func in steps_to_execute:
                success = await self._execute_step(step_name, step_func)
                if not success:
                    self.progress.overall_status = DeploymentStatus.FAILED
                    self.progress.end_time = datetime.now()
                    self._update_progress()
                    
                    return DeploymentResult(
                        success=False,
                        deployment_id=self.progress.deployment_id,
                        deployment_method=self.config.deployment_method,
                        progress=self.progress
                    )
            
            # Deployment successful
            self.progress.overall_status = DeploymentStatus.COMPLETED
            self.progress.end_time = datetime.now()
            self._update_progress()
            
            # Gather service information
            service_info = await self._gather_service_info()
            endpoints = self._get_service_endpoints()
            
            self.logger.info(f"Deployment completed successfully: {self.progress.deployment_id}")
            
            return DeploymentResult(
                success=True,
                deployment_id=self.progress.deployment_id,
                deployment_method=self.config.deployment_method,
                progress=self.progress,
                service_info=service_info,
                endpoints=endpoints,
                configuration_path=self.config.config_path,
                rollback_available=True
            )
            
        except Exception as e:
            self.logger.error(f"Deployment failed with exception: {e}")
            self.progress.overall_status = DeploymentStatus.FAILED
            self.progress.end_time = datetime.now()
            self._update_progress()
            
            return DeploymentResult(
                success=False,
                deployment_id=self.progress.deployment_id,
                deployment_method=self.config.deployment_method,
                progress=self.progress
            )
    
    async def _validate_configuration(self) -> ValidationResult:
        """Validate deployment configuration."""
        validator = ConfigurationValidator(self.config)
        return await validator.validate_full_configuration()
    
    async def _gather_service_info(self) -> Dict[str, Any]:
        """Gather service information after deployment."""
        service_info = {
            "service_name": self.config.service_config.service_name,
            "service_port": self.config.service_config.service_port,
            "deployment_method": self.config.deployment_method.value,
            "installation_path": self.config.installation_path,
            "config_path": self.config.config_path,
            "log_path": self.config.log_path,
        }
        
        try:
            # Try to get service status
            import requests
            health_url = f"http://localhost:{self.config.service_config.service_port}/health"
            response = requests.get(health_url, timeout=5)
            
            if response.status_code == 200:
                service_info["health_status"] = "healthy"
                service_info["health_data"] = response.json()
            else:
                service_info["health_status"] = f"unhealthy ({response.status_code})"
                
        except Exception as e:
            service_info["health_status"] = f"unknown ({e})"
        
        return service_info
    
    def _get_service_endpoints(self) -> Dict[str, str]:
        """Get service endpoint URLs."""
        base_url = f"http://localhost:{self.config.service_config.service_port}"
        
        return {
            "api_base": base_url,
            "health": f"{base_url}/health",
            "health_detailed": f"{base_url}/health/detailed",
            "docs": f"{base_url}/docs",
            "openapi": f"{base_url}/openapi.json",
            "tokenize": f"{base_url}/v1/tokenize",
        }
    
    async def rollback(self) -> ValidationResult:
        """
        Rollback deployment.
        
        Returns:
            Validation result indicating rollback success
        """
        self.logger.info(f"Rolling back deployment: {self.progress.deployment_id}")
        
        try:
            # Stop service
            stop_result = await self.deployment.stop_service()
            if not stop_result.valid:
                self.logger.warning(f"Service stop during rollback had issues: {stop_result.errors}")
            
            # Cleanup deployment
            cleanup_result = await self.deployment.cleanup()
            if not cleanup_result.valid:
                self.logger.warning(f"Cleanup during rollback had issues: {cleanup_result.errors}")
            
            self.progress.overall_status = DeploymentStatus.ROLLED_BACK
            self._update_progress()
            
            self.logger.info("Deployment rollback completed")
            
            return ValidationResult(
                valid=True,
                warnings=["Deployment rolled back successfully"]
            )
            
        except Exception as e:
            self.logger.error(f"Rollback failed: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Rollback failed: {e}"]
            )
    
    async def get_deployment_status(self) -> DeploymentProgress:
        """
        Get current deployment status.
        
        Returns:
            Current deployment progress
        """
        return self.progress
    
    async def stop_deployment(self) -> ValidationResult:
        """
        Stop the deployed service.
        
        Returns:
            Validation result indicating stop success
        """
        self.logger.info(f"Stopping deployment: {self.progress.deployment_id}")
        
        try:
            result = await self.deployment.stop_service()
            
            if result.valid:
                self.logger.info("Deployment stopped successfully")
            else:
                self.logger.warning(f"Deployment stop had issues: {result.errors}")
            
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to stop deployment: {e}")
            return ValidationResult(
                valid=False,
                errors=[f"Failed to stop deployment: {e}"]
            )