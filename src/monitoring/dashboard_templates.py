"""Dashboard configuration templates for monitoring systems."""

import json
from typing import Dict, Any, List, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

from src.utils.logging import get_structured_logger

logger = get_structured_logger(__name__)


@dataclass
class PrometheusConfig:
    """Prometheus configuration for Thai tokenizer monitoring."""
    scrape_interval: str = "15s"
    evaluation_interval: str = "15s"
    external_labels: Dict[str, str] = None
    
    def __post_init__(self):
        if self.external_labels is None:
            self.external_labels = {"service": "thai-tokenizer"}


@dataclass
class GrafanaDashboard:
    """Grafana dashboard configuration."""
    title: str
    description: str
    tags: List[str]
    panels: List[Dict[str, Any]]
    time_range: Dict[str, str] = None
    refresh_interval: str = "30s"
    
    def __post_init__(self):
        if self.time_range is None:
            self.time_range = {"from": "now-1h", "to": "now"}


class DashboardGenerator:
    """Generates monitoring dashboard configurations for various systems."""
    
    def __init__(self):
        self.service_name = "thai-tokenizer"
        self.metric_prefix = "thai_tokenizer"
    
    def generate_prometheus_config(self, 
                                 service_host: str = "localhost",
                                 service_port: int = 8000,
                                 scrape_interval: str = "15s") -> Dict[str, Any]:
        """Generate Prometheus configuration for Thai tokenizer service."""
        config = {
            "global": {
                "scrape_interval": scrape_interval,
                "evaluation_interval": scrape_interval,
                "external_labels": {
                    "service": self.service_name,
                    "environment": "production"
                }
            },
            "rule_files": [
                "thai_tokenizer_alerts.yml"
            ],
            "scrape_configs": [
                {
                    "job_name": "thai-tokenizer",
                    "static_configs": [
                        {
                            "targets": [f"{service_host}:{service_port}"]
                        }
                    ],
                    "metrics_path": "/metrics",
                    "scrape_interval": scrape_interval,
                    "scrape_timeout": "10s",
                    "honor_labels": True,
                    "params": {
                        "format": ["prometheus"]
                    }
                },
                {
                    "job_name": "thai-tokenizer-health",
                    "static_configs": [
                        {
                            "targets": [f"{service_host}:{service_port}"]
                        }
                    ],
                    "metrics_path": "/metrics/health",
                    "scrape_interval": "30s",
                    "scrape_timeout": "5s"
                }
            ],
            "alerting": {
                "alertmanagers": [
                    {
                        "static_configs": [
                            {
                                "targets": ["alertmanager:9093"]
                            }
                        ]
                    }
                ]
            }
        }
        
        return config
    
    def generate_grafana_overview_dashboard(self) -> Dict[str, Any]:
        """Generate Grafana overview dashboard for Thai tokenizer service."""
        panels = [
            # Service Status Panel
            {
                "id": 1,
                "title": "Service Status",
                "type": "stat",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_health_status",
                        "legendFormat": "Health Status"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "mappings": [
                            {"options": {"0": {"text": "Unhealthy", "color": "red"}}},
                            {"options": {"1": {"text": "Degraded", "color": "yellow"}}},
                            {"options": {"2": {"text": "Healthy", "color": "green"}}}
                        ],
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": 0},
                                {"color": "yellow", "value": 1},
                                {"color": "green", "value": 2}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0}
            },
            
            # Request Rate Panel
            {
                "id": 2,
                "title": "Request Rate",
                "type": "graph",
                "targets": [
                    {
                        "expr": f"rate({self.metric_prefix}_requests_total[5m])",
                        "legendFormat": "Requests/sec"
                    }
                ],
                "yAxes": [
                    {"label": "Requests/sec", "min": 0}
                ],
                "gridPos": {"h": 8, "w": 12, "x": 6, "y": 0}
            },
            
            # Response Time Panel
            {
                "id": 3,
                "title": "Response Time",
                "type": "graph",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_response_time_ms",
                        "legendFormat": "Average"
                    },
                    {
                        "expr": f"{self.metric_prefix}_response_time_p95_ms",
                        "legendFormat": "95th Percentile"
                    },
                    {
                        "expr": f"{self.metric_prefix}_response_time_p99_ms",
                        "legendFormat": "99th Percentile"
                    }
                ],
                "yAxes": [
                    {"label": "Milliseconds", "min": 0}
                ],
                "gridPos": {"h": 8, "w": 12, "x": 18, "y": 0}
            },
            
            # Error Rate Panel
            {
                "id": 4,
                "title": "Error Rate",
                "type": "graph",
                "targets": [
                    {
                        "expr": f"rate({self.metric_prefix}_requests_failed_total[5m])",
                        "legendFormat": "Errors/sec"
                    }
                ],
                "yAxes": [
                    {"label": "Errors/sec", "min": 0}
                ],
                "alert": {
                    "conditions": [
                        {
                            "evaluator": {"params": [0.1], "type": "gt"},
                            "operator": {"type": "and"},
                            "query": {"params": ["A", "5m", "now"]},
                            "reducer": {"params": [], "type": "avg"},
                            "type": "query"
                        }
                    ],
                    "executionErrorState": "alerting",
                    "for": "5m",
                    "frequency": "10s",
                    "handler": 1,
                    "name": "High Error Rate",
                    "noDataState": "no_data",
                    "notifications": []
                },
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
            },
            
            # System Resources Panel
            {
                "id": 5,
                "title": "System Resources",
                "type": "graph",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_cpu_usage_percent",
                        "legendFormat": "CPU %"
                    },
                    {
                        "expr": f"{self.metric_prefix}_memory_usage_percent",
                        "legendFormat": "Memory %"
                    },
                    {
                        "expr": f"{self.metric_prefix}_disk_usage_percent",
                        "legendFormat": "Disk %"
                    }
                ],
                "yAxes": [
                    {"label": "Percentage", "min": 0, "max": 100}
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
            },
            
            # Health Checks Panel
            {
                "id": 6,
                "title": "Health Checks",
                "type": "table",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_health_check",
                        "format": "table",
                        "instant": True
                    }
                ],
                "transformations": [
                    {
                        "id": "organize",
                        "options": {
                            "excludeByName": {"Time": True, "__name__": True},
                            "indexByName": {},
                            "renameByName": {
                                "check": "Health Check",
                                "Value": "Status",
                                "critical": "Critical"
                            }
                        }
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16}
            },
            
            # Tokenization Metrics Panel
            {
                "id": 7,
                "title": "Tokenization Quality",
                "type": "stat",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_accuracy_percent",
                        "legendFormat": "Accuracy"
                    },
                    {
                        "expr": f"{self.metric_prefix}_compound_word_detection_rate_percent",
                        "legendFormat": "Compound Word Detection"
                    },
                    {
                        "expr": f"{self.metric_prefix}_cache_hit_rate_percent",
                        "legendFormat": "Cache Hit Rate"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent",
                        "min": 0,
                        "max": 100,
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": 0},
                                {"color": "yellow", "value": 80},
                                {"color": "green", "value": 95}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16}
            }
        ]
        
        dashboard = GrafanaDashboard(
            title="Thai Tokenizer - Overview",
            description="Overview dashboard for Thai Tokenizer service monitoring",
            tags=["thai-tokenizer", "overview", "monitoring"],
            panels=panels,
            time_range={"from": "now-1h", "to": "now"},
            refresh_interval="30s"
        )
        
        return self._convert_to_grafana_json(dashboard)
    
    def generate_grafana_performance_dashboard(self) -> Dict[str, Any]:
        """Generate Grafana performance dashboard."""
        panels = [
            # Throughput Panel
            {
                "id": 1,
                "title": "Throughput",
                "type": "graph",
                "targets": [
                    {
                        "expr": f"rate({self.metric_prefix}_requests_total[5m])",
                        "legendFormat": "Requests/sec"
                    },
                    {
                        "expr": f"{self.metric_prefix}_tokens_per_second",
                        "legendFormat": "Tokens/sec"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0}
            },
            
            # Response Time Distribution
            {
                "id": 2,
                "title": "Response Time Distribution",
                "type": "heatmap",
                "targets": [
                    {
                        "expr": f"rate({self.metric_prefix}_response_time_bucket[5m])",
                        "format": "heatmap",
                        "legendFormat": "{{le}}"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
            },
            
            # Memory Usage Over Time
            {
                "id": 3,
                "title": "Memory Usage",
                "type": "graph",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_memory_used_bytes",
                        "legendFormat": "Used Memory"
                    },
                    {
                        "expr": f"{self.metric_prefix}_memory_available_bytes",
                        "legendFormat": "Available Memory"
                    }
                ],
                "yAxes": [
                    {"label": "Bytes", "min": 0}
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
            },
            
            # GC Metrics
            {
                "id": 4,
                "title": "Garbage Collection",
                "type": "graph",
                "targets": [
                    {
                        "expr": f"rate({self.metric_prefix}_gc_collections_total[5m])",
                        "legendFormat": "GC Rate - Gen {{generation}}"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
            }
        ]
        
        dashboard = GrafanaDashboard(
            title="Thai Tokenizer - Performance",
            description="Performance monitoring dashboard for Thai Tokenizer service",
            tags=["thai-tokenizer", "performance", "monitoring"],
            panels=panels
        )
        
        return self._convert_to_grafana_json(dashboard)
    
    def generate_grafana_errors_dashboard(self) -> Dict[str, Any]:
        """Generate Grafana errors and debugging dashboard."""
        panels = [
            # Error Rate Over Time
            {
                "id": 1,
                "title": "Error Rate",
                "type": "graph",
                "targets": [
                    {
                        "expr": f"rate({self.metric_prefix}_errors_total[5m])",
                        "legendFormat": "Total Errors/sec"
                    },
                    {
                        "expr": f"rate({self.metric_prefix}_errors_by_type_total[5m])",
                        "legendFormat": "{{error_type}}"
                    }
                ],
                "gridPos": {"h": 8, "w": 24, "x": 0, "y": 0}
            },
            
            # Error Types Distribution
            {
                "id": 2,
                "title": "Error Types (Last 24h)",
                "type": "piechart",
                "targets": [
                    {
                        "expr": f"increase({self.metric_prefix}_errors_by_type_total[24h])",
                        "legendFormat": "{{error_type}}"
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 0, "y": 8}
            },
            
            # Health Check Status
            {
                "id": 3,
                "title": "Failed Health Checks",
                "type": "table",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_health_check == 0",
                        "format": "table",
                        "instant": True
                    }
                ],
                "gridPos": {"h": 8, "w": 12, "x": 12, "y": 8}
            },
            
            # Service Uptime
            {
                "id": 4,
                "title": "Service Uptime",
                "type": "stat",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_uptime_percent",
                        "legendFormat": "Uptime %"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "percent",
                        "thresholds": {
                            "steps": [
                                {"color": "red", "value": 0},
                                {"color": "yellow", "value": 99},
                                {"color": "green", "value": 99.9}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 4, "w": 6, "x": 0, "y": 16}
            },
            
            # MTTR
            {
                "id": 5,
                "title": "Mean Time To Recovery",
                "type": "stat",
                "targets": [
                    {
                        "expr": f"{self.metric_prefix}_mttr_seconds",
                        "legendFormat": "MTTR"
                    }
                ],
                "fieldConfig": {
                    "defaults": {
                        "unit": "s",
                        "thresholds": {
                            "steps": [
                                {"color": "green", "value": 0},
                                {"color": "yellow", "value": 300},
                                {"color": "red", "value": 900}
                            ]
                        }
                    }
                },
                "gridPos": {"h": 4, "w": 6, "x": 6, "y": 16}
            }
        ]
        
        dashboard = GrafanaDashboard(
            title="Thai Tokenizer - Errors & Debugging",
            description="Error monitoring and debugging dashboard for Thai Tokenizer service",
            tags=["thai-tokenizer", "errors", "debugging", "monitoring"],
            panels=panels
        )
        
        return self._convert_to_grafana_json(dashboard)
    
    def generate_alertmanager_config(self, 
                                   notification_configs: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate Alertmanager configuration."""
        config = {
            "global": {
                "smtp_smarthost": "localhost:587",
                "smtp_from": "alerts@thai-tokenizer.local"
            },
            "route": {
                "group_by": ["alertname", "severity"],
                "group_wait": "10s",
                "group_interval": "10s",
                "repeat_interval": "1h",
                "receiver": "default"
            },
            "receivers": [
                {
                    "name": "default",
                    "email_configs": [
                        {
                            "to": "admin@thai-tokenizer.local",
                            "subject": "[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}",
                            "body": """
{{ range .Alerts }}
Alert: {{ .Annotations.summary }}
Description: {{ .Annotations.description }}
Severity: {{ .Labels.severity }}
Started: {{ .StartsAt }}
{{ if .EndsAt }}Ended: {{ .EndsAt }}{{ end }}
{{ end }}
"""
                        }
                    ]
                }
            ]
        }
        
        # Add custom notification configurations
        for notification_config in notification_configs:
            if notification_config["type"] == "slack":
                config["receivers"][0]["slack_configs"] = [
                    {
                        "api_url": notification_config["webhook_url"],
                        "channel": notification_config.get("channel", "#alerts"),
                        "title": "[{{ .Status | toUpper }}] {{ .GroupLabels.alertname }}",
                        "text": "{{ range .Alerts }}{{ .Annotations.summary }}{{ end }}"
                    }
                ]
            elif notification_config["type"] == "webhook":
                config["receivers"][0]["webhook_configs"] = [
                    {
                        "url": notification_config["url"],
                        "send_resolved": True
                    }
                ]
        
        return config
    
    def _convert_to_grafana_json(self, dashboard: GrafanaDashboard) -> Dict[str, Any]:
        """Convert dashboard configuration to Grafana JSON format."""
        return {
            "dashboard": {
                "id": None,
                "title": dashboard.title,
                "description": dashboard.description,
                "tags": dashboard.tags,
                "timezone": "browser",
                "panels": dashboard.panels,
                "time": dashboard.time_range,
                "timepicker": {
                    "refresh_intervals": ["5s", "10s", "30s", "1m", "5m", "15m", "30m", "1h", "2h", "1d"],
                    "time_options": ["5m", "15m", "1h", "6h", "12h", "24h", "2d", "7d", "30d"]
                },
                "templating": {
                    "list": []
                },
                "annotations": {
                    "list": []
                },
                "refresh": dashboard.refresh_interval,
                "schemaVersion": 27,
                "version": 1,
                "links": []
            },
            "overwrite": True
        }
    
    def save_dashboard_configs(self, output_dir: str):
        """Save all dashboard configurations to files."""
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)
        
        # Save Prometheus config
        prometheus_config = self.generate_prometheus_config()
        with open(output_path / "prometheus.yml", "w") as f:
            import yaml
            yaml.dump(prometheus_config, f, default_flow_style=False)
        
        # Save Grafana dashboards
        dashboards = {
            "overview": self.generate_grafana_overview_dashboard(),
            "performance": self.generate_grafana_performance_dashboard(),
            "errors": self.generate_grafana_errors_dashboard()
        }
        
        for name, dashboard in dashboards.items():
            with open(output_path / f"grafana-{name}-dashboard.json", "w") as f:
                json.dump(dashboard, f, indent=2)
        
        # Save Alertmanager config
        alertmanager_config = self.generate_alertmanager_config([])
        with open(output_path / "alertmanager.yml", "w") as f:
            import yaml
            yaml.dump(alertmanager_config, f, default_flow_style=False)
        
        logger.info("Dashboard configurations saved", 
                   output_dir=output_dir,
                   files_created=["prometheus.yml", "alertmanager.yml"] + 
                               [f"grafana-{name}-dashboard.json" for name in dashboards.keys()])
    
    def generate_docker_compose_monitoring(self) -> Dict[str, Any]:
        """Generate Docker Compose configuration for monitoring stack."""
        return {
            "version": "3.8",
            "services": {
                "prometheus": {
                    "image": "prom/prometheus:latest",
                    "container_name": "thai-tokenizer-prometheus",
                    "ports": ["9090:9090"],
                    "volumes": [
                        "./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml",
                        "./monitoring/thai_tokenizer_alerts.yml:/etc/prometheus/thai_tokenizer_alerts.yml",
                        "prometheus_data:/prometheus"
                    ],
                    "command": [
                        "--config.file=/etc/prometheus/prometheus.yml",
                        "--storage.tsdb.path=/prometheus",
                        "--web.console.libraries=/etc/prometheus/console_libraries",
                        "--web.console.templates=/etc/prometheus/consoles",
                        "--storage.tsdb.retention.time=200h",
                        "--web.enable-lifecycle"
                    ],
                    "networks": ["monitoring"]
                },
                "grafana": {
                    "image": "grafana/grafana:latest",
                    "container_name": "thai-tokenizer-grafana",
                    "ports": ["3000:3000"],
                    "volumes": [
                        "grafana_data:/var/lib/grafana",
                        "./monitoring/grafana/provisioning:/etc/grafana/provisioning",
                        "./monitoring/grafana/dashboards:/var/lib/grafana/dashboards"
                    ],
                    "environment": {
                        "GF_SECURITY_ADMIN_PASSWORD": "admin",
                        "GF_USERS_ALLOW_SIGN_UP": "false"
                    },
                    "networks": ["monitoring"]
                },
                "alertmanager": {
                    "image": "prom/alertmanager:latest",
                    "container_name": "thai-tokenizer-alertmanager",
                    "ports": ["9093:9093"],
                    "volumes": [
                        "./monitoring/alertmanager.yml:/etc/alertmanager/alertmanager.yml",
                        "alertmanager_data:/alertmanager"
                    ],
                    "command": [
                        "--config.file=/etc/alertmanager/alertmanager.yml",
                        "--storage.path=/alertmanager",
                        "--web.external-url=http://localhost:9093"
                    ],
                    "networks": ["monitoring"]
                }
            },
            "volumes": {
                "prometheus_data": {},
                "grafana_data": {},
                "alertmanager_data": {}
            },
            "networks": {
                "monitoring": {
                    "driver": "bridge"
                }
            }
        }
    
    def generate_kubernetes_monitoring_manifests(self) -> Dict[str, str]:
        """Generate Kubernetes manifests for monitoring stack."""
        manifests = {}
        
        # Prometheus ConfigMap
        manifests["prometheus-config.yaml"] = """
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: monitoring
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    rule_files:
      - "thai_tokenizer_alerts.yml"
    
    scrape_configs:
      - job_name: 'thai-tokenizer'
        kubernetes_sd_configs:
          - role: pod
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: thai-tokenizer
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
            action: keep
            regex: true
          - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
            action: replace
            target_label: __metrics_path__
            regex: (.+)
"""
        
        # Prometheus Deployment
        manifests["prometheus-deployment.yaml"] = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: prometheus
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: prometheus
  template:
    metadata:
      labels:
        app: prometheus
    spec:
      containers:
      - name: prometheus
        image: prom/prometheus:latest
        ports:
        - containerPort: 9090
        volumeMounts:
        - name: config-volume
          mountPath: /etc/prometheus
        - name: storage-volume
          mountPath: /prometheus
      volumes:
      - name: config-volume
        configMap:
          name: prometheus-config
      - name: storage-volume
        emptyDir: {}
"""
        
        # Grafana Deployment
        manifests["grafana-deployment.yaml"] = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: grafana
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: grafana
  template:
    metadata:
      labels:
        app: grafana
    spec:
      containers:
      - name: grafana
        image: grafana/grafana:latest
        ports:
        - containerPort: 3000
        env:
        - name: GF_SECURITY_ADMIN_PASSWORD
          value: "admin"
        volumeMounts:
        - name: storage-volume
          mountPath: /var/lib/grafana
      volumes:
      - name: storage-volume
        emptyDir: {}
"""
        
        return manifests