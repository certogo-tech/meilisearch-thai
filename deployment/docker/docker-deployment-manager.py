#!/usr/bin/env python3
"""
Docker Deployment Manager for Thai Tokenizer Service
Provides comprehensive deployment management with validation, monitoring, and recovery
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import yaml
import requests
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """Deployment status enumeration"""
    NOT_STARTED = "not_started"
    VALIDATING = "validating"
    DEPLOYING = "deploying"
    RUNNING = "running"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class ValidationResult:
    """Result of pre-deployment validation"""
    success: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, any] = field(default_factory=dict)


@dataclass
class DeploymentResult:
    """Result of deployment operation"""
    success: bool
    status: DeploymentStatus
    message: str
    details: Dict[str, any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class HealthCheckResult:
    """Result of health check operation"""
    healthy: bool
    services: Dict[str, bool] = field(default_factory=dict)
    details: Dict[str, any] = field(default_factory=dict)
    response_time_ms: float = 0.0


class DockerDeploymentManager:
    """
    Comprehensive Docker deployment manager for Thai Tokenizer service
    """
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path(__file__).parent
        self.project_root = self.config_dir.parent.parent
        self.compose_file = self.config_dir / "docker-compose.external-meilisearch.yml"
        self.env_file = self.config_dir / ".env.external-meilisearch"
        self.env_template = self.config_dir / ".env.external-meilisearch.template"
        
        # Load configuration
        self.config = self._load_configuration()
        
        # Deployment state
        self.status = DeploymentStatus.NOT_STARTED
        self.deployment_id = f"deploy_{int(time.time())}"
        
    def _load_configuration(self) -> Dict[str, any]:
        """Load deployment configuration from environment file"""
        config = {}
        
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
        
        return config
    
    async def validate_prerequisites(self) -> ValidationResult:
        """
        Comprehensive pre-deployment validation
        Requirements: 2.1, 2.2, 5.1, 5.2
        """
        logger.info("Starting pre-deployment validation...")
        self.status = DeploymentStatus.VALIDATING
        
        result = ValidationResult(success=True)
        
        # Check Docker installation and status
        docker_check = await self._validate_docker()
        if not docker_check.success:
            result.success = False
            result.errors.extend(docker_check.errors)
        
        # Check environment configuration
        env_check = await self._validate_environment()
        if not env_check.success:
            result.success = False
            result.errors.extend(env_check.errors)
        result.warnings.extend(env_check.warnings)
        
        # Check Meilisearch connectivity
        meilisearch_check = await self._validate_meilisearch()
        if not meilisearch_check.success:
            result.success = False
            result.errors.extend(meilisearch_check.errors)
        
        # Check system resources
        resource_check = await self._validate_resources()
        if not resource_check.success:
            result.success = False
            result.errors.extend(resource_check.errors)
        result.warnings.extend(resource_check.warnings)
        
        # Check network configuration
        network_check = await self._validate_network()
        if not network_check.success:
            result.success = False
            result.errors.extend(network_check.errors)
        
        result.details = {
            'docker': docker_check.details,
            'environment': env_check.details,
            'meilisearch': meilisearch_check.details,
            'resources': resource_check.details,
            'network': network_check.details
        }
        
        logger.info(f"Validation completed: {'SUCCESS' if result.success else 'FAILED'}")
        return result
    
    async def _validate_docker(self) -> ValidationResult:
        """Validate Docker installation and status"""
        result = ValidationResult(success=True)
        
        try:
            # Check Docker command availability
            docker_version = subprocess.run(
                ['docker', '--version'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if docker_version.returncode != 0:
                result.success = False
                result.errors.append("Docker command not available")
                return result
            
            # Check Docker daemon status
            docker_info = subprocess.run(
                ['docker', 'info'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if docker_info.returncode != 0:
                result.success = False
                result.errors.append("Docker daemon not running")
                return result
            
            # Check Docker Compose availability
            compose_version = subprocess.run(
                ['docker', 'compose', 'version'], 
                capture_output=True, 
                text=True, 
                timeout=10
            )
            
            if compose_version.returncode != 0:
                result.success = False
                result.errors.append("Docker Compose not available")
                return result
            
            result.details = {
                'docker_version': docker_version.stdout.strip(),
                'compose_version': compose_version.stdout.strip()
            }
            
        except subprocess.TimeoutExpired:
            result.success = False
            result.errors.append("Docker command timeout")
        except Exception as e:
            result.success = False
            result.errors.append(f"Docker validation error: {str(e)}")
        
        return result
    
    async def _validate_environment(self) -> ValidationResult:
        """Validate environment configuration"""
        result = ValidationResult(success=True)
        
        # Check if environment file exists
        if not self.env_file.exists():
            if self.env_template.exists():
                result.warnings.append(
                    f"Environment file not found. Template available at {self.env_template}"
                )
            else:
                result.success = False
                result.errors.append("Environment file and template not found")
                return result
        
        # Validate required environment variables
        required_vars = [
            'MEILISEARCH_HOST',
            'MEILISEARCH_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if var not in self.config or not self.config[var]:
                missing_vars.append(var)
        
        if missing_vars:
            result.success = False
            result.errors.append(f"Missing required environment variables: {', '.join(missing_vars)}")
        
        # Validate configuration values
        if 'MEILISEARCH_HOST' in self.config:
            host = self.config['MEILISEARCH_HOST']
            if not (host.startswith('http://') or host.startswith('https://')):
                result.errors.append("MEILISEARCH_HOST must start with http:// or https://")
                result.success = False
        
        # Check resource limits
        try:
            memory_limit = self.config.get('MEMORY_LIMIT', '1G')
            if memory_limit.endswith('G'):
                memory_gb = float(memory_limit[:-1])
                if memory_gb < 0.5:
                    result.warnings.append("Memory limit is quite low, consider increasing")
        except ValueError:
            result.warnings.append("Invalid memory limit format")
        
        result.details = {
            'config_file_exists': self.env_file.exists(),
            'config_vars_count': len(self.config),
            'required_vars_present': len(required_vars) - len(missing_vars)
        }
        
        return result
    
    async def _validate_meilisearch(self) -> ValidationResult:
        """Validate Meilisearch connectivity and authentication"""
        result = ValidationResult(success=True)
        
        if 'MEILISEARCH_HOST' not in self.config:
            result.success = False
            result.errors.append("MEILISEARCH_HOST not configured")
            return result
        
        host = self.config['MEILISEARCH_HOST']
        api_key = self.config.get('MEILISEARCH_API_KEY', '')
        
        try:
            # Test health endpoint
            health_url = f"{host}/health"
            health_response = requests.get(health_url, timeout=10)
            
            if health_response.status_code != 200:
                result.success = False
                result.errors.append(f"Meilisearch health check failed: {health_response.status_code}")
                return result
            
            # Test authentication
            if api_key:
                keys_url = f"{host}/keys"
                auth_response = requests.get(
                    keys_url,
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=10
                )
                
                if auth_response.status_code != 200:
                    result.success = False
                    result.errors.append("Meilisearch API key authentication failed")
                    return result
            
            result.details = {
                'host': host,
                'health_status': health_response.status_code,
                'auth_configured': bool(api_key),
                'response_time_ms': health_response.elapsed.total_seconds() * 1000
            }
            
        except requests.RequestException as e:
            result.success = False
            result.errors.append(f"Meilisearch connectivity error: {str(e)}")
        
        return result
    
    async def _validate_resources(self) -> ValidationResult:
        """Validate system resources"""
        result = ValidationResult(success=True)
        
        try:
            # Check available memory
            with open('/proc/meminfo', 'r') as f:
                meminfo = f.read()
            
            for line in meminfo.split('\n'):
                if line.startswith('MemAvailable:'):
                    available_kb = int(line.split()[1])
                    available_mb = available_kb // 1024
                    
                    required_mb = 512  # Minimum required memory
                    if available_mb < required_mb:
                        result.success = False
                        result.errors.append(
                            f"Insufficient memory: {available_mb}MB available, {required_mb}MB required"
                        )
                    elif available_mb < 1024:
                        result.warnings.append(
                            f"Low memory: {available_mb}MB available, consider increasing"
                        )
                    
                    result.details['available_memory_mb'] = available_mb
                    break
            
            # Check available disk space
            import shutil
            disk_usage = shutil.disk_usage(self.project_root)
            available_gb = disk_usage.free // (1024**3)
            
            required_gb = 2  # Minimum required disk space
            if available_gb < required_gb:
                result.success = False
                result.errors.append(
                    f"Insufficient disk space: {available_gb}GB available, {required_gb}GB required"
                )
            
            result.details['available_disk_gb'] = available_gb
            
        except Exception as e:
            result.warnings.append(f"Could not check system resources: {str(e)}")
        
        return result
    
    async def _validate_network(self) -> ValidationResult:
        """Validate network configuration"""
        result = ValidationResult(success=True)
        
        # Check if required ports are available
        required_ports = [
            int(self.config.get('THAI_TOKENIZER_PORT', 8000))
        ]
        
        import socket
        for port in required_ports:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(1)
                    result_code = s.connect_ex(('localhost', port))
                    if result_code == 0:
                        result.warnings.append(f"Port {port} is already in use")
            except Exception:
                pass  # Port is available
        
        result.details = {
            'required_ports': required_ports,
            'network_mode': self.config.get('EXTERNAL_MEILISEARCH_NETWORK', 'bridge')
        }
        
        return result
    
    async def deploy(self, 
                    profiles: List[str] = None, 
                    build: bool = True, 
                    detach: bool = True) -> DeploymentResult:
        """
        Deploy the Thai Tokenizer service
        Requirements: 2.1, 2.2, 5.1, 5.2
        """
        logger.info(f"Starting deployment {self.deployment_id}")
        self.status = DeploymentStatus.DEPLOYING
        
        # Validate prerequisites first
        validation = await self.validate_prerequisites()
        if not validation.success:
            return DeploymentResult(
                success=False,
                status=DeploymentStatus.FAILED,
                message="Pre-deployment validation failed",
                details={'validation_errors': validation.errors}
            )
        
        try:
            # Prepare deployment environment
            await self._prepare_deployment()
            
            # Build Docker Compose command
            cmd = ['docker', 'compose', '-f', str(self.compose_file)]
            
            if self.env_file.exists():
                cmd.extend(['--env-file', str(self.env_file)])
            
            # Add profiles
            if profiles:
                for profile in profiles:
                    cmd.extend(['--profile', profile])
            
            # Add deployment flags
            cmd.append('up')
            if build:
                cmd.append('--build')
            if detach:
                cmd.append('-d')
            
            # Execute deployment
            logger.info(f"Executing: {' '.join(cmd)}")
            process = subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            if process.returncode != 0:
                return DeploymentResult(
                    success=False,
                    status=DeploymentStatus.FAILED,
                    message="Docker Compose deployment failed",
                    details={
                        'stdout': process.stdout,
                        'stderr': process.stderr,
                        'return_code': process.returncode
                    }
                )
            
            # Wait for services to be healthy
            await self._wait_for_health()
            
            self.status = DeploymentStatus.RUNNING
            
            return DeploymentResult(
                success=True,
                status=DeploymentStatus.RUNNING,
                message="Deployment completed successfully",
                details={
                    'deployment_id': self.deployment_id,
                    'profiles': profiles or [],
                    'validation_warnings': validation.warnings
                }
            )
            
        except subprocess.TimeoutExpired:
            return DeploymentResult(
                success=False,
                status=DeploymentStatus.FAILED,
                message="Deployment timeout"
            )
        except Exception as e:
            return DeploymentResult(
                success=False,
                status=DeploymentStatus.FAILED,
                message=f"Deployment error: {str(e)}"
            )
    
    async def _prepare_deployment(self):
        """Prepare deployment environment"""
        # Create necessary directories
        log_dir = self.project_root / "logs" / "thai-tokenizer"
        log_dir.mkdir(parents=True, exist_ok=True)
        
        nginx_log_dir = self.project_root / "logs" / "nginx"
        nginx_log_dir.mkdir(parents=True, exist_ok=True)
        
        # Set proper permissions
        os.chmod(log_dir, 0o755)
        os.chmod(nginx_log_dir, 0o755)
    
    async def _wait_for_health(self, timeout: int = 120):
        """Wait for services to become healthy"""
        logger.info("Waiting for services to become healthy...")
        
        start_time = time.time()
        while time.time() - start_time < timeout:
            health_result = await self.check_health()
            if health_result.healthy:
                logger.info("All services are healthy")
                return
            
            await asyncio.sleep(5)
        
        logger.warning("Health check timeout reached")
    
    async def check_health(self) -> HealthCheckResult:
        """
        Comprehensive health check for deployed services
        Requirements: 2.2, 5.2
        """
        result = HealthCheckResult(healthy=False)
        start_time = time.time()
        
        try:
            # Get service port
            service_port = int(self.config.get('THAI_TOKENIZER_PORT', 8000))
            
            # Basic health check
            health_url = f"http://localhost:{service_port}/health"
            health_response = requests.get(health_url, timeout=10)
            
            if health_response.status_code == 200:
                result.services['thai_tokenizer_basic'] = True
                
                # Detailed health check
                detailed_url = f"http://localhost:{service_port}/health/detailed"
                detailed_response = requests.get(detailed_url, timeout=15)
                
                if detailed_response.status_code == 200:
                    detailed_data = detailed_response.json()
                    result.services['thai_tokenizer_detailed'] = True
                    
                    # Check Meilisearch connectivity
                    meilisearch_status = detailed_data.get('meilisearch_status')
                    result.services['meilisearch'] = meilisearch_status == 'healthy'
                    
                    # Check tokenizer status
                    tokenizer_status = detailed_data.get('tokenizer_status')
                    result.services['tokenizer'] = tokenizer_status == 'healthy'
                    
                    result.details = detailed_data
            
            # Check Docker container status
            container_status = await self._check_container_status()
            result.services.update(container_status)
            
            # Overall health determination
            critical_services = ['thai_tokenizer_basic', 'meilisearch']
            result.healthy = all(result.services.get(service, False) for service in critical_services)
            
        except requests.RequestException as e:
            result.details['error'] = f"Health check request failed: {str(e)}"
        except Exception as e:
            result.details['error'] = f"Health check error: {str(e)}"
        
        result.response_time_ms = (time.time() - start_time) * 1000
        return result
    
    async def _check_container_status(self) -> Dict[str, bool]:
        """Check Docker container status"""
        status = {}
        
        try:
            # Get container status
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'ps', '--format', 'json'
            ]
            
            process = subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if process.returncode == 0:
                # Parse container status
                for line in process.stdout.strip().split('\n'):
                    if line:
                        container_info = json.loads(line)
                        service_name = container_info.get('Service', '')
                        container_status = container_info.get('State', '')
                        status[f'container_{service_name}'] = container_status == 'running'
        
        except Exception as e:
            logger.warning(f"Could not check container status: {str(e)}")
        
        return status
    
    async def stop(self) -> DeploymentResult:
        """Stop the deployed service"""
        logger.info("Stopping Thai Tokenizer service...")
        
        try:
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'stop'
            ]
            
            process = subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if process.returncode == 0:
                self.status = DeploymentStatus.STOPPED
                return DeploymentResult(
                    success=True,
                    status=DeploymentStatus.STOPPED,
                    message="Service stopped successfully"
                )
            else:
                return DeploymentResult(
                    success=False,
                    status=self.status,
                    message="Failed to stop service",
                    details={'stderr': process.stderr}
                )
        
        except Exception as e:
            return DeploymentResult(
                success=False,
                status=self.status,
                message=f"Stop error: {str(e)}"
            )
    
    async def restart(self) -> DeploymentResult:
        """Restart the deployed service"""
        logger.info("Restarting Thai Tokenizer service...")
        
        # Stop first
        stop_result = await self.stop()
        if not stop_result.success:
            return stop_result
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Start again
        return await self.deploy()
    
    async def get_logs(self, 
                      service: str = None, 
                      follow: bool = False, 
                      tail: int = 100) -> str:
        """Get service logs"""
        try:
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'logs'
            ]
            
            if follow:
                cmd.append('-f')
            
            if tail > 0:
                cmd.extend(['--tail', str(tail)])
            
            if service:
                cmd.append(service)
            
            process = subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=30 if not follow else None
            )
            
            return process.stdout
        
        except Exception as e:
            return f"Error retrieving logs: {str(e)}"
    
    async def cleanup(self, remove_volumes: bool = False) -> DeploymentResult:
        """Clean up deployment resources"""
        logger.info("Cleaning up deployment resources...")
        
        try:
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'down', '--remove-orphans'
            ]
            
            if remove_volumes:
                cmd.append('--volumes')
            
            process = subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if process.returncode == 0:
                self.status = DeploymentStatus.NOT_STARTED
                return DeploymentResult(
                    success=True,
                    status=DeploymentStatus.NOT_STARTED,
                    message="Cleanup completed successfully"
                )
            else:
                return DeploymentResult(
                    success=False,
                    status=self.status,
                    message="Cleanup failed",
                    details={'stderr': process.stderr}
                )
        
        except Exception as e:
            return DeploymentResult(
                success=False,
                status=self.status,
                message=f"Cleanup error: {str(e)}"
            )


async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Docker Deployment Manager for Thai Tokenizer")
    parser.add_argument('command', choices=[
        'validate', 'deploy', 'health', 'stop', 'restart', 'logs', 'cleanup'
    ])
    parser.add_argument('--profile', action='append', help='Docker Compose profiles')
    parser.add_argument('--no-build', action='store_true', help='Skip building images')
    parser.add_argument('--no-detach', action='store_true', help='Run in foreground')
    parser.add_argument('--service', help='Specific service for logs')
    parser.add_argument('--follow', action='store_true', help='Follow logs')
    parser.add_argument('--remove-volumes', action='store_true', help='Remove volumes during cleanup')
    
    args = parser.parse_args()
    
    manager = DockerDeploymentManager()
    
    if args.command == 'validate':
        result = await manager.validate_prerequisites()
        print(f"Validation: {'PASSED' if result.success else 'FAILED'}")
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
    
    elif args.command == 'deploy':
        result = await manager.deploy(
            profiles=args.profile,
            build=not args.no_build,
            detach=not args.no_detach
        )
        print(f"Deployment: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Message: {result.message}")
    
    elif args.command == 'health':
        result = await manager.check_health()
        print(f"Health: {'HEALTHY' if result.healthy else 'UNHEALTHY'}")
        print(f"Response time: {result.response_time_ms:.2f}ms")
        print("Services:")
        for service, status in result.services.items():
            print(f"  {service}: {'OK' if status else 'FAIL'}")
    
    elif args.command == 'stop':
        result = await manager.stop()
        print(f"Stop: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Message: {result.message}")
    
    elif args.command == 'restart':
        result = await manager.restart()
        print(f"Restart: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Message: {result.message}")
    
    elif args.command == 'logs':
        logs = await manager.get_logs(
            service=args.service,
            follow=args.follow
        )
        print(logs)
    
    elif args.command == 'cleanup':
        result = await manager.cleanup(remove_volumes=args.remove_volumes)
        print(f"Cleanup: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Message: {result.message}")


if __name__ == '__main__':
    asyncio.run(main())