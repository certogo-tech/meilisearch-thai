#!/usr/bin/env python3
"""
Unified Configuration Management for Thai Tokenizer Deployment.

This module provides unified configuration management across all deployment
methods, with validation, transformation, and environment-specific handling.
"""

import json
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Type
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field
import hashlib

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from deployment.config import (
    OnPremiseConfig, DeploymentMethod, MeilisearchConfig, ServiceConfig,
    SecurityConfig, ResourceConfig, MonitoringConfig, ValidationResult
)
from deployment.error_handling import ConfigurationError, handle_deployment_error
from utils.logging import get_structured_logger


class ConfigurationSource(str, Enum):
    """Configuration source types."""
    FILE = "file"
    ENVIRONMENT = "environment"
    CLI_ARGS = "cli_args"
    DEFAULTS = "defaults"
    TEMPLATE = "template"


class ConfigurationFormat(str, Enum):
    """Configuration file formats."""
    JSON = "json"
    YAML = "yaml"
    TOML = "toml"
    ENV = "env"


@dataclass
class ConfigurationLayer:
    """Configuration layer with source tracking."""
    source: ConfigurationSource
    priority: int
    data: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ConfigurationValidationRule:
    """Configuration validation rule."""
    field_path: str
    rule_type: str  # required, type, range, choices, pattern, custom
    parameters: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    severity: str = "error"  # error, warning, info


class UnifiedConfigurationManager:
    """Unified configuration management system."""
    
    def __init__(self, base_config: Optional[OnPremiseConfig] = None):
        self.logger = get_structured_logger(__name__)
        self.layers: List[ConfigurationLayer] = []
        self.validation_rules: List[ConfigurationValidationRule] = []
        self.base_config = base_config
        self.merged_config: Optional[OnPremiseConfig] = None
        self.config_hash: Optional[str] = None
        
        # Initialize validation rules
        self._initialize_validation_rules()
        
        # Load default configuration layer
        self._load_default_layer()
    
    def _initialize_validation_rules(self):
        """Initialize configuration validation rules."""
        
        # Required fields
        required_fields = [
            "deployment_method",
            "meilisearch_config.host",
            "service_config.service_name",
            "service_config.service_port"
        ]
        
        for field in required_fields:
            self.validation_rules.append(
                ConfigurationValidationRule(
                    field_path=field,
                    rule_type="required",
                    error_message=f"Required field '{field}' is missing"
                )
            )
        
        # Type validation
        type_rules = [
            ("deployment_method", "str"),
            ("service_config.service_port", "int"),
            ("service_config.worker_processes", "int"),
            ("resource_config.memory_limit_mb", "int"),
            ("resource_config.cpu_limit_cores", "float"),
            ("resource_config.max_concurrent_requests", "int"),
            ("security_config.api_key_required", "bool"),
            ("security_config.enable_https", "bool"),
            ("monitoring_config.enable_health_checks", "bool"),
            ("monitoring_config.enable_logging", "bool")
        ]
        
        for field, expected_type in type_rules:
            self.validation_rules.append(
                ConfigurationValidationRule(
                    field_path=field,
                    rule_type="type",
                    parameters={"expected_type": expected_type},
                    error_message=f"Field '{field}' must be of type {expected_type}"
                )
            )
        
        # Range validation
        range_rules = [
            ("service_config.service_port", 1024, 65535),
            ("service_config.worker_processes", 1, 16),
            ("resource_config.memory_limit_mb", 64, 8192),
            ("resource_config.cpu_limit_cores", 0.1, 8.0),
            ("resource_config.max_concurrent_requests", 1, 1000),
            ("meilisearch_config.timeout_seconds", 1, 300),
            ("meilisearch_config.max_retries", 0, 10)
        ]
        
        for field, min_val, max_val in range_rules:
            self.validation_rules.append(
                ConfigurationValidationRule(
                    field_path=field,
                    rule_type="range",
                    parameters={"min": min_val, "max": max_val},
                    error_message=f"Field '{field}' must be between {min_val} and {max_val}"
                )
            )
        
        # Choice validation
        choice_rules = [
            ("deployment_method", ["docker", "systemd", "standalone"]),
            ("security_config.security_level", ["basic", "standard", "strict"]),
            ("monitoring_config.log_level", ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        ]
        
        for field, choices in choice_rules:
            self.validation_rules.append(
                ConfigurationValidationRule(
                    field_path=field,
                    rule_type="choices",
                    parameters={"choices": choices},
                    error_message=f"Field '{field}' must be one of {choices}"
                )
            )
    
    def _load_default_layer(self):
        """Load default configuration layer."""
        default_config = {
            "deployment_method": "docker",
            "meilisearch_config": {
                "host": "http://localhost:7700",
                "port": 7700,
                "api_key": None,
                "ssl_enabled": False,
                "ssl_verify": True,
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0
            },
            "service_config": {
                "service_name": "thai-tokenizer",
                "service_port": 8000,
                "service_host": "0.0.0.0",
                "worker_processes": 2,
                "service_user": "thai-tokenizer",
                "service_group": "thai-tokenizer"
            },
            "security_config": {
                "security_level": "standard",
                "allowed_hosts": ["localhost", "127.0.0.1"],
                "cors_origins": [],
                "api_key_required": False,
                "enable_https": False
            },
            "resource_config": {
                "memory_limit_mb": 256,
                "cpu_limit_cores": 0.5,
                "max_concurrent_requests": 50,
                "request_timeout_seconds": 30,
                "enable_metrics": True,
                "metrics_port": 9000
            },
            "monitoring_config": {
                "enable_health_checks": True,
                "health_check_interval_seconds": 30,
                "enable_logging": True,
                "log_level": "INFO",
                "enable_prometheus": False,
                "prometheus_port": 9000
            },
            "installation_path": "/opt/thai-tokenizer",
            "data_path": "/opt/thai-tokenizer/data",
            "log_path": "/opt/thai-tokenizer/logs",
            "config_path": "/opt/thai-tokenizer/config",
            "environment_variables": {}
        }
        
        self.add_configuration_layer(
            ConfigurationSource.DEFAULTS,
            default_config,
            priority=0
        )
    
    def add_configuration_layer(
        self,
        source: ConfigurationSource,
        data: Dict[str, Any],
        priority: int,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """Add a configuration layer."""
        layer = ConfigurationLayer(
            source=source,
            priority=priority,
            data=data,
            metadata=metadata or {}
        )
        
        self.layers.append(layer)
        self.layers.sort(key=lambda x: x.priority)  # Sort by priority
        
        # Invalidate merged config
        self.merged_config = None
        self.config_hash = None
        
        self.logger.debug(f"Added configuration layer: {source.value} (priority: {priority})")
    
    def load_from_file(
        self,
        file_path: str,
        priority: int = 50,
        format: Optional[ConfigurationFormat] = None
    ):
        """Load configuration from file."""
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise ConfigurationError(f"Configuration file not found: {file_path}")
        
        # Determine format
        if format is None:
            format = self._detect_file_format(file_path)
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                if format == ConfigurationFormat.JSON:
                    data = json.load(f)
                elif format == ConfigurationFormat.YAML:
                    data = yaml.safe_load(f)
                elif format == ConfigurationFormat.ENV:
                    data = self._parse_env_file(f.read())
                else:
                    raise ConfigurationError(f"Unsupported configuration format: {format}")
            
            self.add_configuration_layer(
                ConfigurationSource.FILE,
                data,
                priority,
                metadata={
                    "file_path": str(file_path),
                    "format": format.value,
                    "file_size": file_path.stat().st_size,
                    "modified_time": datetime.fromtimestamp(file_path.stat().st_mtime, timezone.utc)
                }
            )
            
            self.logger.info(f"Loaded configuration from file: {file_path}")
            
        except Exception as e:
            raise ConfigurationError(f"Failed to load configuration from {file_path}: {e}")
    
    def load_from_environment(self, priority: int = 75, prefix: str = "THAI_TOKENIZER_"):
        """Load configuration from environment variables."""
        env_config = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # Convert environment variable to nested config key
                config_key = key[len(prefix):].lower()
                nested_key = config_key.replace('_', '.')
                
                # Convert value to appropriate type
                converted_value = self._convert_env_value(value)
                
                # Set nested value
                self._set_nested_value(env_config, nested_key, converted_value)
        
        if env_config:
            self.add_configuration_layer(
                ConfigurationSource.ENVIRONMENT,
                env_config,
                priority,
                metadata={"prefix": prefix, "variables_count": len(env_config)}
            )
            
            self.logger.info(f"Loaded {len(env_config)} configuration values from environment")
    
    def load_from_cli_args(self, args: Dict[str, Any], priority: int = 100):
        """Load configuration from CLI arguments."""
        if args:
            self.add_configuration_layer(
                ConfigurationSource.CLI_ARGS,
                args,
                priority,
                metadata={"args_count": len(args)}
            )
            
            self.logger.info(f"Loaded {len(args)} configuration values from CLI arguments")
    
    def _detect_file_format(self, file_path: Path) -> ConfigurationFormat:
        """Detect configuration file format."""
        suffix = file_path.suffix.lower()
        
        if suffix in ['.json']:
            return ConfigurationFormat.JSON
        elif suffix in ['.yml', '.yaml']:
            return ConfigurationFormat.YAML
        elif suffix in ['.toml']:
            return ConfigurationFormat.TOML
        elif suffix in ['.env']:
            return ConfigurationFormat.ENV
        else:
            # Try to detect from content
            try:
                with open(file_path, 'r') as f:
                    content = f.read().strip()
                    if content.startswith('{'):
                        return ConfigurationFormat.JSON
                    elif '=' in content and not content.startswith('---'):
                        return ConfigurationFormat.ENV
                    else:
                        return ConfigurationFormat.YAML
            except Exception:
                return ConfigurationFormat.JSON  # Default fallback
    
    def _parse_env_file(self, content: str) -> Dict[str, Any]:
        """Parse environment file content."""
        env_config = {}
        
        for line in content.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                key = key.strip()
                value = value.strip().strip('"\'')
                
                # Convert to nested config
                nested_key = key.lower().replace('_', '.')
                converted_value = self._convert_env_value(value)
                self._set_nested_value(env_config, nested_key, converted_value)
        
        return env_config
    
    def _convert_env_value(self, value: str) -> Any:
        """Convert environment variable value to appropriate type."""
        # Boolean conversion
        if value.lower() in ['true', 'yes', '1', 'on']:
            return True
        elif value.lower() in ['false', 'no', '0', 'off']:
            return False
        
        # Number conversion
        try:
            if '.' in value:
                return float(value)
            else:
                return int(value)
        except ValueError:
            pass
        
        # List conversion (comma-separated)
        if ',' in value:
            return [item.strip() for item in value.split(',')]
        
        # String (default)
        return value
    
    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any):
        """Set nested value in dictionary using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
    
    def _get_nested_value(self, obj: Dict[str, Any], path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def merge_configurations(self) -> Dict[str, Any]:
        """Merge all configuration layers."""
        merged = {}
        
        # Merge layers in priority order (lowest to highest)
        for layer in self.layers:
            merged = self._deep_merge(merged, layer.data)
        
        return merged
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def get_unified_config(self) -> OnPremiseConfig:
        """Get unified configuration object."""
        if self.merged_config is None:
            merged_data = self.merge_configurations()
            
            try:
                self.merged_config = OnPremiseConfig(**merged_data)
                
                # Calculate configuration hash
                config_str = json.dumps(merged_data, sort_keys=True)
                self.config_hash = hashlib.sha256(config_str.encode()).hexdigest()
                
            except Exception as e:
                raise ConfigurationError(f"Failed to create unified configuration: {e}")
        
        return self.merged_config
    
    def validate_configuration(self) -> ValidationResult:
        """Validate the unified configuration."""
        try:
            config = self.get_unified_config()
            merged_data = self.merge_configurations()
            
            errors = []
            warnings = []
            
            # Run validation rules
            for rule in self.validation_rules:
                try:
                    self._validate_rule(rule, merged_data, errors, warnings)
                except Exception as e:
                    errors.append(f"Validation rule error for {rule.field_path}: {e}")
            
            # Additional OnPremiseConfig validation
            config_validation = config.validate_paths()
            if not config_validation.valid:
                errors.extend(config_validation.errors)
            warnings.extend(config_validation.warnings)
            
            return ValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Configuration validation failed: {e}"],
                warnings=[]
            )
    
    def _validate_rule(
        self,
        rule: ConfigurationValidationRule,
        data: Dict[str, Any],
        errors: List[str],
        warnings: List[str]
    ):
        """Validate a single configuration rule."""
        value = self._get_nested_value(data, rule.field_path)
        
        if rule.rule_type == "required":
            if value is None:
                errors.append(rule.error_message or f"Required field '{rule.field_path}' is missing")
        
        elif rule.rule_type == "type" and value is not None:
            expected_type = rule.parameters.get("expected_type")
            type_map = {
                "str": str,
                "int": int,
                "float": (int, float),
                "bool": bool,
                "list": list,
                "dict": dict
            }
            
            expected_python_type = type_map.get(expected_type)
            if expected_python_type and not isinstance(value, expected_python_type):
                errors.append(rule.error_message or f"Field '{rule.field_path}' must be of type {expected_type}")
        
        elif rule.rule_type == "range" and value is not None:
            if isinstance(value, (int, float)):
                min_val = rule.parameters.get("min")
                max_val = rule.parameters.get("max")
                
                if min_val is not None and value < min_val:
                    errors.append(rule.error_message or f"Field '{rule.field_path}' must be >= {min_val}")
                
                if max_val is not None and value > max_val:
                    errors.append(rule.error_message or f"Field '{rule.field_path}' must be <= {max_val}")
        
        elif rule.rule_type == "choices" and value is not None:
            choices = rule.parameters.get("choices", [])
            if value not in choices:
                errors.append(rule.error_message or f"Field '{rule.field_path}' must be one of {choices}")
    
    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get configuration summary and metadata."""
        return {
            "layers_count": len(self.layers),
            "layers": [
                {
                    "source": layer.source.value,
                    "priority": layer.priority,
                    "timestamp": layer.timestamp.isoformat(),
                    "metadata": layer.metadata
                }
                for layer in self.layers
            ],
            "config_hash": self.config_hash,
            "validation_rules_count": len(self.validation_rules),
            "merged_config_available": self.merged_config is not None
        }
    
    def export_configuration(
        self,
        output_file: str,
        format: ConfigurationFormat = ConfigurationFormat.JSON,
        include_metadata: bool = False
    ) -> str:
        """Export unified configuration to file."""
        config = self.get_unified_config()
        config_data = config.dict()
        
        if include_metadata:
            export_data = {
                "configuration": config_data,
                "metadata": self.get_configuration_summary(),
                "export_timestamp": datetime.now(timezone.utc).isoformat()
            }
        else:
            export_data = config_data
        
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                if format == ConfigurationFormat.JSON:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                elif format == ConfigurationFormat.YAML:
                    yaml.dump(export_data, f, default_flow_style=False, allow_unicode=True)
                else:
                    raise ConfigurationError(f"Export format not supported: {format}")
            
            self.logger.info(f"Configuration exported to: {output_path}")
            return str(output_path)
            
        except Exception as e:
            raise ConfigurationError(f"Failed to export configuration: {e}")
    
    def get_deployment_method_config(self, method: DeploymentMethod) -> Dict[str, Any]:
        """Get method-specific configuration adjustments."""
        config = self.get_unified_config()
        base_config = config.dict()
        
        # Method-specific adjustments
        if method == DeploymentMethod.DOCKER:
            # Docker-specific adjustments
            base_config.update({
                "service_config": {
                    **base_config.get("service_config", {}),
                    "service_host": "0.0.0.0"  # Docker needs to bind to all interfaces
                }
            })
        
        elif method == DeploymentMethod.SYSTEMD:
            # Systemd-specific adjustments
            base_config.update({
                "service_config": {
                    **base_config.get("service_config", {}),
                    "service_host": "127.0.0.1"  # Systemd can bind to localhost
                },
                "installation_path": "/opt/thai-tokenizer",
                "log_path": "/var/log/thai-tokenizer",
                "config_path": "/etc/thai-tokenizer"
            })
        
        elif method == DeploymentMethod.STANDALONE:
            # Standalone-specific adjustments
            base_config.update({
                "installation_path": "./thai-tokenizer-standalone",
                "data_path": "./thai-tokenizer-standalone/data",
                "log_path": "./thai-tokenizer-standalone/logs",
                "config_path": "./thai-tokenizer-standalone/config"
            })
        
        return base_config
    
    def create_method_specific_config(self, method: DeploymentMethod) -> OnPremiseConfig:
        """Create method-specific configuration object."""
        method_config_data = self.get_deployment_method_config(method)
        method_config_data["deployment_method"] = method.value
        
        try:
            return OnPremiseConfig(**method_config_data)
        except Exception as e:
            raise ConfigurationError(f"Failed to create {method.value} configuration: {e}")


# Factory functions
def create_unified_config_manager(base_config: Optional[OnPremiseConfig] = None) -> UnifiedConfigurationManager:
    """Create a unified configuration manager."""
    return UnifiedConfigurationManager(base_config)


def load_unified_config(
    config_file: Optional[str] = None,
    environment_prefix: str = "THAI_TOKENIZER_",
    cli_args: Optional[Dict[str, Any]] = None
) -> OnPremiseConfig:
    """Load unified configuration from multiple sources."""
    manager = create_unified_config_manager()
    
    # Load from file if provided
    if config_file:
        manager.load_from_file(config_file, priority=50)
    
    # Load from environment
    manager.load_from_environment(priority=75, prefix=environment_prefix)
    
    # Load from CLI args if provided
    if cli_args:
        manager.load_from_cli_args(cli_args, priority=100)
    
    # Validate and return unified config
    validation_result = manager.validate_configuration()
    if not validation_result.valid:
        raise ConfigurationError(f"Configuration validation failed: {validation_result.errors}")
    
    return manager.get_unified_config()