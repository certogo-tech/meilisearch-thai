"""
Network security and access control for on-premise deployment.

This module provides comprehensive network security features including:
- Firewall configuration utilities and recommendations
- Network access control validation
- CORS and allowed hosts configuration management
- Security audit and validation tools
"""

import os
import re
import socket
import subprocess
import ipaddress
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Set
from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator

try:
    from src.deployment.config import OnPremiseConfig, SecurityConfig, SecurityLevel
    from src.utils.logging import get_structured_logger
except ImportError:
    import logging
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class FirewallType(str, Enum):
    """Supported firewall types."""
    UFW = "ufw"
    IPTABLES = "iptables"
    FIREWALLD = "firewalld"
    WINDOWS_FIREWALL = "windows_firewall"


class NetworkProtocol(str, Enum):
    """Network protocols."""
    TCP = "tcp"
    UDP = "udp"
    ICMP = "icmp"


class AccessControlAction(str, Enum):
    """Access control actions."""
    ALLOW = "allow"
    DENY = "deny"
    REJECT = "reject"


class NetworkValidationResult(BaseModel):
    """Result of network security validation."""
    valid: bool
    security_level: str
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    network_info: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class FirewallRule(BaseModel):
    """Firewall rule configuration."""
    action: AccessControlAction
    protocol: NetworkProtocol
    port: Optional[int] = None
    port_range: Optional[Tuple[int, int]] = None
    source_ip: Optional[str] = None
    destination_ip: Optional[str] = None
    comment: Optional[str] = None
    
    @field_validator('source_ip', 'destination_ip')
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """Validate IP address or CIDR notation."""
        if v is None:
            return v
        
        try:
            # Try to parse as IP network (includes single IPs and CIDR)
            ipaddress.ip_network(v, strict=False)
            return v
        except ValueError:
            # Check for special values
            if v in ["any", "0.0.0.0/0", "::/0"]:
                return v
            raise ValueError(f"Invalid IP address or network: {v}")
    
    def to_ufw_rule(self) -> str:
        """Convert to UFW rule format."""
        rule_parts = ["ufw", self.action.value]
        
        if self.source_ip and self.source_ip not in ["any", "0.0.0.0/0"]:
            rule_parts.extend(["from", self.source_ip])
        
        if self.port:
            rule_parts.extend(["to", "any", "port", str(self.port)])
        elif self.port_range:
            rule_parts.extend(["to", "any", "port", f"{self.port_range[0]}:{self.port_range[1]}"])
        
        if self.protocol != NetworkProtocol.TCP:
            rule_parts.extend(["proto", self.protocol.value])
        
        if self.comment:
            rule_parts.extend(["comment", f"'{self.comment}'"])
        
        return " ".join(rule_parts)
    
    def to_iptables_rule(self) -> str:
        """Convert to iptables rule format."""
        rule_parts = ["iptables"]
        
        if self.action == AccessControlAction.ALLOW:
            rule_parts.extend(["-A", "INPUT"])
        else:
            rule_parts.extend(["-A", "INPUT"])
        
        if self.protocol:
            rule_parts.extend(["-p", self.protocol.value])
        
        if self.source_ip and self.source_ip not in ["any", "0.0.0.0/0"]:
            rule_parts.extend(["-s", self.source_ip])
        
        if self.port:
            rule_parts.extend(["--dport", str(self.port)])
        elif self.port_range:
            rule_parts.extend(["--dport", f"{self.port_range[0]}:{self.port_range[1]}"])
        
        if self.action == AccessControlAction.ALLOW:
            rule_parts.extend(["-j", "ACCEPT"])
        elif self.action == AccessControlAction.DENY:
            rule_parts.extend(["-j", "DROP"])
        else:
            rule_parts.extend(["-j", "REJECT"])
        
        return " ".join(rule_parts)


class CORSConfiguration(BaseModel):
    """CORS configuration management."""
    allowed_origins: List[str] = Field(default_factory=list)
    allowed_methods: List[str] = Field(default_factory=lambda: ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    allowed_headers: List[str] = Field(default_factory=lambda: ["Content-Type", "Authorization", "X-Requested-With"])
    allow_credentials: bool = False
    max_age: int = Field(3600, ge=0, le=86400)  # 1 hour default, max 24 hours
    
    @field_validator('allowed_origins')
    @classmethod
    def validate_origins(cls, v: List[str]) -> List[str]:
        """Validate CORS origins."""
        if not v:
            return ["*"]  # Default to allow all if empty
        
        validated_origins = []
        for origin in v:
            if origin == "*":
                validated_origins.append(origin)
            elif origin.startswith(("http://", "https://")):
                validated_origins.append(origin)
            elif re.match(r'^https?://[\w\-\.]+(?::\d+)?(?:/.*)?$', origin):
                validated_origins.append(origin)
            else:
                # Try to construct a valid origin
                if not origin.startswith(("http://", "https://")):
                    origin = f"http://{origin}"
                validated_origins.append(origin)
        
        return validated_origins
    
    def to_fastapi_middleware_config(self) -> Dict[str, Any]:
        """Convert to FastAPI CORS middleware configuration."""
        return {
            "allow_origins": self.allowed_origins,
            "allow_credentials": self.allow_credentials,
            "allow_methods": self.allowed_methods,
            "allow_headers": self.allowed_headers,
            "max_age": self.max_age
        }


class NetworkSecurityManager:
    """
    Comprehensive network security and access control manager.
    
    Features:
    - Firewall configuration and management
    - Network access control validation
    - CORS configuration management
    - Security auditing and recommendations
    """
    
    def __init__(self, config: OnPremiseConfig):
        """Initialize network security manager."""
        self.config = config
        self.logger = get_structured_logger(f"{__name__}.NetworkSecurityManager")
        
        # Detect available firewall
        self.firewall_type = self._detect_firewall_type()
        
        self.logger.info(
            f"Initialized network security manager",
            extra={
                "firewall_type": self.firewall_type.value if self.firewall_type else "none",
                "security_level": config.security_config.security_level.value
            }
        )
    
    def _detect_firewall_type(self) -> Optional[FirewallType]:
        """Detect available firewall system."""
        try:
            # Check for UFW
            result = subprocess.run(["which", "ufw"], capture_output=True, text=True)
            if result.returncode == 0:
                return FirewallType.UFW
            
            # Check for firewalld
            result = subprocess.run(["which", "firewall-cmd"], capture_output=True, text=True)
            if result.returncode == 0:
                return FirewallType.FIREWALLD
            
            # Check for iptables
            result = subprocess.run(["which", "iptables"], capture_output=True, text=True)
            if result.returncode == 0:
                return FirewallType.IPTABLES
            
        except Exception as e:
            self.logger.warning(f"Failed to detect firewall type: {e}")
        
        return None
    
    def generate_firewall_rules(self) -> List[FirewallRule]:
        """
        Generate recommended firewall rules based on configuration.
        
        Returns:
            List of firewall rules
        """
        rules = []
        
        try:
            # Allow SSH (if not already configured)
            rules.append(FirewallRule(
                action=AccessControlAction.ALLOW,
                protocol=NetworkProtocol.TCP,
                port=22,
                comment="SSH access"
            ))
            
            # Allow Thai Tokenizer service
            rules.append(FirewallRule(
                action=AccessControlAction.ALLOW,
                protocol=NetworkProtocol.TCP,
                port=self.config.service_config.service_port,
                comment="Thai Tokenizer service"
            ))
            
            # Allow metrics endpoint if enabled
            if self.config.resource_config.enable_metrics:
                rules.append(FirewallRule(
                    action=AccessControlAction.ALLOW,
                    protocol=NetworkProtocol.TCP,
                    port=self.config.resource_config.metrics_port,
                    source_ip="127.0.0.1",  # Only local access for metrics
                    comment="Metrics endpoint (local only)"
                ))
            
            # Allow Prometheus if enabled
            if self.config.monitoring_config.enable_prometheus:
                rules.append(FirewallRule(
                    action=AccessControlAction.ALLOW,
                    protocol=NetworkProtocol.TCP,
                    port=self.config.monitoring_config.prometheus_port,
                    source_ip="127.0.0.1",  # Only local access for Prometheus
                    comment="Prometheus metrics (local only)"
                ))
            
            # Security level specific rules
            if self.config.security_config.security_level == SecurityLevel.HIGH:
                # High security: Restrict to specific IPs if configured
                if self.config.security_config.allowed_hosts and "*" not in self.config.security_config.allowed_hosts:
                    for host in self.config.security_config.allowed_hosts:
                        if host not in ["localhost", "127.0.0.1"]:
                            try:
                                # Validate and add specific host rules
                                ipaddress.ip_address(host)
                                rules.append(FirewallRule(
                                    action=AccessControlAction.ALLOW,
                                    protocol=NetworkProtocol.TCP,
                                    port=self.config.service_config.service_port,
                                    source_ip=host,
                                    comment=f"Thai Tokenizer access from {host}"
                                ))
                            except ValueError:
                                self.logger.warning(f"Invalid IP address in allowed_hosts: {host}")
            
            # Add custom firewall rules from configuration
            for rule_str in self.config.security_config.firewall_rules:
                try:
                    custom_rule = self._parse_firewall_rule(rule_str)
                    if custom_rule:
                        rules.append(custom_rule)
                except Exception as e:
                    self.logger.warning(f"Failed to parse custom firewall rule '{rule_str}': {e}")
            
            self.logger.info(f"Generated {len(rules)} firewall rules")
            
        except Exception as e:
            self.logger.error(f"Failed to generate firewall rules: {e}")
        
        return rules
    
    def _parse_firewall_rule(self, rule_str: str) -> Optional[FirewallRule]:
        """Parse a firewall rule string into FirewallRule object."""
        # Simple parser for common rule formats
        # Format: "allow tcp 8080 from 192.168.1.0/24 comment 'Web server'"
        
        parts = rule_str.split()
        if len(parts) < 3:
            return None
        
        try:
            action = AccessControlAction(parts[0].lower())
            protocol = NetworkProtocol(parts[1].lower())
            port = int(parts[2])
            
            rule = FirewallRule(
                action=action,
                protocol=protocol,
                port=port
            )
            
            # Parse additional options
            i = 3
            while i < len(parts):
                if parts[i] == "from" and i + 1 < len(parts):
                    rule.source_ip = parts[i + 1]
                    i += 2
                elif parts[i] == "comment" and i + 1 < len(parts):
                    rule.comment = parts[i + 1].strip("'\"")
                    i += 2
                else:
                    i += 1
            
            return rule
            
        except (ValueError, IndexError):
            return None
    
    def apply_firewall_rules(self, rules: List[FirewallRule], dry_run: bool = False) -> Dict[str, Any]:
        """
        Apply firewall rules to the system.
        
        Args:
            rules: List of firewall rules to apply
            dry_run: If True, only show what would be done
        
        Returns:
            Dictionary with application results
        """
        result = {
            "success": True,
            "applied_rules": [],
            "failed_rules": [],
            "commands": [],
            "dry_run": dry_run
        }
        
        if not self.firewall_type:
            result["success"] = False
            result["error"] = "No supported firewall detected"
            return result
        
        try:
            for rule in rules:
                try:
                    if self.firewall_type == FirewallType.UFW:
                        command = rule.to_ufw_rule()
                    elif self.firewall_type == FirewallType.IPTABLES:
                        command = rule.to_iptables_rule()
                    else:
                        self.logger.warning(f"Firewall type {self.firewall_type.value} not fully supported")
                        continue
                    
                    result["commands"].append(command)
                    
                    if not dry_run:
                        # Execute the command
                        cmd_result = subprocess.run(
                            command.split(),
                            capture_output=True,
                            text=True,
                            timeout=30
                        )
                        
                        if cmd_result.returncode == 0:
                            result["applied_rules"].append({
                                "rule": rule.model_dump(),
                                "command": command
                            })
                        else:
                            result["failed_rules"].append({
                                "rule": rule.model_dump(),
                                "command": command,
                                "error": cmd_result.stderr
                            })
                    else:
                        result["applied_rules"].append({
                            "rule": rule.model_dump(),
                            "command": command
                        })
                
                except Exception as e:
                    result["failed_rules"].append({
                        "rule": rule.model_dump(),
                        "error": str(e)
                    })
            
            if result["failed_rules"]:
                result["success"] = False
            
            self.logger.info(
                f"Firewall rules application completed",
                extra={
                    "dry_run": dry_run,
                    "applied": len(result["applied_rules"]),
                    "failed": len(result["failed_rules"])
                }
            )
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            self.logger.error(f"Failed to apply firewall rules: {e}")
        
        return result
    
    def validate_network_access(self) -> NetworkValidationResult:
        """
        Validate network access control configuration.
        
        Returns:
            Network validation result
        """
        result = NetworkValidationResult(
            valid=True,
            security_level="unknown"
        )
        
        try:
            # Check port availability
            self._validate_port_availability(result)
            
            # Check allowed hosts configuration
            self._validate_allowed_hosts(result)
            
            # Check CORS configuration
            self._validate_cors_configuration(result)
            
            # Check firewall status
            self._validate_firewall_status(result)
            
            # Check network interfaces
            self._validate_network_interfaces(result)
            
            # Determine security level
            self._determine_network_security_level(result)
            
            self.logger.info(
                f"Network access validation completed",
                extra={
                    "valid": result.valid,
                    "security_level": result.security_level,
                    "issues": len(result.issues)
                }
            )
            
        except Exception as e:
            result.valid = False
            result.issues.append(f"Network validation failed: {e}")
            self.logger.error(f"Network access validation failed: {e}")
        
        return result
    
    def _validate_port_availability(self, result: NetworkValidationResult):
        """Validate that required ports are available."""
        ports_to_check = [
            ("service_port", self.config.service_config.service_port),
            ("metrics_port", self.config.resource_config.metrics_port),
        ]
        
        if self.config.monitoring_config.enable_prometheus:
            ports_to_check.append(("prometheus_port", self.config.monitoring_config.prometheus_port))
        
        for port_name, port_number in ports_to_check:
            try:
                # Try to bind to the port
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    s.bind(('127.0.0.1', port_number))
                
                result.network_info[f"{port_name}_available"] = True
                
            except OSError as e:
                if e.errno == 98:  # Address already in use
                    result.issues.append(f"Port {port_number} ({port_name}) is already in use")
                    result.valid = False
                else:
                    result.issues.append(f"Cannot bind to port {port_number} ({port_name}): {e}")
                    result.valid = False
                
                result.network_info[f"{port_name}_available"] = False
    
    def _validate_allowed_hosts(self, result: NetworkValidationResult):
        """Validate allowed hosts configuration."""
        allowed_hosts = self.config.security_config.allowed_hosts
        
        if "*" in allowed_hosts:
            if self.config.security_config.security_level == SecurityLevel.HIGH:
                result.recommendations.append("High security level but all hosts are allowed (*)")
            result.network_info["allows_all_hosts"] = True
        else:
            result.network_info["allows_all_hosts"] = False
            
            # Validate each allowed host
            valid_hosts = []
            for host in allowed_hosts:
                try:
                    if host in ["localhost", "127.0.0.1", "::1"]:
                        valid_hosts.append(host)
                    else:
                        # Try to resolve hostname or validate IP
                        socket.gethostbyname(host)
                        valid_hosts.append(host)
                except socket.gaierror:
                    result.recommendations.append(f"Cannot resolve hostname: {host}")
            
            result.network_info["valid_allowed_hosts"] = valid_hosts
            result.network_info["invalid_allowed_hosts"] = list(set(allowed_hosts) - set(valid_hosts))
    
    def _validate_cors_configuration(self, result: NetworkValidationResult):
        """Validate CORS configuration."""
        cors_origins = self.config.security_config.cors_origins
        
        if "*" in cors_origins:
            if self.config.security_config.security_level == SecurityLevel.HIGH:
                result.recommendations.append("High security level but all CORS origins are allowed (*)")
            result.network_info["allows_all_cors_origins"] = True
        else:
            result.network_info["allows_all_cors_origins"] = False
            
            # Validate CORS origins format
            valid_origins = []
            for origin in cors_origins:
                if re.match(r'^https?://[\w\-\.]+(?::\d+)?(?:/.*)?$', origin):
                    valid_origins.append(origin)
                else:
                    result.recommendations.append(f"Invalid CORS origin format: {origin}")
            
            result.network_info["valid_cors_origins"] = valid_origins
    
    def _validate_firewall_status(self, result: NetworkValidationResult):
        """Validate firewall status and configuration."""
        if not self.firewall_type:
            result.recommendations.append("No firewall detected - consider installing ufw or configuring iptables")
            result.network_info["firewall_available"] = False
            return
        
        result.network_info["firewall_available"] = True
        result.network_info["firewall_type"] = self.firewall_type.value
        
        try:
            if self.firewall_type == FirewallType.UFW:
                # Check UFW status
                cmd_result = subprocess.run(
                    ["ufw", "status"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                
                if cmd_result.returncode == 0:
                    if "Status: active" in cmd_result.stdout:
                        result.network_info["firewall_active"] = True
                    else:
                        result.recommendations.append("UFW firewall is not active")
                        result.network_info["firewall_active"] = False
                else:
                    result.recommendations.append("Cannot check UFW status")
                    result.network_info["firewall_active"] = False
        
        except Exception as e:
            result.recommendations.append(f"Cannot validate firewall status: {e}")
    
    def _validate_network_interfaces(self, result: NetworkValidationResult):
        """Validate network interface configuration."""
        try:
            # Get network interface information
            import psutil
            
            interfaces = psutil.net_if_addrs()
            result.network_info["network_interfaces"] = {}
            
            for interface_name, addresses in interfaces.items():
                interface_info = {
                    "addresses": [],
                    "has_ipv4": False,
                    "has_ipv6": False
                }
                
                for addr in addresses:
                    if addr.family == socket.AF_INET:
                        interface_info["addresses"].append(f"IPv4: {addr.address}")
                        interface_info["has_ipv4"] = True
                    elif addr.family == socket.AF_INET6:
                        interface_info["addresses"].append(f"IPv6: {addr.address}")
                        interface_info["has_ipv6"] = True
                
                result.network_info["network_interfaces"][interface_name] = interface_info
            
            # Check if service is binding to all interfaces
            if self.config.service_config.service_host == "0.0.0.0":
                if self.config.security_config.security_level == SecurityLevel.HIGH:
                    result.recommendations.append("Service binding to all interfaces (0.0.0.0) - consider binding to specific interface for high security")
        
        except ImportError:
            result.recommendations.append("psutil not available - cannot validate network interfaces")
        except Exception as e:
            result.recommendations.append(f"Cannot validate network interfaces: {e}")
    
    def _determine_network_security_level(self, result: NetworkValidationResult):
        """Determine overall network security level."""
        security_score = 0
        max_score = 10
        
        # Firewall configuration (3 points)
        if result.network_info.get("firewall_available", False):
            security_score += 1
            if result.network_info.get("firewall_active", False):
                security_score += 2
        
        # Host restrictions (2 points)
        if not result.network_info.get("allows_all_hosts", True):
            security_score += 2
        
        # CORS restrictions (2 points)
        if not result.network_info.get("allows_all_cors_origins", True):
            security_score += 2
        
        # Port availability (2 points)
        available_ports = sum(1 for k, v in result.network_info.items() 
                             if k.endswith("_available") and v)
        if available_ports >= 2:
            security_score += 2
        elif available_ports >= 1:
            security_score += 1
        
        # Interface binding (1 point)
        if self.config.service_config.service_host != "0.0.0.0":
            security_score += 1
        
        # Determine security level based on score
        if security_score >= 8:
            result.security_level = "high"
        elif security_score >= 6:
            result.security_level = "medium"
        elif security_score >= 4:
            result.security_level = "low"
        else:
            result.security_level = "critical"
    
    def generate_cors_configuration(self) -> CORSConfiguration:
        """
        Generate CORS configuration based on security settings.
        
        Returns:
            CORS configuration object
        """
        cors_config = CORSConfiguration()
        
        # Set allowed origins based on security configuration
        if self.config.security_config.cors_origins:
            cors_config.allowed_origins = self.config.security_config.cors_origins
        else:
            # Default based on security level
            if self.config.security_config.security_level == SecurityLevel.HIGH:
                cors_config.allowed_origins = []  # No CORS allowed
            elif self.config.security_config.security_level == SecurityLevel.STANDARD:
                cors_config.allowed_origins = ["http://localhost:*", "https://localhost:*"]
            else:
                cors_config.allowed_origins = ["*"]
        
        # Adjust other settings based on security level
        if self.config.security_config.security_level == SecurityLevel.HIGH:
            cors_config.allow_credentials = False
            cors_config.allowed_methods = ["GET", "POST"]  # Restrict methods
            cors_config.max_age = 300  # 5 minutes
        elif self.config.security_config.security_level == SecurityLevel.STANDARD:
            cors_config.allow_credentials = False
            cors_config.max_age = 1800  # 30 minutes
        
        self.logger.info(
            f"Generated CORS configuration",
            extra={
                "allowed_origins": len(cors_config.allowed_origins),
                "allow_credentials": cors_config.allow_credentials,
                "security_level": self.config.security_config.security_level.value
            }
        )
        
        return cors_config
    
    def generate_security_recommendations(self) -> List[str]:
        """
        Generate network security recommendations.
        
        Returns:
            List of security recommendations
        """
        recommendations = []
        
        try:
            # Firewall recommendations
            if not self.firewall_type:
                recommendations.append("Install and configure a firewall (ufw recommended for Ubuntu/Debian)")
            
            # Port security recommendations
            if self.config.service_config.service_port < 1024:
                recommendations.append("Consider using a non-privileged port (>1024) for the service")
            
            # Host binding recommendations
            if self.config.service_config.service_host == "0.0.0.0":
                recommendations.append("Consider binding to specific interface instead of all interfaces (0.0.0.0)")
            
            # Security level specific recommendations
            if self.config.security_config.security_level == SecurityLevel.HIGH:
                recommendations.extend([
                    "Enable API key authentication for high security",
                    "Use HTTPS/TLS for all communications",
                    "Restrict allowed hosts to specific IP addresses",
                    "Disable CORS or restrict to specific origins",
                    "Enable comprehensive logging and monitoring"
                ])
            
            elif self.config.security_config.security_level == SecurityLevel.STANDARD:
                recommendations.extend([
                    "Consider enabling API key authentication",
                    "Use HTTPS/TLS for production deployments",
                    "Restrict CORS origins to known domains"
                ])
            
            # Monitoring recommendations
            if not self.config.monitoring_config.enable_prometheus:
                recommendations.append("Enable Prometheus metrics for better monitoring")
            
            # SSL/TLS recommendations
            if not self.config.security_config.enable_https:
                recommendations.append("Enable HTTPS/TLS for secure communications")
            
        except Exception as e:
            self.logger.error(f"Failed to generate security recommendations: {e}")
            recommendations.append("Unable to generate complete security recommendations")
        
        return recommendations
    
    def create_network_security_script(self, output_path: str) -> bool:
        """
        Create a script to apply network security configurations.
        
        Args:
            output_path: Path to save the security script
        
        Returns:
            True if script created successfully
        """
        try:
            script_content = self._generate_security_script_content()
            
            script_path = Path(output_path)
            script_path.write_text(script_content)
            script_path.chmod(0o755)  # Make executable
            
            self.logger.info(f"Created network security script: {output_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create network security script: {e}")
            return False
    
    def _generate_security_script_content(self) -> str:
        """Generate content for network security script."""
        rules = self.generate_firewall_rules()
        
        script_lines = [
            "#!/bin/bash",
            "# Thai Tokenizer Network Security Configuration Script",
            f"# Generated on {datetime.now().isoformat()}",
            "",
            "set -e",
            "",
            "echo 'Configuring network security for Thai Tokenizer...'",
            ""
        ]
        
        # Add firewall rules
        if self.firewall_type == FirewallType.UFW:
            script_lines.extend([
                "# Enable UFW firewall",
                "ufw --force enable",
                ""
            ])
            
            for rule in rules:
                script_lines.append(f"echo 'Adding rule: {rule.comment or 'Firewall rule'}'")
                script_lines.append(rule.to_ufw_rule())
                script_lines.append("")
        
        elif self.firewall_type == FirewallType.IPTABLES:
            script_lines.extend([
                "# Configure iptables rules",
                "# Save existing rules",
                "iptables-save > /tmp/iptables.backup",
                ""
            ])
            
            for rule in rules:
                script_lines.append(f"echo 'Adding rule: {rule.comment or 'Firewall rule'}'")
                script_lines.append(rule.to_iptables_rule())
                script_lines.append("")
            
            script_lines.extend([
                "# Save iptables rules",
                "iptables-save > /etc/iptables/rules.v4",
                ""
            ])
        
        script_lines.extend([
            "echo 'Network security configuration completed!'",
            "echo 'Please review the applied rules and test connectivity.'"
        ])
        
        return "\n".join(script_lines)