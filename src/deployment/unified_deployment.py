#!/usr/bin/env python3
"""
Unified Deployment Interface for Thai Tokenizer On-Premise Deployment.

This module provides a unified interface that integrates all deployment methods,
components, and utilities into a cohesive system with comprehensive error handling,
recovery mechanisms, and validation.
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Callable
from datetime import datetime, timezone
from enum import Enum
import json
import traceback

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from deployment.config import OnPremiseConfig, DeploymentMethod, ValidationResult
from deployment.deployment_manager import DeploymentManager, DeploymentResult
from deployment.validation_framework import DeploymentValidationFramework
from deployment.cli import DeploymentCLI
from utils.logging import get_structured_logger


class DeploymentPhase(str, Enum):
    """Deployment phase enumeration."""
    INITIALIZATION = "initialization"
    VALIDATION = "validation"
    PREPARATION = "preparation"
    EXECUTION = "execution"
    VERIFICATION = "verification"
    FINALIZATION = "finalization"
    CLEANUP = "cleanup"
    COMPLETED = "completed"
    FAILED = "failed"


class DeploymentContext:
    """Deployment context for tracking state and resources."""
    
    def __init__(self, config: OnPremiseConfig, deployment_id: str):
        self.config = config
        self.deployment_id = deployment_id
        self.start_time = datetime.now(timezone.utc)
        self.current_phase = DeploymentPhase.INITIALIZATION
        self.resources_allocated = []
        self.cleanup_tasks = []
        self.error_history = []
        self.phase_history = []
        self.metadata = {}
    
    def add_resource(self, resource_type: str, resource_id: str, cleanup_func: Optional[Callable] = None):
        """Add a resource to track for cleanup."""
        resource = {
            "type": resource_type,
            "id": resource_id,
            "allocated_at": datetime.now(timezone.utc),
            "cleanup_func": cleanup_func
        }
        self.resources_allocated.append(resource)
    
    def add_cleanup_task(self, task_name: str, cleanup_func: Callable):
        """Add a cleanup task to execute on failure or completion."""
        self.cleanup_tasks.append({
            "name": task_name,
            "func": cleanup_func,
            "added_at": datetime.now(timezone.utc)
        })
    
    def record_error(self, error: Exception, phase: DeploymentPhase, context: Dict[str, Any] = None):
        """Record an error with context."""
        error_record = {
            "error": str(error),
            "error_type": type(error).__name__,
            "phase": phase.value,
            "timestamp": datetime.now(timezone.utc),
            "traceback": traceback.format_exc(),
            "context": context or {}
        }
        self.error_history.append(error_record)
    
    def transition_phase(self, new_phase: DeploymentPhase):
        """Transition to a new deployment phase."""
        self.phase_history.append({
            "from_phase": self.current_phase.value,
            "to_phase": new_phase.value,
            "timestamp": datetime.now(timezone.utc)
        })
        self.current_phase = new_phase
    
    def get_duration(self) -> float:
        """Get total deployment duration in seconds."""
        return (datetime.now(timezone.utc) - self.start_time).total_seconds()


class UnifiedDeploymentOrchestrator:
    """Unified deployment orchestrator that integrates all components."""
    
    def __init__(self, config: OnPremiseConfig, progress_callback: Optional[Callable] = None):
        self.config = config
        self.progress_callback = progress_callback or (lambda x: None)
        self.logger = get_structured_logger(__name__)
        
        # Initialize components
        self.deployment_manager = None
        self.validation_framework = None
        self.cli = None
        
        # Deployment context
        self.context = None
        
        # Error recovery strategies
        self.recovery_strategies = self._initialize_recovery_strategies()
        
        # Component registry
        self.components = {}
    
    def _initialize_recovery_strategies(self) -> Dict[str, Callable]:
        """Initialize error recovery strategies."""
        return {
            "connection_timeout": self._recover_connection_timeout,
            "permission_denied": self._recover_permission_denied,
            "resource_exhausted": self._recover_resource_exhausted,
            "service_unavailable": self._recover_service_unavailable,
            "configuration_invalid": self._recover_configuration_invalid,
            "deployment_failed": self._recover_deployment_failed
        }
    
    async def deploy(self, deployment_id: Optional[str] = None) -> DeploymentResult:
        """Execute unified deployment with comprehensive error handling."""
        
        # Initialize deployment context
        deployment_id = deployment_id or f"deploy-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        self.context = DeploymentContext(self.config, deployment_id)
        
        self.logger.info(f"Starting unified deployment: {deployment_id}")
        
        try:
            # Phase 1: Initialization
            await self._execute_phase(DeploymentPhase.INITIALIZATION, self._initialize_deployment)
            
            # Phase 2: Validation
            await self._execute_phase(DeploymentPhase.VALIDATION, self._validate_deployment)
            
            # Phase 3: Preparation
            await self._execute_phase(DeploymentPhase.PREPARATION, self._prepare_deployment)
            
            # Phase 4: Execution
            await self._execute_phase(DeploymentPhase.EXECUTION, self._execute_deployment)
            
            # Phase 5: Verification
            await self._execute_phase(DeploymentPhase.VERIFICATION, self._verify_deployment)
            
            # Phase 6: Finalization
            await self._execute_phase(DeploymentPhase.FINALIZATION, self._finalize_deployment)
            
            # Mark as completed
            self.context.transition_phase(DeploymentPhase.COMPLETED)
            
            # Create successful result
            result = DeploymentResult(
                success=True,
                deployment_id=deployment_id,
                deployment_method=self.config.deployment_method,
                progress=self.deployment_manager.progress if self.deployment_manager else None,
                service_info=self.context.metadata.get("service_info", {}),
                endpoints=self.context.metadata.get("endpoints", {}),
                configuration_path=str(self.config.config_path) if hasattr(self.config, 'config_path') else None,
                log_file_path=self.context.metadata.get("log_file_path"),
                rollback_available=True
            )
            
            self.logger.info(f"Unified deployment completed successfully: {deployment_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Unified deployment failed: {e}")
            self.context.record_error(e, self.context.current_phase)
            self.context.transition_phase(DeploymentPhase.FAILED)
            
            # Attempt recovery
            recovery_result = await self._attempt_recovery(e)
            
            if not recovery_result:
                # Execute cleanup
                await self._execute_cleanup()
            
            # Create failed result
            result = DeploymentResult(
                success=False,
                deployment_id=deployment_id,
                deployment_method=self.config.deployment_method,
                progress=self.deployment_manager.progress if self.deployment_manager else None,
                service_info={},
                endpoints={},
                configuration_path=None,
                log_file_path=None,
                rollback_available=False
            )
            
            return result
    
    async def _execute_phase(self, phase: DeploymentPhase, phase_func: Callable):
        """Execute a deployment phase with error handling."""
        self.context.transition_phase(phase)
        self.logger.info(f"Executing phase: {phase.value}")
        
        try:
            await phase_func()
            self.logger.info(f"Phase completed successfully: {phase.value}")
            
        except Exception as e:
            self.logger.error(f"Phase failed: {phase.value} - {e}")
            self.context.record_error(e, phase)
            raise
    
    async def _initialize_deployment(self):
        """Initialize deployment components and resources."""
        self.logger.info("Initializing deployment components")
        
        try:
            # Initialize deployment manager
            self.deployment_manager = DeploymentManager(self.config, self.progress_callback)
            self.components["deployment_manager"] = self.deployment_manager
            
            # Initialize validation framework
            self.validation_framework = DeploymentValidationFramework(self.config)
            self.components["validation_framework"] = self.validation_framework
            
            # Initialize CLI (for utility functions)
            self.cli = DeploymentCLI()
            self.components["cli"] = self.cli
            
            # Create necessary directories
            directories = [
                self.config.installation_path,
                self.config.data_path,
                self.config.log_path,
                self.config.config_path
            ]
            
            for directory in directories:
                dir_path = Path(directory)
                dir_path.mkdir(parents=True, exist_ok=True)
                self.context.add_resource("directory", str(dir_path))
            
            # Register cleanup tasks
            self.context.add_cleanup_task("cleanup_deployment_manager", self._cleanup_deployment_manager)
            
            self.logger.info("Deployment components initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize deployment components: {e}")
            raise
    
    async def _validate_deployment(self):
        """Validate deployment configuration and requirements."""
        self.logger.info("Validating deployment configuration and requirements")
        
        try:
            # Run comprehensive validation
            validation_results = await self.validation_framework.run_comprehensive_validation()
            
            # Store validation results
            self.context.metadata["validation_results"] = validation_results
            
            # Check validation status
            overall_status = validation_results.get("overall_status", "FAILED")
            
            if overall_status == "FAILED":
                failed_validations = []
                
                # Collect failed validations
                for category, results in validation_results.items():
                    if isinstance(results, dict) and "results" in results:
                        for result in results["results"]:
                            if not result.get("success", result.get("satisfied", False)):
                                failed_validations.append(f"{category}: {result.get('requirement', {}).get('name', 'Unknown')}")
                
                raise ValueError(f"Validation failed: {', '.join(failed_validations)}")
            
            elif overall_status == "WARNING":
                self.logger.warning("Validation completed with warnings")
                # Continue deployment but log warnings
                
            self.logger.info("Deployment validation completed successfully")
            
        except Exception as e:
            self.logger.error(f"Deployment validation failed: {e}")
            raise
    
    async def _prepare_deployment(self):
        """Prepare deployment environment and resources."""
        self.logger.info("Preparing deployment environment")
        
        try:
            # Validate deployment method requirements
            deployment = self.deployment_manager.deployment
            
            # Check method-specific requirements
            requirements_result = await deployment.validate_requirements()
            if not requirements_result.valid:
                raise ValueError(f"Deployment method requirements not met: {requirements_result.errors}")
            
            # Install dependencies
            dependencies_result = await deployment.install_dependencies()
            if not dependencies_result.valid:
                raise ValueError(f"Failed to install dependencies: {dependencies_result.errors}")
            
            # Configure service
            configure_result = await deployment.configure_service(self.config)
            if not configure_result.valid:
                raise ValueError(f"Failed to configure service: {configure_result.errors}")
            
            self.logger.info("Deployment environment prepared successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to prepare deployment environment: {e}")
            raise
    
    async def _execute_deployment(self):
        """Execute the actual deployment."""
        self.logger.info("Executing deployment")
        
        try:
            # Start the service
            deployment = self.deployment_manager.deployment
            start_result = await deployment.start_service()
            
            if not start_result.valid:
                raise ValueError(f"Failed to start service: {start_result.errors}")
            
            # Store service information
            self.context.metadata["service_info"] = {
                "status": "running",
                "start_time": datetime.now(timezone.utc).isoformat(),
                "method": self.config.deployment_method.value
            }
            
            # Register service for cleanup
            self.context.add_resource("service", self.config.service_config.service_name)
            self.context.add_cleanup_task("stop_service", self._cleanup_service)
            
            self.logger.info("Deployment executed successfully")
            
        except Exception as e:
            self.logger.error(f"Deployment execution failed: {e}")
            raise
    
    async def _verify_deployment(self):
        """Verify deployment is working correctly."""
        self.logger.info("Verifying deployment")
        
        try:
            # Verify deployment using deployment manager
            deployment = self.deployment_manager.deployment
            verify_result = await deployment.verify_deployment()
            
            if not verify_result.valid:
                raise ValueError(f"Deployment verification failed: {verify_result.errors}")
            
            # Additional verification tests
            await self._run_verification_tests()
            
            self.logger.info("Deployment verification completed successfully")
            
        except Exception as e:
            self.logger.error(f"Deployment verification failed: {e}")
            raise
    
    async def _run_verification_tests(self):
        """Run additional verification tests."""
        try:
            # Test service health
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            
            # Import test utilities
            import httpx
            
            # Basic health check
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(f"{service_url}/health", timeout=30.0)
                    if response.status_code != 200:
                        raise ValueError(f"Health check failed: HTTP {response.status_code}")
                    
                    health_data = response.json()
                    self.context.metadata["health_check"] = health_data
                    
                except httpx.RequestError as e:
                    raise ValueError(f"Health check request failed: {e}")
            
            # Test Thai tokenization
            async with httpx.AsyncClient() as client:
                try:
                    test_text = "สวัสดีครับ"
                    response = await client.post(
                        f"{service_url}/v1/tokenize",
                        json={"text": test_text},
                        timeout=30.0
                    )
                    
                    if response.status_code != 200:
                        raise ValueError(f"Tokenization test failed: HTTP {response.status_code}")
                    
                    tokenization_data = response.json()
                    if not tokenization_data.get("tokens"):
                        raise ValueError("Tokenization test failed: No tokens returned")
                    
                    self.context.metadata["tokenization_test"] = tokenization_data
                    
                except httpx.RequestError as e:
                    raise ValueError(f"Tokenization test request failed: {e}")
            
            # Store endpoints
            self.context.metadata["endpoints"] = {
                "health": f"{service_url}/health",
                "tokenize": f"{service_url}/v1/tokenize",
                "metrics": f"{service_url}/metrics" if self.config.resource_config.enable_metrics else None
            }
            
        except Exception as e:
            self.logger.error(f"Verification tests failed: {e}")
            raise
    
    async def _finalize_deployment(self):
        """Finalize deployment and clean up temporary resources."""
        self.logger.info("Finalizing deployment")
        
        try:
            # Generate deployment summary
            summary = {
                "deployment_id": self.context.deployment_id,
                "deployment_method": self.config.deployment_method.value,
                "start_time": self.context.start_time.isoformat(),
                "duration_seconds": self.context.get_duration(),
                "phases_completed": [p["to_phase"] for p in self.context.phase_history],
                "resources_allocated": len(self.context.resources_allocated),
                "service_info": self.context.metadata.get("service_info", {}),
                "endpoints": self.context.metadata.get("endpoints", {})
            }
            
            # Save deployment summary
            summary_file = Path(self.config.log_path) / f"deployment_summary_{self.context.deployment_id}.json"
            with open(summary_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            
            self.context.metadata["summary_file"] = str(summary_file)
            self.context.metadata["log_file_path"] = str(summary_file)
            
            self.logger.info("Deployment finalized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to finalize deployment: {e}")
            raise
    
    async def _attempt_recovery(self, error: Exception) -> bool:
        """Attempt to recover from deployment error."""
        self.logger.info(f"Attempting recovery from error: {error}")
        
        try:
            # Determine error type and recovery strategy
            error_type = self._classify_error(error)
            
            if error_type in self.recovery_strategies:
                recovery_func = self.recovery_strategies[error_type]
                recovery_result = await recovery_func(error)
                
                if recovery_result:
                    self.logger.info(f"Recovery successful for error type: {error_type}")
                    return True
                else:
                    self.logger.warning(f"Recovery failed for error type: {error_type}")
            else:
                self.logger.warning(f"No recovery strategy available for error type: {error_type}")
            
            return False
            
        except Exception as recovery_error:
            self.logger.error(f"Recovery attempt failed: {recovery_error}")
            return False
    
    def _classify_error(self, error: Exception) -> str:
        """Classify error for recovery strategy selection."""
        error_str = str(error).lower()
        error_type = type(error).__name__.lower()
        
        if "timeout" in error_str or "connection" in error_str:
            return "connection_timeout"
        elif "permission" in error_str or "access" in error_str:
            return "permission_denied"
        elif "memory" in error_str or "resource" in error_str:
            return "resource_exhausted"
        elif "unavailable" in error_str or "refused" in error_str:
            return "service_unavailable"
        elif "configuration" in error_str or "config" in error_str:
            return "configuration_invalid"
        elif "deployment" in error_str:
            return "deployment_failed"
        else:
            return "unknown_error"
    
    async def _recover_connection_timeout(self, error: Exception) -> bool:
        """Recover from connection timeout errors."""
        self.logger.info("Attempting connection timeout recovery")
        
        try:
            # Wait and retry
            await asyncio.sleep(10)
            
            # Test Meilisearch connectivity
            from deployment.validation_framework import MeilisearchConnectivityTester
            tester = MeilisearchConnectivityTester(self.config)
            result = await tester.test_basic_connectivity()
            
            return result.valid
            
        except Exception:
            return False
    
    async def _recover_permission_denied(self, error: Exception) -> bool:
        """Recover from permission denied errors."""
        self.logger.info("Attempting permission recovery")
        
        try:
            # Check if running with sufficient privileges
            if self.config.deployment_method == DeploymentMethod.SYSTEMD:
                if os.geteuid() != 0:
                    self.logger.error("systemd deployment requires root privileges")
                    return False
            
            # Attempt to fix directory permissions
            directories = [
                self.config.installation_path,
                self.config.data_path,
                self.config.log_path,
                self.config.config_path
            ]
            
            for directory in directories:
                dir_path = Path(directory)
                if dir_path.exists():
                    try:
                        os.chmod(dir_path, 0o755)
                    except PermissionError:
                        continue
            
            return True
            
        except Exception:
            return False
    
    async def _recover_resource_exhausted(self, error: Exception) -> bool:
        """Recover from resource exhaustion errors."""
        self.logger.info("Attempting resource exhaustion recovery")
        
        try:
            # Reduce resource limits
            if hasattr(self.config, 'resource_config'):
                self.config.resource_config.memory_limit_mb = min(
                    self.config.resource_config.memory_limit_mb, 128
                )
                self.config.resource_config.max_concurrent_requests = min(
                    self.config.resource_config.max_concurrent_requests, 10
                )
            
            return True
            
        except Exception:
            return False
    
    async def _recover_service_unavailable(self, error: Exception) -> bool:
        """Recover from service unavailable errors."""
        self.logger.info("Attempting service unavailable recovery")
        
        try:
            # Wait for service to become available
            await asyncio.sleep(30)
            
            # Test service availability
            import httpx
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            
            async with httpx.AsyncClient() as client:
                try:
                    response = await client.get(f"{service_url}/health", timeout=10.0)
                    return response.status_code == 200
                except:
                    return False
            
        except Exception:
            return False
    
    async def _recover_configuration_invalid(self, error: Exception) -> bool:
        """Recover from configuration invalid errors."""
        self.logger.info("Attempting configuration recovery")
        
        try:
            # Validate and fix configuration
            validation_result = self.config.validate_paths()
            
            if not validation_result.valid:
                # Attempt to create missing directories
                directories = [
                    self.config.installation_path,
                    self.config.data_path,
                    self.config.log_path,
                    self.config.config_path
                ]
                
                for directory in directories:
                    Path(directory).mkdir(parents=True, exist_ok=True)
                
                # Re-validate
                validation_result = self.config.validate_paths()
                return validation_result.valid
            
            return True
            
        except Exception:
            return False
    
    async def _recover_deployment_failed(self, error: Exception) -> bool:
        """Recover from general deployment failures."""
        self.logger.info("Attempting deployment failure recovery")
        
        try:
            # Clean up partial deployment
            await self._execute_cleanup()
            
            # Wait before retry
            await asyncio.sleep(60)
            
            # This would typically trigger a retry, but for now just return False
            # to indicate that manual intervention is needed
            return False
            
        except Exception:
            return False
    
    async def _execute_cleanup(self):
        """Execute cleanup tasks."""
        self.logger.info("Executing cleanup tasks")
        
        try:
            # Execute registered cleanup tasks
            for task in reversed(self.context.cleanup_tasks):  # Reverse order for proper cleanup
                try:
                    self.logger.info(f"Executing cleanup task: {task['name']}")
                    await task["func"]()
                except Exception as e:
                    self.logger.error(f"Cleanup task failed: {task['name']} - {e}")
            
            # Clean up allocated resources
            for resource in reversed(self.context.resources_allocated):
                try:
                    if resource.get("cleanup_func"):
                        await resource["cleanup_func"]()
                    else:
                        # Default cleanup based on resource type
                        await self._default_resource_cleanup(resource)
                except Exception as e:
                    self.logger.error(f"Resource cleanup failed: {resource['type']} - {e}")
            
            self.logger.info("Cleanup completed")
            
        except Exception as e:
            self.logger.error(f"Cleanup execution failed: {e}")
    
    async def _default_resource_cleanup(self, resource: Dict[str, Any]):
        """Default resource cleanup based on resource type."""
        resource_type = resource["type"]
        resource_id = resource["id"]
        
        if resource_type == "directory":
            # Don't delete directories by default - they might contain important data
            pass
        elif resource_type == "service":
            # Stop service
            await self._cleanup_service()
        elif resource_type == "file":
            # Delete temporary files
            try:
                Path(resource_id).unlink(missing_ok=True)
            except Exception:
                pass
    
    async def _cleanup_deployment_manager(self):
        """Cleanup deployment manager resources."""
        if self.deployment_manager:
            try:
                await self.deployment_manager.cleanup()
            except Exception as e:
                self.logger.error(f"Failed to cleanup deployment manager: {e}")
    
    async def _cleanup_service(self):
        """Cleanup deployed service."""
        if self.deployment_manager and self.deployment_manager.deployment:
            try:
                await self.deployment_manager.deployment.stop_service()
            except Exception as e:
                self.logger.error(f"Failed to stop service: {e}")
    
    def get_deployment_status(self) -> Dict[str, Any]:
        """Get current deployment status."""
        if not self.context:
            return {"status": "not_started"}
        
        return {
            "deployment_id": self.context.deployment_id,
            "current_phase": self.context.current_phase.value,
            "duration_seconds": self.context.get_duration(),
            "resources_allocated": len(self.context.resources_allocated),
            "errors_count": len(self.context.error_history),
            "phases_completed": len(self.context.phase_history),
            "metadata": self.context.metadata
        }


# Factory function for creating unified deployment orchestrator
def create_unified_deployment(
    config: OnPremiseConfig, 
    progress_callback: Optional[Callable] = None
) -> UnifiedDeploymentOrchestrator:
    """Create a unified deployment orchestrator instance."""
    return UnifiedDeploymentOrchestrator(config, progress_callback)


# Convenience function for simple deployment
async def deploy_unified(
    config: OnPremiseConfig,
    progress_callback: Optional[Callable] = None,
    deployment_id: Optional[str] = None
) -> DeploymentResult:
    """Deploy using unified orchestrator with simplified interface."""
    orchestrator = create_unified_deployment(config, progress_callback)
    return await orchestrator.deploy(deployment_id)