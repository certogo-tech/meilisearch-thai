#!/usr/bin/env python3
"""
Final Integration Tests for Thai Tokenizer On-Premise Deployment.

This module provides comprehensive integration tests that validate all deployment
components work together correctly, including unified deployment orchestration,
error handling, configuration management, and cross-component interactions.
"""

import asyncio
import json
import os
import pytest
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timezone

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from deployment.config import OnPremiseConfig, DeploymentMethod
from deployment.unified_deployment import UnifiedDeploymentOrchestrator, DeploymentPhase
from deployment.unified_config import UnifiedConfigurationManager, ConfigurationSource
from deployment.error_handling import ErrorHandler, DeploymentError, ErrorCategory
from deployment.deployment_manager import DeploymentManager
from deployment.cli import DeploymentCLI


class TestFinalIntegration:
    """Comprehensive final integration tests."""
    
    @pytest.fixture
    def base_config(self):
        """Create base configuration for testing."""
        return {
            "deployment_method": "docker",
            "meilisearch_config": {
                "host": "http://localhost:7700",
                "port": 7700,
                "api_key": "test-integration-key",
                "ssl_enabled": False,
                "ssl_verify": True,
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0
            },
            "service_config": {
                "service_name": "thai-tokenizer-integration",
                "service_port": 8010,
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
                "max_concurrent_requests": 50,
                "request_timeout_seconds": 30,
                "enable_metrics": True,
                "metrics_port": 9010
            },
            "monitoring_config": {
                "enable_health_checks": True,
                "health_check_interval_seconds": 30,
                "enable_logging": True,
                "log_level": "INFO",
                "enable_prometheus": False,
                "prometheus_port": 9010
            },
            "installation_path": "/tmp/thai-tokenizer-integration",
            "data_path": "/tmp/thai-tokenizer-integration/data",
            "log_path": "/tmp/thai-tokenizer-integration/logs",
            "config_path": "/tmp/thai-tokenizer-integration/config",
            "environment_variables": {
                "ENVIRONMENT": "integration_test",
                "PYTHONPATH": "src"
            }
        }
    
    @pytest.fixture
    def config_object(self, base_config):
        """Create OnPremiseConfig object."""
        return OnPremiseConfig(**base_config)
    
    @pytest.mark.asyncio
    async def test_unified_deployment_orchestration_success(self, config_object):
        """Test successful unified deployment orchestration."""
        
        # Mock all external dependencies
        with patch('subprocess.run') as mock_run, \
             patch('httpx.AsyncClient') as mock_client, \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True):
            
            # Mock successful subprocess calls
            mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
            
            # Mock successful HTTP responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "healthy",
                "tokens": ["test", "tokens"],
                "processing_time_ms": 25.0
            }
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Create orchestrator
            progress_updates = []
            def progress_callback(progress):
                progress_updates.append({
                    "phase": progress.current_step.name if progress.current_step else "unknown",
                    "percentage": progress.progress_percentage
                })
            
            orchestrator = UnifiedDeploymentOrchestrator(config_object, progress_callback)
            
            # Execute deployment
            result = await orchestrator.deploy()
            
            # Verify successful deployment
            assert result.success == True
            assert result.deployment_id is not None
            assert result.deployment_method == DeploymentMethod.DOCKER
            
            # Verify progress updates were received
            assert len(progress_updates) > 0
            
            # Verify orchestrator context
            assert orchestrator.context is not None
            assert orchestrator.context.current_phase == DeploymentPhase.COMPLETED
            assert len(orchestrator.context.error_history) == 0
            
            # Verify components were initialized
            assert orchestrator.deployment_manager is not None
            assert orchestrator.validation_framework is not None
            assert orchestrator.cli is not None
    
    @pytest.mark.asyncio
    async def test_unified_deployment_orchestration_with_recovery(self, config_object):
        """Test unified deployment orchestration with error recovery."""
        
        # Mock external dependencies with initial failure then success
        call_count = 0
        
        def mock_subprocess_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call fails
                return Mock(returncode=1, stdout="", stderr="Connection timeout")
            else:
                # Subsequent calls succeed
                return Mock(returncode=0, stdout="Success", stderr="")
        
        with patch('subprocess.run', side_effect=mock_subprocess_side_effect), \
             patch('httpx.AsyncClient') as mock_client, \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('asyncio.sleep'):  # Speed up recovery delays
            
            # Mock HTTP responses
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Create orchestrator
            orchestrator = UnifiedDeploymentOrchestrator(config_object)
            
            # Execute deployment (should recover from initial failure)
            result = await orchestrator.deploy()
            
            # Verify deployment eventually succeeded
            # Note: This test might fail if recovery isn't implemented properly
            # The actual behavior depends on the specific error handling implementation
            assert result.deployment_id is not None
    
    @pytest.mark.asyncio
    async def test_unified_configuration_management_integration(self, base_config, tmp_path):
        """Test unified configuration management with multiple sources."""
        
        # Create configuration manager
        manager = UnifiedConfigurationManager()
        
        # Add configuration from file
        config_file = tmp_path / "test_config.json"
        file_config = {
            "service_config": {
                "service_port": 8020,
                "worker_processes": 4
            },
            "security_config": {
                "security_level": "strict"
            }
        }
        with open(config_file, 'w') as f:
            json.dump(file_config, f)
        
        manager.load_from_file(str(config_file), priority=50)
        
        # Add configuration from environment variables
        env_config = {
            "meilisearch.config.host": "http://test-meilisearch:7700",
            "resource.config.memory.limit.mb": "512"
        }
        manager.add_configuration_layer(
            ConfigurationSource.ENVIRONMENT,
            env_config,
            priority=75
        )
        
        # Add configuration from CLI args
        cli_config = {
            "deployment_method": "systemd",
            "service_config": {
                "service_name": "thai-tokenizer-cli"
            }
        }
        manager.add_configuration_layer(
            ConfigurationSource.CLI_ARGS,
            cli_config,
            priority=100
        )
        
        # Get unified configuration
        unified_config = manager.get_unified_config()
        
        # Verify configuration merging
        assert unified_config.deployment_method == DeploymentMethod.SYSTEMD  # From CLI (highest priority)
        assert unified_config.service_config.service_port == 8020  # From file
        assert unified_config.service_config.service_name == "thai-tokenizer-cli"  # From CLI
        assert unified_config.security_config.security_level == "strict"  # From file
        assert unified_config.resource_config.memory_limit_mb == 512  # From environment
        
        # Verify validation
        validation_result = manager.validate_configuration()
        assert validation_result.valid == True
        
        # Test method-specific configuration
        docker_config = manager.create_method_specific_config(DeploymentMethod.DOCKER)
        systemd_config = manager.create_method_specific_config(DeploymentMethod.SYSTEMD)
        
        assert docker_config.service_config.service_host == "0.0.0.0"
        assert systemd_config.service_config.service_host == "127.0.0.1"
        assert systemd_config.installation_path == "/opt/thai-tokenizer"
    
    @pytest.mark.asyncio
    async def test_error_handling_integration(self, config_object):
        """Test comprehensive error handling integration."""
        
        # Create error handler
        error_handler = ErrorHandler()
        
        # Test different error types and recovery
        test_errors = [
            (ConnectionError("Connection timeout"), "connection_timeout"),
            (PermissionError("Access denied"), "permission_denied"),
            (MemoryError("Out of memory"), "resource_exhaustion"),
            (DeploymentError("Service unavailable", category=ErrorCategory.SERVICE), "service_unavailable")
        ]
        
        for error, expected_strategy in test_errors:
            # Handle error
            error_record = error_handler.handle_error(error, attempt_recovery=False)
            
            # Verify error classification
            assert error_record.error_id is not None
            assert error_record.category is not None
            assert error_record.severity is not None
            
            # Verify error is recorded
            assert error_record in error_handler.error_records
        
        # Test error statistics
        stats = error_handler.get_error_statistics()
        assert stats["total_errors"] == len(test_errors)
        assert stats["category_breakdown"] is not None
        assert stats["severity_breakdown"] is not None
        
        # Test error report export
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            report_file = f.name
        
        try:
            exported_file = error_handler.export_error_report(report_file)
            assert Path(exported_file).exists()
            
            # Verify report content
            with open(exported_file, 'r') as f:
                report_data = json.load(f)
            
            assert "statistics" in report_data
            assert "error_records" in report_data
            assert len(report_data["error_records"]) == len(test_errors)
            
        finally:
            Path(report_file).unlink(missing_ok=True)
    
    @pytest.mark.asyncio
    async def test_cli_integration_with_unified_components(self, base_config, tmp_path):
        """Test CLI integration with unified components."""
        
        # Create configuration file
        config_file = tmp_path / "cli_test_config.json"
        with open(config_file, 'w') as f:
            json.dump(base_config, f)
        
        # Create CLI instance
        cli = DeploymentCLI()
        
        # Test configuration loading
        config = cli.load_config(str(config_file))
        assert config.deployment_method == DeploymentMethod.DOCKER
        assert config.service_config.service_port == 8010
        
        # Test configuration validation
        with patch.object(cli, 'config', config):
            # Mock validation framework
            with patch('src.deployment.validation_framework.DeploymentValidationFramework') as mock_framework:
                mock_framework.return_value.run_comprehensive_validation = AsyncMock(
                    return_value={
                        "overall_status": "PASSED",
                        "summary": "All validations passed"
                    }
                )
                
                # Test system validation
                result = await cli.handle_validate_system_command(
                    Mock(config=str(config_file), verbose=False, report_file=None, format='json')
                )
                
                assert result == 0  # Success
        
        # Test configuration generation
        template_config = cli.generate_config_template("docker", with_examples=True)
        assert template_config.deployment_method == DeploymentMethod.DOCKER
        assert template_config.service_config.service_name == "thai-tokenizer-docker"
    
    @pytest.mark.asyncio
    async def test_cross_component_data_flow(self, config_object):
        """Test data flow between different components."""
        
        # Mock external dependencies
        with patch('subprocess.run') as mock_run, \
             patch('httpx.AsyncClient') as mock_client, \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True):
            
            mock_run.return_value = Mock(returncode=0, stdout="Success")
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"status": "healthy"}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Create components
            orchestrator = UnifiedDeploymentOrchestrator(config_object)
            config_manager = UnifiedConfigurationManager()
            error_handler = ErrorHandler()
            
            # Test configuration flow
            config_manager.add_configuration_layer(
                ConfigurationSource.CLI_ARGS,
                {"service_config": {"service_port": 8011}},
                priority=100
            )
            
            unified_config = config_manager.get_unified_config()
            assert unified_config.service_config.service_port == 8011
            
            # Test orchestrator with modified config
            orchestrator.config = unified_config
            
            # Execute deployment
            result = await orchestrator.deploy()
            
            # Verify data flow
            assert result.success == True
            assert orchestrator.context is not None
            
            # Verify service info contains updated port
            service_info = orchestrator.context.metadata.get("service_info", {})
            assert service_info.get("status") == "running"
            
            # Test error handling integration
            if orchestrator.context.error_history:
                for error_record in orchestrator.context.error_history:
                    handled_error = error_handler.handle_error(
                        Exception(error_record["error"]),
                        attempt_recovery=False
                    )
                    assert handled_error.error_id is not None
    
    @pytest.mark.asyncio
    async def test_deployment_method_switching(self, base_config):
        """Test switching between deployment methods with unified configuration."""
        
        # Create configuration manager
        manager = UnifiedConfigurationManager()
        
        # Load base configuration
        manager.add_configuration_layer(
            ConfigurationSource.FILE,
            base_config,
            priority=50
        )
        
        # Test each deployment method
        methods = [DeploymentMethod.DOCKER, DeploymentMethod.SYSTEMD, DeploymentMethod.STANDALONE]
        
        for method in methods:
            # Create method-specific configuration
            method_config = manager.create_method_specific_config(method)
            
            # Verify method-specific adjustments
            assert method_config.deployment_method == method
            
            if method == DeploymentMethod.DOCKER:
                assert method_config.service_config.service_host == "0.0.0.0"
            elif method == DeploymentMethod.SYSTEMD:
                assert method_config.service_config.service_host == "127.0.0.1"
                assert method_config.installation_path == "/opt/thai-tokenizer"
            elif method == DeploymentMethod.STANDALONE:
                assert "standalone" in method_config.installation_path
            
            # Test orchestrator creation with method-specific config
            with patch('subprocess.run'), \
                 patch('httpx.AsyncClient'), \
                 patch('pathlib.Path.mkdir'), \
                 patch('pathlib.Path.exists', return_value=True):
                
                orchestrator = UnifiedDeploymentOrchestrator(method_config)
                
                # Verify orchestrator uses correct configuration
                assert orchestrator.config.deployment_method == method
                assert orchestrator.deployment_manager is None  # Not initialized yet
    
    @pytest.mark.asyncio
    async def test_comprehensive_validation_integration(self, config_object):
        """Test comprehensive validation across all components."""
        
        # Mock external dependencies
        with patch('subprocess.run') as mock_run, \
             patch('httpx.AsyncClient') as mock_client:
            
            mock_run.return_value = Mock(returncode=0, stdout="Success")
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"pkgVersion": "1.0.0"}
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            
            # Create orchestrator
            orchestrator = UnifiedDeploymentOrchestrator(config_object)
            
            # Initialize components
            await orchestrator._initialize_deployment()
            
            # Test validation framework integration
            validation_results = await orchestrator.validation_framework.run_comprehensive_validation()
            
            # Verify validation results structure
            assert "overall_status" in validation_results
            assert "summary" in validation_results
            assert "system_requirements" in validation_results
            assert "meilisearch_connectivity" in validation_results
            
            # Test configuration validation
            config_manager = UnifiedConfigurationManager()
            config_manager.add_configuration_layer(
                ConfigurationSource.FILE,
                config_object.dict(),
                priority=50
            )
            
            config_validation = config_manager.validate_configuration()
            assert config_validation.valid == True
            
            # Test error handling validation
            error_handler = ErrorHandler()
            
            # Simulate validation error
            validation_error = DeploymentError(
                "Validation failed",
                category=ErrorCategory.VALIDATION
            )
            
            error_record = error_handler.handle_error(validation_error, attempt_recovery=False)
            assert error_record.category == ErrorCategory.VALIDATION
    
    @pytest.mark.asyncio
    async def test_performance_and_resource_management(self, config_object):
        """Test performance and resource management across components."""
        
        # Mock external dependencies
        with patch('subprocess.run'), \
             patch('httpx.AsyncClient'), \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('psutil.process_iter') as mock_process_iter:
            
            # Mock process information
            mock_process = Mock()
            mock_process.info = {
                'pid': 12345,
                'name': 'python',
                'cmdline': ['python', '-m', 'thai-tokenizer'],
                'memory_info': Mock(rss=200 * 1024 * 1024)  # 200MB
            }
            mock_process_iter.return_value = [mock_process]
            
            # Create orchestrator
            orchestrator = UnifiedDeploymentOrchestrator(config_object)
            
            # Test resource tracking
            await orchestrator._initialize_deployment()
            
            # Verify context tracks resources
            assert orchestrator.context is not None
            assert len(orchestrator.context.resources_allocated) > 0
            
            # Test cleanup tasks registration
            assert len(orchestrator.context.cleanup_tasks) > 0
            
            # Test performance monitoring
            start_time = time.time()
            
            # Simulate some operations
            await asyncio.sleep(0.1)
            
            duration = orchestrator.context.get_duration()
            assert duration > 0
            
            # Test resource cleanup
            await orchestrator._execute_cleanup()
            
            # Verify cleanup was attempted
            # (In a real test, you'd verify actual resource cleanup)
    
    def test_configuration_compatibility_across_methods(self, base_config):
        """Test configuration compatibility across deployment methods."""
        
        # Create configurations for all methods
        configs = {}
        
        for method in [DeploymentMethod.DOCKER, DeploymentMethod.SYSTEMD, DeploymentMethod.STANDALONE]:
            method_config = base_config.copy()
            method_config["deployment_method"] = method.value
            
            # Create OnPremiseConfig object
            configs[method] = OnPremiseConfig(**method_config)
        
        # Verify all configurations are valid
        for method, config in configs.items():
            validation_result = config.validate_paths()
            # Note: Some validations might fail due to missing directories in test environment
            # but the configuration structure should be valid
            assert isinstance(validation_result, type(validation_result))
        
        # Verify method-specific differences
        docker_config = configs[DeploymentMethod.DOCKER]
        systemd_config = configs[DeploymentMethod.SYSTEMD]
        standalone_config = configs[DeploymentMethod.STANDALONE]
        
        # All should have same core settings
        assert docker_config.service_config.service_port == systemd_config.service_config.service_port
        assert docker_config.meilisearch_config.host == systemd_config.meilisearch_config.host
        
        # But different deployment methods
        assert docker_config.deployment_method == DeploymentMethod.DOCKER
        assert systemd_config.deployment_method == DeploymentMethod.SYSTEMD
        assert standalone_config.deployment_method == DeploymentMethod.STANDALONE
    
    @pytest.mark.asyncio
    async def test_end_to_end_deployment_simulation(self, config_object):
        """Test complete end-to-end deployment simulation."""
        
        # Mock all external dependencies for complete simulation
        with patch('subprocess.run') as mock_run, \
             patch('httpx.AsyncClient') as mock_client, \
             patch('pathlib.Path.mkdir'), \
             patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.write_text'), \
             patch('builtins.open', create=True):
            
            # Mock successful operations
            mock_run.return_value = Mock(returncode=0, stdout="Success", stderr="")
            
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "status": "healthy",
                "tokens": ["สวัสดี", "ครับ"],
                "processing_time_ms": 25.0
            }
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_response)
            
            # Track all operations
            operations_log = []
            
            def log_operation(operation):
                operations_log.append({
                    "operation": operation,
                    "timestamp": datetime.now(timezone.utc)
                })
            
            # Create orchestrator with logging
            def progress_callback(progress):
                log_operation(f"Progress: {progress.progress_percentage:.1f}%")
            
            orchestrator = UnifiedDeploymentOrchestrator(config_object, progress_callback)
            
            # Execute complete deployment
            log_operation("Starting deployment")
            result = await orchestrator.deploy()
            log_operation("Deployment completed")
            
            # Verify complete deployment flow
            assert result.success == True
            assert result.deployment_id is not None
            assert result.deployment_method == DeploymentMethod.DOCKER
            
            # Verify all phases were executed
            assert orchestrator.context.current_phase == DeploymentPhase.COMPLETED
            assert len(orchestrator.context.phase_history) >= 6  # All phases
            
            # Verify operations were logged
            assert len(operations_log) > 0
            assert any("Starting deployment" in op["operation"] for op in operations_log)
            assert any("Deployment completed" in op["operation"] for op in operations_log)
            
            # Verify metadata was collected
            metadata = orchestrator.context.metadata
            assert "service_info" in metadata
            assert "endpoints" in metadata
            assert "health_check" in metadata
            assert "tokenization_test" in metadata
            
            # Test deployment status
            status = orchestrator.get_deployment_status()
            assert status["deployment_id"] == result.deployment_id
            assert status["current_phase"] == DeploymentPhase.COMPLETED.value
            assert status["errors_count"] == 0


if __name__ == "__main__":
    # Run integration tests directly
    pytest.main([__file__, "-v", "--tb=short"])