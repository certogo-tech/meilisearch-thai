#!/usr/bin/env python3
"""
Virtual environment setup script for standalone Thai Tokenizer deployment.

This script creates and manages Python virtual environments for the Thai Tokenizer
service, providing isolation and dependency management for standalone deployment.
"""

import os
import sys
import shutil
import subprocess
import argparse
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import json
import venv

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from deployment.config import OnPremiseConfig, DeploymentMethod
    from utils.logging import get_structured_logger
except ImportError:
    # Fallback logging if imports fail
    logging.basicConfig(level=logging.INFO)
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class VirtualEnvironmentManager:
    """Manages Python virtual environments for standalone deployment."""
    
    def __init__(self, install_path: str, python_executable: Optional[str] = None):
        """
        Initialize virtual environment manager.
        
        Args:
            install_path: Base installation directory
            python_executable: Specific Python executable to use
        """
        self.install_path = Path(install_path)
        self.venv_path = self.install_path / "venv"
        self.python_executable = python_executable or sys.executable
        self.logger = get_structured_logger(f"{__name__}.VirtualEnvironmentManager")
    
    def validate_python_version(self) -> bool:
        """
        Validate that Python version meets requirements.
        
        Returns:
            True if Python version is compatible
        """
        try:
            result = subprocess.run(
                [self.python_executable, "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            
            version_str = result.stdout.strip()
            self.logger.info(f"Python version: {version_str}")
            
            # Extract version numbers
            version_parts = version_str.split()[1].split(".")
            major, minor = int(version_parts[0]), int(version_parts[1])
            
            if major < 3 or (major == 3 and minor < 12):
                self.logger.error(f"Python 3.12+ required, found {major}.{minor}")
                return False
            
            return True
            
        except (subprocess.CalledProcessError, ValueError, IndexError) as e:
            self.logger.error(f"Failed to validate Python version: {e}")
            return False
    
    def check_uv_availability(self) -> bool:
        """
        Check if uv package manager is available.
        
        Returns:
            True if uv is available
        """
        try:
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            
            version_str = result.stdout.strip()
            self.logger.info(f"uv version: {version_str}")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("uv package manager not found")
            return False
    
    def create_directories(self) -> bool:
        """
        Create necessary directories for installation.
        
        Returns:
            True if directories were created successfully
        """
        try:
            directories = [
                self.install_path,
                self.install_path / "bin",
                self.install_path / "config",
                self.install_path / "logs",
                self.install_path / "data",
                self.install_path / "run",
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                self.logger.info(f"Created directory: {directory}")
            
            return True
            
        except PermissionError as e:
            self.logger.error(f"Permission denied creating directories: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to create directories: {e}")
            return False
    
    def create_virtual_environment(self) -> bool:
        """
        Create Python virtual environment.
        
        Returns:
            True if virtual environment was created successfully
        """
        try:
            if self.venv_path.exists():
                self.logger.info(f"Virtual environment already exists at {self.venv_path}")
                return True
            
            self.logger.info(f"Creating virtual environment at {self.venv_path}")
            
            # Create virtual environment
            venv.create(
                self.venv_path,
                system_site_packages=False,
                clear=False,
                symlinks=True,
                with_pip=True
            )
            
            # Verify virtual environment
            venv_python = self.get_venv_python()
            if not venv_python.exists():
                self.logger.error(f"Virtual environment Python not found: {venv_python}")
                return False
            
            # Test virtual environment
            result = subprocess.run(
                [str(venv_python), "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            
            self.logger.info(f"Virtual environment created successfully: {result.stdout.strip()}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create virtual environment: {e}")
            return False
    
    def get_venv_python(self) -> Path:
        """Get path to Python executable in virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "python.exe"
        else:  # Unix-like
            return self.venv_path / "bin" / "python"
    
    def get_venv_pip(self) -> Path:
        """Get path to pip executable in virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "pip.exe"
        else:  # Unix-like
            return self.venv_path / "bin" / "pip"
    
    def upgrade_pip(self) -> bool:
        """
        Upgrade pip in virtual environment.
        
        Returns:
            True if pip was upgraded successfully
        """
        try:
            venv_python = self.get_venv_python()
            
            self.logger.info("Upgrading pip in virtual environment")
            
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
                capture_output=True,
                text=True,
                check=True
            )
            
            self.logger.info("pip upgraded successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to upgrade pip: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to upgrade pip: {e}")
            return False
    
    def install_uv_in_venv(self) -> bool:
        """
        Install uv package manager in virtual environment.
        
        Returns:
            True if uv was installed successfully
        """
        try:
            venv_python = self.get_venv_python()
            
            self.logger.info("Installing uv in virtual environment")
            
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "install", "uv"],
                capture_output=True,
                text=True,
                check=True
            )
            
            self.logger.info("uv installed successfully in virtual environment")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install uv: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to install uv: {e}")
            return False
    
    def create_activation_script(self) -> bool:
        """
        Create convenience activation script.
        
        Returns:
            True if activation script was created successfully
        """
        try:
            script_path = self.install_path / "bin" / "activate-thai-tokenizer"
            
            if os.name == 'nt':  # Windows
                activate_script = self.venv_path / "Scripts" / "activate.bat"
                script_content = f"""@echo off
echo Activating Thai Tokenizer virtual environment...
call "{activate_script}"
echo Virtual environment activated. Python: %VIRTUAL_ENV%\\Scripts\\python.exe
"""
            else:  # Unix-like
                activate_script = self.venv_path / "bin" / "activate"
                script_content = f"""#!/bin/bash
echo "Activating Thai Tokenizer virtual environment..."
source "{activate_script}"
echo "Virtual environment activated. Python: $VIRTUAL_ENV/bin/python"
"""
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make executable on Unix-like systems
            if os.name != 'nt':
                script_path.chmod(0o755)
            
            self.logger.info(f"Created activation script: {script_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create activation script: {e}")
            return False
    
    def create_environment_info(self) -> bool:
        """
        Create environment information file.
        
        Returns:
            True if environment info was created successfully
        """
        try:
            info_path = self.install_path / "venv-info.json"
            
            venv_python = self.get_venv_python()
            
            # Get Python version in venv
            result = subprocess.run(
                [str(venv_python), "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            python_version = result.stdout.strip()
            
            # Get pip version
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            pip_version = result.stdout.strip()
            
            info = {
                "created_at": str(Path(__file__).stat().st_mtime),
                "install_path": str(self.install_path),
                "venv_path": str(self.venv_path),
                "python_executable": str(venv_python),
                "python_version": python_version,
                "pip_version": pip_version,
                "system_python": self.python_executable,
            }
            
            with open(info_path, 'w') as f:
                json.dump(info, f, indent=2)
            
            self.logger.info(f"Created environment info: {info_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create environment info: {e}")
            return False
    
    def setup_complete_environment(self) -> bool:
        """
        Set up complete virtual environment for Thai Tokenizer.
        
        Returns:
            True if setup was successful
        """
        self.logger.info(f"Setting up Thai Tokenizer virtual environment at {self.install_path}")
        
        # Validate Python version
        if not self.validate_python_version():
            return False
        
        # Create directories
        if not self.create_directories():
            return False
        
        # Create virtual environment
        if not self.create_virtual_environment():
            return False
        
        # Upgrade pip
        if not self.upgrade_pip():
            return False
        
        # Install uv if not available system-wide
        if not self.check_uv_availability():
            if not self.install_uv_in_venv():
                return False
        
        # Create activation script
        if not self.create_activation_script():
            return False
        
        # Create environment info
        if not self.create_environment_info():
            return False
        
        self.logger.info("Virtual environment setup completed successfully")
        return True
    
    def remove_environment(self) -> bool:
        """
        Remove virtual environment and associated files.
        
        Returns:
            True if removal was successful
        """
        try:
            if self.venv_path.exists():
                self.logger.info(f"Removing virtual environment: {self.venv_path}")
                shutil.rmtree(self.venv_path)
            
            # Remove activation script
            activation_script = self.install_path / "bin" / "activate-thai-tokenizer"
            if activation_script.exists():
                activation_script.unlink()
            
            # Remove environment info
            info_file = self.install_path / "venv-info.json"
            if info_file.exists():
                info_file.unlink()
            
            self.logger.info("Virtual environment removed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to remove virtual environment: {e}")
            return False


def main():
    """Main entry point for virtual environment setup."""
    parser = argparse.ArgumentParser(
        description="Set up Python virtual environment for Thai Tokenizer standalone deployment"
    )
    
    parser.add_argument(
        "--install-path",
        required=True,
        help="Installation directory path"
    )
    
    parser.add_argument(
        "--python",
        help="Python executable to use (default: current Python)"
    )
    
    parser.add_argument(
        "--remove",
        action="store_true",
        help="Remove existing virtual environment"
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
    
    # Create virtual environment manager
    venv_manager = VirtualEnvironmentManager(
        install_path=args.install_path,
        python_executable=args.python
    )
    
    try:
        if args.remove:
            success = venv_manager.remove_environment()
        else:
            success = venv_manager.setup_complete_environment()
        
        if success:
            logger.info("Virtual environment setup completed successfully")
            sys.exit(0)
        else:
            logger.error("Virtual environment setup failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()