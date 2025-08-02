#!/usr/bin/env python3
"""
Pipeline Integration Utilities for Thai Tokenizer Deployment.

This module provides utilities for integrating Thai Tokenizer deployment
with various CI/CD pipelines including GitHub Actions, GitLab CI, Jenkins,
and Azure DevOps.
"""

import json
import os
import sys
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime


class PipelineIntegration:
    """Pipeline integration utility class."""
    
    def __init__(self, project_root: Optional[str] = None):
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent.parent
        self.templates_dir = self.project_root / "deployment" / "pipeline_templates"
        self.templates_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_github_actions_workflow(
        self, 
        environments: List[str] = None,
        deployment_method: str = "docker",
        include_tests: bool = True
    ) -> str:
        """Generate GitHub Actions workflow for deployment."""
        
        environments = environments or ["development", "staging", "production"]
        
        workflow = {
            "name": "Thai Tokenizer Deployment",
            "on": {
                "push": {
                    "branches": ["main", "develop"]
                },
                "pull_request": {
                    "branches": ["main"]
                },
                "workflow_dispatch": {
                    "inputs": {
                        "environment": {
                            "description": "Target environment",
                            "required": True,
                            "default": "development",
                            "type": "choice",
                            "options": environments
                        },
                        "skip_tests": {
                            "description": "Skip tests",
                            "required": False,
                            "default": False,
                            "type": "boolean"
                        }
                    }
                }
            },
            "env": {
                "PYTHON_VERSION": "3.12",
                "DEPLOYMENT_METHOD": deployment_method
            },
            "jobs": {}
        }
        
        # Test job
        if include_tests:
            workflow["jobs"]["test"] = {
                "runs-on": "ubuntu-latest",
                "steps": [
                    {
                        "name": "Checkout code",
                        "uses": "actions/checkout@v4"
                    },
                    {
                        "name": "Set up Python",
                        "uses": "actions/setup-python@v4",
                        "with": {
                            "python-version": "${{ env.PYTHON_VERSION }}"
                        }
                    },
                    {
                        "name": "Install uv",
                        "run": "pip install uv"
                    },
                    {
                        "name": "Install dependencies",
                        "run": "uv pip install -r requirements.txt"
                    },
                    {
                        "name": "Run tests",
                        "run": "python scripts/run_deployment_tests.py --test-type all --output-dir test_results"
                    },
                    {
                        "name": "Upload test results",
                        "uses": "actions/upload-artifact@v3",
                        "if": "always()",
                        "with": {
                            "name": "test-results",
                            "path": "test_results/"
                        }
                    }
                ]
            }
        
        # Deployment jobs for each environment
        for env in environments:
            job_name = f"deploy-{env}"
            
            job_config = {
                "runs-on": "ubuntu-latest",
                "if": f"github.ref == 'refs/heads/main' || github.event.inputs.environment == '{env}'",
                "environment": env,
                "steps": [
                    {
                        "name": "Checkout code",
                        "uses": "actions/checkout@v4"
                    },
                    {
                        "name": "Set up Python",
                        "uses": "actions/setup-python@v4",
                        "with": {
                            "python-version": "${{ env.PYTHON_VERSION }}"
                        }
                    },
                    {
                        "name": "Install uv",
                        "run": "pip install uv"
                    },
                    {
                        "name": "Install dependencies",
                        "run": "uv pip install -r requirements.txt"
                    }
                ]
            }
            
            # Add Docker setup if needed
            if deployment_method == "docker":
                job_config["steps"].extend([
                    {
                        "name": "Set up Docker Buildx",
                        "uses": "docker/setup-buildx-action@v3"
                    },
                    {
                        "name": "Log in to Docker Hub",
                        "uses": "docker/login-action@v3",
                        "with": {
                            "username": "${{ secrets.DOCKER_USERNAME }}",
                            "password": "${{ secrets.DOCKER_PASSWORD }}"
                        }
                    }
                ])
            
            # Add deployment steps
            job_config["steps"].extend([
                {
                    "name": f"Deploy to {env}",
                    "run": f"python scripts/automation/deploy_automation.py --environment {env} --output-dir deployment_output_{env}",
                    "env": {
                        "MEILISEARCH_HOST": f"${{ secrets.MEILISEARCH_HOST_{env.upper()} }}",
                        "MEILISEARCH_API_KEY": f"${{ secrets.MEILISEARCH_API_KEY_{env.upper()} }}",
                        "SERVICE_PORT": f"${{ vars.SERVICE_PORT_{env.upper()} || '8000' }}"
                    }
                },
                {
                    "name": f"Upload deployment artifacts - {env}",
                    "uses": "actions/upload-artifact@v3",
                    "if": "always()",
                    "with": {
                        "name": f"deployment-artifacts-{env}",
                        "path": f"deployment_output_{env}/"
                    }
                },
                {
                    "name": f"Post-deployment tests - {env}",
                    "run": f"python scripts/thai-tokenizer-deploy test --service-url http://localhost:8000 --test-type all",
                    "if": "success()"
                }
            ])
            
            # Add dependencies
            if include_tests:
                job_config["needs"] = ["test"]
            
            workflow["jobs"][job_name] = job_config
        
        # Convert to YAML
        yaml_content = yaml.dump(workflow, default_flow_style=False, sort_keys=False)
        
        # Save to file
        workflow_file = self.templates_dir / "github-actions.yml"
        with open(workflow_file, 'w') as f:
            f.write(yaml_content)
        
        return str(workflow_file)
    
    def generate_gitlab_ci_pipeline(
        self,
        environments: List[str] = None,
        deployment_method: str = "docker",
        include_tests: bool = True
    ) -> str:
        """Generate GitLab CI pipeline for deployment."""
        
        environments = environments or ["development", "staging", "production"]
        
        pipeline = {
            "stages": ["test", "deploy"],
            "variables": {
                "PYTHON_VERSION": "3.12",
                "DEPLOYMENT_METHOD": deployment_method,
                "PIP_CACHE_DIR": "$CI_PROJECT_DIR/.cache/pip"
            },
            "cache": {
                "paths": [".cache/pip", "venv/"]
            },
            "before_script": [
                "python -V",
                "pip install uv",
                "uv pip install -r requirements.txt"
            ]
        }
        
        # Test stage
        if include_tests:
            pipeline["test"] = {
                "stage": "test",
                "script": [
                    "python scripts/run_deployment_tests.py --test-type all --output-dir test_results"
                ],
                "artifacts": {
                    "when": "always",
                    "paths": ["test_results/"],
                    "reports": {
                        "junit": "test_results/*_results.xml"
                    }
                },
                "only": ["branches"]
            }
        
        # Deployment stages
        for env in environments:
            job_name = f"deploy:{env}"
            
            job_config = {
                "stage": "deploy",
                "script": [
                    f"python scripts/automation/deploy_automation.py --environment {env} --output-dir deployment_output_{env}"
                ],
                "artifacts": {
                    "when": "always",
                    "paths": [f"deployment_output_{env}/"],
                    "expire_in": "1 week"
                },
                "environment": {
                    "name": env,
                    "url": f"http://$SERVICE_HOST_{env.upper()}:$SERVICE_PORT_{env.upper()}"
                }
            }
            
            # Add environment-specific rules
            if env == "development":
                job_config["only"] = ["develop"]
            elif env == "staging":
                job_config["only"] = ["main"]
            elif env == "production":
                job_config["only"] = ["tags"]
                job_config["when"] = "manual"
            
            # Add Docker service if needed
            if deployment_method == "docker":
                job_config["services"] = ["docker:dind"]
                job_config["variables"] = {
                    "DOCKER_HOST": "tcp://docker:2376",
                    "DOCKER_TLS_CERTDIR": "/certs",
                    "DOCKER_TLS_VERIFY": "1",
                    "DOCKER_CERT_PATH": "/certs/client"
                }
            
            pipeline[job_name] = job_config
        
        # Convert to YAML
        yaml_content = yaml.dump(pipeline, default_flow_style=False, sort_keys=False)
        
        # Save to file
        pipeline_file = self.templates_dir / "gitlab-ci.yml"
        with open(pipeline_file, 'w') as f:
            f.write(yaml_content)
        
        return str(pipeline_file)
    
    def generate_jenkins_pipeline(
        self,
        environments: List[str] = None,
        deployment_method: str = "docker",
        include_tests: bool = True
    ) -> str:
        """Generate Jenkins pipeline (Jenkinsfile) for deployment."""
        
        environments = environments or ["development", "staging", "production"]
        
        jenkinsfile_content = f'''pipeline {{
    agent any
    
    environment {{
        PYTHON_VERSION = '3.12'
        DEPLOYMENT_METHOD = '{deployment_method}'
    }}
    
    parameters {{
        choice(
            name: 'ENVIRONMENT',
            choices: {environments},
            description: 'Target environment for deployment'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: 'Skip test execution'
        )
    }}
    
    stages {{
        stage('Checkout') {{
            steps {{
                checkout scm
            }}
        }}
        
        stage('Setup') {{
            steps {{
                sh '''
                    python3 -m venv venv
                    . venv/bin/activate
                    pip install uv
                    uv pip install -r requirements.txt
                '''
            }}
        }}
'''
        
        if include_tests:
            jenkinsfile_content += '''
        stage('Test') {
            when {
                not { params.SKIP_TESTS }
            }
            steps {
                sh '''
                    . venv/bin/activate
                    python scripts/run_deployment_tests.py --test-type all --output-dir test_results
                '''
            }
            post {
                always {
                    archiveArtifacts artifacts: 'test_results/**', allowEmptyArchive: true
                    publishTestResults testResultsPattern: 'test_results/*_results.xml'
                }
            }
        }
'''
        
        jenkinsfile_content += '''
        stage('Deploy') {
            steps {
                script {
                    def environment = params.ENVIRONMENT
                    
                    sh """
                        . venv/bin/activate
                        python scripts/automation/deploy_automation.py \\
                            --environment ${environment} \\
                            --output-dir deployment_output_${environment}
                    """
                }
            }
            post {
                always {
                    archiveArtifacts artifacts: 'deployment_output_*/**', allowEmptyArchive: true
                }
                success {
                    script {
                        def environment = params.ENVIRONMENT
                        
                        sh """
                            . venv/bin/activate
                            python scripts/thai-tokenizer-deploy test \\
                                --service-url http://localhost:8000 \\
                                --test-type health
                        """
                    }
                }
            }
        }
    }
    
    post {
        always {
            cleanWs()
        }
        success {
            emailext (
                subject: "Deployment Success: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Deployment to ${params.ENVIRONMENT} completed successfully.",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
        failure {
            emailext (
                subject: "Deployment Failed: ${env.JOB_NAME} - ${env.BUILD_NUMBER}",
                body: "Deployment to ${params.ENVIRONMENT} failed. Check the build logs for details.",
                to: "${env.CHANGE_AUTHOR_EMAIL}"
            )
        }
    }
}
'''
        
        # Save to file
        jenkinsfile = self.templates_dir / "Jenkinsfile"
        with open(jenkinsfile, 'w') as f:
            f.write(jenkinsfile_content)
        
        return str(jenkinsfile)
    
    def generate_azure_devops_pipeline(
        self,
        environments: List[str] = None,
        deployment_method: str = "docker",
        include_tests: bool = True
    ) -> str:
        """Generate Azure DevOps pipeline for deployment."""
        
        environments = environments or ["development", "staging", "production"]
        
        pipeline = {
            "trigger": {
                "branches": {
                    "include": ["main", "develop"]
                }
            },
            "pr": {
                "branches": {
                    "include": ["main"]
                }
            },
            "variables": {
                "pythonVersion": "3.12",
                "deploymentMethod": deployment_method
            },
            "stages": []
        }
        
        # Test stage
        if include_tests:
            test_stage = {
                "stage": "Test",
                "displayName": "Run Tests",
                "jobs": [{
                    "job": "Test",
                    "displayName": "Test Job",
                    "pool": {
                        "vmImage": "ubuntu-latest"
                    },
                    "steps": [
                        {
                            "task": "UsePythonVersion@0",
                            "inputs": {
                                "versionSpec": "$(pythonVersion)"
                            },
                            "displayName": "Use Python $(pythonVersion)"
                        },
                        {
                            "script": "pip install uv",
                            "displayName": "Install uv"
                        },
                        {
                            "script": "uv pip install -r requirements.txt",
                            "displayName": "Install dependencies"
                        },
                        {
                            "script": "python scripts/run_deployment_tests.py --test-type all --output-dir $(Agent.TempDirectory)/test_results",
                            "displayName": "Run tests"
                        },
                        {
                            "task": "PublishTestResults@2",
                            "condition": "always()",
                            "inputs": {
                                "testResultsFiles": "$(Agent.TempDirectory)/test_results/*_results.xml",
                                "testRunTitle": "Deployment Tests"
                            }
                        },
                        {
                            "task": "PublishBuildArtifacts@1",
                            "condition": "always()",
                            "inputs": {
                                "pathToPublish": "$(Agent.TempDirectory)/test_results",
                                "artifactName": "test-results"
                            }
                        }
                    ]
                }]
            }
            pipeline["stages"].append(test_stage)
        
        # Deployment stages
        for env in environments:
            deploy_stage = {
                "stage": f"Deploy{env.title()}",
                "displayName": f"Deploy to {env.title()}",
                "dependsOn": "Test" if include_tests else [],
                "condition": self._get_azure_condition(env),
                "jobs": [{
                    "deployment": f"Deploy{env.title()}",
                    "displayName": f"Deploy to {env.title()}",
                    "pool": {
                        "vmImage": "ubuntu-latest"
                    },
                    "environment": env,
                    "strategy": {
                        "runOnce": {
                            "deploy": {
                                "steps": [
                                    {
                                        "task": "UsePythonVersion@0",
                                        "inputs": {
                                            "versionSpec": "$(pythonVersion)"
                                        },
                                        "displayName": "Use Python $(pythonVersion)"
                                    },
                                    {
                                        "script": "pip install uv",
                                        "displayName": "Install uv"
                                    },
                                    {
                                        "script": "uv pip install -r requirements.txt",
                                        "displayName": "Install dependencies"
                                    },
                                    {
                                        "script": f"python scripts/automation/deploy_automation.py --environment {env} --output-dir $(Agent.TempDirectory)/deployment_output_{env}",
                                        "displayName": f"Deploy to {env}",
                                        "env": {
                                            f"MEILISEARCH_HOST": f"$(MEILISEARCH_HOST_{env.upper()})",
                                            f"MEILISEARCH_API_KEY": f"$(MEILISEARCH_API_KEY_{env.upper()})",
                                            f"SERVICE_PORT": f"$(SERVICE_PORT_{env.upper()})"
                                        }
                                    },
                                    {
                                        "task": "PublishBuildArtifacts@1",
                                        "condition": "always()",
                                        "inputs": {
                                            "pathToPublish": f"$(Agent.TempDirectory)/deployment_output_{env}",
                                            "artifactName": f"deployment-artifacts-{env}"
                                        }
                                    },
                                    {
                                        "script": "python scripts/thai-tokenizer-deploy test --service-url http://localhost:8000 --test-type health",
                                        "displayName": "Post-deployment health check",
                                        "condition": "succeeded()"
                                    }
                                ]
                            }
                        }
                    }
                }]
            }
            
            pipeline["stages"].append(deploy_stage)
        
        # Convert to YAML
        yaml_content = yaml.dump(pipeline, default_flow_style=False, sort_keys=False)
        
        # Save to file
        pipeline_file = self.templates_dir / "azure-pipelines.yml"
        with open(pipeline_file, 'w') as f:
            f.write(yaml_content)
        
        return str(pipeline_file)
    
    def _get_azure_condition(self, environment: str) -> str:
        """Get Azure DevOps condition for environment deployment."""
        if environment == "development":
            return "and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/develop'))"
        elif environment == "staging":
            return "and(succeeded(), eq(variables['Build.SourceBranch'], 'refs/heads/main'))"
        elif environment == "production":
            return "and(succeeded(), startsWith(variables['Build.SourceBranch'], 'refs/tags/'))"
        else:
            return "succeeded()"
    
    def generate_docker_compose_override(
        self,
        environment: str = "development",
        custom_settings: Dict[str, Any] = None
    ) -> str:
        """Generate Docker Compose override file for specific environment."""
        
        custom_settings = custom_settings or {}
        
        # Base override configuration
        override_config = {
            "version": "3.8",
            "services": {
                "thai-tokenizer": {
                    "environment": [
                        f"ENVIRONMENT={environment}",
                        f"LOG_LEVEL={'DEBUG' if environment == 'development' else 'INFO'}",
                        "PYTHONPATH=src"
                    ],
                    "labels": [
                        f"environment={environment}",
                        f"service=thai-tokenizer",
                        f"version=${BUILD_VERSION:-latest}"
                    ]
                }
            }
        }
        
        # Environment-specific overrides
        if environment == "development":
            override_config["services"]["thai-tokenizer"].update({
                "ports": ["8000:8000", "9000:9000"],
                "volumes": [
                    "./src:/app/src:ro",
                    "./data:/app/data",
                    "./logs:/app/logs"
                ],
                "command": ["uvicorn", "src.api.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
            })
        
        elif environment == "production":
            override_config["services"]["thai-tokenizer"].update({
                "restart": "unless-stopped",
                "deploy": {
                    "resources": {
                        "limits": {
                            "memory": "512M",
                            "cpus": "1.0"
                        },
                        "reservations": {
                            "memory": "256M",
                            "cpus": "0.5"
                        }
                    }
                },
                "healthcheck": {
                    "test": ["CMD", "curl", "-f", "http://localhost:8000/health"],
                    "interval": "30s",
                    "timeout": "10s",
                    "retries": 3,
                    "start_period": "40s"
                }
            })
        
        # Apply custom settings
        if custom_settings:
            self._deep_update(override_config, custom_settings)
        
        # Convert to YAML
        yaml_content = yaml.dump(override_config, default_flow_style=False, sort_keys=False)
        
        # Save to file
        override_file = self.templates_dir / f"docker-compose.{environment}.yml"
        with open(override_file, 'w') as f:
            f.write(yaml_content)
        
        return str(override_file)
    
    def _deep_update(self, base_dict: Dict, update_dict: Dict) -> None:
        """Deep update dictionary."""
        for key, value in update_dict.items():
            if key in base_dict and isinstance(base_dict[key], dict) and isinstance(value, dict):
                self._deep_update(base_dict[key], value)
            else:
                base_dict[key] = value
    
    def generate_deployment_scripts(self) -> Dict[str, str]:
        """Generate deployment scripts for different scenarios."""
        scripts = {}
        
        # Quick deployment script
        quick_deploy_script = '''#!/bin/bash
set -e

# Quick deployment script for Thai Tokenizer
echo "🚀 Starting Thai Tokenizer quick deployment..."

# Default values
ENVIRONMENT=${ENVIRONMENT:-development}
DEPLOYMENT_METHOD=${DEPLOYMENT_METHOD:-docker}
CONFIG_FILE=${CONFIG_FILE:-""}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--environment)
            ENVIRONMENT="$2"
            shift 2
            ;;
        -m|--method)
            DEPLOYMENT_METHOD="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -e, --environment    Target environment (default: development)"
            echo "  -m, --method         Deployment method (default: docker)"
            echo "  -c, --config         Configuration file path"
            echo "  -h, --help           Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "Environment: $ENVIRONMENT"
echo "Method: $DEPLOYMENT_METHOD"

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is required but not installed"
    exit 1
fi

if ! command -v uv &> /dev/null; then
    echo "Installing uv package manager..."
    pip install uv
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv pip install -r requirements.txt

# Run deployment
echo "🚀 Running deployment..."
if [ -n "$CONFIG_FILE" ]; then
    python scripts/automation/deploy_automation.py \\
        --config "$CONFIG_FILE" \\
        --environment "$ENVIRONMENT"
else
    python scripts/automation/deploy_automation.py \\
        --environment "$ENVIRONMENT"
fi

echo "✅ Deployment completed!"
'''
        
        scripts["quick_deploy.sh"] = quick_deploy_script
        
        # Rollback script
        rollback_script = '''#!/bin/bash
set -e

# Rollback script for Thai Tokenizer deployment
echo "🔄 Starting Thai Tokenizer deployment rollback..."

DEPLOYMENT_ID=${1:-""}
ENVIRONMENT=${2:-"development"}

if [ -z "$DEPLOYMENT_ID" ]; then
    echo "Usage: $0 <deployment_id> [environment]"
    echo "Example: $0 deploy-123456 production"
    exit 1
fi

echo "Rolling back deployment: $DEPLOYMENT_ID"
echo "Environment: $ENVIRONMENT"

# Find deployment artifacts
DEPLOYMENT_DIR="deployment_output_${ENVIRONMENT}"
if [ ! -d "$DEPLOYMENT_DIR" ]; then
    echo "❌ Deployment directory not found: $DEPLOYMENT_DIR"
    exit 1
fi

# Stop current service
echo "🛑 Stopping current service..."
python scripts/thai-tokenizer-deploy stop --deployment-id "$DEPLOYMENT_ID"

# Restore previous configuration
echo "🔧 Restoring previous configuration..."
if [ -f "${DEPLOYMENT_DIR}/backup_config.json" ]; then
    cp "${DEPLOYMENT_DIR}/backup_config.json" "${DEPLOYMENT_DIR}/config.json"
    echo "Configuration restored from backup"
else
    echo "⚠️  No backup configuration found"
fi

# Restart with previous configuration
echo "🚀 Restarting service with previous configuration..."
python scripts/thai-tokenizer-deploy deploy \\
    --config "${DEPLOYMENT_DIR}/config.json" \\
    --method docker

echo "✅ Rollback completed!"
'''
        
        scripts["rollback.sh"] = rollback_script
        
        # Health check script
        health_check_script = '''#!/bin/bash
set -e

# Health check script for Thai Tokenizer
SERVICE_URL=${1:-"http://localhost:8000"}
TIMEOUT=${2:-30}

echo "🏥 Checking Thai Tokenizer health at: $SERVICE_URL"

# Function to check endpoint
check_endpoint() {
    local endpoint=$1
    local expected_status=${2:-200}
    
    echo -n "Checking $endpoint... "
    
    if response=$(curl -s -w "%{http_code}" -m $TIMEOUT "$SERVICE_URL$endpoint" -o /tmp/response.json); then
        status_code="${response: -3}"
        if [ "$status_code" = "$expected_status" ]; then
            echo "✅ OK ($status_code)"
            return 0
        else
            echo "❌ FAILED ($status_code)"
            return 1
        fi
    else
        echo "❌ FAILED (connection error)"
        return 1
    fi
}

# Check health endpoints
check_endpoint "/health" 200
check_endpoint "/health/detailed" 200

# Check tokenization endpoint
echo -n "Testing tokenization... "
if curl -s -X POST \\
    -H "Content-Type: application/json" \\
    -d '{"text":"สวัสดีครับ"}' \\
    -m $TIMEOUT \\
    "$SERVICE_URL/v1/tokenize" \\
    -o /tmp/tokenize_response.json; then
    
    if jq -e '.tokens | length > 0' /tmp/tokenize_response.json > /dev/null 2>&1; then
        echo "✅ OK"
    else
        echo "❌ FAILED (no tokens returned)"
        exit 1
    fi
else
    echo "❌ FAILED (connection error)"
    exit 1
fi

echo "🎉 All health checks passed!"
'''
        
        scripts["health_check.sh"] = health_check_script
        
        # Save all scripts
        scripts_dir = self.templates_dir / "scripts"
        scripts_dir.mkdir(exist_ok=True)
        
        saved_scripts = {}
        for script_name, script_content in scripts.items():
            script_path = scripts_dir / script_name
            with open(script_path, 'w') as f:
                f.write(script_content)
            
            # Make executable
            os.chmod(script_path, 0o755)
            saved_scripts[script_name] = str(script_path)
        
        return saved_scripts
    
    def generate_all_templates(
        self,
        environments: List[str] = None,
        deployment_method: str = "docker",
        include_tests: bool = True
    ) -> Dict[str, str]:
        """Generate all pipeline templates and scripts."""
        
        generated_files = {}
        
        # Generate pipeline templates
        generated_files["github_actions"] = self.generate_github_actions_workflow(
            environments, deployment_method, include_tests
        )
        
        generated_files["gitlab_ci"] = self.generate_gitlab_ci_pipeline(
            environments, deployment_method, include_tests
        )
        
        generated_files["jenkins"] = self.generate_jenkins_pipeline(
            environments, deployment_method, include_tests
        )
        
        generated_files["azure_devops"] = self.generate_azure_devops_pipeline(
            environments, deployment_method, include_tests
        )
        
        # Generate Docker Compose overrides
        environments = environments or ["development", "staging", "production"]
        for env in environments:
            generated_files[f"docker_compose_{env}"] = self.generate_docker_compose_override(env)
        
        # Generate deployment scripts
        scripts = self.generate_deployment_scripts()
        generated_files.update(scripts)
        
        return generated_files


def main():
    """Main pipeline integration entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Pipeline Integration Utilities")
    parser.add_argument("--pipeline", choices=["github", "gitlab", "jenkins", "azure", "all"], 
                       default="all", help="Pipeline type to generate")
    parser.add_argument("--environments", nargs="+", default=["development", "staging", "production"],
                       help="Target environments")
    parser.add_argument("--deployment-method", default="docker", help="Deployment method")
    parser.add_argument("--no-tests", action="store_true", help="Exclude test stages")
    parser.add_argument("--output-dir", help="Output directory for templates")
    
    args = parser.parse_args()
    
    # Create pipeline integration instance
    integration = PipelineIntegration(args.output_dir)
    
    include_tests = not args.no_tests
    
    try:
        if args.pipeline == "all":
            generated_files = integration.generate_all_templates(
                args.environments, args.deployment_method, include_tests
            )
            
            print("✅ Generated all pipeline templates:")
            for template_type, file_path in generated_files.items():
                print(f"  📄 {template_type}: {file_path}")
        
        else:
            # Generate specific pipeline
            if args.pipeline == "github":
                file_path = integration.generate_github_actions_workflow(
                    args.environments, args.deployment_method, include_tests
                )
            elif args.pipeline == "gitlab":
                file_path = integration.generate_gitlab_ci_pipeline(
                    args.environments, args.deployment_method, include_tests
                )
            elif args.pipeline == "jenkins":
                file_path = integration.generate_jenkins_pipeline(
                    args.environments, args.deployment_method, include_tests
                )
            elif args.pipeline == "azure":
                file_path = integration.generate_azure_devops_pipeline(
                    args.environments, args.deployment_method, include_tests
                )
            
            print(f"✅ Generated {args.pipeline} pipeline: {file_path}")
        
        return 0
        
    except Exception as e:
        print(f"❌ Pipeline generation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())