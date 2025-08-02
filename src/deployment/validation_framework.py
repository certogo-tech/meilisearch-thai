"""
Deployment validation and testing framework for Thai Tokenizer on-premise deployment.

This module provides comprehensive validation and testing capabilities for
deployment validation including system requirements, Meilisearch connectivity,
Thai tokenization functionality, and performance benchmarking.
"""

import asyncio
import logging
import os
import platform
import psutil
import shutil
import socket
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import json

import httpx
import requests
from pydantic import BaseModel, Field

try:
    from src.deployment.config import (
        OnPremiseConfig, ValidationResult, MeilisearchConnectionTester,
        ConnectionResult, ConnectionStatus
    )
    from src.utils.logging import get_structured_logger
except ImportError:
    # Fallback for when running outside the main application
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class SystemRequirement(BaseModel):
    """System requirement specification."""
    name: str = Field(description="Requirement name")
    description: str = Field(description="Requirement description")
    required: bool = Field(default=True, description="Whether requirement is mandatory")
    minimum_version: Optional[str] = Field(default=None, description="Minimum version required")
    check_command: Optional[str] = Field(default=None, description="Command to check requirement")
    validation_function: Optional[str] = Field(default=None, description="Custom validation function")


class RequirementCheckResult(BaseModel):
    """Result of a system requirement check."""
    requirement: SystemRequirement = Field(description="The requirement that was checked")
    satisfied: bool = Field(description="Whether requirement is satisfied")
    current_version: Optional[str] = Field(default=None, description="Current version found")
    error_message: Optional[str] = Field(default=None, description="Error message if check failed")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class PerformanceBenchmark(BaseModel):
    """Performance benchmark specification."""
    name: str = Field(description="Benchmark name")
    description: str = Field(description="Benchmark description")
    target_value: float = Field(description="Target performance value")
    unit: str = Field(description="Performance unit (ms, req/s, etc.)")
    tolerance_percent: float = Field(default=10.0, description="Acceptable tolerance percentage")


class BenchmarkResult(BaseModel):
    """Result of a performance benchmark."""
    benchmark: PerformanceBenchmark = Field(description="The benchmark that was run")
    measured_value: float = Field(description="Measured performance value")
    passed: bool = Field(description="Whether benchmark passed")
    deviation_percent: float = Field(description="Deviation from target as percentage")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional benchmark details")


class ThaiTokenizationTest(BaseModel):
    """Thai tokenization test case."""
    name: str = Field(description="Test case name")
    input_text: str = Field(description="Thai text to tokenize")
    expected_tokens: Optional[List[str]] = Field(default=None, description="Expected token output")
    test_type: str = Field(default="accuracy", description="Type of test (accuracy, performance, etc.)")
    timeout_seconds: float = Field(default=5.0, description="Test timeout")


class TokenizationTestResult(BaseModel):
    """Result of Thai tokenization test."""
    test: ThaiTokenizationTest = Field(description="The test that was run")
    success: bool = Field(description="Whether test succeeded")
    actual_tokens: Optional[List[str]] = Field(default=None, description="Actual tokens produced")
    response_time_ms: float = Field(description="Response time in milliseconds")
    error_message: Optional[str] = Field(default=None, description="Error message if test failed")
    accuracy_score: Optional[float] = Field(default=None, description="Accuracy score if applicable")


class SystemRequirementsValidator:
    """Validates system requirements for deployment."""
    
    def __init__(self):
        self.logger = get_structured_logger(f"{__name__}.SystemRequirementsValidator")
        self._define_requirements()
    
    def _define_requirements(self):
        """Define system requirements for Thai Tokenizer deployment."""
        self.requirements = [
            SystemRequirement(
                name="python_version",
                description="Python 3.12 or higher",
                required=True,
                minimum_version="3.12.0",
                validation_function="check_python_version"
            ),
            SystemRequirement(
                name="uv_package_manager",
                description="uv package manager",
                required=True,
                check_command="uv --version",
                validation_function="check_uv_availability"
            ),
            SystemRequirement(
                name="available_memory",
                description="At least 1GB available memory",
                required=True,
                validation_function="check_memory_requirements"
            ),
            SystemRequirement(
                name="available_disk_space",
                description="At least 2GB available disk space",
                required=True,
                validation_function="check_disk_space_requirements"
            ),
            SystemRequirement(
                name="network_connectivity",
                description="Internet connectivity for package installation",
                required=True,
                validation_function="check_network_connectivity"
            ),
            SystemRequirement(
                name="port_availability",
                description="Required ports are available",
                required=True,
                validation_function="check_port_availability"
            ),
            SystemRequirement(
                name="file_permissions",
                description="Appropriate file system permissions",
                required=True,
                validation_function="check_file_permissions"
            ),
        ]
        
        # Add deployment method specific requirements
        self._add_docker_requirements()
        self._add_systemd_requirements()
    
    def _add_docker_requirements(self):
        """Add Docker-specific requirements."""
        docker_requirements = [
            SystemRequirement(
                name="docker_engine",
                description="Docker Engine",
                required=False,  # Only required for Docker deployment
                check_command="docker --version",
                validation_function="check_docker_availability"
            ),
            SystemRequirement(
                name="docker_compose",
                description="Docker Compose",
                required=False,  # Only required for Docker deployment
                check_command="docker compose version",
                validation_function="check_docker_compose_availability"
            ),
            SystemRequirement(
                name="docker_daemon",
                description="Docker daemon running",
                required=False,  # Only required for Docker deployment
                validation_function="check_docker_daemon"
            ),
        ]
        self.requirements.extend(docker_requirements)
    
    def _add_systemd_requirements(self):
        """Add systemd-specific requirements."""
        systemd_requirements = [
            SystemRequirement(
                name="systemd_available",
                description="systemd service manager",
                required=False,  # Only required for systemd deployment
                check_command="systemctl --version",
                validation_function="check_systemd_availability"
            ),
            SystemRequirement(
                name="root_privileges",
                description="Root privileges for systemd deployment",
                required=False,  # Only required for systemd deployment
                validation_function="check_root_privileges"
            ),
        ]
        self.requirements.extend(systemd_requirements)
    
    async def validate_all_requirements(self, config: OnPremiseConfig) -> List[RequirementCheckResult]:
        """
        Validate all system requirements.
        
        Args:
            config: Deployment configuration
            
        Returns:
            List of requirement check results
        """
        self.logger.info("Starting system requirements validation")
        results = []
        
        for requirement in self.requirements:
            # Skip deployment-method-specific requirements if not applicable
            if not self._is_requirement_applicable(requirement, config):
                continue
            
            try:
                result = await self._check_requirement(requirement, config)
                results.append(result)
                
                if result.satisfied:
                    self.logger.info(f"✓ {requirement.name}: {requirement.description}")
                else:
                    level = "ERROR" if requirement.required else "WARNING"
                    self.logger.log(
                        logging.ERROR if requirement.required else logging.WARNING,
                        f"✗ {requirement.name}: {result.error_message}"
                    )
                    
            except Exception as e:
                self.logger.error(f"Failed to check requirement {requirement.name}: {e}")
                results.append(RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message=f"Check failed: {e}"
                ))
        
        # Summary
        satisfied_count = sum(1 for r in results if r.satisfied)
        total_count = len(results)
        required_count = sum(1 for r in results if r.requirement.required)
        required_satisfied = sum(1 for r in results if r.requirement.required and r.satisfied)
        
        self.logger.info(
            f"Requirements validation completed: {satisfied_count}/{total_count} satisfied, "
            f"{required_satisfied}/{required_count} required satisfied"
        )
        
        return results
    
    def _is_requirement_applicable(self, requirement: SystemRequirement, config: OnPremiseConfig) -> bool:
        """Check if requirement is applicable for the deployment method."""
        docker_requirements = ["docker_engine", "docker_compose", "docker_daemon"]
        systemd_requirements = ["systemd_available", "root_privileges"]
        
        if requirement.name in docker_requirements:
            return config.deployment_method.value == "docker"
        elif requirement.name in systemd_requirements:
            return config.deployment_method.value == "systemd"
        
        return True
    
    async def _check_requirement(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check a single system requirement."""
        if requirement.validation_function:
            # Use custom validation function
            validation_func = getattr(self, requirement.validation_function, None)
            if validation_func:
                return await validation_func(requirement, config)
        
        if requirement.check_command:
            # Use command-based check
            return await self._check_command_requirement(requirement)
        
        # Default: requirement not checkable
        return RequirementCheckResult(
            requirement=requirement,
            satisfied=False,
            error_message="No validation method available"
        )
    
    async def _check_command_requirement(self, requirement: SystemRequirement) -> RequirementCheckResult:
        """Check requirement using command execution."""
        try:
            process = subprocess.run(
                requirement.check_command.split(),
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if process.returncode == 0:
                version_output = process.stdout.strip()
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    current_version=version_output,
                    details={"stdout": process.stdout, "stderr": process.stderr}
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message=f"Command failed: {process.stderr}",
                    details={"return_code": process.returncode, "stderr": process.stderr}
                )
                
        except subprocess.TimeoutExpired:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message="Command timeout"
            )
        except FileNotFoundError:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message="Command not found"
            )
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Check failed: {e}"
            )
    
    # Custom validation functions
    
    async def check_python_version(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check Python version requirement."""
        try:
            current_version = sys.version_info
            current_version_str = f"{current_version.major}.{current_version.minor}.{current_version.micro}"
            
            if requirement.minimum_version:
                min_parts = [int(x) for x in requirement.minimum_version.split('.')]
                min_version = tuple(min_parts)
                
                if current_version[:len(min_version)] >= min_version:
                    return RequirementCheckResult(
                        requirement=requirement,
                        satisfied=True,
                        current_version=current_version_str,
                        details={"version_info": current_version}
                    )
                else:
                    return RequirementCheckResult(
                        requirement=requirement,
                        satisfied=False,
                        current_version=current_version_str,
                        error_message=f"Python {requirement.minimum_version}+ required, found {current_version_str}"
                    )
            
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=True,
                current_version=current_version_str
            )
            
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check Python version: {e}"
            )
    
    async def check_uv_availability(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check uv package manager availability."""
        try:
            process = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if process.returncode == 0:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    current_version=process.stdout.strip(),
                    details={"version_output": process.stdout}
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message="uv package manager not found or not working"
                )
                
        except FileNotFoundError:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message="uv package manager not installed"
            )
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check uv: {e}"
            )
    
    async def check_memory_requirements(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check available memory requirements."""
        try:
            memory = psutil.virtual_memory()
            available_gb = memory.available / (1024**3)
            required_gb = 1.0  # Minimum 1GB
            
            if available_gb >= required_gb:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    details={
                        "available_gb": available_gb,
                        "required_gb": required_gb,
                        "total_gb": memory.total / (1024**3)
                    }
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message=f"Insufficient memory: {available_gb:.1f}GB available, {required_gb}GB required",
                    details={"available_gb": available_gb, "required_gb": required_gb}
                )
                
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check memory: {e}"
            )
    
    async def check_disk_space_requirements(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check available disk space requirements."""
        try:
            # Check disk space at installation path
            installation_path = Path(config.installation_path)
            installation_path.parent.mkdir(parents=True, exist_ok=True)
            
            disk_usage = shutil.disk_usage(installation_path.parent)
            available_gb = disk_usage.free / (1024**3)
            required_gb = 2.0  # Minimum 2GB
            
            if available_gb >= required_gb:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    details={
                        "available_gb": available_gb,
                        "required_gb": required_gb,
                        "path": str(installation_path.parent)
                    }
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message=f"Insufficient disk space: {available_gb:.1f}GB available, {required_gb}GB required",
                    details={"available_gb": available_gb, "required_gb": required_gb}
                )
                
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check disk space: {e}"
            )
    
    async def check_network_connectivity(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check network connectivity."""
        try:
            # Test connectivity to common package repositories
            test_urls = [
                "https://pypi.org",
                "https://github.com",
                "https://files.pythonhosted.org"
            ]
            
            successful_connections = 0
            connection_details = {}
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                for url in test_urls:
                    try:
                        response = await client.get(url)
                        if response.status_code < 400:
                            successful_connections += 1
                            connection_details[url] = "success"
                        else:
                            connection_details[url] = f"http_{response.status_code}"
                    except Exception as e:
                        connection_details[url] = f"error: {e}"
            
            if successful_connections > 0:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    details={
                        "successful_connections": successful_connections,
                        "total_tested": len(test_urls),
                        "connection_details": connection_details
                    }
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message="No network connectivity to package repositories",
                    details={"connection_details": connection_details}
                )
                
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check network connectivity: {e}"
            )
    
    async def check_port_availability(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check port availability."""
        try:
            ports_to_check = [
                config.service_config.service_port,
                config.resource_config.metrics_port,
            ]
            
            if config.monitoring_config.enable_prometheus:
                ports_to_check.append(config.monitoring_config.prometheus_port)
            
            unavailable_ports = []
            port_details = {}
            
            for port in ports_to_check:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(1)
                        result = s.connect_ex(('localhost', port))
                        if result == 0:
                            unavailable_ports.append(port)
                            port_details[port] = "in_use"
                        else:
                            port_details[port] = "available"
                except Exception as e:
                    port_details[port] = f"check_error: {e}"
            
            if not unavailable_ports:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    details={"port_details": port_details}
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message=f"Ports in use: {unavailable_ports}",
                    details={"unavailable_ports": unavailable_ports, "port_details": port_details}
                )
                
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check port availability: {e}"
            )
    
    async def check_file_permissions(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check file system permissions."""
        try:
            paths_to_check = [
                config.installation_path,
                config.data_path,
                config.log_path,
                config.config_path,
            ]
            
            permission_issues = []
            permission_details = {}
            
            for path_str in paths_to_check:
                path = Path(path_str)
                try:
                    # Try to create directory
                    path.mkdir(parents=True, exist_ok=True)
                    
                    # Try to write a test file
                    test_file = path / "permission_test.tmp"
                    test_file.write_text("test")
                    test_file.unlink()
                    
                    permission_details[path_str] = "writable"
                    
                except PermissionError:
                    permission_issues.append(path_str)
                    permission_details[path_str] = "permission_denied"
                except Exception as e:
                    permission_issues.append(path_str)
                    permission_details[path_str] = f"error: {e}"
            
            if not permission_issues:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    details={"permission_details": permission_details}
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message=f"Permission issues with paths: {permission_issues}",
                    details={"permission_issues": permission_issues, "permission_details": permission_details}
                )
                
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check file permissions: {e}"
            )
    
    async def check_docker_availability(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check Docker availability."""
        return await self._check_command_requirement(requirement)
    
    async def check_docker_compose_availability(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check Docker Compose availability."""
        return await self._check_command_requirement(requirement)
    
    async def check_docker_daemon(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check Docker daemon status."""
        try:
            process = subprocess.run(
                ["docker", "info"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if process.returncode == 0:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    details={"docker_info": process.stdout}
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message="Docker daemon not running or not accessible"
                )
                
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check Docker daemon: {e}"
            )
    
    async def check_systemd_availability(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check systemd availability."""
        return await self._check_command_requirement(requirement)
    
    async def check_root_privileges(self, requirement: SystemRequirement, config: OnPremiseConfig) -> RequirementCheckResult:
        """Check root privileges."""
        try:
            if os.geteuid() == 0:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=True,
                    details={"user_id": os.geteuid()}
                )
            else:
                return RequirementCheckResult(
                    requirement=requirement,
                    satisfied=False,
                    error_message="Root privileges required for systemd deployment",
                    details={"user_id": os.geteuid()}
                )
                
        except Exception as e:
            return RequirementCheckResult(
                requirement=requirement,
                satisfied=False,
                error_message=f"Failed to check privileges: {e}"
            )


class MeilisearchConnectivityTester:
    """Tests Meilisearch connectivity and functionality."""
    
    def __init__(self, config: OnPremiseConfig):
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.MeilisearchConnectivityTester")
        self.connection_tester = MeilisearchConnectionTester(config.meilisearch_config)
    
    async def test_basic_connectivity(self) -> ValidationResult:
        """Test basic Meilisearch connectivity."""
        self.logger.info("Testing Meilisearch basic connectivity")
        
        try:
            result = await self.connection_tester.test_connection_with_retries()
            
            if result.status == ConnectionStatus.CONNECTED:
                return ValidationResult(
                    valid=True,
                    warnings=[f"Meilisearch connected successfully (v{result.meilisearch_version}, {result.response_time_ms:.2f}ms)"]
                )
            else:
                return ValidationResult(
                    valid=False,
                    errors=[f"Meilisearch connection failed: {result.error_message}"]
                )
                
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Meilisearch connectivity test failed: {e}"]
            )
    
    async def test_api_permissions(self) -> ValidationResult:
        """Test Meilisearch API permissions."""
        self.logger.info("Testing Meilisearch API permissions")
        
        try:
            result = await self.connection_tester.validate_api_access()
            return result
            
        except Exception as e:
            return ValidationResult(
                valid=False,
                errors=[f"Meilisearch API permissions test failed: {e}"]
            )
    
    async def test_index_operations(self) -> ValidationResult:
        """Test basic index operations."""
        self.logger.info("Testing Meilisearch index operations")
        
        result = ValidationResult(valid=True)
        
        try:
            timeout = httpx.Timeout(self.config.meilisearch_config.timeout_seconds)
            headers = {}
            
            if self.config.meilisearch_config.api_key:
                headers["Authorization"] = f"Bearer {self.config.meilisearch_config.api_key.get_secret_value()}"
            
            async with httpx.AsyncClient(
                timeout=timeout,
                verify=self.config.meilisearch_config.ssl_verify,
                headers=headers
            ) as client:
                base_url = self.config.meilisearch_config.full_url
                
                # Test index listing
                response = await client.get(f"{base_url}/indexes")
                if response.status_code == 200:
                    result.warnings.append("Index listing successful")
                elif response.status_code == 403:
                    result.errors.append("Insufficient permissions for index operations")
                    result.valid = False
                else:
                    result.warnings.append(f"Index listing returned {response.status_code}")
                
                # Test creating a temporary test index
                test_index_name = "thai-tokenizer-test"
                create_response = await client.post(
                    f"{base_url}/indexes",
                    json={"uid": test_index_name, "primaryKey": "id"}
                )
                
                if create_response.status_code in [201, 202]:
                    result.warnings.append("Test index creation successful")
                    
                    # Clean up test index
                    try:
                        await client.delete(f"{base_url}/indexes/{test_index_name}")
                        result.warnings.append("Test index cleanup successful")
                    except Exception:
                        result.warnings.append("Test index cleanup failed (manual cleanup may be needed)")
                        
                elif create_response.status_code == 403:
                    result.errors.append("Insufficient permissions for index creation")
                    result.valid = False
                else:
                    result.warnings.append(f"Test index creation returned {create_response.status_code}")
        
        except Exception as e:
            result.valid = False
            result.errors.append(f"Index operations test failed: {e}")
        
        return result
    
    async def test_performance(self) -> ValidationResult:
        """Test Meilisearch performance."""
        self.logger.info("Testing Meilisearch performance")
        
        result = ValidationResult(valid=True)
        
        try:
            # Perform multiple connection tests to measure performance
            response_times = []
            
            for i in range(5):
                start_time = time.time()
                conn_result = await self.connection_tester.test_connection()
                end_time = time.time()
                
                if conn_result.status == ConnectionStatus.CONNECTED:
                    response_times.append((end_time - start_time) * 1000)
                else:
                    result.warnings.append(f"Performance test iteration {i+1} failed")
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                max_response_time = max(response_times)
                min_response_time = min(response_times)
                
                result.warnings.append(
                    f"Meilisearch performance: avg={avg_response_time:.2f}ms, "
                    f"min={min_response_time:.2f}ms, max={max_response_time:.2f}ms"
                )
                
                # Check if performance is acceptable
                if avg_response_time > 1000:  # 1 second threshold
                    result.warnings.append("Meilisearch response time is high, may affect performance")
                
            else:
                result.valid = False
                result.errors.append("All performance test iterations failed")
        
        except Exception as e:
            result.valid = False
            result.errors.append(f"Meilisearch performance test failed: {e}")
        
        return result


class ThaiTokenizationValidator:
    """Validates Thai tokenization functionality."""
    
    def __init__(self):
        self.logger = get_structured_logger(f"{__name__}.ThaiTokenizationValidator")
        self._define_test_cases()
    
    def _define_test_cases(self):
        """Define Thai tokenization test cases."""
        self.test_cases = [
            ThaiTokenizationTest(
                name="basic_thai_text",
                input_text="สวัสดีครับ ผมชื่อจอห์น",
                test_type="accuracy",
                timeout_seconds=5.0
            ),
            ThaiTokenizationTest(
                name="compound_words",
                input_text="รถยนต์ไฟฟ้า เครื่องปรับอากาศ",
                test_type="accuracy",
                timeout_seconds=5.0
            ),
            ThaiTokenizationTest(
                name="mixed_thai_english",
                input_text="Hello สวัสดี World โลก",
                test_type="accuracy",
                timeout_seconds=5.0
            ),
            ThaiTokenizationTest(
                name="long_text_performance",
                input_text="ในยุคดิจิทัลที่เทคโนโลยีก้าวหน้าอย่างรวดเร็ว การประมวลผลภาษาธรรมชาติได้กลายเป็นเครื่องมือสำคัญในการพัฒนาระบบสารสนเทศต่างๆ " * 10,
                test_type="performance",
                timeout_seconds=10.0
            ),
            ThaiTokenizationTest(
                name="special_characters",
                input_text="อีเมล: test@example.com โทร: 02-123-4567",
                test_type="accuracy",
                timeout_seconds=5.0
            ),
            ThaiTokenizationTest(
                name="numbers_and_dates",
                input_text="วันที่ 15 มกราคม 2567 เวลา 14:30 น.",
                test_type="accuracy",
                timeout_seconds=5.0
            ),
        ]
    
    async def validate_tokenization_functionality(self, service_url: str) -> List[TokenizationTestResult]:
        """
        Validate Thai tokenization functionality.
        
        Args:
            service_url: Base URL of the Thai Tokenizer service
            
        Returns:
            List of tokenization test results
        """
        self.logger.info("Starting Thai tokenization functionality validation")
        results = []
        
        for test_case in self.test_cases:
            try:
                result = await self._run_tokenization_test(test_case, service_url)
                results.append(result)
                
                if result.success:
                    self.logger.info(f"✓ {test_case.name}: {result.response_time_ms:.2f}ms")
                else:
                    self.logger.error(f"✗ {test_case.name}: {result.error_message}")
                    
            except Exception as e:
                self.logger.error(f"Failed to run test {test_case.name}: {e}")
                results.append(TokenizationTestResult(
                    test=test_case,
                    success=False,
                    response_time_ms=0.0,
                    error_message=f"Test execution failed: {e}"
                ))
        
        # Summary
        successful_tests = sum(1 for r in results if r.success)
        total_tests = len(results)
        
        self.logger.info(
            f"Thai tokenization validation completed: {successful_tests}/{total_tests} tests passed"
        )
        
        return results
    
    async def _run_tokenization_test(self, test_case: ThaiTokenizationTest, service_url: str) -> TokenizationTestResult:
        """Run a single tokenization test."""
        start_time = time.time()
        
        try:
            async with httpx.AsyncClient(timeout=test_case.timeout_seconds) as client:
                response = await client.post(
                    f"{service_url}/v1/tokenize",
                    json={"text": test_case.input_text}
                )
                
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                
                if response.status_code == 200:
                    response_data = response.json()
                    tokens = response_data.get("tokens", [])
                    
                    # Calculate accuracy if expected tokens are provided
                    accuracy_score = None
                    if test_case.expected_tokens:
                        accuracy_score = self._calculate_accuracy(tokens, test_case.expected_tokens)
                    
                    return TokenizationTestResult(
                        test=test_case,
                        success=True,
                        actual_tokens=tokens,
                        response_time_ms=response_time_ms,
                        accuracy_score=accuracy_score
                    )
                else:
                    return TokenizationTestResult(
                        test=test_case,
                        success=False,
                        response_time_ms=response_time_ms,
                        error_message=f"HTTP {response.status_code}: {response.text}"
                    )
                    
        except httpx.TimeoutException:
            return TokenizationTestResult(
                test=test_case,
                success=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message="Request timeout"
            )
        except Exception as e:
            return TokenizationTestResult(
                test=test_case,
                success=False,
                response_time_ms=(time.time() - start_time) * 1000,
                error_message=str(e)
            )
    
    def _calculate_accuracy(self, actual_tokens: List[str], expected_tokens: List[str]) -> float:
        """Calculate tokenization accuracy score."""
        if not expected_tokens:
            return 1.0
        
        # Simple accuracy calculation based on token overlap
        actual_set = set(actual_tokens)
        expected_set = set(expected_tokens)
        
        if not expected_set:
            return 1.0 if not actual_set else 0.0
        
        intersection = actual_set.intersection(expected_set)
        union = actual_set.union(expected_set)
        
        return len(intersection) / len(union) if union else 1.0


class PerformanceBenchmarkRunner:
    """Runs performance benchmarks for deployment validation."""
    
    def __init__(self):
        self.logger = get_structured_logger(f"{__name__}.PerformanceBenchmarkRunner")
        self._define_benchmarks()
    
    def _define_benchmarks(self):
        """Define performance benchmarks."""
        self.benchmarks = [
            PerformanceBenchmark(
                name="tokenization_response_time",
                description="Thai tokenization response time for 1000 characters",
                target_value=50.0,  # 50ms target
                unit="ms",
                tolerance_percent=20.0
            ),
            PerformanceBenchmark(
                name="service_startup_time",
                description="Service startup time",
                target_value=10.0,  # 10 seconds target
                unit="seconds",
                tolerance_percent=50.0
            ),
            PerformanceBenchmark(
                name="concurrent_requests",
                description="Concurrent request handling",
                target_value=50.0,  # 50 concurrent requests
                unit="requests",
                tolerance_percent=30.0
            ),
            PerformanceBenchmark(
                name="memory_usage",
                description="Memory usage under load",
                target_value=256.0,  # 256MB target
                unit="MB",
                tolerance_percent=25.0
            ),
        ]
    
    async def run_performance_benchmarks(self, service_url: str, config: OnPremiseConfig) -> List[BenchmarkResult]:
        """
        Run all performance benchmarks.
        
        Args:
            service_url: Base URL of the Thai Tokenizer service
            config: Deployment configuration
            
        Returns:
            List of benchmark results
        """
        self.logger.info("Starting performance benchmarks")
        results = []
        
        for benchmark in self.benchmarks:
            try:
                result = await self._run_benchmark(benchmark, service_url, config)
                results.append(result)
                
                status = "PASS" if result.passed else "FAIL"
                self.logger.info(
                    f"{status} {benchmark.name}: {result.measured_value:.2f}{benchmark.unit} "
                    f"(target: {benchmark.target_value:.2f}{benchmark.unit}, "
                    f"deviation: {result.deviation_percent:.1f}%)"
                )
                
            except Exception as e:
                self.logger.error(f"Failed to run benchmark {benchmark.name}: {e}")
                results.append(BenchmarkResult(
                    benchmark=benchmark,
                    measured_value=0.0,
                    passed=False,
                    deviation_percent=100.0,
                    details={"error": str(e)}
                ))
        
        # Summary
        passed_benchmarks = sum(1 for r in results if r.passed)
        total_benchmarks = len(results)
        
        self.logger.info(
            f"Performance benchmarks completed: {passed_benchmarks}/{total_benchmarks} passed"
        )
        
        return results
    
    async def _run_benchmark(self, benchmark: PerformanceBenchmark, service_url: str, config: OnPremiseConfig) -> BenchmarkResult:
        """Run a single performance benchmark."""
        if benchmark.name == "tokenization_response_time":
            return await self._benchmark_tokenization_response_time(benchmark, service_url)
        elif benchmark.name == "service_startup_time":
            return await self._benchmark_service_startup_time(benchmark, service_url)
        elif benchmark.name == "concurrent_requests":
            return await self._benchmark_concurrent_requests(benchmark, service_url)
        elif benchmark.name == "memory_usage":
            return await self._benchmark_memory_usage(benchmark, config)
        else:
            return BenchmarkResult(
                benchmark=benchmark,
                measured_value=0.0,
                passed=False,
                deviation_percent=100.0,
                details={"error": "Unknown benchmark"}
            )
    
    async def _benchmark_tokenization_response_time(self, benchmark: PerformanceBenchmark, service_url: str) -> BenchmarkResult:
        """Benchmark tokenization response time."""
        test_text = "ในยุคดิจิทัลที่เทคโนโลยีก้าวหน้าอย่างรวดเร็ว การประมวลผลภาษาธรรมชาติได้กลายเป็นเครื่องมือสำคัญในการพัฒนาระบบสารสนเทศต่างๆ" * 5
        
        response_times = []
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                # Warm up
                await client.post(f"{service_url}/v1/tokenize", json={"text": "สวัสดี"})
                
                # Run benchmark
                for _ in range(10):
                    start_time = time.time()
                    response = await client.post(
                        f"{service_url}/v1/tokenize",
                        json={"text": test_text}
                    )
                    end_time = time.time()
                    
                    if response.status_code == 200:
                        response_times.append((end_time - start_time) * 1000)
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
                deviation_percent = abs(avg_response_time - benchmark.target_value) / benchmark.target_value * 100
                passed = deviation_percent <= benchmark.tolerance_percent
                
                return BenchmarkResult(
                    benchmark=benchmark,
                    measured_value=avg_response_time,
                    passed=passed,
                    deviation_percent=deviation_percent,
                    details={
                        "response_times": response_times,
                        "min_time": min(response_times),
                        "max_time": max(response_times),
                        "test_text_length": len(test_text)
                    }
                )
            else:
                return BenchmarkResult(
                    benchmark=benchmark,
                    measured_value=0.0,
                    passed=False,
                    deviation_percent=100.0,
                    details={"error": "No successful requests"}
                )
                
        except Exception as e:
            return BenchmarkResult(
                benchmark=benchmark,
                measured_value=0.0,
                passed=False,
                deviation_percent=100.0,
                details={"error": str(e)}
            )
    
    async def _benchmark_service_startup_time(self, benchmark: PerformanceBenchmark, service_url: str) -> BenchmarkResult:
        """Benchmark service startup time."""
        # This is a simplified benchmark - in practice, you'd measure actual startup time
        try:
            start_time = time.time()
            
            # Wait for service to be ready
            max_wait_time = 30  # 30 seconds max
            ready = False
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                while time.time() - start_time < max_wait_time:
                    try:
                        response = await client.get(f"{service_url}/health")
                        if response.status_code == 200:
                            ready = True
                            break
                    except Exception:
                        pass
                    
                    await asyncio.sleep(1)
            
            startup_time = time.time() - start_time
            
            if ready:
                deviation_percent = abs(startup_time - benchmark.target_value) / benchmark.target_value * 100
                passed = deviation_percent <= benchmark.tolerance_percent
                
                return BenchmarkResult(
                    benchmark=benchmark,
                    measured_value=startup_time,
                    passed=passed,
                    deviation_percent=deviation_percent,
                    details={"ready": ready}
                )
            else:
                return BenchmarkResult(
                    benchmark=benchmark,
                    measured_value=startup_time,
                    passed=False,
                    deviation_percent=100.0,
                    details={"ready": False, "timeout": True}
                )
                
        except Exception as e:
            return BenchmarkResult(
                benchmark=benchmark,
                measured_value=0.0,
                passed=False,
                deviation_percent=100.0,
                details={"error": str(e)}
            )
    
    async def _benchmark_concurrent_requests(self, benchmark: PerformanceBenchmark, service_url: str) -> BenchmarkResult:
        """Benchmark concurrent request handling."""
        try:
            concurrent_requests = int(benchmark.target_value)
            test_text = "สวัสดีครับ ผมชื่อจอห์น"
            
            async def make_request(client, semaphore):
                async with semaphore:
                    try:
                        response = await client.post(
                            f"{service_url}/v1/tokenize",
                            json={"text": test_text}
                        )
                        return response.status_code == 200
                    except Exception:
                        return False
            
            semaphore = asyncio.Semaphore(concurrent_requests)
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                start_time = time.time()
                
                tasks = [make_request(client, semaphore) for _ in range(concurrent_requests)]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                end_time = time.time()
                
                successful_requests = sum(1 for r in results if r is True)
                total_time = end_time - start_time
                
                deviation_percent = abs(successful_requests - benchmark.target_value) / benchmark.target_value * 100
                passed = deviation_percent <= benchmark.tolerance_percent
                
                return BenchmarkResult(
                    benchmark=benchmark,
                    measured_value=float(successful_requests),
                    passed=passed,
                    deviation_percent=deviation_percent,
                    details={
                        "successful_requests": successful_requests,
                        "total_requests": concurrent_requests,
                        "total_time": total_time,
                        "requests_per_second": successful_requests / total_time if total_time > 0 else 0
                    }
                )
                
        except Exception as e:
            return BenchmarkResult(
                benchmark=benchmark,
                measured_value=0.0,
                passed=False,
                deviation_percent=100.0,
                details={"error": str(e)}
            )
    
    async def _benchmark_memory_usage(self, benchmark: PerformanceBenchmark, config: OnPremiseConfig) -> BenchmarkResult:
        """Benchmark memory usage."""
        try:
            # Find service process
            service_name = config.service_config.service_name
            service_processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_info']):
                try:
                    if any(service_name in str(item) for item in proc.info['cmdline']):
                        service_processes.append(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            if service_processes:
                total_memory_mb = sum(
                    proc.info['memory_info'].rss / 1024 / 1024 
                    for proc in service_processes
                )
                
                deviation_percent = abs(total_memory_mb - benchmark.target_value) / benchmark.target_value * 100
                passed = total_memory_mb <= benchmark.target_value * (1 + benchmark.tolerance_percent / 100)
                
                return BenchmarkResult(
                    benchmark=benchmark,
                    measured_value=total_memory_mb,
                    passed=passed,
                    deviation_percent=deviation_percent,
                    details={
                        "process_count": len(service_processes),
                        "processes": [
                            {"pid": proc.info['pid'], "memory_mb": proc.info['memory_info'].rss / 1024 / 1024}
                            for proc in service_processes
                        ]
                    }
                )
            else:
                return BenchmarkResult(
                    benchmark=benchmark,
                    measured_value=0.0,
                    passed=False,
                    deviation_percent=100.0,
                    details={"error": "Service process not found"}
                )
                
        except Exception as e:
            return BenchmarkResult(
                benchmark=benchmark,
                measured_value=0.0,
                passed=False,
                deviation_percent=100.0,
                details={"error": str(e)}
            )


class DeploymentValidationFramework:
    """
    Comprehensive deployment validation and testing framework.
    
    Coordinates all validation components to provide complete deployment validation.
    """
    
    def __init__(self, config: OnPremiseConfig):
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.DeploymentValidationFramework")
        
        # Initialize validators
        self.requirements_validator = SystemRequirementsValidator()
        self.meilisearch_tester = MeilisearchConnectivityTester(config)
        self.tokenization_validator = ThaiTokenizationValidator()
        self.benchmark_runner = PerformanceBenchmarkRunner()
    
    async def run_comprehensive_validation(self, service_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Run comprehensive deployment validation.
        
        Args:
            service_url: Optional service URL for post-deployment validation
            
        Returns:
            Comprehensive validation results
        """
        self.logger.info("Starting comprehensive deployment validation")
        
        validation_results = {
            "timestamp": datetime.now().isoformat(),
            "config": {
                "deployment_method": self.config.deployment_method.value,
                "service_name": self.config.service_config.service_name,
                "service_port": self.config.service_config.service_port,
            },
            "system_requirements": None,
            "meilisearch_connectivity": None,
            "thai_tokenization": None,
            "performance_benchmarks": None,
            "overall_status": "unknown",
            "summary": {}
        }
        
        try:
            # 1. System Requirements Validation
            self.logger.info("Phase 1: System Requirements Validation")
            requirements_results = await self.requirements_validator.validate_all_requirements(self.config)
            validation_results["system_requirements"] = [
                result.dict() for result in requirements_results
            ]
            
            # 2. Meilisearch Connectivity Testing
            self.logger.info("Phase 2: Meilisearch Connectivity Testing")
            meilisearch_results = await self._test_meilisearch_connectivity()
            validation_results["meilisearch_connectivity"] = meilisearch_results
            
            # 3. Thai Tokenization Validation (if service URL provided)
            if service_url:
                self.logger.info("Phase 3: Thai Tokenization Validation")
                tokenization_results = await self.tokenization_validator.validate_tokenization_functionality(service_url)
                validation_results["thai_tokenization"] = [
                    result.dict() for result in tokenization_results
                ]
                
                # 4. Performance Benchmarks
                self.logger.info("Phase 4: Performance Benchmarks")
                benchmark_results = await self.benchmark_runner.run_performance_benchmarks(service_url, self.config)
                validation_results["performance_benchmarks"] = [
                    result.dict() for result in benchmark_results
                ]
            else:
                self.logger.info("Skipping service-dependent validation (no service URL provided)")
            
            # Generate summary
            validation_results["summary"] = self._generate_validation_summary(validation_results)
            validation_results["overall_status"] = self._determine_overall_status(validation_results)
            
            self.logger.info(f"Comprehensive validation completed: {validation_results['overall_status']}")
            
        except Exception as e:
            self.logger.error(f"Comprehensive validation failed: {e}")
            validation_results["overall_status"] = "error"
            validation_results["error"] = str(e)
        
        return validation_results
    
    async def _test_meilisearch_connectivity(self) -> Dict[str, Any]:
        """Test Meilisearch connectivity comprehensively."""
        results = {
            "basic_connectivity": None,
            "api_permissions": None,
            "index_operations": None,
            "performance": None,
        }
        
        try:
            # Basic connectivity
            basic_result = await self.meilisearch_tester.test_basic_connectivity()
            results["basic_connectivity"] = basic_result.dict()
            
            if basic_result.valid:
                # API permissions
                permissions_result = await self.meilisearch_tester.test_api_permissions()
                results["api_permissions"] = permissions_result.dict()
                
                # Index operations
                index_result = await self.meilisearch_tester.test_index_operations()
                results["index_operations"] = index_result.dict()
                
                # Performance
                performance_result = await self.meilisearch_tester.test_performance()
                results["performance"] = performance_result.dict()
            
        except Exception as e:
            results["error"] = str(e)
        
        return results
    
    def _generate_validation_summary(self, validation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate validation summary."""
        summary = {
            "total_checks": 0,
            "passed_checks": 0,
            "failed_checks": 0,
            "warnings": 0,
            "critical_issues": [],
            "recommendations": []
        }
        
        # System requirements summary
        if validation_results.get("system_requirements"):
            req_results = validation_results["system_requirements"]
            for req in req_results:
                summary["total_checks"] += 1
                if req["satisfied"]:
                    summary["passed_checks"] += 1
                else:
                    summary["failed_checks"] += 1
                    if req["requirement"]["required"]:
                        summary["critical_issues"].append(f"Required: {req['requirement']['description']}")
        
        # Meilisearch connectivity summary
        if validation_results.get("meilisearch_connectivity"):
            ms_results = validation_results["meilisearch_connectivity"]
            for test_name, test_result in ms_results.items():
                if isinstance(test_result, dict) and "valid" in test_result:
                    summary["total_checks"] += 1
                    if test_result["valid"]:
                        summary["passed_checks"] += 1
                    else:
                        summary["failed_checks"] += 1
                        summary["critical_issues"].append(f"Meilisearch {test_name} failed")
        
        # Thai tokenization summary
        if validation_results.get("thai_tokenization"):
            token_results = validation_results["thai_tokenization"]
            for token_result in token_results:
                summary["total_checks"] += 1
                if token_result["success"]:
                    summary["passed_checks"] += 1
                else:
                    summary["failed_checks"] += 1
        
        # Performance benchmarks summary
        if validation_results.get("performance_benchmarks"):
            bench_results = validation_results["performance_benchmarks"]
            for bench_result in bench_results:
                summary["total_checks"] += 1
                if bench_result["passed"]:
                    summary["passed_checks"] += 1
                else:
                    summary["failed_checks"] += 1
        
        # Generate recommendations
        if summary["failed_checks"] > 0:
            summary["recommendations"].append("Review failed checks and address critical issues before deployment")
        
        if summary["critical_issues"]:
            summary["recommendations"].append("Address all critical issues before proceeding with deployment")
        
        return summary
    
    def _determine_overall_status(self, validation_results: Dict[str, Any]) -> str:
        """Determine overall validation status."""
        summary = validation_results.get("summary", {})
        
        if summary.get("critical_issues"):
            return "critical_issues"
        elif summary.get("failed_checks", 0) > 0:
            return "warnings"
        elif summary.get("passed_checks", 0) > 0:
            return "passed"
        else:
            return "unknown"
    
    async def generate_validation_report(self, validation_results: Dict[str, Any], output_path: Optional[str] = None) -> str:
        """
        Generate comprehensive validation report.
        
        Args:
            validation_results: Validation results from run_comprehensive_validation
            output_path: Optional path to save the report
            
        Returns:
            Report content as string
        """
        report_lines = [
            "# Thai Tokenizer Deployment Validation Report",
            "",
            f"**Generated:** {validation_results.get('timestamp', 'Unknown')}",
            f"**Deployment Method:** {validation_results.get('config', {}).get('deployment_method', 'Unknown')}",
            f"**Service:** {validation_results.get('config', {}).get('service_name', 'Unknown')}",
            f"**Overall Status:** {validation_results.get('overall_status', 'Unknown').upper()}",
            "",
        ]
        
        # Summary
        summary = validation_results.get("summary", {})
        if summary:
            report_lines.extend([
                "## Summary",
                "",
                f"- **Total Checks:** {summary.get('total_checks', 0)}",
                f"- **Passed:** {summary.get('passed_checks', 0)}",
                f"- **Failed:** {summary.get('failed_checks', 0)}",
                f"- **Warnings:** {summary.get('warnings', 0)}",
                "",
            ])
            
            if summary.get("critical_issues"):
                report_lines.extend([
                    "### Critical Issues",
                    "",
                ])
                for issue in summary["critical_issues"]:
                    report_lines.append(f"- ❌ {issue}")
                report_lines.append("")
            
            if summary.get("recommendations"):
                report_lines.extend([
                    "### Recommendations",
                    "",
                ])
                for rec in summary["recommendations"]:
                    report_lines.append(f"- 💡 {rec}")
                report_lines.append("")
        
        # Detailed results sections would go here...
        # (Implementation truncated for brevity)
        
        report_content = "\n".join(report_lines)
        
        if output_path:
            Path(output_path).write_text(report_content, encoding="utf-8")
            self.logger.info(f"Validation report saved to: {output_path}")
        
        return report_content