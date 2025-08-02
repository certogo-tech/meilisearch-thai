#!/usr/bin/env python3
"""
Command-line interface for Thai Tokenizer deployment orchestration system.

This CLI provides access to the deployment manager and validation framework
for comprehensive on-premise deployment management.
"""

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any

try:
    from src.deployment.config import OnPremiseConfig, DeploymentMethod
    from src.deployment.deployment_manager import DeploymentManager, DeploymentProgress
    from src.deployment.validation_framework import DeploymentValidationFramework
    from src.utils.logging import get_structured_logger
except ImportError:
    # Fallback for when running outside the main application
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class DeploymentCLI:
    """Command-line interface for deployment orchestration."""
    
    def __init__(self):
        self.logger = get_structured_logger(f"{__name__}.DeploymentCLI")
    
    def create_parser(self) -> argparse.ArgumentParser:
        """Create command-line argument parser."""
        parser = argparse.ArgumentParser(
            description="Thai Tokenizer Deployment Orchestration System",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Validate system requirements
  python -m src.deployment.cli validate-system --config config.json
  
  # Deploy using Docker method
  python -m src.deployment.cli deploy --config config.json --method docker
  
  # Run comprehensive validation
  python -m src.deployment.cli validate-deployment --config config.json --service-url http://localhost:8000
  
  # Check deployment status
  python -m src.deployment.cli status --deployment-id deploy_1234567890
            """
        )
        
        parser.add_argument(
            "--config",
            type=str,
            required=True,
            help="Path to deployment configuration file (JSON)"
        )
        
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Enable verbose logging"
        )
        
        parser.add_argument(
            "--output",
            type=str,
            help="Output file for results (JSON format)"
        )
        
        subparsers = parser.add_subparsers(dest="command", help="Available commands")
        
        # Validate system command
        validate_system_parser = subparsers.add_parser(
            "validate-system",
            help="Validate system requirements"
        )
        
        # Deploy command
        deploy_parser = subparsers.add_parser(
            "deploy",
            help="Deploy Thai Tokenizer service"
        )
        deploy_parser.add_argument(
            "--method",
            type=str,
            choices=["docker", "systemd", "standalone"],
            help="Override deployment method from config"
        )
        deploy_parser.add_argument(
            "--progress-file",
            type=str,
            help="File to write deployment progress updates"
        )
        
        # Validate deployment command
        validate_deployment_parser = subparsers.add_parser(
            "validate-deployment",
            help="Run comprehensive deployment validation"
        )
        validate_deployment_parser.add_argument(
            "--service-url",
            type=str,
            help="Service URL for post-deployment validation"
        )
        validate_deployment_parser.add_argument(
            "--report-file",
            type=str,
            help="File to save validation report"
        )
        
        # Status command
        status_parser = subparsers.add_parser(
            "status",
            help="Check deployment status"
        )
        status_parser.add_argument(
            "--deployment-id",
            type=str,
            help="Deployment ID to check status for"
        )
        
        # Stop command
        stop_parser = subparsers.add_parser(
            "stop",
            help="Stop deployed service"
        )
        
        # Rollback command
        rollback_parser = subparsers.add_parser(
            "rollback",
            help="Rollback deployment"
        )
        
        return parser
    
    def load_config(self, config_path: str) -> OnPremiseConfig:
        """Load deployment configuration from file."""
        try:
            config_file = Path(config_path)
            if not config_file.exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            # Convert to OnPremiseConfig
            config = OnPremiseConfig(**config_data)
            
            self.logger.info(f"Loaded configuration from {config_path}")
            return config
            
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            raise
    
    def save_output(self, data: Dict[str, Any], output_path: str):
        """Save output data to file."""
        try:
            output_file = Path(output_path)
            output_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2, default=str)
            
            self.logger.info(f"Output saved to {output_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save output: {e}")
    
    def progress_callback(self, progress: DeploymentProgress, progress_file: Optional[str] = None):
        """Handle deployment progress updates."""
        progress_data = progress.dict()
        
        # Log progress
        current_step = progress.current_step
        if current_step:
            self.logger.info(
                f"Deployment Progress: {progress.progress_percentage:.1f}% - "
                f"{current_step.name} ({current_step.status.value})"
            )
        
        # Save to file if specified
        if progress_file:
            try:
                with open(progress_file, 'w') as f:
                    json.dump(progress_data, f, indent=2, default=str)
            except Exception as e:
                self.logger.warning(f"Failed to save progress to file: {e}")
    
    async def cmd_validate_system(self, args) -> int:
        """Handle validate-system command."""
        try:
            config = self.load_config(args.config)
            
            # Create validation framework
            validator = DeploymentValidationFramework(config)
            
            # Run system requirements validation only
            requirements_results = await validator.requirements_validator.validate_all_requirements(config)
            
            # Prepare output
            output_data = {
                "command": "validate-system",
                "timestamp": validator._generate_validation_summary({"system_requirements": [r.dict() for r in requirements_results]})["timestamp"] if hasattr(validator, "_generate_validation_summary") else None,
                "config": {
                    "deployment_method": config.deployment_method.value,
                    "service_name": config.service_config.service_name,
                },
                "system_requirements": [result.dict() for result in requirements_results],
                "summary": {
                    "total_checks": len(requirements_results),
                    "passed_checks": sum(1 for r in requirements_results if r.satisfied),
                    "failed_checks": sum(1 for r in requirements_results if not r.satisfied),
                    "critical_issues": [
                        r.error_message for r in requirements_results 
                        if not r.satisfied and r.requirement.required
                    ]
                }
            }
            
            # Print summary
            summary = output_data["summary"]
            print(f"\nSystem Requirements Validation Results:")
            print(f"  Total Checks: {summary['total_checks']}")
            print(f"  Passed: {summary['passed_checks']}")
            print(f"  Failed: {summary['failed_checks']}")
            
            if summary["critical_issues"]:
                print(f"\nCritical Issues:")
                for issue in summary["critical_issues"]:
                    print(f"  ❌ {issue}")
                print(f"\n⚠️  Address critical issues before deployment!")
                return_code = 1
            else:
                print(f"\n✅ System requirements validation passed!")
                return_code = 0
            
            # Save output if requested
            if args.output:
                self.save_output(output_data, args.output)
            
            return return_code
            
        except Exception as e:
            self.logger.error(f"System validation failed: {e}")
            return 1
    
    async def cmd_deploy(self, args) -> int:
        """Handle deploy command."""
        try:
            config = self.load_config(args.config)
            
            # Override deployment method if specified
            if args.method:
                config.deployment_method = DeploymentMethod(args.method)
            
            # Create progress callback
            progress_callback = None
            if args.progress_file:
                progress_callback = lambda p: self.progress_callback(p, args.progress_file)
            else:
                progress_callback = self.progress_callback
            
            # Create deployment manager
            deployment_manager = DeploymentManager(config, progress_callback)
            
            print(f"Starting deployment using {config.deployment_method.value} method...")
            
            # Execute deployment
            result = await deployment_manager.deploy()
            
            # Prepare output
            output_data = {
                "command": "deploy",
                "result": result.dict(),
            }
            
            # Print results
            print(f"\nDeployment Result: {result.summary}")
            
            if result.success:
                print(f"✅ Deployment completed successfully!")
                print(f"   Deployment ID: {result.deployment_id}")
                print(f"   Service Endpoints:")
                for name, url in result.endpoints.items():
                    print(f"     {name}: {url}")
                return_code = 0
            else:
                print(f"❌ Deployment failed!")
                
                # Show failed steps
                failed_steps = [
                    step for step in result.progress.steps 
                    if step.status.value == "failed"
                ]
                
                if failed_steps:
                    print(f"   Failed Steps:")
                    for step in failed_steps:
                        print(f"     - {step.name}: {step.error_message}")
                
                return_code = 1
            
            # Save output if requested
            if args.output:
                self.save_output(output_data, args.output)
            
            return return_code
            
        except Exception as e:
            self.logger.error(f"Deployment failed: {e}")
            return 1
    
    async def cmd_validate_deployment(self, args) -> int:
        """Handle validate-deployment command."""
        try:
            config = self.load_config(args.config)
            
            # Create validation framework
            validator = DeploymentValidationFramework(config)
            
            print(f"Running comprehensive deployment validation...")
            
            # Run comprehensive validation
            validation_results = await validator.run_comprehensive_validation(args.service_url)
            
            # Generate report if requested
            if args.report_file:
                report_content = await validator.generate_validation_report(
                    validation_results, args.report_file
                )
                print(f"Validation report saved to: {args.report_file}")
            
            # Prepare output
            output_data = {
                "command": "validate-deployment",
                "validation_results": validation_results,
            }
            
            # Print summary
            summary = validation_results.get("summary", {})
            overall_status = validation_results.get("overall_status", "unknown")
            
            print(f"\nDeployment Validation Results:")
            print(f"  Overall Status: {overall_status.upper()}")
            print(f"  Total Checks: {summary.get('total_checks', 0)}")
            print(f"  Passed: {summary.get('passed_checks', 0)}")
            print(f"  Failed: {summary.get('failed_checks', 0)}")
            
            if summary.get("critical_issues"):
                print(f"\nCritical Issues:")
                for issue in summary["critical_issues"]:
                    print(f"  ❌ {issue}")
                return_code = 1
            elif overall_status == "passed":
                print(f"\n✅ Deployment validation passed!")
                return_code = 0
            else:
                print(f"\n⚠️  Deployment validation completed with warnings")
                return_code = 0
            
            # Save output if requested
            if args.output:
                self.save_output(output_data, args.output)
            
            return return_code
            
        except Exception as e:
            self.logger.error(f"Deployment validation failed: {e}")
            return 1
    
    async def cmd_status(self, args) -> int:
        """Handle status command."""
        try:
            config = self.load_config(args.config)
            
            # This is a simplified status check
            # In a real implementation, you'd track deployment state
            print(f"Deployment status checking is not fully implemented in this demo")
            print(f"Configuration loaded for: {config.service_config.service_name}")
            
            return 0
            
        except Exception as e:
            self.logger.error(f"Status check failed: {e}")
            return 1
    
    async def cmd_stop(self, args) -> int:
        """Handle stop command."""
        try:
            config = self.load_config(args.config)
            
            # Create deployment manager
            deployment_manager = DeploymentManager(config)
            
            print(f"Stopping deployment...")
            
            # Stop deployment
            result = await deployment_manager.stop_deployment()
            
            if result.valid:
                print(f"✅ Deployment stopped successfully!")
                return_code = 0
            else:
                print(f"❌ Failed to stop deployment!")
                for error in result.errors:
                    print(f"   Error: {error}")
                return_code = 1
            
            return return_code
            
        except Exception as e:
            self.logger.error(f"Stop command failed: {e}")
            return 1
    
    async def cmd_rollback(self, args) -> int:
        """Handle rollback command."""
        try:
            config = self.load_config(args.config)
            
            # Create deployment manager
            deployment_manager = DeploymentManager(config)
            
            print(f"Rolling back deployment...")
            
            # Rollback deployment
            result = await deployment_manager.rollback()
            
            if result.valid:
                print(f"✅ Deployment rolled back successfully!")
                return_code = 0
            else:
                print(f"❌ Failed to rollback deployment!")
                for error in result.errors:
                    print(f"   Error: {error}")
                return_code = 1
            
            return return_code
            
        except Exception as e:
            self.logger.error(f"Rollback command failed: {e}")
            return 1
    
    async def run(self, args) -> int:
        """Run the CLI with parsed arguments."""
        # Configure logging
        log_level = logging.DEBUG if args.verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Dispatch to command handler
        if args.command == "validate-system":
            return await self.cmd_validate_system(args)
        elif args.command == "deploy":
            return await self.cmd_deploy(args)
        elif args.command == "validate-deployment":
            return await self.cmd_validate_deployment(args)
        elif args.command == "status":
            return await self.cmd_status(args)
        elif args.command == "stop":
            return await self.cmd_stop(args)
        elif args.command == "rollback":
            return await self.cmd_rollback(args)
        else:
            print("No command specified. Use --help for usage information.")
            return 1


async def main():
    """Main entry point."""
    cli = DeploymentCLI()
    parser = cli.create_parser()
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    try:
        return await cli.run(args)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        return 130
    except Exception as e:
        print(f"Unexpected error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))