"""Alerting configuration and management for monitoring systems."""

import asyncio
import json
import time
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, asdict
from pathlib import Path

from src.utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


class AlertStatus(Enum):
    """Alert status."""
    ACTIVE = "active"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    name: str
    description: str
    severity: AlertSeverity
    condition: str  # Expression to evaluate
    threshold: float
    duration_seconds: int = 300  # How long condition must be true
    cooldown_seconds: int = 900  # Minimum time between alerts
    enabled: bool = True
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.annotations is None:
            self.annotations = {}


@dataclass
class Alert:
    """Active alert instance."""
    rule_name: str
    severity: AlertSeverity
    message: str
    status: AlertStatus
    started_at: datetime
    resolved_at: Optional[datetime] = None
    labels: Dict[str, str] = None
    annotations: Dict[str, str] = None
    value: Optional[float] = None
    
    def __post_init__(self):
        if self.labels is None:
            self.labels = {}
        if self.annotations is None:
            self.annotations = {}


class AlertManager:
    """Manages alerting rules and active alerts for on-premise deployment."""
    
    def __init__(self, config_path: Optional[str] = None):
        self.rules: Dict[str, AlertRule] = {}
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: List[Alert] = []
        self.notification_handlers: List[Callable] = []
        self.config_path = config_path
        self.last_evaluation = {}
        self.max_history = 1000
        
        # Load default rules
        self._load_default_rules()
        
        # Load custom rules if config path provided
        if config_path:
            self._load_rules_from_file(config_path)
    
    def _load_default_rules(self):
        """Load default alerting rules for Thai tokenizer service."""
        default_rules = [
            AlertRule(
                name="high_error_rate",
                description="High error rate detected",
                severity=AlertSeverity.CRITICAL,
                condition="error_rate_per_hour > threshold",
                threshold=10.0,
                duration_seconds=300,
                labels={"component": "api", "type": "error_rate"},
                annotations={
                    "summary": "Error rate is above {{ .threshold }} errors per hour",
                    "description": "The service is experiencing {{ .value }} errors per hour, which exceeds the threshold of {{ .threshold }}",
                    "runbook_url": "https://docs.example.com/runbooks/high-error-rate"
                }
            ),
            AlertRule(
                name="high_response_time",
                description="High average response time",
                severity=AlertSeverity.WARNING,
                condition="average_response_time_ms > threshold",
                threshold=1000.0,
                duration_seconds=600,
                labels={"component": "api", "type": "performance"},
                annotations={
                    "summary": "Average response time is above {{ .threshold }}ms",
                    "description": "The service response time is {{ .value }}ms, which exceeds the threshold of {{ .threshold }}ms"
                }
            ),
            AlertRule(
                name="low_success_rate",
                description="Low request success rate",
                severity=AlertSeverity.CRITICAL,
                condition="success_rate_percent < threshold",
                threshold=95.0,
                duration_seconds=300,
                labels={"component": "api", "type": "reliability"},
                annotations={
                    "summary": "Request success rate is below {{ .threshold }}%",
                    "description": "The service success rate is {{ .value }}%, which is below the threshold of {{ .threshold }}%"
                }
            ),
            AlertRule(
                name="high_cpu_usage",
                description="High CPU usage",
                severity=AlertSeverity.WARNING,
                condition="cpu_usage_percent > threshold",
                threshold=80.0,
                duration_seconds=600,
                labels={"component": "system", "type": "resource"},
                annotations={
                    "summary": "CPU usage is above {{ .threshold }}%",
                    "description": "System CPU usage is {{ .value }}%, which exceeds the threshold of {{ .threshold }}%"
                }
            ),
            AlertRule(
                name="high_memory_usage",
                description="High memory usage",
                severity=AlertSeverity.WARNING,
                condition="memory_usage_percent > threshold",
                threshold=85.0,
                duration_seconds=600,
                labels={"component": "system", "type": "resource"},
                annotations={
                    "summary": "Memory usage is above {{ .threshold }}%",
                    "description": "System memory usage is {{ .value }}%, which exceeds the threshold of {{ .threshold }}%"
                }
            ),
            AlertRule(
                name="disk_space_low",
                description="Low disk space",
                severity=AlertSeverity.CRITICAL,
                condition="disk_usage_percent > threshold",
                threshold=90.0,
                duration_seconds=300,
                labels={"component": "system", "type": "resource"},
                annotations={
                    "summary": "Disk usage is above {{ .threshold }}%",
                    "description": "System disk usage is {{ .value }}%, which exceeds the threshold of {{ .threshold }}%"
                }
            ),
            AlertRule(
                name="meilisearch_connection_failed",
                description="MeiliSearch connection failed",
                severity=AlertSeverity.CRITICAL,
                condition="meilisearch_connection_status == 0",
                threshold=0.0,
                duration_seconds=60,
                labels={"component": "meilisearch", "type": "connectivity"},
                annotations={
                    "summary": "MeiliSearch connection is down",
                    "description": "Unable to connect to MeiliSearch server"
                }
            ),
            AlertRule(
                name="tokenizer_engine_failed",
                description="Thai tokenizer engine failed",
                severity=AlertSeverity.CRITICAL,
                condition="tokenizer_health_status == 0",
                threshold=0.0,
                duration_seconds=60,
                labels={"component": "tokenizer", "type": "functionality"},
                annotations={
                    "summary": "Thai tokenizer engine is not working",
                    "description": "The Thai tokenization engine has failed and is not processing requests"
                }
            ),
            AlertRule(
                name="low_tokenization_accuracy",
                description="Low tokenization accuracy",
                severity=AlertSeverity.WARNING,
                condition="tokenization_accuracy_percent < threshold",
                threshold=90.0,
                duration_seconds=1800,
                labels={"component": "tokenizer", "type": "quality"},
                annotations={
                    "summary": "Tokenization accuracy is below {{ .threshold }}%",
                    "description": "The tokenization accuracy is {{ .value }}%, which is below the expected threshold of {{ .threshold }}%"
                }
            ),
            AlertRule(
                name="service_down",
                description="Service is down",
                severity=AlertSeverity.CRITICAL,
                condition="service_health_status == 0",
                threshold=0.0,
                duration_seconds=30,
                labels={"component": "service", "type": "availability"},
                annotations={
                    "summary": "Thai tokenizer service is down",
                    "description": "The Thai tokenizer service is not responding to health checks"
                }
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.name] = rule
        
        logger.info("Default alert rules loaded", total_rules=len(default_rules))
    
    def _load_rules_from_file(self, config_path: str):
        """Load alert rules from configuration file."""
        try:
            config_file = Path(config_path)
            if config_file.exists():
                with open(config_file, 'r') as f:
                    config_data = json.load(f)
                
                for rule_data in config_data.get("alert_rules", []):
                    rule = AlertRule(
                        name=rule_data["name"],
                        description=rule_data["description"],
                        severity=AlertSeverity(rule_data["severity"]),
                        condition=rule_data["condition"],
                        threshold=rule_data["threshold"],
                        duration_seconds=rule_data.get("duration_seconds", 300),
                        cooldown_seconds=rule_data.get("cooldown_seconds", 900),
                        enabled=rule_data.get("enabled", True),
                        labels=rule_data.get("labels", {}),
                        annotations=rule_data.get("annotations", {})
                    )
                    self.rules[rule.name] = rule
                
                logger.info("Custom alert rules loaded", 
                           config_path=config_path,
                           custom_rules=len(config_data.get("alert_rules", [])))
            
        except Exception as e:
            logger.error("Failed to load alert rules from file", 
                        config_path=config_path, error=e)
    
    def add_rule(self, rule: AlertRule):
        """Add or update an alert rule."""
        self.rules[rule.name] = rule
        logger.info("Alert rule added/updated", rule_name=rule.name, severity=rule.severity.value)
    
    def remove_rule(self, rule_name: str):
        """Remove an alert rule."""
        if rule_name in self.rules:
            del self.rules[rule_name]
            logger.info("Alert rule removed", rule_name=rule_name)
        else:
            logger.warning("Attempted to remove non-existent rule", rule_name=rule_name)
    
    def add_notification_handler(self, handler: Callable[[Alert], None]):
        """Add a notification handler for alerts."""
        self.notification_handlers.append(handler)
        logger.info("Notification handler added", total_handlers=len(self.notification_handlers))
    
    async def evaluate_rules(self, metrics: Dict[str, float]) -> List[Alert]:
        """Evaluate all alert rules against current metrics."""
        current_time = datetime.now()
        new_alerts = []
        resolved_alerts = []
        
        for rule_name, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            try:
                # Evaluate the rule condition
                triggered = self._evaluate_condition(rule, metrics)
                
                # Check if this rule is currently alerting
                existing_alert = self.active_alerts.get(rule_name)
                
                if triggered:
                    if existing_alert is None:
                        # Check if enough time has passed since last evaluation
                        last_eval = self.last_evaluation.get(rule_name, 0)
                        if current_time.timestamp() - last_eval >= rule.duration_seconds:
                            # Create new alert
                            alert = Alert(
                                rule_name=rule_name,
                                severity=rule.severity,
                                message=self._format_alert_message(rule, metrics),
                                status=AlertStatus.ACTIVE,
                                started_at=current_time,
                                labels=rule.labels.copy(),
                                annotations=self._format_annotations(rule, metrics),
                                value=metrics.get(self._extract_metric_name(rule.condition))
                            )
                            
                            self.active_alerts[rule_name] = alert
                            new_alerts.append(alert)
                            
                            logger.warning("Alert triggered", 
                                         rule_name=rule_name,
                                         severity=rule.severity.value,
                                         message=alert.message)
                    
                    # Update last evaluation time
                    self.last_evaluation[rule_name] = current_time.timestamp()
                
                else:
                    # Rule is not triggered
                    if existing_alert and existing_alert.status == AlertStatus.ACTIVE:
                        # Resolve the alert
                        existing_alert.status = AlertStatus.RESOLVED
                        existing_alert.resolved_at = current_time
                        resolved_alerts.append(existing_alert)
                        
                        # Move to history and remove from active
                        self.alert_history.append(existing_alert)
                        del self.active_alerts[rule_name]
                        
                        logger.info("Alert resolved", 
                                   rule_name=rule_name,
                                   duration_seconds=(current_time - existing_alert.started_at).total_seconds())
                    
                    # Reset evaluation time
                    self.last_evaluation.pop(rule_name, None)
            
            except Exception as e:
                logger.error("Failed to evaluate alert rule", 
                           rule_name=rule_name, error=e)
        
        # Send notifications for new and resolved alerts
        for alert in new_alerts + resolved_alerts:
            await self._send_notifications(alert)
        
        # Cleanup old history
        if len(self.alert_history) > self.max_history:
            self.alert_history = self.alert_history[-self.max_history:]
        
        return new_alerts
    
    def _evaluate_condition(self, rule: AlertRule, metrics: Dict[str, float]) -> bool:
        """Evaluate a rule condition against metrics."""
        try:
            # Simple condition evaluation
            # This is a basic implementation - in production, you might want a more sophisticated expression evaluator
            
            condition = rule.condition.replace("threshold", str(rule.threshold))
            
            # Replace metric names with actual values
            for metric_name, value in metrics.items():
                condition = condition.replace(metric_name, str(value))
            
            # Handle common operators
            if " > " in condition:
                left, right = condition.split(" > ")
                return float(left.strip()) > float(right.strip())
            elif " < " in condition:
                left, right = condition.split(" < ")
                return float(left.strip()) < float(right.strip())
            elif " == " in condition:
                left, right = condition.split(" == ")
                return float(left.strip()) == float(right.strip())
            elif " >= " in condition:
                left, right = condition.split(" >= ")
                return float(left.strip()) >= float(right.strip())
            elif " <= " in condition:
                left, right = condition.split(" <= ")
                return float(left.strip()) <= float(right.strip())
            else:
                logger.warning("Unsupported condition format", 
                             rule_name=rule.name, condition=rule.condition)
                return False
                
        except Exception as e:
            logger.error("Failed to evaluate condition", 
                        rule_name=rule.name, condition=rule.condition, error=e)
            return False
    
    def _extract_metric_name(self, condition: str) -> str:
        """Extract the primary metric name from a condition."""
        # Simple extraction - get the first word before an operator
        for op in [" > ", " < ", " == ", " >= ", " <= "]:
            if op in condition:
                return condition.split(op)[0].strip()
        return condition.strip()
    
    def _format_alert_message(self, rule: AlertRule, metrics: Dict[str, float]) -> str:
        """Format alert message with current metric values."""
        message = rule.description
        
        # Add current value if available
        metric_name = self._extract_metric_name(rule.condition)
        if metric_name in metrics:
            message += f" (current: {metrics[metric_name]}, threshold: {rule.threshold})"
        
        return message
    
    def _format_annotations(self, rule: AlertRule, metrics: Dict[str, float]) -> Dict[str, str]:
        """Format alert annotations with current values."""
        formatted_annotations = {}
        
        for key, template in rule.annotations.items():
            formatted_value = template
            
            # Replace placeholders
            formatted_value = formatted_value.replace("{{ .threshold }}", str(rule.threshold))
            
            # Replace metric values
            metric_name = self._extract_metric_name(rule.condition)
            if metric_name in metrics:
                formatted_value = formatted_value.replace("{{ .value }}", str(metrics[metric_name]))
            
            formatted_annotations[key] = formatted_value
        
        return formatted_annotations
    
    async def _send_notifications(self, alert: Alert):
        """Send notifications for an alert."""
        for handler in self.notification_handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(alert)
                else:
                    handler(alert)
            except Exception as e:
                logger.error("Notification handler failed", 
                           alert_name=alert.rule_name, error=e)
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, hours: int = 24) -> List[Alert]:
        """Get alert history for the specified time period."""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        return [
            alert for alert in self.alert_history
            if alert.started_at >= cutoff_time
        ]
    
    def get_alert_summary(self) -> Dict[str, Any]:
        """Get summary of alert status."""
        active_alerts = self.get_active_alerts()
        recent_history = self.get_alert_history(24)
        
        # Count by severity
        active_by_severity = {}
        for severity in AlertSeverity:
            active_by_severity[severity.value] = sum(
                1 for alert in active_alerts if alert.severity == severity
            )
        
        # Count resolved in last 24h
        resolved_24h = sum(
            1 for alert in recent_history if alert.status == AlertStatus.RESOLVED
        )
        
        return {
            "active_alerts": len(active_alerts),
            "active_by_severity": active_by_severity,
            "resolved_last_24h": resolved_24h,
            "total_rules": len(self.rules),
            "enabled_rules": sum(1 for rule in self.rules.values() if rule.enabled),
            "last_evaluation": max(self.last_evaluation.values()) if self.last_evaluation else 0
        }
    
    def suppress_alert(self, rule_name: str, duration_seconds: int = 3600):
        """Suppress an alert for a specified duration."""
        if rule_name in self.active_alerts:
            alert = self.active_alerts[rule_name]
            alert.status = AlertStatus.SUPPRESSED
            
            # Schedule unsuppression
            async def unsuppress():
                await asyncio.sleep(duration_seconds)
                if rule_name in self.active_alerts and self.active_alerts[rule_name].status == AlertStatus.SUPPRESSED:
                    self.active_alerts[rule_name].status = AlertStatus.ACTIVE
                    logger.info("Alert unsuppressed", rule_name=rule_name)
            
            asyncio.create_task(unsuppress())
            logger.info("Alert suppressed", rule_name=rule_name, duration_seconds=duration_seconds)
    
    def export_prometheus_rules(self) -> str:
        """Export alert rules in Prometheus format."""
        prometheus_rules = {
            "groups": [
                {
                    "name": "thai_tokenizer_alerts",
                    "rules": []
                }
            ]
        }
        
        for rule in self.rules.values():
            if rule.enabled:
                prometheus_rule = {
                    "alert": rule.name,
                    "expr": self._convert_to_prometheus_expr(rule.condition, rule.threshold),
                    "for": f"{rule.duration_seconds}s",
                    "labels": {
                        "severity": rule.severity.value,
                        **rule.labels
                    },
                    "annotations": {
                        "summary": rule.description,
                        **rule.annotations
                    }
                }
                prometheus_rules["groups"][0]["rules"].append(prometheus_rule)
        
        return json.dumps(prometheus_rules, indent=2)
    
    def _convert_to_prometheus_expr(self, condition: str, threshold: float) -> str:
        """Convert internal condition format to Prometheus expression."""
        # This is a basic conversion - in production, you'd want more sophisticated mapping
        metric_mapping = {
            "error_rate_per_hour": "rate(thai_tokenizer_errors_total[1h]) * 3600",
            "average_response_time_ms": "thai_tokenizer_response_time_ms",
            "success_rate_percent": "thai_tokenizer_success_rate_percent",
            "cpu_usage_percent": "thai_tokenizer_cpu_usage_percent",
            "memory_usage_percent": "thai_tokenizer_memory_usage_percent",
            "disk_usage_percent": "thai_tokenizer_disk_usage_percent",
            "meilisearch_connection_status": "thai_tokenizer_meilisearch_connection_status",
            "tokenizer_health_status": "thai_tokenizer_health_check{check=\"tokenizer\"}",
            "service_health_status": "thai_tokenizer_health_status"
        }
        
        # Replace condition with Prometheus expression
        for internal_metric, prometheus_metric in metric_mapping.items():
            if internal_metric in condition:
                expr = condition.replace(internal_metric, prometheus_metric)
                expr = expr.replace("threshold", str(threshold))
                return expr
        
        # Fallback
        return condition.replace("threshold", str(threshold))
    
    def save_config(self, config_path: str):
        """Save current alert rules to configuration file."""
        try:
            config_data = {
                "alert_rules": [
                    {
                        "name": rule.name,
                        "description": rule.description,
                        "severity": rule.severity.value,
                        "condition": rule.condition,
                        "threshold": rule.threshold,
                        "duration_seconds": rule.duration_seconds,
                        "cooldown_seconds": rule.cooldown_seconds,
                        "enabled": rule.enabled,
                        "labels": rule.labels,
                        "annotations": rule.annotations
                    }
                    for rule in self.rules.values()
                ]
            }
            
            config_file = Path(config_path)
            config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(config_file, 'w') as f:
                json.dump(config_data, f, indent=2)
            
            logger.info("Alert rules saved to file", 
                       config_path=config_path, 
                       total_rules=len(self.rules))
            
        except Exception as e:
            logger.error("Failed to save alert rules", 
                        config_path=config_path, error=e)


# Notification handlers
async def webhook_notification_handler(webhook_url: str, alert: Alert):
    """Send alert notification via webhook."""
    try:
        import aiohttp
        
        payload = {
            "alert": {
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "started_at": alert.started_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "value": alert.value
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload, timeout=10) as response:
                if response.status == 200:
                    logger.info("Webhook notification sent", 
                               alert_name=alert.rule_name, webhook_url=webhook_url)
                else:
                    logger.error("Webhook notification failed", 
                               alert_name=alert.rule_name, 
                               webhook_url=webhook_url,
                               status_code=response.status)
                    
    except Exception as e:
        logger.error("Webhook notification error", 
                    alert_name=alert.rule_name, webhook_url=webhook_url, error=e)


def email_notification_handler(smtp_config: Dict[str, Any], alert: Alert):
    """Send alert notification via email."""
    try:
        import smtplib
        from email.mime.text import MimeText
        from email.mime.multipart import MimeMultipart
        
        # Create message
        msg = MimeMultipart()
        msg['From'] = smtp_config['from_email']
        msg['To'] = ', '.join(smtp_config['to_emails'])
        msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.rule_name}"
        
        # Create email body
        body = f"""
Alert: {alert.rule_name}
Severity: {alert.severity.value}
Status: {alert.status.value}
Message: {alert.message}
Started: {alert.started_at.isoformat()}
{"Resolved: " + alert.resolved_at.isoformat() if alert.resolved_at else ""}

Labels: {json.dumps(alert.labels, indent=2)}
Annotations: {json.dumps(alert.annotations, indent=2)}
"""
        
        msg.attach(MimeText(body, 'plain'))
        
        # Send email
        server = smtplib.SMTP(smtp_config['smtp_host'], smtp_config['smtp_port'])
        if smtp_config.get('use_tls'):
            server.starttls()
        if smtp_config.get('username'):
            server.login(smtp_config['username'], smtp_config['password'])
        
        server.send_message(msg)
        server.quit()
        
        logger.info("Email notification sent", 
                   alert_name=alert.rule_name, 
                   to_emails=smtp_config['to_emails'])
        
    except Exception as e:
        logger.error("Email notification error", 
                    alert_name=alert.rule_name, error=e)


def slack_notification_handler(slack_webhook_url: str, alert: Alert):
    """Send alert notification to Slack."""
    try:
        import requests
        
        # Determine color based on severity and status
        color_map = {
            (AlertSeverity.CRITICAL, AlertStatus.ACTIVE): "danger",
            (AlertSeverity.WARNING, AlertStatus.ACTIVE): "warning",
            (AlertSeverity.INFO, AlertStatus.ACTIVE): "good",
            (AlertSeverity.CRITICAL, AlertStatus.RESOLVED): "good",
            (AlertSeverity.WARNING, AlertStatus.RESOLVED): "good",
            (AlertSeverity.INFO, AlertStatus.RESOLVED): "good",
        }
        
        color = color_map.get((alert.severity, alert.status), "warning")
        
        # Create Slack message
        payload = {
            "attachments": [
                {
                    "color": color,
                    "title": f"{alert.severity.value.upper()}: {alert.rule_name}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Status",
                            "value": alert.status.value,
                            "short": True
                        },
                        {
                            "title": "Started",
                            "value": alert.started_at.strftime("%Y-%m-%d %H:%M:%S"),
                            "short": True
                        }
                    ],
                    "footer": "Thai Tokenizer Monitoring",
                    "ts": int(alert.started_at.timestamp())
                }
            ]
        }
        
        if alert.resolved_at:
            payload["attachments"][0]["fields"].append({
                "title": "Resolved",
                "value": alert.resolved_at.strftime("%Y-%m-%d %H:%M:%S"),
                "short": True
            })
        
        response = requests.post(slack_webhook_url, json=payload, timeout=10)
        
        if response.status_code == 200:
            logger.info("Slack notification sent", alert_name=alert.rule_name)
        else:
            logger.error("Slack notification failed", 
                        alert_name=alert.rule_name, 
                        status_code=response.status_code)
            
    except Exception as e:
        logger.error("Slack notification error", 
                    alert_name=alert.rule_name, error=e)