#!/usr/bin/env python3
"""
Demonstration of the deployment configuration management system.

This script shows how to use the OnPremiseConfig system to create and validate
deployment configurations for different methods (Docker, systemd, standalone).
"""

import asyncio
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from deployment.config import (
    OnPremiseConfig,
    DeploymentMethod,
    MeilisearchConnectionConfig,
    SecurityLevel,
    MeilisearchConnectionTester,
    ConfigurationValidator
)
from deployment.templates import DeploymentTemplates, ConfigurationExporter


async def demo_docker_deployment():
    """Demonstrate Docker deployment configuration."""
    print("=== Docker Deployment Configuration ===")
    
    # Create Docker configuration template
    config = DeploymentTemplates.create_docker_template(
        meilisearch_host="http://localhost:7700",
        meilisearch_api_key="your-api-key-here",
        service_port=8000,
        security_level=SecurityLevel.STANDARD
    )
    
    print(f"Deployment Method: {config.deployment_method.value}")
    print(f"Service Port: {config.service_config.service_port}")
    print(f"Meilisearch Host: {config.meilisearch_config.host}")
    print(f"Security Level: {config.security_config.security_level.value}")
    print(f"Memory Limit: {config.resource_config.memory_limit_mb}MB")
    print(f"CPU Limit: {config.resource_config.cpu_limit_cores} cores")
    
    # Export as Docker Compose
    compose_content = ConfigurationExporter.to_docker_compose(config)
    print("\nDocker Compose Preview:")
    print(compose_content[:500] + "..." if len(compose_content) > 500 else compose_content)
    
    return config


async def demo_systemd_deployment():
    """Demonstrate systemd deployment configuration."""
    print("\n=== Systemd Deployment Configuration ===")
    
    # Create systemd configuration template
    config = DeploymentTemplates.create_systemd_template(
        meilisearch_host="https://meilisearch.example.com",
        meilisearch_api_key="production-api-key",
        service_port=8080,
        security_level=SecurityLevel.HIGH
    )
    
    print(f"Deployment Method: {config.deployment_method.value}")
    print(f"Service Host: {config.service_config.service_host}")
    print(f"Installation Path: {config.installation_path}")
    print(f"Log Path: {config.log_path}")
    print(f"API Key Required: {config.security_config.api_key_required}")
    print(f"HTTPS Enabled: {config.security_config.enable_https}")
    
    # Export as systemd unit file
    unit_content = ConfigurationExporter.to_systemd_unit(config)
    print("\nSystemd Unit File Preview:")
    print(unit_content[:500] + "..." if len(unit_content) > 500 else unit_content)
    
    return config


async def demo_standalone_deployment():
    """Demonstrate standalone deployment configuration."""
    print("\n=== Standalone Deployment Configuration ===")
    
    # Create standalone configuration template
    config = DeploymentTemplates.create_standalone_template(
        meilisearch_host="http://192.168.1.100:7700",
        meilisearch_api_key="dev-api-key",
        service_port=8000,
        security_level=SecurityLevel.BASIC
    )
    
    print(f"Deployment Method: {config.deployment_method.value}")
    print(f"Worker Processes: {config.service_config.worker_processes}")
    print(f"Max Concurrent Requests: {config.resource_config.max_concurrent_requests}")
    print(f"Metrics Enabled: {config.resource_config.enable_metrics}")
    print(f"Prometheus Enabled: {config.monitoring_config.enable_prometheus}")
    
    # Export as environment file
    env_content = ConfigurationExporter.to_env_file(config)
    print("\nEnvironment File Preview:")
    lines = env_content.split('\n')[:15]  # Show first 15 lines
    print('\n'.join(lines) + "\n...")
    
    return config


async def demo_connection_testing(config: OnPremiseConfig):
    """Demonstrate Meilisearch connection testing."""
    print(f"\n=== Connection Testing for {config.deployment_method.value} ===")
    
    # Create connection tester
    tester = MeilisearchConnectionTester(config.meilisearch_config)
    
    print(f"Testing connection to: {config.meilisearch_config.full_url}")
    
    # Test connection (this will likely fail in demo since Meilisearch isn't running)
    try:
        result = await tester.test_connection()
        print(f"Connection Status: {result.status.value}")
        if result.response_time_ms:
            print(f"Response Time: {result.response_time_ms:.2f}ms")
        if result.error_message:
            print(f"Error: {result.error_message}")
        if result.meilisearch_version:
            print(f"Meilisearch Version: {result.meilisearch_version}")
    except Exception as e:
        print(f"Connection test failed: {e}")


async def demo_configuration_validation(config: OnPremiseConfig):
    """Demonstrate configuration validation."""
    print(f"\n=== Configuration Validation for {config.deployment_method.value} ===")
    
    # Create validator
    validator = ConfigurationValidator(config)
    
    try:
        # Run comprehensive validation
        result = await validator.validate_full_configuration()
        
        print(f"Configuration Valid: {result.valid}")
        
        if result.errors:
            print("Errors:")
            for error in result.errors:
                print(f"  - {error}")
        
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"  - {warning}")
        
        if not result.errors and not result.warnings:
            print("No validation issues found!")
            
    except Exception as e:
        print(f"Validation failed: {e}")


async def demo_environment_variables(config: OnPremiseConfig):
    """Demonstrate environment variable generation."""
    print(f"\n=== Environment Variables for {config.deployment_method.value} ===")
    
    env_vars = config.get_environment_dict()
    
    # Show key environment variables
    key_vars = [
        "THAI_TOKENIZER_SERVICE_NAME",
        "THAI_TOKENIZER_SERVICE_PORT",
        "THAI_TOKENIZER_MEILISEARCH_HOST",
        "THAI_TOKENIZER_MEMORY_LIMIT_MB",
        "THAI_TOKENIZER_LOG_LEVEL"
    ]
    
    for var in key_vars:
        if var in env_vars:
            value = env_vars[var]
            # Mask sensitive values
            if "api_key" in var.lower():
                value = "***MASKED***"
            print(f"{var}={value}")
    
    print(f"Total environment variables: {len(env_vars)}")


async def main():
    """Run all demonstrations."""
    print("Thai Tokenizer Deployment Configuration System Demo")
    print("=" * 60)
    
    # Demo different deployment methods
    docker_config = await demo_docker_deployment()
    systemd_config = await demo_systemd_deployment()
    standalone_config = await demo_standalone_deployment()
    
    # Demo connection testing (pick one config)
    await demo_connection_testing(docker_config)
    
    # Demo configuration validation
    await demo_configuration_validation(docker_config)
    await demo_configuration_validation(systemd_config)
    
    # Demo environment variables
    await demo_environment_variables(standalone_config)
    
    # Show template recommendations
    print("\n=== Deployment Method Recommendations ===")
    recommendations = DeploymentTemplates.get_template_recommendations()
    
    for method, info in recommendations.items():
        print(f"\n{info['name']}:")
        print(f"  Description: {info['description']}")
        print(f"  Best for: {', '.join(info['best_for'][:2])}...")
        print(f"  Pros: {', '.join(info['pros'][:2])}...")
    
    print("\n" + "=" * 60)
    print("Demo completed! Check the generated configuration files.")


if __name__ == "__main__":
    asyncio.run(main())