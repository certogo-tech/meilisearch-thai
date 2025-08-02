#!/usr/bin/env python3
"""
Process management script for standalone Thai Tokenizer deployment.

This script provides comprehensive process management capabilities for the
Thai Tokenizer service in standalone deployment mode, including start, stop,
restart, status, and monitoring functions.
"""

import os
import sys
import signal
import time
import psutil
import argparse
import logging
import json
from pathlib import Path
from typing import Optional, Dict, Any, List
import subprocess
import requests
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from utils.logging import get_structured_logger
except ImportError:
    # Fallback logging if imports fail
    logging.basicConfig(level=logging.INFO)
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class ProcessManager:
    """Manages Thai Tokenizer service processes for standalone deployment."""
    
    def __init__(self, install_path: str):
        """
        Initialize process manager.
        
        Args:
            install_path: Installation directory path
        """
        self.install_path = Path(install_path)
        self.pid_file = self.install_path / "run" / "thai-tokenizer.pid"
        self.log_file = self.install_path / "logs" / "thai-tokenizer.log"
        self.config_file = self.install_path / "config" / "config.json"
        self.env_file = self.install_path / "config" / ".env"
        self.venv_path = self.install_path / "venv"
        self.logger = get_structured_logger(f"{__name__}.ProcessManager")
        
        # Ensure directories exist
        (self.install_path / "run").mkdir(parents=True, exist_ok=True)
        (self.install_path / "logs").mkdir(parents=True, exist_ok=True)
    
    def get_venv_python(self) -> Path:
        """Get path to Python executable in virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "python.exe"
        else:  # Unix-like
            return self.venv_path / "bin" / "python"
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """
        Load service configuration.
        
        Returns:
            Configuration dictionary or None if loading failed
        """
        try:
            if not self.config_file.exists():
                self.logger.error(f"Configuration file not found: {self.config_file}")
                return None
            
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return None
    
    def load_environment_variables(self) -> Dict[str, str]:
        """
        Load environment variables from .env file.
        
        Returns:
            Dictionary of environment variables
        """
        env_vars = {}
        
        try:
            if self.env_file.exists():
                with open(self.env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            # Remove quotes if present
                            value = value.strip('"\'')
                            env_vars[key] = value
            
            return env_vars
            
        except Exception as e:
            self.logger.error(f"Failed to load environment variables: {e}")
            return {}
    
    def get_service_pid(self) -> Optional[int]:
        """
        Get service process ID from PID file.
        
        Returns:
            Process ID or None if not found
        """
        try:
            if not self.pid_file.exists():
                return None
            
            with open(self.pid_file, 'r') as f:
                pid_str = f.read().strip()
            
            if not pid_str.isdigit():
                self.logger.warning(f"Invalid PID in file: {pid_str}")
                return None
            
            return int(pid_str)
            
        except Exception as e:
            self.logger.error(f"Failed to read PID file: {e}")
            return None
    
    def is_process_running(self, pid: int) -> bool:
        """
        Check if process is running.
        
        Args:
            pid: Process ID to check
            
        Returns:
            True if process is running
        """
        try:
            return psutil.pid_exists(pid)
        except Exception:
            return False
    
    def get_process_info(self, pid: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed process information.
        
        Args:
            pid: Process ID
            
        Returns:
            Process information dictionary or None
        """
        try:
            if not self.is_process_running(pid):
                return None
            
            process = psutil.Process(pid)
            
            return {
                "pid": pid,
                "name": process.name(),
                "status": process.status(),
                "cpu_percent": process.cpu_percent(),
                "memory_info": process.memory_info()._asdict(),
                "create_time": process.create_time(),
                "cmdline": process.cmdline(),
                "connections": len(process.connections()),
            }
            
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            self.logger.warning(f"Cannot get process info for PID {pid}: {e}")
            return None
        except Exception as e:
            self.logger.error(f"Error getting process info for PID {pid}: {e}")
            return None
    
    def start_service(self) -> bool:
        """
        Start the Thai Tokenizer service.
        
        Returns:
            True if service was started successfully
        """
        try:
            # Check if already running
            pid = self.get_service_pid()
            if pid and self.is_process_running(pid):
                self.logger.info(f"Service is already running (PID: {pid})")
                return True
            
            # Remove stale PID file
            if self.pid_file.exists():
                self.pid_file.unlink()
            
            # Load configuration
            config = self.load_config()
            if not config:
                return False
            
            service_config = config.get("service_config", {})
            host = service_config.get("service_host", "0.0.0.0")
            port = service_config.get("service_port", 8000)
            workers = service_config.get("worker_processes", 4)
            
            # Prepare environment
            env = os.environ.copy()
            env.update(self.load_environment_variables())
            
            # Set Python path
            src_path = self.install_path.parent.parent / "src"
            env["PYTHONPATH"] = str(src_path)
            
            # Prepare command
            python_exe = self.get_venv_python()
            cmd = [
                str(python_exe), "-m", "uvicorn", "src.api.main:app",
                "--host", host,
                "--port", str(port),
                "--workers", str(workers),
                "--log-level", "info"
            ]
            
            self.logger.info(f"Starting service: {' '.join(cmd)}")
            
            # Start process
            with open(self.log_file, 'a') as log_f:
                process = subprocess.Popen(
                    cmd,
                    cwd=self.install_path,
                    env=env,
                    stdout=log_f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True
                )
            
            # Save PID
            with open(self.pid_file, 'w') as f:
                f.write(str(process.pid))
            
            # Wait a moment and check if process is still running
            time.sleep(2)
            if not self.is_process_running(process.pid):
                self.logger.error("Service failed to start")
                return False
            
            self.logger.info(f"Service started successfully (PID: {process.pid})")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to start service: {e}")
            return False
    
    def stop_service(self, force: bool = False) -> bool:
        """
        Stop the Thai Tokenizer service.
        
        Args:
            force: Whether to force stop the service
            
        Returns:
            True if service was stopped successfully
        """
        try:
            pid = self.get_service_pid()
            if not pid:
                self.logger.info("Service is not running (no PID file)")
                return True
            
            if not self.is_process_running(pid):
                self.logger.info("Service is not running (stale PID file)")
                self.pid_file.unlink()
                return True
            
            self.logger.info(f"Stopping service (PID: {pid})")
            
            try:
                process = psutil.Process(pid)
                
                if force:
                    # Force kill
                    process.kill()
                    self.logger.info("Service force stopped")
                else:
                    # Graceful shutdown
                    process.terminate()
                    
                    # Wait for process to stop
                    try:
                        process.wait(timeout=10)
                        self.logger.info("Service stopped gracefully")
                    except psutil.TimeoutExpired:
                        self.logger.warning("Service did not stop gracefully, force stopping")
                        process.kill()
                        process.wait(timeout=5)
                        self.logger.info("Service force stopped")
                
                # Remove PID file
                if self.pid_file.exists():
                    self.pid_file.unlink()
                
                return True
                
            except psutil.NoSuchProcess:
                self.logger.info("Process already stopped")
                if self.pid_file.exists():
                    self.pid_file.unlink()
                return True
                
        except Exception as e:
            self.logger.error(f"Failed to stop service: {e}")
            return False
    
    def restart_service(self) -> bool:
        """
        Restart the Thai Tokenizer service.
        
        Returns:
            True if service was restarted successfully
        """
        self.logger.info("Restarting service")
        
        # Stop service
        if not self.stop_service():
            return False
        
        # Wait a moment
        time.sleep(2)
        
        # Start service
        return self.start_service()
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status.
        
        Returns:
            Service status dictionary
        """
        status = {
            "running": False,
            "pid": None,
            "process_info": None,
            "health_check": None,
            "config": None,
            "log_file": str(self.log_file),
            "pid_file": str(self.pid_file),
        }
        
        try:
            # Check PID
            pid = self.get_service_pid()
            if pid:
                status["pid"] = pid
                
                # Check if process is running
                if self.is_process_running(pid):
                    status["running"] = True
                    status["process_info"] = self.get_process_info(pid)
                    
                    # Perform health check
                    status["health_check"] = self.perform_health_check()
            
            # Load configuration
            status["config"] = self.load_config()
            
        except Exception as e:
            self.logger.error(f"Error getting service status: {e}")
            status["error"] = str(e)
        
        return status
    
    def perform_health_check(self) -> Dict[str, Any]:
        """
        Perform health check on the service.
        
        Returns:
            Health check results
        """
        health_result = {
            "healthy": False,
            "response_time": None,
            "error": None,
            "endpoints": {}
        }
        
        try:
            config = self.load_config()
            if not config:
                health_result["error"] = "Cannot load configuration"
                return health_result
            
            service_config = config.get("service_config", {})
            host = service_config.get("service_host", "0.0.0.0")
            port = service_config.get("service_port", 8000)
            
            # Use localhost for health checks if host is 0.0.0.0
            check_host = "localhost" if host == "0.0.0.0" else host
            base_url = f"http://{check_host}:{port}"
            
            # Test endpoints
            endpoints_to_test = [
                ("/health", "Health endpoint"),
                ("/", "Root endpoint"),
                ("/docs", "API documentation"),
            ]
            
            start_time = time.time()
            
            for endpoint, description in endpoints_to_test:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=5)
                    health_result["endpoints"][endpoint] = {
                        "status_code": response.status_code,
                        "description": description,
                        "accessible": response.status_code < 500
                    }
                except requests.RequestException as e:
                    health_result["endpoints"][endpoint] = {
                        "status_code": None,
                        "description": description,
                        "accessible": False,
                        "error": str(e)
                    }
            
            response_time = (time.time() - start_time) * 1000
            health_result["response_time"] = response_time
            
            # Consider healthy if at least one endpoint is accessible
            health_result["healthy"] = any(
                ep.get("accessible", False) for ep in health_result["endpoints"].values()
            )
            
        except Exception as e:
            health_result["error"] = str(e)
        
        return health_result
    
    def get_log_tail(self, lines: int = 50) -> List[str]:
        """
        Get last N lines from service log.
        
        Args:
            lines: Number of lines to retrieve
            
        Returns:
            List of log lines
        """
        try:
            if not self.log_file.exists():
                return ["Log file not found"]
            
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
            
            return [line.rstrip() for line in all_lines[-lines:]]
            
        except Exception as e:
            return [f"Error reading log file: {e}"]
    
    def monitor_service(self, duration: int = 60, interval: int = 5, 
                       detailed: bool = False, alert_thresholds: Optional[Dict[str, float]] = None) -> None:
        """
        Monitor service for specified duration with enhanced monitoring capabilities.
        
        Args:
            duration: Monitoring duration in seconds
            interval: Check interval in seconds
            detailed: Whether to show detailed monitoring information
            alert_thresholds: Optional thresholds for alerts (cpu_percent, memory_mb, response_time_ms)
        """
        self.logger.info(f"Monitoring service for {duration} seconds (interval: {interval}s)")
        
        if alert_thresholds is None:
            alert_thresholds = {
                "cpu_percent": 80.0,
                "memory_mb": 512.0,
                "response_time_ms": 1000.0
            }
        
        start_time = time.time()
        monitoring_data = []
        
        while time.time() - start_time < duration:
            status = self.get_service_status()
            timestamp = datetime.now().isoformat()
            
            monitoring_entry = {
                "timestamp": timestamp,
                "running": status["running"],
                "alerts": []
            }
            
            if status["running"]:
                process_info = status.get("process_info", {})
                health_check = status.get("health_check", {})
                
                # Extract metrics
                cpu_percent = process_info.get('cpu_percent', 0)
                memory_mb = process_info.get('memory_info', {}).get('rss', 0) / 1024 / 1024
                response_time = health_check.get('response_time', 0)
                healthy = health_check.get('healthy', False)
                
                monitoring_entry.update({
                    "pid": status['pid'],
                    "cpu_percent": cpu_percent,
                    "memory_mb": memory_mb,
                    "response_time_ms": response_time,
                    "healthy": healthy,
                    "connections": process_info.get('connections', 0)
                })
                
                # Check thresholds and generate alerts
                if cpu_percent > alert_thresholds["cpu_percent"]:
                    alert = f"High CPU usage: {cpu_percent:.1f}%"
                    monitoring_entry["alerts"].append(alert)
                    self.logger.warning(alert)
                
                if memory_mb > alert_thresholds["memory_mb"]:
                    alert = f"High memory usage: {memory_mb:.1f}MB"
                    monitoring_entry["alerts"].append(alert)
                    self.logger.warning(alert)
                
                if response_time > alert_thresholds["response_time_ms"]:
                    alert = f"Slow response time: {response_time:.1f}ms"
                    monitoring_entry["alerts"].append(alert)
                    self.logger.warning(alert)
                
                if not healthy:
                    alert = "Service health check failed"
                    monitoring_entry["alerts"].append(alert)
                    self.logger.warning(alert)
                
                # Log monitoring information
                if detailed:
                    self.logger.info(
                        f"Service Status - PID: {status['pid']}, "
                        f"CPU: {cpu_percent:.1f}%, "
                        f"Memory: {memory_mb:.1f}MB, "
                        f"Response: {response_time:.1f}ms, "
                        f"Healthy: {healthy}, "
                        f"Connections: {process_info.get('connections', 0)}"
                    )
                else:
                    self.logger.info(
                        f"Service running - PID: {status['pid']}, "
                        f"CPU: {cpu_percent:.1f}%, "
                        f"Memory: {memory_mb:.1f}MB, "
                        f"Healthy: {healthy}"
                    )
            else:
                self.logger.warning("Service is not running")
                monitoring_entry["alerts"].append("Service not running")
            
            monitoring_data.append(monitoring_entry)
            time.sleep(interval)
        
        # Generate monitoring summary
        self.logger.info("Monitoring completed")
        self._generate_monitoring_summary(monitoring_data)
    
    def _generate_monitoring_summary(self, monitoring_data: List[Dict[str, Any]]) -> None:
        """
        Generate and log monitoring summary.
        
        Args:
            monitoring_data: List of monitoring entries
        """
        if not monitoring_data:
            return
        
        running_entries = [entry for entry in monitoring_data if entry["running"]]
        
        if not running_entries:
            self.logger.info("Service was not running during monitoring period")
            return
        
        # Calculate averages
        avg_cpu = sum(entry["cpu_percent"] for entry in running_entries) / len(running_entries)
        avg_memory = sum(entry["memory_mb"] for entry in running_entries) / len(running_entries)
        avg_response_time = sum(entry["response_time_ms"] for entry in running_entries) / len(running_entries)
        
        # Calculate maximums
        max_cpu = max(entry["cpu_percent"] for entry in running_entries)
        max_memory = max(entry["memory_mb"] for entry in running_entries)
        max_response_time = max(entry["response_time_ms"] for entry in running_entries)
        
        # Count alerts
        total_alerts = sum(len(entry["alerts"]) for entry in monitoring_data)
        unique_alerts = set()
        for entry in monitoring_data:
            unique_alerts.update(entry["alerts"])
        
        # Health check success rate
        healthy_checks = sum(1 for entry in running_entries if entry["healthy"])
        health_success_rate = (healthy_checks / len(running_entries)) * 100 if running_entries else 0
        
        self.logger.info("=== Monitoring Summary ===")
        self.logger.info(f"Monitoring Duration: {len(monitoring_data)} checks")
        self.logger.info(f"Service Uptime: {len(running_entries)}/{len(monitoring_data)} checks ({len(running_entries)/len(monitoring_data)*100:.1f}%)")
        self.logger.info(f"Health Success Rate: {health_success_rate:.1f}%")
        self.logger.info(f"Average CPU: {avg_cpu:.1f}% (Max: {max_cpu:.1f}%)")
        self.logger.info(f"Average Memory: {avg_memory:.1f}MB (Max: {max_memory:.1f}MB)")
        self.logger.info(f"Average Response Time: {avg_response_time:.1f}ms (Max: {max_response_time:.1f}ms)")
        self.logger.info(f"Total Alerts: {total_alerts}")
        
        if unique_alerts:
            self.logger.info("Alert Types:")
            for alert in sorted(unique_alerts):
                self.logger.info(f"  - {alert}")
        
        # Save monitoring data to file
        try:
            monitoring_file = self.install_path / "logs" / f"monitoring_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(monitoring_file, 'w') as f:
                json.dump({
                    "summary": {
                        "monitoring_duration_checks": len(monitoring_data),
                        "service_uptime_percent": len(running_entries)/len(monitoring_data)*100,
                        "health_success_rate_percent": health_success_rate,
                        "average_cpu_percent": avg_cpu,
                        "max_cpu_percent": max_cpu,
                        "average_memory_mb": avg_memory,
                        "max_memory_mb": max_memory,
                        "average_response_time_ms": avg_response_time,
                        "max_response_time_ms": max_response_time,
                        "total_alerts": total_alerts,
                        "unique_alerts": list(unique_alerts)
                    },
                    "data": monitoring_data
                }, f, indent=2, default=str)
            
            self.logger.info(f"Monitoring data saved to: {monitoring_file}")
            
        except Exception as e:
            self.logger.warning(f"Failed to save monitoring data: {e}")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """
        Get current performance metrics.
        
        Returns:
            Performance metrics dictionary
        """
        metrics = {
            "timestamp": datetime.now().isoformat(),
            "service_metrics": {},
            "system_metrics": {},
            "health_metrics": {}
        }
        
        try:
            status = self.get_service_status()
            
            if status["running"]:
                process_info = status.get("process_info", {})
                health_check = status.get("health_check", {})
                
                # Service-specific metrics
                metrics["service_metrics"] = {
                    "pid": status["pid"],
                    "cpu_percent": process_info.get("cpu_percent", 0),
                    "memory_rss_mb": process_info.get("memory_info", {}).get("rss", 0) / 1024 / 1024,
                    "memory_vms_mb": process_info.get("memory_info", {}).get("vms", 0) / 1024 / 1024,
                    "connections": process_info.get("connections", 0),
                    "create_time": process_info.get("create_time", 0),
                    "status": process_info.get("status", "unknown")
                }
                
                # Health metrics
                metrics["health_metrics"] = {
                    "healthy": health_check.get("healthy", False),
                    "response_time_ms": health_check.get("response_time", 0),
                    "endpoints": health_check.get("endpoints", {})
                }
            
            # System metrics
            metrics["system_metrics"] = {
                "cpu_count": psutil.cpu_count(),
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_total_mb": psutil.virtual_memory().total / 1024 / 1024,
                "memory_available_mb": psutil.virtual_memory().available / 1024 / 1024,
                "memory_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage('/').percent if os.path.exists('/') else 0
            }
            
        except Exception as e:
            metrics["error"] = str(e)
        
        return metrics


def main():
    """Main entry point for process management."""
    parser = argparse.ArgumentParser(
        description="Manage Thai Tokenizer service processes"
    )
    
    parser.add_argument(
        "--install-path",
        required=True,
        help="Installation directory path"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Start command
    start_parser = subparsers.add_parser("start", help="Start the service")
    
    # Stop command
    stop_parser = subparsers.add_parser("stop", help="Stop the service")
    stop_parser.add_argument("--force", action="store_true", help="Force stop the service")
    
    # Restart command
    restart_parser = subparsers.add_parser("restart", help="Restart the service")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Get service status")
    status_parser.add_argument("--json", action="store_true", help="Output status as JSON")
    
    # Logs command
    logs_parser = subparsers.add_parser("logs", help="Show service logs")
    logs_parser.add_argument("--lines", type=int, default=50, help="Number of lines to show")
    
    # Monitor command
    monitor_parser = subparsers.add_parser("monitor", help="Monitor service")
    monitor_parser.add_argument("--duration", type=int, default=60, help="Monitoring duration in seconds")
    monitor_parser.add_argument("--interval", type=int, default=5, help="Check interval in seconds")
    monitor_parser.add_argument("--detailed", action="store_true", help="Show detailed monitoring information")
    monitor_parser.add_argument("--cpu-threshold", type=float, default=80.0, help="CPU usage alert threshold (%)")
    monitor_parser.add_argument("--memory-threshold", type=float, default=512.0, help="Memory usage alert threshold (MB)")
    monitor_parser.add_argument("--response-threshold", type=float, default=1000.0, help="Response time alert threshold (ms)")
    
    # Metrics command
    metrics_parser = subparsers.add_parser("metrics", help="Get performance metrics")
    metrics_parser.add_argument("--json", action="store_true", help="Output metrics as JSON")
    
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create process manager
        process_manager = ProcessManager(args.install_path)
        
        # Execute command
        if args.command == "start":
            success = process_manager.start_service()
            sys.exit(0 if success else 1)
            
        elif args.command == "stop":
            success = process_manager.stop_service(force=args.force)
            sys.exit(0 if success else 1)
            
        elif args.command == "restart":
            success = process_manager.restart_service()
            sys.exit(0 if success else 1)
            
        elif args.command == "status":
            status = process_manager.get_service_status()
            
            if args.json:
                print(json.dumps(status, indent=2, default=str))
            else:
                print(f"Service Status:")
                print(f"  Running: {status['running']}")
                print(f"  PID: {status.get('pid', 'N/A')}")
                
                if status.get('process_info'):
                    proc_info = status['process_info']
                    print(f"  CPU: {proc_info.get('cpu_percent', 'N/A')}%")
                    print(f"  Memory: {proc_info.get('memory_info', {}).get('rss', 0) / 1024 / 1024:.1f}MB")
                
                if status.get('health_check'):
                    health = status['health_check']
                    print(f"  Healthy: {health.get('healthy', False)}")
                    if health.get('response_time'):
                        print(f"  Response Time: {health['response_time']:.2f}ms")
            
            sys.exit(0 if status['running'] else 1)
            
        elif args.command == "logs":
            log_lines = process_manager.get_log_tail(args.lines)
            for line in log_lines:
                print(line)
            
        elif args.command == "monitor":
            alert_thresholds = {
                "cpu_percent": args.cpu_threshold,
                "memory_mb": args.memory_threshold,
                "response_time_ms": args.response_threshold
            }
            process_manager.monitor_service(
                duration=args.duration, 
                interval=args.interval,
                detailed=args.detailed,
                alert_thresholds=alert_thresholds
            )
        
        elif args.command == "metrics":
            metrics = process_manager.get_performance_metrics()
            
            if args.json:
                print(json.dumps(metrics, indent=2, default=str))
            else:
                print("=== Performance Metrics ===")
                print(f"Timestamp: {metrics['timestamp']}")
                
                if metrics.get("service_metrics"):
                    sm = metrics["service_metrics"]
                    print(f"\nService Metrics:")
                    print(f"  PID: {sm.get('pid', 'N/A')}")
                    print(f"  CPU: {sm.get('cpu_percent', 0):.1f}%")
                    print(f"  Memory RSS: {sm.get('memory_rss_mb', 0):.1f}MB")
                    print(f"  Connections: {sm.get('connections', 0)}")
                
                if metrics.get("health_metrics"):
                    hm = metrics["health_metrics"]
                    print(f"\nHealth Metrics:")
                    print(f"  Healthy: {hm.get('healthy', False)}")
                    print(f"  Response Time: {hm.get('response_time_ms', 0):.1f}ms")
                
                if metrics.get("system_metrics"):
                    sys_m = metrics["system_metrics"]
                    print(f"\nSystem Metrics:")
                    print(f"  CPU: {sys_m.get('cpu_percent', 0):.1f}%")
                    print(f"  Memory: {sys_m.get('memory_percent', 0):.1f}%")
                    print(f"  Disk: {sys_m.get('disk_usage_percent', 0):.1f}%")
            
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()