#!/usr/bin/env python3
"""
Configuration Management Automation for Thai Tokenizer Deployment.

This module provides automated configuration management tools including
configuration validation, environment-specific configuration generation,
secret management, and configuration drift detection.
"""

import json
import os
import sys
import yaml
import hashlib
import base64
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from deployment.config import OnPremiseConfig, DeploymentMethod


@dataclass
class ConfigurationTemplate:
    """Configuration template definition."""
    name: str
    description: str
    deployment_method: str
    environment: str
    template_data: Dict[str, Any]
    required_secrets: List[str]
    validation_rules: Dict[str, Any]


@dataclass
class ConfigurationDrift:
    """Configuration drift detection result."""
    config_path: str
    expected_hash: str
    actual_hash: str
    drift_detected: bool
    changed_fields: List[str]
    timestamp: datetime


class SecretManager:
    """Secure secret management for configuration."""
    
    def __init__(self, key_file: Optional[str] = None):
        self.key_file = Path(key_file) if key_file else Path.home() / ".thai-tokenizer" / "secret.key"
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self._key = self._load_or_generate_key()
        self._cipher = Fernet(self._key)
    
    def _load_or_generate_key(self) -> bytes:
        """Load existing key or generate new one."""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            key = Fernet.generate_key()
            with open(self.key_file, 'wb') as f:
                f.write(key)
            # Set restrictive permissions
            os.chmod(self.key_file, 0o600)
            return key
    
    def encrypt_secret(self, secret: str) -> str:
        """Encrypt a secret value."""
        encrypted = self._cipher.encrypt(secret.encode())
        return base64.b64encode(encrypted).decode()
    
    def decrypt_secret(self, encrypted_secret: str) -> str:
        """Decrypt a secret value."""
        encrypted_bytes = base64.b64decode(encrypted_secret.encode())
        decrypted = self._cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    def encrypt_config_secrets(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Encrypt secrets in configuration dictionary."""
        encrypted_config = config_dict.copy()
        
        # Define secret fields to encrypt
        secret_fields = [
            'api_key', 'password', 'secret', 'token', 'private_key',
            'meilisearch_config.api_key'
        ]
        
        for field in secret_fields:
            value = self._get_nested_value(encrypted_config, field)
            if value and isinstance(value, str):
                encrypted_value = self.encrypt_secret(value)
                self._set_nested_value(encrypted_config, field, f"encrypted:{encrypted_value}")
        
        return encrypted_config
    
    def decrypt_config_secrets(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Decrypt secrets in configuration dictionary."""
        decrypted_config = config_dict.copy()
        
        def decrypt_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if isinstance(value, str) and value.startswith("encrypted:"):
                        encrypted_value = value[10:]  # Remove "encrypted:" prefix
                        obj[key] = self.decrypt_secret(encrypted_value)
                    else:
                        decrypt_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    decrypt_recursive(item)
        
        decrypt_recursive(decrypted_config)
        return decrypted_config
    
    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, obj: Dict, path: str, value: Any) -> None:
        """Set nested value in dictionary using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value


class ConfigurationManager:
    """Configuration management automation."""
    
    def __init__(self, config_dir: str = "configs", templates_dir: str = "config_templates"):
        self.config_dir = Path(config_dir)
        self.templates_dir = Path(templates_dir)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(parents=True, exist_ok=True)
        
        self.secret_manager = SecretManager()
        self.templates = self._load_templates()
    
    def _load_templates(self) -> Dict[str, ConfigurationTemplate]:
        """Load configuration templates."""
        templates = {}
        
        # Define built-in templates
        templates["docker-development"] = ConfigurationTemplate(
            name="docker-development",
            description="Docker deployment for development environment",
            deployment_method="docker",
            environment="development",
            template_data={
                "deployment_method": "docker",
                "meilisearch_config": {
                    "host": "${MEILISEARCH_HOST:-http://localhost:7700}",
                    "port": "${MEILISEARCH_PORT:-7700}",
                    "api_key": "${MEILISEARCH_API_KEY}",
                    "ssl_enabled": False,
                    "ssl_verify": True,
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "retry_delay_seconds": 1.0
                },
                "service_config": {
                    "service_name": "thai-tokenizer-dev",
                    "service_port": "${SERVICE_PORT:-8000}",
                    "service_host": "0.0.0.0",
                    "worker_processes": 2,
                    "service_user": "thai-tokenizer",
                    "service_group": "thai-tokenizer"
                },
                "security_config": {
                    "security_level": "basic",
                    "allowed_hosts": ["*"],
                    "cors_origins": ["*"],
                    "api_key_required": False,
                    "enable_https": False
                },
                "resource_config": {
                    "memory_limit_mb": 256,
                    "cpu_limit_cores": 0.5,
                    "max_concurrent_requests": 20,
                    "request_timeout_seconds": 30,
                    "enable_metrics": True,
                    "metrics_port": 9000
                },
                "monitoring_config": {
                    "enable_health_checks": True,
                    "health_check_interval_seconds": 60,
                    "enable_logging": True,
                    "log_level": "DEBUG",
                    "enable_prometheus": False,
                    "prometheus_port": 9000
                },
                "installation_path": "./thai-tokenizer-dev",
                "data_path": "./thai-tokenizer-dev/data",
                "log_path": "./thai-tokenizer-dev/logs",
                "config_path": "./thai-tokenizer-dev/config",
                "environment_variables": {
                    "ENVIRONMENT": "development",
                    "PYTHONPATH": "src",
                    "LOG_LEVEL": "DEBUG"
                }
            },
            required_secrets=["MEILISEARCH_API_KEY"],
            validation_rules={
                "service_port": {"type": "int", "min": 1024, "max": 65535},
                "memory_limit_mb": {"type": "int", "min": 128, "max": 2048},
                "security_level": {"type": "str", "choices": ["basic", "standard", "strict"]}
            }
        )
        
        templates["docker-production"] = ConfigurationTemplate(
            name="docker-production",
            description="Docker deployment for production environment",
            deployment_method="docker",
            environment="production",
            template_data={
                "deployment_method": "docker",
                "meilisearch_config": {
                    "host": "${MEILISEARCH_HOST}",
                    "port": "${MEILISEARCH_PORT:-7700}",
                    "api_key": "${MEILISEARCH_API_KEY}",
                    "ssl_enabled": True,
                    "ssl_verify": True,
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "retry_delay_seconds": 1.0
                },
                "service_config": {
                    "service_name": "thai-tokenizer-prod",
                    "service_port": "${SERVICE_PORT:-8000}",
                    "service_host": "0.0.0.0",
                    "worker_processes": 4,
                    "service_user": "thai-tokenizer",
                    "service_group": "thai-tokenizer"
                },
                "security_config": {
                    "security_level": "strict",
                    "allowed_hosts": ["${ALLOWED_HOST}"],
                    "cors_origins": ["${CORS_ORIGIN}"],
                    "api_key_required": True,
                    "enable_https": True
                },
                "resource_config": {
                    "memory_limit_mb": 512,
                    "cpu_limit_cores": 2.0,
                    "max_concurrent_requests": 100,
                    "request_timeout_seconds": 30,
                    "enable_metrics": True,
                    "metrics_port": 9000
                },
                "monitoring_config": {
                    "enable_health_checks": True,
                    "health_check_interval_seconds": 15,
                    "enable_logging": True,
                    "log_level": "WARNING",
                    "enable_prometheus": True,
                    "prometheus_port": 9000
                },
                "installation_path": "/opt/thai-tokenizer",
                "data_path": "/opt/thai-tokenizer/data",
                "log_path": "/opt/thai-tokenizer/logs",
                "config_path": "/opt/thai-tokenizer/config",
                "environment_variables": {
                    "ENVIRONMENT": "production",
                    "PYTHONPATH": "src",
                    "LOG_LEVEL": "WARNING"
                }
            },
            required_secrets=["MEILISEARCH_API_KEY", "ALLOWED_HOST", "CORS_ORIGIN"],
            validation_rules={
                "service_port": {"type": "int", "min": 1024, "max": 65535},
                "memory_limit_mb": {"type": "int", "min": 256, "max": 4096},
                "security_level": {"type": "str", "choices": ["standard", "strict"]}
            }
        )
        
        templates["systemd-production"] = ConfigurationTemplate(
            name="systemd-production",
            description="Systemd deployment for production environment",
            deployment_method="systemd",
            environment="production",
            template_data={
                "deployment_method": "systemd",
                "meilisearch_config": {
                    "host": "${MEILISEARCH_HOST}",
                    "port": "${MEILISEARCH_PORT:-7700}",
                    "api_key": "${MEILISEARCH_API_KEY}",
                    "ssl_enabled": True,
                    "ssl_verify": True,
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "retry_delay_seconds": 1.0
                },
                "service_config": {
                    "service_name": "thai-tokenizer",
                    "service_port": "${SERVICE_PORT:-8000}",
                    "service_host": "127.0.0.1",
                    "worker_processes": 4,
                    "service_user": "thai-tokenizer",
                    "service_group": "thai-tokenizer"
                },
                "security_config": {
                    "security_level": "strict",
                    "allowed_hosts": ["127.0.0.1", "${ALLOWED_HOST}"],
                    "cors_origins": ["${CORS_ORIGIN}"],
                    "api_key_required": True,
                    "enable_https": True
                },
                "resource_config": {
                    "memory_limit_mb": 1024,
                    "cpu_limit_cores": 2.0,
                    "max_concurrent_requests": 200,
                    "request_timeout_seconds": 30,
                    "enable_metrics": True,
                    "metrics_port": 9000
                },
                "monitoring_config": {
                    "enable_health_checks": True,
                    "health_check_interval_seconds": 15,
                    "enable_logging": True,
                    "log_level": "INFO",
                    "enable_prometheus": True,
                    "prometheus_port": 9000
                },
                "installation_path": "/opt/thai-tokenizer",
                "data_path": "/opt/thai-tokenizer/data",
                "log_path": "/var/log/thai-tokenizer",
                "config_path": "/etc/thai-tokenizer",
                "environment_variables": {
                    "ENVIRONMENT": "production",
                    "PYTHONPATH": "/opt/thai-tokenizer/src",
                    "LOG_LEVEL": "INFO"
                }
            },
            required_secrets=["MEILISEARCH_API_KEY", "ALLOWED_HOST", "CORS_ORIGIN"],
            validation_rules={
                "service_port": {"type": "int", "min": 1024, "max": 65535},
                "memory_limit_mb": {"type": "int", "min": 512, "max": 8192},
                "security_level": {"type": "str", "choices": ["standard", "strict"]}
            }
        )
        
        return templates
    
    def generate_config_from_template(
        self, 
        template_name: str, 
        environment_vars: Dict[str, str] = None,
        custom_overrides: Dict[str, Any] = None,
        output_file: Optional[str] = None
    ) -> Tuple[str, OnPremiseConfig]:
        """Generate configuration from template."""
        
        if template_name not in self.templates:
            raise ValueError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        environment_vars = environment_vars or {}
        custom_overrides = custom_overrides or {}
        
        # Substitute environment variables
        config_data = self._substitute_variables(template.template_data, environment_vars)
        
        # Apply custom overrides
        if custom_overrides:
            config_data = self._deep_merge(config_data, custom_overrides)
        
        # Validate configuration
        validation_errors = self._validate_config_data(config_data, template.validation_rules)
        if validation_errors:
            raise ValueError(f"Configuration validation failed: {validation_errors}")
        
        # Create OnPremiseConfig object
        config = OnPremiseConfig(**config_data)
        
        # Save configuration if output file specified
        if output_file:
            output_path = Path(output_file)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Encrypt secrets before saving
            encrypted_config = self.secret_manager.encrypt_config_secrets(config_data)
            
            with open(output_path, 'w') as f:
                json.dump(encrypted_config, f, indent=2, ensure_ascii=False)
            
            return str(output_path), config
        else:
            # Generate temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            temp_file = self.config_dir / f"{template_name}_{timestamp}.json"
            
            with open(temp_file, 'w') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            return str(temp_file), config
    
    def _substitute_variables(self, data: Any, env_vars: Dict[str, str]) -> Any:
        """Substitute environment variables in configuration data."""
        if isinstance(data, str):
            # Handle ${VAR} and ${VAR:-default} patterns
            import re
            
            def replace_var(match):
                var_expr = match.group(1)
                if ':-' in var_expr:
                    var_name, default_value = var_expr.split(':-', 1)
                    return env_vars.get(var_name, os.getenv(var_name, default_value))
                else:
                    return env_vars.get(var_expr, os.getenv(var_expr, match.group(0)))
            
            return re.sub(r'\$\{([^}]+)\}', replace_var, data)
        
        elif isinstance(data, dict):
            return {key: self._substitute_variables(value, env_vars) for key, value in data.items()}
        
        elif isinstance(data, list):
            return [self._substitute_variables(item, env_vars) for item in data]
        
        else:
            return data
    
    def _deep_merge(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()
        
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value
        
        return result
    
    def _validate_config_data(self, config_data: Dict[str, Any], validation_rules: Dict[str, Any]) -> List[str]:
        """Validate configuration data against rules."""
        errors = []
        
        for field_path, rules in validation_rules.items():
            value = self._get_nested_value(config_data, field_path)
            
            if value is None:
                if rules.get("required", False):
                    errors.append(f"Required field '{field_path}' is missing")
                continue
            
            # Type validation
            if "type" in rules:
                expected_type = rules["type"]
                if expected_type == "int" and not isinstance(value, int):
                    try:
                        value = int(value)
                    except (ValueError, TypeError):
                        errors.append(f"Field '{field_path}' must be an integer")
                        continue
                elif expected_type == "str" and not isinstance(value, str):
                    errors.append(f"Field '{field_path}' must be a string")
                    continue
            
            # Range validation
            if isinstance(value, (int, float)):
                if "min" in rules and value < rules["min"]:
                    errors.append(f"Field '{field_path}' must be >= {rules['min']}")
                if "max" in rules and value > rules["max"]:
                    errors.append(f"Field '{field_path}' must be <= {rules['max']}")
            
            # Choice validation
            if "choices" in rules and value not in rules["choices"]:
                errors.append(f"Field '{field_path}' must be one of {rules['choices']}")
        
        return errors
    
    def _get_nested_value(self, obj: Dict, path: str) -> Any:
        """Get nested value from dictionary using dot notation."""
        keys = path.split('.')
        current = obj
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def load_config_with_secrets(self, config_file: str) -> OnPremiseConfig:
        """Load configuration file and decrypt secrets."""
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Decrypt secrets
        decrypted_config = self.secret_manager.decrypt_config_secrets(config_data)
        
        return OnPremiseConfig(**decrypted_config)
    
    def detect_configuration_drift(
        self, 
        config_file: str, 
        expected_hash: Optional[str] = None
    ) -> ConfigurationDrift:
        """Detect configuration drift."""
        
        config_path = Path(config_file)
        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_file}")
        
        # Calculate current hash
        with open(config_path, 'rb') as f:
            content = f.read()
            actual_hash = hashlib.sha256(content).hexdigest()
        
        # Load expected hash if not provided
        if expected_hash is None:
            hash_file = config_path.with_suffix('.hash')
            if hash_file.exists():
                with open(hash_file, 'r') as f:
                    expected_hash = f.read().strip()
            else:
                # First time - save current hash as expected
                with open(hash_file, 'w') as f:
                    f.write(actual_hash)
                expected_hash = actual_hash
        
        # Detect drift
        drift_detected = actual_hash != expected_hash
        changed_fields = []
        
        if drift_detected:
            # Try to identify changed fields (simplified)
            try:
                with open(config_path, 'r') as f:
                    current_config = json.load(f)
                
                # This is a simplified approach - in practice, you'd want
                # to store the previous configuration for detailed comparison
                changed_fields = ["configuration_file_modified"]
                
            except Exception:
                changed_fields = ["unknown_changes"]
        
        return ConfigurationDrift(
            config_path=str(config_path),
            expected_hash=expected_hash,
            actual_hash=actual_hash,
            drift_detected=drift_detected,
            changed_fields=changed_fields,
            timestamp=datetime.now(timezone.utc)
        )
    
    def update_configuration_baseline(self, config_file: str) -> str:
        """Update configuration baseline hash."""
        config_path = Path(config_file)
        
        with open(config_path, 'rb') as f:
            content = f.read()
            new_hash = hashlib.sha256(content).hexdigest()
        
        hash_file = config_path.with_suffix('.hash')
        with open(hash_file, 'w') as f:
            f.write(new_hash)
        
        return new_hash
    
    def generate_environment_configs(
        self, 
        environments: List[str],
        base_template: str = "docker-development",
        environment_vars: Dict[str, Dict[str, str]] = None
    ) -> Dict[str, str]:
        """Generate configurations for multiple environments."""
        
        environment_vars = environment_vars or {}
        generated_configs = {}
        
        for env in environments:
            # Determine template based on environment
            if env == "production":
                template_name = base_template.replace("development", "production")
                if template_name not in self.templates:
                    template_name = "docker-production"
            else:
                template_name = base_template
            
            # Get environment-specific variables
            env_vars = environment_vars.get(env, {})
            env_vars["ENVIRONMENT"] = env
            
            # Generate configuration
            config_file, _ = self.generate_config_from_template(
                template_name,
                env_vars,
                output_file=str(self.config_dir / f"{env}_config.json")
            )
            
            generated_configs[env] = config_file
        
        return generated_configs
    
    def validate_all_configurations(self, config_dir: Optional[str] = None) -> Dict[str, List[str]]:
        """Validate all configuration files in directory."""
        
        config_dir = Path(config_dir) if config_dir else self.config_dir
        validation_results = {}
        
        for config_file in config_dir.glob("*.json"):
            try:
                config = self.load_config_with_secrets(str(config_file))
                validation_result = config.validate_paths()
                
                if validation_result.valid:
                    validation_results[str(config_file)] = []
                else:
                    validation_results[str(config_file)] = validation_result.errors
                    
            except Exception as e:
                validation_results[str(config_file)] = [f"Failed to load: {str(e)}"]
        
        return validation_results
    
    def backup_configurations(self, backup_dir: Optional[str] = None) -> str:
        """Backup all configuration files."""
        
        backup_dir = Path(backup_dir) if backup_dir else Path("config_backups")
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_subdir = backup_dir / f"backup_{timestamp}"
        backup_subdir.mkdir()
        
        # Copy all configuration files
        import shutil
        
        for config_file in self.config_dir.glob("*.json"):
            shutil.copy2(config_file, backup_subdir)
        
        # Copy hash files
        for hash_file in self.config_dir.glob("*.hash"):
            shutil.copy2(hash_file, backup_subdir)
        
        # Create backup manifest
        manifest = {
            "backup_timestamp": timestamp,
            "backup_path": str(backup_subdir),
            "files_backed_up": [f.name for f in backup_subdir.glob("*")],
            "total_files": len(list(backup_subdir.glob("*")))
        }
        
        with open(backup_subdir / "manifest.json", 'w') as f:
            json.dump(manifest, f, indent=2)
        
        return str(backup_subdir)


def main():
    """Main configuration management entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Configuration Management Automation")
    parser.add_argument("command", choices=[
        "generate", "validate", "drift-check", "backup", "list-templates"
    ], help="Command to execute")
    
    parser.add_argument("--template", help="Configuration template name")
    parser.add_argument("--environment", help="Target environment")
    parser.add_argument("--output", help="Output configuration file")
    parser.add_argument("--config-dir", default="configs", help="Configuration directory")
    parser.add_argument("--env-vars", help="Environment variables JSON file")
    parser.add_argument("--overrides", help="Configuration overrides JSON file")
    
    args = parser.parse_args()
    
    # Create configuration manager
    config_manager = ConfigurationManager(args.config_dir)
    
    try:
        if args.command == "generate":
            if not args.template:
                print("Error: --template is required for generate command")
                return 1
            
            # Load environment variables
            env_vars = {}
            if args.env_vars:
                with open(args.env_vars, 'r') as f:
                    env_vars = json.load(f)
            
            # Load overrides
            overrides = {}
            if args.overrides:
                with open(args.overrides, 'r') as f:
                    overrides = json.load(f)
            
            # Generate configuration
            config_file, config = config_manager.generate_config_from_template(
                args.template,
                env_vars,
                overrides,
                args.output
            )
            
            print(f"✅ Configuration generated: {config_file}")
            print(f"   Template: {args.template}")
            print(f"   Deployment method: {config.deployment_method.value}")
            
        elif args.command == "validate":
            results = config_manager.validate_all_configurations(args.config_dir)
            
            print("📋 Configuration Validation Results:")
            for config_file, errors in results.items():
                if errors:
                    print(f"❌ {config_file}:")
                    for error in errors:
                        print(f"   - {error}")
                else:
                    print(f"✅ {config_file}: Valid")
        
        elif args.command == "drift-check":
            if not args.output:
                print("Error: --output (config file) is required for drift-check command")
                return 1
            
            drift = config_manager.detect_configuration_drift(args.output)
            
            if drift.drift_detected:
                print(f"⚠️  Configuration drift detected: {drift.config_path}")
                print(f"   Expected hash: {drift.expected_hash[:16]}...")
                print(f"   Actual hash: {drift.actual_hash[:16]}...")
                print(f"   Changed fields: {', '.join(drift.changed_fields)}")
                return 1
            else:
                print(f"✅ No configuration drift detected: {drift.config_path}")
        
        elif args.command == "backup":
            backup_path = config_manager.backup_configurations()
            print(f"✅ Configurations backed up to: {backup_path}")
        
        elif args.command == "list-templates":
            print("📋 Available Configuration Templates:")
            for name, template in config_manager.templates.items():
                print(f"   {name}:")
                print(f"     Description: {template.description}")
                print(f"     Method: {template.deployment_method}")
                print(f"     Environment: {template.environment}")
                print(f"     Required secrets: {', '.join(template.required_secrets)}")
                print()
        
        return 0
        
    except Exception as e:
        print(f"❌ Configuration management failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())