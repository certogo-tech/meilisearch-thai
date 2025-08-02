"""
Systemd service deployment manager for Thai Tokenizer.

This module provides comprehensive systemd service management including
service file generation, user/group management, and system integration.
"""

import os
import pwd
import grp
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

from pydantic import BaseModel, Field

try:
    from src.deployment.config import OnPremiseConfig, DeploymentMethod, ValidationResult
    from src.utils.logging import get_structured_logger
except ImportError:
    from deployment.config import OnPremiseConfig, DeploymentMethod, ValidationResult
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class SystemdServiceConfig(BaseModel):
    """Configuration for systemd service generation."""
    
    service_name: str = Field(description="Name of the systemd service")
    service_file_path: str = Field(description="Path to the systemd service file")
    environment_file_path: str = Field(description="Path to the environment file")
    user_name: str = Field(description="System user for the service")
    group_name: str = Field(description="System group for the service")
    installation_path: str = Field(description="Installation directory")
    data_path: str = Field(description="Data directory")
    log_path: str = Field(description="Log directory")
    config_path: str = Field(description="Configuration directory")


class SystemdUserManager:
    """Manages system users and groups for Thai Tokenizer service."""
    
    def __init__(self, config: OnPremiseConfig):
        """Initialize with deployment configuration."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.SystemdUserManager")
    
    def user_exists(self, username: str) -> bool:
        """Check if a system user exists."""
        try:
            pwd.getpwnam(username)
            return True
        except KeyError:
            return False
    
    def group_exists(self, groupname: str) -> bool:
        """Check if a system group exists."""
        try:
            grp.getgrnam(groupname)
            return True
        except KeyError:
            return False
    
    def create_user(self, username: str, groupname: str, home_dir: str) -> ValidationResult:
        """
        Create system user for Thai Tokenizer service.
        
        Args:
            username: Name of the user to create
            groupname: Name of the group to create
            home_dir: Home directory for the user
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            # Create group first if it doesn't exist
            if not self.group_exists(groupname):
                self.logger.info(f"Creating system group: {groupname}")
                subprocess.run([
                    "groupadd",
                    "--system",
                    groupname
                ], check=True, capture_output=True, text=True)
                result.warnings.append(f"Created system group: {groupname}")
            else:
                result.warnings.append(f"System group already exists: {groupname}")
            
            # Create user if it doesn't exist
            if not self.user_exists(username):
                self.logger.info(f"Creating system user: {username}")
                subprocess.run([
                    "useradd",
                    "--system",
                    "--gid", groupname,
                    "--home-dir", home_dir,
                    "--create-home",
                    "--shell", "/bin/false",
                    "--comment", "Thai Tokenizer Service User",
                    username
                ], check=True, capture_output=True, text=True)
                result.warnings.append(f"Created system user: {username}")
            else:
                result.warnings.append(f"System user already exists: {username}")
            
            # Ensure home directory has correct permissions
            home_path = Path(home_dir)
            if home_path.exists():
                shutil.chown(home_path, username, groupname)
                home_path.chmod(0o755)
                self.logger.info(f"Set ownership and permissions for {home_dir}")
        
        except subprocess.CalledProcessError as e:
            result.valid = False
            result.errors.append(f"Failed to create user/group: {e.stderr}")
            self.logger.error(f"User creation failed: {e.stderr}")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Unexpected error creating user: {e}")
            self.logger.error(f"Unexpected user creation error: {e}")
        
        return result
    
    def setup_directories(self, username: str, groupname: str) -> ValidationResult:
        """
        Set up required directories with proper ownership and permissions.
        
        Args:
            username: System user name
            groupname: System group name
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        directories = [
            (self.config.installation_path, 0o755, "Installation directory"),
            (self.config.data_path, 0o755, "Data directory"),
            (self.config.log_path, 0o755, "Log directory"),
            (self.config.config_path, 0o750, "Configuration directory"),
        ]
        
        for dir_path, permissions, description in directories:
            try:
                path_obj = Path(dir_path)
                path_obj.mkdir(parents=True, exist_ok=True)
                
                # Set ownership
                shutil.chown(path_obj, username, groupname)
                
                # Set permissions
                path_obj.chmod(permissions)
                
                self.logger.info(f"Created {description}: {dir_path}")
                result.warnings.append(f"Created {description}: {dir_path}")
                
            except PermissionError:
                result.valid = False
                result.errors.append(f"Permission denied creating {description}: {dir_path}")
                self.logger.error(f"Permission denied creating {dir_path}")
            except Exception as e:
                result.valid = False
                result.errors.append(f"Failed to create {description}: {e}")
                self.logger.error(f"Failed to create {dir_path}: {e}")
        
        return result


class SystemdServiceGenerator:
    """Generates systemd service files from templates."""
    
    def __init__(self, config: OnPremiseConfig):
        """Initialize with deployment configuration."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.SystemdServiceGenerator")
    
    def generate_service_file(self, template_path: str, output_path: str) -> ValidationResult:
        """
        Generate systemd service file from template.
        
        Args:
            template_path: Path to the service file template
            output_path: Path where the service file should be written
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            # Read template
            template_file = Path(template_path)
            if not template_file.exists():
                result.valid = False
                result.errors.append(f"Template file not found: {template_path}")
                return result
            
            template_content = template_file.read_text(encoding="utf-8")
            
            # Prepare substitution variables
            substitutions = self._get_template_substitutions()
            
            # Perform substitutions
            service_content = template_content
            for key, value in substitutions.items():
                placeholder = f"{{{{{key}}}}}"
                service_content = service_content.replace(placeholder, str(value))
            
            # Write service file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(service_content, encoding="utf-8")
            
            # Set appropriate permissions for systemd service file
            output_file.chmod(0o644)
            
            self.logger.info(f"Generated systemd service file: {output_path}")
            result.warnings.append(f"Generated service file: {output_path}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to generate service file: {e}")
            self.logger.error(f"Service file generation failed: {e}")
        
        return result
    
    def generate_environment_file(self, output_path: str) -> ValidationResult:
        """
        Generate environment file for systemd service.
        
        Args:
            output_path: Path where the environment file should be written
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            env_vars = self.config.get_environment_dict()
            
            # Create environment file content
            env_lines = [
                "# Thai Tokenizer Service Environment Configuration",
                "# Generated for systemd deployment",
                "",
            ]
            
            for key, value in sorted(env_vars.items()):
                # Escape special characters in values
                escaped_value = value.replace('"', '\\"').replace('$', '\\$')
                env_lines.append(f'{key}="{escaped_value}"')
            
            env_content = "\n".join(env_lines)
            
            # Write environment file
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(env_content, encoding="utf-8")
            
            # Set secure permissions for environment file (contains secrets)
            output_file.chmod(0o640)
            
            # Set ownership to service user if possible
            try:
                shutil.chown(
                    output_file,
                    self.config.service_config.service_user,
                    self.config.service_config.service_group
                )
            except (KeyError, PermissionError):
                result.warnings.append("Could not set ownership for environment file")
            
            self.logger.info(f"Generated environment file: {output_path}")
            result.warnings.append(f"Generated environment file: {output_path}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to generate environment file: {e}")
            self.logger.error(f"Environment file generation failed: {e}")
        
        return result
    
    def _get_template_substitutions(self) -> Dict[str, str]:
        """Get template substitution variables."""
        # Calculate resource limits
        cpu_quota = int(self.config.resource_config.cpu_limit_cores * 100)
        max_tasks = max(50, self.config.service_config.worker_processes * 10)
        max_open_files = max(1024, self.config.resource_config.max_concurrent_requests * 2)
        max_processes = max(10, self.config.service_config.worker_processes * 2)
        
        # Determine allowed networks
        allowed_networks = ["127.0.0.1/32", "::1/128"]  # localhost by default
        if self.config.service_config.service_host != "127.0.0.1":
            allowed_networks.append("0.0.0.0/0")  # Allow all if binding to all interfaces
        
        return {
            "SERVICE_NAME": self.config.service_config.service_name,
            "SERVICE_USER": self.config.service_config.service_user,
            "SERVICE_GROUP": self.config.service_config.service_group,
            "SERVICE_HOST": self.config.service_config.service_host,
            "SERVICE_PORT": str(self.config.service_config.service_port),
            "WORKER_PROCESSES": str(self.config.service_config.worker_processes),
            "INSTALLATION_PATH": self.config.installation_path,
            "DATA_PATH": self.config.data_path,
            "LOG_PATH": self.config.log_path,
            "CONFIG_PATH": self.config.config_path,
            "MEMORY_LIMIT_MB": str(self.config.resource_config.memory_limit_mb),
            "CPU_QUOTA": str(cpu_quota),
            "MAX_TASKS": str(max_tasks),
            "MAX_OPEN_FILES": str(max_open_files),
            "MAX_PROCESSES": str(max_processes),
            "LOG_LEVEL": self.config.monitoring_config.log_level.lower(),
            "ALLOWED_NETWORKS": " ".join(allowed_networks),
        }


class SystemdServiceManager:
    """Manages systemd service lifecycle operations."""
    
    def __init__(self, service_name: str):
        """Initialize with service name."""
        self.service_name = service_name
        self.logger = get_structured_logger(f"{__name__}.SystemdServiceManager")
    
    def install_service(self, service_file_path: str) -> ValidationResult:
        """
        Install systemd service file.
        
        Args:
            service_file_path: Path to the service file to install
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            service_file = Path(service_file_path)
            if not service_file.exists():
                result.valid = False
                result.errors.append(f"Service file not found: {service_file_path}")
                return result
            
            # Copy service file to systemd directory
            systemd_service_path = f"/etc/systemd/system/{self.service_name}.service"
            shutil.copy2(service_file_path, systemd_service_path)
            
            # Set correct permissions
            Path(systemd_service_path).chmod(0o644)
            
            # Reload systemd daemon
            subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)
            
            self.logger.info(f"Installed systemd service: {self.service_name}")
            result.warnings.append(f"Installed service: {systemd_service_path}")
            
        except subprocess.CalledProcessError as e:
            result.valid = False
            result.errors.append(f"Failed to install service: {e.stderr}")
            self.logger.error(f"Service installation failed: {e.stderr}")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Unexpected error installing service: {e}")
            self.logger.error(f"Unexpected service installation error: {e}")
        
        return result
    
    def enable_service(self) -> ValidationResult:
        """
        Enable systemd service for automatic startup.
        
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            subprocess.run(
                ["systemctl", "enable", self.service_name],
                check=True,
                capture_output=True,
                text=True
            )
            
            self.logger.info(f"Enabled systemd service: {self.service_name}")
            result.warnings.append(f"Enabled service for automatic startup: {self.service_name}")
            
        except subprocess.CalledProcessError as e:
            result.valid = False
            result.errors.append(f"Failed to enable service: {e.stderr}")
            self.logger.error(f"Service enable failed: {e.stderr}")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Unexpected error enabling service: {e}")
            self.logger.error(f"Unexpected service enable error: {e}")
        
        return result
    
    def start_service(self) -> ValidationResult:
        """
        Start systemd service.
        
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            subprocess.run(
                ["systemctl", "start", self.service_name],
                check=True,
                capture_output=True,
                text=True
            )
            
            self.logger.info(f"Started systemd service: {self.service_name}")
            result.warnings.append(f"Started service: {self.service_name}")
            
        except subprocess.CalledProcessError as e:
            result.valid = False
            result.errors.append(f"Failed to start service: {e.stderr}")
            self.logger.error(f"Service start failed: {e.stderr}")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Unexpected error starting service: {e}")
            self.logger.error(f"Unexpected service start error: {e}")
        
        return result
    
    def stop_service(self) -> ValidationResult:
        """
        Stop systemd service.
        
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            subprocess.run(
                ["systemctl", "stop", self.service_name],
                check=True,
                capture_output=True,
                text=True
            )
            
            self.logger.info(f"Stopped systemd service: {self.service_name}")
            result.warnings.append(f"Stopped service: {self.service_name}")
            
        except subprocess.CalledProcessError as e:
            result.valid = False
            result.errors.append(f"Failed to stop service: {e.stderr}")
            self.logger.error(f"Service stop failed: {e.stderr}")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Unexpected error stopping service: {e}")
            self.logger.error(f"Unexpected service stop error: {e}")
        
        return result
    
    def restart_service(self) -> ValidationResult:
        """
        Restart systemd service.
        
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            subprocess.run(
                ["systemctl", "restart", self.service_name],
                check=True,
                capture_output=True,
                text=True
            )
            
            self.logger.info(f"Restarted systemd service: {self.service_name}")
            result.warnings.append(f"Restarted service: {self.service_name}")
            
        except subprocess.CalledProcessError as e:
            result.valid = False
            result.errors.append(f"Failed to restart service: {e.stderr}")
            self.logger.error(f"Service restart failed: {e.stderr}")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Unexpected error restarting service: {e}")
            self.logger.error(f"Unexpected service restart error: {e}")
        
        return result
    
    def get_service_status(self) -> Tuple[bool, str]:
        """
        Get systemd service status.
        
        Returns:
            Tuple of (is_active, status_output)
        """
        try:
            result = subprocess.run(
                ["systemctl", "is-active", self.service_name],
                capture_output=True,
                text=True
            )
            
            is_active = result.returncode == 0
            status = result.stdout.strip()
            
            # Get detailed status if needed
            if not is_active:
                detailed_result = subprocess.run(
                    ["systemctl", "status", self.service_name, "--no-pager", "-l"],
                    capture_output=True,
                    text=True
                )
                status = detailed_result.stdout
            
            return is_active, status
            
        except Exception as e:
            return False, f"Error getting service status: {e}"
    
    def get_service_logs(self, lines: int = 50) -> str:
        """
        Get systemd service logs.
        
        Args:
            lines: Number of log lines to retrieve
            
        Returns:
            Service log output
        """
        try:
            result = subprocess.run([
                "journalctl",
                "-u", self.service_name,
                "-n", str(lines),
                "--no-pager"
            ], capture_output=True, text=True)
            
            return result.stdout
            
        except Exception as e:
            return f"Error getting service logs: {e}"


class SystemdDeploymentValidator:
    """Validates systemd deployment requirements and configuration."""
    
    def __init__(self, config: OnPremiseConfig):
        """Initialize with deployment configuration."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.SystemdDeploymentValidator")
    
    def validate_system_requirements(self) -> ValidationResult:
        """
        Validate system requirements for systemd deployment.
        
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(valid=True)
        
        # Check if systemd is available
        try:
            subprocess.run(["systemctl", "--version"], check=True, capture_output=True)
            result.warnings.append("systemd is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            result.valid = False
            result.errors.append("systemd is not available on this system")
        
        # Check if running as root or with sudo
        if os.geteuid() != 0:
            result.valid = False
            result.errors.append("systemd deployment requires root privileges")
        
        # Check Python version
        try:
            import sys
            python_version = sys.version_info
            if python_version < (3, 12):
                result.valid = False
                result.errors.append(f"Python 3.12+ required, found {python_version.major}.{python_version.minor}")
            else:
                result.warnings.append(f"Python {python_version.major}.{python_version.minor} is compatible")
        except Exception as e:
            result.errors.append(f"Could not check Python version: {e}")
        
        # Check if uv is available
        try:
            subprocess.run(["uv", "--version"], check=True, capture_output=True)
            result.warnings.append("uv package manager is available")
        except (subprocess.CalledProcessError, FileNotFoundError):
            result.valid = False
            result.errors.append("uv package manager is required but not found")
        
        # Check disk space
        try:
            import shutil
            total, used, free = shutil.disk_usage(self.config.installation_path)
            free_gb = free // (1024**3)
            if free_gb < 1:
                result.valid = False
                result.errors.append(f"Insufficient disk space: {free_gb}GB free, need at least 1GB")
            else:
                result.warnings.append(f"Disk space available: {free_gb}GB")
        except Exception as e:
            result.warnings.append(f"Could not check disk space: {e}")
        
        # Check port availability
        import socket
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind((self.config.service_config.service_host, self.config.service_config.service_port))
            result.warnings.append(f"Port {self.config.service_config.service_port} is available")
        except OSError:
            result.valid = False
            result.errors.append(f"Port {self.config.service_config.service_port} is already in use")
        
        return result
    
    def validate_service_dependencies(self) -> ValidationResult:
        """
        Validate service dependencies and startup order.
        
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(valid=True)
        
        # Check network availability
        try:
            subprocess.run(["systemctl", "is-active", "network.target"], check=True, capture_output=True)
            result.warnings.append("network.target is active")
        except subprocess.CalledProcessError:
            result.warnings.append("network.target may not be active")
        
        # Check if there are conflicting services
        conflicting_services = [
            "apache2",
            "nginx",
            "httpd"
        ]
        
        for service in conflicting_services:
            try:
                result_check = subprocess.run(
                    ["systemctl", "is-active", service],
                    capture_output=True,
                    text=True
                )
                if result_check.returncode == 0:
                    result.warnings.append(f"Web server {service} is running, may cause port conflicts")
            except Exception:
                pass  # Service doesn't exist, which is fine
        
        return result