#!/usr/bin/env python3
"""
Command-line interface for backup and recovery operations.

This script provides a comprehensive CLI for managing backups, recovery procedures,
and rollback operations for the Thai Tokenizer on-premise deployment.

Requirements: 6.1, 6.2, 6.3, 6.4, 6.5
"""

import asyncio
import argparse
import json
import logging
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from utils.logging import get_structured_logger
    from deployment.config import OnPremiseConfig, DeploymentMethod
    from deployment.backup_manager import BackupManager, BackupConfig, BackupType, BackupSchedule
    from deployment.recovery_manager import RecoveryManager, FailureType
except ImportError as e:
    print(f"Import error: {e}")
    print("Please ensure you're running from the project root directory")
    sys.exit(1)

logger = get_structured_logger(__name__)


class BackupCLI:
    """Command-line interface for backup and recovery operations."""
    
    def __init__(self):
        """Initialize CLI."""
        self.backup_manager = None
        self.recovery_manager = None
    
    async def initialize_managers(self, config_file: Optional[str] = None):
        """Initialize backup and recovery managers."""
        try:
            # Load configuration
            if config_file and Path(config_file).exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                config = OnPremiseConfig(**config_data)
            else:
                # Use default configuration
                config = self._create_default_config()
            
            # Create backup configuration
            backup_config = BackupConfig(
                backup_directory=Path(config.data_path) / "backups",
                deployment_method=config.deployment_method,
                installation_path=Path(config.installation_path),
                data_path=Path(config.data_path),
                config_path=Path(config.config_path),
                log_path=Path(config.log_path)
            )
            
            # Initialize managers
            self.backup_manager = BackupManager(backup_config)
            self.recovery_manager = RecoveryManager(config, self.backup_manager)
            
            logger.info("Backup and recovery managers initialized")
        
        except Exception as e:
            logger.error(f"Failed to initialize managers: {e}")
            raise
    
    def _create_default_config(self) -> OnPremiseConfig:
        """Create default configuration for CLI usage."""
        from deployment.config import (
            MeilisearchConnectionConfig, ServiceConfig, SecurityConfig,
            ResourceConfig, MonitoringConfig
        )
        from pydantic import SecretStr
        
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.STANDALONE,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key=SecretStr("default-key")
            ),
            service_config=ServiceConfig(),
            security_config=SecurityConfig(),
            resource_config=ResourceConfig(),
            monitoring_config=MonitoringConfig(),
            installation_path="/opt/thai-tokenizer",
            data_path="/var/lib/thai-tokenizer",
            config_path="/etc/thai-tokenizer",
            log_path="/var/log/thai-tokenizer"
        )
    
    async def create_backup(self, args):
        """Create a backup."""
        try:
            backup_type = BackupType(args.type)
            
            print(f"Creating {backup_type.value} backup...")
            
            result = await self.backup_manager.create_backup(
                backup_type=backup_type,
                backup_name=args.name,
                include_components=args.components
            )
            
            if result.success:
                print(f"✓ Backup created successfully: {result.backup_id}")
                print(f"  Path: {result.backup_path}")
                print(f"  Size: {result.size_bytes / 1024 / 1024:.2f} MB")
                print(f"  Duration: {result.duration_seconds:.2f} seconds")
                print(f"  Components: {', '.join(result.components)}")
                
                if result.warnings:
                    print("⚠ Warnings:")
                    for warning in result.warnings:
                        print(f"    {warning}")
            else:
                print(f"✗ Backup failed: {result.error_message}")
                return 1
            
            return 0
        
        except Exception as e:
            print(f"✗ Backup creation failed: {e}")
            return 1
    
    async def list_backups(self, args):
        """List available backups."""
        try:
            backups = await self.backup_manager.list_backups()
            
            if not backups:
                print("No backups found.")
                return 0
            
            if args.json:
                print(json.dumps(backups, indent=2, default=str))
            else:
                print(f"Available backups ({len(backups)}):")
                print()
                
                for backup in backups:
                    backup_id = backup.get("backup_id", "unknown")
                    backup_type = backup.get("backup_type", "unknown")
                    size_mb = backup.get("size_bytes", 0) / 1024 / 1024
                    timestamp = backup.get("timestamp", "unknown")
                    components = backup.get("components", [])
                    
                    print(f"  {backup_id}")
                    print(f"    Type: {backup_type}")
                    print(f"    Created: {timestamp}")
                    print(f"    Size: {size_mb:.2f} MB")
                    print(f"    Components: {', '.join(components) if components else 'unknown'}")
                    print()
            
            return 0
        
        except Exception as e:
            print(f"✗ Failed to list backups: {e}")
            return 1
    
    async def restore_backup(self, args):
        """Restore from backup."""
        try:
            print(f"Restoring from backup: {args.backup_id}")
            
            if args.dry_run:
                print("DRY RUN - No actual changes will be made")
            
            result = await self.backup_manager.restore_backup(
                backup_id=args.backup_id,
                restore_components=args.components,
                dry_run=args.dry_run
            )
            
            if result.success:
                if args.dry_run:
                    print("✓ Dry run completed successfully")
                    print(f"  Would restore components: {', '.join(result.restored_components)}")
                else:
                    print("✓ Restore completed successfully")
                    print(f"  Restored components: {', '.join(result.restored_components)}")
                    print(f"  Duration: {result.duration_seconds:.2f} seconds")
                
                if result.warnings:
                    print("⚠ Warnings:")
                    for warning in result.warnings:
                        print(f"    {warning}")
            else:
                print(f"✗ Restore failed: {result.error_message}")
                return 1
            
            return 0
        
        except Exception as e:
            print(f"✗ Restore failed: {e}")
            return 1
    
    async def delete_backup(self, args):
        """Delete a backup."""
        try:
            if not args.force:
                response = input(f"Are you sure you want to delete backup '{args.backup_id}'? (y/N): ")
                if response.lower() != 'y':
                    print("Deletion cancelled.")
                    return 0
            
            success = await self.backup_manager.delete_backup(args.backup_id)
            
            if success:
                print(f"✓ Backup deleted: {args.backup_id}")
            else:
                print(f"✗ Failed to delete backup: {args.backup_id}")
                return 1
            
            return 0
        
        except Exception as e:
            print(f"✗ Backup deletion failed: {e}")
            return 1
    
    async def cleanup_backups(self, args):
        """Clean up old backups."""
        try:
            print("Cleaning up old backups...")
            
            removed_count = await self.backup_manager.cleanup_old_backups()
            
            print(f"✓ Cleanup completed: removed {removed_count} old backups")
            return 0
        
        except Exception as e:
            print(f"✗ Backup cleanup failed: {e}")
            return 1
    
    async def diagnose_failure(self, args):
        """Diagnose system failures."""
        try:
            print("Diagnosing system failures...")
            
            symptoms = args.symptoms if args.symptoms else None
            failure_scores = await self.recovery_manager.diagnose_failure(symptoms)
            
            if not failure_scores:
                print("No failures detected.")
                return 0
            
            print(f"Detected {len(failure_scores)} potential failure types:")
            print()
            
            for failure_type, confidence in failure_scores:
                print(f"  {failure_type.value}")
                print(f"    Confidence: {confidence:.2f}")
                
                scenario = self.recovery_manager.failure_scenarios.get(failure_type)
                if scenario:
                    print(f"    Description: {scenario.description}")
                    print(f"    Priority: {scenario.priority.value}")
                    print(f"    Estimated recovery time: {scenario.estimated_recovery_time_minutes} minutes")
                print()
            
            return 0
        
        except Exception as e:
            print(f"✗ Failure diagnosis failed: {e}")
            return 1
    
    async def recover_from_failure(self, args):
        """Execute recovery procedures."""
        try:
            failure_type = FailureType(args.failure_type)
            
            print(f"Executing recovery for: {failure_type.value}")
            
            # Create recovery plan
            plan = await self.recovery_manager.create_recovery_plan(failure_type)
            
            print(f"Recovery plan:")
            print(f"  Actions: {', '.join([action.value for action in plan.recovery_actions])}")
            print(f"  Estimated time: {plan.estimated_time_minutes} minutes")
            print(f"  Backup required: {plan.backup_required}")
            print(f"  Rollback required: {plan.rollback_required}")
            
            if plan.manual_steps:
                print(f"  Manual steps required: {len(plan.manual_steps)}")
            
            if not args.force:
                response = input("Proceed with recovery? (y/N): ")
                if response.lower() != 'y':
                    print("Recovery cancelled.")
                    return 0
            
            # Execute recovery
            result = await self.recovery_manager.execute_recovery(failure_type, plan)
            
            if result.success:
                print("✓ Recovery completed successfully")
                print(f"  Executed actions: {', '.join([action.value for action in result.recovery_actions_executed])}")
                print(f"  Duration: {result.duration_seconds:.2f} seconds")
                
                if result.manual_steps_required:
                    print("⚠ Manual steps required:")
                    for step in result.manual_steps_required:
                        print(f"    - {step}")
                
                if result.warnings:
                    print("⚠ Warnings:")
                    for warning in result.warnings:
                        print(f"    {warning}")
            else:
                print(f"✗ Recovery failed: {result.error_message}")
                return 1
            
            return 0
        
        except Exception as e:
            print(f"✗ Recovery execution failed: {e}")
            return 1
    
    async def create_rollback_point(self, args):
        """Create a rollback point."""
        try:
            print(f"Creating rollback point for version: {args.version}")
            
            rollback_point = await self.recovery_manager.create_rollback_point(
                deployment_version=args.version,
                description=args.description or ""
            )
            
            print(f"✓ Rollback point created: {rollback_point.rollback_id}")
            print(f"  Version: {rollback_point.deployment_version}")
            print(f"  Backup ID: {rollback_point.backup_id}")
            print(f"  Description: {rollback_point.description}")
            
            return 0
        
        except Exception as e:
            print(f"✗ Failed to create rollback point: {e}")
            return 1
    
    async def list_rollback_points(self, args):
        """List available rollback points."""
        try:
            rollback_points = await self.recovery_manager.list_rollback_points()
            
            if not rollback_points:
                print("No rollback points found.")
                return 0
            
            if args.json:
                print(json.dumps([point.model_dump() for point in rollback_points], indent=2, default=str))
            else:
                print(f"Available rollback points ({len(rollback_points)}):")
                print()
                
                for point in rollback_points:
                    print(f"  {point.rollback_id}")
                    print(f"    Version: {point.deployment_version}")
                    print(f"    Created: {point.timestamp}")
                    print(f"    Backup ID: {point.backup_id or 'none'}")
                    print(f"    Description: {point.description or 'none'}")
                    print()
            
            return 0
        
        except Exception as e:
            print(f"✗ Failed to list rollback points: {e}")
            return 1
    
    async def execute_rollback(self, args):
        """Execute rollback to a specific point."""
        try:
            print(f"Executing rollback to: {args.rollback_id}")
            
            if not args.force:
                response = input("Are you sure you want to rollback? This will stop the service and restore previous state. (y/N): ")
                if response.lower() != 'y':
                    print("Rollback cancelled.")
                    return 0
            
            success = await self.recovery_manager.execute_rollback(args.rollback_id)
            
            if success:
                print("✓ Rollback completed successfully")
                print("  Service has been restored to the previous state")
                print("  You may need to manually restart the service")
            else:
                print("✗ Rollback failed")
                return 1
            
            return 0
        
        except Exception as e:
            print(f"✗ Rollback execution failed: {e}")
            return 1
    
    async def schedule_backup(self, args):
        """Configure backup scheduling."""
        try:
            if args.enable:
                schedule = BackupSchedule(
                    enabled=True,
                    frequency_hours=args.frequency,
                    backup_type=BackupType(args.type),
                    max_backups_to_keep=args.keep,
                    include_logs=not args.no_logs,
                    max_log_size_mb=args.max_log_size
                )
                
                # Update backup manager configuration
                self.backup_manager.config.schedule = schedule
                
                print("✓ Backup scheduling enabled")
                print(f"  Frequency: every {args.frequency} hours")
                print(f"  Backup type: {args.type}")
                print(f"  Max backups to keep: {args.keep}")
                print(f"  Include logs: {not args.no_logs}")
            
            elif args.disable:
                self.backup_manager.config.schedule.enabled = False
                print("✓ Backup scheduling disabled")
            
            else:
                # Show current schedule
                schedule = self.backup_manager.config.schedule
                print(f"Backup scheduling status: {'enabled' if schedule.enabled else 'disabled'}")
                
                if schedule.enabled:
                    print(f"  Frequency: every {schedule.frequency_hours} hours")
                    print(f"  Backup type: {schedule.backup_type.value}")
                    print(f"  Max backups to keep: {schedule.max_backups_to_keep}")
                    print(f"  Include logs: {schedule.include_logs}")
                    print(f"  Next backup: {schedule.next_backup_time or 'not scheduled'}")
            
            return 0
        
        except Exception as e:
            print(f"✗ Backup scheduling failed: {e}")
            return 1


def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        description="Backup and recovery CLI for Thai Tokenizer on-premise deployment",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Backup commands
    backup_parser = subparsers.add_parser("backup", help="Backup operations")
    backup_subparsers = backup_parser.add_subparsers(dest="backup_command")
    
    # Create backup
    create_parser = backup_subparsers.add_parser("create", help="Create a backup")
    create_parser.add_argument("--type", choices=["full", "configuration", "dictionaries", "service_state", "logs"], 
                              default="full", help="Type of backup to create")
    create_parser.add_argument("--name", help="Custom backup name")
    create_parser.add_argument("--components", nargs="+", help="Specific components to backup")
    
    # List backups
    list_parser = backup_subparsers.add_parser("list", help="List available backups")
    list_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Restore backup
    restore_parser = backup_subparsers.add_parser("restore", help="Restore from backup")
    restore_parser.add_argument("backup_id", help="ID of backup to restore")
    restore_parser.add_argument("--components", nargs="+", help="Specific components to restore")
    restore_parser.add_argument("--dry-run", action="store_true", help="Show what would be restored")
    
    # Delete backup
    delete_parser = backup_subparsers.add_parser("delete", help="Delete a backup")
    delete_parser.add_argument("backup_id", help="ID of backup to delete")
    delete_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    
    # Cleanup backups
    cleanup_parser = backup_subparsers.add_parser("cleanup", help="Clean up old backups")
    
    # Schedule backup
    schedule_parser = backup_subparsers.add_parser("schedule", help="Configure backup scheduling")
    schedule_parser.add_argument("--enable", action="store_true", help="Enable scheduled backups")
    schedule_parser.add_argument("--disable", action="store_true", help="Disable scheduled backups")
    schedule_parser.add_argument("--frequency", type=int, default=24, help="Backup frequency in hours")
    schedule_parser.add_argument("--type", choices=["full", "configuration", "dictionaries"], 
                                default="full", help="Type of scheduled backup")
    schedule_parser.add_argument("--keep", type=int, default=10, help="Number of backups to keep")
    schedule_parser.add_argument("--no-logs", action="store_true", help="Exclude logs from scheduled backups")
    schedule_parser.add_argument("--max-log-size", type=int, default=100, help="Maximum log size in MB")
    
    # Recovery commands
    recovery_parser = subparsers.add_parser("recovery", help="Recovery operations")
    recovery_subparsers = recovery_parser.add_subparsers(dest="recovery_command")
    
    # Diagnose failure
    diagnose_parser = recovery_subparsers.add_parser("diagnose", help="Diagnose system failures")
    diagnose_parser.add_argument("--symptoms", nargs="+", help="Observed symptoms")
    
    # Recover from failure
    recover_parser = recovery_subparsers.add_parser("recover", help="Execute recovery procedures")
    recover_parser.add_argument("failure_type", choices=[ft.value for ft in FailureType], 
                               help="Type of failure to recover from")
    recover_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    
    # Rollback commands
    rollback_parser = subparsers.add_parser("rollback", help="Rollback operations")
    rollback_subparsers = rollback_parser.add_subparsers(dest="rollback_command")
    
    # Create rollback point
    create_rollback_parser = rollback_subparsers.add_parser("create", help="Create rollback point")
    create_rollback_parser.add_argument("version", help="Deployment version")
    create_rollback_parser.add_argument("--description", help="Description of rollback point")
    
    # List rollback points
    list_rollback_parser = rollback_subparsers.add_parser("list", help="List rollback points")
    list_rollback_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Execute rollback
    execute_rollback_parser = rollback_subparsers.add_parser("execute", help="Execute rollback")
    execute_rollback_parser.add_argument("rollback_id", help="ID of rollback point")
    execute_rollback_parser.add_argument("--force", action="store_true", help="Skip confirmation")
    
    return parser


async def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Initialize CLI
        cli = BackupCLI()
        await cli.initialize_managers(args.config)
        
        # Execute command
        if args.command == "backup":
            if args.backup_command == "create":
                return await cli.create_backup(args)
            elif args.backup_command == "list":
                return await cli.list_backups(args)
            elif args.backup_command == "restore":
                return await cli.restore_backup(args)
            elif args.backup_command == "delete":
                return await cli.delete_backup(args)
            elif args.backup_command == "cleanup":
                return await cli.cleanup_backups(args)
            elif args.backup_command == "schedule":
                return await cli.schedule_backup(args)
        
        elif args.command == "recovery":
            if args.recovery_command == "diagnose":
                return await cli.diagnose_failure(args)
            elif args.recovery_command == "recover":
                return await cli.recover_from_failure(args)
        
        elif args.command == "rollback":
            if args.rollback_command == "create":
                return await cli.create_rollback_point(args)
            elif args.rollback_command == "list":
                return await cli.list_rollback_points(args)
            elif args.rollback_command == "execute":
                return await cli.execute_rollback(args)
        
        parser.print_help()
        return 1
    
    except KeyboardInterrupt:
        print("\nOperation interrupted by user")
        return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))