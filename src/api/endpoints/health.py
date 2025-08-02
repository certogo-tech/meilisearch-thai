"""Enhanced health check endpoints for on-premise deployment monitoring."""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from fastapi import APIRouter, HTTPException, Depends, status, Query, Response
from fastapi.responses import JSONResponse, PlainTextResponse

from src.utils.health import health_checker, HealthStatus
from src.utils.logging import get_structured_logger
from src.api.models.responses import ErrorResponse

logger = get_structured_logger(__name__)

router = APIRouter()


@router.get("/health")
async def basic_health_check():
    """
    Basic health check endpoint for load balancers and container orchestration.
    
    Returns simple status for quick health verification.
    """
    try:
        # Run critical health checks only
        check_results = await health_checker.run_all_checks()
        
        # Filter only critical checks
        critical_results = {
            name: result for name, result in check_results.items()
            if health_checker.checks.get(name, {}).get("critical", True)
        }
        
        overall_status = health_checker.get_overall_status(critical_results)
        
        if overall_status == HealthStatus.HEALTHY:
            return {"status": "healthy", "timestamp": datetime.now().isoformat()}
        elif overall_status == HealthStatus.DEGRADED:
            return Response(
                content='{"status": "degraded", "timestamp": "' + datetime.now().isoformat() + '"}',
                status_code=200,
                media_type="application/json"
            )
        else:
            return Response(
                content='{"status": "unhealthy", "timestamp": "' + datetime.now().isoformat() + '"}',
                status_code=503,
                media_type="application/json"
            )
            
    except Exception as e:
        logger.error("Basic health check failed", error=e)
        return Response(
            content='{"status": "error", "error": "' + str(e) + '", "timestamp": "' + datetime.now().isoformat() + '"}',
            status_code=503,
            media_type="application/json"
        )


@router.get("/health/live")
async def liveness_probe():
    """
    Kubernetes liveness probe endpoint.
    
    Returns 200 if the service is running, 503 if it should be restarted.
    """
    try:
        # Check if the service is fundamentally operational
        from src.tokenizer.thai_segmenter import ThaiSegmenter
        
        # Quick tokenization test
        segmenter = ThaiSegmenter()
        test_result = segmenter.segment_text("ทดสอบ")
        
        if test_result.tokens:
            return {"status": "alive", "timestamp": datetime.now().isoformat()}
        else:
            return Response(
                content='{"status": "dead", "reason": "tokenization_failed"}',
                status_code=503,
                media_type="application/json"
            )
            
    except Exception as e:
        logger.error("Liveness probe failed", error=e)
        return Response(
            content='{"status": "dead", "error": "' + str(e) + '"}',
            status_code=503,
            media_type="application/json"
        )


@router.get("/health/ready")
async def readiness_probe():
    """
    Kubernetes readiness probe endpoint.
    
    Returns 200 if the service is ready to accept traffic, 503 if not ready.
    """
    try:
        # Check all critical dependencies
        check_results = await health_checker.run_all_checks()
        
        # Check critical systems
        critical_checks = ["meilisearch", "tokenizer", "dependencies"]
        for check_name in critical_checks:
            if check_name in check_results:
                result = check_results[check_name]
                if result.status in [HealthStatus.ERROR, HealthStatus.TIMEOUT, HealthStatus.UNHEALTHY]:
                    return Response(
                        content=f'{{"status": "not_ready", "reason": "{check_name}_failed", "details": "{result.message}"}}',
                        status_code=503,
                        media_type="application/json"
                    )
        
        return {"status": "ready", "timestamp": datetime.now().isoformat()}
        
    except Exception as e:
        logger.error("Readiness probe failed", error=e)
        return Response(
            content='{"status": "not_ready", "error": "' + str(e) + '"}',
            status_code=503,
            media_type="application/json"
        )


@router.get("/health/startup")
async def startup_probe():
    """
    Kubernetes startup probe endpoint.
    
    Returns 200 when the service has completed startup, 503 during startup.
    """
    try:
        # Check if all initialization is complete
        uptime = time.time() - health_checker.start_time
        
        # Allow 30 seconds for startup
        if uptime < 30:
            # Check if critical components are initialized
            check_results = await health_checker.run_all_checks()
            
            critical_ready = all(
                check_results.get(name, type('obj', (object,), {'status': HealthStatus.ERROR})).status == HealthStatus.HEALTHY
                for name in ["tokenizer", "dependencies"]
            )
            
            if critical_ready:
                return {"status": "started", "uptime_seconds": int(uptime)}
            else:
                return Response(
                    content='{"status": "starting", "uptime_seconds": ' + str(int(uptime)) + '}',
                    status_code=503,
                    media_type="application/json"
                )
        else:
            return {"status": "started", "uptime_seconds": int(uptime)}
            
    except Exception as e:
        logger.error("Startup probe failed", error=e)
        return Response(
            content='{"status": "startup_failed", "error": "' + str(e) + '"}',
            status_code=503,
            media_type="application/json"
        )


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Comprehensive health check with detailed dependency status.
    
    Returns detailed health information for monitoring and troubleshooting.
    """
    try:
        # Run all health checks
        check_results = await health_checker.run_all_checks()
        
        # Get overall status
        overall_status = health_checker.get_overall_status(check_results)
        
        # Convert results to detailed format
        checks = {}
        for name, result in check_results.items():
            check_info = health_checker.checks.get(name, {})
            checks[name] = {
                "status": result.status.value,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
                "timestamp": result.timestamp.isoformat(),
                "critical": check_info.get("critical", True),
                "timeout": check_info.get("timeout", 5.0),
                "details": result.details,
                "error": result.error
            }
        
        # Get system metrics
        system_metrics = health_checker.get_system_metrics()
        tokenizer_metrics = health_checker.get_tokenizer_metrics()
        
        # Calculate health score (0-100)
        healthy_checks = sum(1 for c in checks.values() if c["status"] == "healthy")
        health_score = (healthy_checks / len(checks) * 100) if checks else 0
        
        response = {
            "overall_status": overall_status.value,
            "health_score": health_score,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(time.time() - health_checker.start_time),
            "version": "1.0.0",
            "checks": checks,
            "system_metrics": {
                "cpu_usage_percent": system_metrics.cpu_usage_percent,
                "memory_usage_percent": system_metrics.memory_usage_percent,
                "memory_used_mb": system_metrics.memory_used_mb,
                "memory_available_mb": system_metrics.memory_available_mb,
                "disk_usage_percent": system_metrics.disk_usage_percent,
                "disk_free_gb": system_metrics.disk_free_gb,
                "process_count": system_metrics.process_count,
                "load_average": system_metrics.load_average
            },
            "performance_metrics": {
                "total_requests": tokenizer_metrics.total_requests,
                "successful_requests": tokenizer_metrics.successful_requests,
                "failed_requests": tokenizer_metrics.failed_requests,
                "success_rate_percent": (tokenizer_metrics.successful_requests / tokenizer_metrics.total_requests * 100) if tokenizer_metrics.total_requests > 0 else 100,
                "average_response_time_ms": tokenizer_metrics.average_response_time_ms,
                "requests_per_second": tokenizer_metrics.requests_per_second,
                "p95_response_time_ms": health_checker.get_percentile_response_time(95),
                "p99_response_time_ms": health_checker.get_percentile_response_time(99)
            }
        }
        
        # Set appropriate HTTP status based on health
        if overall_status == HealthStatus.HEALTHY:
            status_code = 200
        elif overall_status == HealthStatus.DEGRADED:
            status_code = 200  # Still operational
        else:
            status_code = 503  # Service unavailable
        
        logger.info("Detailed health check completed",
                   overall_status=overall_status.value,
                   health_score=health_score,
                   total_checks=len(checks),
                   healthy_checks=healthy_checks)
        
        return Response(
            content=response,
            status_code=status_code,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error("Detailed health check failed", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="health_check_error",
                message=f"Failed to perform detailed health check: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/health/dependencies")
async def dependency_health_check():
    """
    Check health of all external dependencies.
    
    Returns status of MeiliSearch, tokenizer engines, and other dependencies.
    """
    try:
        # Run dependency-specific checks
        dependency_checks = ["meilisearch", "tokenizer", "dependencies", "system_resources"]
        
        results = {}
        for check_name in dependency_checks:
            if check_name in health_checker.checks:
                result = await health_checker.run_check(check_name)
                results[check_name] = {
                    "status": result.status.value,
                    "message": result.message,
                    "response_time_ms": result.response_time_ms,
                    "details": result.details,
                    "error": result.error
                }
        
        # Additional dependency tests
        dependency_tests = await _run_dependency_tests()
        
        overall_healthy = all(
            r["status"] == "healthy" for r in results.values()
        ) and dependency_tests["all_passed"]
        
        response = {
            "overall_status": "healthy" if overall_healthy else "unhealthy",
            "timestamp": datetime.now().isoformat(),
            "dependencies": results,
            "dependency_tests": dependency_tests
        }
        
        status_code = 200 if overall_healthy else 503
        
        return Response(
            content=response,
            status_code=status_code,
            media_type="application/json"
        )
        
    except Exception as e:
        logger.error("Dependency health check failed", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to check dependencies: {str(e)}"
        )


async def _run_dependency_tests() -> Dict[str, Any]:
    """Run comprehensive dependency tests."""
    tests = {}
    
    # Test tokenization engines
    try:
        from src.tokenizer.thai_segmenter import ThaiSegmenter
        
        engines = ["newmm", "attacut", "deepcut"]
        engine_results = {}
        
        for engine in engines:
            try:
                segmenter = ThaiSegmenter(engine=engine)
                result = segmenter.segment_text("ทดสอบ")
                engine_results[engine] = {
                    "available": True,
                    "tokens": len(result.tokens),
                    "processing_time_ms": result.processing_time_ms
                }
            except Exception as e:
                engine_results[engine] = {
                    "available": False,
                    "error": str(e)
                }
        
        tests["tokenization_engines"] = engine_results
        
    except Exception as e:
        tests["tokenization_engines"] = {"error": str(e)}
    
    # Test MeiliSearch connectivity
    try:
        from src.meilisearch_integration.client import MeiliSearchClient
        from src.tokenizer.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        meilisearch_config = config_manager.get_meilisearch_config()
        
        from src.meilisearch_integration.client import MeiliSearchConfig as ClientConfig
        client_config = ClientConfig(
            host=meilisearch_config.host,
            api_key=meilisearch_config.api_key,
            timeout=meilisearch_config.timeout_ms // 1000,
            max_retries=meilisearch_config.max_retries
        )
        client = MeiliSearchClient(client_config)
        
        health_result = await client.health_check()
        tests["meilisearch_connectivity"] = {
            "connected": health_result.get("status") == "healthy",
            "response_time_ms": health_result.get("response_time_ms", 0),
            "version": health_result.get("version", "unknown")
        }
        
    except Exception as e:
        tests["meilisearch_connectivity"] = {
            "connected": False,
            "error": str(e)
        }
    
    # Test Python dependencies
    try:
        import pythainlp
        import meilisearch
        import fastapi
        import pydantic
        
        tests["python_dependencies"] = {
            "pythainlp": pythainlp.__version__,
            "meilisearch": meilisearch.version.__version__,
            "fastapi": fastapi.__version__,
            "pydantic": pydantic.__version__,
            "all_available": True
        }
        
    except ImportError as e:
        tests["python_dependencies"] = {
            "all_available": False,
            "missing": str(e)
        }
    
    # Calculate overall test status
    all_passed = True
    for test_name, test_result in tests.items():
        if isinstance(test_result, dict):
            if "error" in test_result:
                all_passed = False
            elif test_name == "tokenization_engines":
                # At least one engine should be available
                available_engines = sum(1 for r in test_result.values() if isinstance(r, dict) and r.get("available", False))
                if available_engines == 0:
                    all_passed = False
            elif test_name == "meilisearch_connectivity":
                if not test_result.get("connected", False):
                    all_passed = False
            elif test_name == "python_dependencies":
                if not test_result.get("all_available", False):
                    all_passed = False
    
    tests["all_passed"] = all_passed
    return tests


@router.get("/health/check/{check_name}")
async def individual_health_check(check_name: str):
    """
    Run a specific health check by name.
    
    Args:
        check_name: Name of the health check to run
        
    Returns:
        Result of the specific health check
    """
    try:
        if check_name not in health_checker.checks:
            available_checks = list(health_checker.checks.keys())
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Health check '{check_name}' not found. Available checks: {available_checks}"
            )
        
        result = await health_checker.run_check(check_name)
        check_info = health_checker.checks[check_name]
        
        response = {
            "name": result.name,
            "status": result.status.value,
            "message": result.message,
            "response_time_ms": result.response_time_ms,
            "timestamp": result.timestamp.isoformat(),
            "critical": check_info.get("critical", True),
            "timeout": check_info.get("timeout", 5.0),
            "details": result.details,
            "error": result.error
        }
        
        # Set HTTP status based on check result
        if result.status == HealthStatus.HEALTHY:
            status_code = 200
        elif result.status == HealthStatus.DEGRADED:
            status_code = 200
        else:
            status_code = 503
        
        logger.info("Individual health check completed",
                   check_name=check_name,
                   status=result.status.value,
                   response_time_ms=result.response_time_ms)
        
        return Response(
            content=response,
            status_code=status_code,
            media_type="application/json"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Individual health check failed", 
                    check_name=check_name, error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to run health check '{check_name}': {str(e)}"
        )


@router.get("/health/summary")
async def health_summary():
    """
    Get a summary of all health checks with key metrics.
    
    Returns condensed health information suitable for dashboards.
    """
    try:
        # Run all health checks
        check_results = await health_checker.run_all_checks()
        
        # Calculate summary statistics
        total_checks = len(check_results)
        healthy_checks = sum(1 for r in check_results.values() if r.status == HealthStatus.HEALTHY)
        degraded_checks = sum(1 for r in check_results.values() if r.status == HealthStatus.DEGRADED)
        unhealthy_checks = sum(1 for r in check_results.values() if r.status in [HealthStatus.UNHEALTHY, HealthStatus.ERROR, HealthStatus.TIMEOUT])
        
        # Get key metrics
        system_metrics = health_checker.get_system_metrics()
        tokenizer_metrics = health_checker.get_tokenizer_metrics()
        
        # Calculate health score
        health_score = (healthy_checks / total_checks * 100) if total_checks > 0 else 0
        
        # Determine overall status
        overall_status = health_checker.get_overall_status(check_results)
        
        response = {
            "overall_status": overall_status.value,
            "health_score": health_score,
            "timestamp": datetime.now().isoformat(),
            "uptime_seconds": int(time.time() - health_checker.start_time),
            "checks_summary": {
                "total": total_checks,
                "healthy": healthy_checks,
                "degraded": degraded_checks,
                "unhealthy": unhealthy_checks
            },
            "key_metrics": {
                "cpu_usage_percent": system_metrics.cpu_usage_percent,
                "memory_usage_percent": system_metrics.memory_usage_percent,
                "disk_usage_percent": system_metrics.disk_usage_percent,
                "requests_per_second": tokenizer_metrics.requests_per_second,
                "average_response_time_ms": tokenizer_metrics.average_response_time_ms,
                "success_rate_percent": (tokenizer_metrics.successful_requests / tokenizer_metrics.total_requests * 100) if tokenizer_metrics.total_requests > 0 else 100
            },
            "alerts": _generate_health_alerts(check_results, system_metrics, tokenizer_metrics)
        }
        
        logger.info("Health summary generated",
                   overall_status=overall_status.value,
                   health_score=health_score,
                   total_alerts=len(response["alerts"]))
        
        return response
        
    except Exception as e:
        logger.error("Health summary failed", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate health summary: {str(e)}"
        )


def _generate_health_alerts(check_results, system_metrics, tokenizer_metrics) -> List[Dict[str, Any]]:
    """Generate health alerts based on current status."""
    alerts = []
    
    # Check for failed health checks
    for name, result in check_results.items():
        if result.status in [HealthStatus.ERROR, HealthStatus.TIMEOUT, HealthStatus.UNHEALTHY]:
            check_info = health_checker.checks.get(name, {})
            alerts.append({
                "type": "health_check_failed",
                "severity": "critical" if check_info.get("critical", True) else "warning",
                "message": f"Health check '{name}' failed: {result.message}",
                "timestamp": result.timestamp.isoformat(),
                "details": {"check_name": name, "error": result.error}
            })
    
    # Check system resource alerts
    if system_metrics.cpu_usage_percent > 80:
        alerts.append({
            "type": "high_cpu_usage",
            "severity": "warning" if system_metrics.cpu_usage_percent < 90 else "critical",
            "message": f"High CPU usage: {system_metrics.cpu_usage_percent:.1f}%",
            "timestamp": datetime.now().isoformat(),
            "details": {"cpu_usage_percent": system_metrics.cpu_usage_percent}
        })
    
    if system_metrics.memory_usage_percent > 85:
        alerts.append({
            "type": "high_memory_usage",
            "severity": "warning" if system_metrics.memory_usage_percent < 95 else "critical",
            "message": f"High memory usage: {system_metrics.memory_usage_percent:.1f}%",
            "timestamp": datetime.now().isoformat(),
            "details": {"memory_usage_percent": system_metrics.memory_usage_percent}
        })
    
    if system_metrics.disk_usage_percent > 90:
        alerts.append({
            "type": "high_disk_usage",
            "severity": "critical",
            "message": f"High disk usage: {system_metrics.disk_usage_percent:.1f}%",
            "timestamp": datetime.now().isoformat(),
            "details": {"disk_usage_percent": system_metrics.disk_usage_percent}
        })
    
    # Check performance alerts
    if tokenizer_metrics.total_requests > 0:
        success_rate = tokenizer_metrics.successful_requests / tokenizer_metrics.total_requests * 100
        if success_rate < 95:
            alerts.append({
                "type": "low_success_rate",
                "severity": "warning" if success_rate > 90 else "critical",
                "message": f"Low success rate: {success_rate:.1f}%",
                "timestamp": datetime.now().isoformat(),
                "details": {
                    "success_rate_percent": success_rate,
                    "failed_requests": tokenizer_metrics.failed_requests,
                    "total_requests": tokenizer_metrics.total_requests
                }
            })
    
    if tokenizer_metrics.average_response_time_ms > 1000:
        alerts.append({
            "type": "high_response_time",
            "severity": "warning" if tokenizer_metrics.average_response_time_ms < 2000 else "critical",
            "message": f"High average response time: {tokenizer_metrics.average_response_time_ms:.1f}ms",
            "timestamp": datetime.now().isoformat(),
            "details": {"average_response_time_ms": tokenizer_metrics.average_response_time_ms}
        })
    
    return alerts