#!/usr/bin/env python3
"""
Complete setup script for Thai Tokenizer standalone deployment.

This script orchestrates the entire setup process including virtual environment
creation, dependency installation, configuration, and service setup.
"""

import os
import sys
import argparse
import logging
import asyncio
from pathlib import Path
from typing import Optional

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from utils.logging import get_structured_logger
except ImportError:
    # Fallback logging if imports fail
    logging.basicConfig(level=logging.INFO)
    def get_structured_logger(name):
        return logging.getLogger(name)

# Import our setup modules
try:
    from .setup_venv import VirtualEnvironmentManager
    from .install_dependencies import DependencyInstaller
    from .configure_service import StandaloneConfigurationManager
except ImportError:
    # Fallback for direct execution
    import importlib.util
    
    def load_module_from_path(name, path):
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    
    script_dir = Path(__file__).parent
    setup_venv_module = load_module_from_path("setup_venv", script_dir / "setup-venv.py")
    install_deps_module = load_module_from_path("install_dependencies", script_dir / "install-dependencies.py")
    configure_module = load_module_from_path("configure_service", script_dir / "configure-service.py")
    
    VirtualEnvironmentManager = setup_venv_module.VirtualEnvironmentManager
    DependencyInstaller = install_deps_module.DependencyInstaller
    StandaloneConfigurationManager = configure_module.StandaloneConfigurationManager

logger = get_structured_logger(__name__)


class StandaloneSetupOrchestrator:
    """Orchestrates the complete standalone deployment setup."""
    
    def __init__(self, install_path: str, config_file: Optional[str] = None):
        """
        Initialize setup orchestrator.
        
        Args:
            install_path: Installation directory path
            config_file: Optional path to configuration file
        """
        self.install_path = Path(install_path)
        self.config_file = Path(config_file) if config_file else None
        self.logger = get_structured_logger(f"{__name__}.StandaloneSetupOrchestrator")
    
    def setup_virtual_environment(self, python_executable: Optional[str] = None) -> bool:
        """
        Set up Python virtual environment.
        
        Args:
            python_executable: Optional specific Python executable
            
        Returns:
            True if setup was successful
        """
        try:
            self.logger.info("Setting up virtual environment...")
            
            venv_manager = VirtualEnvironmentManager(
                install_path=str(self.install_path),
                python_executable=python_executable
            )
            
            return venv_manager.setup_complete_environment()
            
        except Exception as e:
            self.logger.error(f"Virtual environment setup failed: {e}")
            return False
    
    def install_dependencies(self, use_uv: bool = True) -> bool:
        """
        Install project dependencies.
        
        Args:
            use_uv: Whether to use uv package manager
            
        Returns:
            True if installation was successful
        """
        try:
            self.logger.info("Installing dependencies...")
            
            venv_path = self.install_path / "venv"
            
            installer = DependencyInstaller(
                venv_path=str(venv_path),
                project_root=str(self.install_path.parent.parent)
            )
            
            return installer.install_all_dependencies(use_uv=use_uv)
            
        except Exception as e:
            self.logger.error(f"Dependency installation failed: {e}")
            return False
    
    def configure_service(self) -> bool:
        """
        Configure the service.
        
        Returns:
            True if configuration was successful
        """
        try:
            self.logger.info("Configuring service...")
            
            config_manager = StandaloneConfigurationManager(str(self.install_path))
            
            return config_manager.setup_complete_configuration(self.config_file)
            
        except Exception as e:
            self.logger.error(f"Service configuration failed: {e}")
            return False
    
    def validate_setup(self) -> bool:
        """
        Validate the complete setup.
        
        Returns:
            True if validation was successful
        """
        try:
            self.logger.info("Validating setup...")
            
            # Check virtual environment
            venv_python = self.install_path / "venv" / "bin" / "python"
            if os.name == 'nt':
                venv_python = self.install_path / "venv" / "Scripts" / "python.exe"
            
            if not venv_python.exists():
                self.logger.error(f"Virtual environment Python not found: {venv_python}")
                return False
            
            # Check configuration files
            config_file = self.install_path / "config" / "config.json"
            if not config_file.exists():
                self.logger.error(f"Configuration file not found: {config_file}")
                return False
            
            # Check service scripts
            start_script = self.install_path / "bin" / "start-service.sh"
            if os.name == 'nt':
                start_script = start_script.with_suffix('.bat')
            
            if not start_script.exists():
                self.logger.error(f"Start script not found: {start_script}")
                return False
            
            self.logger.info("Setup validation passed")
            return True
            
        except Exception as e:
            self.logger.error(f"Setup validation failed: {e}")
            return False
    
    def create_setup_summary(self) -> bool:
        """
        Create setup summary and instructions.
        
        Returns:
            True if summary was created successfully
        """
        try:
            summary_file = self.install_path / "SETUP_SUMMARY.md"
            
            summary_content = f"""# Thai Tokenizer Standalone Deployment Setup Summary

## Installation Details

- **Installation Path**: {self.install_path}
- **Virtual Environment**: {self.install_path / "venv"}
- **Configuration**: {self.install_path / "config"}
- **Logs**: {self.install_path / "logs"}
- **Service Scripts**: {self.install_path / "bin"}

## Service Management

### Start Service
```bash
{self.install_path / "bin" / "start-service.sh"}
```

### Stop Service
```bash
python3 {Path(__file__).parent / "manage-service.py"} --install-path {self.install_path} stop
```

### Check Status
```bash
python3 {Path(__file__).parent / "manage-service.py"} --install-path {self.install_path} status
```

### View Logs
```bash
python3 {Path(__file__).parent / "manage-service.py"} --install-path {self.install_path} logs
```

## Configuration

The service configuration is located at:
- Main config: `{self.install_path / "config" / "config.json"}`
- Environment: `{self.install_path / "config" / ".env"}`

To modify the configuration:
1. Edit the configuration files
2. Restart the service

## Health Check

Once the service is running, you can check its health at:
- Health endpoint: `http://localhost:8000/health`
- API documentation: `http://localhost:8000/docs`

## Troubleshooting

### Service Won't Start
1. Check the logs: `tail -f {self.install_path / "logs" / "thai-tokenizer.log"}`
2. Verify configuration: `cat {self.install_path / "config" / "config.json"}`
3. Test Meilisearch connection manually

### Performance Issues
1. Monitor resource usage: `python3 {Path(__file__).parent / "manage-service.py"} --install-path {self.install_path} monitor`
2. Adjust worker processes in configuration
3. Check memory and CPU limits

### Configuration Changes
1. Stop the service
2. Edit configuration files
3. Restart the service

## Next Steps

1. **Configure Meilisearch Connection**: Edit `{self.install_path / "config" / "config.json"}` with your Meilisearch server details
2. **Start the Service**: Run the start script
3. **Test the Service**: Access the health endpoint and API documentation
4. **Set up Monitoring**: Configure log rotation and monitoring as needed

## Support

For issues and support:
- Check the logs in `{self.install_path / "logs"}/`
- Review the configuration in `{self.install_path / "config"}/`
- Consult the project documentation
"""
            
            with open(summary_file, 'w') as f:
                f.write(summary_content)
            
            self.logger.info(f"Setup summary created: {summary_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create setup summary: {e}")
            return False
    
    def run_complete_setup(self, python_executable: Optional[str] = None, use_uv: bool = True) -> bool:
        """
        Run the complete setup process.
        
        Args:
            python_executable: Optional specific Python executable
            use_uv: Whether to use uv package manager
            
        Returns:
            True if setup was successful
        """
        self.logger.info(f"Starting complete standalone setup at {self.install_path}")
        
        # Step 1: Set up virtual environment
        if not self.setup_virtual_environment(python_executable):
            self.logger.error("Virtual environment setup failed")
            return False
        
        # Step 2: Install dependencies
        if not self.install_dependencies(use_uv):
            self.logger.error("Dependency installation failed")
            return False
        
        # Step 3: Configure service
        if not self.configure_service():
            self.logger.error("Service configuration failed")
            return False
        
        # Step 4: Validate setup
        if not self.validate_setup():
            self.logger.error("Setup validation failed")
            return False
        
        # Step 5: Create setup summary
        if not self.create_setup_summary():
            self.logger.warning("Failed to create setup summary")
        
        self.logger.info("Complete standalone setup completed successfully!")
        self.logger.info(f"Next steps:")
        self.logger.info(f"1. Configure Meilisearch connection in {self.install_path / 'config' / 'config.json'}")
        self.logger.info(f"2. Start the service: {self.install_path / 'bin' / 'start-service.sh'}")
        self.logger.info(f"3. Check status: python3 {Path(__file__).parent / 'manage-service.py'} --install-path {self.install_path} status")
        
        return True


def main():
    """Main entry point for complete standalone setup."""
    parser = argparse.ArgumentParser(
        description="Complete setup for Thai Tokenizer standalone deployment"
    )
    
    parser.add_argument(
        "--install-path",
        required=True,
        help="Installation directory path"
    )
    
    parser.add_argument(
        "--config-file",
        help="Path to existing configuration file"
    )
    
    parser.add_argument(
        "--python",
        help="Python executable to use (default: current Python)"
    )
    
    parser.add_argument(
        "--no-uv",
        action="store_true",
        help="Don't use uv package manager, use pip instead"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create setup orchestrator
        orchestrator = StandaloneSetupOrchestrator(
            install_path=args.install_path,
            config_file=args.config_file
        )
        
        # Run complete setup
        success = orchestrator.run_complete_setup(
            python_executable=args.python,
            use_uv=not args.no_uv
        )
        
        if success:
            logger.info("Standalone deployment setup completed successfully")
            sys.exit(0)
        else:
            logger.error("Standalone deployment setup failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()