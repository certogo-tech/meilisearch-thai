#!/usr/bin/env python3
"""
Production-Ready Deployment Package Creator for Thai Tokenizer.

This script creates a distributable deployment package with all necessary
components, installation procedures, and documentation.
"""

import os
import sys
import json
import shutil
import tarfile
import zipfile
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import subprocess
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))


class DeploymentPackageCreator:
    """Creates production-ready deployment packages."""
    
    def __init__(self, project_root: Optional[str] = None, output_dir: str = "dist"):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Package metadata
        self.package_info = {
            "name": "thai-tokenizer-deployment",
            "version": self._get_version(),
            "description": "Thai Tokenizer On-Premise Deployment Package",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "python_version": "3.12+",
            "supported_platforms": ["linux", "darwin"],
            "deployment_methods": ["docker", "systemd", "standalone"]
        }
    
    def _get_version(self) -> str:
        """Get package version."""
        try:
            # Try to get version from git
            result = subprocess.run(
                ["git", "describe", "--tags", "--always"],
                capture_output=True,
                text=True,
                cwd=self.project_root
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        
        # Fallback to date-based version
        return f"1.0.0-{datetime.now().strftime('%Y%m%d')}" 
   
    def create_package(self, package_format: str = "tar.gz") -> str:
        """Create deployment package."""
        print(f"Creating Thai Tokenizer deployment package v{self.package_info['version']}")
        
        # Create temporary directory for package contents
        with tempfile.TemporaryDirectory() as temp_dir:
            package_dir = Path(temp_dir) / "thai-tokenizer-deployment"
            package_dir.mkdir()
            
            # Copy core components
            self._copy_core_components(package_dir)
            
            # Copy deployment scripts
            self._copy_deployment_scripts(package_dir)
            
            # Copy configuration templates
            self._copy_configuration_templates(package_dir)
            
            # Copy documentation
            self._copy_documentation(package_dir)
            
            # Create installation scripts
            self._create_installation_scripts(package_dir)
            
            # Create package metadata
            self._create_package_metadata(package_dir)
            
            # Create the package archive
            package_file = self._create_archive(package_dir, package_format)
            
            print(f"✅ Package created: {package_file}")
            return package_file
    
    def _copy_core_components(self, package_dir: Path):
        """Copy core application components."""
        print("📦 Copying core components...")
        
        # Create src directory structure
        src_dir = package_dir / "src"
        src_dir.mkdir()
        
        # Copy source code
        source_dirs = [
            "deployment",
            "utils",
            "api",
            "tokenizer",
            "meilisearch_integration"
        ]
        
        for dir_name in source_dirs:
            src_path = self.project_root / "src" / dir_name
            if src_path.exists():
                shutil.copytree(src_path, src_dir / dir_name)
        
        # Copy requirements
        requirements_file = self.project_root / "requirements.txt"
        if requirements_file.exists():
            shutil.copy2(requirements_file, package_dir)
    
    def _copy_deployment_scripts(self, package_dir: Path):
        """Copy deployment scripts and utilities."""
        print("🔧 Copying deployment scripts...")
        
        scripts_dir = package_dir / "scripts"
        scripts_dir.mkdir()
        
        # Copy main scripts
        script_files = [
            "thai-tokenizer-deploy",
            "run_deployment_tests.py",
            "ci_deployment_testing.py"
        ]
        
        for script_file in script_files:
            src_path = self.project_root / "scripts" / script_file
            if src_path.exists():
                shutil.copy2(src_path, scripts_dir)
                # Make executable
                os.chmod(scripts_dir / script_file, 0o755)
        
        # Copy automation scripts
        automation_dir = scripts_dir / "automation"
        automation_src = self.project_root / "scripts" / "automation"
        if automation_src.exists():
            shutil.copytree(automation_src, automation_dir)
        
        # Copy package scripts
        package_src = self.project_root / "scripts" / "package"
        if package_src.exists():
            shutil.copytree(package_src, scripts_dir / "package")
    
    def _copy_configuration_templates(self, package_dir: Path):
        """Copy configuration templates."""
        print("⚙️  Copying configuration templates...")
        
        config_dir = package_dir / "config_templates"
        config_dir.mkdir()
        
        # Create configuration templates for each deployment method
        templates = {
            "docker_development.json": {
                "deployment_method": "docker",
                "meilisearch_config": {
                    "host": "${MEILISEARCH_HOST:-http://localhost:7700}",
                    "api_key": "${MEILISEARCH_API_KEY}"
                },
                "service_config": {
                    "service_name": "thai-tokenizer-dev",
                    "service_port": "${SERVICE_PORT:-8000}"
                },
                "security_config": {
                    "security_level": "basic"
                }
            },
            "docker_production.json": {
                "deployment_method": "docker",
                "meilisearch_config": {
                    "host": "${MEILISEARCH_HOST}",
                    "api_key": "${MEILISEARCH_API_KEY}",
                    "ssl_enabled": True
                },
                "service_config": {
                    "service_name": "thai-tokenizer",
                    "service_port": "${SERVICE_PORT:-8000}"
                },
                "security_config": {
                    "security_level": "strict",
                    "api_key_required": True,
                    "enable_https": True
                }
            },
            "systemd_production.json": {
                "deployment_method": "systemd",
                "meilisearch_config": {
                    "host": "${MEILISEARCH_HOST}",
                    "api_key": "${MEILISEARCH_API_KEY}",
                    "ssl_enabled": True
                },
                "service_config": {
                    "service_name": "thai-tokenizer",
                    "service_port": "${SERVICE_PORT:-8000}",
                    "service_host": "127.0.0.1"
                },
                "security_config": {
                    "security_level": "strict"
                },
                "installation_path": "/opt/thai-tokenizer"
            }
        }
        
        for template_name, template_data in templates.items():
            template_file = config_dir / template_name
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
    
    def _copy_documentation(self, package_dir: Path):
        """Copy documentation files."""
        print("📚 Copying documentation...")
        
        docs_dir = package_dir / "docs"
        docs_dir.mkdir()
        
        # Copy documentation files
        doc_files = [
            "README.md",
            "DEPLOYMENT_GUIDE.md",
            "CLI_AND_AUTOMATION.md",
            "TROUBLESHOOTING.md"
        ]
        
        for doc_file in doc_files:
            src_path = self.project_root / "docs" / doc_file
            if src_path.exists():
                shutil.copy2(src_path, docs_dir)
            elif (self.project_root / doc_file).exists():
                shutil.copy2(self.project_root / doc_file, docs_dir)
        
        # Copy deployment-specific documentation
        deployment_docs = self.project_root / "deployment"
        if deployment_docs.exists():
            for doc_file in deployment_docs.glob("*.md"):
                shutil.copy2(doc_file, docs_dir)
    
    def _create_installation_scripts(self, package_dir: Path):
        """Create installation scripts."""
        print("🚀 Creating installation scripts...")
        
        # Create install script
        install_script = package_dir / "install.sh"
        install_content = '''#!/bin/bash
set -e

# Thai Tokenizer Deployment Package Installer
echo "🚀 Installing Thai Tokenizer Deployment Package"

# Check requirements
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

# Check Python version
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
required_version="3.12"

if [ "$(printf '%s\\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then
    echo "❌ Python 3.12+ is required, found $python_version"
    exit 1
fi

# Install uv if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Installing uv package manager..."
    pip install uv
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -r requirements.txt

# Make scripts executable
chmod +x scripts/thai-tokenizer-deploy
chmod +x scripts/*.py
chmod +x scripts/automation/*.py

# Create symlink for CLI (optional)
if [ "$1" = "--install-cli" ]; then
    echo "🔗 Creating CLI symlink..."
    sudo ln -sf "$(pwd)/scripts/thai-tokenizer-deploy" /usr/local/bin/thai-tokenizer-deploy
    echo "✅ CLI installed to /usr/local/bin/thai-tokenizer-deploy"
fi

echo "✅ Installation completed!"
echo ""
echo "Next steps:"
echo "1. Configure your deployment: ./scripts/thai-tokenizer-deploy generate-config --method docker --output config.json"
echo "2. Deploy the service: ./scripts/thai-tokenizer-deploy deploy --config config.json"
echo ""
echo "For more information, see docs/DEPLOYMENT_GUIDE.md"
'''
        
        with open(install_script, 'w') as f:
            f.write(install_content)
        os.chmod(install_script, 0o755)
        
        # Create uninstall script
        uninstall_script = package_dir / "uninstall.sh"
        uninstall_content = '''#!/bin/bash
set -e

echo "🗑️  Uninstalling Thai Tokenizer Deployment Package"

# Stop any running services
echo "🛑 Stopping services..."
./scripts/thai-tokenizer-deploy cleanup --all --force 2>/dev/null || true

# Remove CLI symlink if it exists
if [ -L "/usr/local/bin/thai-tokenizer-deploy" ]; then
    echo "🔗 Removing CLI symlink..."
    sudo rm -f /usr/local/bin/thai-tokenizer-deploy
fi

echo "✅ Uninstallation completed!"
echo "Note: Configuration files and data have been preserved"
'''
        
        with open(uninstall_script, 'w') as f:
            f.write(uninstall_content)
        os.chmod(uninstall_script, 0o755)
    
    def _create_package_metadata(self, package_dir: Path):
        """Create package metadata files."""
        print("📋 Creating package metadata...")
        
        # Create package info file
        package_info_file = package_dir / "package_info.json"
        with open(package_info_file, 'w') as f:
            json.dump(self.package_info, f, indent=2)
        
        # Create version file
        version_file = package_dir / "VERSION"
        with open(version_file, 'w') as f:
            f.write(self.package_info["version"])
        
        # Create manifest file
        manifest = self._create_manifest(package_dir)
        manifest_file = package_dir / "MANIFEST.txt"
        with open(manifest_file, 'w') as f:
            f.write(manifest)
    
    def _create_manifest(self, package_dir: Path) -> str:
        """Create package manifest."""
        manifest_lines = [
            f"Thai Tokenizer Deployment Package v{self.package_info['version']}",
            f"Created: {self.package_info['created_at']}",
            "",
            "Package Contents:",
            ""
        ]
        
        # List all files in package
        for root, dirs, files in os.walk(package_dir):
            level = root.replace(str(package_dir), '').count(os.sep)
            indent = ' ' * 2 * level
            manifest_lines.append(f"{indent}{os.path.basename(root)}/")
            
            subindent = ' ' * 2 * (level + 1)
            for file in files:
                file_path = Path(root) / file
                file_size = file_path.stat().st_size
                manifest_lines.append(f"{subindent}{file} ({file_size} bytes)")
        
        return '\n'.join(manifest_lines)
    
    def _create_archive(self, package_dir: Path, format: str) -> str:
        """Create package archive."""
        print(f"📦 Creating {format} archive...")
        
        package_name = f"thai-tokenizer-deployment-{self.package_info['version']}"
        
        if format == "tar.gz":
            archive_file = self.output_dir / f"{package_name}.tar.gz"
            with tarfile.open(archive_file, "w:gz") as tar:
                tar.add(package_dir, arcname=package_name)
        
        elif format == "zip":
            archive_file = self.output_dir / f"{package_name}.zip"
            with zipfile.ZipFile(archive_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, dirs, files in os.walk(package_dir):
                    for file in files:
                        file_path = Path(root) / file
                        arcname = Path(package_name) / file_path.relative_to(package_dir)
                        zip_file.write(file_path, arcname)
        
        else:
            raise ValueError(f"Unsupported archive format: {format}")
        
        return str(archive_file)


def main():
    """Main package creation function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Create Thai Tokenizer deployment package")
    parser.add_argument("--format", choices=["tar.gz", "zip"], default="tar.gz",
                       help="Package format")
    parser.add_argument("--output-dir", default="dist", help="Output directory")
    parser.add_argument("--project-root", help="Project root directory")
    
    args = parser.parse_args()
    
    try:
        creator = DeploymentPackageCreator(args.project_root, args.output_dir)
        package_file = creator.create_package(args.format)
        
        print(f"\n🎉 Package creation completed!")
        print(f"📦 Package file: {package_file}")
        print(f"📊 Package size: {Path(package_file).stat().st_size / 1024 / 1024:.1f} MB")
        
        return 0
        
    except Exception as e:
        print(f"❌ Package creation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())