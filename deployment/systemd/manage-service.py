#!/usr/bin/env python3
"""
Systemd service management utility for Thai Tokenizer.

This script provides comprehensive service management operations including
start, stop, restart, status, logs, and configuration management for the
Thai Tokenizer systemd service.
"""

import os
import sys
import argparse
import asyncio
import json
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.deployment.config import OnPremiseConfig, ValidationResult
    from src.deployment.systemd_manager import SystemdServiceManager, SystemdDeploymentValidator
    from src.utils.logging import get_structured_logger
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you're running this script from the project root directory")
    sys.exit(1)

logger = get_structured_logger(__name__)


class ServiceController:
    """Main service controller for systemd operations."""
    
    def __init__(self, service_name: str = "thai-tokenizer"):
        """Initialize with service name."""
        self.service_name = service_name
        self.service_manager = SystemdServiceManager(service_name)
        self.logger = get_structured_logger(f"{__name__}.ServiceController")
    
    async def start_service(self) -> ValidationResult:
        """Start the systemd service."""
        self.logger.info(f"Starting service: {self.service_name}")
        return self.service_manager.start_service()
    
    async def stop_service(self) -> ValidationResult:
        """Stop the systemd service."""
        self.logger.info(f"Stopping service: {self.service_name}")
        return self.service_manager.stop_service()
    
    async def restart_service(self) -> ValidationResult:
        """Restart the systemd service."""
        self.logger.info(f"Restarting service: {self.service_name}")
        return self.service_manager.restart_service()
    
    async def get_status(self) -> Dict[str, Any]:
        """Get comprehensive service status."""
        is_active, status_output = self.service_manager.get_service_status()
        
        # Get additional service information
        try:
            import subprocess
            
            # Get service properties
            props_result = subprocess.run([
                "systemctl", "show", self.service_name,
                "--property=ActiveState,SubState,LoadState,UnitFileState,MainPID,ExecMainStartTimestamp"
            ], capture_output=True, text=True)
            
            properties = {}
            if props_result.returncode == 0:
                for line in props_result.stdout.strip().split('\n'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        properties[key] = value
            
            # Get memory and CPU usage if service is running
            resource_info = {}
            if is_active and properties.get('MainPID', '0') != '0':
                try:
                    pid = properties['MainPID']
                    
                    # Get memory usage
                    memory_result = subprocess.run([
                        "ps", "-p", pid, "-o", "rss="
                    ], capture_output=True, text=True)
                    
                    if memory_result.returncode == 0:
                        memory_kb = int(memory_result.stdout.strip())
                        resource_info['memory_mb'] = round(memory_kb / 1024, 2)
                    
                    # Get CPU usage
                    cpu_result = subprocess.run([
                        "ps", "-p", pid, "-o", "pcpu="
                    ], capture_output=True, text=True)
                    
                    if cpu_result.returncode == 0:
                        resource_info['cpu_percent'] = float(cpu_result.stdout.strip())
                
                except (ValueError, subprocess.CalledProcessError):
                    pass
            
            return {
                'service_name': self.service_name,
                'is_active': is_active,
                'status_output': status_output,
                'properties': properties,
                'resource_usage': resource_info,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            return {
                'service_name': self.service_name,
                'is_active': is_active,
                'status_output': status_output,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    async def get_logs(self, lines: int = 50, follow: bool = False) -> str:
        """Get service logs."""
        if follow:
            # For follow mode, we'll just return the command to run
            return f"journalctl -u {self.service_name} -f"
        else:
            return self.service_manager.get_service_logs(lines)
    
    async def reload_configuration(self) -> ValidationResult:
        """Reload service configuration."""
        result = ValidationResult(valid=True)
        
        try:
            import subprocess
            
            # Reload systemd daemon
            subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)
            result.warnings.append("Reloaded systemd daemon")
            
            # Reload the service if it's running
            is_active, _ = self.service_manager.get_service_status()
            if is_active:
                reload_result = subprocess.run([
                    "systemctl", "reload-or-restart", self.service_name
                ], capture_output=True, text=True)
                
                if reload_result.returncode == 0:
                    result.warnings.append(f"Reloaded service: {self.service_name}")
                else:
                    result.errors.append(f"Failed to reload service: {reload_result.stderr}")
                    result.valid = False
            else:
                result.warnings.append("Service is not running, skipping reload")
            
        except subprocess.CalledProcessError as e:
            result.valid = False
            result.errors.append(f"Failed to reload configuration: {e.stderr}")
        except Exception as e:
            result.valid = False
            result.errors.append(f"Unexpected error reloading configuration: {e}")
        
        return result
    
    async def validate_configuration(self, config_path: Optional[str] = None) -> ValidationResult:
        """Validate service configuration."""
        result = ValidationResult(valid=True)
        
        try:
            # Load configuration if provided
            if config_path:
                config_file = Path(config_path)
                if not config_file.exists():
                    result.valid = False
                    result.errors.append(f"Configuration file not found: {config_path}")
                    return result
                
                try:
                    with open(config_file, 'r') as f:
                        config_data = json.load(f)
                    config = OnPremiseConfig(**config_data)
                    
                    # Validate the configuration
                    validator = SystemdDeploymentValidator(config)
                    validation_result = await validator.validate_full_configuration()
                    
                    result.errors.extend(validation_result.errors)
                    result.warnings.extend(validation_result.warnings)
                    if not validation_result.valid:
                        result.valid = False
                    
                except Exception as e:
                    result.valid = False
                    result.errors.append(f"Failed to load/validate configuration: {e}")
            
            # Check service file syntax
            try:
                import subprocess
                service_file = f"/etc/systemd/system/{self.service_name}.service"
                
                if Path(service_file).exists():
                    # Use systemd-analyze to verify service file
                    analyze_result = subprocess.run([
                        "systemd-analyze", "verify", service_file
                    ], capture_output=True, text=True)
                    
                    if analyze_result.returncode == 0:
                        result.warnings.append("Service file syntax is valid")
                    else:
                        result.errors.append(f"Service file syntax errors: {analyze_result.stderr}")
                        result.valid = False
                else:
                    result.errors.append(f"Service file not found: {service_file}")
                    result.valid = False
                
            except FileNotFoundError:
                result.warnings.append("systemd-analyze not available, skipping service file validation")
            except Exception as e:
                result.warnings.append(f"Could not validate service file: {e}")
        
        except Exception as e:
            result.valid = False
            result.errors.append(f"Configuration validation failed: {e}")
        
        return result
    
    async def get_health_status(self) -> Dict[str, Any]:
        """Get comprehensive health status including service and application health."""
        health_info = {
            'service_health': {},
            'application_health': {},
            'timestamp': datetime.now().isoformat()
        }
        
        # Get service health
        status_info = await self.get_status()
        health_info['service_health'] = {
            'is_active': status_info['is_active'],
            'properties': status_info.get('properties', {}),
            'resource_usage': status_info.get('resource_usage', {})
        }
        
        # Try to get application health if service is running
        if status_info['is_active']:
            try:
                import httpx
                
                # Try to determine service port from configuration
                service_port = 8000  # Default port
                
                # Try to read port from environment file
                env_file = Path("/etc/thai-tokenizer/environment")
                if env_file.exists():
                    env_content = env_file.read_text()
                    for line in env_content.split('\n'):
                        if line.startswith('THAI_TOKENIZER_SERVICE_PORT='):
                            service_port = int(line.split('=')[1].strip('"'))
                            break
                
                # Check application health endpoint
                async with httpx.AsyncClient(timeout=5.0) as client:
                    try:
                        response = await client.get(f"http://localhost:{service_port}/health")
                        health_info['application_health'] = {
                            'status_code': response.status_code,
                            'response_time_ms': response.elapsed.total_seconds() * 1000,
                            'healthy': response.status_code == 200
                        }
                        
                        if response.status_code == 200:
                            try:
                                health_data = response.json()
                                health_info['application_health']['details'] = health_data
                            except:
                                health_info['application_health']['response_text'] = response.text
                    
                    except httpx.TimeoutException:
                        health_info['application_health'] = {
                            'healthy': False,
                            'error': 'Health check timeout'
                        }
                    except httpx.ConnectError:
                        health_info['application_health'] = {
                            'healthy': False,
                            'error': 'Cannot connect to application'
                        }
            
            except Exception as e:
                health_info['application_health'] = {
                    'healthy': False,
                    'error': f'Health check failed: {e}'
                }
        else:
            health_info['application_health'] = {
                'healthy': False,
                'error': 'Service is not running'
            }
        
        return health_info


def print_status_info(status_info: Dict[str, Any]):
    """Print formatted status information."""
    print(f"Service: {status_info['service_name']}")
    print(f"Active: {'✅ Yes' if status_info['is_active'] else '❌ No'}")
    
    if 'properties' in status_info:
        props = status_info['properties']
        print(f"State: {props.get('ActiveState', 'unknown')}")
        print(f"Sub-state: {props.get('SubState', 'unknown')}")
        print(f"Load state: {props.get('LoadState', 'unknown')}")
        print(f"Unit file state: {props.get('UnitFileState', 'unknown')}")
        
        if props.get('MainPID', '0') != '0':
            print(f"Main PID: {props['MainPID']}")
        
        if props.get('ExecMainStartTimestamp'):
            print(f"Started: {props['ExecMainStartTimestamp']}")
    
    if 'resource_usage' in status_info and status_info['resource_usage']:
        usage = status_info['resource_usage']
        if 'memory_mb' in usage:
            print(f"Memory usage: {usage['memory_mb']} MB")
        if 'cpu_percent' in usage:
            print(f"CPU usage: {usage['cpu_percent']}%")


def print_health_info(health_info: Dict[str, Any]):
    """Print formatted health information."""
    print("=== Service Health ===")
    service_health = health_info['service_health']
    print(f"Service active: {'✅ Yes' if service_health['is_active'] else '❌ No'}")
    
    if 'resource_usage' in service_health and service_health['resource_usage']:
        usage = service_health['resource_usage']
        if 'memory_mb' in usage:
            print(f"Memory usage: {usage['memory_mb']} MB")
        if 'cpu_percent' in usage:
            print(f"CPU usage: {usage['cpu_percent']}%")
    
    print("\n=== Application Health ===")
    app_health = health_info['application_health']
    
    if 'healthy' in app_health:
        print(f"Application healthy: {'✅ Yes' if app_health['healthy'] else '❌ No'}")
        
        if 'status_code' in app_health:
            print(f"HTTP status: {app_health['status_code']}")
        if 'response_time_ms' in app_health:
            print(f"Response time: {app_health['response_time_ms']:.2f} ms")
        if 'error' in app_health:
            print(f"Error: {app_health['error']}")
        if 'details' in app_health:
            print("Health details:")
            for key, value in app_health['details'].items():
                print(f"  {key}: {value}")


async def main():
    """Main service management function."""
    parser = argparse.ArgumentParser(
        description="Manage Thai Tokenizer systemd service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start       Start the service
  stop        Stop the service
  restart     Restart the service
  status      Show service status
  logs        Show service logs
  health      Show comprehensive health status
  reload      Reload service configuration
  validate    Validate service configuration

Examples:
  # Start the service
  sudo python3 manage-service.py start

  # Show service status
  python3 manage-service.py status

  # Show last 100 log lines
  python3 manage-service.py logs --lines 100

  # Follow logs in real-time
  python3 manage-service.py logs --follow

  # Show health status
  python3 manage-service.py health

  # Validate configuration
  python3 manage-service.py validate --config /etc/thai-tokenizer/config.json
        """
    )
    
    parser.add_argument(
        "command",
        choices=["start", "stop", "restart", "status", "logs", "health", "reload", "validate"],
        help="Service management command"
    )
    
    parser.add_argument(
        "--service-name",
        default="thai-tokenizer",
        help="Name of the systemd service (default: thai-tokenizer)"
    )
    
    parser.add_argument(
        "--lines",
        type=int,
        default=50,
        help="Number of log lines to show (default: 50)"
    )
    
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Follow logs in real-time"
    )
    
    parser.add_argument(
        "--config",
        help="Path to configuration file for validation"
    )
    
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format"
    )
    
    args = parser.parse_args()
    
    try:
        controller = ServiceController(args.service_name)
        
        if args.command == "start":
            if os.geteuid() != 0:
                print("Error: Starting service requires root privileges (use sudo)")
                sys.exit(1)
            
            result = await controller.start_service()
            
            if result.valid:
                print("✅ Service started successfully")
            else:
                print("❌ Failed to start service")
            
            for warning in result.warnings:
                print(f"ℹ️  {warning}")
            for error in result.errors:
                print(f"❌ {error}")
        
        elif args.command == "stop":
            if os.geteuid() != 0:
                print("Error: Stopping service requires root privileges (use sudo)")
                sys.exit(1)
            
            result = await controller.stop_service()
            
            if result.valid:
                print("✅ Service stopped successfully")
            else:
                print("❌ Failed to stop service")
            
            for warning in result.warnings:
                print(f"ℹ️  {warning}")
            for error in result.errors:
                print(f"❌ {error}")
        
        elif args.command == "restart":
            if os.geteuid() != 0:
                print("Error: Restarting service requires root privileges (use sudo)")
                sys.exit(1)
            
            result = await controller.restart_service()
            
            if result.valid:
                print("✅ Service restarted successfully")
            else:
                print("❌ Failed to restart service")
            
            for warning in result.warnings:
                print(f"ℹ️  {warning}")
            for error in result.errors:
                print(f"❌ {error}")
        
        elif args.command == "status":
            status_info = await controller.get_status()
            
            if args.json:
                print(json.dumps(status_info, indent=2))
            else:
                print_status_info(status_info)
        
        elif args.command == "logs":
            if args.follow:
                log_command = await controller.get_logs(follow=True)
                print(f"Run this command to follow logs: {log_command}")
                # Execute the command directly
                os.system(log_command)
            else:
                logs = await controller.get_logs(args.lines)
                print(logs)
        
        elif args.command == "health":
            health_info = await controller.get_health_status()
            
            if args.json:
                print(json.dumps(health_info, indent=2))
            else:
                print_health_info(health_info)
        
        elif args.command == "reload":
            if os.geteuid() != 0:
                print("Error: Reloading configuration requires root privileges (use sudo)")
                sys.exit(1)
            
            result = await controller.reload_configuration()
            
            if result.valid:
                print("✅ Configuration reloaded successfully")
            else:
                print("❌ Failed to reload configuration")
            
            for warning in result.warnings:
                print(f"ℹ️  {warning}")
            for error in result.errors:
                print(f"❌ {error}")
        
        elif args.command == "validate":
            result = await controller.validate_configuration(args.config)
            
            if result.valid:
                print("✅ Configuration is valid")
            else:
                print("❌ Configuration validation failed")
            
            for warning in result.warnings:
                print(f"ℹ️  {warning}")
            for error in result.errors:
                print(f"❌ {error}")
        
        # Exit with appropriate code
        if args.command in ["start", "stop", "restart", "reload", "validate"]:
            sys.exit(0 if result.valid else 1)
        else:
            sys.exit(0)
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Operation failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())