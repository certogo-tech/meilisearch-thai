#!/usr/bin/env python3
"""
Continuous Integration testing script for deployment procedures.

This script provides automated testing pipeline integration for deployment
verification, including pre-deployment validation, deployment testing,
and post-deployment verification.
"""

import asyncio
import json
import os
import sys
import argparse
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import subprocess
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.deployment.config import OnPremiseConfig, DeploymentMethod
from src.deployment.deployment_manager import DeploymentManager
from tests.integration.test_deployment_validation_reporting import (
    DeploymentValidationRunner, DeploymentReportGenerator, ReportFormat
)


class CIDeploymentTester:
    """Continuous Integration deployment testing orchestrator."""
    
    def __init__(self, config_file: Path, output_dir: Path):
        self.config_file = config_file
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Load configuration
        self.config = self._load_config()
        
        # Initialize test results
        self.test_results = {
            "ci_run_id": f"ci-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}",
            "start_time": datetime.now(timezone.utc),
            "config_file": str(config_file),
            "deployment_method": self.config.deployment_method.value,
            "phases": {},
            "overall_status": "running",
            "artifacts": []
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for CI testing."""
        logger = logging.getLogger("ci_deployment_tester")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = self.output_dir / "ci_deployment_test.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _load_config(self) -> OnPremiseConfig:
        """Load deployment configuration from file."""
        try:
            with open(self.config_file, 'r') as f:
                config_data = json.load(f)
            
            return OnPremiseConfig(**config_data)
        
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    async def run_ci_pipeline(self) -> Dict[str, Any]:
        """Run complete CI deployment testing pipeline."""
        self.logger.info(f"Starting CI deployment testing pipeline: {self.test_results['ci_run_id']}")
        
        try:
            # Phase 1: Pre-deployment validation
            await self._run_pre_deployment_validation()
            
            # Phase 2: Deployment testing
            await self._run_deployment_testing()
            
            # Phase 3: Post-deployment verification
            await self._run_post_deployment_verification()
            
            # Phase 4: Cleanup and reporting
            await self._run_cleanup_and_reporting()
            
            self.test_results["overall_status"] = "success"
            self.logger.info("CI deployment testing pipeline completed successfully")
            
        except Exception as e:
            self.test_results["overall_status"] = "failed"
            self.test_results["error"] = str(e)
            self.logger.error(f"CI deployment testing pipeline failed: {e}")
            raise
        
        finally:
            self.test_results["end_time"] = datetime.now(timezone.utc)
            self.test_results["duration_seconds"] = (
                self.test_results["end_time"] - self.test_results["start_time"]
            ).total_seconds()
            
            # Save final results
            await self._save_ci_results()
        
        return self.test_results
    
    async def _run_pre_deployment_validation(self):
        """Run pre-deployment validation phase."""
        phase_name = "pre_deployment_validation"
        self.logger.info(f"Starting phase: {phase_name}")
        
        phase_start = datetime.now(timezone.utc)
        phase_results = {
            "phase": phase_name,
            "start_time": phase_start,
            "status": "running",
            "steps": []
        }
        
        try:
            # Step 1: Configuration validation
            step_result = await self._validate_configuration()
            phase_results["steps"].append(step_result)
            
            if not step_result["success"]:
                raise Exception("Configuration validation failed")
            
            # Step 2: System requirements validation
            step_result = await self._validate_system_requirements()
            phase_results["steps"].append(step_result)
            
            if not step_result["success"]:
                raise Exception("System requirements validation failed")
            
            # Step 3: Dependency validation
            step_result = await self._validate_dependencies()
            phase_results["steps"].append(step_result)
            
            if not step_result["success"]:
                raise Exception("Dependency validation failed")
            
            phase_results["status"] = "success"
            self.logger.info(f"Phase {phase_name} completed successfully")
            
        except Exception as e:
            phase_results["status"] = "failed"
            phase_results["error"] = str(e)
            self.logger.error(f"Phase {phase_name} failed: {e}")
            raise
        
        finally:
            phase_results["end_time"] = datetime.now(timezone.utc)
            phase_results["duration_seconds"] = (
                phase_results["end_time"] - phase_start
            ).total_seconds()
            
            self.test_results["phases"][phase_name] = phase_results
    
    async def _run_deployment_testing(self):
        """Run deployment testing phase."""
        phase_name = "deployment_testing"
        self.logger.info(f"Starting phase: {phase_name}")
        
        phase_start = datetime.now(timezone.utc)
        phase_results = {
            "phase": phase_name,
            "start_time": phase_start,
            "status": "running",
            "steps": []
        }
        
        try:
            # Step 1: Deploy service
            step_result = await self._deploy_service()
            phase_results["steps"].append(step_result)
            
            if not step_result["success"]:
                raise Exception("Service deployment failed")
            
            # Step 2: Verify deployment
            step_result = await self._verify_deployment()
            phase_results["steps"].append(step_result)
            
            if not step_result["success"]:
                raise Exception("Deployment verification failed")
            
            # Step 3: Run integration tests
            step_result = await self._run_integration_tests()
            phase_results["steps"].append(step_result)
            
            if not step_result["success"]:
                self.logger.warning("Integration tests had failures, but continuing")
            
            phase_results["status"] = "success"
            self.logger.info(f"Phase {phase_name} completed successfully")
            
        except Exception as e:
            phase_results["status"] = "failed"
            phase_results["error"] = str(e)
            self.logger.error(f"Phase {phase_name} failed: {e}")
            raise
        
        finally:
            phase_results["end_time"] = datetime.now(timezone.utc)
            phase_results["duration_seconds"] = (
                phase_results["end_time"] - phase_start
            ).total_seconds()
            
            self.test_results["phases"][phase_name] = phase_results
    
    async def _run_post_deployment_verification(self):
        """Run post-deployment verification phase."""
        phase_name = "post_deployment_verification"
        self.logger.info(f"Starting phase: {phase_name}")
        
        phase_start = datetime.now(timezone.utc)
        phase_results = {
            "phase": phase_name,
            "start_time": phase_start,
            "status": "running",
            "steps": []
        }
        
        try:
            # Step 1: Health check verification
            step_result = await self._verify_health_checks()
            phase_results["steps"].append(step_result)
            
            # Step 2: Performance verification
            step_result = await self._verify_performance()
            phase_results["steps"].append(step_result)
            
            # Step 3: Security verification
            step_result = await self._verify_security()
            phase_results["steps"].append(step_result)
            
            # Step 4: Thai tokenization verification
            step_result = await self._verify_thai_tokenization()
            phase_results["steps"].append(step_result)
            
            # Check if any critical steps failed
            critical_failures = [
                step for step in phase_results["steps"] 
                if not step["success"] and step.get("critical", False)
            ]
            
            if critical_failures:
                raise Exception(f"Critical verification steps failed: {len(critical_failures)}")
            
            phase_results["status"] = "success"
            self.logger.info(f"Phase {phase_name} completed successfully")
            
        except Exception as e:
            phase_results["status"] = "failed"
            phase_results["error"] = str(e)
            self.logger.error(f"Phase {phase_name} failed: {e}")
            raise
        
        finally:
            phase_results["end_time"] = datetime.now(timezone.utc)
            phase_results["duration_seconds"] = (
                phase_results["end_time"] - phase_start
            ).total_seconds()
            
            self.test_results["phases"][phase_name] = phase_results
    
    async def _run_cleanup_and_reporting(self):
        """Run cleanup and reporting phase."""
        phase_name = "cleanup_and_reporting"
        self.logger.info(f"Starting phase: {phase_name}")
        
        phase_start = datetime.now(timezone.utc)
        phase_results = {
            "phase": phase_name,
            "start_time": phase_start,
            "status": "running",
            "steps": []
        }
        
        try:
            # Step 1: Generate comprehensive validation report
            step_result = await self._generate_validation_report()
            phase_results["steps"].append(step_result)
            
            # Step 2: Cleanup deployment (if requested)
            if os.getenv("CI_CLEANUP_DEPLOYMENT", "true").lower() == "true":
                step_result = await self._cleanup_deployment()
                phase_results["steps"].append(step_result)
            
            # Step 3: Archive artifacts
            step_result = await self._archive_artifacts()
            phase_results["steps"].append(step_result)
            
            phase_results["status"] = "success"
            self.logger.info(f"Phase {phase_name} completed successfully")
            
        except Exception as e:
            phase_results["status"] = "failed"
            phase_results["error"] = str(e)
            self.logger.error(f"Phase {phase_name} failed: {e}")
            # Don't re-raise here as cleanup failures shouldn't fail the entire pipeline
        
        finally:
            phase_results["end_time"] = datetime.now(timezone.utc)
            phase_results["duration_seconds"] = (
                phase_results["end_time"] - phase_start
            ).total_seconds()
            
            self.test_results["phases"][phase_name] = phase_results
    
    async def _validate_configuration(self) -> Dict[str, Any]:
        """Validate deployment configuration."""
        step_name = "validate_configuration"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            # Validate configuration object
            validation_result = self.config.validate_paths()
            
            if not validation_result.valid:
                return {
                    "step": step_name,
                    "success": False,
                    "error": f"Configuration validation failed: {validation_result.errors}",
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            
            # Additional configuration checks
            checks = []
            
            # Check Meilisearch configuration
            if not self.config.meilisearch_config.host:
                checks.append("Meilisearch host not configured")
            
            if not self.config.meilisearch_config.api_key:
                checks.append("Meilisearch API key not configured")
            
            # Check service configuration
            if self.config.service_config.service_port < 1024 and os.geteuid() != 0:
                checks.append("Service port requires root privileges")
            
            if checks:
                return {
                    "step": step_name,
                    "success": False,
                    "error": f"Configuration issues: {checks}",
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            
            return {
                "step": step_name,
                "success": True,
                "message": "Configuration validation passed",
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _validate_system_requirements(self) -> Dict[str, Any]:
        """Validate system requirements."""
        step_name = "validate_system_requirements"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            # Run validation framework
            runner = DeploymentValidationRunner(self.config)
            report = await runner.run_validation_tests()
            
            # Check for critical failures
            critical_failures = [
                tc for tc in report.test_cases 
                if tc.status.value == "failed" and tc.test_category == "system_requirements"
            ]
            
            if critical_failures:
                return {
                    "step": step_name,
                    "success": False,
                    "error": f"System requirements not met: {len(critical_failures)} failures",
                    "details": [tc.test_name for tc in critical_failures],
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            
            return {
                "step": step_name,
                "success": True,
                "message": f"System requirements validated: {report.passed_tests}/{report.total_tests} passed",
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _validate_dependencies(self) -> Dict[str, Any]:
        """Validate deployment dependencies."""
        step_name = "validate_dependencies"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            dependencies = []
            
            # Check deployment method specific dependencies
            if self.config.deployment_method == DeploymentMethod.DOCKER:
                dependencies.extend(["docker", "docker compose"])
            elif self.config.deployment_method == DeploymentMethod.SYSTEMD:
                dependencies.extend(["systemctl"])
            elif self.config.deployment_method == DeploymentMethod.STANDALONE:
                dependencies.extend(["uv", "python3"])
            
            # Check each dependency
            missing_deps = []
            for dep in dependencies:
                try:
                    result = subprocess.run(
                        [dep.split()[0], "--version"], 
                        capture_output=True, 
                        text=True, 
                        timeout=10
                    )
                    if result.returncode != 0:
                        missing_deps.append(dep)
                except (subprocess.TimeoutExpired, FileNotFoundError):
                    missing_deps.append(dep)
            
            if missing_deps:
                return {
                    "step": step_name,
                    "success": False,
                    "error": f"Missing dependencies: {missing_deps}",
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            
            return {
                "step": step_name,
                "success": True,
                "message": f"All dependencies available: {dependencies}",
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _deploy_service(self) -> Dict[str, Any]:
        """Deploy the service."""
        step_name = "deploy_service"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            # Create deployment manager
            progress_updates = []
            def progress_callback(progress):
                progress_updates.append(progress)
                self.logger.info(f"Deployment progress: {progress.progress_percentage:.1f}%")
            
            manager = DeploymentManager(self.config, progress_callback)
            
            # Execute deployment
            result = await manager.deploy()
            
            if not result.success:
                return {
                    "step": step_name,
                    "success": False,
                    "error": f"Deployment failed: {result.progress.steps[-1].error_message if result.progress.steps else 'Unknown error'}",
                    "deployment_id": result.deployment_id,
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            
            # Store deployment info for later cleanup
            self.test_results["deployment_id"] = result.deployment_id
            self.test_results["deployment_manager"] = manager
            
            return {
                "step": step_name,
                "success": True,
                "message": f"Service deployed successfully: {result.deployment_id}",
                "deployment_id": result.deployment_id,
                "service_endpoints": result.endpoints,
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _verify_deployment(self) -> Dict[str, Any]:
        """Verify deployment is working."""
        step_name = "verify_deployment"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            # Wait for service to be ready
            await asyncio.sleep(10)
            
            # Test service health endpoint
            import httpx
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_url}/health", timeout=30.0)
                
                if response.status_code != 200:
                    return {
                        "step": step_name,
                        "success": False,
                        "error": f"Health check failed: HTTP {response.status_code}",
                        "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                    }
                
                health_data = response.json()
                
                return {
                    "step": step_name,
                    "success": True,
                    "message": "Deployment verification passed",
                    "health_status": health_data,
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _run_integration_tests(self) -> Dict[str, Any]:
        """Run integration tests."""
        step_name = "run_integration_tests"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            # Run pytest on integration tests
            test_files = [
                "tests/integration/test_on_premise_deployment_integration.py",
                "tests/integration/test_deployment_security.py"
            ]
            
            test_results = []
            
            for test_file in test_files:
                if Path(test_file).exists():
                    try:
                        result = subprocess.run([
                            sys.executable, "-m", "pytest", 
                            test_file, "-v", "--tb=short", 
                            "--json-report", "--json-report-file", 
                            str(self.output_dir / f"{Path(test_file).stem}_results.json")
                        ], capture_output=True, text=True, timeout=300)
                        
                        test_results.append({
                            "test_file": test_file,
                            "return_code": result.returncode,
                            "stdout": result.stdout,
                            "stderr": result.stderr
                        })
                        
                    except subprocess.TimeoutExpired:
                        test_results.append({
                            "test_file": test_file,
                            "return_code": -1,
                            "error": "Test execution timeout"
                        })
            
            # Analyze results
            failed_tests = [tr for tr in test_results if tr["return_code"] != 0]
            
            return {
                "step": step_name,
                "success": len(failed_tests) == 0,
                "message": f"Integration tests: {len(test_results) - len(failed_tests)}/{len(test_results)} passed",
                "test_results": test_results,
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _verify_health_checks(self) -> Dict[str, Any]:
        """Verify health checks."""
        step_name = "verify_health_checks"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            import httpx
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            
            health_checks = [
                {"endpoint": "/health", "critical": True},
                {"endpoint": "/health/detailed", "critical": False},
                {"endpoint": "/metrics", "critical": False}
            ]
            
            results = []
            
            async with httpx.AsyncClient() as client:
                for check in health_checks:
                    try:
                        response = await client.get(
                            f"{service_url}{check['endpoint']}", 
                            timeout=10.0
                        )
                        
                        results.append({
                            "endpoint": check["endpoint"],
                            "status_code": response.status_code,
                            "success": response.status_code == 200,
                            "critical": check["critical"]
                        })
                        
                    except Exception as e:
                        results.append({
                            "endpoint": check["endpoint"],
                            "success": False,
                            "error": str(e),
                            "critical": check["critical"]
                        })
            
            # Check for critical failures
            critical_failures = [r for r in results if not r["success"] and r["critical"]]
            
            return {
                "step": step_name,
                "success": len(critical_failures) == 0,
                "message": f"Health checks: {len([r for r in results if r['success']])}/{len(results)} passed",
                "results": results,
                "critical": len(critical_failures) > 0,
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "critical": True,
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _verify_performance(self) -> Dict[str, Any]:
        """Verify performance requirements."""
        step_name = "verify_performance"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            import httpx
            import time
            
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            
            # Test response time
            test_text = "สาหร่ายวากาเมะเป็นสาหร่ายทะเลจากญี่ปุ่น"
            response_times = []
            
            async with httpx.AsyncClient() as client:
                for _ in range(5):  # Test 5 times
                    start_time = time.time()
                    
                    try:
                        response = await client.post(
                            f"{service_url}/v1/tokenize",
                            json={"text": test_text},
                            timeout=30.0
                        )
                        
                        end_time = time.time()
                        response_time_ms = (end_time - start_time) * 1000
                        
                        if response.status_code == 200:
                            response_times.append(response_time_ms)
                        
                    except Exception:
                        pass
                    
                    await asyncio.sleep(0.5)  # Small delay between requests
            
            if not response_times:
                return {
                    "step": step_name,
                    "success": False,
                    "error": "No successful performance tests",
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            
            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            
            # Check performance requirements (< 50ms for 1000 characters)
            performance_ok = avg_response_time < 100  # Allow 100ms for CI environment
            
            return {
                "step": step_name,
                "success": performance_ok,
                "message": f"Performance test: avg {avg_response_time:.1f}ms, max {max_response_time:.1f}ms",
                "avg_response_time_ms": avg_response_time,
                "max_response_time_ms": max_response_time,
                "test_count": len(response_times),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _verify_security(self) -> Dict[str, Any]:
        """Verify security configuration."""
        step_name = "verify_security"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            # Import security tester
            from tests.integration.test_deployment_security import DeploymentSecurityTester
            
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            tester = DeploymentSecurityTester(service_url, self.config)
            
            # Run security audit
            audit_results = await tester.run_comprehensive_security_audit()
            
            # Analyze results
            failed_tests = [
                name for name, result in audit_results.items() 
                if not result.success
            ]
            
            return {
                "step": step_name,
                "success": len(failed_tests) == 0,
                "message": f"Security audit: {len(audit_results) - len(failed_tests)}/{len(audit_results)} passed",
                "failed_tests": failed_tests,
                "audit_results": {name: result.test_name for name, result in audit_results.items()},
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _verify_thai_tokenization(self) -> Dict[str, Any]:
        """Verify Thai tokenization functionality."""
        step_name = "verify_thai_tokenization"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            import httpx
            
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            
            # Test cases
            test_cases = [
                {"text": "สาหร่ายวากาเมะ", "expected_min_tokens": 1},
                {"text": "การพัฒนาเทคโนโลยีปัญญาประดิษฐ์", "expected_min_tokens": 3},
                {"text": "Startup ecosystem ในประเทศไทย", "expected_min_tokens": 4}
            ]
            
            results = []
            
            async with httpx.AsyncClient() as client:
                for test_case in test_cases:
                    try:
                        response = await client.post(
                            f"{service_url}/v1/tokenize",
                            json={"text": test_case["text"]},
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            token_count = len(data.get("tokens", []))
                            
                            results.append({
                                "text": test_case["text"],
                                "success": token_count >= test_case["expected_min_tokens"],
                                "token_count": token_count,
                                "expected_min": test_case["expected_min_tokens"],
                                "processing_time_ms": data.get("processing_time_ms", 0)
                            })
                        else:
                            results.append({
                                "text": test_case["text"],
                                "success": False,
                                "error": f"HTTP {response.status_code}"
                            })
                            
                    except Exception as e:
                        results.append({
                            "text": test_case["text"],
                            "success": False,
                            "error": str(e)
                        })
            
            successful_tests = [r for r in results if r["success"]]
            
            return {
                "step": step_name,
                "success": len(successful_tests) == len(test_cases),
                "message": f"Thai tokenization: {len(successful_tests)}/{len(test_cases)} tests passed",
                "test_results": results,
                "critical": True,
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "critical": True,
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _generate_validation_report(self) -> Dict[str, Any]:
        """Generate comprehensive validation report."""
        step_name = "generate_validation_report"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            # Run validation framework
            runner = DeploymentValidationRunner(self.config)
            report = await runner.run_validation_tests()
            
            # Generate reports in multiple formats
            generator = DeploymentReportGenerator(report)
            
            # Save JSON report
            json_file = generator.save_report(
                self.output_dir / "validation_report", 
                ReportFormat.JSON
            )
            self.test_results["artifacts"].append(str(json_file))
            
            # Save HTML report
            html_file = generator.save_report(
                self.output_dir / "validation_report", 
                ReportFormat.HTML
            )
            self.test_results["artifacts"].append(str(html_file))
            
            # Save Markdown report
            md_file = generator.save_report(
                self.output_dir / "validation_report", 
                ReportFormat.MARKDOWN
            )
            self.test_results["artifacts"].append(str(md_file))
            
            return {
                "step": step_name,
                "success": True,
                "message": f"Validation report generated: {report.overall_status.value}",
                "report_files": [str(json_file), str(html_file), str(md_file)],
                "validation_summary": {
                    "total_tests": report.total_tests,
                    "passed_tests": report.passed_tests,
                    "failed_tests": report.failed_tests,
                    "overall_status": report.overall_status.value
                },
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _cleanup_deployment(self) -> Dict[str, Any]:
        """Cleanup deployment resources."""
        step_name = "cleanup_deployment"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            if "deployment_manager" in self.test_results:
                manager = self.test_results["deployment_manager"]
                cleanup_result = await manager.cleanup()
                
                return {
                    "step": step_name,
                    "success": cleanup_result.success,
                    "message": "Deployment cleanup completed",
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            else:
                return {
                    "step": step_name,
                    "success": True,
                    "message": "No deployment to cleanup",
                    "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
                }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _archive_artifacts(self) -> Dict[str, Any]:
        """Archive test artifacts."""
        step_name = "archive_artifacts"
        self.logger.info(f"Running step: {step_name}")
        
        step_start = datetime.now(timezone.utc)
        
        try:
            # Create archive of all artifacts
            import tarfile
            
            archive_file = self.output_dir / f"ci_artifacts_{self.test_results['ci_run_id']}.tar.gz"
            
            with tarfile.open(archive_file, "w:gz") as tar:
                for artifact in self.test_results["artifacts"]:
                    if Path(artifact).exists():
                        tar.add(artifact, arcname=Path(artifact).name)
                
                # Add log file
                log_file = self.output_dir / "ci_deployment_test.log"
                if log_file.exists():
                    tar.add(log_file, arcname="ci_deployment_test.log")
            
            return {
                "step": step_name,
                "success": True,
                "message": f"Artifacts archived: {archive_file}",
                "archive_file": str(archive_file),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e),
                "duration_seconds": (datetime.now(timezone.utc) - step_start).total_seconds()
            }
    
    async def _save_ci_results(self):
        """Save CI test results."""
        results_file = self.output_dir / "ci_results.json"
        
        # Convert datetime objects to ISO format for JSON serialization
        serializable_results = self._make_json_serializable(self.test_results)
        
        with open(results_file, 'w') as f:
            json.dump(serializable_results, f, indent=2, ensure_ascii=False)
        
        self.test_results["artifacts"].append(str(results_file))
        self.logger.info(f"CI results saved: {results_file}")
    
    def _make_json_serializable(self, obj):
        """Make object JSON serializable."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._make_json_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._make_json_serializable(item) for item in obj]
        else:
            return obj


async def main():
    """Main CI testing function."""
    parser = argparse.ArgumentParser(description="CI Deployment Testing")
    parser.add_argument("--config", required=True, help="Deployment configuration file")
    parser.add_argument("--output-dir", default="ci_output", help="Output directory for results")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create CI tester
    tester = CIDeploymentTester(Path(args.config), output_dir)
    
    try:
        # Run CI pipeline
        results = await tester.run_ci_pipeline()
        
        # Print summary
        print(f"\nCI Deployment Testing Results:")
        print(f"Run ID: {results['ci_run_id']}")
        print(f"Overall Status: {results['overall_status']}")
        print(f"Duration: {results.get('duration_seconds', 0):.1f} seconds")
        
        # Print phase results
        for phase_name, phase_data in results.get("phases", {}).items():
            print(f"\nPhase: {phase_name}")
            print(f"  Status: {phase_data['status']}")
            print(f"  Duration: {phase_data.get('duration_seconds', 0):.1f} seconds")
            print(f"  Steps: {len(phase_data.get('steps', []))}")
        
        # Print artifacts
        if results.get("artifacts"):
            print(f"\nArtifacts generated:")
            for artifact in results["artifacts"]:
                print(f"  - {artifact}")
        
        # Exit with appropriate code
        sys.exit(0 if results["overall_status"] == "success" else 1)
        
    except Exception as e:
        print(f"CI pipeline failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())