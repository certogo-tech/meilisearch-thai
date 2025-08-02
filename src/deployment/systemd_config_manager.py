"""
Systemd-specific configuration management for Thai Tokenizer deployment.

This module provides specialized configuration management for systemd deployments,
including environment file management, service configuration updates, and
systemd-specific optimizations.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
import logging

from pydantic import BaseModel, Field

try:
    from src.deployment.config import OnPremiseConfig, ValidationResult
    from src.utils.logging import get_structured_logger
except ImportError:
    from deployment.config import OnPremiseConfig, ValidationResult
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class SystemdConfigurationManager:
    """Manages systemd-specific configuration files and settings."""
    
    def __init__(self, config: OnPremiseConfig):
        """Initialize with deployment configuration."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.SystemdConfigurationManager")
    
    def create_environment_file(self, output_path: str, mask_secrets: bool = False) -> ValidationResult:
        """
        Create systemd environment file with proper formatting and security.
        
        Args:
            output_path: Path where the environment file should be written
            mask_secrets: Whether to mask secret values in the file
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            env_vars = self.config.get_environment_dict()
            
            # Create environment file content with systemd-specific formatting
            env_lines = [
                "# Thai Tokenizer Service Environment Configuration",
                "# Generated for systemd deployment",
                f"# Service: {self.config.service_config.service_name}",
                f"# Generated: {result.timestamp.isoformat()}",
                "",
                "# WARNING: This file contains sensitive information.",
                "# Ensure proper file permissions (0640) and ownership.",
                "",
            ]
            
            # Group variables by category for better organization
            categories = {
                "Service Configuration": [
                    "THAI_TOKENIZER_SERVICE_NAME",
                    "THAI_TOKENIZER_SERVICE_PORT",
                    "THAI_TOKENIZER_SERVICE_HOST",
                    "THAI_TOKENIZER_WORKER_PROCESSES"
                ],
                "Meilisearch Configuration": [
                    "THAI_TOKENIZER_MEILISEARCH_HOST",
                    "THAI_TOKENIZER_MEILISEARCH_API_KEY",
                    "THAI_TOKENIZER_MEILISEARCH_TIMEOUT",
                    "THAI_TOKENIZER_MEILISEARCH_MAX_RETRIES",
                    "THAI_TOKENIZER_MEILISEARCH_SSL_VERIFY"
                ],
                "Security Configuration": [
                    "THAI_TOKENIZER_ALLOWED_HOSTS",
                    "THAI_TOKENIZER_CORS_ORIGINS",
                    "THAI_TOKENIZER_API_KEY_REQUIRED",
                    "THAI_TOKENIZER_API_KEY"
                ],
                "Resource Configuration": [
                    "THAI_TOKENIZER_MEMORY_LIMIT_MB",
                    "THAI_TOKENIZER_CPU_LIMIT_CORES",
                    "THAI_TOKENIZER_MAX_CONCURRENT_REQUESTS",
                    "THAI_TOKENIZER_REQUEST_TIMEOUT"
                ],
                "Monitoring Configuration": [
                    "THAI_TOKENIZER_LOG_LEVEL",
                    "THAI_TOKENIZER_ENABLE_METRICS",
                    "THAI_TOKENIZER_METRICS_PORT"
                ],
                "Path Configuration": [
                    "THAI_TOKENIZER_INSTALLATION_PATH",
                    "THAI_TOKENIZER_DATA_PATH",
                    "THAI_TOKENIZER_LOG_PATH",
                    "THAI_TOKENIZER_CONFIG_PATH"
                ]
            }
            
            # Add categorized environment variables
            for category, var_names in categories.items():
                env_lines.append(f"# {category}")
                
                for var_name in var_names:
                    if var_name in env_vars:
                        value = env_vars[var_name]
                        
                        # Mask sensitive values if requested
                        if mask_secrets and any(sensitive in var_name.lower() for sensitive in ["api_key", "password", "secret"]):
                            display_value = "***MASKED***"
                        else:
                            display_value = value
                        
                        # Escape special characters for systemd
                        escaped_value = display_value.replace('"', '\\"').replace('$', '\\$')
                        env_lines.append(f'{var_name}="{escaped_value}"')
                
                env_lines.append("")
            
            # Add any remaining environment variables
            remaining_vars = set(env_vars.keys()) - set(var for vars in categories.values() for var in vars)
            if remaining_vars:
                env_lines.append("# Additional Configuration")
                for var_name in sorted(remaining_vars):
                    value = env_vars[var_name]
                    
                    if mask_secrets and any(sensitive in var_name.lower() for sensitive in ["api_key", "password", "secret"]):
                        display_value = "***MASKED***"
                    else:
                        display_value = value
                    
                    escaped_value = display_value.replace('"', '\\"').replace('$', '\\$')
                    env_lines.append(f'{var_name}="{escaped_value}"')
                env_lines.append("")
            
            # Write environment file
            env_content = "\n".join(env_lines)
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(env_content, encoding="utf-8")
            
            # Set secure permissions (readable by owner and group only)
            output_file.chmod(0o640)
            
            # Set ownership to service user if possible
            try:
                shutil.chown(
                    output_file,
                    self.config.service_config.service_user,
                    self.config.service_config.service_group
                )
                result.warnings.append(f"Set ownership to {self.config.service_config.service_user}:{self.config.service_config.service_group}")
            except (KeyError, PermissionError):
                result.warnings.append("Could not set ownership for environment file")
            
            self.logger.info(f"Created environment file: {output_path}")
            result.warnings.append(f"Created environment file: {output_path}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to create environment file: {e}")
            self.logger.error(f"Environment file creation failed: {e}")
        
        return result
    
    def update_environment_variable(self, env_file_path: str, variable_name: str, new_value: str) -> ValidationResult:
        """
        Update a specific environment variable in the environment file.
        
        Args:
            env_file_path: Path to the environment file
            variable_name: Name of the variable to update
            new_value: New value for the variable
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            env_file = Path(env_file_path)
            if not env_file.exists():
                result.valid = False
                result.errors.append(f"Environment file not found: {env_file_path}")
                return result
            
            # Read current content
            lines = env_file.read_text(encoding="utf-8").split('\n')
            
            # Find and update the variable
            updated = False
            for i, line in enumerate(lines):
                if line.strip().startswith(f"{variable_name}="):
                    # Escape special characters
                    escaped_value = new_value.replace('"', '\\"').replace('$', '\\$')
                    lines[i] = f'{variable_name}="{escaped_value}"'
                    updated = True
                    break
            
            if not updated:
                # Add the variable at the end
                escaped_value = new_value.replace('"', '\\"').replace('$', '\\$')
                lines.append(f'{variable_name}="{escaped_value}"')
                result.warnings.append(f"Added new environment variable: {variable_name}")
            else:
                result.warnings.append(f"Updated environment variable: {variable_name}")
            
            # Write updated content
            updated_content = '\n'.join(lines)
            env_file.write_text(updated_content, encoding="utf-8")
            
            self.logger.info(f"Updated environment variable {variable_name} in {env_file_path}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to update environment variable: {e}")
            self.logger.error(f"Environment variable update failed: {e}")
        
        return result
    
    def create_systemd_override_directory(self, service_name: str) -> ValidationResult:
        """
        Create systemd override directory for service customization.
        
        Args:
            service_name: Name of the systemd service
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            override_dir = Path(f"/etc/systemd/system/{service_name}.service.d")
            override_dir.mkdir(parents=True, exist_ok=True)
            override_dir.chmod(0o755)
            
            self.logger.info(f"Created systemd override directory: {override_dir}")
            result.warnings.append(f"Created override directory: {override_dir}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to create override directory: {e}")
            self.logger.error(f"Override directory creation failed: {e}")
        
        return result
    
    def create_resource_limits_override(self, service_name: str) -> ValidationResult:
        """
        Create systemd override file for resource limits.
        
        Args:
            service_name: Name of the systemd service
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            # Create override directory first
            override_result = self.create_systemd_override_directory(service_name)
            if not override_result.valid:
                return override_result
            
            # Create resource limits override
            override_content = f"""[Service]
# Resource limits for Thai Tokenizer service
MemoryLimit={self.config.resource_config.memory_limit_mb}M
CPUQuota={int(self.config.resource_config.cpu_limit_cores * 100)}%

# Process limits
LimitNOFILE={max(1024, self.config.resource_config.max_concurrent_requests * 2)}
LimitNPROC={max(10, self.config.service_config.worker_processes * 2)}
TasksMax={max(50, self.config.service_config.worker_processes * 10)}

# Additional security settings
PrivateDevices=true
ProtectClock=true
ProtectHostname=true
RemoveIPC=true
"""
            
            override_file = Path(f"/etc/systemd/system/{service_name}.service.d/resource-limits.conf")
            override_file.write_text(override_content, encoding="utf-8")
            override_file.chmod(0o644)
            
            self.logger.info(f"Created resource limits override: {override_file}")
            result.warnings.append(f"Created resource limits override: {override_file}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to create resource limits override: {e}")
            self.logger.error(f"Resource limits override creation failed: {e}")
        
        return result
    
    def create_logging_override(self, service_name: str) -> ValidationResult:
        """
        Create systemd override file for logging configuration.
        
        Args:
            service_name: Name of the systemd service
            
        Returns:
            ValidationResult indicating success or failure
        """
        result = ValidationResult(valid=True)
        
        try:
            # Create override directory first
            override_result = self.create_systemd_override_directory(service_name)
            if not override_result.valid:
                return override_result
            
            # Create logging override
            override_content = f"""[Service]
# Logging configuration for Thai Tokenizer service
StandardOutput=journal
StandardError=journal
SyslogIdentifier={service_name}

# Journal settings
LogLevelMax={self._get_systemd_log_level(self.config.monitoring_config.log_level)}
LogExtraFields=SERVICE_NAME={service_name}
"""
            
            # Add file logging if configured
            if self.config.monitoring_config.log_file_path:
                log_dir = Path(self.config.monitoring_config.log_file_path).parent
                override_content += f"""
# File logging
StandardOutput=append:{self.config.monitoring_config.log_file_path}
StandardError=append:{log_dir}/error.log
"""
            
            override_file = Path(f"/etc/systemd/system/{service_name}.service.d/logging.conf")
            override_file.write_text(override_content, encoding="utf-8")
            override_file.chmod(0o644)
            
            self.logger.info(f"Created logging override: {override_file}")
            result.warnings.append(f"Created logging override: {override_file}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Failed to create logging override: {e}")
            self.logger.error(f"Logging override creation failed: {e}")
        
        return result
    
    def _get_systemd_log_level(self, log_level: str) -> str:
        """Convert application log level to systemd log level."""
        level_mapping = {
            "DEBUG": "debug",
            "INFO": "info",
            "WARNING": "warning",
            "ERROR": "err",
            "CRITICAL": "crit"
        }
        return level_mapping.get(log_level.upper(), "info")
    
    def validate_systemd_configuration(self, service_name: str) -> ValidationResult:
        """
        Validate systemd service configuration.
        
        Args:
            service_name: Name of the systemd service
            
        Returns:
            ValidationResult with validation details
        """
        result = ValidationResult(valid=True)
        
        try:
            # Check if service file exists
            service_file = Path(f"/etc/systemd/system/{service_name}.service")
            if not service_file.exists():
                result.valid = False
                result.errors.append(f"Service file not found: {service_file}")
                return result
            
            # Validate service file syntax using systemd-analyze
            try:
                analyze_result = subprocess.run([
                    "systemd-analyze", "verify", str(service_file)
                ], capture_output=True, text=True)
                
                if analyze_result.returncode == 0:
                    result.warnings.append("Service file syntax is valid")
                else:
                    result.errors.append(f"Service file syntax errors: {analyze_result.stderr}")
                    result.valid = False
            
            except FileNotFoundError:
                result.warnings.append("systemd-analyze not available, skipping syntax validation")
            
            # Check environment file
            env_file = Path(f"{self.config.config_path}/environment")
            if env_file.exists():
                result.warnings.append(f"Environment file exists: {env_file}")
                
                # Check file permissions
                file_stat = env_file.stat()
                file_mode = oct(file_stat.st_mode)[-3:]
                if file_mode != "640":
                    result.warnings.append(f"Environment file permissions should be 640, found {file_mode}")
            else:
                result.errors.append(f"Environment file not found: {env_file}")
                result.valid = False
            
            # Check required directories
            required_dirs = [
                self.config.installation_path,
                self.config.data_path,
                self.config.log_path,
                self.config.config_path
            ]
            
            for dir_path in required_dirs:
                path_obj = Path(dir_path)
                if not path_obj.exists():
                    result.errors.append(f"Required directory not found: {dir_path}")
                    result.valid = False
                elif not path_obj.is_dir():
                    result.errors.append(f"Path is not a directory: {dir_path}")
                    result.valid = False
                else:
                    result.warnings.append(f"Directory exists: {dir_path}")
            
            # Check service user and group
            try:
                import pwd
                import grp
                
                pwd.getpwnam(self.config.service_config.service_user)
                result.warnings.append(f"Service user exists: {self.config.service_config.service_user}")
                
                grp.getgrnam(self.config.service_config.service_group)
                result.warnings.append(f"Service group exists: {self.config.service_config.service_group}")
                
            except KeyError as e:
                result.errors.append(f"Service user/group not found: {e}")
                result.valid = False
            
            # Check systemd daemon status
            try:
                daemon_result = subprocess.run([
                    "systemctl", "is-system-running"
                ], capture_output=True, text=True)
                
                system_state = daemon_result.stdout.strip()
                if system_state in ["running", "degraded"]:
                    result.warnings.append(f"Systemd is running (state: {system_state})")
                else:
                    result.warnings.append(f"Systemd state: {system_state}")
                
            except Exception as e:
                result.warnings.append(f"Could not check systemd status: {e}")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Configuration validation failed: {e}")
            self.logger.error(f"Configuration validation failed: {e}")
        
        return result
    
    def get_service_configuration_summary(self, service_name: str) -> Dict[str, Any]:
        """
        Get a comprehensive summary of the service configuration.
        
        Args:
            service_name: Name of the systemd service
            
        Returns:
            Dictionary with configuration summary
        """
        summary = {
            "service_name": service_name,
            "configuration": {},
            "files": {},
            "validation": {},
            "timestamp": result.timestamp.isoformat() if 'result' in locals() else None
        }
        
        try:
            # Get configuration from the OnPremiseConfig
            summary["configuration"] = {
                "deployment_method": self.config.deployment_method.value,
                "service_port": self.config.service_config.service_port,
                "service_user": self.config.service_config.service_user,
                "service_group": self.config.service_config.service_group,
                "worker_processes": self.config.service_config.worker_processes,
                "memory_limit_mb": self.config.resource_config.memory_limit_mb,
                "cpu_limit_cores": self.config.resource_config.cpu_limit_cores,
                "installation_path": self.config.installation_path,
                "data_path": self.config.data_path,
                "log_path": self.config.log_path,
                "config_path": self.config.config_path
            }
            
            # Check file existence
            files_to_check = {
                "service_file": f"/etc/systemd/system/{service_name}.service",
                "environment_file": f"{self.config.config_path}/environment",
                "logrotate_config": f"/etc/logrotate.d/{service_name}",
                "override_directory": f"/etc/systemd/system/{service_name}.service.d"
            }
            
            for file_type, file_path in files_to_check.items():
                path_obj = Path(file_path)
                summary["files"][file_type] = {
                    "path": file_path,
                    "exists": path_obj.exists(),
                    "is_directory": path_obj.is_dir() if path_obj.exists() else False,
                    "permissions": oct(path_obj.stat().st_mode)[-3:] if path_obj.exists() else None
                }
            
            # Run validation
            validation_result = self.validate_systemd_configuration(service_name)
            summary["validation"] = {
                "valid": validation_result.valid,
                "errors": validation_result.errors,
                "warnings": validation_result.warnings
            }
            
        except Exception as e:
            summary["error"] = str(e)
        
        return summary