"""
Deployment-specific backup handlers for different deployment methods.

This module provides specialized backup and recovery logic for Docker, systemd,
and standalone deployments while maintaining a unified interface.
"""

import asyncio
import json
import logging
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

try:
    from src.utils.logging import get_structured_logger
    from src.deployment.config import DeploymentMethod
except ImportError:
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)
    
    class DeploymentMethod:
        DOCKER = "docker"
        SYSTEMD = "systemd"
        STANDALONE = "standalone"

logger = get_structured_logger(__name__)


@dataclass
class BackupComponent:
    """Represents a component that can be backed up."""
    name: str
    source_path: Path
    description: str
    required: bool = True
    size_bytes: int = 0
    checksum: str = ""


class DeploymentBackupHandler(ABC):
    """Abstract base class for deployment-specific backup handlers."""
    
    def __init__(self, config):
        """Initialize handler with backup configuration."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.{self.__class__.__name__}")
    
    @abstractmethod
    async def get_deployment_specific_components(self, backup_type) -> List[BackupComponent]:
        """Get deployment-specific components to backup."""
        pass
    
    @abstractmethod
    async def get_deployment_metadata(self) -> Dict[str, Any]:
        """Get deployment-specific metadata for backup."""
        pass
    
    @abstractmethod
    async def stop_service_for_restore(self):
        """Stop service before restore operation."""
        pass
    
    @abstractmethod
    async def post_restore_actions(self, restored_components: List[str]):
        """Perform post-restore actions."""
        pass
    
    @abstractmethod
    async def restore_deployment_component(self, component_name: str, component_dir: Path) -> bool:
        """Restore deployment-specific component."""
        pass


class DockerBackupHandler(DeploymentBackupHandler):
    """Backup handler for Docker deployments."""
    
    def __init__(self, config):
        super().__init__(config)
        self.compose_file = self._find_compose_file()
        self.env_file = self._find_env_file()
    
    def _find_compose_file(self) -> Optional[Path]:
        """Find Docker Compose file."""
        possible_paths = [
            self.config.installation_path / "docker-compose.yml",
            self.config.installation_path / "docker-compose.external-meilisearch.yml",
            Path("deployment/docker/docker-compose.external-meilisearch.yml")
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    def _find_env_file(self) -> Optional[Path]:
        """Find environment file."""
        possible_paths = [
            self.config.installation_path / ".env",
            self.config.installation_path / ".env.external-meilisearch",
            Path("deployment/docker/.env.external-meilisearch")
        ]
        
        for path in possible_paths:
            if path.exists():
                return path
        
        return None
    
    async def get_deployment_specific_components(self, backup_type) -> List[BackupComponent]:
        """Get Docker-specific components to backup."""
        components = []
        
        # Docker Compose configuration
        if self.compose_file:
            components.append(BackupComponent(
                name="docker_compose",
                source_path=self.compose_file,
                description="Docker Compose configuration",
                required=True
            ))
        
        # Environment file
        if self.env_file:
            components.append(BackupComponent(
                name="docker_env",
                source_path=self.env_file,
                description="Docker environment configuration",
                required=True
            ))
        
        # Docker volumes (metadata only)
        volumes_info = await self._get_volumes_info()
        if volumes_info:
            # Create temporary file with volumes info
            volumes_file = self.config.backup_directory / "temp_volumes_info.json"
            with open(volumes_file, 'w') as f:
                json.dump(volumes_info, f, indent=2)
            
            components.append(BackupComponent(
                name="docker_volumes_info",
                source_path=volumes_file,
                description="Docker volumes information",
                required=False
            ))
        
        # Nginx configuration if exists
        nginx_conf = self.config.installation_path / "nginx.conf"
        if not nginx_conf.exists():
            nginx_conf = Path("deployment/docker/nginx.external-meilisearch.conf")
        
        if nginx_conf.exists():
            components.append(BackupComponent(
                name="nginx_config",
                source_path=nginx_conf,
                description="Nginx configuration",
                required=False
            ))
        
        return components
    
    async def _get_volumes_info(self) -> Optional[Dict[str, Any]]:
        """Get information about Docker volumes."""
        if not self.compose_file:
            return None
        
        try:
            # Get volumes from compose file
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                'config', '--volumes'
            ]
            
            if self.env_file:
                cmd.extend(['--env-file', str(self.env_file)])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.compose_file.parent
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                volumes = stdout.decode().strip().split('\n')
                volumes_info = {
                    'volumes': [v.strip() for v in volumes if v.strip()],
                    'timestamp': str(asyncio.get_event_loop().time())
                }
                return volumes_info
            else:
                self.logger.warning(f"Cannot get volumes info: {stderr.decode()}")
                return None
        
        except Exception as e:
            self.logger.warning(f"Error getting volumes info: {e}")
            return None
    
    async def get_deployment_metadata(self) -> Dict[str, Any]:
        """Get Docker-specific metadata."""
        metadata = {
            'deployment_type': 'docker',
            'compose_file': str(self.compose_file) if self.compose_file else None,
            'env_file': str(self.env_file) if self.env_file else None,
            'docker_version': await self._get_docker_version(),
            'compose_version': await self._get_compose_version()
        }
        
        # Get container information
        containers_info = await self._get_containers_info()
        if containers_info:
            metadata['containers'] = containers_info
        
        return metadata
    
    async def _get_docker_version(self) -> str:
        """Get Docker version."""
        try:
            process = await asyncio.create_subprocess_exec(
                'docker', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                return "unknown"
        
        except Exception:
            return "unknown"
    
    async def _get_compose_version(self) -> str:
        """Get Docker Compose version."""
        try:
            process = await asyncio.create_subprocess_exec(
                'docker', 'compose', 'version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                return "unknown"
        
        except Exception:
            return "unknown"
    
    async def _get_containers_info(self) -> Optional[List[Dict[str, Any]]]:
        """Get information about running containers."""
        if not self.compose_file:
            return None
        
        try:
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                'ps', '--format', 'json'
            ]
            
            if self.env_file:
                cmd.extend(['--env-file', str(self.env_file)])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.compose_file.parent
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode == 0:
                containers = []
                for line in stdout.decode().strip().split('\n'):
                    if line:
                        try:
                            container_info = json.loads(line)
                            containers.append(container_info)
                        except json.JSONDecodeError:
                            pass
                return containers
            else:
                self.logger.warning(f"Cannot get containers info: {stderr.decode()}")
                return None
        
        except Exception as e:
            self.logger.warning(f"Error getting containers info: {e}")
            return None
    
    async def stop_service_for_restore(self):
        """Stop Docker services before restore."""
        if not self.compose_file:
            self.logger.warning("No compose file found, cannot stop services")
            return
        
        try:
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                'down'
            ]
            
            if self.env_file:
                cmd.extend(['--env-file', str(self.env_file)])
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.compose_file.parent
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                self.logger.info("Docker services stopped for restore")
            else:
                self.logger.warning("Failed to stop Docker services")
        
        except Exception as e:
            self.logger.warning(f"Error stopping Docker services: {e}")
    
    async def post_restore_actions(self, restored_components: List[str]):
        """Perform post-restore actions for Docker."""
        self.logger.info("Docker post-restore actions completed")
        
        # Note: We don't automatically restart services after restore
        # This should be done manually by the administrator
        if "docker_compose" in restored_components or "docker_env" in restored_components:
            self.logger.info("Docker configuration restored. You may need to restart services manually.")
    
    async def restore_deployment_component(self, component_name: str, component_dir: Path) -> bool:
        """Restore Docker-specific component."""
        try:
            if component_name == "docker_compose":
                # Restore compose file
                compose_files = list(component_dir.glob("*.yml")) + list(component_dir.glob("*.yaml"))
                if compose_files and self.compose_file:
                    shutil.copy2(compose_files[0], self.compose_file)
                    return True
            
            elif component_name == "docker_env":
                # Restore environment file
                env_files = list(component_dir.glob(".env*"))
                if env_files and self.env_file:
                    shutil.copy2(env_files[0], self.env_file)
                    return True
            
            elif component_name == "docker_volumes_info":
                # This is informational only, no actual restore needed
                self.logger.info("Docker volumes info restored (informational only)")
                return True
            
            elif component_name == "nginx_config":
                # Restore nginx config
                nginx_files = list(component_dir.glob("nginx*.conf"))
                if nginx_files:
                    nginx_conf = self.config.installation_path / "nginx.conf"
                    nginx_conf.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(nginx_files[0], nginx_conf)
                    return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Docker component restore failed ({component_name}): {e}")
            return False


class SystemdBackupHandler(DeploymentBackupHandler):
    """Backup handler for systemd deployments."""
    
    async def get_deployment_specific_components(self, backup_type) -> List[BackupComponent]:
        """Get systemd-specific components to backup."""
        components = []
        
        # Systemd service file
        service_file = Path(f"/etc/systemd/system/thai-tokenizer.service")
        if service_file.exists():
            components.append(BackupComponent(
                name="systemd_service",
                source_path=service_file,
                description="Systemd service file",
                required=True
            ))
        
        # Systemd environment file
        env_file = Path("/etc/default/thai-tokenizer")
        if env_file.exists():
            components.append(BackupComponent(
                name="systemd_env",
                source_path=env_file,
                description="Systemd environment file",
                required=False
            ))
        
        # Log rotation config
        logrotate_file = Path("/etc/logrotate.d/thai-tokenizer")
        if logrotate_file.exists():
            components.append(BackupComponent(
                name="logrotate_config",
                source_path=logrotate_file,
                description="Log rotation configuration",
                required=False
            ))
        
        return components
    
    async def get_deployment_metadata(self) -> Dict[str, Any]:
        """Get systemd-specific metadata."""
        metadata = {
            'deployment_type': 'systemd',
            'systemd_version': await self._get_systemd_version(),
            'service_status': await self._get_service_status()
        }
        
        return metadata
    
    async def _get_systemd_version(self) -> str:
        """Get systemd version."""
        try:
            process = await asyncio.create_subprocess_exec(
                'systemctl', '--version',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                lines = stdout.decode().strip().split('\n')
                if lines:
                    return lines[0]
            
            return "unknown"
        
        except Exception:
            return "unknown"
    
    async def _get_service_status(self) -> Dict[str, Any]:
        """Get service status information."""
        try:
            process = await asyncio.create_subprocess_exec(
                'systemctl', 'status', 'thai-tokenizer.service',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            status_info = {
                'return_code': process.returncode,
                'stdout': stdout.decode(),
                'stderr': stderr.decode()
            }
            
            return status_info
        
        except Exception as e:
            return {'error': str(e)}
    
    async def stop_service_for_restore(self):
        """Stop systemd service before restore."""
        try:
            process = await asyncio.create_subprocess_exec(
                'sudo', 'systemctl', 'stop', 'thai-tokenizer.service',
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            await process.communicate()
            
            if process.returncode == 0:
                self.logger.info("Systemd service stopped for restore")
            else:
                self.logger.warning("Failed to stop systemd service")
        
        except Exception as e:
            self.logger.warning(f"Error stopping systemd service: {e}")
    
    async def post_restore_actions(self, restored_components: List[str]):
        """Perform post-restore actions for systemd."""
        try:
            if "systemd_service" in restored_components:
                # Reload systemd daemon
                process = await asyncio.create_subprocess_exec(
                    'sudo', 'systemctl', 'daemon-reload',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                
                await process.communicate()
                
                if process.returncode == 0:
                    self.logger.info("Systemd daemon reloaded")
                else:
                    self.logger.warning("Failed to reload systemd daemon")
            
            self.logger.info("Systemd post-restore actions completed")
        
        except Exception as e:
            self.logger.warning(f"Systemd post-restore actions failed: {e}")
    
    async def restore_deployment_component(self, component_name: str, component_dir: Path) -> bool:
        """Restore systemd-specific component."""
        try:
            if component_name == "systemd_service":
                # Restore service file
                service_files = list(component_dir.glob("*.service"))
                if service_files:
                    target_file = Path("/etc/systemd/system/thai-tokenizer.service")
                    # This requires sudo privileges
                    cmd = ['sudo', 'cp', str(service_files[0]), str(target_file)]
                    process = await asyncio.create_subprocess_exec(*cmd)
                    await process.communicate()
                    return process.returncode == 0
            
            elif component_name == "systemd_env":
                # Restore environment file
                env_files = list(component_dir.glob("thai-tokenizer"))
                if env_files:
                    target_file = Path("/etc/default/thai-tokenizer")
                    cmd = ['sudo', 'cp', str(env_files[0]), str(target_file)]
                    process = await asyncio.create_subprocess_exec(*cmd)
                    await process.communicate()
                    return process.returncode == 0
            
            elif component_name == "logrotate_config":
                # Restore logrotate config
                logrotate_files = list(component_dir.glob("thai-tokenizer"))
                if logrotate_files:
                    target_file = Path("/etc/logrotate.d/thai-tokenizer")
                    cmd = ['sudo', 'cp', str(logrotate_files[0]), str(target_file)]
                    process = await asyncio.create_subprocess_exec(*cmd)
                    await process.communicate()
                    return process.returncode == 0
            
            return False
        
        except Exception as e:
            self.logger.error(f"Systemd component restore failed ({component_name}): {e}")
            return False


class StandaloneBackupHandler(DeploymentBackupHandler):
    """Backup handler for standalone deployments."""
    
    async def get_deployment_specific_components(self, backup_type) -> List[BackupComponent]:
        """Get standalone-specific components to backup."""
        components = []
        
        # Virtual environment info
        venv_info_file = self.config.installation_path / "venv-info.json"
        if venv_info_file.exists():
            components.append(BackupComponent(
                name="venv_info",
                source_path=venv_info_file,
                description="Virtual environment information",
                required=False
            ))
        
        # Installation report
        install_report_file = self.config.installation_path / "installation-report.json"
        if install_report_file.exists():
            components.append(BackupComponent(
                name="install_report",
                source_path=install_report_file,
                description="Installation report",
                required=False
            ))
        
        # Process management scripts
        scripts_dir = self.config.installation_path / "scripts"
        if scripts_dir.exists():
            components.append(BackupComponent(
                name="management_scripts",
                source_path=scripts_dir,
                description="Process management scripts",
                required=False
            ))
        
        # Requirements file
        requirements_file = self.config.installation_path / "requirements.txt"
        if requirements_file.exists():
            components.append(BackupComponent(
                name="requirements",
                source_path=requirements_file,
                description="Python requirements",
                required=False
            ))
        
        return components
    
    async def get_deployment_metadata(self) -> Dict[str, Any]:
        """Get standalone-specific metadata."""
        metadata = {
            'deployment_type': 'standalone',
            'python_version': await self._get_python_version(),
            'pip_version': await self._get_pip_version(),
            'process_status': await self._get_process_status()
        }
        
        return metadata
    
    async def _get_python_version(self) -> str:
        """Get Python version."""
        try:
            venv_python = self.config.installation_path / "venv" / "bin" / "python"
            if venv_python.exists():
                process = await asyncio.create_subprocess_exec(
                    str(venv_python), '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    'python3', '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                return "unknown"
        
        except Exception:
            return "unknown"
    
    async def _get_pip_version(self) -> str:
        """Get pip version."""
        try:
            venv_pip = self.config.installation_path / "venv" / "bin" / "pip"
            if venv_pip.exists():
                process = await asyncio.create_subprocess_exec(
                    str(venv_pip), '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            else:
                process = await asyncio.create_subprocess_exec(
                    'pip3', '--version',
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
            
            stdout, _ = await process.communicate()
            
            if process.returncode == 0:
                return stdout.decode().strip()
            else:
                return "unknown"
        
        except Exception:
            return "unknown"
    
    async def _get_process_status(self) -> Dict[str, Any]:
        """Get process status information."""
        try:
            # Try to import the process manager
            import sys
            sys.path.append(str(self.config.installation_path.parent.parent / "deployment" / "standalone"))
            
            from manage_service import ProcessManager
            process_manager = ProcessManager(str(self.config.installation_path))
            status = process_manager.get_service_status()
            return status
        
        except Exception as e:
            return {'error': str(e)}
    
    async def stop_service_for_restore(self):
        """Stop standalone service before restore."""
        try:
            import sys
            sys.path.append(str(self.config.installation_path.parent.parent / "deployment" / "standalone"))
            
            from manage_service import ProcessManager
            process_manager = ProcessManager(str(self.config.installation_path))
            
            if process_manager.get_service_status().get("running", False):
                success = process_manager.stop_service()
                if success:
                    self.logger.info("Standalone service stopped for restore")
                else:
                    self.logger.warning("Failed to stop standalone service")
        
        except Exception as e:
            self.logger.warning(f"Error stopping standalone service: {e}")
    
    async def post_restore_actions(self, restored_components: List[str]):
        """Perform post-restore actions for standalone."""
        self.logger.info("Standalone post-restore actions completed")
        
        if "management_scripts" in restored_components:
            # Make scripts executable
            scripts_dir = self.config.installation_path / "scripts"
            if scripts_dir.exists():
                for script_file in scripts_dir.glob("*.sh"):
                    script_file.chmod(0o755)
                
                for script_file in scripts_dir.glob("*.py"):
                    script_file.chmod(0o755)
    
    async def restore_deployment_component(self, component_name: str, component_dir: Path) -> bool:
        """Restore standalone-specific component."""
        try:
            if component_name == "venv_info":
                # Restore venv info
                venv_files = list(component_dir.glob("venv-info.json"))
                if venv_files:
                    target_file = self.config.installation_path / "venv-info.json"
                    shutil.copy2(venv_files[0], target_file)
                    return True
            
            elif component_name == "install_report":
                # Restore installation report
                report_files = list(component_dir.glob("installation-report.json"))
                if report_files:
                    target_file = self.config.installation_path / "installation-report.json"
                    shutil.copy2(report_files[0], target_file)
                    return True
            
            elif component_name == "management_scripts":
                # Restore management scripts
                target_dir = self.config.installation_path / "scripts"
                target_dir.mkdir(parents=True, exist_ok=True)
                
                for script_file in component_dir.rglob("*"):
                    if script_file.is_file():
                        relative_path = script_file.relative_to(component_dir)
                        target_file = target_dir / relative_path
                        target_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(script_file, target_file)
                        
                        # Make executable if it's a script
                        if script_file.suffix in ['.sh', '.py']:
                            target_file.chmod(0o755)
                
                return True
            
            elif component_name == "requirements":
                # Restore requirements file
                req_files = list(component_dir.glob("requirements.txt"))
                if req_files:
                    target_file = self.config.installation_path / "requirements.txt"
                    shutil.copy2(req_files[0], target_file)
                    return True
            
            return False
        
        except Exception as e:
            self.logger.error(f"Standalone component restore failed ({component_name}): {e}")
            return False