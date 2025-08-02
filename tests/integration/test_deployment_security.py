#!/usr/bin/env python3
"""
Security and authentication testing for on-premise deployment methods.

This module provides comprehensive security testing for deployed Thai tokenizer
services, including authentication, authorization, CORS, rate limiting, and
security configuration validation.
"""

import asyncio
import json
import pytest
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from unittest.mock import Mock, patch, AsyncMock
import httpx
import ssl
import socket

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.deployment.config import OnPremiseConfig, SecurityLevel


@dataclass
class SecurityTestResult:
    """Security test result data structure."""
    test_name: str
    success: bool
    details: Dict[str, Any]
    error_message: Optional[str] = None
    recommendations: List[str] = None


class DeploymentSecurityTester:
    """Security testing utility for deployed services."""
    
    def __init__(self, service_url: str, config: OnPremiseConfig):
        self.service_url = service_url
        self.config = config
        self.base_headers = {"Content-Type": "application/json"}
    
    async def test_cors_configuration(self) -> SecurityTestResult:
        """Test CORS configuration and security."""
        test_name = "cors_configuration"
        
        try:
            async with httpx.AsyncClient() as client:
                # Test preflight request
                preflight_response = await client.options(
                    f"{self.service_url}/v1/tokenize",
                    headers={
                        "Origin": "http://localhost:3000",
                        "Access-Control-Request-Method": "POST",
                        "Access-Control-Request-Headers": "Content-Type"
                    }
                )
                
                # Test actual CORS request
                cors_response = await client.post(
                    f"{self.service_url}/v1/tokenize",
                    json={"text": "test"},
                    headers={
                        "Origin": "http://localhost:3000",
                        **self.base_headers
                    }
                )
                
                # Analyze CORS headers
                cors_headers = cors_response.headers
                
                details = {
                    "preflight_status": preflight_response.status_code,
                    "cors_status": cors_response.status_code,
                    "access_control_allow_origin": cors_headers.get("access-control-allow-origin"),
                    "access_control_allow_methods": cors_headers.get("access-control-allow-methods"),
                    "access_control_allow_headers": cors_headers.get("access-control-allow-headers"),
                    "access_control_max_age": cors_headers.get("access-control-max-age")
                }
                
                # Validate CORS configuration
                success = True
                recommendations = []
                
                if self.config.security_config.cors_origins == ["*"]:
                    recommendations.append("Consider restricting CORS origins for production")
                
                if not cors_headers.get("access-control-allow-origin"):
                    success = False
                    recommendations.append("CORS headers not properly configured")
                
                return SecurityTestResult(
                    test_name=test_name,
                    success=success,
                    details=details,
                    recommendations=recommendations
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name=test_name,
                success=False,
                details={},
                error_message=str(e)
            )
    
    async def test_api_key_authentication(self) -> SecurityTestResult:
        """Test API key authentication if enabled."""
        test_name = "api_key_authentication"
        
        if not self.config.security_config.api_key_required:
            return SecurityTestResult(
                test_name=test_name,
                success=True,
                details={"authentication_disabled": True},
                recommendations=["Consider enabling API key authentication for production"]
            )
        
        try:
            async with httpx.AsyncClient() as client:
                # Test without API key
                no_auth_response = await client.post(
                    f"{self.service_url}/v1/tokenize",
                    json={"text": "test"},
                    headers=self.base_headers
                )
                
                # Test with invalid API key
                invalid_auth_response = await client.post(
                    f"{self.service_url}/v1/tokenize",
                    json={"text": "test"},
                    headers={
                        "Authorization": "Bearer invalid-key",
                        **self.base_headers
                    }
                )
                
                # Test with valid API key (if available)
                valid_auth_response = None
                if hasattr(self.config.meilisearch_config, 'api_key'):
                    valid_auth_response = await client.post(
                        f"{self.service_url}/v1/tokenize",
                        json={"text": "test"},
                        headers={
                            "Authorization": f"Bearer {self.config.meilisearch_config.api_key}",
                            **self.base_headers
                        }
                    )
                
                details = {
                    "no_auth_status": no_auth_response.status_code,
                    "invalid_auth_status": invalid_auth_response.status_code,
                    "valid_auth_status": valid_auth_response.status_code if valid_auth_response else None
                }
                
                # Validate authentication behavior
                success = True
                recommendations = []
                
                if no_auth_response.status_code != 401:
                    success = False
                    recommendations.append("Service should return 401 for requests without API key")
                
                if invalid_auth_response.status_code != 401:
                    success = False
                    recommendations.append("Service should return 401 for invalid API keys")
                
                if valid_auth_response and valid_auth_response.status_code != 200:
                    success = False
                    recommendations.append("Service should accept valid API keys")
                
                return SecurityTestResult(
                    test_name=test_name,
                    success=success,
                    details=details,
                    recommendations=recommendations
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name=test_name,
                success=False,
                details={},
                error_message=str(e)
            )
    
    async def test_rate_limiting(self) -> SecurityTestResult:
        """Test rate limiting configuration."""
        test_name = "rate_limiting"
        
        try:
            async with httpx.AsyncClient() as client:
                # Make rapid requests to test rate limiting
                responses = []
                start_time = time.time()
                
                for i in range(20):  # Make 20 rapid requests
                    try:
                        response = await client.post(
                            f"{self.service_url}/v1/tokenize",
                            json={"text": f"test request {i}"},
                            headers=self.base_headers,
                            timeout=5.0
                        )
                        responses.append({
                            "status_code": response.status_code,
                            "headers": dict(response.headers),
                            "request_number": i
                        })
                    except Exception as e:
                        responses.append({
                            "error": str(e),
                            "request_number": i
                        })
                    
                    # Small delay between requests
                    await asyncio.sleep(0.1)
                
                end_time = time.time()
                total_time = end_time - start_time
                
                # Analyze rate limiting behavior
                rate_limited_responses = [
                    r for r in responses 
                    if r.get("status_code") == 429
                ]
                
                successful_responses = [
                    r for r in responses 
                    if r.get("status_code") == 200
                ]
                
                details = {
                    "total_requests": len(responses),
                    "successful_requests": len(successful_responses),
                    "rate_limited_requests": len(rate_limited_responses),
                    "total_time_seconds": total_time,
                    "requests_per_second": len(responses) / total_time
                }
                
                # Evaluate rate limiting effectiveness
                success = True
                recommendations = []
                
                if len(rate_limited_responses) == 0:
                    recommendations.append("Consider implementing rate limiting for production")
                
                if len(successful_responses) > self.config.resource_config.max_concurrent_requests:
                    recommendations.append("Rate limiting may not be properly configured")
                
                return SecurityTestResult(
                    test_name=test_name,
                    success=success,
                    details=details,
                    recommendations=recommendations
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name=test_name,
                success=False,
                details={},
                error_message=str(e)
            )
    
    async def test_https_configuration(self) -> SecurityTestResult:
        """Test HTTPS/TLS configuration."""
        test_name = "https_configuration"
        
        if not self.config.security_config.enable_https:
            return SecurityTestResult(
                test_name=test_name,
                success=True,
                details={"https_disabled": True},
                recommendations=["Consider enabling HTTPS for production deployment"]
            )
        
        try:
            # Parse URL to get host and port
            from urllib.parse import urlparse
            parsed_url = urlparse(self.service_url)
            host = parsed_url.hostname or "localhost"
            port = parsed_url.port or 443
            
            # Test SSL/TLS connection
            context = ssl.create_default_context()
            
            with socket.create_connection((host, port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=host) as ssock:
                    cert = ssock.getpeercert()
                    cipher = ssock.cipher()
                    version = ssock.version()
            
            details = {
                "ssl_version": version,
                "cipher_suite": cipher[0] if cipher else None,
                "certificate_subject": cert.get("subject") if cert else None,
                "certificate_issuer": cert.get("issuer") if cert else None,
                "certificate_expires": cert.get("notAfter") if cert else None
            }
            
            # Validate SSL/TLS configuration
            success = True
            recommendations = []
            
            if version and version < "TLSv1.2":
                success = False
                recommendations.append("Upgrade to TLS 1.2 or higher")
            
            if not cert:
                success = False
                recommendations.append("SSL certificate not properly configured")
            
            return SecurityTestResult(
                test_name=test_name,
                success=success,
                details=details,
                recommendations=recommendations
            )
            
        except Exception as e:
            return SecurityTestResult(
                test_name=test_name,
                success=False,
                details={},
                error_message=str(e),
                recommendations=["HTTPS connection failed - check SSL/TLS configuration"]
            )
    
    async def test_input_validation(self) -> SecurityTestResult:
        """Test input validation and sanitization."""
        test_name = "input_validation"
        
        # Test cases for input validation
        test_cases = [
            {"text": ""},  # Empty input
            {"text": "A" * 10000},  # Very long input
            {"text": "<script>alert('xss')</script>"},  # XSS attempt
            {"text": "'; DROP TABLE users; --"},  # SQL injection attempt
            {"text": "../../../etc/passwd"},  # Path traversal attempt
            {"text": "\x00\x01\x02"},  # Binary data
            {"invalid_field": "test"},  # Invalid field
            {},  # Missing required field
        ]
        
        try:
            async with httpx.AsyncClient() as client:
                results = []
                
                for i, test_case in enumerate(test_cases):
                    try:
                        response = await client.post(
                            f"{self.service_url}/v1/tokenize",
                            json=test_case,
                            headers=self.base_headers,
                            timeout=10.0
                        )
                        
                        results.append({
                            "test_case": i,
                            "input": test_case,
                            "status_code": response.status_code,
                            "response_size": len(response.content)
                        })
                        
                    except Exception as e:
                        results.append({
                            "test_case": i,
                            "input": test_case,
                            "error": str(e)
                        })
                
                # Analyze input validation behavior
                validation_errors = [
                    r for r in results 
                    if r.get("status_code") in [400, 422]
                ]
                
                server_errors = [
                    r for r in results 
                    if r.get("status_code", 0) >= 500
                ]
                
                details = {
                    "total_test_cases": len(test_cases),
                    "validation_errors": len(validation_errors),
                    "server_errors": len(server_errors),
                    "test_results": results
                }
                
                # Evaluate input validation
                success = True
                recommendations = []
                
                if len(server_errors) > 0:
                    success = False
                    recommendations.append("Server errors indicate insufficient input validation")
                
                if len(validation_errors) < 4:  # Should reject at least some invalid inputs
                    recommendations.append("Consider stricter input validation")
                
                return SecurityTestResult(
                    test_name=test_name,
                    success=success,
                    details=details,
                    recommendations=recommendations
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name=test_name,
                success=False,
                details={},
                error_message=str(e)
            )
    
    async def test_security_headers(self) -> SecurityTestResult:
        """Test security headers configuration."""
        test_name = "security_headers"
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.service_url}/health",
                    headers=self.base_headers
                )
                
                headers = response.headers
                
                # Check for important security headers
                security_headers = {
                    "x-content-type-options": headers.get("x-content-type-options"),
                    "x-frame-options": headers.get("x-frame-options"),
                    "x-xss-protection": headers.get("x-xss-protection"),
                    "strict-transport-security": headers.get("strict-transport-security"),
                    "content-security-policy": headers.get("content-security-policy"),
                    "referrer-policy": headers.get("referrer-policy"),
                    "permissions-policy": headers.get("permissions-policy")
                }
                
                details = {
                    "security_headers": security_headers,
                    "response_status": response.status_code
                }
                
                # Evaluate security headers
                success = True
                recommendations = []
                
                if not security_headers.get("x-content-type-options"):
                    recommendations.append("Add X-Content-Type-Options: nosniff header")
                
                if not security_headers.get("x-frame-options"):
                    recommendations.append("Add X-Frame-Options header to prevent clickjacking")
                
                if self.config.security_config.enable_https and not security_headers.get("strict-transport-security"):
                    recommendations.append("Add Strict-Transport-Security header for HTTPS")
                
                if not security_headers.get("content-security-policy"):
                    recommendations.append("Consider adding Content-Security-Policy header")
                
                return SecurityTestResult(
                    test_name=test_name,
                    success=success,
                    details=details,
                    recommendations=recommendations
                )
                
        except Exception as e:
            return SecurityTestResult(
                test_name=test_name,
                success=False,
                details={},
                error_message=str(e)
            )
    
    async def run_comprehensive_security_audit(self) -> Dict[str, SecurityTestResult]:
        """Run comprehensive security audit."""
        tests = [
            self.test_cors_configuration(),
            self.test_api_key_authentication(),
            self.test_rate_limiting(),
            self.test_https_configuration(),
            self.test_input_validation(),
            self.test_security_headers()
        ]
        
        results = await asyncio.gather(*tests, return_exceptions=True)
        
        audit_results = {}
        for result in results:
            if isinstance(result, SecurityTestResult):
                audit_results[result.test_name] = result
            elif isinstance(result, Exception):
                audit_results["error"] = SecurityTestResult(
                    test_name="audit_error",
                    success=False,
                    details={},
                    error_message=str(result)
                )
        
        return audit_results


class TestDeploymentSecurity:
    """Security test suite for deployment methods."""
    
    @pytest.fixture
    def security_config_basic(self):
        """Create basic security configuration."""
        return {
            "deployment_method": "docker",
            "meilisearch_config": {
                "host": "http://localhost:7700",
                "port": 7700,
                "api_key": "test-security-key",
                "ssl_enabled": False,
                "ssl_verify": True,
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0
            },
            "service_config": {
                "service_name": "thai-tokenizer-security-test",
                "service_port": 8006,
                "service_host": "0.0.0.0",
                "worker_processes": 2,
                "service_user": "thai-tokenizer",
                "service_group": "thai-tokenizer"
            },
            "security_config": {
                "security_level": "standard",
                "allowed_hosts": ["localhost", "127.0.0.1"],
                "cors_origins": ["http://localhost:3000"],
                "api_key_required": False,
                "enable_https": False
            },
            "resource_config": {
                "memory_limit_mb": 256,
                "cpu_limit_cores": 0.5,
                "max_concurrent_requests": 10,
                "request_timeout_seconds": 30,
                "enable_metrics": True,
                "metrics_port": 9096
            },
            "monitoring_config": {
                "enable_health_checks": True,
                "health_check_interval_seconds": 30,
                "enable_logging": True,
                "log_level": "INFO",
                "enable_prometheus": False,
                "prometheus_port": 9096
            },
            "installation_path": "/tmp/thai-tokenizer-security-test",
            "data_path": "/tmp/thai-tokenizer-security-test/data",
            "log_path": "/tmp/thai-tokenizer-security-test/logs",
            "config_path": "/tmp/thai-tokenizer-security-test/config",
            "environment_variables": {}
        }
    
    @pytest.fixture
    def security_config_strict(self):
        """Create strict security configuration."""
        return {
            "deployment_method": "docker",
            "meilisearch_config": {
                "host": "https://localhost:7700",
                "port": 7700,
                "api_key": "test-strict-security-key",
                "ssl_enabled": True,
                "ssl_verify": True,
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0
            },
            "service_config": {
                "service_name": "thai-tokenizer-strict-security-test",
                "service_port": 8007,
                "service_host": "127.0.0.1",
                "worker_processes": 2,
                "service_user": "thai-tokenizer",
                "service_group": "thai-tokenizer"
            },
            "security_config": {
                "security_level": "strict",
                "allowed_hosts": ["127.0.0.1"],
                "cors_origins": ["https://app.example.com"],
                "api_key_required": True,
                "enable_https": True
            },
            "resource_config": {
                "memory_limit_mb": 256,
                "cpu_limit_cores": 0.5,
                "max_concurrent_requests": 5,
                "request_timeout_seconds": 15,
                "enable_metrics": True,
                "metrics_port": 9097
            },
            "monitoring_config": {
                "enable_health_checks": True,
                "health_check_interval_seconds": 30,
                "enable_logging": True,
                "log_level": "WARNING",
                "enable_prometheus": True,
                "prometheus_port": 9097
            },
            "installation_path": "/tmp/thai-tokenizer-strict-security-test",
            "data_path": "/tmp/thai-tokenizer-strict-security-test/data",
            "log_path": "/tmp/thai-tokenizer-strict-security-test/logs",
            "config_path": "/tmp/thai-tokenizer-strict-security-test/config",
            "environment_variables": {}
        }
    
    @pytest.mark.asyncio
    async def test_cors_security_basic(self, security_config_basic):
        """Test CORS security with basic configuration."""
        config = OnPremiseConfig(**security_config_basic)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentSecurityTester(service_url, config)
        
        # Mock HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            # Mock CORS responses
            mock_options_response = Mock()
            mock_options_response.status_code = 200
            mock_options_response.headers = {
                "access-control-allow-origin": "http://localhost:3000",
                "access-control-allow-methods": "GET, POST, OPTIONS",
                "access-control-allow-headers": "Content-Type, Authorization"
            }
            
            mock_post_response = Mock()
            mock_post_response.status_code = 200
            mock_post_response.headers = {
                "access-control-allow-origin": "http://localhost:3000"
            }
            
            mock_client.return_value.__aenter__.return_value.options = AsyncMock(return_value=mock_options_response)
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_post_response)
            
            result = await tester.test_cors_configuration()
            
            assert result.success == True
            assert result.details["preflight_status"] == 200
            assert result.details["cors_status"] == 200
            assert "http://localhost:3000" in result.details["access_control_allow_origin"]
    
    @pytest.mark.asyncio
    async def test_api_key_authentication_strict(self, security_config_strict):
        """Test API key authentication with strict configuration."""
        config = OnPremiseConfig(**security_config_strict)
        service_url = f"https://localhost:{config.service_config.service_port}"
        
        tester = DeploymentSecurityTester(service_url, config)
        
        # Mock HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            def mock_auth_response(*args, **kwargs):
                headers = kwargs.get('headers', {})
                auth_header = headers.get('Authorization', '')
                
                if not auth_header:
                    return Mock(status_code=401, json=lambda: {"error": "Authentication required"})
                elif auth_header == "Bearer test-strict-security-key":
                    return Mock(status_code=200, json=lambda: {"tokens": ["test"]})
                else:
                    return Mock(status_code=401, json=lambda: {"error": "Invalid API key"})
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_auth_response)
            
            result = await tester.test_api_key_authentication()
            
            assert result.success == True
            assert result.details["no_auth_status"] == 401
            assert result.details["invalid_auth_status"] == 401
            assert result.details["valid_auth_status"] == 200
    
    @pytest.mark.asyncio
    async def test_rate_limiting_security(self, security_config_basic):
        """Test rate limiting security measures."""
        config = OnPremiseConfig(**security_config_basic)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentSecurityTester(service_url, config)
        
        # Mock HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            request_count = 0
            
            def mock_rate_limit_response(*args, **kwargs):
                nonlocal request_count
                request_count += 1
                
                if request_count <= 10:  # Allow first 10 requests
                    return Mock(status_code=200, json=lambda: {"tokens": ["test"]})
                else:  # Rate limit subsequent requests
                    return Mock(
                        status_code=429, 
                        json=lambda: {"error": "Rate limit exceeded"},
                        headers={"retry-after": "60"}
                    )
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_rate_limit_response)
            
            result = await tester.test_rate_limiting()
            
            assert result.success == True
            assert result.details["rate_limited_requests"] > 0
            assert result.details["successful_requests"] <= config.resource_config.max_concurrent_requests
    
    @pytest.mark.asyncio
    async def test_input_validation_security(self, security_config_basic):
        """Test input validation security measures."""
        config = OnPremiseConfig(**security_config_basic)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentSecurityTester(service_url, config)
        
        # Mock HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            def mock_validation_response(*args, **kwargs):
                request_data = kwargs.get('json', {})
                
                # Simulate input validation
                if not request_data.get('text'):
                    return Mock(status_code=400, json=lambda: {"error": "Text field required"})
                elif len(request_data.get('text', '')) > 5000:
                    return Mock(status_code=413, json=lambda: {"error": "Text too long"})
                elif '<script>' in request_data.get('text', ''):
                    return Mock(status_code=400, json=lambda: {"error": "Invalid characters"})
                else:
                    return Mock(status_code=200, json=lambda: {"tokens": ["test"]})
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(side_effect=mock_validation_response)
            
            result = await tester.test_input_validation()
            
            assert result.success == True
            assert result.details["validation_errors"] >= 3  # Should reject invalid inputs
            assert result.details["server_errors"] == 0  # Should not cause server errors
    
    @pytest.mark.asyncio
    async def test_security_headers(self, security_config_basic):
        """Test security headers configuration."""
        config = OnPremiseConfig(**security_config_basic)
        service_url = f"http://localhost:{config.service_config.service_port}"
        
        tester = DeploymentSecurityTester(service_url, config)
        
        # Mock HTTP client for testing
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.headers = {
                "x-content-type-options": "nosniff",
                "x-frame-options": "DENY",
                "x-xss-protection": "1; mode=block",
                "content-security-policy": "default-src 'self'",
                "referrer-policy": "strict-origin-when-cross-origin"
            }
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            result = await tester.test_security_headers()
            
            assert result.success == True
            assert result.details["security_headers"]["x-content-type-options"] == "nosniff"
            assert result.details["security_headers"]["x-frame-options"] == "DENY"
    
    @pytest.mark.asyncio
    async def test_comprehensive_security_audit(self, security_config_strict):
        """Test comprehensive security audit."""
        config = OnPremiseConfig(**security_config_strict)
        service_url = f"https://localhost:{config.service_config.service_port}"
        
        tester = DeploymentSecurityTester(service_url, config)
        
        # Mock all security test methods
        with patch.object(tester, 'test_cors_configuration') as mock_cors, \
             patch.object(tester, 'test_api_key_authentication') as mock_auth, \
             patch.object(tester, 'test_rate_limiting') as mock_rate, \
             patch.object(tester, 'test_https_configuration') as mock_https, \
             patch.object(tester, 'test_input_validation') as mock_input, \
             patch.object(tester, 'test_security_headers') as mock_headers:
            
            # Mock successful security test results
            mock_cors.return_value = SecurityTestResult("cors_configuration", True, {})
            mock_auth.return_value = SecurityTestResult("api_key_authentication", True, {})
            mock_rate.return_value = SecurityTestResult("rate_limiting", True, {})
            mock_https.return_value = SecurityTestResult("https_configuration", True, {})
            mock_input.return_value = SecurityTestResult("input_validation", True, {})
            mock_headers.return_value = SecurityTestResult("security_headers", True, {})
            
            results = await tester.run_comprehensive_security_audit()
            
            # Verify all security tests were run
            assert len(results) == 6
            assert "cors_configuration" in results
            assert "api_key_authentication" in results
            assert "rate_limiting" in results
            assert "https_configuration" in results
            assert "input_validation" in results
            assert "security_headers" in results
            
            # Verify all tests passed
            for test_name, result in results.items():
                assert result.success == True
    
    def test_security_configuration_validation(self):
        """Test security configuration validation."""
        # Test valid security levels
        for level in ["basic", "standard", "strict"]:
            config_dict = {
                "deployment_method": "docker",
                "meilisearch_config": {
                    "host": "http://localhost:7700",
                    "port": 7700,
                    "api_key": "test-key"
                },
                "security_config": {
                    "security_level": level,
                    "allowed_hosts": ["localhost"],
                    "cors_origins": ["*"],
                    "api_key_required": False,
                    "enable_https": False
                }
            }
            
            config = OnPremiseConfig(**config_dict)
            assert config.security_config.security_level == level
        
        # Test invalid security level
        with pytest.raises(ValueError):
            OnPremiseConfig(
                deployment_method="docker",
                meilisearch_config={
                    "host": "http://localhost:7700",
                    "port": 7700,
                    "api_key": "test-key"
                },
                security_config={
                    "security_level": "invalid_level"
                }
            )


if __name__ == "__main__":
    # Run security tests directly
    pytest.main([__file__, "-v", "--tb=short"])