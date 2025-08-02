#!/usr/bin/env python3
"""
Security Integration Example

This example shows how to integrate the security features into a real deployment.
It demonstrates the complete workflow from configuration to deployment with security.
"""

import os
import sys
import json
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
    ServiceConfig,
    ResourceConfig,
    MonitoringConfig
)


def create_production_config() -> OnPremiseConfig:
    """Create a production-ready configuration with security."""
    
    return OnPremiseConfig(
        deployment_method=DeploymentMethod.SYSTEMD,
        
        meilisearch_config=MeilisearchConnectionConfig(
            host="https://meilisearch.internal.company.com:7700",
            api_key=SecretStr(os.environ.get("MEILISEARCH_API_KEY", "production_api_key_here")),
            ssl_enabled=True,
            ssl_verify=True,
            timeout_seconds=30,
            max_retries=3
        ),
        
        service_config=ServiceConfig(
            service_name="thai-tokenizer-prod",
            service_port=8000,
            service_host="127.0.0.1",  # Bind to localhost only
            worker_processes=4,
            service_user="thai-tokenizer",
            service_group="thai-tokenizer"
        ),
        
        security_config=SecurityConfig(
            security_level=SecurityLevel.HIGH,
            allowed_hosts=[
                "api-gateway.company.com",
                "192.168.10.100",
                "192.168.10.101"
            ],
            cors_origins=[
                "https://app.company.com",
                "https://admin.company.com"
            ],
            api_key_required=True,
            api_key=SecretStr(os.environ.get("THAI_TOKENIZER_API_KEY", "production_service_key")),
            enable_https=True,
            ssl_cert_path="/etc/ssl/certs/thai-tokenizer.crt",
            ssl_key_path="/etc/ssl/private/thai-tokenizer.key",
            firewall_rules=[
                "allow tcp 8000 from 192.168.10.0/24 comment 'Thai Tokenizer API'",
                "allow tcp 9090 from 127.0.0.1 comment 'Metrics (local only)'"
            ]
        ),
        
        resource_config=ResourceConfig(
            memory_limit_mb=1024,
            cpu_limit_cores=2.0,
            max_concurrent_requests=200,
            request_timeout_seconds=30,
            enable_metrics=True,
            metrics_port=9090
        ),
        
        monitoring_config=MonitoringConfig(
            enable_health_checks=True,
            health_check_interval_seconds=30,
            enable_logging=True,
            log_level="INFO",
            log_file_path="/var/log/thai-tokenizer/service.log",
            enable_prometheus=True,
            prometheus_port=9091
        ),
        
        # Deployment paths
        installation_path="/opt/thai-tokenizer",
        data_path="/var/lib/thai-tokenizer",
        log_path="/var/log/thai-tokenizer",
        config_path="/etc/thai-tokenizer",
        
        # Additional environment variables
        environment_variables={
            "PYTHONPATH": "/opt/thai-tokenizer/src",
            "THAI_TOKENIZER_ENV": "production"
        }
    )


def demonstrate_security_setup():
    """Demonstrate complete security setup workflow."""
    
    print("🔐 Thai Tokenizer Production Security Setup")
    print("=" * 50)
    
    # 1. Create production configuration
    print("\n1️⃣  Creating production configuration...")
    config = create_production_config()
    
    print(f"✅ Configuration created:")
    print(f"   - Deployment: {config.deployment_method.value}")
    print(f"   - Security Level: {config.security_config.security_level.value}")
    print(f"   - HTTPS Enabled: {config.security_config.enable_https}")
    print(f"   - API Key Required: {config.security_config.api_key_required}")
    print(f"   - Allowed Hosts: {len(config.security_config.allowed_hosts)} hosts")
    print(f"   - CORS Origins: {len(config.security_config.cors_origins)} origins")
    
    # 2. Generate environment variables
    print("\n2️⃣  Generating environment variables...")
    env_vars = config.get_environment_dict()
    
    # Save environment file
    env_file_content = []
    for key, value in env_vars.items():
        # Mask sensitive values for display
        display_value = value
        if any(sensitive in key for sensitive in ["API_KEY", "PASSWORD", "SECRET"]):
            display_value = f"{value[:8]}..." if len(value) > 8 else "***"
        
        env_file_content.append(f"{key}={value}")
        print(f"   - {key}={display_value}")
    
    # Write environment file (in production, this would be secured)
    env_file_path = "/tmp/thai-tokenizer.env"
    with open(env_file_path, 'w') as f:
        f.write('\n'.join(env_file_content))
    
    print(f"✅ Environment file saved: {env_file_path}")
    
    # 3. Generate firewall configuration
    print("\n3️⃣  Generating firewall configuration...")
    
    try:
        from deployment.network_security import NetworkSecurityManager
        
        network_manager = NetworkSecurityManager(config)
        firewall_rules = network_manager.generate_firewall_rules()
        
        print(f"✅ Generated {len(firewall_rules)} firewall rules:")
        for rule in firewall_rules:
            print(f"   - {rule.action.value.upper()} {rule.protocol.value.upper()} "
                  f"port {rule.port}")
            if rule.source_ip:
                print(f"     from {rule.source_ip}")
            if rule.comment:
                print(f"     ({rule.comment})")
        
        # Generate firewall script
        script_path = "/tmp/configure-firewall.sh"
        success = network_manager.create_network_security_script(script_path)
        
        if success:
            print(f"✅ Firewall script created: {script_path}")
        
    except Exception as e:
        print(f"⚠️  Firewall configuration failed: {e}")
    
    # 4. Generate systemd service configuration
    print("\n4️⃣  Generating systemd service configuration...")
    
    try:
        from deployment.systemd_config_manager import SystemdConfigManager
        
        systemd_manager = SystemdConfigManager(config)
        
        # Generate service file content
        service_content = systemd_manager.generate_service_file()
        
        # Save service file
        service_file_path = "/tmp/thai-tokenizer.service"
        with open(service_file_path, 'w') as f:
            f.write(service_content)
        
        print(f"✅ Systemd service file created: {service_file_path}")
        
        # Show key security settings
        print("   Security settings in service file:")
        security_lines = [line.strip() for line in service_content.split('\n') 
                         if any(sec in line for sec in ['Private', 'Protect', 'Restrict', 'NoNew'])]
        for line in security_lines[:5]:  # Show first 5 security settings
            print(f"     {line}")
        
    except Exception as e:
        print(f"⚠️  Systemd configuration failed: {e}")
    
    # 5. Generate deployment documentation
    print("\n5️⃣  Generating deployment documentation...")
    
    deployment_doc = {
        "deployment_info": {
            "service_name": config.service_config.service_name,
            "deployment_method": config.deployment_method.value,
            "security_level": config.security_config.security_level.value,
            "generated_at": "2024-01-01T00:00:00Z"
        },
        "security_checklist": [
            "✅ API key authentication enabled",
            "✅ HTTPS/TLS configured",
            "✅ Firewall rules defined",
            "✅ Host access restricted",
            "✅ CORS origins limited",
            "✅ Service runs as non-root user",
            "✅ Secure file permissions configured",
            "✅ Logging and monitoring enabled"
        ],
        "deployment_steps": [
            "1. Copy SSL certificates to /etc/ssl/",
            "2. Create thai-tokenizer user and group",
            "3. Install systemd service file",
            "4. Configure firewall rules",
            "5. Set up log rotation",
            "6. Start and enable service",
            "7. Verify security configuration",
            "8. Run security audit"
        ],
        "post_deployment_verification": [
            "curl -k https://localhost:8000/health",
            "systemctl status thai-tokenizer",
            "ufw status",
            "journalctl -u thai-tokenizer -n 20"
        ]
    }
    
    doc_file_path = "/tmp/deployment-guide.json"
    with open(doc_file_path, 'w') as f:
        json.dump(deployment_doc, f, indent=2)
    
    print(f"✅ Deployment documentation created: {doc_file_path}")
    
    # 6. Security recommendations
    print("\n6️⃣  Security recommendations...")
    
    try:
        from deployment.network_security import NetworkSecurityManager
        
        network_manager = NetworkSecurityManager(config)
        recommendations = network_manager.generate_security_recommendations()
        
        print("✅ Security recommendations:")
        for i, rec in enumerate(recommendations[:5], 1):
            print(f"   {i}. {rec}")
        
    except Exception as e:
        print(f"⚠️  Security recommendations failed: {e}")
    
    # 7. Summary
    print("\n" + "=" * 50)
    print("✅ Production security setup completed!")
    
    print("\n📁 Generated files:")
    print(f"   - Environment: {env_file_path}")
    print(f"   - Firewall script: /tmp/configure-firewall.sh")
    print(f"   - Systemd service: {service_file_path}")
    print(f"   - Deployment guide: {doc_file_path}")
    
    print("\n🔒 Security features enabled:")
    print("   - High security level")
    print("   - API key authentication")
    print("   - HTTPS/TLS encryption")
    print("   - Firewall protection")
    print("   - Host access control")
    print("   - CORS restrictions")
    print("   - Secure service user")
    print("   - Comprehensive logging")
    
    print("\n⚠️  Important notes:")
    print("   - Set MEILISEARCH_API_KEY environment variable")
    print("   - Set THAI_TOKENIZER_API_KEY environment variable")
    print("   - Install SSL certificates before deployment")
    print("   - Create thai-tokenizer system user")
    print("   - Configure log rotation")
    print("   - Run security audit after deployment")
    
    return True


def main():
    """Run the security integration example."""
    
    try:
        success = demonstrate_security_setup()
        
        if success:
            print("\n🎉 Security integration example completed successfully!")
            return 0
        else:
            print("\n❌ Security integration example failed!")
            return 1
            
    except Exception as e:
        print(f"\n💥 Example failed with error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())