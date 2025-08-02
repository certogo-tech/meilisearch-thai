#!/usr/bin/env python3
"""
Integration tests for deployment orchestration system.

Tests the DeploymentManager and validation framework components.
"""

import asyncio
import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from src.deployment.config import OnPremiseConfig, DeploymentMethod
from src.deployment.deployment_manager import DeploymentManager, DeploymentMethodFactory
from src.deployment.validation_framework import (
    DeploymentValidationFramework, SystemRequirementsValidator,
    MeilisearchConnectivityTester, ThaiTokenizationValidator,
    PerformanceBenchmarkRunner
)


class TestDeploymentOrchestration:
    """Test deployment orchestration system."""
    
    @pytest.fixture
    def sample_config(self):
        """Create sample deployment configuration."""
        return {
            "deployment_method": "docker",
            "meilisearch_config": {
                "host": "http://localhost:7700",
                "port": 7700,
                "api_key": "test-api-key",
                "ssl_enabled": False,
                "ssl_verify": True,
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0
            },
            "service_config": {
                "service_name": "thai-tokenizer-test",
                "service_port": 8001,
                "service_host": "0.0.0.0",
                "worker_processes": 2,
                "service_user": "thai-tokenizer",
                "service_group": "thai-tokenizer"
            },
            "security_config": {
                "security_level": "standard",
                "allowed_hosts": ["*"],
                "cors_origins": ["*"],
                "api_key_required": False,
                "enable_https": False
            },
            "resource_config": {
                "memory_limit_mb": 256,
                "cpu_limit_cores": 0.5,
                "max_concurrent_requests": 50,
                "request_timeout_seconds": 30,
                "enable_metrics": True,
                "metrics_port": 9091
            },
            "monitoring_config": {
                "enable_health_checks": True,
                "health_check_interval_seconds": 30,
                "enable_logging": True,
                "log_level": "INFO",
                "enable_prometheus": False,
                "prometheus_port": 9091
            },
            "installation_path": "/tmp/thai-tokenizer-test",
            "data_path": "/tmp/thai-tokenizer-test/data",
            "log_path": "/tmp/thai-tokenizer-test/logs",
            "config_path": "/tmp/thai-tokenizer-test/config",
            "environment_variables": {}
        }
    
    @pytest.fixture
    def config_object(self, sample_config):
        """Create OnPremiseConfig object."""
        return OnPremiseConfig(**sample_config)
    
    def test_config_validation(self, sample_config):
        """Test configuration validation."""
        # Valid configuration should work
        config = OnPremiseConfig(**sample_config)
        assert config.deployment_method == DeploymentMethod.DOCKER
        assert config.service_config.service_name == "thai-tokenizer-test"
        assert config.service_config.service_port == 8001
        
        # Test environment variable generation
        env_vars = config.get_environment_dict()
        assert "THAI_TOKENIZER_SERVICE_NAME" in env_vars
        assert "THAI_TOKENIZER_SERVICE_PORT" in env_vars
        assert "THAI_TOKENIZER_MEILISEARCH_HOST" in env_vars
        
        # Test path validation
        path_validation = config.validate_paths()
        # Should be valid since we're using /tmp paths
        assert path_validation.valid or len(path_validation.errors) == 0
    
    def test_deployment_method_factory(self, config_object):
        """Test deployment method factory."""
        # Test Docker deployment creation
        docker_deployment = DeploymentMethodFactory.create_deployment(
            DeploymentMethod.DOCKER, config_object
        )
        assert docker_deployment is not None
        assert hasattr(docker_deployment, 'validate_requirements')
        
        # Test systemd deployment creation
        systemd_deployment = DeploymentMethodFactory.create_deployment(
            DeploymentMethod.SYSTEMD, config_object
        )
        assert systemd_deployment is not None
        assert hasattr(systemd_deployment, 'validate_requirements')
        
        # Test standalone deployment creation
        standalone_deployment = DeploymentMethodFactory.create_deployment(
            DeploymentMethod.STANDALONE, config_object
        )
        assert standalone_deployment is not None
        assert hasattr(standalone_deployment, 'validate_requirements')
        
        # Test invalid deployment method
        with pytest.raises(ValueError):
            DeploymentMethodFactory.create_deployment("invalid", config_object)
    
    @pytest.mark.asyncio
    async def test_deployment_manager_initialization(self, config_object):
        """Test deployment manager initialization."""
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append(progress)
        
        manager = DeploymentManager(config_object, progress_callback)
        
        assert manager.config == config_object
        assert manager.progress_callback == progress_callback
        assert manager.deployment is not None
        assert manager.progress.deployment_method == config_object.deployment_method
        assert len(manager.progress.steps) > 0
    
    @pytest.mark.asyncio
    async def test_system_requirements_validator(self, config_object):
        """Test system requirements validation."""
        validator = SystemRequirementsValidator()
        
        # Test requirement definition
        assert len(validator.requirements) > 0
        
        # Check that basic requirements are defined
        requirement_names = [req.name for req in validator.requirements]
        assert "python_version" in requirement_names
        assert "available_memory" in requirement_names
        assert "available_disk_space" in requirement_names
        
        # Test validation (this will actually check the system)
        results = await validator.validate_all_requirements(config_object)
        assert len(results) > 0
        
        # At least Python version should be satisfied
        python_result = next(
            (r for r in results if r.requirement.name == "python_version"), 
            None
        )
        assert python_result is not None
        # Note: This might fail if Python version is too old, but that's expected
    
    @pytest.mark.asyncio
    async def test_meilisearch_connectivity_tester(self, config_object):
        """Test Meilisearch connectivity testing."""
        tester = MeilisearchConnectivityTester(config_object)
        
        # Test basic connectivity (will likely fail without actual Meilisearch)
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"pkgVersion": "1.0.0"}
            
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            result = await tester.test_basic_connectivity()
            assert result.valid == True
    
    @pytest.mark.asyncio
    async def test_thai_tokenization_validator(self):
        """Test Thai tokenization validation."""
        validator = ThaiTokenizationValidator()
        
        # Test test case definition
        assert len(validator.test_cases) > 0
        
        # Check that basic test cases are defined
        test_names = [test.name for test in validator.test_cases]
        assert "basic_thai_text" in test_names
        assert "compound_words" in test_names
        assert "mixed_thai_english" in test_names
        
        # Test validation with mocked service
        with patch('httpx.AsyncClient') as mock_client:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "tokens": ["สวัสดี", "ครับ", "ผม", "ชื่อ", "จอห์น"]
            }
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            
            results = await validator.validate_tokenization_functionality("http://localhost:8000")
            assert len(results) > 0
            
            # All tests should succeed with mocked response
            successful_tests = [r for r in results if r.success]
            assert len(successful_tests) > 0
    
    @pytest.mark.asyncio
    async def test_performance_benchmark_runner(self, config_object):
        """Test performance benchmark runner."""
        runner = PerformanceBenchmarkRunner()
        
        # Test benchmark definition
        assert len(runner.benchmarks) > 0
        
        # Check that basic benchmarks are defined
        benchmark_names = [bench.name for bench in runner.benchmarks]
        assert "tokenization_response_time" in benchmark_names
        assert "memory_usage" in benchmark_names
        
        # Test benchmark execution with mocked service
        with patch('httpx.AsyncClient') as mock_client, \
             patch('psutil.process_iter') as mock_process_iter:
            
            # Mock HTTP response
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"tokens": ["test"]}
            
            mock_client.return_value.__aenter__.return_value.post = AsyncMock(
                return_value=mock_response
            )
            mock_client.return_value.__aenter__.return_value.get = AsyncMock(
                return_value=mock_response
            )
            
            # Mock process information
            mock_process = Mock()
            mock_process.info = {
                'pid': 1234,
                'name': 'python',
                'cmdline': ['python', '-m', 'thai-tokenizer-test'],
                'memory_info': Mock(rss=256 * 1024 * 1024)  # 256MB
            }
            mock_process_iter.return_value = [mock_process]
            
            results = await runner.run_performance_benchmarks("http://localhost:8000", config_object)
            assert len(results) > 0
    
    @pytest.mark.asyncio
    async def test_deployment_validation_framework(self, config_object):
        """Test comprehensive deployment validation framework."""
        framework = DeploymentValidationFramework(config_object)
        
        # Test framework initialization
        assert framework.config == config_object
        assert framework.requirements_validator is not None
        assert framework.meilisearch_tester is not None
        assert framework.tokenization_validator is not None
        assert framework.benchmark_runner is not None
        
        # Test comprehensive validation with mocked components
        with patch.object(framework.requirements_validator, 'validate_all_requirements') as mock_req, \
             patch.object(framework.meilisearch_tester, 'test_basic_connectivity') as mock_ms_basic, \
             patch.object(framework.meilisearch_tester, 'test_api_permissions') as mock_ms_api, \
             patch.object(framework.meilisearch_tester, 'test_index_operations') as mock_ms_index, \
             patch.object(framework.meilisearch_tester, 'test_performance') as mock_ms_perf:
            
            # Mock successful validation results
            from src.deployment.config import ValidationResult
            from src.deployment.validation_framework import RequirementCheckResult, SystemRequirement
            
            mock_req.return_value = [
                RequirementCheckResult(
                    requirement=SystemRequirement(name="test", description="Test requirement"),
                    satisfied=True
                )
            ]
            
            mock_ms_basic.return_value = ValidationResult(valid=True, warnings=["Connected"])
            mock_ms_api.return_value = ValidationResult(valid=True, warnings=["API OK"])
            mock_ms_index.return_value = ValidationResult(valid=True, warnings=["Index OK"])
            mock_ms_perf.return_value = ValidationResult(valid=True, warnings=["Performance OK"])
            
            results = await framework.run_comprehensive_validation()
            
            assert results is not None
            assert "timestamp" in results
            assert "system_requirements" in results
            assert "meilisearch_connectivity" in results
            assert "overall_status" in results
            assert "summary" in results
    
    @pytest.mark.asyncio
    async def test_deployment_manager_mock_deployment(self, config_object):
        """Test deployment manager with mocked deployment methods."""
        progress_updates = []
        
        def progress_callback(progress):
            progress_updates.append(progress)
        
        manager = DeploymentManager(config_object, progress_callback)
        
        # Mock all deployment interface methods to return success
        with patch.object(manager.deployment, 'validate_requirements') as mock_validate, \
             patch.object(manager.deployment, 'install_dependencies') as mock_install, \
             patch.object(manager.deployment, 'configure_service') as mock_configure, \
             patch.object(manager.deployment, 'start_service') as mock_start, \
             patch.object(manager.deployment, 'verify_deployment') as mock_verify, \
             patch.object(manager, '_validate_configuration') as mock_config_validate, \
             patch.object(manager, '_gather_service_info') as mock_service_info:
            
            from src.deployment.config import ValidationResult
            
            # Mock successful results
            success_result = ValidationResult(valid=True, warnings=["Success"])
            
            mock_validate.return_value = success_result
            mock_install.return_value = success_result
            mock_configure.return_value = success_result
            mock_start.return_value = success_result
            mock_verify.return_value = success_result
            mock_config_validate.return_value = success_result
            mock_service_info.return_value = {"status": "healthy"}
            
            # Execute deployment
            result = await manager.deploy()
            
            # Verify deployment result
            assert result.success == True
            assert result.deployment_id is not None
            assert result.deployment_method == config_object.deployment_method
            assert result.progress.overall_status.value == "completed"
            
            # Verify progress updates were called
            assert len(progress_updates) > 0
            
            # Verify all deployment methods were called
            mock_validate.assert_called_once()
            mock_install.assert_called_once()
            mock_configure.assert_called_once()
            mock_start.assert_called_once()
            mock_verify.assert_called_once()
    
    def test_cli_config_loading(self, sample_config):
        """Test CLI configuration loading."""
        from src.deployment.cli import DeploymentCLI
        
        cli = DeploymentCLI()
        
        # Create temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config, f, indent=2)
            config_path = f.name
        
        try:
            # Test loading configuration
            config = cli.load_config(config_path)
            assert config.deployment_method == DeploymentMethod.DOCKER
            assert config.service_config.service_name == "thai-tokenizer-test"
            
        finally:
            # Clean up
            Path(config_path).unlink()
    
    def test_cli_parser_creation(self):
        """Test CLI argument parser creation."""
        from src.deployment.cli import DeploymentCLI
        
        cli = DeploymentCLI()
        parser = cli.create_parser()
        
        # Test that parser was created
        assert parser is not None
        
        # Test parsing valid arguments
        args = parser.parse_args([
            "--config", "test.json",
            "validate-system"
        ])
        
        assert args.config == "test.json"
        assert args.command == "validate-system"
        assert args.verbose == False
        
        # Test parsing deploy command with options
        args = parser.parse_args([
            "--config", "test.json",
            "--verbose",
            "deploy",
            "--method", "docker",
            "--progress-file", "progress.json"
        ])
        
        assert args.config == "test.json"
        assert args.command == "deploy"
        assert args.verbose == True
        assert args.method == "docker"
        assert args.progress_file == "progress.json"


if __name__ == "__main__":
    # Run tests directly
    pytest.main([__file__, "-v"])