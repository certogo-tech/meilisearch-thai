#!/usr/bin/env python3
"""
Backup and recovery utilities for standalone Thai Tokenizer deployment.

This script provides comprehensive backup and recovery capabilities for the
Thai Tokenizer service in standalone deployment mode, including configuration,
custom dictionaries, service state, and logs.
"""

import os
import sys
import json
import shutil
import tarfile
import argparse
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
import hashlib

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


class StandaloneBackupManager:
    """Manages backup and recovery for standalone Thai Tokenizer deployment."""
    
    def __init__(self, install_path: str):
        """
        Initialize backup manager.
        
        Args:
            install_path: Installation directory path
        """
        self.install_path = Path(install_path)
        self.backup_dir = self.install_path / "backups"
        self.logger = get_structured_logger(f"{__name__}.StandaloneBackupManager")
        
        # Ensure backup directory exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
    
    def create_backup_manifest(self, backup_path: Path) -> Dict[str, Any]:
        """
        Create backup manifest with metadata.
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            Backup manifest dictionary
        """
        manifest = {
            "backup_type": "standalone_thai_tokenizer",
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "install_path": str(self.install_path),
            "backup_file": str(backup_path),
            "components": [],
            "checksums": {},
            "size_bytes": 0
        }
        
        return manifest
    
    def calculate_file_checksum(self, file_path: Path) -> str:
        """
        Calculate SHA256 checksum of a file.
        
        Args:
            file_path: Path to file
            
        Returns:
            SHA256 checksum as hex string
        """
        sha256_hash = hashlib.sha256()
        
        try:
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(chunk)
            return sha256_hash.hexdigest()
        except Exception as e:
            self.logger.warning(f"Cannot calculate checksum for {file_path}: {e}")
            return ""
    
    def backup_configuration(self, backup_root: Path) -> bool:
        """
        Backup configuration files.
        
        Args:
            backup_root: Root directory for backup
            
        Returns:
            True if backup was successful
        """
        try:
            config_backup_dir = backup_root / "config"
            config_backup_dir.mkdir(parents=True, exist_ok=True)
            
            config_dir = self.install_path / "config"
            if not config_dir.exists():
                self.logger.warning("Configuration directory not found")
                return False
            
            # Backup all configuration files
            for config_file in config_dir.iterdir():
                if config_file.is_file():
                    shutil.copy2(config_file, config_backup_dir / config_file.name)
                    self.logger.debug(f"Backed up config file: {config_file.name}")
            
            self.logger.info("Configuration backup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration backup failed: {e}")
            return False
    
    def backup_custom_dictionaries(self, backup_root: Path) -> bool:
        """
        Backup custom dictionaries and data files.
        
        Args:
            backup_root: Root directory for backup
            
        Returns:
            True if backup was successful
        """
        try:
            data_backup_dir = backup_root / "data"
            data_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup data directory if it exists
            data_dir = self.install_path / "data"
            if data_dir.exists():
                for data_file in data_dir.rglob("*"):
                    if data_file.is_file():
                        relative_path = data_file.relative_to(data_dir)
                        backup_file_path = data_backup_dir / relative_path
                        backup_file_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(data_file, backup_file_path)
                        self.logger.debug(f"Backed up data file: {relative_path}")
            
            # Backup project-level dictionaries
            project_data_dir = self.install_path.parent.parent / "data" / "dictionaries"
            if project_data_dir.exists():
                project_backup_dir = data_backup_dir / "project_dictionaries"
                project_backup_dir.mkdir(parents=True, exist_ok=True)
                
                for dict_file in project_data_dir.iterdir():
                    if dict_file.is_file():
                        shutil.copy2(dict_file, project_backup_dir / dict_file.name)
                        self.logger.debug(f"Backed up project dictionary: {dict_file.name}")
            
            self.logger.info("Custom dictionaries backup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Custom dictionaries backup failed: {e}")
            return False
    
    def backup_service_state(self, backup_root: Path) -> bool:
        """
        Backup service state and runtime information.
        
        Args:
            backup_root: Root directory for backup
            
        Returns:
            True if backup was successful
        """
        try:
            state_backup_dir = backup_root / "state"
            state_backup_dir.mkdir(parents=True, exist_ok=True)
            
            # Backup runtime files
            run_dir = self.install_path / "run"
            if run_dir.exists():
                for run_file in run_dir.iterdir():
                    if run_file.is_file():
                        shutil.copy2(run_file, state_backup_dir / run_file.name)
                        self.logger.debug(f"Backed up runtime file: {run_file.name}")
            
            # Backup virtual environment info
            venv_info_file = self.install_path / "venv-info.json"
            if venv_info_file.exists():
                shutil.copy2(venv_info_file, state_backup_dir / "venv-info.json")
            
            # Backup installation report
            install_report_file = self.install_path / "installation-report.json"
            if install_report_file.exists():
                shutil.copy2(install_report_file, state_backup_dir / "installation-report.json")
            
            # Create service state snapshot
            state_snapshot = {
                "timestamp": datetime.now().isoformat(),
                "install_path": str(self.install_path),
                "python_version": sys.version,
                "platform": sys.platform,
            }
            
            # Try to get current service status
            try:
                from .manage_service import ProcessManager
                process_manager = ProcessManager(str(self.install_path))
                status = process_manager.get_service_status()
                state_snapshot["service_status"] = status
            except Exception as e:
                self.logger.warning(f"Cannot get service status for backup: {e}")
                state_snapshot["service_status"] = {"error": str(e)}
            
            with open(state_backup_dir / "service_state.json", 'w') as f:
                json.dump(state_snapshot, f, indent=2, default=str)
            
            self.logger.info("Service state backup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Service state backup failed: {e}")
            return False
    
    def backup_logs(self, backup_root: Path, max_log_size_mb: int = 100) -> bool:
        """
        Backup log files with size limit.
        
        Args:
            backup_root: Root directory for backup
            max_log_size_mb: Maximum log size to backup in MB
            
        Returns:
            True if backup was successful
        """
        try:
            logs_backup_dir = backup_root / "logs"
            logs_backup_dir.mkdir(parents=True, exist_ok=True)
            
            logs_dir = self.install_path / "logs"
            if not logs_dir.exists():
                self.logger.info("No logs directory found")
                return True
            
            max_size_bytes = max_log_size_mb * 1024 * 1024
            
            for log_file in logs_dir.iterdir():
                if log_file.is_file():
                    file_size = log_file.stat().st_size
                    
                    if file_size > max_size_bytes:
                        self.logger.warning(
                            f"Log file {log_file.name} is too large ({file_size / 1024 / 1024:.1f}MB), "
                            f"backing up last {max_log_size_mb}MB only"
                        )
                        
                        # Backup only the tail of large log files
                        with open(log_file, 'rb') as src:
                            src.seek(-max_size_bytes, 2)  # Seek to last N bytes
                            with open(logs_backup_dir / log_file.name, 'wb') as dst:
                                dst.write(src.read())
                    else:
                        shutil.copy2(log_file, logs_backup_dir / log_file.name)
                    
                    self.logger.debug(f"Backed up log file: {log_file.name}")
            
            self.logger.info("Logs backup completed")
            return True
            
        except Exception as e:
            self.logger.error(f"Logs backup failed: {e}")
            return False
    
    def create_full_backup(self, backup_name: Optional[str] = None, 
                          include_logs: bool = True, max_log_size_mb: int = 100) -> Optional[Path]:
        """
        Create a complete backup of the standalone deployment.
        
        Args:
            backup_name: Optional custom backup name
            include_logs: Whether to include log files
            max_log_size_mb: Maximum log size to backup in MB
            
        Returns:
            Path to backup file or None if failed
        """
        try:
            # Generate backup name
            if not backup_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_name = f"thai_tokenizer_standalone_backup_{timestamp}"
            
            backup_file = self.backup_dir / f"{backup_name}.tar.gz"
            temp_backup_dir = self.backup_dir / f"temp_{backup_name}"
            
            self.logger.info(f"Creating full backup: {backup_file}")
            
            # Create temporary backup directory
            temp_backup_dir.mkdir(parents=True, exist_ok=True)
            
            try:
                # Create backup manifest
                manifest = self.create_backup_manifest(backup_file)
                
                # Backup components
                components_backed_up = []
                
                if self.backup_configuration(temp_backup_dir):
                    components_backed_up.append("configuration")
                
                if self.backup_custom_dictionaries(temp_backup_dir):
                    components_backed_up.append("custom_dictionaries")
                
                if self.backup_service_state(temp_backup_dir):
                    components_backed_up.append("service_state")
                
                if include_logs and self.backup_logs(temp_backup_dir, max_log_size_mb):
                    components_backed_up.append("logs")
                
                manifest["components"] = components_backed_up
                
                # Calculate checksums for backed up files
                for file_path in temp_backup_dir.rglob("*"):
                    if file_path.is_file():
                        relative_path = str(file_path.relative_to(temp_backup_dir))
                        manifest["checksums"][relative_path] = self.calculate_file_checksum(file_path)
                
                # Save manifest
                with open(temp_backup_dir / "backup_manifest.json", 'w') as f:
                    json.dump(manifest, f, indent=2, default=str)
                
                # Create tar.gz archive
                with tarfile.open(backup_file, "w:gz") as tar:
                    tar.add(temp_backup_dir, arcname=backup_name)
                
                # Update manifest with final size
                manifest["size_bytes"] = backup_file.stat().st_size
                
                self.logger.info(f"Backup created successfully: {backup_file}")
                self.logger.info(f"Backup size: {manifest['size_bytes'] / 1024 / 1024:.1f}MB")
                self.logger.info(f"Components backed up: {', '.join(components_backed_up)}")
                
                return backup_file
                
            finally:
                # Clean up temporary directory
                if temp_backup_dir.exists():
                    shutil.rmtree(temp_backup_dir)
            
        except Exception as e:
            self.logger.error(f"Full backup failed: {e}")
            return None
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List available backups with metadata.
        
        Returns:
            List of backup information dictionaries
        """
        backups = []
        
        try:
            for backup_file in self.backup_dir.glob("*.tar.gz"):
                backup_info = {
                    "name": backup_file.stem,
                    "file": str(backup_file),
                    "size_bytes": backup_file.stat().st_size,
                    "created": datetime.fromtimestamp(backup_file.stat().st_mtime).isoformat(),
                    "manifest": None
                }
                
                # Try to extract manifest
                try:
                    with tarfile.open(backup_file, "r:gz") as tar:
                        manifest_member = None
                        for member in tar.getmembers():
                            if member.name.endswith("backup_manifest.json"):
                                manifest_member = member
                                break
                        
                        if manifest_member:
                            manifest_file = tar.extractfile(manifest_member)
                            if manifest_file:
                                manifest_data = json.load(manifest_file)
                                backup_info["manifest"] = manifest_data
                
                except Exception as e:
                    self.logger.warning(f"Cannot read manifest from {backup_file}: {e}")
                
                backups.append(backup_info)
            
            # Sort by creation time (newest first)
            backups.sort(key=lambda x: x["created"], reverse=True)
            
        except Exception as e:
            self.logger.error(f"Failed to list backups: {e}")
        
        return backups
    
    def restore_backup(self, backup_file: Path, restore_components: Optional[List[str]] = None,
                      dry_run: bool = False) -> bool:
        """
        Restore from backup file.
        
        Args:
            backup_file: Path to backup file
            restore_components: Optional list of components to restore
            dry_run: If True, only show what would be restored
            
        Returns:
            True if restore was successful
        """
        try:
            if not backup_file.exists():
                self.logger.error(f"Backup file not found: {backup_file}")
                return False
            
            self.logger.info(f"Restoring from backup: {backup_file}")
            
            temp_restore_dir = self.backup_dir / f"temp_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            try:
                # Extract backup
                with tarfile.open(backup_file, "r:gz") as tar:
                    tar.extractall(temp_restore_dir)
                
                # Find the backup directory (should be the only directory)
                backup_content_dirs = [d for d in temp_restore_dir.iterdir() if d.is_dir()]
                if not backup_content_dirs:
                    self.logger.error("No backup content found in archive")
                    return False
                
                backup_content_dir = backup_content_dirs[0]
                
                # Load manifest
                manifest_file = backup_content_dir / "backup_manifest.json"
                if manifest_file.exists():
                    with open(manifest_file, 'r') as f:
                        manifest = json.load(f)
                    self.logger.info(f"Backup manifest loaded: {manifest.get('timestamp', 'unknown')}")
                else:
                    self.logger.warning("No backup manifest found")
                    manifest = {}
                
                # Determine components to restore
                available_components = manifest.get("components", [])
                if restore_components is None:
                    restore_components = available_components
                else:
                    # Filter to only available components
                    restore_components = [c for c in restore_components if c in available_components]
                
                if dry_run:
                    self.logger.info("DRY RUN - Would restore the following:")
                    for component in restore_components:
                        self.logger.info(f"  - {component}")
                    return True
                
                # Stop service before restore
                try:
                    from .manage_service import ProcessManager
                    process_manager = ProcessManager(str(self.install_path))
                    if process_manager.get_service_status()["running"]:
                        self.logger.info("Stopping service for restore")
                        process_manager.stop_service()
                except Exception as e:
                    self.logger.warning(f"Cannot stop service: {e}")
                
                # Restore components
                restored_components = []
                
                if "configuration" in restore_components:
                    config_backup_dir = backup_content_dir / "config"
                    if config_backup_dir.exists():
                        config_dir = self.install_path / "config"
                        config_dir.mkdir(parents=True, exist_ok=True)
                        
                        for config_file in config_backup_dir.iterdir():
                            if config_file.is_file():
                                shutil.copy2(config_file, config_dir / config_file.name)
                        
                        restored_components.append("configuration")
                        self.logger.info("Configuration restored")
                
                if "custom_dictionaries" in restore_components:
                    data_backup_dir = backup_content_dir / "data"
                    if data_backup_dir.exists():
                        data_dir = self.install_path / "data"
                        data_dir.mkdir(parents=True, exist_ok=True)
                        
                        for data_file in data_backup_dir.rglob("*"):
                            if data_file.is_file() and not data_file.name.startswith("project_dictionaries"):
                                relative_path = data_file.relative_to(data_backup_dir)
                                restore_file_path = data_dir / relative_path
                                restore_file_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.copy2(data_file, restore_file_path)
                        
                        restored_components.append("custom_dictionaries")
                        self.logger.info("Custom dictionaries restored")
                
                if "service_state" in restore_components:
                    state_backup_dir = backup_content_dir / "state"
                    if state_backup_dir.exists():
                        run_dir = self.install_path / "run"
                        run_dir.mkdir(parents=True, exist_ok=True)
                        
                        for state_file in state_backup_dir.iterdir():
                            if state_file.is_file() and state_file.name != "service_state.json":
                                shutil.copy2(state_file, run_dir / state_file.name)
                        
                        restored_components.append("service_state")
                        self.logger.info("Service state restored")
                
                if "logs" in restore_components:
                    logs_backup_dir = backup_content_dir / "logs"
                    if logs_backup_dir.exists():
                        logs_dir = self.install_path / "logs"
                        logs_dir.mkdir(parents=True, exist_ok=True)
                        
                        for log_file in logs_backup_dir.iterdir():
                            if log_file.is_file():
                                # Append timestamp to avoid overwriting current logs
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                restore_name = f"{log_file.stem}_restored_{timestamp}{log_file.suffix}"
                                shutil.copy2(log_file, logs_dir / restore_name)
                        
                        restored_components.append("logs")
                        self.logger.info("Logs restored")
                
                self.logger.info(f"Restore completed successfully. Restored components: {', '.join(restored_components)}")
                return True
                
            finally:
                # Clean up temporary directory
                if temp_restore_dir.exists():
                    shutil.rmtree(temp_restore_dir)
            
        except Exception as e:
            self.logger.error(f"Restore failed: {e}")
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Clean up old backup files, keeping only the most recent ones.
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            Number of backups removed
        """
        try:
            backups = self.list_backups()
            
            if len(backups) <= keep_count:
                self.logger.info(f"No cleanup needed. Current backups: {len(backups)}, keeping: {keep_count}")
                return 0
            
            backups_to_remove = backups[keep_count:]
            removed_count = 0
            
            for backup in backups_to_remove:
                try:
                    backup_path = Path(backup["file"])
                    backup_path.unlink()
                    self.logger.info(f"Removed old backup: {backup_path.name}")
                    removed_count += 1
                except Exception as e:
                    self.logger.warning(f"Failed to remove backup {backup['file']}: {e}")
            
            self.logger.info(f"Cleanup completed. Removed {removed_count} old backups")
            return removed_count
            
        except Exception as e:
            self.logger.error(f"Backup cleanup failed: {e}")
            return 0


def main():
    """Main entry point for backup management."""
    parser = argparse.ArgumentParser(
        description="Backup and recovery for Thai Tokenizer standalone deployment"
    )
    
    parser.add_argument(
        "--install-path",
        required=True,
        help="Installation directory path"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Create backup command
    create_parser = subparsers.add_parser("create", help="Create a backup")
    create_parser.add_argument("--name", help="Custom backup name")
    create_parser.add_argument("--no-logs", action="store_true", help="Exclude logs from backup")
    create_parser.add_argument("--max-log-size", type=int, default=100, help="Maximum log size in MB")
    
    # List backups command
    list_parser = subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Restore backup command
    restore_parser = subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_file", help="Path to backup file")
    restore_parser.add_argument("--components", nargs="+", 
                               choices=["configuration", "custom_dictionaries", "service_state", "logs"],
                               help="Components to restore")
    restore_parser.add_argument("--dry-run", action="store_true", help="Show what would be restored")
    
    # Cleanup command
    cleanup_parser = subparsers.add_parser("cleanup", help="Clean up old backups")
    cleanup_parser.add_argument("--keep", type=int, default=10, help="Number of backups to keep")
    
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
        # Create backup manager
        backup_manager = StandaloneBackupManager(args.install_path)
        
        # Execute command
        if args.command == "create":
            backup_file = backup_manager.create_full_backup(
                backup_name=args.name,
                include_logs=not args.no_logs,
                max_log_size_mb=args.max_log_size
            )
            
            if backup_file:
                print(f"Backup created: {backup_file}")
                sys.exit(0)
            else:
                print("Backup creation failed")
                sys.exit(1)
        
        elif args.command == "list":
            backups = backup_manager.list_backups()
            
            if args.json:
                print(json.dumps(backups, indent=2, default=str))
            else:
                if not backups:
                    print("No backups found")
                else:
                    print(f"Available backups ({len(backups)}):")
                    for backup in backups:
                        size_mb = backup["size_bytes"] / 1024 / 1024
                        components = backup.get("manifest", {}).get("components", [])
                        print(f"  {backup['name']}")
                        print(f"    Created: {backup['created']}")
                        print(f"    Size: {size_mb:.1f}MB")
                        print(f"    Components: {', '.join(components) if components else 'unknown'}")
                        print()
        
        elif args.command == "restore":
            backup_file = Path(args.backup_file)
            success = backup_manager.restore_backup(
                backup_file=backup_file,
                restore_components=args.components,
                dry_run=args.dry_run
            )
            
            if success:
                if args.dry_run:
                    print("Dry run completed successfully")
                else:
                    print("Restore completed successfully")
                sys.exit(0)
            else:
                print("Restore failed")
                sys.exit(1)
        
        elif args.command == "cleanup":
            removed_count = backup_manager.cleanup_old_backups(args.keep)
            print(f"Removed {removed_count} old backups")
            sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()