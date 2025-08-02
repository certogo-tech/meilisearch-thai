#!/usr/bin/env python3
"""
Systemd service installation script for Thai Tokenizer.

This script provides a comprehensive installation process for deploying
the Thai Tokenizer service as a systemd service with proper user management,
security configuration, and system integration.
"""

import os
import sys
import argparse
import asyncio
from pathlib import Path
from typing import Optional

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.deployment.config import OnPremiseConfig, DeploymentMethod, ValidationResult
    from src.deployment.templates import DeploymentTemplates, ConfigurationExporter
    from src.deployment.systemd_manager import (
        SystemdUserManager,
        SystemdServiceGenerator,
        SystemdServiceManager,
        SystemdDeploymentValidator
    )
    from src.utils.logging import get_structured_logger
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Please ensure you're running this script from the project root directory")
    sys.exit(1)

logger = get_structured_logger(__name__)


class SystemdInstaller:
    """Main installer class for systemd deployment."""
    
    def __init__(self, config: OnPremiseConfig):
        """Initialize with deployment configuration."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.SystemdInstaller")
        
        # Initialize managers
        self.user_manager = SystemdUserManager(config)
        self.service_generator = SystemdServiceGenerator(config)
        self.service_manager = SystemdServiceManager(config.service_config.service_name)
        self.validator = SystemdDeploymentValidator(config)
    
    async def install(self, skip_validation: bool = False) -> ValidationResult:
        """
        Perform complete systemd installation.
        
        Args:
            skip_validation: Skip pre-installation validation
            
        Returns:
            ValidationResult with installation details
        """
        result = ValidationResult(valid=True)
        
        try:
            # Step 1: Validate system requirements
            if not skip_validation:
                self.logger.info("Validating system requirements...")
                validation_result = self.validator.validate_system_requirements()
                result.errors.extend(validation_result.errors)
                result.warnings.extend(validation_result.warnings)
                
                if not validation_result.valid:
                    result.valid = False
                    self.logger.error("System validation failed")
                    return result
                
                # Validate service dependencies
                deps_result = self.validator.validate_service_dependencies()
                result.warnings.extend(deps_result.warnings)
            
            # Step 2: Create system user and group
            self.logger.info("Creating system user and group...")
            user_result = self.user_manager.create_user(
                self.config.service_config.service_user,
                self.config.service_config.service_group,
                self.config.data_path
            )
            result.errors.extend(user_result.errors)
            result.warnings.extend(user_result.warnings)
            
            if not user_result.valid:
                result.valid = False
                self.logger.error("User creation failed")
                return result
            
            # Step 3: Set up directories
            self.logger.info("Setting up directories...")
            dirs_result = self.user_manager.setup_directories(
                self.config.service_config.service_user,
                self.config.service_config.service_group
            )
            result.errors.extend(dirs_result.errors)
            result.warnings.extend(dirs_result.warnings)
            
            if not dirs_result.valid:
                result.valid = False
                self.logger.error("Directory setup failed")
                return result
            
            # Step 4: Generate service files
            self.logger.info("Generating systemd service files...")
            
            # Generate service file
            template_path = project_root / "deployment" / "systemd" / "thai-tokenizer.service.template"
            service_file_path = f"/tmp/{self.config.service_config.service_name}.service"
            
            service_result = self.service_generator.generate_service_file(
                str(template_path),
                service_file_path
            )
            result.errors.extend(service_result.errors)
            result.warnings.extend(service_result.warnings)
            
            if not service_result.valid:
                result.valid = False
                self.logger.error("Service file generation failed")
                return result
            
            # Generate environment file
            env_file_path = f"{self.config.config_path}/environment"
            env_result = self.service_generator.generate_environment_file(env_file_path)
            result.errors.extend(env_result.errors)
            result.warnings.extend(env_result.warnings)
            
            if not env_result.valid:
                result.valid = False
                self.logger.error("Environment file generation failed")
                return result
            
            # Step 5: Install systemd service
            self.logger.info("Installing systemd service...")
            install_result = self.service_manager.install_service(service_file_path)
            result.errors.extend(install_result.errors)
            result.warnings.extend(install_result.warnings)
            
            if not install_result.valid:
                result.valid = False
                self.logger.error("Service installation failed")
                return result
            
            # Step 6: Enable service for automatic startup
            self.logger.info("Enabling service for automatic startup...")
            enable_result = self.service_manager.enable_service()
            result.errors.extend(enable_result.errors)
            result.warnings.extend(enable_result.warnings)
            
            if not enable_result.valid:
                result.valid = False
                self.logger.error("Service enable failed")
                return result
            
            # Step 7: Generate additional configuration files
            self.logger.info("Generating additional configuration files...")
            
            # Generate logrotate configuration
            logrotate_content = ConfigurationExporter.to_logrotate_config(self.config)
            logrotate_path = f"/etc/logrotate.d/{self.config.service_config.service_name}"
            
            try:
                Path(logrotate_path).write_text(logrotate_content, encoding="utf-8")
                Path(logrotate_path).chmod(0o644)
                result.warnings.append(f"Created logrotate configuration: {logrotate_path}")
            except Exception as e:
                result.warnings.append(f"Could not create logrotate config: {e}")
            
            # Generate environment file for reference
            env_content = ConfigurationExporter.to_env_file(self.config)
            env_reference_path = f"{self.config.config_path}/environment.example"
            
            try:
                Path(env_reference_path).write_text(env_content, encoding="utf-8")
                Path(env_reference_path).chmod(0o644)
                result.warnings.append(f"Created environment reference: {env_reference_path}")
            except Exception as e:
                result.warnings.append(f"Could not create environment reference: {e}")
            
            # Clean up temporary files
            try:
                Path(service_file_path).unlink()
            except Exception:
                pass
            
            self.logger.info("Systemd installation completed successfully")
            result.warnings.append("Installation completed successfully")
            result.warnings.append(f"Service can be started with: systemctl start {self.config.service_config.service_name}")
            result.warnings.append(f"Service logs can be viewed with: journalctl -u {self.config.service_config.service_name} -f")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Installation failed with unexpected error: {e}")
            self.logger.error(f"Installation failed: {e}")
        
        return result
    
    async def uninstall(self) -> ValidationResult:
        """
        Uninstall systemd service and clean up.
        
        Returns:
            ValidationResult with uninstallation details
        """
        result = ValidationResult(valid=True)
        
        try:
            # Stop service if running
            self.logger.info("Stopping service...")
            stop_result = self.service_manager.stop_service()
            result.warnings.extend(stop_result.warnings)
            
            # Disable service
            self.logger.info("Disabling service...")
            try:
                import subprocess
                subprocess.run(
                    ["systemctl", "disable", self.config.service_config.service_name],
                    check=True,
                    capture_output=True
                )
                result.warnings.append(f"Disabled service: {self.config.service_config.service_name}")
            except subprocess.CalledProcessError as e:
                result.warnings.append(f"Could not disable service: {e.stderr}")
            
            # Remove service file
            service_file_path = f"/etc/systemd/system/{self.config.service_config.service_name}.service"
            try:
                Path(service_file_path).unlink()
                result.warnings.append(f"Removed service file: {service_file_path}")
            except FileNotFoundError:
                result.warnings.append("Service file was not found")
            except Exception as e:
                result.errors.append(f"Could not remove service file: {e}")
            
            # Remove logrotate configuration
            logrotate_path = f"/etc/logrotate.d/{self.config.service_config.service_name}"
            try:
                Path(logrotate_path).unlink()
                result.warnings.append(f"Removed logrotate config: {logrotate_path}")
            except FileNotFoundError:
                result.warnings.append("Logrotate config was not found")
            except Exception as e:
                result.warnings.append(f"Could not remove logrotate config: {e}")
            
            # Reload systemd daemon
            try:
                import subprocess
                subprocess.run(["systemctl", "daemon-reload"], check=True, capture_output=True)
                result.warnings.append("Reloaded systemd daemon")
            except Exception as e:
                result.warnings.append(f"Could not reload systemd daemon: {e}")
            
            self.logger.info("Systemd uninstallation completed")
            result.warnings.append("Uninstallation completed")
            result.warnings.append("Note: User, group, and data directories were not removed")
            
        except Exception as e:
            result.valid = False
            result.errors.append(f"Uninstallation failed: {e}")
            self.logger.error(f"Uninstallation failed: {e}")
        
        return result


def create_config_from_args(args) -> OnPremiseConfig:
    """Create configuration from command line arguments."""
    return DeploymentTemplates.create_systemd_template(
        meilisearch_host=args.meilisearch_host,
        meilisearch_api_key=args.meilisearch_api_key,
        service_port=args.port,
        installation_path=args.installation_path
    )


async def main():
    """Main installation function."""
    parser = argparse.ArgumentParser(
        description="Install Thai Tokenizer as systemd service",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic installation
  sudo python3 install-systemd-service.py \\
    --meilisearch-host http://localhost:7700 \\
    --meilisearch-api-key your-api-key

  # Custom installation path and port
  sudo python3 install-systemd-service.py \\
    --meilisearch-host https://meilisearch.example.com \\
    --meilisearch-api-key your-api-key \\
    --port 8080 \\
    --installation-path /opt/custom/thai-tokenizer

  # Uninstall service
  sudo python3 install-systemd-service.py --uninstall
        """
    )
    
    parser.add_argument(
        "--meilisearch-host",
        required=False,
        help="Meilisearch server host URL (e.g., http://localhost:7700)"
    )
    
    parser.add_argument(
        "--meilisearch-api-key",
        required=False,
        help="Meilisearch API key for authentication"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for Thai Tokenizer service (default: 8000)"
    )
    
    parser.add_argument(
        "--installation-path",
        default="/opt/thai-tokenizer",
        help="Installation directory path (default: /opt/thai-tokenizer)"
    )
    
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip pre-installation validation checks"
    )
    
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall the systemd service"
    )
    
    parser.add_argument(
        "--config-file",
        help="Path to configuration file (JSON format)"
    )
    
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without making changes"
    )
    
    args = parser.parse_args()
    
    # Check if running as root
    if os.geteuid() != 0:
        print("Error: This script must be run as root (use sudo)")
        sys.exit(1)
    
    try:
        # Load configuration
        if args.config_file:
            import json
            with open(args.config_file, 'r') as f:
                config_data = json.load(f)
            config = OnPremiseConfig(**config_data)
        elif args.uninstall:
            # For uninstall, we need minimal config
            config = DeploymentTemplates.create_systemd_template(
                meilisearch_host="http://localhost:7700",
                meilisearch_api_key="dummy"
            )
        else:
            if not args.meilisearch_host or not args.meilisearch_api_key:
                print("Error: --meilisearch-host and --meilisearch-api-key are required")
                parser.print_help()
                sys.exit(1)
            
            config = create_config_from_args(args)
        
        # Initialize installer
        installer = SystemdInstaller(config)
        
        if args.dry_run:
            print("DRY RUN MODE - No changes will be made")
            print(f"Configuration:")
            print(f"  Service name: {config.service_config.service_name}")
            print(f"  Service user: {config.service_config.service_user}")
            print(f"  Installation path: {config.installation_path}")
            print(f"  Service port: {config.service_config.service_port}")
            print(f"  Meilisearch host: {config.meilisearch_config.host}")
            return
        
        # Perform installation or uninstallation
        if args.uninstall:
            print("Uninstalling Thai Tokenizer systemd service...")
            result = await installer.uninstall()
        else:
            print("Installing Thai Tokenizer systemd service...")
            result = await installer.install(skip_validation=args.skip_validation)
        
        # Display results
        if result.valid:
            print("✅ Operation completed successfully!")
        else:
            print("❌ Operation failed!")
        
        if result.warnings:
            print("\nInfo:")
            for warning in result.warnings:
                print(f"  ℹ️  {warning}")
        
        if result.errors:
            print("\nErrors:")
            for error in result.errors:
                print(f"  ❌ {error}")
        
        # Exit with appropriate code
        sys.exit(0 if result.valid else 1)
        
    except KeyboardInterrupt:
        print("\nInstallation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"Installation failed with unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())