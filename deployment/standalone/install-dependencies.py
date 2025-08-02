#!/usr/bin/env python3
"""
Dependency installation script for standalone Thai Tokenizer deployment.

This script manages dependency installation using the uv package manager,
providing fast and reliable dependency resolution for the Thai Tokenizer service.
"""

import os
import sys
import subprocess
import argparse
import logging
import json
from pathlib import Path
from typing import List, Optional, Dict, Any

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


class DependencyInstaller:
    """Manages dependency installation for standalone deployment."""
    
    def __init__(self, venv_path: str, project_root: Optional[str] = None):
        """
        Initialize dependency installer.
        
        Args:
            venv_path: Path to virtual environment
            project_root: Path to project root (default: auto-detect)
        """
        self.venv_path = Path(venv_path)
        self.project_root = Path(project_root) if project_root else self._detect_project_root()
        self.logger = get_structured_logger(f"{__name__}.DependencyInstaller")
        
        # Validate paths
        if not self.venv_path.exists():
            raise ValueError(f"Virtual environment not found: {self.venv_path}")
        
        if not self.project_root.exists():
            raise ValueError(f"Project root not found: {self.project_root}")
    
    def _detect_project_root(self) -> Path:
        """Auto-detect project root directory."""
        current = Path(__file__).parent
        
        # Look for project indicators
        indicators = ["requirements.txt", "pyproject.toml", "src", ".git"]
        
        while current != current.parent:
            if any((current / indicator).exists() for indicator in indicators):
                return current
            current = current.parent
        
        # Fallback to script's grandparent directory
        return Path(__file__).parent.parent.parent
    
    def get_venv_python(self) -> Path:
        """Get path to Python executable in virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "python.exe"
        else:  # Unix-like
            return self.venv_path / "bin" / "python"
    
    def get_venv_uv(self) -> Path:
        """Get path to uv executable in virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "uv.exe"
        else:  # Unix-like
            return self.venv_path / "bin" / "uv"
    
    def check_uv_availability(self) -> bool:
        """
        Check if uv is available in virtual environment.
        
        Returns:
            True if uv is available
        """
        try:
            venv_uv = self.get_venv_uv()
            
            if venv_uv.exists():
                result = subprocess.run(
                    [str(venv_uv), "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.logger.info(f"uv available in venv: {result.stdout.strip()}")
                return True
            
            # Try system uv
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                check=True
            )
            self.logger.info(f"uv available system-wide: {result.stdout.strip()}")
            return True
            
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.logger.warning("uv not available")
            return False
    
    def install_uv(self) -> bool:
        """
        Install uv package manager in virtual environment.
        
        Returns:
            True if uv was installed successfully
        """
        try:
            venv_python = self.get_venv_python()
            
            self.logger.info("Installing uv package manager")
            
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "install", "uv"],
                capture_output=True,
                text=True,
                check=True
            )
            
            self.logger.info("uv installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install uv: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to install uv: {e}")
            return False
    
    def get_requirements_files(self) -> List[Path]:
        """
        Get list of requirements files to install.
        
        Returns:
            List of requirements file paths
        """
        requirements_files = []
        
        # Main requirements.txt
        main_req = self.project_root / "requirements.txt"
        if main_req.exists():
            requirements_files.append(main_req)
        
        # Development requirements (optional)
        dev_req = self.project_root / "requirements-dev.txt"
        if dev_req.exists():
            requirements_files.append(dev_req)
        
        # Production requirements (optional)
        prod_req = self.project_root / "requirements-prod.txt"
        if prod_req.exists():
            requirements_files.append(prod_req)
        
        return requirements_files
    
    def install_requirements_with_uv(self, requirements_file: Path) -> bool:
        """
        Install requirements using uv package manager.
        
        Args:
            requirements_file: Path to requirements file
            
        Returns:
            True if installation was successful
        """
        try:
            # Try venv uv first, then system uv
            venv_uv = self.get_venv_uv()
            uv_cmd = str(venv_uv) if venv_uv.exists() else "uv"
            
            self.logger.info(f"Installing requirements from {requirements_file} using uv")
            
            # Use uv pip install for requirements file
            cmd = [
                uv_cmd, "pip", "install",
                "--python", str(self.get_venv_python()),
                "-r", str(requirements_file)
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_root
            )
            
            self.logger.info(f"Requirements installed successfully from {requirements_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install requirements from {requirements_file}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to install requirements from {requirements_file}: {e}")
            return False
    
    def install_requirements_with_pip(self, requirements_file: Path) -> bool:
        """
        Install requirements using pip (fallback).
        
        Args:
            requirements_file: Path to requirements file
            
        Returns:
            True if installation was successful
        """
        try:
            venv_python = self.get_venv_python()
            
            self.logger.info(f"Installing requirements from {requirements_file} using pip")
            
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "install", "-r", str(requirements_file)],
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_root
            )
            
            self.logger.info(f"Requirements installed successfully from {requirements_file}")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install requirements from {requirements_file}: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to install requirements from {requirements_file}: {e}")
            return False
    
    def install_project_in_development_mode(self) -> bool:
        """
        Install project in development mode.
        
        Returns:
            True if installation was successful
        """
        try:
            venv_python = self.get_venv_python()
            
            # Check if pyproject.toml exists
            pyproject_file = self.project_root / "pyproject.toml"
            if pyproject_file.exists():
                self.logger.info("Installing project in development mode using pyproject.toml")
                
                # Try uv first
                if self.check_uv_availability():
                    venv_uv = self.get_venv_uv()
                    uv_cmd = str(venv_uv) if venv_uv.exists() else "uv"
                    
                    result = subprocess.run(
                        [uv_cmd, "pip", "install", "--python", str(venv_python), "-e", "."],
                        capture_output=True,
                        text=True,
                        check=True,
                        cwd=self.project_root
                    )
                else:
                    # Fallback to pip
                    result = subprocess.run(
                        [str(venv_python), "-m", "pip", "install", "-e", "."],
                        capture_output=True,
                        text=True,
                        check=True,
                        cwd=self.project_root
                    )
                
                self.logger.info("Project installed in development mode")
                return True
            else:
                self.logger.info("No pyproject.toml found, skipping development mode installation")
                return True
                
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install project in development mode: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to install project in development mode: {e}")
            return False
    
    def verify_installation(self) -> bool:
        """
        Verify that key dependencies are installed correctly.
        
        Returns:
            True if verification was successful
        """
        try:
            venv_python = self.get_venv_python()
            
            # Key packages to verify
            key_packages = [
                "fastapi",
                "uvicorn",
                "pythainlp",
                "pydantic",
                "httpx",
                "meilisearch",
                "psutil",
                "requests"
            ]
            
            self.logger.info("Verifying key package installations")
            
            for package in key_packages:
                try:
                    result = subprocess.run(
                        [str(venv_python), "-c", f"import {package}; print(f'{package} imported successfully')"],
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    self.logger.info(f"✓ {package} verified")
                except subprocess.CalledProcessError:
                    self.logger.warning(f"✗ {package} not available or import failed")
            
            # Test Thai tokenization
            try:
                result = subprocess.run(
                    [str(venv_python), "-c", 
                     "from pythainlp import word_tokenize; print('Thai tokenization:', word_tokenize('สวัสดีครับ'))"],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.logger.info("✓ Thai tokenization test passed")
            except subprocess.CalledProcessError as e:
                self.logger.warning(f"✗ Thai tokenization test failed: {e.stderr}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Verification failed: {e}")
            return False
    
    def create_installation_report(self) -> bool:
        """
        Create installation report with package information.
        
        Returns:
            True if report was created successfully
        """
        try:
            venv_python = self.get_venv_python()
            report_path = self.venv_path.parent / "installation-report.json"
            
            # Get installed packages
            result = subprocess.run(
                [str(venv_python), "-m", "pip", "list", "--format=json"],
                capture_output=True,
                text=True,
                check=True
            )
            
            packages = json.loads(result.stdout)
            
            # Create report
            report = {
                "installation_date": str(Path(__file__).stat().st_mtime),
                "venv_path": str(self.venv_path),
                "project_root": str(self.project_root),
                "python_version": subprocess.run(
                    [str(venv_python), "--version"],
                    capture_output=True,
                    text=True,
                    check=True
                ).stdout.strip(),
                "installed_packages": packages,
                "package_count": len(packages)
            }
            
            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2)
            
            self.logger.info(f"Installation report created: {report_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create installation report: {e}")
            return False
    
    def install_additional_packages(self, packages: List[str], use_uv: bool = True) -> bool:
        """
        Install additional packages not in requirements files.
        
        Args:
            packages: List of package names to install
            use_uv: Whether to use uv package manager
            
        Returns:
            True if installation was successful
        """
        try:
            if not packages:
                return True
            
            self.logger.info(f"Installing additional packages: {', '.join(packages)}")
            
            if use_uv and self.check_uv_availability():
                venv_uv = self.get_venv_uv()
                uv_cmd = str(venv_uv) if venv_uv.exists() else "uv"
                
                cmd = [uv_cmd, "pip", "install", "--python", str(self.get_venv_python())] + packages
            else:
                venv_python = self.get_venv_python()
                cmd = [str(venv_python), "-m", "pip", "install"] + packages
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                cwd=self.project_root
            )
            
            self.logger.info(f"Additional packages installed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to install additional packages: {e.stderr}")
            return False
        except Exception as e:
            self.logger.error(f"Failed to install additional packages: {e}")
            return False
    
    def install_all_dependencies(self, use_uv: bool = True) -> bool:
        """
        Install all dependencies for Thai Tokenizer.
        
        Args:
            use_uv: Whether to use uv package manager (fallback to pip if False)
            
        Returns:
            True if installation was successful
        """
        self.logger.info("Starting dependency installation for Thai Tokenizer")
        
        # Ensure uv is available if requested
        if use_uv and not self.check_uv_availability():
            if not self.install_uv():
                self.logger.warning("Failed to install uv, falling back to pip")
                use_uv = False
        
        # Get requirements files
        requirements_files = self.get_requirements_files()
        
        if not requirements_files:
            self.logger.error("No requirements files found")
            return False
        
        # Install requirements
        for req_file in requirements_files:
            if use_uv:
                success = self.install_requirements_with_uv(req_file)
            else:
                success = self.install_requirements_with_pip(req_file)
            
            if not success:
                self.logger.error(f"Failed to install requirements from {req_file}")
                return False
        
        # Install additional packages needed for standalone deployment
        additional_packages = ["psutil", "requests"]
        if not self.install_additional_packages(additional_packages, use_uv):
            self.logger.warning("Failed to install some additional packages")
        
        # Install project in development mode
        if not self.install_project_in_development_mode():
            self.logger.warning("Failed to install project in development mode")
        
        # Verify installation
        if not self.verify_installation():
            self.logger.warning("Installation verification had issues")
        
        # Create installation report
        if not self.create_installation_report():
            self.logger.warning("Failed to create installation report")
        
        self.logger.info("Dependency installation completed successfully")
        return True


def main():
    """Main entry point for dependency installation."""
    parser = argparse.ArgumentParser(
        description="Install dependencies for Thai Tokenizer standalone deployment"
    )
    
    parser.add_argument(
        "--venv-path",
        required=True,
        help="Path to virtual environment"
    )
    
    parser.add_argument(
        "--project-root",
        help="Path to project root directory (default: auto-detect)"
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
        # Create dependency installer
        installer = DependencyInstaller(
            venv_path=args.venv_path,
            project_root=args.project_root
        )
        
        # Install dependencies
        success = installer.install_all_dependencies(use_uv=not args.no_uv)
        
        if success:
            logger.info("Dependency installation completed successfully")
            sys.exit(0)
        else:
            logger.error("Dependency installation failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Installation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()