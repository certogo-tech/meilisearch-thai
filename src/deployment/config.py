"""
On-premise deployment configuration management system.

This module provides comprehensive configuration management for deploying
the Thai Tokenizer service to integrate with existing Meilisearch infrastructure.
"""

import os
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Literal
from enum import Enum
from datetime import datetime

from pydantic import BaseModel, Field, field_validator, ValidationError, ConfigDict, SecretStr
from pydantic_settings import BaseSettings
import httpx

try:
    from src.utils.logging import get_structured_logger
except ImportError:
    # Fallback for when running outside the main application
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class DeploymentMethod(str, Enum):
    """Supported deployment methods."""
    DOCKER = "docker"
    SYSTEMD = "systemd"
    STANDALONE = "standalone"


class SecurityLevel(str, Enum):
    """Security configuration levels."""
    BASIC = "basic"
    STANDARD = "standard"
    HIGH = "high"


class ConnectionStatus(str, Enum):
    """Connection status values."""
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TIMEOUT = "timeout"


class ValidationResult(BaseModel):
    """Result of configuration validation."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class ConnectionResult(BaseModel):
    """Result of connection testing."""
    status: ConnectionStatus
    response_time_ms: Optional[float] = None
    error_message: Optional[str] = None
    meilisearch_version: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)


class MeilisearchConnectionConfig(BaseModel):
    """Configuration for connecting to existing Meilisearch server."""
    
    host: str = Field(
        description="Meilisearch server host URL (e.g., http://localhost:7700)"
    )
    port: int = Field(
        7700,
        ge=1,
        le=65535,
        description="Meilisearch server port"
    )
    api_key: SecretStr = Field(
        description="Meilisearch API key for authentication"
    )
    ssl_enabled: bool = Field(
        False,
        description="Whether to use SSL/TLS for connections"
    )
    ssl_verify: bool = Field(
        True,
        description="Whether to verify SSL certificates"
    )
    timeout_seconds: int = Field(
        30,
        ge=5,
        le=300,
        description="Connection timeout in seconds"
    )
    max_retries: int = Field(
        3,
        ge=0,
        le=10,
        description="Maximum retry attempts for failed connections"
    )
    retry_delay_seconds: float = Field(
        1.0,
        ge=0.1,
        le=10.0,
        description="Delay between retry attempts"
    )
    
    @field_validator('host')
    @classmethod
    def validate_host(cls, v: str) -> str:
        """Validate Meilisearch host URL."""
        if not v:
            raise ValueError("Host cannot be empty")
        
        # Ensure proper URL format
        if not v.startswith(('http://', 'https://')):
            v = f"http://{v}"
        
        return v.rstrip('/')
    
    @property
    def full_url(self) -> str:
        """Get the full Meilisearch URL."""
        if ':' in self.host and not self.host.startswith(('http://', 'https://')):
            return f"http://{self.host}"
        elif self.port != 7700 and not any(f":{self.port}" in self.host for _ in [None]):
            return f"{self.host}:{self.port}"
        return self.host


class ServiceConfig(BaseModel):
    """Configuration for the Thai Tokenizer service."""
    
    service_name: str = Field(
        "thai-tokenizer",
        description="Name of the service"
    )
    service_port: int = Field(
        8000,
        ge=1024,
        le=65535,
        description="Port for the Thai Tokenizer service"
    )
    service_host: str = Field(
        "0.0.0.0",
        description="Host interface to bind the service"
    )
    worker_processes: int = Field(
        4,
        ge=1,
        le=32,
        description="Number of worker processes"
    )
    service_user: str = Field(
        "thai-tokenizer",
        description="System user to run the service"
    )
    service_group: str = Field(
        "thai-tokenizer",
        description="System group for the service"
    )
    
    @field_validator('service_name')
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        """Validate service name format."""
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError("Service name must contain only alphanumeric characters, hyphens, and underscores")
        return v


class SecurityConfig(BaseModel):
    """Security configuration for on-premise deployment."""
    
    security_level: SecurityLevel = Field(
        SecurityLevel.STANDARD,
        description="Overall security level"
    )
    allowed_hosts: List[str] = Field(
        default_factory=lambda: ["*"],
        description="List of allowed host headers"
    )
    cors_origins: List[str] = Field(
        default_factory=lambda: ["*"],
        description="List of allowed CORS origins"
    )
    api_key_required: bool = Field(
        False,
        description="Whether API key authentication is required"
    )
    api_key: Optional[SecretStr] = Field(
        None,
        description="API key for service authentication"
    )
    enable_https: bool = Field(
        False,
        description="Whether to enable HTTPS"
    )
    ssl_cert_path: Optional[str] = Field(
        None,
        description="Path to SSL certificate file"
    )
    ssl_key_path: Optional[str] = Field(
        None,
        description="Path to SSL private key file"
    )
    firewall_rules: List[str] = Field(
        default_factory=list,
        description="Firewall rules to apply"
    )
    
    @field_validator('allowed_hosts', 'cors_origins')
    @classmethod
    def validate_host_lists(cls, v: List[str]) -> List[str]:
        """Validate host and origin lists."""
        if not v:
            return ["*"]
        return [host.strip() for host in v if host.strip()]


class ResourceConfig(BaseModel):
    """Resource management configuration."""
    
    memory_limit_mb: int = Field(
        512,
        ge=128,
        le=8192,
        description="Memory limit in megabytes"
    )
    cpu_limit_cores: float = Field(
        1.0,
        ge=0.1,
        le=16.0,
        description="CPU limit in cores"
    )
    max_concurrent_requests: int = Field(
        100,
        ge=1,
        le=1000,
        description="Maximum concurrent requests"
    )
    request_timeout_seconds: int = Field(
        30,
        ge=5,
        le=300,
        description="Request timeout in seconds"
    )
    enable_metrics: bool = Field(
        True,
        description="Whether to enable metrics collection"
    )
    metrics_port: int = Field(
        9090,
        ge=1024,
        le=65535,
        description="Port for metrics endpoint"
    )


class MonitoringConfig(BaseModel):
    """Monitoring and health check configuration."""
    
    enable_health_checks: bool = Field(
        True,
        description="Whether to enable health checks"
    )
    health_check_interval_seconds: int = Field(
        30,
        ge=5,
        le=300,
        description="Health check interval in seconds"
    )
    enable_logging: bool = Field(
        True,
        description="Whether to enable structured logging"
    )
    log_level: str = Field(
        "INFO",
        description="Logging level"
    )
    log_file_path: Optional[str] = Field(
        None,
        description="Path to log file (if file logging enabled)"
    )
    enable_prometheus: bool = Field(
        False,
        description="Whether to enable Prometheus metrics"
    )
    prometheus_port: int = Field(
        9090,
        ge=1024,
        le=65535,
        description="Port for Prometheus metrics"
    )


class OnPremiseConfig(BaseModel):
    """
    Comprehensive configuration for on-premise Thai Tokenizer deployment.
    
    This model provides validation and management for all aspects of deploying
    the Thai Tokenizer service to integrate with existing Meilisearch infrastructure.
    """
    
    # Deployment method
    deployment_method: DeploymentMethod = Field(
        description="Deployment method to use"
    )
    
    # Core configurations
    meilisearch_config: MeilisearchConnectionConfig = Field(
        description="Configuration for existing Meilisearch connection"
    )
    service_config: ServiceConfig = Field(
        default_factory=ServiceConfig,
        description="Thai Tokenizer service configuration"
    )
    security_config: SecurityConfig = Field(
        default_factory=SecurityConfig,
        description="Security configuration"
    )
    resource_config: ResourceConfig = Field(
        default_factory=ResourceConfig,
        description="Resource management configuration"
    )
    monitoring_config: MonitoringConfig = Field(
        default_factory=MonitoringConfig,
        description="Monitoring and health check configuration"
    )
    
    # Deployment-specific settings
    installation_path: str = Field(
        "/opt/thai-tokenizer",
        description="Installation directory path"
    )
    data_path: str = Field(
        "/var/lib/thai-tokenizer",
        description="Data directory path"
    )
    log_path: str = Field(
        "/var/log/thai-tokenizer",
        description="Log directory path"
    )
    config_path: str = Field(
        "/etc/thai-tokenizer",
        description="Configuration directory path"
    )
    
    # Environment variables
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Additional environment variables"
    )
    
    model_config = ConfigDict(
        validate_assignment=True,
        extra="forbid"
    )
    
    def validate_paths(self) -> ValidationResult:
        """Validate all configured paths."""
        result = ValidationResult(valid=True)
        
        paths_to_check = [
            ("installation_path", self.installation_path),
            ("data_path", self.data_path),
            ("log_path", self.log_path),
            ("config_path", self.config_path),
        ]
        
        for path_name, path_value in paths_to_check:
            path_obj = Path(path_value)
            
            # Check if parent directory exists or can be created
            try:
                path_obj.parent.mkdir(parents=True, exist_ok=True)
            except PermissionError:
                result.valid = False
                result.errors.append(f"Cannot create parent directory for {path_name}: {path_value}")
            except Exception as e:
                result.warnings.append(f"Warning for {path_name} ({path_value}): {e}")
        
        return result
    
    def get_environment_dict(self) -> Dict[str, str]:
        """Get all environment variables for deployment."""
        env_vars = {
            # Service configuration
            "THAI_TOKENIZER_SERVICE_NAME": self.service_config.service_name,
            "THAI_TOKENIZER_SERVICE_PORT": str(self.service_config.service_port),
            "THAI_TOKENIZER_SERVICE_HOST": self.service_config.service_host,
            "THAI_TOKENIZER_WORKER_PROCESSES": str(self.service_config.worker_processes),
            
            # Meilisearch configuration
            "THAI_TOKENIZER_MEILISEARCH_HOST": self.meilisearch_config.full_url,
            "THAI_TOKENIZER_MEILISEARCH_API_KEY": self.meilisearch_config.api_key.get_secret_value(),
            "THAI_TOKENIZER_MEILISEARCH_TIMEOUT": str(self.meilisearch_config.timeout_seconds),
            "THAI_TOKENIZER_MEILISEARCH_MAX_RETRIES": str(self.meilisearch_config.max_retries),
            "THAI_TOKENIZER_MEILISEARCH_SSL_VERIFY": str(self.meilisearch_config.ssl_verify).lower(),
            
            # Security configuration
            "THAI_TOKENIZER_ALLOWED_HOSTS": ",".join(self.security_config.allowed_hosts),
            "THAI_TOKENIZER_CORS_ORIGINS": ",".join(self.security_config.cors_origins),
            "THAI_TOKENIZER_API_KEY_REQUIRED": str(self.security_config.api_key_required).lower(),
            
            # Resource configuration
            "THAI_TOKENIZER_MEMORY_LIMIT_MB": str(self.resource_config.memory_limit_mb),
            "THAI_TOKENIZER_CPU_LIMIT_CORES": str(self.resource_config.cpu_limit_cores),
            "THAI_TOKENIZER_MAX_CONCURRENT_REQUESTS": str(self.resource_config.max_concurrent_requests),
            "THAI_TOKENIZER_REQUEST_TIMEOUT": str(self.resource_config.request_timeout_seconds),
            
            # Monitoring configuration
            "THAI_TOKENIZER_LOG_LEVEL": self.monitoring_config.log_level,
            "THAI_TOKENIZER_ENABLE_METRICS": str(self.resource_config.enable_metrics).lower(),
            "THAI_TOKENIZER_METRICS_PORT": str(self.resource_config.metrics_port),
            
            # Paths
            "THAI_TOKENIZER_INSTALLATION_PATH": self.installation_path,
            "THAI_TOKENIZER_DATA_PATH": self.data_path,
            "THAI_TOKENIZER_LOG_PATH": self.log_path,
            "THAI_TOKENIZER_CONFIG_PATH": self.config_path,
        }
        
        # Add optional security settings
        if self.security_config.api_key:
            env_vars["THAI_TOKENIZER_API_KEY"] = self.security_config.api_key.get_secret_value()
        
        if self.security_config.ssl_cert_path:
            env_vars["THAI_TOKENIZER_SSL_CERT_PATH"] = self.security_config.ssl_cert_path
        
        if self.security_config.ssl_key_path:
            env_vars["THAI_TOKENIZER_SSL_KEY_PATH"] = self.security_config.ssl_key_path
        
        # Add custom environment variables
        env_vars.update(self.environment_variables)
        
        return env_vars


class MeilisearchConnectionTester:
    """Utility class for testing Meilisearch connections."""
    
    def __init__(self, config: MeilisearchConnectionConfig):
        """Initialize with Meilisearch configuration."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.MeilisearchConnectionTester")
    
    async def test_connection(self) -> ConnectionResult:
        """
        Test connection to Meilisearch server.
        
        Returns:
            ConnectionResult with status and details
        """
        start_time = datetime.now()
        
        try:
            timeout = httpx.Timeout(self.config.timeout_seconds)
            headers = {}
            
            # Add API key if provided
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key.get_secret_value()}"
            
            # Configure SSL verification
            verify_ssl = self.config.ssl_verify if self.config.ssl_enabled else True
            
            async with httpx.AsyncClient(
                timeout=timeout,
                verify=verify_ssl,
                headers=headers
            ) as client:
                # Test basic connectivity
                response = await client.get(f"{self.config.full_url}/health")
                
                response_time = (datetime.now() - start_time).total_seconds() * 1000
                
                if response.status_code == 200:
                    # Try to get version information
                    version_info = None
                    try:
                        version_response = await client.get(f"{self.config.full_url}/version")
                        if version_response.status_code == 200:
                            version_data = version_response.json()
                            version_info = version_data.get("pkgVersion", "unknown")
                    except Exception:
                        pass  # Version info is optional
                    
                    self.logger.info(
                        f"Meilisearch connection successful to {self.config.full_url} "
                        f"(v{version_info}, {response_time:.2f}ms)"
                    )
                    
                    return ConnectionResult(
                        status=ConnectionStatus.CONNECTED,
                        response_time_ms=response_time,
                        meilisearch_version=version_info
                    )
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    self.logger.warning(
                        f"Meilisearch connection failed to {self.config.full_url}: {error_msg}"
                    )
                    
                    return ConnectionResult(
                        status=ConnectionStatus.ERROR,
                        response_time_ms=response_time,
                        error_message=error_msg
                    )
        
        except (httpx.TimeoutException, asyncio.TimeoutError):
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = f"Connection timeout after {self.config.timeout_seconds}s"
            
            self.logger.warning(
                f"Meilisearch connection timeout to {self.config.full_url} after {self.config.timeout_seconds}s"
            )
            
            return ConnectionResult(
                status=ConnectionStatus.TIMEOUT,
                response_time_ms=response_time,
                error_message=error_msg
            )
        
        except Exception as e:
            response_time = (datetime.now() - start_time).total_seconds() * 1000
            error_msg = str(e)
            
            self.logger.error(
                f"Meilisearch connection error to {self.config.full_url}: {error_msg}"
            )
            
            return ConnectionResult(
                status=ConnectionStatus.ERROR,
                response_time_ms=response_time,
                error_message=error_msg
            )
    
    async def test_connection_with_retries(self) -> ConnectionResult:
        """
        Test connection with retry logic.
        
        Returns:
            ConnectionResult from the final attempt
        """
        last_result = None
        
        for attempt in range(self.config.max_retries + 1):
            if attempt > 0:
                self.logger.info(
                    f"Retrying Meilisearch connection (attempt {attempt}/{self.config.max_retries})"
                )
                await asyncio.sleep(self.config.retry_delay_seconds)
            
            result = await self.test_connection()
            last_result = result
            
            if result.status == ConnectionStatus.CONNECTED:
                return result
        
        return last_result or ConnectionResult(
            status=ConnectionStatus.ERROR,
            error_message="All connection attempts failed"
        )
    
    async def validate_api_access(self) -> ValidationResult:
        """
        Validate API access and permissions.
        
        Returns:
            ValidationResult with detailed validation information
        """
        validation = ValidationResult(valid=True)
        
        try:
            # First test basic connection
            connection_result = await self.test_connection()
            
            if connection_result.status != ConnectionStatus.CONNECTED:
                validation.valid = False
                validation.errors.append(f"Cannot connect to Meilisearch: {connection_result.error_message}")
                return validation
            
            # Test API key permissions
            timeout = httpx.Timeout(self.config.timeout_seconds)
            headers = {}
            
            if self.config.api_key:
                headers["Authorization"] = f"Bearer {self.config.api_key.get_secret_value()}"
            
            async with httpx.AsyncClient(
                timeout=timeout,
                verify=self.config.ssl_verify if self.config.ssl_enabled else True,
                headers=headers
            ) as client:
                # Test index listing (requires read permissions)
                try:
                    response = await client.get(f"{self.config.full_url}/indexes")
                    if response.status_code == 403:
                        validation.errors.append("API key does not have sufficient permissions to list indexes")
                        validation.valid = False
                    elif response.status_code != 200:
                        validation.warnings.append(f"Unexpected response when listing indexes: {response.status_code}")
                except Exception as e:
                    validation.warnings.append(f"Could not test index permissions: {e}")
                
                # Test stats endpoint (basic read access)
                try:
                    response = await client.get(f"{self.config.full_url}/stats")
                    if response.status_code == 403:
                        validation.errors.append("API key does not have permissions to access stats")
                        validation.valid = False
                    elif response.status_code == 200:
                        validation.warnings.append("API key has stats access (good for monitoring)")
                except Exception as e:
                    validation.warnings.append(f"Could not test stats permissions: {e}")
        
        except Exception as e:
            validation.valid = False
            validation.errors.append(f"API validation failed: {e}")
        
        return validation


class ConfigurationValidator:
    """Comprehensive configuration validator for on-premise deployment."""
    
    def __init__(self, config: OnPremiseConfig):
        """Initialize with configuration to validate."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.ConfigurationValidator")
    
    async def validate_full_configuration(self) -> ValidationResult:
        """
        Perform comprehensive validation of all configuration components.
        
        Returns:
            ValidationResult with detailed validation information
        """
        result = ValidationResult(valid=True)
        
        # Validate paths
        path_validation = self.config.validate_paths()
        result.errors.extend(path_validation.errors)
        result.warnings.extend(path_validation.warnings)
        if not path_validation.valid:
            result.valid = False
        
        # Validate Meilisearch connection
        try:
            tester = MeilisearchConnectionTester(self.config.meilisearch_config)
            connection_result = await tester.test_connection_with_retries()
            
            if connection_result.status != ConnectionStatus.CONNECTED:
                result.valid = False
                result.errors.append(f"Meilisearch connection failed: {connection_result.error_message}")
            else:
                result.warnings.append(f"Meilisearch connection successful (v{connection_result.meilisearch_version})")
                
                # Validate API permissions
                api_validation = await tester.validate_api_access()
                result.errors.extend(api_validation.errors)
                result.warnings.extend(api_validation.warnings)
                if not api_validation.valid:
                    result.valid = False
        
        except Exception as e:
            result.valid = False
            result.errors.append(f"Meilisearch validation error: {e}")
        
        # Validate port availability
        port_validation = self._validate_ports()
        result.errors.extend(port_validation.errors)
        result.warnings.extend(port_validation.warnings)
        if not port_validation.valid:
            result.valid = False
        
        # Validate security configuration
        security_validation = self._validate_security()
        result.errors.extend(security_validation.errors)
        result.warnings.extend(security_validation.warnings)
        if not security_validation.valid:
            result.valid = False
        
        # Validate resource configuration
        resource_validation = self._validate_resources()
        result.errors.extend(resource_validation.errors)
        result.warnings.extend(resource_validation.warnings)
        if not resource_validation.valid:
            result.valid = False
        
        self.logger.info(
            f"Configuration validation completed: valid={result.valid}, "
            f"errors={len(result.errors)}, warnings={len(result.warnings)}"
        )
        
        return result
    
    def _validate_ports(self) -> ValidationResult:
        """Validate port configuration and availability."""
        result = ValidationResult(valid=True)
        
        ports_to_check = [
            ("service_port", self.config.service_config.service_port),
            ("metrics_port", self.config.resource_config.metrics_port),
        ]
        
        if self.config.monitoring_config.enable_prometheus:
            ports_to_check.append(("prometheus_port", self.config.monitoring_config.prometheus_port))
        
        used_ports = set()
        for port_name, port_number in ports_to_check:
            if port_number in used_ports:
                result.valid = False
                result.errors.append(f"Port conflict: {port_name} ({port_number}) is already used")
            else:
                used_ports.add(port_number)
            
            # Check if port is in valid range
            if port_number < 1024:
                result.warnings.append(f"Port {port_name} ({port_number}) is in privileged range (<1024)")
        
        return result
    
    def _validate_security(self) -> ValidationResult:
        """Validate security configuration."""
        result = ValidationResult(valid=True)
        
        # Check SSL configuration
        if self.config.security_config.enable_https:
            if not self.config.security_config.ssl_cert_path:
                result.valid = False
                result.errors.append("HTTPS enabled but no SSL certificate path provided")
            
            if not self.config.security_config.ssl_key_path:
                result.valid = False
                result.errors.append("HTTPS enabled but no SSL key path provided")
            
            # Check if SSL files exist
            if self.config.security_config.ssl_cert_path:
                cert_path = Path(self.config.security_config.ssl_cert_path)
                if not cert_path.exists():
                    result.warnings.append(f"SSL certificate file not found: {cert_path}")
            
            if self.config.security_config.ssl_key_path:
                key_path = Path(self.config.security_config.ssl_key_path)
                if not key_path.exists():
                    result.warnings.append(f"SSL key file not found: {key_path}")
        
        # Check API key configuration
        if self.config.security_config.api_key_required and not self.config.security_config.api_key:
            result.valid = False
            result.errors.append("API key authentication required but no API key provided")
        
        # Check security level consistency
        if self.config.security_config.security_level == SecurityLevel.HIGH:
            if not self.config.security_config.api_key_required:
                result.warnings.append("High security level but API key authentication not required")
            
            if "*" in self.config.security_config.allowed_hosts:
                result.warnings.append("High security level but all hosts are allowed")
            
            if "*" in self.config.security_config.cors_origins:
                result.warnings.append("High security level but all CORS origins are allowed")
        
        return result
    
    def _validate_resources(self) -> ValidationResult:
        """Validate resource configuration."""
        result = ValidationResult(valid=True)
        
        # Check memory limits
        if self.config.resource_config.memory_limit_mb < 256:
            result.warnings.append("Memory limit is quite low (<256MB), may affect performance")
        
        # Check CPU limits
        if self.config.resource_config.cpu_limit_cores < 0.5:
            result.warnings.append("CPU limit is quite low (<0.5 cores), may affect performance")
        
        # Check worker process configuration
        if self.config.service_config.worker_processes > self.config.resource_config.cpu_limit_cores * 2:
            result.warnings.append("Worker processes exceed 2x CPU limit, may cause resource contention")
        
        # Check concurrent request limits
        memory_per_request_mb = 2  # Estimated memory per request
        estimated_memory_usage = self.config.resource_config.max_concurrent_requests * memory_per_request_mb
        
        if estimated_memory_usage > self.config.resource_config.memory_limit_mb * 0.8:
            result.warnings.append(
                f"High concurrent requests ({self.config.resource_config.max_concurrent_requests}) "
                f"may exceed memory limit ({self.config.resource_config.memory_limit_mb}MB)"
            )
        
        return result