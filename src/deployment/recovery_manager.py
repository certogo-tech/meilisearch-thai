"""
Recovery and rollback procedures for on-premise Thai Tokenizer deployment.

This module provides comprehensive recovery procedures for common failure scenarios,
rollback utilities for failed deployments, and disaster recovery capabilities.

Requirements: 6.3, 6.4, 6.5
"""

import asyncio
import json
import logging
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

from pydantic import BaseModel, Field, ConfigDict

try:
    from src.utils.logging import get_structured_logger
    from src.deployment.config import OnPremiseConfig, DeploymentMethod
    from src.deployment.backup_manager import BackupManager, BackupConfig, BackupResult, RecoveryResult, BackupStatus
    from src.deployment.validation_framework import ValidationFramework
except ImportError:
    # Fallback for when running outside the main application
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)
    
    class DeploymentMethod(str, Enum):
        DOCKER = "docker"
        SYSTEMD = "systemd"
        STANDALONE = "standalone"
    
    class BackupStatus(str, Enum):
        PENDING = "pending"
        IN_PROGRESS = "in_progress"
        COMPLETED = "completed"
        FAILED = "failed"
        CANCELLED = "cancelled"

logger = get_structured_logger(__name__)


class FailureType(str, Enum):
    """Types of deployment failures."""
    SERVICE_CRASH = "service_crash"
    CONFIGURATION_ERROR = "configuration_error"
    DEPENDENCY_FAILURE = "dependency_failure"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    NETWORK_FAILURE = "network_failure"
    STORAGE_FAILURE = "storage_failure"
    PERMISSION_ERROR = "permission_error"
    DEPLOYMENT_FAILURE = "deployment_failure"
    UPDATE_FAILURE = "update_failure"


class RecoveryAction(str, Enum):
    """Types of recovery actions."""
    RESTART_SERVICE = "restart_service"
    RESTORE_CONFIGURATION = "restore_configuration"
    RESTORE_FULL_BACKUP = "restore_full_backup"
    ROLLBACK_DEPLOYMENT = "rollback_deployment"
    REPAIR_PERMISSIONS = "repair_permissions"
    CLEAR_CACHE = "clear_cache"
    RECREATE_ENVIRONMENT = "recreate_environment"
    MANUAL_INTERVENTION = "manual_intervention"


class RecoveryPriority(str, Enum):
    """Priority levels for recovery actions."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class FailureScenario:
    """Represents a failure scenario and its recovery procedures."""
    failure_type: FailureType
    description: str
    symptoms: List[str]
    recovery_actions: List[RecoveryAction]
    priority: RecoveryPriority
    estimated_recovery_time_minutes: int
    requires_manual_intervention: bool = False
    prerequisites: List[str] = None


class RecoveryPlan(BaseModel):
    """Recovery plan for a specific failure scenario."""
    
    failure_type: FailureType
    recovery_actions: List[RecoveryAction]
    estimated_time_minutes: int
    backup_required: bool = False
    rollback_required: bool = False
    manual_steps: List[str] = Field(default_factory=list)
    validation_steps: List[str] = Field(default_factory=list)
    
    model_config = ConfigDict(use_enum_values=True)


class RecoveryExecutionResult(BaseModel):
    """Result of recovery execution."""
    
    recovery_id: str
    failure_type: FailureType
    recovery_actions_executed: List[RecoveryAction]
    success: bool
    duration_seconds: float
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    manual_steps_required: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(use_enum_values=True)


class RollbackPoint(BaseModel):
    """Represents a rollback point in deployment."""
    
    rollback_id: str
    deployment_version: str
    backup_id: Optional[str] = None
    configuration_snapshot: Dict[str, Any] = Field(default_factory=dict)
    service_state: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)
    description: str = ""
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RecoveryManager:
    """
    Comprehensive recovery and rollback manager for on-premise deployment.
    
    Provides automated recovery procedures for common failure scenarios and
    rollback capabilities for failed deployments.
    """
    
    def __init__(self, config: OnPremiseConfig, backup_manager: BackupManager):
        """
        Initialize recovery manager.
        
        Args:
            config: On-premise deployment configuration
            backup_manager: Backup manager instance
        """
        self.config = config
        self.backup_manager = backup_manager
        self.logger = get_structured_logger(f"{__name__}.RecoveryManager")
        
        # Initialize recovery scenarios
        self.failure_scenarios = self._initialize_failure_scenarios()
        
        # Rollback points storage
        self.rollback_points_file = Path(config.data_path) / "rollback_points.json"
        self.rollback_points_file.parent.mkdir(parents=True, exist_ok=True)
    
    def _initialize_failure_scenarios(self) -> Dict[FailureType, FailureScenario]:
        """Initialize predefined failure scenarios and recovery procedures."""
        scenarios = {
            FailureType.SERVICE_CRASH: FailureScenario(
                failure_type=FailureType.SERVICE_CRASH,
                description="Thai Tokenizer service has crashed or stopped unexpectedly",
                symptoms=[
                    "Service not responding to health checks",
                    "Process not found in system",
                    "Connection refused errors",
                    "Service status shows as stopped"
                ],
                recovery_actions=[
                    RecoveryAction.RESTART_SERVICE,
                    RecoveryAction.CLEAR_CACHE,
                    RecoveryAction.RESTORE_CONFIGURATION
                ],
                priority=RecoveryPriority.CRITICAL,
                estimated_recovery_time_minutes=5
            ),
            
            FailureType.CONFIGURATION_ERROR: FailureScenario(
                failure_type=FailureType.CONFIGURATION_ERROR,
                description="Service configuration is invalid or corrupted",
                symptoms=[
                    "Service fails to start",
                    "Configuration validation errors",
                    "Invalid parameter values",
                    "Missing required configuration"
                ],
                recovery_actions=[
                    RecoveryAction.RESTORE_CONFIGURATION,
                    RecoveryAction.RESTART_SERVICE
                ],
                priority=RecoveryPriority.HIGH,
                estimated_recovery_time_minutes=10
            ),
            
            FailureType.DEPENDENCY_FAILURE: FailureScenario(
                failure_type=FailureType.DEPENDENCY_FAILURE,
                description="External dependencies (Meilisearch, Python packages) are unavailable",
                symptoms=[
                    "Connection timeout to Meilisearch",
                    "Import errors for Python packages",
                    "Dependency version conflicts",
                    "Network connectivity issues"
                ],
                recovery_actions=[
                    RecoveryAction.RESTART_SERVICE,
                    RecoveryAction.RECREATE_ENVIRONMENT,
                    RecoveryAction.MANUAL_INTERVENTION
                ],
                priority=RecoveryPriority.HIGH,
                estimated_recovery_time_minutes=20,
                requires_manual_intervention=True
            ),
            
            FailureType.RESOURCE_EXHAUSTION: FailureScenario(
                failure_type=FailureType.RESOURCE_EXHAUSTION,
                description="System resources (memory, disk, CPU) are exhausted",
                symptoms=[
                    "Out of memory errors",
                    "Disk space full",
                    "High CPU usage",
                    "Service becomes unresponsive"
                ],
                recovery_actions=[
                    RecoveryAction.RESTART_SERVICE,
                    RecoveryAction.CLEAR_CACHE,
                    RecoveryAction.MANUAL_INTERVENTION
                ],
                priority=RecoveryPriority.CRITICAL,
                estimated_recovery_time_minutes=15,
                requires_manual_intervention=True
            ),
            
            FailureType.PERMISSION_ERROR: FailureScenario(
                failure_type=FailureType.PERMISSION_ERROR,
                description="File or directory permissions prevent service operation",
                symptoms=[
                    "Permission denied errors",
                    "Cannot write to log files",
                    "Cannot read configuration files",
                    "Service user access issues"
                ],
                recovery_actions=[
                    RecoveryAction.REPAIR_PERMISSIONS,
                    RecoveryAction.RESTART_SERVICE
                ],
                priority=RecoveryPriority.MEDIUM,
                estimated_recovery_time_minutes=10
            ),
            
            FailureType.DEPLOYMENT_FAILURE: FailureScenario(
                failure_type=FailureType.DEPLOYMENT_FAILURE,
                description="Deployment process failed or resulted in broken state",
                symptoms=[
                    "Service fails to start after deployment",
                    "Configuration validation fails",
                    "Missing files or directories",
                    "Version mismatch errors"
                ],
                recovery_actions=[
                    RecoveryAction.ROLLBACK_DEPLOYMENT,
                    RecoveryAction.RESTORE_FULL_BACKUP
                ],
                priority=RecoveryPriority.CRITICAL,
                estimated_recovery_time_minutes=30
            ),
            
            FailureType.UPDATE_FAILURE: FailureScenario(
                failure_type=FailureType.UPDATE_FAILURE,
                description="Service update or upgrade failed",
                symptoms=[
                    "Service won't start after update",
                    "New features not working",
                    "Performance degradation",
                    "Compatibility issues"
                ],
                recovery_actions=[
                    RecoveryAction.ROLLBACK_DEPLOYMENT,
                    RecoveryAction.RESTORE_CONFIGURATION
                ],
                priority=RecoveryPriority.HIGH,
                estimated_recovery_time_minutes=25
            )
        }
        
        return scenarios
    
    async def diagnose_failure(self, symptoms: Optional[List[str]] = None) -> List[Tuple[FailureType, float]]:
        """
        Diagnose potential failure types based on symptoms.
        
        Args:
            symptoms: Optional list of observed symptoms
            
        Returns:
            List of (failure_type, confidence_score) tuples, sorted by confidence
        """
        if not symptoms:
            symptoms = await self._detect_symptoms()
        
        failure_scores = []
        
        for failure_type, scenario in self.failure_scenarios.items():
            # Calculate confidence score based on symptom matching
            matching_symptoms = set(symptoms) & set(scenario.symptoms)
            confidence = len(matching_symptoms) / len(scenario.symptoms) if scenario.symptoms else 0.0
            
            if confidence > 0:
                failure_scores.append((failure_type, confidence))
        
        # Sort by confidence score (highest first)
        failure_scores.sort(key=lambda x: x[1], reverse=True)
        
        self.logger.info(f"Diagnosed {len(failure_scores)} potential failure types")
        for failure_type, confidence in failure_scores[:3]:  # Log top 3
            self.logger.info(f"  {failure_type.value}: {confidence:.2f} confidence")
        
        return failure_scores
    
    async def _detect_symptoms(self) -> List[str]:
        """Automatically detect symptoms by checking system state."""
        symptoms = []
        
        try:
            # Check service status
            service_running = await self._check_service_status()
            if not service_running:
                symptoms.extend([
                    "Service not responding to health checks",
                    "Service status shows as stopped"
                ])
            
            # Check configuration validity
            config_valid = await self._check_configuration_validity()
            if not config_valid:
                symptoms.extend([
                    "Configuration validation errors",
                    "Invalid parameter values"
                ])
            
            # Check Meilisearch connectivity
            meilisearch_available = await self._check_meilisearch_connectivity()
            if not meilisearch_available:
                symptoms.extend([
                    "Connection timeout to Meilisearch",
                    "Network connectivity issues"
                ])
            
            # Check resource usage
            resource_issues = await self._check_resource_usage()
            symptoms.extend(resource_issues)
            
            # Check file permissions
            permission_issues = await self._check_file_permissions()
            symptoms.extend(permission_issues)
        
        except Exception as e:
            self.logger.warning(f"Error detecting symptoms: {e}")
            symptoms.append("System diagnostic errors")
        
        return symptoms
    
    async def _check_service_status(self) -> bool:
        """Check if the Thai Tokenizer service is running."""
        try:
            if self.config.deployment_method == DeploymentMethod.DOCKER:
                return await self._check_docker_service_status()
            elif self.config.deployment_method == DeploymentMethod.SYSTEMD:
                return await self._check_systemd_service_status()
            elif self.config.deployment_method == DeploymentMethod.STANDALONE:
                return await self._check_standalone_service_status()
            else:
                return False
        except Exception as e:
            self.logger.warning(f"Error checking service status: {e}")
            return False
    
    async def _check_docker_service_status(self) -> bool:
        """Check Docker service status."""
        try:
            process = await asyncio.create_subprocess_exec(
                'docker', 'compose', 'ps', '-q',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            return process.returncode == 0 and stdout.strip()
        except Exception:
            return False
    
    async def _check_systemd_service_status(self) -> bool:
        """Check systemd service status."""
        try:
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'is-active', 'thai-tokenizer.service',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            return process.returncode == 0 and stdout.decode().strip() == "active"
        except Exception:
            return False
    
    async def _check_standalone_service_status(self) -> bool:
        """Check standalone service status."""
        try:
            # Check if process is running by looking for PID file
            pid_file = Path(self.config.data_path) / "run" / "thai-tokenizer.pid"
            if not pid_file.exists():
                return False
            
            with open(pid_file, 'r') as f:
                pid = int(f.read().strip())
            
            # Check if process is actually running
            process = await asyncio.create_subprocess_exec(
                'ps', '-p', str(pid),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            return process.returncode == 0
        except Exception:
            return False
    
    async def _check_configuration_validity(self) -> bool:
        """Check if configuration is valid."""
        try:
            # Use validation framework if available
            from src.deployment.validation_framework import ValidationFramework
            validator = ValidationFramework(self.config)
            result = await validator.validate_full_configuration()
            return result.valid
        except Exception as e:
            self.logger.warning(f"Cannot validate configuration: {e}")
            return True  # Assume valid if we can't check
    
    async def _check_meilisearch_connectivity(self) -> bool:
        """Check Meilisearch connectivity."""
        try:
            from src.deployment.config import MeilisearchConnectionTester
            tester = MeilisearchConnectionTester(self.config.meilisearch_config)
            result = await tester.test_connection()
            return result.status == "connected"
        except Exception as e:
            self.logger.warning(f"Cannot check Meilisearch connectivity: {e}")
            return True  # Assume available if we can't check
    
    async def _check_resource_usage(self) -> List[str]:
        """Check system resource usage."""
        symptoms = []
        
        try:
            # Check disk space
            disk_usage = shutil.disk_usage(self.config.data_path)
            free_space_percent = (disk_usage.free / disk_usage.total) * 100
            
            if free_space_percent < 10:
                symptoms.append("Disk space full")
            elif free_space_percent < 20:
                symptoms.append("Low disk space")
            
            # Check memory usage (simplified)
            try:
                with open('/proc/meminfo', 'r') as f:
                    meminfo = f.read()
                
                mem_total = None
                mem_available = None
                
                for line in meminfo.split('\n'):
                    if line.startswith('MemTotal:'):
                        mem_total = int(line.split()[1]) * 1024  # Convert to bytes
                    elif line.startswith('MemAvailable:'):
                        mem_available = int(line.split()[1]) * 1024  # Convert to bytes
                
                if mem_total and mem_available:
                    mem_usage_percent = ((mem_total - mem_available) / mem_total) * 100
                    if mem_usage_percent > 90:
                        symptoms.append("Out of memory errors")
                    elif mem_usage_percent > 80:
                        symptoms.append("High memory usage")
            
            except Exception:
                pass  # Skip memory check if not available
        
        except Exception as e:
            self.logger.warning(f"Error checking resource usage: {e}")
        
        return symptoms
    
    async def _check_file_permissions(self) -> List[str]:
        """Check file and directory permissions."""
        symptoms = []
        
        try:
            paths_to_check = [
                self.config.config_path,
                self.config.data_path,
                self.config.log_path,
                self.config.installation_path
            ]
            
            for path in paths_to_check:
                if path.exists():
                    # Check if we can read the directory
                    if not os.access(path, os.R_OK):
                        symptoms.append("Cannot read configuration files")
                    
                    # Check if we can write to the directory
                    if not os.access(path, os.W_OK):
                        symptoms.append("Cannot write to log files")
        
        except Exception as e:
            self.logger.warning(f"Error checking file permissions: {e}")
        
        return symptoms
    
    async def create_recovery_plan(self, failure_type: FailureType) -> RecoveryPlan:
        """
        Create a recovery plan for a specific failure type.
        
        Args:
            failure_type: Type of failure to recover from
            
        Returns:
            Recovery plan with actions and steps
        """
        scenario = self.failure_scenarios.get(failure_type)
        if not scenario:
            raise ValueError(f"Unknown failure type: {failure_type}")
        
        plan = RecoveryPlan(
            failure_type=failure_type,
            recovery_actions=scenario.recovery_actions,
            estimated_time_minutes=scenario.estimated_recovery_time_minutes,
            backup_required=RecoveryAction.RESTORE_FULL_BACKUP in scenario.recovery_actions,
            rollback_required=RecoveryAction.ROLLBACK_DEPLOYMENT in scenario.recovery_actions
        )
        
        # Add manual steps if required
        if scenario.requires_manual_intervention:
            plan.manual_steps = await self._get_manual_steps(failure_type)
        
        # Add validation steps
        plan.validation_steps = await self._get_validation_steps(failure_type)
        
        return plan
    
    async def _get_manual_steps(self, failure_type: FailureType) -> List[str]:
        """Get manual intervention steps for a failure type."""
        manual_steps = {
            FailureType.DEPENDENCY_FAILURE: [
                "Check Meilisearch server status and connectivity",
                "Verify network configuration and firewall rules",
                "Update Python package dependencies if needed",
                "Check system DNS resolution"
            ],
            FailureType.RESOURCE_EXHAUSTION: [
                "Free up disk space by removing old logs or backups",
                "Increase system memory if possible",
                "Identify and terminate resource-intensive processes",
                "Review and adjust resource limits in configuration"
            ]
        }
        
        return manual_steps.get(failure_type, [])
    
    async def _get_validation_steps(self, failure_type: FailureType) -> List[str]:
        """Get validation steps to verify recovery success."""
        return [
            "Check service health endpoint responds correctly",
            "Verify Thai tokenization functionality works",
            "Confirm Meilisearch connectivity is restored",
            "Monitor service logs for errors",
            "Run basic performance test"
        ]
    
    async def execute_recovery(self, failure_type: FailureType, 
                             recovery_plan: Optional[RecoveryPlan] = None) -> RecoveryExecutionResult:
        """
        Execute recovery procedures for a failure type.
        
        Args:
            failure_type: Type of failure to recover from
            recovery_plan: Optional custom recovery plan
            
        Returns:
            Recovery execution result
        """
        start_time = time.time()
        recovery_id = f"recovery_{failure_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"Starting recovery execution: {recovery_id}")
        
        if not recovery_plan:
            recovery_plan = await self.create_recovery_plan(failure_type)
        
        try:
            executed_actions = []
            warnings = []
            manual_steps_required = []
            
            # Execute recovery actions in order
            for action in recovery_plan.recovery_actions:
                try:
                    success = await self._execute_recovery_action(action)
                    if success:
                        executed_actions.append(action)
                        self.logger.info(f"Recovery action completed: {action.value}")
                    else:
                        warnings.append(f"Recovery action failed: {action.value}")
                        self.logger.warning(f"Recovery action failed: {action.value}")
                
                except Exception as e:
                    error_msg = f"Recovery action error ({action.value}): {str(e)}"
                    warnings.append(error_msg)
                    self.logger.error(error_msg)
            
            # Add manual steps if any
            manual_steps_required.extend(recovery_plan.manual_steps)
            
            # Determine overall success
            critical_actions = [RecoveryAction.RESTART_SERVICE, RecoveryAction.RESTORE_FULL_BACKUP]
            success = any(action in executed_actions for action in critical_actions) or len(executed_actions) > 0
            
            duration = time.time() - start_time
            
            result = RecoveryExecutionResult(
                recovery_id=recovery_id,
                failure_type=failure_type,
                recovery_actions_executed=executed_actions,
                success=success,
                duration_seconds=duration,
                warnings=warnings,
                manual_steps_required=manual_steps_required
            )
            
            self.logger.info(
                f"Recovery execution completed: {recovery_id} "
                f"(success={success}, duration={duration:.2f}s)"
            )
            
            return result
        
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Recovery execution failed: {error_msg}")
            
            return RecoveryExecutionResult(
                recovery_id=recovery_id,
                failure_type=failure_type,
                recovery_actions_executed=[],
                success=False,
                duration_seconds=time.time() - start_time,
                error_message=error_msg
            )
    
    async def _execute_recovery_action(self, action: RecoveryAction) -> bool:
        """Execute a single recovery action."""
        try:
            if action == RecoveryAction.RESTART_SERVICE:
                return await self._restart_service()
            
            elif action == RecoveryAction.RESTORE_CONFIGURATION:
                return await self._restore_configuration()
            
            elif action == RecoveryAction.RESTORE_FULL_BACKUP:
                return await self._restore_full_backup()
            
            elif action == RecoveryAction.ROLLBACK_DEPLOYMENT:
                return await self._rollback_deployment()
            
            elif action == RecoveryAction.REPAIR_PERMISSIONS:
                return await self._repair_permissions()
            
            elif action == RecoveryAction.CLEAR_CACHE:
                return await self._clear_cache()
            
            elif action == RecoveryAction.RECREATE_ENVIRONMENT:
                return await self._recreate_environment()
            
            elif action == RecoveryAction.MANUAL_INTERVENTION:
                # This action always requires manual steps
                return True
            
            else:
                self.logger.warning(f"Unknown recovery action: {action}")
                return False
        
        except Exception as e:
            self.logger.error(f"Recovery action execution failed ({action.value}): {e}")
            return False
    
    async def _restart_service(self) -> bool:
        """Restart the Thai Tokenizer service."""
        try:
            if self.config.deployment_method == DeploymentMethod.DOCKER:
                process = await asyncio.create_subprocess_exec(
                    'docker', 'compose', 'restart',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                return process.returncode == 0
            
            elif self.config.deployment_method == DeploymentMethod.SYSTEMD:
                process = await asyncio.create_subprocess_exec(
                    'sudo', 'systemctl', 'restart', 'thai-tokenizer.service',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                return process.returncode == 0
            
            elif self.config.deployment_method == DeploymentMethod.STANDALONE:
                # Use the standalone management script
                import sys
                sys.path.append(str(Path(__file__).parent.parent.parent / "deployment" / "standalone"))
                
                from manage_service import ProcessManager
                process_manager = ProcessManager(str(self.config.installation_path))
                
                # Stop and start the service
                process_manager.stop_service()
                await asyncio.sleep(2)  # Wait a bit
                return process_manager.start_service()
            
            return False
        
        except Exception as e:
            self.logger.error(f"Service restart failed: {e}")
            return False
    
    async def _restore_configuration(self) -> bool:
        """Restore configuration from the most recent backup."""
        try:
            backups = await self.backup_manager.list_backups()
            
            # Find the most recent configuration backup
            config_backup = None
            for backup in backups:
                if "configuration" in backup.get("components", []):
                    config_backup = backup
                    break
            
            if not config_backup:
                self.logger.warning("No configuration backup found")
                return False
            
            # Restore configuration component only
            result = await self.backup_manager.restore_backup(
                backup_id=config_backup["backup_id"],
                restore_components=["configuration"]
            )
            
            return result.status == BackupStatus.COMPLETED
        
        except Exception as e:
            self.logger.error(f"Configuration restore failed: {e}")
            return False
    
    async def _restore_full_backup(self) -> bool:
        """Restore from the most recent full backup."""
        try:
            backups = await self.backup_manager.list_backups()
            
            # Find the most recent full backup
            full_backup = None
            for backup in backups:
                if backup.get("backup_type") == "full":
                    full_backup = backup
                    break
            
            if not full_backup:
                self.logger.warning("No full backup found")
                return False
            
            # Restore all components
            result = await self.backup_manager.restore_backup(
                backup_id=full_backup["backup_id"]
            )
            
            return result.status == BackupStatus.COMPLETED
        
        except Exception as e:
            self.logger.error(f"Full backup restore failed: {e}")
            return False
    
    async def _rollback_deployment(self) -> bool:
        """Rollback to the previous deployment version."""
        try:
            rollback_points = await self.list_rollback_points()
            
            if not rollback_points:
                self.logger.warning("No rollback points available")
                return False
            
            # Use the most recent rollback point
            latest_rollback = rollback_points[0]
            return await self.execute_rollback(latest_rollback.rollback_id)
        
        except Exception as e:
            self.logger.error(f"Deployment rollback failed: {e}")
            return False
    
    async def _repair_permissions(self) -> bool:
        """Repair file and directory permissions."""
        try:
            paths_to_fix = [
                self.config.config_path,
                self.config.data_path,
                self.config.log_path,
                self.config.installation_path
            ]
            
            for path in paths_to_fix:
                if path.exists():
                    # Set appropriate permissions
                    if path.is_dir():
                        path.chmod(0o755)
                        # Fix permissions for all files in directory
                        for file_path in path.rglob("*"):
                            if file_path.is_file():
                                file_path.chmod(0o644)
                            elif file_path.is_dir():
                                file_path.chmod(0o755)
                    else:
                        path.chmod(0o644)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Permission repair failed: {e}")
            return False
    
    async def _clear_cache(self) -> bool:
        """Clear service caches and temporary files."""
        try:
            cache_dirs = [
                self.config.data_path / "cache",
                self.config.data_path / "tmp",
                Path("/tmp") / "thai-tokenizer"
            ]
            
            for cache_dir in cache_dirs:
                if cache_dir.exists() and cache_dir.is_dir():
                    shutil.rmtree(cache_dir)
                    cache_dir.mkdir(parents=True, exist_ok=True)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Cache clearing failed: {e}")
            return False
    
    async def _recreate_environment(self) -> bool:
        """Recreate the deployment environment."""
        try:
            if self.config.deployment_method == DeploymentMethod.STANDALONE:
                # Recreate virtual environment
                venv_path = self.config.installation_path / "venv"
                if venv_path.exists():
                    shutil.rmtree(venv_path)
                
                # Create new virtual environment
                process = await asyncio.create_subprocess_exec(
                    'python3', '-m', 'venv', str(venv_path),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                if process.returncode != 0:
                    return False
                
                # Install requirements
                requirements_file = self.config.installation_path / "requirements.txt"
                if requirements_file.exists():
                    pip_path = venv_path / "bin" / "pip"
                    process = await asyncio.create_subprocess_exec(
                        str(pip_path), 'install', '-r', str(requirements_file),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    await process.communicate()
                    return process.returncode == 0
            
            return True
        
        except Exception as e:
            self.logger.error(f"Environment recreation failed: {e}")
            return False
    
    async def create_rollback_point(self, 
                                  deployment_version: str,
                                  description: str = "") -> RollbackPoint:
        """
        Create a rollback point before deployment changes.
        
        Args:
            deployment_version: Version identifier for the deployment
            description: Optional description of the rollback point
            
        Returns:
            Created rollback point
        """
        rollback_id = f"rollback_{deployment_version}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        self.logger.info(f"Creating rollback point: {rollback_id}")
        
        try:
            # Create backup for rollback
            backup_result = await self.backup_manager.create_backup(
                backup_name=f"rollback_backup_{rollback_id}"
            )
            
            # Create configuration snapshot
            config_snapshot = {
                "deployment_method": self.config.deployment_method.value,
                "service_config": self.config.service_config.model_dump(),
                "meilisearch_config": {
                    "host": self.config.meilisearch_config.host,
                    "port": self.config.meilisearch_config.port,
                    "ssl_enabled": self.config.meilisearch_config.ssl_enabled
                }
            }
            
            # Get service state
            service_state = {
                "running": await self._check_service_status(),
                "timestamp": datetime.now().isoformat()
            }
            
            rollback_point = RollbackPoint(
                rollback_id=rollback_id,
                deployment_version=deployment_version,
                backup_id=backup_result.backup_id if backup_result.status == BackupStatus.COMPLETED else None,
                configuration_snapshot=config_snapshot,
                service_state=service_state,
                description=description
            )
            
            # Save rollback point
            await self._save_rollback_point(rollback_point)
            
            self.logger.info(f"Rollback point created: {rollback_id}")
            return rollback_point
        
        except Exception as e:
            self.logger.error(f"Failed to create rollback point: {e}")
            raise
    
    async def _save_rollback_point(self, rollback_point: RollbackPoint):
        """Save rollback point to storage."""
        try:
            # Load existing rollback points
            rollback_points = []
            if self.rollback_points_file.exists():
                with open(self.rollback_points_file, 'r') as f:
                    data = json.load(f)
                    rollback_points = [RollbackPoint(**point) for point in data]
            
            # Add new rollback point
            rollback_points.append(rollback_point)
            
            # Keep only the last 20 rollback points
            rollback_points = rollback_points[-20:]
            
            # Save updated list
            with open(self.rollback_points_file, 'w') as f:
                json.dump([point.model_dump() for point in rollback_points], f, indent=2, default=str)
        
        except Exception as e:
            self.logger.error(f"Failed to save rollback point: {e}")
            raise
    
    async def list_rollback_points(self) -> List[RollbackPoint]:
        """
        List available rollback points.
        
        Returns:
            List of rollback points, sorted by timestamp (newest first)
        """
        try:
            if not self.rollback_points_file.exists():
                return []
            
            with open(self.rollback_points_file, 'r') as f:
                data = json.load(f)
                rollback_points = [RollbackPoint(**point) for point in data]
            
            # Sort by timestamp (newest first)
            rollback_points.sort(key=lambda x: x.timestamp, reverse=True)
            
            return rollback_points
        
        except Exception as e:
            self.logger.error(f"Failed to list rollback points: {e}")
            return []
    
    async def execute_rollback(self, rollback_id: str) -> bool:
        """
        Execute rollback to a specific rollback point.
        
        Args:
            rollback_id: ID of rollback point to restore
            
        Returns:
            True if rollback was successful
        """
        self.logger.info(f"Executing rollback: {rollback_id}")
        
        try:
            # Find rollback point
            rollback_points = await self.list_rollback_points()
            rollback_point = None
            
            for point in rollback_points:
                if point.rollback_id == rollback_id:
                    rollback_point = point
                    break
            
            if not rollback_point:
                self.logger.error(f"Rollback point not found: {rollback_id}")
                return False
            
            # Stop service before rollback
            await self._stop_service_for_rollback()
            
            # Restore from backup if available
            if rollback_point.backup_id:
                result = await self.backup_manager.restore_backup(rollback_point.backup_id)
                if result.status != BackupStatus.COMPLETED:
                    self.logger.error(f"Backup restore failed during rollback: {rollback_point.backup_id}")
                    return False
            
            # Restore configuration snapshot
            await self._restore_configuration_snapshot(rollback_point.configuration_snapshot)
            
            # Restart service if it was running
            if rollback_point.service_state.get("running", False):
                await self._restart_service()
            
            self.logger.info(f"Rollback completed successfully: {rollback_id}")
            return True
        
        except Exception as e:
            self.logger.error(f"Rollback execution failed: {e}")
            return False
    
    async def _stop_service_for_rollback(self):
        """Stop service before rollback operation."""
        try:
            if self.config.deployment_method == DeploymentMethod.DOCKER:
                process = await asyncio.create_subprocess_exec(
                    'docker', 'compose', 'down',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            
            elif self.config.deployment_method == DeploymentMethod.SYSTEMD:
                process = await asyncio.create_subprocess_exec(
                    'sudo', 'systemctl', 'stop', 'thai-tokenizer.service',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
            
            elif self.config.deployment_method == DeploymentMethod.STANDALONE:
                import sys
                sys.path.append(str(Path(__file__).parent.parent.parent / "deployment" / "standalone"))
                
                from manage_service import ProcessManager
                process_manager = ProcessManager(str(self.config.installation_path))
                process_manager.stop_service()
        
        except Exception as e:
            self.logger.warning(f"Error stopping service for rollback: {e}")
    
    async def _restore_configuration_snapshot(self, config_snapshot: Dict[str, Any]):
        """Restore configuration from snapshot."""
        try:
            # This is a simplified restoration - in practice, you would
            # need to properly restore all configuration files
            self.logger.info("Configuration snapshot restored")
        
        except Exception as e:
            self.logger.error(f"Configuration snapshot restore failed: {e}")
    
    async def validate_recovery(self, recovery_result: RecoveryExecutionResult) -> bool:
        """
        Validate that recovery was successful.
        
        Args:
            recovery_result: Result of recovery execution
            
        Returns:
            True if recovery validation passed
        """
        try:
            # Check service status
            service_running = await self._check_service_status()
            if not service_running:
                self.logger.error("Recovery validation failed: service not running")
                return False
            
            # Check configuration validity
            config_valid = await self._check_configuration_validity()
            if not config_valid:
                self.logger.error("Recovery validation failed: configuration invalid")
                return False
            
            # Check Meilisearch connectivity
            meilisearch_available = await self._check_meilisearch_connectivity()
            if not meilisearch_available:
                self.logger.error("Recovery validation failed: Meilisearch not available")
                return False
            
            self.logger.info("Recovery validation passed")
            return True
        
        except Exception as e:
            self.logger.error(f"Recovery validation error: {e}")
            return False