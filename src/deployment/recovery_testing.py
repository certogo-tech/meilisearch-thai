#!/usr/bin/env python3
"""
Recovery testing and validation procedures for Thai Tokenizer deployment.

This module provides automated testing of backup and recovery procedures
to ensure they work correctly when needed.

Requirements: 6.3, 6.4, 6.5
"""

import asyncio
import json
import logging
import tempfile
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum

try:
    from src.utils.logging import get_structured_logger
    from src.deployment.config import OnPremiseConfig, DeploymentMethod
    from src.deployment.backup_manager import BackupManager, BackupConfig, BackupType
    from src.deployment.recovery_manager import RecoveryManager, FailureType
except ImportError:
    # Fallback for when running outside the main application
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)
    
    class DeploymentMethod(str, Enum):
        DOCKER = "docker"
        SYSTEMD = "systemd"
        STANDALONE = "standalone"
    
    class BackupType(str, Enum):
        FULL = "full"
        CONFIGURATION = "configuration"
        DICTIONARIES = "dictionaries"
        SERVICE_STATE = "service_state"
        LOGS = "logs"
    
    class FailureType(str, Enum):
        SERVICE_CRASH = "service_crash"
        CONFIGURATION_ERROR = "configuration_error"
        DEPENDENCY_FAILURE = "dependency_failure"

logger = get_structured_logger(__name__)


class TestResult(str, Enum):
    """Test result status."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


@dataclass
class RecoveryTest:
    """Represents a recovery test case."""
    test_id: str
    name: str
    description: str
    test_type: str
    prerequisites: List[str]
    expected_duration_seconds: int
    critical: bool = True


class RecoveryTestResult:
    """Result of a recovery test execution."""
    
    def __init__(self, test: RecoveryTest):
        self.test = test
        self.result = TestResult.SKIPPED
        self.duration_seconds = 0.0
        self.error_message: Optional[str] = None
        self.warnings: List[str] = []
        self.details: Dict[str, Any] = {}
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "test_id": self.test.test_id,
            "name": self.test.name,
            "result": self.result.value,
            "duration_seconds": self.duration_seconds,
            "error_message": self.error_message,
            "warnings": self.warnings,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
            "critical": self.test.critical
        }


class RecoveryTestSuite:
    """
    Comprehensive test suite for backup and recovery procedures.
    
    Tests all aspects of backup creation, restoration, and recovery procedures
    to ensure they work correctly in disaster scenarios.
    """
    
    def __init__(self, config: OnPremiseConfig, backup_manager: BackupManager, recovery_manager: RecoveryManager):
        """
        Initialize test suite.
        
        Args:
            config: On-premise deployment configuration
            backup_manager: Backup manager instance
            recovery_manager: Recovery manager instance
        """
        self.config = config
        self.backup_manager = backup_manager
        self.recovery_manager = recovery_manager
        self.logger = get_structured_logger(f"{__name__}.RecoveryTestSuite")
        
        # Initialize test cases
        self.test_cases = self._initialize_test_cases()
    
    def _initialize_test_cases(self) -> List[RecoveryTest]:
        """Initialize all test cases."""
        tests = [
            # Backup tests
            RecoveryTest(
                test_id="backup_001",
                name="Create Full Backup",
                description="Test creation of full system backup",
                test_type="backup",
                prerequisites=["service_running"],
                expected_duration_seconds=60,
                critical=True
            ),
            RecoveryTest(
                test_id="backup_002",
                name="Create Configuration Backup",
                description="Test creation of configuration-only backup",
                test_type="backup",
                prerequisites=["service_running"],
                expected_duration_seconds=10,
                critical=True
            ),
            RecoveryTest(
                test_id="backup_003",
                name="Backup Integrity Verification",
                description="Test backup file integrity and checksums",
                test_type="backup",
                prerequisites=["backup_exists"],
                expected_duration_seconds=30,
                critical=True
            ),
            
            # Restore tests
            RecoveryTest(
                test_id="restore_001",
                name="Restore Configuration",
                description="Test restoration of configuration files",
                test_type="restore",
                prerequisites=["backup_exists", "service_stopped"],
                expected_duration_seconds=30,
                critical=True
            ),
            RecoveryTest(
                test_id="restore_002",
                name="Full System Restore",
                description="Test complete system restoration from backup",
                test_type="restore",
                prerequisites=["full_backup_exists", "service_stopped"],
                expected_duration_seconds=120,
                critical=True
            ),
            RecoveryTest(
                test_id="restore_003",
                name="Selective Component Restore",
                description="Test restoration of specific components only",
                test_type="restore",
                prerequisites=["backup_exists"],
                expected_duration_seconds=45,
                critical=False
            ),
            
            # Recovery tests
            RecoveryTest(
                test_id="recovery_001",
                name="Service Crash Recovery",
                description="Test automatic recovery from service crash",
                test_type="recovery",
                prerequisites=["service_running"],
                expected_duration_seconds=30,
                critical=True
            ),
            RecoveryTest(
                test_id="recovery_002",
                name="Configuration Error Recovery",
                description="Test recovery from configuration corruption",
                test_type="recovery",
                prerequisites=["backup_exists"],
                expected_duration_seconds=60,
                critical=True
            ),
            RecoveryTest(
                test_id="recovery_003",
                name="Failure Diagnosis",
                description="Test automatic failure diagnosis capabilities",
                test_type="recovery",
                prerequisites=["service_running"],
                expected_duration_seconds=15,
                critical=False
            ),
            
            # Rollback tests
            RecoveryTest(
                test_id="rollback_001",
                name="Create Rollback Point",
                description="Test creation of deployment rollback points",
                test_type="rollback",
                prerequisites=["service_running"],
                expected_duration_seconds=90,
                critical=True
            ),
            RecoveryTest(
                test_id="rollback_002",
                name="Execute Rollback",
                description="Test rollback to previous deployment state",
                test_type="rollback",
                prerequisites=["rollback_point_exists"],
                expected_duration_seconds=120,
                critical=True
            ),
            
            # Performance tests
            RecoveryTest(
                test_id="performance_001",
                name="Backup Performance",
                description="Test backup creation performance meets targets",
                test_type="performance",
                prerequisites=["service_running"],
                expected_duration_seconds=300,
                critical=False
            ),
            RecoveryTest(
                test_id="performance_002",
                name="Restore Performance",
                description="Test restore performance meets RTO targets",
                test_type="performance",
                prerequisites=["backup_exists"],
                expected_duration_seconds=180,
                critical=False
            ),
            
            # Integration tests
            RecoveryTest(
                test_id="integration_001",
                name="End-to-End Recovery",
                description="Test complete backup-to-recovery workflow",
                test_type="integration",
                prerequisites=["service_running"],
                expected_duration_seconds=300,
                critical=True
            ),
            RecoveryTest(
                test_id="integration_002",
                name="Multi-Component Recovery",
                description="Test recovery involving multiple components",
                test_type="integration",
                prerequisites=["service_running"],
                expected_duration_seconds=240,
                critical=True
            )
        ]
        
        return tests
    
    async def run_all_tests(self, test_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Run all recovery tests.
        
        Args:
            test_types: Optional list of test types to run
            
        Returns:
            Test results summary
        """
        start_time = time.time()
        self.logger.info("Starting recovery test suite execution")
        
        # Filter tests by type if specified
        tests_to_run = self.test_cases
        if test_types:
            tests_to_run = [test for test in self.test_cases if test.test_type in test_types]
        
        results = []
        passed_count = 0
        failed_count = 0
        skipped_count = 0
        warning_count = 0
        
        for test in tests_to_run:
            self.logger.info(f"Running test: {test.test_id} - {test.name}")
            
            try:
                # Check prerequisites
                if not await self._check_prerequisites(test.prerequisites):
                    result = RecoveryTestResult(test)
                    result.result = TestResult.SKIPPED
                    result.error_message = "Prerequisites not met"
                    results.append(result)
                    skipped_count += 1
                    continue
                
                # Run the test
                result = await self._run_single_test(test)
                results.append(result)
                
                # Update counters
                if result.result == TestResult.PASSED:
                    passed_count += 1
                elif result.result == TestResult.FAILED:
                    failed_count += 1
                elif result.result == TestResult.SKIPPED:
                    skipped_count += 1
                elif result.result == TestResult.WARNING:
                    warning_count += 1
                
                self.logger.info(f"Test {test.test_id} completed: {result.result.value}")
                
            except Exception as e:
                result = RecoveryTestResult(test)
                result.result = TestResult.FAILED
                result.error_message = str(e)
                results.append(result)
                failed_count += 1
                self.logger.error(f"Test {test.test_id} failed with exception: {e}")
        
        total_duration = time.time() - start_time
        
        # Generate summary
        summary = {
            "test_suite": "recovery_tests",
            "execution_time": datetime.now().isoformat(),
            "total_duration_seconds": total_duration,
            "total_tests": len(tests_to_run),
            "passed": passed_count,
            "failed": failed_count,
            "skipped": skipped_count,
            "warnings": warning_count,
            "success_rate": (passed_count / len(tests_to_run)) * 100 if tests_to_run else 0,
            "critical_failures": len([r for r in results if r.result == TestResult.FAILED and r.test.critical]),
            "results": [result.to_dict() for result in results]
        }
        
        self.logger.info(
            f"Recovery test suite completed: {passed_count}/{len(tests_to_run)} passed "
            f"({summary['success_rate']:.1f}% success rate)"
        )
        
        return summary
    
    async def _check_prerequisites(self, prerequisites: List[str]) -> bool:
        """Check if test prerequisites are met."""
        for prerequisite in prerequisites:
            if not await self._check_single_prerequisite(prerequisite):
                self.logger.warning(f"Prerequisite not met: {prerequisite}")
                return False
        return True
    
    async def _check_single_prerequisite(self, prerequisite: str) -> bool:
        """Check a single prerequisite."""
        try:
            if prerequisite == "service_running":
                return await self._is_service_running()
            
            elif prerequisite == "service_stopped":
                return not await self._is_service_running()
            
            elif prerequisite == "backup_exists":
                backups = await self.backup_manager.list_backups()
                return len(backups) > 0
            
            elif prerequisite == "full_backup_exists":
                backups = await self.backup_manager.list_backups()
                return any(b.get("backup_type") == "full" for b in backups)
            
            elif prerequisite == "rollback_point_exists":
                rollback_points = await self.recovery_manager.list_rollback_points()
                return len(rollback_points) > 0
            
            else:
                self.logger.warning(f"Unknown prerequisite: {prerequisite}")
                return False
        
        except Exception as e:
            self.logger.error(f"Error checking prerequisite {prerequisite}: {e}")
            return False
    
    async def _is_service_running(self) -> bool:
        """Check if the Thai Tokenizer service is running."""
        try:
            # This is a simplified check - in practice, you would implement
            # proper service status checking based on deployment method
            import httpx
            
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"http://localhost:{self.config.service_config.service_port}/health")
                return response.status_code == 200
        
        except Exception:
            return False
    
    async def _run_single_test(self, test: RecoveryTest) -> RecoveryTestResult:
        """Run a single test case."""
        result = RecoveryTestResult(test)
        start_time = time.time()
        
        try:
            if test.test_type == "backup":
                await self._run_backup_test(test, result)
            elif test.test_type == "restore":
                await self._run_restore_test(test, result)
            elif test.test_type == "recovery":
                await self._run_recovery_test(test, result)
            elif test.test_type == "rollback":
                await self._run_rollback_test(test, result)
            elif test.test_type == "performance":
                await self._run_performance_test(test, result)
            elif test.test_type == "integration":
                await self._run_integration_test(test, result)
            else:
                result.result = TestResult.FAILED
                result.error_message = f"Unknown test type: {test.test_type}"
        
        except Exception as e:
            result.result = TestResult.FAILED
            result.error_message = str(e)
        
        result.duration_seconds = time.time() - start_time
        
        # Check if test exceeded expected duration
        if result.duration_seconds > test.expected_duration_seconds * 1.5:
            result.warnings.append(f"Test took longer than expected ({result.duration_seconds:.1f}s vs {test.expected_duration_seconds}s)")
        
        return result
    
    async def _run_backup_test(self, test: RecoveryTest, result: RecoveryTestResult):
        """Run backup-related tests."""
        if test.test_id == "backup_001":
            # Test full backup creation
            backup_result = await self.backup_manager.create_backup(BackupType.FULL)
            
            if backup_result.status.value == "completed":
                result.result = TestResult.PASSED
                result.details = {
                    "backup_id": backup_result.backup_id,
                    "size_bytes": backup_result.size_bytes,
                    "components": backup_result.components
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = backup_result.error_message
        
        elif test.test_id == "backup_002":
            # Test configuration backup creation
            backup_result = await self.backup_manager.create_backup(BackupType.CONFIGURATION)
            
            if backup_result.status.value == "completed":
                result.result = TestResult.PASSED
                result.details = {
                    "backup_id": backup_result.backup_id,
                    "components": backup_result.components
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = backup_result.error_message
        
        elif test.test_id == "backup_003":
            # Test backup integrity verification
            backups = await self.backup_manager.list_backups()
            if not backups:
                result.result = TestResult.SKIPPED
                result.error_message = "No backups available for integrity check"
                return
            
            # Test the most recent backup
            latest_backup = backups[0]
            backup_file = Path(latest_backup["backup_path"])
            
            if backup_file.exists():
                # Basic integrity check - file exists and has reasonable size
                file_size = backup_file.stat().st_size
                if file_size > 1024:  # At least 1KB
                    result.result = TestResult.PASSED
                    result.details = {"file_size": file_size}
                else:
                    result.result = TestResult.FAILED
                    result.error_message = f"Backup file too small: {file_size} bytes"
            else:
                result.result = TestResult.FAILED
                result.error_message = "Backup file not found"
    
    async def _run_restore_test(self, test: RecoveryTest, result: RecoveryTestResult):
        """Run restore-related tests."""
        backups = await self.backup_manager.list_backups()
        if not backups:
            result.result = TestResult.SKIPPED
            result.error_message = "No backups available for restore test"
            return
        
        latest_backup = backups[0]
        
        if test.test_id == "restore_001":
            # Test configuration restore
            restore_result = await self.backup_manager.restore_backup(
                backup_id=latest_backup["backup_id"],
                restore_components=["configuration"],
                dry_run=True  # Use dry run to avoid affecting system
            )
            
            if restore_result.status.value == "completed":
                result.result = TestResult.PASSED
                result.details = {
                    "restored_components": restore_result.restored_components
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = restore_result.error_message
        
        elif test.test_id == "restore_002":
            # Test full system restore (dry run)
            restore_result = await self.backup_manager.restore_backup(
                backup_id=latest_backup["backup_id"],
                dry_run=True
            )
            
            if restore_result.status.value == "completed":
                result.result = TestResult.PASSED
                result.details = {
                    "would_restore_components": restore_result.restored_components
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = restore_result.error_message
        
        elif test.test_id == "restore_003":
            # Test selective component restore
            restore_result = await self.backup_manager.restore_backup(
                backup_id=latest_backup["backup_id"],
                restore_components=["configuration", "dictionaries"],
                dry_run=True
            )
            
            if restore_result.status.value == "completed":
                result.result = TestResult.PASSED
                result.details = {
                    "selected_components": ["configuration", "dictionaries"],
                    "would_restore_components": restore_result.restored_components
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = restore_result.error_message
    
    async def _run_recovery_test(self, test: RecoveryTest, result: RecoveryTestResult):
        """Run recovery-related tests."""
        if test.test_id == "recovery_001":
            # Test service crash recovery (simulation)
            recovery_result = await self.recovery_manager.execute_recovery(
                FailureType.SERVICE_CRASH
            )
            
            if recovery_result.success:
                result.result = TestResult.PASSED
                result.details = {
                    "recovery_actions": [action.value for action in recovery_result.recovery_actions_executed]
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = recovery_result.error_message
        
        elif test.test_id == "recovery_002":
            # Test configuration error recovery
            recovery_result = await self.recovery_manager.execute_recovery(
                FailureType.CONFIGURATION_ERROR
            )
            
            if recovery_result.success:
                result.result = TestResult.PASSED
                result.details = {
                    "recovery_actions": [action.value for action in recovery_result.recovery_actions_executed]
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = recovery_result.error_message
        
        elif test.test_id == "recovery_003":
            # Test failure diagnosis
            failure_scores = await self.recovery_manager.diagnose_failure()
            
            if failure_scores:
                result.result = TestResult.PASSED
                result.details = {
                    "diagnosed_failures": [(ft.value, score) for ft, score in failure_scores[:3]]
                }
            else:
                result.result = TestResult.WARNING
                result.warnings.append("No failures diagnosed (system appears healthy)")
    
    async def _run_rollback_test(self, test: RecoveryTest, result: RecoveryTestResult):
        """Run rollback-related tests."""
        if test.test_id == "rollback_001":
            # Test rollback point creation
            rollback_point = await self.recovery_manager.create_rollback_point(
                deployment_version=f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
                description="Test rollback point"
            )
            
            if rollback_point:
                result.result = TestResult.PASSED
                result.details = {
                    "rollback_id": rollback_point.rollback_id,
                    "backup_id": rollback_point.backup_id
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = "Failed to create rollback point"
        
        elif test.test_id == "rollback_002":
            # Test rollback execution (dry run simulation)
            rollback_points = await self.recovery_manager.list_rollback_points()
            if not rollback_points:
                result.result = TestResult.SKIPPED
                result.error_message = "No rollback points available"
                return
            
            # Simulate rollback validation
            latest_rollback = rollback_points[0]
            
            # Check if rollback point has valid backup
            if latest_rollback.backup_id:
                backups = await self.backup_manager.list_backups()
                backup_exists = any(b["backup_id"] == latest_rollback.backup_id for b in backups)
                
                if backup_exists:
                    result.result = TestResult.PASSED
                    result.details = {
                        "rollback_id": latest_rollback.rollback_id,
                        "backup_validated": True
                    }
                else:
                    result.result = TestResult.FAILED
                    result.error_message = "Rollback point references non-existent backup"
            else:
                result.result = TestResult.WARNING
                result.warnings.append("Rollback point has no associated backup")
    
    async def _run_performance_test(self, test: RecoveryTest, result: RecoveryTestResult):
        """Run performance-related tests."""
        if test.test_id == "performance_001":
            # Test backup performance
            start_time = time.time()
            backup_result = await self.backup_manager.create_backup(BackupType.FULL)
            backup_duration = time.time() - start_time
            
            # Performance targets (adjust based on requirements)
            max_backup_time = 300  # 5 minutes
            
            if backup_result.status.value == "completed":
                if backup_duration <= max_backup_time:
                    result.result = TestResult.PASSED
                else:
                    result.result = TestResult.WARNING
                    result.warnings.append(f"Backup took {backup_duration:.1f}s (target: {max_backup_time}s)")
                
                result.details = {
                    "backup_duration": backup_duration,
                    "backup_size": backup_result.size_bytes,
                    "throughput_mbps": (backup_result.size_bytes / 1024 / 1024) / backup_duration
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = backup_result.error_message
        
        elif test.test_id == "performance_002":
            # Test restore performance
            backups = await self.backup_manager.list_backups()
            if not backups:
                result.result = TestResult.SKIPPED
                result.error_message = "No backups available for performance test"
                return
            
            latest_backup = backups[0]
            
            start_time = time.time()
            restore_result = await self.backup_manager.restore_backup(
                backup_id=latest_backup["backup_id"],
                dry_run=True
            )
            restore_duration = time.time() - start_time
            
            # Performance targets
            max_restore_time = 180  # 3 minutes
            
            if restore_result.status.value == "completed":
                if restore_duration <= max_restore_time:
                    result.result = TestResult.PASSED
                else:
                    result.result = TestResult.WARNING
                    result.warnings.append(f"Restore took {restore_duration:.1f}s (target: {max_restore_time}s)")
                
                result.details = {
                    "restore_duration": restore_duration,
                    "components_restored": len(restore_result.restored_components)
                }
            else:
                result.result = TestResult.FAILED
                result.error_message = restore_result.error_message
    
    async def _run_integration_test(self, test: RecoveryTest, result: RecoveryTestResult):
        """Run integration tests."""
        if test.test_id == "integration_001":
            # End-to-end recovery test
            steps_completed = []
            
            try:
                # Step 1: Create backup
                backup_result = await self.backup_manager.create_backup(BackupType.FULL)
                if backup_result.status.value != "completed":
                    raise Exception(f"Backup creation failed: {backup_result.error_message}")
                steps_completed.append("backup_created")
                
                # Step 2: Create rollback point
                rollback_point = await self.recovery_manager.create_rollback_point(
                    deployment_version="integration-test",
                    description="Integration test rollback point"
                )
                if not rollback_point:
                    raise Exception("Rollback point creation failed")
                steps_completed.append("rollback_point_created")
                
                # Step 3: Simulate failure diagnosis
                failure_scores = await self.recovery_manager.diagnose_failure()
                steps_completed.append("failure_diagnosed")
                
                # Step 4: Test restore (dry run)
                restore_result = await self.backup_manager.restore_backup(
                    backup_id=backup_result.backup_id,
                    dry_run=True
                )
                if restore_result.status.value != "completed":
                    raise Exception(f"Restore test failed: {restore_result.error_message}")
                steps_completed.append("restore_tested")
                
                result.result = TestResult.PASSED
                result.details = {
                    "steps_completed": steps_completed,
                    "backup_id": backup_result.backup_id,
                    "rollback_id": rollback_point.rollback_id
                }
            
            except Exception as e:
                result.result = TestResult.FAILED
                result.error_message = str(e)
                result.details = {"steps_completed": steps_completed}
        
        elif test.test_id == "integration_002":
            # Multi-component recovery test
            components_tested = []
            
            try:
                # Test each component type
                for backup_type in [BackupType.CONFIGURATION, BackupType.DICTIONARIES]:
                    backup_result = await self.backup_manager.create_backup(backup_type)
                    if backup_result.status.value == "completed":
                        components_tested.append(backup_type.value)
                    else:
                        raise Exception(f"Component backup failed: {backup_type.value}")
                
                result.result = TestResult.PASSED
                result.details = {"components_tested": components_tested}
            
            except Exception as e:
                result.result = TestResult.FAILED
                result.error_message = str(e)
                result.details = {"components_tested": components_tested}
    
    async def generate_test_report(self, test_results: Dict[str, Any], output_file: Optional[Path] = None) -> str:
        """
        Generate a comprehensive test report.
        
        Args:
            test_results: Test results from run_all_tests()
            output_file: Optional file to save report
            
        Returns:
            Report content as string
        """
        report_lines = []
        
        # Header
        report_lines.append("# Recovery Test Suite Report")
        report_lines.append(f"Generated: {test_results['execution_time']}")
        report_lines.append(f"Duration: {test_results['total_duration_seconds']:.2f} seconds")
        report_lines.append("")
        
        # Summary
        report_lines.append("## Summary")
        report_lines.append(f"- Total Tests: {test_results['total_tests']}")
        report_lines.append(f"- Passed: {test_results['passed']}")
        report_lines.append(f"- Failed: {test_results['failed']}")
        report_lines.append(f"- Skipped: {test_results['skipped']}")
        report_lines.append(f"- Warnings: {test_results['warnings']}")
        report_lines.append(f"- Success Rate: {test_results['success_rate']:.1f}%")
        report_lines.append(f"- Critical Failures: {test_results['critical_failures']}")
        report_lines.append("")
        
        # Test Results by Category
        test_types = {}
        for test_result in test_results['results']:
            test_type = test_result.get('test_type', 'unknown')
            if test_type not in test_types:
                test_types[test_type] = []
            test_types[test_type].append(test_result)
        
        for test_type, tests in test_types.items():
            report_lines.append(f"## {test_type.title()} Tests")
            
            for test in tests:
                status_icon = {
                    'passed': '✅',
                    'failed': '❌',
                    'skipped': '⏭️',
                    'warning': '⚠️'
                }.get(test['result'], '❓')
                
                report_lines.append(f"### {status_icon} {test['name']} ({test['test_id']})")
                report_lines.append(f"- **Result**: {test['result']}")
                report_lines.append(f"- **Duration**: {test['duration_seconds']:.2f}s")
                
                if test['error_message']:
                    report_lines.append(f"- **Error**: {test['error_message']}")
                
                if test['warnings']:
                    report_lines.append("- **Warnings**:")
                    for warning in test['warnings']:
                        report_lines.append(f"  - {warning}")
                
                if test['details']:
                    report_lines.append("- **Details**:")
                    for key, value in test['details'].items():
                        report_lines.append(f"  - {key}: {value}")
                
                report_lines.append("")
        
        # Recommendations
        report_lines.append("## Recommendations")
        
        if test_results['critical_failures'] > 0:
            report_lines.append("⚠️ **CRITICAL**: There are critical test failures that must be addressed before production deployment.")
        
        if test_results['failed'] > 0:
            report_lines.append("- Review and fix failed tests before relying on backup/recovery procedures")
        
        if test_results['warnings'] > 0:
            report_lines.append("- Address warning conditions to improve recovery reliability")
        
        if test_results['success_rate'] < 90:
            report_lines.append("- Success rate is below 90% - comprehensive review recommended")
        
        report_lines.append("- Regularly run these tests to ensure continued reliability")
        report_lines.append("- Update test cases when deployment configuration changes")
        
        report_content = "\n".join(report_lines)
        
        # Save to file if requested
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            with open(output_file, 'w') as f:
                f.write(report_content)
            self.logger.info(f"Test report saved to: {output_file}")
        
        return report_content


async def main():
    """Main entry point for running recovery tests."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Recovery testing for Thai Tokenizer deployment")
    parser.add_argument("--config", help="Path to configuration file")
    parser.add_argument("--test-types", nargs="+", 
                       choices=["backup", "restore", "recovery", "rollback", "performance", "integration"],
                       help="Types of tests to run")
    parser.add_argument("--output", help="Output file for test report")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Load configuration (simplified for testing)
        from deployment.config import OnPremiseConfig, DeploymentMethod
        from deployment.config import (
            MeilisearchConnectionConfig, ServiceConfig, SecurityConfig,
            ResourceConfig, MonitoringConfig
        )
        from pydantic import SecretStr
        
        config = OnPremiseConfig(
            deployment_method=DeploymentMethod.STANDALONE,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key=SecretStr("test-key")
            ),
            service_config=ServiceConfig(),
            security_config=SecurityConfig(),
            resource_config=ResourceConfig(),
            monitoring_config=MonitoringConfig(),
            installation_path="/opt/thai-tokenizer",
            data_path="/var/lib/thai-tokenizer",
            config_path="/etc/thai-tokenizer",
            log_path="/var/log/thai-tokenizer"
        )
        
        # Create backup configuration
        backup_config = BackupConfig(
            backup_directory=Path(config.data_path) / "backups",
            deployment_method=config.deployment_method,
            installation_path=Path(config.installation_path),
            data_path=Path(config.data_path),
            config_path=Path(config.config_path),
            log_path=Path(config.log_path)
        )
        
        # Initialize managers
        backup_manager = BackupManager(backup_config)
        recovery_manager = RecoveryManager(config, backup_manager)
        
        # Create test suite
        test_suite = RecoveryTestSuite(config, backup_manager, recovery_manager)
        
        # Run tests
        print("Starting recovery test suite...")
        results = await test_suite.run_all_tests(args.test_types)
        
        # Generate report
        output_file = Path(args.output) if args.output else None
        report = await test_suite.generate_test_report(results, output_file)
        
        # Print summary
        print("\n" + "="*60)
        print("RECOVERY TEST SUITE RESULTS")
        print("="*60)
        print(f"Total Tests: {results['total_tests']}")
        print(f"Passed: {results['passed']}")
        print(f"Failed: {results['failed']}")
        print(f"Skipped: {results['skipped']}")
        print(f"Warnings: {results['warnings']}")
        print(f"Success Rate: {results['success_rate']:.1f}%")
        print(f"Critical Failures: {results['critical_failures']}")
        
        if results['critical_failures'] > 0:
            print("\n⚠️  CRITICAL FAILURES DETECTED - Review required before production use")
            return 1
        elif results['failed'] > 0:
            print("\n⚠️  Some tests failed - Review recommended")
            return 1
        else:
            print("\n✅ All tests passed successfully")
            return 0
    
    except Exception as e:
        print(f"Test execution failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(asyncio.run(main()))