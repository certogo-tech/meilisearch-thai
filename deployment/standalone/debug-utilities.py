#!/usr/bin/env python3
"""
Development and debugging utilities for standalone Thai Tokenizer deployment.

This script provides comprehensive debugging, development, and troubleshooting
utilities for the Thai Tokenizer service in standalone deployment mode.
"""

import os
import sys
import json
import time
import psutil
import argparse
import logging
import requests
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import traceback

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

try:
    from utils.logging import get_structured_logger
    from utils.health import HealthChecker
except ImportError:
    # Fallback logging if imports fail
    logging.basicConfig(level=logging.INFO)
    def get_structured_logger(name):
        return logging.getLogger(name)

logger = get_structured_logger(__name__)


class StandaloneDebugUtilities:
    """Development and debugging utilities for standalone deployment."""
    
    def __init__(self, install_path: str):
        """
        Initialize debug utilities.
        
        Args:
            install_path: Installation directory path
        """
        self.install_path = Path(install_path)
        self.config_file = self.install_path / "config" / "config.json"
        self.env_file = self.install_path / "config" / ".env"
        self.log_file = self.install_path / "logs" / "thai-tokenizer.log"
        self.venv_path = self.install_path / "venv"
        self.logger = get_structured_logger(f"{__name__}.StandaloneDebugUtilities")
    
    def get_venv_python(self) -> Path:
        """Get path to Python executable in virtual environment."""
        if os.name == 'nt':  # Windows
            return self.venv_path / "Scripts" / "python.exe"
        else:  # Unix-like
            return self.venv_path / "bin" / "python"
    
    def load_config(self) -> Optional[Dict[str, Any]]:
        """Load service configuration."""
        try:
            if not self.config_file.exists():
                return None
            
            with open(self.config_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            return None
    
    def validate_installation(self) -> Dict[str, Any]:
        """
        Validate the standalone installation.
        
        Returns:
            Validation results dictionary
        """
        results = {
            "overall_status": "unknown",
            "checks": {},
            "errors": [],
            "warnings": [],
            "recommendations": []
        }
        
        try:
            # Check installation directory
            if not self.install_path.exists():
                results["checks"]["install_path"] = {
                    "status": "failed",
                    "message": f"Installation path does not exist: {self.install_path}"
                }
                results["errors"].append("Installation path missing")
            else:
                results["checks"]["install_path"] = {
                    "status": "passed",
                    "message": f"Installation path exists: {self.install_path}"
                }
            
            # Check virtual environment
            venv_python = self.get_venv_python()
            if not venv_python.exists():
                results["checks"]["virtual_environment"] = {
                    "status": "failed",
                    "message": f"Virtual environment Python not found: {venv_python}"
                }
                results["errors"].append("Virtual environment missing")
            else:
                results["checks"]["virtual_environment"] = {
                    "status": "passed",
                    "message": f"Virtual environment found: {venv_python}"
                }
            
            # Check configuration files
            if not self.config_file.exists():
                results["checks"]["configuration"] = {
                    "status": "failed",
                    "message": f"Configuration file not found: {self.config_file}"
                }
                results["errors"].append("Configuration file missing")
            else:
                config = self.load_config()
                if config:
                    results["checks"]["configuration"] = {
                        "status": "passed",
                        "message": "Configuration file loaded successfully",
                        "details": {
                            "meilisearch_host": config.get("meilisearch_config", {}).get("host", "not configured"),
                            "service_port": config.get("service_config", {}).get("service_port", "not configured")
                        }
                    }
                else:
                    results["checks"]["configuration"] = {
                        "status": "failed",
                        "message": "Configuration file exists but cannot be loaded"
                    }
                    results["errors"].append("Configuration file invalid")
            
            # Check required directories
            required_dirs = ["config", "logs", "run", "bin"]
            for dir_name in required_dirs:
                dir_path = self.install_path / dir_name
                if not dir_path.exists():
                    results["checks"][f"directory_{dir_name}"] = {
                        "status": "warning",
                        "message": f"Directory missing: {dir_path}"
                    }
                    results["warnings"].append(f"Missing directory: {dir_name}")
                else:
                    results["checks"][f"directory_{dir_name}"] = {
                        "status": "passed",
                        "message": f"Directory exists: {dir_path}"
                    }
            
            # Check service scripts
            start_script = self.install_path / "bin" / "start-service.sh"
            if os.name == 'nt':
                start_script = start_script.with_suffix('.bat')
            
            if not start_script.exists():
                results["checks"]["service_scripts"] = {
                    "status": "warning",
                    "message": f"Start script not found: {start_script}"
                }
                results["warnings"].append("Service scripts missing")
            else:
                results["checks"]["service_scripts"] = {
                    "status": "passed",
                    "message": f"Start script found: {start_script}"
                }
            
            # Determine overall status
            if results["errors"]:
                results["overall_status"] = "failed"
            elif results["warnings"]:
                results["overall_status"] = "warning"
            else:
                results["overall_status"] = "passed"
            
            # Add recommendations
            if results["errors"]:
                results["recommendations"].append("Run setup script to fix installation issues")
            if results["warnings"]:
                results["recommendations"].append("Review warnings and create missing directories/files")
            
        except Exception as e:
            results["overall_status"] = "error"
            results["errors"].append(f"Validation error: {e}")
        
        return results
    
    def test_dependencies(self) -> Dict[str, Any]:
        """
        Test Python dependencies in virtual environment.
        
        Returns:
            Dependency test results
        """
        results = {
            "status": "unknown",
            "dependencies": {},
            "errors": [],
            "python_info": {}
        }
        
        try:
            venv_python = self.get_venv_python()
            
            if not venv_python.exists():
                results["status"] = "failed"
                results["errors"].append("Virtual environment Python not found")
                return results
            
            # Get Python version info
            try:
                python_version_result = subprocess.run(
                    [str(venv_python), "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                results["python_info"]["version"] = python_version_result.stdout.strip()
            except Exception as e:
                results["python_info"]["version"] = f"Error: {e}"
            
            # Test key dependencies
            key_dependencies = [
                "fastapi",
                "uvicorn",
                "pythainlp",
                "meilisearch",
                "pydantic",
                "requests",
                "psutil"
            ]
            
            for dep in key_dependencies:
                try:
                    import_result = subprocess.run(
                        [str(venv_python), "-c", f"import {dep}; print({dep}.__version__ if hasattr({dep}, '__version__') else 'imported')"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    
                    if import_result.returncode == 0:
                        results["dependencies"][dep] = {
                            "status": "available",
                            "version": import_result.stdout.strip()
                        }
                    else:
                        results["dependencies"][dep] = {
                            "status": "failed",
                            "error": import_result.stderr.strip()
                        }
                        results["errors"].append(f"Dependency {dep} failed to import")
                
                except Exception as e:
                    results["dependencies"][dep] = {
                        "status": "error",
                        "error": str(e)
                    }
                    results["errors"].append(f"Error testing dependency {dep}: {e}")
            
            # Determine overall status
            failed_deps = [dep for dep, info in results["dependencies"].items() 
                          if info["status"] != "available"]
            
            if not failed_deps:
                results["status"] = "passed"
            elif len(failed_deps) < len(key_dependencies) / 2:
                results["status"] = "warning"
            else:
                results["status"] = "failed"
        
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Dependency test error: {e}")
        
        return results
    
    def test_meilisearch_connection(self) -> Dict[str, Any]:
        """
        Test connection to Meilisearch server.
        
        Returns:
            Connection test results
        """
        results = {
            "status": "unknown",
            "connection_info": {},
            "health_check": {},
            "errors": [],
            "response_times": {}
        }
        
        try:
            config = self.load_config()
            if not config:
                results["status"] = "failed"
                results["errors"].append("Cannot load configuration")
                return results
            
            meilisearch_config = config.get("meilisearch_config", {})
            host = meilisearch_config.get("host", "localhost")
            port = meilisearch_config.get("port", 7700)
            api_key = meilisearch_config.get("api_key", "")
            ssl_enabled = meilisearch_config.get("ssl_enabled", False)
            
            protocol = "https" if ssl_enabled else "http"
            base_url = f"{protocol}://{host}:{port}"
            
            results["connection_info"] = {
                "host": host,
                "port": port,
                "ssl_enabled": ssl_enabled,
                "base_url": base_url,
                "api_key_configured": bool(api_key)
            }
            
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Test basic connectivity
            try:
                start_time = time.time()
                response = requests.get(f"{base_url}/health", headers=headers, timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                results["response_times"]["health"] = response_time
                results["health_check"] = {
                    "status_code": response.status_code,
                    "response_time_ms": response_time,
                    "accessible": response.status_code == 200
                }
                
                if response.status_code == 200:
                    try:
                        health_data = response.json()
                        results["health_check"]["data"] = health_data
                    except:
                        results["health_check"]["data"] = response.text
                
            except requests.RequestException as e:
                results["health_check"] = {
                    "accessible": False,
                    "error": str(e)
                }
                results["errors"].append(f"Health check failed: {e}")
            
            # Test version endpoint
            try:
                start_time = time.time()
                response = requests.get(f"{base_url}/version", headers=headers, timeout=10)
                response_time = (time.time() - start_time) * 1000
                
                results["response_times"]["version"] = response_time
                
                if response.status_code == 200:
                    try:
                        version_data = response.json()
                        results["connection_info"]["meilisearch_version"] = version_data
                    except:
                        pass
                
            except requests.RequestException as e:
                results["errors"].append(f"Version check failed: {e}")
            
            # Test indexes endpoint (requires API key)
            if api_key:
                try:
                    start_time = time.time()
                    response = requests.get(f"{base_url}/indexes", headers=headers, timeout=10)
                    response_time = (time.time() - start_time) * 1000
                    
                    results["response_times"]["indexes"] = response_time
                    
                    if response.status_code == 200:
                        try:
                            indexes_data = response.json()
                            results["connection_info"]["indexes_count"] = len(indexes_data.get("results", []))
                        except:
                            pass
                    elif response.status_code == 403:
                        results["errors"].append("API key authentication failed")
                
                except requests.RequestException as e:
                    results["errors"].append(f"Indexes check failed: {e}")
            
            # Determine overall status
            if results["health_check"].get("accessible", False):
                if results["errors"]:
                    results["status"] = "warning"
                else:
                    results["status"] = "passed"
            else:
                results["status"] = "failed"
        
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Connection test error: {e}")
        
        return results
    
    def test_thai_tokenization(self) -> Dict[str, Any]:
        """
        Test Thai tokenization functionality.
        
        Returns:
            Tokenization test results
        """
        results = {
            "status": "unknown",
            "tests": {},
            "errors": [],
            "performance": {}
        }
        
        try:
            venv_python = self.get_venv_python()
            
            if not venv_python.exists():
                results["status"] = "failed"
                results["errors"].append("Virtual environment Python not found")
                return results
            
            # Test cases
            test_cases = [
                {
                    "name": "simple_thai",
                    "text": "สวัสดีครับ",
                    "description": "Simple Thai greeting"
                },
                {
                    "name": "compound_words",
                    "text": "โรงเรียนมหาวิทยาลัย",
                    "description": "Thai compound words"
                },
                {
                    "name": "mixed_content",
                    "text": "Hello สวัสดี World โลก",
                    "description": "Mixed Thai-English content"
                },
                {
                    "name": "formal_text",
                    "text": "การประชุมคณะรัฐมนตรีจะจัดขึ้นในวันพรุ่งนี้",
                    "description": "Formal Thai text"
                }
            ]
            
            for test_case in test_cases:
                test_name = test_case["name"]
                text = test_case["text"]
                
                try:
                    # Test PyThaiNLP tokenization
                    start_time = time.time()
                    
                    tokenization_script = f"""
import sys
sys.path.insert(0, '{self.install_path.parent.parent / "src"}')

try:
    from tokenizer.thai_segmenter import ThaiSegmenter
    
    segmenter = ThaiSegmenter()
    result = segmenter.segment_text('{text}')
    
    print("SUCCESS")
    print(f"Tokens: {{result['tokens']}}")
    print(f"Count: {{len(result['tokens'])}}")
    
except Exception as e:
    print("ERROR")
    print(f"Error: {{str(e)}}")
    import traceback
    traceback.print_exc()
"""
                    
                    tokenization_result = subprocess.run(
                        [str(venv_python), "-c", tokenization_script],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    
                    processing_time = (time.time() - start_time) * 1000
                    
                    if tokenization_result.returncode == 0 and "SUCCESS" in tokenization_result.stdout:
                        output_lines = tokenization_result.stdout.strip().split('\n')
                        tokens_line = next((line for line in output_lines if line.startswith("Tokens:")), "")
                        count_line = next((line for line in output_lines if line.startswith("Count:")), "")
                        
                        results["tests"][test_name] = {
                            "status": "passed",
                            "text": text,
                            "description": test_case["description"],
                            "processing_time_ms": processing_time,
                            "tokens": tokens_line.replace("Tokens: ", "") if tokens_line else "unknown",
                            "token_count": count_line.replace("Count: ", "") if count_line else "unknown"
                        }
                    else:
                        error_output = tokenization_result.stderr or tokenization_result.stdout
                        results["tests"][test_name] = {
                            "status": "failed",
                            "text": text,
                            "description": test_case["description"],
                            "processing_time_ms": processing_time,
                            "error": error_output
                        }
                        results["errors"].append(f"Tokenization test {test_name} failed")
                
                except Exception as e:
                    results["tests"][test_name] = {
                        "status": "error",
                        "text": text,
                        "description": test_case["description"],
                        "error": str(e)
                    }
                    results["errors"].append(f"Error in tokenization test {test_name}: {e}")
            
            # Calculate performance metrics
            successful_tests = [test for test in results["tests"].values() if test["status"] == "passed"]
            if successful_tests:
                processing_times = [test["processing_time_ms"] for test in successful_tests]
                results["performance"] = {
                    "average_processing_time_ms": sum(processing_times) / len(processing_times),
                    "max_processing_time_ms": max(processing_times),
                    "min_processing_time_ms": min(processing_times),
                    "successful_tests": len(successful_tests),
                    "total_tests": len(results["tests"])
                }
            
            # Determine overall status
            failed_tests = [test for test in results["tests"].values() if test["status"] != "passed"]
            if not failed_tests:
                results["status"] = "passed"
            elif len(failed_tests) < len(results["tests"]):
                results["status"] = "warning"
            else:
                results["status"] = "failed"
        
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Thai tokenization test error: {e}")
        
        return results
    
    def analyze_logs(self, lines: int = 100) -> Dict[str, Any]:
        """
        Analyze service logs for issues and patterns.
        
        Args:
            lines: Number of log lines to analyze
            
        Returns:
            Log analysis results
        """
        results = {
            "status": "unknown",
            "log_file": str(self.log_file),
            "analysis": {},
            "errors": [],
            "warnings": [],
            "patterns": {}
        }
        
        try:
            if not self.log_file.exists():
                results["status"] = "warning"
                results["warnings"].append("Log file not found")
                return results
            
            # Read log lines
            with open(self.log_file, 'r') as f:
                all_lines = f.readlines()
            
            recent_lines = all_lines[-lines:] if len(all_lines) > lines else all_lines
            
            results["analysis"] = {
                "total_lines": len(all_lines),
                "analyzed_lines": len(recent_lines),
                "file_size_bytes": self.log_file.stat().st_size
            }
            
            # Analyze patterns
            error_patterns = []
            warning_patterns = []
            info_patterns = []
            
            for line in recent_lines:
                line_lower = line.lower()
                
                if "error" in line_lower or "exception" in line_lower:
                    error_patterns.append(line.strip())
                elif "warning" in line_lower or "warn" in line_lower:
                    warning_patterns.append(line.strip())
                elif "info" in line_lower:
                    info_patterns.append(line.strip())
            
            results["patterns"] = {
                "errors": error_patterns[-10:],  # Last 10 errors
                "warnings": warning_patterns[-10:],  # Last 10 warnings
                "info": len(info_patterns)
            }
            
            # Check for specific issues
            if error_patterns:
                results["errors"].extend([f"Found {len(error_patterns)} error entries in logs"])
            
            if warning_patterns:
                results["warnings"].extend([f"Found {len(warning_patterns)} warning entries in logs"])
            
            # Determine status
            if error_patterns:
                results["status"] = "failed"
            elif warning_patterns:
                results["status"] = "warning"
            else:
                results["status"] = "passed"
        
        except Exception as e:
            results["status"] = "error"
            results["errors"].append(f"Log analysis error: {e}")
        
        return results
    
    def run_comprehensive_diagnostics(self) -> Dict[str, Any]:
        """
        Run comprehensive diagnostics on the standalone deployment.
        
        Returns:
            Complete diagnostic results
        """
        diagnostics = {
            "timestamp": datetime.now().isoformat(),
            "install_path": str(self.install_path),
            "overall_status": "unknown",
            "tests": {},
            "summary": {
                "passed": 0,
                "warning": 0,
                "failed": 0,
                "error": 0
            },
            "recommendations": []
        }
        
        try:
            self.logger.info("Running comprehensive diagnostics...")
            
            # Run all diagnostic tests
            test_functions = [
                ("installation", self.validate_installation),
                ("dependencies", self.test_dependencies),
                ("meilisearch_connection", self.test_meilisearch_connection),
                ("thai_tokenization", self.test_thai_tokenization),
                ("log_analysis", lambda: self.analyze_logs(100))
            ]
            
            for test_name, test_function in test_functions:
                try:
                    self.logger.info(f"Running {test_name} test...")
                    test_result = test_function()
                    diagnostics["tests"][test_name] = test_result
                    
                    # Update summary
                    status = test_result.get("status", "unknown")
                    if status in diagnostics["summary"]:
                        diagnostics["summary"][status] += 1
                    
                except Exception as e:
                    self.logger.error(f"Error in {test_name} test: {e}")
                    diagnostics["tests"][test_name] = {
                        "status": "error",
                        "error": str(e),
                        "traceback": traceback.format_exc()
                    }
                    diagnostics["summary"]["error"] += 1
            
            # Determine overall status
            if diagnostics["summary"]["error"] > 0 or diagnostics["summary"]["failed"] > 0:
                diagnostics["overall_status"] = "failed"
            elif diagnostics["summary"]["warning"] > 0:
                diagnostics["overall_status"] = "warning"
            else:
                diagnostics["overall_status"] = "passed"
            
            # Generate recommendations
            if diagnostics["tests"].get("installation", {}).get("status") == "failed":
                diagnostics["recommendations"].append("Run setup script to fix installation issues")
            
            if diagnostics["tests"].get("dependencies", {}).get("status") != "passed":
                diagnostics["recommendations"].append("Reinstall dependencies using install-dependencies.py")
            
            if diagnostics["tests"].get("meilisearch_connection", {}).get("status") == "failed":
                diagnostics["recommendations"].append("Check Meilisearch server configuration and connectivity")
            
            if diagnostics["tests"].get("thai_tokenization", {}).get("status") != "passed":
                diagnostics["recommendations"].append("Check PyThaiNLP installation and Thai language models")
            
            if diagnostics["tests"].get("log_analysis", {}).get("status") == "failed":
                diagnostics["recommendations"].append("Review service logs for error details")
            
            self.logger.info(f"Diagnostics completed. Overall status: {diagnostics['overall_status']}")
            
        except Exception as e:
            diagnostics["overall_status"] = "error"
            diagnostics["error"] = str(e)
            diagnostics["traceback"] = traceback.format_exc()
        
        return diagnostics
    
    def interactive_debug_session(self) -> None:
        """Run an interactive debugging session."""
        print("=== Thai Tokenizer Standalone Debug Session ===")
        print(f"Installation Path: {self.install_path}")
        print()
        
        while True:
            print("Available commands:")
            print("  1. Run comprehensive diagnostics")
            print("  2. Test Meilisearch connection")
            print("  3. Test Thai tokenization")
            print("  4. Analyze logs")
            print("  5. Validate installation")
            print("  6. Test dependencies")
            print("  7. Show configuration")
            print("  8. Exit")
            print()
            
            try:
                choice = input("Enter command number: ").strip()
                
                if choice == "1":
                    print("\nRunning comprehensive diagnostics...")
                    results = self.run_comprehensive_diagnostics()
                    print(json.dumps(results, indent=2, default=str))
                
                elif choice == "2":
                    print("\nTesting Meilisearch connection...")
                    results = self.test_meilisearch_connection()
                    print(json.dumps(results, indent=2, default=str))
                
                elif choice == "3":
                    print("\nTesting Thai tokenization...")
                    results = self.test_thai_tokenization()
                    print(json.dumps(results, indent=2, default=str))
                
                elif choice == "4":
                    lines = input("Number of log lines to analyze (default 100): ").strip()
                    lines = int(lines) if lines.isdigit() else 100
                    print(f"\nAnalyzing last {lines} log lines...")
                    results = self.analyze_logs(lines)
                    print(json.dumps(results, indent=2, default=str))
                
                elif choice == "5":
                    print("\nValidating installation...")
                    results = self.validate_installation()
                    print(json.dumps(results, indent=2, default=str))
                
                elif choice == "6":
                    print("\nTesting dependencies...")
                    results = self.test_dependencies()
                    print(json.dumps(results, indent=2, default=str))
                
                elif choice == "7":
                    print("\nCurrent configuration:")
                    config = self.load_config()
                    if config:
                        print(json.dumps(config, indent=2, default=str))
                    else:
                        print("Configuration not found or invalid")
                
                elif choice == "8":
                    print("Exiting debug session...")
                    break
                
                else:
                    print("Invalid choice. Please enter a number 1-8.")
                
                print("\n" + "="*50 + "\n")
                
            except KeyboardInterrupt:
                print("\nExiting debug session...")
                break
            except Exception as e:
                print(f"Error: {e}")


def main():
    """Main entry point for debug utilities."""
    parser = argparse.ArgumentParser(
        description="Development and debugging utilities for Thai Tokenizer standalone deployment"
    )
    
    parser.add_argument(
        "--install-path",
        required=True,
        help="Installation directory path"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Diagnostics command
    diag_parser = subparsers.add_parser("diagnostics", help="Run comprehensive diagnostics")
    diag_parser.add_argument("--json", action="store_true", help="Output as JSON")
    
    # Test commands
    test_parser = subparsers.add_parser("test", help="Run specific tests")
    test_subparsers = test_parser.add_subparsers(dest="test_type", help="Test types")
    
    test_subparsers.add_parser("installation", help="Test installation")
    test_subparsers.add_parser("dependencies", help="Test dependencies")
    test_subparsers.add_parser("meilisearch", help="Test Meilisearch connection")
    test_subparsers.add_parser("tokenization", help="Test Thai tokenization")
    
    # Log analysis command
    log_parser = subparsers.add_parser("logs", help="Analyze logs")
    log_parser.add_argument("--lines", type=int, default=100, help="Number of lines to analyze")
    
    # Interactive command
    interactive_parser = subparsers.add_parser("interactive", help="Start interactive debug session")
    
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Configure logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        # Create debug utilities
        debug_utils = StandaloneDebugUtilities(args.install_path)
        
        # Execute command
        if args.command == "diagnostics":
            results = debug_utils.run_comprehensive_diagnostics()
            
            if args.json:
                print(json.dumps(results, indent=2, default=str))
            else:
                print(f"=== Diagnostic Results ===")
                print(f"Overall Status: {results['overall_status']}")
                print(f"Install Path: {results['install_path']}")
                print(f"Timestamp: {results['timestamp']}")
                print()
                
                for test_name, test_result in results["tests"].items():
                    status = test_result.get("status", "unknown")
                    print(f"{test_name}: {status}")
                    
                    if test_result.get("errors"):
                        for error in test_result["errors"]:
                            print(f"  ERROR: {error}")
                    
                    if test_result.get("warnings"):
                        for warning in test_result["warnings"]:
                            print(f"  WARNING: {warning}")
                
                if results.get("recommendations"):
                    print("\nRecommendations:")
                    for rec in results["recommendations"]:
                        print(f"  - {rec}")
            
            sys.exit(0 if results["overall_status"] in ["passed", "warning"] else 1)
        
        elif args.command == "test":
            if args.test_type == "installation":
                results = debug_utils.validate_installation()
            elif args.test_type == "dependencies":
                results = debug_utils.test_dependencies()
            elif args.test_type == "meilisearch":
                results = debug_utils.test_meilisearch_connection()
            elif args.test_type == "tokenization":
                results = debug_utils.test_thai_tokenization()
            else:
                print("Please specify a test type")
                sys.exit(1)
            
            print(json.dumps(results, indent=2, default=str))
            sys.exit(0 if results["status"] in ["passed", "warning"] else 1)
        
        elif args.command == "logs":
            results = debug_utils.analyze_logs(args.lines)
            print(json.dumps(results, indent=2, default=str))
            sys.exit(0 if results["status"] in ["passed", "warning"] else 1)
        
        elif args.command == "interactive":
            debug_utils.interactive_debug_session()
            sys.exit(0)
        
    except KeyboardInterrupt:
        logger.info("Operation interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()