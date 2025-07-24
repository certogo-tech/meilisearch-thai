"""Health check utilities for the Thai tokenizer service."""

import asyncio
import time
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class HealthChecker:
    """Health check utility class."""
    
    def __init__(self):
        self.checks: Dict[str, callable] = {}
        self.last_results: Dict[str, Dict[str, Any]] = {}
    
    def register_check(self, name: str, check_func: callable, timeout: float = 5.0):
        """Register a health check function."""
        self.checks[name] = {
            "func": check_func,
            "timeout": timeout
        }
    
    async def run_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check."""
        if name not in self.checks:
            return {
                "status": "error",
                "message": f"Check '{name}' not found",
                "timestamp": time.time()
            }
        
        check_info = self.checks[name]
        start_time = time.time()
        
        try:
            # Run check with timeout
            result = await asyncio.wait_for(
                check_info["func"](),
                timeout=check_info["timeout"]
            )
            
            check_result = {
                "status": "healthy" if result else "unhealthy",
                "message": "Check passed" if result else "Check failed",
                "response_time": time.time() - start_time,
                "timestamp": time.time()
            }
            
        except asyncio.TimeoutError:
            check_result = {
                "status": "timeout",
                "message": f"Check timed out after {check_info['timeout']}s",
                "response_time": time.time() - start_time,
                "timestamp": time.time()
            }
            
        except Exception as e:
            logger.error(f"Health check '{name}' failed: {e}")
            check_result = {
                "status": "error",
                "message": str(e),
                "response_time": time.time() - start_time,
                "timestamp": time.time()
            }
        
        self.last_results[name] = check_result
        return check_result
    
    async def run_all_checks(self) -> Dict[str, Dict[str, Any]]:
        """Run all registered health checks."""
        results = {}
        
        # Run all checks concurrently
        tasks = [
            (name, self.run_check(name))
            for name in self.checks.keys()
        ]
        
        for name, task in tasks:
            results[name] = await task
        
        return results
    
    def get_overall_status(self, results: Optional[Dict[str, Dict[str, Any]]] = None) -> str:
        """Get overall health status based on check results."""
        if results is None:
            results = self.last_results
        
        if not results:
            return "unknown"
        
        statuses = [result["status"] for result in results.values()]
        
        if all(status == "healthy" for status in statuses):
            return "healthy"
        elif any(status in ["error", "timeout"] for status in statuses):
            return "unhealthy"
        else:
            return "degraded"


# Global health checker instance
health_checker = HealthChecker()


async def check_meilisearch_health(client) -> bool:
    """Check MeiliSearch health."""
    try:
        if client is None:
            return False
        return await client.health_check()
    except Exception:
        return False


async def check_tokenizer_health(config_manager) -> bool:
    """Check tokenizer health."""
    try:
        if config_manager is None:
            return False
        # Simple check - try to get configuration
        config = config_manager.get_config()
        return config is not None
    except Exception:
        return False


def register_default_checks(meilisearch_client, config_manager):
    """Register default health checks."""
    health_checker.register_check(
        "meilisearch",
        lambda: check_meilisearch_health(meilisearch_client),
        timeout=3.0
    )
    
    health_checker.register_check(
        "tokenizer",
        lambda: check_tokenizer_health(config_manager),
        timeout=1.0
    )