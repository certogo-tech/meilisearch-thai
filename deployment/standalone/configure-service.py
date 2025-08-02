#!/usr/bin/env python3
"""
Configuration management script for standalone Thai Tokenizer deployment.

This script manages Python-specific configuration for the Thai Tokenizer service,
including environment variables, service settings, and deployment-specific options.
"""

import os
import sys
import json
import argparse
import logging
from pathlib import Path
from typing import Dict, Any, Optional
import tempfile
import shutil

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from deployment.config import (
        OnPremiseConfig, DeploymentMethod, MeilisearchConnectionConfig,
        ServiceConfig, SecurityConfig, ResourceConfig, MonitoringConfig,
        ConfigurationValidator
    )
    from utils.logging import get_structured_logger
except ImportError:
    # Fallback logging if imports fail
    logging.basicConfig(level=logging.INFO)
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class StandaloneConfigurationManager:
    """Manages configuration for standalone Python deployment."""
    
    def __init__(self, install_path: str):
        """
        Initialize configuration manager.
        
        Args:
            install_path: Installation directory path
        """
        self.install_path = Path(install_path)
        self.config_dir = self.install_path / "config"
        self.logger = get_structured_logger(f"{__name__}.StandaloneConfigurationManager")
        
        # Ensure config directory exists
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def create_default_config(self) -> OnPremiseConfig:
        """
        Create default configuration for standalone deployment.
        
        Returns:
            Default OnPremiseConfig instance
        """
        return OnPremiseConfig(
            deployment_method=DeploymentMethod.STANDALONE,
            meilisearch_config=MeilisearchConnectionConfig(
                host="http://localhost:7700",
                api_key="your-meilisearch-api-key"
            ),
            service_config=ServiceConfig(
                service_name="thai-tokenizer",
                service_port=8000,
                service_host="0.0.0.0",
                worker_processes=4
            ),
            security_config=SecurityConfig(),
            resource_config=ResourceConfig(),
            monitoring_config=MonitoringConfig(),
            installation_path=str(self.install_path),
            data_path=str(self.install_path / "data"),
            log_path=str(self.install_path / "logs"),
            config_path=str(self.config_dir)
        )
    
    def load_config_from_file(self, config_file: Path) -> Optional[OnPremiseConfig]:
        """
        Load configuration from JSON file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            OnPremiseConfig instance or None if loading failed
        """
        try:
            if not config_file.exists():
                self.logger.error(f"Configuration file not found: {config_file}")
                return None
            
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Ensure deployment method is set to standalone
            config_data["deployment_method"] = "standalone"
            
            config = OnPremiseConfig(**config_data)
            self.logger.info(f"Configuration loaded from {config_file}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration from {config_file}: {e}")
            return None
    
    def save_config_to_file(self, config: OnPremiseConfig, config_file: Path) -> bool:
        """
        Save configuration to JSON file.
        
        Args:
            config: OnPremiseConfig instance
            config_file: Path to save configuration
            
        Returns:
            True if saving was successful
        """
        try:
            # Convert to dict and handle SecretStr fields
            config_dict = config.model_dump()
            
            # Handle SecretStr fields by converting to string
            if "meilisearch_config" in config_dict:
                ms_config = config_dict["meilisearch_config"]
                if "api_key" in ms_config and hasattr(ms_config["api_key"], "get_secret_value"):
                    ms_config["api_key"] = ms_config["api_key"].get_secret_value()
            
            if "security_config" in config_dict:
                sec_config = config_dict["security_config"]
                if "api_key" in sec_config and sec_config["api_key"] and hasattr(sec_config["api_key"], "get_secret_value"):
                    sec_config["api_key"] = sec_config["api_key"].get_secret_value()
            
            with open(config_file, 'w') as f:
                json.dump(config_dict, f, indent=2)
            
            # Set appropriate file permissions (readable only by owner)
            config_file.chmod(0o600)
            
            self.logger.info(f"Configuration saved to {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration to {config_file}: {e}")
            return False
    
    def create_environment_file(self, config: OnPremiseConfig) -> bool:
        """
        Create environment file for standalone deployment.
        
        Args:
            config: OnPremiseConfig instance
            
        Returns:
            True if environment file was created successfully
        """
        try:
            env_file = self.config_dir / ".env"
            env_vars = config.get_environment_dict()
            
            with open(env_file, 'w') as f:
                f.write("# Thai Tokenizer Standalone Deployment Environment Variables\n")
                f.write(f"# Generated automatically - do not edit manually\n\n")
                
                for key, value in env_vars.items():
                    # Escape values that contain special characters
                    if ' ' in value or '"' in value or "'" in value:
                        value = f'"{value}"'
                    f.write(f"{key}={value}\n")
            
            # Set appropriate file permissions (readable only by owner)
            env_file.chmod(0o600)
            
            self.logger.info(f"Environment file created: {env_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create environment file: {e}")
            return False
    
    def create_service_script(self, config: OnPremiseConfig) -> bool:
        """
        Create service startup script.
        
        Args:
            config: OnPremiseConfig instance
            
        Returns:
            True if service script was created successfully
        """
        try:
            script_path = self.install_path / "bin" / "start-thai-tokenizer.sh"
            venv_path = self.install_path / "venv"
            
            if os.name == 'nt':  # Windows
                script_path = script_path.with_suffix('.bat')
                python_exe = venv_path / "Scripts" / "python.exe"
                script_content = f"""@echo off
echo Starting Thai Tokenizer service...
cd /d "{self.install_path}"
set PYTHONPATH={self.install_path.parent.parent / "src"}
"{python_exe}" -m uvicorn src.api.main:app --host {config.service_config.service_host} --port {config.service_config.service_port} --workers {config.service_config.worker_processes}
"""
            else:  # Unix-like
                python_exe = venv_path / "bin" / "python"
                script_content = f"""#!/bin/bash
set -e

echo "Starting Thai Tokenizer service..."
cd "{self.install_path}"

# Load environment variables
if [ -f "{self.config_dir}/.env" ]; then
    export $(cat "{self.config_dir}/.env" | grep -v '^#' | xargs)
fi

# Set Python path
export PYTHONPATH="{self.install_path.parent.parent / "src"}"

# Start service
"{python_exe}" -m uvicorn src.api.main:app \\
    --host {config.service_config.service_host} \\
    --port {config.service_config.service_port} \\
    --workers {config.service_config.worker_processes} \\
    --log-level info
"""
            
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make executable on Unix-like systems
            if os.name != 'nt':
                script_path.chmod(0o755)
            
            self.logger.info(f"Service script created: {script_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create service script: {e}")
            return False
    
    def create_process_management_scripts(self, config: OnPremiseConfig) -> bool:
        """
        Create process management scripts for standalone deployment.
        
        Args:
            config: OnPremiseConfig instance
            
        Returns:
            True if scripts were created successfully
        """
        try:
            bin_dir = self.install_path / "bin"
            bin_dir.mkdir(exist_ok=True)
            
            scripts = {
                "start-service.sh": self._get_start_script_content(config),
                "stop-service.sh": self._get_stop_script_content(config),
                "restart-service.sh": self._get_restart_script_content(config),
                "status-service.sh": self._get_status_script_content(config),
            }
            
            for script_name, content in scripts.items():
                script_path = bin_dir / script_name
                
                if os.name == 'nt':  # Windows
                    script_path = script_path.with_suffix('.bat')
                
                with open(script_path, 'w') as f:
                    f.write(content)
                
                # Make executable on Unix-like systems
                if os.name != 'nt':
                    script_path.chmod(0o755)
                
                self.logger.info(f"Created script: {script_path}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create process management scripts: {e}")
            return False
    
    def _get_start_script_content(self, config: OnPremiseConfig) -> str:
        """Get content for start service script."""
        venv_path = self.install_path / "venv"
        pid_file = self.install_path / "run" / "thai-tokenizer.pid"
        log_file = self.install_path / "logs" / "thai-tokenizer.log"
        
        if os.name == 'nt':  # Windows
            python_exe = venv_path / "Scripts" / "python.exe"
            return f"""@echo off
echo Starting Thai Tokenizer service...
cd /d "{self.install_path}"

if exist "{pid_file}" (
    echo Service may already be running. Check with status-service.bat
    exit /b 1
)

mkdir "{self.install_path / "run"}" 2>nul
mkdir "{self.install_path / "logs"}" 2>nul

set PYTHONPATH={self.install_path.parent.parent / "src"}
start /b "{python_exe}" -m uvicorn src.api.main:app --host {config.service_config.service_host} --port {config.service_config.service_port} --workers {config.service_config.worker_processes} > "{log_file}" 2>&1

echo Service started. Check logs at {log_file}
"""
        else:  # Unix-like
            python_exe = venv_path / "bin" / "python"
            return f"""#!/bin/bash
set -e

echo "Starting Thai Tokenizer service..."
cd "{self.install_path}"

# Check if already running
if [ -f "{pid_file}" ]; then
    PID=$(cat "{pid_file}")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Service is already running (PID: $PID)"
        exit 1
    else
        echo "Removing stale PID file"
        rm -f "{pid_file}"
    fi
fi

# Create directories
mkdir -p "{self.install_path / "run"}"
mkdir -p "{self.install_path / "logs"}"

# Load environment variables
if [ -f "{self.config_dir}/.env" ]; then
    export $(cat "{self.config_dir}/.env" | grep -v '^#' | xargs)
fi

# Set Python path
export PYTHONPATH="{self.install_path.parent.parent / "src"}"

# Start service in background
nohup "{python_exe}" -m uvicorn src.api.main:app \\
    --host {config.service_config.service_host} \\
    --port {config.service_config.service_port} \\
    --workers {config.service_config.worker_processes} \\
    --log-level info \\
    > "{log_file}" 2>&1 &

# Save PID
echo $! > "{pid_file}"

echo "Service started (PID: $(cat "{pid_file}"))"
echo "Logs: {log_file}"
"""
    
    def _get_stop_script_content(self, config: OnPremiseConfig) -> str:
        """Get content for stop service script."""
        pid_file = self.install_path / "run" / "thai-tokenizer.pid"
        
        if os.name == 'nt':  # Windows
            return f"""@echo off
echo Stopping Thai Tokenizer service...

if not exist "{pid_file}" (
    echo No PID file found. Service may not be running.
    exit /b 1
)

set /p PID=<"{pid_file}"
taskkill /PID %PID% /F
del "{pid_file}"

echo Service stopped.
"""
        else:  # Unix-like
            return f"""#!/bin/bash
set -e

echo "Stopping Thai Tokenizer service..."

if [ ! -f "{pid_file}" ]; then
    echo "No PID file found. Service may not be running."
    exit 1
fi

PID=$(cat "{pid_file}")

if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping service (PID: $PID)"
    kill "$PID"
    
    # Wait for process to stop
    for i in {{1..10}}; do
        if ! kill -0 "$PID" 2>/dev/null; then
            break
        fi
        sleep 1
    done
    
    # Force kill if still running
    if kill -0 "$PID" 2>/dev/null; then
        echo "Force stopping service"
        kill -9 "$PID"
    fi
    
    rm -f "{pid_file}"
    echo "Service stopped"
else
    echo "Process not running, removing PID file"
    rm -f "{pid_file}"
fi
"""
    
    def _get_restart_script_content(self, config: OnPremiseConfig) -> str:
        """Get content for restart service script."""
        if os.name == 'nt':  # Windows
            return f"""@echo off
echo Restarting Thai Tokenizer service...
call "{self.install_path / "bin" / "stop-service.bat"}"
timeout /t 2 /nobreak >nul
call "{self.install_path / "bin" / "start-service.bat"}"
"""
        else:  # Unix-like
            return f"""#!/bin/bash
set -e

echo "Restarting Thai Tokenizer service..."
"{self.install_path / "bin" / "stop-service.sh"}"
sleep 2
"{self.install_path / "bin" / "start-service.sh"}"
"""
    
    def _get_status_script_content(self, config: OnPremiseConfig) -> str:
        """Get content for status service script."""
        pid_file = self.install_path / "run" / "thai-tokenizer.pid"
        
        if os.name == 'nt':  # Windows
            return f"""@echo off
echo Thai Tokenizer Service Status:

if not exist "{pid_file}" (
    echo Status: Not running ^(no PID file^)
    exit /b 1
)

set /p PID=<"{pid_file}"
tasklist /FI "PID eq %PID%" 2>nul | find /I "python.exe" >nul
if %ERRORLEVEL% EQU 0 (
    echo Status: Running ^(PID: %PID%^)
    echo Port: {config.service_config.service_port}
    echo URL: http://{config.service_config.service_host}:{config.service_config.service_port}
) else (
    echo Status: Not running ^(stale PID file^)
    del "{pid_file}"
    exit /b 1
)
"""
        else:  # Unix-like
            return f"""#!/bin/bash

echo "Thai Tokenizer Service Status:"

if [ ! -f "{pid_file}" ]; then
    echo "Status: Not running (no PID file)"
    exit 1
fi

PID=$(cat "{pid_file}")

if kill -0 "$PID" 2>/dev/null; then
    echo "Status: Running (PID: $PID)"
    echo "Port: {config.service_config.service_port}"
    echo "URL: http://{config.service_config.service_host}:{config.service_config.service_port}"
    echo "Health: http://{config.service_config.service_host}:{config.service_config.service_port}/health"
else
    echo "Status: Not running (stale PID file)"
    rm -f "{pid_file}"
    exit 1
fi
"""
    
    def create_logging_config(self, config: OnPremiseConfig) -> bool:
        """
        Create logging configuration for standalone deployment.
        
        Args:
            config: OnPremiseConfig instance
            
        Returns:
            True if logging config was created successfully
        """
        try:
            logging_config = {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "standard": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
                    },
                    "detailed": {
                        "format": "%(asctime)s - %(name)s - %(levelname)s - %(module)s - %(funcName)s - %(message)s"
                    }
                },
                "handlers": {
                    "console": {
                        "class": "logging.StreamHandler",
                        "level": config.monitoring_config.log_level,
                        "formatter": "standard",
                        "stream": "ext://sys.stdout"
                    },
                    "file": {
                        "class": "logging.handlers.RotatingFileHandler",
                        "level": config.monitoring_config.log_level,
                        "formatter": "detailed",
                        "filename": str(self.install_path / "logs" / "thai-tokenizer.log"),
                        "maxBytes": 10485760,  # 10MB
                        "backupCount": 5
                    }
                },
                "loggers": {
                    "": {
                        "level": config.monitoring_config.log_level,
                        "handlers": ["console", "file"],
                        "propagate": False
                    }
                }
            }
            
            config_file = self.config_dir / "logging.json"
            with open(config_file, 'w') as f:
                json.dump(logging_config, f, indent=2)
            
            self.logger.info(f"Logging configuration created: {config_file}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create logging configuration: {e}")
            return False
    
    async def validate_configuration(self, config: OnPremiseConfig) -> bool:
        """
        Validate configuration for standalone deployment.
        
        Args:
            config: OnPremiseConfig instance
            
        Returns:
            True if configuration is valid
        """
        try:
            validator = ConfigurationValidator(config)
            result = await validator.validate_full_configuration()
            
            if result.valid:
                self.logger.info("Configuration validation passed")
                if result.warnings:
                    for warning in result.warnings:
                        self.logger.warning(f"Configuration warning: {warning}")
            else:
                self.logger.error("Configuration validation failed")
                for error in result.errors:
                    self.logger.error(f"Configuration error: {error}")
            
            return result.valid
            
        except Exception as e:
            self.logger.error(f"Configuration validation error: {e}")
            return False
    
    def setup_complete_configuration(self, config_file: Optional[Path] = None) -> bool:
        """
        Set up complete configuration for standalone deployment.
        
        Args:
            config_file: Optional path to existing configuration file
            
        Returns:
            True if setup was successful
        """
        try:
            # Load or create configuration
            if config_file and config_file.exists():
                config = self.load_config_from_file(config_file)
                if not config:
                    return False
            else:
                config = self.create_default_config()
            
            # Save configuration
            main_config_file = self.config_dir / "config.json"
            if not self.save_config_to_file(config, main_config_file):
                return False
            
            # Create environment file
            if not self.create_environment_file(config):
                return False
            
            # Create service scripts
            if not self.create_service_script(config):
                return False
            
            # Create process management scripts
            if not self.create_process_management_scripts(config):
                return False
            
            # Create logging configuration
            if not self.create_logging_config(config):
                return False
            
            self.logger.info("Configuration setup completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Configuration setup failed: {e}")
            return False


def main():
    """Main entry point for configuration management."""
    parser = argparse.ArgumentParser(
        description="Configure Thai Tokenizer for standalone deployment"
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
        # Create configuration manager
        config_manager = StandaloneConfigurationManager(args.install_path)
        
        # Set up configuration
        config_file = Path(args.config_file) if args.config_file else None
        success = config_manager.setup_complete_configuration(config_file)
        
        if success:
            logger.info("Configuration setup completed successfully")
            sys.exit(0)
        else:
            logger.error("Configuration setup failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Configuration setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()