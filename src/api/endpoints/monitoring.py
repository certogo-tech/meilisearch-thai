"""Monitoring and health endpoints for the Thai tokenizer API."""

import logging
from typing import Dict, Any, List
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status, Query
from fastapi.responses import JSONResponse

from src.utils.health import health_checker, HealthStatus
from src.utils.logging import get_structured_logger
from src.api.models.responses import ErrorResponse

logger = get_structured_logger(__name__)

router = APIRouter()


@router.get("/health/detailed")
async def detailed_health_check():
    """
    Detailed health check with comprehensive system information.
    
    Returns detailed health status for all registered checks,
    system metrics, and diagnostic information.
    """
    try:
        # Run all health checks
        check_results = await health_checker.run_all_checks()
        
        # Get overall status
        overall_status = health_checker.get_overall_status(check_results)
        
        # Convert results to API format
        checks = {}
        for name, result in check_results.items():
            checks[name] = {
                "status": result.status.value,
                "message": result.message,
                "response_time_ms": result.response_time_ms,
                "timestamp": result.timestamp.isoformat(),
                "details": result.details,
                "error": result.error
            }
        
        # Get system metrics
        system_metrics = health_checker.get_system_metrics()
        tokenizer_metrics = health_checker.get_tokenizer_metrics()
        
        response = {
            "overall_status": overall_status.value,
            "timestamp": datetime.now().isoformat(),
            "checks": checks,
            "system_metrics": {
                "cpu_usage_percent": system_metrics.cpu_usage_percent,
                "memory_usage_percent": system_metrics.memory_usage_percent,
                "memory_used_mb": system_metrics.memory_used_mb,
                "memory_available_mb": system_metrics.memory_available_mb,
                "disk_usage_percent": system_metrics.disk_usage_percent,
                "disk_free_gb": system_metrics.disk_free_gb,
                "uptime_seconds": system_metrics.uptime_seconds,
                "process_count": system_metrics.process_count,
                "load_average": system_metrics.load_average
            },
            "tokenizer_metrics": {
                "total_requests": tokenizer_metrics.total_requests,
                "successful_requests": tokenizer_metrics.successful_requests,
                "failed_requests": tokenizer_metrics.failed_requests,
                "average_response_time_ms": tokenizer_metrics.average_response_time_ms,
                "requests_per_second": tokenizer_metrics.requests_per_second,
                "active_connections": tokenizer_metrics.active_connections,
                "cache_hit_rate": tokenizer_metrics.cache_hit_rate,
                "tokenization_accuracy": tokenizer_metrics.tokenization_accuracy
            }
        }
        
        logger.info("Detailed health check completed",
                   overall_status=overall_status.value,
                   total_checks=len(checks),
                   healthy_checks=sum(1 for c in checks.values() if c["status"] == "healthy"))
        
        return response
        
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


@router.get("/health/check/{check_name}")
async def individual_health_check(check_name: str):
    """
    Run a specific health check.
    
    Args:
        check_name: Name of the health check to run
        
    Returns:
        Result of the specific health check
    """
    try:
        if check_name not in health_checker.checks:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Health check '{check_name}' not found"
            )
        
        result = await health_checker.run_check(check_name)
        
        response = {
            "name": result.name,
            "status": result.status.value,
            "message": result.message,
            "response_time_ms": result.response_time_ms,
            "timestamp": result.timestamp.isoformat(),
            "details": result.details,
            "error": result.error
        }
        
        logger.info("Individual health check completed",
                   check_name=check_name,
                   status=result.status.value,
                   response_time_ms=result.response_time_ms)
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Individual health check failed", 
                    check_name=check_name, error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="health_check_error",
                message=f"Failed to run health check '{check_name}': {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/metrics/system")
async def get_system_metrics():
    """
    Get current system performance metrics.
    
    Returns detailed system resource usage information.
    """
    try:
        metrics = health_checker.get_system_metrics()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "cpu": {
                "usage_percent": metrics.cpu_usage_percent,
                "load_average": metrics.load_average
            },
            "memory": {
                "usage_percent": metrics.memory_usage_percent,
                "used_mb": metrics.memory_used_mb,
                "available_mb": metrics.memory_available_mb
            },
            "disk": {
                "usage_percent": metrics.disk_usage_percent,
                "free_gb": metrics.disk_free_gb
            },
            "system": {
                "uptime_seconds": metrics.uptime_seconds,
                "process_count": metrics.process_count
            }
        }
        
        logger.debug("System metrics retrieved",
                    cpu_usage=metrics.cpu_usage_percent,
                    memory_usage=metrics.memory_usage_percent,
                    disk_usage=metrics.disk_usage_percent)
        
        return response
        
    except Exception as e:
        logger.error("Failed to get system metrics", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="metrics_error",
                message=f"Failed to retrieve system metrics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/metrics/tokenizer")
async def get_tokenizer_metrics():
    """
    Get tokenizer-specific performance metrics.
    
    Returns metrics about tokenization requests, performance, and accuracy.
    """
    try:
        metrics = health_checker.get_tokenizer_metrics()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "requests": {
                "total": metrics.total_requests,
                "successful": metrics.successful_requests,
                "failed": metrics.failed_requests,
                "success_rate": (metrics.successful_requests / metrics.total_requests * 100) if metrics.total_requests > 0 else 0
            },
            "performance": {
                "average_response_time_ms": metrics.average_response_time_ms,
                "requests_per_second": metrics.requests_per_second,
                "active_connections": metrics.active_connections
            },
            "quality": {
                "cache_hit_rate": metrics.cache_hit_rate,
                "tokenization_accuracy": metrics.tokenization_accuracy
            }
        }
        
        logger.debug("Tokenizer metrics retrieved",
                    total_requests=metrics.total_requests,
                    success_rate=response["requests"]["success_rate"],
                    avg_response_time=metrics.average_response_time_ms)
        
        return response
        
    except Exception as e:
        logger.error("Failed to get tokenizer metrics", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="metrics_error",
                message=f"Failed to retrieve tokenizer metrics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/metrics/performance")
async def get_performance_metrics(
    time_window: int = Query(3600, description="Time window in seconds for metrics calculation")
):
    """
    Get detailed performance metrics for the specified time window.
    
    Args:
        time_window: Time window in seconds for metrics calculation (default: 1 hour)
        
    Returns:
        Detailed performance metrics including response times, throughput, and error rates
    """
    try:
        # Get current metrics
        tokenizer_metrics = health_checker.get_tokenizer_metrics()
        system_metrics = health_checker.get_system_metrics()
        
        # Get error trends
        from src.utils.logging import error_tracker
        error_trends = error_tracker.get_error_trends(hours=time_window // 3600)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "time_window_seconds": time_window,
            "performance": {
                "requests_per_second": tokenizer_metrics.requests_per_second,
                "average_response_time_ms": tokenizer_metrics.average_response_time_ms,
                "p95_response_time_ms": health_checker.get_percentile_response_time(95),
                "p99_response_time_ms": health_checker.get_percentile_response_time(99),
                "throughput_tokens_per_second": health_checker.get_token_throughput(),
                "concurrent_requests": tokenizer_metrics.active_connections
            },
            "reliability": {
                "success_rate": (tokenizer_metrics.successful_requests / tokenizer_metrics.total_requests * 100) if tokenizer_metrics.total_requests > 0 else 100,
                "error_rate": error_trends["error_rate_per_hour"],
                "uptime_percentage": health_checker.get_uptime_percentage(),
                "mean_time_to_recovery": health_checker.get_mttr()
            },
            "resource_utilization": {
                "cpu_usage_percent": system_metrics.cpu_usage_percent,
                "memory_usage_percent": system_metrics.memory_usage_percent,
                "memory_efficiency": health_checker.get_memory_efficiency(),
                "gc_pressure": health_checker.get_gc_metrics()
            },
            "quality_metrics": {
                "tokenization_accuracy": tokenizer_metrics.tokenization_accuracy,
                "cache_hit_rate": tokenizer_metrics.cache_hit_rate,
                "false_positive_rate": health_checker.get_false_positive_rate(),
                "compound_word_detection_rate": health_checker.get_compound_word_detection_rate()
            }
        }
        
        logger.info("Performance metrics retrieved",
                   time_window=time_window,
                   requests_per_second=tokenizer_metrics.requests_per_second,
                   success_rate=response["reliability"]["success_rate"],
                   cpu_usage=system_metrics.cpu_usage_percent)
        
        return response
        
    except Exception as e:
        logger.error("Failed to get performance metrics", error=e, time_window=time_window)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="metrics_error",
                message=f"Failed to retrieve performance metrics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/metrics/errors")
async def get_error_metrics(
    hours: int = Query(24, description="Number of hours to analyze for error trends")
):
    """
    Get detailed error metrics and trends.
    
    Args:
        hours: Number of hours to analyze for error trends
        
    Returns:
        Comprehensive error analysis including trends, patterns, and recommendations
    """
    try:
        from src.utils.logging import error_tracker
        
        # Get error summary and trends
        error_summary = error_tracker.get_error_summary()
        error_trends = error_tracker.get_error_trends(hours=hours)
        
        # Analyze error patterns
        error_patterns = health_checker.analyze_error_patterns(hours)
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "analysis_period_hours": hours,
            "summary": {
                "total_errors": error_summary["total_errors"],
                "unique_error_types": len(error_summary["error_counts"]),
                "error_rate_per_hour": error_trends["error_rate_per_hour"],
                "most_common_errors": sorted(
                    error_summary["error_counts"].items(),
                    key=lambda x: x[1],
                    reverse=True
                )[:5]
            },
            "trends": {
                "recent_error_count": error_trends["total_errors"],
                "error_types": error_trends["error_counts"],
                "trend_direction": health_checker.get_error_trend_direction(hours),
                "peak_error_hours": health_checker.get_peak_error_hours(hours)
            },
            "patterns": error_patterns,
            "recent_errors": error_summary["recent_errors"],
            "recommendations": health_checker.get_error_recommendations(error_trends)
        }
        
        logger.info("Error metrics retrieved",
                   analysis_hours=hours,
                   total_errors=error_summary["total_errors"],
                   error_rate=error_trends["error_rate_per_hour"],
                   unique_error_types=len(error_summary["error_counts"]))
        
        return response
        
    except Exception as e:
        logger.error("Failed to get error metrics", error=e, hours=hours)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="metrics_error",
                message=f"Failed to retrieve error metrics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/diagnostics")
async def get_diagnostic_info():
    """
    Get comprehensive diagnostic information.
    
    Returns detailed diagnostic data for troubleshooting and monitoring.
    """
    try:
        diagnostic_info = health_checker.get_diagnostic_info()
        
        logger.info("Diagnostic information retrieved",
                   service_uptime=diagnostic_info["service_info"]["uptime_seconds"],
                   total_checks=len(diagnostic_info["health_checks"]),
                   registered_checks=len(diagnostic_info["registered_checks"]))
        
        return diagnostic_info
        
    except Exception as e:
        logger.error("Failed to get diagnostic information", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="diagnostics_error",
                message=f"Failed to retrieve diagnostic information: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/diagnostics/tokenization")
async def get_tokenization_diagnostics(
    test_text: str = Query("ทดสอบการแบ่งคำภาษาไทย", description="Text to use for tokenization testing")
):
    """
    Get tokenization-specific diagnostic information.
    
    Args:
        test_text: Text to use for diagnostic tokenization test
        
    Returns:
        Detailed tokenization diagnostic results
    """
    try:
        from src.tokenizer.thai_segmenter import ThaiSegmenter
        from src.tokenizer.token_processor import TokenProcessor
        from src.tokenizer.query_processor import QueryProcessor
        
        # Test tokenization with different engines
        engines = ["newmm", "attacut", "deepcut"]
        tokenization_results = {}
        
        for engine in engines:
            try:
                segmenter = ThaiSegmenter(engine=engine)
                result = segmenter.segment_text(test_text)
                
                tokenization_results[engine] = {
                    "tokens": result.tokens,
                    "token_count": len(result.tokens),
                    "processing_time_ms": result.processing_time_ms,
                    "word_boundaries": result.word_boundaries,
                    "engine": result.engine,
                    "success": True
                }
            except Exception as e:
                tokenization_results[engine] = {
                    "success": False,
                    "error": str(e)
                }
        
        # Test token processing
        try:
            processor = TokenProcessor()
            # Use the first successful tokenization result
            successful_result = next(
                (r for r in tokenization_results.values() if r.get("success")),
                None
            )
            
            if successful_result:
                # Create a mock tokenization result for processing
                from src.tokenizer.thai_segmenter import TokenizationResult
                mock_result = TokenizationResult(
                    original_text=test_text,
                    tokens=successful_result["tokens"],
                    word_boundaries=successful_result["word_boundaries"],
                    processing_time_ms=successful_result["processing_time_ms"],
                    engine=successful_result["engine"]
                )
                
                processed = processor.process_tokenization_result(mock_result)
                token_processing = {
                    "success": True,
                    "processed_tokens": processed.processed_tokens if hasattr(processed, 'processed_tokens') else [],
                    "separators_added": True
                }
            else:
                token_processing = {
                    "success": False,
                    "error": "No successful tokenization to process"
                }
        except Exception as e:
            token_processing = {
                "success": False,
                "error": str(e)
            }
        
        # Test query processing
        try:
            query_processor = QueryProcessor()
            query_result = query_processor.process_search_query(test_text)
            
            query_processing = {
                "success": True,
                "processed_query": query_result.processed_query,
                "query_tokens": len(query_result.query_tokens),
                "search_variants": len(query_result.search_variants),
                "suggested_completions": len(query_result.suggested_completions),
                "processing_metadata": query_result.processing_metadata
            }
        except Exception as e:
            query_processing = {
                "success": False,
                "error": str(e)
            }
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "test_text": test_text,
            "test_text_length": len(test_text),
            "tokenization_engines": tokenization_results,
            "token_processing": token_processing,
            "query_processing": query_processing,
            "recommendations": []
        }
        
        # Add recommendations based on results
        if not any(r.get("success") for r in tokenization_results.values()):
            response["recommendations"].append("All tokenization engines failed - check PyThaiNLP installation")
        
        if not token_processing.get("success"):
            response["recommendations"].append("Token processing failed - check token processor configuration")
        
        if not query_processing.get("success"):
            response["recommendations"].append("Query processing failed - check query processor setup")
        
        logger.info("Tokenization diagnostics completed",
                   test_text_length=len(test_text),
                   successful_engines=sum(1 for r in tokenization_results.values() if r.get("success")),
                   token_processing_success=token_processing.get("success", False),
                   query_processing_success=query_processing.get("success", False))
        
        return response
        
    except Exception as e:
        logger.error("Tokenization diagnostics failed", error=e, test_text=test_text)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="diagnostics_error",
                message=f"Failed to run tokenization diagnostics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/health/checks")
async def list_health_checks():
    """
    List all registered health checks.
    
    Returns information about all available health checks.
    """
    try:
        checks_info = {}
        
        for name, check_info in health_checker.checks.items():
            last_result = health_checker.last_results.get(name)
            
            checks_info[name] = {
                "timeout": check_info["timeout"],
                "critical": check_info.get("critical", True),
                "last_run": {
                    "status": last_result.status.value if last_result else "never_run",
                    "timestamp": last_result.timestamp.isoformat() if last_result else None,
                    "response_time_ms": last_result.response_time_ms if last_result else None
                }
            }
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "total_checks": len(checks_info),
            "critical_checks": sum(1 for c in checks_info.values() if c["critical"]),
            "checks": checks_info
        }
        
        logger.debug("Health checks listed", total_checks=len(checks_info))
        
        return response
        
    except Exception as e:
        logger.error("Failed to list health checks", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="health_checks_error",
                message=f"Failed to list health checks: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/diagnostics/meilisearch")
async def get_meilisearch_diagnostics():
    """
    Get detailed MeiliSearch diagnostic information.
    
    Returns comprehensive MeiliSearch health, configuration, and performance data.
    """
    try:
        from src.meilisearch_integration.client import MeiliSearchClient
        from src.tokenizer.config_manager import ConfigManager
        
        # Get MeiliSearch client from app state
        # This would typically be injected as a dependency
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
        
        # Test connection and get health
        health_result = await client.health_check()
        
        # Get index information
        indexes_info = await client.get_indexes_info()
        
        # Get stats if available
        stats = await client.get_stats()
        
        # Test tokenization settings
        tokenization_test = await client.test_tokenization_settings()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "connection": {
                "host": meilisearch_config.host,
                "status": health_result.get("status", "unknown"),
                "response_time_ms": health_result.get("response_time_ms", 0),
                "version": health_result.get("version", "unknown")
            },
            "indexes": indexes_info,
            "statistics": stats,
            "tokenization": {
                "settings_applied": tokenization_test.get("settings_applied", False),
                "thai_support": tokenization_test.get("thai_support", False),
                "custom_separators": tokenization_test.get("custom_separators", []),
                "test_results": tokenization_test.get("test_results", {})
            },
            "performance": {
                "average_search_time_ms": stats.get("average_search_time_ms", 0),
                "total_documents": stats.get("total_documents", 0),
                "index_size_mb": stats.get("index_size_mb", 0)
            }
        }
        
        logger.info("MeiliSearch diagnostics completed",
                   connection_status=health_result.get("status"),
                   total_indexes=len(indexes_info),
                   total_documents=stats.get("total_documents", 0))
        
        return response
        
    except Exception as e:
        logger.error("MeiliSearch diagnostics failed", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="diagnostics_error",
                message=f"Failed to run MeiliSearch diagnostics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.get("/diagnostics/configuration")
async def get_configuration_diagnostics():
    """
    Get comprehensive configuration diagnostic information.
    
    Returns current configuration state, validation results, and recommendations.
    """
    try:
        from src.tokenizer.config_manager import ConfigManager
        
        config_manager = ConfigManager()
        
        # Get current configuration
        current_config = config_manager.get_config()
        meilisearch_config = config_manager.get_meilisearch_config()
        tokenizer_config = config_manager.get_tokenizer_config()
        
        # Validate configuration
        validation_results = config_manager.validate_configuration()
        
        # Check environment variables
        env_check = health_checker.check_environment_variables()
        
        # Get configuration history if available
        config_history = config_manager.get_configuration_history()
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "current_configuration": {
                "tokenizer": {
                    "engine": tokenizer_config.engine,
                    "model_version": tokenizer_config.model_version,
                    "custom_dictionary_enabled": bool(tokenizer_config.custom_dictionary),
                    "fallback_enabled": tokenizer_config.enable_fallback
                },
                "meilisearch": {
                    "host": meilisearch_config.host,
                    "timeout_ms": meilisearch_config.timeout_ms,
                    "max_retries": meilisearch_config.max_retries,
                    "connection_pool_size": meilisearch_config.connection_pool_size
                },
                "processing": {
                    "batch_size": current_config.get("batch_size", 100),
                    "max_text_length": current_config.get("max_text_length", 10000),
                    "enable_caching": current_config.get("enable_caching", True)
                }
            },
            "validation": {
                "is_valid": validation_results["is_valid"],
                "errors": validation_results.get("errors", []),
                "warnings": validation_results.get("warnings", []),
                "recommendations": validation_results.get("recommendations", [])
            },
            "environment": {
                "required_vars_present": env_check["required_vars_present"],
                "missing_vars": env_check.get("missing_vars", []),
                "optional_vars": env_check.get("optional_vars", {}),
                "environment_type": env_check.get("environment_type", "unknown")
            },
            "history": {
                "total_changes": len(config_history),
                "recent_changes": config_history[-5:] if config_history else [],
                "last_modified": config_history[-1]["timestamp"] if config_history else None
            }
        }
        
        logger.info("Configuration diagnostics completed",
                   config_valid=validation_results["is_valid"],
                   total_errors=len(validation_results.get("errors", [])),
                   total_warnings=len(validation_results.get("warnings", [])))
        
        return response
        
    except Exception as e:
        logger.error("Configuration diagnostics failed", error=e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="diagnostics_error",
                message=f"Failed to run configuration diagnostics: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )


@router.post("/diagnostics/run-tests")
async def run_diagnostic_tests(
    test_types: List[str] = Query(["tokenization", "meilisearch", "performance"], 
                                 description="Types of tests to run")
):
    """
    Run comprehensive diagnostic tests.
    
    Args:
        test_types: List of test types to run (tokenization, meilisearch, performance, integration)
        
    Returns:
        Results of all requested diagnostic tests
    """
    try:
        test_results = {}
        
        if "tokenization" in test_types:
            test_results["tokenization"] = await health_checker.run_tokenization_tests()
        
        if "meilisearch" in test_types:
            test_results["meilisearch"] = await health_checker.run_meilisearch_tests()
        
        if "performance" in test_types:
            test_results["performance"] = await health_checker.run_performance_tests()
        
        if "integration" in test_types:
            test_results["integration"] = await health_checker.run_integration_tests()
        
        # Calculate overall test status
        all_passed = all(
            result.get("status") == "passed" 
            for result in test_results.values()
        )
        
        response = {
            "timestamp": datetime.now().isoformat(),
            "test_types": test_types,
            "overall_status": "passed" if all_passed else "failed",
            "results": test_results,
            "summary": {
                "total_tests": sum(len(result.get("tests", [])) for result in test_results.values()),
                "passed_tests": sum(
                    len([t for t in result.get("tests", []) if t.get("status") == "passed"])
                    for result in test_results.values()
                ),
                "failed_tests": sum(
                    len([t for t in result.get("tests", []) if t.get("status") == "failed"])
                    for result in test_results.values()
                )
            }
        }
        
        logger.info("Diagnostic tests completed",
                   test_types=test_types,
                   overall_status=response["overall_status"],
                   total_tests=response["summary"]["total_tests"],
                   passed_tests=response["summary"]["passed_tests"])
        
        return response
        
    except Exception as e:
        logger.error("Diagnostic tests failed", error=e, test_types=test_types)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error="diagnostics_error",
                message=f"Failed to run diagnostic tests: {str(e)}",
                timestamp=datetime.now()
            ).model_dump()
        )