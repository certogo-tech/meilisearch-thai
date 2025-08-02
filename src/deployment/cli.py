#!/usr/bin/env python3
"""
Deployment Command-Line Interface for Thai Tokenizer On-Premise Deployment.

This module provides a comprehensive CLI tool for deployment method selection,
execution, configuration setup, validation, and management of Thai Tokenizer
on-premise deployments.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
import tempfile

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from deployment.config import OnPremiseConfig, DeploymentMethod, ValidationResult
from deployment.deployment_manager import DeploymentManager, DeploymentResult
from deployment.validation_framework import DeploymentValidationFramework
from utils.logging import get_structured_logger


class DeploymentCLI:
    """Main deployment CLI class."""
    
    def __init__(self):
        self.logger = get_structured_logger(__name__)
        self.config: Optional[OnPremiseConfig] = None
        self.deployment_manager: Optional[DeploymentManager] = None
        
    def create_parser(self) -> argparse.ArgumentParser:
        """Create the main argument parser."""
        parser = argparse.ArgumentParser(
            prog='thai-tokenizer-deploy',
            description='Thai Tokenizer On-Premise Deployment Tool',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Interactive deployment setup
  thai-tokenizer-deploy deploy --interactive
  
  # Deploy with configuration file
  thai-tokenizer-deploy deploy --config config.json --method docker
  
  # Validate system requirements
  thai-tokenizer-deploy validate-system --config config.json
  
  # Check deployment status
  thai-tokenizer-deploy status --deployment-id abc123
  
  # Generate configuration template
  thai-tokenizer-deploy generate-config --method docker --output config.json
            """
        )
        
        parser.add_argument(
            '--config', '-c',
            type=str,
            help='Path to deployment configuration file'
        )
        
        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='Enable verbose logging'
        )
        
        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='Suppress non-essential output'
        )
        
        parser.add_argument(
            '--log-file',
            type=str,
            help='Path to log file (default: deployment.log)'
        )
        
        # Create subparsers for commands
        subparsers = parser.add_subparsers(
            dest='command',
            help='Available commands',
            metavar='COMMAND'
        )
        
        # Deploy command
        self._add_deploy_parser(subparsers)
        
        # Validate commands
        self._add_validate_parsers(subparsers)
        
        # Status and management commands
        self._add_management_parsers(subparsers)
        
        # Configuration commands
        self._add_config_parsers(subparsers)
        
        # Utility commands
        self._add_utility_parsers(subparsers)
        
        return parser
    
    def _add_deploy_parser(self, subparsers):
        """Add deployment command parser."""
        deploy_parser = subparsers.add_parser(
            'deploy',
            help='Deploy Thai Tokenizer service',
            description='Deploy Thai Tokenizer service using specified method'
        )
        
        deploy_parser.add_argument(
            '--method', '-m',
            choices=['docker', 'systemd', 'standalone'],
            help='Deployment method to use'
        )
        
        deploy_parser.add_argument(
            '--interactive', '-i',
            action='store_true',
            help='Interactive deployment setup'
        )
        
        deploy_parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate configuration without deploying'
        )
        
        deploy_parser.add_argument(
            '--force',
            action='store_true',
            help='Force deployment even if validation warnings exist'
        )
        
        deploy_parser.add_argument(
            '--progress-file',
            type=str,
            help='File to write deployment progress updates'
        )
        
        deploy_parser.add_argument(
            '--output-dir',
            type=str,
            default='deployment_output',
            help='Directory for deployment artifacts and logs'
        )
    
    def _add_validate_parsers(self, subparsers):
        """Add validation command parsers."""
        # System validation
        validate_system_parser = subparsers.add_parser(
            'validate-system',
            help='Validate system requirements',
            description='Check if system meets deployment requirements'
        )
        
        validate_system_parser.add_argument(
            '--method', '-m',
            choices=['docker', 'systemd', 'standalone'],
            help='Deployment method to validate for'
        )
        
        validate_system_parser.add_argument(
            '--report-file',
            type=str,
            help='File to save validation report'
        )
        
        validate_system_parser.add_argument(
            '--format',
            choices=['json', 'html', 'markdown'],
            default='json',
            help='Report format'
        )
        
        # Configuration validation
        validate_config_parser = subparsers.add_parser(
            'validate-config',
            help='Validate deployment configuration',
            description='Validate deployment configuration file'
        )
        
        validate_config_parser.add_argument(
            '--fix',
            action='store_true',
            help='Attempt to fix common configuration issues'
        )
        
        # Meilisearch validation
        validate_meilisearch_parser = subparsers.add_parser(
            'validate-meilisearch',
            help='Validate Meilisearch connectivity',
            description='Test connection to existing Meilisearch server'
        )
        
        validate_meilisearch_parser.add_argument(
            '--host',
            type=str,
            help='Meilisearch host URL'
        )
        
        validate_meilisearch_parser.add_argument(
            '--api-key',
            type=str,
            help='Meilisearch API key'
        )
    
    def _add_management_parsers(self, subparsers):
        """Add management command parsers."""
        # Status command
        status_parser = subparsers.add_parser(
            'status',
            help='Check deployment status',
            description='Check status of deployed service'
        )
        
        status_parser.add_argument(
            '--deployment-id',
            type=str,
            help='Deployment ID to check'
        )
        
        status_parser.add_argument(
            '--service-name',
            type=str,
            help='Service name to check'
        )
        
        status_parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed status information'
        )
        
        # Stop command
        stop_parser = subparsers.add_parser(
            'stop',
            help='Stop deployed service',
            description='Stop running Thai Tokenizer service'
        )
        
        stop_parser.add_argument(
            '--deployment-id',
            type=str,
            help='Deployment ID to stop'
        )
        
        stop_parser.add_argument(
            '--service-name',
            type=str,
            help='Service name to stop'
        )
        
        stop_parser.add_argument(
            '--force',
            action='store_true',
            help='Force stop service'
        )
        
        # Restart command
        restart_parser = subparsers.add_parser(
            'restart',
            help='Restart deployed service',
            description='Restart running Thai Tokenizer service'
        )
        
        restart_parser.add_argument(
            '--deployment-id',
            type=str,
            help='Deployment ID to restart'
        )
        
        restart_parser.add_argument(
            '--service-name',
            type=str,
            help='Service name to restart'
        )
        
        # Cleanup command
        cleanup_parser = subparsers.add_parser(
            'cleanup',
            help='Clean up deployment resources',
            description='Remove deployment resources and artifacts'
        )
        
        cleanup_parser.add_argument(
            '--deployment-id',
            type=str,
            help='Deployment ID to clean up'
        )
        
        cleanup_parser.add_argument(
            '--all',
            action='store_true',
            help='Clean up all deployments'
        )
        
        cleanup_parser.add_argument(
            '--force',
            action='store_true',
            help='Force cleanup without confirmation'
        )
    
    def _add_config_parsers(self, subparsers):
        """Add configuration command parsers."""
        # Generate config command
        generate_config_parser = subparsers.add_parser(
            'generate-config',
            help='Generate configuration template',
            description='Generate deployment configuration template'
        )
        
        generate_config_parser.add_argument(
            '--method', '-m',
            choices=['docker', 'systemd', 'standalone'],
            required=True,
            help='Deployment method for configuration template'
        )
        
        generate_config_parser.add_argument(
            '--output', '-o',
            type=str,
            required=True,
            help='Output file for configuration template'
        )
        
        generate_config_parser.add_argument(
            '--interactive', '-i',
            action='store_true',
            help='Interactive configuration generation'
        )
        
        generate_config_parser.add_argument(
            '--example',
            action='store_true',
            help='Generate example configuration with sample values'
        )
        
        # Edit config command
        edit_config_parser = subparsers.add_parser(
            'edit-config',
            help='Edit deployment configuration',
            description='Interactive configuration editor'
        )
        
        edit_config_parser.add_argument(
            '--editor',
            type=str,
            help='Text editor to use (default: $EDITOR or nano)'
        )
        
        # Show config command
        show_config_parser = subparsers.add_parser(
            'show-config',
            help='Display configuration',
            description='Display current deployment configuration'
        )
        
        show_config_parser.add_argument(
            '--format',
            choices=['json', 'yaml', 'table'],
            default='json',
            help='Output format'
        )
        
        show_config_parser.add_argument(
            '--mask-secrets',
            action='store_true',
            help='Mask sensitive information'
        )
    
    def _add_utility_parsers(self, subparsers):
        """Add utility command parsers."""
        # Test command
        test_parser = subparsers.add_parser(
            'test',
            help='Test deployed service',
            description='Run tests against deployed service'
        )
        
        test_parser.add_argument(
            '--service-url',
            type=str,
            help='Service URL to test'
        )
        
        test_parser.add_argument(
            '--test-type',
            choices=['health', 'tokenization', 'performance', 'security', 'all'],
            default='health',
            help='Type of test to run'
        )
        
        test_parser.add_argument(
            '--report-file',
            type=str,
            help='File to save test report'
        )
        
        # Logs command
        logs_parser = subparsers.add_parser(
            'logs',
            help='View service logs',
            description='View logs from deployed service'
        )
        
        logs_parser.add_argument(
            '--deployment-id',
            type=str,
            help='Deployment ID to view logs for'
        )
        
        logs_parser.add_argument(
            '--service-name',
            type=str,
            help='Service name to view logs for'
        )
        
        logs_parser.add_argument(
            '--follow', '-f',
            action='store_true',
            help='Follow log output'
        )
        
        logs_parser.add_argument(
            '--lines', '-n',
            type=int,
            default=100,
            help='Number of lines to show'
        )
        
        # Version command
        version_parser = subparsers.add_parser(
            'version',
            help='Show version information',
            description='Display version and build information'
        )
        
        version_parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed version information'
        )
    
    def setup_logging(self, args) -> None:
        """Setup logging based on CLI arguments."""
        log_level = logging.DEBUG if args.verbose else logging.INFO
        if args.quiet:
            log_level = logging.WARNING
        
        # Configure root logger
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup file logging if specified
        if args.log_file:
            file_handler = logging.FileHandler(args.log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(file_formatter)
            logging.getLogger().addHandler(file_handler)
    
    def load_config(self, config_path: str) -> OnPremiseConfig:
        """Load deployment configuration from file."""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            with open(config_file, 'r') as f:
                if config_file.suffix.lower() == '.json':
                    config_data = json.load(f)
                elif config_file.suffix.lower() in ['.yml', '.yaml']:
                    import yaml
                    config_data = yaml.safe_load(f)
                else:
                    # Try JSON first, then YAML
                    content = f.read()
                    try:
                        config_data = json.loads(content)
                    except json.JSONDecodeError:
                        import yaml
                        config_data = yaml.safe_load(content)
            
            return OnPremiseConfig(**config_data)
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def save_config(self, config: OnPremiseConfig, output_path: str) -> None:
        """Save configuration to file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Convert config to dict with proper serialization
            try:
                # Try Pydantic v2 method first
                config_dict = config.model_dump(mode='json')
            except AttributeError:
                # Fallback to Pydantic v1 method
                config_dict = config.dict()
                # Handle SecretStr manually
                def convert_secrets(obj):
                    if hasattr(obj, 'get_secret_value'):
                        return obj.get_secret_value()
                    elif isinstance(obj, dict):
                        return {k: convert_secrets(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [convert_secrets(item) for item in obj]
                    return obj
                config_dict = convert_secrets(config_dict)
            
            # Save based on file extension
            if output_file.suffix.lower() == '.json':
                with open(output_file, 'w') as f:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
            elif output_file.suffix.lower() in ['.yml', '.yaml']:
                import yaml
                with open(output_file, 'w') as f:
                    yaml.dump(config_dict, f, default_flow_style=False, allow_unicode=True)
            else:
                # Default to JSON
                with open(output_file, 'w') as f:
                    json.dump(config_dict, f, indent=2, ensure_ascii=False)
            
            self.logger.info(f"Configuration saved to: {output_file}")
            
        except Exception as e:
            self.logger.error(f"Failed to save configuration: {e}")
            raise
    
    async def handle_deploy_command(self, args) -> int:
        """Handle deploy command."""
        try:
            # Load or create configuration
            if args.config:
                self.config = self.load_config(args.config)
            elif args.interactive:
                self.config = await self.interactive_config_setup(args.method)
            else:
                print("Error: Either --config or --interactive must be specified")
                return 1
            
            # Override method if specified
            if args.method:
                self.config.deployment_method = DeploymentMethod(args.method)
            
            # Create output directory
            output_dir = Path(args.output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Setup progress tracking
            progress_file = None
            if args.progress_file:
                progress_file = Path(args.progress_file)
                progress_file.parent.mkdir(parents=True, exist_ok=True)
            
            progress_updates = []
            def progress_callback(progress):
                progress_updates.append(progress)
                if not args.quiet:
                    print(f"Progress: {progress.progress_percentage:.1f}% - {progress.current_step.name if progress.current_step else 'Starting'}")
                
                if progress_file:
                    with open(progress_file, 'w') as f:
                        json.dump({
                            "deployment_id": progress.deployment_id,
                            "progress_percentage": progress.progress_percentage,
                            "current_step": progress.current_step.name if progress.current_step else None,
                            "overall_status": progress.overall_status.value,
                            "timestamp": datetime.now().isoformat()
                        }, f, indent=2)
            
            # Dry run validation
            if args.dry_run:
                print("Performing dry run validation...")
                validation_framework = DeploymentValidationFramework(self.config)
                validation_results = await validation_framework.run_comprehensive_validation()
                
                if validation_results["overall_status"] == "FAILED":
                    print("❌ Validation failed - deployment would not succeed")
                    return 1
                elif validation_results["overall_status"] == "WARNING":
                    print("⚠️  Validation warnings found - deployment may have issues")
                    if not args.force:
                        print("Use --force to proceed despite warnings")
                        return 1
                else:
                    print("✅ Validation passed - deployment should succeed")
                    return 0
            
            # Create deployment manager
            self.deployment_manager = DeploymentManager(self.config, progress_callback)
            
            print(f"Starting deployment using {self.config.deployment_method.value} method...")
            
            # Execute deployment
            result = await self.deployment_manager.deploy()
            
            # Save deployment result
            result_file = output_dir / "deployment_result.json"
            with open(result_file, 'w') as f:
                json.dump({
                    "deployment_id": result.deployment_id,
                    "success": result.success,
                    "deployment_method": result.deployment_method.value,
                    "summary": result.summary,
                    "endpoints": result.endpoints,
                    "configuration_path": result.configuration_path,
                    "log_file_path": result.log_file_path,
                    "timestamp": datetime.now().isoformat()
                }, f, indent=2)
            
            if result.success:
                print(f"✅ Deployment successful!")
                print(f"   Deployment ID: {result.deployment_id}")
                print(f"   Method: {result.deployment_method.value}")
                if result.endpoints:
                    print("   Endpoints:")
                    for name, url in result.endpoints.items():
                        print(f"     {name}: {url}")
                print(f"   Result saved to: {result_file}")
                return 0
            else:
                print(f"❌ Deployment failed: {result.summary}")
                return 1
                
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            print(f"❌ Deployment failed: {e}")
            return 1
    
    async def interactive_config_setup(self, method: Optional[str] = None) -> OnPremiseConfig:
        """Interactive configuration setup."""
        print("🚀 Thai Tokenizer Deployment Configuration Setup")
        print("=" * 50)
        
        # Deployment method selection
        if not method:
            print("\nSelect deployment method:")
            print("1. Docker (recommended for most users)")
            print("2. systemd (for Linux servers)")
            print("3. Standalone Python (for development)")
            
            while True:
                choice = input("\nEnter choice (1-3): ").strip()
                if choice == "1":
                    method = "docker"
                    break
                elif choice == "2":
                    method = "systemd"
                    break
                elif choice == "3":
                    method = "standalone"
                    break
                else:
                    print("Invalid choice. Please enter 1, 2, or 3.")
        
        print(f"\nConfiguring for {method} deployment...")
        
        # Meilisearch configuration
        print("\n📊 Meilisearch Configuration")
        print("Enter details for your existing Meilisearch server:")
        
        ms_host = input("Meilisearch host URL [http://localhost:7700]: ").strip() or "http://localhost:7700"
        ms_api_key = input("Meilisearch API key (optional): ").strip() or None
        
        # Service configuration
        print("\n⚙️  Service Configuration")
        service_name = input(f"Service name [thai-tokenizer-{method}]: ").strip() or f"thai-tokenizer-{method}"
        service_port = input("Service port [8000]: ").strip() or "8000"
        
        try:
            service_port = int(service_port)
        except ValueError:
            print("Invalid port number, using default 8000")
            service_port = 8000
        
        # Security configuration
        print("\n🔒 Security Configuration")
        print("Select security level:")
        print("1. Basic (minimal security)")
        print("2. Standard (recommended)")
        print("3. Strict (maximum security)")
        
        while True:
            choice = input("Enter choice (1-3) [2]: ").strip() or "2"
            if choice == "1":
                security_level = "basic"
                break
            elif choice == "2":
                security_level = "standard"
                break
            elif choice == "3":
                security_level = "strict"
                break
            else:
                print("Invalid choice. Please enter 1, 2, or 3.")
        
        api_key_required = False
        if security_level in ["standard", "strict"]:
            api_key_choice = input("Require API key authentication? (y/N): ").strip().lower()
            api_key_required = api_key_choice in ['y', 'yes']
        
        # Installation paths
        print("\n📁 Installation Configuration")
        default_path = f"/opt/thai-tokenizer" if method == "systemd" else f"./thai-tokenizer-{method}"
        install_path = input(f"Installation path [{default_path}]: ").strip() or default_path
        
        # Create configuration
        config_data = {
            "deployment_method": method,
            "meilisearch_config": {
                "host": ms_host,
                "port": int(ms_host.split(':')[-1]) if ':' in ms_host else 7700,
                "api_key": ms_api_key,
                "ssl_enabled": ms_host.startswith('https'),
                "ssl_verify": True,
                "timeout_seconds": 30,
                "max_retries": 3,
                "retry_delay_seconds": 1.0
            },
            "service_config": {
                "service_name": service_name,
                "service_port": service_port,
                "service_host": "0.0.0.0",
                "worker_processes": 2,
                "service_user": "thai-tokenizer",
                "service_group": "thai-tokenizer"
            },
            "security_config": {
                "security_level": security_level,
                "allowed_hosts": ["*"] if security_level == "basic" else ["localhost", "127.0.0.1"],
                "cors_origins": ["*"] if security_level == "basic" else [],
                "api_key_required": api_key_required,
                "enable_https": security_level == "strict"
            },
            "resource_config": {
                "memory_limit_mb": 256,
                "cpu_limit_cores": 0.5,
                "max_concurrent_requests": 50,
                "request_timeout_seconds": 30,
                "enable_metrics": True,
                "metrics_port": service_port + 1000
            },
            "monitoring_config": {
                "enable_health_checks": True,
                "health_check_interval_seconds": 30,
                "enable_logging": True,
                "log_level": "INFO",
                "enable_prometheus": security_level in ["standard", "strict"],
                "prometheus_port": service_port + 1000
            },
            "installation_path": install_path,
            "data_path": f"{install_path}/data",
            "log_path": f"{install_path}/logs",
            "config_path": f"{install_path}/config",
            "environment_variables": {}
        }
        
        config = OnPremiseConfig(**config_data)
        
        # Save configuration option
        save_config = input("\nSave configuration to file? (Y/n): ").strip().lower()
        if save_config not in ['n', 'no']:
            config_file = input("Configuration file path [deployment_config.json]: ").strip() or "deployment_config.json"
            self.save_config(config, config_file)
        
        print("\n✅ Configuration setup complete!")
        return config
    
    async def handle_validate_system_command(self, args) -> int:
        """Handle validate-system command."""
        try:
            if not self.config and args.config:
                self.config = self.load_config(args.config)
            elif not self.config:
                # Create minimal config for validation
                method = args.method or "docker"
                self.config = OnPremiseConfig(
                    deployment_method=method,
                    meilisearch_config={
                        "host": "http://localhost:7700",
                        "port": 7700,
                        "api_key": "test-key"
                    }
                )
            
            print("🔍 Validating system requirements...")
            
            validation_framework = DeploymentValidationFramework(self.config)
            results = await validation_framework.run_comprehensive_validation()
            
            # Display results
            status_emoji = {
                "PASSED": "✅",
                "WARNING": "⚠️",
                "FAILED": "❌"
            }
            
            overall_status = results["overall_status"]
            print(f"\n{status_emoji.get(overall_status, '❓')} Overall Status: {overall_status}")
            print(f"Summary: {results['summary']}")
            
            # Show detailed results
            if args.verbose or overall_status != "PASSED":
                print("\nDetailed Results:")
                
                for category, category_results in results.items():
                    if category in ["timestamp", "overall_status", "summary"]:
                        continue
                    
                    print(f"\n📋 {category.replace('_', ' ').title()}:")
                    
                    if isinstance(category_results, dict) and "results" in category_results:
                        for result in category_results["results"]:
                            status = "✅" if result.get("success", result.get("satisfied", False)) else "❌"
                            name = result.get("requirement", {}).get("name") or result.get("test_case", {}).get("name") or result.get("benchmark", {}).get("name") or "Unknown"
                            print(f"  {status} {name}")
            
            # Save report if requested
            if args.report_file:
                report_path = Path(args.report_file)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                
                if args.format == 'json':
                    with open(report_path, 'w') as f:
                        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
                elif args.format == 'html':
                    # Generate HTML report (simplified)
                    html_content = f"""
                    <html><head><title>System Validation Report</title></head>
                    <body>
                    <h1>System Validation Report</h1>
                    <p><strong>Status:</strong> {overall_status}</p>
                    <p><strong>Summary:</strong> {results['summary']}</p>
                    <pre>{json.dumps(results, indent=2, default=str)}</pre>
                    </body></html>
                    """
                    with open(report_path, 'w') as f:
                        f.write(html_content)
                elif args.format == 'markdown':
                    # Generate Markdown report (simplified)
                    md_content = f"""# System Validation Report

**Status:** {overall_status}
**Summary:** {results['summary']}

## Detailed Results

```json
{json.dumps(results, indent=2, default=str)}
```
                    """
                    with open(report_path, 'w') as f:
                        f.write(md_content)
                
                print(f"Report saved to: {report_path}")
            
            return 0 if overall_status == "PASSED" else 1
            
        except Exception as e:
            self.logger.error(f"System validation failed: {e}")
            print(f"❌ System validation failed: {e}")
            return 1
    
    async def handle_generate_config_command(self, args) -> int:
        """Handle generate-config command."""
        try:
            if args.interactive:
                config = await self.interactive_config_setup(args.method)
                self.save_config(config, args.output)
            else:
                # Generate template configuration
                template_config = self.generate_config_template(args.method, args.example)
                self.save_config(template_config, args.output)
                
                if not args.quiet:
                    print(f"✅ Configuration template generated: {args.output}")
                    if not args.example:
                        print("💡 Use --example flag to generate with sample values")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Configuration generation failed: {e}")
            print(f"❌ Configuration generation failed: {e}")
            return 1
    
    def generate_config_template(self, method: str, with_examples: bool = False) -> OnPremiseConfig:
        """Generate configuration template."""
        if with_examples:
            # Configuration with example values
            config_data = {
                "deployment_method": method,
                "meilisearch_config": {
                    "host": "http://localhost:7700",
                    "port": 7700,
                    "api_key": "your-meilisearch-api-key",
                    "ssl_enabled": False,
                    "ssl_verify": True,
                    "timeout_seconds": 30,
                    "max_retries": 3,
                    "retry_delay_seconds": 1.0
                },
                "service_config": {
                    "service_name": f"thai-tokenizer-{method}",
                    "service_port": 8000,
                    "service_host": "0.0.0.0",
                    "worker_processes": 2,
                    "service_user": "thai-tokenizer",
                    "service_group": "thai-tokenizer"
                },
                "security_config": {
                    "security_level": "standard",
                    "allowed_hosts": ["localhost", "127.0.0.1"],
                    "cors_origins": ["http://localhost:3000"],
                    "api_key_required": False,
                    "enable_https": False
                },
                "resource_config": {
                    "memory_limit_mb": 256,
                    "cpu_limit_cores": 0.5,
                    "max_concurrent_requests": 50,
                    "request_timeout_seconds": 30,
                    "enable_metrics": True,
                    "metrics_port": 9000
                },
                "monitoring_config": {
                    "enable_health_checks": True,
                    "health_check_interval_seconds": 30,
                    "enable_logging": True,
                    "log_level": "INFO",
                    "enable_prometheus": False,
                    "prometheus_port": 9000
                },
                "installation_path": f"/opt/thai-tokenizer" if method == "systemd" else f"./thai-tokenizer-{method}",
                "data_path": f"/opt/thai-tokenizer/data" if method == "systemd" else f"./thai-tokenizer-{method}/data",
                "log_path": f"/opt/thai-tokenizer/logs" if method == "systemd" else f"./thai-tokenizer-{method}/logs",
                "config_path": f"/opt/thai-tokenizer/config" if method == "systemd" else f"./thai-tokenizer-{method}/config",
                "environment_variables": {
                    "PYTHONPATH": "src",
                    "LOG_LEVEL": "INFO"
                }
            }
        else:
            # Minimal template configuration
            config_data = {
                "deployment_method": method,
                "meilisearch_config": {
                    "host": "http://localhost:7700",
                    "port": 7700,
                    "api_key": None
                }
            }
        
        return OnPremiseConfig(**config_data)
    
    async def handle_validate_config_command(self, args) -> int:
        """Handle validate-config command."""
        try:
            if not args.config:
                print("Error: --config is required for config validation")
                return 1
            
            print("🔍 Validating configuration...")
            
            # Load and validate configuration
            self.config = self.load_config(args.config)
            
            # Perform validation
            validation_result = self.config.validate_paths()
            
            if validation_result.valid:
                print("✅ Configuration is valid")
                
                if validation_result.warnings:
                    print("\n⚠️  Warnings:")
                    for warning in validation_result.warnings:
                        print(f"  - {warning}")
                
                return 0
            else:
                print("❌ Configuration validation failed")
                print("\nErrors:")
                for error in validation_result.errors:
                    print(f"  - {error}")
                
                if args.fix:
                    print("\n🔧 Attempting to fix configuration issues...")
                    # Implement basic fixes here
                    print("Configuration fixes not yet implemented")
                
                return 1
                
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            print(f"❌ Configuration validation failed: {e}")
            return 1
    
    async def handle_validate_meilisearch_command(self, args) -> int:
        """Handle validate-meilisearch command."""
        try:
            # Use provided host/key or load from config
            if args.host or args.api_key:
                from deployment.config import MeilisearchConfig
                ms_config = MeilisearchConfig(
                    host=args.host or "http://localhost:7700",
                    port=int(args.host.split(':')[-1]) if args.host and ':' in args.host else 7700,
                    api_key=args.api_key
                )
                
                # Create minimal config for testing
                self.config = OnPremiseConfig(
                    deployment_method="docker",
                    meilisearch_config=ms_config
                )
            elif args.config:
                self.config = self.load_config(args.config)
            else:
                print("Error: Either --config or --host must be specified")
                return 1
            
            print("🔍 Testing Meilisearch connectivity...")
            
            from deployment.validation_framework import MeilisearchConnectivityTester
            tester = MeilisearchConnectivityTester(self.config)
            
            # Test basic connectivity
            basic_result = await tester.test_basic_connectivity()
            if basic_result.valid:
                print("✅ Basic connectivity: OK")
            else:
                print("❌ Basic connectivity: FAILED")
                for error in basic_result.errors:
                    print(f"  - {error}")
                return 1
            
            # Test API permissions
            api_result = await tester.test_api_permissions()
            if api_result.valid:
                print("✅ API permissions: OK")
            else:
                print("⚠️  API permissions: LIMITED")
                for warning in api_result.warnings:
                    print(f"  - {warning}")
            
            # Test index operations
            index_result = await tester.test_index_operations()
            if index_result.valid:
                print("✅ Index operations: OK")
            else:
                print("❌ Index operations: FAILED")
                for error in index_result.errors:
                    print(f"  - {error}")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Meilisearch validation failed: {e}")
            print(f"❌ Meilisearch validation failed: {e}")
            return 1
    
    async def handle_status_command(self, args) -> int:
        """Handle status command."""
        try:
            # Load deployment info
            deployment_info = None
            
            if args.deployment_id:
                # Look for deployment result file
                result_files = list(Path(".").glob(f"**/deployment_result.json"))
                for result_file in result_files:
                    with open(result_file, 'r') as f:
                        data = json.load(f)
                        if data.get("deployment_id") == args.deployment_id:
                            deployment_info = data
                            break
            
            if args.service_name or not deployment_info:
                # Check service status directly
                service_name = args.service_name or "thai-tokenizer"
                print(f"🔍 Checking status for service: {service_name}")
                
                # Try to determine service type and check status
                status_info = await self.check_service_status(service_name)
                
                if status_info:
                    print(f"Service Status: {status_info['status']}")
                    if args.detailed:
                        for key, value in status_info.items():
                            if key != 'status':
                                print(f"  {key}: {value}")
                else:
                    print("❌ Service not found or not accessible")
                    return 1
            
            if deployment_info:
                print(f"📋 Deployment Information")
                print(f"  ID: {deployment_info['deployment_id']}")
                print(f"  Method: {deployment_info['deployment_method']}")
                print(f"  Status: {'✅ Active' if deployment_info['success'] else '❌ Failed'}")
                
                if deployment_info.get('endpoints'):
                    print("  Endpoints:")
                    for name, url in deployment_info['endpoints'].items():
                        print(f"    {name}: {url}")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")
            print(f"❌ Status check failed: {e}")
            return 1
    
    async def check_service_status(self, service_name: str) -> Optional[Dict[str, Any]]:
        """Check service status across different deployment methods."""
        import subprocess
        
        # Try systemd first
        try:
            result = subprocess.run(
                ["systemctl", "is-active", service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                return {
                    "status": "active (systemd)",
                    "type": "systemd",
                    "active": True
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Try Docker
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={service_name}", "--format", "{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                return {
                    "status": f"running (docker): {result.stdout.strip()}",
                    "type": "docker",
                    "active": True
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Try process check
        try:
            result = subprocess.run(
                ["pgrep", "-f", service_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and result.stdout.strip():
                pids = result.stdout.strip().split('\n')
                return {
                    "status": f"running (process): {len(pids)} processes",
                    "type": "process",
                    "pids": pids,
                    "active": True
                }
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        return None
    
    async def handle_test_command(self, args) -> int:
        """Handle test command."""
        try:
            # Determine service URL
            service_url = args.service_url
            if not service_url:
                if args.config:
                    self.config = self.load_config(args.config)
                    service_url = f"http://localhost:{self.config.service_config.service_port}"
                else:
                    service_url = "http://localhost:8000"
            
            print(f"🧪 Testing service at: {service_url}")
            
            # Import test modules
            if args.test_type in ['health', 'all']:
                success = await self.test_service_health(service_url)
                if not success and args.test_type == 'health':
                    return 1
            
            if args.test_type in ['tokenization', 'all']:
                success = await self.test_tokenization(service_url)
                if not success and args.test_type == 'tokenization':
                    return 1
            
            if args.test_type in ['performance', 'all']:
                success = await self.test_performance(service_url)
                if not success and args.test_type == 'performance':
                    return 1
            
            if args.test_type in ['security', 'all']:
                success = await self.test_security(service_url)
                if not success and args.test_type == 'security':
                    return 1
            
            print("✅ All tests completed successfully")
            return 0
            
        except Exception as e:
            self.logger.error(f"Testing failed: {e}")
            print(f"❌ Testing failed: {e}")
            return 1
    
    async def test_service_health(self, service_url: str) -> bool:
        """Test service health endpoints."""
        try:
            import httpx
            
            print("  🏥 Testing health endpoints...")
            
            async with httpx.AsyncClient() as client:
                # Test basic health
                response = await client.get(f"{service_url}/health", timeout=10.0)
                if response.status_code == 200:
                    print("    ✅ Basic health check: OK")
                else:
                    print(f"    ❌ Basic health check: HTTP {response.status_code}")
                    return False
                
                # Test detailed health if available
                try:
                    response = await client.get(f"{service_url}/health/detailed", timeout=10.0)
                    if response.status_code == 200:
                        print("    ✅ Detailed health check: OK")
                    else:
                        print("    ⚠️  Detailed health check: Not available")
                except:
                    print("    ⚠️  Detailed health check: Not available")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Health check failed: {e}")
            return False
    
    async def test_tokenization(self, service_url: str) -> bool:
        """Test Thai tokenization functionality."""
        try:
            import httpx
            
            print("  🔤 Testing Thai tokenization...")
            
            test_cases = [
                "สวัสดีครับ",
                "สาหร่ายวากาเมะเป็นสาหร่ายทะเล",
                "การพัฒนาเทคโนโลยีปัญญาประดิษฐ์"
            ]
            
            async with httpx.AsyncClient() as client:
                for i, text in enumerate(test_cases, 1):
                    response = await client.post(
                        f"{service_url}/v1/tokenize",
                        json={"text": text},
                        timeout=30.0
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        token_count = len(data.get("tokens", []))
                        processing_time = data.get("processing_time_ms", 0)
                        print(f"    ✅ Test {i}: {token_count} tokens in {processing_time:.1f}ms")
                    else:
                        print(f"    ❌ Test {i}: HTTP {response.status_code}")
                        return False
            
            return True
            
        except Exception as e:
            print(f"    ❌ Tokenization test failed: {e}")
            return False
    
    async def test_performance(self, service_url: str) -> bool:
        """Test service performance."""
        try:
            import httpx
            import time
            
            print("  ⚡ Testing performance...")
            
            test_text = "สาหร่ายวากาเมะเป็นสาหร่ายทะเลจากญี่ปุ่นที่มีรสชาติหวานเล็กน้อย"
            response_times = []
            
            async with httpx.AsyncClient() as client:
                for i in range(5):
                    start_time = time.time()
                    
                    response = await client.post(
                        f"{service_url}/v1/tokenize",
                        json={"text": test_text},
                        timeout=30.0
                    )
                    
                    end_time = time.time()
                    response_time = (end_time - start_time) * 1000
                    
                    if response.status_code == 200:
                        response_times.append(response_time)
                    else:
                        print(f"    ❌ Performance test failed: HTTP {response.status_code}")
                        return False
            
            avg_time = sum(response_times) / len(response_times)
            max_time = max(response_times)
            
            print(f"    ✅ Average response time: {avg_time:.1f}ms")
            print(f"    ✅ Maximum response time: {max_time:.1f}ms")
            
            if avg_time > 100:
                print("    ⚠️  Average response time exceeds 100ms")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Performance test failed: {e}")
            return False
    
    async def test_security(self, service_url: str) -> bool:
        """Test security configuration."""
        try:
            import httpx
            
            print("  🔒 Testing security configuration...")
            
            async with httpx.AsyncClient() as client:
                # Test CORS
                response = await client.options(
                    f"{service_url}/v1/tokenize",
                    headers={"Origin": "http://localhost:3000"},
                    timeout=10.0
                )
                
                if response.status_code in [200, 204]:
                    print("    ✅ CORS configuration: OK")
                else:
                    print("    ⚠️  CORS configuration: May need review")
                
                # Test invalid input handling
                response = await client.post(
                    f"{service_url}/v1/tokenize",
                    json={"invalid": "data"},
                    timeout=10.0
                )
                
                if response.status_code in [400, 422]:
                    print("    ✅ Input validation: OK")
                else:
                    print("    ⚠️  Input validation: May need review")
            
            return True
            
        except Exception as e:
            print(f"    ❌ Security test failed: {e}")
            return False
    
    async def handle_show_config_command(self, args) -> int:
        """Handle show-config command."""
        try:
            if not args.config:
                print("Error: --config is required")
                return 1
            
            self.config = self.load_config(args.config)
            
            if args.format == 'json':
                config_dict = self.config.dict()
                if args.mask_secrets:
                    config_dict = self.mask_sensitive_data(config_dict)
                print(json.dumps(config_dict, indent=2, ensure_ascii=False))
            
            elif args.format == 'yaml':
                import yaml
                config_dict = self.config.dict()
                if args.mask_secrets:
                    config_dict = self.mask_sensitive_data(config_dict)
                print(yaml.dump(config_dict, default_flow_style=False, allow_unicode=True))
            
            elif args.format == 'table':
                self.print_config_table(self.config, args.mask_secrets)
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Show config failed: {e}")
            print(f"❌ Show config failed: {e}")
            return 1
    
    def mask_sensitive_data(self, config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive information in configuration."""
        import copy
        masked_config = copy.deepcopy(config_dict)
        
        # Mask API keys and passwords
        sensitive_keys = ['api_key', 'password', 'secret', 'token']
        
        def mask_recursive(obj):
            if isinstance(obj, dict):
                for key, value in obj.items():
                    if any(sensitive in key.lower() for sensitive in sensitive_keys):
                        if value:
                            obj[key] = "***MASKED***"
                    else:
                        mask_recursive(value)
            elif isinstance(obj, list):
                for item in obj:
                    mask_recursive(item)
        
        mask_recursive(masked_config)
        return masked_config
    
    def print_config_table(self, config: OnPremiseConfig, mask_secrets: bool = False):
        """Print configuration in table format."""
        print("📋 Deployment Configuration")
        print("=" * 50)
        
        sections = [
            ("General", {
                "Deployment Method": config.deployment_method.value,
                "Installation Path": config.installation_path,
                "Data Path": config.data_path,
                "Log Path": config.log_path,
                "Config Path": config.config_path
            }),
            ("Meilisearch", {
                "Host": config.meilisearch_config.host,
                "Port": config.meilisearch_config.port,
                "API Key": "***MASKED***" if mask_secrets and config.meilisearch_config.api_key else config.meilisearch_config.api_key,
                "SSL Enabled": config.meilisearch_config.ssl_enabled,
                "Timeout": f"{config.meilisearch_config.timeout_seconds}s"
            }),
            ("Service", {
                "Name": config.service_config.service_name,
                "Host": config.service_config.service_host,
                "Port": config.service_config.service_port,
                "Workers": config.service_config.worker_processes,
                "User": config.service_config.service_user
            }),
            ("Security", {
                "Level": config.security_config.security_level,
                "API Key Required": config.security_config.api_key_required,
                "HTTPS Enabled": config.security_config.enable_https,
                "Allowed Hosts": ", ".join(config.security_config.allowed_hosts[:3]) + ("..." if len(config.security_config.allowed_hosts) > 3 else "")
            }),
            ("Resources", {
                "Memory Limit": f"{config.resource_config.memory_limit_mb}MB",
                "CPU Limit": f"{config.resource_config.cpu_limit_cores} cores",
                "Max Requests": config.resource_config.max_concurrent_requests,
                "Request Timeout": f"{config.resource_config.request_timeout_seconds}s"
            })
        ]
        
        for section_name, section_data in sections:
            print(f"\n{section_name}:")
            for key, value in section_data.items():
                print(f"  {key:<20}: {value}")
    
    async def run(self, args: List[str] = None) -> int:
        """Run the CLI with given arguments."""
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        # Setup logging
        self.setup_logging(parsed_args)
        
        # Handle commands
        if not parsed_args.command:
            parser.print_help()
            return 1
        
        try:
            if parsed_args.command == 'deploy':
                return await self.handle_deploy_command(parsed_args)
            elif parsed_args.command == 'validate-system':
                return await self.handle_validate_system_command(parsed_args)
            elif parsed_args.command == 'validate-config':
                return await self.handle_validate_config_command(parsed_args)
            elif parsed_args.command == 'validate-meilisearch':
                return await self.handle_validate_meilisearch_command(parsed_args)
            elif parsed_args.command == 'generate-config':
                return await self.handle_generate_config_command(parsed_args)
            elif parsed_args.command == 'show-config':
                return await self.handle_show_config_command(parsed_args)
            elif parsed_args.command == 'status':
                return await self.handle_status_command(parsed_args)
            elif parsed_args.command == 'test':
                return await self.handle_test_command(parsed_args)
            elif parsed_args.command == 'version':
                return self.handle_version_command(parsed_args)
            else:
                print(f"Command '{parsed_args.command}' not yet implemented")
                return 1
                
        except KeyboardInterrupt:
            print("\n⚠️  Operation cancelled by user")
            return 130
        except Exception as e:
            self.logger.error(f"Unexpected error: {e}")
            print(f"❌ Unexpected error: {e}")
            return 1
    
    def handle_version_command(self, args) -> int:
        """Handle version command."""
        version_info = {
            "version": "1.0.0",
            "build_date": "2024-01-01",
            "python_version": sys.version,
            "platform": sys.platform
        }
        
        if args.detailed:
            print("Thai Tokenizer Deployment Tool")
            print("=" * 35)
            for key, value in version_info.items():
                print(f"{key.replace('_', ' ').title()}: {value}")
        else:
            print(f"thai-tokenizer-deploy {version_info['version']}")
        
        return 0


async def main():
    """Main CLI entry point."""
    cli = DeploymentCLI()
    return await cli.run()


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))