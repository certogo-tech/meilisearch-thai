#!/usr/bin/env python3
"""
Deployment Automation Scripts for Thai Tokenizer On-Premise Deployment.

This module provides automation scripts for common deployment tasks,
pipeline integration utilities, and configuration management automation.
"""

import asyncio
import json
import logging
import os
import sys
import yaml
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
import subprocess
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from deployment.config import OnPremiseConfig, DeploymentMethod
from deployment.deployment_manager import DeploymentManager
from deployment.cli import DeploymentCLI


class DeploymentAutomation:
    """Deployment automation orchestrator."""
    
    def __init__(self, config_file: Optional[str] = None, output_dir: str = "automation_output"):
        self.config_file = config_file
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup logging
        self.logger = self._setup_logging()
        
        # Load configuration if provided
        self.config = None
        if config_file:
            self.config = self._load_config(config_file)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging for automation."""
        logger = logging.getLogger("deployment_automation")
        logger.setLevel(logging.INFO)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
        
        # File handler
        log_file = self.output_dir / "automation.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.DEBUG)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _load_config(self, config_file: str) -> OnPremiseConfig:
        """Load configuration from file."""
        try:
            with open(config_file, 'r') as f:
                if config_file.endswith('.json'):
                    config_data = json.load(f)
                elif config_file.endswith(('.yml', '.yaml')):
                    config_data = yaml.safe_load(f)
                else:
                    # Try JSON first, then YAML
                    content = f.read()
                    try:
                        config_data = json.loads(content)
                    except json.JSONDecodeError:
                        config_data = yaml.safe_load(content)
            
            return OnPremiseConfig(**config_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    async def automated_deployment(
        self, 
        environment: str = "development",
        skip_validation: bool = False,
        cleanup_on_failure: bool = True
    ) -> Dict[str, Any]:
        """Run automated deployment with predefined settings."""
        self.logger.info(f"Starting automated deployment for {environment} environment")
        
        deployment_result = {
            "environment": environment,
            "start_time": datetime.now(timezone.utc),
            "success": False,
            "deployment_id": None,
            "steps": [],
            "artifacts": []
        }
        
        try:
            # Step 1: Environment-specific configuration
            step_result = await self._prepare_environment_config(environment)
            deployment_result["steps"].append(step_result)
            
            if not step_result["success"]:
                raise Exception("Environment configuration failed")
            
            # Step 2: Pre-deployment validation
            if not skip_validation:
                step_result = await self._run_pre_deployment_validation()
                deployment_result["steps"].append(step_result)
                
                if not step_result["success"]:
                    raise Exception("Pre-deployment validation failed")
            
            # Step 3: Execute deployment
            step_result = await self._execute_automated_deployment()
            deployment_result["steps"].append(step_result)
            
            if not step_result["success"]:
                raise Exception("Deployment execution failed")
            
            deployment_result["deployment_id"] = step_result.get("deployment_id")
            
            # Step 4: Post-deployment verification
            step_result = await self._run_post_deployment_verification()
            deployment_result["steps"].append(step_result)
            
            if not step_result["success"]:
                self.logger.warning("Post-deployment verification had issues")
            
            # Step 5: Generate deployment report
            step_result = await self._generate_deployment_report(deployment_result)
            deployment_result["steps"].append(step_result)
            deployment_result["artifacts"].extend(step_result.get("artifacts", []))
            
            deployment_result["success"] = True
            self.logger.info("Automated deployment completed successfully")
            
        except Exception as e:
            deployment_result["error"] = str(e)
            self.logger.error(f"Automated deployment failed: {e}")
            
            if cleanup_on_failure:
                await self._cleanup_failed_deployment(deployment_result.get("deployment_id"))
        
        finally:
            deployment_result["end_time"] = datetime.now(timezone.utc)
            deployment_result["duration_seconds"] = (
                deployment_result["end_time"] - deployment_result["start_time"]
            ).total_seconds()
            
            # Save deployment result
            result_file = self.output_dir / f"deployment_result_{environment}.json"
            with open(result_file, 'w') as f:
                json.dump(deployment_result, f, indent=2, default=str)
            
            deployment_result["artifacts"].append(str(result_file))
        
        return deployment_result
    
    async def _prepare_environment_config(self, environment: str) -> Dict[str, Any]:
        """Prepare environment-specific configuration."""
        step_name = "prepare_environment_config"
        self.logger.info(f"Preparing configuration for {environment} environment")
        
        try:
            # Load environment-specific settings
            env_settings = self._get_environment_settings(environment)
            
            # Update configuration with environment settings
            if self.config:
                config_dict = self.config.dict()
                config_dict.update(env_settings)
                self.config = OnPremiseConfig(**config_dict)
            else:
                # Create configuration from environment settings
                self.config = OnPremiseConfig(**env_settings)
            
            # Save environment configuration
            config_file = self.output_dir / f"config_{environment}.json"
            with open(config_file, 'w') as f:
                json.dump(self.config.dict(), f, indent=2)
            
            return {
                "step": step_name,
                "success": True,
                "message": f"Environment configuration prepared for {environment}",
                "config_file": str(config_file),
                "environment": environment
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e)
            }
    
    def _get_environment_settings(self, environment: str) -> Dict[str, Any]:
        """Get environment-specific settings."""
        base_settings = {
            "deployment_method": "docker",
            "meilisearch_config": {
                "host": os.getenv("MEILISEARCH_HOST", "http://localhost:7700"),
                "port": int(os.getenv("MEILISEARCH_PORT", "7700")),
                "api_key": os.getenv("MEILISEARCH_API_KEY"),
                "ssl_enabled": os.getenv("MEILISEARCH_SSL", "false").lower() == "true",
                "ssl_verify": True,
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0
            },
            "service_config": {
                "service_name": f"thai-tokenizer-{environment}",
                "service_port": int(os.getenv("SERVICE_PORT", "8000")),
                "service_host": "0.0.0.0",
                "worker_processes": int(os.getenv("WORKER_PROCESSES", "2")),
                "service_user": "thai-tokenizer",
                "service_group": "thai-tokenizer"
            }
        }
        
        # Environment-specific overrides
        if environment == "development":
            base_settings.update({
                "security_config": {
                    "security_level": "basic",
                    "allowed_hosts": ["*"],
                    "cors_origins": ["*"],
                    "api_key_required": False,
                    "enable_https": False
                },
                "resource_config": {
                    "memory_limit_mb": 128,
                    "cpu_limit_cores": 0.5,
                    "max_concurrent_requests": 10,
                    "request_timeout_seconds": 30,
                    "enable_metrics": True,
                    "metrics_port": 9000
                },
                "monitoring_config": {
                    "enable_health_checks": True,
                    "health_check_interval_seconds": 60,
                    "enable_logging": True,
                    "log_level": "DEBUG",
                    "enable_prometheus": False,
                    "prometheus_port": 9000
                }
            })
        
        elif environment == "staging":
            base_settings.update({
                "security_config": {
                    "security_level": "standard",
                    "allowed_hosts": ["localhost", "127.0.0.1", "staging.example.com"],
                    "cors_origins": ["https://staging.example.com"],
                    "api_key_required": True,
                    "enable_https": True
                },
                "resource_config": {
                    "memory_limit_mb": 256,
                    "cpu_limit_cores": 1.0,
                    "max_concurrent_requests": 50,
                    "request_timeout_seconds": 30,
                    "enable_metrics": True,
                    "metrics_port": 9000
                },
                "monitoring_config": {
                    "enable_health_checks": True,
                    "health_check_interval_seconds": 30,
                    "enable_logging": True,
                    "log_level": "INFO",
                    "enable_prometheus": True,
                    "prometheus_port": 9000
                }
            })
        
        elif environment == "production":
            base_settings.update({
                "security_config": {
                    "security_level": "strict",
                    "allowed_hosts": ["production.example.com"],
                    "cors_origins": ["https://production.example.com"],
                    "api_key_required": True,
                    "enable_https": True
                },
                "resource_config": {
                    "memory_limit_mb": 512,
                    "cpu_limit_cores": 2.0,
                    "max_concurrent_requests": 100,
                    "request_timeout_seconds": 30,
                    "enable_metrics": True,
                    "metrics_port": 9000
                },
                "monitoring_config": {
                    "enable_health_checks": True,
                    "health_check_interval_seconds": 15,
                    "enable_logging": True,
                    "log_level": "WARNING",
                    "enable_prometheus": True,
                    "prometheus_port": 9000
                }
            })
        
        # Add common paths
        base_settings.update({
            "installation_path": f"/opt/thai-tokenizer-{environment}",
            "data_path": f"/opt/thai-tokenizer-{environment}/data",
            "log_path": f"/opt/thai-tokenizer-{environment}/logs",
            "config_path": f"/opt/thai-tokenizer-{environment}/config",
            "environment_variables": {
                "ENVIRONMENT": environment,
                "PYTHONPATH": "src",
                "LOG_LEVEL": base_settings.get("monitoring_config", {}).get("log_level", "INFO")
            }
        })
        
        return base_settings
    
    async def _run_pre_deployment_validation(self) -> Dict[str, Any]:
        """Run pre-deployment validation."""
        step_name = "pre_deployment_validation"
        self.logger.info("Running pre-deployment validation")
        
        try:
            from deployment.validation_framework import DeploymentValidationFramework
            
            framework = DeploymentValidationFramework(self.config)
            results = await framework.run_comprehensive_validation()
            
            # Save validation results
            validation_file = self.output_dir / "pre_deployment_validation.json"
            with open(validation_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)
            
            success = results["overall_status"] == "PASSED"
            
            return {
                "step": step_name,
                "success": success,
                "message": f"Pre-deployment validation: {results['overall_status']}",
                "validation_file": str(validation_file),
                "overall_status": results["overall_status"],
                "summary": results["summary"]
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e)
            }
    
    async def _execute_automated_deployment(self) -> Dict[str, Any]:
        """Execute the automated deployment."""
        step_name = "execute_deployment"
        self.logger.info("Executing automated deployment")
        
        try:
            # Setup progress tracking
            progress_updates = []
            def progress_callback(progress):
                progress_updates.append({
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "deployment_id": progress.deployment_id,
                    "progress_percentage": progress.progress_percentage,
                    "current_step": progress.current_step.name if progress.current_step else None,
                    "overall_status": progress.overall_status.value
                })
                self.logger.info(f"Deployment progress: {progress.progress_percentage:.1f}%")
            
            # Create deployment manager
            manager = DeploymentManager(self.config, progress_callback)
            
            # Execute deployment
            result = await manager.deploy()
            
            # Save progress updates
            progress_file = self.output_dir / "deployment_progress.json"
            with open(progress_file, 'w') as f:
                json.dump(progress_updates, f, indent=2)
            
            return {
                "step": step_name,
                "success": result.success,
                "message": result.summary,
                "deployment_id": result.deployment_id,
                "endpoints": result.endpoints,
                "progress_file": str(progress_file)
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e)
            }
    
    async def _run_post_deployment_verification(self) -> Dict[str, Any]:
        """Run post-deployment verification."""
        step_name = "post_deployment_verification"
        self.logger.info("Running post-deployment verification")
        
        try:
            # Wait for service to be ready
            await asyncio.sleep(10)
            
            verification_results = []
            
            # Test service health
            health_result = await self._verify_service_health()
            verification_results.append(health_result)
            
            # Test Thai tokenization
            tokenization_result = await self._verify_thai_tokenization()
            verification_results.append(tokenization_result)
            
            # Test performance
            performance_result = await self._verify_performance()
            verification_results.append(performance_result)
            
            # Save verification results
            verification_file = self.output_dir / "post_deployment_verification.json"
            with open(verification_file, 'w') as f:
                json.dump(verification_results, f, indent=2)
            
            # Check overall success
            success = all(result["success"] for result in verification_results)
            
            return {
                "step": step_name,
                "success": success,
                "message": f"Post-deployment verification: {'PASSED' if success else 'FAILED'}",
                "verification_file": str(verification_file),
                "results": verification_results
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e)
            }
    
    async def _verify_service_health(self) -> Dict[str, Any]:
        """Verify service health."""
        try:
            import httpx
            
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{service_url}/health", timeout=30.0)
                
                return {
                    "test": "service_health",
                    "success": response.status_code == 200,
                    "status_code": response.status_code,
                    "response_data": response.json() if response.status_code == 200 else None
                }
                
        except Exception as e:
            return {
                "test": "service_health",
                "success": False,
                "error": str(e)
            }
    
    async def _verify_thai_tokenization(self) -> Dict[str, Any]:
        """Verify Thai tokenization functionality."""
        try:
            import httpx
            
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            test_text = "สาหร่ายวากาเมะเป็นสาหร่ายทะเลจากญี่ปุ่น"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{service_url}/v1/tokenize",
                    json={"text": test_text},
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    token_count = len(data.get("tokens", []))
                    processing_time = data.get("processing_time_ms", 0)
                    
                    return {
                        "test": "thai_tokenization",
                        "success": token_count > 0 and processing_time < 100,
                        "token_count": token_count,
                        "processing_time_ms": processing_time,
                        "tokens": data.get("tokens", [])
                    }
                else:
                    return {
                        "test": "thai_tokenization",
                        "success": False,
                        "status_code": response.status_code
                    }
                
        except Exception as e:
            return {
                "test": "thai_tokenization",
                "success": False,
                "error": str(e)
            }
    
    async def _verify_performance(self) -> Dict[str, Any]:
        """Verify service performance."""
        try:
            import httpx
            import time
            
            service_url = f"http://localhost:{self.config.service_config.service_port}"
            test_text = "การพัฒนาเทคโนโลยีปัญญาประดิษฐ์ในประเทศไทย"
            
            response_times = []
            
            async with httpx.AsyncClient() as client:
                for _ in range(3):
                    start_time = time.time()
                    
                    response = await client.post(
                        f"{service_url}/v1/tokenize",
                        json={"text": test_text},
                        timeout=30.0
                    )
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    
                    if response.status_code == 200:
                        response_times.append(response_time)
            
            if response_times:
                avg_time = sum(response_times) / len(response_times)
                max_time = max(response_times)
                
                return {
                    "test": "performance",
                    "success": avg_time < 100,  # Target: < 100ms
                    "average_response_time_ms": avg_time,
                    "max_response_time_ms": max_time,
                    "response_times": response_times
                }
            else:
                return {
                    "test": "performance",
                    "success": False,
                    "error": "No successful requests"
                }
                
        except Exception as e:
            return {
                "test": "performance",
                "success": False,
                "error": str(e)
            }
    
    async def _generate_deployment_report(self, deployment_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive deployment report."""
        step_name = "generate_deployment_report"
        self.logger.info("Generating deployment report")
        
        try:
            # Create comprehensive report
            report = {
                "deployment_summary": {
                    "environment": deployment_result["environment"],
                    "success": deployment_result["success"],
                    "deployment_id": deployment_result.get("deployment_id"),
                    "start_time": deployment_result["start_time"].isoformat(),
                    "end_time": deployment_result["end_time"].isoformat(),
                    "duration_seconds": deployment_result["duration_seconds"]
                },
                "configuration": self.config.dict() if self.config else {},
                "deployment_steps": deployment_result["steps"],
                "artifacts": deployment_result.get("artifacts", []),
                "recommendations": self._generate_recommendations(deployment_result)
            }
            
            # Save JSON report
            json_report_file = self.output_dir / "deployment_report.json"
            with open(json_report_file, 'w') as f:
                json.dump(report, f, indent=2, default=str)
            
            # Generate HTML report
            html_report_file = self.output_dir / "deployment_report.html"
            self._generate_html_report(report, html_report_file)
            
            artifacts = [str(json_report_file), str(html_report_file)]
            
            return {
                "step": step_name,
                "success": True,
                "message": "Deployment report generated",
                "artifacts": artifacts
            }
            
        except Exception as e:
            return {
                "step": step_name,
                "success": False,
                "error": str(e)
            }
    
    def _generate_recommendations(self, deployment_result: Dict[str, Any]) -> List[str]:
        """Generate deployment recommendations."""
        recommendations = []
        
        if not deployment_result["success"]:
            recommendations.append("Review deployment logs and error messages")
            recommendations.append("Verify system requirements and dependencies")
        
        # Check for performance issues
        for step in deployment_result.get("steps", []):
            if step.get("step") == "post_deployment_verification":
                for result in step.get("results", []):
                    if result.get("test") == "performance" and not result.get("success"):
                        recommendations.append("Consider increasing system resources for better performance")
        
        # Security recommendations
        if self.config and self.config.security_config.security_level == "basic":
            recommendations.append("Consider upgrading to 'standard' or 'strict' security level for production")
        
        if self.config and not self.config.security_config.enable_https:
            recommendations.append("Enable HTTPS for production deployment")
        
        # Monitoring recommendations
        if self.config and not self.config.monitoring_config.enable_prometheus:
            recommendations.append("Enable Prometheus metrics for better monitoring")
        
        return recommendations
    
    def _generate_html_report(self, report: Dict[str, Any], output_file: Path):
        """Generate HTML deployment report."""
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Deployment Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        .header { background-color: #f5f5f5; padding: 20px; border-radius: 5px; }
        .success { color: #28a745; }
        .failure { color: #dc3545; }
        .section { margin: 20px 0; }
        .step { margin: 10px 0; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }
        .step-success { border-left: 4px solid #28a745; }
        .step-failure { border-left: 4px solid #dc3545; }
        table { width: 100%; border-collapse: collapse; margin: 20px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background-color: #f8f9fa; }
        .recommendations { background-color: #e9ecef; padding: 15px; border-radius: 5px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Thai Tokenizer Deployment Report</h1>
        <p><strong>Environment:</strong> {environment}</p>
        <p><strong>Status:</strong> <span class="{status_class}">{status}</span></p>
        <p><strong>Duration:</strong> {duration:.1f} seconds</p>
        <p><strong>Deployment ID:</strong> {deployment_id}</p>
    </div>
    
    <div class="section">
        <h2>Deployment Steps</h2>
        {steps_html}
    </div>
    
    <div class="section">
        <h2>Configuration Summary</h2>
        <table>
            <tr><th>Setting</th><th>Value</th></tr>
            <tr><td>Deployment Method</td><td>{deployment_method}</td></tr>
            <tr><td>Service Port</td><td>{service_port}</td></tr>
            <tr><td>Security Level</td><td>{security_level}</td></tr>
            <tr><td>Memory Limit</td><td>{memory_limit}MB</td></tr>
        </table>
    </div>
    
    <div class="recommendations">
        <h2>Recommendations</h2>
        <ul>
            {recommendations_html}
        </ul>
    </div>
</body>
</html>
        """
        
        # Generate steps HTML
        steps_html = ""
        for step in report.get("deployment_steps", []):
            step_class = "step-success" if step.get("success") else "step-failure"
            status_text = "✅ SUCCESS" if step.get("success") else "❌ FAILED"
            
            steps_html += f"""
            <div class="step {step_class}">
                <h3>{step.get('step', 'Unknown Step')} - {status_text}</h3>
                <p>{step.get('message', step.get('error', 'No details available'))}</p>
            </div>
            """
        
        # Generate recommendations HTML
        recommendations_html = ""
        for rec in report.get("recommendations", []):
            recommendations_html += f"<li>{rec}</li>"
        
        # Get configuration values
        config = report.get("configuration", {})
        
        html_content = html_template.format(
            environment=report["deployment_summary"]["environment"],
            status="SUCCESS" if report["deployment_summary"]["success"] else "FAILED",
            status_class="success" if report["deployment_summary"]["success"] else "failure",
            duration=report["deployment_summary"]["duration_seconds"],
            deployment_id=report["deployment_summary"]["deployment_id"] or "N/A",
            steps_html=steps_html,
            deployment_method=config.get("deployment_method", "N/A"),
            service_port=config.get("service_config", {}).get("service_port", "N/A"),
            security_level=config.get("security_config", {}).get("security_level", "N/A"),
            memory_limit=config.get("resource_config", {}).get("memory_limit_mb", "N/A"),
            recommendations_html=recommendations_html
        )
        
        with open(output_file, 'w') as f:
            f.write(html_content)
    
    async def _cleanup_failed_deployment(self, deployment_id: Optional[str]):
        """Cleanup resources from failed deployment."""
        if not deployment_id:
            return
        
        self.logger.info(f"Cleaning up failed deployment: {deployment_id}")
        
        try:
            # Create deployment manager for cleanup
            if self.config:
                manager = DeploymentManager(self.config, lambda x: None)
                await manager.cleanup()
                self.logger.info("Cleanup completed")
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    async def batch_deployment(
        self, 
        environments: List[str],
        parallel: bool = False,
        continue_on_failure: bool = False
    ) -> Dict[str, Any]:
        """Deploy to multiple environments."""
        self.logger.info(f"Starting batch deployment to environments: {environments}")
        
        batch_result = {
            "environments": environments,
            "start_time": datetime.now(timezone.utc),
            "results": {},
            "overall_success": True
        }
        
        try:
            if parallel:
                # Deploy to all environments in parallel
                tasks = [
                    self.automated_deployment(env) 
                    for env in environments
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
                for env, result in zip(environments, results):
                    if isinstance(result, Exception):
                        batch_result["results"][env] = {
                            "success": False,
                            "error": str(result)
                        }
                        batch_result["overall_success"] = False
                    else:
                        batch_result["results"][env] = result
                        if not result["success"]:
                            batch_result["overall_success"] = False
            else:
                # Deploy to environments sequentially
                for env in environments:
                    try:
                        result = await self.automated_deployment(env)
                        batch_result["results"][env] = result
                        
                        if not result["success"]:
                            batch_result["overall_success"] = False
                            if not continue_on_failure:
                                break
                                
                    except Exception as e:
                        batch_result["results"][env] = {
                            "success": False,
                            "error": str(e)
                        }
                        batch_result["overall_success"] = False
                        
                        if not continue_on_failure:
                            break
        
        finally:
            batch_result["end_time"] = datetime.now(timezone.utc)
            batch_result["duration_seconds"] = (
                batch_result["end_time"] - batch_result["start_time"]
            ).total_seconds()
            
            # Save batch result
            batch_result_file = self.output_dir / "batch_deployment_result.json"
            with open(batch_result_file, 'w') as f:
                json.dump(batch_result, f, indent=2, default=str)
        
        return batch_result


async def main():
    """Main automation entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Thai Tokenizer Deployment Automation")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--environment", default="development", help="Target environment")
    parser.add_argument("--output-dir", default="automation_output", help="Output directory")
    parser.add_argument("--skip-validation", action="store_true", help="Skip pre-deployment validation")
    parser.add_argument("--batch", nargs="+", help="Deploy to multiple environments")
    parser.add_argument("--parallel", action="store_true", help="Run batch deployments in parallel")
    
    args = parser.parse_args()
    
    # Create automation instance
    automation = DeploymentAutomation(args.config, args.output_dir)
    
    try:
        if args.batch:
            # Batch deployment
            result = await automation.batch_deployment(
                args.batch,
                parallel=args.parallel
            )
            
            print(f"Batch deployment completed: {result['overall_success']}")
            for env, env_result in result["results"].items():
                status = "✅" if env_result.get("success") else "❌"
                print(f"  {status} {env}: {env_result.get('success', False)}")
        else:
            # Single environment deployment
            result = await automation.automated_deployment(
                args.environment,
                skip_validation=args.skip_validation
            )
            
            status = "✅" if result["success"] else "❌"
            print(f"{status} Deployment to {args.environment}: {result['success']}")
            
            if result.get("deployment_id"):
                print(f"Deployment ID: {result['deployment_id']}")
        
        return 0 if result.get("success") or result.get("overall_success") else 1
        
    except Exception as e:
        print(f"❌ Automation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))