"""
Comprehensive backup and recovery system for on-premise Thai Tokenizer deployment.

This module provides unified backup and recovery capabilities across all deployment
methods (Docker, systemd, standalone) with support for configuration files,
custom dictionaries, service state, and automated scheduling.

Requirements: 6.1, 6.2, 6.3
"""

import asyncio
import json
import logging
import os
import shutil
import tarfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum
import hashlib
import tempfile

from pydantic import BaseModel, Field, ConfigDict

try:
    from src.utils.logging import get_structured_logger
    from src.deployment.config import OnPremiseConfig, DeploymentMethod
except ImportError:
    # Fallback for when running outside the main application
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)
    
    class DeploymentMethod(str, Enum):
        DOCKER = "docker"
        SYSTEMD = "systemd"
        STANDALONE = "standalone"

logger = get_structured_logger(__name__)


class BackupType(str, Enum):
    """Types of backup operations."""
    FULL = "full"
    CONFIGURATION = "configuration"
    DICTIONARIES = "dictionaries"
    SERVICE_STATE = "service_state"
    LOGS = "logs"


class BackupStatus(str, Enum):
    """Backup operation status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class BackupComponent:
    """Represents a component that can be backed up."""
    name: str
    source_path: Path
    description: str
    required: bool = True
    size_bytes: int = 0
    checksum: str = ""


class BackupResult(BaseModel):
    """Result of a backup operation."""
    
    backup_id: str
    backup_type: BackupType
    deployment_method: DeploymentMethod
    status: BackupStatus
    backup_path: Optional[Path] = None
    size_bytes: int = 0
    duration_seconds: float = 0.0
    components: List[str] = Field(default_factory=list)
    checksums: Dict[str, str] = Field(default_factory=dict)
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class RecoveryResult(BaseModel):
    """Result of a recovery operation."""
    
    backup_id: str
    status: BackupStatus
    restored_components: List[str] = Field(default_factory=list)
    duration_seconds: float = 0.0
    error_message: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)


class BackupSchedule(BaseModel):
    """Backup scheduling configuration."""
    
    enabled: bool = False
    frequency_hours: int = Field(24, ge=1, le=168)  # 1 hour to 1 week
    backup_type: BackupType = BackupType.FULL
    max_backups_to_keep: int = Field(10, ge=1, le=100)
    include_logs: bool = True
    max_log_size_mb: int = Field(100, ge=1, le=1000)
    next_backup_time: Optional[datetime] = None


class BackupConfig(BaseModel):
    """Configuration for backup operations."""
    
    backup_directory: Path
    deployment_method: DeploymentMethod
    installation_path: Path
    data_path: Path
    config_path: Path
    log_path: Path
    
    # Backup settings
    compression_enabled: bool = True
    encryption_enabled: bool = False
    encryption_key: Optional[str] = None
    verify_checksums: bool = True
    
    # Retention settings
    max_backup_age_days: int = Field(30, ge=1, le=365)
    max_backup_size_gb: float = Field(10.0, ge=0.1, le=100.0)
    
    # Scheduling
    schedule: BackupSchedule = Field(default_factory=BackupSchedule)
    
    model_config = ConfigDict(arbitrary_types_allowed=True)


class BackupManager:
    """
    Comprehensive backup and recovery manager for on-premise deployment.
    
    Supports all deployment methods with unified interface for backup operations.
    """
    
    def __init__(self, config: BackupConfig):
        """
        Initialize backup manager.
        
        Args:
            config: Backup configuration
        """
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.BackupManager")
        
        # Ensure backup directory exists
        self.config.backup_directory.mkdir(parents=True, exist_ok=True)
        
        # Initialize deployment-specific handlers
        self._init_deployment_handlers()
    
    def _init_deployment_handlers(self):
        """Initialize deployment-specific backup handlers."""
        if self.config.deployment_method == DeploymentMethod.DOCKER:
            from .docker_backup_handler import DockerBackupHandler
            self.deployment_handler = DockerBackupHandler(self.config)
        elif self.config.deployment_method == DeploymentMethod.SYSTEMD:
            from .systemd_backup_handler import SystemdBackupHandler
            self.deployment_handler = SystemdBackupHandler(self.config)
        elif self.config.deployment_method == DeploymentMethod.STANDALONE:
            from .standalone_backup_handler import StandaloneBackupHandler
            self.deployment_handler = StandaloneBackupHandler(self.config)
        else:
            raise ValueError(f"Unsupported deployment method: {self.config.deployment_method}")
    
    async def create_backup(self, 
                           backup_type: BackupType = BackupType.FULL,
                           backup_name: Optional[str] = None,
                           include_components: Optional[List[str]] = None) -> BackupResult:
        """
        Create a backup of the specified type.
        
        Args:
            backup_type: Type of backup to create
            backup_name: Optional custom backup name
            include_components: Optional list of components to include
            
        Returns:
            BackupResult with operation details
        """
        start_time = time.time()
        
        # Generate backup ID
        if not backup_name:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{self.config.deployment_method.value}_{backup_type.value}_{timestamp}"
        
        backup_id = backup_name
        
        self.logger.info(f"Starting {backup_type.value} backup: {backup_id}")
        
        try:
            # Create backup result
            result = BackupResult(
                backup_id=backup_id,
                backup_type=backup_type,
                deployment_method=self.config.deployment_method,
                status=BackupStatus.IN_PROGRESS
            )
            
            # Create temporary backup directory
            with tempfile.TemporaryDirectory(prefix=f"backup_{backup_id}_") as temp_dir:
                temp_backup_path = Path(temp_dir)
                
                # Identify components to backup
                components = await self._identify_backup_components(backup_type, include_components)
                
                # Backup each component
                backed_up_components = []
                total_size = 0
                
                for component in components:
                    try:
                        component_result = await self._backup_component(component, temp_backup_path)
                        if component_result:
                            backed_up_components.append(component.name)
                            total_size += component.size_bytes
                            result.checksums[component.name] = component.checksum
                            self.logger.debug(f"Backed up component: {component.name}")
                        else:
                            if component.required:
                                raise Exception(f"Required component backup failed: {component.name}")
                            else:
                                result.warnings.append(f"Optional component backup failed: {component.name}")
                    
                    except Exception as e:
                        error_msg = f"Component backup failed ({component.name}): {str(e)}"
                        if component.required:
                            raise Exception(error_msg)
                        else:
                            result.warnings.append(error_msg)
                            self.logger.warning(error_msg)
                
                # Create backup metadata
                metadata = await self._create_backup_metadata(backup_id, backup_type, backed_up_components, result.checksums)
                metadata_file = temp_backup_path / "backup_metadata.json"
                with open(metadata_file, 'w') as f:
                    json.dump(metadata, f, indent=2, default=str)
                
                # Create final backup archive
                backup_file_path = self.config.backup_directory / f"{backup_id}.tar.gz"
                await self._create_backup_archive(temp_backup_path, backup_file_path)
                
                # Update result
                result.backup_path = backup_file_path
                result.size_bytes = backup_file_path.stat().st_size
                result.components = backed_up_components
                result.status = BackupStatus.COMPLETED
                result.duration_seconds = time.time() - start_time
                
                self.logger.info(
                    f"Backup {backup_id} completed successfully "
                    f"({result.size_bytes / 1024 / 1024:.2f}MB, {result.duration_seconds:.2f}s)"
                )
                
                # Save backup record
                await self._save_backup_record(result)
                
                return result
        
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Backup {backup_id} failed: {error_msg}")
            
            return BackupResult(
                backup_id=backup_id,
                backup_type=backup_type,
                deployment_method=self.config.deployment_method,
                status=BackupStatus.FAILED,
                error_message=error_msg,
                duration_seconds=time.time() - start_time
            )
    
    async def _identify_backup_components(self, 
                                        backup_type: BackupType, 
                                        include_components: Optional[List[str]] = None) -> List[BackupComponent]:
        """
        Identify components to include in backup based on type and filters.
        
        Args:
            backup_type: Type of backup
            include_components: Optional component filter
            
        Returns:
            List of backup components
        """
        components = []
        
        # Configuration files
        if backup_type in [BackupType.FULL, BackupType.CONFIGURATION]:
            if not include_components or "configuration" in include_components:
                config_component = BackupComponent(
                    name="configuration",
                    source_path=self.config.config_path,
                    description="Service configuration files",
                    required=True
                )
                components.append(config_component)
        
        # Custom dictionaries and data
        if backup_type in [BackupType.FULL, BackupType.DICTIONARIES]:
            if not include_components or "dictionaries" in include_components:
                dict_component = BackupComponent(
                    name="dictionaries",
                    source_path=self.config.data_path,
                    description="Custom dictionaries and data files",
                    required=False
                )
                components.append(dict_component)
        
        # Service state
        if backup_type in [BackupType.FULL, BackupType.SERVICE_STATE]:
            if not include_components or "service_state" in include_components:
                state_component = BackupComponent(
                    name="service_state",
                    source_path=self.config.installation_path / "run",
                    description="Service runtime state",
                    required=False
                )
                components.append(state_component)
        
        # Logs
        if backup_type in [BackupType.FULL, BackupType.LOGS]:
            if not include_components or "logs" in include_components:
                logs_component = BackupComponent(
                    name="logs",
                    source_path=self.config.log_path,
                    description="Service log files",
                    required=False
                )
                components.append(logs_component)
        
        # Add deployment-specific components
        deployment_components = await self.deployment_handler.get_deployment_specific_components(backup_type)
        components.extend(deployment_components)
        
        return components
    
    async def _backup_component(self, component: BackupComponent, backup_root: Path) -> bool:
        """
        Backup a single component.
        
        Args:
            component: Component to backup
            backup_root: Root backup directory
            
        Returns:
            True if backup was successful
        """
        try:
            if not component.source_path.exists():
                if component.required:
                    raise Exception(f"Required component path not found: {component.source_path}")
                else:
                    self.logger.warning(f"Optional component path not found: {component.source_path}")
                    return False
            
            component_backup_dir = backup_root / component.name
            component_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Calculate component size and checksum
            total_size = 0
            file_checksums = []
            
            if component.source_path.is_file():
                # Single file
                shutil.copy2(component.source_path, component_backup_dir / component.source_path.name)
                total_size = component.source_path.stat().st_size
                file_checksums.append(self._calculate_file_checksum(component.source_path))
            
            elif component.source_path.is_dir():
                # Directory tree
                for source_file in component.source_path.rglob("*"):
                    if source_file.is_file():
                        relative_path = source_file.relative_to(component.source_path)
                        backup_file_path = component_backup_dir / relative_path
                        backup_file_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Apply size limits for logs
                        if component.name == "logs" and self._should_limit_log_file(source_file):
                            await self._backup_log_file_with_limit(source_file, backup_file_path)
                        else:
                            shutil.copy2(source_file, backup_file_path)
                        
                        total_size += source_file.stat().st_size
                        file_checksums.append(self._calculate_file_checksum(source_file))
            
            # Update component metadata
            component.size_bytes = total_size
            component.checksum = self._calculate_combined_checksum(file_checksums)
            
            self.logger.debug(f"Component {component.name} backed up: {total_size} bytes")
            return True
        
        except Exception as e:
            self.logger.error(f"Component backup failed ({component.name}): {str(e)}")
            return False
    
    def _should_limit_log_file(self, log_file: Path) -> bool:
        """Check if log file should be size-limited."""
        max_size_bytes = self.config.schedule.max_log_size_mb * 1024 * 1024
        return log_file.stat().st_size > max_size_bytes
    
    async def _backup_log_file_with_limit(self, source_file: Path, backup_file: Path):
        """Backup log file with size limit (tail of file)."""
        max_size_bytes = self.config.schedule.max_log_size_mb * 1024 * 1024
        
        with open(source_file, 'rb') as src:
            src.seek(-max_size_bytes, 2)  # Seek to last N bytes
            with open(backup_file, 'wb') as dst:
                dst.write(src.read())
    
    def _calculate_file_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.warning(f"Cannot calculate checksum for {file_path}: {e}")
            return ""
    
    def _calculate_combined_checksum(self, checksums: List[str]) -> str:
        """Calculate combined checksum from multiple file checksums."""
        combined = "".join(sorted(checksums))
        return hashlib.sha256(combined.encode()).hexdigest()
    
    async def _create_backup_metadata(self, 
                                    backup_id: str, 
                                    backup_type: BackupType,
                                    components: List[str],
                                    checksums: Dict[str, str]) -> Dict[str, Any]:
        """Create backup metadata."""
        metadata = {
            "backup_id": backup_id,
            "backup_type": backup_type.value,
            "deployment_method": self.config.deployment_method.value,
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "installation_path": str(self.config.installation_path),
            "components": components,
            "checksums": checksums,
            "config_snapshot": {
                "backup_directory": str(self.config.backup_directory),
                "compression_enabled": self.config.compression_enabled,
                "verify_checksums": self.config.verify_checksums
            }
        }
        
        # Add deployment-specific metadata
        deployment_metadata = await self.deployment_handler.get_deployment_metadata()
        metadata["deployment_metadata"] = deployment_metadata
        
        return metadata
    
    async def _create_backup_archive(self, source_dir: Path, archive_path: Path):
        """Create compressed backup archive."""
        if self.config.compression_enabled:
            with tarfile.open(archive_path, "w:gz") as tar:
                tar.add(source_dir, arcname=".")
        else:
            with tarfile.open(archive_path, "w") as tar:
                tar.add(source_dir, arcname=".")
    
    async def _save_backup_record(self, result: BackupResult):
        """Save backup record to index."""
        records_file = self.config.backup_directory / "backup_records.json"
        
        # Load existing records
        records = []
        if records_file.exists():
            try:
                with open(records_file, 'r') as f:
                    records = json.load(f)
            except Exception as e:
                self.logger.warning(f"Cannot load backup records: {e}")
        
        # Add new record
        record = {
            "backup_id": result.backup_id,
            "backup_type": result.backup_type.value,
            "deployment_method": result.deployment_method.value,
            "status": result.status.value,
            "backup_path": str(result.backup_path) if result.backup_path else None,
            "size_bytes": result.size_bytes,
            "components": result.components,
            "timestamp": result.timestamp.isoformat(),
            "duration_seconds": result.duration_seconds
        }
        
        records.append(record)
        
        # Keep only recent records
        records = records[-100:]  # Keep last 100 records
        
        # Save updated records
        try:
            with open(records_file, 'w') as f:
                json.dump(records, f, indent=2, default=str)
        except Exception as e:
            self.logger.warning(f"Cannot save backup records: {e}")
    
    async def restore_backup(self, 
                           backup_id: str,
                           restore_components: Optional[List[str]] = None,
                           dry_run: bool = False) -> RecoveryResult:
        """
        Restore from backup.
        
        Args:
            backup_id: ID of backup to restore
            restore_components: Optional list of components to restore
            dry_run: If True, only show what would be restored
            
        Returns:
            RecoveryResult with operation details
        """
        start_time = time.time()
        
        self.logger.info(f"Starting restore from backup: {backup_id}")
        
        try:
            # Find backup file
            backup_file = self.config.backup_directory / f"{backup_id}.tar.gz"
            if not backup_file.exists():
                # Try without .tar.gz extension
                backup_file = self.config.backup_directory / backup_id
                if not backup_file.exists():
                    raise Exception(f"Backup file not found: {backup_id}")
            
            # Extract backup to temporary directory
            with tempfile.TemporaryDirectory(prefix=f"restore_{backup_id}_") as temp_dir:
                temp_restore_path = Path(temp_dir)
                
                # Extract backup
                with tarfile.open(backup_file, "r:gz" if backup_file.suffix == ".gz" else "r") as tar:
                    tar.extractall(temp_restore_path)
                
                # Load backup metadata
                metadata_file = temp_restore_path / "backup_metadata.json"
                if metadata_file.exists():
                    with open(metadata_file, 'r') as f:
                        metadata = json.load(f)
                else:
                    raise Exception("Backup metadata not found")
                
                # Validate backup integrity
                if self.config.verify_checksums:
                    await self._verify_backup_integrity(temp_restore_path, metadata)
                
                # Determine components to restore
                available_components = metadata.get("components", [])
                if restore_components is None:
                    restore_components = available_components
                else:
                    restore_components = [c for c in restore_components if c in available_components]
                
                if dry_run:
                    self.logger.info("DRY RUN - Would restore the following components:")
                    for component in restore_components:
                        self.logger.info(f"  - {component}")
                    
                    return RecoveryResult(
                        backup_id=backup_id,
                        status=BackupStatus.COMPLETED,
                        restored_components=restore_components,
                        duration_seconds=time.time() - start_time
                    )
                
                # Stop service before restore
                await self.deployment_handler.stop_service_for_restore()
                
                # Restore components
                restored_components = []
                
                for component_name in restore_components:
                    try:
                        component_dir = temp_restore_path / component_name
                        if component_dir.exists():
                            success = await self._restore_component(component_name, component_dir)
                            if success:
                                restored_components.append(component_name)
                                self.logger.info(f"Component restored: {component_name}")
                            else:
                                self.logger.warning(f"Component restore failed: {component_name}")
                    except Exception as e:
                        self.logger.error(f"Component restore error ({component_name}): {str(e)}")
                
                # Post-restore actions
                await self.deployment_handler.post_restore_actions(restored_components)
                
                self.logger.info(f"Restore completed: {len(restored_components)} components restored")
                
                return RecoveryResult(
                    backup_id=backup_id,
                    status=BackupStatus.COMPLETED,
                    restored_components=restored_components,
                    duration_seconds=time.time() - start_time
                )
        
        except Exception as e:
            error_msg = str(e)
            self.logger.error(f"Restore failed: {error_msg}")
            
            return RecoveryResult(
                backup_id=backup_id,
                status=BackupStatus.FAILED,
                error_message=error_msg,
                duration_seconds=time.time() - start_time
            )
    
    async def _verify_backup_integrity(self, backup_path: Path, metadata: Dict[str, Any]):
        """Verify backup integrity using checksums."""
        checksums = metadata.get("checksums", {})
        
        for component_name, expected_checksum in checksums.items():
            component_dir = backup_path / component_name
            if component_dir.exists():
                # Calculate actual checksum
                file_checksums = []
                for file_path in component_dir.rglob("*"):
                    if file_path.is_file():
                        file_checksums.append(self._calculate_file_checksum(file_path))
                
                actual_checksum = self._calculate_combined_checksum(file_checksums)
                
                if actual_checksum != expected_checksum:
                    raise Exception(f"Backup integrity check failed for component: {component_name}")
    
    async def _restore_component(self, component_name: str, component_dir: Path) -> bool:
        """
        Restore a single component.
        
        Args:
            component_name: Name of component to restore
            component_dir: Directory containing component backup
            
        Returns:
            True if restore was successful
        """
        try:
            if component_name == "configuration":
                target_dir = self.config.config_path
            elif component_name == "dictionaries":
                target_dir = self.config.data_path
            elif component_name == "service_state":
                target_dir = self.config.installation_path / "run"
            elif component_name == "logs":
                target_dir = self.config.log_path
                # For logs, append timestamp to avoid overwriting current logs
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_dir = target_dir / f"restored_{timestamp}"
            else:
                # Deployment-specific component
                return await self.deployment_handler.restore_deployment_component(component_name, component_dir)
            
            # Create target directory
            target_dir.mkdir(parents=True, exist_ok=True)
            
            # Copy files
            for source_file in component_dir.rglob("*"):
                if source_file.is_file():
                    relative_path = source_file.relative_to(component_dir)
                    target_file = target_dir / relative_path
                    target_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file, target_file)
            
            return True
        
        except Exception as e:
            self.logger.error(f"Component restore failed ({component_name}): {str(e)}")
            return False
    
    async def list_backups(self) -> List[Dict[str, Any]]:
        """
        List available backups with metadata.
        
        Returns:
            List of backup information
        """
        backups = []
        
        try:
            # Load backup records
            records_file = self.config.backup_directory / "backup_records.json"
            if records_file.exists():
                with open(records_file, 'r') as f:
                    records = json.load(f)
                
                for record in records:
                    backup_file = Path(record.get("backup_path", ""))
                    if backup_file.exists():
                        backups.append(record)
            
            # Also scan for backup files not in records
            for backup_file in self.config.backup_directory.glob("*.tar.gz"):
                backup_id = backup_file.stem
                
                # Check if already in records
                if any(r["backup_id"] == backup_id for r in backups):
                    continue
                
                # Add basic info
                backup_info = {
                    "backup_id": backup_id,
                    "backup_path": str(backup_file),
                    "size_bytes": backup_file.stat().st_size,
                    "timestamp": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                    "status": "completed"
                }
                
                backups.append(backup_info)
            
            # Sort by timestamp (newest first)
            backups.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
        
        return backups
    
    async def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a backup.
        
        Args:
            backup_id: ID of backup to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            backup_file = self.config.backup_directory / f"{backup_id}.tar.gz"
            if backup_file.exists():
                backup_file.unlink()
                self.logger.info(f"Backup deleted: {backup_id}")
                return True
            else:
                self.logger.warning(f"Backup file not found: {backup_id}")
                return False
        
        except Exception as e:
            self.logger.error(f"Failed to delete backup {backup_id}: {e}")
            return False
    
    async def cleanup_old_backups(self) -> int:
        """
        Clean up old backups based on retention policy.
        
        Returns:
            Number of backups removed
        """
        try:
            backups = await self.list_backups()
            removed_count = 0
            
            # Remove backups older than max age
            cutoff_date = datetime.now() - timedelta(days=self.config.max_backup_age_days)
            
            for backup in backups:
                try:
                    backup_date = datetime.fromisoformat(backup["timestamp"].replace("Z", "+00:00"))
                    if backup_date < cutoff_date:
                        if await self.delete_backup(backup["backup_id"]):
                            removed_count += 1
                except Exception as e:
                    self.logger.warning(f"Cannot process backup for cleanup: {backup['backup_id']}: {e}")
            
            # Remove excess backups if over size limit
            total_size = sum(b.get("size_bytes", 0) for b in backups)
            max_size_bytes = self.config.max_backup_size_gb * 1024 * 1024 * 1024
            
            if total_size > max_size_bytes:
                # Remove oldest backups first
                backups_by_age = sorted(backups, key=lambda x: x.get("timestamp", ""))
                
                for backup in backups_by_age:
                    if total_size <= max_size_bytes:
                        break
                    
                    if await self.delete_backup(backup["backup_id"]):
                        total_size -= backup.get("size_bytes", 0)
                        removed_count += 1
            
            if removed_count > 0:
                self.logger.info(f"Cleanup completed: removed {removed_count} old backups")
            
            return removed_count
        
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
            return 0
    
    async def schedule_backup(self) -> Optional[BackupResult]:
        """
        Execute scheduled backup if due.
        
        Returns:
            BackupResult if backup was executed, None otherwise
        """
        if not self.config.schedule.enabled:
            return None
        
        now = datetime.now()
        
        # Check if backup is due
        if self.config.schedule.next_backup_time and now < self.config.schedule.next_backup_time:
            return None
        
        self.logger.info("Executing scheduled backup")
        
        try:
            # Create backup
            result = await self.create_backup(
                backup_type=self.config.schedule.backup_type,
                backup_name=f"scheduled_{now.strftime('%Y%m%d_%H%M%S')}"
            )
            
            # Update next backup time
            self.config.schedule.next_backup_time = now + timedelta(hours=self.config.schedule.frequency_hours)
            
            # Cleanup old backups
            await self.cleanup_old_backups()
            
            return result
        
        except Exception as e:
            self.logger.error(f"Scheduled backup failed: {e}")
            return None