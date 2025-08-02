#!/usr/bin/env python3
"""
Docker Health Check and Monitoring System for Thai Tokenizer Service
Provides comprehensive health monitoring and alerting for Docker deployments
"""

import asyncio
import json
import logging
import os
import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import requests
import psutil
from enum import Enum

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status of a single component"""
    name: str
    status: HealthStatus
    message: str = ""
    response_time_ms: float = 0.0
    details: Dict[str, any] = field(default_factory=dict)
    last_check: datetime = field(default_factory=datetime.now)


@dataclass
class SystemHealth:
    """Overall system health status"""
    status: HealthStatus
    components: Dict[str, ComponentHealth] = field(default_factory=dict)
    overall_response_time_ms: float = 0.0
    check_timestamp: datetime = field(default_factory=datetime.now)
    uptime_seconds: float = 0.0


@dataclass
class MetricPoint:
    """Single metric data point"""
    timestamp: datetime
    value: float
    labels: Dict[str, str] = field(default_factory=dict)


@dataclass
class PerformanceMetrics:
    """Performance metrics collection"""
    cpu_usage_percent: float = 0.0
    memory_usage_mb: float = 0.0
    memory_usage_percent: float = 0.0
    disk_usage_percent: float = 0.0
    network_rx_bytes: int = 0
    network_tx_bytes: int = 0
    request_count: int = 0
    error_count: int = 0
    avg_response_time_ms: float = 0.0


class DockerHealthMonitor:
    """
    Comprehensive health monitoring system for Docker deployments
    Requirements: 2.2, 5.2, 7.5
    """
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path(__file__).parent
        self.project_root = self.config_dir.parent.parent
        self.compose_file = self.config_dir / "docker-compose.external-meilisearch.yml"
        self.env_file = self.config_dir / ".env.external-meilisearch"
        
        # Monitoring configuration
        self.monitoring_dir = self.project_root / "monitoring" / "docker"
        self.monitoring_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.config = self._load_configuration()
        
        # Health check history
        self.health_history: List[SystemHealth] = []
        self.max_history_size = 1000
        
        # Performance metrics
        self.metrics_history: List[PerformanceMetrics] = []
        self.start_time = datetime.now()
        
    def _load_configuration(self) -> Dict[str, str]:
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
    
    async def check_comprehensive_health(self) -> SystemHealth:
        """
        Perform comprehensive health check of all system components
        Requirements: 2.2, 5.2
        """
        start_time = time.time()
        logger.info("Starting comprehensive health check...")
        
        system_health = SystemHealth(status=HealthStatus.HEALTHY)
        
        # Check individual components
        components_to_check = [
            ('docker_daemon', self._check_docker_daemon),
            ('containers', self._check_containers),
            ('thai_tokenizer_api', self._check_thai_tokenizer_api),
            ('meilisearch_connectivity', self._check_meilisearch_connectivity),
            ('system_resources', self._check_system_resources),
            ('network_connectivity', self._check_network_connectivity),
            ('storage_health', self._check_storage_health)
        ]
        
        for component_name, check_function in components_to_check:
            try:
                component_health = await check_function()
                system_health.components[component_name] = component_health
                
                # Update overall status based on component status
                if component_health.status == HealthStatus.UNHEALTHY:
                    system_health.status = HealthStatus.UNHEALTHY
                elif (component_health.status == HealthStatus.DEGRADED and 
                      system_health.status == HealthStatus.HEALTHY):
                    system_health.status = HealthStatus.DEGRADED
                    
            except Exception as e:
                logger.error(f"Health check failed for {component_name}: {str(e)}")
                system_health.components[component_name] = ComponentHealth(
                    name=component_name,
                    status=HealthStatus.UNKNOWN,
                    message=f"Health check error: {str(e)}"
                )
                system_health.status = HealthStatus.DEGRADED
        
        # Calculate overall response time and uptime
        system_health.overall_response_time_ms = (time.time() - start_time) * 1000
        system_health.uptime_seconds = (datetime.now() - self.start_time).total_seconds()
        
        # Store in history
        self._store_health_history(system_health)
        
        logger.info(f"Health check completed: {system_health.status.value}")
        return system_health
    
    async def _check_docker_daemon(self) -> ComponentHealth:
        """Check Docker daemon health"""
        start_time = time.time()
        
        try:
            # Check Docker daemon status
            process = subprocess.run(
                ['docker', 'info'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            response_time = (time.time() - start_time) * 1000
            
            if process.returncode == 0:
                # Parse Docker info for additional details
                docker_info = {}
                for line in process.stdout.split('\n'):
                    if ':' in line:
                        key, value = line.split(':', 1)
                        docker_info[key.strip()] = value.strip()
                
                return ComponentHealth(
                    name="docker_daemon",
                    status=HealthStatus.HEALTHY,
                    message="Docker daemon is running",
                    response_time_ms=response_time,
                    details={
                        'containers_running': docker_info.get('Containers', 'unknown'),
                        'images': docker_info.get('Images', 'unknown'),
                        'server_version': docker_info.get('Server Version', 'unknown')
                    }
                )
            else:
                return ComponentHealth(
                    name="docker_daemon",
                    status=HealthStatus.UNHEALTHY,
                    message="Docker daemon is not responding",
                    response_time_ms=response_time
                )
                
        except subprocess.TimeoutExpired:
            return ComponentHealth(
                name="docker_daemon",
                status=HealthStatus.UNHEALTHY,
                message="Docker daemon check timeout"
            )
        except Exception as e:
            return ComponentHealth(
                name="docker_daemon",
                status=HealthStatus.UNKNOWN,
                message=f"Docker daemon check error: {str(e)}"
            )
    
    async def _check_containers(self) -> ComponentHealth:
        """Check container health status"""
        start_time = time.time()
        
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
            
            response_time = (time.time() - start_time) * 1000
            
            if process.returncode != 0:
                return ComponentHealth(
                    name="containers",
                    status=HealthStatus.UNKNOWN,
                    message="Could not retrieve container status",
                    response_time_ms=response_time
                )
            
            # Parse container information
            containers = []
            unhealthy_count = 0
            
            for line in process.stdout.strip().split('\n'):
                if line:
                    try:
                        container_info = json.loads(line)
                        containers.append(container_info)
                        
                        state = container_info.get('State', '')
                        health = container_info.get('Health', '')
                        
                        if state != 'running' or health == 'unhealthy':
                            unhealthy_count += 1
                            
                    except json.JSONDecodeError:
                        continue
            
            # Determine overall container health
            if not containers:
                status = HealthStatus.UNHEALTHY
                message = "No containers found"
            elif unhealthy_count == 0:
                status = HealthStatus.HEALTHY
                message = f"All {len(containers)} containers are healthy"
            elif unhealthy_count < len(containers):
                status = HealthStatus.DEGRADED
                message = f"{unhealthy_count}/{len(containers)} containers are unhealthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = f"All {len(containers)} containers are unhealthy"
            
            return ComponentHealth(
                name="containers",
                status=status,
                message=message,
                response_time_ms=response_time,
                details={
                    'total_containers': len(containers),
                    'unhealthy_containers': unhealthy_count,
                    'containers': containers
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="containers",
                status=HealthStatus.UNKNOWN,
                message=f"Container check error: {str(e)}"
            )
    
    async def _check_thai_tokenizer_api(self) -> ComponentHealth:
        """Check Thai Tokenizer API health"""
        start_time = time.time()
        
        try:
            service_port = int(self.config.get('THAI_TOKENIZER_PORT', 8000))
            
            # Basic health check
            health_url = f"http://localhost:{service_port}/health"
            health_response = requests.get(health_url, timeout=10)
            
            basic_response_time = (time.time() - start_time) * 1000
            
            if health_response.status_code != 200:
                return ComponentHealth(
                    name="thai_tokenizer_api",
                    status=HealthStatus.UNHEALTHY,
                    message=f"API health endpoint returned {health_response.status_code}",
                    response_time_ms=basic_response_time
                )
            
            # Detailed health check
            detailed_start = time.time()
            detailed_url = f"http://localhost:{service_port}/health/detailed"
            detailed_response = requests.get(detailed_url, timeout=15)
            
            total_response_time = (time.time() - start_time) * 1000
            
            if detailed_response.status_code == 200:
                detailed_data = detailed_response.json()
                
                # Check specific health indicators
                meilisearch_status = detailed_data.get('meilisearch_status', 'unknown')
                tokenizer_status = detailed_data.get('tokenizer_status', 'unknown')
                
                if meilisearch_status == 'healthy' and tokenizer_status == 'healthy':
                    status = HealthStatus.HEALTHY
                    message = "API is fully functional"
                elif meilisearch_status == 'healthy' or tokenizer_status == 'healthy':
                    status = HealthStatus.DEGRADED
                    message = "API is partially functional"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = "API components are not healthy"
                
                return ComponentHealth(
                    name="thai_tokenizer_api",
                    status=status,
                    message=message,
                    response_time_ms=total_response_time,
                    details=detailed_data
                )
            else:
                return ComponentHealth(
                    name="thai_tokenizer_api",
                    status=HealthStatus.DEGRADED,
                    message="Basic health OK, detailed health unavailable",
                    response_time_ms=total_response_time
                )
                
        except requests.RequestException as e:
            return ComponentHealth(
                name="thai_tokenizer_api",
                status=HealthStatus.UNHEALTHY,
                message=f"API connectivity error: {str(e)}"
            )
        except Exception as e:
            return ComponentHealth(
                name="thai_tokenizer_api",
                status=HealthStatus.UNKNOWN,
                message=f"API check error: {str(e)}"
            )
    
    async def _check_meilisearch_connectivity(self) -> ComponentHealth:
        """Check Meilisearch connectivity"""
        start_time = time.time()
        
        if 'MEILISEARCH_HOST' not in self.config:
            return ComponentHealth(
                name="meilisearch_connectivity",
                status=HealthStatus.UNKNOWN,
                message="Meilisearch host not configured"
            )
        
        try:
            host = self.config['MEILISEARCH_HOST']
            api_key = self.config.get('MEILISEARCH_API_KEY', '')
            
            # Test health endpoint
            health_url = f"{host}/health"
            health_response = requests.get(health_url, timeout=10)
            
            response_time = (time.time() - start_time) * 1000
            
            if health_response.status_code != 200:
                return ComponentHealth(
                    name="meilisearch_connectivity",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Meilisearch health check failed: {health_response.status_code}",
                    response_time_ms=response_time
                )
            
            # Test authentication if API key is configured
            if api_key:
                auth_start = time.time()
                keys_url = f"{host}/keys"
                auth_response = requests.get(
                    keys_url,
                    headers={'Authorization': f'Bearer {api_key}'},
                    timeout=10
                )
                
                total_response_time = (time.time() - start_time) * 1000
                
                if auth_response.status_code != 200:
                    return ComponentHealth(
                        name="meilisearch_connectivity",
                        status=HealthStatus.DEGRADED,
                        message="Meilisearch accessible but authentication failed",
                        response_time_ms=total_response_time
                    )
            
            return ComponentHealth(
                name="meilisearch_connectivity",
                status=HealthStatus.HEALTHY,
                message="Meilisearch is accessible and authenticated",
                response_time_ms=response_time,
                details={
                    'host': host,
                    'authenticated': bool(api_key)
                }
            )
            
        except requests.RequestException as e:
            return ComponentHealth(
                name="meilisearch_connectivity",
                status=HealthStatus.UNHEALTHY,
                message=f"Meilisearch connectivity error: {str(e)}"
            )
        except Exception as e:
            return ComponentHealth(
                name="meilisearch_connectivity",
                status=HealthStatus.UNKNOWN,
                message=f"Meilisearch check error: {str(e)}"
            )
    
    async def _check_system_resources(self) -> ComponentHealth:
        """Check system resource utilization"""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            memory_available_gb = memory.available / (1024**3)
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_percent = disk.percent
            disk_free_gb = disk.free / (1024**3)
            
            # Determine status based on thresholds
            status = HealthStatus.HEALTHY
            warnings = []
            
            if cpu_percent > 90:
                status = HealthStatus.UNHEALTHY
                warnings.append(f"CPU usage critical: {cpu_percent:.1f}%")
            elif cpu_percent > 75:
                status = HealthStatus.DEGRADED
                warnings.append(f"CPU usage high: {cpu_percent:.1f}%")
            
            if memory_percent > 95:
                status = HealthStatus.UNHEALTHY
                warnings.append(f"Memory usage critical: {memory_percent:.1f}%")
            elif memory_percent > 85:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                warnings.append(f"Memory usage high: {memory_percent:.1f}%")
            
            if disk_percent > 95:
                status = HealthStatus.UNHEALTHY
                warnings.append(f"Disk usage critical: {disk_percent:.1f}%")
            elif disk_percent > 85:
                if status == HealthStatus.HEALTHY:
                    status = HealthStatus.DEGRADED
                warnings.append(f"Disk usage high: {disk_percent:.1f}%")
            
            message = "System resources are healthy"
            if warnings:
                message = "; ".join(warnings)
            
            return ComponentHealth(
                name="system_resources",
                status=status,
                message=message,
                details={
                    'cpu_percent': cpu_percent,
                    'memory_percent': memory_percent,
                    'memory_available_gb': round(memory_available_gb, 2),
                    'disk_percent': disk_percent,
                    'disk_free_gb': round(disk_free_gb, 2)
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="system_resources",
                status=HealthStatus.UNKNOWN,
                message=f"Resource check error: {str(e)}"
            )
    
    async def _check_network_connectivity(self) -> ComponentHealth:
        """Check network connectivity"""
        try:
            # Check if required ports are accessible
            service_port = int(self.config.get('THAI_TOKENIZER_PORT', 8000))
            
            import socket
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                result = s.connect_ex(('localhost', service_port))
                
                if result == 0:
                    status = HealthStatus.HEALTHY
                    message = f"Service port {service_port} is accessible"
                else:
                    status = HealthStatus.UNHEALTHY
                    message = f"Service port {service_port} is not accessible"
            
            return ComponentHealth(
                name="network_connectivity",
                status=status,
                message=message,
                details={'service_port': service_port}
            )
            
        except Exception as e:
            return ComponentHealth(
                name="network_connectivity",
                status=HealthStatus.UNKNOWN,
                message=f"Network check error: {str(e)}"
            )
    
    async def _check_storage_health(self) -> ComponentHealth:
        """Check storage and volume health"""
        try:
            # Check Docker volumes
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'config', '--volumes'
            ]
            
            process = subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if process.returncode != 0:
                return ComponentHealth(
                    name="storage_health",
                    status=HealthStatus.UNKNOWN,
                    message="Could not check volume configuration"
                )
            
            volumes = [v.strip() for v in process.stdout.strip().split('\n') if v.strip()]
            
            # Check if volumes exist
            volume_status = {}
            for volume in volumes:
                volume_cmd = ['docker', 'volume', 'inspect', volume]
                volume_process = subprocess.run(
                    volume_cmd,
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                volume_status[volume] = volume_process.returncode == 0
            
            healthy_volumes = sum(volume_status.values())
            total_volumes = len(volumes)
            
            if healthy_volumes == total_volumes:
                status = HealthStatus.HEALTHY
                message = f"All {total_volumes} volumes are healthy"
            elif healthy_volumes > 0:
                status = HealthStatus.DEGRADED
                message = f"{healthy_volumes}/{total_volumes} volumes are healthy"
            else:
                status = HealthStatus.UNHEALTHY
                message = "No volumes are accessible"
            
            return ComponentHealth(
                name="storage_health",
                status=status,
                message=message,
                details={
                    'total_volumes': total_volumes,
                    'healthy_volumes': healthy_volumes,
                    'volume_status': volume_status
                }
            )
            
        except Exception as e:
            return ComponentHealth(
                name="storage_health",
                status=HealthStatus.UNKNOWN,
                message=f"Storage check error: {str(e)}"
            )
    
    def _store_health_history(self, health: SystemHealth):
        """Store health check result in history"""
        self.health_history.append(health)
        
        # Limit history size
        if len(self.health_history) > self.max_history_size:
            self.health_history = self.health_history[-self.max_history_size:]
    
    async def collect_performance_metrics(self) -> PerformanceMetrics:
        """
        Collect performance metrics from containers and system
        Requirements: 5.2, 7.5
        """
        metrics = PerformanceMetrics()
        
        try:
            # Get container statistics
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'ps', '-q'
            ]
            
            process = subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if process.returncode == 0:
                container_ids = [cid.strip() for cid in process.stdout.strip().split('\n') if cid.strip()]
                
                for container_id in container_ids:
                    container_metrics = await self._get_container_metrics(container_id)
                    
                    # Aggregate metrics
                    metrics.cpu_usage_percent += container_metrics.get('cpu_percent', 0)
                    metrics.memory_usage_mb += container_metrics.get('memory_mb', 0)
                    metrics.network_rx_bytes += container_metrics.get('network_rx', 0)
                    metrics.network_tx_bytes += container_metrics.get('network_tx', 0)
            
            # Get system-level metrics
            system_metrics = await self._get_system_metrics()
            metrics.memory_usage_percent = system_metrics.get('memory_percent', 0)
            metrics.disk_usage_percent = system_metrics.get('disk_percent', 0)
            
            # Get application-specific metrics if available
            app_metrics = await self._get_application_metrics()
            metrics.request_count = app_metrics.get('request_count', 0)
            metrics.error_count = app_metrics.get('error_count', 0)
            metrics.avg_response_time_ms = app_metrics.get('avg_response_time_ms', 0)
            
        except Exception as e:
            logger.error(f"Error collecting performance metrics: {str(e)}")
        
        # Store metrics in history
        self.metrics_history.append(metrics)
        if len(self.metrics_history) > self.max_history_size:
            self.metrics_history = self.metrics_history[-self.max_history_size:]
        
        return metrics
    
    async def _get_container_metrics(self, container_id: str) -> Dict[str, float]:
        """Get metrics for a specific container"""
        try:
            cmd = ['docker', 'stats', '--no-stream', '--format', 'json', container_id]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if process.returncode == 0:
                stats = json.loads(process.stdout.strip())
                
                # Parse CPU percentage
                cpu_str = stats.get('CPUPerc', '0%').rstrip('%')
                cpu_percent = float(cpu_str) if cpu_str != 'N/A' else 0.0
                
                # Parse memory usage
                mem_usage = stats.get('MemUsage', '0B / 0B')
                if ' / ' in mem_usage:
                    used_str = mem_usage.split(' / ')[0]
                    memory_mb = self._parse_memory_string(used_str)
                else:
                    memory_mb = 0.0
                
                # Parse network I/O
                net_io = stats.get('NetIO', '0B / 0B')
                if ' / ' in net_io:
                    rx_str, tx_str = net_io.split(' / ')
                    network_rx = self._parse_memory_string(rx_str)
                    network_tx = self._parse_memory_string(tx_str)
                else:
                    network_rx = network_tx = 0.0
                
                return {
                    'cpu_percent': cpu_percent,
                    'memory_mb': memory_mb,
                    'network_rx': int(network_rx * 1024 * 1024),  # Convert to bytes
                    'network_tx': int(network_tx * 1024 * 1024)   # Convert to bytes
                }
            
        except Exception as e:
            logger.warning(f"Could not get metrics for container {container_id}: {str(e)}")
        
        return {}
    
    def _parse_memory_string(self, mem_str: str) -> float:
        """Parse memory string like '123.4MiB' to MB"""
        try:
            mem_str = mem_str.strip()
            if mem_str.endswith('B'):
                mem_str = mem_str[:-1]
            
            if mem_str.endswith('Ki'):
                return float(mem_str[:-2]) / 1024
            elif mem_str.endswith('Mi'):
                return float(mem_str[:-2])
            elif mem_str.endswith('Gi'):
                return float(mem_str[:-2]) * 1024
            elif mem_str.endswith('K'):
                return float(mem_str[:-1]) / 1024
            elif mem_str.endswith('M'):
                return float(mem_str[:-1])
            elif mem_str.endswith('G'):
                return float(mem_str[:-1]) * 1024
            else:
                return float(mem_str) / (1024 * 1024)  # Assume bytes
                
        except (ValueError, IndexError):
            return 0.0
    
    async def _get_system_metrics(self) -> Dict[str, float]:
        """Get system-level metrics"""
        try:
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return {
                'memory_percent': memory.percent,
                'disk_percent': disk.percent
            }
        except Exception:
            return {}
    
    async def _get_application_metrics(self) -> Dict[str, float]:
        """Get application-specific metrics from the API"""
        try:
            service_port = int(self.config.get('THAI_TOKENIZER_PORT', 8000))
            metrics_url = f"http://localhost:{service_port}/metrics"
            
            response = requests.get(metrics_url, timeout=5)
            
            if response.status_code == 200:
                # Parse Prometheus-style metrics
                metrics_text = response.text
                metrics = {}
                
                for line in metrics_text.split('\n'):
                    if line and not line.startswith('#'):
                        if ' ' in line:
                            metric_name, value = line.rsplit(' ', 1)
                            try:
                                metrics[metric_name] = float(value)
                            except ValueError:
                                continue
                
                return {
                    'request_count': metrics.get('http_requests_total', 0),
                    'error_count': metrics.get('http_errors_total', 0),
                    'avg_response_time_ms': metrics.get('http_request_duration_ms', 0)
                }
            
        except Exception as e:
            logger.debug(f"Could not get application metrics: {str(e)}")
        
        return {}
    
    async def generate_health_report(self) -> Dict[str, any]:
        """Generate comprehensive health report"""
        health = await self.check_comprehensive_health()
        metrics = await self.collect_performance_metrics()
        
        # Calculate health trends
        recent_health = self.health_history[-10:] if len(self.health_history) >= 10 else self.health_history
        health_trend = self._calculate_health_trend(recent_health)
        
        # Calculate performance trends
        recent_metrics = self.metrics_history[-10:] if len(self.metrics_history) >= 10 else self.metrics_history
        performance_trend = self._calculate_performance_trend(recent_metrics)
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'overall_status': health.status.value,
            'uptime_seconds': health.uptime_seconds,
            'components': {
                name: {
                    'status': comp.status.value,
                    'message': comp.message,
                    'response_time_ms': comp.response_time_ms,
                    'details': comp.details
                }
                for name, comp in health.components.items()
            },
            'performance_metrics': {
                'cpu_usage_percent': metrics.cpu_usage_percent,
                'memory_usage_mb': metrics.memory_usage_mb,
                'memory_usage_percent': metrics.memory_usage_percent,
                'disk_usage_percent': metrics.disk_usage_percent,
                'network_rx_bytes': metrics.network_rx_bytes,
                'network_tx_bytes': metrics.network_tx_bytes,
                'request_count': metrics.request_count,
                'error_count': metrics.error_count,
                'avg_response_time_ms': metrics.avg_response_time_ms
            },
            'trends': {
                'health_trend': health_trend,
                'performance_trend': performance_trend
            },
            'recommendations': self._generate_recommendations(health, metrics)
        }
        
        return report
    
    def _calculate_health_trend(self, health_history: List[SystemHealth]) -> str:
        """Calculate health trend from recent history"""
        if len(health_history) < 2:
            return "insufficient_data"
        
        # Count status occurrences in recent history
        status_counts = {}
        for health in health_history:
            status = health.status.value
            status_counts[status] = status_counts.get(status, 0) + 1
        
        # Determine trend
        recent_status = health_history[-1].status.value
        older_status = health_history[0].status.value
        
        if recent_status == 'healthy' and older_status != 'healthy':
            return "improving"
        elif recent_status != 'healthy' and older_status == 'healthy':
            return "degrading"
        elif recent_status == older_status:
            return "stable"
        else:
            return "fluctuating"
    
    def _calculate_performance_trend(self, metrics_history: List[PerformanceMetrics]) -> str:
        """Calculate performance trend from recent history"""
        if len(metrics_history) < 2:
            return "insufficient_data"
        
        # Compare recent vs older metrics
        recent = metrics_history[-1]
        older = metrics_history[0]
        
        # Calculate trend based on key metrics
        cpu_trend = recent.cpu_usage_percent - older.cpu_usage_percent
        memory_trend = recent.memory_usage_percent - older.memory_usage_percent
        response_time_trend = recent.avg_response_time_ms - older.avg_response_time_ms
        
        # Determine overall trend
        if cpu_trend > 10 or memory_trend > 10 or response_time_trend > 50:
            return "degrading"
        elif cpu_trend < -10 or memory_trend < -10 or response_time_trend < -50:
            return "improving"
        else:
            return "stable"
    
    def _generate_recommendations(self, health: SystemHealth, metrics: PerformanceMetrics) -> List[str]:
        """Generate recommendations based on health and performance data"""
        recommendations = []
        
        # Resource-based recommendations
        if metrics.cpu_usage_percent > 80:
            recommendations.append("Consider increasing CPU resources or reducing worker processes")
        
        if metrics.memory_usage_percent > 85:
            recommendations.append("Consider increasing memory allocation or optimizing memory usage")
        
        if metrics.disk_usage_percent > 85:
            recommendations.append("Consider cleaning up logs or increasing disk space")
        
        if metrics.avg_response_time_ms > 1000:
            recommendations.append("Response times are high, consider performance optimization")
        
        # Component-specific recommendations
        for name, component in health.components.items():
            if component.status == HealthStatus.UNHEALTHY:
                if name == "meilisearch_connectivity":
                    recommendations.append("Check Meilisearch server status and network connectivity")
                elif name == "containers":
                    recommendations.append("Check container logs and restart unhealthy containers")
                elif name == "thai_tokenizer_api":
                    recommendations.append("Check API service logs and configuration")
        
        return recommendations
    
    async def export_metrics_prometheus(self) -> str:
        """Export metrics in Prometheus format"""
        metrics = await self.collect_performance_metrics()
        health = await self.check_comprehensive_health()
        
        prometheus_metrics = []
        
        # Health status metrics (0=unknown, 1=unhealthy, 2=degraded, 3=healthy)
        status_value = {
            HealthStatus.UNKNOWN: 0,
            HealthStatus.UNHEALTHY: 1,
            HealthStatus.DEGRADED: 2,
            HealthStatus.HEALTHY: 3
        }
        
        prometheus_metrics.append(f"thai_tokenizer_health_status {status_value[health.status]}")
        prometheus_metrics.append(f"thai_tokenizer_uptime_seconds {health.uptime_seconds}")
        prometheus_metrics.append(f"thai_tokenizer_health_check_duration_ms {health.overall_response_time_ms}")
        
        # Component health metrics
        for name, component in health.components.items():
            prometheus_metrics.append(
                f'thai_tokenizer_component_health{{component="{name}"}} {status_value[component.status]}'
            )
            prometheus_metrics.append(
                f'thai_tokenizer_component_response_time_ms{{component="{name}"}} {component.response_time_ms}'
            )
        
        # Performance metrics
        prometheus_metrics.append(f"thai_tokenizer_cpu_usage_percent {metrics.cpu_usage_percent}")
        prometheus_metrics.append(f"thai_tokenizer_memory_usage_mb {metrics.memory_usage_mb}")
        prometheus_metrics.append(f"thai_tokenizer_memory_usage_percent {metrics.memory_usage_percent}")
        prometheus_metrics.append(f"thai_tokenizer_disk_usage_percent {metrics.disk_usage_percent}")
        prometheus_metrics.append(f"thai_tokenizer_network_rx_bytes {metrics.network_rx_bytes}")
        prometheus_metrics.append(f"thai_tokenizer_network_tx_bytes {metrics.network_tx_bytes}")
        prometheus_metrics.append(f"thai_tokenizer_request_count {metrics.request_count}")
        prometheus_metrics.append(f"thai_tokenizer_error_count {metrics.error_count}")
        prometheus_metrics.append(f"thai_tokenizer_avg_response_time_ms {metrics.avg_response_time_ms}")
        
        return '\n'.join(prometheus_metrics) + '\n'


async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Docker Health Monitor for Thai Tokenizer")
    parser.add_argument('command', choices=[
        'health', 'metrics', 'report', 'prometheus', 'monitor'
    ])
    parser.add_argument('--interval', type=int, default=30, help='Monitoring interval in seconds')
    parser.add_argument('--output', help='Output file for reports')
    
    args = parser.parse_args()
    
    monitor = DockerHealthMonitor()
    
    if args.command == 'health':
        health = await monitor.check_comprehensive_health()
        print(f"Overall Status: {health.status.value.upper()}")
        print(f"Uptime: {health.uptime_seconds:.0f} seconds")
        print(f"Response Time: {health.overall_response_time_ms:.2f}ms")
        print("\nComponents:")
        for name, component in health.components.items():
            status_icon = "✓" if component.status == HealthStatus.HEALTHY else "✗"
            print(f"  {status_icon} {name}: {component.status.value} - {component.message}")
    
    elif args.command == 'metrics':
        metrics = await monitor.collect_performance_metrics()
        print("Performance Metrics:")
        print(f"  CPU Usage: {metrics.cpu_usage_percent:.1f}%")
        print(f"  Memory Usage: {metrics.memory_usage_mb:.1f}MB ({metrics.memory_usage_percent:.1f}%)")
        print(f"  Disk Usage: {metrics.disk_usage_percent:.1f}%")
        print(f"  Network RX: {metrics.network_rx_bytes} bytes")
        print(f"  Network TX: {metrics.network_tx_bytes} bytes")
        print(f"  Requests: {metrics.request_count}")
        print(f"  Errors: {metrics.error_count}")
        print(f"  Avg Response Time: {metrics.avg_response_time_ms:.2f}ms")
    
    elif args.command == 'report':
        report = await monitor.generate_health_report()
        report_json = json.dumps(report, indent=2)
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(report_json)
            print(f"Report saved to {args.output}")
        else:
            print(report_json)
    
    elif args.command == 'prometheus':
        prometheus_metrics = await monitor.export_metrics_prometheus()
        
        if args.output:
            with open(args.output, 'w') as f:
                f.write(prometheus_metrics)
            print(f"Prometheus metrics saved to {args.output}")
        else:
            print(prometheus_metrics)
    
    elif args.command == 'monitor':
        print(f"Starting continuous monitoring (interval: {args.interval}s)")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                health = await monitor.check_comprehensive_health()
                metrics = await monitor.collect_performance_metrics()
                
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                print(f"\n[{timestamp}] Status: {health.status.value.upper()}")
                print(f"CPU: {metrics.cpu_usage_percent:.1f}% | "
                      f"Memory: {metrics.memory_usage_percent:.1f}% | "
                      f"Disk: {metrics.disk_usage_percent:.1f}% | "
                      f"Response: {health.overall_response_time_ms:.0f}ms")
                
                await asyncio.sleep(args.interval)
                
        except KeyboardInterrupt:
            print("\nMonitoring stopped")


if __name__ == '__main__':
    asyncio.run(main())