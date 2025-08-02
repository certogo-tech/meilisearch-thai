"""Monitoring integration endpoints for on-premise deployment."""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Depends, status, Query, BackgroundTasks
from fastapi.responses import JSONResponse, PlainTextResponse

from src.monitoring.alerting import AlertManager, AlertRule, AlertSeverity
from src.monitoring.log_aggregation import LogAggregator, LogAnalyzer
from src.monitoring.dashboard_templates import DashboardGenerator
from src.utils.health import health_checker
from src.utils.logging import get_structured_logger

logger = get_structured_logger(__name__)

router = APIRouter()

# Global instances
alert_manager = AlertManager()
log_aggregator = LogAggregator()
log_analyzer = LogAnalyzer(log_aggregator)
dashboard_generator = DashboardGenerator()


@router.get("/monitoring/alerts")
async def get_alerts(
    active_only: bool = Query(False, description="Return only active alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity (critical, warning, info)")
):
    """
    Get current alerts and alert history.
    
    Returns active alerts and recent alert history for monitoring dashboards.
    """
    try:
        if active_only:
            alerts = alert_manager.get_active_alerts()
        else:
            alerts = alert_manager.get_active_alerts() + alert_manager.get_alert_history(24)
        
        # Filter by severity if specified
        if severity:
            try:
                severity_filter = AlertSeverity(severity.lower())
                alerts = [alert for alert in alerts if alert.severity == severity_filter]
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid severity: {severity}. Must be one of: critical, warning, info"
                )
        
        # Convert alerts to dict format
        alerts_data = []
        for alert in alerts:
            alerts_data.append({
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "message": alert.message,
                "started_at": alert.started_at.isoformat(),
                "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                "labels": alert.labels,
                "annotations": alert.annotations,
                "value": alert.value
            })
        
        # Get alert summary
        summary = alert_manager.get_alert_summary()
        
        response = {
            "alerts": alerts_data,
            "summary": summary,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("Alerts retrieved", 
                   total_alerts=len(alerts_data),
                   active_alerts=summary["active_alerts"],
                   severity_filter=severity)
        
        return response
        
    except Exception as e:
        logger.error("Failed to get alerts", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve alerts: {str(e)}"
        )


@router.post("/monitoring/alerts/evaluate")
async def evaluate_alerts(background_tasks: BackgroundTasks):
    """
    Manually trigger alert evaluation.
    
    Evaluates all alert rules against current metrics and triggers notifications.
    """
    try:
        # Get current metrics from health checker
        system_metrics = health_checker.get_system_metrics()
        tokenizer_metrics = health_checker.get_tokenizer_metrics()
        check_results = await health_checker.run_all_checks()
        
        # Convert to metrics format expected by alert manager
        metrics = {
            "cpu_usage_percent": system_metrics.cpu_usage_percent,
            "memory_usage_percent": system_metrics.memory_usage_percent,
            "disk_usage_percent": system_metrics.disk_usage_percent,
            "average_response_time_ms": tokenizer_metrics.average_response_time_ms,
            "success_rate_percent": (tokenizer_metrics.successful_requests / tokenizer_metrics.total_requests * 100) if tokenizer_metrics.total_requests > 0 else 100,
            "error_rate_per_hour": tokenizer_metrics.failed_requests,  # Simplified calculation
            "meilisearch_connection_status": 1 if check_results.get("meilisearch", type('obj', (object,), {'status': 'unhealthy'})).status.value == "healthy" else 0,
            "tokenizer_health_status": 1 if check_results.get("tokenizer", type('obj', (object,), {'status': 'unhealthy'})).status.value == "healthy" else 0,
            "service_health_status": 1 if health_checker.get_overall_status(check_results).value == "healthy" else 0,
            "tokenization_accuracy_percent": tokenizer_metrics.tokenization_accuracy * 100
        }
        
        # Evaluate alerts in background
        background_tasks.add_task(alert_manager.evaluate_rules, metrics)
        
        return {
            "message": "Alert evaluation triggered",
            "metrics_evaluated": len(metrics),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to evaluate alerts", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to evaluate alerts: {str(e)}"
        )


@router.post("/monitoring/alerts/suppress/{rule_name}")
async def suppress_alert(
    rule_name: str,
    duration_seconds: int = Query(3600, description="Suppression duration in seconds")
):
    """
    Suppress an active alert for a specified duration.
    
    Args:
        rule_name: Name of the alert rule to suppress
        duration_seconds: How long to suppress the alert (default: 1 hour)
    """
    try:
        if rule_name not in alert_manager.active_alerts:
            raise HTTPException(
                status_code=404,
                detail=f"No active alert found for rule: {rule_name}"
            )
        
        alert_manager.suppress_alert(rule_name, duration_seconds)
        
        return {
            "message": f"Alert '{rule_name}' suppressed for {duration_seconds} seconds",
            "rule_name": rule_name,
            "duration_seconds": duration_seconds,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to suppress alert", rule_name=rule_name, error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to suppress alert: {str(e)}"
        )


@router.get("/monitoring/logs/analyze")
async def analyze_logs(
    hours_back: int = Query(24, description="Hours of logs to analyze"),
    log_types: Optional[str] = Query(None, description="Comma-separated log types (app,performance,errors,metrics)")
):
    """
    Analyze log files and provide insights.
    
    Returns log analysis results including error patterns, performance metrics, and recommendations.
    """
    try:
        # Parse log types
        log_types_list = None
        if log_types:
            log_types_list = [t.strip() for t in log_types.split(",")]
        
        # Perform log analysis
        analysis_result = log_analyzer.analyze_logs(hours_back)
        
        # Convert to response format
        response = {
            "analysis_period": {
                "hours_back": hours_back,
                "start_time": analysis_result.time_range[0].isoformat(),
                "end_time": analysis_result.time_range[1].isoformat()
            },
            "summary": {
                "total_entries": analysis_result.total_entries,
                "entries_by_level": analysis_result.entries_by_level
            },
            "error_analysis": {
                "patterns": analysis_result.error_patterns,
                "top_errors": analysis_result.top_errors
            },
            "performance_analysis": analysis_result.performance_metrics,
            "request_patterns": analysis_result.request_patterns,
            "recommendations": analysis_result.recommendations,
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("Log analysis completed", 
                   hours_back=hours_back,
                   total_entries=analysis_result.total_entries,
                   error_patterns=len(analysis_result.error_patterns),
                   recommendations=len(analysis_result.recommendations))
        
        return response
        
    except Exception as e:
        logger.error("Failed to analyze logs", hours_back=hours_back, error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to analyze logs: {str(e)}"
        )


@router.get("/monitoring/logs/aggregate")
async def aggregate_logs(
    hours_back: int = Query(24, description="Hours of logs to aggregate"),
    log_types: Optional[str] = Query(None, description="Comma-separated log types")
):
    """
    Aggregate log data for monitoring dashboards.
    
    Returns aggregated log statistics suitable for dashboard visualization.
    """
    try:
        # Parse log types
        log_types_list = None
        if log_types:
            log_types_list = [t.strip() for t in log_types.split(",")]
        
        # Aggregate logs
        aggregated_data = log_aggregator.aggregate_logs(hours_back, log_types_list)
        
        logger.info("Log aggregation completed", 
                   hours_back=hours_back,
                   total_entries=aggregated_data["total_entries"])
        
        return aggregated_data
        
    except Exception as e:
        logger.error("Failed to aggregate logs", hours_back=hours_back, error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to aggregate logs: {str(e)}"
        )


@router.get("/monitoring/dashboards/grafana/{dashboard_type}")
async def get_grafana_dashboard(dashboard_type: str):
    """
    Get Grafana dashboard configuration.
    
    Args:
        dashboard_type: Type of dashboard (overview, performance, errors)
    """
    try:
        if dashboard_type == "overview":
            dashboard = dashboard_generator.generate_grafana_overview_dashboard()
        elif dashboard_type == "performance":
            dashboard = dashboard_generator.generate_grafana_performance_dashboard()
        elif dashboard_type == "errors":
            dashboard = dashboard_generator.generate_grafana_errors_dashboard()
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid dashboard type: {dashboard_type}. Must be one of: overview, performance, errors"
            )
        
        logger.info("Grafana dashboard generated", dashboard_type=dashboard_type)
        
        return dashboard
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate Grafana dashboard", 
                    dashboard_type=dashboard_type, error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate dashboard: {str(e)}"
        )


@router.get("/monitoring/config/prometheus", response_class=PlainTextResponse)
async def get_prometheus_config(
    service_host: str = Query("localhost", description="Service host for scraping"),
    service_port: int = Query(8000, description="Service port for scraping")
):
    """
    Get Prometheus configuration for Thai tokenizer service.
    
    Returns Prometheus configuration in YAML format.
    """
    try:
        config = dashboard_generator.generate_prometheus_config(service_host, service_port)
        
        # Convert to YAML
        import yaml
        yaml_config = yaml.dump(config, default_flow_style=False)
        
        logger.info("Prometheus configuration generated", 
                   service_host=service_host, service_port=service_port)
        
        return PlainTextResponse(
            content=yaml_config,
            media_type="text/yaml"
        )
        
    except Exception as e:
        logger.error("Failed to generate Prometheus config", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Prometheus config: {str(e)}"
        )


@router.get("/monitoring/config/alertmanager", response_class=PlainTextResponse)
async def get_alertmanager_config(
    notification_configs: Optional[str] = Query(None, description="JSON string of notification configurations")
):
    """
    Get Alertmanager configuration.
    
    Returns Alertmanager configuration in YAML format.
    """
    try:
        # Parse notification configs
        notifications = []
        if notification_configs:
            try:
                notifications = json.loads(notification_configs)
            except json.JSONDecodeError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid JSON in notification_configs parameter"
                )
        
        config = dashboard_generator.generate_alertmanager_config(notifications)
        
        # Convert to YAML
        import yaml
        yaml_config = yaml.dump(config, default_flow_style=False)
        
        logger.info("Alertmanager configuration generated", 
                   notification_configs_count=len(notifications))
        
        return PlainTextResponse(
            content=yaml_config,
            media_type="text/yaml"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to generate Alertmanager config", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Alertmanager config: {str(e)}"
        )


@router.get("/monitoring/config/docker-compose")
async def get_docker_compose_monitoring():
    """
    Get Docker Compose configuration for monitoring stack.
    
    Returns Docker Compose configuration for Prometheus, Grafana, and Alertmanager.
    """
    try:
        config = dashboard_generator.generate_docker_compose_monitoring()
        
        logger.info("Docker Compose monitoring configuration generated")
        
        return config
        
    except Exception as e:
        logger.error("Failed to generate Docker Compose config", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Docker Compose config: {str(e)}"
        )


@router.post("/monitoring/export/elasticsearch")
async def export_logs_to_elasticsearch(
    hours_back: int = Query(24, description="Hours of logs to export"),
    batch_size: int = Query(1000, description="Batch size for export")
):
    """
    Export logs in Elasticsearch bulk format.
    
    Returns logs formatted for Elasticsearch ingestion.
    """
    try:
        batches = []
        batch_count = 0
        
        for batch in log_aggregator.export_for_elasticsearch(hours_back, batch_size):
            batches.extend(batch)
            batch_count += 1
            
            # Limit response size
            if batch_count >= 10:  # Max 10 batches in response
                break
        
        response = {
            "elasticsearch_bulk_data": batches,
            "batch_count": batch_count,
            "total_documents": len(batches) // 2,  # Each document has metadata + data
            "timestamp": datetime.now().isoformat()
        }
        
        logger.info("Elasticsearch export completed", 
                   batch_count=batch_count,
                   total_documents=response["total_documents"])
        
        return response
        
    except Exception as e:
        logger.error("Failed to export logs to Elasticsearch", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export logs: {str(e)}"
        )


@router.get("/monitoring/rules/prometheus", response_class=PlainTextResponse)
async def get_prometheus_alert_rules():
    """
    Get Prometheus alert rules configuration.
    
    Returns alert rules in Prometheus format.
    """
    try:
        rules_config = alert_manager.export_prometheus_rules()
        
        logger.info("Prometheus alert rules exported", 
                   total_rules=len(alert_manager.rules))
        
        return PlainTextResponse(
            content=rules_config,
            media_type="text/yaml"
        )
        
    except Exception as e:
        logger.error("Failed to export Prometheus rules", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export alert rules: {str(e)}"
        )


@router.post("/monitoring/setup/complete")
async def setup_monitoring_stack(
    output_directory: str = Query("/tmp/thai-tokenizer-monitoring", description="Directory to save monitoring configs"),
    service_host: str = Query("localhost", description="Service host"),
    service_port: int = Query(8000, description="Service port")
):
    """
    Generate complete monitoring stack configuration.
    
    Creates all necessary configuration files for Prometheus, Grafana, and Alertmanager.
    """
    try:
        output_path = Path(output_directory)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Generate and save all configurations
        dashboard_generator.save_dashboard_configs(str(output_path))
        
        # Generate Docker Compose file
        docker_compose = dashboard_generator.generate_docker_compose_monitoring()
        with open(output_path / "docker-compose.monitoring.yml", "w") as f:
            import yaml
            yaml.dump(docker_compose, f, default_flow_style=False)
        
        # Generate alert rules
        alert_rules = alert_manager.export_prometheus_rules()
        with open(output_path / "thai_tokenizer_alerts.yml", "w") as f:
            f.write(alert_rules)
        
        # Generate setup instructions
        setup_instructions = f"""
# Thai Tokenizer Monitoring Setup

## Quick Start with Docker Compose

1. Start the monitoring stack:
   ```bash
   docker-compose -f docker-compose.monitoring.yml up -d
   ```

2. Access the services:
   - Grafana: http://localhost:3000 (admin/admin)
   - Prometheus: http://localhost:9090
   - Alertmanager: http://localhost:9093

## Manual Setup

1. Copy prometheus.yml to your Prometheus configuration directory
2. Copy thai_tokenizer_alerts.yml to your Prometheus rules directory
3. Import Grafana dashboards from grafana-*-dashboard.json files
4. Configure Alertmanager with alertmanager.yml

## Service Configuration

Make sure your Thai Tokenizer service is running on {service_host}:{service_port}
and exposing metrics at /metrics endpoint.

## Customization

Edit the configuration files as needed for your environment:
- Update service endpoints in prometheus.yml
- Modify alert thresholds in thai_tokenizer_alerts.yml
- Customize dashboard panels in Grafana JSON files
- Configure notification channels in alertmanager.yml
"""
        
        with open(output_path / "README.md", "w") as f:
            f.write(setup_instructions)
        
        # List generated files
        generated_files = list(output_path.glob("*"))
        file_names = [f.name for f in generated_files]
        
        logger.info("Monitoring stack setup completed", 
                   output_directory=output_directory,
                   files_generated=len(file_names))
        
        return {
            "message": "Monitoring stack configuration generated successfully",
            "output_directory": output_directory,
            "generated_files": file_names,
            "setup_instructions": "See README.md in the output directory",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error("Failed to setup monitoring stack", 
                    output_directory=output_directory, error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to setup monitoring stack: {str(e)}"
        )