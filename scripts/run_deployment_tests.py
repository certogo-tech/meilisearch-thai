#!/usr/bin/env python3
"""
Test runner script for deployment integration tests.

This script provides a convenient way to run all deployment-related tests
including integration tests, performance tests, and security tests.
"""

import asyncio
import argparse
import sys
import subprocess
from pathlib import Path
from typing import List, Dict, Any


def run_pytest_tests(test_files: List[str], output_dir: Path, verbose: bool = False) -> Dict[str, Any]:
    """Run pytest tests and return results."""
    results = {}
    
    for test_file in test_files:
        test_path = Path(test_file)
        if not test_path.exists():
            results[test_file] = {
                "status": "skipped",
                "reason": "Test file not found"
            }
            continue
        
        print(f"Running tests: {test_file}")
        
        # Prepare pytest command
        cmd = [
            sys.executable, "-m", "pytest",
            str(test_path),
            "-v" if verbose else "-q",
            "--tb=short",
            "--json-report",
            "--json-report-file", str(output_dir / f"{test_path.stem}_results.json")
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600  # 10 minutes timeout
            )
            
            results[test_file] = {
                "status": "passed" if result.returncode == 0 else "failed",
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr
            }
            
            if verbose:
                print(f"  Return code: {result.returncode}")
                if result.stdout:
                    print(f"  Output: {result.stdout[:500]}...")
                if result.stderr:
                    print(f"  Errors: {result.stderr[:500]}...")
            
        except subprocess.TimeoutExpired:
            results[test_file] = {
                "status": "timeout",
                "reason": "Test execution exceeded timeout"
            }
            print(f"  TIMEOUT: Test execution exceeded 10 minutes")
        
        except Exception as e:
            results[test_file] = {
                "status": "error",
                "reason": str(e)
            }
            print(f"  ERROR: {e}")
    
    return results


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="Run deployment integration tests")
    parser.add_argument(
        "--test-type", 
        choices=["all", "integration", "performance", "security", "validation"],
        default="all",
        help="Type of tests to run"
    )
    parser.add_argument(
        "--output-dir", 
        default="test_results",
        help="Output directory for test results"
    )
    parser.add_argument(
        "--verbose", 
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--config",
        help="Configuration file for deployment tests"
    )
    
    args = parser.parse_args()
    
    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Define test files by category
    test_categories = {
        "integration": [
            "tests/integration/test_on_premise_deployment_integration.py",
            "tests/integration/test_deployment_orchestration.py"
        ],
        "performance": [
            "tests/performance/test_deployment_performance.py"
        ],
        "security": [
            "tests/integration/test_deployment_security.py"
        ],
        "validation": [
            "tests/integration/test_deployment_validation_reporting.py"
        ]
    }
    
    # Determine which tests to run
    if args.test_type == "all":
        test_files = []
        for category_tests in test_categories.values():
            test_files.extend(category_tests)
    else:
        test_files = test_categories.get(args.test_type, [])
    
    if not test_files:
        print(f"No test files found for type: {args.test_type}")
        sys.exit(1)
    
    print(f"Running {args.test_type} tests...")
    print(f"Test files: {len(test_files)}")
    print(f"Output directory: {output_dir}")
    
    # Run tests
    results = run_pytest_tests(test_files, output_dir, args.verbose)
    
    # Print summary
    print("\n" + "="*60)
    print("TEST RESULTS SUMMARY")
    print("="*60)
    
    total_tests = len(results)
    passed_tests = len([r for r in results.values() if r["status"] == "passed"])
    failed_tests = len([r for r in results.values() if r["status"] == "failed"])
    skipped_tests = len([r for r in results.values() if r["status"] == "skipped"])
    error_tests = len([r for r in results.values() if r["status"] in ["error", "timeout"]])
    
    print(f"Total test files: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    print(f"Skipped: {skipped_tests}")
    print(f"Errors/Timeouts: {error_tests}")
    
    # Print detailed results
    for test_file, result in results.items():
        status_symbol = {
            "passed": "✅",
            "failed": "❌", 
            "skipped": "⏭️",
            "error": "💥",
            "timeout": "⏰"
        }.get(result["status"], "❓")
        
        print(f"\n{status_symbol} {test_file}: {result['status'].upper()}")
        
        if result.get("reason"):
            print(f"   Reason: {result['reason']}")
        
        if result.get("return_code") is not None and result["return_code"] != 0:
            print(f"   Return code: {result['return_code']}")
    
    # Print artifacts
    print(f"\nTest artifacts saved to: {output_dir}")
    artifacts = list(output_dir.glob("*_results.json"))
    if artifacts:
        print("Generated files:")
        for artifact in artifacts:
            print(f"  - {artifact}")
    
    # Exit with appropriate code
    if failed_tests > 0 or error_tests > 0:
        print(f"\n❌ Tests failed: {failed_tests + error_tests} test files had issues")
        sys.exit(1)
    elif passed_tests == 0:
        print(f"\n⚠️  No tests were executed successfully")
        sys.exit(1)
    else:
        print(f"\n✅ All tests passed: {passed_tests}/{total_tests} test files successful")
        sys.exit(0)


if __name__ == "__main__":
    main()