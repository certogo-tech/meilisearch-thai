"""
Configuration templates for different deployment methods.

This module provides pre-configured templates for Docker, systemd, and standalone
deployment methods, making it easy to generate deployment-specific configurations.
"""

from typing import Dict, Any, Optional
from pathlib import Path

try:
    from src.deployment.config import (
        OnPremiseConfig,
        DeploymentMethod,
        MeilisearchConnectionConfig,
        ServiceConfig,
        SecurityConfig,
        ResourceConfig,
        MonitoringConfig,
        SecurityLevel
    )
except ImportError:
    from deployment.config import (
        OnPremiseConfig,
        DeploymentMethod,
        MeilisearchConnectionConfig,
        ServiceConfig,
        SecurityConfig,
        ResourceConfig,
        MonitoringConfig,
        SecurityLevel
    )


class DeploymentTemplates:
    """Factory class for creating deployment configuration templates."""
    
    @staticmethod
    def create_docker_template(
        meilisearch_host: str,
        meilisearch_api_key: str,
        service_port: int = 8000,
        security_level: SecurityLevel = SecurityLevel.STANDARD
    ) -> OnPremiseConfig:
        """
        Create a Docker deployment configuration template.
        
        Args:
            meilisearch_host: Existing Meilisearch server host
            meilisearch_api_key: API key for Meilisearch
            service_port: Port for the Thai Tokenizer service
            security_level: Security configuration level
            
        Returns:
            OnPremiseConfig configured for Docker deployment
        """
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.DOCKER,
            meilisearch_config=MeilisearchConnectionConfig(
                host=meilisearch_host,
                api_key=meilisearch_api_key,
                timeout_seconds=30,
                max_retries=3,
                ssl_enabled=meilisearch_host.startswith('https://'),
                ssl_verify=True
            ),
            service_config=ServiceConfig(
                service_name="thai-tokenizer",
                service_port=service_port,
                service_host="0.0.0.0",
                worker_processes=4,
                service_user="thai-tokenizer",
                service_group="thai-tokenizer"
            ),
            security_config=SecurityConfig(
                security_level=security_level,
                allowed_hosts=["*"] if security_level == SecurityLevel.BASIC else ["localhost", "127.0.0.1"],
                cors_origins=["*"] if security_level == SecurityLevel.BASIC else [],
                api_key_required=security_level == SecurityLevel.HIGH,
                enable_https=False,
                firewall_rules=[]
            ),
            resource_config=ResourceConfig(
                memory_limit_mb=512,
                cpu_limit_cores=1.0,
                max_concurrent_requests=100,
                request_timeout_seconds=30,
                enable_metrics=True,
                metrics_port=9090
            ),
            monitoring_config=MonitoringConfig(
                enable_health_checks=True,
                health_check_interval_seconds=30,
                enable_logging=True,
                log_level="INFO",
                log_file_path=None,  # Docker uses stdout/stderr
                enable_prometheus=True,
                prometheus_port=9090
            ),
            installation_path="/app",
            data_path="/app/data",
            log_path="/app/logs",
            config_path="/app/config",
            environment_variables={
                "PYTHONPATH": "/app",
                "PYTHONUNBUFFERED": "1",
                "DOCKER_DEPLOYMENT": "true"
            }
        )
    
    @staticmethod
    def create_systemd_template(
        meilisearch_host: str,
        meilisearch_api_key: str,
        service_port: int = 8000,
        security_level: SecurityLevel = SecurityLevel.STANDARD,
        installation_path: str = "/opt/thai-tokenizer"
    ) -> OnPremiseConfig:
        """
        Create a systemd service deployment configuration template.
        
        Args:
            meilisearch_host: Existing Meilisearch server host
            meilisearch_api_key: API key for Meilisearch
            service_port: Port for the Thai Tokenizer service
            security_level: Security configuration level
            installation_path: Installation directory path
            
        Returns:
            OnPremiseConfig configured for systemd deployment
        """
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.SYSTEMD,
            meilisearch_config=MeilisearchConnectionConfig(
                host=meilisearch_host,
                api_key=meilisearch_api_key,
                timeout_seconds=30,
                max_retries=3,
                ssl_enabled=meilisearch_host.startswith('https://'),
                ssl_verify=True
            ),
            service_config=ServiceConfig(
                service_name="thai-tokenizer",
                service_port=service_port,
                service_host="127.0.0.1",  # More secure default for systemd
                worker_processes=2,  # Conservative for systemd
                service_user="thai-tokenizer",
                service_group="thai-tokenizer"
            ),
            security_config=SecurityConfig(
                security_level=security_level,
                allowed_hosts=["localhost", "127.0.0.1"] if security_level != SecurityLevel.BASIC else ["*"],
                cors_origins=[] if security_level == SecurityLevel.HIGH else ["http://localhost:*"],
                api_key_required=security_level == SecurityLevel.HIGH,
                enable_https=security_level == SecurityLevel.HIGH,
                firewall_rules=[
                    f"ufw allow {service_port}/tcp comment 'Thai Tokenizer Service'"
                ] if security_level != SecurityLevel.BASIC else []
            ),
            resource_config=ResourceConfig(
                memory_limit_mb=256,  # Conservative for systemd
                cpu_limit_cores=0.5,
                max_concurrent_requests=50,
                request_timeout_seconds=30,
                enable_metrics=True,
                metrics_port=9091  # Different port to avoid conflicts
            ),
            monitoring_config=MonitoringConfig(
                enable_health_checks=True,
                health_check_interval_seconds=60,
                enable_logging=True,
                log_level="INFO",
                log_file_path="/var/log/thai-tokenizer/service.log",
                enable_prometheus=security_level != SecurityLevel.BASIC,
                prometheus_port=9091
            ),
            installation_path=installation_path,
            data_path="/var/lib/thai-tokenizer",
            log_path="/var/log/thai-tokenizer",
            config_path="/etc/thai-tokenizer",
            environment_variables={
                "PYTHONPATH": installation_path,
                "SYSTEMD_DEPLOYMENT": "true",
                "HOME": "/var/lib/thai-tokenizer"
            }
        )
    
    @staticmethod
    def create_standalone_template(
        meilisearch_host: str,
        meilisearch_api_key: str,
        service_port: int = 8000,
        security_level: SecurityLevel = SecurityLevel.BASIC,
        installation_path: str = "/home/thai-tokenizer/app"
    ) -> OnPremiseConfig:
        """
        Create a standalone Python deployment configuration template.
        
        Args:
            meilisearch_host: Existing Meilisearch server host
            meilisearch_api_key: API key for Meilisearch
            service_port: Port for the Thai Tokenizer service
            security_level: Security configuration level
            installation_path: Installation directory path
            
        Returns:
            OnPremiseConfig configured for standalone deployment
        """
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.STANDALONE,
            meilisearch_config=MeilisearchConnectionConfig(
                host=meilisearch_host,
                api_key=meilisearch_api_key,
                timeout_seconds=30,
                max_retries=3,
                ssl_enabled=meilisearch_host.startswith('https://'),
                ssl_verify=True
            ),
            service_config=ServiceConfig(
                service_name="thai-tokenizer",
                service_port=service_port,
                service_host="127.0.0.1",  # Secure default
                worker_processes=1,  # Single process for standalone
                service_user="thai-tokenizer",
                service_group="thai-tokenizer"
            ),
            security_config=SecurityConfig(
                security_level=security_level,
                allowed_hosts=["localhost", "127.0.0.1"],
                cors_origins=["http://localhost:*"] if security_level == SecurityLevel.BASIC else [],
                api_key_required=security_level == SecurityLevel.HIGH,
                enable_https=False,  # Typically behind reverse proxy
                firewall_rules=[]
            ),
            resource_config=ResourceConfig(
                memory_limit_mb=256,
                cpu_limit_cores=0.5,
                max_concurrent_requests=25,  # Conservative for standalone
                request_timeout_seconds=30,
                enable_metrics=False,  # Simplified for standalone
                metrics_port=9092
            ),
            monitoring_config=MonitoringConfig(
                enable_health_checks=True,
                health_check_interval_seconds=60,
                enable_logging=True,
                log_level="INFO",
                log_file_path=f"{installation_path}/logs/service.log",
                enable_prometheus=False,  # Simplified for standalone
                prometheus_port=9092
            ),
            installation_path=installation_path,
            data_path=f"{installation_path}/data",
            log_path=f"{installation_path}/logs",
            config_path=f"{installation_path}/config",
            environment_variables={
                "PYTHONPATH": installation_path,
                "STANDALONE_DEPLOYMENT": "true",
                "VIRTUAL_ENV": f"{installation_path}/venv"
            }
        )
    
    @staticmethod
    def get_template_recommendations() -> Dict[str, Dict[str, Any]]:
        """
        Get recommendations for when to use each deployment template.
        
        Returns:
            Dictionary with template recommendations
        """
        return {
            "docker": {
                "name": "Docker Deployment",
                "description": "Containerized deployment with isolation and easy scaling",
                "best_for": [
                    "Production environments with container orchestration",
                    "Easy scaling and load balancing",
                    "Consistent deployment across environments",
                    "Teams familiar with Docker/Kubernetes"
                ],
                "requirements": [
                    "Docker Engine 20.10+",
                    "Docker Compose 2.0+ (optional)",
                    "Container orchestration platform (optional)"
                ],
                "pros": [
                    "Complete isolation from host system",
                    "Easy to scale horizontally",
                    "Consistent environment",
                    "Built-in health checks",
                    "Easy rollback and updates"
                ],
                "cons": [
                    "Requires Docker knowledge",
                    "Additional resource overhead",
                    "More complex networking setup"
                ]
            },
            "systemd": {
                "name": "Systemd Service",
                "description": "Native Linux service with system integration",
                "best_for": [
                    "Traditional Linux server environments",
                    "Integration with system monitoring",
                    "Automatic startup and restart",
                    "System administrators familiar with systemd"
                ],
                "requirements": [
                    "Linux with systemd",
                    "Python 3.12+",
                    "System administrator privileges",
                    "uv package manager"
                ],
                "pros": [
                    "Native system integration",
                    "Automatic startup and restart",
                    "System resource management",
                    "Integrated logging with journald",
                    "Lower resource overhead"
                ],
                "cons": [
                    "Linux/systemd specific",
                    "Requires system-level configuration",
                    "Manual dependency management"
                ]
            },
            "standalone": {
                "name": "Standalone Python",
                "description": "Direct Python execution with virtual environment",
                "best_for": [
                    "Development and testing",
                    "Simple single-server deployments",
                    "Environments without Docker or systemd",
                    "Quick prototyping and evaluation"
                ],
                "requirements": [
                    "Python 3.12+",
                    "uv package manager",
                    "Virtual environment support"
                ],
                "pros": [
                    "Simple setup and configuration",
                    "Direct access to Python environment",
                    "Easy debugging and development",
                    "Minimal system requirements",
                    "Cross-platform compatibility"
                ],
                "cons": [
                    "Manual process management",
                    "No automatic restart on failure",
                    "Limited scalability",
                    "Manual dependency management"
                ]
            }
        }
    
    @staticmethod
    def create_custom_template(
        deployment_method: DeploymentMethod,
        meilisearch_host: str,
        meilisearch_api_key: str,
        **kwargs
    ) -> OnPremiseConfig:
        """
        Create a custom configuration template with specific overrides.
        
        Args:
            deployment_method: Deployment method to use
            meilisearch_host: Existing Meilisearch server host
            meilisearch_api_key: API key for Meilisearch
            **kwargs: Additional configuration overrides
            
        Returns:
            OnPremiseConfig with custom configuration
        """
        # Start with appropriate base template
        if deployment_method == DeploymentMethod.DOCKER:
            config = DeploymentTemplates.create_docker_template(
                meilisearch_host, meilisearch_api_key
            )
        elif deployment_method == DeploymentMethod.SYSTEMD:
            config = DeploymentTemplates.create_systemd_template(
                meilisearch_host, meilisearch_api_key
            )
        else:  # STANDALONE
            config = DeploymentTemplates.create_standalone_template(
                meilisearch_host, meilisearch_api_key
            )
        
        # Apply custom overrides
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                # Try to set nested attributes
                for attr_name in ['service_config', 'security_config', 'resource_config', 'monitoring_config']:
                    attr_obj = getattr(config, attr_name)
                    if hasattr(attr_obj, key):
                        setattr(attr_obj, key, value)
                        break
        
        return config


class ConfigurationExporter:
    """Utility class for exporting configurations to various formats."""
    
    @staticmethod
    def to_env_file(config: OnPremiseConfig, file_path: Optional[str] = None) -> str:
        """
        Export configuration as environment file format.
        
        Args:
            config: Configuration to export
            file_path: Optional file path to write to
            
        Returns:
            Environment file content as string
        """
        env_vars = config.get_environment_dict()
        
        lines = [
            "# Thai Tokenizer On-Premise Deployment Configuration",
            f"# Generated for {config.deployment_method.value} deployment",
            f"# Timestamp: {config.model_fields_set}",
            "",
        ]
        
        # Group variables by category
        categories = {
            "Service Configuration": [k for k in env_vars.keys() if "SERVICE" in k],
            "Meilisearch Configuration": [k for k in env_vars.keys() if "MEILISEARCH" in k],
            "Security Configuration": [k for k in env_vars.keys() if any(sec in k for sec in ["ALLOWED", "CORS", "API_KEY", "SSL"])],
            "Resource Configuration": [k for k in env_vars.keys() if any(res in k for res in ["MEMORY", "CPU", "CONCURRENT", "TIMEOUT"])],
            "Monitoring Configuration": [k for k in env_vars.keys() if any(mon in k for mon in ["LOG", "METRICS", "PROMETHEUS"])],
            "Path Configuration": [k for k in env_vars.keys() if "PATH" in k],
            "Other Configuration": [k for k in env_vars.keys() if not any(cat in k for cat in ["SERVICE", "MEILISEARCH", "ALLOWED", "CORS", "API_KEY", "SSL", "MEMORY", "CPU", "CONCURRENT", "TIMEOUT", "LOG", "METRICS", "PROMETHEUS", "PATH"])]
        }
        
        for category, keys in categories.items():
            if keys:
                lines.append(f"# {category}")
                for key in sorted(keys):
                    value = env_vars[key]
                    # Mask sensitive values
                    if any(sensitive in key.lower() for sensitive in ["api_key", "password", "secret"]):
                        display_value = "***MASKED***"
                    else:
                        display_value = value
                    lines.append(f"{key}={display_value}")
                lines.append("")
        
        content = "\n".join(lines)
        
        if file_path:
            Path(file_path).write_text(content, encoding="utf-8")
        
        return content
    
    @staticmethod
    def to_docker_compose(config: OnPremiseConfig, file_path: Optional[str] = None) -> str:
        """
        Export configuration as Docker Compose format.
        
        Args:
            config: Configuration to export
            file_path: Optional file path to write to
            
        Returns:
            Docker Compose content as string
        """
        if config.deployment_method != DeploymentMethod.DOCKER:
            raise ValueError("Docker Compose export only available for Docker deployment method")
        
        env_vars = config.get_environment_dict()
        
        # Create Docker Compose content
        compose_content = f"""version: '3.8'

services:
  thai-tokenizer:
    image: thai-tokenizer:latest
    container_name: {config.service_config.service_name}
    restart: unless-stopped
    ports:
      - "{config.service_config.service_port}:{config.service_config.service_port}"
"""
        
        if config.monitoring_config.enable_prometheus:
            compose_content += f"      - \"{config.monitoring_config.prometheus_port}:{config.monitoring_config.prometheus_port}\"\n"
        
        compose_content += """    environment:
"""
        
        # Add environment variables
        for key, value in sorted(env_vars.items()):
            # Mask sensitive values in the template
            if any(sensitive in key.lower() for sensitive in ["api_key", "password", "secret"]):
                display_value = "${" + key + "}"
            else:
                display_value = value
            compose_content += f"      - {key}={display_value}\n"
        
        compose_content += f"""    volumes:
      - {config.data_path}:/app/data
      - {config.log_path}:/app/logs
      - {config.config_path}:/app/config
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:{config.service_config.service_port}/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          memory: {config.resource_config.memory_limit_mb}M
          cpus: '{config.resource_config.cpu_limit_cores}'
        reservations:
          memory: {config.resource_config.memory_limit_mb // 2}M
          cpus: '{config.resource_config.cpu_limit_cores / 2}'
    networks:
      - thai-tokenizer-network

networks:
  thai-tokenizer-network:
    driver: bridge
"""
        
        if file_path:
            Path(file_path).write_text(compose_content, encoding="utf-8")
        
        return compose_content
    
    @staticmethod
    def to_systemd_unit(config: OnPremiseConfig, file_path: Optional[str] = None) -> str:
        """
        Export configuration as systemd unit file.
        
        Args:
            config: Configuration to export
            file_path: Optional file path to write to
            
        Returns:
            Systemd unit file content as string
        """
        if config.deployment_method != DeploymentMethod.SYSTEMD:
            raise ValueError("Systemd unit export only available for systemd deployment method")
        
        unit_content = f"""[Unit]
Description=Thai Tokenizer Service for Meilisearch Integration
Documentation=https://github.com/your-org/thai-tokenizer
After=network.target
Wants=network.target

[Service]
Type=exec
User={config.service_config.service_user}
Group={config.service_config.service_group}
WorkingDirectory={config.installation_path}
Environment=PYTHONPATH={config.installation_path}
EnvironmentFile={config.config_path}/environment
ExecStart={config.installation_path}/venv/bin/uvicorn src.api.main:app --host {config.service_config.service_host} --port {config.service_config.service_port} --workers {config.service_config.worker_processes}
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier={config.service_config.service_name}

# Security settings
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={config.data_path} {config.log_path} {config.config_path}

# Resource limits
MemoryLimit={config.resource_config.memory_limit_mb}M
CPUQuota={int(config.resource_config.cpu_limit_cores * 100)}%

[Install]
WantedBy=multi-user.target
"""
        
        if file_path:
            Path(file_path).write_text(unit_content, encoding="utf-8")
        
        return unit_content