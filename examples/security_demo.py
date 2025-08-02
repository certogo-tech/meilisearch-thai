#!/usr/bin/env python3
"""
Security Implementation Demo

This script demonstrates the comprehensive security features implemented
for on-premise deployment of the Thai Tokenizer service.

Usage:
    python examples/security_demo.py
"""

import os
import sys
import tempfile
from pathlib import Path
from pydantic import SecretStr

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from deployment.config import (
    OnPremiseConfig,
    SecurityConfig,
    SecurityLevel,
    DeploymentMethod,
    MeilisearchConnectionConfig,
    ServiceConfig
)


def create_demo_config() -> OnPremiseConfig:
    """Create a demonstration configuration."""
    print("🔧 Creating demonstration configuration...")
    
    config = OnPremiseConfig(
        deployment_method=DeploymentMethod.DOCKER,
        meilisearch_config=MeilisearchConnectionConfig(
            host="http://localhost:7700",
            api_key=SecretStr("demo_meilisearch_api_key_12345"),
            ssl_enabled=False,
            timeout_seconds=30
        ),
        service_config=ServiceConfig(
            service_name="thai-tokenizer-demo",
            service_port=8000,
            worker_processes=2
        ),
        security_config=SecurityConfig(
            security_level=SecurityLevel.STANDARD,
            allowed_hosts=["localhost", "127.0.0.1"],
            cors_origins=["http://localhost:3000"],
            api_key_required=True,
            api_key=SecretStr("demo_service_api_key_67890"),
            enable_https=False,
            firewall_rules=[
                "allow tcp 8000 from 192.168.1.0/24 comment 'Thai Tokenizer Demo'"
            ]
        ),
        config_path="/tmp/thai-tokenizer-demo/config",
        data_path="/tmp/thai-tokenizer-demo/data",
        log_path="/tmp/thai-tokenizer-demo/logs"
    )
    
    print(f"✅ Configuration created with security level: {config.security_config.security_level.value}")
    return config


def demonstrate_configuration_validation(config: OnPremiseConfig):
    """Demonstrate configuration validation."""
    print("\n🔍 Demonstrating configuration validation...")
    
    try:
        from deployment.config import ConfigurationValidator
        
        validator = ConfigurationValidator(config)
        
        # Note: This would normally test Meilisearch connection, but we'll skip for demo
        print("✅ Configuration validator initialized")
        print(f"   - Deployment method: {config.deployment_method.value}")
        print(f"   - Security level: {config.security_config.security_level.value}")
        print(f"   - Service port: {config.service_config.service_port}")
        print(f"   - API key required: {config.security_config.api_key_required}")
        
        # Validate paths
        path_validation = config.validate_paths()
        if path_validation.valid:
            print("✅ Path validation passed")
        else:
            print("⚠️  Path validation issues:")
            for error in path_validation.errors:
                print(f"   - {error}")
        
    except Exception as e:
        print(f"❌ Configuration validation failed: {e}")


def demonstrate_security_features():
    """Demonstrate security features without external dependencies."""
    print("\n🔐 Demonstrating security features...")
    
    # Demonstrate firewall rule creation
    try:
        from deployment.network_security import (
            FirewallRule,
            AccessControlAction,
            NetworkProtocol,
            CORSConfiguration
        )
        
        print("🛡️  Creating firewall rules...")
        
        # Create sample firewall rules
        rules = [
            FirewallRule(
                action=AccessControlAction.ALLOW,
                protocol=NetworkProtocol.TCP,
                port=22,
                comment="SSH access"
            ),
            FirewallRule(
                action=AccessControlAction.ALLOW,
                protocol=NetworkProtocol.TCP,
                port=8000,
                source_ip="192.168.1.0/24",
                comment="Thai Tokenizer service"
            ),
            FirewallRule(
                action=AccessControlAction.ALLOW,
                protocol=NetworkProtocol.TCP,
                port=9090,
                source_ip="127.0.0.1",
                comment="Metrics endpoint (local only)"
            )
        ]
        
        print(f"✅ Created {len(rules)} firewall rules:")
        for rule in rules:
            print(f"   - {rule.action.value.upper()} {rule.protocol.value.upper()} port {rule.port}")
            if rule.source_ip:
                print(f"     from {rule.source_ip}")
            if rule.comment:
                print(f"     ({rule.comment})")
            
            # Show UFW command format
            ufw_command = rule.to_ufw_rule()
            print(f"     UFW: {ufw_command}")
        
        # Demonstrate CORS configuration
        print("\n🌐 Creating CORS configuration...")
        cors_config = CORSConfiguration(
            allowed_origins=["http://localhost:3000", "https://app.example.com"],
            allowed_methods=["GET", "POST", "PUT", "DELETE"],
            allow_credentials=False,
            max_age=3600
        )
        
        print("✅ CORS configuration created:")
        print(f"   - Allowed origins: {cors_config.allowed_origins}")
        print(f"   - Allowed methods: {cors_config.allowed_methods}")
        print(f"   - Allow credentials: {cors_config.allow_credentials}")
        print(f"   - Max age: {cors_config.max_age} seconds")
        
        # Show FastAPI middleware config
        middleware_config = cors_config.to_fastapi_middleware_config()
        print(f"   - FastAPI config: {middleware_config}")
        
    except Exception as e:
        print(f"❌ Security features demonstration failed: {e}")


def demonstrate_network_security(config: OnPremiseConfig):
    """Demonstrate network security management."""
    print("\n🌐 Demonstrating network security management...")
    
    try:
        from deployment.network_security import NetworkSecurityManager
        
        # Initialize network security manager
        network_manager = NetworkSecurityManager(config)
        print(f"✅ Network security manager initialized")
        print(f"   - Detected firewall: {network_manager.firewall_type.value if network_manager.firewall_type else 'none'}")
        
        # Generate firewall rules
        rules = network_manager.generate_firewall_rules()
        print(f"✅ Generated {len(rules)} firewall rules:")
        
        for i, rule in enumerate(rules[:3], 1):  # Show first 3 rules
            print(f"   {i}. {rule.comment or 'Firewall rule'}")
            print(f"      Action: {rule.action.value}")
            print(f"      Protocol: {rule.protocol.value}")
            print(f"      Port: {rule.port}")
            if rule.source_ip:
                print(f"      Source: {rule.source_ip}")
        
        # Generate CORS configuration
        cors_config = network_manager.generate_cors_configuration()
        print(f"✅ Generated CORS configuration:")
        print(f"   - Origins: {cors_config.allowed_origins}")
        print(f"   - Methods: {cors_config.allowed_methods}")
        
        # Generate security recommendations
        recommendations = network_manager.generate_security_recommendations()
        print(f"✅ Generated {len(recommendations)} security recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):  # Show first 3
            print(f"   {i}. {rec}")
        
    except Exception as e:
        print(f"❌ Network security demonstration failed: {e}")


def demonstrate_security_audit(config: OnPremiseConfig):
    """Demonstrate security auditing capabilities."""
    print("\n🔍 Demonstrating security audit capabilities...")
    
    try:
        from deployment.security_audit import (
            SecurityAuditor,
            AuditFinding,
            AuditCategory,
            AuditSeverity
        )
        
        # Create a sample audit finding
        sample_finding = AuditFinding(
            category=AuditCategory.AUTHENTICATION,
            severity=AuditSeverity.MEDIUM,
            title="API Key Authentication Configured",
            description="Service has API key authentication enabled",
            recommendation="Ensure API key is strong and rotated regularly",
            affected_component="api_authentication",
            evidence={"api_key_length": 25, "api_key_required": True},
            remediation_steps=[
                "Verify API key strength (32+ characters recommended)",
                "Set up API key rotation schedule",
                "Monitor API key usage"
            ],
            compliance_frameworks=["NIST", "ISO27001"]
        )
        
        print("✅ Sample audit finding created:")
        print(f"   - Category: {sample_finding.category.value}")
        print(f"   - Severity: {sample_finding.severity.value}")
        print(f"   - Title: {sample_finding.title}")
        print(f"   - Description: {sample_finding.description}")
        print(f"   - Recommendation: {sample_finding.recommendation}")
        print(f"   - Compliance: {', '.join(sample_finding.compliance_frameworks)}")
        
        # Initialize auditor (without running full audit to avoid dependencies)
        auditor = SecurityAuditor(config)
        print("✅ Security auditor initialized")
        print(f"   - Deployment method: {config.deployment_method.value}")
        print(f"   - Security level: {config.security_config.security_level.value}")
        
        # Show what a full audit would check
        audit_categories = [
            "Authentication mechanisms",
            "Authorization and access control",
            "Encryption and data protection",
            "Network security configuration",
            "Configuration file security",
            "System-level security",
            "Compliance framework alignment"
        ]
        
        print("✅ Full audit would check:")
        for category in audit_categories:
            print(f"   - {category}")
        
    except Exception as e:
        print(f"❌ Security audit demonstration failed: {e}")


def demonstrate_environment_variables(config: OnPremiseConfig):
    """Demonstrate environment variable generation."""
    print("\n🔧 Demonstrating environment variable generation...")
    
    try:
        env_vars = config.get_environment_dict()
        
        print(f"✅ Generated {len(env_vars)} environment variables:")
        
        # Show key environment variables (mask sensitive ones)
        important_vars = [
            "THAI_TOKENIZER_SERVICE_NAME",
            "THAI_TOKENIZER_SERVICE_PORT",
            "THAI_TOKENIZER_MEILISEARCH_HOST",
            "THAI_TOKENIZER_SECURITY_LEVEL",
            "THAI_TOKENIZER_API_KEY_REQUIRED",
            "THAI_TOKENIZER_MEMORY_LIMIT_MB",
            "THAI_TOKENIZER_LOG_LEVEL"
        ]
        
        for var_name in important_vars:
            if var_name in env_vars:
                value = env_vars[var_name]
                # Mask sensitive values
                if "API_KEY" in var_name and value:
                    value = f"{value[:8]}..." if len(value) > 8 else "***"
                print(f"   - {var_name}={value}")
        
        # Show how to save to file
        print("\n💾 Environment variables can be saved to:")
        print("   - .env file for development")
        print("   - systemd environment file")
        print("   - Docker environment file")
        print("   - Kubernetes ConfigMap/Secret")
        
    except Exception as e:
        print(f"❌ Environment variable demonstration failed: {e}")


def main():
    """Run the security implementation demonstration."""
    print("🚀 Thai Tokenizer Security Implementation Demo")
    print("=" * 50)
    
    try:
        # Create demo configuration
        config = create_demo_config()
        
        # Demonstrate various security features
        demonstrate_configuration_validation(config)
        demonstrate_security_features()
        demonstrate_network_security(config)
        demonstrate_security_audit(config)
        demonstrate_environment_variables(config)
        
        print("\n" + "=" * 50)
        print("✅ Security implementation demonstration completed!")
        print("\n📋 Summary of implemented security features:")
        print("   🔐 Secure credential storage and encryption")
        print("   🔑 API key management and validation")
        print("   🛡️  Firewall configuration and rules")
        print("   🌐 Network access control and CORS")
        print("   📁 Configuration file protection")
        print("   🔍 Comprehensive security auditing")
        print("   📊 Security compliance checking")
        print("   🔄 Credential rotation capabilities")
        print("   📝 Security documentation generation")
        
        print("\n🎯 Next steps:")
        print("   1. Install required dependencies (cryptography, psutil)")
        print("   2. Set up master password for credential encryption")
        print("   3. Configure firewall rules for your environment")
        print("   4. Run security audit to identify improvements")
        print("   5. Set up regular security monitoring")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())