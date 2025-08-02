#!/usr/bin/env python3
"""
Docker Backup and Recovery Manager for Thai Tokenizer Service
Provides comprehensive backup and recovery procedures for Docker deployments
"""

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tarfile
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import yaml

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class BackupResult:
    """Result of backup operation"""
    success: bool
    backup_id: str
    backup_path: Path
    size_bytes: int = 0
    duration_seconds: float = 0.0
    components: List[str] = field(default_factory=list)
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class RecoveryResult:
    """Result of recovery operation"""
    success: bool
    backup_id: str
    restored_components: List[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    message: str = ""
    timestamp: datetime = field(default_factory=datetime.now)


class DockerBackupRecoveryManager:
    """
    Comprehensive backup and recovery manager for Docker deployments
    Requirements: 6.1, 6.2, 6.3
    """
    
    def __init__(self, config_dir: Path = None):
        self.config_dir = config_dir or Path(__file__).parent
        self.project_root = self.config_dir.parent.parent
        self.compose_file = self.config_dir / "docker-compose.external-meilisearch.yml"
        self.env_file = self.config_dir / ".env.external-meilisearch"
        
        # Backup configuration
        self.backup_dir = self.project_root / "backups" / "docker"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Load configuration
        self.config = self._load_configuration()
        
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
    
    async def create_backup(self, 
                           include_volumes: bool = True,
                           include_images: bool = False,
                           include_logs: bool = True) -> BackupResult:
        """
        Create comprehensive backup of Docker deployment
        Requirements: 6.1, 6.2
        """
        start_time = time.time()
        backup_id = f"docker_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        backup_path = self.backup_dir / f"{backup_id}.tar.gz"
        
        logger.info(f"Creating backup {backup_id}...")
        
        try:
            # Create temporary backup directory
            temp_backup_dir = self.backup_dir / f"temp_{backup_id}"
            temp_backup_dir.mkdir(exist_ok=True)
            
            components = []
            
            # Backup configuration files
            config_backup = await self._backup_configuration(temp_backup_dir)
            if config_backup:
                components.append("configuration")
            
            # Backup Docker volumes
            if include_volumes:
                volume_backup = await self._backup_volumes(temp_backup_dir)
                if volume_backup:
                    components.append("volumes")
            
            # Backup Docker images
            if include_images:
                image_backup = await self._backup_images(temp_backup_dir)
                if image_backup:
                    components.append("images")
            
            # Backup logs
            if include_logs:
                log_backup = await self._backup_logs(temp_backup_dir)
                if log_backup:
                    components.append("logs")
            
            # Backup service state
            state_backup = await self._backup_service_state(temp_backup_dir)
            if state_backup:
                components.append("service_state")
            
            # Create compressed archive
            await self._create_archive(temp_backup_dir, backup_path)
            
            # Calculate backup size
            backup_size = backup_path.stat().st_size
            
            # Cleanup temporary directory
            shutil.rmtree(temp_backup_dir)
            
            duration = time.time() - start_time
            
            # Create backup metadata
            await self._create_backup_metadata(backup_id, backup_path, components, backup_size, duration)
            
            logger.info(f"Backup {backup_id} created successfully ({backup_size / 1024 / 1024:.2f} MB)")
            
            return BackupResult(
                success=True,
                backup_id=backup_id,
                backup_path=backup_path,
                size_bytes=backup_size,
                duration_seconds=duration,
                components=components,
                message="Backup created successfully"
            )
            
        except Exception as e:
            logger.error(f"Backup failed: {str(e)}")
            
            # Cleanup on failure
            if temp_backup_dir.exists():
                shutil.rmtree(temp_backup_dir)
            if backup_path.exists():
                backup_path.unlink()
            
            return BackupResult(
                success=False,
                backup_id=backup_id,
                backup_path=backup_path,
                message=f"Backup failed: {str(e)}"
            )
    
    async def _backup_configuration(self, backup_dir: Path) -> bool:
        """Backup configuration files"""
        try:
            config_dir = backup_dir / "configuration"
            config_dir.mkdir(exist_ok=True)
            
            # Backup environment file
            if self.env_file.exists():
                shutil.copy2(self.env_file, config_dir / ".env.external-meilisearch")
            
            # Backup Docker Compose file
            if self.compose_file.exists():
                shutil.copy2(self.compose_file, config_dir / "docker-compose.external-meilisearch.yml")
            
            # Backup Nginx configuration if exists
            nginx_conf = self.config_dir / "nginx.external-meilisearch.conf"
            if nginx_conf.exists():
                shutil.copy2(nginx_conf, config_dir / "nginx.external-meilisearch.conf")
            
            # Backup SSL certificates if they exist
            ssl_dir = self.project_root / "ssl"
            if ssl_dir.exists() and any(ssl_dir.iterdir()):
                ssl_backup_dir = config_dir / "ssl"
                shutil.copytree(ssl_dir, ssl_backup_dir, dirs_exist_ok=True)
            
            logger.info("Configuration backup completed")
            return True
            
        except Exception as e:
            logger.error(f"Configuration backup failed: {str(e)}")
            return False
    
    async def _backup_volumes(self, backup_dir: Path) -> bool:
        """Backup Docker volumes"""
        try:
            volumes_dir = backup_dir / "volumes"
            volumes_dir.mkdir(exist_ok=True)
            
            # Get list of volumes used by the service
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
                logger.warning("Could not list volumes")
                return False
            
            volumes = process.stdout.strip().split('\n')
            
            for volume in volumes:
                if volume.strip():
                    await self._backup_single_volume(volume.strip(), volumes_dir)
            
            logger.info("Volume backup completed")
            return True
            
        except Exception as e:
            logger.error(f"Volume backup failed: {str(e)}")
            return False
    
    async def _backup_single_volume(self, volume_name: str, backup_dir: Path):
        """Backup a single Docker volume"""
        try:
            volume_backup_path = backup_dir / f"{volume_name}.tar"
            
            # Create a temporary container to access the volume
            cmd = [
                'docker', 'run', '--rm',
                '-v', f"{volume_name}:/volume",
                '-v', f"{backup_dir}:/backup",
                'alpine:latest',
                'tar', 'cf', f"/backup/{volume_name}.tar", '-C', '/volume', '.'
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if process.returncode == 0:
                logger.info(f"Volume {volume_name} backed up successfully")
            else:
                logger.warning(f"Volume {volume_name} backup failed: {process.stderr}")
                
        except Exception as e:
            logger.error(f"Volume {volume_name} backup error: {str(e)}")
    
    async def _backup_images(self, backup_dir: Path) -> bool:
        """Backup Docker images"""
        try:
            images_dir = backup_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # Get list of images used by the service
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'images', '--format', 'json'
            ]
            
            process = subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if process.returncode != 0:
                logger.warning("Could not list images")
                return False
            
            # Parse image information
            for line in process.stdout.strip().split('\n'):
                if line:
                    image_info = json.loads(line)
                    image_name = image_info.get('Repository', '')
                    image_tag = image_info.get('Tag', 'latest')
                    
                    if image_name:
                        full_image_name = f"{image_name}:{image_tag}"
                        await self._backup_single_image(full_image_name, images_dir)
            
            logger.info("Image backup completed")
            return True
            
        except Exception as e:
            logger.error(f"Image backup failed: {str(e)}")
            return False
    
    async def _backup_single_image(self, image_name: str, backup_dir: Path):
        """Backup a single Docker image"""
        try:
            # Sanitize image name for filename
            safe_name = image_name.replace('/', '_').replace(':', '_')
            image_backup_path = backup_dir / f"{safe_name}.tar"
            
            cmd = ['docker', 'save', '-o', str(image_backup_path), image_name]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for large images
            )
            
            if process.returncode == 0:
                logger.info(f"Image {image_name} backed up successfully")
            else:
                logger.warning(f"Image {image_name} backup failed: {process.stderr}")
                
        except Exception as e:
            logger.error(f"Image {image_name} backup error: {str(e)}")
    
    async def _backup_logs(self, backup_dir: Path) -> bool:
        """Backup service logs"""
        try:
            logs_dir = backup_dir / "logs"
            logs_dir.mkdir(exist_ok=True)
            
            # Backup application logs
            app_logs_dir = self.project_root / "logs"
            if app_logs_dir.exists():
                shutil.copytree(app_logs_dir, logs_dir / "application", dirs_exist_ok=True)
            
            # Backup Docker container logs
            container_logs_dir = logs_dir / "containers"
            container_logs_dir.mkdir(exist_ok=True)
            
            # Get container IDs
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
                container_ids = process.stdout.strip().split('\n')
                
                for container_id in container_ids:
                    if container_id.strip():
                        await self._backup_container_logs(container_id.strip(), container_logs_dir)
            
            logger.info("Log backup completed")
            return True
            
        except Exception as e:
            logger.error(f"Log backup failed: {str(e)}")
            return False
    
    async def _backup_container_logs(self, container_id: str, backup_dir: Path):
        """Backup logs from a specific container"""
        try:
            log_file = backup_dir / f"{container_id}.log"
            
            cmd = ['docker', 'logs', container_id]
            
            with open(log_file, 'w') as f:
                process = subprocess.run(
                    cmd,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    timeout=60
                )
            
            if process.returncode == 0:
                logger.info(f"Container {container_id} logs backed up")
            else:
                logger.warning(f"Container {container_id} log backup failed")
                
        except Exception as e:
            logger.error(f"Container {container_id} log backup error: {str(e)}")
    
    async def _backup_service_state(self, backup_dir: Path) -> bool:
        """Backup service state information"""
        try:
            state_dir = backup_dir / "service_state"
            state_dir.mkdir(exist_ok=True)
            
            # Backup container information
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
                with open(state_dir / "containers.json", 'w') as f:
                    f.write(process.stdout)
            
            # Backup network information
            network_cmd = ['docker', 'network', 'ls', '--format', 'json']
            network_process = subprocess.run(
                network_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if network_process.returncode == 0:
                with open(state_dir / "networks.json", 'w') as f:
                    f.write(network_process.stdout)
            
            # Backup volume information
            volume_cmd = ['docker', 'volume', 'ls', '--format', 'json']
            volume_process = subprocess.run(
                volume_cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if volume_process.returncode == 0:
                with open(state_dir / "volumes.json", 'w') as f:
                    f.write(volume_process.stdout)
            
            # Create backup metadata
            metadata = {
                'backup_timestamp': datetime.now().isoformat(),
                'docker_version': self._get_docker_version(),
                'compose_version': self._get_compose_version(),
                'configuration': dict(self.config)
            }
            
            with open(state_dir / "metadata.json", 'w') as f:
                json.dump(metadata, f, indent=2)
            
            logger.info("Service state backup completed")
            return True
            
        except Exception as e:
            logger.error(f"Service state backup failed: {str(e)}")
            return False
    
    def _get_docker_version(self) -> str:
        """Get Docker version"""
        try:
            process = subprocess.run(
                ['docker', '--version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return process.stdout.strip() if process.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    def _get_compose_version(self) -> str:
        """Get Docker Compose version"""
        try:
            process = subprocess.run(
                ['docker', 'compose', 'version'],
                capture_output=True,
                text=True,
                timeout=10
            )
            return process.stdout.strip() if process.returncode == 0 else "unknown"
        except:
            return "unknown"
    
    async def _create_archive(self, source_dir: Path, archive_path: Path):
        """Create compressed archive from backup directory"""
        with tarfile.open(archive_path, 'w:gz') as tar:
            tar.add(source_dir, arcname='.')
    
    async def _create_backup_metadata(self, 
                                     backup_id: str, 
                                     backup_path: Path, 
                                     components: List[str],
                                     size_bytes: int,
                                     duration_seconds: float):
        """Create backup metadata file"""
        metadata = {
            'backup_id': backup_id,
            'timestamp': datetime.now().isoformat(),
            'backup_path': str(backup_path),
            'size_bytes': size_bytes,
            'size_mb': round(size_bytes / 1024 / 1024, 2),
            'duration_seconds': round(duration_seconds, 2),
            'components': components,
            'docker_version': self._get_docker_version(),
            'compose_version': self._get_compose_version(),
            'configuration_snapshot': dict(self.config)
        }
        
        metadata_path = self.backup_dir / f"{backup_id}_metadata.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
    
    async def restore_backup(self, backup_id: str, 
                           restore_volumes: bool = True,
                           restore_images: bool = False,
                           restore_configuration: bool = True) -> RecoveryResult:
        """
        Restore from backup
        Requirements: 6.3, 6.4, 6.5
        """
        start_time = time.time()
        
        logger.info(f"Starting restore from backup {backup_id}...")
        
        try:
            # Find backup file
            backup_path = self.backup_dir / f"{backup_id}.tar.gz"
            if not backup_path.exists():
                return RecoveryResult(
                    success=False,
                    backup_id=backup_id,
                    message=f"Backup file not found: {backup_path}"
                )
            
            # Extract backup
            temp_restore_dir = self.backup_dir / f"restore_{backup_id}"
            temp_restore_dir.mkdir(exist_ok=True)
            
            with tarfile.open(backup_path, 'r:gz') as tar:
                tar.extractall(temp_restore_dir)
            
            restored_components = []
            
            # Stop current services before restore
            await self._stop_services()
            
            # Restore configuration
            if restore_configuration:
                config_restored = await self._restore_configuration(temp_restore_dir)
                if config_restored:
                    restored_components.append("configuration")
            
            # Restore volumes
            if restore_volumes:
                volumes_restored = await self._restore_volumes(temp_restore_dir)
                if volumes_restored:
                    restored_components.append("volumes")
            
            # Restore images
            if restore_images:
                images_restored = await self._restore_images(temp_restore_dir)
                if images_restored:
                    restored_components.append("images")
            
            # Cleanup temporary directory
            shutil.rmtree(temp_restore_dir)
            
            duration = time.time() - start_time
            
            logger.info(f"Restore from backup {backup_id} completed successfully")
            
            return RecoveryResult(
                success=True,
                backup_id=backup_id,
                restored_components=restored_components,
                duration_seconds=duration,
                message="Restore completed successfully"
            )
            
        except Exception as e:
            logger.error(f"Restore failed: {str(e)}")
            
            # Cleanup on failure
            if temp_restore_dir.exists():
                shutil.rmtree(temp_restore_dir)
            
            return RecoveryResult(
                success=False,
                backup_id=backup_id,
                message=f"Restore failed: {str(e)}"
            )
    
    async def _stop_services(self):
        """Stop running services before restore"""
        try:
            cmd = [
                'docker', 'compose', '-f', str(self.compose_file),
                '--env-file', str(self.env_file),
                'down'
            ]
            
            subprocess.run(
                cmd,
                cwd=self.config_dir,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            logger.info("Services stopped for restore")
            
        except Exception as e:
            logger.warning(f"Could not stop services: {str(e)}")
    
    async def _restore_configuration(self, restore_dir: Path) -> bool:
        """Restore configuration files"""
        try:
            config_dir = restore_dir / "configuration"
            if not config_dir.exists():
                return False
            
            # Restore environment file
            env_backup = config_dir / ".env.external-meilisearch"
            if env_backup.exists():
                shutil.copy2(env_backup, self.env_file)
            
            # Restore Docker Compose file
            compose_backup = config_dir / "docker-compose.external-meilisearch.yml"
            if compose_backup.exists():
                shutil.copy2(compose_backup, self.compose_file)
            
            # Restore Nginx configuration
            nginx_backup = config_dir / "nginx.external-meilisearch.conf"
            nginx_conf = self.config_dir / "nginx.external-meilisearch.conf"
            if nginx_backup.exists():
                shutil.copy2(nginx_backup, nginx_conf)
            
            # Restore SSL certificates
            ssl_backup_dir = config_dir / "ssl"
            ssl_dir = self.project_root / "ssl"
            if ssl_backup_dir.exists():
                if ssl_dir.exists():
                    shutil.rmtree(ssl_dir)
                shutil.copytree(ssl_backup_dir, ssl_dir)
            
            logger.info("Configuration restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Configuration restore failed: {str(e)}")
            return False
    
    async def _restore_volumes(self, restore_dir: Path) -> bool:
        """Restore Docker volumes"""
        try:
            volumes_dir = restore_dir / "volumes"
            if not volumes_dir.exists():
                return False
            
            # Restore each volume
            for volume_backup in volumes_dir.glob("*.tar"):
                volume_name = volume_backup.stem
                await self._restore_single_volume(volume_name, volume_backup)
            
            logger.info("Volumes restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Volume restore failed: {str(e)}")
            return False
    
    async def _restore_single_volume(self, volume_name: str, backup_file: Path):
        """Restore a single Docker volume"""
        try:
            # Create volume if it doesn't exist
            subprocess.run(
                ['docker', 'volume', 'create', volume_name],
                capture_output=True,
                timeout=30
            )
            
            # Restore volume data
            cmd = [
                'docker', 'run', '--rm',
                '-v', f"{volume_name}:/volume",
                '-v', f"{backup_file.parent}:/backup",
                'alpine:latest',
                'tar', 'xf', f"/backup/{backup_file.name}", '-C', '/volume'
            ]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300
            )
            
            if process.returncode == 0:
                logger.info(f"Volume {volume_name} restored successfully")
            else:
                logger.warning(f"Volume {volume_name} restore failed: {process.stderr}")
                
        except Exception as e:
            logger.error(f"Volume {volume_name} restore error: {str(e)}")
    
    async def _restore_images(self, restore_dir: Path) -> bool:
        """Restore Docker images"""
        try:
            images_dir = restore_dir / "images"
            if not images_dir.exists():
                return False
            
            # Restore each image
            for image_backup in images_dir.glob("*.tar"):
                await self._restore_single_image(image_backup)
            
            logger.info("Images restored successfully")
            return True
            
        except Exception as e:
            logger.error(f"Image restore failed: {str(e)}")
            return False
    
    async def _restore_single_image(self, backup_file: Path):
        """Restore a single Docker image"""
        try:
            cmd = ['docker', 'load', '-i', str(backup_file)]
            
            process = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes for large images
            )
            
            if process.returncode == 0:
                logger.info(f"Image from {backup_file.name} restored successfully")
            else:
                logger.warning(f"Image restore from {backup_file.name} failed: {process.stderr}")
                
        except Exception as e:
            logger.error(f"Image restore from {backup_file.name} error: {str(e)}")
    
    async def list_backups(self) -> List[Dict[str, any]]:
        """List available backups"""
        backups = []
        
        for backup_file in self.backup_dir.glob("docker_backup_*.tar.gz"):
            backup_id = backup_file.stem
            metadata_file = self.backup_dir / f"{backup_id}_metadata.json"
            
            backup_info = {
                'backup_id': backup_id,
                'backup_file': str(backup_file),
                'size_bytes': backup_file.stat().st_size,
                'created': datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat()
            }
            
            # Load metadata if available
            if metadata_file.exists():
                try:
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                        backup_info.update(metadata)
                except Exception as e:
                    logger.warning(f"Could not load metadata for {backup_id}: {str(e)}")
            
            backups.append(backup_info)
        
        # Sort by creation time (newest first)
        backups.sort(key=lambda x: x['created'], reverse=True)
        
        return backups
    
    async def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup"""
        try:
            backup_file = self.backup_dir / f"{backup_id}.tar.gz"
            metadata_file = self.backup_dir / f"{backup_id}_metadata.json"
            
            if backup_file.exists():
                backup_file.unlink()
            
            if metadata_file.exists():
                metadata_file.unlink()
            
            logger.info(f"Backup {backup_id} deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete backup {backup_id}: {str(e)}")
            return False


async def main():
    """Main CLI interface"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Docker Backup and Recovery Manager")
    parser.add_argument('command', choices=[
        'backup', 'restore', 'list', 'delete'
    ])
    parser.add_argument('--backup-id', help='Backup ID for restore/delete operations')
    parser.add_argument('--include-volumes', action='store_true', default=True, help='Include volumes in backup')
    parser.add_argument('--include-images', action='store_true', help='Include images in backup')
    parser.add_argument('--include-logs', action='store_true', default=True, help='Include logs in backup')
    parser.add_argument('--restore-volumes', action='store_true', default=True, help='Restore volumes')
    parser.add_argument('--restore-images', action='store_true', help='Restore images')
    parser.add_argument('--restore-configuration', action='store_true', default=True, help='Restore configuration')
    
    args = parser.parse_args()
    
    manager = DockerBackupRecoveryManager()
    
    if args.command == 'backup':
        result = await manager.create_backup(
            include_volumes=args.include_volumes,
            include_images=args.include_images,
            include_logs=args.include_logs
        )
        print(f"Backup: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Message: {result.message}")
        if result.success:
            print(f"Backup ID: {result.backup_id}")
            print(f"Size: {result.size_bytes / 1024 / 1024:.2f} MB")
            print(f"Components: {', '.join(result.components)}")
    
    elif args.command == 'restore':
        if not args.backup_id:
            print("Error: --backup-id is required for restore")
            sys.exit(1)
        
        result = await manager.restore_backup(
            backup_id=args.backup_id,
            restore_volumes=args.restore_volumes,
            restore_images=args.restore_images,
            restore_configuration=args.restore_configuration
        )
        print(f"Restore: {'SUCCESS' if result.success else 'FAILED'}")
        print(f"Message: {result.message}")
        if result.success:
            print(f"Restored components: {', '.join(result.restored_components)}")
    
    elif args.command == 'list':
        backups = await manager.list_backups()
        if backups:
            print("Available backups:")
            for backup in backups:
                size_mb = backup.get('size_bytes', 0) / 1024 / 1024
                components = backup.get('components', [])
                print(f"  {backup['backup_id']}")
                print(f"    Created: {backup['created']}")
                print(f"    Size: {size_mb:.2f} MB")
                print(f"    Components: {', '.join(components)}")
                print()
        else:
            print("No backups found")
    
    elif args.command == 'delete':
        if not args.backup_id:
            print("Error: --backup-id is required for delete")
            sys.exit(1)
        
        success = await manager.delete_backup(args.backup_id)
        print(f"Delete: {'SUCCESS' if success else 'FAILED'}")


if __name__ == '__main__':
    asyncio.run(main())